"""Register authored winter costume/flow drawings; preserve world-foot placement.

Operations are cell extraction, binary alpha cleanup, fixed nearest scaling,
foot registration, and compositing authored loose-cloth/hair around a fixed core.
No sprite is deformed, interpolated or procedurally posed.
"""
from pathlib import Path
import hashlib,json
import numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'assets/source/cinematics/rhea_winter'
OUTPUT=ROOT/'assets/story/rhea_winter'
VIEWS=(('front',0),('front_right',45),('right',90),('rear_right',135),('rear',180),('rear_left',-135),('left',-90),('front_left',-45))

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def cells(path,columns,rows):
    image=Image.open(path).convert('RGBA')
    return [image.crop((round(c*image.width/columns),round(r*image.height/rows),round((c+1)*image.width/columns),round((r+1)*image.height/rows))) for r in range(rows) for c in range(columns)]

def clean(tile):
    alpha=np.asarray(tile)[:,:,3]>=140
    # Discard saturated red matte fringe from source transparency edges.
    pixels=np.asarray(tile);red=(pixels[:,:,0]>120)&(pixels[:,:,0]>pixels[:,:,1]*2.2)&(pixels[:,:,1]<75)&(pixels[:,:,2]<75)
    alpha &= ~red
    rgb=tile.convert('RGB').quantize(colors=128,dither=Image.Dither.NONE).convert('RGBA')
    rgb.putalpha(Image.fromarray((alpha*255).astype('uint8')))
    return rgb

def register(tile,scale=.2):
    tile=clean(tile);pixels=np.asarray(tile);alpha=pixels[:,:,3]>0
    ys,xs=np.where(alpha);bottom=int(ys.max())
    rgb=pixels[:,:,:3].astype(float)
    feet=(np.indices(alpha.shape)[0]>=bottom-7)&alpha&(rgb[:,:,0]>rgb[:,:,1]*1.09)&(rgb[:,:,1]>rgb[:,:,2]*1.05)
    if not feet.any():feet=alpha&(np.indices(alpha.shape)[0]>=bottom-3)
    fy,fx=np.where(feet);footx=float((fx.min()+fx.max())/2)
    b=tile.getbbox();crop=tile.crop(b);res=crop.resize((round(crop.width*scale),round(crop.height*scale)),Image.Resampling.NEAREST)
    # Align the last nontransparent foot pixel, avoiding rounding-driven bob.
    offset=(round(64-(footx-b[0])*scale),117-res.height)
    output=Image.new('RGBA',(128,128));output.alpha_composite(res,offset)
    if output.getbbox() is None or output.getbbox()[0]<1 or output.getbbox()[1]<1 or output.getbbox()[2]>127:raise ValueError('Drawing clipped by native canvas')
    return output,dict(bounds=list(b),foot=[footx,bottom],scale=scale,offset=list(offset))

def contact(frames,path,columns=8):
    w=128*3;h=145*3;out=Image.new('RGB',(columns*w,((len(frames)+columns-1)//columns)*h),(18,27,35));draw=ImageDraw.Draw(out)
    for i,(name,im) in enumerate(frames):
        x=(i%columns)*w;y=(i//columns)*h
        big=im.resize((w,w),Image.Resampling.NEAREST);out.paste(big,(x,y),big);draw.text((x+8,y+w+4),name,fill='white')
    out.save(path,optimize=True)

def build_rested():
    folder=OUTPUT/'rested';folder.mkdir(parents=True,exist_ok=True)
    tiles=cells(SOURCE/'rested_generated.png',4,2)
    # Supplemental opposite profiles are authored separately, never mirrored.
    extra=SOURCE/'rested_opposites_generated.png'
    supplements=cells(extra,3,1) if extra.exists() else None
    mapping={'front':tiles[0],'front_right':tiles[1],'right':tiles[2],'rear_right':tiles[3],'rear':tiles[4],'rear_left':tiles[5],'left':tiles[6],'front_left':tiles[7]}
    if supplements:mapping.update(right=supplements[0],front_left=supplements[1],rear_right=supplements[2])
    frames=[];records={}
    for view,angle in VIEWS:
        im,registration=register(mapping[view],.112 if supplements and view in ('right','front_left','rear_right') else .2);p=folder/f'{view}.png';im.save(p,optimize=True)
        records[view]=dict(file=f'rested/{view}.png',view_azimuth_deg=angle,sha256=sha(p),registration=registration)
        frames.append((view,im))
    contact(frames,OUTPUT/'rested_contact_sheet.png')
    return records

def build_energy():
    folder=OUTPUT/'energy';folder.mkdir(parents=True,exist_ok=True)
    records={};contact_frames=[]
    for view,angle in VIEWS:
        path=SOURCE/f'energy_{view}_generated.png'
        if not path.exists():continue
        registered=[register(tile,.185)[0] for tile in cells(path,3,2)]
        # Anatomical core is identical across all keys. Only authored peripheral
        # hair and loose shawl pixels change; no body/foot/staff jitter.
        base=np.array(registered[2]);core=np.zeros((128,128),bool)
        core[43:60,58:71]=True;core[62:98,56:73]=True;core[98:117,49:79]=True
        rgb=base[:,:,:3].astype(float);opaque=base[:,:,3]>0
        purple=opaque&(rgb[:,:,0]>rgb[:,:,1]*1.15)&(rgb[:,:,2]>rgb[:,:,1]*1.05)
        # Freeze staff crown/orb and holding hand as a single anchored assembly.
        greenorb=opaque&(rgb[:,:,1]>rgb[:,:,0]*1.18)&(rgb[:,:,1]>rgb[:,:,2]*1.4)&(np.indices(core.shape)[0]<58)
        purple |= greenorb
        for dy in range(-2,3):
            for dx in range(-2,3):core|=np.roll(np.roll(purple,dy,axis=0),dx,axis=1)
        frames=[]
        for i,im in enumerate(registered):
            result=np.array(im);result[core]=base[core]
            p=folder/f'{view}_{i+1:02}.png';frame=Image.fromarray(result,'RGBA');frame.save(p,optimize=True)
            frames.append(dict(file=f'energy/{view}_{i+1:02}.png',duration_ms=200,sha256=sha(p)))
            contact_frames.append((f'{view} {i+1}',frame))
        mask=folder/f'{view}_core.png';Image.fromarray((core*255).astype('uint8')).save(mask,optimize=True)
        records[view]=dict(frames=frames,view_azimuth_deg=angle,loop=True,core_mask=f'energy/{view}_core.png')
    if contact_frames:contact(contact_frames,OUTPUT/'energy_contact_sheet.png',6)
    return records

def build():
    OUTPUT.mkdir(parents=True,exist_ok=True)
    rest=build_rested();energy=build_energy()
    manifest=dict(version=1,actor='rhea',canvas=[128,128],anchor=[64,116],body_pixels=82,rested=rest,energy=energy)
    expressions=OUTPUT/'awakening/manifest.json'
    if expressions.exists():
        expressions=json.loads(expressions.read_text());manifest['awakening']=expressions
    if (OUTPUT/'opening_manifest.json').exists():manifest['opening']=json.loads((OUTPUT/'opening_manifest.json').read_text())
    actions=OUTPUT/'actions/animation.json'
    if actions.exists():
        groups=json.loads(actions.read_text())['animations']
        manifest['actions']={name:dict(entry,frames=[dict(f,file='actions/'+f['file']) for f in entry['frames']]) for name,entry in groups.items()}
    manifest['provenance']=dict(tool='image_gen',sources={str(p.relative_to(ROOT)):sha(p) for p in sorted(SOURCE.glob('*_generated.png'))},operation=__doc__.strip())
    (OUTPUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(dict(rested=len(rest),energy=len(energy),actions=len(manifest.get('actions',{})),awakening=len(manifest.get('awakening',{}).get('frames',{})))))
if __name__=='__main__':build()
