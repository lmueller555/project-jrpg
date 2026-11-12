"""Author native contact poses and care props from Mira's registered body."""
import argparse,json,math,random,struct,wave
from pathlib import Path
from io import BytesIO
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'assets/story/sanctuary_arrival/performance'
def products():
    out={};animations={}
    base=Image.open(ROOT/'assets/characters/mira/idle_left.png').convert('RGBA')
    for name,count in [('place',6),('treat',12),('retrieve',8)]:
        frames=[]
        for i in range(count):
            image=Image.new('RGBA',(64,56));image.alpha_composite(base,(16,10))
            d=ImageDraw.Draw(image);q=i/(count-1)
            # Body registration is fixed. The left hand reaches the existing
            # dressing at worker688,318 from Mira716,318: world(-20,-15).
            reach=(min(1,q*3) if name=='treat' else q if name=='place' else 1-q)
            hand=(round(24-8*reach),round(36-2*reach)) if name=='treat' else (round(26+8*reach),round(30+19*reach))
            if name=='treat' and 4<=i<=8:hand=(hand[0],hand[1]+(-1,0,1,0,-1)[i-4])
            d.line((29,27,20,27,hand[0],hand[1]),fill='#332b28',width=4)
            d.line((29,26,20,26,hand[0],hand[1]),fill='#b68b5e',width=2)
            d.rectangle((hand[0]-1,hand[1]-1,hand[0]+2,hand[1]+1),fill='#ebbe91')
            if name=='treat':
                d.rectangle((hand[0]-2,hand[1]+1,hand[0]+3,hand[1]+3),fill=('#d8d7b5' if i%3 else '#f0e9c8'))
            path=OUT/f'{name}_{i:02}.png';stream=BytesIO();image.save(stream,format='PNG');out[path]=stream.getvalue()
            frames.append({'file':path.relative_to(ROOT).as_posix(),'duration_ms':100})
        animations[name]={'frames':frames,'loop':False,'anchor':[32,40]}
    frames=[]
    patient=Image.open(ROOT/'assets/story/sanctuary_arrival/art/worker_a/injured.png').convert('RGBA')
    for i in range(4):
        image=Image.new('RGBA',(36,40));image.alpha_composite(patient,(0,0));d=ImageDraw.Draw(image)
        end=14+round(10*i/3)
        d.line((14,24,end,24),fill='#524b3b',width=4)
        d.line((14,24,end,24),fill='#e2d9b7',width=2)
        d.rectangle((end,23,end+2,25),fill='#dfad7d')
        path=OUT/f'patient_{i:02}.png';stream=BytesIO();image.save(stream,format='PNG');out[path]=stream.getvalue()
        frames.append({'file':path.relative_to(ROOT).as_posix(),'duration_ms':100})
    animations['offer_arm']={'frames':frames,'loop':False,'anchor':[12,30]}
    frames=[]
    runner=Image.open(ROOT/'assets/characters/npcs/female_01/idle_back.png').convert('RGBA')
    for i in range(6):
        image=Image.new('RGBA',(40,40));image.alpha_composite(runner,(8,0));d=ImageDraw.Draw(image)
        hand=(round(14-10*i/5),round(15+3*i/5))
        d.line((19,17,hand[0],hand[1]),fill='#6c9baa',width=3)
        d.rectangle((hand[0]-2,hand[1]-1,hand[0]+3,hand[1]+2),fill='#e5ddbb')
        path=OUT/f'runner_{i:02}.png';stream=BytesIO();image.save(stream,format='PNG');out[path]=stream.getvalue()
        frames.append({'file':path.relative_to(ROOT).as_posix(),'duration_ms':100})
    animations['runner_place']={'frames':frames,'loop':False,'anchor':[20,30]}
    props={}
    for name in ('kit','linen'):
        image=Image.new('RGBA',(20,14));d=ImageDraw.Draw(image)
        if name=='kit':
            d.rounded_rectangle((1,4,18,12),radius=2,fill='#69482f',outline='#302b24');d.rectangle((6,1,13,5),outline='#c29c61');d.line((2,7,17,7),fill='#b18b51');d.rectangle((8,6,11,9),fill='#d5b779')
        else:
            d.polygon(((2,5),(14,3),(18,7),(16,11),(3,12)),fill='#d8d7b5',outline='#85866d');d.line((4,8,15,6),fill='#f5edcd');d.line((5,10,15,8),fill='#adae93')
        stream=BytesIO();image.save(stream,format='PNG');path=OUT/(name+'.png');out[path]=stream.getvalue();props[name]=path.relative_to(ROOT).as_posix()
    rng=random.Random(314);data=BytesIO()
    with wave.open(data,'wb') as sound:
        sound.setparams((1,2,22050,0,'NONE','not compressed'))
        value=0.;samples=[]
        for i in range(3308):
            value=.6*value+.4*rng.uniform(-1,1)
            samples.append(struct.pack('<h',round(2200*value*math.sin(math.pi*i/3308)**2)))
        sound.writeframes(b''.join(samples))
    out[OUT/'cloth.wav']=data.getvalue()
    out[OUT/'art.json']=(json.dumps({'poses':animations,'props':props},indent=2)+'\n').encode();return out
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');args=p.parse_args()
    for path,data in products().items():
        if args.check:assert path.exists() and path.read_bytes()==data,path
        else:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
