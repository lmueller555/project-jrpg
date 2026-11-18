"""Select Liam's complete native design only after its separate art PR is present."""
import json
from pathlib import Path
from rendering import load_art

ROOT=Path(__file__).resolve().parent
BANK=Path('assets/characters/liam/activity_hd')
DESIGN=ROOT/'assets/characters/named_hd/liam/design.json'


def active():return DESIGN.is_file()


def manifest(path):
    return json.loads((ROOT/BANK/path).read_text())


def story_sheet(world, kind, legacy_path):
    if active():
        meta=manifest(f'lantern_{kind}/liam.json')
        return meta,load_art(world,meta['sheet'],meta)
    meta=json.loads((ROOT/legacy_path).read_text())
    return meta,world.image(meta['sheet'])


def home_actions(world, kind):
    meta=manifest(f'{kind}/animations.json')
    return {key:[(load_art(world,frame['file'],meta),frame['duration_ms'])
                 for frame in spec['frames']] for key,spec in meta['actions'].items()}
