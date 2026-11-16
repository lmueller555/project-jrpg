"""Integrate native-density Sanctuary art into the assembled town, preserving gameplay.

Reads the current map, never recompiles the whole town. Baseline files provide
coverage and contract evidence only; their legacy RGB is not artwork input.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from tools import build_eldenmere_exteriors_hd as exterior
from tools.build_world_water_hd import encoded, load
SOURCE=ROOT/'assets/source/maps/eldenmere/courtyard_hd'
PACK='assets/maps/eldenmere/courtyard_hd'

def read(path):return json.loads(Path(path).read_text())
def document(data):return (json.dumps(data,indent=2)+'\n').encode()
def overlaps(a,b):return a[0]<b[0]+b[2] and b[0]<a[0]+a[2] and a[1]<b[1]+b[3] and b[1]<a[1]+a[3]

def products():
    rec=read(SOURCE/'recipe.json');out={};exports=[]
    for r in rec['sources']:
        if sha256((SOURCE/r['file']).read_bytes()).hexdigest()!=r['sha256']:raise ValueError('Changed integration source: '+r['file'])
    data=read(ROOT/rec['map']);baseline=read(SOURCE/'baseline_map.json')
    for field in ('collision','navigation'):
        path=data['collision'] if field=='collision' else data['navigation_allowed']
        if sha256((ROOT/path).read_bytes()).hexdigest()!=rec[field+'_sha256']:raise ValueError('Review changed '+field+' before rebuilding')
    def export(path,im):
        raw=encoded(im);out[path]=raw;exports.append({'file':path,'artwork_size':list(im.size),'sha256':sha256(raw).hexdigest()});return path
    def native(im,name):return export(PACK+'/'+name+'.png',im)
    region=rec['region_logical'];rx,ry,rw,rh=region;ground=Image.new('RGBA',(rw*2,rh*2))
    gm=read(ROOT/'assets/terrain/eldenmere/grass_dirt_hd/tileset.json');gp=ROOT/'assets/terrain/eldenmere/grass_dirt_hd'
    grass=[load(gp/p) for p in gm['materials']['grass']];dirt={r['mask']:load(gp/r['file']) for r in gm['tiles']};geo=read(SOURCE/'geometry.json');dirt_cells={tuple(r['cell']):r['mask'] for r in geo['dirt']}
    for y in range(ry//24,(ry+rh)//24):
        for x in range(rx//24,(rx+rw)//24):
            pos=((x*24-rx)*2,(y*24-ry)*2);ground.alpha_composite(grass[(x//3+y//4)%4],pos)
            if (x,y) in dirt_cells:ground.alpha_composite(dirt[dirt_cells[x,y]],pos)
    # Flagstone coverage remains authored logical geometry; all RGB is new paving.
    cover=Image.open(SOURCE/'flagstone_coverage.png').convert('L').resize((64,32),Image.Resampling.NEAREST);pattern=load(ROOT/'assets/terrain/eldenmere/stone_paving_hd/surface/pattern_96.png');stones=Image.new('RGBA',(64,32));fx,fy=rec['flagstones_world']
    for y in range(32):
        for x in range(64):stones.putpixel((x,y),pattern.getpixel(((fx*2+x)%96,(fy*2+y)%96)))
    stones.putalpha(cover);ground.alpha_composite(stones,((fx-rx)*2,(fy-ry)*2));under=ground.copy()
    terrace=ROOT/'assets/terrain/eldenmere/terraces_hd'
    for r in geo['masonry']:
        x,y=r['position']
        if overlaps([x,y,24,24],region):ground.alpha_composite(load(terrace/f'modules/maintained/{r["tile"]}.png'),((x-rx)*2,(y-ry)*2))
    for r in geo['stairs']:
        x,y=r['position']
        if overlaps([x,y,48,48],region):
            px,py=(x-rx)*2,(y-ry)*2;ground.paste(under.crop((px,py,px+96,py+96)),(px,py));ground.alpha_composite(load(terrace/'stairs/maintained.png'),(px,py))
    ground_path=native(ground,'ground');layer={'id':'sanctuary_courtyard_hd','image':ground_path,'position':[rx,ry],'logical_size':[rw,rh],'artwork_pixels_per_world_pixel':2}
    data['ground_overlays']=[r for r in data.get('ground_overlays',[]) if r.get('id')!=layer['id']]+[layer]
    entities={r['id']:r for r in data['entities']};plant_pack=ROOT/'assets/terrain/vegetation_hd';plants={r['id']:r for r in read(plant_pack/'plants.json')['plants']}
    for name,plant in rec['vegetation'].items():
        r=plants[plant];entities[name].update(frames=['assets/terrain/vegetation_hd/'+f['file'] for f in r['frames']],artwork_pixels_per_world_pixel=2,logical_size=r['logical_size'],reduced_motion_frame=0)
    # Small props are registered from fresh full-resolution masters, not scaled legacy exports.
    er=exterior.recipe();sheet=load(SOURCE/'props_authored.png');props={}
    for name,r in rec['props'].items():
        col,row=r['cell'];w,h=r['logical_size'];raw=exterior.cutout(sheet,(col*sheet.width//3+4,row*sheet.height//2+4,(col+1)*sheet.width//3-4,(row+1)*sheet.height//2-4));raw.thumbnail((w*2-2,h*2-2),Image.Resampling.NEAREST);im=Image.new('RGBA',(w*2,h*2));im.alpha_composite(raw,((im.width-raw.width)//2,im.height-2-raw.height));props[name]=exterior.quantize(im,er)[0];native(props[name],'props/'+name)
    for name,prop in [('sanctuary.bench','bench'),('sanctuary.provision_basket','provision_basket')]:entities[name].update(frames=[PACK+'/props/'+prop+'.png'],artwork_pixels_per_world_pixel=2,logical_size=rec['props'][prop]['logical_size'])
    design=next(r for r in er['designs'] if r['id']=='sanctuary');sources={r['file']:load(exterior.SOURCE/r['file']) for r in er['sources']};sources['landmarks_authored.png']=load(SOURCE/'structure_authored.png');structure,windows=exterior.building_structure(design,sources,er);_,glyphs=exterior.effect_sources(sources,er)
    def building(tick,still=False):
        im=structure.copy()
        for x,y in rec['planters_world']:im.alpha_composite(props['herb_planter'],((x-252)*2,(y-84)*2))
        x,y=rec['lantern_local'];im.alpha_composite(props['lantern'],(x*2,y*2))
        x,y=rec['bell_local'];bell=props['bell'];fixed=4;dx=0 if still else (0,1,2,1,0,-1,-2,-1,0)[tick//3%9];im.alpha_composite(bell.crop((0,0,bell.width,fixed)),(x*2,y*2));im.alpha_composite(bell.crop((0,fixed,bell.width,bell.height)),(x*2+dx,y*2+fixed))
        if not still:
            im.alpha_composite(exterior.glow_layer(structure,windows,tick%18,er));im.alpha_composite(exterior.smoke_layer(design,tick%18,glyphs))
        return im
    host=entities['sanctuary'];host.update(frames=[native(building(t),'sanctuary/frame_'+f'{t:02}') for t in range(54)],artwork_pixels_per_world_pixel=2,logical_size=[216,216],reduced_motion_image=native(building(0,True),'sanctuary/reduced_motion'))
    door=next(r for r in data['doors'] if r['id']=='sanctuary');door.update(frames=[f'assets/terrain/eldenmere/exteriors_hd/buildings/sanctuary/doors/frame_{t:02}.png' for t in range(5)],artwork_pixels_per_world_pixel=2,logical_size=[32,42])
    # Keep every existing grass interaction, anchor and clock. Only scoped variants change.
    manifest=read(ROOT/rec['legacy_grass_manifest']);variants=manifest['tall_grass']['variants']
    for variant,plant in [('sparse_hd','grass_sparse'),('splayed_hd','grass_splayed'),('dense_hd','grass_dense')]:
        raw=load(plant_pack/plants[plant]['idle']);box=raw.getbbox();raw=raw.crop(box);raw.thumbnail((34,34),Image.Resampling.NEAREST);base=Image.new('RGBA',(48,64));base.alpha_composite(raw,((48-raw.width)//2,56-raw.height))
        def bend(amount,direction):
            im=Image.new('RGBA',base.size)
            # Each source row moves continuously; bottom root rows remain fixed.
            for y in range(64):
                row=base.crop((0,y,48,y+1));weight=max(0,min(1,(52-y)/30));shift=round(amount*weight)
                if direction in ('east','west'):im.alpha_composite(row,(shift*(1 if direction=='east' else -1),y))
                elif direction=='idle':im.alpha_composite(row,(shift,y))
                else:
                    flatten=.14 if direction=='north' else .24
                    yy=y+round(amount*flatten*weight)
                    im.alpha_composite(row.crop((0,0,24,1)),(-shift,yy));im.alpha_composite(row.crop((24,0,48,1)),(24+shift,yy))
            return im
        def pair(im,label):
            rear=im.copy();rear.paste((0,0,0,0),(0,46,48,64));front=im.copy();front.paste((0,0,0,0),(0,0,48,46));return {layer:native(pic,f'grass/{variant}/{label}_{layer}') for layer,pic in [('rear',rear),('front',front)]}
        variants[variant]={'artwork_pixels_per_world_pixel':2,'logical_size':[24,32],'idle':[{**pair(bend(amount,'idle'),f'idle_{i}'),'duration_ms':800} for i,amount in enumerate((0,1,1,0,-1,-1))],'parted':{direction:[pair(bend(strength*3,direction),f'{direction}_{strength}') for strength in range(3)] for direction in ('north','east','south','west')}}
    manifest_path=PACK+'/grass/manifest.json';out[manifest_path]=document(manifest);data['grass']['manifest']=manifest_path;mapping={'fan':'splayed_hd','slender':'sparse_hd','arching':'dense_hd','seeded':'dense_hd'};originals={r['id']:r for r in baseline['grass']['instances']}
    for r in data['grass']['instances']:
        if r['id'] in rec['grass_ids']:r['variant']=mapping[originals[r['id']]['variant']]
    data['pause_on_focus_loss']=True
    data['art_integrations']={**data.get('art_integrations',{}),'sanctuary_courtyard':{'recipe':str(SOURCE.relative_to(ROOT)/'recipe.json'),'region_logical':region,'density':2}}
    # Refresh only the scoped overview crop. All entity/door overhangs are replayed.
    overview=load(SOURCE/'overview_reference.png');crop=ground.resize((rw,rh),Image.Resampling.NEAREST)
    def generated(path):
        if path in out:
            from io import BytesIO
            return Image.open(BytesIO(out[path])).convert('RGBA')
        return load(ROOT/path)
    for e in sorted(data['entities'],key=lambda r:(r['sort_y'],r.get('sort_priority',0))):
        im=generated(e['frames'][e.get('phase_offset',0)%len(e['frames'])]);density=e.get('artwork_pixels_per_world_pixel',data.get('artwork_pixels_per_world_pixel',1))
        if density==2:im=im.resize(tuple(v//2 for v in im.size),Image.Resampling.NEAREST)
        x,y=e['position']
        if overlaps([x,y,*im.size],region):crop.alpha_composite(im,(x-rx,y-ry))
        for d in data['doors']:
            if d.get('host')==e['id']:
                im=generated(d['frames'][0]);im=im.resize(tuple(d.get('logical_size',im.size)),Image.Resampling.NEAREST);x,y=d['position'];crop.alpha_composite(im,(x-rx,y-ry))
    for r in data['grass']['instances']:
        x,y=r['position'];v=variants[r['variant']];phase=r.get('phase_ms',0)//800%len(v['idle']);frame=v['idle'][int(phase)]
        if overlaps([x-12,y-28,24,32],region):
            for layer in ('rear','front'):
                im=generated(frame[layer]).resize((24,32),Image.Resampling.NEAREST);crop.alpha_composite(im,(x-12-rx,y-28-ry))
    overview.paste(crop,(rx,ry));data['overview']=native(overview,'overview')
    out[rec['map']]=document(data);out[PACK+'/exports.json']=document({'builder':rec['builder'],'sources':rec['sources'],'exports':exports});return out

def build(check=False):
    result=products();stale=[]
    for path,raw in result.items():
        target=ROOT/path
        if not target.exists() or target.read_bytes()!=raw:
            stale.append(path)
            if not check:target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
    if check and stale:raise SystemExit('Stale courtyard integration: '+', '.join(stale))
    return result
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');args=parser.parse_args();print(f'{len(build(args.check))} courtyard exports '+('verified' if args.check else 'built'))
