"""Register original imagegen scenery as bounded cinematic depth plates.

No environment artwork is painted here. The exporter nearest-resizes authored
plates, extracts their foreground strips and registers the isolated gate prop.
Original generations, revisions and prompts remain untouched. --check compares
every resulting byte against a fresh temporary export.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tempfile

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/cinematics/regent_arrival/scenery'
TARGET = ROOT/'assets/story/regent_arrival/scenery'
SIZE = (960, 480)
PLATES = {
    'gate': ('south_gate_revised.png', 'south_gate.png'),
    'riverbank': ('riverbank_revised.png', 'riverbank.png'),
    'approach': ('town_approach_revised.png', 'town_approach.png'),
    'sanctuary': ('sanctuary_window_revised.png', 'sanctuary_window.png'),
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def record(path, prefix):
    with Image.open(path) as image:
        size = list(image.size)
    return {'file': prefix+'/'+path.name, 'size': size, 'sha256': digest(path)}


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2)+'\n', encoding='utf-8')


def export(target):
    target.mkdir(parents=True, exist_ok=True)
    names = sorted(SOURCE.glob('*.png'))
    original = {path.name: digest(path) for path in names}
    scenes = {}
    for key, (source_name, filename) in PLATES.items():
        with Image.open(SOURCE/source_name) as image:
            plate = image.convert('RGB').resize(SIZE, Image.Resampling.NEAREST)
        plate.save(target/filename, optimize=True)
        foreground = Image.new('RGBA', SIZE)
        # Keep fully painted overscan beneath the independently moving strip.
        # This crop does not invent, retouch or recolor any scenery pixels.
        foreground.alpha_composite(plate.crop((0, 442, 960, 480)).convert('RGBA'), (0, 442))
        foreground_name = filename.removesuffix('.png')+'_foreground.png'
        foreground.save(target/foreground_name, optimize=True)
        scenes[key] = {
            'background': filename,
            'foreground': foreground_name,
            'floor_y': 375,
            'camera': [380, 125] if key == 'gate' else [320, 140],
            'anchors': {},
        }
    with Image.open(SOURCE/'gate_leaf_generated.png') as image:
        gate = image.convert('RGBA')
        gate.putalpha(gate.getchannel('A').point(lambda value: 255 if value >= 128 else 0))
        bounds = gate.getbbox()
        if bounds is None:
            raise ValueError('Authored gate leaf is empty')
        gate = gate.crop(bounds).resize((156, 49), Image.Resampling.NEAREST)
        gate.save(target/'gate_leaf.png', optimize=True)
    scenes['gate'].update({
        'gate_leaf': {'file': 'gate_leaf.png', 'position': [495, 248],
                      'anchor': [0, 0], 'slide': [-150, -8],
                      'hinge': [0, 49], 'open_scale': [0.08, 1.0]},
        'anchors': {'left_post': [480, 296], 'right_post': [650, 287],
                    'aperture_center': [575, 292], 'guard': [530, 375],
                    'aldric': [625, 375], 'caravan': [805, 375],
                    'north_exit': [550, 280]},
    })
    scenes['riverbank']['anchors'] = {
        'aldric': [620, 375], 'local': [530, 375], 'clerk': [710, 380],
        'safe_bank': [610, 375], 'broken_span_focus': [330, 260],
        'river_surface': [285, 330],
    }
    scenes['approach']['anchors'] = {
        'wagon_waiting': [610, 375], 'aldric_waiting': [530, 375],
        'brook_bridge': [840, 265], 'sanctuary': [320, 180],
        'west_bank_layby': [610, 340],
    }
    scenes['sanctuary'].update({
        'camera': [320, 100],
        'anchors': {'serene_window': [625, 335], 'tomas_cups': [735, 375],
                    'window_sill': [520, 270], 'window_view': [530, 210],
                    'hospitality_counter': [790, 280]},
    })
    manifest = {
        'version': 1, 'canvas': list(SIZE), 'viewport': [480, 320],
        'scenes': scenes,
        'geography': {
            'gate': 'Intact southern land checkpoint; the caravan never crosses the ruined western river bridge.',
            'riverbank': 'Safe east bank of the western boundary river; a broad stone crossing has lost its central span.',
            'approach': 'West approach to the intact LOWER MAIN WOODEN town-brook bridge. Caravan waits on the southern verge; sanctuary lies farther northwest.',
            'sanctuary': 'Serene watches from inside the village sanctuary dining room; this is not the old protected ridge sanctuary.',
        },
    }
    write_json(target/'scenery.json', manifest)
    provenance = {
        'version': 1, 'canvas': list(SIZE),
        'exporter': 'tools/build_regent_arrival_scenery.py',
        'exporter_sha256': digest(Path(__file__)),
        'prompts_sha256': digest(SOURCE/'prompts.json'),
        'sources': [record(path, 'assets/source/cinematics/regent_arrival/scenery') for path in names],
        'exports': [record(path, 'assets/story/regent_arrival/scenery') for path in sorted(target.glob('*.png'))],
        'scenery_manifest_sha256': digest(target/'scenery.json'),
        'notes': [
            'Original imagegen generations and revisions are retained without alteration.',
            'Exports only crop alpha/foreground pixels and nearest-resize authored imagery.',
            'No actors, horses, caravans, interface or dialogue are baked into the scenery.',
            'Gate leaf is a separate authored transparent prop; the background aperture is open.',
            'Far village architecture uses a humble blue-roof sanctuary and timber belfry, not a cathedral.',
            'The destroyed bridge is broad enough for wagon traffic; both road approaches are scarred.',
            'The intact town-brook wooden bridge is distinct from the ruined western stone river crossing.',
            'Sanctuary window sill and character feet are registered for a 76-pixel adult looking outward.',
        ],
    }
    write_json(target/'scenery_provenance.json', provenance)
    if original != {path.name: digest(path) for path in names}:
        raise AssertionError('An original scenery source changed during export')
    return sorted(path.name for path in target.iterdir())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.check:
        with tempfile.TemporaryDirectory(prefix='regent-scenery-') as temporary:
            output = Path(temporary)
            names = export(output)
            for name in names:
                if not (TARGET/name).exists() or (TARGET/name).read_bytes() != (output/name).read_bytes():
                    raise SystemExit('Scenery export differs: '+name)
            if sorted(path.name for path in TARGET.iterdir()) != names:
                raise SystemExit('Unexpected files in scenery export directory')
        print('Verified four cinematic plates, four foreground layers, gate leaf and provenance')
    else:
        names = export(TARGET)
        print('Exported '+str(len(names))+' registered cinematic scenery files')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
