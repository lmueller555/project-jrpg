"""Build layered 24px bridge modules, still decking and six-phase lantern/water art."""

from copy import deepcopy
from pathlib import Path
from random import Random

from PIL import Image, ImageDraw

from build_eldenmere_stream import read_json, write_json, rgba, enlarged, save_loop

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'assets/source/terrain/eldenmere/bridge'
OUTPUT=ROOT/'assets/terrain/eldenmere/bridge'
GATE=OUTPUT.parent/'gate'
STREAM=OUTPUT.parent/'stream'
GROUND=OUTPUT.parent/'grass_dirt'
TERRACE=OUTPUT.parent/'terraces'


def sample_part(source,rect,size,colors):
    sample=source.crop(rect).convert('RGB').resize(size,Image.Resampling.NEAREST)
    ramp=[rgba(c) for c in colors]; image=Image.new('RGBA',size)
    for y in range(size[1]):
        for x in range(size[0]):
            color=sample.getpixel((x,y))
            image.putpixel((x,y),min(ramp,key=lambda p:sum((a-b)**2 for a,b in zip(color,p))))
    return image


def extract_parts(recipe,palette):
    reference=Image.open(SOURCE/recipe['source']).convert('RGB'); parts={}
    directory=SOURCE/'parts'; directory.mkdir(exist_ok=True)
    for name,size,ramp in [('planks',(24,48),'wood'),('rail',(24,4),'wood'),
                            ('post',(4,14),'wood'),('stone',(24,14),'stone')]:
        parts[name]=sample_part(reference,recipe[f'{name}_crop'],size,palette[ramp].values())
        if name=='rail':
            for y,key in enumerate(('worn','light','base','shadow')):
                for x in (0,23): parts[name].putpixel((x,y),rgba(palette['wood'][key]))
        parts[name].save(directory/f'{name}.png')
    parts['paper']=sample_part(reference,recipe['paper_crop'],(3,4),
                               [palette['stone']['highlight'],palette['dirt']['light']])
    parts['paper'].save(directory/'paper.png')
    return parts


def add_post(image,parts,palette,top):
    image.alpha_composite(parts['post'],(10,top)); d=ImageDraw.Draw(image)
    d.line((10,top,13,top),fill=palette['wood']['worn'])
    d.rectangle((10,top+10,13,top+11),fill=palette['iron']['shadow'])
    d.line((10,top+10,12,top+10),fill=palette['iron']['base'])
    d.point((11,top+11),fill=palette['iron']['light'])


def module_layers(kind,parts,palette):
    base=Image.new('RGBA',(24,72)); front=Image.new('RGBA',(24,72))
    plank=parts['planks'].copy()
    if kind in ('middle_b','east'): plank=plank.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    d=ImageDraw.Draw(plank)
    # Shared join profiles let straight middle variants repeat in any order.
    for y in range(48):
        for x in (0,23): plank.putpixel((x,y),rgba(palette['wood']['base']))
    d.line((0,0,23,0),fill=palette['wood']['shadow'])
    d.line((0,47,23,47),fill=palette['wood']['shadow'])
    if kind in ('west','east'):
        base.alpha_composite(parts['stone'],(0,53))
        base.alpha_composite(parts['stone'].crop((0,0,24,3)),(0,9))
    base.alpha_composite(plank,(0,12))
    if kind in ('west','east'):
        # A flush stone threshold meets the approach without implying a stair or slope.
        x=0 if kind=='west' else 20
        for y in range(12,60):
            for xx in range(x,x+4):
                c=parts['stone'].getpixel((xx,y%14))
                base.putpixel((xx,y),c)
    else:
        d=ImageDraw.Draw(base)
        d.rectangle((11,60,13,65),fill=palette['wood']['shadow'])
        d.line((11,60,11,64),fill=palette['wood']['base'])
    for layer,top in ((base,0),(front,48)):
        layer.alpha_composite(parts['rail'],(0,top+3))
        layer.alpha_composite(parts['rail'].crop((0,0,24,3)),(0,top+9))
        add_post(layer,parts,palette,top)
    return base,front


def lantern_layer(kind,phase,parts,palette,recipe):
    image=Image.new('RGBA',(24,72))
    if kind not in ('west','east'): return image
    mirrored=kind=='east'; offset=recipe['lantern_east_phase_offset'] if mirrored else 0
    dx=recipe['lantern_sway_pixels'][(phase+offset)%6]
    pivot=6 if mirrored else 18
    d=ImageDraw.Draw(image)
    d.line((12,1,pivot,1),fill=palette['iron']['shadow'])
    d.line((12,3,pivot-1 if mirrored else pivot+1,1),fill=palette['iron']['base'])
    d.line((pivot,2,pivot+dx,4),fill=palette['iron']['shadow'])
    left=pivot+dx-2
    d.rectangle((left,5,left+4,10),fill=palette['iron']['shadow'])
    d.line((left+1,4,left+3,4),fill=palette['iron']['base'])
    image.alpha_composite(parts['paper'],(left+1,6))
    d.line((left+1,11,left+3,11),fill=palette['iron']['base'])
    return image


def water_layers(kind,phase,palette):
    shadow=Image.new('RGBA',(24,72)); wake=Image.new('RGBA',(24,72))
    if kind not in ('middle_a','middle_b'): return shadow,wake
    d=ImageDraw.Draw(shadow); d.rectangle((0,60,23,64),fill=palette['water']['deep'])
    d=ImageDraw.Draw(wake); offset=0 if kind=='middle_a' else 2
    progress=(phase+offset)%6; radius=2+progress//2; yy=66+progress%2
    d.arc((12-radius,yy-1,12+radius,yy+1),0,180,
          fill=palette['water']['flow' if progress in (0,5) else 'reflection'])
    return shadow,wake


def assemble(modules,names,layer,phase=None):
    image=Image.new('RGBA',(len(names)*24,72))
    for i,name in enumerate(names):
        part=modules[name][layer] if phase is None else modules[name][layer][phase]
        image.alpha_composite(part,(i*24,0))
    return image


def underlying_ground(cell,grass_ids,ground_meta,stream_scene):
    x,y=cell; tile=Image.open(GROUND/ground_meta['grass']['images'][grass_ids[y][x]]).convert('RGBA')
    mask=stream_scene['dirt_masks'][y][x]; fill=stream_scene['dirt_fill_variants'][y][x]
    if mask is not None:
        path=ground_meta['dirt_interiors']['images'][fill] if fill is not None else next(t['image'] for t in ground_meta['tiles'] if t['mask']==mask)
        tile.alpha_composite(Image.open(GROUND/path).convert('RGBA'))
    assert stream_scene['water_masks'][y][x] is None
    return tile


def clip_to_water(overlay,background,position,palette):
    image=overlay.copy(); colors={rgba(c) for c in palette['water'].values()}
    ox,oy=position
    for y in range(image.height):
        for x in range(image.width):
            if image.getpixel((x,y))[3] and background.getpixel((ox+x,oy+y)) not in colors:
                image.putpixel((x,y),(0,0,0,0))
    return image


def build_scene(recipe,palette,modules):
    old=read_json(TERRACE/'review_scene.json'); stream=read_json(STREAM/'review_scene.json')
    gm=read_json(GROUND/'tileset.json'); rng=Random(341)
    width,height=recipe['scene_size']; grass_ids=deepcopy(old['grass_variants'])
    for row in grass_ids: row.extend(rng.choices(range(4),weights=(5,3,2,1),k=width-len(row)))
    grass=[Image.open(GROUND/p).convert('RGBA') for p in gm['grass']['images']]
    dirt={t['mask']:Image.open(GROUND/t['image']).convert('RGBA') for t in gm['tiles']}
    cells={tuple(p) for p in recipe['east_dirt_cells']}; joins=cells|{tuple(p) for p in recipe['dirt_join_cells']}
    offsets=[(0,-1),(1,-1),(1,0),(1,1),(0,1),(-1,1),(-1,0),(-1,-1)]
    base=assemble(modules,recipe['assembly'],'base'); front=assemble(modules,recipe['assembly'],'foreground')
    sprite=Image.open(ROOT/'assets/characters/caelan/idle_right.png').convert('RGBA')
    previews=[]; closeups=[]; frames=[]
    for phase in range(6):
        background=Image.new('RGBA',(width*24,height*24))
        for y,row in enumerate(grass_ids):
            for x,variant in enumerate(row): background.paste(grass[variant],(x*24,y*24))
        source_frame=recipe['base_gate_scene_frames'][phase]
        old_frame=Image.open(GATE/f'scene_frames/frame_{source_frame:03}.png').convert('RGBA')
        background.paste(old_frame,(0,0))
        for cell in recipe['restored_cells']:
            background.paste(underlying_ground(cell,grass_ids,gm,stream),(cell[0]*24,cell[1]*24))
        for x,y in cells:
            raw=sum(1<<i for i,(dx,dy) in enumerate(offsets) if (x+dx,y+dy) in joins)
            mask=gm['tiles'][gm['lookup_256'][raw]]['mask']
            background.alpha_composite(dirt[mask],(x*24,y*24))
        image=background.copy(); position=tuple(recipe['scene_position'])
        for layer in ('shadow','wake'):
            overlay=assemble(modules,recipe['assembly'],layer,phase)
            image.alpha_composite(clip_to_water(overlay,background,position,palette),position)
        image.alpha_composite(base,position)
        image.alpha_composite(assemble(modules,recipe['assembly'],'lanterns',phase),position)
        image.alpha_composite(sprite,tuple(recipe['caelan_position']))
        image.alpha_composite(front,position)
        native=image.convert('RGB'); path=f'scene_frames/frame_{phase+1:02}.png'
        native.save(OUTPUT/path); frames.append({'image':path,'base_gate_frame':source_frame,'water_phase':phase,'duration_ms':200})
        previews.append(enlarged(native,recipe['scene_scale']))
        closeups.append(enlarged(native.crop(recipe['closeup_rect']),recipe['closeup_scale']))
    previews[0].save(OUTPUT/'review_scene.png'); closeups[0].save(OUTPUT/'bridge_closeup.png')
    save_loop(OUTPUT/'review_scene.gif',previews,recipe); save_loop(OUTPUT/'bridge_closeup.gif',closeups,recipe)
    write_json(OUTPUT/'review_scene.json',{'status':recipe['status'],'purpose':'Bridge art/scale review; illustrative, not a canonical map or playable level',
        'grid_size':[width,height],'base_scene':'../gate/review_scene.json','frames':frames,'grass_variants':grass_ids,
        'bridge_position':recipe['scene_position'],'assembly':recipe['assembly'],'restored_cells':recipe['restored_cells'],
        'east_dirt_cells':recipe['east_dirt_cells'],'dirt_join_cells':recipe['dirt_join_cells'],
        'character':{'name':'caelan','image_from_repo_root':'assets/characters/caelan/idle_right.png',
                     'position':recipe['caelan_position'],'foot':recipe['caelan_foot'],'replaces_original':True},
        'bank_elevations_pixels':recipe['bank_elevations_pixels'],'deck_elevation_pixels':recipe['deck_elevation_pixels'],
        'water_surface_elevation_pixels':recipe['water_surface_elevation_pixels'],'water_flow_direction':'S',
        'layer_order':['water_shadow','water_wakes','base_and_rear_rail','lanterns','character','foreground_rail'],
        'review':{'scene_scale':recipe['scene_scale'],'closeup_rect':recipe['closeup_rect'],'closeup_scale':recipe['closeup_scale']},
        'loop':True,'cycle_duration_ms':1200})


def build():
    recipe=read_json(SOURCE/'recipe.json'); palette=read_json(GATE/'palette.json')['materials']
    OUTPUT.mkdir(exist_ok=True)
    for directory in ('modules','frames','lanterns','wakes','scene_frames'): (OUTPUT/directory).mkdir(exist_ok=True)
    parts=extract_parts(recipe,palette); modules={}; records=[]
    for name in ('west','middle_a','middle_b','east'):
        base,front=module_layers(name,parts,palette)
        lanterns=[lantern_layer(name,p,parts,palette,recipe) for p in range(6)]
        water=[water_layers(name,p,palette) for p in range(6)]
        modules[name]={'base':base,'foreground':front,'lanterns':lanterns,
                       'shadow':[pair[0] for pair in water],'wake':[pair[1] for pair in water]}
        directory=OUTPUT/'modules'/name; directory.mkdir(exist_ok=True)
        base.save(directory/'base.png'); front.save(directory/'foreground.png')
        records.append({'id':name,'size':[24,72],'base':f'modules/{name}/base.png',
                        'foreground':f'modules/{name}/foreground.png','assembly_column':len(records),
                        'is_bank_end':name in ('west','east'),'is_repeatable':name.startswith('middle')})
    names=recipe['assembly']; base=assemble(modules,names,'base'); front=assemble(modules,names,'foreground')
    base.save(OUTPUT/'base.png'); front.save(OUTPUT/'foreground.png')
    assemble(modules,names,'shadow',0).save(OUTPUT/'water_shadow.png')
    sheet=Image.new('RGBA',(96,432)); boards=[]
    grass=Image.open(GROUND/'grass_00.png').convert('RGBA')
    for phase in range(6):
        lanterns=assemble(modules,names,'lanterns',phase); wake=assemble(modules,names,'wake',phase)
        lanterns.save(OUTPUT/f'lanterns/frame_{phase+1:02}.png'); wake.save(OUTPUT/f'wakes/frame_{phase+1:02}.png')
        frame=base.copy(); frame.alpha_composite(lanterns); frame.alpha_composite(front)
        frame.save(OUTPUT/f'frames/frame_{phase+1:02}.png'); sheet.paste(frame,(0,phase*72))
        if phase==0: frame.save(OUTPUT/'bridge.png')
        board=Image.new('RGB',(1008,608),'#e8edf2'); d=ImageDraw.Draw(board); d.fontmode='1'
        d.text((16,12),f"Eldenmere wooden bridge / 48px deck / {recipe['status']}",fill='#243529',font_size=22)
        for col,name in enumerate(names):
            sample=Image.new('RGBA',(24,72))
            for y in range(3): sample.paste(grass,(0,y*24))
            sample.alpha_composite(modules[name]['base']); sample.alpha_composite(modules[name]['lanterns'][phase]); sample.alpha_composite(modules[name]['foreground'])
            board.paste(enlarged(sample.convert('RGB'),7),(col*252+42,56))
            d.text((col*252+42,574),name,fill='#243529',font_size=20)
        boards.append(board)
    sheet.save(OUTPUT/'bridge_sheet.png'); boards[0].save(OUTPUT/'modules_review.png'); save_loop(OUTPUT/'modules_review.gif',boards,recipe)
    write_json(OUTPUT/'palette.json',{'status':recipe['status'],'materials':palette})
    write_json(OUTPUT/'tileset.json',{'id':recipe['id'],'status':recipe['status'],'tile_size':[24,24],
        'orientation':'E-W','module_size':[24,72],'prefab_size':[96,72],'ground_rect':recipe['ground_rect'],
        'clear_deck_width_pixels':48,'ground_overhang_north_pixels':12,'modules':records,'assembly':names,
        'base':'base.png','foreground':'foreground.png','image':'bridge.png','sheet':'bridge_sheet.png',
        'water_shadow':'water_shadow.png','frames':[{'image':f'frames/frame_{p+1:02}.png','sheet_rect':[0,p*72,96,72],
            'lanterns':f'lanterns/frame_{p+1:02}.png','water_wakes':f'wakes/frame_{p+1:02}.png','duration_ms':200} for p in range(6)],
        'loop':True,'cycle_duration_ms':1200,'front_rail_draws_after_characters':True,
        'repeat_rule':'west + one or more middle_a/middle_b columns + east; keep base/foreground/lantern column rectangles aligned',
        'recipe':'../../../source/terrain/eldenmere/bridge/recipe.json',
        'review':{'scene':'review_scene.gif','closeup':'bridge_closeup.gif','modules':'modules_review.gif'}})
    build_scene(recipe,palette,modules)
    print('Built east-west bridge: four 24x72 modules, 48px deck, layered rails, lanterns and water wakes')


if __name__=='__main__':
    build()
