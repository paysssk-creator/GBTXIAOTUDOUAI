from playwright.sync_api import sync_playwright
import json
import sys


URL = "http://127.0.0.1:8765/dashboard"


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1200})
        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2500)

        tabs = page.locator(".n-item").all_inner_texts()
        page.click(".n-item[data-tab='desktop']")
        page.wait_for_timeout(1200)
        desktop_buttons = page.locator("#desk-grid .btn-cap").all_inner_texts()

        result = {
            "tabs": tabs,
            "has_hacker_tab": any("黑客" in x for x in tabs),
            "has_recharge_tab": any("充值" in x or "付费" in x for x in tabs),
            "desktop_button_count": len(desktop_buttons),
            "desktop_buttons": desktop_buttons,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        browser.close()


if __name__ == "__main__":
    main()
