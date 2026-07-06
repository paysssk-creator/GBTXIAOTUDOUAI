from playwright.sync_api import sync_playwright
import json
import time


URL = "http://127.0.0.1:8765/dashboard"


def main():
    events = []
    page_errors = []
    console_errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        def on_response(resp):
            url = resp.url
            if any(key in url for key in ["/api/auth/login", "/api/auth/profile", "/api/token/balance"]):
                body = None
                try:
                    body = resp.text()
                except Exception as e:
                    body = f"<read-failed:{e}>"
                events.append({"url": url, "status": resp.status, "body": body})

        def on_page_error(err):
            page_errors.append(str(err))

        def on_console(msg):
            if msg.type == "error":
                console_errors.append(msg.text)

        page.on("response", on_response)
        page.on("pageerror", on_page_error)
        page.on("console", on_console)
        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(4000)
        page.evaluate(
            """
            () => {
              try { localStorage.removeItem('gbt_auth_token'); } catch (e) {}
              if (typeof authState !== 'undefined') {
                authState.token = '';
                authState.profile = null;
                authState.balance = null;
                if (typeof updateAuthUI === 'function') updateAuthUI();
              }
            }
            """
        )
        page.click(".n-item[data-tab='auth']")
        page.fill("#login-username", "gbtuser0630b")
        page.fill("#login-password", "Pass0630!")
        page.click("button[onclick='loginUser()']")
        page.wait_for_timeout(5000)

        result = {
            "events": events,
            "page_errors": page_errors,
            "console_errors": console_errors,
            "auth_state": page.locator("#auth-state").inner_text() if page.locator("#auth-state").count() else None,
            "auth_user": page.locator("#auth-user").inner_text() if page.locator("#auth-user").count() else None,
            "auth_chip": page.locator("#auth-chip").inner_text() if page.locator("#auth-chip").count() else None,
            "stored_token": page.evaluate("() => { try { return localStorage.getItem('gbt_auth_token'); } catch (e) { return null; } }"),
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        browser.close()


if __name__ == "__main__":
    main()
