"""Pose the approved family idles using shared human and quadruped strides."""
import hashlib
import json
from collections import Counter
from pathlib import Path

from PIL import Image,ImageDraw,ImageFont

from build_character_walk import blank,isolated,rgba,shifted
from build_dress_walk import legs_pose

ROOT=Path(__file__).resolve().parents[1]
TEMPLATE=ROOT/'assets/templates/humanoid_24x36/walk_front'
DOG_TEMPLATE=ROOT/'assets/templates/quadruped_32x36/walk_front'
REVIEW=ROOT/'docs/reviews/liam_family_front_walks'
BACKGROUND='#e8edf2'
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
ORDER=('liam','liam_mother','liam_father','daisy')
LABELS={'liam':'Liam','liam_mother':'Mother','liam_father':'Father','daisy':'Daisy'}
SPECS={
    'liam':{'head_end':21,'torso':[9,21,6,4],'hem':[9,25,6,3],
            'arm_size':[18,7],'arm_offset':[3,21],'rest_height':26,'leg_start':28},
    'liam_mother':{'head_end':14,'torso':[7,14,10,7],'hem':[0,0,0,0],
                   'arm_size':[22,11],'arm_offset':[1,14],'rest_height':34,'leg_start':26},
    'liam_father':{'head_end':14,'torso':[7,14,10,8],'hem':[8,22,8,6],
                   'arm_size':[24,12],'arm_offset':[0,14],'rest_height':34,'leg_start':26},
}


def read(path):return json.loads(path.read_text())
def write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,indent=2)+'\n')
def font(size):return ImageFont.truetype(FONT,size)
def rgba_colors(materials):return {rgba(c) for colors in materials.values() for c in colors}


def arm_pose(mask,template,m,spec,phase,identity):
    """Register silhouette first, then restore an exact native shoulder bob."""
    dy=phase['upper_body_offset'][1]
    normalized=shifted(mask,-dy)
    # Semantic colors survive nearest-neighbor registration.
    crop=normalized.crop((0,14,24,27)).resize(tuple(spec['arm_size']),Image.Resampling.NEAREST)
    posed=blank((24,36));posed.paste(crop,tuple(spec['arm_offset']))
    box=posed.getbbox();hand_height=3 if identity=='liam_father' else 2
    hand_top=box[3]-hand_height
    codes={rgba(v):k for k,v in template['semantic_colors'].items()}
    output=blank((24,36))
    for y in range(36):
        for x in range(24):
            p=posed.getpixel((x,y))
            if not p[3]:continue
            code=codes[p]
            shade=0 if code.endswith('shadow') else 2 if code.endswith('light') else 1
            if code=='outline':color=m['outline'][0]
            elif y>=hand_top:color=m['skin'][1 if shade==0 else 0]
            elif identity=='liam_mother':
                material='linen' if y==hand_top-1 else 'dress'
                color=m[material][shade]
            elif identity=='liam_father':
                material='tunic' if y<box[1]+4 else 'linen'
                color=m[material][shade]
            else:color=m['tunic'][shade]
            output.putpixel((x,y),rgba(color))
    return shifted(output,dy)


def child_legs(reference,m):
    raw=blank((24,36));raw.paste(reference.crop((0,26,24,35)).resize((18,7),Image.Resampling.NEAREST),(3,28))
    output=blank((24,36));toes={}
    outlines={rgba(c) for c in ('#1a0e16','#1a0e17','#2b1715')}
    shadow=rgba('#573422');light=rgba('#b67644')
    for side,(left,right) in {'left':(0,12),'right':(12,24)}.items():
        ys=[y for y in range(28,35) for x in range(left,right) if raw.getpixel((x,y))[3]]
        toe=max(ys);toes[side]=toe
        boot_height=3 if toe==34 else 2;boot_top=toe-boot_height+1
        for y in range(28,35):
            for x in range(left,right):
                p=raw.getpixel((x,y))
                if not p[3]:continue
                shade=0 if p==shadow else 2 if p==light else 1
                if p in outlines:color=m['outline'][0]
                elif y>=boot_top:color=m['leather'][shade]
                elif y==boot_top-1:color=m['skin'][1 if shade==0 else 0]
                else:color=m['trousers'][shade]
                output.putpixel((x,y),rgba(color))
    return output,toes


def mother_legs(reference,m,index):
    pose={'boot_top_rows':{'left':32 if index<2 else 28,'right':28 if index<2 else 32}}
    materials={'outline':{'base':m['outline'][0]},
               'skin':{'base':m['skin'][0],'shadow':m['skin'][1]},
               'leather':dict(zip(('shadow','base','light'),m['leather'],strict=True))}
    raw=legs_pose(reference,pose,materials);output=blank((24,36))
    toes=({'left':34,'right':33} if index<2 else {'left':33,'right':34})
    for side,(left,right) in {'left':(0,12),'right':(12,24)}.items():
        source=isolated(raw,[left,26,right-left,9]);bottom=source.getbbox()[3]-1
        output.alpha_composite(shifted(source,toes[side]-bottom))
    return output,toes


def skirt_pose(idle,m,index):
    """Keep the approved apron texture while the lower dress follows the step."""
    output=blank((24,36));passing=index in (1,3);hem=30 if passing else 31
    allowed={rgba(c) for key in ('dress','linen') for c in m[key]}
    widths={21:(8,16),22:(7,17),23:(7,17),24:(7,17),25:(7,17),
            26:(6,18),27:(6,18),28:(6,18),29:(5,19),30:(5,19),31:(7,17)}
    sway=1 if index==0 else -1 if index==2 else 0
    for y in range(21,hem+1):
        sy=y+1 if passing and y>=24 else y
        left,right=widths[sy]
        offset=sway if y>=24 else 0
        for x in range(left,right):
            p=idle.getpixel((x,sy))
            if p not in allowed:
                p=rgba(m['linen'][1] if 9<=x<=15 and sy<=28 else m['dress'][1])
            if x in (left,right-1):p=rgba(m['outline'][0])
            output.putpixel((x+offset,y),p)
    return output,hem


def human(identity,template):
    spec=SPECS[identity];folder=ROOT/f'assets/characters/{identity}'
    idle=Image.open(folder/'idle_front.png').convert('RGBA');meta=read(folder/'idle_front.json')
    palette=read(folder/'palette.json');m=palette['materials']
    head=isolated(idle,[0,0,24,spec['head_end']]);torso=isolated(idle,spec['torso'])
    hem=isolated(idle,spec['hem']);frames=[];records=[];all_layers=[]
    for i,phase in enumerate(template['frames']):
        dy=phase['upper_body_offset'][1];source=TEMPLATE/f"frame_{phase['id']}"
        # These costumes have symmetric legs. Reuse the clean left-stride
        # pair and mirror it for the opposite step, excluding the source
        # costume's asymmetric center hem from the far-foot silhouette.
        leg_source=TEMPLATE/f'frame_{i%2+1:02}/legs.png'
        reference=Image.open(leg_source).convert('RGBA')
        if i>=2:reference=reference.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        if identity=='liam':legs,toes=child_legs(reference,m)
        elif identity=='liam_mother':legs,toes=mother_legs(reference,m,i)
        else:
            pose={'boot_top_rows':{'left':31 if i<2 else 28,'right':28 if i<2 else 31}}
            lm={'outline':{'base':m['outline'][0]},
                'skin':{'base':m['trousers'][1],'shadow':m['trousers'][0]},
                'leather':dict(zip(('shadow','base','light'),m['leather'],strict=True))}
            legs=legs_pose(reference,pose,lm)
            toes={s:max(y for y in range(26,35) for x in range(a,b) if legs.getpixel((x,y))[3])
                  for s,(a,b) in {'left':(0,12),'right':(12,24)}.items()}
        layers={'legs':legs}
        if identity=='liam_mother':layers['skirt_and_apron'],hem_row=skirt_pose(idle,m,i)
        else:layers['waist_and_hem']=hem;hem_row=spec['hem'][1]+spec['hem'][3]-1
        for side in ('left','right'):
            mask=Image.open(source/f'{side}_arm_mask.png').convert('RGBA')
            layers[f'{side}_arm']=arm_pose(mask,template,m,spec,phase,identity)
        chest=shifted(torso,dy)
        if dy==-1:
            x,y,w,h=spec['torso'];bridge=isolated(torso,[x,y+h-1,w,1])
            if identity=='liam_mother':
                hair={rgba(c) for c in m['hair']}
                for xx in range(x,x+w):
                    if bridge.getpixel((xx,y+h-1)) in hair:bridge.putpixel((xx,y+h-1),rgba(m['dress'][1]))
            chest.alpha_composite(bridge)
        layers['upper_body']=chest;layers['head']=shifted(head,dy)
        frame=blank((24,36))
        for layer in layers.values():frame.alpha_composite(layer)
        # Exact approved face/neck pixels travel with the shoulders.
        for y in range(spec['head_end']):
            for x in range(24):
                if idle.getpixel((x,y))[3]:assert frame.getpixel((x,y+dy))==idle.getpixel((x,y))
        assert frame.getbbox()[1::2]==(35-spec['rest_height']+dy,35),(identity,i,frame.getbbox())
        frames.append(frame);all_layers.append(layers)
        records.append({'phase':phase['phase'],'upper_body_offset':[0,dy],
                        'shoulder_offset':[0,dy],'eyes':[[x,y+dy] for x,y in meta['eyes']['top_pixels']],
                        'leg_toe_rows':toes,'hem_row':hem_row,
                        'leg_source':leg_source.relative_to(ROOT).as_posix(),'leg_source_mirrored':i>=2})
    recipe={'character':identity,'status':'review','idle':'../idle_front.png','palette':'../palette.json',
            'template':'assets/templates/humanoid_24x36/walk_front/poses.json','head_rows':[0,spec['head_end']],
            'torso_rect':spec['torso'],'hem_rect':spec['hem'],
            'arm_registration':{'source_rect':[0,14,24,13],'target_size':spec['arm_size'],
                                'offset':spec['arm_offset'],'normalize_source_bob':True},
            'rest_visible_height_px':spec['rest_height'],'notes':
            'Read-only approved appearance; shared stride registered to proportions, exact head/shoulder bob.'}
    return frames,records,all_layers,recipe


def dog_template():
    """Four-beat lateral-sequence walk: hind L, fore L, hind R, fore R."""
    order=('hind_left','fore_left','hind_right','fore_right')
    paws={'hind_left':{'root':[12,26],'toe':[10,32],'width':3},
          'fore_left':{'root':[13,27],'toe':[13,34],'width':4},
          'hind_right':{'root':[21,26],'toe':[23,32],'width':3},
          'fore_right':{'root':[19,27],'toe':[19,34],'width':4}}
    phases=[]
    for i,swing in enumerate(order):
        dy=0 if i%2==0 else -1;legs={}
        for name,paw in paws.items():
            planted=name!=swing;toe=list(paw['toe']);toe[1]-=0 if planted else 2
            root=[paw['root'][0],paw['root'][1]+dy]
            knee=[round((root[0]+toe[0])/2)+(0 if planted else (-1 if 'left' in name else 1)),
                  round((root[1]+toe[1])/2)]
            legs[name]={'root':root,'knee':knee,'toe':toe,'width':paw['width'],'planted':planted}
        phases.append({'id':f'{i+1:02}','phase':f'{swing}_swing','duration_ms':140,
                       'upper_body_offset':[0,dy],'tail_offset':[-1 if i==0 else 1 if i==2 else 0,dy],
                       'ear_tip_offsets':{'left':1 if i==0 else 0,'right':1 if i==2 else 0},
                       'legs':legs})
    data={'id':'quadruped_32x36.walk.front','frame_size':[32,36],'foot_anchor':[16,34],
          'gait':'four-beat lateral-sequence walk','order':list(order),'frames':phases}
    write(DOG_TEMPLATE/'poses.json',data);return data


def dog_parts(idle):
    parts={name:blank(idle.size) for name in ('head','left_ear_tip','right_ear_tip','body','tail')}
    for y in range(36):
        for x in range(32):
            p=idle.getpixel((x,y))
            if not p[3] or y>=29:continue
            if (x>=24 and y<=24) or (x>=23 and 21<=y<=23):key='tail'
            elif y<=20:
                key='left_ear_tip' if x<=11 and y>=18 else 'right_ear_tip' if x>=21 and y>=18 else 'head'
            else:key='body'
            parts[key].putpixel((x,y),p)
    return parts


def dog_leg(reference,spec,m,far=False):
    """Repose approved shaggy leg/paw pixels, keeping the paw tip unscaled."""
    im=blank((32,36));root,knee,toe=[tuple(spec[k]) for k in ('root','knee','toe')]
    width=3 if far else 5;height=toe[1]-root[1]+1;paw_rows=2 if far else 3
    shank=reference.crop((0,0,5,8-paw_rows)).resize((width,height-paw_rows),Image.Resampling.NEAREST)
    paw=reference.crop((0,8-paw_rows,5,8)).resize((width,paw_rows),Image.Resampling.NEAREST)
    posed=blank((width,height));posed.paste(shank,(0,0));posed.paste(paw,(0,height-paw_rows))
    for row in range(height):
        t=row/(height-1)
        center=round(root[0]+(knee[0]-root[0])*t*2) if t<=.5 else round(knee[0]+(toe[0]-knee[0])*(t-.5)*2)
        for x in range(width):
            p=posed.getpixel((x,row))
            if not p[3]:continue
            if far:
                if p==rgba(m['gray_fur'][1]):p=rgba(m['gray_fur'][0])
                if p==rgba(m['white_fur'][1]):p=rgba(m['white_fur'][0])
            im.putpixel((center-width//2+x,root[1]+row),p)
    return im


def daisy():
    folder=ROOT/'assets/characters/daisy';idle=Image.open(folder/'idle_front.png').convert('RGBA')
    palette=read(folder/'palette.json');m=palette['materials'];meta=read(folder/'idle_front.json')
    template=dog_template();parts=dog_parts(idle);frames=[];records=[];all_layers=[]
    for phase in template['frames']:
        dy=phase['upper_body_offset'][1];sway=phase['tail_offset'][0]
        tail=blank(idle.size);tail.paste(parts['tail'],(sway,dy))
        # A fixed short root joins the swaying plume to the body.
        d=ImageDraw.Draw(tail)
        d.polygon(((22,21+dy),(24+sway,21+dy),(25+sway,23+dy),(22,24+dy)),fill=m['gray_fur'][0])
        layers={'tail':tail}
        leg_sources={'left':idle.crop((11,27,16,35)),'right':idle.crop((17,27,22,35))}
        for name in ('hind_left','hind_right'):layers[name]=dog_leg(leg_sources[name.split('_')[1]],phase['legs'][name],m,True)
        layers['body']=shifted(parts['body'],dy)
        for name in ('fore_left','fore_right'):layers[name]=dog_leg(leg_sources[name.split('_')[1]],phase['legs'][name],m)
        layers['head']=shifted(parts['head'],dy)
        for side in ('left','right'):
            lag=phase['ear_tip_offsets'][side];ear=shifted(parts[f'{side}_ear_tip'],dy+lag)
            if lag:ear.alpha_composite(shifted(isolated(parts[f'{side}_ear_tip'],[0,18,32,1]),dy))
            layers[f'{side}_ear_tip']=ear
        frame=blank(idle.size)
        for layer in layers.values():frame.alpha_composite(layer)
        for ex,ey in meta['eyes']['top_pixels']:
            assert frame.getpixel((ex,ey+dy))==rgba(palette['eyes']['pupil'])
            assert frame.getpixel((ex,ey+dy+1))==rgba(palette['eyes']['iris'])
        assert frame.getbbox()[1::2]==(11+dy,35),(phase['id'],frame.getbbox())
        frames.append(frame);all_layers.append(layers)
        records.append({k:phase[k] for k in ('phase','upper_body_offset','tail_offset','ear_tip_offsets','legs')})
        records[-1]['shoulder_offset']=[0,dy]
        records[-1]['eyes']=[[x,y+dy] for x,y in meta['eyes']['top_pixels']]
    recipe={'character':'daisy','status':'review','idle':'../idle_front.png','palette':'../palette.json',
            'template':'assets/templates/quadruped_32x36/walk_front/poses.json',
            'rest_visible_height_px':24,'gait':template['gait'],
            'notes':'Approved head, torso spots and tail retained; one paw swings, three support; hinged plume and ear-tip follow-through.'}
    return frames,records,all_layers,recipe


def save_gif(path,frames,duration=140):
    colors=Counter()
    for im in frames:colors.update({color:count for count,color in im.getcolors(im.width*im.height)})
    assert len(colors)<=256,(path,len(colors))
    palette=Image.new('P',(1,1));rgb=[v for color in colors for v in color];palette.putpalette(rgb+[0]*(768-len(rgb)))
    indexed=[im.quantize(palette=palette,dither=Image.Dither.NONE) for im in frames]
    indexed[0].save(path,save_all=True,append_images=indexed[1:],duration=duration,loop=0,disposal=2,optimize=False)


def panel(frames,labels,scale,title,subtitle):
    stride=32*scale+32;width=stride*len(frames)+24;height=36*scale+168
    im=Image.new('RGB',(width,height),BACKGROUND);d=ImageDraw.Draw(im);d.fontmode='1'
    d.text((24,16),title,font=font(26),fill='#26343e');d.text((24,56),subtitle,font=font(18),fill='#52616c')
    baseline=104+35*scale;d.line((20,baseline,width-20,baseline),fill='#b5c1c4')
    for i,(frame,label) in enumerate(zip(frames,labels,strict=True)):
        canvas=blank((32,36));canvas.alpha_composite(frame,((32-frame.width)//2,0))
        big=canvas.resize((32*scale,36*scale),Image.Resampling.NEAREST)
        im.paste(big,(24+i*stride,104),big)
        d.text((24+i*stride,36*scale+128),label,font=font(20),fill='#26343e')
    return im


def export(identity,result):
    frames,records,layer_sets,recipe=result
    folder=ROOT/f'assets/characters/{identity}/walk_front';folder.mkdir(parents=True,exist_ok=True)
    status=read(folder/'animation.json').get('status','review') if (folder/'animation.json').exists() else 'review'
    recipe['status']=status
    source=ROOT/('assets/source/characters/daisy/walk_front/parts' if identity=='daisy' else
                 f'assets/source/characters/liam_family/{identity}/walk_front/parts')
    source.mkdir(parents=True,exist_ok=True)
    palette=read(folder.parent/'palette.json');allowed=rgba_colors(palette['materials'])|{rgba(c) for c in palette['eyes'].values()}
    for i,(frame,record,layers) in enumerate(zip(frames,records,layer_sets,strict=True),1):
        assert frame.getbbox()[3]==35 and not frame.getchannel('A').crop((0,35,frame.width,36)).getbbox()
        assert set(frame.getchannel('A').tobytes())=={0,255}
        assert all(not p[3] or p in allowed for p in getattr(frame,'get_flattened_data',frame.getdata)())
        paths=[];combined=blank(frame.size)
        for name,layer in layers.items():
            path=source/f'frame_{i:02}_{name}.png';layer.save(path);combined.alpha_composite(layer)
            paths.append(path.relative_to(ROOT).as_posix())
        assert combined.tobytes()==frame.tobytes()
        name=f'frame_{i:02}.png';frame.save(folder/name)
        record.update(file=name,rect=[(i-1)*frame.width,0,frame.width,36],duration_ms=140,layers_from_repo_root=paths)
    assert len({frame.tobytes() for frame in frames})==4
    sheet=blank((frames[0].width*4,36))
    for i,frame in enumerate(frames):sheet.alpha_composite(frame,(i*frame.width,0))
    sheet.save(folder/'spritesheet.png')
    recipe['approved_idle_sha256']=hashlib.sha256((folder.parent/'idle_front.png').read_bytes()).hexdigest()
    write(folder/'recipe.json',recipe)
    write(folder/'animation.json',{'character':identity,'animation':'walk.front','status':status,
          'image':'spritesheet.png','frame_size':list(frames[0].size),'foot_anchor':[16 if identity=='daisy' else 12,34],
          'loop':True,'duration_ms':560,'rest_visible_height_px':recipe['rest_visible_height_px'],
          'template':recipe['template'],'recipe':'recipe.json','offsets_baked_into_pixels':True,'frames':records})
    individual=[panel([frame],[LABELS[identity]],20,f'{LABELS[identity]} / front walk','Four frames | 140 ms per frame | design review') for frame in frames]
    save_gif(REVIEW/f'{identity}.gif',individual)
    individual[0].save(REVIEW/f'{identity}.png')
    panel(frames,[f'Frame {i+1}' for i in range(4)],12,f'{LABELS[identity]} / front walk frames','Contact and passing phases | native pixel artwork').save(REVIEW/f'{identity}_frames.png')
    return frames


def build():
    REVIEW.mkdir(parents=True,exist_ok=True)
    protected=[p for identity in ORDER for p in (ROOT/f'assets/characters/{identity}').glob('idle_*.png')]
    protected+=[ROOT/f'assets/characters/{identity}/palette.json' for identity in ORDER]
    hashes={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
    template=read(TEMPLATE/'poses.json');animations={}
    for identity in ORDER:animations[identity]=export(identity,daisy() if identity=='daisy' else human(identity,template))
    frames=[panel([animations[identity][i] for identity in ORDER],[LABELS[identity] for identity in ORDER],10,
                  'Liam, his parents and Daisy / front walks','Shared scale and timing | four-frame loops | designs for review') for i in range(4)]
    save_gif(REVIEW/'all_front_walks.gif',frames);frames[0].save(REVIEW/'all_front_walks.png')
    status='approved' if all(read(ROOT/f'assets/characters/{identity}/walk_front/animation.json')['status']=='approved' for identity in ORDER) else 'review'
    write(REVIEW/'animations.json',{'status':status,'frame_duration_ms':140,'cycle_duration_ms':560,
          'order':list(ORDER),'animations':{identity:f'assets/characters/{identity}/walk_front/animation.json' for identity in ORDER}})
    assert all(hashlib.sha256(p.read_bytes()).hexdigest()==sha for p,sha in hashes.items())
    print('Built four front walks, exact shared-palette GIFs and retained pose layers; approved idles unchanged.')


if __name__=='__main__':build()
