"""Extract Mira's authored combat bank with explicit anatomical registration.

The retained atlas is unmodified imagegen artwork. Export only selects its main
connected alpha silhouettes, reduces at one fixed nearest-neighbor scale, and
places each complete drawing against its measured ground point. Detached source
projectiles are discarded; the battle renderer owns release and impact effects.
"""
from __future__ import annotations

from collections import deque
import hashlib
import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/combat/mira_arm_rig'
OUTPUT = ROOT/'assets/combat/mira'
ANIMATIONS = {
    'idle': ([0, 1, 2, 3], [280, 260, 280, 260], True),
    'attack': (list(range(4, 12)), [100, 80, 100, 60, 80, 100, 140, 140], False),
    'guard_enter': ([12, 13], [150, 150], False),
    'guard': ([14, 15], [300, 300], True),
    'guard_impact': ([16, 17, 40, 41], [80, 100, 100, 120], False),
    'hurt': ([18, 19, 20, 21], [80, 100, 100, 120], False),
    'rig_activation': (list(range(22, 28)), [150, 150, 200, 100, 150, 150], False),
    'victory': (list(range(28, 32)), [180, 180, 320, 420], False),
    'defeat': (list(range(32, 36)), [120, 160, 180, 420], False),
    'walk': (list(range(36, 40)), [140, 140, 140, 140], True),
    'charged_bolt': (list(range(42,50)), [120,100,100,140,90,90,140,180], False),
    'bulwark': (list(range(50,58)), [100,100,140,120,180,180,120,160], False),
    'repair_pulse': (list(range(58,66)), [120,120,140,140,180,140,140,180], False),
    'impact_bolt': (list(range(66,74)), [100,100,120,80,100,160,120,180], False),
    'arc_discharge': (list(range(74,82)), [120,100,120,160,100,100,140,180], False),
}


def _main_component(image):
    """Keep the authored whole body, excluding detached bolts and alpha fringe."""
    width, height = image.size
    pending_pixels = bytearray(value >= 128 for value in image.getchannel('A').tobytes())
    largest = []
    for start in range(width*height):
        if not pending_pixels[start]:continue
        pending_pixels[start] = 0
        queue, members = deque([start]), []
        while queue:
            pixel = queue.popleft()
            members.append(pixel)
            x, y = pixel % width, pixel // width
            for dy in (-1, 0, 1):
                yy = y+dy
                if not 0 <= yy < height:continue
                for dx in (-1, 0, 1):
                    xx = x+dx
                    if (dx or dy) and 0 <= xx < width:
                        neighbor = yy*width+xx
                        if pending_pixels[neighbor]:
                            pending_pixels[neighbor] = 0
                            queue.append(neighbor)
        if len(members) > len(largest):largest = members
    if len(largest) < 1000:raise ValueError('Missing complete Mira drawing')
    mask = bytearray(width*height)
    for pixel in largest:mask[pixel] = 255
    result = image.copy()
    result.putalpha(Image.frombytes('L', image.size, bytes(mask)))
    return result


def build():
    specification = json.loads((SOURCE/'registration.json').read_text())
    source_path = SOURCE/specification['source']
    sources = {record['file']: Image.open(SOURCE/record['file']).convert('RGBA')
               for record in specification['sources']}
    # Transparent source RGB can contain arbitrary matte colors. Use only
    # visible pixels so those colors cannot displace Mira's dusty rose shirt.
    # One palette for the whole bank also keeps materials stable across poses.
    visible = [pixel[:3] for source in sources.values() for pixel in source.getdata()
               if pixel[3] >= 128]
    opaque_colors = Image.new('RGB', (len(visible), 1))
    opaque_colors.putdata(visible)
    palette = opaque_colors.quantize(colors=specification['palette_colors'],
                                     dither=Image.Dither.NONE)
    scale = specification['native_scale']
    canvas, anchor = specification['canvas'], specification['anchor']
    drawings, records = [], []
    for drawing in specification['drawings']:
        source = sources[drawing['source']]
        scale = drawing.get('native_scale', specification['native_scale'])
        left, top, width, height = drawing['source_rect']
        cell = _main_component(source.crop((left, top, left+width, top+height)))
        bounds = cell.getbbox()
        cutout = cell.crop(bounds)
        size = tuple(max(1, round(value*scale)) for value in cutout.size)
        cutout = cutout.resize(size, Image.Resampling.NEAREST)
        alpha = cutout.getchannel('A')
        cutout = cutout.convert('RGB').quantize(palette=palette,
            dither=Image.Dither.NONE).convert('RGBA')
        cutout.putalpha(alpha)
        foot = drawing['source_foot']
        position = [round(anchor[0]-(foot[0]-bounds[0])*scale),
                    round(anchor[1]-(foot[1]-bounds[1])*scale)]
        frame = Image.new('RGBA', canvas)
        frame.alpha_composite(cutout, position)
        box = frame.getbbox()
        if (box is None or box[0] <= 0 or box[1] <= 0
                or box[2] >= canvas[0] or box[3] >= canvas[1]):
            raise ValueError(f'Mira drawing is clipped: {drawing["source_cell"]}')
        anchors = {'floor': list(anchor)}
        anchors.update({name: [round(anchor[axis]+(point[axis]-foot[axis])*scale)
                              for axis in (0, 1)]
                        for name, point in drawing['anchors'].items()})
        record = dict(drawing, source_bounds=[left+bounds[0], top+bounds[1],
                                               left+bounds[2], top+bounds[3]],
                      source_sheet=(SOURCE/drawing['source']).relative_to(ROOT).as_posix(),
                      native_scale=scale, position=position, anchors=anchors)
        drawings.append(frame)
        records.append(record)
    if len({image.tobytes() for image in drawings}) != 82:
        raise ValueError('All 82 Mira drawings must remain visually distinct')
    OUTPUT.mkdir(parents=True, exist_ok=True)
    animations, names = {}, set()
    for state, (indices, durations, loop) in ANIMATIONS.items():
        frames = []
        for number, (index, duration) in enumerate(zip(indices, durations), 1):
            filename = f'{state}_{number:02}.png'
            names.add(filename)
            drawings[index].save(OUTPUT/filename, optimize=True)
            frames.append(dict(records[index], file=filename, duration_ms=duration))
        animations[state] = dict(loop=loop, frames=frames)
        if state in ('attack', 'rig_activation'):
            animations[state]['contact_ms'] = 400 if state == 'attack' else 500
        if state == 'attack':animations[state]['release_ms'] = 280
        if state in ('charged_bolt','impact_bolt','arc_discharge'):
            animations[state]['contact_ms'] = {'charged_bolt':650,'impact_bolt':400,'arc_discharge':650}[state]
        if state in ('bulwark','repair_pulse'):
            animations[state]['contact_ms'] = 620
    animations['bolt_shot'] = animations['attack']
    animations['flee'] = animations['walk']
    for filename in OUTPUT.glob('*.png'):
        if not filename.stem.startswith('world_') and filename.name not in names | {'spritesheet.png'}:
            filename.unlink()
    sheet = Image.new('RGBA', (canvas[0]*8, canvas[1]*11))
    for index, image in enumerate(drawings):
        sheet.alpha_composite(image, ((index % 8)*canvas[0], (index//8)*canvas[1]))
    sheet.save(OUTPUT/'spritesheet.png', optimize=True)
    metadata = dict(version=1, actor='mira', canvas=canvas, anchor=anchor,
        facing='left', source_sheet=source_path.relative_to(ROOT).as_posix(),
        source_sha256=hashlib.sha256(source_path.read_bytes()).hexdigest(),
        source_sheets=[dict(path=(SOURCE/record['file']).relative_to(ROOT).as_posix(),
            sha256=hashlib.sha256((SOURCE/record['file']).read_bytes()).hexdigest(),grid=record['grid'])
            for record in specification['sources']],
        sheet='spritesheet.png', sheet_grid=[8,11], source_grid=[6,7], authored_frames=82,
        extraction=f'largest connected authored alpha; binary alpha; fixed nearest-neighbor native scale; shared opaque-only {specification["palette_colors"]}-color palette; explicit anatomical floor',
        registration=(SOURCE/'registration.json').relative_to(ROOT).as_posix(),
        native_scale=scale, animations=animations)
    (OUTPUT/'animation.json').write_text(json.dumps(metadata, indent=2)+'\n')
    return metadata


if __name__ == '__main__':
    print(json.dumps({'actor': 'mira', 'authored_frames': build()['authored_frames']}))
