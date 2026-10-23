"""Export source-derived kitchen props and compose a furnished review arrangement."""
from pathlib import Path
from PIL import Image, ImageDraw
from build_eldenmere_stream import read_json, write_json, rgba, enlarged
from build_eldenmere_foliage import opened, nearest, save_loop

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'assets/source/terrain/eldenmere/cottage_kitchen'
OUTPUT=ROOT/'assets/terrain/eldenmere/cottage_kitchen'
INTERIOR=OUTPUT.parent/'cottage_interior'
FURNITURE=OUTPUT.parent/'cottage_furniture'
STORAGE=OUTPUT.parent/'cottage_storage'
HEARTH=OUTPUT.parent/'cottage_hearth'


def extract(recipe):
    source=opened(SOURCE/recipe['source']);sprites={}
    for record in recipe['samples']:
        sample=source.crop(record['crop']).resize(tuple(record['size']),Image.Resampling.NEAREST)
        colors=[rgba(c) for key,c in recipe['palette'].items() if any(key.startswith(p) for p in record['materials'])]
        sprite=Image.new('RGBA',tuple(record['frame_size']));ox,oy=record['offset']
        for y in range(sample.height):
            for x in range(sample.width):
                r,g,b,_=sample.getpixel((x,y))
                if r>160 and b>120 and r>g+70 and b>g+70:continue
                candidates=colors
                if 'iron_sample_rect' in record:
                    ix,iy,iw,ih=record['iron_sample_rect']
                    if ix<=x<ix+iw and iy<=y<iy+ih and (max(r,g,b)-min(r,g,b)<24 or (g>r and b>r)):
                        candidates=[rgba(c) for key,c in recipe['palette'].items() if key.startswith('iron_')]
                sprite.putpixel((x+ox,y+oy),nearest((r,g,b),candidates))
        for directory in (SOURCE/'parts',OUTPUT/'sprites'):sprite.save(directory/f"{record['id']}.png")
        sprites[record['id']]=sprite
    return sprites


def build():
    recipe=read_json(SOURCE/'recipe.json')
    for directory in (SOURCE/'parts',OUTPUT/'sprites',OUTPUT/'scene_frames'):directory.mkdir(parents=True,exist_ok=True)
    sprites=extract(recipe);room=read_json(HEARTH/'room.json');base=read_json(INTERIOR/'room.json')
    layer=Image.new('RGBA',tuple(room['room_size']));atlas=Image.new('RGBA',(144,48));records=[]
    for index,record in enumerate(recipe['samples']):
        sprite=sprites[record['id']];layer.alpha_composite(sprite,tuple(record['position']));atlas.paste(sprite,(index*48,0))
        records.append({**record,'image':f"sprites/{record['id']}.png",'atlas_rect':[index*48,0,*sprite.size],'animated':False})
    layer.save(OUTPUT/'kitchen_layer.png');atlas.save(OUTPUT/'sprite_sheet.png')
    furnishings=Image.new('RGBA',layer.size)
    for r in recipe['furniture_placements']:furnishings.alpha_composite(opened(FURNITURE/'sprites'/f"{r['id']}.png"),tuple(r['position']))
    for r in recipe['storage_placements']:furnishings.alpha_composite(opened(STORAGE/'sprites'/f"{r['id']}.png"),tuple(r['position']))
    furnishings.save(OUTPUT/'approved_furnishings_layer.png')
    structure=opened(INTERIOR/'room/structure.png');hero=opened(ROOT/'assets/characters/caelan/idle_front.png')
    previews=[];frames=[]
    for index,r in enumerate(room['frames']):
        image=structure.copy();image.alpha_composite(opened(INTERIOR/base['frames'][r['daylight_phase']]['light']))
        image.alpha_composite(opened(HEARTH/r['floor_glow']));image.alpha_composite(furnishings);image.alpha_composite(layer)
        image.alpha_composite(opened(HEARTH/'frames'/f"frame_{r['fire_phase']+1:02}.png"),tuple(room['hearth_position']))
        image.alpha_composite(hero,tuple(room['hero_position']))
        path=f'scene_frames/frame_{index+1:02}.png';image.convert('RGB').save(OUTPUT/path)
        previews.append(enlarged(image.convert('RGB'),recipe['review_scale']))
        frames.append({**r,'image':path,'floor_glow':f"../cottage_hearth/{r['floor_glow']}"})
    previews[0].save(OUTPUT/'room_review.png');save_loop(OUTPUT/'room_review.gif',previews,{'duration_ms':room['frames'][0]['duration_ms']})
    board=Image.new('RGB',(1248,620),'#e8edf2');draw=ImageDraw.Draw(board);draw.fontmode='1'
    draw.text((24,18),f"Eldenmere kitchen props / {recipe['status']}",fill='#243529',font_size=26)
    for index,record in enumerate(recipe['samples']):
        x=24+index*416;draw.text((x,76),record['id'].title(),fill='#243529',font_size=24)
        cell=Image.new('RGBA',(48,48),'#c5c2b4');sprite=sprites[record['id']]
        cell.alpha_composite(sprite,((48-sprite.width)//2,(48-sprite.height)//2))
        board.paste(enlarged(cell.convert('RGB'),8),(x,116))
        draw.text((x,528),f'{sprite.width} x {sprite.height} / static',fill='#243529',font_size=22)
    draw.text((24,584),'24px grid / original furniture and character pixels preserved',fill='#243529',font_size=22)
    board.save(OUTPUT/'components_review.png')
    write_json(OUTPUT/'kitchen.json',{'id':recipe['id'],'status':recipe['status'],'tile_size':[24,24],
        'palette':recipe['palette'],'sprites':records,'sprite_sheet':'sprite_sheet.png','atlas_cell_size':[48,48],'atlas_columns':3,
        'source_recipe':'../../../source/terrain/eldenmere/cottage_kitchen/recipe.json','animation':recipe['animation'],
        'collision_implemented':False,'interaction_implemented':False})
    write_json(OUTPUT/'room.json',{'status':recipe['status'],'purpose':'Illustrative kitchen asset review, not an approved cottage size or household layout',
        'room_source':recipe['room_source'],'room_size':room['room_size'],'floor_rect':[24,72,240,192],
        'furniture_placements':recipe['furniture_placements'],'storage_placements':recipe['storage_placements'],
        'kitchen_placements':[{'id':r['id'],'position':r['position']} for r in records],
        'kitchen_layer':'kitchen_layer.png','approved_furnishings_layer':'approved_furnishings_layer.png',
        'clear_path_rect':recipe['clear_path_rect'],'hero_position':room['hero_position'],'hearth_position':room['hearth_position'],
        'entry_rect':room['entry_rect'],'frames':frames,'cycle_duration_ms':room['cycle_duration_ms'],'loop':True,
        'review_scale':recipe['review_scale'],'collision_implemented':False,
        'draw_order':['structure','approved_daylight','approved_firelight','approved_furnishings','kitchen','approved_hearth','character']})
    print('Built counter, washbasin and pantry; retained the approved 10.8-second fire/daylight loop.')


if __name__=='__main__':build()
