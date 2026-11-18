"""Build source-derived cottage interior foundations and an expanded room review."""
from pathlib import Path
from PIL import Image, ImageDraw
from build_eldenmere_stream import read_json, write_json, rgba, enlarged
from build_eldenmere_foliage import opened, nearest, save_loop

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'assets/source/terrain/eldenmere/cottage_interior'
OUTPUT = ROOT / 'assets/terrain/eldenmere/cottage_interior'


def extract_parts(recipe):
    parts = {}
    for record in recipe['source_samples']:
        reference = Image.open(SOURCE / record.get('source', recipe['source'])).convert('RGB')
        sample = reference.crop(record['crop']).resize(tuple(record['size']), Image.Resampling.NEAREST)
        image = Image.new('RGBA', sample.size)
        for y in range(image.height):
            for x in range(image.width):
                r, g, b = sample.getpixel((x, y))
                if r > 160 and b > 120 and r > g + 70 and b > g + 70:
                    continue
                material = record['material']
                if record['id'] == 'window' and g >= r + 3 and b >= r:
                    material = 'glass'
                if record['id'] == 'door' and 14 <= x < 22 and 16 <= y < 26 and max(r, g, b) - min(r, g, b) < 30:
                    material = 'iron'
                if record.get('wood_color_rule') == 'quiet_floor':
                    dark, light, worn = recipe['quiet_floor_red_thresholds']
                    shade = 'shadow' if r < dark else 'base' if r < light else 'light' if r < worn else 'worn'
                    color = rgba(recipe['palette']['wood'][shade])
                else:
                    color = nearest((r, g, b), [rgba(c) for c in recipe['palette'][material].values()])
                image.putpixel((x, y), color)
        image.save(SOURCE / f"parts/{record['id']}.png")
        image.save(OUTPUT / 'parts' / f"{record['id']}.png")
        parts[record['id']] = image
    return parts


def export_tiles(parts):
    tiles = {}
    for name, part in (('floor_a', 'floor'), ('floor_b', 'floor_b'), ('floor_c', 'floor_c')):
        tiles[name] = parts[part].copy()
    beam = parts['horizontal_beam']
    for index, name in enumerate(('north_a', 'north_b')):
        tile = parts['plaster'].copy()
        tile.alpha_composite(beam.crop((index * 24, 0, index * 24 + 24, 6)), (0, 0))
        tile.alpha_composite(beam.crop((index * 24, 2, index * 24 + 24, 6)), (0, 44))
        tiles[name] = tile
    nw = Image.new('RGBA', (24, 48))
    nw.alpha_composite(parts['plaster'].crop((0, 0, 12, 48)), (12, 0))
    nw.alpha_composite(parts['vertical_beam'], (18, 0))
    nw.alpha_composite(beam.crop((0, 0, 12, 6)), (12, 0))
    tiles['northwest_corner'] = nw
    tiles['northeast_corner'] = nw.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    west = Image.new('RGBA', (24, 24))
    west.alpha_composite(parts['plaster'].crop((0, 0, 12, 24)), (12, 0))
    west.alpha_composite(parts['vertical_beam'].crop((3, 0, 6, 24)), (21, 0))
    tiles['west_side'] = west
    tiles['east_side'] = west.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    south = parts['plaster'].crop((0, 40, 24, 48))
    south.alpha_composite(beam.crop((0, 0, 24, 3)), (0, 0))
    tiles['south_cap'] = south
    sw = Image.new('RGBA', (24, 24))
    sw.alpha_composite(south.crop((0, 0, 12, 8)), (12, 0))
    tiles['southwest_corner'] = sw
    tiles['southeast_corner'] = sw.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    threshold = Image.new('RGBA', (24, 8))
    # Retain the approved cottage's native stone doorstep, at the same pixel scale.
    threshold.alpha_composite(opened(OUTPUT.parent / 'cottage/closed.png').crop((48, 138, 72, 144)), (0, 0))
    tiles['entry_threshold'] = threshold
    for name, tile in tiles.items(): tile.save(OUTPUT / 'tiles' / f'{name}.png')
    return tiles


def assemble_room(recipe, parts, tiles):
    size = tuple(recipe['room_size'])
    floor = Image.new('RGBA', size)
    x, y, width, height = recipe['floor_rect']
    for row in range(height // 24):
        for col in range(width // 24):
            floor.alpha_composite(tiles[('floor_a', 'floor_b', 'floor_c')[(col + row * 2) % 3]], (x + col * 24, y + row * 24))
    walls = Image.new('RGBA', size)
    records = []
    def place(name, position):
        walls.alpha_composite(tiles[name], position)
        records.append({'tile': name, 'position': list(position)})
    for col in range(width // 24): place('north_a' if col % 2 == 0 else 'north_b', (x + col * 24, 24))
    place('northwest_corner', (0, 24)); place('northeast_corner', (264, 24))
    for yy in range(72, 264, 24):
        place('west_side', (0, yy)); place('east_side', (264, yy))
    for xx in range(24, 264, 24):
        if xx != recipe['entry_rect'][0]: place('south_cap', (xx, 264))
    place('southwest_corner', (0, 264)); place('southeast_corner', (264, 264))
    place('entry_threshold', tuple(recipe['entry_rect'][:2]))
    # Exposed supports define broad wall bays rather than a post every tile.
    supports = Image.new('RGBA', size)
    for xx in (24, 96, 168, 258): supports.alpha_composite(parts['vertical_beam'], (xx, 24))
    fixtures = Image.new('RGBA', size)
    for position in recipe['window_positions']: fixtures.alpha_composite(parts['window'], tuple(position))
    fixtures.alpha_composite(parts['door'], tuple(recipe['door_position']))
    shadow = Image.new('RGBA', size)
    wood = [rgba(c) for c in recipe['palette']['wood'].values()]
    for yy in range(y, y + height):
        for xx in range(x, x + width):
            if yy < y + 2 or xx == x or xx == x + width - 1:
                pixel = floor.getpixel((xx, yy))
                shadow.putpixel((xx, yy), wood[max(0, wood.index(pixel) - 1)])
    structure = Image.new('RGBA', size, recipe['void_color'])
    for layer in (floor, walls, supports, fixtures, shadow): structure.alpha_composite(layer)
    for name, image in (('floor', floor), ('walls', walls), ('supports', supports), ('fixtures', fixtures), ('contact_shadow', shadow), ('structure', structure)):
        image.save(OUTPUT / 'room' / f'{name}.png')
    return structure, floor, records


def light_mask(recipe, window):
    glass = {rgba(c) for c in recipe['palette']['glass'].values()}
    source = Image.new('L', window.size)
    source.putdata([255 if p in glass else 0 for p in window.get_flattened_data()])
    projected = source.resize((30, 24), Image.Resampling.NEAREST)
    mask = Image.new('L', tuple(recipe['room_size']))
    for wx, _ in recipe['window_positions']:
        for y in range(24):
            for x in range(30):
                if projected.getpixel((x, y)): mask.putpixel((wx + 6 + x + y // 3, 78 + y), 255)
    mask.save(OUTPUT / 'room/daylight_mask.png')
    return mask


def daylight_ramps(recipe):
    plaster = rgba(recipe['palette']['plaster']['light'])
    ramps = []
    for ratio in (.08, .12, .16):
        ramps.append({key: '#' + ''.join(f'{round(c + (p-c)*ratio):02x}' for c, p in zip(rgba(value)[:3], plaster[:3], strict=True))
                      for key, value in recipe['palette']['wood'].items()})
    return ramps


def export_lighting(recipe, floor, mask):
    ramps = daylight_ramps(recipe)
    wood = list(recipe['palette']['wood'].values())
    base = [rgba(c) for c in wood]
    frames = []
    for phase, strength in enumerate(recipe['light_strengths']):
        overlay = Image.new('RGBA', floor.size)
        shades = [rgba(c) for c in ramps[strength].values()]
        for y in range(mask.height):
            for x in range(mask.width):
                if mask.getpixel((x, y)):
                    overlay.putpixel((x, y), shades[base.index(floor.getpixel((x, y)))])
        overlay.save(OUTPUT / 'lighting' / f'frame_{phase+1:02}.png')
        frames.append(overlay)
    return frames, ramps


def review_board(recipe, parts, tiles):
    board = Image.new('RGB', (1248, 1040), '#e8edf2'); d = ImageDraw.Draw(board); d.fontmode = '1'
    d.text((20, 14), f"Eldenmere cottage interior foundations / {recipe['status']}", fill='#243529', font_size=26)
    samples = [('Floor A', tiles['floor_a']), ('Floor B', tiles['floor_b']), ('Floor C', tiles['floor_c']),
               ('North wall', tiles['north_a']), ('NW corner', tiles['northwest_corner']), ('West side', tiles['west_side']),
               ('Window', parts['window']), ('Door', parts['door']), ('Entry threshold', tiles['entry_threshold'])]
    for index, (label, sample) in enumerate(samples):
        x = 20 + index % 3 * 408; y = 98 + index // 3 * 304
        d.text((x, y - 28), label, fill='#243529', font_size=21)
        tile = Image.new('RGBA', (48, 48), '#c5c2b4')
        tile.alpha_composite(sample, ((48-sample.width)//2, 0))
        board.paste(enlarged(tile.convert('RGB'), 5), (x, y))
    d.text((20, 1002), '24px terrain grid / characters remain 24 x 36 / structural components are fixed', fill='#243529', font_size=23)
    board.save(OUTPUT / 'components_review.png')


def build():
    recipe = read_json(SOURCE / 'recipe.json')
    for folder in ('parts', 'tiles', 'room', 'lighting', 'scene_frames'): (OUTPUT / folder).mkdir(exist_ok=True)
    parts = extract_parts(recipe); tiles = export_tiles(parts)
    atlas = Image.new('RGBA', (168, 96)); tile_records = []
    for index, (name, image) in enumerate(tiles.items()):
        x, y = index % 7 * 24, index // 7 * 48
        atlas.paste(image, (x, y))
        tile_records.append({'id': name, 'image': f'tiles/{name}.png', 'frame_size': list(image.size), 'atlas_rect': [x,y,image.width,image.height]})
    atlas.save(OUTPUT / 'tile_sheet.png')
    structure, floor, placements = assemble_room(recipe, parts, tiles)
    mask = light_mask(recipe, parts['window']); lighting, ramps = export_lighting(recipe, floor, mask)
    hero = opened(ROOT / 'assets/characters/caelan/idle_front.png')
    previews = []; records = []
    for phase, light in enumerate(lighting):
        image = structure.copy(); image.alpha_composite(light); image.alpha_composite(hero, tuple(recipe['hero_position']))
        path = f'scene_frames/frame_{phase+1:02}.png'; image.convert('RGB').save(OUTPUT / path)
        previews.append(enlarged(image.convert('RGB'), recipe['review_scale']))
        records.append({'image': path, 'light': f'lighting/frame_{phase+1:02}.png', 'strength': recipe['light_strengths'][phase], 'duration_ms': recipe['duration_ms']})
    previews[0].save(OUTPUT / 'room_review.png'); save_loop(OUTPUT / 'room_review.gif', previews, {'duration_ms': recipe['duration_ms']})
    review_board(recipe, parts, tiles)
    write_json(OUTPUT / 'palette.json', {'status': recipe['status'], 'materials': recipe['palette'], 'daylight': ramps, 'void': recipe['void_color']})
    write_json(OUTPUT / 'interior.json', {'id': recipe['id'], 'status': recipe['status'], 'tile_size': [24,24],
        'interior_scale': recipe['interior_scale'], 'floor_size_tiles': recipe['floor_size_tiles'],
        'tile_sheet': 'tile_sheet.png', 'atlas_columns': 7, 'atlas_cell_size': [24,48], 'tiles': tile_records,
        'parts': [{'id': name, 'image': f'parts/{name}.png', 'frame_size': list(image.size)} for name, image in parts.items()],
        'structure_moves': False, 'daylight_cycle_duration_ms': 5400, 'collision_implemented': False,
        'review': {'room': 'room_review.gif', 'parts': 'components_review.png'},
        'recipe': '../../../source/terrain/eldenmere/cottage_interior/recipe.json'})
    write_json(OUTPUT / 'room.json', {'status': recipe['status'], 'purpose': 'Reusable interior foundation review; unfurnished, not a named household or final level',
        'room_size': recipe['room_size'], 'floor_rect': recipe['floor_rect'], 'north_wall_rect': recipe['north_wall_rect'],
        'entry_rect': recipe['entry_rect'], 'door_position': recipe['door_position'], 'door_purpose': 'Closed adjoining-room door appearance sample',
        'window_positions': recipe['window_positions'], 'hero_position': recipe['hero_position'], 'wall_tile_placements': placements,
        'floor_pattern': ['floor_a','floor_b','floor_c'], 'support_positions': [[x,24] for x in (24,96,168,258)],
        'draw_order': ['structure','daylight','character'], 'floor_elevation_pixels': 0,
        'exterior_transition_implemented': False, 'furniture_included': False, 'frames': records, 'cycle_duration_ms': 5400, 'loop': True,
        'daylight': {'mask': 'room/daylight_mask.png', 'geometry_moves': False, 'source': 'Projected window glass panes; mullion gaps remain unlit'},
        'review_scale': recipe['review_scale']})
    print('Built expanded 10x8 cottage room foundations, reusable shell tiles and a nine-pose daylight review')


if __name__ == '__main__': build()
