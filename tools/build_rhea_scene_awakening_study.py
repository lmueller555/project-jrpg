"""Extract authored tiny expressions into the unchanged full-body scene sprite.

No facial features are painted or deformed by this script. The eight facial
expressions are authored in expressions_generated.png with image_gen. Equal-cell
extraction, nearest sampling, palette registration, and a fixed facial mask are
the only operations applied. Existing scene/body assets are never overwritten.
"""
from pathlib import Path
import hashlib
import json

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/story/ice_reaper_continuity/actors/rhea/frozen_front_01.png'
ART = ROOT/'assets/source/cinematics/rhea_scene_awakening_study'
OUTPUT = ROOT/'assets/story/rhea_scene_awakening_study'
NAMES = ('neutral_closed','strain_begin','strain_mid','strain_peak',
         'opening_01','opening_02','angry_open','angry_hold')
TIMES = (0.,.45,.75,1.03,1.3,1.43,1.57,1.8)
OPENNESS = (0.,0.,0.,0.,.25,.6,1.,1.)
# A fixed facial-feature mask; silhouette, hair, neck, clothing and staff remain
# exactly the original source pixels. Values are inclusive native coordinates.
MASK_ROWS = {44:(59,64),45:(58,64),46:(58,64),47:(58,64),48:(59,64),
             49:(60,63),50:(60,63)}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build():
    (OUTPUT/'frames').mkdir(parents=True,exist_ok=True)
    source=Image.open(SOURCE).convert('RGBA')
    base=np.asarray(source).copy()
    generated=Image.open(ART/'expressions_generated.png').convert('RGB')
    if generated.size!=(1536,1024):
        raise ValueError('Authored expression sheet must retain its reference grid')
    palette=np.unique(base[base[:,:,3]>0,:3].reshape(-1,3),axis=0).astype(np.int32)
    mask=np.zeros((128,128),bool)
    for y,(left,right) in MASK_ROWS.items(): mask[y,left:right+1]=True
    frames={};verification={}
    review=Image.new('RGB',(128*4*3,154*2*3),(17,26,36))
    labels=ImageDraw.Draw(review)
    for index,name in enumerate(NAMES):
        cx=index%4*384;cy=index//4*512
        # The authored native face patch is 17x18, enlarged16x on the grid.
        patch=generated.crop((cx+56,cy+112,cx+328,cy+400)).resize((17,18),Image.Resampling.NEAREST)
        pixels=np.asarray(patch).astype(np.int32)
        distance=((pixels[:,:,None,:]-palette[None,None,:,:])**2).sum(axis=3)
        registered=palette[distance.argmin(axis=2)].astype(np.uint8)
        result=base.copy()
        for y,x in zip(*np.where(mask)):
            # The authored features sit one native pixel lower than the source;
            # integer translation registers lids and pupils with the scene eyes.
            result[y,x,:3]=registered[y-39+1,x-49]
        if not np.array_equal(result[~mask],base[~mask]):
            raise AssertionError('Expression altered a protected source pixel')
        path=OUTPUT/'frames'/f'{name}.png'
        frame=Image.fromarray(result,'RGBA');frame.save(path,optimize=True)
        frames[name]=dict(file=f'frames/{name}.png',eyes=[[59.5,46.0],[63.5,46.0]],
                          openness=OPENNESS[index],start=TIMES[index])
        verification[name]=dict(sha256=digest(path),changed_pixels=int(np.any(result!=base,axis=2).sum()),
                                protected_pixels_unchanged=True)
        x=index%4*384;y=index//4*462
        review.paste(frame.resize((384,384),Image.Resampling.NEAREST),(x,y),frame.resize((384,384),Image.Resampling.NEAREST))
        labels.text((x+8,y+392),name,fill='white')
    manifest=dict(version=1,actor='rhea',purpose='Full-body scene-sprite awakening for the Ice Reaper cinematic',
                  canvas=[128,128],anchor=[64,116],body_pixels=82,
                  source=SOURCE.relative_to(ROOT).as_posix(),source_sha256=digest(SOURCE),
                  frames=frames,sequence=list(NAMES),shatter_at=2.2,
                  protected=dict(body=True,hair=True,staff=True,clothing=True,original_alpha=True),
                  facial_mask_rows={str(y):list(bounds) for y,bounds in MASK_ROWS.items()},
                  registration=dict(native_source_crop=[49,39,66,57],source_grid=[4,2],
                                    cell=[384,512],crop_in_cell=[56,112,328,400],
                                    integer_translation=[0,-1],method='nearest extraction; source-palette nearest-color registration'),
                  authored=dict(tool='image_gen',sheet=(ART/'expressions_generated.png').relative_to(ROOT).as_posix(),
                                sha256=digest(ART/'expressions_generated.png'),
                                prompt=(ART/'expressions_prompt.txt').relative_to(ROOT).as_posix()),
                  verification=verification)
    (OUTPUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    review.save(OUTPUT/'expressions_contact_sheet.png',optimize=True)
    print(json.dumps(dict(frames=len(frames),protected_pixels_unchanged=True,source_unchanged=digest(SOURCE)==manifest['source_sha256'])))


if __name__=='__main__':build()
