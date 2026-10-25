"""Liam's wooden block box and four-pose close-contact building actions."""
import hashlib
from PIL import Image,ImageDraw
from build_liam_family_front_walks import ROOT,read,write,blank
from build_liam_daisy_run_prototypes import translate
from build_daisy_routines import parts_for

OUT=ROOT/'assets/characters/liam_family/block_play'
SOURCE=ROOT/'assets/source/characters/liam_family/block_play'
PROPS=ROOT/'assets/terrain/eldenmere/liam_home/blocks'
PROP_SOURCE=ROOT/'assets/source/terrain/eldenmere/liam_home/blocks'
SIZE=(96,96);ANCHOR=(64,66)


def save_layers(directory,name,layers):
    directory.mkdir(parents=True,exist_ok=True);merged=blank(next(iter(layers.values())).size);paths=[]
    for key,layer in layers.items():
        path=directory/f'{name}_{key}.png';layer.save(path);paths.append(path.relative_to(ROOT).as_posix());merged.alpha_composite(layer)
    return merged,paths


def props():
    palette=read(ROOT/'assets/terrain/eldenmere/cottage_furniture/furniture.json')['palette']
    outline=palette['outline'];shadow=palette['wood_shadow'];base=palette['wood_base'];light=palette['wood_light'];worn=palette['wood_worn']
    blocks=[];images=[]
    for index in range(5):
        size=(5,5) if index<4 else (16,4);im=blank(size);d=ImageDraw.Draw(im)
        d.rectangle((0,0,size[0]-1,size[1]-1),fill=outline)
        d.rectangle((1,1,size[0]-2,size[1]-2),fill=base if index%2 else light)
        d.line((1,1,size[0]-2,1),fill=worn)
        if index<4:d.point((3,2),fill=shadow)
        else:d.line((4,2,10,2),fill=shadow)
        name=f'block_{index+1}';PROPS.mkdir(parents=True,exist_ok=True);im.save(PROPS/(name+'.png'));images.append(im)
        _,layers=save_layers(PROP_SOURCE,name,{'wood':im})
        blocks.append({'id':name,'image':(PROPS/(name+'.png')).relative_to(ROOT).as_posix(),'frame_size':list(size),
                       'draw_anchor':[2,2] if index<4 else [8,2],'layers_from_repo_root':layers})
    shell=blank((32,24));d=ImageDraw.Draw(shell)
    # Open top; the far rim is behind contents, the front face in front.
    d.polygon(((3,5),(27,5),(30,8),(29,20),(26,23),(3,22),(1,18),(1,8)),fill=outline)
    d.polygon(((4,7),(26,7),(28,9),(27,17),(4,17),(3,9)),fill=shadow)
    d.line((4,6,26,6),fill=worn);d.line((3,8,3,16),fill=light)
    front=blank((32,24));d=ImageDraw.Draw(front)
    d.polygon(((2,14),(28,14),(28,20),(25,22),(4,21),(2,18)),fill=outline)
    d.polygon(((4,15),(26,15),(26,20),(5,20),(4,18)),fill=base)
    d.line((4,15,26,15),fill=worn);d.line((6,19,24,19),fill=shadow)
    for x in (5,25):d.point((x,17),fill=outline)
    d.line((3,21,25,22),fill=shadow)
    states={};inside=[(8,10),(15,10),(10,13),(23,11),(15,8)]
    for count in range(6):
        contents=blank((32,24))
        for index in range(count):
            x,y=inside[index];anchor=blocks[index]['draw_anchor'];contents.alpha_composite(images[index],(x-anchor[0],y-anchor[1]))
        layers={'box_back':shell,'blocks_inside':contents,'box_front':front}
        merged,paths=save_layers(PROP_SOURCE,f'box_{count}',layers);merged.save(PROPS/f'box_{count}.png')
        states[str(count)]={'image':(PROPS/f'box_{count}.png').relative_to(ROOT).as_posix(),'layers_from_repo_root':paths}
    front.save(PROPS/'front_overlay.png')
    status=read(PROPS/'blocks.json')['status'] if (PROPS/'blocks.json').exists() else 'review'
    write(PROPS/'blocks.json',{'id':'liam.wooden_blocks','status':status,'box_frame_size':[32,24],
          'box_position':[44,180],'box_access':[80,200],'box_contact':[70,191],
          'floor_rect':[2,15,28,8],'box_states':states,'blocks':blocks,
          'front_overlay':(PROPS/'front_overlay.png').relative_to(ROOT).as_posix(),
          'palette_source':'assets/terrain/eldenmere/cottage_furniture/furniture.json'})


def parts(direction):
    spec=read(ROOT/f'assets/characters/liam/idle_{direction}.json')
    return {p.split('/')[-1].split('.')[0]:Image.open(ROOT/p).convert('RGBA') for p in spec['layers_from_repo_root']}


def kneeling(direction,lower=3,hand=None,head_lean=0):
    p=parts(direction);m=read(ROOT/'assets/characters/liam/palette.json')['materials']
    head=translate(p['head'],52+head_lean,36+lower,SIZE)
    body=translate(p['upper_body'],52,36+lower,SIZE)
    tunic=translate(p['tunic_and_hands'],52,36+lower,SIZE)
    legs=blank(SIZE);d=ImageDraw.Draw(legs)
    sign=-1 if direction=='left' else 1
    # Fold both knees beneath the tunic, retaining the original ground baseline.
    d.rectangle((61,65,66,67),fill=m['trousers'][1])
    d.line((61,66,59 if sign>0 else 68,68),fill=m['trousers'][2],width=2)
    d.line((60 if sign>0 else 67,69,65 if sign>0 else 62,69),fill=m['leather'][0],width=2)
    arm=blank(SIZE)
    if hand:
        d=ImageDraw.Draw(arm);shoulder=(64+sign*2,60+lower-3);elbow=(64+sign*5,62)
        d.line((*shoulder,*elbow),fill=m['tunic'][0],width=2)
        d.line((*elbow,*hand),fill=m['tunic'][1],width=2)
        d.point(tuple(hand),fill=m['skin'][0]);d.point((hand[0],hand[1]+1),fill=m['skin'][1])
    return {'legs':legs,'torso':body,'tunic':tunic,'head':head,'arm_and_hand':arm}


def export(name,items,duration=260,contact=None,anchor=ANCHOR,character='liam'):
    frames=[];unique=set()
    for i,(layers,hand) in enumerate(items,1):
        im,paths=save_layers(SOURCE/name,f'frame_{i:02}',layers)
        directory=OUT/name;directory.mkdir(parents=True,exist_ok=True);path=directory/f'frame_{i:02}.png';im.save(path)
        assert set(im.getchannel('A').tobytes())=={0,255};unique.add(im.tobytes())
        frames.append({'file':path.relative_to(ROOT).as_posix(),'duration_ms':duration,
                       ('nose_local' if character=='daisy' else 'hand_local'):list(hand),
                       'layers_from_repo_root':paths})
    assert len(unique)==4,name
    return {'character':character,'frame_count':4,'canvas_size':list(im.size),'duration_ms':duration*4,'draw_anchor':list(anchor),'contact_frame':contact,
            'handoff_contact_frame':contact,'frames':frames}


def actions():
    protected={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for name in ('liam','daisy') for p in (ROOT/'assets/characters'/name).rglob('*.png')}
    result={}
    for direction in ('left','right'):
        sign=-1 if direction=='left' else 1;idle=Image.open(ROOT/f'assets/characters/liam/idle_{direction}.png').convert('RGBA')
        seq=[]
        for phase in range(4):
            hand=(64+sign*4,61+phase//2)
            if phase==0:layers={'approved_idle':translate(idle,52,36,SIZE)}
            elif phase==1:
                layers={'lowered_body':translate(idle,52,37,SIZE)}
            else:layers=kneeling(direction,2 if phase==2 else 3,hand)
            seq.append((layers,hand))
        result[f'kneel_{direction}']=export(f'kneel_{direction}',seq,180)
        result[f'rise_{direction}']=export(f'rise_{direction}',list(reversed(seq)),180)
    # Every physical contact is the third pose. Other hands stay near the chest.
    specs={
      'take_left':('left',[(60,63),(57,60),(54,57),(59,61)]),
      'return_left':('left',[(59,61),(57,59),(54,57),(60,63)]),
      'place_right':('right',[(68,63),(71,60),(74,57),(69,62)]),
      'collect_right':('right',[(69,62),(72,59),(74,57),(68,61)]),
    }
    for name,(direction,hands) in specs.items():
        seq=[(kneeling(direction,3,hand,head_lean=0 if phase in (0,3) else (-1 if direction=='left' else 1)),hand) for phase,hand in enumerate(hands)]
        result[name]=export(name,seq,300,2)
    hands=[(68,60),(70,57),(72,60),(74,62)]
    react=[]
    for phase,hand in enumerate(hands):
        # Recoil, look at the fallen tower, turn/raise hand, short rug-point.
        layers=kneeling('right',3 if phase!=0 else 2,hand,head_lean=-1 if phase==0 else 0)
        react.append((layers,hand))
    result['react']=export('react',react,700)
    # Curious sniff: fixed paws/body, a small downward nose motion and ear lag.
    dog=Image.open(ROOT/'assets/characters/daisy/idle_left.png').convert('RGBA');p=parts_for(dog,'left')
    seq=[]
    for phase,dy in enumerate((0,1,2,1)):
        lag=1 if phase==3 else 0
        layers={'tail':translate(p['tail'],16,12,(64,48)),
                'body':translate(p['body'],16,12,(64,48)),
                'head':translate(p['head'],16,12+dy,(64,48)),
                'ear':translate(p['ear'],16,12+dy+lag,(64,48))}
        seq.append((layers,(17,30+dy)))
    result['curious_nudge_left']=export('curious_nudge_left',seq,250,2,(32,42),'daisy')
    status=read(OUT/'animations.json')['status'] if (OUT/'animations.json').exists() else 'review'
    write(OUT/'animations.json',{'character':'liam','status':status,'canvas_size':list(SIZE),'draw_anchor':list(ANCHOR),
          'native_offset':[52,36],'actions':result,'approved_png_sha256':protected,
          'notes':'Third pose (zero-based frame 2) is each take/place/collect/return handoff. Hand-local is the center of a separately drawn held block. Knees and hips stay grounded.'})
    assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==sha for p,sha in protected.items())


def build():
    props();actions();print('Built wooden block box, five blocks and four-pose kneeling/building/reaction actions.')


if __name__=='__main__':build()
