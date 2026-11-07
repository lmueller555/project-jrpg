"""Capture free grass, cloister, cave and hall as part of the pixel-asset review.

The old painted-scene comparison has been replaced by the complete review.
"""
from pathlib import Path
import argparse
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.capture_sanctuary_reserve import OUT, capture, check


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=OUT)
    parser.add_argument('--no-movie',action='store_true')
    parser.add_argument('--check',action='store_true')
    args = parser.parse_args()
    if args.check:check(args.out)
    else:capture(args.out,not args.no_movie)
