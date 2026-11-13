"""Register authored rescue bodies at fixed scale; reuse existing prop drawings.

No body parts are stretched or interpolated. Retained atlases supply
all joint changes. Source alpha is hardened before nearest-neighbour reduction.
Caelan's row receives the shared native contour pass after registration.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
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
SOURCE=ROOT/'assets/source/story/sanctuary_rescue'
BASE='assets/story/sanctuary_rescue'
DIRECTIONS=('front','back','left','right')
ANCHOR=[20,34]


def encoded(image):
    stream=BytesIO();image.save(stream,format='PNG',optimize=True);return stream.getvalue()


def products():
    result={};registration=[]
    def export(path,image):
        result[path]=encoded(image)
        return path
    def authored(name,row,col,rows,scale,path):
        with Image.open(SOURCE/name) as raw:sheet=raw.convert('RGBA')
        rect=(round(col*sheet.width/4),round(row*sheet.height/rows),round((col+1)*sheet.width/4),round((row+1)*sheet.height/rows))
        cell=_main_component(sheet.crop(rect));bounds=cell.getbbox();crop=cell.crop(bounds)
        body=crop.resize((round(crop.width*scale),round(crop.height*scale)),Image.Resampling.NEAREST)
        x=20-round(body.width/2);y=39-body.height
        if x<0 or y<0 or x+body.width>40:raise ValueError(('Rescue art clipping',name,row,col,body.size))
        image=Image.new('RGBA',(40,40));image.alpha_composite(body,(x,y))
        if name=='actions_authored.png' and row==5:image=apply_outline(image)
        registration.append(dict(file=path,source=name,source_rect=list(rect),source_bounds=list(bounds),scale=scale,destination=[x,y],canvas=[40,40],draw_anchor=ANCHOR))
        return export(path,image)
    action=[]
    scales=[34/223,34/223,34/223,34/221,34/224,34/229]
    for row in range(6):
        action.append([authored('actions_authored.png',row,col,6,scales[row],f'{BASE}/actions/row_{row}_{col}.png') for col in range(4)])
    def animation(files,duration=260,loop=False):
        return dict(frames=[dict(file=path,duration_ms=duration) for path in files],anchor=ANCHOR,loop=loop)
    def standard(key):
        folder=f'assets/characters/{key}'
        return dict(anchor=[12,30],frame_size=[24,36],idles={d:f'{folder}/idle_{d}.png' for d in DIRECTIONS},walks={d:[dict(file=f'{folder}/walk_{d}/frame_{p:02}.png',duration_ms=140) for p in range(1,5)] for d in DIRECTIONS},poses={})
    actors={key:standard(key) for key in ('mira','lucan','caelan')}
    arrival_path='assets/story/sanctuary_arrival/art.json'
    arrival=json.loads((ROOT/arrival_path).read_text())
    caretaker=deepcopy(arrival['actors']['caretaker'])
    receive=deepcopy(caretaker['poses']['unhook'])
    receive['frames']=receive['frames'][2:10]
    for frame in receive['frames']:frame['duration_ms']=200
    caretaker['poses']={'receive':receive}
    actors['caretaker']=caretaker
    actors['worker']=dict(anchor=ANCHOR,frame_size=[40,40],idles={},walks={},poses={})
    for key,filename,scale in [('worker','worker_supported_authored.png',34/260),('lucan','lucan_supported_authored.png',34/236)]:
        bank={};idles={}
        for row,direction in enumerate(DIRECTIONS):
            files=[authored(filename,row,col,4,scale,f'{BASE}/{key}/supported_{direction}_{col}.png') for col in range(4)]
            bank[direction]=[dict(file=path,duration_ms=220) for path in files];idles[direction]=files[0]
        if key=='worker':actors[key]['walks']=bank;actors[key]['idles']=idles
        else:
            actors[key]['supported_walks']=bank;actors[key]['supported_idles']=idles;actors[key]['supported_anchor']=ANCHOR
    actors['worker']['poses']={'pinned':animation(action[0][:2],500,True),'seated':animation([action[0][3]],1000),'rise':animation(action[1],300),'supported':animation([action[1][3]],1000)}
    actors['lucan']['poses']={'brace':animation(action[3][:2],350),'lift':animation(action[3],650)}
    actors['mira']['poses']={'kneel':animation([action[4][0]],1000),'tool':animation(action[4],650),'treat':animation(action[4]+list(reversed(action[4])),400)}
    actors['caelan']['poses']={'assist':animation(action[5],320)}
    slab='assets/terrain/limestone_cave/geology/modules/slab/fallen/0.png'
    tool='assets/story/mill/poses/mira_tool.png'
    linen='assets/story/sanctuary_arrival/performance/linen.png'
    with Image.open(ROOT/slab) as image:rock=image.convert('RGBA').resize((36,24),Image.Resampling.NEAREST)
    rock_file=export(BASE+'/props/rock.png',rock)
    with Image.open(ROOT/tool) as image:pry=image.convert('RGBA').crop((24,74,31,79))
    tool_file=export(BASE+'/props/tool.png',pry)
    props={'rock':dict(file=rock_file,anchor=[18,20]),'tool':dict(file=tool_file,anchor=[3,3]),'dressing':dict(file=linen,anchor=[6,7])}
    sources={name:sha256((SOURCE/name).read_bytes()).hexdigest() for name in ('actions_authored.png','worker_supported_authored.png','lucan_supported_authored.png')}
    manifest=dict(version=1,status='review',caelan_outline=STYLE,actors=actors,props=props,source_sha256=sources,
        prop_sources={path:sha256((ROOT/path).read_bytes()).hexdigest() for path in (slab,tool,linen,arrival_path)},
        registration='assets/source/story/sanctuary_rescue/registration.json')
    result[BASE+'/art.json']=(json.dumps(manifest,indent=2)+'\n').encode()
    result['assets/source/story/sanctuary_rescue/registration.json']=(json.dumps(dict(version=1,sources=sources,frames=registration),indent=2)+'\n').encode()
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');args=parser.parse_args()
    result=products();stale=[]
    for name,raw in result.items():
        path=ROOT/name
        if not path.exists() or path.read_bytes()!=raw:
            stale.append(name)
            if not args.check:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    if args.check and stale:raise SystemExit('Stale rescue exports: '+', '.join(stale))
    print(('Verified' if args.check else 'Built')+f' {len(result)} rescue artifacts')

if __name__=='__main__':main()
