"""Export the wearable Engineer and Ridgeback Tusker combat banks."""
from __future__ import annotations

from collections import deque
import hashlib
import json
from pathlib import Path

from PIL import Image

if __package__:
    from .build_mira_combat import build as build_mira
else:
    from build_mira_combat import build as build_mira


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/combat'
OUTPUT = ROOT/'assets/combat'
ACTORS = {
    'ridgeback_tusker': {'source': 'mq02_tusker_generated_sheet.png',
                        'canvas': (96, 72), 'anchor': (48, 62),
                        'scale': .205, 'facing': 'right',
                        'animations': {
                            'idle': ([0, 1, 2, 3], [240]*4, True),
                            'attack': ([4, 5, 6], [250, 350, 300], False),
                            'prepare': ([7, 8], [400, 400], True),
                            'charge': ([9, 10, 11], [250, 400, 350], False),
                            'hurt': ([12, 13], [180, 240], False),
                            'defeat': ([14, 15], [300, 500], False),
                        }},
}


def authored_components(image):
    """Find the sixteen complete silhouettes using binary-alpha connectivity."""
    width, height = image.size
    pixels = bytearray(value >= 128 for value in image.getchannel('A').tobytes())
    components = []
    for start in range(width*height):
        if not pixels[start]:continue
        pixels[start] = 0
        pending, members = deque([start]), []
        minimum_x = maximum_x = start % width
        minimum_y = maximum_y = start // width
        total_x = total_y = 0
        while pending:
            pixel = pending.popleft()
            x, y = pixel % width, pixel // width
            members.append(pixel)
            minimum_x, maximum_x = min(minimum_x, x), max(maximum_x, x)
            minimum_y, maximum_y = min(minimum_y, y), max(maximum_y, y)
            total_x += x; total_y += y
            for dy in (-1, 0, 1):
                next_y = y+dy
                if not 0 <= next_y < height:continue
                for dx in (-1, 0, 1):
                    next_x = x+dx
                    if (dx or dy) and 0 <= next_x < width:
                        neighbor = next_y*width+next_x
                        if pixels[neighbor]:
                            pixels[neighbor] = 0
                            pending.append(neighbor)
        if len(members) < 500:continue
        count = len(members)
        center = total_x/count, total_y/count
        cell = min(3, int(center[1]*4/height))*4+min(3, int(center[0]*4/width))
        bounds = minimum_x, minimum_y, maximum_x+1, maximum_y+1
        components.append((cell, bounds, center, members))
    if len(components) != 16 or len({record[0] for record in components}) != 16:
        raise ValueError('Source must contain one complete connected sprite per cell')
    return sorted(components)


def exported_frames(source, actor):
    settings = ACTORS[actor]
    with Image.open(source) as original:image = original.convert('RGBA')
    frames, records = [], []
    for cell, bounds, center, members in authored_components(image):
        left, top, right, bottom = bounds
        cutout = image.crop(bounds)
        mask = bytearray((right-left)*(bottom-top))
        for pixel in members:
            x, y = pixel % image.width-left, pixel // image.width-top
            mask[y*(right-left)+x] = 255
        cutout.putalpha(Image.frombytes('L', cutout.size, bytes(mask)))
        scale = settings['scale']
        size = max(1, round(cutout.width*scale)), max(1, round(cutout.height*scale))
        cutout = cutout.resize(size, Image.Resampling.NEAREST)
        anchor = settings['anchor']
        position = round(anchor[0]-(center[0]-left)*scale), anchor[1]-cutout.height
        frame = Image.new('RGBA', settings['canvas'])
        frame.alpha_composite(cutout, position)
        if frame.getchannel('A').getbbox() is None:
            raise ValueError('Exported frame is empty')
        box = frame.getbbox()
        if box[0] <= 0 or box[1] <= 0 or box[2] >= frame.width or box[3] >= frame.height:
            raise ValueError(f'Exported frame is clipped: {actor}:{cell}')
        frames.append(frame)
        records.append({'source_cell': cell, 'source_bounds': list(bounds)})
    return frames, records


def build_actor(actor):
    if actor == 'mira':
        return build_mira()
    settings = ACTORS[actor]
    source = SOURCE/settings['source']
    directory = OUTPUT/actor
    directory.mkdir(parents=True, exist_ok=True)
    frames, records = exported_frames(source, actor)
    animations = {}
    for state, (indices, durations, loop) in settings['animations'].items():
        entries = []
        for number, (index, duration) in enumerate(zip(indices, durations), 1):
            filename = f'{state}_{number:02d}.png'
            frames[index].save(directory/filename, optimize=True)
            entries.append({'file': filename, 'duration_ms': duration, **records[index]})
        animations[state] = {'loop': loop, 'frames': entries}
    aliases = {'tusk_strike': 'attack', 'prepare_charge': 'prepare', 'tusker_charge': 'charge'}
    for alias, state in aliases.items():animations[alias] = animations[state]
    size = settings['canvas']
    sheet = Image.new('RGBA', (size[0]*4, size[1]*4))
    for index, frame in enumerate(frames):
        sheet.alpha_composite(frame, ((index % 4)*size[0], (index // 4)*size[1]))
    sheet.save(directory/'spritesheet.png', optimize=True)
    data = {'version': 1, 'actor': actor, 'canvas': list(size),
            'anchor': list(settings['anchor']), 'facing': settings['facing'],
            'source_sheet': source.relative_to(ROOT).as_posix(),
            'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
            'sheet': 'spritesheet.png', 'extraction': 'connected-alpha sprites; fixed native scale',
            'native_scale': settings['scale'], 'animations': animations}
    (directory/'animation.json').write_text(json.dumps(data, indent=2)+'\n')
    return data


def main():
    build_mira()
    for actor in ACTORS:build_actor(actor)
    print(json.dumps({'actors': ['mira', *ACTORS],
                      'source_cells_per_actor': {'mira': 82, 'ridgeback_tusker': 16}}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
