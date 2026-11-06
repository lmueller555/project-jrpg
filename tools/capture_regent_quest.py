"""Capture the revised MQ03 from a real, disposable New Game.

The original entry point now delegates to the unseeded visit capture. Its
new default directory preserves earlier reviews as historical records.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.capture_mq03_revised_visit import Capture, main


def capture():main()


if __name__ == '__main__':capture()
