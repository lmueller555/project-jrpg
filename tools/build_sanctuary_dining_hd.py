"""Export retained new artwork at 2× density, preserving the dining-room layout.

The generated source atlases are retained, not recreated by this command.
Extraction, hard-alpha cleanup, palette reduction and registration are explicit;
no legacy sprite is enlarged to supply the new drawings.
"""
from pathlib import Path
import hashlib
import json
import math

from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'assets/source/terrain/eldenmere/sanctuary_dining_hd'
OUT=ROOT/'assets/terrain/eldenmere/sanctuary_dining_hd'
INK=(17,18,20,255)


def save(image,path):
    path.parent.mkdir(parents=True,exist_ok=True);image.save(path)
    return path.relative_to(ROOT).as_posix()


def cell(atlas,index,columns):
    x,y=index%columns,index//columns
    return atlas.crop((round(x*atlas.width/columns),round(y*atlas.height/columns),
                       round((x+1)*atlas.width/columns),round((y+1)*atlas.height/columns)))


def clean_source(source):
    """Remove transparent-source export matte before measuring its silhouette."""
    source=source.convert('RGBA')
    mask=source.getchannel('A').point(lambda a:255 if a>=220 else 0)
    # Some generated transparent margins contain near-black, partly opaque
    # matte pixels. Exclude that matte before fitting; otherwise it shrinks a
    # small workstation prop into a corner of its registered canvas.
    channels=source.split()
    brightness=ImageChops.lighter(ImageChops.lighter(channels[0],channels[1]),channels[2])
    mask=ImageChops.multiply(mask,brightness.point(lambda c:255 if c>8 else 0))
    source.putalpha(mask)
    bounds=mask.getbbox()
    if bounds is None:raise ValueError('Source cell has no opaque artwork')
    return source.crop(bounds)


def export_sprite(source,size,bounds=None,fit=True):
    """Register new silhouettes inside the original logical canvas/support bounds."""
    source=clean_source(source)
    bounds=bounds or (0,0,*size)
    left,top,right,bottom=bounds;w,h=right-left,bottom-top
    # Fit without changing the new drawing's proportions; keep support fixed.
    factor=min(w/source.width,h/source.height)
    target=(max(1,round(source.width*factor)),max(1,round(source.height*factor))) if fit else (w,h)
    source=source.resize(target,Image.Resampling.NEAREST)
    # Nearest sampling can miss the last isolated source-edge texel. Register
    # the resulting opaque support, not the resampled transparent margin.
    if fit:source=source.crop(source.getbbox())
    alpha=source.getchannel('A')
    source=source.convert('RGB').quantize(colors=48,dither=Image.Dither.NONE).convert('RGBA')
    source.putalpha(alpha)
    # A single artwork-pixel black contour survives export; internal shading
    # stays authored. Transparent padding prevents clipping at the canvas edge.
    padded=Image.new('L',(source.width+2,source.height+2));padded.paste(alpha,(1,1))
    inner=padded.filter(ImageFilter.MinFilter(3)).crop((1,1,source.width+1,source.height+1))
    edge=ImageChops.subtract(alpha,inner)
    source.paste(INK,(0,0),edge)
    canvas=Image.new('RGBA',size)
    canvas.alpha_composite(source,(left+(w-source.width)//2,bottom-source.height))
    return canvas


def registered_hearth_frames(sources,contract):
    """Animate only rooted fire, behind one stationary firebox and log lip.

    Independently fitting generated whole-fireplace drawings is not animation
    registration: their logs and bright flame beds move even with fixed masonry.
    Keep the first drawing's support, extract just its connected flame family,
    and give every pose the same local bottom-center attachment.
    """
    structure=sources[0].copy()
    mask=Image.new('L',structure.size)
    ImageDraw.Draw(mask).polygon([tuple(p) for p in contract['cavity_polygon_artwork']],fill=255)
    soot=Image.new('RGBA',structure.size,tuple(contract['soot_rgba']))
    draw=ImageDraw.Draw(soot)
    for x0,y0,x1,y1 in contract['brick_seams_artwork']:
        draw.line((x0,y0,x1,y1),fill=tuple(contract['mortar_rgba']))
    structure.paste(soot,(0,0),mask)
    layers=[];frames=[]
    x0,y0,x1,y1=contract['source_flame_rect_artwork']
    root_x,root_y=contract['root_artwork']
    for source in sources:
        warm=set()
        for y in range(y0,y1):
            for x in range(x0,x1):
                r,g,b,a=source.getpixel((x,y))
                if a and r>=140 and g>=60 and r-g>=12 and g-b>=20:
                    warm.add((x,y))
        components=[]
        while warm:
            queue=[warm.pop()];component=set(queue)
            while queue:
                x,y=queue.pop()
                for dx in (-1,0,1):
                    for dy in (-1,0,1):
                        point=(x+dx,y+dy)
                        if point in warm:
                            warm.remove(point);component.add(point);queue.append(point)
            components.append(component)
        if not components:raise ValueError('Hearth source has no connected flame')
        # Discard detached sparks/brick highlights, not just transparent padding.
        connected=max(components,key=len)
        flame=Image.new('RGBA',source.size)
        for point in connected:flame.putpixel(point,source.getpixel(point))
        bounds=flame.getbbox();flame=flame.crop(bounds)
        if flame.height>contract['maximum_flame_height_artwork']:
            height=contract['maximum_flame_height_artwork']
            flame=flame.resize((round(flame.width*height/flame.height),height),Image.Resampling.NEAREST)
        bottom=[x for x in range(flame.width) if flame.getpixel((x,flame.height-1))[3]]
        anchor=(min(bottom)+max(bottom)+1)//2
        layer=Image.new('RGBA',structure.size)
        layer.alpha_composite(flame,(root_x-anchor,root_y-flame.height))
        layer.putalpha(ImageChops.multiply(layer.getchannel('A'),mask))
        frame=structure.copy();frame.alpha_composite(layer)
        frames.append(frame);layers.append(layer)
    return frames,structure,mask,layers


def build_hearth(recipe,props):
    contract=recipe['hearth_animation']
    sources=[]
    for item in recipe['props']:
        if item['id']!='hearth':continue
        sources.append(export_sprite(cell(props,item['cell'],item.get('columns',5)),
            tuple(v*2 for v in item['logical_size']),tuple(v*2 for v in item['logical_bounds'])))
    frames,structure,mask,layers=registered_hearth_frames(sources,contract)
    save(structure,OUT/'hearth/structure.png');save(mask,OUT/'hearth/cavity_mask.png')
    for index,(frame,layer) in enumerate(zip(frames,layers),1):
        save(frame,OUT/f'props/hearth_frame_{index:02}.png')
        save(layer,OUT/f'hearth/flame_{index:02}.png')
    return {**contract,'structure':'hearth/structure.png','cavity_mask':'hearth/cavity_mask.png',
            'flame_layers':[f'hearth/flame_{i:02}.png' for i in range(1,len(frames)+1)]}


def build():
    recipe=json.loads((SOURCE/'recipe.json').read_text());original=recipe['original_map']
    for name,digest in recipe['sources'].items():
        if hashlib.sha256((SOURCE/name).read_bytes()).hexdigest()!=digest:
            raise ValueError('Source changed: update the explicit extraction recipe first')
    props=Image.open(SOURCE/'props_atlas.png').convert('RGBA')
    architecture=Image.open(SOURCE/'architecture_atlas.png').convert('RGBA')
    replacements={};exports=[]
    for item in recipe['props']:
        name=item['id']
        if name=='hearth':name+='_'+Path(item['legacy_path']).stem
        size=tuple(v*2 for v in item['logical_size'])
        bounds=tuple(v*2 for v in item['logical_bounds'])
        source=Image.open(SOURCE/item['source']).convert('RGBA') if 'source' in item else props
        if 'cell' in item:source=cell(source,item['cell'],item.get('columns',5))
        image=export_sprite(source,size,bounds)
        replacements[item['legacy_path']]=save(image,OUT/f'props/{name}.png')
        exports.append({**item,'image':replacements[item['legacy_path']],
                        'artwork_size':list(size),'artwork_pixels_per_world_pixel':2})
    hearth_animation=build_hearth(recipe,props)
    cup=export_sprite(cell(props,24,5),(12,12))
    save(cup,OUT/'props/cup.png')
    # Steam is vapor, not an outlined solid object.
    glyph=clean_source(cell(props,23,5)).resize((10,10),Image.Resampling.NEAREST)
    save(glyph,OUT/'props/steam_glyph.png')

    def part(index,name,size):
        # Architecture strips tile edge-to-edge; their run length is layout,
        # not an isolated furniture silhouette with transparent fit padding.
        im=export_sprite(cell(architecture,index,3),size,fit=False)
        save(im,OUT/f'architecture/{name}.png');return im
    # Interior texture crops discard source-sheet margins, never include an
    # outline around floor tiles, and tile on an even logical grid.
    floor=architecture.crop((24,24,396,396)).resize((96,96),Image.Resampling.NEAREST).convert('RGB')
    plaster=architecture.crop((450,32,796,376)).resize((96,96),Image.Resampling.NEAREST).convert('RGB')
    floor=floor.quantize(colors=24,dither=Image.Dither.NONE).convert('RGBA')
    plaster=plaster.quantize(colors=16,dither=Image.Dither.NONE).convert('RGBA')
    floor.putalpha(255);plaster.putalpha(255)
    save(floor,OUT/'architecture/floor_tile.png');save(plaster,OUT/'architecture/plaster_tile.png')
    beam=part(2,'upright',(12,96));rail=part(4,'rail',(192,12))
    window=part(3,'window',(48,60));side=part(6,'cutaway',(24,96))
    threshold=part(5,'threshold',(48,16))
    size=tuple(v*2 for v in original['size_pixels'])
    shell=Image.new('RGBA',size,'#24302d')
    for y in range(144,624,96):
        for x in range(48,816,96):shell.alpha_composite(floor,(x,y))
    for x in range(48,816,96):shell.alpha_composite(plaster,(x,48))
    for x in range(48,816,192):
        shell.alpha_composite(rail,(x,48));shell.alpha_composite(rail,(x,132))
    for x in (40,240,432,804):shell.alpha_composite(beam,(x,48))
    for x in (24,816):
        for y in range(48,624,96):shell.alpha_composite(side,(x,y))
    for x,y in ((72,32),(168,32)):shell.alpha_composite(window,(x*2,y*2))
    for x in range(24,840,192):
        piece=rail.crop((0,0,min(192,840-x),12));shell.alpha_composite(piece,(x,624))
    shell.alpha_composite(threshold,(408,624))
    save(shell,OUT/'architecture/structure.png')
    old=ROOT/'assets/terrain/eldenmere/sanctuary_interior/dining'
    day=Image.open(old/'daylight_mask.png').convert('L').resize(size,Image.Resampling.NEAREST)
    glow=Image.open(old/'floor_glow_mask.png').convert('L').resize(size,Image.Resampling.NEAREST)
    # Store architecture once. Small registered light layers preserve the old
    # 5.4s daylight / 1.2s hearth rhythms without twelve full-room 2× copies.
    ground=save(shell.convert('RGB'),OUT/'ground/base.png')
    for obsolete in (OUT/'ground').glob('frame_*.png'):obsolete.unlink()
    lighting=[]
    for name,mask,color,strengths,duration in (
        ('daylight',day,'#f2d7a0',[.08+.045*(1+math.sin(i*math.tau/9)) for i in range(9)],600),
        ('firelight',glow,'#ef9d53',[.09,.14,.12,.17],300)):
        bounds=mask.getbbox();frames=[]
        for index,strength in enumerate(strengths):
            overlay=Image.new('RGBA',size,color)
            overlay.putalpha(mask.point(lambda a:round(a*strength)))
            frames.append(save(overlay.crop(bounds),OUT/f'lighting/{name}_{index:02}.png'))
        lighting.append({'id':'dining_'+name,'position':[bounds[0]//2,bounds[1]//2],
                         'sort_y':-1,'sort_priority':0,'frames':frames,
                         'frame_duration_ms':duration,'phase_offset':0,'reduced_motion_frame':0,
                         'artwork_pixels_per_world_pixel':2})
    steam=[]
    for phase in range(6):
        frame=Image.new('RGBA',size)
        for particle in (0,3):
            age=(phase+particle)%6
            frame.alpha_composite(glyph,((271-2+age//3)*2,(63-2-age)*2))
        steam.append(save(frame.crop((538,112,550,132)),OUT/f'steam/frame_{phase+1:02}.png'))
    # Preserve future gameplay edits: replace only art paths/density and cues.
    map_path=ROOT/recipe['map'];data=json.loads(map_path.read_text())
    if hashlib.sha256((ROOT/data['collision']).read_bytes()).hexdigest()!=recipe['preserved_collision_sha256']:
        raise ValueError('Collision changed: review registration before rebuilding')
    data['artwork_pixels_per_world_pixel']=2
    data['art_bank']=(OUT/'manifest.json').relative_to(ROOT).as_posix()
    data['art_replacements']={path:{'file':replacement,'artwork_pixels_per_world_pixel':2}
                              for path,replacement in replacements.items()}
    data['art_replacements']['assets/story/sanctuary_opening/poses/cup.png']={
        'file':str((OUT/'props/cup.png').relative_to(ROOT)),'artwork_pixels_per_world_pixel':2}
    data['ground_frames']=[ground]
    originals={e['id']:e for e in original['entities']}
    data['entities']=[e for e in data['entities'] if e['id'] not in ('dining_daylight','dining_firelight')]
    for entity in data['entities']:
        if entity['id'] not in originals:continue
        record=originals[entity['id']]
        entity['frames']=steam if entity['id']=='kettle_steam' else [replacements[p] for p in record['frames']]
        entity['artwork_pixels_per_world_pixel']=2
        if entity['id']=='kettle_steam':
            entity['position']=[269,56]
            entity['source_logical_canvas']=original['size_pixels']
            entity['registration_offset']=[269,56]
        if entity['id'] in ('hearth','kettle_steam'):entity['reduced_motion_frame']=0
    data['entities'].extend(lighting)
    other_cues=[r for r in data.get('interaction_cues',[]) if r['id']!='breakfast']
    data['interaction_cues']=other_cues+[{'id':'breakfast','entity':'breakfast','available_when':'opening_breakfast',
        'interaction_boundary':[144,192,48,18],'glint_anchor':[14,5]}]
    map_path.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
    manifest={'version':1,'status':'integrated','artwork_pixels_per_world_pixel':2,
              'logical_size':original['size_pixels'],'recipe':str((SOURCE/'recipe.json').relative_to(ROOT)),
              'collision_sha256':recipe['preserved_collision_sha256'],'props':exports,
              'legacy_replacements':replacements,'character_banks_migrated':False,
              'hearth_animation':hearth_animation,
              'ground_duration_ms':original['ground_frame_duration_ms']*len(original['ground_frames'])}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(f'Exported {len(exports)} registered prop drawings, shared architecture, compact light layers and six steam frames.')


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hearth-only',action='store_true',help='Rebuild the shared fire without touching room/layout exports')
    args=parser.parse_args()
    if args.hearth_only:
        recipe=json.loads((SOURCE/'recipe.json').read_text())
        for name,digest in recipe['sources'].items():
            if hashlib.sha256((SOURCE/name).read_bytes()).hexdigest()!=digest:
                raise ValueError('Source changed: update the explicit extraction recipe first')
        animation=build_hearth(recipe,Image.open(SOURCE/'props_atlas.png').convert('RGBA'))
        path=OUT/'manifest.json';manifest=json.loads(path.read_text());manifest['hearth_animation']=animation
        path.write_text(json.dumps(manifest,indent=2)+'\n')
    else:build()
