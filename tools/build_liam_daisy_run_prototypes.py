"""Four-pose left-facing run prototypes from approved native character parts."""
import hashlib
import math
from pathlib import Path

from PIL import Image, ImageDraw

from build_liam_family_front_walks import (
    ROOT, BACKGROUND, LABELS, read, write, blank, isolated, rgba, font, save_gif,
)

REVIEW = ROOT / 'docs/reviews/liam_daisy_run_prototypes'
CHARACTERS = ('liam', 'daisy')
FRAME_MS = 100


def translate(layer, dx=0, dy=0, size=None):
    output = blank(size or layer.size)
    output.alpha_composite(layer, (dx, dy))
    return output


def protected_inputs():
    paths = []
    for who in CHARACTERS:
        root = ROOT / f'assets/characters/{who}'
        paths += [p for p in root.glob('idle*') if p.is_file()] + [root/'palette.json']
        for direction in ('front','left','right','back'):
            paths += list((root/f'walk_{direction}').glob('*'))
    return {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.is_file()}


def tapered(draw, a, b, start_width, end_width, fill, border=None):
    """Pixel polygon with a joint, rather than a long straight limb mutation."""
    length = math.dist(a,b)
    if not length:return
    nx,ny = -(b[1]-a[1])/length, (b[0]-a[0])/length
    points = [(round(a[0]+nx*start_width/2),round(a[1]+ny*start_width/2)),
              (round(b[0]+nx*end_width/2),round(b[1]+ny*end_width/2)),
              (round(b[0]-nx*end_width/2),round(b[1]-ny*end_width/2)),
              (round(a[0]-nx*start_width/2),round(a[1]-ny*start_width/2))]
    draw.polygon(points,fill=fill)
    if border:draw.line(points+[points[0]],fill=border,width=1)


def child_template():
    poses=[]
    # Joints are authored for Liam's seven-pixel lower body. Head and shoulder
    # translation are identical; the waist bridges a one-pixel forward lean.
    legs=[
        {'near':[[12,27],[9,30],[7,34]], 'far':[[13,27],[16,30],[17,28]]},
        {'near':[[12,25],[15,28],[17,31]],'far':[[13,25],[9,26],[10,29]]},
        {'near':[[12,27],[16,30],[17,28]],'far':[[13,27],[9,30],[7,34]]},
        {'near':[[12,25],[9,26],[10,29]],'far':[[13,25],[15,28],[17,31]]},
    ]
    arms=[
        {'near':[[12,23],[15,25],[16,23]],'far':[[11,23],[9,25],[7,23]]},
        {'near':[[12,21],[13,23],[11,22]],'far':[[11,21],[10,23],[9,21]]},
        {'near':[[12,23],[9,25],[7,23]],'far':[[11,23],[14,25],[16,23]]},
        {'near':[[12,21],[10,23],[9,21]],'far':[[11,21],[13,23],[14,21]]},
    ]
    for i in range(4):
        dy = -2 if i%2 else 0
        poses.append({'id':f'{i+1:02}','phase':('contact_near','flight_near','contact_far','flight_far')[i],
                      'duration_ms':FRAME_MS,'upper_body_offset':[-1,dy],'shoulder_offset':[-1,dy],
                      'airborne':bool(i%2),'supporting_legs':[] if i%2 else ['near' if i==0 else 'far'],
                      'legs':legs[i], 'arms':arms[i]})
    return {'id':'child_24x36.run.left','frame_size':[24,36],'foot_anchor':[12,34],
            'direction':'left','proportions':'Liam, age 8; 26-pixel resting height',
            'frames':poses}


def child_leg(joints, m, far):
    im=blank((24,36));d=ImageDraw.Draw(im);hip,knee,toe=joints
    outline=m['outline'][0];trouser=m['trousers'][0 if far else 1]
    ankle=(toe[0]+1,toe[1]-2)
    tapered(d,hip,knee,3,3,trouser)
    d.line((hip,knee),fill=m['trousers'][0 if far else 2],width=1)
    # Breeches end at the knee; a small bare calf meets the boot shaft.
    tapered(d,knee,ankle,2,2,m['skin'][1 if far else 0])
    tx,ty=toe
    if ty < knee[1]:
        # The recovered heel rises toward his seat; its boot points down.
        d.rectangle((tx-1,ty-1,tx+1,ty+2),fill=outline)
        d.line((tx,ty-1,tx,ty+1),fill=m['leather'][0 if far else 1],width=1)
    else:
        d.polygon(((tx,ty-2),(tx+1,ty-2),(tx+1,ty),(tx-2,ty),(tx-2,ty-1)),fill=outline)
        d.line((tx-1,ty-1,tx,ty-1),fill=m['leather'][0 if far else 1],width=1)
    return im


def child_arm(joints,m,far):
    im=blank((24,36));d=ImageDraw.Draw(im);shoulder,elbow,hand=joints
    tapered(d,shoulder,elbow,2,2,m['tunic'][0 if far else 1])
    tapered(d,elbow,hand,2,2,m['tunic'][0 if far else 2])
    d.point((elbow[0],elbow[1]+1),fill=m['tunic'][0])
    hx,hy=hand
    d.rectangle((hx-1,hy,hx,hy+1),fill=m['skin'][1 if far else 0])
    return im


def liam():
    base=ROOT/'assets/characters/liam'
    idle=Image.open(base/'idle_left.png').convert('RGBA');m=read(base/'palette.json')['materials']
    template=child_template();head=isolated(idle,[0,0,24,21])
    torso=isolated(idle,[10,21,5,4]);hem=isolated(idle,[9,25,6,3])
    for y in range(25,28):
        for x in range(9,15):
            if hem.getpixel((x,y)) in {rgba(c) for c in m['skin']}:
                hem.putpixel((x,y),rgba(m['tunic'][0]))
    frames=[];sets=[]
    for phase in template['frames']:
        dx,dy=phase['upper_body_offset']
        chest=translate(torso,dx,dy)
        layers={'far_leg':child_leg(phase['legs']['far'],m,True),
                'near_leg':child_leg(phase['legs']['near'],m,False),
                'far_arm':child_arm(phase['arms']['far'],m,True),
                'tunic_hem':translate(hem,0,dy),'chest':chest,
                'near_arm':child_arm(phase['arms']['near'],m,False),
                'collar':translate(isolated(idle,[10,21,5,2]),dx,dy),
                'head':translate(head,dx,dy)}
        im=blank(idle.size)
        for layer in layers.values():im.alpha_composite(layer)
        frames.append(im);sets.append(layers)
    return frames,sets,template,{'source_idle':'../idle_left.png','head_rect':[0,0,24,21],
            'torso_rect':[10,21,5,4],'hem_rect':[9,25,6,3],
            'notes':'Authored bent-elbow and folded-knee run joints; original head, neck, collar and tunic pixels. Two alternating support poses and two flights.'}


def dog_template():
    # Native coordinates include four pixels of new padding on each side.
    # A compact four-pose gallop summarizes staggered footfalls, not four
    # separate still frames with the walking support pattern.
    poses=[
        ('forepaw_landing',0,1,False,['fore_left','fore_right'],
         {'fore_left':[[13,26],[12,30],[10,34]],'fore_right':[[15,26],[14,29],[12,32]],
          'hind_left':[[27,26],[24,30],[23,28]],'hind_right':[[25,26],[22,29],[22,27]]},[-1,-1],1),
        ('gather_and_hind_loading',1,-1,False,['hind_left','hind_right'],
         {'fore_left':[[13,27],[16,30],[17,29]],'fore_right':[[15,27],[18,29],[19,28]],
          'hind_left':[[25,27],[22,30],[22,34]],'hind_right':[[23,27],[21,29],[24,32]]},[2,-1],2),
        ('hind_push_off',0,1,False,['hind_left','hind_right'],
         {'fore_left':[[13,26],[10,28],[9,30]],'fore_right':[[15,26],[12,27],[11,29]],
          'hind_left':[[27,26],[29,30],[30,34]],'hind_right':[[25,26],[28,28],[30,32]]},[2,0],0),
        ('extended_flight',-2,2,True,[],
         {'fore_left':[[13,24],[10,27],[8,31]],'fore_right':[[15,24],[12,25],[10,29]],
          'hind_left':[[28,24],[31,26],[33,30]],'hind_right':[[26,24],[29,25],[31,28]]},[0,-2],-2),
    ]
    frames=[]
    for i,(name,dy,stretch,airborne,support,legs,tail,ear) in enumerate(poses):
        frames.append({'id':f'{i+1:02}','phase':name,'duration_ms':FRAME_MS,
                       'upper_body_offset':[4,dy],'shoulder_offset':[4,dy],
                       'airborne':airborne,'supporting_legs':support,'body_width_delta':stretch,
                       'legs':legs,'tail_tip_offset':tail,'ear_tip_offset':[1 if i in (2,3) else 0,ear]})
    return {'id':'quadruped_40x36.run.left','frame_size':[40,36],'foot_anchor':[20,34],
            'direction':'left','gait':'four-pose gallop prototype','frames':frames}


def dog_parts(idle):
    palette=read(ROOT/'assets/characters/daisy/palette.json')['materials']
    ear_colors={rgba(c) for key in ('gray_fur','black_spots','outline') for c in palette[key]}
    parts={k:blank(idle.size) for k in ('body','head','ear','tail')}
    for y in range(28):
        for x in range(32):
            p=idle.getpixel((x,y))
            if not p[3]:continue
            if x>=23 and y<=25:key='tail'
            elif 9<=x<=12 and 16<=y<=20 and p in ear_colors:key='ear'
            elif x<=12 and y<=20:key='head'
            else:key='body'
            parts[key].putpixel((x,y),p)
    return parts


def hinged(layer,pivot,dx,dy,tip_offset,extent,size=(40,36)):
    """Inverse nearest sampling keeps a fixed root without forward-map holes."""
    out=blank(size);px,py=pivot;tx,ty=tip_offset
    # The tail points up from its root; ears hang down from theirs.
    sign=-1 if extent<0 else 1
    factor=(abs(extent)+sign*ty)/abs(extent)
    for y in range(size[1]):
        sy=py+(y-dy-py)/factor
        influence=(sy-py)/extent
        for x in range(size[0]):
            sx=x-dx-tx*influence
            xx,yy=round(sx),round(sy)
            if 0<=xx<layer.width and 0<=yy<layer.height:
                p=layer.getpixel((xx,yy))
                if p[3]:out.putpixel((x,y),p)
    return out


def dog_leg(joints,reference,m,far):
    im=blank((40,36));d=ImageDraw.Draw(im);root,knee,toe=joints
    ankle=(toe[0],toe[1]-2)
    # Tapered, bent bones retain fur shading and a native shaggy paw tip.
    tapered(d,root,knee,4 if not far else 3,3,m['gray_fur'][0 if far else 1])
    tapered(d,knee,ankle,3,2,m['gray_fur'][0 if far else 1])
    d.line((root,knee,ankle),fill=m['gray_fur'][1 if far else 2],width=1)
    d.point((knee[0]+1,knee[1]),fill=m['gray_fur'][1 if far else 2])
    paw=reference.crop((0,5,5,8))
    if far:
        paw=paw.resize((3,3),Image.Resampling.NEAREST)
        for y in range(3):
            for x in range(3):
                p=paw.getpixel((x,y))
                if p==rgba(m['white_fur'][1]):paw.putpixel((x,y),rgba(m['white_fur'][0]))
                elif p==rgba(m['gray_fur'][1]):paw.putpixel((x,y),rgba(m['gray_fur'][0]))
    im.alpha_composite(paw,(toe[0]-paw.width//2,toe[1]-2))
    return im


def daisy():
    base=ROOT/'assets/characters/daisy';idle=Image.open(base/'idle_left.png').convert('RGBA')
    m=read(base/'palette.json')['materials'];parts=dog_parts(idle);template=dog_template()
    frames=[];sets=[];box=parts['body'].getbbox()
    for phase in template['frames']:
        dy=phase['upper_body_offset'][1];stretch=phase['body_width_delta']
        tail=hinged(parts['tail'],(23,24),4+stretch,dy,phase['tail_tip_offset'],-11)
        body=blank((40,36));crop=parts['body'].crop(box)
        body.alpha_composite(crop.resize((crop.width+stretch,crop.height),Image.Resampling.NEAREST),(box[0]+4,box[1]+dy))
        # Approved root pixels bridge the moving plume and rump.
        tail.alpha_composite(translate(isolated(idle,[22,22,3,4]),4+stretch,dy,(40,36)))
        refs={'fore':idle.crop((7,27,12,35)),'hind':idle.crop((20,27,25,35))}
        layers={'tail':tail}
        for name in ('fore_right','hind_right'):
            layers[name]=dog_leg(phase['legs'][name],refs[name.split('_')[0]],m,True)
        layers['body']=body
        for name in ('fore_left','hind_left'):
            layers[name]=dog_leg(phase['legs'][name],refs[name.split('_')[0]],m,False)
        layers['head']=translate(parts['head'],4,dy,(40,36))
        layers['ear']=hinged(parts['ear'],(10,16),4,dy,phase['ear_tip_offset'],4)
        im=blank((40,36))
        for layer in layers.values():im.alpha_composite(layer)
        frames.append(im);sets.append(layers)
    return frames,sets,template,{'source_idle':'../idle_left.png','source_padding':[4,0],
            'ear_pivot_native':[10,16],'tail_pivot_native':[23,24],
            'body_rect_native':list(box),'paw_rects_native':{'fore':[7,27,5,8],'hind':[20,27,5,8]},
            'notes':'Four-pose gallop, native face/paws/fur, gently compressed/extended torso, hinged gray ear and fluffy tail; 40px canvas adds padding without scaling the dog.'}


def review_panel(sprites,labels,title,subtitle,scale=12):
    stride=40*scale+32
    im=Image.new('RGB',(24+len(sprites)*stride,36*scale+168),BACKGROUND)
    d=ImageDraw.Draw(im);d.fontmode='1'
    d.text((24,16),title,font=font(26),fill='#26343e')
    d.text((24,56),subtitle,font=font(18),fill='#52616c')
    d.line((20,104+35*scale,im.width-20,104+35*scale),fill='#b5c1c4')
    for i,(sprite,label) in enumerate(zip(sprites,labels,strict=True)):
        canvas=translate(sprite,(40-sprite.width)//2,0,(40,36))
        large=canvas.resize((40*scale,36*scale),Image.Resampling.NEAREST)
        im.paste(large,(24+i*stride,104),large)
        d.text((24+i*stride,36*scale+128),label,font=font(20),fill='#26343e')
    return im


def export(who,result):
    frames,layers,template,recipe=result
    folder=ROOT/f'assets/characters/{who}/run_left';folder.mkdir(parents=True,exist_ok=True)
    source=ROOT/(f'assets/source/characters/liam_family/liam/run_left/parts' if who=='liam' else 'assets/source/characters/daisy/run_left/parts')
    source.mkdir(parents=True,exist_ok=True)
    template_path=f"assets/templates/{'child_24x36' if who=='liam' else 'quadruped_40x36'}/run_left/poses.json"
    write(ROOT/template_path,template)
    palette=read(folder.parent/'palette.json');allowed={rgba(c) for colors in palette['materials'].values() for c in colors}|{rgba(c) for c in palette['eyes'].values()}
    records=[];sheet=blank((4*frames[0].width,36))
    for i,(frame,parts,pose) in enumerate(zip(frames,layers,template['frames'],strict=True),1):
        assert frame.size==tuple(template['frame_size'])
        assert set(frame.getchannel('A').tobytes())=={0,255}
        assert all(not p[3] or p in allowed for p in getattr(frame,'get_flattened_data',frame.getdata)())
        bbox=frame.getbbox();assert bbox[0]>0 and bbox[2]<frame.width and bbox[3]<=35,(who,i,bbox)
        assert (bbox[3]<35)==pose['airborne'],(who,i,bbox,pose['airborne'])
        files=[]
        for name,part in parts.items():
            path=source/f'frame_{i:02}_{name}.png';part.save(path);files.append(path.relative_to(ROOT).as_posix())
        filename=f'frame_{i:02}.png';frame.save(folder/filename);sheet.alpha_composite(frame,((i-1)*frame.width,0))
        records.append(dict(pose,file=filename,rect=[(i-1)*frame.width,0,frame.width,36],layers_from_repo_root=files))
    assert len({im.tobytes() for im in frames})==4
    sheet.save(folder/'spritesheet.png')
    status=read(folder/'animation.json')['status'] if (folder/'animation.json').exists() else 'review'
    recipe.update(character=who,status=status,template=template_path,
                  approved_idle_sha256=hashlib.sha256((folder.parent/'idle_left.png').read_bytes()).hexdigest())
    write(folder/'recipe.json',recipe)
    write(folder/'animation.json',{'character':who,'animation':'run.left','status':status,'image':'spritesheet.png',
          'frame_size':template['frame_size'],'foot_anchor':template['foot_anchor'],'loop':True,'duration_ms':400,
          'template':template_path,'recipe':'recipe.json','offsets_baked_into_pixels':True,'frames':records})
    views=[review_panel([im],[LABELS[who]],f'{LABELS[who]} / left-facing run','4 frames | 100 ms per frame | prototype for review',16) for im in frames]
    save_gif(REVIEW/f'{who}_run.gif',views,FRAME_MS)
    slow=[review_panel([im],[LABELS[who]],f'{LABELS[who]} / left-facing run','Slow motion | 300 ms per frame | same four poses',16) for im in frames]
    save_gif(REVIEW/f'{who}_run_slow.gif',slow,300)
    views[0].save(REVIEW/f'{who}_run.png')
    review_panel(frames,[r['phase'].replace('_',' ').title() for r in records],f'{LABELS[who]} / four running poses',
                 'Ground guide remains fixed; airborne poses visibly clear it',8).save(REVIEW/f'{who}_frames.png')
    return frames


def build():
    REVIEW.mkdir(parents=True,exist_ok=True);protected=protected_inputs()
    animations={who:export(who,liam() if who=='liam' else daisy()) for who in CHARACTERS}
    views=[review_panel([animations[who][i] for who in CHARACTERS],['Liam','Daisy'],
                       'Liam and Daisy / four-frame runs','400 ms cycles | same native scale | prototype review',14) for i in range(4)]
    save_gif(REVIEW/'both_running.gif',views,FRAME_MS)
    slow=[review_panel([animations[who][i] for who in CHARACTERS],['Liam','Daisy'],
                      'Liam and Daisy / four-frame runs','Slow motion | 300 ms per frame | same native scale',14) for i in range(4)]
    save_gif(REVIEW/'both_running_slow.gif',slow,300)
    views[0].save(REVIEW/'both_running.png')
    # Walking and running clocks stay independent. Their 560/400ms loops
    # coincide after 2800ms; 20ms ticks represent every transition exactly.
    walk={who:[Image.open(ROOT/f'assets/characters/{who}/walk_left/frame_{i:02}.png').convert('RGBA') for i in range(1,5)] for who in CHARACTERS}
    comparison=[]
    for tick in range(0,2800,20):
        sprites=[sprite for who in CHARACTERS for sprite in (walk[who][tick//140%4],animations[who][tick//100%4])]
        comparison.append(review_panel(sprites,['Liam / walk','Liam / run','Daisy / walk','Daisy / run'],
                          'Approved walks and running prototypes','Independent clocks | walk 140 ms/frame; run 100 ms/frame',8))
    save_gif(REVIEW/'walk_run_comparison.gif',comparison,20)
    assert protected==protected_inputs(),'Approved idles or walks changed'
    status='approved' if all(read(ROOT/f'assets/characters/{who}/run_left/animation.json')['status']=='approved' for who in CHARACTERS) else 'review'
    write(REVIEW/'animations.json',{'status':status,'new_directions':['left'],'frame_count':4,'frame_duration_ms':FRAME_MS,
          'cycle_duration_ms':400,'protected_inputs_sha256':protected,
          'animations':{who:f'assets/characters/{who}/run_left/animation.json' for who in CHARACTERS}})
    print('Built two four-frame left run prototypes, normal/slow loops and independently timed walk comparisons.')


if __name__=='__main__':build()
