"""Register imagegen-authored masonry and tea bodies without synthesizing limbs."""
from __future__ import annotations
import argparse
import hashlib
import io
import json
from pathlib import Path
from PIL import Image, ImageDraw
try:
    from build_grain_loader import register, png
except ModuleNotFoundError:
    from tools.build_grain_loader import register, png

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'assets/source/characters/bridge_workers/mason'
OUT=ROOT/'assets/characters/bridge_workers/mason'
ANCHOR=(20,38)
SHEETS={'work':('work_generated.png',6),'carry':('carry_generated.png',7),
        'tea':('tea_generated.png',6),'seat':('seated_generated.png',3)}


def sha(data):return hashlib.sha256(data).hexdigest()


def cells(image,rows):
    result={}
    for col in range(4):
        left=round(col*image.width/4);right=round((col+1)*image.width/4)
        strip=image.crop((left,0,right,image.height))
        a=strip.getchannel('A').point(lambda v:255 if v>=128 else 0)
        occupied=[bool(a.crop((0,y,strip.width,y+1)).getbbox()) for y in range(strip.height)]
        bands=[];start=None
        for y,active in enumerate(occupied+[False]):
            if active and start is None:start=y
            elif not active and start is not None:
                if y-start>60:bands.append((start,y))
                start=None
        if len(bands)!=rows:raise ValueError(f'{rows} rows expected, column{col}: {bands}')
        for row,(top,bottom) in enumerate(bands):
            body=strip.crop((0,top,strip.width,bottom));alpha=body.getchannel('A').point(lambda v:255 if v>=128 else 0)
            body.putalpha(alpha);box=alpha.getbbox()
            result[row,col]=(body.crop(box),[left+box[0],top,left+box[2],bottom])
    return result


def build():
    raw={};source_records=[];boxes={}
    for key,(name,n) in SHEETS.items():
        path=SOURCE/name;source=Image.open(path).convert('RGBA');c=cells(source,n)
        raw[key]={rc:body for rc,(body,_) in c.items()}
        boxes[key]={f'{r},{c}':box for (r,c),(_,box) in c.items()}
        source_records.append({'file':path.relative_to(ROOT).as_posix(),'sha256':sha(path.read_bytes()),'size':list(source.size)})
    exports={};sequences={};scales={}
    seat_scale=34/max(raw['seat'][0,0].height,raw['seat'][2,3].height)
    def seq(key,refs,ms,loop=False,offsets=None,prop=None,hands=None,layer='front',gripped=None,scale=None,mirror=False,mouth=None,seat=None):
        if scale is None:scale=34/max(raw[s][r,c].height for s,r,c in refs)
        scales[key]=scale;frames=[]
        for i,(sheet,row,col) in enumerate(refs):
            body=raw[sheet][row,col]
            if mirror:body=body.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            image=register(body,scale);file=f'{key}_{i}.png';exports[file]=png(image)
            f={'file':file,'duration_ms':ms if isinstance(ms,int) else ms[i]}
            if prop and offsets is not None:f[prop+'_offset']=offsets[i];f[prop+'_layer']=layer
            if hands is not None:
                contacts=[]
                for dx,dy in hands[i]:
                    x,y=20+dx,38+dy;points=[]
                    for py in range(max(18,y-4),min(44,y+5)):
                        for px in range(max(0,x-4),min(40,x+5)):
                            r,g,b,a=image.getpixel((px,py))
                            if a and r>165 and g>85 and 35<b<190 and r-g>28 and g-b>5:
                                points.append(((px-x)**2+(py-y)**2,px,py))
                    if points and layer!='back':_,px,py=min(points);contacts.append([px-20,py-38])
                    else:contacts.append([dx,dy])
                f['hands']=contacts
            if gripped is not None:f['gripped']=gripped[i]
            if mouth is not None:f['mouth_offset']=mouth[i]
            if seat is not None:f['seat_contact']=seat[i]
            frames.append(f)
        sequences[key]={'loop':loop,'frames':frames}
    w=lambda r,cols:[('work',r,c) for c in cols]
    c=lambda r,cols:[('carry',r,v) for v in cols]
    t=lambda r,cols:[('tea',r,c) for c in cols]
    s=lambda r,cols:[('seat',r,c) for c in cols]
    lift_scale=34/raw['work'][0,3].height
    seq('inspect_front',w(4,[0,1]),650,True)
    seq('lift_front',w(0,[0,1,2,3]),300,False,[[0,-2],[0,-6],[0,-9],[0,-12]],'stone',
        [[[-4,-4],[4,-4]],[[-4,-7],[4,-7]],[[-5,-11],[5,-11]],[[-5,-12],[5,-12]]],gripped=[False,True,True,True],scale=lift_scale)
    seq('recover_front',w(0,[0,1,2,3]),100,False,gripped=[False]*4,scale=lift_scale)
    seq('place_front',w(0,[3,2,1,0]),300,False,[[0,-12],[0,-9],[0,-6],[0,-2]],'stone',
        [[[-5,-12],[5,-12]],[[-5,-11],[5,-11]],[[-4,-7],[4,-7]],[[-4,-4],[4,-4]]],gripped=[True,True,True,False],scale=lift_scale)
    seq('work_right',w(2,[0,1,2,3]),500,True,[[7,-12],[8,-12],[9,-11],[7,-12]],'tool',[[[7,-12]],[[8,-12]],[[9,-11]],[[7,-12]]])
    seq('measure_left',w(3,[0,1]),600,True,[[-8,-12],[-6,-12]],'tool',[[[-8,-12]],[[-6,-12]]])
    seq('measure_right',w(3,[2,3]),600,True,[[8,-12],[6,-12]],'tool',[[[8,-12]],[[6,-12]]])
    seq('stretch_front',w(4,[2,3]),800,False)
    stone_offsets={'front':[0,-12],'back':[0,-12],'left':[-7,-12],'right':[7,-12]}
    cup_offsets={'front':[0,-11],'back':[0,-11],'left':[-7,-12],'right':[7,-12]}
    for row,direction in enumerate(('front','back','left','right')):
        layer='back' if direction=='back' else 'front'
        palms=([[-5,-12],[5,-12]] if direction in ('front','back') else [[-7,-12],[-5,-12]] if direction=='left' else [[5,-12],[7,-12]])
        seq('hold_'+direction,w(5,[row]),720,True,[stone_offsets[direction]],'stone',[palms],layer)
        seq('carry_'+direction,c(row,[0,1,2,3]),180,True,[stone_offsets[direction]]*4,'stone',[palms]*4,layer)
        seq('cup_hold_'+direction,t(5,[row]),720,True,[cup_offsets[direction]],'cup',[palms],layer)
        # The proper right-facing authored cargo pose also supports a small
        # cupped mug. Reusing its whole body preserves anatomical direction.
        cup_row={0:4,1:5,2:6,3:3}[row]
        seq('cup_'+direction,c(cup_row,[0,1,2,3]),180,True,[cup_offsets[direction]]*4,'cup',[palms]*4,layer)
    seq('receive_right',t(0,[1,2,3,0]),350,False,[[9,-13],[9,-13],[7,-12],[7,-12]],'cup',[[[9,-13]],[[9,-13]],[[7,-12]],[[7,-12]]],gripped=[False,True,True,True])
    seq('offer_right',t(1,[0,1,2,3]),250,False,[[7,-12],[8,-14],[8,-14],[8,-14]],'cup',[[[7,-12]],[[8,-14]],[[8,-14]],[[8,-14]]],gripped=[True,True,True,False])
    seq('sit_down_front',s(0,[0,1,2,3]),250,False,[[-7,-13],[-5,-11],[-3,-8],[2,-6]],'cup',
        [[[-5,-14]],[[-3,-13]],[[0,-11]],[[1,-9],[5,-9]]],scale=seat_scale,mirror=True,seat=[[0,-12],[2,-10],[5,-7],[7,-5]])
    seq('sit_front',s(1,[0]),1000,True,[[2,-6]],'cup',[[[1,-9],[5,-9]]],scale=seat_scale,mirror=True,seat=[[7,-5]])
    seq('drink_front',s(1,[0,1,2,3]),[650,350,850,450],True,[[2,-6],[0,-11],[0,-11],[2,-6]],'cup',
        [[[1,-9],[5,-9]],[[0,-13],[2,-11]],[[0,-13],[2,-11]],[[1,-9],[5,-9]]],scale=seat_scale,mirror=True,
        mouth=[[1,-16]]*4,seat=[[7,-5]]*4)
    seq('stand_front',s(2,[0,1,2,3]),250,False,[[2,-6],[-3,-9],[-5,-11],[-7,-13]],'cup',
        [[[1,-9],[5,-9]],[[0,-11]],[[-3,-13]],[[-5,-14]]],scale=seat_scale,mirror=True,seat=[[7,-5],[5,-7],[2,-10],[0,-12]])
    manifest={'version':1,'canvas':[40,44],'anchor':[20,38],'sequences':sequences}
    exports['animation.json']=(json.dumps(manifest,indent=2)+'\n').encode()
    provenance={'version':1,'exporter':'tools/build_bridge_mason.py','sources':source_records,
        'registration':{'alpha_threshold':128,'source_boxes':boxes,'sequence_scales':scales,'seat_reflected_full_profile':True,'anchor':[20,38]},
        'exports':{k:sha(v) for k,v in exports.items()},
        'notes':['Complete imagegen-authored bodies only; no procedural arms or body warps.',
                 'Seat source is a genuinely sideways whole-body clip reflected as a whole to face the bench; no front-pose substitution.',
                 'One physical scale throughout seated transitions preserves native 27px seated vs34px standing height.',
                 'Stone, cup and tool remain separate props; metadata registers actual painted contacts.',
                 'The missing cup-right source row uses the anatomically compatible fully authored cargo-right body.']}
    exports['provenance.json']=(json.dumps(provenance,indent=2)+'\n').encode()
    return exports,manifest


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');args=parser.parse_args()
    exports,manifest=build()
    if args.check:
        for name,data in exports.items():
            path=OUT/name
            if not path.exists() or path.read_bytes()!=data:raise SystemExit(f'Outdated bridge mason export:{path}')
        print(f'Verified {len(exports)} bridge mason exports');return
    OUT.mkdir(parents=True,exist_ok=True)
    for name,data in exports.items():(OUT/name).write_bytes(data)
    review=Image.new('RGB',(700,len(manifest['sequences'])*88),'#29413a');draw=ImageDraw.Draw(review)
    props={name:Image.open(ROOT/'assets/characters/bridge_workers'/f'{name}.png').convert('RGBA') for name in ('stone','cup','tool')}
    for row,(key,sequence) in enumerate(manifest['sequences'].items()):
        draw.text((3,row*88+3),key,fill='#f1dfbb')
        for i,f in enumerate(sequence['frames']):
            body=Image.open(io.BytesIO(exports[f['file']])).convert('RGBA');im=Image.new('RGBA',(56,44))
            for name in ('stone','cup','tool'):
                if name+'_offset' in f and f.get(name+'_layer')=='back':
                    p=props[name];x,y=f[name+'_offset'];im.alpha_composite(p,(20+x-p.width//2,38+y-p.height))
            im.alpha_composite(body)
            for name in ('stone','cup','tool'):
                if name+'_offset' in f and f.get(name+'_layer')!='back':
                    p=props[name];x,y=f[name+'_offset'];im.alpha_composite(p,(20+x-p.width//2,38+y-p.height))
            large=im.resize((112,88),Image.Resampling.NEAREST);review.paste(large,(175+i*125,row*88),large)
    review.save(SOURCE/'native_review.png')
    print(f'Exported {len(exports)} bridge mason files, {len(manifest["sequences"])} sequences')


if __name__=='__main__':main()
