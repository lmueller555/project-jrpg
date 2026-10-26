"""Build a small hand-lifted sluice, state water art and a labeled scene demo."""

from copy import deepcopy
from pathlib import Path

from PIL import Image, ImageDraw

from build_eldenmere_stream import read_json, write_json, rgba, enlarged, save_loop

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'assets/source/terrain/eldenmere/gate'
OUTPUT=ROOT/'assets/terrain/eldenmere/gate'
TERRACE=OUTPUT.parent/'terraces'
CHANNELS=OUTPUT.parent/'irrigation'
GROUND=OUTPUT.parent/'grass_dirt'
LABELS={
    'idle_open':'OPEN / water restored', 'idle_closed':'CLOSED / no through-flow',
    'idle_jammed':'JAMMED / restricted trickle', 'opening':'OPENING / lifting gate',
    'closing':'CLOSING / lowering gate', 'repair':'REPAIR / reseating pin',
    'jamming':'JAMMING / pin slips',
}


def extract_parts(recipe,palette):
    source=Image.open(SOURCE/recipe['source']).convert('RGB')
    parts={}; directory=SOURCE/'parts'; directory.mkdir(exist_ok=True)
    for name,size,ramp in [('post',(4,23),'wood'),('panel',(10,9),'wood'),
                            ('beam',(16,3),'wood'),('stone',(6,7),'stone')]:
        sample=source.crop(recipe[f'{name}_crop']).resize(size,Image.Resampling.NEAREST)
        colors=[rgba(c) for c in palette[ramp].values()]; image=Image.new('RGBA',size)
        for y in range(size[1]):
            for x in range(size[0]):
                c=sample.getpixel((x,y))
                image.putpixel((x,y),min(colors,key=lambda p:sum((a-b)**2 for a,b in zip(c,p))))
        image.save(directory/f'{name}.png'); parts[name]=image
    return parts


def fixed_structure(parts,palette):
    image=Image.new('RGBA',(24,36)); d=ImageDraw.Draw(image)
    for x in (2,16): image.alpha_composite(parts['stone'],(x,28))
    for x in (4,16):
        image.alpha_composite(parts['post'],(x,5))
        d.line((x,5,x+3,5),fill=palette['wood']['worn'])
        d.rectangle((x,17,x+3,18),fill=palette['iron']['shadow'])
        d.line((x,17,x+2,17),fill=palette['iron']['base'])
        d.point((x+1,18),fill=palette['iron']['light'])
    image.alpha_composite(parts['beam'],(4,6))
    d.line((5,6,18,6),fill=palette['wood']['worn'])
    image.save(SOURCE/'parts/fixed_structure.png')
    return image


def poses(recipe):
    lifts=recipe['lift_pixels']; result={}
    for animation in LABELS:
        frames=[]
        for phase in range(6):
            if animation=='idle_open': lift,jam=11,0
            elif animation=='idle_closed': lift,jam=0,0
            elif animation=='idle_jammed': lift,jam=0,3
            elif animation=='opening': lift,jam=lifts[phase],0
            elif animation=='closing': lift,jam=lifts[5-phase],0
            elif animation=='repair': lift,jam=0,[3,3,2,1,0,0][phase]
            else: lift,jam=0,[0,0,1,2,3,3][phase]
            flow=lift/11 if lift else (0.15 if jam else 0)
            frames.append({'phase':phase,'lift':lift,'jam':jam,'flow':flow})
        result[animation]=frames
    return result


def channel_assets():
    meta=read_json(CHANNELS/'tileset.json')
    records={r['id']:r for r in meta['routes']}
    atlases=[Image.open(CHANNELS/f['image']).convert('RGBA') for f in meta['frames']]
    tiles={}; masks={}
    for name,r in records.items():
        x,y,w,h=r['rect']; tiles[name]=[a.crop((x,y,x+w,y+h)) for a in atlases]
        masks[name]=Image.open(CHANNELS/r['water_mask']).convert('RGBA')
    return records,tiles,masks


def thin_path(record,x,y):
    if record['kind']=='outlet':
        return x in (11,12) and y<19 or ((x-11.5)/2)**2+((y-20.5)/1.2)**2<=1
    ports=[record['input'],*record['outputs']]
    return bool('N' in ports and x in (11,12) and y<=12
                or 'S' in ports and x in (11,12) and y>=11
                or 'W' in ports and y in (11,12) and x<=12
                or 'E' in ports and y in (11,12) and x>=11)


def channel_response(tile,mask,record,mode,phase,palette):
    image=tile.copy(); water=palette['water']
    water_colors={rgba(c) for c in water.values()}
    for y in range(24):
        for x in range(24):
            pixel=image.getpixel((x,y))
            if not mask.getpixel((x,y))[3] and pixel not in water_colors: continue
            puddle=record['kind']=='outlet' and ((x-11.5)/2)**2+((y-20.5)/1.2)**2<=1
            dry=palette['dirt']['base' if (x+3*y)%11==0 else 'shadow']
            image.putpixel((x,y),rgba(water['deep'] if puddle else dry))
            if mode=='trickle' and thin_path(record,x,y):
                color=pixel if pixel in water_colors else rgba(water['flow' if (x+y-phase*2)%12<2 else 'base'])
                image.putpixel((x,y),color)
    return image


def spillway_response(frame,mode,phase,palette):
    structure=Image.open(TERRACE/'../../../source/terrain/eldenmere/terraces/parts/spillway_structure.png').convert('RGBA')
    mask=Image.open(TERRACE/'../../../source/terrain/eldenmere/terraces/parts/spillway_water_mask.png').convert('RGBA')
    wall=Image.open(TERRACE/'tiles/wall_front_01.png').convert('RGBA')
    image=structure.copy()
    for y in range(48):
        for x in range(24):
            if not mask.getpixel((x,y))[3]: continue
            basin=((x-11.5)/7)**2+((y-35)/3.5)**2<=1
            if y<6 or y>=40: color=rgba(palette['dirt']['shadow'])
            elif y<24: color=wall.getpixel((x,y))
            else: color=(0,0,0,0)
            if basin: color=rgba(palette['water']['deep'])
            if mode=='trickle' and x in (11,12):
                if y<6 or y>=40 or y<=33 and (y-phase*2)%12<5:
                    color=frame.getpixel((x,y))
            if mode=='trickle' and basin and y==35 and abs(x-11.5)<=phase%3+1:
                color=rgba(palette['water']['flow'])
            image.putpixel((x,y),color)
    return image


def gate_frame(pose,parts,structure,channel_tiles,palette,recipe,pin_side='right',pin_y_override=None):
    phase=pose['phase']; image=Image.new('RGBA',(24,36))
    tile=channel_tiles[phase].copy(); water=palette['water']
    for y in range(24):
        for x in range(8,16):
            if y<16:
                if pose['flow']<0.7:
                    color=water['shallow'] if x in (8,15) else water['base']
                    if y==5+phase//2 and 10<=x<=13: color=water['reflection']
                    tile.putpixel((x,y),rgba(color))
            else:
                wet=pose['flow']>0.7 or pose['flow']>0 and x in (10,11)
                if not wet:
                    tile.putpixel((x,y),rgba(palette['dirt']['shadow']))
    image.alpha_composite(tile,(0,12))
    top=recipe['closed_panel_y']-pose['lift']
    panel=parts['panel']; moving=Image.new('RGBA',image.size)
    for x in range(panel.width):
        skew=round(pose['jam']*(panel.width-1-x)/(panel.width-1))
        for y in range(panel.height): moving.putpixel((7+x,top+y-skew),panel.getpixel((x,y)))
    d=ImageDraw.Draw(moving)
    for y in (3,6):
        for x in range(10):
            skew=round(pose['jam']*(9-x)/9)
            d.point((7+x,top+y-skew),fill=palette['wood']['shadow'])
    d.line((8,top-pose['jam'],15,top),fill=palette['wood']['worn'])
    d.rectangle((11,top-7,12,top),fill=palette['iron']['shadow'])
    d.line((11,top-7,11,top-1),fill=palette['iron']['base'])
    d.line((9,top-7,14,top-7),fill=palette['iron']['base'])
    image.alpha_composite(moving); image.alpha_composite(structure)
    d=ImageDraw.Draw(image)
    pin_y=(15 if pose['lift']>=9 else 23) if pin_y_override is None else pin_y_override
    a,b=(19,21) if pin_side=='right' else (4,2)
    d.line((a,pin_y,b,pin_y+(1 if pose['jam'] else 0)),fill=palette['iron']['base'])
    d.point((b,pin_y+(2 if pose['jam'] else 0)),fill=palette['iron']['light'])
    return image


def timeline(recipe,all_poses):
    result=[]
    for segment in recipe['scene_sequence']:
        for i in range(segment['ticks']):
            name=segment['animation']; pose=deepcopy(all_poses[name][i%6])
            result.append({'animation':name,'animation_frame':i%6,'pose':pose})
    return result


def downstream_spec(step=2):
    result=[
        {'cell':[11,19],'route':'channel_03_from_n','delay':2},
        {'cell':[12,19],'route':'channel_10_from_w','delay':4},
        {'cell':[13,19],'route':'channel_12_from_w','delay':6},
        {'cell':[13,20],'prefab':'spillway','delay':8},
        {'cell':[13,22],'route':'channel_09_from_n','delay':12},
        {'cell':[12,22],'route':'channel_10_from_e','delay':14},
        {'cell':[11,22],'route':'channel_06_from_e','delay':16},
        {'cell':[11,23],'route':'outlet_s','delay':18},
    ]
    for cell in result:
        cell['delay']=cell['delay']//2*step
        cell['size']=[24,48] if 'prefab' in cell else [24,24]
    return result


def response_mode(value):
    return 'full' if value>0.7 else 'trickle' if value>0 else 'dry'


def caption(image,label,height):
    result=Image.new('RGB',(image.width,image.height+height),'#e8edf2'); result.paste(image,(0,height))
    d=ImageDraw.Draw(result); d.fontmode='1'; d.text((12,10),label,fill='#243529',font_size=20)
    return result


def indexed(image):
    # Reduce memory during the long scene loop; every native color must survive exactly.
    assert len(image.getcolors(image.width*image.height))<=256
    return image.convert('P',palette=Image.Palette.ADAPTIVE,colors=256)


def build():
    recipe=read_json(SOURCE/'recipe.json')
    palette=deepcopy(read_json(TERRACE/'palette.json')['materials']); palette.update(recipe['palette'])
    OUTPUT.mkdir(exist_ok=True)
    for name in ('animations','downstream','scene_frames'): (OUTPUT/name).mkdir(exist_ok=True)
    parts=extract_parts(recipe,palette); structure=fixed_structure(parts,palette)
    records,channel_tiles,masks=channel_assets(); all_poses=poses(recipe); frames={}; animations=[]
    sheet=Image.new('RGBA',(144,252))
    for row,(animation,animation_poses) in enumerate(all_poses.items()):
        directory=OUTPUT/'animations'/animation; directory.mkdir(exist_ok=True); frames[animation]=[]; meta=[]
        for i,pose in enumerate(animation_poses):
            frame=gate_frame(pose,parts,structure,channel_tiles['channel_05_from_n'],palette,recipe)
            path=f'animations/{animation}/frame_{i+1:02}.png'; frame.save(OUTPUT/path)
            sheet.paste(frame,(i*24,row*36)); frames[animation].append(frame)
            meta.append({'image':path,'sheet_rect':[i*24,row*36,24,36],'duration_ms':200,**pose})
        animations.append({'id':animation,'loop':animation.startswith('idle_'),'frames':meta})
    sheet.save(OUTPUT/'gate.png')
    responses={}; response_meta=[]; names=list(dict.fromkeys(p['route'] for p in downstream_spec() if 'route' in p))
    spillways=[Image.open(TERRACE/f'spillway/frame_{i+1:02}.png').convert('RGBA') for i in range(6)]
    for name in names:
        responses[name]={mode:[channel_response(channel_tiles[name][p],masks[name],records[name],mode,p,palette) for p in range(6)] for mode in ('dry','trickle')}
    responses['spillway']={mode:[spillway_response(spillways[p],mode,p,palette) for p in range(6)] for mode in ('dry','trickle')}
    for index,name in enumerate([*names,'spillway']):
        for half in range(2 if name=='spillway' else 1):
            n=len(response_meta); response_meta.append({'id':name,'half':half,'rect':[n%3*24,n//3*24,24,24]})
    for mode in ('dry','trickle'):
        for phase in range(6 if mode=='trickle' else 1):
            atlas=Image.new('RGBA',(72,72))
            for record in response_meta:
                tile=responses[record['id']][mode][phase]
                if record['id']=='spillway': tile=tile.crop((0,record['half']*24,24,(record['half']+1)*24))
                atlas.paste(tile,tuple(record['rect'][:2]))
            atlas.save(OUTPUT/f'downstream/{mode}_{phase+1:02}.png')
    clock=timeline(recipe,all_poses); scene=read_json(TERRACE/'review_scene.json')
    downstream=downstream_spec(recipe['water_delay_ticks_per_cell'])
    grass=[Image.open(GROUND/f'grass_{i:02}.png').convert('RGBA') for i in range(4)]
    full=[]; closeups=[]; scene_meta=[]
    for tick,event in enumerate(clock):
        phase=tick%6; image=Image.open(TERRACE/f'review_scene_frame_{phase+1:02}.png').convert('RGBA')
        modes=[]
        for cell in downstream:
            # Delayed signals provide a readable fill/drain front rather than instant remote changes.
            value=clock[(tick-cell['delay'])%len(clock)]['pose']['flow']; mode=response_mode(value)
            x,y=cell['cell']; size=(24,48) if 'prefab' in cell else (24,24)
            replacement=spillways[phase] if 'prefab' in cell else channel_tiles[cell['route']][phase]
            if mode!='full': replacement=responses[cell.get('route','spillway')][mode][phase if mode=='trickle' else 0]
            for dy in range(size[1]//24): image.paste(grass[scene['grass_variants'][y+dy][x]],(x*24,(y+dy)*24))
            image.alpha_composite(replacement,(x*24,y*24)); modes.append(mode)
        x,y=recipe['gate_cell']; image.paste(grass[scene['grass_variants'][y][x]],(x*24,y*24))
        gate=frames[event['animation']][event['animation_frame']]
        image.alpha_composite(gate,tuple(recipe['gate_position']))
        native=image.convert('RGB'); path=f'scene_frames/frame_{tick+1:03}.png'; native.save(OUTPUT/path)
        label=LABELS[event['animation']]
        full.append(indexed(caption(enlarged(native,recipe['scene_scale']),label,recipe['caption_height'])))
        closeups.append(indexed(caption(enlarged(native.crop(recipe['closeup_rect']),recipe['closeup_scale']),label,recipe['caption_height'])))
        scene_meta.append({'image':path,'animation':event['animation'],'animation_frame':event['animation_frame'],
                           'water_phase':phase,'downstream_modes':modes,'duration_ms':200})
    full[0].convert('RGB').save(OUTPUT/'review_scene.png'); closeups[0].convert('RGB').save(OUTPUT/'gate_closeup.png')
    save_loop(OUTPUT/'review_scene.gif',full,recipe); save_loop(OUTPUT/'gate_closeup.gif',closeups,recipe)
    boards=[]
    for phase in range(6):
        board=Image.new('RGB',(720,680),'#e8edf2'); d=ImageDraw.Draw(board); d.fontmode='1'
        d.text((16,12),f"Eldenmere irrigation gate / {recipe['status']}",fill='#243529',font_size=22)
        for col,name in enumerate(('idle_open','idle_closed','idle_jammed')):
            native=Image.new('RGBA',(24,72))
            for y in range(3): native.paste(grass[0],(0,y*24))
            native.alpha_composite(channel_tiles['channel_05_from_n'][phase],(0,0))
            mode={'idle_open':'full','idle_closed':'dry','idle_jammed':'trickle'}[name]
            below=channel_tiles['channel_05_from_n'][phase]
            if mode!='full': below=channel_response(below,masks['channel_05_from_n'],records['channel_05_from_n'],mode,phase,palette)
            native.alpha_composite(below,(0,48)); native.alpha_composite(frames[name][phase],(0,12))
            board.paste(enlarged(native.convert('RGB'),8),(col*240+24,64))
            d.text((col*240+24,644),name.removeprefix('idle_').upper(),fill='#243529',font_size=20)
        boards.append(board)
    boards[0].save(OUTPUT/'states_review.png'); save_loop(OUTPUT/'states_review.gif',boards,recipe)
    write_json(OUTPUT/'palette.json',{'status':recipe['status'],'materials':palette})
    write_json(OUTPUT/'sprite.json',{'id':recipe['id'],'status':recipe['status'],'image':'gate.png','sprite_size':[24,36],
        'ground_rect':recipe['ground_rect'],'anchor':[12,34],'input':'N','output':'S','water_width_pixels':8,
        'mechanism':'hand-lifted sliding board and locking pin','animations':animations,
        'recipe':'../../../source/terrain/eldenmere/gate/recipe.json',
        'fixed_structure':'../../../source/terrain/eldenmere/gate/parts/fixed_structure.png',
        'downstream_responses':{'tiles':response_meta,'dry':'downstream/dry_01.png',
            'trickle':[f'downstream/trickle_{i+1:02}.png' for i in range(6)],'full':'../irrigation/tileset.json'},
        'review':{'scene':'review_scene.gif','closeup':'gate_closeup.gif','states':'states_review.gif'}})
    write_json(OUTPUT/'review_scene.json',{'status':recipe['status'],'base_scene':'../terraces/review_scene.json',
        'purpose':'Labeled gate-state art demonstration; illustrative layout, not gameplay or a fluid simulation',
        'gate_position':recipe['gate_position'],'gate_cell':recipe['gate_cell'],'ground_elevation_pixels':24,
        'downstream':downstream,'elevation_note':'Gate and upper channels are on the same level; the existing southern spillway is the only drop. Earlier terrace layout is retained without alteration.',
        'frames':scene_meta,'loop':True,'cycle_duration_ms':len(clock)*200,
        'review':{'scene_scale':3,'caption_height':48,'closeup_rect':recipe['closeup_rect'],'closeup_scale':5}})
    print(f'Built 7 gate animations, 42 native frames and a {len(clock)*200/1000:g}s synchronized scene demo')


if __name__=='__main__':
    build()
