"""Register full imagegen-authored loader bodies; never synthesize limbs."""
from __future__ import annotations
import argparse
import hashlib
import io
import json
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/characters/grain_workers/loader'
OUT = ROOT/'assets/characters/grain_workers/loader'
ANCHOR = (20,38)
SHEETS = {'work': ('work_sheet_generated.png',6),
          'carry': ('carry_sheet_generated.png',6),
          'walk': ('loaded_walk_generated.png',4)}


def png(image):
    buf=io.BytesIO();image.save(buf,format='PNG',optimize=True);return buf.getvalue()


def digest(data):return hashlib.sha256(data).hexdigest()


def cells(image, rows):
    """Find actual transparent row gutters rather than clip generated boots."""
    found={}
    for col in range(4):
        left=round(col*image.width/4);right=round((col+1)*image.width/4)
        strip=image.crop((left,0,right,image.height))
        alpha=strip.getchannel('A').point(lambda x:255 if x>=128 else 0)
        occupied=[bool(alpha.crop((0,y,strip.width,y+1)).getbbox()) for y in range(strip.height)]
        bands=[];start=None;last=-1
        for y,active in enumerate(occupied+[False]*10):
            if active:
                if start is None:start=y
                last=y
            elif start is not None and y-last>=8:
                if last-start>60:bands.append((start,last+1))
                start=None
        if len(bands)!=rows:raise ValueError(f'Expected {rows} authored rows in column{col}; found{bands}')
        for row,(top,bottom) in enumerate(bands):
            cell=strip.crop((0,top,strip.width,bottom))
            a=cell.getchannel('A').point(lambda x:255 if x>=128 else 0);cell.putalpha(a)
            bbox=a.getbbox();cell=cell.crop(bbox)
            found[row,col]=(cell,(left+bbox[0],top,left+bbox[2],bottom))
    return found


def register(image, scale):
    resized=image.resize((round(image.width*scale),round(image.height*scale)),Image.Resampling.NEAREST)
    # Common soles, while preserving squat height and the complete painted body.
    soles=image.getchannel('A').crop((0,max(0,image.height-8),image.width,image.height)).getbbox()
    cx=(soles[0]+soles[2])/2
    target=Image.new('RGBA',(40,44))
    target.alpha_composite(resized,(ANCHOR[0]-round(cx*scale),ANCHOR[1]-resized.height))
    return target


def build():
    exports={};source_records=[];images={};raw_images={};boxes={};scales={};clip_scales={}
    for key,(name,rows) in SHEETS.items():
        path=SOURCE/name;raw=path.read_bytes();source=Image.open(path).convert('RGBA')
        records=cells(source,rows)
        # A standing row determines one uniform scale for the entire sheet.
        standing=5 if rows==6 else 0
        h=max(records[standing,col][0].height for col in range(4))
        scales[key]=34/h
        raw_images[key]={rc:im for rc,(im,_) in records.items()}
        images[key]={rc:register(im,scales[key]) for rc,(im,_) in records.items()}
        boxes[key]={f'{r},{c}':list(box) for (r,c),(_,box) in records.items()}
        source_records.append({'file':path.relative_to(ROOT).as_posix(),'sha256':digest(raw),'size':list(source.size)})
    sequences={}
    def seq(key,refs,ms,loop=False,offsets=None,hands=None,layer='front',gripped=None,cloth=None):
        frames=[]
        # Generated rows have slightly different whole-figure scales. These
        # fully standing clips use one clip-wide registration scale so a turn
        # cannot grow the worker. Bends retain their relative compressed height.
        work_refs=[(r,c) for s,r,c in refs if s=='work']
        clip_scale=(34/max(raw_images['work'][rc].height for rc in work_refs)
                    if work_refs and key in ('cover_front','place_right','work_right','look_left') else None)
        if clip_scale is not None:clip_scales[key]=clip_scale
        for i,(sheet,row,col) in enumerate(refs):
            body=(register(raw_images[sheet][row,col],clip_scale)
                  if sheet=='work' and clip_scale is not None else images[sheet][row,col])
            file=f'{key}_{i}.png';exports[file]=png(body)
            frame={'file':file,'duration_ms':ms}
            if offsets is not None:
                frame['sack_offset']=offsets[i];frame['sack_layer']=layer
            if hands is not None:
                contacts=[]
                for dx,dy in hands[i]:
                    x,y=ANCHOR[0]+dx,ANCHOR[1]+dy
                    candidates=[]
                    for py in range(max(18,y-4),min(44,y+5)):
                        for px in range(max(0,x-4),min(40,x+5)):
                            r,g,b,a=body.getpixel((px,py))
                            if a and r>165 and g>85 and 35<b<190 and r-g>28 and g-b>5:
                                candidates.append(((px-x)**2+(py-y)**2,px,py))
                    if candidates and layer!='back':
                        _,px,py=min(candidates);contacts.append([px-ANCHOR[0],py-ANCHOR[1]])
                    else:contacts.append([dx,dy])
                frame['hands']=contacts
            if gripped is not None:frame['gripped']=gripped[i]
            if cloth is not None:frame['cloth_offset']=cloth[i]
            frames.append(frame)
        sequences[key]={'loop':loop,'frames':frames}
    w=lambda row,cols:[('work',row,c) for c in cols]
    c=lambda row,cols:[('carry',row,v) for v in cols]
    q=lambda row,cols:[('walk',row,v) for v in cols]
    seq('inspect_front',w(2,[0,1]),650,True)
    seq('cover_front',w(0,[3])+w(2,[3]),500,False,cloth=[[0,-14],[0,-14]],hands=[[[-5,-12],[5,-12]],[[-5,-13],[5,-13]]])
    seq('lift_front',w(0,[0,1,2])+c(5,[0]),300,False,
        [[0,-3],[0,-7],[0,-11],[0,-14]],
        [[[-2,-3],[2,-3]],[[-3,-7],[3,-7]],[[-5,-10],[5,-10]],[[-5,-12],[5,-12]]],gripped=[False,True,True,True])
    seq('recover_front',w(0,[0,1,2])+w(5,[1]),100,False,gripped=[False]*4)
    hold_refs={'front':c(5,[0]),'back':c(5,[1]),'left':q(2,[1]),'right':c(5,[3])}
    hold_offsets={'front':[0,-14],'back':[0,-14],'left':[-7,-13],'right':[7,-13]}
    hold_hands={'front':[[-5,-12],[5,-12]],'back':[[-4,-13],[4,-13]],'left':[[-7,-11],[-5,-12]],'right':[[5,-11],[7,-12]]}
    for direction,refs in hold_refs.items():
        seq('hold_'+direction,refs,720,True,[hold_offsets[direction]],[hold_hands[direction]],'back' if direction=='back' else 'front')
    for row,direction in enumerate(('front','back','left','right')):
        seq('carry_'+direction,q(row,[0,1,2,3]),180,True,
            [hold_offsets[direction]]*4,[hold_hands[direction]]*4,'back' if direction=='back' else 'front')
    # A single deliberate glance, then hold. The generated rear-facing detail
    # pose is intentionally unused because it would place the load on his back.
    seq('look_left',c(5,[0])+w(3,[0]),350,False,[[0,-14],[0,-14]],[[[-5,-12],[5,-12]],[[-5,-12],[5,-12]]])
    seq('place_right',w(1,[0,1,2,3]),300,False,
        [[4,-14],[9,-13],[14,-10],[14,-10]],
        [[[5,-12],[7,-12]],[[8,-11],[10,-11]],[[11,-10],[13,-10]],[[4,-12],[7,-12]]],gripped=[True,True,True,False])
    seq('push_right',c(4,[0,1,2,2]),240,False,
        [[14,-10],[16,-11],[18,-11],[20,-12]],
        [[[11,-18]],[[12,-18]],[[15,-19]],[[15,-19]]])
    seq('work_right',w(3,[2,3]),550,True)
    seq('stretch_front',w(5,[0,1]),850,False)
    manifest={'version':1,'canvas':[40,44],'anchor':list(ANCHOR),'sequences':sequences}
    exports['animation.json']=(json.dumps(manifest,indent=2)+'\n').encode()
    provenance={'version':1,'exporter':'tools/build_grain_loader.py','sources':source_records,
        'registration':{'alpha_threshold':128,'sheet_scales':scales,'clip_scale_overrides':clip_scales,'source_boxes':boxes,'anchor':list(ANCHOR)},
        'exports':{name:digest(data) for name,data in exports.items()},
        'notes':['Full authored bodies only; no limb synthesis, body warps or hand repainting.',
                 'One uniform sheet/clip scale preserves squat compression; no per-frame body-height normalization.',
                 'Sacks and cloth remain controller-owned separate props.',
                 'Approved normal directional idles/walks are unchanged.']}
    exports['provenance.json']=(json.dumps(provenance,indent=2)+'\n').encode()
    return exports,manifest


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');args=parser.parse_args()
    exports,manifest=build()
    if args.check:
        for name,data in exports.items():
            path=OUT/name
            if not path.exists() or path.read_bytes()!=data:raise SystemExit(f'Outdated loader export: {path}')
        print(f'Verified {len(exports)} loader body/manifest exports');return
    OUT.mkdir(parents=True,exist_ok=True)
    for name,data in exports.items():(OUT/name).write_bytes(data)
    # Review sheets compose actual exported whole bodies and actual external sack.
    sack=Image.open(ROOT/'assets/characters/grain_workers/sack.png').convert('RGBA')
    names=list(manifest['sequences']);review=Image.new('RGB',(700,len(names)*88),'#29413a');draw=ImageDraw.Draw(review)
    for row,name in enumerate(names):
        draw.text((3,row*88+3),name,fill='#f1dfbb')
        for i,frame in enumerate(manifest['sequences'][name]['frames']):
            body=Image.open(io.BytesIO(exports[frame['file']])).convert('RGBA')
            withbag=Image.new('RGBA',(56,44))
            off=frame.get('sack_offset')
            pos=(20+off[0]-6,38+off[1]-10) if off is not None else None
            if off is not None and frame.get('sack_layer')=='back':withbag.alpha_composite(sack,pos)
            withbag.alpha_composite(body)
            if off is not None and frame.get('sack_layer')!='back':withbag.alpha_composite(sack,pos)
            enlarged=withbag.resize((112,88),Image.Resampling.NEAREST)
            review.paste(enlarged,(175+i*125,row*88),enlarged)
    review.save(SOURCE/'native_review.png')
    print(f'Exported {len(exports)} loader body/manifest files')


if __name__=='__main__':main()
