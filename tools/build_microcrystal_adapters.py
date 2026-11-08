"""Build additional wall-seam geometries from the approved native microfacets.

Only grain positions change. Source pixel crops retain their original size,
facet orientation and six brightness frames. Every field stays transparent so
the dungeon's limestone remains visible between the tiny separated grains.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/terrain/limestone_cave/micro_adapters.json'
PACK = 'assets/terrain/limestone_cave/micro_adapters'


def png(image):
    output = BytesIO();image.save(output, format='PNG');return output.getvalue()


def products():
    spec = json.loads(SOURCE.read_text())
    manifest_path = ROOT/spec['source_manifest']
    approved = json.loads(manifest_path.read_text())
    used = {SOURCE, manifest_path, ROOT/spec['wall_texture'], ROOT/spec['character']}
    output = {};modules = {};images = {}

    def opened(path):
        full = ROOT/path;used.add(full)
        if full not in images:
            with Image.open(full) as image:images[full] = image.convert('RGBA')
        return images[full]

    def emit(path, value):
        output[path] = (png(value) if isinstance(value, Image.Image) else
                        (json.dumps(value, indent=2)+'\n').encode())

    def source_module(color, pattern):
        return approved['modules'][f"wall_gem.{color}.{pattern['source_variant']}"]

    def validate(pattern):
        width, height = pattern['size'];rects = pattern['crystals']
        if len(rects) != pattern['count']:raise ValueError('Wrong seam grain count')
        if len(pattern['source_grain_ordinals']) != len(rects):raise ValueError('Missing source grain')
        for ordinal, (x, y, w, h) in enumerate(rects):
            if not (0 < w <= spec['grain_limits']['max_width'] and
                    0 < h <= spec['grain_limits']['max_height'] and
                    1 <= x < x+w < width and 1 <= y < y+h < height):
                raise ValueError('Microcrystal grain exceeds its native bounds')
            for ox, oy, ow, oh in rects[ordinal+1:]:
                if not (x+w < ox or ox+ow < x or y+h < oy or oy+oh < y):
                    raise ValueError('Microcrystal grains must remain separated')

    def render(color, pattern, level):
        image = Image.new('RGBA', tuple(pattern['size']))
        draw = ImageDraw.Draw(image)
        for path in pattern['paths']:
            draw.line([tuple(point) for point in path], fill='#414842', width=1)
        source = source_module(color, pattern)
        source_image = opened(source['frames'][level])
        for ordinal, (x, y, w, h) in enumerate(pattern['crystals']):
            sx, sy, sw, sh = source['core_components'][pattern['source_grain_ordinals'][ordinal]]
            if (w, h) != (sw, sh):raise ValueError('Source microfacet would need rescaling')
            # These are exact source pixels, copied without rotations or resize.
            grain = source_image.crop((sx, sy, sx+sw, sy+sh))
            image.alpha_composite(grain, (x, y))
            if ordinal % 3 == 0:draw.point((x-1, y+1), fill='#72786e')
        return image

    for name, pattern in spec['patterns'].items():validate(pattern)
    for color in spec['colors']:
        palette = approved['colors'][color]
        for name, pattern in spec['patterns'].items():
            frames = []
            for level in range(spec['pulse_frames']):
                path = f'{PACK}/{color}/{name}/frame_{level:02}.png'
                emit(path, render(color, pattern, level));frames.append(path)
            rects = pattern['crystals']
            left = min(rect[0] for rect in rects);top = min(rect[1] for rect in rects)
            right = max(x+w for x, y, w, h in rects);bottom = max(y+h for x, y, w, h in rects)
            modules[f'micro.{color}.{name}'] = {
                'frames': frames, 'size': pattern['size'], 'anchor': pattern['anchor'],
                'footprints': [], 'color': palette['light'], 'gem_color': color,
                'label': palette['label']+' '+name.replace('_', ' '),
                'description': pattern['description'], 'pattern': name,
                'orientation': name, 'connection_ports': pattern['connection_ports'],
                'emission_bounds': [left, top, right-left, bottom-top],
                'core_components': rects, 'crystal_sizes': [[r[2], r[3]] for r in rects],
                'crystal_count': len(rects), 'mount': 'embedded_wall',
                'representation': 'embedded_microcrystal_adapters',
                'frame_duration_ms': 600, 'reduced_motion_frame': 4,
                'pulse_frames': spec['pulse_frames'],
                'source_module': f"wall_gem.{color}.{pattern['source_variant']}",
                'source_grain_ordinals': pattern['source_grain_ordinals'],
            }

    wall = opened(spec['wall_texture']);character = opened(spec['character'])
    names = list(spec['patterns']);colors = spec['colors']
    title_font = ImageFont.load_default(size=19);label_font = ImageFont.load_default(size=15)
    small_font = ImageFont.load_default(size=13)

    def board(level):
        image = Image.new('RGB', (1380, 1410), '#25312e');draw = ImageDraw.Draw(image)
        draw.text((18, 14), 'MICROCRYSTAL SEAM ADAPTERS / native facets, all specimens enlarged exactly 2x',
                  font=title_font, fill='#ece3ce')
        draw.text((18, 42), 'Six colors; fixed tiny grains; new seam directions and mineral densities.',
                  font=label_font, fill='#c6d2c5')
        for col, color in enumerate(colors):
            draw.text((160+col*196, 74), color.title(), font=label_font, fill='#ece3ce')
        for row, name in enumerate(names):
            pattern = spec['patterns'][name];y = 105+row*169
            for line, word in enumerate(name.replace('_', ' ').split()):
                draw.text((18, y+12+line*20), word.title(), font=label_font, fill='#e7dfc9')
            draw.text((18, y+64), f"{len(pattern['crystals'])} grains", font=small_font, fill='#b9c8ba')
            for col, color in enumerate(colors):
                width, height = pattern['size']
                panel = Image.new('RGBA', (width, height))
                for py in range(height):
                    for px in range(width):
                        pixel = wall.getpixel(((px+row*11)%wall.width, (py+13)%wall.height))
                        panel.putpixel((px, py), pixel if pixel[3] else (137,139,122,255))
                panel.alpha_composite(render(color, pattern, level))
                scaled = panel.resize((width*2, height*2), Image.Resampling.NEAREST)
                image.paste(scaled, (160+col*196+(176-width*2)//2, y+4), scaled)
        draw.line((18, 1300, 1360, 1300), fill='#64786c')
        ca = character.resize((character.width*2, character.height*2), Image.Resampling.NEAREST)
        image.paste(ca, (1300, 1313), ca)
        draw.text((18, 1316), 'Facet pixels are copied directly from the current microcrystal pack.', font=label_font, fill='#e7dfc9')
        draw.text((18, 1341), 'Most grains are 2 x 3 native pixels. None exceeds 4 x 5. No grain is rotated or resized.',
                  font=label_font, fill='#c6d2c5')
        draw.text((1175, 1384), 'Caelan / same 2x scale', font=small_font, fill='#e7dfc9')
        return image

    boards = [board(level) for level in range(spec['pulse_frames'])]
    emit(f'{PACK}/modules_review.png', boards[-1])
    # A complete six-second breath, preserving all labels and native geometry.
    cycle = [boards[index] for index in (0,1,2,3,4,5,4,3,2,1)]
    stream = BytesIO()
    cycle[0].save(stream, format='GIF', save_all=True, append_images=cycle[1:],
                  duration=600, loop=0, optimize=False, disposal=2)
    output[f'{PACK}/modules_review.gif'] = stream.getvalue()
    output[f'{PACK}/README.md'] = (
        '# Microcrystal seam adapters\n\n'
        'Status: additions pending review. The existing cave and approved microcrystal fields are unchanged.\n\n'
        'Seven new field patterns support vertical and diagonal fractures, concave and convex wall turns, '
        'sparse isolated grains and denser mineral pockets. Every pattern is provided in Red, Blue, Green, '
        'White, Orange and Purple.\n\n'
        'All individual facets reuse exact native pixel crops from the existing microcrystal pack. '
        'Their size, shading direction and six brightness levels are preserved; only their positions change. '
        'Fields are transparent, with fixed neutral hairline crevices and no floor footprints.\n\n'
        '`assets.json` records anchors, core rectangles, grain counts, color light values and semantic '
        'connection ports. Place the colored cores within rock faces and assign a nearby exposed floor '
        'light root using the existing cave renderer. `frame_duration_ms` describes review playback; '
        'production crystal lighting selects frames from its shared six-second pulse.\n\n'
        'The PNG and GIF boards display every new field at exactly 2x native scale with Caelan for reference.\n\n'
        'Rebuild with `python tools/build_microcrystal_adapters.py`; add `--check` for a read-only '
        'deterministic verification. The authoritative source is '
        '`assets/source/terrain/limestone_cave/micro_adapters.json`.\n'
    ).encode()
    inputs = {str(path.relative_to(ROOT)): sha256(path.read_bytes()).hexdigest() for path in sorted(used)}
    manifest = {'version': 1, 'id': spec['id'], 'approval_status': spec['approval_status'],
                'tile_size': 24, 'representation': 'embedded_microcrystal_adapters',
                'grain_limits': spec['grain_limits'], 'pulse_frames': spec['pulse_frames'],
                'colors': approved['colors'], 'source_recipe': str(SOURCE.relative_to(ROOT)),
                'modules': modules, 'inputs': inputs,
                'artifacts': {path: sha256(raw).hexdigest() for path, raw in output.items()}}
    emit(f'{PACK}/assets.json', manifest)
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true');args = parser.parse_args(argv)
    output = products();changed = []
    for relative, raw in output.items():
        path = ROOT/relative
        if not path.exists() or path.read_bytes() != raw:
            changed.append(relative)
            if not args.check:path.parent.mkdir(parents=True, exist_ok=True);path.write_bytes(raw)
    if args.check and changed:raise SystemExit('Stale microcrystal adapter exports: '+', '.join(changed))
    print(('Verified' if args.check else 'Built')+f' {len(output)} microcrystal adapter exports')
    return 0


if __name__ == '__main__':raise SystemExit(main())
