"""Four-pose standing, settling, eating and lapping from approved Daisy parts."""
import hashlib
import math
from pathlib import Path

from PIL import Image,ImageDraw

from build_liam_family_front_walks import ROOT,read,write,blank,isolated,rgba
from build_liam_daisy_run_prototypes import dog_parts as left_parts,translate,hinged
from build_liam_daisy_directional_runs import dog_parts as other_parts

OUT=ROOT/'assets/characters/daisy/house_routines'
SOURCE=ROOT/'assets/source/characters/daisy/house_routines'
SIZE=(64,48)
ANCHOR=(32,42)
TONGUE='#dc9c91'


def transformed(point,pivot,angle,dy=0):
    a=math.radians(angle);c,s=math.cos(a),math.sin(a)
    x,y=point[0]-pivot[0],point[1]-pivot[1]
    return [round(pivot[0]+x*c-y*s+16),round(pivot[1]+x*s+y*c+12+dy)]


def rotated(layer,pivot,angle,dy=0,offset=(16,12)):
    out=blank(SIZE);a=math.radians(angle);c,s=math.cos(a),math.sin(a)
    for y in range(SIZE[1]):
        for x in range(SIZE[0]):
            xx,yy=x-offset[0]-pivot[0],y-offset[1]-dy-pivot[1]
            sx=round(pivot[0]+xx*c+yy*s);sy=round(pivot[1]-xx*s+yy*c)
            if 0<=sx<layer.width and 0<=sy<layer.height:
                p=layer.getpixel((sx,sy))
                if p[3]:out.putpixel((x,y),p)
    return out


def parts_for(idle,direction):
    if direction=='left':
        p=left_parts(idle);return {'head':p['head'],'ear':p['ear'],'body':p['body'],'tail':p['tail']}
    p=other_parts(idle,'right')
    return {'head':p['head'],'ear':p['ear_right'],'body':p['body'],'tail':p['tail']}


def contact_pose(direction,angle,phase=0,crouch=1,tongue=False,jaw=False):
    base=ROOT/'assets/characters/daisy';idle=Image.open(base/f'idle_{direction}.png').convert('RGBA')
    p=parts_for(idle,direction);pivot=(23,20) if direction=='right' else (10,20)
    # Fixed feet; only the front of the torso crouches, keeping hips and tail rooted.
    body=blank(SIZE)
    for y in range(36):
        for x in range(32):
            pixel=p['body'].getpixel((x,y))
            if pixel[3]:
                lower=crouch if (x>=19 if direction=='right' else x<=13) else 0
                body.putpixel((x+16,y+12+lower),pixel)
    tail=hinged(p['tail'],(8,24) if direction=='right' else (23,24),4,0,
                [((0,1,0,-1)[phase])*(-1 if direction=='right' else 1),0],-11)
    tail=translate(tail,12,12,SIZE)
    # Keep the native tail/body overlap fixed through its very small tip sway.
    root=[7,22,3,4] if direction=='right' else [22,22,3,4]
    tail.alpha_composite(translate(isolated(idle,root),16,12,SIZE))
    ear=p['ear'].copy();lag=1 if phase==2 else 0
    if lag:
        base_row=18
        for y in range(20,base_row-1,-1):
            for x in range(32):
                pixel=ear.getpixel((x,y))
                if pixel[3]:ear.putpixel((x,y+1),pixel)
    layers={'tail':tail,'feet':translate(isolated(idle,[0,28,32,8]),16,12,SIZE),
            'torso':body,'head':rotated(p['head'],pivot,angle,crouch),
            'ear':rotated(ear,pivot,angle,crouch)}
    muzzle=(30,18) if direction=='right' else (1,18)
    mouth=transformed(muzzle,pivot,angle,crouch)
    detail=blank(SIZE);d=ImageDraw.Draw(detail)
    # Explicit eye landmarks survive nearest-neighbor head rotation.
    eye=read(base/f'idle_{direction}.json')['eyes']['top_pixels'][0]
    palette=read(base/'palette.json')
    for point,color in ((eye,palette['eyes']['pupil']),([eye[0],eye[1]+1],palette['eyes']['iris'])):
        d.point(tuple(transformed(point,pivot,angle,crouch)),fill=color)
    if jaw:
        d.point((mouth[0]+(-2 if direction=='right' else 2),mouth[1]+1),fill=palette['materials']['white_fur'][0])
    if tongue:d.point((mouth[0]-1,mouth[1]),fill=TONGUE)
    layers['face_detail']=detail
    image=blank(SIZE)
    for layer in layers.values():image.alpha_composite(layer)
    return image,layers,mouth


def rising():
    base=ROOT/'assets/characters/daisy';idle=Image.open(base/'idle_left.png').convert('RGBA')
    p=parts_for(idle,'left');lying=Image.open(base/'lying_left/pose.png').convert('RGBA')
    frames=[(translate(lying,12,12,SIZE),{'approved_lying':translate(lying,12,12,SIZE)})]
    for head_dy,body_dy,angle in ((4,3,60),(2,1,30)):
        tail=rotated(p['tail'],(23,24),angle,body_dy)
        layers={'tail':tail,'feet':translate(isolated(idle,[0,28,32,8]),16,12,SIZE),
                'torso':translate(p['body'],16,12+body_dy,SIZE),
                'head':translate(p['head'],16,12+head_dy,SIZE),
                'ear':translate(p['ear'],16,12+head_dy,SIZE)}
        image=blank(SIZE)
        for layer in layers.values():image.alpha_composite(layer)
        frames.append((image,layers))
    upright=translate(idle,16,12,SIZE)
    frames.append((upright,{'approved_idle':upright}))
    return frames


def export(name,items,duration,direction,loop=False):
    directory=OUT/name;directory.mkdir(parents=True,exist_ok=True);records=[]
    for i,(image,layers,info) in enumerate(items,1):
        paths=[];reconstructed=blank(SIZE)
        for layer_name,layer in layers.items():
            path=SOURCE/name/f'frame_{i:02}_{layer_name}.png';path.parent.mkdir(parents=True,exist_ok=True)
            layer.save(path);paths.append(path.relative_to(ROOT).as_posix());reconstructed.alpha_composite(layer)
        assert reconstructed.tobytes()==image.tobytes()
        assert set(image.getchannel('A').tobytes())=={0,255}
        box=image.getbbox();assert box[0]>0 and box[2]<64 and box[3]<=47,(name,i,box)
        filename=f'frame_{i:02}.png';image.save(directory/filename)
        records.append({'file':(directory/filename).relative_to(ROOT).as_posix(),'duration_ms':duration,
                        'layers_from_repo_root':paths,**info})
    return {'frame_count':4,'duration_ms':duration*4,'facing':direction,'loop':loop,'frames':records}


def build():
    OUT.mkdir(parents=True,exist_ok=True)
    protected=[p for p in (ROOT/'assets/characters/daisy').rglob('*.png') if 'house_routines' not in p.parts]
    hashes={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
    actions={};rise=rising()
    actions['stand_up']=export('stand_up',[(im,parts,{'phase':phase}) for (im,parts),phase in zip(rise,('rest','lift_chest','raise_hips','stand'))],180,'left')
    actions['settle_down']=export('settle_down',[(im,parts,{'phase':phase}) for (im,parts),phase in zip(reversed(rise),('stand','fold_hips','lower_chest','rest'))],180,'left')
    for kind,direction,sign in (('food','right',1),('water','left',-1)):
        lower=[]
        for i,angle in enumerate((0,10,20,28)):
            image,layers,mouth=contact_pose(direction,sign*angle,i,crouch=0 if i==0 else 1)
            lower.append((image,layers,{'phase':'lower_head','mouth_local':mouth,'contact':i==3}))
        actions[f'lower_{kind}']=export(f'lower_{kind}',lower,160,direction)
        actions[f'raise_{kind}']=export(f'raise_{kind}',list(reversed(lower)),160,direction)
        poses=[];angles=(28,18,22,24) if kind=='food' else (24,28,20,22)
        names=('take_bite','lift','chew','swallow') if kind=='food' else ('dip','lap','retract','swallow')
        for i,(angle,phase) in enumerate(zip(angles,names)):
            image,layers,mouth=contact_pose(direction,sign*angle,i,tongue=kind=='water' and i==1,jaw=kind=='food' and i==2)
            poses.append((image,layers,{'phase':phase,'mouth_local':mouth,'contact':i==0 if kind=='food' else i in (0,1)}))
        key='eat' if kind=='food' else 'drink'
        actions[key]=export(key,poses,180 if kind=='food' else 100,direction,True)
    status=read(OUT/'animations.json')['status'] if (OUT/'animations.json').exists() else 'review'
    write(OUT/'animations.json',{'character':'daisy','status':status,'canvas_size':list(SIZE),'draw_anchor':list(ANCHOR),
          'native_offset':[16,12],'lying_offset':[12,12],'lying_image':'assets/characters/daisy/lying_left/pose.png',
          'sprite_root':'assets/characters/daisy','tongue_color':TONGUE,'actions':actions,
          'approved_png_sha256':hashes})
    assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==sha for p,sha in hashes.items())
    print('Built Daisy standing/settling and four-frame eating/drinking actions; approved sprites unchanged.')


if __name__=='__main__':build()
