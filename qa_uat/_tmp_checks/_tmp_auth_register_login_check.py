from playwright.sync_api import sync_playwright
import json
import time


URL = "http://127.0.0.1:8765/dashboard"


def main():
    username = f"uiuser{int(time.time())}"
    password = "Pass0630!"
    email = f"{username}@example.com"
    events = []
    page_errors = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        def on_response(resp):
            url = resp.url
            if any(key in url for key in ["/api/auth/register", "/api/auth/login", "/api/auth/profile", "/api/token/balance"]):
                try:
                    body = resp.text()
                except Exception as e:
                    body = f"<read-failed:{e}>"
                events.append({"url": url, "status": resp.status, "body": body})

        page.on("response", on_response)
        page.on("pageerror", lambda err: page_errors.append(str(err)))

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
        page.wait_for_timeout(5000)

        result = {
            "username": username,
            "events": events,
            "page_errors": page_errors,
            "auth_state": page.locator("#auth-state").inner_text() if page.locator("#auth-state").count() else None,
            "auth_user": page.locator("#auth-user").inner_text() if page.locator("#auth-user").count() else None,
            "auth_chip": page.locator("#auth-chip").inner_text() if page.locator("#auth-chip").count() else None,
            "stored_token": page.evaluate("() => { try { return localStorage.getItem('gbt_auth_token'); } catch (e) { return null; } }"),
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        browser.close()


if __name__ == "__main__":
    main()
