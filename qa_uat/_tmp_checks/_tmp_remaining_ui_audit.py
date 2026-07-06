from playwright.sync_api import sync_playwright
import json
import sys
import time


URL = "http://127.0.0.1:8765/dashboard"


def text_or_none(page, selector):
    loc = page.locator(selector)
    if not loc.count():
        return None
    try:
        return loc.first.inner_text().strip()
    except Exception:
        return None


def count(page, selector):
    try:
        return page.locator(selector).count()
    except Exception:
        return 0


def last_toast(page):
    try:
        txt = page.locator("#toast").inner_text().strip()
        return txt or None
    except Exception:
        return None


def wait_idle(page, ms=1200):
    page.wait_for_timeout(ms)


def click_tab(page, tab):
    page.click(f".n-item[data-tab='{tab}']")
    wait_idle(page, 1400)


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    username = f"uiaudit{int(time.time())}"
    password = "Pass0630!"
    email = f"{username}@example.com"
    api_events = []
    console_errors = []
    page_errors = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        def on_response(resp):
            url = resp.url
            interesting = [
                "/api/auth/register",
                "/api/auth/login",
                "/api/auth/profile",
                "/api/token/balance",
                "/api/chat",
                "/api/market",
                "/api/market/recap",
                "/api/pilot/status",
                "/api/hacker/capabilities",
                "/api/hacker/exec",
                "/api/dashboard",
                "/api/config/llm",
                "/api/payment/status",
                "/api/payment/link",
                "/api/token/recharge",
            ]
            if any(key in url for key in interesting):
                body = None
                try:
                    body = resp.text()
                except Exception as exc:
                    body = f"<read-failed:{exc}>"
                api_events.append({
                    "url": url,
                    "status": resp.status,
                    "body": body[:400],
                })

        page.on("response", on_response)
        page.on("pageerror", lambda err: page_errors.append(str(err)))
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        wait_idle(page, 3500)

        click_tab(page, "auth")
        page.fill("#register-username", username)
        page.fill("#register-email", email)
        page.fill("#register-password", password)
        page.click("button[onclick='registerUser()']")
        wait_idle(page, 2200)

        page.fill("#login-username", username)
        page.fill("#login-password", password)
        page.click("button[onclick='loginUser()']")
        wait_idle(page, 4500)

        click_tab(page, "chat")
        page.fill("#chat-input", "请确认剩余面板巡检链路已接通。")
        page.click("button[onclick='sendChat()']")
        wait_idle(page, 7000)

        click_tab(page, "trade")
        page.click("#recap-btn")
        wait_idle(page, 12000)

        click_tab(page, "pilot")
        wait_idle(page, 1800)

        click_tab(page, "llm")
        wait_idle(page, 1600)
        llm_statuses = page.locator("#llm-list span").all_inner_texts() if count(page, "#llm-list span") else []

        click_tab(page, "account")
        account_snapshot = {
            "cash": text_or_none(page, "#a-cash"),
            "equity": text_or_none(page, "#a-equity"),
            "pnl": text_or_none(page, "#a-pnl"),
            "tokens": text_or_none(page, "#a-tokens"),
            "user": text_or_none(page, "#a-user"),
            "auth": text_or_none(page, "#a-auth"),
        }

        click_tab(page, "hacker")
        hacker_snapshot = {
            "count_label": text_or_none(page, "#hack-cnt"),
            "button_count": count(page, "#hack-grid .btn-cap"),
            "first_buttons": page.locator("#hack-grid .btn-cap").all_inner_texts()[:8] if count(page, "#hack-grid .btn-cap") else [],
        }

        click_tab(page, "desktop")
        desktop_snapshot = {
            "button_count": count(page, "#desk-grid .btn-cap"),
            "buttons": page.locator("#desk-grid .btn-cap").all_inner_texts(),
        }
        if page.locator("#desk-grid .btn-cap").filter(has_text="进程列表").count():
            page.locator("#desk-grid .btn-cap").filter(has_text="进程列表").first.click()
            wait_idle(page, 2200)
        desktop_snapshot["log"] = text_or_none(page, "#desk-log")
        desktop_snapshot["toast"] = last_toast(page)

        click_tab(page, "mcp")
        mcp_snapshot = {
            "count": count(page, "#mcp-grid .btn-cap"),
            "items": page.locator("#mcp-grid .btn-cap").all_inner_texts() if count(page, "#mcp-grid .btn-cap") else [],
            "count_label": text_or_none(page, "#mcp-cnt"),
        }

        click_tab(page, "connect")
        connect_snapshot = {
            "provider_count": count(page, "#cfg-provider option"),
            "providers": page.locator("#cfg-provider option").all_inner_texts(),
            "model_placeholder": page.locator("#cfg-model").get_attribute("placeholder"),
        }

        click_tab(page, "recharge")
        wait_idle(page, 2500)
        recharge_snapshot = {
            "target": text_or_none(page, "#recharge-target"),
            "channel": text_or_none(page, "#recharge-channel"),
            "package_count": count(page, "#recharge-packages > div"),
            "packages_preview": page.locator("#recharge-packages > div").all_inner_texts()[:6] if count(page, "#recharge-packages > div") else [],
            "currency_note": text_or_none(page, "#recharge-currency-note"),
        }

        page.fill("#recharge-first", "UI")
        page.fill("#recharge-last", "Audit")
        page.fill("#recharge-email", email)
        page.fill("#recharge-amount", "10")
        page.select_option("#recharge-currency", "USD")
        page.click("#recharge-btn")
        wait_idle(page, 4500)
        recharge_snapshot["payment_modal_open"] = page.locator("text=Futurapay 安全付款").count() > 0
        recharge_snapshot["toast_after_payment"] = last_toast(page)
        if recharge_snapshot["payment_modal_open"]:
            try:
                page.click("button[onclick='closePaymentIframe()']")
                wait_idle(page, 1200)
            except Exception:
                pass

        page.click("button[onclick='doRechargeCode()']")
        wait_idle(page, 800)
        page.fill("#recharge-code", "INVALID123")
        page.click("button[onclick='doRecharge()']")
        wait_idle(page, 1800)
        recharge_snapshot["toast_after_code"] = last_toast(page)

        click_tab(page, "auth")
        auth_snapshot = {
            "state": text_or_none(page, "#auth-state"),
            "user": text_or_none(page, "#auth-user"),
            "email": text_or_none(page, "#auth-email"),
            "remaining": text_or_none(page, "#auth-remaining"),
            "chip": text_or_none(page, "#auth-chip"),
            "stored_token": page.evaluate(
                "() => { try { return localStorage.getItem('gbt_auth_token'); } catch (e) { return null; } }"
            ),
        }

        result = {
            "username": username,
            "auth": auth_snapshot,
            "chat_last": text_or_none(page, "#chat-messages .chat-msg .msg-text:last-child"),
            "recap_headline": text_or_none(page, "#recap-headline"),
            "recap_meta": text_or_none(page, "#recap-meta"),
            "pilot_status": text_or_none(page, "#pilot-st"),
            "pilot_log": text_or_none(page, "#p-log"),
            "llm": {
                "statuses": llm_statuses,
                "list_count": count(page, "#llm-list > div"),
            },
            "account": account_snapshot,
            "hacker": hacker_snapshot,
            "desktop": desktop_snapshot,
            "mcp": mcp_snapshot,
            "connect": connect_snapshot,
            "recharge": recharge_snapshot,
            "console_errors": console_errors,
            "page_errors": page_errors,
            "api_events": api_events,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        browser.close()


if __name__ == "__main__":
    main()
