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



if __name__=='__main__':
    raise SystemExit('The 1x travel exporter is retired. Use tools/export_caelan_*_hd.py; this module retains only source registration for unique story/action recipes.')
