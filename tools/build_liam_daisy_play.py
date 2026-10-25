"""Four-pose invitation, excited hops/wag, and mattress-registered bed actions."""
import hashlib
from PIL import Image,ImageDraw
from build_liam_family_front_walks import ROOT,read,write,blank
from build_daisy_routines import parts_for,rotated
from build_liam_daisy_run_prototypes import translate,hinged

OUT=ROOT/'assets/characters/liam_family/play_routine'
SOURCE=ROOT/'assets/source/characters/liam_family/play_routine'


def export(name,frames,duration,anchor,landmarks=None):
    records=[]
    for index,layers in enumerate(frames,1):
        merged=blank(next(iter(layers.values())).size);paths=[]
        for key,layer in layers.items():
            path=SOURCE/name/f'frame_{index:02}_{key}.png';path.parent.mkdir(parents=True,exist_ok=True)
            layer.save(path);paths.append(path.relative_to(ROOT).as_posix());merged.alpha_composite(layer)
        path=OUT/name/f'frame_{index:02}.png';path.parent.mkdir(parents=True,exist_ok=True);merged.save(path)
        assert set(merged.getchannel('A').tobytes())=={0,255}
        records.append({'file':path.relative_to(ROOT).as_posix(),'duration_ms':duration,'layers_from_repo_root':paths})
    return {'frame_count':4,'draw_anchor':anchor,'duration_ms':duration*4,'frames':records,'landmarks':landmarks or {}}


def build():
    protected={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
               for name in ('liam','daisy') for p in (ROOT/'assets/characters'/name).rglob('*.png')}
    actions={};size=(96,96)
    for direction in ('left','right'):
        idle=Image.open(ROOT/f'assets/characters/liam/idle_{direction}.png').convert('RGBA')
        parts=read(ROOT/f'assets/characters/liam/idle_{direction}.json')['layers_from_repo_root']
        layers={p.split('/')[-1].split('.')[0]:Image.open(ROOT/p).convert('RGBA') for p in parts}
        frames=[]
        for phase in range(4):
            body=translate(idle,52,36,size)
            # A compact hand gesture beside the chest, with a one-pixel lean.
            arm=blank(size);d=ImageDraw.Draw(arm);sign=-1 if direction=='left' else 1
            x=64+sign*4;y=60
            if phase in (1,2):
                skin=read(ROOT/'assets/characters/liam/palette.json')['materials']['skin'][0]
                tunic=read(ROOT/'assets/characters/liam/palette.json')['materials']['tunic'][1]
                d.line((x,y,x+sign*(2 if phase==1 else 3),y-2),fill=tunic,width=2)
                d.point((x+sign*(3 if phase==1 else 4),y-2),fill=skin)
            if phase==2:body=translate(body,sign,1,size)
            if phase==3:body=translate(body,0,1,size)
            frames.append({'body':body,'hand_gesture':arm})
        actions[f'invite_{direction}']=export(f'invite_{direction}',frames,500,[64,66])
    for direction in ('left','right'):
        idle=Image.open(ROOT/f'assets/characters/daisy/idle_{direction}.png').convert('RGBA');parts=parts_for(idle,direction)
        pivot=(23,24) if direction=='left' else (8,24)
        for name in ('hop','wag'):
            frames=[]
            for phase in range(4):
                tail=hinged(parts['tail'],pivot,4,0,[(0,-1,0,1)[phase],0],-11)
                dy=(1,-1,-3,1)[phase] if name=='hop' else 0
                ear=translate(parts['ear'],0,(0,1,-1,1)[phase],(32,36))
                layers={'tail':translate(tail,16,12+dy,(64,48)),
                        'body':translate(parts['body'],16,12+dy,(64,48)),
                        'head':translate(parts['head'],16,12+dy,(64,48)),
                        'ear':translate(ear,16,12+dy,(64,48))}
                if name=='wag':layers['tail']=rotated(parts['tail'],pivot,(0,16,0,-16)[phase])
                key=f'{name}_{direction}';frames.append(layers)
            actions[key]=export(key,frames,140 if name=='hop' else 180,[32,42],{'body_lift_px':[0,2,4,0] if name=='hop' else [0]*4})
    bed=Image.open(ROOT/'assets/terrain/eldenmere/cottage_furniture/sprites/bed.png').convert('RGBA')
    # Liam remains at the walkable bedside [88,246]. Canvas origin is [24,180].
    overlay=blank(size);overlay.alpha_composite(bed.crop((0,29,48,72)),(12,53))
    front=Image.open(ROOT/'assets/characters/liam/idle_front.png').convert('RGBA')
    head=front.crop((6,9,18,22));closed=head.copy();d=ImageDraw.Draw(closed)
    eyes=read(ROOT/'assets/characters/liam/idle_front.json')['eyes']['top_pixels']
    skin=read(ROOT/'assets/characters/liam/palette.json')['materials']['skin'][0]
    for x,y in eyes:
        if 6<=x<18 and 9<=y<22:
            d.point((x-6,y-9),fill=skin);d.point((x-6,y-8),fill='#71452c')
    frames=[{'body':translate(Image.open(ROOT/'assets/characters/liam/idle_left.png').convert('RGBA'),52,36,size)}]
    frames.append({'body':translate(front,40,30,size),'quilt_and_frame':overlay})
    frames.append({'head_on_pillow':translate(head,32,40,size),'quilt_and_frame':overlay})
    frames.append({'head_on_pillow':translate(closed,30,39,size),'quilt_and_frame':overlay})
    actions['settle_bed']=export('settle_bed',frames,300,[64,66],{'bed_position':[36,204],'bedside':[88,246],'head_on_pillow_world':[60,225]})
    actions['leave_bed']=export('leave_bed',list(reversed(frames)),220,[64,66])
    status=read(OUT/'animations.json')['status'] if (OUT/'animations.json').exists() else 'review'
    write(OUT/'animations.json',{'status':status,'actions':actions,'approved_png_sha256':protected})
    assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==sha for p,sha in protected.items())
    print('Built Liam/Daisy invitation, hop, wag and bed actions; approved art unchanged.')


if __name__=='__main__':build()
