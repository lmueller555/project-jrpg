"""Export authored companion studies without redrawing character anatomy.

Each transparent design sheet has three columns: front overworld idle,
left-facing combat idle, and detailed standing cinematic pose. Export performs
cropping, uniform nearest-neighbor scaling, palette reduction and foot-baseline
registration only. Optional source.json export overrides use whole-sheet pixel
coordinates, so a tall staff need not determine a character's body scale.
"""
from __future__ import annotations

import argparse
import colorsys
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/companions'
REVIEW = ROOT/'docs/reviews/companion_sprites'
ACTORS = {'lucan': 'Lucan Rooke', 'rhea': 'Rhea Sorel', 'edran': 'Edran Hale'}
FORMATS = {
    'overworld': {'column': 0, 'canvas': (24, 36), 'anchor': (12, 34),
                 'height': 32, 'colors': 32, 'facing': 'front',
                 'directory': 'assets/characters/{actor}', 'file': 'idle_front.png',
                 'metadata': 'idle_front.json'},
    'combat': {'column': 1, 'canvas': (64, 64), 'anchor': (32, 54),
               'height': 42, 'colors': 48, 'facing': 'left',
               'directory': 'assets/combat/{actor}', 'file': 'idle_01.png',
               'metadata': 'animation.json'},
    'cinematic': {'column': 2, 'canvas': (96, 112), 'anchor': (48, 104),
                  'height': 78, 'colors': 64, 'facing': 'front',
                  'directory': 'assets/cinematics/companions/{actor}', 'file': 'stand_front.png',
                  'metadata': 'animation.json'},
}
BACKGROUND = '#e8edf2'
INK = '#26343e'


def write_json(path, record):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')


def font(size):
    return ImageFont.truetype(str(ROOT/'assets/ui/fonts/DejaVuSans.ttf'), size)


def pixels(image):
    reader = getattr(image, 'get_flattened_data', None)
    return reader() if reader is not None else image.getdata()


def palette_reduce(image, count, actor):
    """Reduce colors while retaining rare source-authored Rhea color accents."""
    opaque = [p[:3] for p in pixels(image) if p[3]]
    unique = set(opaque)
    if len(unique) <= count:return image
    reserved = []
    if actor == 'rhea':
        # Preserve existing blue-eye/purple-wood/green-orb/gold-hair pixels;
        # no new colored landmarks are inserted into the authored drawing.
        for low, high in ((185, 250), (255, 325), (70, 165), (28, 65)):
            candidates = []
            for color in unique:
                hue, saturation, value = colorsys.rgb_to_hsv(*(c/255 for c in color))
                if low <= hue*360 <= high and saturation >= .35 and value >= .3:
                    candidates.append((saturation*value, color))
            if candidates:reserved.append(max(candidates)[1])
    opaque_strip = Image.new('RGB', (len(opaque), 1))
    opaque_strip.putdata(opaque)
    quantized = opaque_strip.quantize(colors=max(2, count-len(reserved)),
                                     method=Image.Quantize.FASTOCTREE)
    palette = quantized.getpalette()
    colors = sorted(quantized.getcolors() or [], reverse=True)
    choices = [tuple(palette[index*3:index*3+3]) for _, index in colors]+reserved
    choices = list(dict.fromkeys(choices))
    lookup = {color: min(choices, key=lambda p: sum((a-b)**2 for a, b in zip(color, p)))
              for color in unique}
    result = Image.new('RGBA', image.size)
    result.putdata([(*lookup[p[:3]], 255) if p[3] else (0, 0, 0, 0)
                    for p in pixels(image)])
    return result


def export_pose(sheet, actor, kind, overrides):
    fmt = FORMATS[kind]
    width, height = sheet.size
    column = fmt['column']
    panel = tuple(overrides.get('source_bounds',
                  [round(column*width/3), 0, round((column+1)*width/3), height]))
    crop = sheet.crop(panel)
    crop.putalpha(crop.getchannel('A').point(lambda value: 255 if value >= 128 else 0))
    occupied = crop.getbbox()
    if occupied is None:raise ValueError(f'No opaque sprite in {actor}:{kind}')
    bounds = (panel[0]+occupied[0], panel[1]+occupied[1],
              panel[0]+occupied[2], panel[1]+occupied[3])
    body = tuple(overrides.get('source_body_bounds', bounds))
    if body[3] <= body[1]:raise ValueError(f'Invalid body bounds: {actor}:{kind}')
    # Locate the supporting feet in the lowest body band. A body-bounds override
    # excludes a staff planted outside the stance when the automatic center is off.
    body_alpha = sheet.getchannel('A').crop(body)
    band_height = max(1, round(body_alpha.height*.08))
    band = body_alpha.crop((0, body_alpha.height-band_height, body_alpha.width, body_alpha.height))
    foot_x = [x for x in range(band.width) if band.crop((x, 0, x+1, band.height)).getextrema()[1] >= 128]
    if not foot_x:raise ValueError(f'No supporting foot pixels in {actor}:{kind}')
    ground_x = overrides.get('ground_x', body[0]+(min(foot_x)+max(foot_x))/2)
    ground_y = overrides.get('ground_y', bounds[3]-1)
    target_height = overrides.get('target_body_height', fmt['height'])
    desired = target_height/(body[3]-body[1])
    ax, ay = overrides.get('anchor', fmt['anchor']);cw, ch = fmt['canvas']
    limits = [desired]
    for available, extent in ((ax-1, ground_x-bounds[0]),
                              (cw-2-ax, bounds[2]-1-ground_x),
                              (ay-1, ground_y-bounds[1]),
                              (ch-2-ay, bounds[3]-1-ground_y)):
        if extent > 0:limits.append(available/extent)
    scale = min(limits)
    if scale <= 0:raise ValueError(f'Invalid registration in {actor}:{kind}')
    crop = crop.crop(occupied)
    resized = crop.resize((max(1, round(crop.width*scale)), max(1, round(crop.height*scale))),
                          Image.Resampling.NEAREST)
    # Use the actual rounded pixel dimensions when registering the ground point.
    gx = round((ground_x-bounds[0]+.5)*resized.width/crop.width-.5)
    gy = round((ground_y-bounds[1]+.5)*resized.height/crop.height-.5)
    offset = (ax-gx, ay-gy)
    if (offset[0] < 0 or offset[1] < 0 or offset[0]+resized.width > cw or
            offset[1]+resized.height > ch):
        raise ValueError(f'Export would clip {actor}:{kind}: {offset}, {resized.size}')
    frame = Image.new('RGBA', fmt['canvas'])
    frame.alpha_composite(resized, offset)
    frame = palette_reduce(frame, overrides.get('palette_size', fmt['colors']), actor)
    alpha = set(pixels(frame.getchannel('A')))
    assert alpha <= {0, 255}, (actor, kind, alpha)
    occupied_native = frame.getbbox()
    assert occupied_native is not None
    assert 0 < occupied_native[0] and occupied_native[2] < cw
    assert 0 < occupied_native[1] and occupied_native[3] <= ch-1
    extraction = {'panel_bounds': list(panel), 'source_bounds': list(bounds),
                  'source_body_bounds': list(body), 'source_ground': [ground_x, ground_y],
                  'uniform_scale': scale, 'target_body_height': target_height,
                  'exported_body_height': round((body[3]-body[1])*scale),
                  'offset': list(offset), 'bounds': list(occupied_native),
                  'equipment_reduced_body_scale': scale < desired*.85,
                  'palette_colors': len({p[:3] for p in pixels(frame) if p[3]})}
    return frame, extraction


def build_actor(actor):
    source = SOURCE/actor/'design_sheet.png'
    recipe_path = source.with_name('source.json')
    recipe = json.loads(recipe_path.read_text()) if recipe_path.exists() else {}
    status = recipe.get('art_status', 'review')
    if status not in ('approved', 'review'):raise ValueError(f'Invalid artwork status: {actor}')
    sheet = Image.open(source).convert('RGBA')
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    records = {};frames = {}
    for kind, fmt in FORMATS.items():
        overrides = recipe.get('export', {}).get(kind, {})
        frame, extraction = export_pose(sheet, actor, kind, overrides)
        directory = ROOT/fmt['directory'].format(actor=actor)
        directory.mkdir(parents=True, exist_ok=True)
        path = directory/fmt['file']
        frame.save(path, optimize=True)
        metadata = {'version': 1, 'actor': actor, 'display_name': ACTORS[actor],
                    'status': status, 'canvas': list(fmt['canvas']),
                    'anchor': list(overrides.get('anchor', fmt['anchor'])),
                    'facing': overrides.get('facing', fmt['facing']),
                    'source': source.relative_to(ROOT).as_posix(), 'source_sha256': digest,
                    'extraction': extraction, 'image': fmt['file'],
                    'authored_pose_count': 1}
        if kind == 'overworld':
            metadata.update(frame_size=list(fmt['canvas']), foot_anchor=metadata['anchor'],
                            animation='idle.front')
        elif kind == 'combat':
            metadata['animations'] = {'idle': {'loop': True,
                'frames': [{'file': fmt['file'], 'duration_ms': 500}]}}
        else:metadata['poses'] = {'stand_front': fmt['file']}
        write_json(directory/fmt['metadata'], metadata)
        frames[kind] = frame
        records[kind] = {'image': path.relative_to(ROOT).as_posix(), 'status': status,
                         'metadata': (directory/fmt['metadata']).relative_to(ROOT).as_posix(),
                         'canvas': list(fmt['canvas']), 'anchor': metadata['anchor'],
                         'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), **extraction}
    return frames, records


def comparison_board(frames, actors, records, filename='sprite_comparison.png'):
    board = Image.new('RGB', (1500, 145+len(actors)*475), BACKGROUND)
    draw = ImageDraw.Draw(board)
    approved = all(records[actor]['overworld']['status'] == 'approved' for actor in actors)
    title = 'Companion sprite designs — approved' if approved else 'Companion sprite studies — review'
    draw.text((28, 16), title, font=font(30), fill=INK)
    draw.text((28, 59), 'Authored static poses · nearest-neighbor enlargements · shared planted-foot baseline',
              font=font(18), fill='#52616c')
    headings = [('overworld', 'Front idle · 24×36', 10), ('combat', 'Combat ready · 64×64', 6),
                ('cinematic', 'Cinematic standing · 96×112', 3)]
    for col, (_, label, _) in enumerate(headings):
        draw.text((28+col*490, 100), label, font=font(23), fill=INK)
    for row, actor in enumerate(actors):
        top = 140+row*475;baseline = top+370
        draw.text((28, top), ACTORS[actor], font=font(24), fill=INK)
        for col, (kind, _, factor) in enumerate(headings):
            frame = frames[actor][kind];anchor = records[actor][kind]['anchor']
            left = 28+col*490
            draw.line((left, baseline+1, left+450, baseline+1), fill='#c7d0d5')
            enlarged = frame.resize((frame.width*factor, frame.height*factor), Image.Resampling.NEAREST)
            x = left+225-anchor[0]*factor;y = baseline-anchor[1]*factor
            board.paste(enlarged, (x, y), enlarged)
            board.paste(frame, (left+12, top+417-frame.height), frame)
            draw.text((left+118, top+408), f'{factor}× above · native at left', font=font(16), fill='#52616c')
    REVIEW.mkdir(parents=True, exist_ok=True)
    board.save(REVIEW/filename, optimize=True)


def scale_board(frames, actors, records):
    references = {
        'overworld': (ROOT/'assets/characters/caelan/idle_front.png', (12, 34), 6),
        'combat': (ROOT/'assets/combat/caelan/idle_01.png', (24, 42), 4),
        'cinematic': (ROOT/'assets/story/opening_cinematic/actors/caelan/stand_empty.png', (48, 104), 2),
    }
    board = Image.new('RGB', (1600, 1030), BACKGROUND);draw = ImageDraw.Draw(board)
    draw.text((24, 14), 'Shared scene scale — Caelan and companion studies', font=font(27), fill=INK)
    for row, (kind, (path, anchor, factor)) in enumerate(references.items()):
        top = 62+row*320;baseline=top+260
        draw.text((24, top), kind.title(), font=font(21), fill=INK)
        entries = [('Caelan reference', Image.open(path).convert('RGBA'), anchor)]
        entries += [(ACTORS[a], frames[a][kind], records[a][kind]['anchor']) for a in actors]
        for col, (name, frame, foot) in enumerate(entries):
            left=col*400
            enlarged=frame.resize((frame.width*factor, frame.height*factor),Image.Resampling.NEAREST)
            draw.line((left+15,baseline+1,left+385,baseline+1), fill='#c7d0d5')
            board.paste(enlarged,(left+200-foot[0]*factor,baseline-foot[1]*factor),enlarged)
            draw.text((left+25,baseline+18),name,font=font(18),fill=INK)
    board.save(REVIEW/'scale_comparison.png', optimize=True)


def build(actors=None):
    actors = list(actors or ACTORS)
    frames={};records={}
    for actor in actors:frames[actor],records[actor]=build_actor(actor)
    comparison_board(frames, actors, records)
    if 'edran' in actors:
        comparison_board(frames, ['edran'], records, 'edran_sky_blue_review.png')
    scale_board(frames, actors, records)
    status = 'approved' if all(records[actor]['overworld']['status'] == 'approved'
                               for actor in actors) else 'review'
    report={'status':status,'static_poses_only':True,'binary_alpha':True,
            'actor_statuses':{actor:records[actor]['overworld']['status'] for actor in actors},
            'sampling':'uniform nearest-neighbor; no anatomy redrawing or per-axis warping',
            'actors':records}
    write_json(REVIEW/'verification.json',report)
    print(json.dumps({'actors':actors,'pose_count':len(actors)*3,
                      'review':(REVIEW/'sprite_comparison.png').relative_to(ROOT).as_posix()}))
    return report


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--actor',action='append',choices=list(ACTORS),dest='actors')
    args=parser.parse_args()
    build(args.actors)
