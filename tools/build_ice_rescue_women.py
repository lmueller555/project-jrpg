"""Mechanically register authored Mira/Rhea rescue sheets; no pose deformation."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
SOURCE=ROOT/'assets/source/cinematics/ice_reaper_rescue/women'
TARGET=ROOT/'assets/story/ice_reaper_rescue'

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def clean(image):
    image=image.convert('RGBA')
    alpha=image.getchannel('A').point(lambda value:255 if value>=140 else 0)
    result=image.convert('RGB').quantize(colors=128,dither=Image.Dither.NONE).convert('RGBA')
    result.putalpha(alpha)
    return result

def export_sheet(actor,columns,rows,groups,scale):
    source=SOURCE/f'{actor}_actions_generated.png'
    image=Image.open(source).convert('RGBA')
    directory=TARGET/'actors'/actor
    directory.mkdir(parents=True,exist_ok=True)
    animations={};records=[]
    for key,indices in groups.items():
        frames=[]
        for index,cell in enumerate(indices,1):
            col,row=cell%columns,cell//columns
            bounds=(round(col*image.width/columns),round(row*image.height/rows),round((col+1)*image.width/columns),round((row+1)*image.height/rows))
            tile=clean(image.crop(bounds));bbox=tile.getbbox()
            if bbox is None: raise ValueError(f'Empty authored cell {actor}:{cell}')
            tile=tile.crop(bbox)
            closeup=key in ('eyes','loading_detail')
            fit=min(124/tile.width,120/tile.height) if closeup else scale
            tile=tile.resize((max(1,round(tile.width*fit)),max(1,round(tile.height*fit))),Image.Resampling.NEAREST)
            if tile.width>128 or tile.height>(128 if closeup else 116):raise ValueError(f'Authored pose exceeds registered canvas {actor}:{cell}')
            registered=Image.new('RGBA',(128,128))
            offset=((128-tile.width)//2,(128-tile.height)//2 if closeup else 116-tile.height)
            registered.alpha_composite(tile,offset)
            filename=f'{key}_{index:02}.png'
            registered.save(directory/filename,optimize=True)
            frames.append(dict(file=filename,duration_ms=90 if actor=='mira' else 100))
            records.append(dict(file=filename,cell=cell,source_bounds=list(bounds),source_content_bounds=list(bbox),scale=fit,offset=list(offset),sha256=sha(directory/filename)))
        animations[key]=dict(frames=frames,closeup=key in ('eyes','loading_detail'))
    manifest=dict(version=1,actor=actor,canvas=[128,128],anchor=[64,116],animations=animations,source=source.relative_to(ROOT).as_posix(),source_sha256=sha(source),authored=True)
    (directory/'animation.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (directory/'provenance.json').write_text(json.dumps(dict(source=manifest['source'],source_sha256=sha(source),operation='Equal-cell extraction, alpha threshold, pixel palette registration, nearest scaling and foot registration only; every pose is separately authored.',frames=records),indent=2)+'\n')
    return records

def _build_other_actors():
    mira=[]
    rhea=export_sheet('rhea',4,4,{'release':list(range(8)),'release_rear':list(range(12,16))},.29)
    scope=clean(Image.open(SOURCE/'launcher_scope_generated.png')).resize((480,320),Image.Resampling.NEAREST)
    props=TARGET/'props';props.mkdir(parents=True,exist_ok=True)
    scope.save(props/'launcher_scope.png',optimize=True)
    (props/'launcher_scope.json').write_text(json.dumps(dict(canvas=[480,320],scope_center=[240,125],source='assets/source/cinematics/ice_reaper_rescue/women/launcher_scope_generated.png',source_sha256=sha(SOURCE/'launcher_scope_generated.png'),transparent_center=True),indent=2)+'\n')
    print(json.dumps(dict(mira_frames=len(mira),rhea_frames=len(rhea),scope=[480,320])))

def build():
    result = _build_other_actors()
    from tools.build_mira_rig_continuity import build as rig_build
    rig_build()
    return result


if __name__=='__main__':build()
