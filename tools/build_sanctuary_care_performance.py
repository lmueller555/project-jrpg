"""Author proportionate Sanctuary care poses and one-owner prop transfers.

Heads retain the approved native designs. Bodies are articulated for each
kneel/bend instead of attaching a long arm to an unchanged standing sprite.
Contact metadata describes staging guides, not pixel-perfect reach mandates.
"""
import argparse
from io import BytesIO
import json
import math
from pathlib import Path
import random
import struct
import wave

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'assets/story/sanctuary_arrival/performance'
ANCHOR = (32, 40)
P = {'edge':'#302627', 'pink':'#c88495', 'pink_dark':'#805062',
     'pink_light':'#e6a8b4', 'skin':'#e8b68a', 'skin_light':'#f2c79b',
     'pants':'#654737', 'pants_dark':'#3d3028', 'boot':'#483525',
     'teal':'#3f7774', 'brass':'#c49b56', 'cloth':'#e5dfbe',
     'blue':'#4d77a0', 'blue_dark':'#304f70', 'blue_light':'#7da5c7'}


def png(image):
    stream = BytesIO(); image.save(stream, format='PNG'); return stream.getvalue()


def mix(a, b, q):
    return tuple(round(x+(y-x)*q) for x, y in zip(a, b))


def limb(draw, shoulder, elbow, hand, color, width=3):
    draw.line((shoulder, elbow, hand), fill=P['edge'], width=width+2)
    draw.line((shoulder, elbow, hand), fill=color, width=width)
    draw.rectangle((hand[0]-1, hand[1]-1, hand[0]+1, hand[1]+1), fill=P['skin'])


def props():
    kit = Image.new('RGBA', (14, 11)); d = ImageDraw.Draw(kit)
    d.rounded_rectangle((1,3,12,10), radius=1, fill='#69482f', outline='#302b24')
    d.rectangle((4,0,9,3), outline='#c29c61')
    d.line((2,5,11,5), fill='#b18b51'); d.rectangle((6,4,8,7), fill='#d5b779')
    linen = Image.new('RGBA', (12,8)); d = ImageDraw.Draw(linen)
    d.polygon(((0,2),(8,0),(11,3),(10,7),(1,7)), fill='#d8d7b5', outline='#85866d')
    d.line((2,3,9,2),fill='#f5edcd'); d.line((2,5,9,4), fill='#adae93')
    return {'kit':kit, 'linen':linen}


def mira_body(heads, kind='care', hand=None, q=1., direction='left'):
    """Fixed feet, bent knees, lowered pelvis and normal upper/forearm lengths."""
    image = Image.new('RGBA', (64,64)); d=ImageDraw.Draw(image)
    # Canonical side head and palette; bent body is drawn independently.
    if kind == 'stand':
        shoulder=(31,24); hip=(32,32); head=(14,7)
        legs=(((32,32),(30,36),(30,40)), ((33,32),(35,36),(35,40)))
    elif kind == 'bend':
        shoulder=mix((31,24),(28,32),q); hip=mix((32,32),(32,36),q)
        head=mix((14,7),(10,15),q)
        legs=((hip,mix((30,36),(26,38),q),(30,40)),
              (hip,mix((35,36),(36,38),q),(36,40)))
    elif kind == 'recover':
        shoulder=mix((28,32),(27,28),q); hip=mix((32,36),(32,35),q)
        head=mix((10,15),(9,12),q)
        legs=((hip,(26,38),(30,40)),(hip,mix((36,38),(37,38),q),(37,40)))
    else:
        shoulder=(27,28); hip=(32,35); head=(9,12)
        legs=(((32,35),(26,38),(30,40)), ((32,35),(37,38),(37,40)))
    if direction=='right':
        def reflect(point):return (64-point[0],point[1])
        shoulder=reflect(shoulder); hip=reflect(hip)
        legs=tuple(tuple(reflect(point) for point in leg) for leg in legs)
        head=(64-head[0]-32,head[1])
    # Legs articulate around hips/knees; the boots stay on their ground row.
    for index,(hip_point,knee,ankle) in enumerate(legs):
        d.line((hip_point,knee,ankle), fill=P['edge'], width=5)
        d.line((hip_point,knee,ankle), fill=P['pants_dark'] if index else P['pants'], width=3)
        d.rectangle((ankle[0]-2,39,ankle[0]+2,41),fill=P['edge'])
        d.line((ankle[0]-1,39,ankle[0]+1,39),fill=P['boot'])
    sx,sy=shoulder;hx,hy=hip
    d.polygon(((sx-3,sy-1),(sx+3,sy-1),(hx+3,hy),(hx-3,hy)),fill=P['pink_dark'],outline=P['edge'])
    d.line((sx-1,sy,sx,sy+3,hx,hy-1),fill=P['pink'],width=3)
    d.point((sx,sy),fill=P['pink_light'])
    d.line((hx-3,hy,hx+3,hy),fill=P['edge'],width=2)
    d.point((hx,hy),fill=P['brass'])
    # Far arm folds at the waist; no retained standing arms under the new pose.
    far=(sx+3,sy+1); far_elbow=(hx+3,hy-2);far_hand=(hx,hy-1)
    limb(d,far,far_elbow,far_hand,P['pink_dark'],2)
    if hand is None:hand=(sx-1,sy+6)
    elbow=((sx+hand[0])//2-1, min(hand[1]-2,sy+5))
    limb(d,shoulder,elbow,hand,P['pink'],2)
    # A small worn brass/teal cuff stays on the forearm, rather than floating.
    d.line((elbow,(round((elbow[0]+hand[0])/2),round((elbow[1]+hand[1])/2))),fill=P['teal'],width=3)
    d.point(elbow,fill=P['brass'])
    image.alpha_composite(heads[direction],head)
    return image


def cloth_in_hand(image, hand):
    d=ImageDraw.Draw(image)
    d.polygon(((hand[0]-2,hand[1]+1),(hand[0]+2,hand[1]),
               (hand[0]+3,hand[1]+4),(hand[0]-1,hand[1]+4)),fill=P['cloth'],outline='#a7a080')
    d.point(hand,fill=P['skin_light'])


def carry_bundle(body, direction, bundle):
    """Native directional carrying: rear bundle is occluded by opaque body."""
    image=Image.new('RGBA',body.size)
    center={'left':(6,23),'right':(18,23),'front':(12,24),'back':(12,23)}[direction]
    point=(center[0]-6,center[1]-3)
    if direction=='back':
        image.alpha_composite(bundle,point);image.alpha_composite(body)
        # Hands are on the far side too; no front-facing overlay through coat.
        return image
    image.alpha_composite(body);d=ImageDraw.Draw(image)
    if direction=='left':shoulder=(11,18); elbow=(8,22); hand=(6,25)
    elif direction=='right':shoulder=(13,18);elbow=(16,22);hand=(18,25)
    else:shoulder=(7,18);elbow=(6,23);hand=(8,26)
    limb(d,shoulder,elbow,hand,P['blue'],2)
    image.alpha_composite(bundle,point);d=ImageDraw.Draw(image)
    for x in ((center[0]-4,center[0]+4) if direction=='front' else (center[0],)):
        d.point((x,center[1]+3),fill=P['skin'])
    return image


def runner_body(head, q, hand):
    image=Image.new('RGBA',(64,64));d=ImageDraw.Draw(image)
    shoulder=mix((31,24),(28,32),q);hip=mix((32,32),(32,36),q)
    for knee,ankle in ((mix((30,36),(26,38),q),(30,40)),(mix((35,36),(36,38),q),(36,40))):
        d.line((hip,knee,ankle),fill=P['edge'],width=5)
        d.line((hip,knee,ankle),fill=P['blue_dark'],width=3)
        d.rectangle((ankle[0]-2,39,ankle[0]+2,41),fill=P['edge'])
    sx,sy=shoulder
    d.polygon(((sx-3,sy-1),(sx+3,sy-1),(hip[0]+4,hip[1]+1),(hip[0]-4,hip[1]+1)),fill=P['blue'],outline=P['edge'])
    d.line((sx-1,sy,sx,sy+3,hip[0],hip[1]-1),fill=P['blue_light'],width=2)
    limb(d,shoulder,((sx+hand[0])//2, min(hand[1]-2,sy+5)),hand,P['blue'],2)
    image.alpha_composite(head,mix((20,7),(17,15),q))
    return image


def products():
    output={};animations={};objects=props()
    heads={direction:Image.open(ROOT/f'assets/characters/mira/idle_{direction}.png').convert('RGBA').crop((0,0,32,18)) for direction in ('left','right')}
    def export(path,image):
        output[OUT/path]=png(image)
        return (OUT/path).relative_to(ROOT).as_posix()
    def animation(name,frames,cues=None,facing='left'):
        records=[]
        for index,(image,hand,held) in enumerate(frames):
            record={'file':export(Path(f'{name}_{index:02}.png'),image),'duration_ms':100}
            if hand is not None:record['hand']=list(hand)
            if held:record['held_prop']=held
            records.append(record)
        animations[name]={'frames':records,'loop':False,'anchor':list(ANCHOR),'facing':facing,'cue_ms':cues or {}}
    frames=[]
    for i in range(12):
        if i<=7:
            q=min(1,i/6);hand=mix((27,28),(24,40),q)
            im=mira_body(heads,'bend',hand,q=q)
        else:
            q=(i-7)/4;hand=mix((24,40),(27,35),q)
            im=mira_body(heads,'recover',hand,q=q)
        held='kit' if i<7 else None
        if held:im.alpha_composite(objects['kit'],(hand[0]-7,hand[1]-1))
        frames.append((im,hand,held))
    animation('place',frames,{'kit_deposit':700})
    frames=[]
    for i in range(12):
        if i==0:
            hand=(27,35);im=mira_body(heads,'care',hand)
        elif i<=6:
            q=min(1,(i-1)/4);hand=mix((37,34),(44,39),q)
            im=mira_body(heads,'recover',hand,q=1-q,direction='right')
        elif i<=8:
            q=(i-6)/3;hand=mix((44,39),(35,36),q)
            im=mira_body(heads,'recover',hand,q=q,direction='right')
        else:
            hand=mix((33,36),(26,35),(i-9)/2)
            im=mira_body(heads,'care',hand)
        held='cloth' if i>=6 else None
        if held:cloth_in_hand(im,hand)
        frames.append((im,hand,held))
    animation('take_cloth',frames,{'cloth_pickup':600},'right')
    frames=[]
    for i in range(14):
        hand=mix((26,35),(20,34),min(1,i/4))
        if 5<=i<=10:hand=(hand[0],hand[1]+(0,-1,0,1,0,0)[i-5])
        im=mira_body(heads,'care',hand);cloth_in_hand(im,hand)
        frames.append((im,hand,'cloth'))
    animation('treat',frames)
    frames=[]
    for i in range(8):
        hand=mix((20,34),(27,35),min(1,max(0,i-2)/5))
        im=mira_body(heads,'care',hand)
        if i<2:cloth_in_hand(im,hand)
        frames.append((im,hand,'cloth' if i<2 else None))
    animation('finish',frames,{'dressing_release':200})
    animation('care_idle',[(mira_body(heads,'care',(27,35)),(27,35),None)])
    ready=mira_body(heads,'care',(26,35));cloth_in_hand(ready,(26,35))
    animation('care_ready',[(ready,(26,35),'cloth')])
    frames=[]
    for i in range(14):
        if i<=4:
            q=i/4;hand=mix((27,35),(24,40),q);im=mira_body(heads,'recover',hand,q=1-q)
        elif i<=11:
            q=1-(i-4)/7;hand=mix((27,28),(24,40),q);im=mira_body(heads,'bend',hand,q=q)
        else:
            hand=(27,28);im=mira_body(heads,'stand',hand)
        held='kit' if 4<=i<12 else None
        if held:im.alpha_composite(objects['kit'],(hand[0]-7,hand[1]-1))
        frames.append((im,hand,held))
    animation('retrieve',frames,{'kit_pickup':400,'kit_stow':1200})
    patient=Image.open(ROOT/'assets/story/sanctuary_arrival/art/worker_a/injured.png').convert('RGBA')
    for name,reverse in (('offer_arm',False),('arm_rest',True)):
        frames=[]
        for i in range(8):
            q=(7-i)/7 if reverse else i/7
            im=Image.new('RGBA',(64,64));im.alpha_composite(patient,(20,10));d=ImageDraw.Draw(im)
            shoulder=(33,28);elbow=mix((35,32),(38,31),q);hand=mix((34,34),(44,34),q)
            limb(d,shoulder,elbow,hand,'#8d614d',2)
            d.line((elbow,hand),fill='#d8d7b5',width=3)
            d.point(hand,fill=P['skin'])
            frames.append((im,hand,None))
        animation(name,frames,facing='right')
    runner_head=Image.open(ROOT/'assets/characters/npcs/female_01/idle_left.png').convert('RGBA').crop((0,0,24,17))
    frames=[]
    for i in range(12):
        q=min(1,i/6) if i<=7 else 1-(i-7)/4
        hand=mix((27,29),(22,41),q)
        im=runner_body(runner_head,q,hand)
        held='linen' if i<7 else None
        if held:im.alpha_composite(objects['linen'],(hand[0]-6,hand[1]))
        frames.append((im,hand,held))
    animation('runner_place',frames,{'linen_deposit':700})
    carry_idles={};carry_walks={}
    for direction in ('front','back','left','right'):
        source=ROOT/f'assets/characters/npcs/female_01'
        idle=Image.open(source/f'idle_{direction}.png').convert('RGBA')
        carry_idles[direction]=export(Path('carry')/f'idle_{direction}.png',carry_bundle(idle,direction,objects['linen']))
        carry_walks[direction]=[]
        for i in range(1,5):
            body=Image.open(source/f'walk_{direction}/frame_{i:02}.png').convert('RGBA')
            path=export(Path('carry')/f'walk_{direction}_{i:02}.png',carry_bundle(body,direction,objects['linen']))
            carry_walks[direction].append({'file':path,'duration_ms':140})
    prop_paths={name:export(Path(name+'.png'),image) for name,image in objects.items()}
    rng=random.Random(314);data=BytesIO()
    with wave.open(data,'wb') as sound:
        sound.setparams((1,2,22050,0,'NONE','not compressed'));value=0.;samples=[]
        for i in range(3308):
            value=.6*value+.4*rng.uniform(-1,1)
            samples.append(struct.pack('<h',round(2200*value*math.sin(math.pi*i/3308)**2)))
        sound.writeframes(b''.join(samples))
    output[OUT/'cloth.wav']=data.getvalue()
    manifest={'version':2,'poses':animations,'props':prop_paths,
              'stations':{'mira':[712,318],'worker_a':[688,318],'runner':[800,350]},
              'prop_metadata':{
                  'kit':{'position':[704,328],'anchor':[7,10],'contact':[7,1]},
                  'linen_mira':{'position':[724,324],'anchor':[6,7],'contact':[6,0],'prop':'linen'},
                  'linen_runner':{'position':[790,358],'anchor':[6,7],'contact':[6,0],'prop':'linen'}},
              'carry_idles':carry_idles,'carry_walks':carry_walks,'carry_anchor':[12,30]}
    manifest['objects']={name:{**record,'file':prop_paths[record.get('prop',name)]} for name,record in manifest['prop_metadata'].items()}
    output[OUT/'art.json']=(json.dumps(manifest,indent=2)+'\n').encode()
    return output


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');args=parser.parse_args()
    for path,data in products().items():
        if args.check:assert path.exists() and path.read_bytes()==data,path
        else:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
