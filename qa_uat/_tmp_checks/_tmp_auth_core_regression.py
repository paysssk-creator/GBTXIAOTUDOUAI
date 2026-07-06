from playwright.sync_api import sync_playwright
import json
import time


URL = "http://127.0.0.1:8765/dashboard"


def main():
    username = f"uiuser{int(time.time())}"
    password = "Pass0630!"
    email = f"{username}@example.com"
    events = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        def on_response(resp):
            url = resp.url
            if any(key in url for key in [
                "/api/auth/register",
                "/api/auth/login",
                "/api/auth/profile",
                "/api/token/balance",
                "/api/chat",
                "/api/market/recap",
                "/api/pilot/status",
            ]):
                try:
                    body = resp.text()
                except Exception as e:
                    body = f"<read-failed:{e}>"
                events.append({"url": url, "status": resp.status, "body": body[:500]})

        page.on("response", on_response)
        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(4000)

        page.click(".n-item[data-tab='auth']")
        page.fill("#register-username", username)
        page.fill("#register-email", email)
        page.fill("#register-password", password)
        page.click("button[onclick='registerUser()']")
        page.wait_for_timeout(2500)

        page.fill("#login-username", username)
        page.fill("#login-password", password)
        page.click("button[onclick='loginUser()']")
        page.wait_for_timeout(4000)

        page.click(".n-item[data-tab='chat']")
        page.fill("#chat-input", "请用一句话确认 authfix 后聊天可用。")
        page.click("button[onclick='sendChat()']")
        page.wait_for_timeout(7000)

        page.click(".n-item[data-tab='trade']")
        page.click("#recap-btn")
        page.wait_for_timeout(12000)

        page.click(".n-item[data-tab='pilot']")
        page.wait_for_timeout(2500)

        result = {
            "username": username,
            "events": events,
            "auth_state": page.locator("#auth-state").inner_text() if page.locator("#auth-state").count() else None,
            "auth_chip": page.locator("#auth-chip").inner_text() if page.locator("#auth-chip").count() else None,
            "chat_last": page.locator("#chat-messages .chat-msg .msg-text").last.inner_text() if page.locator("#chat-messages .chat-msg .msg-text").count() else None,
            "recap_headline": page.locator("#recap-headline").inner_text() if page.locator("#recap-headline").count() else None,
            "recap_report": page.locator("#recap-report").inner_text()[:300] if page.locator("#recap-report").count() else None,
            "pilot_status": page.locator("#pilot-st").inner_text() if page.locator("#pilot-st").count() else None,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        browser.close()


if __name__ == "__main__":
    main()
