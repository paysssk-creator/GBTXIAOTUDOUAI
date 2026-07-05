"""GBT 终端版入口 — 委托给 mirror_dimension_tui"""
import sys, os
_tui_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'GBTXIAOTUDOUAI')
if _tui_dir not in sys.path:
    sys.path.insert(0, _tui_dir)
from mirror_dimension_tui import main

if __name__ == '__main__':
    main()
