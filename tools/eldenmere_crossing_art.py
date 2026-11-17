"""Authored, span-aware Eldenmere crossings at two artwork pixels/world unit.

This module owns artwork, never collision or travel. ``crossing_assemblies`` is
pure: the town composer places ``ground`` after water in EVERY phase and draws
``near_rail`` at its existing foreground origin. The small source export command
writes only the crossing source bank; the maintained town builder owns gameplay.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path('assets/source/maps/eldenmere/town_hd/crossings')
DENSITY = 2
PALETTE = {
    'outline': '#181b16', 'wood_dark': '#4f3c29', 'wood_joint': '#735431',
    'wood_base': '#9b7548', 'wood_mid': '#a98350', 'wood_light': '#b8935d',
    'wood_worn': '#c8a66e', 'wood_grain': '#8a663c', 'iron': '#4a4c47',
    'iron_light': '#909487', 'stone_dark': '#65675a', 'stone': '#979985',
    'stone_light': '#b2af96', 'shadow': '#17291e',
}

# These are authoring contracts, not inferred alpha/collision bounds. Coordinates
# are logical/world units, with exclusive right/bottom rectangle endpoints.
CONTRACTS = (
    {'id': 'upper_bridge', 'position': [768, 444], 'logical_size': [144, 72],
     'orientation': 'east-west', 'walk_surface': [0, 12, 144, 48],
     'bank_endpoints_world': [[768, 480], [912, 480]],
     'bank_overlap_world': [[768, 456, 48, 48], [888, 456, 24, 48]],
     'water_beside_samples_world': [[850, 432], [850, 528]],
     'preserved_clear_rows_world': [456, 504]},
    {'id': 'main_bridge', 'position': [744, 996], 'logical_size': [168, 72],
     'orientation': 'east-west', 'walk_surface': [0, 12, 168, 48],
     'bank_endpoints_world': [[744, 1032], [912, 1032]],
     'bank_overlap_world': [[744, 1008, 48, 48], [864, 1008, 48, 48]],
     'water_beside_samples_world': [[850, 984], [850, 1080]],
     'preserved_clear_rows_world': [1008, 1056]},
    {'id': 'mill_landing', 'position': [948, 318], 'logical_size': [48, 72],
     'orientation': 'north-south', 'walk_surface': [0, 12, 48, 48],
     'bank_endpoints_world': [[971, 330], [971, 378]],
     'bank_overlap_world': [[948, 330, 48, 12], [948, 360, 48, 18]],
     'water_beside_samples_world': [[930, 348], [1008, 348]],
     'door_anchor_world': [971, 342], 'road_connection_world': [972, 384],
     'clear_approach_world': [960, 330, 24, 54],
     'exterior_interface': {'deck_world': [948, 330, 48, 48],
                            'door_opening_world': [962, 311, 18, 31],
                            'wheel_west_world': 1024,
                            'remove_old_fence_world': [938, 345, 20, 14]}},
)


def _new(size):
    return Image.new('RGBA', tuple(v * DENSITY for v in size))


def _rect(draw, xy, color):
    """Exclusive logical rectangle, sampled without fractional transforms."""
    x, y, w, h = xy
    draw.rectangle((round(x * 2), round(y * 2), round((x + w) * 2) - 1,
                    round((y + h) * 2) - 1), fill=PALETTE.get(color, color))


def board_section(variant=0):
    """One deliberately drawn 12×48 logical tread board, not a donor resize."""
    im = _new((12, 48)); d = ImageDraw.Draw(im)
    _rect(d, (0, 0, 12, 48), 'wood_base' if variant % 3 else 'wood_mid')
    # Joints are one artwork pixel, not character-weight black borders.
    d.line((0, 0, 0, 95), fill=PALETTE['wood_joint'])
    d.line((1, 1, 1, 94), fill=PALETTE['wood_light'])
    d.line((23, 1, 23, 94), fill=PALETTE['wood_dark'])
    # Long purposeful grain clusters. Their ends do not tile into noise.
    for x, y, length in ((5, 12, 20), (17, 40, 24), (10, 69, 14)):
        yy = y + (variant % 3) * 3
        d.line((x, yy, x, min(92, yy + length)), fill=PALETTE['wood_grain'])
        d.line((x + 1, yy + 4, x + 1, min(92, yy + length - 3)), fill=PALETTE['wood_mid'])
    if variant % 3 == 1:
        # A small closed knot, still at exactly the common board scale.
        d.line((13, 30, 15, 28, 17, 30, 17, 34, 15, 36, 13, 34, 13, 30),
               fill=PALETTE['wood_grain'], width=1)
        d.line((15, 30, 15, 34), fill=PALETTE['wood_joint'])
    for x, y in ((5, 6), (18, 6), (5, 88), (18, 88)):
        d.point((x, y), fill=PALETTE['iron'])
        d.point((x, y - 1), fill=PALETTE['wood_worn'])
    return im


def post_section():
    """3×13 logical rail post: 11-unit rise and a two-unit cap/foot."""
    im = _new((3, 13)); d = ImageDraw.Draw(im)
    _rect(d, (0, 0, 3, 13), 'outline')
    _rect(d, (.5, .5, 2, 12), 'wood_dark')
    _rect(d, (.5, 1, 1, 11), 'wood_light')
    _rect(d, (1.5, 1, .5, 11), 'wood_base')
    _rect(d, (.5, .5, 2, 1), 'wood_worn')
    _rect(d, (.5, 9, 2, 1), 'iron')
    d.point((2, 18), fill=PALETTE['iron_light'])
    return im


def rail_section(length=24):
    """Two horizontal 2-unit timber rails in a standard 24-unit bay."""
    im = _new((length, 13)); d = ImageDraw.Draw(im)
    for y in (2, 8):
        _rect(d, (0, y, length, 2.5), 'outline')
        _rect(d, (0, y + .5, length, 1.5), 'wood_base')
        _rect(d, (0, y + .5, length, .5), 'wood_worn')
        _rect(d, (0, y + 2, length, .5), 'wood_dark')
    return im


def _post_centers(width):
    return [*range(3, width - 3, 24), width - 3]


def _horizontal_rail(width, ground_y):
    im = _new((width, 72)); centers = _post_centers(width)
    # Whole authored bays plus one short closing bay. No post/board is scaled.
    for a, b in zip(centers, centers[1:]):
        im.alpha_composite(rail_section(b - a), (a * 2, (ground_y - 11) * 2))
    post = post_section()
    for x in centers:
        im.alpha_composite(post, (x * 2 - 3, (ground_y - 11) * 2))
    return im, centers


def _side_rail(width, ground_x):
    """North/south rail; only its raised timber projects upward, never inward."""
    im = _new((width, 72)); d = ImageDraw.Draw(im)
    # Side-facing timber is narrow in x. The top face is exposed at the left.
    _rect(d, (ground_x - 1, 3, 2, 48), 'outline')
    _rect(d, (ground_x - .5, 3, 1, 48), 'wood_base')
    _rect(d, (ground_x - .5, 3, .5, 48), 'wood_worn')
    # A lower stretcher reads through the three well-spaced posts.
    _rect(d, (ground_x - 1, 9, 2, 48), 'wood_dark')
    _rect(d, (ground_x - .5, 9, .5, 48), 'wood_mid')
    post = post_section()
    for y in (12, 36, 60):
        im.alpha_composite(post, (round(ground_x * 2) - 3, (y - 11) * 2))
    return im


def _deck(width, orientation):
    im = _new((width, 72)); surface = _new((width, 48))
    if orientation == 'east-west':
        for i in range(width // 12):
            surface.alpha_composite(board_section(i % 3), (i * 24, 0))
    else:
        # Square tread boards are drawn in the other cardinal direction, with
        # exact quarter-turn pixels, never a perspective or nonuniform resize.
        for i in range(4):
            section = board_section(i % 3).transpose(Image.Transpose.ROTATE_90)
            surface.alpha_composite(section, (0, i * 24))
    im.alpha_composite(surface, (0, 24)); d = ImageDraw.Draw(im)
    # Four-unit flush stone abutments overlap each physical bank. They do not
    # invent a stair/step in an otherwise level crossing.
    ends = ((0, 12, 4, 48), (width - 4, 12, 4, 48)) if orientation == 'east-west' else ((0, 12, width, 4), (0, 56, width, 4))
    for x, y, w, h in ends:
        _rect(d, (x, y, w, h), 'stone_dark')
        _rect(d, (x + .5, y + .5, w - 1, h - 1), 'stone')
        _rect(d, (x + .5, y + .5, w - 1, .5), 'stone_light')
        if orientation == 'east-west':
            for yy in (28, 44):
                _rect(d, (x + .5, yy, w - 1, .5), 'stone_dark')
        else:
            for xx in (16, 32):
                _rect(d, (xx, y + .5, .5, h - 1), 'stone_dark')
    # One-artwork-pixel outer contour. The visible face is only three logical
    # units deep beneath 48 units of top surface, not a frontal platform.
    d.rectangle((0, 24, width * 2 - 1, 119), outline=PALETTE['outline'], width=1)
    _rect(d, (0, 60, width, 3), 'outline')
    _rect(d, (.5, 60, width - 1, 2.5), 'wood_dark')
    _rect(d, (.5, 60, width - 1, .5), 'wood_mid')
    for x in range(12, width, 12):
        _rect(d, (x, 60.5, .5, 2), 'wood_joint')
    return im


@dataclass(frozen=True)
class CrossingArt:
    id: str
    position: tuple[int, int]
    logical_size: tuple[int, int]
    deck: Image.Image
    far_rail: Image.Image
    near_rail: Image.Image
    contact_shadow: Image.Image
    metadata: dict

    @property
    def ground(self):
        """After-water assembly, underneath every actor and normal foreground."""
        out = self.contact_shadow.copy()
        out.alpha_composite(self.deck)
        out.alpha_composite(self.far_rail)
        return out


def _bounds_logical(im):
    box = im.getchannel('A').getbbox()
    return [v / 2 for v in box] if box else None


def _coverage(im, rect):
    x, y, w, h = rect
    alpha = im.getchannel('A').crop((x * 2, y * 2, (x + w) * 2, (y + h) * 2))
    return alpha.histogram()[255] / (w * h * 4)


def crossing_assemblies():
    """Return fresh, reproducible native images plus explicit world contracts."""
    result = {}
    for contract in CONTRACTS:
        meta = json.loads(json.dumps(contract)); name = meta['id']; width = meta['logical_size'][0]
        deck = _deck(width, meta['orientation']); shade = _new((width, 72))
        d = ImageDraw.Draw(shade)
        # Partial alpha is confined to an explicit small contact-shadow layer.
        _rect(d, (1, 63, width - 2, 1), (23, 41, 30, 72))
        if meta['orientation'] == 'east-west':
            far, centers = _horizontal_rail(width, 12)
            near, _ = _horizontal_rail(width, 60)
            meta['rails_logical'] = {'far_ground_y': 12, 'near_ground_y': 60,
                                     'rise': 11, 'post_centers_x': centers,
                                     'standard_bay': 24, 'post_width': 3,
                                     'near_occupied_y': [49, 62]}
        else:
            far = _side_rail(width, 3); near = _side_rail(width, width - 3)
            meta['rails_logical'] = {'far_ground_x': 3, 'near_ground_x': 45,
                                     'rise': 11, 'post_centers_y': [12, 36, 60],
                                     'standard_bay': 24, 'post_width': 3,
                                     'clear_middle_x': [12, 36]}
        meta.update(artwork_pixels_per_world_pixel=2,
                    artwork_size_pixels=[width * 2, 144],
                    geometry_space='logical world units; rectangles x/y/width/height',
                    draw_anchor_logical=[0, 0],
                    depth_baseline_world=meta['position'][1] + 60,
                    assembly_order=['water_phase', 'contact_shadow', 'deck', 'far_rail', 'actors', 'near_rail'],
                    collision_owner='existing town collision; this generator does not change it',
                    reduced_motion='same assembly after the selected still water phase',
                    design_status='authored; native gameplay review required by integrating PR')
        meta['occupied_artwork'] = {k: {'bounds_logical_xyxy': _bounds_logical(im),
                                       'opaque_pixel_count': im.getchannel('A').histogram()[255]}
                                    for k, im in (('deck', deck), ('far_rail', far), ('near_rail', near))}
        meta['walking_surface_opaque_coverage'] = _coverage(deck, meta['walk_surface'])
        result[name] = CrossingArt(name, tuple(meta['position']), tuple(meta['logical_size']),
                                   deck, far, near, shade, meta)
    return result


def _png(im):
    stream = BytesIO(); im.save(stream, format='PNG'); return stream.getvalue()


def _diagram(assembly):
    """A labelled 960×640 orthogonal construction diagram, NOT gameplay."""
    out = Image.new('RGBA', (960, 640), '#23322a'); d = ImageDraw.Draw(out)
    font = ImageFont.load_default()
    d.text((24, 20), 'CONSTRUCTION DIAGRAM - NOT GAMEPLAY | native 2x | 24-unit ground grid', fill='#eee5c6', font=font)
    d.text((24, 42), assembly.id + ' | full-scale artwork, Caelan and explicit ground contracts', fill='#eee5c6', font=font)
    # Local artwork is shown without resampling, with world origin at (288,208).
    ox, oy = (288, 208) if assembly.id != 'mill_landing' else (432, 208)
    surface = assembly.metadata['walk_surface']; width = assembly.logical_size[0]
    if assembly.metadata['orientation'] == 'east-west':
        d.rectangle((ox + 48, 96, ox + width * 2 - 49, 568), fill='#537f86')
        d.rectangle((40, oy + 24, 920, oy + 119), fill='#a28a60')
        d.rectangle((ox + 48, oy - 100, ox + width * 2 - 49, oy + 200), fill='#537f86')
    else:
        d.rectangle((64, oy + 48, 896, oy + 71), fill='#537f86')
        d.rectangle((ox + 24, oy - 60, ox + 71, 568), fill='#a28a60')
    for x in range(0, 960, 48): d.line((x, 82, x, 568), fill='#68806a')
    for y in range(112, 569, 48): d.line((32, y, 928, y), fill='#68806a')
    out.alpha_composite(assembly.ground, (ox, oy))
    actor_path = ROOT/'assets/characters/caelan/review_hd/idles/idle_front.png'
    if actor_path.exists():
        actor = Image.open(actor_path).convert('RGBA')
        # Two physical positions explain centre-vs-near lower-leg occlusion.
        for px, py in ((width / 2, 36), (width / 2 + (30 if width > 48 else 0), 57)):
            out.alpha_composite(actor, (round(ox + px * 2 - 24), round(oy + py * 2 - 60)))
    out.alpha_composite(assembly.near_rail, (ox, oy))
    d = ImageDraw.Draw(out)
    x, y, w, h = surface
    d.rectangle((ox + x * 2, oy + y * 2, ox + (x + w) * 2 - 1, oy + (y + h) * 2 - 1), outline='#f4d35c', width=1)
    d.text((24, 586), f'Solid top {w}x{h} logical | origin {assembly.position} | opaque walking coverage 100%', fill='#eee5c6', font=font)
    d.text((24, 607), 'Yellow: walking-surface envelope. Grid/labels are review aids, never exported into gameplay.', fill='#eee5c6', font=font)
    return out


def products():
    """Reproducible retained sources, recipe, metrics and clearly named diagrams."""
    products = {}; records = []; assemblies = crossing_assemblies()
    for a in assemblies.values():
        for role in ('deck', 'far_rail', 'near_rail', 'contact_shadow', 'ground'):
            products[SOURCE/f'{a.id}/{role}.png'] = _png(getattr(a, role))
        products[SOURCE/f'{a.id}/construction_diagram.png'] = _png(_diagram(a))
        records.append(a.metadata)
    for name, im in (('board_a', board_section(0)), ('board_b', board_section(1)),
                     ('board_c', board_section(2)), ('rail_bay_24', rail_section()),
                     ('post', post_section())):
        products[SOURCE/f'sections/{name}.png'] = _png(im)
    recipe = {
        'version': 1, 'artwork_status': 'authored', 'runtime_status': 'integrating PR2 owns selection',
        'generator': 'tools/eldenmere_crossing_art.py',
        'generator_sha256': sha256(Path(__file__).read_bytes()).hexdigest(),
        'preview_dependency': {'file': 'assets/characters/caelan/review_hd/idles/idle_front.png',
                               'sha256': sha256((ROOT/'assets/characters/caelan/review_hd/idles/idle_front.png').read_bytes()).hexdigest()},
        'palette': PALETTE,
        'construction': 'Direct native-pixel authored board, two-rail bay, post, flush bank ends and shallow fascia; no donor fitting, perspective warp, or nonuniform scaling.',
        'coordinate_space': 'positions and geometry logical/world; exported PNGs 2 artwork pixels per logical unit',
        'crossings': records,
        'review': {'diagrams': 'construction_diagram.png files are not gameplay captures',
                   'gameplay': 'Integration owner must capture stationary, walking/running, both rails, every water phase and reduced motion with the actual Game renderer.'},
        'exports': [{'file': str(p.relative_to(SOURCE)), 'sha256': sha256(data).hexdigest()}
                    for p, data in sorted(products.items())],
    }
    products[SOURCE/'recipe.json'] = (json.dumps(recipe, indent=2) + '\n').encode()
    return products


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='non-writing reproducibility check')
    args = parser.parse_args(); stale = []
    for path, data in products().items():
        path = ROOT/path
        if args.check:
            if not path.exists() or path.read_bytes() != data: stale.append(str(path.relative_to(ROOT)))
        else:
            path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
    if stale:
        raise SystemExit('Stale crossing source exports:\n' + '\n'.join(stale))
    print('Crossing source exports ' + ('verified' if args.check else 'written'))


if __name__ == '__main__':
    main()
