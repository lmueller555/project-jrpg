"""Register twelve authored Caelan crosswind drawings without pose deformation.

The four-column, three-row image_gen source contains impact, sideways flight and
landing in order. A single scale derived from the first standing drawing preserves
the naturally crouched proportions of the airborne and recovery drawings.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.build_ice_reaper_continuity_views import register, remove_detached_cell_bleed

SOURCE = ROOT/'assets/source/cinematics/caelan_crosswind/crosswind_generated.png'
TARGET = ROOT/'assets/story/ice_reaper_duel/men/caelan/crosswind'
REVIEW = ROOT/'docs/reviews/caelan_duel_correction'
CANVAS, ANCHOR = (128, 128), (64, 116)
BODY_PIXELS = 82
STANDING_HEIGHT = 71


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def extract(path):
    source = Image.open(path).convert('RGBA')
    result = []
    for row in range(3):
        for col in range(4):
            box = (round(col*source.width/4), round(row*source.height/3),
                   round((col+1)*source.width/4), round((row+1)*source.height/3))
            tile = source.crop(box)
            tile.putalpha(tile.getchannel('A').point(lambda alpha: 255 if alpha >= 140 else 0))
            tile = remove_detached_cell_bleed(tile)
            if tile.getbbox() is None:
                raise ValueError(f'Empty crosswind cell {row},{col}')
            result.append((tile, box))
    return result


def body_height(image):
    """Ignore projecting orange sword fire when measuring standing scale."""
    pixels = np.asarray(image)
    alpha = pixels[:, :, 3] > 0
    orange = ((pixels[:, :, 0] > 180) &
              (pixels[:, :, 0] > pixels[:, :, 1]*1.3) &
              (pixels[:, :, 2] < 110))
    rows = np.where(np.any(alpha & ~orange, axis=1))[0]
    return int(rows[-1]-rows[0]+1)


def build(source=SOURCE, target=TARGET, review=REVIEW):
    target.mkdir(parents=True, exist_ok=True)
    review.mkdir(parents=True, exist_ok=True)
    cells = extract(source)
    scale = STANDING_HEIGHT/body_height(cells[0][0])
    # One scale for all poses. Reject oversized art rather than distorting it.
    max_width = max(image.getbbox()[2]-image.getbbox()[0] for image, _ in cells)
    if max_width*scale > CANVAS[0]-4:
        raise ValueError('Crosswind art is too wide at its fixed body scale')
    source_name = str(source.relative_to(ROOT))
    source_hash = digest(source)
    frames_by_action, provenance, contact = {}, [], []
    specs = (
        ('wind_hit_rear_right', -150, 51,
         'Rear three-quarter boss-facing crosswind hit; torso shifts right, free arm braces and sword stays low.'),
        ('wind_flight_rear', -180, 123,
         'Rear-view sideways flight toward Mira; knees lift naturally and legs trail the lateral displacement.'),
        ('wind_land_rear_right', -145, 58,
         'Rear-quarter landing and bent-knee recovery, looking back toward the confrontation.'),
    )
    animations = {}
    for row, (key, angle, duration, note) in enumerate(specs):
        frames = []
        for col, (tile, box) in enumerate(cells[row*4:row*4+4], 1):
            frame, registration = register(tile, scale, CANVAS, ANCHOR)
            filename = f'{key}_{col:02}.png'
            frame.save(target/filename, optimize=True)
            frames.append(dict(file=filename, duration_ms=duration))
            provenance.append(dict(file=filename, source=source_name,
                source_cell=row*4+col-1, source_box=list(box), sha256=digest(target/filename),
                **registration))
            contact.append((filename, frame))
        frames_by_action[key] = frames
        animations[key] = dict(frames=frames, view_azimuth_deg=angle,
                               loop=False, facing_note=note)
    # The same authored landing silhouette spans the brief rear/quarter selector
    # boundary during the moving camera, avoiding a return to the old art.
    animations['wind_land_rear'] = dict(animations['wind_land_rear_right'],
                                       view_azimuth_deg=-180)
    manifest = dict(version=1, actor='caelan', canvas=list(CANVAS), anchor=list(ANCHOR),
                    body_pixels=BODY_PIXELS, authored=True, source_art_review='awaiting_user_review',
                    sources=[dict(file=source_name, sha256=source_hash)], animations=animations,
                    note=__doc__.strip())
    (target/'animation.json').write_text(json.dumps(manifest, indent=2)+'\n')
    record = dict(version=1, generated_with='image_gen', source=source_name,
                  source_sha256=source_hash, operation='Equal-cell extraction, alpha threshold, '
                  'detached-cell cleanup, one uniform nearest-neighbor scale, palette and foot registration. '
                  'No mirroring, joint warping or generated in-between poses.',
                  standing_height_pixels=STANDING_HEIGHT, fixed_scale=scale,
                  original_parent_wind_art_unchanged=True, frames=provenance)
    (target/'provenance.json').write_text(json.dumps(record, indent=2)+'\n')
    sheet = Image.new('RGB', (384*4, 416*3), '#14232c')
    draw = ImageDraw.Draw(sheet)
    for index, (filename, frame) in enumerate(contact):
        x, y = index%4*384, index//4*416
        enlarged = frame.resize((384, 384), Image.Resampling.NEAREST)
        sheet.paste(enlarged, (x, y), enlarged)
        draw.text((x+6, y+390), filename, fill='white')
    sheet.save(review/'crosswind_drawings.png', optimize=True)
    print(json.dumps(dict(drawings=len(contact), fixed_scale=scale,
                          manifest=str((target/'animation.json').relative_to(ROOT)),
                          contact=str((review/'crosswind_drawings.png').relative_to(ROOT)))))
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=SOURCE)
    parser.add_argument('--target', type=Path, default=TARGET)
    parser.add_argument('--review', type=Path, default=REVIEW)
    args = parser.parse_args()
    build(args.source.resolve(), args.target.resolve(), args.review.resolve())
