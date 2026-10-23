"""Export generated furniture source at native scale; furnish the approved room."""
from pathlib import Path
from PIL import Image, ImageDraw
from build_eldenmere_stream import read_json, write_json, rgba, enlarged
from build_eldenmere_foliage import opened, nearest, save_loop

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'assets/source/terrain/eldenmere/cottage_furniture'
OUTPUT = ROOT / 'assets/terrain/eldenmere/cottage_furniture'
INTERIOR = OUTPUT.parent / 'cottage_interior'


def extract(recipe):
    sprites = {}
    for record in recipe['samples']:
        if 'mirror_of' in record:
            sprite = sprites[record['mirror_of']].transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        else:
            reference = opened(SOURCE / record.get('source',recipe['source']))
            colors = [rgba(c) for key,c in recipe['palette'].items()
                      if record.get('material') != 'wood' or key == 'outline' or key.startswith('wood_')]
            sample = reference.crop(record['crop']).resize(tuple(record['size']), Image.Resampling.NEAREST)
            sprite = Image.new('RGBA', tuple(record['frame_size']))
            ox, oy = record['offset']
            for y in range(sample.height):
                for x in range(sample.width):
                    r, g, b, _ = sample.getpixel((x,y))
                    if r > 160 and b > 120 and r > g + 70 and b > g + 70:
                        continue
                    sprite.putpixel((x+ox,y+oy), nearest((r,g,b), colors))
        sprite.save(SOURCE / 'parts' / f"{record['id']}.png")
        sprite.save(OUTPUT / 'sprites' / f"{record['id']}.png")
        sprites[record['id']] = sprite
    # Keep the previous default filename usable, with the corrected down view.
    for directory in (SOURCE/'parts',OUTPUT/'sprites'):
        sprites['chair_down'].save(directory/'chair.png')
    return sprites


def review_board(recipe, sprites):
    board = Image.new('RGB', (1104,1288), '#e8edf2')
    draw = ImageDraw.Draw(board); draw.fontmode = '1'
    draw.text((24,20), f"Eldenmere cottage furniture / {recipe['status']}", fill='#243529', font_size=26)
    for index, record in enumerate(recipe['samples']):
        x = 24 + index%3*360; y = index//3*520
        draw.text((x,76+y), record['id'].replace('_',' ').title(), fill='#243529', font_size=24)
        cell = Image.new('RGBA',(48,72),'#c5c2b4')
        sprite = sprites[record['id']]
        cell.alpha_composite(sprite,((48-sprite.width)//2,72-sprite.height))
        board.paste(enlarged(cell.convert('RGB'),6),(x,116+y))
        draw.text((x,568+y), f"{sprite.width} x {sprite.height} / {record['status']}", fill='#243529', font_size=20)
    hero = opened(ROOT / 'assets/characters/caelan/idle_front.png')
    board.paste(enlarged(hero,3),(24,1160),enlarged(hero,3))
    draw.text((112,1190), 'Original 24 x 36 character for scale (3x); furniture above at 6x',fill='#243529',font_size=21)
    board.save(OUTPUT / 'components_review.png')


def build():
    recipe = read_json(SOURCE / 'recipe.json')
    for path in (SOURCE/'parts', OUTPUT/'sprites', OUTPUT/'scene_frames'):
        path.mkdir(parents=True,exist_ok=True)
    sprites = extract(recipe)
    room = read_json(INTERIOR / 'room.json')
    layer = Image.new('RGBA',tuple(room['room_size']))
    atlas = Image.new('RGBA',(144,144)); records = []
    for index, record in enumerate(recipe['samples']):
        sprite = sprites[record['id']]
        layer.alpha_composite(sprite,tuple(record['position']))
        ax,ay = index%3*48,index//3*72
        atlas.paste(sprite,(ax,ay))
        records.append({**record,'image': f"sprites/{record['id']}.png",
                        'atlas_rect': [ax,ay,*sprite.size], 'animated': False})
    layer.save(OUTPUT / 'furniture_layer.png'); atlas.save(OUTPUT / 'sprite_sheet.png')
    structure = opened(INTERIOR / 'room/structure.png')
    hero = opened(ROOT / 'assets/characters/caelan/idle_front.png')
    previews = []; frames = []
    for phase, record in enumerate(room['frames']):
        image = structure.copy()
        image.alpha_composite(opened(INTERIOR / record['light']))
        image.alpha_composite(layer)
        image.alpha_composite(hero,tuple(room['hero_position']))
        name = f'scene_frames/frame_{phase+1:02}.png'
        image.convert('RGB').save(OUTPUT / name)
        previews.append(enlarged(image.convert('RGB'),recipe['review_scale']))
        frames.append({'image':name,'light': f"../cottage_interior/{record['light']}",
                       'duration_ms':record['duration_ms']})
    previews[0].save(OUTPUT / 'room_review.png')
    save_loop(OUTPUT / 'room_review.gif',previews,{'duration_ms':recipe['duration_ms']})
    review_board(recipe,sprites)
    write_json(OUTPUT / 'furniture.json',{
        'id':recipe['id'],'status':recipe['status'],'tile_size':[24,24],
        'palette':recipe['palette'],'sprites':records,'sprite_sheet':'sprite_sheet.png',
        'atlas_cell_size':[48,72],'atlas_columns':3,
        'source_recipe':'../../../source/terrain/eldenmere/cottage_furniture/recipe.json',
        'aliases':{'chair':'chair_down'},
        'direction_convention':'Direction the seated person would face; up shows the back of the chair.',
        'animation':recipe['animation'],'collision_implemented':False})
    write_json(OUTPUT / 'room.json',{
        'status':recipe['status'],'purpose':'Furniture art review; illustrative generic room, not a final household layout',
        'room_source':recipe['room_source'],'room_size':room['room_size'],
        'placements':[{'id':r['id'],'position':r['position']} for r in records],
        'furniture_layer':'furniture_layer.png','clear_path_rect':recipe['clear_path_rect'],
        'floor_rect':room['floor_rect'],'entry_rect':room['entry_rect'],
        'hero_position':room['hero_position'],'character_source':'../../../characters/caelan/idle_front.png',
        'draw_order':['structure','approved_daylight','furniture','character'],
        'frames':frames,'cycle_duration_ms':room['cycle_duration_ms'],'loop':True,
        'review_scale':recipe['review_scale'],'collision_implemented':False,
        'exterior_transition_implemented':False})
    print('Built unchanged approved bed/table and four refined chair directions; retained the 5.4-second daylight loop.')


if __name__ == '__main__': build()
