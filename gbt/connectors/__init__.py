"""GBT Connectors — 18个真实生产级连接器"""
from .registry import ConnectorRegistry, get_registry, ConnectorInfo

# 核心本地连接器
from . import github as _github
from . import git_local as _git_local
from . import filesystem as _filesystem
from . import terminal as _terminal
from . import pypi as _pypi
from . import network as _network
from . import wifi as _wifi
from . import wregistry as _wregistry
from . import web_search as _web_search
from . import market as _market
from . import weather as _weather
from . import device as _device
from . import cloud as _cloud

# 模块映射: connector_id -> module_with_handler
MODULE_MAP = {
    "github": _github,
    "git": _git_local,
    "filesystem": _filesystem,
    "terminal": _terminal,
    "pypi": _pypi,
    "network": _network,
    "wifi": _wifi,
    "registry": _wregistry,
    "web_search": _web_search,
    "market": _market,
    "weather": _weather,
    "camera": _device,
    "audio": _device,
    "display": _device,
    "process": _device,
    "notion": _cloud,
    "slack": _cloud,
    "gmail": _cloud,
    "calendar": _cloud,
}
