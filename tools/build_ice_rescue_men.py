"""Mechanically register authored Caelan/Lucan action and angle drawings.

Generated source sheets remain unchanged. No joint deformation or synthesized
in-between poses are performed: every output comes from its own authored cell.
"""
from __future__ import annotations
import hashlib
from collections import deque
import json
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/cinematics/ice_reaper_rescue/men'
TARGET = ROOT/'assets/story/ice_reaper_rescue/actors'
CANVAS = (128, 128)
ANCHOR = (64, 116)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cells(path, columns, rows):
    with Image.open(path) as source:
        source = source.convert('RGBA')
        output = []
        for row in range(rows):
            for column in range(columns):
                box = (round(column*source.width/columns), round(row*source.height/rows),
                       round((column+1)*source.width/columns), round((row+1)*source.height/rows))
                image = source.crop(box)
                image.putalpha(image.getchannel('A').point(lambda a: 255 if a >= 128 else 0))
                # Remove only detached, flat neutral ground-shadow strips; the
                # stage owns contact shadows. Character/weapon pixels stay intact.
                px = image.load()
                seen = set()
                for sy in range(image.height):
                    for sx in range(image.width):
                        if (sx, sy) in seen or not px[sx, sy][3]:
                            continue
                        todo = deque([(sx, sy)])
                        seen.add((sx, sy))
                        component = []
                        while todo:
                            x, y = todo.popleft()
                            component.append((x, y))
                            for nx, ny in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                                if 0 <= nx < image.width and 0 <= ny < image.height and (nx,ny) not in seen and px[nx,ny][3]:
                                    seen.add((nx,ny)); todo.append((nx,ny))
                        xs, ys = zip(*component)
                        if max(xs)-min(xs) > 20 and max(ys)-min(ys) < 5:
                            neutral = sum(max(px[x,y][:3])-min(px[x,y][:3]) < 25 for x,y in component)/len(component)
                            if neutral > .9:
                                for x,y in component:
                                    px[x,y] = (*px[x,y][:3], 0)
                output.append((image, box))
        return output


def register(image, scale):
    bounds = image.getbbox()
    if bounds is None:
        raise ValueError('Empty authored action cell')
    # Median of the bottom opaque band registers the feet rather than centering
    # the weapon. Use opaque non-fire pixels so sword embers cannot move actors.
    pixels = image.load()
    candidates = []
    for y in range(max(bounds[1], bounds[3]-max(20, round((bounds[3]-bounds[1])*.22))), bounds[3]):
        for x in range(bounds[0], bounds[2]):
            r, g, b, a = pixels[x, y]
            if a and not (r > 180 and r > g*1.3 and b < 110):
                candidates.append(x)
    foot_x = (min(candidates)+max(candidates))/2 if candidates else (bounds[0]+bounds[2])/2
    # A broad slash can reach farther than the planted foot; retain all authored
    # pixels by moving registration inside its safe horizontal interval.
    foot_x = max(bounds[2]-(CANVAS[0]-ANCHOR[0]-1)/scale,
                 min(bounds[0]+(ANCHOR[0]-1)/scale, foot_x))
    resized = image.resize((round(image.width*scale), round(image.height*scale)), Image.Resampling.NEAREST)
    x = round(ANCHOR[0]-foot_x*scale)
    y = round(ANCHOR[1]-bounds[3]*scale)
    drawn = resized.getbbox()
    if drawn and (drawn[0]+x < 0 or drawn[2]+x > CANVAS[0] or drawn[1]+y < 0 or drawn[3]+y > CANVAS[1]):
        raise ValueError(f'Action cell would clip at scale {scale}: {bounds}, anchor={foot_x}')
    frame = Image.new('RGBA', CANVAS)
    frame.alpha_composite(resized, (x, y))
    return frame, {'source_bounds': list(bounds), 'source_foot_x': foot_x,
                   'scale': scale, 'registration': [x,y]}


def build():
    definitions = {
        'caelan': [('ready', 4, 180), ('dash', 6, 80), ('slash', 10, 200), ('land', 4, 100)],
        'lucan': [('dash', 6, 80), ('brace', 8, 180), ('impact', 6, 100),
                  ('ready_rear', 1, 250), ('brace_rear', 1, 250), ('brace_front', 1, 250), ('ready_side', 1, 250)],
    }
    report = {'version': 1, 'method': 'Authored imagegen cell extraction, alpha threshold, nearest scaling and foot registration only', 'actors': {}}
    for actor, actions in definitions.items():
        output = TARGET/actor
        output.mkdir(parents=True, exist_ok=True)
        source_path = SOURCE/f'{actor}_actions_generated.png'
        authored = cells(source_path, 6, 4)
        manifest = {'version': 1, 'actor': actor, 'canvas': list(CANVAS), 'anchor': list(ANCHOR),
                    'standing_height': 80, 'animations': {}, 'source': source_path.relative_to(ROOT).as_posix()}
        offset = 0
        registrations = []
        for action, count, duration in actions:
            sequence = []
            for index in range(count):
                cell, box = authored[offset]
                frame, registration = register(cell, .38)
                filename = f'{action}_{index+1:02}.png'
                frame.save(output/filename, optimize=True)
                sequence.append({'file': filename, 'duration_ms': duration})
                registrations.append(dict(action=action, index=index, source_cell=offset,
                                          source_box=list(box), **registration))
                offset += 1
            manifest['animations'][action] = {'loop': action == 'ready', 'frames': sequence}
        if actor == 'caelan':
            angle_path = SOURCE/'caelan_angles_generated.png'
            names = ['ready_rear', 'ready_rear_threequarter', 'slash_rear', 'land_rear',
                     'dash_rear', 'dash_front', 'slash_side', 'land_side']
            for action, (cell, box) in zip(names, cells(angle_path, 4, 2)):
                frame, registration = register(cell, .205)
                filename=f'{action}_01.png'
                frame.save(output/filename, optimize=True)
                manifest['animations'][action] = {'loop': False, 'frames': [{'file': filename, 'duration_ms': 250}]}
                registrations.append(dict(action=action, source=angle_path.name, source_box=list(box), **registration))
        (output/'animation.json').write_text(json.dumps(manifest, indent=2)+'\n')
        report['actors'][actor] = {'source_sha256': digest(source_path), 'frames': registrations}
    report['angle_source_sha256'] = digest(SOURCE/'caelan_angles_generated.png')
    (SOURCE/'provenance.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({actor: sum(count for _, count, _ in definitions[actor]) for actor in definitions}))


if __name__ == '__main__':
    build()
