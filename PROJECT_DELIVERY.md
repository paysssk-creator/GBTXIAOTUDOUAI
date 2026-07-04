# GBT Pro 交付收口

## 目标

只保留一条可交付结论：

1. 用户能启动
2. 用户能登录
3. 用户能使用核心功能
4. 用户付款后商家能收到款

## 唯一正式交付线

- 正式版本：`v1.1.17`
- 正式启动入口：`release/launch_current_runtime.bat`
- 正式 onefile 交付包：`release/GBT_Pro_v1.1.17.exe`
- 正式发布清单：`release/manifest.json`
- 正式 UAT 证据目录：`qa_uat/`

## 目录分层

### 1. 正式交付层

- `release/`
- `qa_uat/`
- `build_exe.py`
- `install.bat`
- `deploy/`

### 2. 开发实现层

- `gbt/`
- `desktop/`
- `tests/`

### 3. 历史归档层

- `_archive/legacy_runtime/`

### 4. 运行时脏数据层

以下文件不属于源码，不应作为正式代码交付内容：

- `auth_users.json`
- `token_balance.json`
- `autopilot.json`
- `audit_trail.jsonl`
- `decision_log.jsonl`
- `.dbg/`

## 上线判定标准

只有同时满足以下条件，才允许对用户发包：

1. `release/GBT_Pro_v1.1.17.exe` 可在干净目录独立启动
2. `/api/status` 返回 `ok=true`
3. Google 官方授权登录可用
4. A 股行情页可正常出数
5. 充值激活页可生成付款链接
6. 支付链路可生成订单和二维码
7. 商家回款配置指向当前有效 Futurapay 凭据

## 当前已确认

- 正式运行线可用
- onefile 交付包已生成
- Google 官方授权入口已打通
- 支付链接、订单详情、二维码链路已跑通

## 发布边界

- 面向普通用户上线：优先使用 `deploy/` 服务端发布线，由你控制 `.env.prod` 中的 Google / Futurapay 密钥
- 桌面 onefile：只适合本机、受控环境或内部演示；未配本地 `.env` 时不应假定支付与 OAuth 可直接对外可用
- 冻结包默认只认 `cwd / exe 同级 / _MEIPASS` 的 `.env`，不再向父目录偷偷回退，避免把开发机配置误当成用户机能力

## 当前仍需继续盯住的用户机风险

- onefile 首次启动时间可能偏长
- 打包后 `bcrypt` 必须确保不再回退到 `sha256 fallback`
- 交付前仍需按干净目录/干净环境再做一次最终验收
