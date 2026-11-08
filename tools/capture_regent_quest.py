"""Capture the current MQ03 emergency in a disposable gameplay session.

The current driver labels its earlier-quest fixture and plays MQ03 through
ordinary dialogue and travel. Earlier visit reviews remain historical records.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.capture_mq03_emergency import capture, main


if __name__ == '__main__':main()
