"""Register authored wind-reaction drawings; no procedural pose deformation."""
from pathlib import Path
import sys
import hashlib
import json
import numpy as np
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
SOURCE=ROOT/'assets/source/cinematics/ice_reaper_duel/men'
TARGET=ROOT/'assets/story/ice_reaper_duel/men'
CANVAS=(128,128)
ANCHOR=(64,116)


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def register(tile,scale):
    tile=tile.convert('RGBA')
    tile.putalpha(tile.getchannel('A').point(lambda value:255 if value>=128 else 0))
    bounds=tile.getbbox()
    if bounds is None:raise ValueError('Empty authored action cell')
    pixels=np.asarray(tile)
    y0=max(bounds[1],bounds[3]-max(12,round((bounds[3]-bounds[1])*.15)))
    # Register the lower central boot/knee silhouette, excluding outward blades.
    x0=round(tile.width*.25);x1=round(tile.width*.75)
    band=pixels[y0:bounds[3],x0:x1]
    mask=band[:,:,3]>0
    orange=(band[:,:,0]>180)&(band[:,:,0]>band[:,:,1]*1.25)&(band[:,:,2]<110)
    ys,xs=np.where(mask&~orange)
    foot_x=float(np.median(xs+x0)) if len(xs) else (bounds[0]+bounds[2])*.5
    foot_y=bounds[3]-1
    resized=tile.resize((round(tile.width*scale),round(tile.height*scale)),Image.Resampling.NEAREST)
    offset=(round(ANCHOR[0]-foot_x*scale),round(ANCHOR[1]-foot_y*scale))
    frame=Image.new('RGBA',CANVAS)
    frame.alpha_composite(resized,offset)
    opaque=frame.getbbox()
    if opaque is None or opaque[0]<=0 or opaque[2]>=128 or opaque[1]<=0:
        raise ValueError('Authored action clips registered canvas')
    return frame,dict(scale=scale,source_content_bounds=list(bounds),foot=[foot_x,foot_y],offset=list(offset))


def extract(source,columns,rows,index):
    col,row=index%columns,index//columns
    bounds=(round(col*source.width/columns),round(row*source.height/rows),round((col+1)*source.width/columns),round((row+1)*source.height/rows))
    return source.crop(bounds),bounds


def _build_other_actors():
    source=SOURCE/'wind_men_generated.png';men=Image.open(source).convert('RGBA')
    side_source=SOURCE/'wind_right_generated.png';side=Image.open(side_source).convert('RGBA')
    left_source=SOURCE/'caelan_left_generated.png';left=Image.open(left_source).convert('RGBA')
    specs={'caelan':[(men,source,6,4,.38,'rear',list(range(6))),
                     (men,source,6,4,.38,'front',list(range(6,12))),
                     (side,side_source,6,3,.31,'right',list(range(6))),
                     (left,left_source,3,2,.203,'left',list(range(6)))],
           'lucan':[(men,source,6,4,.405,'rear',list(range(12,18))),
                    (men,source,6,4,.405,'front',list(range(18,24))),
                    (side,side_source,6,3,.31,'right',list(range(6,12)))]}
    summaries={}
    for actor,views in specs.items():
        folder=TARGET/actor;folder.mkdir(parents=True,exist_ok=True)
        animations={};records=[];board=Image.new('RGB',(128*6,152*len(views)),(18,27,39));draw=ImageDraw.Draw(board)
        for row,(sheet,path,columns,rows,scale,view,indices) in enumerate(views):
            frames=[]
            for phase,index in enumerate(indices):
                tile,bounds=extract(sheet,columns,rows,index);frame,registration=register(tile,scale)
                filename=f'{"brace" if actor=="mira" else "wind"}_{view}_{phase+1:02}.png'
                output=folder/filename;frame.save(output,optimize=True)
                frames.append(dict(file=filename,duration_ms=180 if actor=='mira' else 180))
                records.append(dict(file=filename,source=path.relative_to(ROOT).as_posix(),cell=index,source_bounds=list(bounds),sha256=digest(output),**registration))
                board.paste(frame,(phase*128,row*152),frame);draw.text((phase*128+4,row*152+130),f'{view} {phase+1}',fill='white')
            angle={'rear':180,'front':0,'right':90,'left':-90}[view]
            if actor=='caelan':
                # These filenames describe image-facing, not the viewer's
                # signed azimuth. Preserve the sword hand by registering views.
                angle=-angle
            base=dict(frames=frames,view_azimuth_deg=angle,loop=False)
            if actor=='mira':
                animations[f'brace_{view}']=base
                animations[f'react_{view}']=base
                animations[f'settle_{view}']=dict(frames=frames[-1:],view_azimuth_deg=angle,loop=True)
            else:
                animations[f'wind_{view}']=base
                for action,subset in (('wind_hit',frames[:2]),('wind_flight',frames[2:4]),('wind_land',frames[4:])):
                    animations[f'{action}_{view}']=dict(frames=subset,view_azimuth_deg=angle,loop=False)
                animations[f'settle_{view}']=dict(frames=frames[-1:],view_azimuth_deg=angle,loop=True)
        paths=sorted({str(entry[1].relative_to(ROOT)) for entry in views})
        manifest=dict(version=1,actor=actor,canvas=list(CANVAS),anchor=list(ANCHOR),body_pixels=82,animations=animations,
                      sources=[dict(file=p,sha256=digest(ROOT/p)) for p in paths],authored=True,
                      note='Complete authored full-body drawings; wind pose is six distinct drawings per view. Runtime owns translation, lift and cast shadows.')
        (folder/'animation.json').write_text(json.dumps(manifest,indent=2)+'\n')
        (folder/'provenance.json').write_text(json.dumps(dict(version=1,generated_with='image_gen',sources=manifest['sources'],
             operation='Equal-cell extraction, alpha threshold, fixed actor scale and foot/knee registration. No joint warping, mirrored weapons or generated in-between poses.',frames=records),indent=2)+'\n')
        board.save(folder/'contact_sheet.png',optimize=True)
        summaries[actor]=dict(drawings=len(records),actions=len(animations))
    print(json.dumps(summaries))


def build():
    result = _build_other_actors()
    from tools.build_mira_rig_continuity import build as rig_build
    rig_build()
    return result


if __name__=='__main__':build()
