"""Complete the four-frame run views while protecting approved left runs."""
import copy
import hashlib

from PIL import Image, ImageDraw

from build_liam_daisy_run_prototypes import (
    ROOT, FRAME_MS, CHARACTERS, LABELS, read, write, blank, isolated, rgba,
    translate, tapered, child_leg, child_arm, hinged, dog_leg, review_panel,
    save_gif, protected_inputs,
)

DIRECTIONS=('front','right','back')
ALL_DIRECTIONS=('front','left','right','back')
REVIEW=ROOT/'docs/reviews/liam_daisy_directional_runs'


def child_template(direction):
    source=read(ROOT/'assets/templates/child_24x36/run_left/poses.json')
    if direction=='right':
        data=copy.deepcopy(source);data.update(id='child_24x36.run.right',direction='right')
        for phase in data['frames']:
            phase['upper_body_offset'][0]=phase['shoulder_offset'][0]=1
            for group in ('arms','legs'):
                phase[group]={name:[[23-x,y] for x,y in joints] for name,joints in phase[group].items()}
        return data
    legs=[
        {'left':[[10,27],[9,30],[8,34]], 'right':[[14,27],[15,28],[15,30]]},
        {'left':[[10,25],[9,27],[10,30]],'right':[[14,25],[15,26],[15,31]]},
    ]
    arms=[
        {'left':[[9,23],[7,25],[8,26]],'right':[[14,23],[16,25],[13,24]]},
        {'left':[[9,21],[7,23],[9,24]],'right':[[14,21],[16,23],[14,22]]},
    ]
    for group in (legs,arms):
        for index in (0,1):
            group.append({name:[[23-x,y] for x,y in group[index]['right' if name=='left' else 'left']]
                          for name in ('left','right')})
    frames=[]
    for i in range(4):
        dy=-2 if i%2 else 0
        frames.append({'id':f'{i+1:02}','phase':('contact_left','flight_left','contact_right','flight_right')[i],
                       'duration_ms':FRAME_MS,'upper_body_offset':[0,dy],'shoulder_offset':[0,dy],
                       'airborne':bool(i%2),'supporting_legs':[] if i%2 else ['left' if i==0 else 'right'],
                       'legs':legs[i],'arms':arms[i]})
    return {'id':f'child_24x36.run.{direction}','frame_size':[24,36], 'foot_anchor':[12,34],
            'direction':direction,'proportions':source['proportions'],'frames':frames}


def child_axial_leg(joints,m,far,back):
    im=blank((24,36));d=ImageDraw.Draw(im);hip,knee,toe=joints
    ankle=(toe[0],toe[1]-2)
    tapered(d,hip,knee,3,3,m['trousers'][0 if far else 1])
    d.line((hip,knee),fill=m['trousers'][0 if far else 2],width=1)
    tapered(d,knee,ankle,2,2,m['skin'][1 if far else 0])
    tx,ty=toe;d.rectangle((tx-1,ty-2,tx+2,ty),fill=m['outline'][0])
    d.rectangle((tx,ty-2,tx+1,ty-1),fill=m['leather'][0 if far or back else 1])
    if back:d.point((tx,ty-1),fill=m['leather'][1])
    return im


def liam(direction):
    base=ROOT/'assets/characters/liam';idle=Image.open(base/f'idle_{direction}.png').convert('RGBA')
    m=read(base/'palette.json')['materials'];template=child_template(direction)
    torso_rect=[9,21,5,4] if direction=='right' else [9,21,6,4]
    collar_rect=[9,21,5,2] if direction=='right' else [8,21,8,2] if direction=='back' else [9,21,6,2]
    head=isolated(idle,[0,0,24,21]);torso=isolated(idle,torso_rect);hem=isolated(idle,[9,25,6,3])
    for y in range(25,28):
        for x in range(9,15):
            if hem.getpixel((x,y)) in {rgba(c) for c in m['skin']}:hem.putpixel((x,y),rgba(m['tunic'][0]))
    frames=[];sets=[]
    for i,pose in enumerate(template['frames']):
        dx,dy=pose['upper_body_offset'];layers={}
        if direction=='right':
            # Reflect only the approved left limb geometry. The right-facing
            # head, hair, eyes, collar and torso come from their own idle.
            for name in ('far','near'):
                joints=[[23-x,y] for x,y in pose['legs'][name]]
                layers[f'{name}_leg']=child_leg(joints,m,name=='far').transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            joints=[[23-x,y] for x,y in pose['arms']['far']]
            layers['far_arm']=child_arm(joints,m,True).transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        else:
            near='left' if i<2 else 'right';far='right' if near=='left' else 'left'
            for name in (far,near):layers[f'{name}_leg']=child_axial_leg(pose['legs'][name],m,name==far,direction=='back')
            layers['far_arm']=child_arm(pose['arms'][far],m,True)
        layers['tunic_hem']=translate(hem,0,dy)
        layers['chest']=translate(torso,dx,dy)
        if direction=='right':
            joints=[[23-x,y] for x,y in pose['arms']['near']]
            layers['near_arm']=child_arm(joints,m,False).transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        else:layers['near_arm']=child_arm(pose['arms'][near],m,False)
        layers['collar']=translate(isolated(idle,collar_rect),dx,dy)
        layers['head']=translate(head,dx,dy)
        image=blank(idle.size)
        for layer in layers.values():image.alpha_composite(layer)
        frames.append(image);sets.append(layers)
    return frames,sets,template,{'source_idle':f'../idle_{direction}.png','head_rect':[0,0,24,21],
            'torso_rect':torso_rect,'collar_rect':collar_rect,'hem_rect':[9,25,6,3],
            'notes':'Approved four-pose human run cadence, paired head/shoulder bob, bent elbows, opposite steps and two flights. Each view retains its own approved appearance.'}


def dog_template(direction):
    source=read(ROOT/'assets/templates/quadruped_40x36/run_left/poses.json')
    if direction=='right':
        data=copy.deepcopy(source);data.update(id='quadruped_40x36.run.right',direction='right')
        for pose in data['frames']:
            pose['legs']={name.replace('left','SIDE').replace('right','left').replace('SIDE','right'):
                          [[39-x,y] for x,y in joints] for name,joints in pose['legs'].items()}
            pose['tail_tip_offset'][0]*=-1;pose['ear_tip_offset'][0]*=-1
        return data
    frames=[]
    for i,reference in enumerate(source['frames']):
        dy=reference['upper_body_offset'][1]
        if direction=='front':
            legs=[
                {'fore_left':[[17,27],[16,30],[16,34]],'fore_right':[[23,27],[24,30],[24,34]],
                 'hind_left':[[16,26],[15,29],[16,29]],'hind_right':[[25,26],[26,29],[25,29]]},
                {'fore_left':[[17,28],[18,31],[18,29]],'fore_right':[[23,28],[22,30],[22,29]],
                 'hind_left':[[16,27],[15,29],[15,32]],'hind_right':[[25,27],[26,29],[26,32]]},
                {'fore_left':[[17,27],[16,28],[16,30]],'fore_right':[[23,27],[24,28],[24,30]],
                 'hind_left':[[16,26],[15,29],[15,32]],'hind_right':[[25,26],[26,29],[26,32]]},
                {'fore_left':[[17,25],[16,27],[16,31]],'fore_right':[[23,25],[24,27],[24,31]],
                 'hind_left':[[16,24],[15,26],[15,29]],'hind_right':[[25,24],[26,26],[26,29]]},
            ][i]
            floors={name:34 if name.startswith('fore') else 32 for name in legs}
        else:
            legs=[
                {'fore_left':[[15,26],[14,29],[14,32]],'fore_right':[[23,26],[24,29],[24,32]],
                 'hind_left':[[14,27],[15,30],[16,30]],'hind_right':[[22,27],[21,30],[20,30]]},
                {'fore_left':[[15,27],[16,30],[17,29]],'fore_right':[[23,27],[22,30],[21,29]],
                 'hind_left':[[14,28],[13,31],[13,34]],'hind_right':[[22,28],[23,31],[23,34]]},
                {'fore_left':[[15,26],[14,28],[14,29]],'fore_right':[[23,26],[24,28],[24,29]],
                 'hind_left':[[14,27],[13,30],[13,34]],'hind_right':[[22,27],[23,30],[23,34]]},
                {'fore_left':[[15,24],[14,26],[14,29]],'fore_right':[[23,24],[24,26],[24,29]],
                 'hind_left':[[14,25],[13,28],[13,31]],'hind_right':[[22,25],[23,28],[23,31]]},
            ][i]
            floors={name:34 if name.startswith('hind') else 32 for name in legs}
        pose={k:copy.deepcopy(v) for k,v in reference.items() if k not in ('body_width_delta','legs')}
        pose.update(legs=legs,contact_rows=floors,body_height_delta=(0,-1,0,1)[i],
                    tail_tip_offset=[(-1,2,2,0)[i],(-1,-1,0,-2)[i]],
                    ear_tip_offsets={'left':[-1 if i in (2,3) else 0,(1,2,0,-2)[i]],
                                     'right':[1 if i in (2,3) else 0,(1,2,0,-2)[i]]})
        frames.append(pose)
    return {'id':f'quadruped_40x36.run.{direction}','frame_size':[40,36],'foot_anchor':[20,34],
            'direction':direction,'gait':'four-pose gallop','frames':frames}


def dog_parts(idle,direction):
    m=read(ROOT/'assets/characters/daisy/palette.json')['materials']
    gray={rgba(c) for key in ('gray_fur','black_spots','outline') for c in m[key]}
    parts={k:blank(idle.size) for k in ('tail','body','head','ear_left','ear_right')}
    for y in range(29 if direction=='front' else 28):
        for x in range(32):
            p=idle.getpixel((x,y))
            if not p[3]:continue
            if direction=='right':
                tail=x<=8 and y<=25;head=x>=19 and y<=20
                ear='right' if 20<=x<=23 and 16<=y<=20 and p in gray else None
            elif direction=='front':
                tail=(x>=24 and y<=24) or (x>=23 and 21<=y<=23)
                head=y<=20
                ear='left' if 9<=x<=12 and 15<=y<=20 and p in gray else 'right' if 20<=x<=23 and 15<=y<=20 and p in gray else None
            else:
                tail=x>=20 and y<=26;head=y<=18
                ear='left' if 5<=x<=8 and 15<=y<=18 and p in gray else 'right' if 14<=x<=16 and 15<=y<=18 and p in gray else None
            key='tail' if tail else 'ear_'+ear if ear else 'head' if head else 'body'
            parts[key].putpixel((x,y),p)
    return parts


def daisy(direction):
    base=ROOT/'assets/characters/daisy';idle=Image.open(base/f'idle_{direction}.png').convert('RGBA')
    m=read(base/'palette.json')['materials'];template=dog_template(direction);parts=dog_parts(idle,direction)
    config={
        'right':{'tail_pivot':[8,24],'tail_extent':-11,'root_rect':[7,22,3,4],
                 'ears':{'right':[21,16]},'ear_extent':4,
                 'paws':{'fore':(20,27,25,35),'hind':(6,27,11,35)}},
        'front':{'tail_pivot':[23,23],'tail_extent':-9,'root_rect':[22,21,3,4],
                 'ears':{'left':[11,15],'right':[21,15]},'ear_extent':5,
                 'paws':{'left':(11,27,16,35),'right':(17,27,22,35)}},
        'back':{'tail_pivot':[20,24],'tail_extent':-9,'root_rect':[18,22,4,4],
                'ears':{'left':[7,15],'right':[15,15]},'ear_extent':4,
                'paws':{'left':(8,27,13,35),'right':(15,27,20,35)}},
    }[direction]
    box=parts['body'].getbbox();frames=[];sets=[]
    for phase in template['frames']:
        dy=phase['upper_body_offset'][1];stretch=phase.get('body_width_delta',0)
        taildx=4-stretch if direction=='right' else 4
        tail=hinged(parts['tail'],config['tail_pivot'],taildx,dy,phase['tail_tip_offset'],config['tail_extent'])
        tail.alpha_composite(translate(isolated(idle,config['root_rect']),taildx,dy,(40,36)))
        # The front tail's narrow native root needs a filled overlap at the hip.
        if direction=='front':
            d=ImageDraw.Draw(tail);d.polygon(((26,22+dy),(28,22+dy),(29,24+dy),(26,25+dy)),fill=m['gray_fur'][0])
        body=blank((40,36));crop=parts['body'].crop(box)
        size=(crop.width+stretch,crop.height+phase.get('body_height_delta',0))
        body.alpha_composite(crop.resize(size,Image.Resampling.NEAREST),(box[0]+4-stretch,box[1]+dy))
        layers={'tail':tail}
        far_names=('fore_left','hind_left') if direction=='right' else ('hind_left','hind_right') if direction=='front' else ('fore_left','fore_right')
        near_names=[name for name in phase['legs'] if name not in far_names]
        def limb(name):
            key=name.split('_')[0] if direction=='right' else name.split('_')[1]
            return dog_leg(phase['legs'][name],idle.crop(config['paws'][key]),m,name in far_names)
        for name in far_names:layers[name]=limb(name)
        layers['body']=body
        for name in near_names:layers[name]=limb(name)
        layers['head']=translate(parts['head'],4,dy,(40,36))
        for side,pivot in config['ears'].items():
            tip=phase['ear_tip_offset'] if direction=='right' else phase['ear_tip_offsets'][side]
            layers['ear_'+side]=hinged(parts['ear_'+side],pivot,4,dy,tip,config['ear_extent'])
        image=blank((40,36))
        for layer in layers.values():image.alpha_composite(layer)
        frames.append(image);sets.append(layers)
    return frames,sets,template,{'source_idle':f'../idle_{direction}.png','source_padding':[4,0],
            'tail_pivot_native':config['tail_pivot'],'ear_pivots_native':config['ears'],'body_rect_native':list(box),
            'paw_rects_native':{name:list(rect) for name,rect in config['paws'].items()},
            'notes':'Approved four-pose gallop and 400ms cadence. Own directional face, coat and paw pixels; hinged ear tips and tail, stable roots, one extended flight.'}


def export(who,direction,result):
    frames,sets,template,recipe=result
    folder=ROOT/f'assets/characters/{who}/run_{direction}';folder.mkdir(parents=True,exist_ok=True)
    source=ROOT/(f'assets/source/characters/liam_family/liam/run_{direction}/parts' if who=='liam' else f'assets/source/characters/daisy/run_{direction}/parts')
    source.mkdir(parents=True,exist_ok=True)
    template_path=f"assets/templates/{'child_24x36' if who=='liam' else 'quadruped_40x36'}/run_{direction}/poses.json"
    write(ROOT/template_path,template)
    palette=read(folder.parent/'palette.json');allowed={rgba(c) for ramp in palette['materials'].values() for c in ramp}|{rgba(c) for c in palette['eyes'].values()}
    sheet=blank((frames[0].width*4,36));records=[]
    for i,(im,layers,pose) in enumerate(zip(frames,sets,template['frames'],strict=True),1):
        assert im.size==tuple(template['frame_size']) and set(im.getchannel('A').tobytes())=={0,255}
        assert all(not p[3] or p in allowed for p in getattr(im,'get_flattened_data',im.getdata)())
        x,y,r,b=im.getbbox();assert x>0 and r<im.width and y>0 and b<=35,(who,direction,i,im.getbbox())
        if pose['airborne']:assert b<=33,(who,direction,i,b)
        files=[]
        for name,layer in layers.items():
            p=source/f'frame_{i:02}_{name}.png';layer.save(p);files.append(p.relative_to(ROOT).as_posix())
        filename=f'frame_{i:02}.png';im.save(folder/filename);sheet.alpha_composite(im,((i-1)*im.width,0))
        records.append(dict(pose,file=filename,rect=[(i-1)*im.width,0,im.width,36],layers_from_repo_root=files))
    assert len({im.tobytes() for im in frames})==4
    sheet.save(folder/'spritesheet.png')
    status=read(folder/'animation.json')['status'] if (folder/'animation.json').exists() else 'review'
    recipe.update(character=who,direction=direction,status=status,template=template_path,
                  approved_idle_sha256=hashlib.sha256((folder.parent/f'idle_{direction}.png').read_bytes()).hexdigest())
    write(folder/'recipe.json',recipe)
    write(folder/'animation.json',{'character':who,'animation':f'run.{direction}','status':status,'image':'spritesheet.png',
          'frame_size':template['frame_size'],'foot_anchor':template['foot_anchor'],'loop':True,'duration_ms':400,
          'template':template_path,'recipe':'recipe.json','offsets_baked_into_pixels':True,'frames':records})
    for suffix,duration in (('',100),('_slow',300)):
        sub='4 frames | 100 ms per frame | design review' if duration==100 else 'Slow motion | 300 ms per frame | same four poses'
        previews=[review_panel([im],[LABELS[who]],f'{LABELS[who]} / {direction} run',sub,16) for im in frames]
        save_gif(REVIEW/f'{who}_{direction}{suffix}.gif',previews,duration)
    review_panel(frames,[p['phase'].replace('_',' ').title() for p in records],f'{LABELS[who]} / {direction} run poses',
                 'Four native poses | 100 ms per frame | design review',8).save(REVIEW/f'{who}_{direction}_frames.png')
    return frames


def build():
    REVIEW.mkdir(parents=True,exist_ok=True);protected=protected_inputs()
    for who in CHARACTERS:
        for p in (ROOT/f'assets/characters/{who}/run_left').glob('*'):
            if p.is_file():protected[p.relative_to(ROOT).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
        for record in read(ROOT/f'assets/characters/{who}/run_left/animation.json')['frames']:
            for relative in record['layers_from_repo_root']:
                protected[relative]=hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()
    for root in ('docs/reviews/liam_daisy_run_prototypes','assets/templates/child_24x36/run_left','assets/templates/quadruped_40x36/run_left'):
        for p in (ROOT/root).rglob('*'):
            if p.is_file():protected[p.relative_to(ROOT).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
    animations={}
    for who in CHARACTERS:
        animations[who]={direction:export(who,direction,liam(direction) if who=='liam' else daisy(direction)) for direction in DIRECTIONS}
        animations[who]['left']=[Image.open(ROOT/f'assets/characters/{who}/run_left/frame_{i:02}.png').convert('RGBA') for i in range(1,5)]
        for suffix,duration in (('',100),('_slow',300)):
            sub='4 frames | 100 ms per frame | left approved; other views for review' if duration==100 else 'Slow motion | 300 ms per frame | left approved; other views for review'
            views=[review_panel([animations[who][d][i] for d in ALL_DIRECTIONS],[d.title() for d in ALL_DIRECTIONS],
                               f'{LABELS[who]} / all running directions',sub,10) for i in range(4)]
            save_gif(REVIEW/f'{who}_all_directions{suffix}.gif',views,duration)
            if not suffix:views[0].save(REVIEW/f'{who}_all_directions.png')
    for direction in DIRECTIONS:
        views=[review_panel([animations[who][direction][i] for who in CHARACTERS],['Liam','Daisy'],
                           f'Liam and Daisy / {direction} runs','Same native scale | four poses | 100 ms per frame',14) for i in range(4)]
        save_gif(REVIEW/f'both_{direction}.gif',views,100)
    assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==v for p,v in protected.items()),'Approved input changed'
    status='approved' if all(read(ROOT/f'assets/characters/{who}/run_{d}/animation.json')['status']=='approved' for who in CHARACTERS for d in DIRECTIONS) else 'review'
    write(REVIEW/'animations.json',{'status':status,'frame_count':4,'frame_duration_ms':100,'cycle_duration_ms':400,
          'new_directions':list(DIRECTIONS),'approved_reference_direction':'left','protected_inputs_sha256':protected,
          'animations':{who:{d:f'assets/characters/{who}/run_{d}/animation.json' for d in DIRECTIONS} for who in CHARACTERS}})
    print('Built six directional runs, synchronized four-direction previews and slow-motion loops; approved left runs unchanged.')


if __name__=='__main__':build()
