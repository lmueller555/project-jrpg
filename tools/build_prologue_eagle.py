"""Export complete authored eagle poses with fixed chest registration.

The preserved sheets supply every pose. This exporter crops cells, removes
matte fringe, uniformly samples each source and applies one shared palette.
It never rotates, warps or assembles body parts.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
from io import BytesIO
import json
import math
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/cinematics/fire_veinhold/shot01/eagle'
TARGET = ROOT/'assets/story/fire_veinhold_opening/shot01/eagle'
CANVAS = (256, 256)
ANCHOR = (128, 144)
SOURCE_GRIDS = {'flap': (4, 4), 'bank': (4, 2)}
SEQUENCES = ('flap', 'bank', 'glide')


def _json(value):
    return (json.dumps(value, indent=2)+'\n').encode()


def _png(image):
    buffer = BytesIO()
    image.save(buffer, 'PNG', optimize=False, compress_level=9)
    return buffer.getvalue()


def _source_path(source, filename):
    if not isinstance(filename, str) or not filename:
        raise ValueError('Eagle source requires a relative filename')
    candidate = source/filename
    if Path(filename).is_absolute() or not candidate.resolve().is_relative_to(source.resolve()):
        raise ValueError('Eagle source must remain inside its source directory')
    return candidate


def _numbers(value, length):
    return (isinstance(value, list) and len(value) == length
            and all(type(number) in (int, float) and math.isfinite(number)
                    for number in value))


def _clean(image, threshold):
    """Discard transparent generation haze and the specified red/green matte."""
    image = image.convert('RGBA')
    reader = getattr(image, 'get_flattened_data', None)
    pixels = reader() if reader is not None else image.getdata()
    result = Image.new('RGBA', image.size)
    result.putdata([
        (0, 0, 0, 0) if (alpha < threshold
            or (red >= 180 and red > 2.5*green and red > 2.5*blue)
            or (green >= 80 and green > 1.3*red and green > 1.8*blue))
        else (red, green, blue, 255)
        for red, green, blue, alpha in pixels
    ])
    return result


def _durations(sequence, count):
    if 'duration_ms' in sequence and 'durations_ms' in sequence:
        raise ValueError('Eagle sequence must use one duration format')
    if 'durations_ms' in sequence:
        values = sequence['durations_ms']
    else:
        values = [sequence.get('duration_ms')]*count
    if (not isinstance(values, list) or len(values) != count
            or any(type(value) is not int or value <= 0 for value in values)):
        raise ValueError('Eagle sequence needs one positive duration per frame')
    return values


def products(source=SOURCE, target=TARGET):
    """Return deterministic runtime products without writing any files."""
    source, target = Path(source), Path(target)
    recipe_bytes = (source/'recipe.json').read_bytes()
    recipe = json.loads(recipe_bytes)
    if (recipe.get('version') != 1 or recipe.get('canvas') != list(CANVAS)
            or recipe.get('anchor') != list(ANCHOR) or recipe.get('density') != 2):
        raise ValueError('Eagle requires version one, 256-pixel canvas, chest anchor and density two')
    if recipe.get('alpha_threshold') != 128 or recipe.get('palette_colors') != 128:
        raise ValueError('Eagle requires binary alpha at 128 and one 128-colour palette')
    if set(recipe.get('sources', {})) != set(SOURCE_GRIDS):
        raise ValueError('Eagle requires preserved flap and bank source sheets')
    if set(recipe.get('sequences', {})) != set(SEQUENCES):
        raise ValueError('Eagle requires flap, bank and glide sequences')

    frames = {}
    records = {}
    source_records = {}
    for name, grid in SOURCE_GRIDS.items():
        spec = recipe['sources'][name]
        if spec.get('grid') != list(grid):
            raise ValueError('Eagle source has an incorrect cell grid: '+name)
        scale = spec.get('scale')
        chest = spec.get('chest_anchor')
        if (type(scale) not in (int, float) or not math.isfinite(scale) or scale <= 0
                or not _numbers(chest, 2)):
            raise ValueError('Eagle source requires one positive scale and fixed chest landmark: '+name)
        path = _source_path(source, spec.get('file'))
        raw = path.read_bytes()
        if sha256(raw).hexdigest() != spec.get('sha256'):
            raise ValueError('Eagle source changed without a recipe update: '+path.name)
        with Image.open(BytesIO(raw)) as original:
            sheet = original.convert('RGBA')
        columns, rows = grid
        sampling_canvas = (math.ceil(sheet.width/columns), math.ceil(sheet.height/rows))
        source_records[name] = {'file':spec['file'], 'sha256':spec['sha256'],
                                'dimensions':list(sheet.size), 'grid':list(grid),
                                'scale':scale, 'chest_anchor':chest,
                                'sampling_canvas':list(sampling_canvas)}
        for landmark in ('head_landmark', 'tail_landmark'):
            if landmark in spec:
                if not _numbers(spec[landmark], 2):
                    raise ValueError('Eagle source landmark must have two finite coordinates')
                source_records[name][landmark] = spec[landmark]
        for cell in range(columns*rows):
            column, row = cell % columns, cell // columns
            crop = [round(column*sheet.width/columns), round(row*sheet.height/rows),
                    round((column+1)*sheet.width/columns), round((row+1)*sheet.height/rows)]
            if not 0 <= chest[0] < crop[2]-crop[0] or not 0 <= chest[1] < crop[3]-crop[1]:
                raise ValueError('Eagle chest landmark lies outside its source cell: '+name)
            drawing = _clean(sheet.crop(crop), recipe['alpha_threshold'])
            source_bounds = drawing.getbbox()
            if source_bounds is None:
                raise ValueError(f'Empty authored eagle pose: {name} cell {cell}')
            # Fractional sheet grids have one-pixel cell-size differences.
            # Transparent padding keeps the sampling ratio fixed per source.
            if drawing.size != sampling_canvas:
                padded = Image.new('RGBA', sampling_canvas)
                padded.paste(drawing, (0, 0))
                drawing = padded
            size = (round(drawing.width*scale), round(drawing.height*scale))
            if min(size) <= 0:
                raise ValueError('Eagle source scale creates an empty frame')
            # These are source landmarks, never the changing feather bounds.
            scaled_chest = [round(coordinate*scale) for coordinate in chest]
            offset = [ANCHOR[index]-scaled_chest[index] for index in range(2)]
            drawing = drawing.resize(size, Image.Resampling.NEAREST)
            bounds = drawing.getbbox()
            if bounds is None:
                raise ValueError(f'Eagle sampling erased its complete pose: {name} cell {cell}')
            occupied = [bounds[0]+offset[0], bounds[1]+offset[1],
                        bounds[2]+offset[0], bounds[3]+offset[1]]
            if not 0 <= occupied[0] < occupied[2] <= CANVAS[0] or not 0 <= occupied[1] < occupied[3] <= CANVAS[1]:
                raise ValueError(f'Eagle canvas clips the authored pose: {name} cell {cell}')
            registered = Image.new('RGBA', CANVAS)
            registered.paste(drawing, tuple(offset))
            filename = f'{name}_{cell+1:02}.png'
            frames[filename] = registered
            records[filename] = {'source':name, 'cell':cell, 'crop':crop,
                'source_occupied_bounds':list(source_bounds), 'scaled_canvas':list(size),
                'scaled_chest_anchor':scaled_chest, 'offset':offset,
                'occupied_bounds':occupied}

    # Every base drawing contributes to the same deterministic palette.
    atlas = Image.new('RGBA', (CANVAS[0]*4, CANVAS[1]*6))
    for index, frame in enumerate(frames.values()):
        atlas.paste(frame, ((index % 4)*CANVAS[0], (index // 4)*CANVAS[1]))
    indexed = atlas.convert('RGB').quantize(colors=recipe['palette_colors'],
        method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    palette = indexed.getpalette()
    manifest = {'version':1, 'canvas':list(CANVAS), 'anchor':list(ANCHOR),
                'density':2, 'sequences':{}}
    for name in SEQUENCES:
        sequence = recipe['sequences'][name]
        source_name, cells = sequence.get('source'), sequence.get('cells')
        count = 16 if name == 'flap' else 8 if name == 'bank' else 2
        if (source_name != ('flap' if name == 'flap' else 'bank')
                or not isinstance(cells, list) or len(cells) != count
                or any(type(cell) is not int or not 0 <= cell < math.prod(SOURCE_GRIDS[source_name])
                       for cell in cells)
                or len(set(cells)) != count):
            raise ValueError('Eagle sequence has invalid authored cells: '+name)
        if type(sequence.get('loop')) is not bool or sequence['loop'] != (name != 'bank'):
            raise ValueError('Eagle sequence has an incorrect loop boundary: '+name)
        if name == 'glide' and cells != [6, 7]:
            raise ValueError('Eagle glide must reuse the two terminal bank poses')
        filenames = sequence.get('frame_files',
            [f'{source_name}_{cell+1:02}.png' for cell in cells])
        if (not isinstance(filenames, list) or len(filenames) != count
                or any(not isinstance(filename, str) or filename not in frames
                       for filename in filenames)):
            raise ValueError('Eagle sequence must reference exported complete poses: '+name)
        manifest['sequences'][name] = {'loop':sequence['loop'], 'frames':[
            {'file':filename, 'duration_ms':duration}
            for filename, duration in zip(filenames, _durations(sequence, count))]}
    if 'timing' in recipe:
        timing = recipe['timing']
        period = sum(frame['duration_ms'] for frame in manifest['sequences']['flap']['frames'])
        if (not isinstance(timing, dict) or timing.get('period_ms') != period
                or any(type(timing.get(name)) is not int or not 0 <= timing[name] < period
                       for name in ('first_phase_ms', 'second_phase_ms'))
                or type(timing.get('downstroke_phase')) not in (int, float)
                or not math.isfinite(timing['downstroke_phase'])
                or not 0 <= timing['downstroke_phase'] <= 1):
            raise ValueError('Eagle timing must match its complete flap period and phase bounds')
        manifest['timing'] = timing

    output = {}
    for index, (filename, frame) in enumerate(frames.items()):
        left, top = (index % 4)*CANVAS[0], (index // 4)*CANVAS[1]
        result = indexed.crop((left, top, left+CANVAS[0], top+CANVAS[1])).convert('RGBA')
        result.putalpha(frame.getchannel('A'))
        output[target/filename] = _png(result)
    provenance = {'version':1, 'recipe_sha256':sha256(recipe_bytes).hexdigest(),
        'canvas':list(CANVAS), 'anchor':list(ANCHOR), 'density':2,
        'alpha_threshold':recipe['alpha_threshold'], 'palette_colors':recipe['palette_colors'],
        'matte_cleanup':{'red':'r >= 180 and r > 2.5*g and r > 2.5*b',
                         'green':'g >= 80 and g > 1.3*r and g > 1.8*b'},
        'palette_sha256':sha256(bytes(palette)).hexdigest(), 'palette_rgb':palette,
        'sources':source_records, 'frames':records,
        'sequence_sources':recipe['sequences']}
    output[target/'animation.json'] = _json(manifest)
    output[target/'export_provenance.json'] = _json(provenance)
    return output


def build(check=False, *, source=SOURCE, target=TARGET):
    output = products(source=source, target=target)
    changed = [path for path, data in output.items() if not path.is_file() or path.read_bytes() != data]
    if check and changed:
        raise ValueError('Stale prologue eagle exports: '+', '.join(path.name for path in changed))
    if not check:
        for path, data in output.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    build(check=parser.parse_args().check)
