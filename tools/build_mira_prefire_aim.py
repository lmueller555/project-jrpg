"""Rebuild the registered cuff-lift cinematic endpoints and poses."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from tools.build_mira_rig_continuity import build

if __name__ == "__main__":build()
