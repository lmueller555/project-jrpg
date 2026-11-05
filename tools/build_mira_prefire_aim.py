"""Register Mira's authored pre-fire lift between existing approved endpoints.

Only source-cell extraction, palette/alpha cleanup, nearest sampling and foot
registration are applied. The firing and subsequent artwork are never changed.
"""
from pathlib import Path
import hashlib
import json

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/cinematics/mira_prefire_aim/raise_generated.png'
OUT = ROOT/'assets/story/mira_prefire_aim'
START = ROOT/'assets/story/ice_reaper_rescue/actors/mira/load_08.png'
END = ROOT/'assets/story/ice_reaper_continuity/actors/mira/aim_front_01.png'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def foot_center(image):
    pixels = np.asarray(image)
    rows = np.flatnonzero((pixels[:,:,3]>0).any(axis=1))
    bottom = int(rows[-1])
    ys,xs = np.where((pixels[:,:,3]>0) & (np.indices(pixels.shape[:2])[0]>=bottom-5))
    return float((xs.min()+xs.max())/2), bottom


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    sheet = Image.open(SOURCE).convert('RGBA')
    first = Image.open(START).convert('RGBA')
    last = Image.open(END).convert('RGBA')
    frames = [first]
    start_x,_ = foot_center(first)
    end_x,_ = foot_center(last)
    registration = []
    for cell,index in ((1,1),(2,2)):
        col,row = cell%2,cell//2
        box = (round(col*sheet.width/2),round(row*sheet.height/2),
               round((col+1)*sheet.width/2),round((row+1)*sheet.height/2))
        image = sheet.crop(box)
        rgba = np.array(image)
        alpha = rgba[:,:,3] >= 140
        rgb = rgba[:,:,:3].astype(float)
        # Remove only the saturated red matte fringe outside the costume.
        alpha &= ~((rgb[:,:,0]>120)&(rgb[:,:,0]>rgb[:,:,1]*2.2)
                   &(rgb[:,:,1]<75)&(rgb[:,:,2]<75))
        image = image.convert('RGB').quantize(colors=128,dither=Image.Dither.NONE).convert('RGBA')
        image.putalpha(Image.fromarray((alpha*255).astype('uint8')))
        bounds = image.getbbox()
        crop = image.crop(bounds)
        # Bridge the existing lowered (81px) and raised (84px) silhouette sizes.
        height = 81+index
        scale = height/crop.height
        size = (round(crop.width*scale),height)
        source_x,source_y = foot_center(crop)
        target_x = start_x+(end_x-start_x)*index/3
        offset = (round(target_x-source_x*scale),116-height)
        frame = Image.new('RGBA',(128,128))
        frame.alpha_composite(crop.resize(size,Image.Resampling.NEAREST),offset)
        frames.append(frame)
        registration.append(dict(cell=cell,source_box=list(box),subject_bounds=list(bounds),
                                 scale=scale,offset=list(offset)))
    frames.append(last)
    records=[]
    contact=Image.new('RGB',(128*4*4,150*4),'#14212c')
    draw=ImageDraw.Draw(contact)
    for index,frame in enumerate(frames):
        name=f'raise_{index+1:02}.png'
        frame.save(OUT/name,optimize=True)
        records.append(dict(file=name,duration_ms=112.5,sha256=sha(OUT/name)))
        large=frame.resize((512,512),Image.Resampling.NEAREST)
        contact.paste(large,(index*512,0),large)
        draw.text((index*512+10,530),f'Lift {index+1}',fill='white')
    manifest=dict(version=1,actor='mira',canvas=[128,128],anchor=[64,116],
                  animations=dict(prefire_raise=dict(frames=records,loop=False)),
                  authored_with='image_gen',source=str(SOURCE.relative_to(ROOT)),
                  source_sha256=sha(SOURCE),registration=registration,
                  endpoints={str(p.relative_to(ROOT)):sha(p) for p in (START,END)},
                  active_scene_interval=[12.35,12.8])
    (OUT/'animation.json').write_text(json.dumps(manifest,indent=2)+'\n')
    contact.save(OUT/'contact_sheet.png',optimize=True)


if __name__=='__main__':
    build()
