"""Export shelf/cupboard source and extend the approved furnished room for review."""
from pathlib import Path
from PIL import Image, ImageDraw
from build_eldenmere_stream import read_json, write_json, rgba, enlarged
from build_eldenmere_foliage import opened, nearest, save_loop

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'assets/source/terrain/eldenmere/cottage_storage'
OUTPUT = ROOT / 'assets/terrain/eldenmere/cottage_storage'
INTERIOR = OUTPUT.parent / 'cottage_interior'
FURNITURE = OUTPUT.parent / 'cottage_furniture'


def extract(recipe):
    reference = opened(SOURCE / recipe['source'])
    sprites = {}
    for record in recipe['samples']:
        sample = reference.crop(record['crop']).resize(tuple(record['size']),Image.Resampling.NEAREST)
        colors = [rgba(c) for key,c in recipe['palette'].items()
                  if any(key.startswith(prefix) for prefix in record['allowed_materials'])]
        sprite = Image.new('RGBA',tuple(record['frame_size']))
        ox,oy = record['offset']
        for y in range(sample.height):
            for x in range(sample.width):
                r,g,b,_ = sample.getpixel((x,y))
                if r > 160 and b > 120 and r > g+70 and b > g+70:
                    continue
                candidates = colors
                if 'iron_sample_rect' in record:
                    ix,iy,iw,ih = record['iron_sample_rect']
                    if ix <= x < ix+iw and iy <= y < iy+ih and (max(r,g,b)-min(r,g,b)<24 or (g>r and b>r)):
                        candidates = [rgba(c) for key,c in recipe['palette'].items() if key.startswith('iron_')]
                sprite.putpixel((x+ox,y+oy),nearest((r,g,b),candidates))
        for directory in (SOURCE/'parts',OUTPUT/'sprites'):
            sprite.save(directory/f"{record['id']}.png")
        sprites[record['id']] = sprite
    return sprites


def review_board(recipe,sprites):
    board = Image.new('RGB',(856,650),'#e8edf2')
    draw = ImageDraw.Draw(board); draw.fontmode = '1'
    draw.text((24,20),f"Eldenmere shelf and cupboard / {recipe['status']}",fill='#243529',font_size=26)
    for index,record in enumerate(recipe['samples']):
        x = 24+index*416
        draw.text((x,78),record['id'].title(),fill='#243529',font_size=24)
        cell = Image.new('RGBA',(48,48),'#c5c2b4')
        sprite = sprites[record['id']]
        cell.alpha_composite(sprite,(0,(48-sprite.height)//2))
        board.paste(enlarged(cell.convert('RGB'),8),(x,120))
        draw.text((x,528),f"{sprite.width} x {sprite.height} / static",fill='#243529',font_size=22)
    draw.text((24,596),'24px terrain grid / original furniture and room remain approved',fill='#243529',font_size=21)
    board.save(OUTPUT/'components_review.png')


def build():
    recipe = read_json(SOURCE/'recipe.json')
    for directory in (SOURCE/'parts',OUTPUT/'sprites',OUTPUT/'scene_frames'):
        directory.mkdir(parents=True,exist_ok=True)
    sprites = extract(recipe)
    room = read_json(FURNITURE/'room.json')
    base = read_json(INTERIOR/'room.json')
    layer = Image.new('RGBA',tuple(room['room_size']))
    atlas = Image.new('RGBA',(96,48)); records = []
    for index,record in enumerate(recipe['samples']):
        sprite = sprites[record['id']]
        layer.alpha_composite(sprite,tuple(record['position']))
        atlas.paste(sprite,(index*48,0))
        records.append({**record,'image':f"sprites/{record['id']}.png",
                        'atlas_rect':[index*48,0,*sprite.size],'animated':False,'status':recipe['status']})
    layer.save(OUTPUT/'storage_layer.png'); atlas.save(OUTPUT/'sprite_sheet.png')
    structure = opened(INTERIOR/'room/structure.png')
    furniture = opened(FURNITURE/room['furniture_layer'])
    hero = opened(ROOT/'assets/characters/caelan/idle_front.png')
    previews = []; frames = []
    for phase,record in enumerate(base['frames']):
        image = structure.copy()
        image.alpha_composite(opened(INTERIOR/record['light']))
        image.alpha_composite(furniture)
        image.alpha_composite(layer)
        image.alpha_composite(hero,tuple(room['hero_position']))
        name = f'scene_frames/frame_{phase+1:02}.png'
        image.convert('RGB').save(OUTPUT/name)
        previews.append(enlarged(image.convert('RGB'),recipe['review_scale']))
        frames.append({'image':name,'light':f"../cottage_interior/{record['light']}",
                       'duration_ms':record['duration_ms']})
    previews[0].save(OUTPUT/'room_review.png')
    save_loop(OUTPUT/'room_review.gif',previews,{'duration_ms':recipe['duration_ms']})
    review_board(recipe,sprites)
    write_json(OUTPUT/'storage.json',{'id':recipe['id'],'status':recipe['status'],'tile_size':[24,24],
        'palette':recipe['palette'],'sprites':records,'sprite_sheet':'sprite_sheet.png',
        'atlas_cell_size':[48,48],'atlas_columns':2,
        'source_recipe':'../../../source/terrain/eldenmere/cottage_storage/recipe.json',
        'animation':recipe['animation'],'collision_implemented':False,'door_interaction_implemented':False})
    write_json(OUTPUT/'room.json',{'status':recipe['status'],
        'purpose':'Shelf and cupboard art review; illustrative generic room, not a named household or final level',
        'room_source':recipe['room_source'],'room_size':room['room_size'],
        'placements':[{'id':r['id'],'position':r['position'],'mount':r['mount']} for r in records],
        'storage_layer':'storage_layer.png','furniture_layer':'../cottage_furniture/furniture_layer.png',
        'clear_path_rect':recipe['clear_path_rect'],'entry_rect':room['entry_rect'],
        'hero_position':room['hero_position'],'draw_order':['structure','approved_daylight','approved_furniture','storage','character'],
        'frames':frames,'cycle_duration_ms':room['cycle_duration_ms'],'loop':True,
        'review_scale':recipe['review_scale'],'collision_implemented':False,'exterior_transition_implemented':False,
        'hearth_included':False})
    print('Built static wall shelf and closed cupboard with the approved furnished-room daylight loop.')


if __name__ == '__main__': build()
