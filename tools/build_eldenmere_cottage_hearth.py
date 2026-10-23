"""Assemble source-derived hearth/fire poses and local lighting in the approved room."""
import math
from pathlib import Path
from PIL import Image, ImageDraw
from build_eldenmere_stream import read_json, write_json, rgba, enlarged
from build_eldenmere_foliage import opened, nearest, save_loop

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/terrain/eldenmere/cottage_hearth'
OUTPUT = ROOT/'assets/terrain/eldenmere/cottage_hearth'
INTERIOR = OUTPUT.parent/'cottage_interior'
FURNITURE = OUTPUT.parent/'cottage_furniture'
STORAGE = OUTPUT.parent/'cottage_storage'


def mix(pixel,target,ratio):
    return tuple(round(a+(b-a)*ratio) for a,b in zip(pixel[:3],target[:3]))+(255,)


def extract(recipe):
    source = opened(SOURCE/recipe['source']); parts = {}
    for record in recipe['samples']:
        sample = source.crop(record['crop']).resize(tuple(record['size']),Image.Resampling.NEAREST)
        colors = [rgba(c) for key,c in recipe['palette'].items()
                  if any(key.startswith(prefix) for prefix in record['materials'])]
        part = Image.new('RGBA',sample.size)
        for y in range(sample.height):
            for x in range(sample.width):
                r,g,b,_ = sample.getpixel((x,y))
                if r>160 and b>120 and r>g+70 and b>g+70: continue
                part.putpixel((x,y),nearest((r,g,b),colors))
        for directory in (SOURCE/'parts',OUTPUT/'parts'): part.save(directory/f"{record['id']}.png")
        parts[record['id']] = part
    return parts


def hearth_frames(recipe,parts):
    body = Image.new('RGBA',tuple(recipe['frame_size']))
    for record in recipe['samples']:
        if 'position' in record: body.alpha_composite(parts[record['id']],tuple(record['position']))
    body.save(OUTPUT/'structure.png')
    stone = {rgba(c) for key,c in recipe['palette'].items() if key.startswith('stone_')}
    ember = Image.new('L',body.size); rim = Image.new('L',body.size); fire = Image.new('L',body.size)
    x0,y0,w,h = recipe['rim_rect']
    for y in range(body.height):
        for x in range(body.width):
            pixel = body.getpixel((x,y))
            if pixel==rgba(recipe['palette']['ember']): ember.putpixel((x,y),255)
            if x0<=x<x0+w and y0<=y<y0+h and pixel in stone: rim.putpixel((x,y),255)
    frames = []; target = rgba(recipe['glow_color'])
    for phase in range(4):
        frame = body.copy()
        for y in range(body.height):
            for x in range(body.width):
                if rim.getpixel((x,y)):
                    frame.putpixel((x,y),mix(body.getpixel((x,y)),target,recipe['glow_strengths'][phase]))
                if ember.getpixel((x,y)): frame.putpixel((x,y),rgba(recipe['ember_colors'][phase]))
        flame = parts[f'flame_{phase+1:02}']; px,py = recipe['flame_position']
        frame.alpha_composite(flame,(px,py))
        for y in range(flame.height):
            for x in range(flame.width):
                if flame.getpixel((x,y))[3]: fire.putpixel((px+x,py+y),255)
        frame.save(OUTPUT/'frames'/f'frame_{phase+1:02}.png'); frames.append(frame)
    for name,mask in (('fire',fire),('embers',ember),('rim',rim)): mask.save(OUTPUT/'masks'/f'{name}.png')
    return frames


def floor_mask(recipe):
    floor = opened(INTERIOR/'room/floor.png').getchannel('A')
    mask = Image.new('L',floor.size)
    x0,y0,w,h = recipe['floor_glow_rect']
    for y in range(y0,y0+h):
        for x in range(x0,x0+w):
            distance = ((x+.5-x0-w/2)/(w/2))**2+((y+.5-y0-h/2)/(h/2))**2
            if floor.getpixel((x,y)) and distance<=1:
                mask.putpixel((x,y),255 if distance<=.45 else 128)
    mask.save(OUTPUT/'masks/floor_glow.png')
    return mask


def apply_floor_glow(image,mask,recipe,phase):
    overlay = Image.new('RGBA',image.size); target = rgba(recipe['glow_color'])
    for y in range(mask.height):
        for x in range(mask.width):
            strength = mask.getpixel((x,y))
            if strength:
                ratio = recipe['glow_strengths'][phase]*(1 if strength==255 else .5)
                overlay.putpixel((x,y),mix(image.getpixel((x,y)),target,ratio))
    image.alpha_composite(overlay)
    return overlay


def build():
    recipe = read_json(SOURCE/'recipe.json')
    for directory in (SOURCE/'parts',OUTPUT/'parts',OUTPUT/'frames',OUTPUT/'masks',OUTPUT/'scene_frames',OUTPUT/'lighting'):
        directory.mkdir(parents=True,exist_ok=True)
    parts = extract(recipe); frames = hearth_frames(recipe,parts); mask = floor_mask(recipe)
    atlas = Image.new('RGBA',(192,72))
    for phase,frame in enumerate(frames): atlas.paste(frame,(phase*48,0))
    atlas.save(OUTPUT/'sprite_sheet.png')
    board = Image.new('RGB',(1248,680),'#e8edf2'); draw = ImageDraw.Draw(board); draw.fontmode='1'
    draw.text((24,18),f"Eldenmere animated hearth / {recipe['status']}",fill='#243529',font_size=26)
    for phase,frame in enumerate(frames):
        cell = Image.new('RGBA',frame.size,'#c5c2b4'); cell.alpha_composite(frame)
        board.paste(enlarged(cell.convert('RGB'),6),(24+phase*306,90))
        draw.text((24+phase*306,546),f'Pose {phase+1} / 300ms',fill='#243529',font_size=22)
    draw.text((24,622),'48 x 72 / fixed stone and logs / four fire poses / no indoor smoke',fill='#243529',font_size=24)
    board.save(OUTPUT/'components_review.png')
    closeups=[]
    for frame in frames:
        cell=Image.new('RGBA',frame.size,'#c5c2b4');cell.alpha_composite(frame)
        closeups.append(enlarged(cell.convert('RGB'),8))
    save_loop(OUTPUT/'hearth_review.gif',closeups,{'duration_ms':recipe['fire_duration_ms']})
    room = read_json(STORAGE/'room.json'); base = read_json(INTERIOR/'room.json')
    structure = opened(INTERIOR/'room/structure.png'); furniture = opened(FURNITURE/'furniture_layer.png')
    storage = opened(STORAGE/'storage_layer.png'); hero = opened(ROOT/'assets/characters/caelan/idle_front.png')
    total_ms = math.lcm(4*recipe['fire_duration_ms'],room['cycle_duration_ms'])
    tick_ms = math.gcd(recipe['fire_duration_ms'],base['frames'][0]['duration_ms'])
    previews=[]; records=[]
    for tick in range(total_ms//tick_ms):
        time = tick*tick_ms
        phase = time//recipe['fire_duration_ms']%4
        daylight = time//base['frames'][0]['duration_ms']%len(base['frames'])
        image = structure.copy(); image.alpha_composite(opened(INTERIOR/base['frames'][daylight]['light']))
        overlay = apply_floor_glow(image,mask,recipe,phase)
        light_path=f'lighting/frame_{tick+1:02}.png';overlay.save(OUTPUT/light_path)
        image.alpha_composite(furniture);image.alpha_composite(storage)
        image.alpha_composite(frames[phase],tuple(recipe['position']))
        image.alpha_composite(hero,tuple(room['hero_position']))
        path=f'scene_frames/frame_{tick+1:02}.png';image.convert('RGB').save(OUTPUT/path)
        previews.append(enlarged(image.convert('RGB'),recipe['review_scale']))
        records.append({'image':path,'floor_glow':light_path,'fire_phase':phase,'daylight_phase':daylight,'duration_ms':tick_ms})
    previews[0].save(OUTPUT/'room_review.png');save_loop(OUTPUT/'room_review.gif',previews,{'duration_ms':tick_ms})
    write_json(OUTPUT/'hearth.json',{'id':recipe['id'],'status':recipe['status'],'frame_size':recipe['frame_size'],
        'tile_size':[24,24],'sprite_sheet':'sprite_sheet.png','palette':recipe['palette'],
        'frames':[{'image':f'frames/frame_{i+1:02}.png','atlas_rect':[i*48,0,48,72],'duration_ms':recipe['fire_duration_ms']} for i in range(4)],
        'cycle_duration_ms':4*recipe['fire_duration_ms'],'structure_moves':False,'logs_move':False,
        'static_base':'structure.png','ember_colors':recipe['ember_colors'],'glow_color':recipe['glow_color'],
        'flame_position':recipe['flame_position'],'opening_rect':recipe['opening_rect'],
        'animation_masks':{'fire':'masks/fire.png','embers':'masks/embers.png','rim':'masks/rim.png'},
        'floor_glow_mask':'masks/floor_glow.png','glow_strengths':recipe['glow_strengths'],
        'smoke_included':False,'collision_implemented':False,
        'source_recipe':'../../../source/terrain/eldenmere/cottage_hearth/recipe.json'})
    write_json(OUTPUT/'room.json',{'status':recipe['status'],'purpose':'Hearth art review in the illustrative expanded cottage interior',
        'room_source':recipe['room_source'],'room_size':room['room_size'],'hearth_position':recipe['position'],
        'hearth_floor_rect':recipe['floor_rect'],'clear_path_rect':recipe['clear_path_rect'],
        'hero_position':room['hero_position'],'entry_rect':room['entry_rect'],
        'draw_order':['structure','approved_daylight','floor_firelight','approved_furniture','approved_storage','hearth','character'],
        'frames':records,'cycle_duration_ms':total_ms,'loop':True,'review_scale':recipe['review_scale'],
        'fire_cycle_duration_ms':4*recipe['fire_duration_ms'],'daylight_cycle_duration_ms':room['cycle_duration_ms'],
        'collision_implemented':False,'exterior_transition_implemented':False})
    print(f'Built fixed stone hearth, four fire poses and local light; scene loop {total_ms}ms / {len(records)} frames.')


if __name__=='__main__':build()
