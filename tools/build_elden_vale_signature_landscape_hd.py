#!/usr/bin/env python3
"""Export staged signature landscape drawings and offline review compositions."""
from __future__ import annotations
import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'assets/source/terrain/overworld/elden_vale/signature_landscape_hd'
OUT=ROOT/'assets/terrain/overworld/elden_vale/signature_landscape_hd'
REVIEW=ROOT/'docs/reviews/elden_vale_signature_landscape_hd'

def png(image):
    buffer=BytesIO();image.save(buffer,format='PNG',optimize=True);return buffer.getvalue()

def packed(data):return (json.dumps(data,indent=2)+'\n').encode()
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def clean(image):
    image=image.convert('RGBA')
    alpha=image.getchannel('A').point(lambda a:255 if a>=160 else 0)
    image=image.convert('RGB').quantize(colors=64,dither=Image.Dither.NONE).convert('RGBA')
    image.putalpha(alpha)
    return image

def fit(image,size):
    image=clean(image);box=image.getbbox()
    if box is None:raise ValueError('Empty source crop')
    image=image.crop(box);factor=min((size[0]-8)/image.width,(size[1]-8)/image.height)
    image=image.resize((max(1,round(image.width*factor)),max(1,round(image.height*factor))),Image.Resampling.NEAREST)
    canvas=Image.new('RGBA',size);canvas.alpha_composite(image,((size[0]-image.width)//2,size[1]-4-image.height))
    alpha=canvas.getchannel('A');outline=Image.new('RGBA',size)
    outline.putalpha(alpha.filter(ImageFilter.MaxFilter(3)));outline.alpha_composite(canvas)
    return outline

def segment_distance(p,a,b):
    dx,dy=b[0]-a[0],b[1]-a[1];den=dx*dx+dy*dy
    t=max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/den)) if den else 0
    return ((p[0]-a[0]-t*dx)**2+(p[1]-a[1]-t*dy)**2)**.5

def verify_layout(plan):
    map_path=ROOT/'assets/maps/elden_vale_sanctuary/map.json'
    if sha(map_path)!=plan['map_sha256']:raise ValueError('Scene changed: revisit layout plan')
    collision=Image.open(ROOT/plan['collision']).convert('L')
    if sha(ROOT/plan['collision'])!=plan['collision_sha256']:raise ValueError('Collision changed: revisit supports')
    for support in plan['base_supports']:
        x,y,w,h=support['rect']
        if collision.crop((x,y,x+w,y+h)).getextrema()!=(255,255):raise ValueError('Support occupies walkable ground')
        for point in plan['protected_approaches'].values():
            if x-24<=point[0]<=x+w+24 and y-24<=point[1]<=y+h+24:raise ValueError('Support obstructs approach')
        center=(x+w/2,y+h/2)
        for a,b in zip(plan['protected_loop'],plan['protected_loop'][1:]):
            if segment_distance(center,a,b)<max(w,h)/2+18:raise ValueError('Support crowds exploration loop')

def build(check=False):
    products={};dependencies={};images={}
    def depend(path):dependencies[str(path.relative_to(ROOT))]=sha(path)
    def emit(path,image):
        if set(image.getchannel('A').tobytes())-{0,255}:raise ValueError('Soft export alpha')
        products[path]=png(image)
    plan=json.loads((SOURCE/'layout_plan.json').read_text());verify_layout(plan)
    for path in [SOURCE/'generation_brief.json',SOURCE/'layout_plan.json',Path(__file__),ROOT/'assets/maps/elden_vale_sanctuary/map.json',ROOT/plan['collision']]:depend(path)
    manifest={'id':'elden_vale.signature_landscape.hd','integration_status':'not_integrated',
              'visual_approval':'not_reviewed_by_user','artwork_pixels_per_world_pixel':2,
              'path_space':'repository_relative','anchor_space':'logical','assets':{},'assemblies':{},
              'layout_plan':str((SOURCE/'layout_plan.json').relative_to(ROOT)),
              'palette':{'bone':['#e7dfc9','#b3ad9f','#646975'],'limestone':['#dfd6bc','#a7a293','#525b57'],
                         'moss':['#2c7c50','#194934'],'roles':'Ivory bone, cool stone shadows, emerald moss; retained drawn ramps are quantized, not flat recolors.'}}
    def asset(name,image,kind,**extra):
        path=OUT/kind/f'{name}.png';emit(path,image);images[name]=image
        record={'image':str(path.relative_to(ROOT)),'logical_size':[image.width/2,image.height/2],
                'draw_anchor_logical':[image.width/4,image.height/2-2],
                'depth_baseline_logical':image.height/2-2,
                'collision':'none' if kind in ('antlers','dressing') else 'unregistered; declared contacts require placement',
                'interaction_cues':False,**extra}
        manifest['assets'][name]=record
        return record
    master_path=SOURCE/'antlers_master.png';depend(master_path)
    master=fit(Image.open(master_path),(1568,1056))
    asset('antlers_complete',master,'antlers',role='coherent arrangement reference; not a single collision object')
    parts=[]
    for name,box,role in [('embedded_skull',(0,760,1568,1056),'grounded core and ridge-contact drawing'),
                          ('beam_left',(0,0,528,760),'overhead'),('beam_central',(528,0,1040,760),'overhead'),
                          ('beam_right',(1040,0,1568,760),'overhead')]:
        image=master.crop(box)
        record=asset(name,image,'antlers',role=role,assembly_position_artwork=list(box[:2]),
                     contact_rects_logical=[] if role=='overhead' else [[356,124,72,20]],
                     collision='none' if role=='overhead' else 'unregistered embedded ground contact',
                     occlusion='segmented alpha; local fade/cutaway at integration' if role=='overhead' else 'ridge grounded')
        if name=='embedded_skull':
            record['draw_anchor_logical']=[392,144]
            record['placement_candidate_logical']=[984,294]
            record['placement_status']='registered support study; final composition/grounding at integration'
        mask=OUT/'masks'/f'{name}.png' ;products[mask]=png(image.getchannel('A'))
        record['occlusion_mask']=str(mask.relative_to(ROOT));parts.append(name)
    manifest['assemblies']['antlers']={'canvas_artwork':[1568,1056],'parts':parts,
        'orientation':'skull lower center-right, facing lower-left; preserve at every scale',
        'connections':'Assembly positions reconstruct master exactly; do not independently mirror or rotate parts.'}
    for name,size in [('antlers_regional',(768,528)),('antlers_distant',(384,264))]:
        alternate=master.copy()
        if name=='antlers_distant':
            alternate.paste((0,0,0,0),(0,760,alternate.width,alternate.height))
        asset(name,alternate.resize(size,Image.Resampling.NEAREST),'antlers',role='same orientation; distant view excludes skull/base',source_asset='antlers_complete')
    ridge_names=['ridge_low','ridge_tall','ridge_outer_corner','ridge_inner_corner','ridge_left_end','ridge_right_end',
                 'ridge_broken_slope','earth_grass_contact','root_contact','ivy_contact','bone_fragment_small',
                 'bone_fragment_forked','buried_foundation','exposed_strata','bone_socket','nest_moss']
    causeway_names=['deck_straight','paving_top','deck_bend','deck_junction','broken_deck_end',
                    'parapet_intact','parapet_damaged','parapet_corner','arch_complete','arch_left_pier','arch_right_pier','buried_masonry']
    for sheet_name,names,rows in [('ridge',ridge_names,4),('causeway',causeway_names,3)]:
        path=SOURCE/f'{sheet_name}_master.png';depend(path);sheet=Image.open(path)
        for index,name in enumerate(names):
            col,row=index%4,index//4
            box=(round(col*sheet.width/4),round(row*sheet.height/rows),round((col+1)*sheet.width/4),round((row+1)*sheet.height/rows))
            size=(384,288) if name=='arch_complete' else (192,144)
            if name in ('bone_fragment_small','nest_moss'):size=(96,72)
            kind='dressing' if any(k in name for k in ('contact','fragment','nest')) else sheet_name
            extra={'source_cell':[col,row],'source_sheet':str(path.relative_to(ROOT)),
                   'ground_anchor_policy':'bottom registered; no footprint inferred from sprite alpha',
                   'support_rects_logical':[] if kind=='dressing' else [[8,size[1]/2-12,size[0]/2-16,10]]}
            if name=='arch_complete':
                extra['support_rects_logical']=[[4,130,44,12],[142,130,46,12]]
                extra['clear_underpass_logical']=[48,72,94,72]
            if name.startswith(('deck','ridge_','parapet')):
                extra['ports_logical']={'west':[4,size[1]/2-12],'east':[size[0]/2-4,size[1]/2-12]}
                extra['connection_rule']='authored overlapping joint/cap; not seamless autotile. Corners/ends have explicit handedness.'
            if 'ports_logical' in extra:
                directions={'deck_bend':['north','east'],'deck_junction':['west','east','south'],
                            'ridge_left_end':['east'],'ridge_right_end':['west'],
                            'ridge_outer_corner':['west','north'],'ridge_inner_corner':['south','east'],
                            'parapet_corner':['west','north']}.get(name,['west','east'])
                ports={'west':[4,size[1]/2-12],'east':[size[0]/2-4,size[1]/2-12],
                       'north':[size[0]/4,4],'south':[size[0]/4,size[1]/2-4]}
                extra['ports_logical']={d:ports[d] for d in directions}
            if name=='broken_deck_end':extra['ports_logical']={'west':[4,size[1]/2-24]}
            asset(name,fit(sheet.crop(box),size),kind,**extra)
    # Derive separately selectable overhead arch and supports from one drawing.
    arch=images['arch_complete'];arch_parts=[]
    for name,box in [('arch_lintel',(0,0,384,144)),('arch_support_left',(0,144,96,288)),('arch_support_right',(284,144,384,288))]:
        asset(name,arch.crop(box),'causeway',assembly_position_artwork=list(box[:2]),
              collision='none' if name=='arch_lintel' else 'unregistered support')
        arch_parts.append(name)
    manifest['assemblies']['arch']={'canvas_artwork':[384,288],'parts':arch_parts,
                                   'policy':'Supports beside open passage; no new boundary crossing.'}
    # The building miniature remains separately bounded; antlers are a separate landmark.
    miniature_source=ROOT/'assets/terrain/overworld/elden_vale/sanctuary/ridge_sanctuary.png'
    # Use the retained original generation rather than enlarging the legacy export.
    mini_recipe_path=ROOT/'assets/source/terrain/overworld/elden_vale/sanctuary/recipe.json'
    depend(mini_recipe_path)
    manifest['miniature_reference']={'existing_canvas_logical':[96,80],'legacy_image':str(miniature_source.relative_to(ROOT)),
        'policy':'Architecture from current detailed reserve donors; ridge and antlers independent.'}
    hall_path=ROOT/'assets/maps/sanctuary_reserve_hd/props/reserve_hall.png'
    if not hall_path.exists():
        candidates=list((ROOT/'assets/maps/sanctuary_reserve_hd/props').glob('*hall*.png'))
        hall_path=sorted(candidates)[0]
    depend(hall_path)
    miniature=Image.new('RGBA',(192,160))
    miniature.alpha_composite(fit(images['ridge_low'],(192,96)),(0,64))
    miniature.alpha_composite(fit(Image.open(hall_path),(144,112)),(8,18))
    tree_path=ROOT/'assets/terrain/vegetation_hd/plants/broadleaf_full/idle.png';depend(tree_path)
    cave_path=ROOT/'assets/maps/sanctuary_reserve_hd/props/reserve_cave.png';depend(cave_path)
    miniature.alpha_composite(fit(Image.open(cave_path),(72,64)),(118,28))
    memorial=Image.new('RGBA',(384,352))
    for layer in ('roots','trunk','canopy'):
        path=ROOT/f'assets/maps/sanctuary_reserve_hd/props/reserve_tree_44_landmark_{layer}.png';depend(path)
        memorial.alpha_composite(Image.open(path).convert('RGBA'))
    miniature.alpha_composite(fit(memorial,(56,64)),(132,86))
    asset('sanctuary_miniature',miniature,'miniature',logical_entry_geometry='unchanged; separate runtime contract',
          regional_landmark='antlers_regional is independently placed behind this building icon')
    # Review-only diagrams and scene studies, not active-game captures.
    board=Image.new('RGBA',(1200,((len(images)+3)//4)*220),'#d6ddcd');draw=ImageDraw.Draw(board)
    for index,(name,image) in enumerate(images.items()):
        factor=min(270/image.width,180/image.height,1)
        shown=image.resize((round(image.width*factor),round(image.height*factor)),Image.Resampling.NEAREST)
        x,y=index%4*300,index//4*220;board.alpha_composite(shown,(x+(300-shown.width)//2,y+185-shown.height))
        draw.text((x+8,y+192),name,fill='black')
    products[REVIEW/'asset_board.png']=png(board)
    scene_path=ROOT/'assets/maps/elden_vale_sanctuary/map.json';scene=json.loads(scene_path.read_text())
    plan_image=Image.new('RGB',tuple(scene['size_pixels']),'#dae2d4');draw=ImageDraw.Draw(plan_image)
    draw.line([tuple(p) for p in plan['protected_loop']],fill='#a37a49',width=12)
    for name,point in plan['protected_approaches'].items():
        x,y=point;draw.ellipse((x-15,y-15,x+15,y+15),outline='#335e98',width=2);draw.text((x+16,y),name,fill='black')
    for support in plan['base_supports']:
        x,y,w,h=support['rect'];draw.rectangle((x,y,x+w,y+h),fill='#70577a')
    draw.line((400,140,660,90,984,284),fill='#70577a',width=5)
    draw.text((20,20),'LOGICAL PLAN: purple support lies wholly in existing solid ridge; arcs overhead only',fill='black')
    products[REVIEW/'clearance_plan.png']=png(plan_image)
    grass_path=ROOT/'assets/terrain/eldenmere/grass_dirt_hd/materials/lawn_00.png';depend(grass_path)
    grass=Image.open(grass_path).convert('RGBA')
    actor_bank=ROOT/'assets/characters/caelan/animation.json';depend(actor_bank)
    actor_path=ROOT/json.loads(actor_bank.read_text())['idles']['front']['file'];depend(actor_path)
    actor=Image.open(actor_path).convert('RGBA')
    def scene_canvas(title):
        image=Image.new('RGBA',(960,640))
        for y in range(0,640,48):
            for x in range(0,960,48):image.paste(grass,(x,y))
        ImageDraw.Draw(image).text((12,12),'OFFLINE '+title+' / asset study; not gameplay',fill='white')
        return image
    for name,scale,offset in [('distant',.4,(310,50)),('forecourt',.55,(20,-20)),('approach',.65,(30,20)),('skull',1,(-200,-420)),('underpass',.8,(-600,-300))]:
        canvas=scene_canvas(name.upper());view=master.copy()
        if name=='distant':view.paste((0,0,0,0),(0,760,view.width,view.height))
        view=view.resize((round(master.width*scale),round(master.height*scale)),Image.Resampling.NEAREST)
        canvas.alpha_composite(view,offset)
        if name=='distant':
            for x in range(0,960,76):canvas.alpha_composite(fit(Image.open(tree_path),(112,144)),(x,230+(x//76%3)*15))
        canvas.alpha_composite(fit(Image.open(hall_path),(192,144)),(660,400))
        for x,y in [(40,370),(150,450),(820,350)]:canvas.alpha_composite(fit(Image.open(tree_path),(96,120)),(x,y))
        canvas.alpha_composite(actor,(470,550));products[REVIEW/f'{name}.png']=png(canvas)
    canvas=scene_canvas('INHABITED CAUSEWAY')
    for x in (50,220,390):canvas.alpha_composite(images['deck_straight'],(x,370))
    canvas.alpha_composite(images['broken_deck_end'],(550,370))
    canvas.alpha_composite(arch,(520,60))
    canvas.alpha_composite(images['parapet_damaged'],(70,280))
    bench_path=ROOT/'assets/terrain/overworld/elden_vale/hd/props/bench.png';depend(bench_path)
    canvas.alpha_composite(Image.open(bench_path).convert('RGBA'),(340,280));canvas.alpha_composite(actor,(690,270))
    products[REVIEW/'causeway.png']=png(canvas)
    for key,modules in [('ridge_run',['ridge_left_end','ridge_low','ridge_low','ridge_outer_corner']),
                        ('causeway_run',['deck_straight','deck_straight','deck_straight','broken_deck_end'])]:
        placements=[{'asset':name,'position_logical':[88*i,12 if name=='broken_deck_end' else 0]} for i,name in enumerate(modules)]
        manifest['assemblies'][key]={'placements':placements,'port_join':'east to west at identical logical points; 4-unit artwork overlap each side'}
        assembled=scene_canvas(key.upper())
        for placement in placements:
            x,y=placement['position_logical'];assembled.alpha_composite(images[placement['asset']],(60+2*x,260+2*y))
        assembled.alpha_composite(actor,(440,450));products[REVIEW/f'{key}.png']=png(assembled)

    products[OUT/'manifest.json']=packed(manifest)
    products[SOURCE/'recipe.json']=packed({'id':manifest['id'],'sources':dependencies,'alpha_threshold':160,
        'processing':'cell crops, uniform sampling, 64-color quantization, hard alpha, one artwork pixel exterior contour',
        'lighting':'upper-left','density':2,'region':'Elden Vale','animation':'static; weather in PR3',
        'geometry':'layout_plan.json; all exports staged, no runtime collision or selectors changed'})
    stale=[]
    for path,data in products.items():
        if check:
            if not path.exists() or path.read_bytes()!=data:stale.append(str(path.relative_to(ROOT)))
        else:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    if stale:raise SystemExit('Stale exports: '+', '.join(stale))
    print(f'{"Verified" if check else "Exported"} {len(manifest["assets"])} assets, {len(products)} products')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true')
    build(parser.parse_args().check)
