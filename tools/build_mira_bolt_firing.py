"""Export the scoped, whole-drawing Bolt Shot firing repair.

The generated master supplies complete poses. A documented regional restore
protects the accepted head and planted lower body; no limb is transformed or
procedurally drawn. The original aim drawings and every other skill stay intact.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/combat/mira_bolt_firing'
OUTPUT = ROOT/'assets/combat/mira'
SCALE = 45/448
POSITION = (4, 10)
DURATIONS = (40, 40, 50, 60, 70, 80, 100, 120)
PHASES = ('compression', 'snap', 'recoil', 'recoil_peak', 'settle',
          'followthrough', 'lower', 'rest')
# Source-cell landmarks, measured on the retained complete drawings.
MUZZLES = ((103,178), (103,177), (111,177), (127,175),
           (127,172), (107,177), (110,202), (97,248))


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build(metadata=None):
    if metadata is None:
        metadata = json.loads((OUTPUT/'animation.json').read_text())
    specification = json.loads((SOURCE/'recipe.json').read_text())
    for name, expected in specification['source_hashes'].items():
        if digest(SOURCE/name) != expected:
            raise ValueError('Changed protected Mira source: '+name)
    atlas = Image.open(SOURCE/'firing_authored.png').convert('RGBA')
    reference = Image.open(SOURCE/'protected_aim.png').convert('RGBA')
    # Reuse the accepted bank's existing colors, not a newly generated palette.
    colors = sorted(set(pixel[:3] for pixel in reference.getdata() if pixel[3]))
    palette = Image.new('RGB', (len(colors), 1));palette.putdata(colors)
    palette = palette.quantize(colors=len(colors), dither=Image.Dither.NONE)
    # The first 240 ms retain the original three complete aim drawings.
    original = metadata['animations']['attack']['frames'][:3]
    frames = deepcopy(original)
    frames[-1]['duration_ms'] = 60
    for index, (duration, phase, muzzle) in enumerate(zip(DURATIONS, PHASES, MUZZLES)):
        left, top = index%4*448, index//4*448
        cell = atlas.crop((left, top, left+448, top+448))
        cell.putalpha(cell.getchannel('A').point(lambda alpha:255 if alpha >= 128 else 0))
        cutout = cell.resize((45,45), Image.Resampling.NEAREST)
        alpha = cutout.getchannel('A')
        cutout = cutout.convert('RGB').quantize(palette=palette,
            dither=Image.Dither.NONE).convert('RGBA');cutout.putalpha(alpha)
        image = Image.new('RGBA', (64,64));image.alpha_composite(cutout, POSITION)
        # Protect original identity and the complete, stationary hip/leg chains.
        image.paste(reference.crop((0,0,64,26)), (0,0))
        image.paste(reference.crop((0,36,64,64)), (0,36))
        name = f'bolt_firing_{index+1:02}.png'
        image.save(OUTPUT/name, optimize=True)
        point = [round(POSITION[axis]+muzzle[axis]*SCALE) for axis in (0,1)]
        # Registration formula remains explicit even though protected regions
        # intentionally retain their exact accepted native pixels.
        foot = [(32-POSITION[0])/SCALE, (54-POSITION[1])/SCALE]
        anchors = dict(floor=[32,54], muzzle=point, controller=[point[0]+7,point[1]],
                       projector=point, tool=point)
        frames.append(dict(file=name, duration_ms=duration, phase=phase,
            source_cell=82+index, source='firing_authored.png',
            source_sheet='assets/source/combat/mira_bolt_firing/firing_authored.png',
            source_rect=[left,top,448,448],
            # Pillow pads the outermost extraction cells with transparent
            # pixels. Provenance bounds describe only real source pixels.
            source_bounds=[left,top,min(left+448,atlas.width),min(top+448,atlas.height)],
            source_foot=foot, native_scale=SCALE, position=list(POSITION), anchors=anchors,
            regional_restore='assets/source/combat/mira_bolt_firing/recipe.json'))
    animation = dict(loop=False, frames=frames, release_ms=280, contact_ms=400,
                     flash_duration_ms=40, duration_ms=800)
    metadata['animations']['attack'] = animation
    metadata['animations']['bolt_shot'] = deepcopy(animation)
    path = 'assets/source/combat/mira_bolt_firing/firing_authored.png'
    metadata['source_sheets'] = [r for r in metadata['source_sheets'] if r['path'] != path]
    metadata['source_sheets'].append(dict(path=path, sha256=digest(SOURCE/'firing_authored.png'), grid=[4,2]))
    metadata['authored_frames'] = 90
    # Retain all 82 historical complete drawings on their original sheet cells.
    sheet = Image.open(OUTPUT/'spritesheet.png').convert('RGBA')
    expanded = Image.new('RGBA',(512,768));expanded.alpha_composite(sheet.crop((0,0,512,704)))
    for index, record in enumerate(frames[3:],82):
        expanded.alpha_composite(Image.open(OUTPUT/record['file']),((index%8)*64,(index//8)*64))
    expanded.save(OUTPUT/'spritesheet.png',optimize=True)
    metadata['sheet_grid'] = [8,12]
    (OUTPUT/'animation.json').write_text(json.dumps(metadata,indent=2)+'\n')
    return metadata


if __name__ == '__main__':
    print(json.dumps({'authored_frames':build()['authored_frames']}))
