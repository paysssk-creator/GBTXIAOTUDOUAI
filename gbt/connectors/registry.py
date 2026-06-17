"""GBT Pro — Connector & Plugin Registry
Inspired by OpenHuman's Skills Runtime Engine + Integration layer.
Each connector is a self-contained module with register/status/disconnect.
"""
import os, sys, importlib, logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field

L = logging.getLogger("GBT.Connectors")

@dataclass
class ConnectorInfo:
    id: str
    name: str
    description: str
    icon: str  # Phosphor icon name
    category: str  # "code", "data", "communication", "device"
    status: str = "disconnected"  # connected | disconnected | error
    config_keys: List[str] = field(default_factory=list)  # required env vars
    tools: List[dict] = field(default_factory=list)

class ConnectorRegistry:
    """Global registry of all available connectors/plugins."""
    
    def __init__(self):
        self._connectors: Dict[str, ConnectorInfo] = {}
        self._instances: Dict[str, object] = {}
        self._register_builtins()
    
    def _register_builtins(self):
        """Register all built-in connectors."""
        # ── Code & Development ──
        self.add(ConnectorInfo(
            id="github", name="GitHub", description="Repositories, PRs, issues, CI/CD",
            icon="ph ph-github-logo", category="code",
            config_keys=["GITHUB_TOKEN"],
            tools=[{"name":"list_repos","desc":"List repositories"},{"name":"search_code","desc":"Search code"},{"name":"create_pr","desc":"Create pull request"}]
        ))
        self.add(ConnectorInfo(
            id="git", name="Local Git", description="Local repository management",
            icon="ph ph-git-branch", category="code",
            tools=[{"name":"git_status","desc":"Show working tree status"},{"name":"git_log","desc":"Show commit log"},{"name":"git_diff","desc":"Show changes"}]
        ))
        self.add(ConnectorInfo(
            id="filesystem", name="File System", description="Read, write, search files",
            icon="ph ph-folder-open", category="code",
            tools=[{"name":"read_file","desc":"Read file contents"},{"name":"write_file","desc":"Write/create file"},{"name":"list_dir","desc":"List directory"},{"name":"search_files","desc":"Search with glob"}]
        ))
        self.add(ConnectorInfo(
            id="terminal", name="Terminal", description="Execute shell commands",
            icon="ph ph-terminal-window", category="code",
            tools=[{"name":"exec","desc":"Execute command"},{"name":"shell","desc":"Interactive shell"}]
        ))
        self.add(ConnectorInfo(
            id="pypi", name="PyPI", description="Python package management",
            icon="ph ph-package", category="code",
            tools=[{"name":"install","desc":"Install package"},{"name":"uninstall","desc":"Remove package"},{"name":"search","desc":"Search packages"}]
        ))
        
        # ── Communication & Cloud ──
        self.add(ConnectorInfo(
            id="notion", name="Notion", description="Pages, databases, comments",
            icon="ph ph-note", category="communication",
            config_keys=["NOTION_TOKEN"],
            tools=[{"name":"search_pages","desc":"Search pages"},{"name":"create_page","desc":"Create page"},{"name":"query_db","desc":"Query database"}]
        ))
        self.add(ConnectorInfo(
            id="slack", name="Slack", description="Channels, messages, files",
            icon="ph ph-slack-logo", category="communication",
            config_keys=["SLACK_BOT_TOKEN"],
            tools=[{"name":"send_message","desc":"Send message"},{"name":"list_channels","desc":"List channels"},{"name":"upload_file","desc":"Upload file"}]
        ))
        self.add(ConnectorInfo(
            id="gmail", name="Gmail", description="Emails, drafts, labels",
            icon="ph ph-envelope", category="communication",
            config_keys=["GMAIL_CREDENTIALS"],
            tools=[{"name":"search_emails","desc":"Search emails"},{"name":"send_email","desc":"Send email"},{"name":"list_labels","desc":"List labels"}]
        ))
        self.add(ConnectorInfo(
            id="calendar", name="Google Calendar", description="Events, reminders, scheduling",
            icon="ph ph-calendar", category="communication",
            config_keys=["GOOGLE_CREDENTIALS"],
            tools=[{"name":"list_events","desc":"List events"},{"name":"create_event","desc":"Create event"},{"name":"find_slots","desc":"Find free time"}]
        ))
        
        # ── Data & Web ──
        self.add(ConnectorInfo(
            id="web_search", name="Web Search", description="Real-time web search",
            icon="ph ph-globe", category="data",
            tools=[{"name":"search","desc":"Search the web"},{"name":"fetch","desc":"Fetch page content"}]
        ))
        self.add(ConnectorInfo(
            id="market", name="A-Shares Market", description="Real-time Chinese stock data",
            icon="ph ph-trend-up", category="data",
            tools=[{"name":"get_indices","desc":"Get all indices"},{"name":"get_stock","desc":"Get stock quote"}]
        ))
        self.add(ConnectorInfo(
            id="weather", name="Weather", description="Current conditions, forecasts",
            icon="ph ph-cloud-sun", category="data",
            tools=[{"name":"current","desc":"Current weather"},{"name":"forecast","desc":"Weather forecast"}]
        ))
        
        # ── Device Control ──
        self.add(ConnectorInfo(
            id="camera", name="Camera", description="Capture photos, video",
            icon="ph ph-camera", category="device",
            tools=[{"name":"snap","desc":"Take photo"},{"name":"list","desc":"List cameras"}]
        ))
        self.add(ConnectorInfo(
            id="audio", name="Audio", description="Play, record, manage audio",
            icon="ph ph-speaker-high", category="device",
            tools=[{"name":"play","desc":"Play audio"},{"name":"record","desc":"Record audio"},{"name":"list","desc":"List devices"}]
        ))
        self.add(ConnectorInfo(
            id="display", name="Display", description="Screen capture, multi-monitor",
            icon="ph ph-monitor", category="device",
            tools=[{"name":"screenshot","desc":"Capture screen"},{"name":"list","desc":"List displays"}]
        ))
        self.add(ConnectorInfo(
            id="process", name="Process Manager", description="Manage running processes",
            icon="ph ph-cpu", category="device",
            tools=[{"name":"list","desc":"List processes"},{"name":"kill","desc":"Kill process"},{"name":"info","desc":"Process info"}]
        ))
    
    def add(self, info: ConnectorInfo):
        self._connectors[info.id] = info
        # Auto-connect if no config keys needed
        if not info.config_keys:
            info.status = "connected"
    
    def list_all(self) -> List[dict]:
        """Return all connectors with status."""
        result = []
        for c in self._connectors.values():
            result.append({
                "id": c.id, "name": c.name, "description": c.description,
                "icon": c.icon, "category": c.category, "status": c.status,
                "config_keys": c.config_keys, "tools": c.tools
            })
        # Sort: connected first, then by category
        cats = {"device": 0, "code": 1, "data": 2, "communication": 3}
        result.sort(key=lambda x: (0 if x["status"]=="connected" else 1, cats.get(x["category"], 9), x["name"]))
        return result
    
    def list_by_category(self) -> Dict[str, List[dict]]:
        """Group connectors by category."""
        all_c = self.list_all()
        cats = {}
        for c in all_c:
            cat = c["category"]
            if cat not in cats:
                cats[cat] = []
            cats[cat].append(c)
        return cats
    
    def connect(self, conn_id: str) -> dict:
        """Attempt to connect a connector."""
        if conn_id not in self._connectors:
            return {"ok": False, "error": "Unknown connector"}
        c = self._connectors[conn_id]
        if not c.config_keys:
            c.status = "connected"
            return {"ok": True, "status": "connected"}
        # Check env vars
        missing = []
        for key in c.config_keys:
            if not os.environ.get(key):
                missing.append(key)
        if missing:
            c.status = "disconnected"
            return {"ok": False, "error": f"Missing config: {', '.join(missing)}"}
        c.status = "connected"
        return {"ok": True, "status": "connected"}
    
    def disconnect(self, conn_id: str):
        if conn_id in self._connectors:
            self._connectors[conn_id].status = "disconnected"

# Global singleton
_registry = None

def get_registry() -> ConnectorRegistry:
    global _registry
    if _registry is None:
        _registry = ConnectorRegistry()
    return _registry
