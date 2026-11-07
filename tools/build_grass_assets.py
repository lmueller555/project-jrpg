"""Export the approved shared emerald terrain and interactive vegetation pack.

The reviewed native art functions are reused so promotion cannot subtly change
the approved pixels. Original source packs and the review prototype stay intact.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

try:
    from .build_grass_demo_assets import blade_frame, native_material, png
except ImportError:
    from build_grass_demo_assets import blade_frame, native_material, png


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/terrain/grass/recipe.json'
OUTPUT = ROOT/'assets/terrain/grass'


def remap_green(image, replacements):
    """Replace exact legacy green colors; preserve soil, petals and alpha."""
    image = image.convert('RGBA')
    colors = {tuple(bytes.fromhex(old[1:])): tuple(bytes.fromhex(new[1:]))
              for old, new in replacements.items()}
    image.putdata([(*colors.get(pixel[:3], pixel[:3]), pixel[3])
                   for pixel in image.get_flattened_data()])
    return image


def products():
    recipe = json.loads(SOURCE.read_text())
    for source in recipe['sources']:
        if sha256((ROOT/source['path']).read_bytes()).hexdigest() != source['sha256']:
            raise ValueError('Grass source reference changed: '+source['path'])
    palette = recipe['palette']
    output = {}

    def export(relative, image):
        path = OUTPUT/relative
        output[path] = png(image)
        return path.relative_to(ROOT).as_posix()

    def document(relative, data):
        output[OUTPUT/relative] = (json.dumps(data, indent=2)+'\n').encode()
        return (OUTPUT/relative).relative_to(ROOT).as_posix()

    hero = Image.open(ROOT/'assets/characters/caelan/idle_front.png').convert('RGBA')
    bounds = hero.getchannel('A').getbbox()
    character_height = bounds[3]-bounds[1]
    if recipe['opaque_height_limit'] != (character_height+1)//2:
        raise ValueError('Grass must stay within half the reference character height')
    manifest = {
        'version': 1, 'id': recipe['id'], 'status': recipe['status'],
        'tile_size': recipe['tile_size'], 'palette': palette, 'materials': {},
        'tall_grass': {key: recipe[key] for key in (
            'frame_size', 'anchor', 'contact_rect', 'height_limits', 'opaque_height_limit')},
        'flowers': {}, 'dirt_transitions': {},
        'source_recipe': SOURCE.relative_to(ROOT).as_posix(),
        'source_recipe_sha256': sha256(SOURCE.read_bytes()).hexdigest(),
        'source_assets': recipe['sources'], 'approval_reference': recipe['approval_reference']}
    manifest['tall_grass'].update(reference_character_visible_height=character_height,
                                  variants={})
    materials = {}
    for family, spec in recipe['families'].items():
        images = [native_material(family, seed, palette) for seed in spec['seeds']]
        materials[family] = images
        manifest['materials'][family] = {
            'label': spec['label'],
            'tiles': [export(f'ground/{family}_{index:02}.png', image)
                      for index, image in enumerate(images)]}

    def export_pose(variant, name, layers):
        for layer, image in layers.items():
            box = image.getchannel('A').getbbox()
            if box is None or recipe['anchor'][1]-box[1] > recipe['height_limits'][layer]:
                raise ValueError('Grass exceeds the '+layer+' height limit')
        combined = Image.alpha_composite(layers['rear'], layers['front'])
        box = combined.getchannel('A').getbbox()
        if box[3]-box[1] > recipe['opaque_height_limit']:
            raise ValueError('Grass exceeds half-character height')
        return {layer: export(f'tall/{variant}/{name}_{layer}.png', image)
                for layer, image in layers.items()}

    for variant, blades in recipe['variants'].items():
        poses = {'idle': [], 'parted': {}}
        for index, wind in enumerate(recipe['idle_wind']):
            pose = export_pose(variant, f'idle_{index:02}',
                               blade_frame(blades, palette, variant, wind=wind))
            pose['duration_ms'] = recipe['idle_duration_ms']
            poses['idle'].append(pose)
        for direction in ('north', 'east', 'south', 'west'):
            poses['parted'][direction] = [
                export_pose(variant, f'{direction}_{index:02}', blade_frame(
                    blades, palette, variant, direction=direction, strength=strength))
                for index, strength in enumerate(recipe['part_strengths'])]
        manifest['tall_grass']['variants'][variant] = poses

    dirt_source = ROOT/recipe['legacy_dirt_tileset']
    dirt = json.loads(dirt_source.read_text())
    manifest['dirt_transitions']['tiles'] = [
        {'mask': record['mask'], 'image': export(
            f"dirt/mask_{record['mask']:03}.png", remap_green(
                Image.open(dirt_source.parent/record['image']), recipe['legacy_green_remap']))}
        for record in dirt['tiles']]
    manifest['dirt_transitions']['interiors'] = [
        export(f'dirt_fill_{index:02}.png', Image.open(dirt_source.parent/path))
        for index, path in enumerate(dirt['dirt_interiors']['images'])]
    for name in recipe['flowers']:
        folder = ROOT/recipe['legacy_flower_root']/name
        plant = json.loads((folder/'plant.json').read_text())
        for path in sorted(folder.rglob('*.png')):
            export(f'flowers/{name}/{path.relative_to(folder).as_posix()}',
                   remap_green(Image.open(path), recipe['legacy_green_remap']))
        plant.update(id=f'terrain.grass.{name}.24', status=recipe['status'],
                     recipe=SOURCE.relative_to(ROOT).as_posix(),
                     source_metadata=(folder/'plant.json').relative_to(ROOT).as_posix())
        manifest['flowers'][name] = {
            'metadata': document(f'flowers/{name}/plant.json', plant),
            'idle': (OUTPUT/f'flowers/{name}/idle.png').relative_to(ROOT).as_posix()}

    board = Image.new('RGB', (960, 690), '#173f31')
    draw = ImageDraw.Draw(board)
    font = ImageFont.truetype(str(ROOT/'assets/ui/fonts/DejaVuSans.ttf'), 18)
    draw.text((20, 12), 'Approved emerald terrain / 24px materials / leg-height grass',
              font=font, fill='#dce8d1')
    for row, (family, images) in enumerate(materials.items()):
        y = 72+row*178
        draw.text((20, y-26), recipe['families'][family]['label'], font=font, fill='#dce8d1')
        for index, image in enumerate(images):
            board.paste(image.resize((144,144), Image.Resampling.NEAREST), (20+index*160, y))
    for index, (variant, blades) in enumerate(recipe['variants'].items()):
        tile = Image.new('RGBA', (48,40), palette['base'])
        # Visible boot bottom and grass roots share row 37.
        tile.alpha_composite(hero, (0,37-(bounds[3]-1)))
        layers = blade_frame(blades, palette, variant)
        for layer in ('rear','front'):
            tile.alpha_composite(layers[layer], (24,37-recipe['anchor'][1]))
        board.paste(tile.convert('RGB').resize((192,160), Image.Resampling.NEAREST),
                    (696,44+index*160))
        draw.text((696, 44+index*160), variant.title(), font=font, fill='#dce8d1')
    draw.text((20, 626), 'Caelan: 34px visible / Grass: 16–17px',
              font=font, fill='#dce8d1')
    draw.text((20, 654), 'Foreground tips stay within 5px above fixed roots.',
              font=font, fill='#dce8d1')
    export('materials_review.png', board)
    document('assets.json', manifest)
    return output


def build(check=False):
    output = products()
    obsolete = [path for path in OUTPUT.rglob('*.png') if path not in output]
    if check and obsolete:
        raise ValueError('Obsolete shared grass exports remain')
    for path, body in output.items():
        if check:
            if not path.exists() or path.read_bytes() != body:
                raise ValueError('Stale shared grass export: '+str(path.relative_to(ROOT)))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(body)
    if not check:
        for path in obsolete:
            path.unlink()
    print(('Verified' if check else 'Built')+' approved shared emerald grass pack')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    build(parser.parse_args().check)
