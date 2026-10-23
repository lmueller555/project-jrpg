"""Assemble source-derived modular garden fences and a hinged gate art review."""
from math import ceil, cos, radians, sin
from pathlib import Path
from PIL import Image, ImageDraw
from build_eldenmere_stream import read_json, write_json, rgba, enlarged
from build_eldenmere_foliage import opened, nearest, save_loop

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'assets/source/terrain/eldenmere/garden_fence'
OUTPUT = ROOT / 'assets/terrain/eldenmere/garden_fence'
PREVIOUS = OUTPUT.parent / 'reeds'
GROUND = OUTPUT.parent / 'grass_dirt'
DIRECTIONS = ('N', 'E', 'S', 'W')
OFFSETS = ((0, -1), (1, 0), (0, 1), (-1, 0))


def indexed(image):
    assert image.getcolors(256) is not None, 'Review frames must fit a lossless GIF palette'
    return image.convert('P', palette=Image.Palette.ADAPTIVE, colors=256, dither=Image.Dither.NONE)


def extract_parts(recipe):
    reference = Image.open(SOURCE / recipe['source']).convert('RGB')
    palette = recipe['palette']
    parts = {}
    for record in recipe['samples']:
        sample = reference.crop(record['crop']).resize(tuple(record['size']), Image.Resampling.NEAREST)
        image = Image.new('RGBA', sample.size)
        for y in range(sample.height):
            for x in range(sample.width):
                r, g, b = sample.getpixel((x, y))
                if r > 160 and b > 120 and r > g + 70 and b > g + 70:
                    continue
                metal_region = (x < 6 and (2 <= y < 5 or 10 <= y < 13)) or (x >= 20 and 5 <= y < 9)
                material = 'moss' if record['id'] == 'post' and g > r + 3 else 'iron' if record['id'] == 'gate_panel' and metal_region and max(r, g, b) - min(r, g, b) <= 32 else 'wood'
                image.putpixel((x, y), nearest((r, g, b), [rgba(c) for c in palette[material].values()]))
        image.save(SOURCE / f"parts/{record['id']}.png")
        image.save(OUTPUT / 'parts' / f"{record['id']}.png")
        parts[record['id']] = image
    return parts


def module_layers(recipe, parts, mask, variant):
    shadow = Image.new('RGBA', (24, 48))
    ImageDraw.Draw(shadow).rectangle((9, 32, 14, 33), fill=rgba(recipe['palette']['shadow']['base']))
    rails = Image.new('RGBA', shadow.size)
    upper, lower = parts[f'upper_{variant}'], parts[f'lower_{variant}']
    for i, direction in enumerate(DIRECTIONS):
        if not mask & (1 << i):
            continue
        if direction in ('E', 'W'):
            left = 12 if direction == 'E' else 0
            for part, y in ((upper, 16), (lower, 26)):
                rails.alpha_composite(part.crop((left, 0, left + 12, 3)), (left, y))
        else:
            # North/south runs retain sampled grain along the rails; a small
            # horizontal offset separates their upper and lower faces in projection.
            for part, x, y in ((upper, 10, 4 if direction == 'N' else 16),
                               (lower, 12, 14 if direction == 'N' else 26)):
                strip = part.rotate(90, expand=True)
                top = 0 if direction == 'N' else 12
                rails.alpha_composite(strip.crop((0, top, 3, top + 12)), (x, y))
    post = Image.new('RGBA', rails.size)
    post.alpha_composite(parts['post'], (10, 14))
    return {'shadow': shadow, 'rails': rails, 'post': post}


def export_modules(recipe, parts):
    modules = {}
    records = []
    sheet = Image.new('RGBA', (240, 144))
    for variant in ('a', 'b'):
        for mask in range(1, 16):
            name = ''.join(d.lower() for i, d in enumerate(DIRECTIONS) if mask & (1 << i)) + '_' + variant
            directory = OUTPUT / 'modules' / name
            directory.mkdir(parents=True, exist_ok=True)
            layers = module_layers(recipe, parts, mask, variant)
            image = Image.new('RGBA', (24, 48))
            for layer, pixels in layers.items():
                pixels.save(directory / f'{layer}.png')
                image.alpha_composite(pixels)
            image.save(directory / 'module.png')
            index = (mask - 1) + (15 if variant == 'b' else 0)
            sheet.paste(image, ((index % 10) * 24, (index // 10) * 48))
            records.append({'id': name, 'mask': mask, 'wear_variant': variant,
                            'connections': [d for i, d in enumerate(DIRECTIONS) if mask & (1 << i)],
                            'image': f'modules/{name}/module.png', 'sheet_rect': [index % 10 * 24, index // 10 * 48, 24, 48]})
            modules[name] = layers
    sheet.save(OUTPUT / 'modules.png')
    write_json(OUTPUT / 'fence.json', {
        'id': recipe['id'], 'status': recipe['status'], 'tile_size': [24, 24], 'frame_size': [24, 48],
        'ground_rect': [0, 20, 24, 24], 'post_anchor': [12, 32], 'post_height_pixels': 18,
        'rail_heights_pixels': [16, 6], 'cloth_details': False, 'ambient_motion': False,
        'ports': {'N': [12, 20], 'E': [24, 32], 'S': [12, 44], 'W': [0, 32]},
        'sheet': 'modules.png', 'columns': 10, 'modules': records,
        'draw_order_across_instances': ['shadow', 'rails', 'post'], 'gate': 'gate/gate.json',
        'collision_implemented': False, 'recipe': '../../../source/terrain/eldenmere/garden_fence/recipe.json'})
    return modules


def project_leaf(panel, latch, angle, latch_lift):
    leaf = panel.copy()
    leaf.alpha_composite(latch, (0, -latch_lift))
    image = Image.new('RGBA', (48, 48))
    c = 0 if angle == 90 else cos(radians(angle))
    s = sin(radians(angle))
    # Draw far columns before near ones, around a stationary left hinge axis.
    for u in reversed(range(24)):
        x = 11 + ceil((u + 1) * c)
        depth = round(u * s)
        for v in range(14):
            pixel = leaf.getpixel((u, v))
            if pixel[3]:
                image.putpixel((x, 24 + v - depth), pixel)
    return image


def export_gate(recipe, parts):
    directory = OUTPUT / 'gate'
    (directory / 'frames').mkdir(parents=True, exist_ok=True)
    (directory / 'leaves').mkdir(exist_ok=True)
    panel = parts['gate_panel'].copy()
    latch = Image.new('RGBA', panel.size)
    iron = {rgba(c) for c in recipe['palette']['iron'].values()}
    for y in range(panel.height):
        for x in range(20, panel.width):
            pixel = panel.getpixel((x, y))
            if pixel in iron:
                latch.putpixel((x, y), pixel)
                panel.putpixel((x, y), (0, 0, 0, 0))
    assert latch.getbbox(), 'Source gate must retain a visible latch'
    panel.save(directory / 'panel.png')
    latch.save(directory / 'latch.png')
    panel.save(SOURCE / 'parts/gate_panel_without_latch.png')
    latch.save(SOURCE / 'parts/gate_latch.png')
    posts = Image.new('RGBA', (48, 48))
    for x in (8, 36):
        posts.alpha_composite(parts['post'], (x, 22))
    # Pins use source hinge material and stay entirely outside the 24px opening.
    pins = parts['gate_panel'].crop(recipe['hinge_sample_crop'])
    for y in range(pins.height):
        for x in range(pins.width):
            p = pins.getpixel((x, y))
            if p[3]: pins.putpixel((x, y), nearest(p[:3], [rgba(c) for c in recipe['palette']['iron'].values()]))
    for y in (26, 34): posts.alpha_composite(pins, (10, y))
    shadow = Image.new('RGBA', posts.size)
    d = ImageDraw.Draw(shadow)
    for x in (7, 35): d.rectangle((x, 40, x + 6, 41), fill=rgba(recipe['palette']['shadow']['base']))
    posts.save(directory / 'posts_hinges.png')
    shadow.save(directory / 'shadow.png')
    records = []
    frames = []
    leaves = []
    sheet = Image.new('RGBA', (384, 48))
    for phase, pose in enumerate(recipe['gate_poses']):
        leaf = project_leaf(panel, latch, pose['angle_degrees'], pose['latch_lift'])
        frame = shadow.copy()
        frame.alpha_composite(leaf)
        frame.alpha_composite(posts)
        path = f'frames/frame_{phase + 1:02}.png'
        frame.save(directory / path)
        leaf.save(directory / f'leaves/frame_{phase + 1:02}.png')
        sheet.paste(frame, (phase * 48, 0))
        records.append({**pose, 'image': path, 'leaf': f'leaves/frame_{phase + 1:02}.png',
                        'sheet_rect': [phase * 48, 0, 48, 48], 'duration_ms': 100})
        frames.append(frame)
        leaves.append(leaf)
    sheet.save(directory / 'sheet.png')
    frames[0].save(directory / 'closed.png')
    frames[7].save(directory / 'open.png')
    write_json(directory / 'gate.json', {
        'id': recipe['id'] + '.gate', 'status': recipe['status'], 'tile_size': [24, 24],
        'frame_size': [48, 48], 'ground_rect': [12, 24, 24, 24], 'ground_line': [12, 40, 24],
        'clear_opening_width_pixels': 24, 'hinge_axis_x': 11, 'opens_toward': 'north',
        'fixed_layers': ['shadow.png', 'posts_hinges.png'], 'panel': 'panel.png', 'latch': 'latch.png',
        'draw_order': ['shadow', 'leaf', 'posts_hinges'], 'sheet': 'sheet.png', 'poses': records,
        'animations': {'closed': {'frames': [0], 'loop': True}, 'open': {'frames': [7], 'loop': True},
                       'opening': {'frames': [1, 2, 3, 4, 5, 6, 7], 'loop': False},
                       'closing': {'frames': [4, 3, 2, 1, 0], 'loop': False}},
        'autonomous_open_close': False, 'collision_implemented': False})
    return {'frames': frames, 'leaves': leaves, 'posts': posts, 'shadow': shadow}


def gate_phase(tick):
    tick %= 54
    if 8 <= tick <= 14: return tick - 7
    if 15 <= tick <= 32: return 7
    if 33 <= tick <= 37: return (4, 3, 2, 1, 0)[tick - 33]
    return 0


def background(recipe):
    gm = read_json(GROUND / 'tileset.json')
    grass = [opened(GROUND / path) for path in gm['grass']['images']]
    width, height = recipe['scene_grid_size']
    image = Image.new('RGBA', (width * 24, height * 24))
    for y in range(height):
        for x in range(width): image.paste(grass[(x * 3 + y * 5) % 4], (x * 24, y * 24))
    image.save(OUTPUT / 'review_ground.png')
    old_cells = {tuple(p) for p in read_json(OUTPUT.parent / 'cottage_shapes/review_scene.json')['path_cells']}
    cells = old_cells | {tuple(p) for p in recipe['new_path_cells']}
    # Refresh the former path endpoint and new cells using the existing 47-state atlas.
    paths = Image.new('RGBA', image.size)
    offsets = ((0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1))
    touched = {tuple(p) for p in recipe['new_path_cells']} | {tuple(recipe['path_join_cell'])}
    for x, y in sorted(touched):
        mask = sum(1 << i for i, (dx, dy) in enumerate(offsets) if (x + dx, y + dy) in cells)
        tile = gm['tiles'][gm['lookup_256'][mask]]
        paths.alpha_composite(opened(GROUND / tile['image']), (x * 24, y * 24))
    paths.save(OUTPUT / 'review_path.png')
    return image, paths


def fence_instances(recipe):
    left, top, right, bottom = recipe['enclosure_cells']
    cells = {(x, y) for x in range(left, right + 1) for y in (top, bottom)}
    cells |= {(x, y) for y in range(top, bottom + 1) for x in (left, right)}
    gate_cell = tuple(recipe['gate_cell'])
    cells.remove(gate_cell)
    records = []
    for x, y in sorted(cells):
        mask = sum(1 << i for i, (dx, dy) in enumerate(OFFSETS) if (x + dx, y + dy) in cells | {gate_cell})
        name = ''.join(d.lower() for i, d in enumerate(DIRECTIONS) if mask & (1 << i)) + ('_a' if (x + y) % 2 else '_b')
        records.append({'module': name, 'cell': [x, y], 'position': [x * 24, y * 24 - 20], 'ground_elevation_pixels': 0})
    return records


def scene_frame(recipe, modules, gate, ground, paths, instances, tick):
    parent = tick // 2
    image = ground.copy()
    image.paste(opened(PREVIOUS / f'scene_frames/frame_{parent + 1:02}.png'), (0, 0))
    image.alpha_composite(paths)
    for plant in recipe['garden_plants']:
        phase = (tick // 6 + plant['phase_offset']) % 9
        image.alpha_composite(opened(OUTPUT.parent / plant['pack'] / plant['plant'] / f'frames/frame_{phase + 1:02}.png'), tuple(plant['position']))
    pose = gate_phase(tick)
    for layer in ('shadow', 'rails'):
        for instance in instances: image.alpha_composite(modules[instance['module']][layer], tuple(instance['position']))
    image.alpha_composite(gate['shadow'], tuple(recipe['gate_position']))
    image.alpha_composite(gate['leaves'][pose], tuple(recipe['gate_position']))
    for instance in instances: image.alpha_composite(modules[instance['module']]['post'], tuple(instance['position']))
    image.alpha_composite(gate['posts'], tuple(recipe['gate_position']))
    return image, pose


def review_board(recipe, modules, gate):
    boards = []
    names = ('ew_a', 'ew_b', 'ns_a', 'ne_a', 'nes_a', 'nesw_a', 'e_a')
    for phase in range(54):
        board = Image.new('RGB', (1248, 1080), '#e8edf2')
        d = ImageDraw.Draw(board); d.fontmode = '1'
        d.text((20, 12), f"Eldenmere garden fence / {recipe['status']} / 24px grid", fill='#243529', font_size=26)
        for index, name in enumerate(names):
            x = 20 + index % 4 * 310; y = 88 + index // 4 * 334
            d.text((x, y - 28), name, fill='#243529', font_size=21)
            tile = Image.new('RGBA', (24, 48), '#70935a')
            for part in modules[name].values(): tile.alpha_composite(part)
            board.paste(enlarged(tile.convert('RGB'), 6), (x, y))
        pose = gate_phase(phase)
        d.text((720, 740), 'Gate / 24px clear opening / 6x', fill='#243529', font_size=21)
        tile = Image.new('RGBA', (48, 48), '#70935a'); tile.alpha_composite(gate['frames'][pose])
        board.paste(enlarged(tile.convert('RGB'), 6), (720, 772))
        d.text((20, 776), 'Fixed posts / latch release / inward swing', fill='#243529', font_size=23)
        d.text((20, 820), 'Two wear variants; no cloth details', fill='#243529', font_size=23)
        hero = opened(ROOT / 'assets/characters/caelan/idle_front.png')
        scale = Image.new('RGBA', (72, 48), '#70935a'); scale.alpha_composite(hero, (2, 4)); scale.alpha_composite(gate['frames'][pose], (24, 0))
        board.paste(enlarged(scale.convert('RGB'), 3), (20, 856))
        d.text((250, 906), 'Character + gate at matching 3x', fill='#243529', font_size=21)
        boards.append(indexed(board))
    boards[0].save(OUTPUT / 'modules_review.png')
    save_loop(OUTPUT / 'modules_review.gif', boards, {'duration_ms': 100})


def build():
    recipe = read_json(SOURCE / 'recipe.json')
    for folder in ('parts', 'scene_frames'): (OUTPUT / folder).mkdir(exist_ok=True)
    parts = extract_parts(recipe)
    modules = export_modules(recipe, parts)
    gate = export_gate(recipe, parts)
    ground, paths = background(recipe)
    instances = fence_instances(recipe)
    full, closeups, records = [], [], []
    for tick in range(108):
        image, pose = scene_frame(recipe, modules, gate, ground, paths, instances, tick)
        native = image.convert('RGB'); path = f'scene_frames/frame_{tick + 1:03}.png'; native.save(OUTPUT / path)
        full.append(indexed(enlarged(native, 2))); closeups.append(indexed(enlarged(native.crop(recipe['scene_closeup']), 4)))
        records.append({'image': path, 'parent_frame': tick // 2, 'gate_pose': pose, 'duration_ms': 100})
    for name, images in (('review_scene', full), ('garden_closeup', closeups)):
        images[0].save(OUTPUT / f'{name}.png'); save_loop(OUTPUT / f'{name}.gif', images, {'duration_ms': 100})
    del full, closeups
    review_board(recipe, modules, gate)
    write_json(OUTPUT / 'palette.json', {'status': recipe['status'], 'materials': recipe['palette']})
    write_json(OUTPUT / 'review_scene.json', {
        'status': recipe['status'], 'purpose': 'Garden fence and gate art review; illustrative layout, not a game level',
        'base_scene': '../reeds/review_scene.json', 'grid_size': recipe['scene_grid_size'], 'instances': instances,
        'enclosure_cells': recipe['enclosure_cells'], 'gate_position': recipe['gate_position'], 'gate_cell': recipe['gate_cell'],
        'garden_plants': recipe['garden_plants'], 'path_cells_added': recipe['new_path_cells'],
        'path_join_cell': recipe['path_join_cell'], 'frames': records, 'cycle_duration_ms': 10800, 'loop': True,
        'gate_use_is_demonstration_only': True, 'review': {'scene_scale': 2, 'closeup_rect': recipe['scene_closeup'], 'closeup_scale': 4}})
    print('Built 30 fence modules, eight hinged gate poses and a synchronized 108-frame garden review')


if __name__ == '__main__': build()
