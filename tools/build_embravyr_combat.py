"""Export Embravyr's retained authored atlas poses without synthesizing motion.

Only explicit source-rectangle extraction, binary alpha, one shared opaque-only
palette, fixed nearest-neighbor scaling and anatomical anchoring are applied.
Disconnected mineral fragments and fire ribbons are part of the authored pose.
"""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
from io import BytesIO
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/combat/embravyr'
OUTPUT = ROOT/'assets/combat/embravyr'
REVIEW = ROOT/'docs/reviews/embravyr_combat'
RECIPE = SOURCE/'registration.json'
STATES = ('emerge', 'idle', 'cinder_lash', 'emberwash', 'gather_embers',
          'charged_hold', 'furnace_lunge', 'cooling', 'hurt', 'defeat')
COUNTS = dict(zip(STATES, (16, 16, 16, 24, 24, 16, 24, 16, 8, 24)))


def encoded(image, *, kind='PNG', **options):
    stream = BytesIO()
    image.save(stream, format=kind, **options)
    return stream.getvalue()


def split_time(total, count):
    if type(total) is not int or type(count) is not int or not 0 < count <= total:
        raise ValueError('Animation needs at least one millisecond per authored pose')
    return [round((index+1)*total/count)-round(index*total/count)
            for index in range(count)]


def _finite_pair(value, label):
    if (not isinstance(value, (list, tuple)) or len(value) != 2
            or any(type(number) not in (int, float) or not math.isfinite(number)
                   for number in value)):
        raise ValueError('Invalid Embravyr '+label)
    return value


def shared_palette(images, colors):
    """Keep transparent RGB matte out of the shared opaque palette entirely."""
    frequencies = Counter()
    for image in images:
        frequencies.update(pixel[:3] for pixel in image.get_flattened_data() if pixel[3] >= 128)
    if not frequencies:raise ValueError('Embravyr sources contain no opaque artwork')
    # Bound palette-training memory while retaining weighted source colors.
    denominator = max(1, sum(frequencies.values())//500000)
    samples = [color for color, count in sorted(frequencies.items())
               for _ in range(max(1, count//denominator))]
    sample = Image.new('RGB', (len(samples), 1))
    sample.putdata(samples)
    return sample.quantize(colors=colors, dither=Image.Dither.NONE)


def products():
    spec = json.loads(RECIPE.read_text(encoding='utf-8'))
    canvas = _finite_pair(spec['canvas'], 'canvas')
    anchor = _finite_pair(spec['anchor'], 'floor anchor')
    if (any(type(number) is not int or number <= 0 for number in canvas)
            or not 0 < anchor[0] < canvas[0] or not 0 < anchor[1] < canvas[1]):
        raise ValueError('Invalid Embravyr native canvas')
    scale = spec['native_scale']
    if type(scale) not in (int, float) or not math.isfinite(scale) or not 0 < scale <= 2:
        raise ValueError('Invalid Embravyr fixed native scale')
    colors = spec['palette_colors']
    if type(colors) is not int or not 2 <= colors <= 64:
        raise ValueError('Embravyr uses at most 64 opaque palette colors')
    columns, rows = spec.get('source_grid', [8, 6])
    if type(columns) is not int or type(rows) is not int or min(columns, rows) < 1:
        raise ValueError('Invalid Embravyr source grid')
    source_images = {}
    for name, expected in spec['source_sha256'].items():
        path = ROOT/name
        if sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError('Embravyr source changed: '+name)
        with Image.open(path) as image:source_images[name] = image.convert('RGBA')
    palette = shared_palette(source_images.values(), colors)
    drawings, provenance, source_cells = [], [], set()
    for index, drawing in enumerate(spec['drawings']):
        source_name = drawing['source_sheet']
        source = source_images[source_name]
        cell = drawing['source_cell']
        if type(cell) is not int or not 0 <= cell < columns*rows:
            raise ValueError('Invalid Embravyr source cell: '+str(index))
        identity = (source_name, cell)
        if identity in source_cells:
            raise ValueError('An authored Embravyr cell cannot be used twice: '+str(identity))
        source_cells.add(identity)
        left, top, width, height = drawing['source_rect']
        if (any(type(value) is not int for value in (left, top, width, height))
                or not 0 <= left < left+width <= source.width
                or not 0 <= top < top+height <= source.height):
            raise ValueError('Invalid Embravyr source rectangle: '+str(index))
        body = source.crop((left, top, left+width, top+height))
        body.putalpha(body.getchannel('A').point(lambda value:255 if value >= 128 else 0))
        if body.getbbox() is None:raise ValueError('Empty Embravyr authored pose: '+str(index))
        body = body.resize((max(1, round(width*scale)), max(1, round(height*scale))),
                           Image.Resampling.NEAREST)
        alpha = body.getchannel('A')
        body = body.convert('RGB').quantize(palette=palette,
                dither=Image.Dither.NONE).convert('RGBA')
        body.putalpha(alpha)
        foot = _finite_pair(drawing['source_foot'], 'source foot')
        position = [round(anchor[0]-(foot[0]-left)*scale),
                    round(anchor[1]-(foot[1]-top)*scale)]
        bounds = body.getbbox()
        native_bounds = [bounds[0]+position[0], bounds[1]+position[1],
                         bounds[2]+position[0], bounds[3]+position[1]]
        if (native_bounds[0] <= 0 or native_bounds[1] <= 0
                or native_bounds[2] >= canvas[0] or native_bounds[3] >= canvas[1]):
            raise ValueError('Clipped Embravyr authored pose: '+str(index)+' '+str(native_bounds))
        frame = Image.new('RGBA', tuple(canvas))
        frame.alpha_composite(body, tuple(position))
        if set(frame.getchannel('A').tobytes())-{0, 255}:
            raise ValueError('Embravyr exports require binary alpha')
        anchors = {'floor':list(anchor)}
        for key, point in drawing['source_anchors'].items():
            _finite_pair(point, 'anatomical point')
            anchors[key] = [round(anchor[0]+(point[0]-foot[0])*scale),
                            round(anchor[1]+(point[1]-foot[1])*scale)]
        if not {'floor', 'body', 'contact', 'cast_origin', 'core'} <= set(anchors):
            raise ValueError('Missing Embravyr anatomical anchors: '+str(index))
        drawings.append(frame)
        provenance.append({**drawing,
            'source_sha256':spec['source_sha256'][source_name],
            'native_scale':scale, 'native_bounds':native_bounds,
            'position':position, 'anchors':anchors})
    if len(drawings) != 184 or len({sha256(frame.tobytes()).digest() for frame in drawings}) != 184:
        raise ValueError('Embravyr requires 184 unique native authored drawings')
    if set(spec['animations']) != set(STATES):
        raise ValueError('Embravyr requires the ten approved animation states')

    result, animations, ordered_frames, review_frames, used = {}, {}, [], [], []
    for state in STATES:
        animation_spec = spec['animations'][state]
        indices = animation_spec['drawings']
        count = len(indices)
        if count != COUNTS[state]:raise ValueError('Wrong Embravyr pose count: '+state)
        contact = animation_spec.get('contact_frame')
        if contact is None:durations = split_time(animation_spec['duration_ms'], count)
        else:
            if type(contact) is not int or not 0 < contact < count:
                raise ValueError('Invalid Embravyr contact boundary: '+state)
            durations = (split_time(animation_spec['contact_ms'], contact)
                +split_time(animation_spec['duration_ms']-animation_spec['contact_ms'], count-contact))
        frames = []
        for number, (index, duration) in enumerate(zip(indices, durations), 1):
            if type(index) is not int or not 0 <= index < len(drawings):
                raise ValueError('Invalid Embravyr authored drawing reference')
            frame = drawings[index]
            filename = f'{state}_{number:02}.png'
            result[(OUTPUT/filename).relative_to(ROOT).as_posix()] = encoded(frame, optimize=True)
            frames.append({**provenance[index], 'file':filename, 'duration_ms':duration})
            ordered_frames.append((state, number, frame))
            used.append(index)
            review = Image.new('RGB', (480, 464), '#14231f')
            painter = ImageDraw.Draw(review)
            painter.text((12, 10), 'EMBRAVYR / '+state.replace('_', ' ')+' / '+str(number)+' of '+str(count), fill='#efd38c')
            enlarged = frame.resize((canvas[0]*3, canvas[1]*3), Image.Resampling.NEAREST)
            review.paste(enlarged, ((480-enlarged.width)//2, 30), enlarged)
            review_frames.append((review, duration))
        animations[state] = {'loop':animation_spec['loop'],
                              'duration_ms':animation_spec['duration_ms'], 'frames':frames}
        for field in ('contact_frame', 'contact_ms'):
            if field in animation_spec:animations[state][field] = animation_spec[field]
    if sorted(used) != list(range(len(drawings))):
        raise ValueError('Each authored Embravyr drawing must be used exactly once')
    sheet = Image.new('RGBA', (16*canvas[0], math.ceil(len(drawings)/16)*canvas[1]))
    contact = Image.new('RGB', (12*canvas[0], math.ceil(len(drawings)/12)*(canvas[1]+22)), '#14231f')
    painter = ImageDraw.Draw(contact)
    for index, (state, number, frame) in enumerate(ordered_frames):
        sheet.alpha_composite(frame, (index%16*canvas[0], index//16*canvas[1]))
        x, y = index%12*canvas[0], index//12*(canvas[1]+22)
        painter.text((x+4, y+3), state+' '+str(number), fill='#efd38c')
        contact.paste(frame, (x, y+22), frame)
    result[(OUTPUT/'spritesheet.png').relative_to(ROOT).as_posix()] = encoded(sheet, optimize=True)
    result[(REVIEW/'contact_sheet.png').relative_to(ROOT).as_posix()] = encoded(contact, optimize=True)
    preview_palette = Image.new('P', (1, 1))
    preview_colors = list(palette.getpalette())
    preview_colors[colors*3:(colors+2)*3] = [20, 35, 31, 239, 211, 140]
    preview_palette.putpalette(preview_colors)
    indexed = [frame.quantize(palette=preview_palette, dither=Image.Dither.NONE)
               for frame, _ in review_frames]
    result[(REVIEW/'animation.gif').relative_to(ROOT).as_posix()] = encoded(indexed[0], kind='GIF',
        save_all=True, append_images=indexed[1:], duration=[duration for _, duration in review_frames],
        loop=0, disposal=2, optimize=False)
    manifest = {'version':1, 'actor':'embravyr', 'canvas':list(canvas), 'anchor':list(anchor),
        'facing':'right', 'sheet':'spritesheet.png', 'authored_frames':len(drawings),
        'source_grid':[columns, rows], 'source_sha256':spec['source_sha256'],
        'registration':RECIPE.relative_to(ROOT).as_posix(),
        'registration_sha256':sha256(RECIPE.read_bytes()).hexdigest(),
        'native_scale':scale, 'palette_colors':colors,
        'extraction':'complete authored pose rectangles including detached fire/mineral fragments; binary alpha; shared opaque-only palette; fixed nearest-neighbor scale; explicit floor/core/contact/cast anchors',
        'animations':animations}
    result[(OUTPUT/'animation.json').relative_to(ROOT).as_posix()] = (json.dumps(manifest, indent=2)+'\n').encode()
    provenance_record = {'version':1, 'actor':'embravyr', 'generated_with':'image_gen',
        'registration':manifest['registration'], 'registration_sha256':manifest['registration_sha256'],
        'source_sha256':spec['source_sha256'], 'authored_frames':len(drawings),
        'operation':__doc__.strip(), 'frames':provenance}
    result[(OUTPUT/'provenance.json').relative_to(ROOT).as_posix()] = (json.dumps(provenance_record, indent=2)+'\n').encode()
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args(argv)
    output = products()
    changed = []
    for name, content in output.items():
        path = ROOT/name
        if not path.exists() or path.read_bytes() != content:
            changed.append(name)
            if not args.check:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
    if args.check and changed:raise SystemExit('Stale Embravyr exports: '+', '.join(changed))
    print(('Verified' if args.check else 'Built')+f' 184 unique Embravyr poses / {len(output)} exports')
    return 0


if __name__ == '__main__':raise SystemExit(main())
