"""Extract the imagegen-authored combat atlases into native game frames.

This exporter performs grid extraction, nearest-neighbor scaling, baseline
registration and binary-alpha PNG conversion only. It does not redraw art or
invent poses. The two source PNGs are retained for reproducible extraction.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/combat'
OUTPUT = ROOT/'assets/combat'
SIZE = (48, 48)
ANCHOR = (24, 42)
EXTRACTED = (42, 42)

ANIMATIONS = {
    'caelan': {
        'idle': ([0, 1], [260, 260], True),
        'attack': ([2, 3, 4], [180, 240, 300], False),
        'cast': ([5, 6, 7], [250, 330, 320], False),
        'guard': ([8, 9], [240, 240], True),
        'hurt': ([10, 11], [160, 240], False),
        'victory': ([12, 13], [340, 340], True),
        'defeat': ([14, 15], [260, 420], False),
    },
    'bat': {
        'idle': ([0, 1, 2, 3], [120, 120, 120, 120], True),
        'attack': ([4, 5, 6], [180, 240, 300], False),
        'cast': ([7, 8, 9], [200, 330, 320], False),
        'hurt': ([10, 11], [150, 220], False),
        'defeat': ([12, 13, 14, 15], [150, 180, 200, 350], False),
    },
}


def extracted_frames(source, actor):
    image = Image.open(source).convert('RGBA')
    width, height = image.size
    frames = []
    for index in range(16):
        column, row = index%4, index//4
        bounds = (round(column*width/4), round(row*height/4),
                  round((column+1)*width/4), round((row+1)*height/4))
        cell = image.crop(bounds).resize(EXTRACTED, Image.Resampling.NEAREST)
        # Native pixel sprites require binary coverage. imagegen sources have
        # subpixel alpha and very faint background residue, not intended pixels.
        cell.putalpha(cell.getchannel('A').point(lambda alpha: 255 if alpha >= 128 else 0))
        box = cell.getbbox()
        if box is None:raise ValueError(f'Empty generated cell {actor}:{index}')
        if actor == 'caelan':
            # Register the supporting foot, preserving authored arm, heel,
            # knee and torso motion and the shorter kneeling defeat poses.
            y = ANCHOR[1]-box[3]
        elif index < 12:
            # Flight poses retain their authored bob and wing motion above
            # the ground anchor. The same translation is used for every pose.
            y = -7
        else:
            # The authored defeat sequence descends to the shared ground plane.
            y = (32, 36, 42, 42)[index-12]-box[3]
        frame = Image.new('RGBA', SIZE)
        frame.alpha_composite(cell, (3, y))
        if set(frame.getchannel('A').tobytes())-{0, 255}:
            raise ValueError('Sprite alpha export must remain binary')
        frames.append(frame)
    return frames


def build_actor(actor):
    source = SOURCE/(actor+'_generated_sheet.png')
    directory = OUTPUT/actor
    directory.mkdir(parents=True, exist_ok=True)
    frames = extracted_frames(source, actor)
    animations = {}
    for state, (indices, durations, loop) in ANIMATIONS[actor].items():
        records = []
        for number, (index, duration) in enumerate(zip(indices, durations), 1):
            filename = f'{state}_{number:02d}.png'
            frames[index].save(directory/filename, optimize=True)
            records.append({'file': filename, 'duration_ms': duration,
                            'source_cell': index})
        animations[state] = {'loop': loop, 'frames': records}
    if actor == 'bat':
        for alias, canonical in (('fly', 'idle'), ('bite', 'attack'), ('wing_gust', 'cast')):
            animations[alias] = animations[canonical]
    sheet = Image.new('RGBA', (SIZE[0]*4, SIZE[1]*4))
    for index, frame in enumerate(frames):
        sheet.alpha_composite(frame, ((index%4)*SIZE[0], (index//4)*SIZE[1]))
    sheet.save(directory/'spritesheet.png', optimize=True)
    metadata = {
        'version': 1, 'actor': actor, 'canvas': list(SIZE), 'anchor': list(ANCHOR),
        'facing': 'left' if actor == 'caelan' else 'right',
        'source_sheet': source.relative_to(ROOT).as_posix(),
        'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'sheet': 'spritesheet.png', 'animations': animations,
    }
    (directory/'animation.json').write_text(json.dumps(metadata, indent=2)+'\n')
    return metadata


def main():
    results = {actor: build_actor(actor) for actor in ANIMATIONS}
    print(json.dumps({'actors': list(results), 'native_canvas': list(SIZE),
                      'source_cells_per_actor': 16}))
    return 0


if __name__ == '__main__':raise SystemExit(main())
