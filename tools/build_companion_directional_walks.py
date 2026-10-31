"""Export source-authored left/right/rear companion walks and review boards.

Each cycle uses one exact affine nearest-neighbor scale/grid, the approved front
palette and authored body-center/floor registration. Equipment never changes
the body scale. This tool does not redraw, mirror or warp character anatomy.
Approved front walks are read-only references in the four-direction atlases.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import statistics

from PIL import Image, ImageDraw

from build_companion_front_walks import (approved_palette, export_frame, font,
                                         pixels, save_gif, write_json)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/companions'
REVIEW = ROOT/'docs/reviews/companion_directional_walks'
ACTORS = {'lucan': 'Lucan Rooke', 'rhea': 'Rhea Sorel', 'edran': 'Edran Hale'}
HEIGHTS = {'lucan': 31, 'rhea': 32, 'edran': 29}
DIRECTIONS = ('left', 'right', 'back')
ORDER = ('front',)+DIRECTIONS
PHASES = ('first_contact', 'first_support_passing',
          'opposite_contact', 'opposite_support_passing')
DIRECTION_NAMES = {'front': 'Front', 'left': 'Left', 'right': 'Right', 'back': 'Rear'}
SIZE = (24, 36)
DURATION = 140
PAPER = (232, 237, 242)
INK = (38, 52, 62)
MUTED = (82, 97, 108)
GROUND = (199, 208, 213)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def protected_assets(snapshot=None):
    if snapshot is not None:
        record = json.loads(Path(snapshot).read_text())
        check_protected(record)
        return {name: record[name] for name in sorted(record)}
    paths = []
    for actor in ACTORS:
        home = ROOT/f'assets/characters/{actor}'
        paths.extend(home.glob('idle*.png'))
        paths.extend((home/'walk_front').glob('*.png'))
        for relative in (f'assets/combat/{actor}', f'assets/cinematics/companions/{actor}'):
            paths.extend((ROOT/relative).glob('*.png'))
        for directory in (SOURCE/actor, SOURCE/actor/'directional_idles', SOURCE/actor/'walk_front'):
            paths.extend(directory.glob('*.png'))
    return {p.relative_to(ROOT).as_posix(): sha256(p) for p in sorted(set(paths))}


def check_protected(record):
    changed = [name for name, digest in record.items()
               if not (ROOT/name).is_file() or sha256(ROOT/name) != digest]
    if changed:raise ValueError('Approved PNGs changed: '+', '.join(changed))


def source_file(directory, recipe):
    name = recipe.get('source_file', recipe.get('source_sheet', 'walk_sheet.png'))
    path = Path(name)
    return path if path.is_absolute() else directory/path


def source_frames(sheet, recipe):
    export = recipe.get('export', {})
    entries = export.get('frames', recipe.get('frames', []))
    if len(entries) != 4:raise ValueError('The source recipe must contain four authored frames.')
    prepared = []
    for index, entry in enumerate(entries):
        if ('body_center_x' not in entry or 'ground_y' not in entry or
                not any(key in entry for key in ('body_bounds', 'source_body_bounds'))):
            raise ValueError(f'Source frame{index+1} needs explicit body bounds, pelvis center and floor.')
        panel = tuple(entry.get('source_bounds', entry.get('source_cell',
                      [round(index*sheet.width/4), 0, round((index+1)*sheet.width/4), sheet.height])))
        crop = sheet.crop(panel)
        crop.putalpha(crop.getchannel('A').point(lambda alpha: 255 if alpha >= 128 else 0))
        occupied = crop.getbbox()
        if occupied is None:raise ValueError(f'Empty source pose {index+1}')
        bounds = (panel[0]+occupied[0], panel[1]+occupied[1],
                  panel[0]+occupied[2], panel[1]+occupied[3])
        body = tuple(entry.get('body_bounds', entry.get('source_body_bounds')))
        if body[3] <= body[1] or body[2] <= body[0]:raise ValueError(f'Invalid body bounds in frame{index+1}')
        prepared.append({'image': crop.crop(occupied), 'panel': panel, 'bounds': bounds,
                         'body_bounds': body, 'body_center_x': entry['body_center_x'],
                         'ground_y': entry['ground_y'], 'native_offset': (0, 0),
                         'phase': entry.get('phase', PHASES[index])})
    return export, prepared


def build_cycle(actor, direction):
    directory = SOURCE/actor/f'walk_{direction}'
    recipe_path = directory/'source.json'
    recipe = json.loads(recipe_path.read_text())
    original = source_file(directory, recipe)
    sheet = Image.open(original).convert('RGBA')
    home = ROOT/f'assets/characters/{actor}'
    idle_path = home/f'idle_{direction}.png'
    idle_meta = json.loads((home/f'idle_{direction}.json').read_text())
    front_path = home/'idle_front.png'
    palette = approved_palette(Image.open(front_path).convert('RGBA'))
    export, prepared = source_frames(sheet, recipe)
    anchor = tuple(export.get('anchor', idle_meta.get('foot_anchor', idle_meta.get('anchor'))))
    if anchor[1] != 34:raise ValueError(f'{actor}:{direction} floor must remain34.')
    target_height = export.get('target_body_height', HEIGHTS[actor])
    body_heights = [f['body_bounds'][3]-f['body_bounds'][1] for f in prepared]
    scale = export.get('scale', export.get('native_scale', target_height/statistics.median(body_heights)))
    phase = tuple(export.get('sampling_phase', (.5, .5)))
    if scale <= 0:raise ValueError(f'{actor}:{direction} common scale must be positive.')
    status = recipe.get('art_status', recipe.get('status', 'review'))
    if status not in ('review', 'approved'):raise ValueError(f'Invalid art approval status: {status}')
    output = home/f'walk_{direction}';output.mkdir(parents=True, exist_ok=True)
    frames = [];records = []
    for index, authored in enumerate(prepared):
        frame, geometry = export_frame(authored, scale, anchor, palette, phase)
        if frame.getbbox()[3] != 35:
            raise ValueError(f'{actor}:{direction}:{index+1} does not retain supporting floor34: {frame.getbbox()}')
        path = output/f'frame_{index+1:02}.png';frame.save(path, optimize=True)
        frames.append(frame)
        records.append({'file': path.name, 'rect': [index*24, 0, 24, 36],
                        'duration_ms': DURATION, 'phase': authored['phase'],
                        'source_frame': index, 'sha256': sha256(path), **geometry})
    distinct = len({frame.tobytes() for frame in frames})
    if distinct != 4:raise ValueError(f'{actor}:{direction} contains only{distinct} distinct native frames.')
    atlas = Image.new('RGBA', (96, 36))
    for index, frame in enumerate(frames):atlas.alpha_composite(frame, (index*24, 0))
    atlas.save(output/'spritesheet.png', optimize=True)
    metadata = {'version': 1, 'character': actor, 'display_name': ACTORS[actor],
                'animation': 'walk.'+direction, 'facing': direction, 'status': status,
                'design_status': status, 'image': 'spritesheet.png', 'frame_size': list(SIZE),
                'foot_anchor': list(anchor), 'loop': True, 'frame_duration_ms': DURATION,
                'source': original.relative_to(ROOT).as_posix(), 'source_sha256': sha256(original),
                'source_recipe': recipe_path.relative_to(ROOT).as_posix(),
                'source_recipe_sha256': sha256(recipe_path),
                'palette_source': front_path.relative_to(ROOT).as_posix(),
                'palette_source_sha256': sha256(front_path), 'palette': [list(c) for c in palette],
                'common_uniform_scale': scale, 'common_sampling_phase': list(phase),
                'sampling': 'one exact affine nearest-neighbor grid for all four authored poses',
                'registration': 'authored pelvis/body center and supporting floor; equipment does not recenter actor',
                'target_body_height': target_height, 'source_body_heights': body_heights,
                'directional_idle_reference': idle_path.relative_to(ROOT).as_posix(),
                'directional_idle_sha256': sha256(idle_path),
                'distinct_native_frames': distinct, 'shared_palette_color_count': len(palette),
                'frames': records}
    write_json(output/'animation.json', metadata)
    return metadata


def load_cycles():
    data = {}
    for actor in ACTORS:
        home = ROOT/f'assets/characters/{actor}'
        front = Image.open(home/'idle_front.png').convert('RGBA')
        record = {'palette': approved_palette(front), 'cycles': {}}
        for direction in ORDER:
            directory = home/f'walk_{direction}';path = directory/'animation.json'
            if not path.exists():continue
            metadata = json.loads(path.read_text())
            frames = [Image.open(directory/f['file']).convert('RGBA') for f in metadata['frames']]
            if len(frames) != 4:raise ValueError(f'{actor}:{direction} requires four frames.')
            idle_meta = json.loads((home/f'idle_{direction}.json').read_text())
            record['cycles'][direction] = {'frames': frames, 'metadata': metadata,
                                           'anchor': tuple(metadata['foot_anchor']),
                                           'idle': Image.open(home/f'idle_{direction}.png').convert('RGBA'),
                                           'idle_anchor': tuple(idle_meta.get('foot_anchor', idle_meta.get('anchor')))}
        data[actor] = record
    return data


def build_direction_atlas(actor, record):
    if any(direction not in record['cycles'] for direction in ORDER):return False
    directory = ROOT/f'assets/characters/{actor}'
    atlas = Image.new('RGBA', (96, 144));directions = []
    for row, direction in enumerate(ORDER):
        cycle = record['cycles'][direction]
        for column, frame in enumerate(cycle['frames']):atlas.alpha_composite(frame, (column*24, row*36))
        directions.append({'direction': direction,
                           'status': 'approved' if direction == 'front' else cycle['metadata']['status'],
                           'animation': f'walk_{direction}/animation.json',
                           'foot_anchor': list(cycle['anchor']),
                           'frames': [{'rect': [column*24, row*36, 24, 36], 'duration_ms': DURATION}
                                      for column in range(4)]})
    # The first row must reproduce the approved front atlas exactly at pixel level.
    front_atlas = Image.open(directory/'walk_front/spritesheet.png').convert('RGBA')
    if atlas.crop((0, 0, 96, 36)).tobytes() != front_atlas.tobytes():
        raise ValueError(f'{actor}: four-direction atlas changed the approved front row.')
    atlas.save(directory/'walk_directions.png', optimize=True)
    write_json(directory/'walk_directions.json',
               {'version': 1, 'character': actor, 'status': actor_status(record), 'image': 'walk_directions.png',
                'frame_size': list(SIZE), 'foot_anchor': list(record['cycles']['front']['anchor']),
                'per_direction_anchors': {d: list(record['cycles'][d]['anchor']) for d in ORDER},
                'directions': directions,
                'review': {'gif': f'../../../docs/reviews/companion_directional_walks/{actor}_walk_directions.gif',
                           'columns': list(ORDER), 'scale': 10, 'background': '#e8edf2'}})
    return True


def actor_status(record):
    return ('approved' if all(direction in record['cycles'] and
                              record['cycles'][direction]['metadata']['status']=='approved'
                              for direction in ORDER) else 'review')


def cycle_label(record, direction):
    cycle = record['cycles'].get(direction)
    return DIRECTION_NAMES[direction]+' — '+(cycle['metadata']['status'] if cycle else 'pending')


def place(board, sprite, center, baseline, anchor, scale):
    enlarged = sprite.resize((24*scale, 36*scale), Image.Resampling.NEAREST)
    board.paste(enlarged, (center-anchor[0]*scale, baseline-anchor[1]*scale), enlarged)


def actor_preview(actor, record):
    images = []
    for phase in range(4):
        board = Image.new('RGB', (1440, 570), PAPER);draw = ImageDraw.Draw(board)
        draw.text((22, 15), ACTORS[actor]+' — directional walking '+actor_status(record), font=font(28), fill=INK)
        draw.text((22, 59), 'Four authored poses per direction · 140ms each · approved front shown unchanged', font=font(18), fill=MUTED)
        for index, direction in enumerate(ORDER):
            left=index*360;center=left+180
            draw.text((left+20, 100), cycle_label(record,direction), font=font(22), fill=INK)
            draw.line((left+18, 456, left+342, 456), fill=GROUND)
            cycle = record['cycles'].get(direction)
            if cycle is None:draw.text((left+70, 300), 'Awaiting source', font=font(20), fill=MUTED)
            else:
                frame=cycle['frames'][phase]
                place(board, frame, center, 455, cycle['anchor'], 10)
                board.paste(frame, (center-12, 488), frame)
        draw.text((22, 540), '10× nearest-neighbor above · native examples below · 560ms loop', font=font(17), fill=MUTED)
        images.append(board)
    return save_gif(REVIEW/f'{actor}_walk_directions.gif', images, [record['palette']])


def combined_preview(data):
    images = []
    status='approved' if all(actor_status(record)=='approved' for record in data.values()) else 'review'
    for phase in range(4):
        board = Image.new('RGB', (1360, 1240), PAPER);draw=ImageDraw.Draw(board)
        draw.text((22, 15), 'Companion directional walks — '+status, font=font(29), fill=INK)
        draw.text((22, 59), '24×36 native · four authored poses · 140ms per frame · approved front reference unchanged', font=font(17), fill=MUTED)
        for index,direction in enumerate(ORDER):
            statuses={record['cycles'][direction]['metadata']['status'] for record in data.values()
                      if direction in record['cycles']}
            label_status='approved' if statuses=={'approved'} and all(direction in r['cycles'] for r in data.values()) else 'review'
            draw.text((index*340+22, 88),DIRECTION_NAMES[direction]+' — '+label_status,font=font(21),fill=INK)
        for row,(actor,record) in enumerate(data.items()):
            top=122+row*370;baseline=top+284
            draw.text((22,top+4),ACTORS[actor],font=font(21),fill=INK)
            for index,direction in enumerate(ORDER):
                left=index*340;center=left+170
                draw.line((left+18,baseline+1,left+322,baseline+1),fill=GROUND)
                cycle=record['cycles'].get(direction)
                if cycle is None:draw.text((left+56,top+170),'Awaiting source',font=font(18),fill=MUTED)
                else:
                    sprite=cycle['frames'][phase]
                    place(board,sprite,center,baseline,cycle['anchor'],8)
                    board.paste(sprite,(center-12,baseline+20),sprite)
        images.append(board)
    return save_gif(REVIEW/'walk_directions.gif',images,[r['palette'] for r in data.values()])


def contact_board(data, path, actors=None, scale=6):
    actors=list(actors or data)
    rows=[(a,d,c) for a in actors for d,c in data[a]['cycles'].items() if d in DIRECTIONS]
    row_height=scale*36+60;column_width=scale*24+58;width=column_width*5
    board=Image.new('RGB',(width,110+row_height*max(1,len(rows))),PAPER);draw=ImageDraw.Draw(board)
    draw.text((20,14),'Authored walk poses beside approved direction idles',font=font(24),fill=INK)
    headers=['Approved idle','First contact','First passing','Other contact','Other passing']
    for col,label in enumerate(headers):draw.text((col*column_width+12,67),label,font=font(17),fill=INK)
    if not rows:draw.text((30,170),'Awaiting directional source sheets',font=font(20),fill=MUTED)
    for row,(actor,direction,cycle) in enumerate(rows):
        top=110+row*row_height;baseline=top+scale*34+20
        draw.text((14,top+1),ACTORS[actor]+' / '+('rear' if direction=='back' else direction),font=font(17),fill=INK)
        entries=[(cycle['idle'],cycle['idle_anchor'])]+[(frame,cycle['anchor']) for frame in cycle['frames']]
        for col,(sprite,anchor) in enumerate(entries):
            left=col*column_width;center=left+column_width//2
            draw.line((left+12,baseline+1,left+column_width-12,baseline+1),fill=GROUND)
            place(board,sprite,center,baseline,anchor,scale)
    board.save(path,optimize=True)


def build(actors=None,directions=None,snapshot=None,available=False):
    actors=list(actors or ACTORS);directions=list(directions or DIRECTIONS)
    protected=protected_assets(snapshot)
    built=[]
    for actor in actors:
        for direction in directions:
            recipe=SOURCE/actor/f'walk_{direction}/source.json'
            if available and not recipe.is_file():continue
            build_cycle(actor,direction);built.append((actor,direction))
    data=load_cycles();REVIEW.mkdir(parents=True,exist_ok=True)
    atlases={a:build_direction_atlas(a,r) for a,r in data.items()}
    previews={a:actor_preview(a,r) for a,r in data.items()}
    previews['combined']=combined_preview(data)
    contact_board(data,REVIEW/'contact_sheet.png')
    for actor in data:contact_board(data,REVIEW/f'{actor}_contact_sheet.png',[actor],8)
    check_protected(protected)
    complete=[(a,d) for a,r in data.items() for d in DIRECTIONS if d in r['cycles']]
    pending=[(a,d) for a in ACTORS for d in DIRECTIONS if (a,d) not in complete]
    status='approved' if all(actor_status(record)=='approved' for record in data.values()) else 'review'
    report={'status':status,'frame_size':list(SIZE),'frame_duration_ms':DURATION,
            'loop_duration_ms':DURATION*4,'binary_alpha':True,'supporting_floor_row':34,
            'sampling':'one exact common affine nearest-neighbor grid per cycle; no mirroring or anatomy changes',
            'palette_policy':'exact approved front-idle palette per actor',
            'built_cycles':[list(x) for x in built],'available_new_cycles':len(complete),
            'pending_new_cycles':[list(x) for x in pending],'complete':not pending,
            'protected_pngs_verified_unchanged':len(protected),'protected_png_hashes':protected,
            'direction_atlases_complete':atlases,'previews':previews,
            'actors':{a:{d:c['metadata'] for d,c in r['cycles'].items()} for a,r in data.items()}}
    write_json(REVIEW/'validation.json',report)
    print(json.dumps({'built_cycles':len(built),'available_cycles':len(complete),'pending_cycles':pending,
                      'protected_pngs_unchanged':len(protected),
                      'review':(REVIEW/'walk_directions.gif').relative_to(ROOT).as_posix()}))
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--actor',action='append',choices=list(ACTORS),dest='actors')
    parser.add_argument('--direction',action='append',choices=list(DIRECTIONS),dest='directions')
    parser.add_argument('--approved-snapshot',type=Path)
    parser.add_argument('--available',action='store_true',help='Build currently available source recipes only')
    args=parser.parse_args()
    build(args.actors,args.directions,args.approved_snapshot,args.available)
