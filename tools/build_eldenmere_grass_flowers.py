"""Export source-derived 24px ground plants and an additive foliage-scene review."""
from pathlib import Path
from PIL import Image, ImageDraw
from build_eldenmere_stream import read_json, write_json, rgba, enlarged
from build_eldenmere_foliage import opened, nearest, save_loop

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'assets/source/terrain/eldenmere/grass_flowers'
OUTPUT = ROOT / 'assets/terrain/eldenmere/grass_flowers'
PREVIOUS = OUTPUT.parent / 'foliage'


def extract_native(reference, plant, palette):
    sample = reference.crop(plant['source_crop']).resize(tuple(plant['sample_size']), Image.Resampling.NEAREST)
    native = Image.new('RGBA', (24, 24))
    greens = [rgba(c) for c in palette['greens'].values()]
    petals = [rgba(c) for c in palette.get(plant['material'], {}).values()]
    centers = [rgba(c) for c in palette['centers'].values()]
    ox, oy = plant['sample_position']
    for y in range(sample.height):
        for x in range(sample.width):
            r, g, b = sample.getpixel((x, y))
            if r > 160 and b > 120 and r > g + 70 and b > g + 70:
                continue
            # Source leaf colors are green-dominant; blossoms use their own ramps.
            colors = greens if plant['material'] == 'greens' or y + oy >= plant['leaf_rows_from'] or g > r + 3 else petals + centers
            native.putpixel((x + ox, y + oy), nearest((r, g, b), colors))
    native.save(SOURCE / f"parts/{plant['id']}_native.png")
    return native


def split_bands(native, plant):
    base = native.copy()
    bands = []
    for band in plant['bands']:
        top, bottom = band['rows']
        part = Image.new('RGBA', native.size)
        for y in range(top, bottom):
            for x in range(native.width):
                part.putpixel((x, y), native.getpixel((x, y)))
                base.putpixel((x, y), (0, 0, 0, 0))
        assert part.getbbox(), f"Empty bend band {plant['id']}/{band['id']}"
        part.save(SOURCE / f"parts/{plant['id']}_{band['id']}.png")
        bands.append(part)
    base.save(SOURCE / f"parts/{plant['id']}_base.png")
    return base, bands


def export_plant(recipe, plant, reference):
    directory = OUTPUT / plant['id']
    (directory / 'frames').mkdir(parents=True, exist_ok=True)
    (directory / 'bands').mkdir(exist_ok=True)
    native = extract_native(reference, plant, recipe['palette'])
    base, bands = split_bands(native, plant)
    base.save(directory / 'base.png')
    for band, part in zip(plant['bands'], bands, strict=True):
        part.save(directory / f"bands/{band['id']}.png")
    frames = []
    records = []
    sheet = Image.new('RGBA', (24 * len(recipe['poses']), 24))
    for phase, offsets in enumerate(recipe['poses']):
        frame = Image.new('RGBA', (24, 24))
        for part, dx in zip(bands, offsets, strict=True):
            frame.alpha_composite(part, (dx, 0))
        frame.alpha_composite(base)
        path = f'frames/frame_{phase + 1:02}.png'
        frame.save(directory / path)
        sheet.paste(frame, (phase * 24, 0))
        frames.append(frame)
        records.append({'image': path, 'duration_ms': recipe['duration_ms'],
                        'sheet_rect': [phase * 24, 0, 24, 24], 'band_offsets_x': offsets})
    assert frames[0].tobytes() == native.tobytes(), 'Rest must match the source sample exactly'
    frames[0].save(directory / 'idle.png')
    sheet.save(directory / 'sheet.png')
    write_json(directory / 'plant.json', {
        'id': f"eldenmere.ground_plants.{plant['id']}.24", 'status': recipe['status'],
        'tile_size': [24, 24], 'frame_size': [24, 24], 'ground_rect': [0, 0, 24, 24],
        'collision': False, 'idle': 'idle.png', 'sheet': 'sheet.png', 'fixed_base': 'base.png',
        'fixed_rows_from': plant['fixed_rows_from'],
        'bands': [{'id': b['id'], 'image': f"bands/{b['id']}.png", 'rows': b['rows']} for b in plant['bands']],
        'wind': {'direction': 'E', 'max_displacement_pixels': [1, 0], 'whole_plant_moves': False,
                 'cycle_duration_ms': 5400, 'loop': True, 'frames': records},
        'recipe': '../../../../source/terrain/eldenmere/grass_flowers/recipe.json'})
    return frames


def review_board(recipe, plants):
    boards = []
    hero = opened(ROOT / 'assets/characters/caelan/idle_front.png')
    for phase in range(9):
        board = Image.new('RGB', (1056, 920), '#e8edf2')
        d = ImageDraw.Draw(board)
        d.fontmode = '1'
        d.text((24, 16), f"Eldenmere grass & wildflowers / {recipe['status']}", fill='#243529', font_size=26)
        d.text((24, 52), '24 x 24 frames at 12x / anchored bases / 5.4s eastward breeze', fill='#243529', font_size=21)
        for index, plant in enumerate(recipe['plants']):
            x = 24 + (index % 3) * 344
            y = 118 + (index // 3) * 350
            d.text((x, y - 28), plant['label'], fill='#243529', font_size=22)
            tile = Image.new('RGBA', (24, 24), '#70935a')
            tile.alpha_composite(plants[plant['id']][phase])
            board.paste(enlarged(tile.convert('RGB'), 12), (x, y))
        scale_tile = Image.new('RGBA', (100, 38), '#70935a')
        scale_tile.alpha_composite(hero, (2, 1))
        scale_tile.alpha_composite(plants['grass_sparse'][phase], (32, 14))
        scale_tile.alpha_composite(plants['flowers_white'][phase], (64, 14))
        board.paste(enlarged(scale_tile.convert('RGB'), 3), (24, 788))
        d.text((348, 810), 'Character + plants share 3x scale', fill='#243529', font_size=21)
        d.text((348, 844), 'Native grass heights 11-18px / flowers 20px', fill='#243529', font_size=21)
        boards.append(board)
    boards[0].save(OUTPUT / 'plants_review.png')
    save_loop(OUTPUT / 'plants_review.gif', boards, recipe)


def build_scene(recipe, plants):
    old = read_json(PREVIOUS / 'review_scene.json')
    full = []
    closeups = []
    records = []
    for tick in range(54):
        image = opened(PREVIOUS / f'scene_frames/frame_{tick + 1:02}.png')
        phases = []
        for instance in recipe['instances']:
            phase = (tick // 3 + instance['phase_offset']) % 9
            image.alpha_composite(plants[instance['plant']][phase], tuple(instance['position']))
            phases.append(phase)
        native = image.convert('RGB')
        path = f'scene_frames/frame_{tick + 1:02}.png'
        native.save(OUTPUT / path)
        full.append(enlarged(native, 2))
        closeups.append(enlarged(native.crop(recipe['scene_closeup']), 4))
        records.append({'image': path, 'base_phase': tick, 'plant_phases': phases, 'duration_ms': 200})
    for name, images in (('review_scene', full), ('garden_closeup', closeups)):
        images[0].save(OUTPUT / f'{name}.png')
        save_loop(OUTPUT / f'{name}.gif', images, {'duration_ms': 200})
    write_json(OUTPUT / 'review_scene.json', {
        'status': recipe['status'], 'purpose': 'Grass and wildflower art review; illustrative placements, not a level',
        'base_scene': '../foliage/review_scene.json', 'grid_size': old['grid_size'],
        'instances': recipe['instances'], 'wind_direction': 'E', 'plants_cycle_duration_ms': 5400,
        'cycle_duration_ms': 10800, 'frames': records, 'loop': True,
        'review': {'scene_scale': 2, 'closeup_rect': recipe['scene_closeup'], 'closeup_scale': 4}})


def build():
    recipe = read_json(SOURCE / 'recipe.json')
    (OUTPUT / 'scene_frames').mkdir(exist_ok=True)
    reference = Image.open(SOURCE / recipe['source']).convert('RGB')
    plants = {p['id']: export_plant(recipe, p, reference) for p in recipe['plants']}
    write_json(OUTPUT / 'palette.json', {'status': recipe['status'], 'materials': recipe['palette']})
    write_json(OUTPUT / 'plants.json', {
        'id': recipe['id'], 'status': recipe['status'], 'tile_size': [24, 24],
        'plants': [{'id': p['id'], 'metadata': f"{p['id']}/plant.json"} for p in recipe['plants']],
        'cycle_duration_ms': 5400, 'wind_direction': 'E',
        'review': {'plants': 'plants_review.gif', 'garden': 'garden_closeup.gif', 'scene': 'review_scene.gif'}})
    review_board(recipe, plants)
    build_scene(recipe, plants)
    print('Built six 24px ground plants, anchored wind poses and a 54-frame synchronized garden review')


if __name__ == '__main__':
    build()
