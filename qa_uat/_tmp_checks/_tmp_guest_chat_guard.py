from playwright.sync_api import sync_playwright
import json
import sys


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

    result = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2500)

        page.click(".n-item[data-tab='chat']")
        page.wait_for_timeout(1200)
        page.fill("#chat-input", "访客模式聊天门禁复检")
        page.click("button[onclick='sendChat()']")
        page.wait_for_timeout(2200)

        result["active_tab"] = page.locator(".n-item.active").first.get_attribute("data-tab")
        result["chat_last"] = txt(page, "#chat-messages .chat-msg:last-child .msg-text")
        result["auth_tip"] = txt(page, "#auth-tip")
        result["chat_auth_tip"] = txt(page, "#chat-auth-tip")
        result["auth_state"] = txt(page, "#auth-state")
        result["auth_remaining"] = txt(page, "#auth-remaining")
        result["toast"] = txt(page, "#toast")
        result["token_balance"] = page.evaluate(
            """() => fetch('/api/token/balance')
            .then(r => r.json())
            .catch(e => ({ok:false,error:String(e)}))"""
        )

        print(json.dumps(result, ensure_ascii=False, indent=2))
        browser.close()


if __name__ == "__main__":
    main()
