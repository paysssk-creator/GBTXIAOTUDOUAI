from playwright.sync_api import sync_playwright
import json
import requests
import sys
import time


URL = "http://127.0.0.1:8765/dashboard"


def txt(page, selector):
    try:
        loc = page.locator(selector)
        if not loc.count():
            return None
        return loc.first.inner_text().strip()
    except Exception:
        return None


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    username = f"capui{int(time.time())}"
    password = "Pass0630!"
    email = f"{username}@example.com"
    requests.post(
        "http://127.0.0.1:8765/api/auth/register",
        json={"username": username, "password": password, "email": email},
        timeout=20,
    )
    login = requests.post(
        "http://127.0.0.1:8765/api/auth/login",
        json={"username": username, "password": password},
        timeout=20,
    )
    login.raise_for_status()
    token = login.json()["token"]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1200})
        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2500)
        page.evaluate("(tk) => { localStorage.setItem('gbt_auth_token', tk); }", token)
        page.reload(wait_until="domcontentloaded")
        page.wait_for_timeout(2500)

        page.click(".n-item[data-tab='chat']")
        page.wait_for_timeout(1200)
        page.fill("#chat-input", "那你现在操控电脑操作的达到什么程度了")
        page.click("button[onclick='sendChat()']")

        last = ""
        for _ in range(25):
            page.wait_for_timeout(1000)
            last = txt(page, "#chat-messages .chat-msg:last-child .msg-text") or ""
            if last and "思考中" not in last:
                break

        result = {
            "chat_last": last,
            "auth_state": txt(page, "#auth-state"),
            "chat_auth_tip": txt(page, "#chat-auth-tip"),
            "toast": txt(page, "#toast"),
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        browser.close()


if __name__ == "__main__":
    main()
