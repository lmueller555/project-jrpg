"""Build directed 24px earth channels, stream intakes and trickling outlets."""

from copy import deepcopy
from pathlib import Path
from random import Random

from PIL import Image, ImageDraw

from build_eldenmere_stream import read_json, write_json, rgba, enlarged, save_loop


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'assets/source/terrain/eldenmere/irrigation'
OUTPUT = ROOT / 'assets/terrain/eldenmere/irrigation'
PORTS = {'N':1,'E':2,'S':4,'W':8}
VECTORS = {'N':(0,-1),'E':(1,0),'S':(0,1),'W':(-1,0)}
OPPOSITE = {'N':'S','E':'W','S':'N','W':'E'}
ROTATIONS = {'S':None,'E':Image.Transpose.ROTATE_90,'N':Image.Transpose.ROTATE_180,'W':Image.Transpose.ROTATE_270}


def rotated(image,direction):
    return image.copy() if direction=='S' else image.transpose(ROTATIONS[direction])


def channel_water(mask,x,y):
    if not mask:
        return False
    hub = 8<=x<16 and 8<=y<16 and (x,y) not in ((8,8),(15,8),(8,15),(15,15))
    return bool(hub or mask&1 and 8<=x<16 and y<12 or mask&2 and x>=12 and 8<=y<16
                or mask&4 and 8<=x<16 and y>=12 or mask&8 and x<12 and 8<=y<16)


def extract_parts(recipe,palette):
    source = Image.open(SOURCE / recipe['source']).convert('RGB')
    directory = SOURCE / 'parts'
    directory.mkdir(exist_ok=True)
    sample = source.crop(recipe['earth_crop']).resize((2,24),Image.Resampling.NEAREST)
    earth = Image.new('RGBA',(2,24))
    ramp = [rgba(palette['dirt'][name]) for name in ('edge','shadow','base')]
    for y in range(24):
        for x in range(2):
            c = sample.getpixel((x,y))
            color = min(ramp,key=lambda p:sum((a-b)**2 for a,b in zip(c,p[:3])))
            earth.putpixel((x,y),color)
    earth.save(directory / 'earth_strip.png')
    sample = source.crop(recipe['droplet_crop']).resize(tuple(recipe['droplet_size']),Image.Resampling.NEAREST)
    drop = Image.new('RGBA',sample.size)
    for y in range(sample.height):
        for x in range(sample.width):
            if sum(sample.getpixel((x,y)))/3>=recipe['droplet_threshold']:
                drop.putpixel((x,y),(255,255,255,255))
    if drop.getbbox() is None:
        raise ValueError('The source droplet crop exported empty')
    drop.save(directory / 'droplet_mask.png')
    return earth,drop


def core_layers(mask,palette,earth):
    bank,water = Image.new('RGBA',(24,24)),Image.new('RGBA',(24,24))
    for y in range(24):
        for x in range(24):
            if channel_water(mask,x,y):
                water.putpixel((x,y),(255,255,255,255))
                if any(not channel_water(mask,x+dx,y+dy) for dx,dy in ((-1,0),(1,0),(0,-1),(0,1))):
                    bank.putpixel((x,y),rgba(palette['water']['shallow']))
                continue
            for radius in (1,2):
                if any(channel_water(mask,x+dx,y+dy) for dx in range(-radius,radius+1) for dy in range(-radius,radius+1)):
                    color = rgba(palette['dirt']['shadow' if radius==1 else 'edge'])
                    if min(x,y,23-x,23-y)>1 and (3*x+5*y)%17==4:
                        color = earth.getpixel((radius-1,(x+y)%24))
                    bank.putpixel((x,y),color)
                    break
    return bank,water


def special_layers(kind,direction,palette):
    bank,water = Image.new('RGBA',(24,24)),Image.new('RGBA',(24,24))
    if kind=='inlet':
        for y in range(12,24):
            for x in range(8,16):
                water.putpixel((x,y),(255,255,255,255))
            if y>=18:
                for x in (6,7,16,17):
                    bank.putpixel((x,y),rgba(palette['dirt']['edge' if x in (6,17) else 'shadow']))
                for x in (8,15):
                    bank.putpixel((x,y),rgba(palette['water']['shallow']))
    else:
        for y in range(24):
            for x in range(24):
                receiver = ((x-11.5)/3)**2+((y-20.5)/2)**2<=1
                mud = ((x-11.5)/5)**2+((y-20.5)/3)**2<=1
                if mud and not receiver:
                    bank.putpixel((x,y),rgba(palette['dirt']['shadow']))
                if 8<=x<16 and y<12 or 10<=x<14 and 12<=y<15 or receiver:
                    water.putpixel((x,y),(255,255,255,255))
                if x in (6,7,16,17) and y<12:
                    bank.putpixel((x,y),rgba(palette['dirt']['edge' if x in (6,17) else 'shadow']))
                if x in (8,15) and y<12 or 8<=x<16 and 12<=y<14 and x not in (10,11,12,13):
                    bank.putpixel((x,y),rgba(palette['water']['shallow'] if y<12 else palette['dirt']['shadow']))
                if receiver and (x in (9,14) or y in (19,22)):
                    bank.putpixel((x,y),rgba(palette['water']['shallow']))
    return rotated(bank,direction),rotated(water,direction)


def flow_points(port,incoming):
    for t in range(12):
        distance = t if incoming else 12+t
        for lane in (11,12):
            if port=='N': point = (lane,t if incoming else 11-t)
            elif port=='E': point = (23-t if incoming else 12+t,lane)
            elif port=='S': point = (lane,23-t if incoming else 12+t)
            else: point = (t if incoming else 11-t,lane)
            yield point,distance


def core_frame(record,bank,mask,phase,recipe,palette):
    water = Image.new('RGBA',(24,24),rgba(palette['water']['base']))
    image = Image.new('RGBA',(24,24))
    image.paste(water,(0,0),mask.getchannel('A'))
    points = dict(flow_points(record['input'],True))
    for port in record['outputs']:
        for point,distance in flow_points(port,False):
            points.setdefault(point,distance)
    for point,distance in points.items():
        mark = (distance-phase*recipe['flow_step_pixels'])%recipe['flow_period_pixels']
        if mark in (0,1) and mask.getpixel(point)[3]:
            image.putpixel(point,rgba(palette['water']['reflection' if mark==0 else 'flow']))
    return Image.alpha_composite(image,bank)


def special_frame(record,phase,recipe,palette,drop):
    direction,kind = record['direction'],record['kind']
    bank,mask = special_layers(kind,'S',palette)
    record_s = {'input':'N','outputs':['S']}
    image = core_frame(record_s,bank,mask,phase,recipe,palette)
    if kind=='outlet':
        fx = Image.new('RGBA',(24,24))
        for y in range(12,12+recipe['trickle_length'][phase]):
            fx.putpixel((11,y),rgba(palette['water']['flow']))
            fx.putpixel((12,y),rgba(palette['water']['base']))
        left,top = 11+recipe['trickle_x'][phase],recipe['trickle_y'][phase]
        for y in range(drop.height):
            for x in range(drop.width):
                if drop.getpixel((x,y))[3]:
                    fx.putpixel((left+x,top+y),rgba(palette['water']['reflection']))
        if phase in (4,5):
            for x in range(10,14):
                fx.putpixel((x,21 if phase==4 else 20),rgba(palette['water']['flow']))
        image = Image.alpha_composite(image,fx)
    return rotated(image,direction)


def routes():
    records = []
    for mask in range(1,16):
        connected = [name for name,bit in PORTS.items() if mask&bit]
        for incoming in connected:
            records.append({'id':f'channel_{mask:02}_from_{incoming.lower()}','kind':'channel','ports':mask,
                            'input':incoming,'outputs':[p for p in connected if p!=incoming]})
    for kind in ('inlet','outlet'):
        for direction in PORTS:
            records.append({'id':f'{kind}_{direction.lower()}','kind':kind,'direction':direction,
                            'ports':PORTS[direction if kind=='inlet' else OPPOSITE[direction]],
                            'input':'stream' if kind=='inlet' else OPPOSITE[direction],
                            'outputs':[direction] if kind=='inlet' else ['receiver']})
            if kind=='outlet':
                records[-1]['effect_bounds']={'S':[10,12,4,10],'E':[12,10,10,4],
                                               'N':[10,2,4,10],'W':[2,10,10,4]}[direction]
    return records


def placements():
    result = [{'cell':[14,15],'route':'inlet_s'}]
    def add(x,y,incoming,*outgoing):
        mask = sum(PORTS[p] for p in (incoming,*outgoing))
        result.append({'cell':[x,y],'route':f'channel_{mask:02}_from_{incoming.lower()}'})
    add(14,16,'N','S'); add(14,17,'N','W','S'); add(14,18,'N','S'); add(14,19,'N','W')
    for x in (13,12,11): add(x,17,'E','W')
    add(10,17,'E','W','N')
    for x in (9,8): add(x,17,'E','W')
    add(7,17,'E','S'); add(7,18,'N','S')
    for x in (13,12): add(x,19,'E','W')
    for x,y,d in ((10,16,'N'),(7,19,'S'),(11,19,'W')):
        result.append({'cell':[x,y],'route':f'outlet_{d.lower()}'})
    return result


def build_scene(recipe,stream_pack,ground_pack,route_tiles,records):
    old = read_json(stream_pack / 'review_scene.json')
    ground_meta,stream_meta = read_json(ground_pack / 'tileset.json'),read_json(stream_pack / 'tileset.json')
    width,height = recipe['scene_size']
    rng = Random(81)
    grass_ids = deepcopy(old['grass_variants'])
    grass_ids.extend([[rng.choices(range(4),weights=(5,3,2,1))[0] for x in range(width)] for y in range(height-len(grass_ids))])
    grass = [Image.open(ground_pack/p).convert('RGBA') for p in ground_meta['grass']['images']]
    dirt = {t['mask']:Image.open(ground_pack/t['image']).convert('RGBA') for t in ground_meta['tiles']}
    fills = [Image.open(ground_pack/p).convert('RGBA') for p in ground_meta['dirt_interiors']['images']]
    banks = Image.open(stream_pack / stream_meta['banks']).convert('RGBA')
    masks = Image.open(stream_pack / stream_meta['water_masks']).convert('RGBA')
    surfaces = [[Image.open(stream_pack/f['image']).convert('RGBA') for f in v['frames']] for v in stream_meta['surface']['variants']]
    base = Image.new('RGBA',(width*24,height*24))
    for y in range(height):
        for x in range(width):
            base.paste(grass[grass_ids[y][x]],(x*24,y*24))
            if y<len(old['dirt_masks']) and old['dirt_masks'][y][x] is not None:
                mask,fill = old['dirt_masks'][y][x],old['dirt_fill_variants'][y][x]
                base.alpha_composite(fills[fill] if fill is not None else dirt[mask],(x*24,y*24))
    characters = deepcopy(old['characters'])
    for character in characters:
        if character['name'] in ('mira','female_02'):
            x,y = (12,18) if character['name']=='mira' else (8,20)
            character['foot']=[x*24+12,y*24+20]
            character['position']=[x*24,y*24-14]
    characters.sort(key=lambda c:c['foot'][1])
    cells = placements()
    previews,closeups = [],[]
    for phase in range(6):
        image = base.copy()
        for y,row in enumerate(old['water_masks']):
            for x,mask in enumerate(row):
                if mask is None: continue
                record = stream_meta['tiles'][stream_meta['lookup_256'][mask]]
                tx,ty,w,h = record['rect']; box=(tx,ty,tx+w,ty+h)
                variant = old['water_surface_variants'][y][x]
                tile=Image.new('RGBA',(24,24))
                tile.paste(surfaces[variant][phase],(0,0),masks.crop(box).getchannel('A'))
                tile=Image.alpha_composite(tile,banks.crop(box))
                image.alpha_composite(tile,(x*24,y*24))
        for cell in cells:
            x,y=cell['cell']
            image.alpha_composite(route_tiles[cell['route']][phase],(x*24,y*24))
        for character in characters:
            image.alpha_composite(Image.open(ROOT/character['image_from_repo_root']).convert('RGBA'),tuple(character['position']))
        native=image.convert('RGB')
        native.save(OUTPUT/f'review_scene_frame_{phase+1:02}.png')
        previews.append(enlarged(native,recipe['scene_scale']))
        closeups.append(enlarged(native.crop(recipe['closeup_rect']),recipe['closeup_scale']))
    previews[0].save(OUTPUT/'review_scene.png'); closeups[0].save(OUTPUT/'channels_closeup.png')
    save_loop(OUTPUT/'review_scene.gif',previews,recipe); save_loop(OUTPUT/'channels_closeup.gif',closeups,recipe)
    write_json(OUTPUT/'review_scene.json',{
        'status':recipe['status'],'purpose':'Irrigation art/flow review; not a canonical map or playable game',
        'grid_size':[width,height],'tile_size':[24,24],'grass_variants':grass_ids,
        'base_scene':'../stream/review_scene.json','channels':cells,'characters':characters,
        'shared_phase':True,'loop':True,'frames':[{'image':f'review_scene_frame_{i+1:02}.png','duration_ms':200} for i in range(6)],
        'review':{'gif':'review_scene.gif','image':'review_scene.png','scale':recipe['scene_scale'],
                  'closeup_gif':'channels_closeup.gif','closeup_rect':recipe['closeup_rect'],'closeup_scale':recipe['closeup_scale']}})


def build():
    recipe=read_json(SOURCE/'recipe.json')
    stream_pack=(SOURCE/recipe['stream_pack']).resolve(); ground_pack=(SOURCE/recipe['ground_pack']).resolve()
    palette=read_json(stream_pack/'palette.json')['materials']
    OUTPUT.mkdir(parents=True,exist_ok=True)
    (OUTPUT/'frames').mkdir(exist_ok=True)
    earth,drop=extract_parts(recipe,palette)
    shape_dir=SOURCE/'shapes'; shape_dir.mkdir(exist_ok=True)
    bank_atlas,mask_atlas=Image.new('RGBA',(96,96)),Image.new('RGBA',(96,96))
    layers={}
    for mask in range(16):
        bank,water=core_layers(mask,palette,earth); layers[mask]=bank,water
        bank.save(shape_dir/f'shape_{mask:02}_bank.png'); water.save(shape_dir/f'shape_{mask:02}_water.png')
        position=(mask%4*24,mask//4*24); bank_atlas.paste(bank,position); mask_atlas.paste(water,position)
    bank_atlas.save(OUTPUT/'channel_banks.png'); mask_atlas.save(OUTPUT/'channel_masks.png')
    records=routes(); tiles={}; rows=5
    combined=Image.new('RGBA',(192,rows*24*6)); atlases=[]
    for index,record in enumerate(records):
        record.update(index=index,rect=[index%8*24,index//8*24,24,24])
        if record['kind']=='channel': bank,mask=layers[record['ports']]
        else:
            bank,mask=special_layers(record['kind'],record['direction'],palette)
            bank.save(shape_dir/f"{record['id']}_bank.png"); mask.save(shape_dir/f"{record['id']}_water.png")
        prefix=f"shape_{record['ports']:02}" if record['kind']=='channel' else record['id']
        record['bank']=f'../../../source/terrain/eldenmere/irrigation/shapes/{prefix}_bank.png'
        record['water_mask']=f'../../../source/terrain/eldenmere/irrigation/shapes/{prefix}_water.png'
        tiles[record['id']]=[core_frame(record,bank,mask,p,recipe,palette) if record['kind']=='channel'
                             else special_frame(record,p,recipe,palette,drop) for p in range(6)]
    for phase in range(6):
        atlas=Image.new('RGBA',(192,120))
        for record in records: atlas.paste(tiles[record['id']][phase],tuple(record['rect'][:2]))
        atlas.save(OUTPUT/f'frames/frame_{phase+1:02}.png'); combined.paste(atlas,(0,phase*120)); atlases.append(atlas)
    combined.save(OUTPUT/'irrigation.png')
    write_json(OUTPUT/'palette.json',{'status':recipe['status'],'materials':palette})
    write_json(OUTPUT/'tileset.json',{
        'id':recipe['id'],'status':recipe['status'],'tile_size':[24,24],'route_count':40,'port_bits':PORTS,'port_vectors':VECTORS,
        'input_rule':'One input per directed module; junctions split to the other connected ports',
        'image':'irrigation.png','columns':8,'rows_per_phase':5,'spacing':0,'margin':0,'routes':records,
        'frames':[{'image':f'frames/frame_{i+1:02}.png','sheet_rect':[0,i*120,192,120],'duration_ms':200} for i in range(6)],
        'loop':True,'cycle_duration_ms':1200,'flow_step_pixels':2,'flow_period_pixels':12,'water_width_pixels':8,'earth_width_pixels':2,
        'bank_atlas':'channel_banks.png','water_mask_atlas':'channel_masks.png',
        'recipe':'../../../source/terrain/eldenmere/irrigation/recipe.json','palette':'palette.json',
        'review':{'scene':'review_scene.gif','closeup':'channels_closeup.gif','modules':'modules_review.gif'}})
    grass=Image.open(ground_pack/'grass_00.png').convert('RGBA'); boards=[]
    for phase in range(6):
        board=Image.new('RGB',(1344,1028),'#e8edf2'); draw=ImageDraw.Draw(board); draw.fontmode='1'
        draw.text((16,12),f"Eldenmere irrigation / 32 directed channels + 4 inlets + 4 outlets / {recipe['status']}",fill='#243529',font_size=22)
        for record in records:
            x,y=record['index']%8*168+12,record['index']//8*196+48
            board.paste(enlarged(Image.alpha_composite(grass,tiles[record['id']][phase]).convert('RGB'),6),(x,y))
            label=(f"{record['ports']:02} {record['input']} -> {''.join(record['outputs']) or 'cap'}" if record['kind']=='channel' else record['id'])
            draw.text((x,y+150),label,fill='#243529',font_size=16)
        boards.append(board)
    boards[0].save(OUTPUT/'modules_review.png'); save_loop(OUTPUT/'modules_review.gif',boards,recipe)
    build_scene(recipe,stream_pack,ground_pack,tiles,records)
    print('Built irrigation: 32 directed channels, 4 stream inlets, 4 trickling outlets and a six-phase review scene')


if __name__=='__main__':
    build()
