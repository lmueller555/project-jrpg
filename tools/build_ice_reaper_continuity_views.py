"""Register authored continuity views and rear action drawings without pose deformation.

Only equal-cell extraction, alpha cleanup, palette registration and nearest-neighbor
scaling are performed. Each view and action frame has its own authored source cell.
"""
from __future__ import annotations
import hashlib
import json
import sys
from pathlib import Path
from statistics import median
from collections import deque
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
SOURCE=ROOT/'assets/source/cinematics/ice_reaper_continuity'
TARGET=ROOT/'assets/story/ice_reaper_continuity/actors'
VIEWS=('front','front_right','right','rear_right','rear','rear_left','left','front_left')
ANGLES=(0,45,90,135,180,-135,-90,-45)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def remove_detached_cell_bleed(image):
    """Drop only tiny residue or adjacent-cell fragments touching a gutter edge."""
    arr=np.array(image);mask=arr[:,:,3]>0;seen=np.zeros(mask.shape,dtype=bool);components=[]
    for y,x in zip(*np.nonzero(mask)):
        if seen[y,x]:continue
        queue=deque([(int(x),int(y))]);seen[y,x]=True;component=[]
        while queue:
            px,py=queue.popleft();component.append((px,py))
            for nx,ny in ((px-1,py),(px+1,py),(px,py-1),(px,py+1)):
                if 0<=nx<image.width and 0<=ny<image.height and mask[ny,nx] and not seen[ny,nx]:
                    seen[ny,nx]=True;queue.append((nx,ny))
        components.append(component)
    largest=max(map(len,components),default=0)
    for comp in components:
        touches=any(x in (0,image.width-1) or y in (0,image.height-1) for x,y in comp)
        if len(comp)<max(12,largest*.004) or (touches and len(comp)<largest*.1):
            for x,y in comp:arr[y,x,3]=0
    return Image.fromarray(arr)

def cells(name,columns,rows):
    path=SOURCE/name
    source=Image.open(path).convert('RGBA')
    result=[]
    for row in range(rows):
        for col in range(columns):
            box=(round(col*source.width/columns),round(row*source.height/rows),
                 round((col+1)*source.width/columns),round((row+1)*source.height/rows))
            image=source.crop(box)
            threshold=224 if name=='boss_views_generated.png' else 140
            image.putalpha(image.getchannel('A').point(lambda a:255 if a>=threshold else 0))
            image=remove_detached_cell_bleed(image)
            if not image.getbbox():
                raise ValueError(f'Empty cell {name}:{row},{col}')
            result.append((image,box))
    return result

def register(image,scale,canvas,anchor):
    bounds=image.getbbox();arr=np.asarray(image)
    lower=arr[max(bounds[1],bounds[3]-round((bounds[3]-bounds[1])*.18)):bounds[3],:,:]
    mask=(lower[:,:,3]>0)&~((lower[:,:,0]>180)&(lower[:,:,0]>lower[:,:,1]*1.3)&(lower[:,:,2]<110))
    xs=np.nonzero(mask)[1]
    foot_x=float(np.median(xs)) if len(xs) else (bounds[0]+bounds[2])/2
    # Keep a blade/staff fully visible without changing the authored body.
    foot_x=max(bounds[2]-(canvas[0]-anchor[0]-1)/scale,
               min(bounds[0]+(anchor[0]-1)/scale,foot_x))
    cropped=image.crop(bounds)
    resized=cropped.resize((max(1,round(cropped.width*scale)),max(1,round(cropped.height*scale))),Image.Resampling.NEAREST)
    x=round(anchor[0]-(foot_x-bounds[0])*scale);y=anchor[1]-resized.height
    if x<0 or x+resized.width>canvas[0] or y<0:
        raise ValueError(f'Clipped view {bounds}, {scale}, {resized.size}, {(x,y)}')
    # Pixel palette preserves alpha and hard pixel boundaries.
    alpha=resized.getchannel('A')
    resized=resized.convert('RGB').quantize(colors=192,dither=Image.Dither.NONE).convert('RGBA')
    resized.putalpha(alpha)
    frame=Image.new('RGBA',canvas);frame.alpha_composite(resized,(x,y))
    return frame,dict(source_content_bounds=list(bounds),scale=scale,foot_source_x=foot_x,registration=[x,y])

def build():
    atlases={
      'men':cells('men_views_generated.png',8,2),
      'women':cells('women_views_generated.png',8,3),
      'boss':cells('boss_views_generated.png',4,2),
      'rear':cells('rear_actions_generated.png',8,3),
      'actions':cells('rescue_actions_generated.png',6,4),
      'impact':cells('lucan_impact_generated.png',6,1),
      'overhead':cells('lucan_overhead_left_generated.png',8,2),
      'quarter':cells('front_right_corrections_generated.png',1,3),
    }
    sources={k:v for k,v in [('men','men_views_generated.png'),('women','women_views_generated.png'),('boss','boss_views_generated.png'),('rear','rear_actions_generated.png'),('actions','rescue_actions_generated.png'),('impact','lucan_impact_generated.png'),('overhead','lucan_overhead_left_generated.png'),('quarter','front_right_corrections_generated.png')]}
    manifests={};provenance={}
    def init(actor):
        if actor not in manifests:
            boss=actor=='ice_reaper'
            manifests[actor]=dict(version=1,actor=actor,canvas=[192,192] if boss else [128,128],anchor=[96,172] if boss else [64,116],animations={},authored=True,source_art_review='awaiting_user_review')
            provenance[actor]=[]
        return manifests[actor]
    def export(actor,key,atlas,indices,height,angle,*,duration=200,held=False):
        m=init(actor);directory=TARGET/actor;directory.mkdir(parents=True,exist_ok=True)
        selected=[atlases[atlas][i] for i in indices]
        natural_heights=[im.getbbox()[3]-im.getbbox()[1] for im,_ in selected]
        scale=height/median(natural_heights)
        maxw=max(im.getbbox()[2]-im.getbbox()[0] for im,_ in selected)
        scale=min(scale,(m['canvas'][0]-4)/maxw)
        frames=[]
        for index,(image,box) in enumerate(selected,1):
            frame,registration=register(image,scale,tuple(m['canvas']),tuple(m['anchor']))
            file=f'{key}_{index:02}.png';frame.save(directory/file,optimize=True)
            frames.append(dict(file=file,duration_ms=duration))
            provenance[actor].append(dict(file=file,source=sources[atlas],source_cell=indices[index-1],source_box=list(box),sha256=sha(directory/file),**registration))
        m['animations'][key]=dict(frames=frames,view_azimuth_deg=angle,held_view=held,loop=held)
    # Held directions preserve pose, equipment hand, and foot registration.
    for view,angle,col in zip(VIEWS,ANGLES,range(8)):
        export('caelan','ready_'+view,'men',[col],71,angle,held=True)
        # Lucan's held atlas uses the opposite authored view sign to the stage.
        export('lucan','hold_brace_'+view,'men',[8+col],68,-angle,held=True)
        export('mira','aim_'+view,'quarter' if col==1 else 'women',[0] if col==1 else [col],84,angle,held=True)
        export('rhea','frozen_'+view,'quarter' if col==1 else 'women',[1] if col==1 else [8+col],81,angle,held=True)
        export('rhea','release_'+view,'quarter' if col==1 else 'women',[2] if col==1 else [16+col],81,angle,held=True)
        export('ice_reaper','ready_'+view,'boss',[(-col)%8],145,angle,held=True)
    # Exact rescue camera directions, preserving 4–10 authored action drawings.
    export('caelan','dash_rear','rear',list(range(6)),71,160,duration=80)
    export('lucan','dash_rear','rear',list(range(8,14)),68,160,duration=80)
    export('lucan','brace_rear_left','overhead',list(range(8)),80,-120,duration=180)
    export('caelan','slash_rear_right','actions',[0,1,2,3,4,6,7,8,10,11],78,150,duration=165)
    export('caelan','land_rear_right','actions',[12,13,15,17],71,150,duration=137)
    export('lucan','impact_rear_left','overhead',list(range(8,14)),80,-110,duration=117)
    for actor,m in manifests.items():
        directory=TARGET/actor
        (directory/'animation.json').write_text(json.dumps(m,indent=2)+'\n')
        record=dict(version=1,operation='Authored equal-cell extraction, alpha threshold, palette registration, nearest scaling and foot anchoring only; no mirrored equipment, pose deformation or synthetic in-betweens.',sources={name:sha(SOURCE/name) for name in sources.values()},frames=provenance[actor])
        (directory/'provenance.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps({actor:sum(len(a['frames']) for a in m['animations'].values()) for actor,m in manifests.items()}))
    # Keep the user-requested enemy-facing guard when rebuilding the atlas.
    from tools.build_lucan_guard_correction import build as correct_lucan_guard
    correct_lucan_guard()

if __name__=='__main__':
    build()
