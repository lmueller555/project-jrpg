"""Export four source-authored front-walk poses without altering body anatomy.

The approved idle supplies each actor's single shared palette. Every pose uses
one common nearest-neighbor scale. Registration follows an authored body/pelvis
center and floor coordinate, never the full equipment bounding box or a moving
support foot. Source and export recipes remain beside the generated artwork.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import statistics
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageSequence


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/companions'
REVIEW = ROOT/'docs/reviews/companion_front_walks'
FRAME_SIZE = (24, 36)
DURATION = 140
ACTORS = {
    'lucan': {'name': 'Lucan Rooke', 'anchor': (12, 34), 'body_height': 31},
    'rhea': {'name': 'Rhea Sorel', 'anchor': (10, 34), 'body_height': 32},
    'edran': {'name': 'Edran Hale', 'anchor': (12, 34), 'body_height': 29},
}
PHASES = ('screen_left_contact', 'screen_left_support_passing',
          'screen_right_contact', 'screen_right_support_passing')
PAPER = (232, 237, 242)
INK = (38, 52, 62)
MUTED = (82, 97, 108)
GROUND = (199, 208, 213)


def pixels(image):
    method = getattr(image, 'get_flattened_data', None)
    return method() if method is not None else image.getdata()


def write_json(path, record):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def font(size):
    return ImageFont.truetype(str(ROOT/'assets/ui/fonts/DejaVuSans.ttf'), size)


def approved_palette(idle):
    counts = Counter(pixel[:3] for pixel in pixels(idle) if pixel[3])
    return [color for color, _ in sorted(counts.items(), key=lambda item: (-item[1], item[0]))]


def remap_to_idle(image, palette):
    colors = {p[:3] for p in pixels(image) if p[3]}
    lookup = {color: min(palette, key=lambda candidate:
              sum((a-b)**2 for a, b in zip(color, candidate))) for color in colors}
    result = Image.new('RGBA', image.size)
    result.putdata([(*lookup[p[:3]], 255) if p[3] else (0, 0, 0, 0)
                    for p in pixels(image)])
    return result


def frame_recipes(recipe):
    overrides = recipe.get('export', {})
    frames = overrides.get('frames', recipe.get('frames', recipe.get('panels', [])))
    if isinstance(frames, dict):frames = [frames.get(phase, {}) for phase in PHASES]
    if frames and len(frames) != 4:raise ValueError('Exactly four frame recipes are required.')
    return overrides, frames or [{} for _ in PHASES]


def default_panel(sheet, recipe, index):
    layout = recipe.get('export', {}).get('layout', recipe.get('layout', 'four columns'))
    columns = 2 if '2x2' in str(layout).lower().replace('×', 'x') else 4
    rows = 4//columns
    column, row = index % columns, index//columns
    return (round(column*sheet.width/columns), round(row*sheet.height/rows),
            round((column+1)*sheet.width/columns), round((row+1)*sheet.height/rows))


def extract_sources(sheet, recipe):
    export, entries = frame_recipes(recipe)
    prepared = []
    for index, settings in enumerate(entries):
        panel = tuple(settings.get('source_bounds', settings.get('source_cell',
                      default_panel(sheet, recipe, index))))
        crop = sheet.crop(panel)
        crop.putalpha(crop.getchannel('A').point(lambda alpha: 255 if alpha >= 128 else 0))
        local = crop.getbbox()
        if local is None:raise ValueError(f'Empty authored source frame {index+1}')
        bounds = (panel[0]+local[0], panel[1]+local[1],
                  panel[0]+local[2], panel[1]+local[3])
        body = tuple(settings.get('body_bounds', settings.get('source_body_bounds', bounds)))
        if body[2] <= body[0] or body[3] <= body[1]:
            raise ValueError(f'Invalid body bounds for source frame {index+1}')
        prepared.append({'image': crop.crop(local), 'panel': panel, 'bounds': bounds,
                         'body_bounds': body,
                         'body_center_x': settings.get('body_center_x', (body[0]+body[2]-1)/2),
                         'ground_y': settings.get('ground_y', bounds[3]-1),
                         'native_offset': tuple(settings.get('native_offset', (0, 0)))})
    return export, prepared


def choose_scale(actor, export, prepared):
    target_height = export.get('target_body_height', ACTORS[actor]['body_height'])
    body_heights = [p['body_bounds'][3]-p['body_bounds'][1] for p in prepared]
    desired = target_height/statistics.median(body_heights)
    anchor = tuple(export.get('anchor', ACTORS[actor]['anchor']))
    margin = export.get('margin', 1)
    limits = [desired]
    for frame in prepared:
        x0, y0, x1, y1 = frame['bounds']
        center, ground = frame['body_center_x'], frame['ground_y']
        ax = anchor[0]+frame['native_offset'][0]
        ay = anchor[1]+frame['native_offset'][1]
        for available, extent in ((ax-margin, center-x0),
                                  (FRAME_SIZE[0]-1-margin-ax, x1-1-center),
                                  (ay-margin, ground-y0),
                                  (FRAME_SIZE[1]-1-margin-ay, y1-1-ground)):
            if extent > 0:limits.append(available/extent)
    scale = export.get('scale', export.get('native_scale', min(limits)))
    if scale <= 0:raise ValueError(f'Nonpositive common export scale for {actor}')
    return scale, anchor, {'target_body_height': target_height,
                          'source_body_heights': body_heights,
                          'inferred_desired_scale': desired,
                          'equipment_fit_scale': min(limits),
                          'equipment_reduced_scale': scale < desired*.85}


def export_frame(source, scale, anchor, palette, phase):
    crop = source['image']
    x0, y0, _, _ = source['bounds']
    center = source['body_center_x']-x0
    floor = source['ground_y']-y0
    target_x = anchor[0]+source['native_offset'][0]+phase[0]
    target_y = anchor[1]+source['native_offset'][1]+phase[1]
    matrix = (1/scale, 0, center-target_x/scale,
              0, 1/scale, floor-target_y/scale)
    # Render an expanded canvas first so the contract can detect any sampled
    # opaque equipment pixels outside the native frame, rather than clipping
    # them silently. The exact same affine grid is shared by all four poses.
    padding = 36
    padded_matrix = (matrix[0], 0, matrix[2]-padding/scale,
                     0, matrix[4], matrix[5]-padding/scale)
    padded = crop.transform((FRAME_SIZE[0]+padding*2, FRAME_SIZE[1]+padding*2),
                            Image.Transform.AFFINE, padded_matrix, Image.Resampling.NEAREST)
    occupied = padded.getbbox()
    if (occupied is None or occupied[0] < padding or occupied[1] < padding or
            occupied[2] > padding+FRAME_SIZE[0] or occupied[3] > padding+FRAME_SIZE[1]):
        raise ValueError(f'Pose clips native frame at common scale={scale}, phase={phase}: '
                         f'occupied padded bounds={occupied}, source={source["bounds"]}')
    frame = padded.crop((padding, padding, padding+FRAME_SIZE[0], padding+FRAME_SIZE[1]))
    frame = remap_to_idle(frame, palette)
    alpha = set(pixels(frame.getchannel('A')))
    assert alpha <= {0, 255}
    assert frame.getbbox() is not None
    assert {p[:3] for p in pixels(frame) if p[3]} <= set(palette)
    info = {key: list(value) if isinstance(value, tuple) else value
            for key, value in source.items() if key != 'image'}
    info.update(native_bounds=list(frame.getbbox()),
                sampling_phase=list(phase), affine_output_to_source=list(matrix),
                registered_body_center=[anchor[0]+source['native_offset'][0],
                                        anchor[1]+source['native_offset'][1]],
                palette_colors=len({p[:3] for p in pixels(frame) if p[3]}))
    return frame, info


def build_actor(actor):
    directory = SOURCE/actor/'walk_front'
    source_path = directory/'walk_sheet.png'
    recipe_path = directory/'source.json'
    recipe = json.loads(recipe_path.read_text()) if recipe_path.exists() else {}
    status = recipe.get('art_status', 'review')
    if status not in ('approved', 'review'):
        raise ValueError(f'Invalid front-walk approval status: {actor}')
    sheet = Image.open(source_path).convert('RGBA')
    idle_path = ROOT/f'assets/characters/{actor}/idle_front.png'
    idle = Image.open(idle_path).convert('RGBA')
    palette = approved_palette(idle)
    export, prepared = extract_sources(sheet, recipe)
    scale, anchor, scale_info = choose_scale(actor, export, prepared)
    phase = tuple(export.get('sampling_phase', (.5, .5)))
    output = ROOT/f'assets/characters/{actor}/walk_front'
    output.mkdir(parents=True, exist_ok=True)
    frames = [];records = []
    for index, source in enumerate(prepared):
        frame, geometry = export_frame(source, scale, anchor, palette, phase)
        filename = f'frame_{index+1:02}.png';path = output/filename
        frame.save(path, optimize=True)
        frames.append(frame)
        records.append({'file': filename, 'rect': [index*24, 0, 24, 36],
                        'duration_ms': DURATION, 'phase': PHASES[index],
                        'source_frame': index, 'sha256': sha256(path), **geometry})
    distinct = len({frame.tobytes() for frame in frames})
    if distinct != 4:raise ValueError(f'{actor}: authored gait has only {distinct} distinct native frames')
    atlas = Image.new('RGBA', (96, 36))
    for index, frame in enumerate(frames):atlas.alpha_composite(frame, (index*24, 0))
    atlas.save(output/'spritesheet.png', optimize=True)
    metadata = {'version': 1, 'character': actor, 'display_name': ACTORS[actor]['name'],
                'animation': 'walk.front', 'status': status, 'design_status': status,
                'image': 'spritesheet.png', 'frame_size': list(FRAME_SIZE),
                'foot_anchor': list(anchor), 'loop': True, 'frame_duration_ms': DURATION,
                'source': source_path.relative_to(ROOT).as_posix(),
                'source_sha256': sha256(source_path),
                'source_recipe': recipe_path.relative_to(ROOT).as_posix(),
                'source_recipe_sha256': sha256(recipe_path) if recipe_path.exists() else None,
                'palette_source': idle_path.relative_to(ROOT).as_posix(),
                'palette_source_sha256': sha256(idle_path),
                'palette': [list(color) for color in palette],
                'common_uniform_scale': scale, 'registration': 'authored body/pelvis center and floor',
                'common_sampling_phase': list(phase),
                'sampling': 'one exact affine nearest-neighbor grid for all four poses',
                'distinct_native_frames': distinct, 'shared_palette_color_count': len(palette),
                'frames': records, 'scale_analysis': scale_info,
                'review': {'gif': f'../../../../docs/reviews/companion_front_walks/{actor}_front_walk.gif',
                           'scale': 10, 'background': '#e8edf2'}}
    write_json(output/'animation.json', metadata)
    return {'idle': idle, 'frames': frames, 'anchor': anchor, 'palette': palette,
            'metadata': metadata, 'output': output, 'distinct': distinct}


def place(canvas, sprite, center, baseline, anchor, scale):
    enlarged = sprite.resize((sprite.width*scale, sprite.height*scale), Image.Resampling.NEAREST)
    canvas.paste(enlarged, (center-anchor[0]*scale, baseline-anchor[1]*scale), enlarged)


def review_palette(frames, palettes):
    colors = list(dict.fromkeys([PAPER, INK, MUTED, GROUND]+[color for p in palettes for color in p]))
    dominant = frames[0].quantize(colors=256, method=Image.Quantize.FASTOCTREE)
    table = dominant.getpalette()
    for _, index in sorted(dominant.getcolors() or [], reverse=True):
        color = tuple(table[index*3:index*3+3])
        if color not in colors:colors.append(color)
        if len(colors) == 256:break
    colors = (colors+[(0, 0, 0)]*256)[:256]
    image = Image.new('P', (1, 1))
    image.putpalette([value for color in colors for value in color])
    return image


def save_gif(path, frames, palettes):
    fixed = review_palette(frames, palettes)
    indexed = [frame.quantize(palette=fixed, dither=Image.Dither.NONE) for frame in frames]
    indexed[0].save(path, save_all=True, append_images=indexed[1:], duration=[DURATION]*4,
                    loop=0, disposal=2, optimize=False, background=0)
    with Image.open(path) as image:
        durations = [frame.info.get('duration') for frame in ImageSequence.Iterator(image)]
        assert len(durations) == 4 and durations == [DURATION]*4, (path, durations)
        assert image.info.get('loop') == 0
    return {'file': path.name, 'duration_ms': DURATION*4, 'frame_count': 4,
            'loop': 0, 'sha256': sha256(path)}


def actor_previews(actor, record):
    boards = []
    for index, sprite in enumerate(record['frames']):
        board = Image.new('RGB', (760, 560), PAPER);draw = ImageDraw.Draw(board)
        draw.text((24, 16), ACTORS[actor]['name']+' — front walk', font=font(27), fill=INK)
        draw.text((24, 58), 'Four authored poses · 140 ms per frame · 24×36 native', font=font(18), fill=MUTED)
        draw.text((104, 94), 'Approved idle', font=font(20), fill=INK)
        draw.text((464, 94), 'Walking loop', font=font(20), fill=INK)
        for center in (200, 560):draw.line((center-152, 456, center+152, 456), fill=GROUND)
        place(board, record['idle'], 200, 455, record['anchor'], 10)
        place(board, sprite, 560, 455, record['anchor'], 10)
        board.paste(record['idle'], (188, 486), record['idle'])
        board.paste(sprite, (548, 486), sprite)
        draw.text((24, 535), f'10× nearest-neighbor above · native below · {PHASES[index].replace("_", " ")}',
                  font=font(14), fill=MUTED)
        boards.append(board)
    return save_gif(REVIEW/f'{actor}_front_walk.gif', boards, [record['palette']])


def combined_preview(records):
    caelen_path = ROOT/'assets/characters/caelan/walk_front'
    reference = [Image.open(caelen_path/f'frame_{i+1:02}.png').convert('RGBA') for i in range(4)]
    reference_idle = Image.open(ROOT/'assets/characters/caelan/idle_front.png').convert('RGBA')
    actors = list(records)
    frames = []
    for index in range(4):
        board = Image.new('RGB', (340*(len(actors)+1), 550), PAPER);draw = ImageDraw.Draw(board)
        draw.text((20, 15), 'Front walking — shared 24×36 game scale', font=font(28), fill=INK)
        draw.text((20, 56), 'Four authored poses · 140 ms each · 560 ms loop · nearest-neighbor enlargement', font=font(18), fill=MUTED)
        entries = [('Caelan reference', reference[index], (12, 34))]
        entries += [(ACTORS[a]['name'], records[a]['frames'][index], records[a]['anchor']) for a in actors]
        for column, (name, sprite, anchor) in enumerate(entries):
            center=170+column*340
            draw.text((column*340+24, 92), name, font=font(21), fill=INK)
            draw.line((column*340+20, 456, (column+1)*340-20, 456), fill=GROUND)
            place(board, sprite, center, 455, anchor, 10)
            board.paste(sprite, (center-12, 482), sprite)
        draw.text((20, 526), 'Native sprites shown below each enlargement', font=font(15), fill=MUTED)
        frames.append(board)
    palettes = [approved_palette(reference_idle)]+[r['palette'] for r in records.values()]
    return save_gif(REVIEW/'front_walks.gif', frames, palettes)


def contact_sheet(records):
    board = Image.new('RGB', (1280, 100+370*len(records)), PAPER);draw = ImageDraw.Draw(board)
    draw.text((22, 15), 'Companion front walks — authored contact poses', font=font(28), fill=INK)
    headers = ['Approved idle', 'Left contact', 'Left passing', 'Right contact', 'Right passing']
    for column, text in enumerate(headers):draw.text((column*256+18, 62), text, font=font(20), fill=INK)
    for row, (actor, record) in enumerate(records.items()):
        top=100+row*370;baseline=top+300
        draw.text((18, top+8), ACTORS[actor]['name'], font=font(19), fill=INK)
        for column, sprite in enumerate([record['idle']]+record['frames']):
            center=128+column*256
            draw.line((column*256+16, baseline+1, (column+1)*256-16, baseline+1), fill=GROUND)
            place(board, sprite, center, baseline, record['anchor'], 8)
    board.save(REVIEW/'contact_sheet.png', optimize=True)


def build(actors=None):
    actors = list(actors or ACTORS)
    records = {actor: build_actor(actor) for actor in actors}
    REVIEW.mkdir(parents=True, exist_ok=True)
    previews = {actor: actor_previews(actor, record) for actor, record in records.items()}
    previews['combined'] = combined_preview(records)
    contact_sheet(records)
    status = 'approved' if all(r['metadata']['status'] == 'approved'
                               for r in records.values()) else 'review'
    report = {'status': status, 'frame_size': list(FRAME_SIZE), 'frame_duration_ms': DURATION,
              'loop_duration_ms': DURATION*4, 'binary_alpha': True,
              'registration': 'body/pelvis center; equipment and support feet do not recenter frames',
              'palette_policy': 'one exact approved idle palette per actor for all four poses',
              'sampling': 'exact common affine nearest-neighbor grid per actor; no limb redrawing or warping',
              'previews': previews, 'actors': {a: r['metadata'] for a, r in records.items()}}
    write_json(REVIEW/'validation.json', report)
    print(json.dumps({'actors': actors, 'authored_frames': len(actors)*4,
                      'review': (REVIEW/'front_walks.gif').relative_to(ROOT).as_posix()}))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--actor', action='append', choices=list(ACTORS), dest='actors')
    args = parser.parse_args()
    build(args.actors)
