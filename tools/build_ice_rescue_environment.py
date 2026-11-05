"""Mechanically register authored rescue scenery, boss frames and Lucan portrait."""
from pathlib import Path
import hashlib
import json
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'assets/story/ice_reaper_rescue'

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def save_json(path, data):
    path.write_text(json.dumps(data, indent=2)+'\n')

def build():
    source = BASE/'source/environment/views_generated.png'
    out = BASE/'environment'
    out.mkdir(exist_ok=True, parents=True)
    im = Image.open(source).convert('RGB')
    views = ['rescue', 'reverse', 'aerial']
    for index, name in enumerate(views):
        y0, y1 = round(im.height*index/3), round(im.height*(index+1)/3)
        plate = im.crop((0,y0,im.width,y1)).resize((960,640),Image.Resampling.NEAREST)
        plate.save(out/f'{name}.png',optimize=True)
        # Separate sky plate for layered parallax. The flat strip is transparent below its horizon.
        sky = plate.convert('RGBA')
        alpha = Image.new('L',sky.size,0)
        alpha.paste(255,(0,0,960,295 if index<2 else 210))
        sky.putalpha(alpha)
        sky.save(out/f'{name}_sky.png',optimize=True)
    # Tile of the same authored snow for perspective ground projection.
    ground = im.crop((370,430,498,558)).resize((128,128),Image.Resampling.NEAREST)
    ground.save(out/'ground.png',optimize=True)
    boss_source = BASE/'source/ice_reaper/actions_generated.png'
    sheet=Image.open(boss_source).convert('RGBA')
    out=BASE/'actors/ice_reaper'
    out.mkdir(parents=True,exist_ok=True)
    alpha=sheet.getchannel('A').point(lambda a:0 if a<32 else min(255,round(a/16)*16))
    sheet.putalpha(alpha)
    groups={'aim':(0,6),'launch':(6,6),'recharge':(12,6),'ready_rear':(18,3),'ready_side':(21,3)}
    animations={}
    for name,(first,count) in groups.items():
        frames=[]
        for index in range(count):
            cell=first+index;col,row=cell%6,cell//6
            frame=sheet.crop((col*256,row*256,(col+1)*256,(row+1)*256))
            frame=frame.resize((166,166),Image.Resampling.NEAREST)
            canvas=Image.new('RGBA',(192,192))
            canvas.alpha_composite(frame,(13,12))
            filename=f'{name}_{index+1:02}.png';canvas.save(out/filename,optimize=True)
            frames.append({'file':filename,'duration_ms':100})
        animations[name]={'frames':frames,'loop':name.startswith('ready')}
    save_json(out/'animation.json',{'version':1,'actor':'ice_reaper','canvas':[192,192],'anchor':[96,172],'animations':animations,'source':'../../source/ice_reaper/actions_generated.png','source_sha256':digest(boss_source),'registration':'6x4 authored cells; fixed nearest scale and placement; alpha threshold only'})
    out=BASE/'portraits';out.mkdir(parents=True,exist_ok=True)
    portrait_source=BASE/'source/portraits/lucan_generated.png'
    Image.open(portrait_source).convert('RGB').resize((96,96),Image.Resampling.NEAREST).save(out/'lucan.png',optimize=True)
    sources=[source,boss_source,portrait_source]
    save_json(BASE/'environment/provenance.json',{'version':1,'creative_method':'Image generation using approved environment, Ice Reaper and Lucan references. Sources retained unchanged.','sources':[{'file':str(p.relative_to(ROOT)),'sha256':digest(p)} for p in sources],'operations':['equal-panel crop','nearest-neighbor registration','fixed actor anchor','alpha cleanup','no body morphing or limb deformation']})
    print('Registered three 960x640 scenic views, ground, skies, 24 boss frames and Lucan portrait.')

if __name__=='__main__':build()
