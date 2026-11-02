"""Extract generated Mira/Rivet art without drawing or repainting sprite pixels.

The retained imagegen atlases use a four-column logical grid. Connected alpha
components keep each complete authored silhouette intact even when it extends
across an approximate grid boundary. Small disconnected steam/spark components
are registered with the same source cell. One fixed nearest-neighbor scale is
used per actor, then each cutout is registered to its ground anchor.
"""
from __future__ import annotations

from collections import deque
import hashlib
import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'assets/source/combat/machinist'
OUTPUT = ROOT / 'assets/combat'
ACTORS = {
    'mira': {
        'source': 'mira_bolt_launcher_generated_sheet.png',
        'grid': (4, 5), 'canvas': (64, 64), 'anchor': (32, 54),
        'scale': .146, 'facing': 'left', 'count': 19,
        'animations': {
            'idle': ([0, 1], [260, 260], True),
            'attack': ([2, 3, 4], [200, 280, 320], False),
            'guard': ([5, 6], [240, 240], True),
            'hurt': ([7, 8], [160, 240], False),
            'victory': ([9, 10], [340, 340], True),
            'defeat': ([11, 12], [260, 420], False),
            'walk': ([13, 14, 15], [140, 140, 140], True),
            'overclock': ([16, 17, 18], [300, 300, 300], False),
        },
        'aliases': {'bolt_shot': 'attack', 'flee': 'walk'},
        'contacts': {'attack': 400, 'overclock': 500},
    },
    'rivet': {
        'source': 'rivet_generated_sheet.png',
        'grid': (4, 4), 'canvas': (32, 32), 'anchor': (16, 28),
        'scale': .076, 'facing': 'left', 'count': 16,
        'animations': {
            'idle': ([0, 1, 2, 3], [180, 220, 180, 220], True),
            'deploy': ([4, 5], [260, 340], False),
            'attack': ([6, 7, 8], [250, 250, 300], False),
            'overclock': ([9, 10, 11], [110, 110, 110], True),
            'victory': ([12, 13], [260, 260], True),
            'suspend': ([14, 15], [240, 360], False),
        },
        'aliases': {'piston_jab': 'attack'},
        'contacts': {'attack': 400},
    },
}


def source_sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def authored_cells(image, grid):
    """Group complete binary-alpha components into their logical source cells."""
    width, height = image.size
    columns, rows = grid
    remaining = bytearray(value >= 128 for value in image.getchannel('A').tobytes())
    groups = {index: [] for index in range(columns * rows)}
    for start in range(width * height):
        if not remaining[start]:
            continue
        remaining[start] = 0
        pending, members = deque([start]), []
        total_x = total_y = 0
        while pending:
            pixel = pending.popleft()
            x, y = pixel % width, pixel // width
            members.append(pixel)
            total_x += x
            total_y += y
            for dy in (-1, 0, 1):
                next_y = y + dy
                if not 0 <= next_y < height:
                    continue
                for dx in (-1, 0, 1):
                    next_x = x + dx
                    if (dx or dy) and 0 <= next_x < width:
                        neighbor = next_y * width + next_x
                        if remaining[neighbor]:
                            remaining[neighbor] = 0
                            pending.append(neighbor)
        # Discard detached subpixel antialias specks, retain authored effects.
        if len(members) < 16:
            continue
        center_x, center_y = total_x / len(members), total_y / len(members)
        column = min(columns - 1, int(center_x * columns / width))
        row = min(rows - 1, int(center_y * rows / height))
        groups[row * columns + column].extend(members)
    records = []
    for index, members in groups.items():
        if len(members) < 1000:
            raise ValueError(f'Missing authored source cell {index}')
        xs, ys = [p % width for p in members], [p // width for p in members]
        bounds = min(xs), min(ys), max(xs) + 1, max(ys) + 1
        left, top, right, bottom = bounds
        cutout = image.crop(bounds)
        mask = bytearray((right - left) * (bottom - top))
        for pixel in members:
            x, y = pixel % width - left, pixel // width - top
            mask[y * (right - left) + x] = 255
        cutout.putalpha(Image.frombytes('L', cutout.size, bytes(mask)))
        center = sum(xs) / len(xs), sum(ys) / len(ys)
        records.append((cutout, center, {'source_cell': index,
                                       'source_bounds': list(bounds)}))
    return records


def exported_frames(actor):
    settings = ACTORS[actor]
    source = SOURCE / settings['source']
    with Image.open(source) as original:
        cells = authored_cells(original.convert('RGBA'), settings['grid'])
    frames, records = [], []
    for cutout, center, record in cells[:settings['count']]:
        scale = settings['scale']
        size = max(1, round(cutout.width * scale)), max(1, round(cutout.height * scale))
        cutout = cutout.resize(size, Image.Resampling.NEAREST)
        position = (round(settings['anchor'][0] -
                          (center[0] - record['source_bounds'][0]) * scale),
                    settings['anchor'][1] - cutout.height)
        frame = Image.new('RGBA', settings['canvas'])
        frame.alpha_composite(cutout, position)
        box = frame.getbbox()
        if box is None or box[0] <= 0 or box[1] <= 0 or box[2] >= frame.width or box[3] >= frame.height:
            raise ValueError(f'Exported frame is empty or clipped: {actor}:{record["source_cell"]}')
        frames.append(frame)
        records.append({**record, 'position': list(position)})
    if len({frame.tobytes() for frame in frames}) != len(frames):
        raise ValueError(f'Authored poses must remain visually distinct: {actor}')
    return frames, records, cells


def build_actor(actor):
    settings = ACTORS[actor]
    source = SOURCE / settings['source']
    directory = OUTPUT / actor
    directory.mkdir(parents=True, exist_ok=True)
    frames, records, cells = exported_frames(actor)
    animations = {}
    exported_names = set()
    for state, (indices, durations, loop) in settings['animations'].items():
        entries = []
        for number, (index, duration) in enumerate(zip(indices, durations), 1):
            filename = f'{state}_{number:02d}.png'
            frames[index].save(directory / filename, optimize=True)
            exported_names.add(filename)
            entries.append({'file': filename, 'duration_ms': duration, **records[index]})
        animation = {'loop': loop, 'frames': entries}
        if state in settings['contacts']:
            animation['contact_ms'] = settings['contacts'][state]
        animations[state] = animation
    for alias, state in settings['aliases'].items():
        animations[alias] = animations[state]
    # Remove obsolete actor frames/props so the runtime folder is reviewable.
    for path in directory.glob('*.png'):
        if path.stem.startswith('world_'):
            if path.stem == 'world_spear':
                path.unlink()
            continue
        if path.name not in exported_names and path.name != 'spritesheet.png':
            path.unlink()
    old_spear_metadata = directory / 'world_spear.json'
    if old_spear_metadata.exists():
        old_spear_metadata.unlink()
    columns = settings['grid'][0]
    rows = (len(frames) + columns - 1) // columns
    width, height = settings['canvas']
    sheet = Image.new('RGBA', (width * columns, height * rows))
    for index, frame in enumerate(frames):
        sheet.alpha_composite(frame, ((index % columns) * width, (index // columns) * height))
    sheet.save(directory / 'spritesheet.png', optimize=True)
    metadata = {
        'version': 1, 'actor': actor, 'canvas': list(settings['canvas']),
        'anchor': list(settings['anchor']), 'facing': settings['facing'],
        'source_sheet': source.relative_to(ROOT).as_posix(),
        'source_sha256': source_sha256(source), 'sheet': 'spritesheet.png',
        'source_grid': list(settings['grid']), 'authored_frames': len(frames),
        'extraction': 'connected-alpha source cells; binary alpha; fixed nearest-neighbor native scale',
        'native_scale': settings['scale'], 'animations': animations,
    }
    (directory / 'animation.json').write_text(json.dumps(metadata, indent=2) + '\n')
    if actor == 'mira':
        build_world_launcher(cells[19], source)
    return metadata


def build_world_launcher(cell, source):
    """Extract the generated isolated launcher; preserve its authored aspect."""
    cutout, _, record = cell
    scale = 21 / cutout.width
    cutout = cutout.resize((21, max(1, round(cutout.height * scale))), Image.Resampling.NEAREST)
    canvas = Image.new('RGBA', (24, 20))
    position = 1, 3
    canvas.alpha_composite(cutout, position)
    bounds = canvas.getbbox()
    if bounds is None or bounds[0] <= 0 or bounds[1] <= 0 or bounds[2] >= 24 or bounds[3] >= 20:
        raise ValueError('World launcher must be complete and unclipped')
    directory = OUTPUT / 'mira'
    canvas.save(directory / 'world_bolt_launcher.png', optimize=True)
    metadata = {
        'canvas': [24, 20], 'hand_anchor': [18, 12],
        'holster_anchor': [18, 9], 'muzzle': [2, 7],
        'facing': 'left', 'orientation': 'barrel_left',
        'source': source.relative_to(ROOT).as_posix(),
        'source_sha256': source_sha256(source), **record,
        'position': list(position), 'native_scale': scale,
    }
    (directory / 'world_bolt_launcher.json').write_text(json.dumps(metadata, indent=2) + '\n')


def main():
    result = {actor: build_actor(actor)['authored_frames'] for actor in ACTORS}
    print(json.dumps({'actors': result}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
