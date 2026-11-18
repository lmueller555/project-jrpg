"""Export the retained approved dialogue portrait without any sprite builders."""
from __future__ import annotations

import argparse
from io import BytesIO
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'assets/source/portraits/eldenmere/iselin_master.png'
OUTPUT = ROOT / 'assets/portraits/eldenmere/iselin_neutral.png'


def product():
    master = Image.open(SOURCE)
    if master.width != master.height:
        raise ValueError('Iselin portrait source must be square')
    expected = master.convert('RGB').resize((72, 72), Image.Resampling.NEAREST)
    if OUTPUT.exists():
        current = Image.open(OUTPUT).convert('RGB')
        if current.size == expected.size and current.tobytes() == expected.tobytes():
            return OUTPUT.read_bytes()
    stream = BytesIO()
    expected.save(stream, format='PNG', optimize=True)
    return stream.getvalue()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    data = product()
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_bytes() != data:
            raise SystemExit('Stale Iselin dialogue portrait')
        print('Approved Iselin dialogue portrait matches the retained source.')
        return
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_bytes(data)


if __name__ == '__main__':
    main()
