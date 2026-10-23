"""Export a source-derived modular cottage, triggered doors and ambient smoke."""
from copy import deepcopy
from pathlib import Path
from PIL import Image, ImageDraw
from build_eldenmere_stream import read_json, write_json, enlarged, save_loop, rgba
from build_eldenmere_watermill import quantized

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'assets/source/terrain/eldenmere/cottage'
OUTPUT=ROOT/'assets/terrain/eldenmere/cottage'
MILL=OUTPUT.parent/'watermill'
GROUND=OUTPUT.parent/'grass_dirt'


def extract(recipe,palette):
    source=Image.open(SOURCE/recipe['source']).convert('RGB')
    sample=source.crop(recipe['source_crop']).resize(tuple(recipe['native_size']),Image.Resampling.NEAREST)
    colors=[c for name,ramp in palette.items() if name!='smoke' for c in ramp.values()]
    native=quantized(sample,colors)
    for y in range(native.height):
        for x in range(native.width):
            r,g,b=sample.getpixel((x,y))
            if r>180 and g<80 and b>160: native.putpixel((x,y),(0,0,0,0))
    native.save(SOURCE/'parts/building_native.png')
    remaining=native.copy(); parts={}
    for record in recipe['components']:
        rect=record['rect']; part=remaining.crop(rect); parts[record['id']]=part
        part.save(SOURCE/f"parts/{record['id']}.png")
        remaining.paste((0,0,0,0),tuple(rect))
    assert not remaining.getbbox(), 'Every native pixel must belong to a documented component'
    return native,parts


def structure(recipe,palette,parts):
    image=Image.new('RGBA',tuple(recipe['prefab_size'])); ox,oy=recipe['building_offset']
    for record in recipe['components']:
        if record['id'] in ('door_leaf','lantern'): continue
        x,y,_,_=record['rect']; image.alpha_composite(parts[record['id']],(x+ox,y+oy))
    # An opaque dark interior sits behind a door leaf at every opening width.
    x,y,r,b=recipe['door_leaf_rect']
    ImageDraw.Draw(image).rectangle((x+ox,y+oy,r+ox-1,b+oy-1),fill=palette['glass']['dark'])
    return image


def door_frames(recipe,palette,parts):
    leaf=parts['door_leaf']; x,y,r,b=recipe['door_leaf_rect']; ox,oy=recipe['building_offset']; frames=[]
    for index,width in enumerate(recipe['door_widths']):
        layer=Image.new('RGBA',tuple(recipe['prefab_size']))
        layer.alpha_composite(leaf.resize((width,b-y),Image.Resampling.NEAREST),(x+ox,y+oy))
        if index: ImageDraw.Draw(layer).line((x+ox+width-1,y+oy,x+ox+width-1,b+oy-1),fill=palette['wood']['shadow'])
        frames.append(layer)
    return frames


def lantern_frame(phase,recipe,parts):
    layer=Image.new('RGBA',tuple(recipe['prefab_size'])); ox,oy=recipe['building_offset']
    record=next(c for c in recipe['components'] if c['id']=='lantern'); x,y,_,_=record['rect']
    source=parts['lantern']; swing=(0,1,1,0,-1,-1)[phase%6]
    # Separate the hanging silhouette from its source plaster/post backdrop.
    # Moving an entire rectangular crop would also wobble the wall behind it.
    backing=source.copy(); hanging=Image.new('RGBA',source.size)
    rows=((3,6),(2,6),(1,7),(1,7),(1,7),(1,7),(1,7),(1,7),(2,6))
    for yy,(left,right) in enumerate(rows,start=5):
        for xx in range(left,right):
            hanging.putpixel((xx,yy),source.getpixel((xx,yy)))
            backing.putpixel((xx,yy),source.getpixel((0 if xx<5 else 7,yy)))
    layer.alpha_composite(backing,(x+ox,y+oy))
    layer.alpha_composite(hanging,(x+ox+swing,y+oy))
    return layer


def smoke_frame(phase,recipe,palette):
    layer=Image.new('RGBA',tuple(recipe['prefab_size'])); d=ImageDraw.Draw(layer)
    origin=recipe['smoke_origin']; count=recipe['smoke_frame_count']; particles=[]
    for offset in (0,6,12):
        age=(phase+offset)%count
        # Three staggered wisps: rise continuously, drift east, then thin into isolated clusters.
        x=origin[0]+age//2; y=origin[1]-age*2
        particles.append({'age':age,'center':[x,y]})
        if age>=17: continue
        size=1 if age<2 else 2 if age<7 else 3
        color=palette['smoke']['shadow' if age<4 else 'base' if age<12 else 'light']
        if age<13:
            d.rectangle((x-size+1,y-1,x+size-1,y+1),fill=color)
            d.line((x-size,y,x+size,y),fill=color)
            if age>3: d.point((x-1,y-2),fill=palette['smoke']['light'])
            # Distinct tiny contours keep staggered puffs from collapsing to a 1.2s repeat.
            if 3<=age<13 and offset==6: d.point((x+size,y+1),fill=color)
            if 3<=age<13 and offset==12: d.point((x-size,y-1),fill=color)
        else:
            d.line((x-2,y,x,y),fill=color); d.point((x+2,y-1),fill=color)
            if age<16: d.point((x,y+2),fill=color)
    return layer,particles


def door_index(tick):
    if tick<4 or tick>=15: return 0
    if tick<8: return tick-3
    if tick<11: return 4
    return 14-tick


def path_layer(recipe):
    meta=read_json(GROUND/'tileset.json'); tiles={t['mask']:Image.open(GROUND/t['image']).convert('RGBA') for t in meta['tiles']}
    layer=Image.new('RGBA',(720,624)); cells={tuple(p) for p in recipe['path_cells']}; joins=cells|{tuple(p) for p in recipe['path_join_cells']}
    offsets=((0,-1),(1,-1),(1,0),(1,1),(0,1),(-1,1),(-1,0),(-1,-1))
    for x,y in cells:
        raw=sum(1<<i for i,(dx,dy) in enumerate(offsets) if (x+dx,y+dy) in joins)
        mask=meta['tiles'][meta['lookup_256'][raw]]['mask']; layer.alpha_composite(tiles[mask],(x*24,y*24))
    return layer


def components_board(recipe,parts):
    board=Image.new('RGB',(1120,1064),'#e8edf2'); d=ImageDraw.Draw(board); d.fontmode='1'
    d.text((20,16),f"Eldenmere cottage / {recipe['status']} / parts at 4x / wide roof at 3x",fill='#243529',font_size=22)
    for index,record in enumerate(recipe['components']):
        col=index%4; row=index//4; x=20+col*276; y=62+row*248
        d.text((x,y),record['id'].replace('_',' '),fill='#243529',font_size=17)
        d.text((x,y+23),f"{parts[record['id']].width} x {parts[record['id']].height} px",fill='#53696e',font_size=14)
        part=enlarged(parts[record['id']],3 if record['id']=='roof_middle' else 4)
        board.paste(part,(x,y+44),part)
    board.save(OUTPUT/'components_review.png')


def reusable_inserts(native,parts,palette):
    """Retain clean source-material inserts for later width/decoration assemblies."""
    repeat=native.crop((48,8,72,53))
    repeat.save(OUTPUT/'parts/roof_repeat.png')
    panel=Image.new('RGBA',(24,43),palette['plaster']['base'])
    plaster=native.crop((14,57,18,81))
    for x in range(0,24,4): panel.alpha_composite(plaster,(x,3))
    panel.alpha_composite(native.crop((9,53,13,81)),(0,0))
    panel.alpha_composite(native.crop((24,81,48,96)),(0,28))
    panel.alpha_composite(native.crop((24,53,48,57)),(0,0))
    panel.save(OUTPUT/'parts/wall_blank.png')
    for name in ('window_left','window_right'):
        lit=parts[name].copy()
        # Exact glass replacements preserve muntins, shutters, flowers and alpha.
        glass={rgba(c) for c in palette['glass'].values()}
        for y in range(lit.height):
            for x in range(lit.width):
                if lit.getpixel((x,y)) in glass:
                    lit.putpixel((x,y),rgba(palette['lamplight']['base' if y<lit.height//2 else 'light']))
        lit.save(OUTPUT/f'parts/{name}_lit.png')


def build():
    recipe=read_json(SOURCE/'recipe.json'); palette=deepcopy(read_json(MILL/'palette.json')['materials']); palette.update(recipe['palette'])
    for directory in ('parts','doors','smoke','lantern','preview_frames','scene_frames'): (OUTPUT/directory).mkdir(parents=True,exist_ok=True)
    native,parts=extract(recipe,palette); reusable_inserts(native,parts,palette)
    base=structure(recipe,palette,parts); base.save(OUTPUT/'structure.png')
    component_meta=[]
    for c in recipe['components']:
        part=parts[c['id']]; part.save(OUTPUT/f"parts/{c['id']}.png")
        component_meta.append({**c,'image':f"parts/{c['id']}.png",'position':[c['rect'][0],c['rect'][1]+48]})
    doors=door_frames(recipe,palette,parts)
    for i,frame in enumerate(doors): frame.save(OUTPUT/f'doors/frame_{i+1:02}.png')
    closed=base.copy(); closed.alpha_composite(doors[0]); closed.alpha_composite(lantern_frame(0,recipe,parts)); closed.save(OUTPUT/'closed.png')
    opened=base.copy(); opened.alpha_composite(doors[-1]); opened.alpha_composite(lantern_frame(0,recipe,parts)); opened.save(OUTPUT/'open.png')
    previews=[]; scenes=[]; closeups=[]; records=[]; smoke_records=[]; paths=path_layer(recipe); paths.save(OUTPUT/'review_path.png')
    sheet=Image.new('RGBA',(600,144));
    for i,door in enumerate(doors):
        frame=base.copy(); frame.alpha_composite(door); frame.alpha_composite(lantern_frame(0,recipe,parts)); sheet.paste(frame,(i*120,0))
    sheet.save(OUTPUT/'door_sheet.png')
    for tick in range(recipe['smoke_frame_count']):
        smoke,particles=smoke_frame(tick,recipe,palette); smoke.save(OUTPUT/f'smoke/frame_{tick+1:02}.png')
        lantern=lantern_frame(tick,recipe,parts); lantern.save(OUTPUT/f'lantern/frame_{tick+1:02}.png')
        frame=base.copy(); frame.alpha_composite(doors[door_index(tick)]); frame.alpha_composite(lantern); frame.alpha_composite(smoke)
        frame.save(OUTPUT/f'preview_frames/frame_{tick+1:02}.png'); previews.append(frame)
        scene=Image.open(MILL/f'scene_running/frame_{tick%6+1:02}.png').convert('RGBA')
        scene.alpha_composite(paths); scene.alpha_composite(frame,tuple(recipe['scene_position'])); scene=scene.convert('RGB')
        scene.save(OUTPUT/f'scene_frames/frame_{tick+1:02}.png'); scenes.append(enlarged(scene,recipe['scene_scale']))
        closeups.append(enlarged(scene.crop(recipe['closeup_rect']),recipe['closeup_scale']))
        records.append({'image':f'scene_frames/frame_{tick+1:02}.png','water_phase':tick%6,'door_frame':door_index(tick),'smoke_frame':tick,'duration_ms':recipe['duration_ms']})
        smoke_records.append({'image':f'smoke/frame_{tick+1:02}.png','particles':particles,'duration_ms':recipe['duration_ms']})
    for name,frames in (('review_scene',scenes),('cottage_closeup',closeups)):
        frames[0].save(OUTPUT/f'{name}.png'); save_loop(OUTPUT/f'{name}.gif',frames,recipe)
    components_board(recipe,parts)
    write_json(OUTPUT/'palette.json',{'status':recipe['status'],'materials':palette})
    write_json(OUTPUT/'cottage.json',{'id':recipe['id'],'status':recipe['status'],'tile_size':[24,24],'prefab_size':recipe['prefab_size'],
        'ground_rect':recipe['ground_rect'],'structure':'structure.png','closed':'closed.png','open':'open.png','components':component_meta,
        'door':{'hinge':'west','position':[53,111],'size':[13,26],'opening':{'loop':False,'frames':[{'image':f'doors/frame_{i+1:02}.png','duration_ms':100} for i in range(5)]},
                'closing':{'loop':False,'frames':[{'image':f'doors/frame_{i+1:02}.png','duration_ms':100} for i in reversed(range(5))]},'hold_closed':0,'hold_open':4},
        'smoke':{'optional':True,'direction':'east','loop':True,'cycle_duration_ms':3600,'frames':smoke_records},
        'lantern':{'max_sway_pixels':1,'bracket_fixed':True,'frames':[f'lantern/frame_{i+1:02}.png' for i in range(18)]},
        'reusable_inserts':{'roof_repeat':'parts/roof_repeat.png','wall_blank':'parts/wall_blank.png',
                            'lit_windows':['parts/window_left_lit.png','parts/window_right_lit.png']},
        'animations_are_separate_layers':True,'recipe':'../../../source/terrain/eldenmere/cottage/recipe.json'})
    write_json(OUTPUT/'review_scene.json',{'status':recipe['status'],'purpose':'Cottage appearance and animation review; illustrative layout, not a game level',
        'base_scene':'../watermill/review_scene.json','position':recipe['scene_position'],'path_cells':recipe['path_cells'],'path_join_cells':recipe['path_join_cells'],
        'doorway_foot':recipe['doorway_foot'],'elevations':{'ground':recipe['ground_elevation_pixels'],'threshold':recipe['threshold_elevation_pixels']},
        'review_door_loops_only_for_demonstration':True,'frames':records,'loop':True,'cycle_duration_ms':3600,
        'review':{'scene_scale':recipe['scene_scale'],'closeup_rect':recipe['closeup_rect'],'closeup_scale':recipe['closeup_scale']}})
    print('Built draft cottage: 14 components, five triggered door poses, 18 smoke phases and unchanged mill scene with dry approach')

if __name__=='__main__': build()
