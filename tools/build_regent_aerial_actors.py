"""Export authored bird and overhead convoy art for Aldric's aerial opening.

The source sheets remain unchanged.  Alpha components isolate whole subjects
where feather tips cross nominal grid boundaries; crops, registration and
uniform nearest resizing are the only image operations used by this exporter.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path

os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import pygame
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/cinematics/regent_aerial/actors'
TARGET = ROOT/'assets/story/regent_aerial/actors'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(image):
    stream = io.BytesIO()
    image.save(stream, format='PNG', optimize=True)
    return stream.getvalue()


def json_bytes(value):
    return (json.dumps(value, indent=2)+'\n').encode()


def subjects(path, expected, minimum):
    image = Image.open(path).convert('RGBA')
    surface = pygame.image.frombytes(image.tobytes(), image.size, 'RGBA')
    mask = pygame.mask.from_surface(surface, 127)
    components = sorted(mask.connected_components(minimum),
                        key=lambda item: item.count(), reverse=True)
    if len(components) != expected:
        raise ValueError(f'{path.name}: expected {expected} complete subjects, got {len(components)}')
    components.sort(key=lambda item: (
        item.get_bounding_rects()[0].centery//(image.height/2),
        item.get_bounding_rects()[0].centerx))
    result = []
    for component in components:
        bounds = component.get_bounding_rects()[0]
        alpha_surface = component.to_surface(setcolor=(255,255,255,255),
                                             unsetcolor=(0,0,0,0))
        alpha_image = Image.frombytes('RGBA', image.size,
                                     pygame.image.tobytes(alpha_surface, 'RGBA')).getchannel('A')
        isolated = image.copy()
        isolated.putalpha(alpha_image)
        result.append((isolated, component, bounds))
    return result


def registered(image, bounds, scale, canvas, source_anchor, target_anchor):
    crop = image.crop(tuple(bounds))
    crop = crop.resize((round(crop.width*scale), round(crop.height*scale)),
                       Image.Resampling.NEAREST)
    offset = (round(target_anchor[0]-(source_anchor[0]-bounds[0])*scale),
              round(target_anchor[1]-(source_anchor[1]-bounds[1])*scale))
    if (offset[0] < 0 or offset[1] < 0
            or offset[0]+crop.width > canvas[0] or offset[1]+crop.height > canvas[1]):
        raise ValueError(f'Subject exceeds registered {canvas} canvas: {offset}, {crop.size}')
    result = Image.new('RGBA', canvas)
    result.alpha_composite(crop, offset)
    return result


def build():
    outputs = {}
    registrations = {}
    bird = subjects(SOURCE/'bird_generated.png', 8, 256)
    bird_scale = 80/max(bounds.width for _,_,bounds in bird)
    bank_anchors = ((1130,666), (1540,670))
    bird_files = []
    for index,(image,component,bounds) in enumerate(bird):
        if index < 6:
            tail = [x for y in range(bounds.bottom-8,bounds.bottom)
                    for x in range(bounds.left,bounds.right) if component.get_at((x,y))]
            center_x = sum(tail)/len(tail)
            body = [y for y in range(bounds.top,bounds.bottom)
                    for x in range(round(center_x)-8,round(center_x)+9)
                    if component.get_at((x,y))]
            anchor = (center_x,(min(body)+bounds.bottom)/2)
            name = f'flap_{index}.png'
        else:
            anchor = bank_anchors[index-6]
            name = 'bank_left.png' if index == 6 else 'bank_right.png'
        sprite = registered(image, (bounds.left,bounds.top,bounds.right,bounds.bottom),
                            bird_scale, (96,96), anchor, (48,48))
        outputs['bird/'+name] = encoded(sprite)
        bird_files.append(name)
        registrations['bird/'+name] = {'source_bounds':list(bounds),
            'source_body_anchor':[round(n,3) for n in anchor], 'scale':round(bird_scale,8)}
    durations = (80,75,95,75,75,80)
    outputs['bird/animation.json'] = json_bytes({
        'version':1, 'canvas':[96,96], 'anchor':[48,48], 'facing':'north',
        'poses':{'glide_north':'flap_2.png', 'bank_left_north':'bank_left.png',
                 'bank_right_north':'bank_right.png'},
        'loops':{'flap_north':[{'file':name,'duration_ms':duration}
                              for name,duration in zip(bird_files[:6],durations)]},
        'source':'imagegen-authored kestrel; dorsal six-frame wingbeat and bank poses',
        'registration':'Shared whole-sheet scale and torso anchors; wings never cropped to a uniform grid.'})

    convoy = subjects(SOURCE/'convoy_generated.png', 6, 512)
    poses = {name:{} for name in ('aldric','guard','caravan')}
    for index,(image,_,bounds) in enumerate(convoy):
        identifier = ('aldric','guard','caravan')[index%3]
        pose = 'overhead' if index < 3 else 'oblique'
        if identifier == 'caravan':
            canvas, target_anchor = (160,160), (80,128)
            scale = 120/bounds.height if pose == 'overhead' else 132/bounds.width
        else:
            canvas, target_anchor = (48,64), (24,56)
            scale = .175 if pose == 'overhead' else .18
        anchor = (bounds.centerx,bounds.bottom)
        sprite = registered(image, (bounds.left,bounds.top,bounds.right,bounds.bottom),
                            scale, canvas, anchor, target_anchor)
        filename = identifier+'/'+pose+'.png'
        outputs[filename] = encoded(sprite)
        poses[identifier][pose] = pose+'.png'
        registrations[filename] = {'source_bounds':list(bounds),
            'source_ground_anchor':list(anchor), 'scale':round(scale,8)}
    for identifier,actor_poses in poses.items():
        vehicle = identifier == 'caravan'
        record = {'version':1, 'canvas':[160,160] if vehicle else [48,64],
            'anchor':[80,128] if vehicle else [24,56], 'poses':actor_poses, 'loops':{},
            'source':'imagegen-authored overhead and high-oblique cinematic subjects',
            'overhead_facing':'north', 'oblique_facing':'northwest'}
        if vehicle:
            record['driver_baked_poses'] = ['overhead','oblique']
            record['driver_count'] = 1
        outputs[identifier+'/animation.json'] = json_bytes(record)
    outputs['manifest.json'] = json_bytes({'version':1,'actors':{
        name:name+'/animation.json' for name in ('bird','aldric','guard','caravan')}})
    outputs['provenance.json'] = json_bytes({'version':1,
        'exporter':'tools/build_regent_aerial_actors.py',
        'exporter_sha256':sha(Path(__file__).read_bytes()),
        'prompts_sha256':sha((SOURCE/'prompts.json').read_bytes()),
        'sources':{path.name:sha(path.read_bytes()) for path in sorted(SOURCE.glob('*.png'))},
        'registrations':registrations,
        'exports':{name:sha(data) for name,data in outputs.items()},
        'notes':['Original generations and exact prompts retained without repainting.',
                 'Binary alpha component isolation removes low-alpha matte and keeps neighboring birds out of overlapping crop rectangles.',
                 'All six flap frames share scale and align the head/tail body axis; banking frames align the torso pivot.',
                 'Overhead humans are foreshortened, and the overhead vehicle exposes its roof and complete ground footprint.',
                 'Both caravan views include exactly one seated driver; no separate aerial driver is attached.',
                 'Existing ground cinematic actor exports remain unchanged.']})
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    outputs = build()
    if args.check:
        current = {str(path.relative_to(TARGET)) for path in TARGET.rglob('*') if path.is_file()}
        if current != set(outputs):
            raise SystemExit('Unexpected or missing aerial actor export files')
        for name,data in outputs.items():
            if (TARGET/name).read_bytes() != data:
                raise SystemExit('Aerial actor export differs: '+name)
        print(f'Verified {len(outputs)} registered aerial actor exports')
    else:
        for name,data in outputs.items():
            path = TARGET/name
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(data)
        print(f'Exported {len(outputs)} registered aerial actor files')


if __name__ == '__main__':
    main()
