"""cloud.py — Notion/Slack/Gmail/Calendar connectors"""
import urllib.request, json, os

# ── Notion ──
def notion_search_pages(query):
    token = os.getenv("NOTION_TOKEN")
    if not token: return {"ok": False, "error": "NOTION_TOKEN not set"}
    try:
        req = urllib.request.Request("https://api.notion.com/v1/search", 
            data=json.dumps({"query": query}).encode(), headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"}, method="POST")
        with urllib.request.urlopen(req, timeout=10) as r: return {"ok": True, "results": json.loads(r.read()).get("results", [])[:10]}
    except Exception as e: return {"ok": False, "error": str(e)}

def notion_create_page(title, parent_id=None):
    token = os.getenv("NOTION_TOKEN")
    if not token: return {"ok": False, "error": "NOTION_TOKEN not set"}
    try:
        parent = {"page_id": parent_id} if parent_id else {"type": "workspace", "workspace": True}
        data = {"parent": parent, "properties": {"title": {"title": [{"text": {"content": title}}]}}}
        req = urllib.request.Request("https://api.notion.com/v1/pages", data=json.dumps(data).encode(),
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"}, method="POST")
        with urllib.request.urlopen(req, timeout=10) as r: return {"ok": True, "page": json.loads(r.read())}
    except Exception as e: return {"ok": False, "error": str(e)}

# ── Slack ──
def slack_send_message(channel, text):
    token = os.getenv("SLACK_BOT_TOKEN")
    if not token: return {"ok": False, "error": "SLACK_BOT_TOKEN not set"}
    try:
        req = urllib.request.Request("https://slack.com/api/chat.postMessage",
            data=json.dumps({"channel": channel, "text": text}).encode(),
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=10) as r: return {"ok": True, "result": json.loads(r.read())}
    except Exception as e: return {"ok": False, "error": str(e)}

# ── Gmail (via Gmail API) ──
def gmail_search(query, max_results=10):
    return {"ok": False, "error": "Gmail API requires OAuth2 setup — use GMAIL_CREDENTIALS env"}
def gmail_send(to, subject, body):
    return {"ok": False, "error": "Gmail API requires OAuth2 setup — use GMAIL_CREDENTIALS env"}

# ── Calendar ──
def calendar_list_events(max_results=10):
    return {"ok": False, "error": "Google Calendar requires OAuth2 setup — use GOOGLE_CREDENTIALS env"}
def calendar_create_event(summary, start_time, end_time):
    return {"ok": False, "error": "Google Calendar requires OAuth2 setup"}

def cloud_handle(service, action, **params):
    handlers = {
        "notion": {"search_pages": lambda: notion_search_pages(params.get("query","")), "create_page": lambda: notion_create_page(params.get("title",""), params.get("parent_id"))},
        "slack": {"send_message": lambda: slack_send_message(params.get("channel",""), params.get("text","")), "list_channels": lambda: {"ok": False, "error": "Use conversations.list API"}},
        "gmail": {"search_emails": lambda: gmail_search(params.get("query","")), "send_email": lambda: gmail_send(params.get("to",""), params.get("subject",""), params.get("body",""))},
        "calendar": {"list_events": lambda: calendar_list_events(), "create_event": lambda: calendar_create_event(params.get("summary",""), params.get("start",""), params.get("end",""))},
    }
    svc = handlers.get(service, {})
    h = svc.get(action)
    return h() if h else {"ok": False, "error": f"Unknown: {service}.{action}"}
