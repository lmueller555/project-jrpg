"""Register Caelan's authored overworld drawings; preserve scale and game cadence.

The source atlases are retained unchanged. Export isolates connected hard alpha,
reduces with nearest sampling at one scale per atlas, and registers complete
silhouettes. The native contour pass inks the silhouette edge without changing
anatomy, interior shading or alpha.
"""
from __future__ import annotations

import argparse
from functools import lru_cache
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import sys

from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from tools.build_mira_combat import _main_component
from tools.caelan_outline import apply_outline, STYLE

SOURCE=ROOT/'assets/source/characters/caelan/overworld_refresh'
BASE='assets/characters/caelan'
DIRECTIONS=('front','back','left','right')
TRAVEL_EDGES=(0,221,425,631,834,1035,1237,1441,1647,1882)
ACTION_EDGES=(0,245,448,704,939,1158,1370,1605,1882)
TRAVEL_SCALE=34/197.5
ACTION_SCALE=34/224


def encoded(image):
    stream=BytesIO();image.save(stream,format='PNG',optimize=True);return stream.getvalue()


@lru_cache(maxsize=2)
def _atlas(name,mtime_ns,size):return Image.open(SOURCE/name).convert('RGBA')

def atlas(name):
    stat=(SOURCE/name).stat()
    return _atlas(name,stat.st_mtime_ns,stat.st_size)


def drawing(index, *, actions=False):
    name='actions_authored.png' if actions else 'travel_authored.png'
    sheet=atlas(name);edges=ACTION_EDGES if actions else TRAVEL_EDGES
    col,row=index%4,index//4
    rect=(round(col*sheet.width/4),edges[row],round((col+1)*sheet.width/4),edges[row+1])
    cell=_main_component(sheet.crop(rect));bounds=cell.getbbox()
    return cell,bounds,rect


def registered(index, *, actions=False, canvas=(24,36), anchor=(12,34), flight=False):
    cell,bounds,rect=drawing(index,actions=actions)
    scale=ACTION_SCALE if actions else TRAVEL_SCALE
    crop=cell.crop(bounds)
    resized=crop.resize((round(crop.width*scale),round(crop.height*scale)),Image.Resampling.NEAREST)
    # The midpoint of the boot support keeps the existing foot registration.
    low=max(bounds[1],bounds[3]-max(10,round(crop.height*.12)))
    contacts=[x for y in range(low,bounds[3]) for x in range(bounds[0],bounds[2]) if cell.getpixel((x,y))[3]]
    foot=(min(contacts)+max(contacts))/2
    if flight:foot=(bounds[0]+bounds[2]-1)/2
    x=round(anchor[0]-(foot-bounds[0])*scale)
    x=max(1,min(x,canvas[0]-resized.width-1))
    y=anchor[1]+1-resized.height-(3 if flight else 0)
    if x<0 or y<0 or x+resized.width>canvas[0] or y+resized.height>canvas[1]:
        raise ValueError(('Caelan drawing would clip',index,actions,canvas,(x,y),resized.size))
    image=Image.new('RGBA',canvas);image.alpha_composite(resized,(x,y))
    return apply_outline(image),dict(source_rect=[rect[0],rect[1],rect[2]-rect[0],rect[3]-rect[1]],
                      source_bounds=list(bounds),scale=scale,canvas=list(canvas),
                      foot_anchor=list(anchor),destination=[x,y])


def action_frame(index,canvas=(24,36),anchor=(12,34)):
    return registered(index,actions=True,canvas=canvas,anchor=anchor)[0]


def products():
    result={};records=[];frames={}
    for index in range(36):
        if index<4:
            direction=DIRECTIONS[index];gait='idle';phase=0
            file=f'{BASE}/idle_{direction}.png'
        else:
            row=(index-4)//4
            gait='walk' if row<4 else 'run';direction=DIRECTIONS[row%4];phase=index%4
            file=f'{BASE}/{gait}_{direction}/frame_{phase+1:02}.png'
        flight=gait=='run' and phase%2==1
        image,record=registered(index,flight=flight)
        record.update(file=file,index=index,direction=direction,gait=gait,phase=phase)
        result[file]=encoded(image);records.append(record);frames[(gait,direction,phase)]=image
    for gait in ('walk','run'):
        for direction in DIRECTIONS:
            strip=Image.new('RGBA',(96,36))
            for phase in range(4):strip.alpha_composite(frames[(gait,direction,phase)],(phase*24,0))
            folder=f'{BASE}/{gait}_{direction}'
            result[folder+'/spritesheet.png']=encoded(strip)
            meta=dict(character='caelan',animation=gait+'.'+direction,status='review',
                      frame_size=[24,36],foot_anchor=[12,34],loop=True,image='spritesheet.png',
                      source='assets/source/characters/caelan/overworld_refresh/travel_authored.png',
                      frames=[dict(file=f'frame_{p+1:02}.png',rect=[p*24,0,24,36],
                                   duration_ms=140 if gait=='walk' else 100,
                                   phase=('contact_a','passing_a','contact_b','passing_b')[p] if gait=='walk'
                                         else ('contact_a','flight_a','contact_b','flight_b')[p],
                                   airborne=gait=='run' and p%2==1) for p in range(4)])
            result[folder+'/animation.json']=(json.dumps(meta,indent=2)+'\n').encode()
    idle=Image.new('RGBA',(96,36));walk=Image.new('RGBA',(96,144))
    for i,direction in enumerate(('front','left','right','back')):
        idle.alpha_composite(frames[('idle',direction,0)],(i*24,0))
        for p in range(4):walk.alpha_composite(frames[('walk',direction,p)],(p*24,i*36))
    result[BASE+'/idle_directions.png']=encoded(idle)
    result[BASE+'/walk_directions.png']=encoded(walk)
    for name in ('idle_directions.json','walk_directions.json'):
        meta=json.loads((ROOT/BASE/name).read_text())
        def status(data):
            if isinstance(data,dict):
                for key,value in data.items():
                    if key=='status':data[key]='review'
                    else:status(value)
            elif isinstance(data,list):
                for value in data:status(value)
        status(meta)
        meta['source']='assets/source/characters/caelan/overworld_refresh/travel_authored.png'
        result[BASE+'/'+name]=(json.dumps(meta,indent=2)+'\n').encode()
    reg=dict(version=1,status='review',outline=STYLE,source='assets/source/characters/caelan/overworld_refresh/travel_authored.png',
             source_sha256=sha256((SOURCE/'travel_authored.png').read_bytes()).hexdigest(),
             source_cells=records,action_source='assets/source/characters/caelan/overworld_refresh/actions_authored.png',
             action_source_sha256=sha256((SOURCE/'actions_authored.png').read_bytes()).hexdigest(),
             action_scale=ACTION_SCALE,action_row_edges=list(ACTION_EDGES))
    result['assets/source/characters/caelan/overworld_refresh/registration.json']=(json.dumps(reg,indent=2)+'\n').encode()
    from tools.build_caelan_overworld_dependents import products as dependent_products
    result.update(dependent_products())
    return result


def build(check=False):
    result=products();changed=[]
    for name,raw in result.items():
        path=ROOT/name
        if not path.exists() or path.read_bytes()!=raw:
            changed.append(name)
            if not check:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    if check and changed:raise SystemExit('Stale Caelan exports: '+', '.join(changed))
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true')
    args=parser.parse_args();print(f'{len(build(args.check))} Caelan exports verified' if args.check else f'{len(build())} Caelan exports built')
