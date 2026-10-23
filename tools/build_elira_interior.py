"""Export Elira's quest props and compare shelf states in the compact cottage."""
from copy import deepcopy
from pathlib import Path
from PIL import Image, ImageDraw
from build_eldenmere_stream import read_json, write_json, rgba, enlarged
from build_eldenmere_foliage import opened, nearest, save_loop
from build_eldenmere_cottage_layouts import navigation

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'assets/source/terrain/eldenmere/elira_interior'
OUTPUT = ROOT / 'assets/terrain/eldenmere/elira_interior'


def extract(recipe):
    reference = opened(SOURCE / recipe['source'])
    sprites = {}
    for record in recipe['samples']:
        sample = reference.crop(record['crop']).resize(tuple(record['sample_size']), Image.Resampling.NEAREST)
        sprite = Image.new('RGBA', tuple(record['frame_size']))
        palette = recipe['palette']
        for y in range(sample.height):
            for x in range(sample.width):
                r, g, b, a = sample.getpixel((x, y))
                if a < 128:
                    continue
                if record['id'] == 'step_stool':
                    keys = ['outline', 'wood_shadow', 'wood_base', 'wood_light', 'wood_worn']
                elif max(r, g, b) - min(r, g, b) < 36:
                    keys = ['outline', 'iron_dark', 'iron_shadow', 'iron_base', 'iron_light']
                else:
                    keys = ['outline', 'glass_shadow', 'glass_base', 'glass_light', 'candle']
                ox, oy = record['offset']
                sprite.putpixel((x + ox, y + oy), nearest((r, g, b), [rgba(palette[k]) for k in keys]))
        sprite.save(SOURCE / 'parts' / f"{record['id']}.png")
        sprite.save(OUTPUT / 'sprites' / f"{record['id']}.png")
        sprites[record['id']] = sprite
    # Reuse the approved shelf in full: books, pottery, wood and brackets persist.
    empty = Image.new('RGBA', tuple(recipe['shelf_frame_size']))
    empty.alpha_composite(opened(ROOT / 'assets/terrain/eldenmere/cottage_storage/sprites/shelf.png'), tuple(recipe['shelf_base_offset']))
    occupied = empty.copy()
    occupied.alpha_composite(sprites['lantern_unlit'], tuple(recipe['lantern_on_shelf']))
    for name, sprite in [('shelf_empty', empty), ('shelf_with_lantern', occupied)]:
        sprite.save(OUTPUT / 'sprites' / f'{name}.png')
        sprites[name] = sprite
    return sprites


def component_board(recipe, sprites):
    board = Image.new('RGB', (1224, 530), '#e8edf2')
    draw = ImageDraw.Draw(board)
    draw.fontmode = '1'
    draw.text((24, 18), f"Elira's memorial lantern and step stool / {recipe['status']}", fill='#243529', font_size=26)
    for i, name in enumerate(('lantern_unlit', 'step_stool', 'shelf_with_lantern', 'shelf_empty')):
        sprite = sprites[name]
        cell = Image.new('RGBA', (48, 48), '#c5c2b4')
        cell.alpha_composite(sprite, ((48 - sprite.width)//2, (48 - sprite.height)//2))
        x = 24 + i * 300
        board.paste(enlarged(cell.convert('RGB'), 6), (x, 110))
        draw.text((x, 72), name.replace('_', ' '), fill='#243529', font_size=20)
        draw.text((x, 418), f'{sprite.width} x {sprite.height}px', fill='#243529', font_size=20)
    draw.text((24, 480), 'Stored unlit / fixed stool / approved shelf preserved / two discrete quest states', fill='#243529', font_size=23)
    board.save(OUTPUT / 'components_review.png')


def build():
    recipe = read_json(SOURCE / 'recipe.json')
    for path in (SOURCE/'parts', OUTPUT/'sprites', OUTPUT/'before/scene_frames', OUTPUT/'after/scene_frames'):
        path.mkdir(parents=True, exist_ok=True)
    sprites = extract(recipe)
    base = ROOT / recipe['base_room']
    room = read_json(base / 'room.json')
    objects = deepcopy(room['objects'])
    sx, sy = recipe['stool_position']
    fx, fy, fw, fh = recipe['stool_floor_rect']
    objects.append({'id': 'step_stool', 'position': [sx, sy], 'frame_size': [24, 24],
                    'floor_rect': [sx+fx, sy+fy, fw, fh], 'access': recipe['interaction_approach']})
    blocked, centres, reached = navigation(tuple(room['room_size']), room['floor_rect'], objects,
                                            room['partition_rect'], room['entry_rect'], room['actor_probe_size'])
    blocked.save(OUTPUT/'blocking.png')
    centres.save(OUTPUT/'navigable_centres.png')
    boards = []
    frame_records = []
    for tick, frame_record in enumerate(room['frames']):
        panels = []
        for state, shelf_name in [('before', 'shelf_with_lantern'), ('after', 'shelf_empty')]:
            image = opened(base / frame_record['image'])
            image.alpha_composite(sprites[shelf_name], tuple(recipe['shelf_position']))
            image.alpha_composite(sprites['step_stool'], tuple(recipe['stool_position']))
            native = image.convert('RGB')
            native.save(OUTPUT / state / 'scene_frames' / f'frame_{tick+1:02}.png')
            if tick == 0:
                enlarged(native, 4).save(OUTPUT / state / 'room_review.png')
            panels.append(native)
        board = Image.new('RGB', (1800, 1110), '#e8edf2')
        draw = ImageDraw.Draw(board)
        draw.fontmode = '1'
        draw.text((24, 16), f"Elira / compact 10 x 10 cottage / {recipe['status']}", fill='#243529', font_size=26)
        for i, (label, panel) in enumerate(zip(('Before retrieval: lantern on high shelf', 'After retrieval: lantern removed'), panels, strict=True)):
            x = 24 + i * 888
            draw.text((x, 60), label, fill='#243529', font_size=23)
            board.paste(enlarged(panel, 3), (x, 94))
        boards.append(board)
        frame_records.append({**frame_record, 'image': None,
                              'before': f'before/scene_frames/frame_{tick+1:02}.png',
                              'after': f'after/scene_frames/frame_{tick+1:02}.png'})
    boards[0].save(OUTPUT / 'room_states_review.png')
    save_loop(OUTPUT / 'room_states_review.gif', boards, {'duration_ms': 300})
    component_board(recipe, sprites)
    write_json(OUTPUT/'room.json', {
        'id': recipe['id'], 'status': recipe['status'], 'household': 'Elira',
        'story_reference': 'docs/narrative/game_01/CH01_MQ01.md#s05--elira-bridge-cottage-order-flexible',
        'base_room': recipe['base_room']+'/room.json', 'floor_tiles': room['floor_tiles'],
        'room_size': room['room_size'], 'floor_rect': room['floor_rect'], 'entry_rect': room['entry_rect'],
        'objects': objects, 'shelf_position': recipe['shelf_position'],
        'shelf_states': {'before': 'sprites/shelf_with_lantern.png', 'after': 'sprites/shelf_empty.png'},
        'lantern': {'image': 'sprites/lantern_unlit.png', 'size': [12, 24], 'lit': False, 'animated': False},
        'step_stool': {'image': 'sprites/step_stool.png', 'size': [24, 24], 'position': [sx, sy],
                       'floor_rect': [sx+fx, sy+fy, fw, fh], 'movable': False},
        'actor_probe_size': room['actor_probe_size'], 'navigation_start': room['navigation_start'],
        'interaction_approach': recipe['interaction_approach'], 'reachable_probe_positions': len(reached),
        'hero_position': room['hero_position'], 'hero_foot_anchor': room['hero_foot_anchor'],
        'frames': frame_records, 'cycle_duration_ms': 10800, 'loop': True,
        'review': {'image': 'room_states_review.gif', 'scale': 3, 'size': [1800, 1110],
                   'panel_positions': [[24, 94], [912, 94]], 'states_shown_simultaneously': True},
        'engine_collision_implemented': False, 'quest_interaction_implemented': False,
        'purpose': 'Household art and discrete shelf-state review; retrieval/climbing animation and engine wiring are not implemented.'})
    print('Built Elira before/after room states; shelf and stool approach reachable with 24x12 floor probe.')


if __name__ == '__main__':
    build()
