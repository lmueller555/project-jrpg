"""Export registered one-shot Bolt Shot recoil from full authored Tusker poses."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/combat'
ART = ROOT/'assets/combat/ridgeback_tusker'
# Common sample size, density and native registration for all complete drawings.
LOW = ('mq02_tusker_bolt_recoil.png', 16,
       tuple((x, 155, x+570, 558) for x in (89, 813, 1536)), (69, 48), (13, 14))
RAISED = ('mq02_tusker_bolt_recoil_raised.png', 19,
          tuple((x, 143, x+572, 563) for x in (82, 806, 1530)), (69, 49), (14, 13))
BANKS = (
    ('bolt_hurt', 0, LOW),
    ('bolt_hurt_raised', 1, RAISED),
    ('bolt_hurt_low3', 2, LOW),
    ('bolt_hurt_low4', 3, LOW),
)
DURATIONS = (55, 95, 100)
REST_MS = 70
# Restore protected idle pixels around each depicted repair window. These
# windows preserve the tail, hindquarters and all four lower leg contacts;
# the shoulder-only key additionally preserves the entire idle head.
SHOULDER = ((36,16),(62,10),(62,26),(61,39),(58,49),(55,53),(50,53),(46,46),(39,42))
NECK = ((40,14),(95,9),(95,54),(68,54),(62,51),(55,53),(49,53),(45,45),(41,41))


def export_bank(directory, data, state, idle_index, artwork):
    basename, first_source_cell, crops, sample_size, origin = artwork
    source = SOURCE/basename
    idle_record = data['animations']['idle']['frames'][idle_index]
    idle = Image.open(directory/idle_record['file']).convert('RGBA')
    sheet = Image.open(source).convert('RGBA')
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    frames = []
    for index, (crop, duration, window) in enumerate(zip(crops, DURATIONS,
                                                          (SHOULDER, NECK, NECK))):
        sample = sheet.crop(crop).resize(sample_size, Image.Resampling.NEAREST)
        sample.putalpha(sample.getchannel('A').point(lambda alpha: 255 if alpha >= 128 else 0))
        registered = Image.new('RGBA', idle.size)
        registered.paste(sample, origin)
        mask = Image.new('L', idle.size)
        ImageDraw.Draw(mask).polygon(window, fill=255)
        frame = Image.composite(registered, idle, mask)
        filename = f'{state}_{index+1:02}.png'
        frame.save(directory/filename, optimize=True)
        frames.append(dict(file=filename, duration_ms=duration, source_cell=first_source_cell+index,
                           source_sheet=source.relative_to(ROOT).as_posix(), source_sha256=source_hash,
                           source_bounds=list(crop)))
    frames.append(dict(idle_record, duration_ms=REST_MS))
    return dict(loop=False, frames=frames)


def export(directory=ART):
    manifest = directory/'animation.json'
    data = json.loads(manifest.read_text())
    for state, idle_index, artwork in BANKS:
        data['animations'][state] = export_bank(directory, data, state, idle_index, artwork)
    manifest.write_text(json.dumps(data, indent=2)+'\n')
    return data


if __name__ == '__main__':
    export()
