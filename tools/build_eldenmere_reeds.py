"""Build anchored bank reeds from retained source art and extend the approved scene."""
from pathlib import Path
from PIL import Image, ImageDraw
from build_eldenmere_stream import read_json, write_json, rgba, enlarged
from build_eldenmere_foliage import opened, nearest, save_loop

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'assets/source/terrain/eldenmere/reeds'
OUTPUT = ROOT / 'assets/terrain/eldenmere/reeds'
PREVIOUS = OUTPUT.parent / 'grass_flowers'


def extract_native(reference, plant, recipe):
    source = reference.crop(plant['source_crop']).convert('RGBA')
    pixels = []
    for r, g, b, _ in source.get_flattened_data():
        background = r > 160 and b > 120 and r > g + 70 and b > g + 70
        pixels.append((0, 0, 0, 0) if background else (r, g, b, 255))
    source.putdata(pixels)
    # Coverage-aware sampling retains subpixel-width stalks, then hardens alpha.
    sample = source.resize(tuple(plant['sample_size']), Image.Resampling.BOX)
    native = Image.new('RGBA', tuple(plant['frame_size']))
    greens = [rgba(c) for c in recipe['palette']['greens'].values()]
    seeds = [rgba(c) for c in recipe['palette']['seedheads'].values()]
    ox, oy = plant['sample_position']
    for y in range(sample.height):
        for x in range(sample.width):
            r, g, b, alpha = sample.getpixel((x, y))
            if alpha < recipe['alpha_coverage_threshold']:
                continue
            brown = plant['seedheads'] and y + oy < plant['seedheads_bottom'] and r > g + 14 and r > b + 20
            native.putpixel((x + ox, y + oy), nearest((r, g, b), seeds if brown else greens))
    native.save(SOURCE / f"parts/{plant['id']}_native.png")
    return native


def export_plant(recipe, plant, reference):
    directory = OUTPUT / plant['id']
    (directory / 'frames').mkdir(parents=True, exist_ok=True)
    (directory / 'bands').mkdir(exist_ok=True)
    native = extract_native(reference, plant, recipe)
    base = native.copy()
    parts = []
    for band in plant['bands']:
        top, bottom = band['rows']
        part = Image.new('RGBA', native.size)
        for y in range(top, bottom):
            for x in range(native.width):
                part.putpixel((x, y), native.getpixel((x, y)))
                base.putpixel((x, y), (0, 0, 0, 0))
        assert part.getbbox(), f"Empty reed band {plant['id']}/{band['id']}"
        part.save(SOURCE / f"parts/{plant['id']}_{band['id']}.png")
        part.save(directory / f"bands/{band['id']}.png")
        parts.append(part)
    base.save(directory / 'base.png')
    base.save(SOURCE / f"parts/{plant['id']}_base.png")
    w, h = native.size
    frames = []
    records = []
    sheet = Image.new('RGBA', (w * len(recipe['poses']), h))
    for phase, offsets in enumerate(recipe['poses']):
        frame = Image.new('RGBA', native.size)
        for part, dx in zip(parts, offsets, strict=True):
            frame.alpha_composite(part, (dx, 0))
        frame.alpha_composite(base)
        path = f'frames/frame_{phase + 1:02}.png'
        frame.save(directory / path)
        sheet.paste(frame, (phase * w, 0))
        records.append({'image': path, 'duration_ms': recipe['duration_ms'],
                        'sheet_rect': [phase * w, 0, w, h], 'band_offsets_x': offsets})
        frames.append(frame)
    assert frames[0].tobytes() == native.tobytes(), 'Rest must reproduce the source-derived plant'
    frames[0].save(directory / 'idle.png')
    sheet.save(directory / 'sheet.png')
    write_json(directory / 'reeds.json', {
        'id': f"eldenmere.reeds.{plant['id']}.24", 'status': recipe['status'],
        'tile_size': [24, 24], 'frame_size': list(native.size), 'ground_rect': plant['ground_rect'],
        'placement': 'dry_bank', 'collision': False, 'idle': 'idle.png', 'sheet': 'sheet.png',
        'fixed_base': 'base.png', 'fixed_rows_from': plant['fixed_rows_from'],
        'bands': [{'id': b['id'], 'image': f"bands/{b['id']}.png", 'rows': b['rows']} for b in plant['bands']],
        'wind': {'direction': 'E', 'max_displacement_pixels': [1, 0], 'whole_plant_moves': False,
                 'cycle_duration_ms': 5400, 'loop': True, 'frames': records},
        'recipe': '../../../../source/terrain/eldenmere/reeds/recipe.json'})
    return frames


def review_board(recipe, plants):
    boards = []
    hero = opened(ROOT / 'assets/characters/caelan/idle_front.png')
    for phase in range(9):
        board = Image.new('RGB', (1136, 788), '#e8edf2')
        d = ImageDraw.Draw(board)
        d.fontmode = '1'
        d.text((24, 14), f"Eldenmere bank reeds / {recipe['status']} / 5.4s eastward breeze", fill='#243529', font_size=25)
        for name, x, label in (('tall', 24, 'Tall / 24 x 48 / 12x'), ('short', 400, 'Short / 24 x 24 / 12x')):
            d.text((x, 58), label, fill='#243529', font_size=22)
            frame = plants[name][phase]
            tile = Image.new('RGBA', frame.size, '#70935a')
            tile.alpha_composite(frame)
            board.paste(enlarged(tile.convert('RGB'), 12), (x, 94))
        d.text((512, 398), 'Caelan and both reeds share 6x scale', fill='#243529', font_size=22)
        tile = Image.new('RGBA', (96, 56), '#70935a')
        tile.alpha_composite(hero, (2, 17))
        tile.alpha_composite(plants['tall'][phase], (36, 6))
        tile.alpha_composite(plants['short'][phase], (68, 30))
        board.paste(enlarged(tile.convert('RGB'), 6), (512, 430))
        d.text((24, 704), 'Fixed roots', fill='#243529', font_size=22)
        d.text((24, 738), '1px tip / stem bend', fill='#243529', font_size=22)
        boards.append(board)
    boards[0].save(OUTPUT / 'reeds_review.png')
    save_loop(OUTPUT / 'reeds_review.gif', boards, recipe)


def build_scene(recipe, plants):
    old = read_json(PREVIOUS / 'review_scene.json')
    full = []
    closeups = []
    records = []
    for tick in range(recipe['scene_frame_count']):
        image = opened(PREVIOUS / f'scene_frames/frame_{tick + 1:02}.png')
        phases = []
        for instance in recipe['instances']:
            phase = (tick // 3 + instance['phase_offset']) % 9
            image.alpha_composite(plants[instance['plant']][phase], tuple(instance['position']))
            phases.append(phase)
        native = image.convert('RGB')
        path = f'scene_frames/frame_{tick + 1:02}.png'
        native.save(OUTPUT / path)
        full.append(enlarged(native, recipe['scene_scale']))
        closeups.append(enlarged(native.crop(recipe['scene_closeup']), recipe['scene_closeup_scale']))
        records.append({'image': path, 'base_phase': tick, 'reed_phases': phases, 'duration_ms': recipe['scene_duration_ms']})
    for name, images in (('review_scene', full), ('banks_closeup', closeups)):
        images[0].save(OUTPUT / f'{name}.png')
        save_loop(OUTPUT / f'{name}.gif', images, {'duration_ms': recipe['scene_duration_ms']})
    write_json(OUTPUT / 'review_scene.json', {
        'status': recipe['status'], 'purpose': 'Bank reed art review; illustrative placements, not a game level',
        'base_scene': '../grass_flowers/review_scene.json', 'grid_size': old['grid_size'],
        'instances': recipe['instances'], 'wind_direction': 'E', 'reeds_cycle_duration_ms': 5400,
        'cycle_duration_ms': 10800, 'frames': records, 'loop': True,
        'review': {'scene_scale': recipe['scene_scale'], 'closeup_rect': recipe['scene_closeup'],
                   'closeup_scale': recipe['scene_closeup_scale']}})


def build():
    recipe = read_json(SOURCE / 'recipe.json')
    (OUTPUT / 'scene_frames').mkdir(exist_ok=True)
    reference = Image.open(SOURCE / recipe['source']).convert('RGB')
    plants = {p['id']: export_plant(recipe, p, reference) for p in recipe['plants']}
    write_json(OUTPUT / 'palette.json', {'status': recipe['status'], 'materials': recipe['palette']})
    write_json(OUTPUT / 'reeds.json', {'id': recipe['id'], 'status': recipe['status'], 'tile_size': [24, 24],
        'plants': [{'id': p['id'], 'metadata': f"{p['id']}/reeds.json"} for p in recipe['plants']],
        'cycle_duration_ms': 5400, 'wind_direction': 'E',
        'review': {'plants': 'reeds_review.gif', 'banks': 'banks_closeup.gif', 'scene': 'review_scene.gif'}})
    review_board(recipe, plants)
    build_scene(recipe, plants)
    print('Built tall/short bank reeds, anchored 5.4s breeze and synchronized 54-frame scene')


if __name__ == '__main__':
    build()
