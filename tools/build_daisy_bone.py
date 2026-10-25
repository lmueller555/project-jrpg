"""One ivory play bone and authored four-pose dog actions with exact mouth contacts."""
import hashlib
import math
from PIL import Image,ImageDraw
from build_liam_family_front_walks import ROOT,read,write,blank
from build_liam_daisy_run_prototypes import translate
from build_daisy_routines import contact_pose,transformed,rising

OUT=ROOT/'assets/characters/daisy/bone_play'
SOURCE=ROOT/'assets/source/characters/daisy/bone_play'
PROP=ROOT/'assets/terrain/eldenmere/liam_home/bone'
PROP_SOURCE=ROOT/'assets/source/terrain/eldenmere/liam_home/bone'
SIZE=(64,48);ANCHOR=(32,42)
PALETTE={'edge':'#a89b7e','shadow':'#c6b893','base':'#e2d3ad','light':'#f5e8c6'}


def bone_images():
    im=blank((8,4));d=ImageDraw.Draw(im)
    d.rectangle((1,1,6,2),fill=PALETTE['shadow'])
    for x in (0,5):
        d.rectangle((x,0,x+2,3),fill=PALETTE['shadow']);d.point((x+1,0),fill=PALETTE['light'])
        d.rectangle((x,1,x+2,2),fill=PALETTE['base'])
    d.line((2,1,5,1),fill=PALETTE['light']);d.point((1,3),fill=PALETTE['edge']);d.point((6,3),fill=PALETTE['edge'])
    images={'horizontal':im,'vertical':im.transpose(Image.Transpose.ROTATE_90),
            'diagonal':im.rotate(-28,Image.Resampling.NEAREST,expand=True)}
    PROP.mkdir(parents=True,exist_ok=True);PROP_SOURCE.mkdir(parents=True,exist_ok=True)
    records={}
    for name,image in images.items():
        path=PROP/(name+'.png');image.save(path)
        source=PROP_SOURCE/(name+'_bone.png');image.save(source)
        records[name]={'image':path.relative_to(ROOT).as_posix(),'draw_anchor':[image.width//2,image.height//2],
                       'frame_size':list(image.size),'layers_from_repo_root':[source.relative_to(ROOT).as_posix()]}
    status=read(PROP/'bone.json')['status'] if (PROP/'bone.json').exists() else 'review'
    write(PROP/'bone.json',{'id':'daisy.play_bone','status':status,'palette':PALETTE,'variants':records,
                          'initial_center':[138,259],'solid':False,'quantity':1})
    return images


def store(directory,stem,layers):
    directory.mkdir(parents=True,exist_ok=True);im=blank(SIZE);paths=[]
    for name,layer in layers.items():
        path=directory/(stem+'_'+name+'.png');layer.save(path);paths.append(path.relative_to(ROOT).as_posix());im.alpha_composite(layer)
    return im,paths


def overlay(images,center,orientation='horizontal',visible=True,occluder=None):
    layer=blank(SIZE)
    if not visible:return layer
    image=images[orientation];layer.alpha_composite(image,(center[0]-image.width//2,center[1]-image.height//2))
    if occluder is not None:
        for y in range(SIZE[1]):
            for x in range(SIZE[0]):
                if occluder.getpixel((x,y))[3]:layer.putpixel((x,y),(0,0,0,0))
    return layer


def grip_mask(body,center,back=False,paws=None):
    mask=blank(SIZE)
    if back:return body
    # The small near-jaw edge covers the center of the held bone, preserving
    # the visible muzzle rather than painting the toy through Daisy's face.
    for dx,dy in ((0,-1),(0,0)):
        point=(center[0]+dx,center[1]+dy)
        if 0<=point[0]<64 and 0<=point[1]<48:
            pixel=body.getpixel(point)
            if pixel[3]:mask.putpixel(point,pixel)
    if paws is not None:mask.alpha_composite(paws)
    return mask


def export(name,frames,images,duration=180,facing='left',loop=False,contact=None):
    directory=OUT/name;directory.mkdir(parents=True,exist_ok=True);records=[];unique=set()
    for index,(layers,info) in enumerate(frames,1):
        body,paths=store(SOURCE/name,f'frame_{index:02}',layers)
        path=directory/f'frame_{index:02}.png';body.save(path);unique.add(body.tobytes())
        center=info['bone_local'];visible=info.get('bone_visible',True);orientation=info.get('bone_orientation','horizontal')
        mask=grip_mask(body,center,back=not visible,paws=info.pop('_paws',None))
        toy=overlay(images,center,orientation,visible,mask)
        toy_path=directory/f'frame_{index:02}_bone.png';toy.save(toy_path)
        source=SOURCE/name/f'frame_{index:02}_bone.png';toy.save(source)
        assert set(body.getchannel('A').tobytes())=={0,255}
        assert set(toy.getchannel('A').tobytes())<={0,255}
        records.append({'file':path.relative_to(ROOT).as_posix(),'bone_file':toy_path.relative_to(ROOT).as_posix(),
                        'duration_ms':duration,'layers_from_repo_root':paths,'bone_layers_from_repo_root':[source.relative_to(ROOT).as_posix()],
                        'bone_visible':visible,'bone_orientation':orientation,**info})
    assert len(unique)==4,(name,len(unique))
    return {'frame_count':4,'duration_ms':duration*4,'facing':facing,'loop':loop,'contact_frame':contact,'frames':records}


def rotate_canvas(layer,pivot,angle):
    return layer.rotate(-angle,Image.Resampling.NEAREST,center=pivot)


def lying_pose(phase=0,angle=-53):
    spec=read(ROOT/'assets/characters/daisy/lying_left/pose.json');layers={}
    for path in spec['layers_from_repo_root']:
        name=path.rsplit('/',1)[-1][:-4];im=translate(Image.open(ROOT/path).convert('RGBA'),12,12,SIZE)
        if name=='head':im=rotate_canvas(im,(26,38),angle)
        elif name=='ear':
            im=rotate_canvas(im,(26,38),angle);im=translate(im,0,1 if phase==2 else 0,SIZE)
        elif name=='tail' and phase in (1,3):
            # A one-pixel tip movement, retaining the tail root and body contact.
            tip=im.crop((45,40,51,47));im.paste((0,0,0,0),(45,40,51,47));im.alpha_composite(tip,(45,39 if phase==1 else 40))
        layers[name]=im
    paws=blank(SIZE)
    for name in ('far_forepaw','folded_foreleg'):paws.alpha_composite(layers[name])
    return layers,paws


def carry_mouth(direction,phase,frame):
    # Approved walks bake the coordinated bob into the head; their semantic
    # offset is retained in metadata, including the side-specific nose position.
    dy=frame.get('upper_body_offset',[0,0])[1]
    x,y={'left':(17,32),'right':(46,32),'front':(32,35),'back':(32,31)}[direction]
    return [x,y+dy]


def build():
    OUT.mkdir(parents=True,exist_ok=True);images=bone_images()
    protected={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
               for p in (ROOT/'assets/characters/daisy').rglob('*.png') if 'bone_play' not in p.parts}
    actions={}
    for name in ('pickup_left','drop_left'):
        frames=[]
        for phase,angle in enumerate((0,-25,-60,0)):
            _,layers,_=contact_pose('left',angle,phase,crouch=0 if phase in (0,3) else 1)
            mouth=transformed((1,20),(10,20),angle,0 if phase in (0,3) else 1)
            frames.append((layers,{'bone_local':mouth,'mouth_local':mouth,'phase':('look','lower','contact','raise')[phase]}))
        actions[name]=export(name,frames,images,220,contact=2)
    frames=[]
    for phase,angle in enumerate((0,-20,-40,-10)):
        _,layers,_=contact_pose('left',angle,phase,crouch=(0,1,2,1)[phase])
        center=transformed((1,20),(10,20),angle,(0,1,2,1)[phase])
        frames.append((layers,{'bone_local':center,'mouth_local':center}))
    actions['play_bow']=export('play_bow',frames,images,180)
    frames=[]
    for phase,(dx,dy) in enumerate(((0,0),(-1,1),(1,-1),(0,1))):
        _,layers,_=contact_pose('left',0,phase,crouch=0)
        layers['head']=translate(layers['head'],dx,dy,SIZE);layers['ear']=translate(layers['ear'],dx,dy+(1 if phase==3 else 0),SIZE)
        layers['face_detail']=translate(layers['face_detail'],dx,dy,SIZE)
        center=[17+dx,32+dy];frames.append((layers,{'bone_local':center,'mouth_local':center,'bone_orientation':'diagonal' if phase in (1,2) else 'horizontal'}))
    actions['shake_left']=export('shake_left',frames,images,150,loop=True)
    chew=[]
    for phase,angle in enumerate((-48,-56,-51,-54)):
        layers,paws=lying_pose(phase,angle);chew.append((layers,{'bone_local':[20,45],'mouth_local':[20,44], '_paws':paws}))
    actions['chew_left']=export('chew_left',chew,images,220,loop=True)
    rise=rising();settle=[]
    for phase,(body,layers) in enumerate(reversed(rise)):
        center=([17,32],[17,34],[17,36],[20,45])[phase]
        info={'bone_local':list(center),'mouth_local':list(center)}
        if phase==3:
            layers,paws=lying_pose(phase,-48);info['_paws']=paws
        settle.append((layers,info))
    actions['settle_bone']=export('settle_bone',settle,images,220,contact=3)
    # Avoid the mutated private-paw records consumed by export by rebuilds.
    rise_frames=[]
    for phase,(body,layers) in enumerate(rise):
        center=([20,45],[17,36],[17,34],[17,32])[phase]
        rise_frames.append((layers,{'bone_local':list(center),'mouth_local':list(center)}))
    actions['rise_bone']=export('rise_bone',rise_frames,images,220,contact=0)
    frames=[]
    for phase,angle in enumerate((-54,-50,-42,-34)):
        layers,paws=lying_pose(phase,angle)
        frames.append((layers,{'bone_local':[20,45],'mouth_local':[20,44],'_paws':paws}))
    actions['release_paws']=export('release_paws',frames,images,200,contact=2)
    frames=[]
    for phase,angle in enumerate((-34,-48,-56,-40)):
        layers,paws=lying_pose(phase,angle);center=[20 if phase<2 else 18,45]
        frames.append((layers,{'bone_local':center,'mouth_local':[20,44], '_paws':paws}))
    actions['nudge_left']=export('nudge_left',frames,images,180,contact=2)
    idle_frames={}
    for direction in ('front','left','right','back'):
        folder=ROOT/f'assets/characters/daisy/walk_{direction}';spec=read(folder/'animation.json');frames=[]
        for phase,frame in enumerate(spec['frames']):
            body=translate(Image.open(folder/frame['file']).convert('RGBA'),16,12,SIZE);center=carry_mouth(direction,phase,frame)
            frames.append(({'approved_walk':body},{'bone_local':center,'mouth_local':center,'bone_visible':direction!='back'}))
        actions[f'carry_walk_{direction}']=export(f'carry_walk_{direction}',frames,images,140,direction,True)
        body=translate(Image.open(ROOT/f'assets/characters/daisy/idle_{direction}.png').convert('RGBA'),16,12,SIZE)
        center=carry_mouth(direction,0,{});bodypath=OUT/f'carry_idle_{direction}.png';body.save(bodypath)
        toy=overlay(images,center,visible=direction!='back',occluder=grip_mask(body,center,back=direction=='back'))
        toypath=OUT/f'carry_idle_{direction}_bone.png';toy.save(toypath)
        source=SOURCE/f'carry_idle_{direction}.png';source.parent.mkdir(parents=True,exist_ok=True);body.save(source)
        toy_source=SOURCE/f'carry_idle_{direction}_bone.png';toy.save(toy_source)
        idle_frames[direction]={'file':bodypath.relative_to(ROOT).as_posix(),'bone_file':toypath.relative_to(ROOT).as_posix(),
                               'bone_local':center,'bone_visible':direction!='back','bone_orientation':'horizontal',
                               'layers_from_repo_root':[source.relative_to(ROOT).as_posix()],
                               'bone_layers_from_repo_root':[toy_source.relative_to(ROOT).as_posix()]}
    status=read(OUT/'animations.json')['status'] if (OUT/'animations.json').exists() else 'review'
    write(OUT/'animations.json',{'character':'daisy','status':status,'canvas_size':list(SIZE),'draw_anchor':list(ANCHOR),
          'native_offset':[16,12],'lying_offset':[12,12],'actions':actions,'idle_frames':idle_frames,
          'pickup_offset':[-10,-1],'paw_offset':[-12,3],'nudge_offset':[-14,3],
          'bone_pack':(PROP/'bone.json').relative_to(ROOT).as_posix(),'approved_png_sha256':protected})
    assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==sha for p,sha in protected.items())
    print('Built one play bone, exact contact/chew actions and all four mouth-carry directions.')


if __name__=='__main__':build()
