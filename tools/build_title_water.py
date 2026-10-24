"""Build registered, hard-alpha water animation from the approved title art.

Only pixels inside authored water polygons and the water-color selection may
change. Flow phases travel downstream; all non-water illustration pixels stay
in the original background. NumPy/Pillow are asset-build dependencies only.
"""
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'assets/source/ui/title/water'
OUTPUT=ROOT/'assets/ui/title/water'


def build():
    recipe=json.loads((SOURCE/'recipe.json').read_text())
    background=ROOT/'assets/ui/title/eldenmere_dawn.png'
    original=Image.open(background).convert('RGB')
    rgb=np.asarray(original).astype(np.float32)
    r,g,b=rgb[:,:,0],rgb[:,:,1],rgb[:,:,2]
    cool=(b>r*.93)&(b>g*.79)
    foam=(r>158)&(g>170)&(b>154)&(np.maximum.reduce((r,g,b))-np.minimum.reduce((r,g,b))<65)
    warm=(r>145)&(g>125)&(b>65)&(r<g*1.5)
    exclusions=Image.new('L',original.size)
    draw=ImageDraw.Draw(exclusions)
    for polygon in recipe['exclude']:draw.polygon([tuple(p) for p in polygon],fill=255)
    excluded=np.asarray(exclusions)>0
    regions=[]
    union=np.zeros((original.height,original.width),dtype=bool)
    OUTPUT.mkdir(parents=True,exist_ok=True)
    for region in recipe['regions']:
        outline=Image.new('L',original.size)
        draw=ImageDraw.Draw(outline)
        for polygon in region['polygons']:draw.polygon([tuple(p) for p in polygon],fill=255)
        selection=(cool|foam|(warm if region.get('warm_reflections') else False))
        mask=(np.asarray(outline)>0)&selection&~excluded
        # A region's pixels have a single clock, even at neighboring boundaries.
        mask &= ~union
        union |= mask
        regions.append((region,mask))
        Image.fromarray((mask*255).astype('uint8')).save(OUTPUT/(region['id']+'_mask.png'))
    mask_image=Image.fromarray((union*255).astype('uint8'))
    mask_image.save(OUTPUT/'mask.png')
    bbox=mask_image.getbbox()
    yy,xx=np.mgrid[0:original.height,0:original.width]
    records=[]
    for index in range(recipe['frame_count']):
        output=rgb.copy()
        phase=index/recipe['frame_count']
        for region,mask in regions:
            dx,dy=region['flow']
            travel=xx*dx+yy*dy
            angle=2*np.pi*(travel/9-phase*region['cycles'])
            detail=2*np.pi*(xx/13+yy/4-phase*region['cycles'])
            change=region['amplitude']*(.7*np.sin(angle)+.3*np.sin(detail))
            local=(phase*region['cycles'])%1
            source_x=np.clip(np.round(xx-dx*local*3).astype(int),0,original.width-1)
            source_y=np.clip(np.round(yy-dy*local*3).astype(int),0,original.height-1)
            valid=mask&mask[source_y,source_x]
            reflected=rgb.copy()
            mix=.24*np.sin(local*np.pi)**2
            reflected[valid]=rgb[valid]*(1-mix)+rgb[source_y[valid],source_x[valid]]*mix
            # Change complete water regions, with blue-green reflection shifts.
            color_change=np.stack((change*.7,change*.91,change),axis=2)
            output[mask]=np.clip(reflected[mask]+color_change[mask],0,255)
        rgba=np.zeros((original.height,original.width,4),dtype='uint8')
        rgba[:,:,:3]=np.round(output).astype('uint8')
        rgba[:,:,3]=(union*255).astype('uint8')
        frame=Image.fromarray(rgba).crop(bbox)
        name=f'frame_{index+1:02}.png'
        frame.save(OUTPUT/name)
        records.append({'file':name,'duration_ms':recipe['loop_ms']//recipe['frame_count']})
    manifest={'position':list(bbox[:2]),'size':[bbox[2]-bbox[0],bbox[3]-bbox[1]],
              'canvas_size':list(original.size),'loop_ms':recipe['loop_ms'],
              'source_sha256':hashlib.sha256(background.read_bytes()).hexdigest(),
              'mask':'mask.png','regions':[{**region,'pixel_count':int(mask.sum())} for region,mask in regions],
              'frames':records}
    (OUTPUT/'animation.json').write_text(json.dumps(manifest,indent=2)+'\n')
    # Diagnostic mask overlay, never loaded as game art.
    overlay=original.convert('RGBA')
    ink=Image.new('RGBA',original.size,'#e052b6')
    ink.putalpha(mask_image.point(lambda value:round(value*.6)))
    overlay.alpha_composite(ink)
    overlay.resize((1280,720),Image.Resampling.NEAREST).save('/tmp/title-water-mask-review.png')
    print('Built',len(records),'water frames;',int(union.sum()),'registered water pixels')


if __name__=='__main__':build()
