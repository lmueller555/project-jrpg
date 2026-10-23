"""Recolor approved cottage materials without changing pixel geometry or animation."""
from copy import deepcopy
from pathlib import Path
from random import Random
from PIL import Image, ImageDraw
from build_eldenmere_stream import read_json, write_json, rgba, enlarged, save_loop

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'assets/source/terrain/eldenmere/cottage_variants'
OUTPUT=ROOT/'assets/terrain/eldenmere/cottage_variants'
BASE=OUTPUT.parent/'cottage'
GROUND=OUTPUT.parent/'grass_dirt'
HANGING_ROWS=((3,6),(2,6),(1,7),(1,7),(1,7),(1,7),(1,7),(1,7),(2,6))
SWING=(0,1,1,0,-1,-1)


def roof_aliases(palette,overrides):
    """Preserve sampled shade differences, including dark tile joints between shingles."""
    luminance=lambda c:0.2126*c[0]+0.7152*c[1]+0.0722*c[2]
    joint=tuple(max(0,v-25) for v in rgba(overrides['roof']['shadow'])[:3])+(255,)
    anchors=[(luminance(rgba(palette['glass']['dark'])),joint)]
    anchors.extend((luminance(rgba(palette['roof'][shade])),rgba(overrides['roof'][shade])) for shade in palette['roof'])
    edge=rgba(overrides['roof']['edge'])
    anchors.append((220,tuple(min(255,v+18) for v in edge[:3])+(255,)))
    aliases={}
    for ramp in palette.values():
        for color in ramp.values():
            source=rgba(color); value=luminance(source)
            for (low,a),(high,b) in zip(anchors,anchors[1:]):
                if low<=value<=high:
                    t=(value-low)/(high-low)
                    aliases[source]=tuple(round(x+(y-x)*t) for x,y in zip(a[:3],b[:3]))+(255,)
                    break
            else:aliases[source]=anchors[0][1] if value<anchors[0][0] else anchors[-1][1]
    return aliases


def lantern_pixel(x,y,swing):
    row=y-112
    return 0<=row<len(HANGING_ROWS) and 68+HANGING_ROWS[row][0]+swing<=x<68+HANGING_ROWS[row][1]+swing


def recolored(image,palette,overrides,origin=(0,0),phase=0,plain=False):
    """Exact shade substitutions with semantic exceptions for flowers/light/stone."""
    maps={material:{rgba(color):rgba(overrides[material][shade]) for shade,color in palette[material].items()}
          for material in overrides}
    roof_map=roof_aliases(palette,overrides)
    result=image.copy(); swing=SWING[phase%6]
    for yy in range(image.height):
        for xx in range(image.width):
            pixel=image.getpixel((xx,yy))
            if not pixel[3]: continue
            x,y=xx+origin[0],yy+origin[1]
            protected=not plain and ((82<=x<98 and 48<=y<70) or lantern_pixel(x,y,swing)
                                     or (23<=x<39 and 123<=y<132 and pixel in maps['plaster']))
            if protected: continue
            roof=56<=y<101 and not (82<=x<98 and y<70)
            if roof and pixel not in maps['wood']:
                # The sampled reference shares gray/blue roof pixels with other named ramps.
                # Resolve aliases inside the roof only, retaining joint contrast and neutral stone elsewhere.
                result.putpixel((xx,yy),roof_map[pixel])
            elif pixel in maps['wood']: result.putpixel((xx,yy),maps['wood'][pixel])
            elif pixel in maps['plaster'] and y>=101: result.putpixel((xx,yy),maps['plaster'][pixel])
    return result


def native_inputs(meta):
    records=[('structure.png',(0,0),0,False),('closed.png',(0,0),0,False),('open.png',(0,0),0,False)]
    for c in meta['components']: records.append((c['image'],tuple(c['position']),0,False))
    inserts=(('roof_repeat',(48,56),True),('wall_blank',(24,101),True),
             ('window_left_lit',(19,109),False),('window_right_lit',(79,109),False))
    for name,position,plain in inserts: records.append((f'parts/{name}.png',position,0,plain))
    for phase in range(5): records.append((f'doors/frame_{phase+1:02}.png',(0,0),0,False))
    for phase in range(18):
        for folder in ('smoke','lantern','preview_frames'): records.append((f'{folder}/frame_{phase+1:02}.png',(0,0),phase,False))
    return records


def export_variant(record,recipe,base_meta,palette):
    directory=OUTPUT/record['id']; directory.mkdir(exist_ok=True)
    for path,origin,phase,plain in native_inputs(base_meta):
        destination=directory/path; destination.parent.mkdir(exist_ok=True)
        image=Image.open(BASE/path).convert('RGBA')
        recolored(image,palette,record['palette'],origin,phase,plain).save(destination)
    # Derive previews from exported layers to guarantee identical pose/phase composition.
    base=Image.open(directory/'structure.png').convert('RGBA'); sheet=Image.new('RGBA',(600,144))
    lamp=Image.open(directory/'lantern/frame_01.png').convert('RGBA')
    for index in range(5):
        frame=base.copy(); frame.alpha_composite(Image.open(directory/f'doors/frame_{index+1:02}.png').convert('RGBA'))
        frame.alpha_composite(lamp); sheet.paste(frame,(index*120,0))
    sheet.save(directory/'door_sheet.png')
    frames=[]
    for phase in range(18):
        frame=base.copy(); door_index=read_json(BASE/'review_scene.json')['frames'][phase]['door_frame']
        for path in (f'doors/frame_{door_index+1:02}.png',f'lantern/frame_{phase+1:02}.png',f'smoke/frame_{phase+1:02}.png'):
            frame.alpha_composite(Image.open(directory/path).convert('RGBA'))
        frame.save(directory/f'preview_frames/frame_{phase+1:02}.png'); frames.append(frame)
    for state,index in (('closed',0),('open',4)):
        frame=base.copy();frame.alpha_composite(Image.open(directory/f'doors/frame_{index+1:02}.png').convert('RGBA'));frame.alpha_composite(lamp)
        frame.save(directory/f'{state}.png')
    materials=deepcopy(palette);materials.update(record['palette'])
    materials['retained_details']={f'{name}_{shade}':color for name in ('roof','wood','plaster') for shade,color in palette[name].items()}
    aliases=roof_aliases(palette,record['palette'])
    materials['roof_detail']={f'{name}_{shade}':'#'+bytes(aliases[rgba(color)][:3]).hex()
                              for name,ramp in palette.items() for shade,color in ramp.items() if name!='wood'}
    write_json(directory/'palette.json',{'status':recipe['status'],'materials':materials})
    metadata=deepcopy(base_meta);metadata['id']=f"eldenmere.cottage.{record['id']}.24";metadata['status']=recipe['status']
    metadata['palette_name']=record['name'];metadata['base_from_repo_root']=str(BASE.relative_to(ROOT))
    metadata['recipe']='../../../../source/terrain/eldenmere/cottage_variants/recipe.json'
    write_json(directory/'cottage.json',metadata)
    return frames


def path_cells(recipe):
    cells={(8,y) for y in range(24,34)}|{(x,33) for x in range(3,26)}
    for variant in recipe['variants']:
        x,y=variant['position']; cells.add(((x+60)//24,(y+142)//24))
    return cells


def background(recipe):
    meta=read_json(GROUND/'tileset.json'); rng=Random(recipe['scene_seed']); width,height=recipe['scene_size']
    grass=[Image.open(GROUND/p).convert('RGBA') for p in meta['grass']['images']]
    grass_ids=[[rng.choices(range(4),weights=(5,3,2,1))[0] for _ in range(width)] for _ in range(height-26)]
    extension=Image.new('RGBA',(width*24,height*24))
    for y,row in enumerate(grass_ids,start=26):
        for x,index in enumerate(row): extension.paste(grass[index],(x*24,y*24))
    dirt={t['mask']:Image.open(GROUND/t['image']).convert('RGBA') for t in meta['tiles']}
    paths=Image.new('RGBA',extension.size); cells=path_cells(recipe); joins=cells|{tuple(p) for p in recipe['path_join_cells']}
    offsets=((0,-1),(1,-1),(1,0),(1,1),(0,1),(-1,1),(-1,0),(-1,-1))
    for x,y in sorted(cells):
        raw=sum(1<<i for i,(dx,dy) in enumerate(offsets) if (x+dx,y+dy) in joins)
        mask=meta['tiles'][meta['lookup_256'][raw]]['mask']; paths.alpha_composite(dirt[mask],(x*24,y*24))
    # A narrow apron joins the existing rounded path tip without redrawing the NPC.
    fills=[Image.open(GROUND/p).convert('RGBA') for p in meta['dirt_interiors']['images']]
    x,y,w,h=recipe['connector_apron']; paths.alpha_composite(fills[0].crop((8,0,8+w,h)),(x,y))
    paths.save(OUTPUT/'review_path.png')
    return extension,paths,grass_ids


def review_board(recipe,frames):
    boards=[]; base_name='Slate / cream / timber (approved)'
    for phase in range(18):
        board=Image.new('RGB',(2048,720),'#e8edf2'); d=ImageDraw.Draw(board); d.fontmode='1'
        d.text((20,16),f"Eldenmere cottage palettes / synchronized door, lantern and smoke / new colors: {recipe['status']}",fill='#243529',font_size=24)
        for column,(name,images) in enumerate([(base_name,frames['base'])]+[(r['name'],frames[r['id']]) for r in recipe['variants']]):
            x=column*512+16; d.text((x,64),name,fill='#243529',font_size=20)
            tile=Image.new('RGBA',(120,144),'#70935a');tile.alpha_composite(images[phase]);board.paste(enlarged(tile.convert('RGB'),4),(x,104))
        boards.append(board)
    boards[0].save(OUTPUT/'variants_review.png');save_loop(OUTPUT/'variants_review.gif',boards,recipe)


def build():
    recipe=read_json(SOURCE/'recipe.json'); meta=read_json(BASE/'cottage.json'); palette=read_json(BASE/'palette.json')['materials']
    OUTPUT.mkdir(exist_ok=True);(OUTPUT/'scene_frames').mkdir(exist_ok=True)
    frames={'base':[Image.open(BASE/f'preview_frames/frame_{i+1:02}.png').convert('RGBA') for i in range(18)]}
    for record in recipe['variants']:frames[record['id']]=export_variant(record,recipe,meta,palette)
    extension,paths,grass_ids=background(recipe);scenes=[];closeups=[];records=[]
    for phase in range(18):
        scene=extension.copy(); scene.paste(Image.open(BASE/f'scene_frames/frame_{phase+1:02}.png').convert('RGBA'),(0,0));scene.alpha_composite(paths)
        for record in recipe['variants']:scene.alpha_composite(frames[record['id']][phase],tuple(record['position']))
        native=scene.convert('RGB'); path=f'scene_frames/frame_{phase+1:02}.png';native.save(OUTPUT/path)
        scenes.append(enlarged(native,recipe['scene_scale']));closeups.append(enlarged(native.crop(recipe['courtyard_crop']),recipe['courtyard_scale']))
        records.append({'image':path,'base_phase':phase,'duration_ms':recipe['duration_ms']})
    for name,images in (('review_scene',scenes),('courtyard_closeup',closeups)):
        images[0].save(OUTPUT/f'{name}.png');save_loop(OUTPUT/f'{name}.gif',images,recipe)
    review_board(recipe,frames)
    write_json(OUTPUT/'variants.json',{'id':recipe['id'],'status':recipe['status'],'tile_size':[24,24],'prefab_size':meta['prefab_size'],'ground_rect':meta['ground_rect'],
        'base':{'id':'base','status':'approved','metadata':'../cottage/cottage.json'},
        'variants':[{'id':r['id'],'name':r['name'],'status':recipe['status'],'metadata':f"{r['id']}/cottage.json"} for r in recipe['variants']],
        'review':{'comparison':'variants_review.gif','scene':'review_scene.gif','courtyard':'courtyard_closeup.gif'},'timing_inherited':True})
    write_json(OUTPUT/'review_scene.json',{'status':recipe['status'],'purpose':'Palette art review; demonstration courtyard, not canonical geography or a game level',
        'base_scene':'../cottage/review_scene.json','grid_size':recipe['scene_size'],'grass_extension_start_row':26,'grass_extension':grass_ids,
        'path_cells':[list(p) for p in sorted(path_cells(recipe))],'path_join_cells':recipe['path_join_cells'],'connector_apron':recipe['connector_apron'],
        'instances':[{'id':r['id'],'position':r['position'],'ground_elevation_pixels':recipe['ground_elevation_pixels'],
                      'threshold_elevation_pixels':recipe['threshold_elevation_pixels'],'foot':[r['position'][0]+60,r['position'][1]+142]} for r in recipe['variants']],
        'frames':records,'cycle_duration_ms':3600,'loop':True,'door_use_is_demonstration_only':True,
        'review':{'scene_scale':recipe['scene_scale'],'courtyard_crop':recipe['courtyard_crop'],'courtyard_scale':recipe['courtyard_scale']}})
    print(f"Built three {recipe['status']} material palettes, synchronized four-cottage comparison and extended scene")

if __name__=='__main__':build()
