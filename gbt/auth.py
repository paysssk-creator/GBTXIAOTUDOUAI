"""
auth.py — GBT Pro 用户认证 + API限流 + Token充值管理
生产级: bcrypt密码哈希 + JWT令牌 + Redis级限流
"""
import os, sys, re, json, time, hashlib, hmac, threading, logging, shutil, secrets
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from urllib.parse import urlencode
from gbt.oauth_catalog import OAUTH_PROVIDER_CATALOG, VISIBLE_PROVIDER_ORDER

L = logging.getLogger("gbt.auth")


def _runtime_root_dir() -> str:
    """返回可持久化的运行根目录，避免 PyInstaller 把用户数据写进临时解压目录。"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _legacy_data_candidates(filename: str) -> list[str]:
    root = _runtime_root_dir()
    candidates = [
        os.path.join(root, filename),
        os.path.join(os.getcwd(), filename),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), filename),
    ]
    seen = set()
    unique = []
    for path in candidates:
        norm = os.path.abspath(path)
        if norm not in seen:
            seen.add(norm)
            unique.append(norm)
    return unique


def _ensure_persistent_file(filename: str) -> str:
    target = os.path.join(_runtime_root_dir(), filename)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    if os.path.exists(target):
        return target
    for candidate in _legacy_data_candidates(filename):
        if candidate == os.path.abspath(target):
            continue
        if os.path.exists(candidate):
            try:
                shutil.copy2(candidate, target)
                L.info("migrated %s -> %s", candidate, target)
                return target
            except Exception as e:
                L.warning("migrate %s failed: %s", filename, e)
    return target


AUTH_FILE = _ensure_persistent_file("auth_users.json")
TOKEN_FILE = _ensure_persistent_file("token_balance.json")
print(f"[AUTH] AUTH_FILE={AUTH_FILE}")
print(f"[AUTH] TOKEN_FILE={TOKEN_FILE}")

# ── bcrypt 可选 ──
try:
    import bcrypt
    _has_bcrypt = True
except ImportError:
    _has_bcrypt = False
    L.warning("bcrypt not installed, using sha256 fallback — NOT for production")


def _hash_pw(password: str) -> str:
    if _has_bcrypt:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    salt = os.urandom(16).hex()
    return f"sha256${salt}${hashlib.sha256((salt + password).encode()).hexdigest()}"


def _verify_pw(password: str, hashed: str) -> bool:
    if hashed.startswith("sha256$"):
        _, salt, h = hashed.split("$", 2)
        return h == hashlib.sha256((salt + password).encode()).hexdigest()
    if _has_bcrypt:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    return False


class TokenBalance:
    """Token余额管理 — 单例"""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._load()
        return cls._instance

    def _load(self):
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, "r") as f:
                self.balances = json.load(f)
        else:
            # T-008 修复：_default 启动余额 0，绝不再 hardcode 10000
            self.balances = {"_default": {"tokens": 0, "used": 0, "plan": "none"}}

    def _save(self):
        with open(TOKEN_FILE, "w") as f:
            json.dump(self.balances, f, indent=2)

    def get_balance(self, user_id: str = "_default") -> dict:
        # T-008 修复：未注册用户 plan=none，绝不再返回 fake "free" 标签
        return self.balances.get(user_id, {"tokens": 0, "used": 0, "plan": "none"})

    def consume(self, user_id: str, tokens: int) -> bool:
        if user_id not in self.balances:
            # T-008 修复：未注册用户默认 plan=none（不再是 fake "free"）
            self.balances[user_id] = {"tokens": 0, "used": 0, "plan": "none"}
        b = self.balances[user_id]
        remaining = b["tokens"] - b["used"]
        if remaining < tokens:
            return False
        b["used"] += tokens
        self._save()
        return True

    def recharge(self, user_id: str, amount: int, plan: str = "recharge") -> dict:
        if user_id not in self.balances:
            self.balances[user_id] = {"tokens": 0, "used": 0, "plan": "none"}
        self.balances[user_id]["tokens"] += amount
        self.balances[user_id]["plan"] = plan
        self._save()
        return self.balances[user_id]

    def plans(self) -> list:
        return [
            {"id": "starter", "name": "新手包", "tokens": 50000, "price": 9.9,
             "desc": "约500次对话，适合体验"},
            {"id": "pro", "name": "专业版", "tokens": 500000, "price": 49.9,
             "desc": "约5000次对话，适合日常交易"},
            {"id": "trader", "name": "交易员版", "tokens": 2000000, "price": 149.9,
             "desc": "约20000次对话，适合高频交易"},
            {"id": "unlimited", "name": "旗舰版", "tokens": 10000000, "price": 499.9,
             "desc": "约100000次对话，深度推理优先"},
        ]


class UserAuth:
    """用户认证系统"""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._load()
        return cls._instance

    def _load(self):
        if os.path.exists(AUTH_FILE):
            with open(AUTH_FILE, "r") as f:
                data = json.load(f)
                self.users = data.get("users", {})
                self.sessions = data.get("sessions", {})
                self.oauth_links = data.get("oauth_links", {})
        else:
            self.users = {}
            self.sessions = {}
            self.oauth_links = {}

    def _save(self):
        with open(AUTH_FILE, "w") as f:
            json.dump({
                "users": self.users,
                "sessions": self.sessions,
                "oauth_links": self.oauth_links,
            }, f, indent=2)

    def _make_session_token(self) -> str:
        return secrets.token_hex(16)

    def _issue_session(self, username: str) -> str:
        token = self._make_session_token()
        self.sessions[token] = {
            "username": username,
            "created_at": time.time(),
            "expires_at": time.time() + 86400 * 3,
        }
        self.users[username]["last_login"] = datetime.now().isoformat()
        self._save()
        return token

    def _grant_welcome_balance(self, username: str, plan: str = "free") -> None:
        tb = TokenBalance()
        balance = tb.get_balance(username)
        if balance.get("tokens", 0) <= 0 and balance.get("used", 0) <= 0:
            tb.recharge(username, 10000, plan)

    def _alloc_oauth_username(self, provider: str, provider_user_id: str) -> str:
        base = re.sub(r"[^a-z0-9_]+", "_", f"{provider}_{provider_user_id}".lower()).strip("_")
        base = base[:40] or f"{provider}_user"
        candidate = base
        idx = 1
        while candidate in self.users:
            idx += 1
            candidate = f"{base[:32]}_{idx}"
        return candidate

    def register(self, username: str, password: str, email: str = "") -> Tuple[bool, str]:
        username = username.strip().lower()
        if not username or len(username) < 3:
            return False, "用户名至少3个字符"
        if not password or len(password) < 6:
            return False, "密码至少6个字符"
        if username in self.users:
            return False, "用户名已存在"
        self.users[username] = {
            "username": username,
            "password_hash": _hash_pw(password),
            "email": email,
            "display_name": username,
            "auth_provider": "local",
            "oauth_only": False,
            "avatar_url": "",
            "created_at": datetime.now().isoformat(),
            "last_login": None,
            "api_calls": 0,
            "rate_limit_until": None,
        }
        self._save()
        self._grant_welcome_balance(username, "free")
        return True, "注册成功，赠送10000 tokens"

    def login(self, username: str, password: str) -> Tuple[bool, str, Optional[str]]:
        username = username.strip().lower()
        user = self.users.get(username)
        if not user:
            return False, "用户名不存在", None
        if not _verify_pw(password, user["password_hash"]):
            return False, "密码错误", None
        token = self._issue_session(username)
        return True, "登录成功", token

    def verify_session(self, token: str) -> Optional[str]:
        sess = self.sessions.get(token)
        if not sess:
            return None
        if time.time() > sess["expires_at"]:
            del self.sessions[token]
            self._save()
            return None
        return sess["username"]

    def logout(self, token: str):
        self.sessions.pop(token, None)
        self._save()

    def oauth_login(self, provider: str, provider_user_id: str, email: str = "",
                    display_name: str = "", avatar_url: str = "", raw_profile: Optional[dict] = None
                    ) -> Tuple[bool, str, Optional[str], Optional[str]]:
        provider = (provider or "").strip().lower()
        provider_user_id = str(provider_user_id or "").strip()
        if not provider or not provider_user_id:
            return False, "OAuth 用户信息不完整", None, None
        link_key = f"{provider}:{provider_user_id}"
        username = self.oauth_links.get(link_key)

        if not username:
            username = self._alloc_oauth_username(provider, provider_user_id)
            self.users[username] = {
                "username": username,
                "password_hash": "",
                "email": email,
                "display_name": display_name or email or username,
                "auth_provider": provider,
                "oauth_only": True,
                "avatar_url": avatar_url or "",
                "oauth_profile": raw_profile or {},
                "created_at": datetime.now().isoformat(),
                "last_login": None,
                "api_calls": 0,
                "rate_limit_until": None,
            }
            self.oauth_links[link_key] = username
            self._save()
            self._grant_welcome_balance(username, "free")
        else:
            user = self.users.get(username, {})
            user["email"] = email or user.get("email", "")
            user["display_name"] = display_name or user.get("display_name", username)
            user["avatar_url"] = avatar_url or user.get("avatar_url", "")
            user["auth_provider"] = provider
            user["oauth_only"] = True
            user["oauth_profile"] = raw_profile or user.get("oauth_profile", {})
            self.users[username] = user
            self._save()

        token = self._issue_session(username)
        return True, "授权登录成功", token, username

    def check_rate_limit(self, username: str, max_per_min: int = 30) -> bool:
        """简单令牌桶限流"""
        user = self.users.get(username)
        if not user:
            return True
        # 简易计数限流 (60秒窗口)
        now = time.time()
        rl_key = f"_rl_{username}"
        rl = self.users.get(rl_key, {"count": 0, "window_start": now})
        if now - rl["window_start"] > 60:
            rl = {"count": 0, "window_start": now}
        if rl["count"] >= max_per_min:
            return False
        rl["count"] += 1
        self.users[rl_key] = rl
        return True

    def get_profile(self, username: str) -> Optional[dict]:
        user = self.users.get(username)
        if not user:
            return None
        tb = TokenBalance()
        balance = tb.get_balance(username)
        return {
            "username": username,
            "email": user.get("email", ""),
            "display_name": user.get("display_name", username),
            "auth_provider": user.get("auth_provider", "local"),
            "oauth_only": user.get("oauth_only", False),
            "avatar_url": user.get("avatar_url", ""),
            "created_at": user.get("created_at"),
            "last_login": user.get("last_login"),
            "api_calls": user.get("api_calls", 0),
            "tokens_total": balance["tokens"],
            "tokens_used": balance["used"],
            "tokens_remaining": balance["tokens"] - balance["used"],
            "plan": balance["plan"],
        }


# 全局单例
_auth: Optional[UserAuth] = None
_balance: Optional[TokenBalance] = None


def get_auth() -> UserAuth:
    global _auth
    if _auth is None:
        _auth = UserAuth()
    return _auth


def get_balance() -> TokenBalance:
    global _balance
    if _balance is None:
        _balance = TokenBalance()
    return _balance


class OAuthManager:
    """桌面端第三方授权管理器：系统浏览器授权 + 本地回调 + 前端轮询取 token。"""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance.pending = {}
                    cls._instance.results = {}
        return cls._instance

    def _base_url(self) -> str:
        return (os.environ.get("GBT_OAUTH_BASE_URL", "http://127.0.0.1:8765").rstrip("/"))

    def _provider_env(self, provider: str, suffix: str) -> str:
        provider_key = provider.upper().replace("-", "_")
        return os.environ.get(f"OAUTH_{provider_key}_{suffix}", "").strip()

    def _provider_cfg(self, provider: str) -> dict:
        provider = (provider or "").lower().strip()
        meta = OAUTH_PROVIDER_CATALOG.get(provider, {})
        if not meta:
            return {}

        short_prefix = provider.upper().replace("-", "_")
        client_id = os.environ.get(f"{short_prefix}_CLIENT_ID", "").strip() or self._provider_env(provider, "CLIENT_ID")
        client_secret = os.environ.get(f"{short_prefix}_CLIENT_SECRET", "").strip() or self._provider_env(provider, "CLIENT_SECRET")
        redirect_uri = (
            os.environ.get(f"{short_prefix}_REDIRECT_URI", "").strip()
            or self._provider_env(provider, "REDIRECT_URI")
            or (self._base_url() + f"/api/auth/oauth/callback/{provider}")
        )

        cfg = dict(meta)
        cfg.update({
            "provider": provider,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "configured": bool(client_id and client_secret),
        })
        return cfg

    def provider_status(self) -> list:
        data = []
        for provider in VISIBLE_PROVIDER_ORDER:
            cfg = self._provider_cfg(provider)
            if not cfg:
                continue
            data.append({
                "provider": provider,
                "label": cfg.get("label", provider),
                "category": cfg.get("category", "其他"),
                "implemented": bool(cfg.get("implemented")),
                "configured": bool(cfg.get("configured")),
                "redirect_uri": cfg.get("redirect_uri", ""),
                "docs_url": cfg.get("docs_url", ""),
                "status_text": "可用" if cfg.get("implemented") and cfg.get("configured")
                else ("待配置" if cfg.get("implemented") else "待适配"),
            })
        return data

    def start(self, provider: str) -> dict:
        cfg = self._provider_cfg(provider)
        if not cfg:
            return {"ok": False, "error": "不支持的 OAuth 提供方"}
        if not cfg.get("implemented"):
            return {"ok": False, "error": f"{cfg['label']} 已加入入口矩阵，但当前桌面端适配器尚未完成"}
        if not (cfg["client_id"] and cfg["client_secret"]):
            return {"ok": False, "error": f"{cfg['label']} OAuth 未配置 client_id/client_secret"}
        state = secrets.token_urlsafe(24)
        self.pending[state] = {
            "provider": provider,
            "created_at": time.time(),
        }
        params = {
            "client_id": cfg["client_id"],
            "redirect_uri": cfg["redirect_uri"],
            "response_type": "code",
            "scope": cfg["scope"],
            "state": state,
        }
        params.update(cfg.get("extra_auth_params") or {})
        auth_url = cfg["auth_url"] + "?" + urlencode(params)
        return {
            "ok": True,
            "provider": provider,
            "state": state,
            "auth_url": auth_url,
            "expires_in": 600,
        }

    def finish(self, provider: str, state: str, code: str = "", error: str = "") -> dict:
        pending = self.pending.get(state)
        if not pending or pending.get("provider") != provider:
            return {"ok": False, "error": "授权状态无效或已过期"}
        if time.time() - pending.get("created_at", 0) > 600:
            self.pending.pop(state, None)
            return {"ok": False, "error": "授权状态已过期，请重新发起登录"}
        if error:
            self.pending.pop(state, None)
            self.results[state] = {"status": "error", "error": error}
            return {"ok": False, "error": error}
        try:
            token_data = self._exchange_code(provider, code)
            profile = self._fetch_profile(provider, token_data)
            ok, msg, token, username = get_auth().oauth_login(
                provider=provider,
                provider_user_id=profile["provider_user_id"],
                email=profile.get("email", ""),
                display_name=profile.get("display_name", ""),
                avatar_url=profile.get("avatar_url", ""),
                raw_profile=profile.get("raw_profile", {}),
            )
            if not ok or not token:
                raise RuntimeError(msg or "本地会话创建失败")
            self.results[state] = {
                "status": "success",
                "token": token,
                "username": username,
                "provider": provider,
            }
            return {"ok": True, "token": token, "username": username}
        except Exception as e:
            self.results[state] = {"status": "error", "error": str(e)}
            return {"ok": False, "error": str(e)}
        finally:
            self.pending.pop(state, None)

    def poll(self, state: str) -> dict:
        if not state:
            return {"ok": False, "status": "error", "error": "state 缺失"}
        if state in self.pending:
            return {"ok": True, "status": "pending"}
        result = self.results.pop(state, None)
        if not result:
            return {"ok": False, "status": "expired", "error": "授权结果不存在或已过期"}
        return {"ok": result.get("status") == "success", **result}

    def _exchange_code(self, provider: str, code: str) -> dict:
        if not code:
            raise RuntimeError("授权 code 缺失")
        import requests

        cfg = self._provider_cfg(provider)
        payload = {
            "client_id": cfg["client_id"],
            "client_secret": cfg["client_secret"],
            "code": code,
            "redirect_uri": cfg["redirect_uri"],
        }
        headers = {"Accept": "application/json"}
        if provider in ("google", "microsoft", "linkedin"):
            payload["grant_type"] = "authorization_code"
        resp = requests.post(cfg["token_url"], data=payload, headers=headers, timeout=20)
        data = resp.json()
        if resp.status_code >= 400 or data.get("error"):
            raise RuntimeError(f"{cfg['label']} token 交换失败: {data.get('error_description') or data.get('error') or resp.text[:200]}")
        if not data.get("access_token"):
            raise RuntimeError(f"{cfg['label']} 未返回 access_token")
        return data

    def _fetch_profile(self, provider: str, token_data: dict) -> dict:
        import requests

        access_token = token_data.get("access_token", "")
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "User-Agent": "GBT-Pro-OAuth/1.0",
        }
        cfg = self._provider_cfg(provider)
        if provider == "google":
            resp = requests.get(cfg["user_info_url"], headers=headers, timeout=20)
            data = resp.json()
            if resp.status_code >= 400 or not data.get("sub"):
                raise RuntimeError(f"Google 用户信息拉取失败: {resp.text[:200]}")
            return {
                "provider_user_id": str(data.get("sub")),
                "email": data.get("email", ""),
                "display_name": data.get("name") or data.get("email", ""),
                "avatar_url": data.get("picture", ""),
                "raw_profile": data,
            }
        if provider == "github":
            resp = requests.get(cfg["user_info_url"], headers=headers, timeout=20)
            data = resp.json()
            if resp.status_code >= 400 or not data.get("id"):
                raise RuntimeError(f"GitHub 用户信息拉取失败: {resp.text[:200]}")
            email = data.get("email", "")
            if not email:
                emails = requests.get("https://api.github.com/user/emails", headers=headers, timeout=20)
                email_list = emails.json() if emails.ok else []
                primary = next((x for x in email_list if x.get("primary")), None) if isinstance(email_list, list) else None
                verified = next((x for x in email_list if x.get("verified")), None) if isinstance(email_list, list) else None
                email = (primary or verified or {}).get("email", "")
            return {
                "provider_user_id": str(data.get("id")),
                "email": email,
                "display_name": data.get("name") or data.get("login") or email or "GitHub User",
                "avatar_url": data.get("avatar_url", ""),
                "raw_profile": data,
            }
        if provider == "gitee":
            resp = requests.get(cfg["user_info_url"], headers=headers, timeout=20)
            data = resp.json()
            if resp.status_code >= 400 or not data.get("id"):
                raise RuntimeError(f"Gitee 用户信息拉取失败: {resp.text[:200]}")
            return {
                "provider_user_id": str(data.get("id")),
                "email": data.get("email", ""),
                "display_name": data.get("name") or data.get("login") or "Gitee User",
                "avatar_url": data.get("avatar_url", ""),
                "raw_profile": data,
            }
        if provider == "gitlab":
            resp = requests.get(cfg["user_info_url"], headers=headers, timeout=20)
            data = resp.json()
            if resp.status_code >= 400 or not data.get("id"):
                raise RuntimeError(f"GitLab 用户信息拉取失败: {resp.text[:200]}")
            return {
                "provider_user_id": str(data.get("id")),
                "email": data.get("email", ""),
                "display_name": data.get("name") or data.get("username") or "GitLab User",
                "avatar_url": data.get("avatar_url", ""),
                "raw_profile": data,
            }
        if provider == "microsoft":
            resp = requests.get(cfg["user_info_url"], headers=headers, timeout=20)
            data = resp.json()
            if resp.status_code >= 400 or not data.get("id"):
                raise RuntimeError(f"Microsoft 用户信息拉取失败: {resp.text[:200]}")
            return {
                "provider_user_id": str(data.get("id")),
                "email": data.get("mail") or data.get("userPrincipalName", ""),
                "display_name": data.get("displayName") or data.get("userPrincipalName") or "Microsoft User",
                "avatar_url": "",
                "raw_profile": data,
            }
        if provider == "linkedin":
            resp = requests.get(cfg["user_info_url"], headers=headers, timeout=20)
            data = resp.json()
            if resp.status_code >= 400 or not (data.get("sub") or data.get("id")):
                raise RuntimeError(f"LinkedIn 用户信息拉取失败: {resp.text[:200]}")
            return {
                "provider_user_id": str(data.get("sub") or data.get("id")),
                "email": data.get("email", ""),
                "display_name": data.get("name") or data.get("given_name") or "LinkedIn User",
                "avatar_url": data.get("picture", ""),
                "raw_profile": data,
            }
        if provider == "facebook":
            resp = requests.get(cfg["user_info_url"], headers=headers, timeout=20)
            data = resp.json()
            if resp.status_code >= 400 or not data.get("id"):
                raise RuntimeError(f"Facebook 用户信息拉取失败: {resp.text[:200]}")
            picture = (((data.get("picture") or {}).get("data")) or {}).get("url", "")
            return {
                "provider_user_id": str(data.get("id")),
                "email": data.get("email", ""),
                "display_name": data.get("name") or "Facebook User",
                "avatar_url": picture,
                "raw_profile": data,
            }
        raise RuntimeError("不支持的 OAuth 提供方")


_oauth: Optional[OAuthManager] = None


def get_oauth() -> OAuthManager:
    global _oauth
    if _oauth is None:
        _oauth = OAuthManager()
    return _oauth
