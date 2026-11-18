"""Assemble Iselin's approved native idles and walks for the live actor.

The four idle and 64 walking PNGs remain untouched. This builder only arranges
their existing 24x36 pixels into the ordinary actor sheet and authored timings.
"""
from __future__ import annotations

import argparse
import io
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'assets/characters/iselin'
DIRECTIONS = ('front', 'left', 'right', 'back')


def products():
    sheet = Image.new('RGBA', (68 * 24, 36))
    idles, walks = {}, {}
    for index, direction in enumerate(DIRECTIONS):
        idle = Image.open(BASE / f'native_idles/idle_{direction}.png').convert('RGBA')
        if idle.size != (24, 36):
            raise ValueError('Native Iselin idle must be 24x36: ' + direction)
        rect = [index * 24, 0, 24, 36]
        sheet.alpha_composite(idle, (rect[0], 0))
        idles[direction] = rect
        manifest = json.loads((BASE / f'native_walk_{direction}/animation.json').read_text())
        if len(manifest['frames']) != 16 or sum(frame['duration_ms'] for frame in manifest['frames']) != 560:
            raise ValueError('Native Iselin walk must retain its 16-frame, 560 ms cadence')
        sequence = []
        for frame_index, frame in enumerate(manifest['frames']):
            image = Image.open(BASE / f'native_walk_{direction}' / frame['file']).convert('RGBA')
            if image.size != (24, 36) or frame['duration_ms'] != 35:
                raise ValueError('Native Iselin frame/timing changed: ' + direction)
            rect = [(4 + index * 16 + frame_index) * 24, 0, 24, 36]
            sheet.alpha_composite(image, (rect[0], 0))
            sequence.append({'rect': rect, 'duration_ms': frame['duration_ms']})
        walks[direction] = sequence
    buffer = io.BytesIO()
    sheet.save(buffer, format='PNG', optimize=True)
    sheet_path = BASE / 'native_overworld.png'
    sheet_data = buffer.getvalue()
    # Pixel-identical PNGs can have different encodings across Pillow versions.
    # Preserve the committed encoding without hiding any actual source change.
    if sheet_path.exists():
        current = Image.open(sheet_path).convert('RGBA')
        if current.size == sheet.size and current.tobytes() == sheet.tobytes():
            sheet_data = sheet_path.read_bytes()
    manifest = {
        'sheet': 'assets/characters/iselin/native_overworld.png',
        'idles': idles,
        'walks': walks,
        'frame_size': [24, 36],
        'draw_anchor': [12, 30],
        'foot_anchor': [12, 34],
        'artwork_pixels_per_world_pixel': 1,
        'status': 'Approved native artwork integrated into live Iselin actor.',
    }
    return {sheet_path: sheet_data,
            BASE / 'animation.json': (json.dumps(manifest, indent=2) + '\n').encode()}


def build(check=False):
    outputs = products()
    if check:
        stale = [str(path.relative_to(ROOT)) for path, data in outputs.items()
                 if not path.exists() or path.read_bytes() != data]
        if stale:
            raise SystemExit('Stale native Iselin actor exports: ' + ', '.join(stale))
        print('Live native Iselin actor matches all approved source frames.')
        return outputs
    for path, data in outputs.items():
        path.write_bytes(data)
    print('Assembled live native Iselin actor from four idles and 64 walking frames.')
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    build(args.check)


if __name__ == '__main__':
    main()
