"""Export source-authored companion side/rear idles on the approved game scale.

All three views of an actor share one exact affine nearest-neighbor sampling
grid and the approved front-idle palette. Body centers and floor points are
authored in source.json; equipment never recenters or shrinks the character.
The approved front, front walk, combat and cinematic PNGs remain read-only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import statistics

from PIL import Image, ImageDraw

from build_companion_front_walks import (approved_palette, export_frame, font,
                                         pixels, write_json)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/companions'
REVIEW = ROOT/'docs/reviews/companion_directional_idles'
ACTORS = {'lucan': 'Lucan Rooke', 'rhea': 'Rhea Sorel', 'edran': 'Edran Hale'}
DIRECTIONS = ('left', 'right', 'back')
ORDER = ('front',)+DIRECTIONS
LABELS = {'front': 'Front — approved', 'left': 'Left — review',
          'right': 'Right — review', 'back': 'Rear — review'}
FRAME_SIZE = (24, 36)
PAPER = (232, 237, 242)
INK = (38, 52, 62)
MUTED = (82, 97, 108)
GROUND = (199, 208, 213)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def capture_protected(snapshot=None):
    if snapshot is not None:
        hashes = json.loads(Path(snapshot).read_text())
        verify_protected(hashes)
        return hashes
    paths = []
    for actor in ACTORS:
        paths.append(ROOT/f'assets/characters/{actor}/idle_front.png')
        for directory in (ROOT/f'assets/characters/{actor}/walk_front',
                          ROOT/f'assets/combat/{actor}',
                          ROOT/f'assets/cinematics/companions/{actor}'):
            if directory.exists():paths.extend(directory.glob('*.png'))
    return {path.relative_to(ROOT).as_posix(): sha256(path) for path in sorted(set(paths))}


def verify_protected(hashes):
    changed = [name for name, digest in hashes.items()
               if not (ROOT/name).is_file() or sha256(ROOT/name) != digest]
    if changed:raise ValueError('Approved assets changed: '+', '.join(changed))


def source_path(directory, recipe):
    supplied = recipe.get('source_file', recipe.get('source_sheet'))
    if supplied:
        path = Path(supplied)
        return path if path.is_absolute() else directory/path
    for name in ('idle_sheet.png', 'directional_idles.png', 'design_sheet.png', 'sheet.png'):
        if (directory/name).is_file():return directory/name
    raise FileNotFoundError(f'No directional-idle source sheet in {directory}')


def prepare_sources(sheet, recipe):
    export = recipe.get('export', {})
    entries = export.get('poses', recipe.get('poses', recipe.get('panels', {})))
    if isinstance(entries, list):
        entries = {entry.get('direction', entry.get('id', DIRECTIONS[index])): entry
                   for index, entry in enumerate(entries)}
    prepared = {}
    for index, direction in enumerate(DIRECTIONS):
        settings = entries.get(direction, {})
        if ('body_center_x' not in settings or 'ground_y' not in settings or
                not any(key in settings for key in ('body_bounds', 'source_body_bounds'))):
            raise ValueError(f'{direction}: source recipe must identify body bounds, body center and floor')
        panel = tuple(settings.get('source_bounds', settings.get('source_cell',
                      [round(index*sheet.width/3), 0,
                       round((index+1)*sheet.width/3), sheet.height])))
        crop = sheet.crop(panel)
        crop.putalpha(crop.getchannel('A').point(lambda alpha: 255 if alpha >= 128 else 0))
        occupied = crop.getbbox()
        if occupied is None:raise ValueError(f'Empty source view: {direction}')
        bounds = (panel[0]+occupied[0], panel[1]+occupied[1],
                  panel[0]+occupied[2], panel[1]+occupied[3])
        body = tuple(settings.get('body_bounds', settings.get('source_body_bounds', bounds)))
        if body[3] <= body[1] or body[2] <= body[0]:raise ValueError(f'Invalid body bounds: {direction}')
        prepared[direction] = {'image': crop.crop(occupied), 'panel': panel,
                               'bounds': bounds, 'body_bounds': body,
                               'body_center_x': settings.get('body_center_x', (body[0]+body[2]-1)/2),
                               'ground_y': settings.get('ground_y', body[3]-1),
                               'native_offset': (0, 0)}
        if settings.get('anchor') is not None:
            prepared[direction]['anchor'] = settings['anchor']
    return export, prepared


def build_actor(actor):
    directory = SOURCE/actor/'directional_idles'
    recipe_path = directory/'source.json'
    recipe = json.loads(recipe_path.read_text())
    original = source_path(directory, recipe)
    sheet = Image.open(original).convert('RGBA')
    destination = ROOT/f'assets/characters/{actor}'
    front_path = destination/'idle_front.png'
    front = Image.open(front_path).convert('RGBA')
    front_meta = json.loads((destination/'idle_front.json').read_text())
    palette = approved_palette(front)
    export, prepared = prepare_sources(sheet, recipe)
    anchor = tuple(export.get('anchor', front_meta.get('foot_anchor', front_meta.get('anchor', (12, 34)))))
    if anchor[1] != 34:raise ValueError(f'{actor}: native floor must remain 34')
    target_height = export.get('target_body_height', front.getbbox()[3]-front.getbbox()[1])
    source_heights = [pose['body_bounds'][3]-pose['body_bounds'][1] for pose in prepared.values()]
    scale = export.get('scale', export.get('native_scale', target_height/statistics.median(source_heights)))
    phase = tuple(export.get('sampling_phase', (.5, .5)))
    if scale <= 0:raise ValueError(f'{actor}: invalid common scale')
    poses = {'front': front};records = {}
    anchors = {'front': tuple(front_meta.get('foot_anchor', front_meta.get('anchor', (12, 34))))}
    for direction, source in prepared.items():
        # export_frame detects sampled pixels beyond the native canvas and fails;
        # this builder deliberately does not reduce body scale to fit equipment.
        pose_anchor = tuple(source.get('anchor', anchor))
        if pose_anchor[1] != 34:raise ValueError(f'{actor}:{direction} floor must remain 34')
        frame, geometry = export_frame(source, scale, pose_anchor, palette, phase)
        if frame.getbbox()[3] != 35:
            raise ValueError(f'{actor}:{direction} has a floating/below-floor foot: {frame.getbbox()}')
        path = destination/f'idle_{direction}.png'
        frame.save(path, optimize=True)
        metadata = {'version': 1, 'actor': actor, 'display_name': ACTORS[actor],
                    'status': 'review', 'design_status': 'review', 'facing': direction,
                    'animation': 'idle.'+direction, 'authored_pose_count': 1,
                    'image': path.name, 'canvas': list(FRAME_SIZE), 'frame_size': list(FRAME_SIZE),
                    'anchor': list(pose_anchor), 'foot_anchor': list(pose_anchor),
                    'source': original.relative_to(ROOT).as_posix(), 'source_sha256': sha256(original),
                    'source_recipe': recipe_path.relative_to(ROOT).as_posix(),
                    'source_recipe_sha256': sha256(recipe_path),
                    'palette_source': front_path.relative_to(ROOT).as_posix(),
                    'palette_source_sha256': sha256(front_path),
                    'palette': [list(color) for color in palette],
                    'common_uniform_scale': scale, 'common_sampling_phase': list(phase),
                    'sampling': 'one exact affine nearest-neighbor grid across left/right/back',
                    'registration': 'authored body center and floor; equipment does not recenter the actor',
                    'extraction': geometry}
        metadata_path = destination/f'idle_{direction}.json'
        write_json(metadata_path, metadata)
        poses[direction] = frame
        anchors[direction] = pose_anchor
        records[direction] = {**metadata, 'image': path.relative_to(ROOT).as_posix(),
                              'metadata': metadata_path.relative_to(ROOT).as_posix(),
                              'sha256': sha256(path)}
    atlas = Image.new('RGBA', (96, 36))
    frame_records = []
    for index, direction in enumerate(ORDER):
        atlas.alpha_composite(poses[direction], (index*24, 0))
        frame_records.append({'direction': direction, 'file': f'idle_{direction}.png',
                              'rect': [index*24, 0, 24, 36], 'foot_anchor': list(anchors[direction]),
                              'status': 'approved' if direction == 'front' else 'review'})
    atlas.save(destination/'idle_directions.png', optimize=True)
    write_json(destination/'idle_directions.json',
               {'version': 1, 'actor': actor, 'display_name': ACTORS[actor], 'status': 'review',
                'image': 'idle_directions.png', 'frame_size': list(FRAME_SIZE),
                'foot_anchor': list(anchor), 'order': list(ORDER),
                'per_direction_anchors': {key: list(value) for key, value in anchors.items()},
                'frames': frame_records})
    return {'poses': poses, 'anchor': anchor, 'anchors': anchors, 'records': records,
            'scale': scale, 'phase': phase, 'target_height': target_height,
            'source_body_heights': source_heights}


def place(board, sprite, center, baseline, anchor, scale):
    enlarged = sprite.resize((24*scale, 36*scale), Image.Resampling.NEAREST)
    board.paste(enlarged, (center-anchor[0]*scale, baseline-anchor[1]*scale), enlarged)


def actor_board(actor, data):
    board = Image.new('RGB', (1440, 570), PAPER);draw = ImageDraw.Draw(board)
    draw.text((22, 15), ACTORS[actor]+' — directional idle studies', font=font(29), fill=INK)
    draw.text((22, 60), 'Static poses · approved front reference unchanged · 24×36 native · nearest-neighbor',
              font=font(18), fill=MUTED)
    for index, direction in enumerate(ORDER):
        left=index*360;center=left+180
        draw.text((left+22, 101), LABELS[direction], font=font(22), fill=INK)
        draw.line((left+18, 456, left+342, 456), fill=GROUND)
        sprite = data['poses'][direction]
        place(board, sprite, center, 455, data['anchors'][direction], 10)
        board.paste(sprite, (center-12, 487), sprite)
    draw.text((22, 540), '10× above · native sprites below · new views awaiting review', font=font(17), fill=MUTED)
    board.save(REVIEW/f'{actor}_directional_idles.png', optimize=True)


def comparison_board(data):
    board = Image.new('RGB', (1360, 112+370*len(data)), PAPER);draw = ImageDraw.Draw(board)
    draw.text((22, 15), 'Companion directional idle studies — review', font=font(29), fill=INK)
    draw.text((22, 59), 'Front reference approved · new left/right/rear static poses · no mirroring or anatomy warping',
              font=font(17), fill=MUTED)
    for index, direction in enumerate(ORDER):
        draw.text((index*340+22, 88), LABELS[direction], font=font(21), fill=INK)
    for row, (actor, record) in enumerate(data.items()):
        top=122+row*370;baseline=top+284
        draw.text((22, top+4), ACTORS[actor], font=font(21), fill=INK)
        for index, direction in enumerate(ORDER):
            left=index*340;center=left+170;sprite=record['poses'][direction]
            draw.line((left+18, baseline+1, left+322, baseline+1), fill=GROUND)
            place(board, sprite, center, baseline, record['anchors'][direction], 8)
            board.paste(sprite, (center-12, baseline+20), sprite)
    board.save(REVIEW/'directional_comparison.png', optimize=True)


def build(actors=None, snapshot=None):
    actors = list(actors or ACTORS)
    protected = capture_protected(snapshot)
    data = {actor: build_actor(actor) for actor in actors}
    REVIEW.mkdir(parents=True, exist_ok=True)
    for actor, record in data.items():actor_board(actor, record)
    comparison_board(data)
    verify_protected(protected)
    write_json(REVIEW/'validation.json',
               {'status': 'review', 'static_poses_only': True, 'new_pose_count': len(data)*3,
                'new_directions': list(DIRECTIONS), 'frame_size': list(FRAME_SIZE),
                'binary_alpha': True, 'floor_row': 34,
                'sampling': 'one uniform affine nearest-neighbor grid per actor; no anatomy edits or mirroring',
                'palette_policy': 'exact approved front-idle palette for each actor',
                'approved_pngs_verified_unchanged': len(protected),
                'protected_png_hashes': protected,
                'actors': {actor: {'common_uniform_scale': record['scale'],
                                  'common_sampling_phase': list(record['phase']),
                                  'per_direction_anchors': {key: list(value) for key, value in record['anchors'].items()},
                                  'target_body_height': record['target_height'],
                                  'source_body_heights': record['source_body_heights'],
                                  'poses': record['records']} for actor, record in data.items()}})
    print(json.dumps({'actors': actors, 'new_static_poses': len(data)*3,
                      'protected_pngs_unchanged': len(protected),
                      'review': (REVIEW/'directional_comparison.png').relative_to(ROOT).as_posix()}))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--actor', action='append', choices=list(ACTORS), dest='actors')
    parser.add_argument('--approved-snapshot', type=Path)
    arguments=parser.parse_args()
    build(arguments.actors, arguments.approved_snapshot)
