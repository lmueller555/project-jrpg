"""Repose approved family turnarounds; never rewrite approved fronts or idles."""
import hashlib
from PIL import Image, ImageDraw

from build_liam_family_front_walks import (
    ROOT, ORDER, LABELS, SPECS, read, write, rgba, blank, isolated, shifted,
    rgba_colors, child_legs, arm_pose, dog_leg, panel, save_gif,
)
from build_dress_walk import legs_pose

DIRECTIONS = ('left', 'right', 'back')
ALL_DIRECTIONS = ('front',) + DIRECTIONS
REVIEW = ROOT / 'docs/reviews/liam_family_directional_walks'


def protected_files():
    """Approval applies to appearance and existing front motion, byte for byte."""
    paths = []
    for identity in ORDER:
        base = ROOT / f'assets/characters/{identity}'
        paths += list(base.glob('idle*')) + [base / 'palette.json']
        paths += list((base / 'walk_front').glob('*'))
    paths += list((ROOT / 'docs/reviews/liam_family_front_walks').glob('*'))
    return [p for p in paths if p.is_file()]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def body_rect(identity, direction):
    if direction == 'back':
        return {'liam': [9, 21, 6, 7], 'liam_mother': [8, 14, 8, 7],
                'liam_father': [8, 14, 8, 9]}[identity]
    if identity == 'liam':
        return [10 if direction == 'left' else 9, 21, 5, 7]
    if identity == 'liam_mother':
        return [10 if direction == 'left' else 9, 14, 5, 7]
    return [8, 14, 8, 9]


def dress(idle, m, index):
    """Native directional apron/waistband texture; one-pixel lower-skirt sway."""
    im = blank(idle.size)
    allowed = {rgba(c) for k in ('dress', 'linen') for c in m[k]}
    passing = index % 2 == 1
    sway = (1, 0, -1, 0)[index]
    # Each authored directional silhouette supplies its own row widths.
    for y in range(21, 31 if passing else 32):
        sy = y + 1 if passing and y >= 24 else y
        xs = [x for x in range(24) if idle.getpixel((x, sy))[3]]
        left, right = min(xs), max(xs)
        for x in range(left, right + 1):
            p = idle.getpixel((x, sy))
            if p not in allowed:
                # Hands are a separate moving layer, never painted into skirt.
                neighbors = [idle.getpixel((xx, sy)) for xx in range(max(left, x-3), min(right+1, x+4))
                             if idle.getpixel((xx, sy)) in allowed]
                p = neighbors[0] if neighbors else rgba(m['dress'][1])
            if x in (left, right): p = rgba(m['outline'][0])
            im.putpixel((x + (sway if y >= 24 else 0), y), p)
    return im


def human(identity, direction):
    base = ROOT / f'assets/characters/{identity}'
    idle = Image.open(base / f'idle_{direction}.png').convert('RGBA')
    meta = read(base / f'idle_{direction}.json')
    m = read(base / 'palette.json')['materials']
    spec = SPECS[identity]
    template_root = ROOT / f'assets/templates/humanoid_24x36/walk_{direction}'
    template = read(template_root / 'poses.json')
    costume = read(ROOT / f'assets/characters/npcs/female_01/walk_{direction}/recipe.json')['costume_poses']
    head = isolated(idle, [0, 0, 24, spec['head_end']])
    rect = body_rect(identity, direction)
    torso = isolated(idle, rect)
    # Keep the approved braid continuous and on the same anatomical shoulder.
    if identity == 'liam_mother':
        hair = {rgba(c) for c in m['hair']}
        outline = rgba(m['outline'][0])
        for y in range(14, 21):
            for x in range(10, 17):
                p = idle.getpixel((x, y))
                if p in hair or (p == outline and any(idle.getpixel((xx, y)) in hair for xx in range(max(0,x-1), min(24,x+2)))):
                    torso.putpixel((x, y), p)
    frames, records, layer_sets = [], [], []
    for index, phase in enumerate(template['frames']):
        dy = phase['upper_body_offset'][1]
        source = template_root / f"frame_{phase['id']}"
        reference = Image.open(source / 'legs.png').convert('RGBA')
        if identity == 'liam':
            legs, toes = child_legs(reference, m)
        else:
            boots = costume[index]['boot_top_rows'] if identity == 'liam_mother' else {
                k: v-1 for k, v in costume[index]['boot_top_rows'].items()}
            lm = {'outline': {'base': m['outline'][0]},
                  'skin': {'base': m.get('trousers', m['skin'])[1 if 'trousers' in m else 0],
                           'shadow': m.get('trousers', m['skin'])[0 if 'trousers' in m else 1]},
                  'leather': dict(zip(('shadow','base','light'), m['leather'], strict=True))}
            if identity == 'liam_mother':
                # Her long dress covers the calves. What shows beneath the
                # hem is the boot shaft, including the reaching side-view foot.
                lm['skin'] = {'base':m['leather'][1], 'shadow':m['leather'][0]}
            pose = {'boot_top_rows': boots, 'leg_split_x': costume[index].get('leg_split_x',12)}
            legs = legs_pose(reference, pose, lm)
            if identity == 'liam_mother':
                # Dress is longer than the generic NPC's. Expose both toe tips.
                moved = blank(idle.size)
                split = pose['leg_split_x']
                for a,b in ((0,split),(split,24)):
                    part = isolated(legs,[a,26,b-a,9])
                    if part.getbbox(): moved.alpha_composite(shifted(part, max(0,33-(part.getbbox()[3]-1))))
                legs = moved
            toes = {k:max(y for y in range(26,35) for x in range(a,b) if legs.getpixel((x,y))[3])
                    for k,(a,b) in {'left':(0,12),'right':(12,24)}.items()}
        layers = {'legs':legs}
        if identity == 'liam_mother':
            layers['skirt_and_apron'] = dress(idle,m,index)
        else:
            start, stop = (25,28) if identity == 'liam' else (23,26)
            # Central tunic hem stays connected while arms move around it.
            hx,_,hw,_ = rect
            layers['tunic_hem'] = isolated(idle,[hx,start,hw,stop-start])
        for side in ('left','right'):
            mask = Image.open(source / f'{side}_arm_mask.png').convert('RGBA')
            if direction != 'back':
                skin_codes = {rgba(template['semantic_colors'][k]) for k in ('skin_base','skin_shadow')}
                # Profile templates contain Caelan's long neck. Supply this
                # family's approved neck instead of scaling those pixels.
                normalized = shifted(mask,-dy)
                for y in range(13,19):
                    for x in range(9,15):
                        if normalized.getpixel((x,y)) in skin_codes:normalized.putpixel((x,y),(0,0,0,0))
                mask = shifted(normalized,dy)
            layers[f'{side}_arm'] = arm_pose(mask,template,m,spec,phase,identity)
        chest = shifted(torso,dy)
        if dy == -1:
            x,y,w,h = rect
            bridge = isolated(torso,[x,y+h-1,w,1])
            if identity == 'liam_mother':
                for xx in range(24):
                    if bridge.getpixel((xx,y+h-1)) in {rgba(c) for c in m['hair']}:
                        bridge.putpixel((xx,y+h-1),rgba(m['dress'][1]))
            chest.alpha_composite(bridge)
        layers['upper_body'] = chest
        layers['head'] = shifted(head,dy)
        image = blank(idle.size)
        for layer in layers.values():image.alpha_composite(layer)
        frames.append(image);layer_sets.append(layers)
        records.append({'phase':phase['phase'],'upper_body_offset':[0,dy],'shoulder_offset':[0,dy],
                        'eyes':[[x,y+dy] for x,y in meta['eyes']['top_pixels']], 'leg_toe_rows':toes,
                        'leg_source':(source/'legs.png').relative_to(ROOT).as_posix()})
    recipe = {'character':identity,'direction':direction,'status':'review',
              'idle':f'../idle_{direction}.png','palette':'../palette.json',
              'template':f'assets/templates/humanoid_24x36/walk_{direction}/poses.json',
              'head_end':spec['head_end'],'torso_rect':rect,
              'arm_registration':{'source_rect':[0,14,24,13], 'target_size':spec['arm_size'],
                                  'offset':spec['arm_offset'], 'normalize_source_bob':True},
              'costume_reference':f'assets/characters/npcs/female_01/walk_{direction}/recipe.json',
              'rest_visible_height_px':spec['rest_height'],
              'notes':'Shared stride and native head/shoulder bob; approved directional face, collar, braid and costume retained.'}
    return frames,records,layer_sets,recipe


def dog_template(direction):
    """One lifted paw at a time; the planted paws travel through the stride."""
    order = ('hind_left','fore_left','hind_right','fore_right')
    if direction == 'back':
        roots = {'fore_left':(11,26,32),'fore_right':(19,26,32),
                 'hind_left':(10,27,34),'hind_right':(18,27,34)}
    elif direction == 'left':
        roots = {'fore_left':(9,26,34),'fore_right':(11,26,32),
                 'hind_left':(22,26,34),'hind_right':(19,26,32)}
    else:
        roots = {'fore_right':(23,26,34),'fore_left':(21,26,32),
                 'hind_right':(8,26,34),'hind_left':(11,26,32)}
    phases=[]
    for i,swing in enumerate(order):
        dy = -(i%2);legs={}
        for name,(x,y,floor) in roots.items():
            cycle=(i-order.index(name))%4;planted=cycle!=0
            stride=(-2,-1,1,2)[cycle]
            toe=[x,floor-(0 if planted else 2)]
            if direction=='back':
                toe[0]+=(-1 if 'left' in name else 1) if not planted else 0
            else:toe[0]+=stride*(1 if direction=='left' else -1)
            root=[x,y+dy]
            knee=[round((x+toe[0])/2),round((root[1]+toe[1])/2)]
            legs[name]={'root':root,'knee':knee,'toe':toe,'planted':planted,
                        'contact_row':floor,'far':floor==32}
        phases.append({'id':f'{i+1:02}','phase':f'{swing}_swing','duration_ms':140,
                       'upper_body_offset':[0,dy],'shoulder_offset':[0,dy],
                       'tail_offset':[(-1,0,1,0)[i] if direction=='back' else 0,dy+(0,0,-1,0)[i]],
                       'ear_tip_lag':1 if i in (0,2) else 0,'legs':legs})
    template={'id':f'quadruped_32x36.walk.{direction}','frame_size':[32,36],
              'foot_anchor':[16,34],'gait':'four-beat lateral-sequence walk',
              'order':list(order),'frames':phases}
    write(ROOT/f'assets/templates/quadruped_32x36/walk_{direction}/poses.json',template)
    return template


def dog_parts(idle,direction):
    parts={name:blank(idle.size) for name in ('head','ear_tip','body','tail')}
    for y in range(29):
        for x in range(32):
            p=idle.getpixel((x,y))
            if not p[3]:continue
            tail=(x>=23 and y<=25) if direction=='left' else (x<=8 and y<=25) if direction=='right' else (x>=20 and y<=26)
            head=(x<=12 and y<=20) if direction=='left' else (x>=19 and y<=20) if direction=='right' else y<=18
            ear=(8<=x<=11 and 18<=y<=20) if direction=='left' else (20<=x<=23 and 18<=y<=20) if direction=='right' else (x<=7 and 16<=y<=18)
            key='tail' if tail else 'ear_tip' if ear else 'head' if head else 'body'
            parts[key].putpixel((x,y),p)
    return parts


def daisy(direction):
    base=ROOT/'assets/characters/daisy'
    idle=Image.open(base/f'idle_{direction}.png').convert('RGBA');m=read(base/'palette.json')['materials']
    meta=read(base/f'idle_{direction}.json');template=dog_template(direction)
    parts=dog_parts(idle,direction)
    crops={'left':{'fore':(7,27,12,35),'hind':(20,27,25,35)},
           'right':{'fore':(20,27,25,35),'hind':(6,27,11,35)},
           'back':{'left':(8,27,13,35),'right':(15,27,20,35)}}
    frames,records,layer_sets=[],[],[]
    for phase in template['frames']:
        dy=phase['upper_body_offset'][1]
        tail=blank(idle.size);tail.paste(parts['tail'],tuple(phase['tail_offset']))
        # Only the free plume moves; its root stays attached to the rump.
        rootrect={'left':[22,21,3,4],'right':[7,21,3,4],'back':[18,21,4,5]}[direction]
        tail.alpha_composite(shifted(isolated(idle,rootrect),dy))
        layers={'tail':tail}
        def leg(name):
            key=name.split('_')[1] if direction=='back' else name.split('_')[0]
            return dog_leg(idle.crop(crops[direction][key]),phase['legs'][name],m,phase['legs'][name]['far'])
        far=[n for n,s in phase['legs'].items() if s['far']]
        near=[n for n,s in phase['legs'].items() if not s['far']]
        for name in far:layers[name]=leg(name)
        layers['body']=shifted(parts['body'],dy)
        for name in near:layers[name]=leg(name)
        layers['head']=shifted(parts['head'],dy)
        lag=phase['ear_tip_lag'];ear=shifted(parts['ear_tip'],dy+lag)
        # Root overlap prevents a gap when the floppy tip lags behind the head.
        if lag:
            box=parts['ear_tip'].getbbox()
            ear.alpha_composite(shifted(isolated(parts['ear_tip'],[0,box[1],32,1]),dy))
        layers['ear_tip']=ear
        image=blank(idle.size)
        for layer in layers.values():image.alpha_composite(layer)
        frames.append(image);layer_sets.append(layers)
        records.append({k:v for k,v in phase.items() if k not in ('id','duration_ms')})
        records[-1]['eyes']=[[x,y+dy] for x,y in meta['eyes']['top_pixels']]
    recipe={'character':'daisy','direction':direction,'status':'review',
            'idle':f'../idle_{direction}.png','palette':'../palette.json',
            'template':f'assets/templates/quadruped_32x36/walk_{direction}/poses.json',
            'rest_visible_height_px':meta['visible_height_px'],
            'gait':template['gait'],'leg_source_rects':crops[direction],
            'notes':'Each view uses its own approved fur markings, not a mirrored body. Paw tips, floppy ears and hinged fluffy tail retain native pixels.'}
    return frames,records,layer_sets,recipe


def export(identity,direction,result):
    frames,records,layer_sets,recipe=result
    base=ROOT/f'assets/characters/{identity}';folder=base/f'walk_{direction}'
    folder.mkdir(parents=True,exist_ok=True)
    status=read(folder/'animation.json')['status'] if (folder/'animation.json').exists() else 'review'
    recipe['status']=status
    source=ROOT/(f'assets/source/characters/daisy/walk_{direction}/parts' if identity=='daisy' else
                 f'assets/source/characters/liam_family/{identity}/walk_{direction}/parts')
    source.mkdir(parents=True,exist_ok=True)
    palette=read(base/'palette.json');allowed=rgba_colors(palette['materials'])|{rgba(c) for c in palette['eyes'].values()}
    sheet=blank((frames[0].width*4,36))
    for i,(frame,record,layers) in enumerate(zip(frames,records,layer_sets,strict=True),1):
        assert frame.getbbox()[1::2]==(35-recipe['rest_visible_height_px']+record['upper_body_offset'][1],35),(identity,direction,i,frame.getbbox())
        assert set(frame.getchannel('A').tobytes())=={0,255}
        assert all(not p[3] or p in allowed for p in getattr(frame,'get_flattened_data',frame.getdata)())
        paths=[]
        for name,layer in layers.items():
            path=source/f'frame_{i:02}_{name}.png';layer.save(path);paths.append(path.relative_to(ROOT).as_posix())
        filename=f'frame_{i:02}.png';frame.save(folder/filename)
        sheet.alpha_composite(frame,((i-1)*frame.width,0))
        record.update(file=filename,rect=[(i-1)*frame.width,0,frame.width,36],duration_ms=140,layers_from_repo_root=paths)
    assert len({im.tobytes() for im in frames})==4
    sheet.save(folder/'spritesheet.png')
    recipe['approved_idle_sha256']=sha(base/f'idle_{direction}.png');write(folder/'recipe.json',recipe)
    write(folder/'animation.json',{'character':identity,'animation':f'walk.{direction}','status':status,
          'image':'spritesheet.png','frame_size':list(frames[0].size),'foot_anchor':[16 if identity=='daisy' else 12,34],
          'loop':True,'duration_ms':560,'rest_visible_height_px':recipe['rest_visible_height_px'],
          'template':recipe['template'],'recipe':'recipe.json','offsets_baked_into_pixels':True,'frames':records})
    panel(frames,[f'Frame {i+1}' for i in range(4)],10,f'{LABELS[identity]} / {direction} walk frames',
          'Four phases | 140 ms per frame | design review').save(REVIEW/f'{identity}_{direction}_frames.png')
    previews=[panel([im],[LABELS[identity]],16,f'{LABELS[identity]} / {direction} walk',
                    '4 frames | 140 ms per frame | design review') for im in frames]
    save_gif(REVIEW/f'{identity}_{direction}.gif',previews)
    return frames


def build():
    REVIEW.mkdir(parents=True,exist_ok=True)
    protected={p:sha(p) for p in protected_files()}
    animations={}
    for identity in ORDER:
        animations[identity]={}
        for direction in DIRECTIONS:
            result=daisy(direction) if identity=='daisy' else human(identity,direction)
            animations[identity][direction]=export(identity,direction,result)
        animations[identity]['front']=[Image.open(ROOT/f'assets/characters/{identity}/walk_front/frame_{i:02}.png').convert('RGBA') for i in range(1,5)]
        views=[panel([animations[identity][d][i] for d in ALL_DIRECTIONS],[d.title() for d in ALL_DIRECTIONS],10,
                     f'{LABELS[identity]} / all walking directions','Front approved | left, right and back for review') for i in range(4)]
        save_gif(REVIEW/f'{identity}_all_directions.gif',views)
        views[0].save(REVIEW/f'{identity}_all_directions.png')
    for direction in DIRECTIONS:
        views=[panel([animations[identity][direction][i] for identity in ORDER],[LABELS[identity] for identity in ORDER],10,
                     f'Liam and family / {direction} walks','Shared scale and timing | 140 ms per frame | design review') for i in range(4)]
        save_gif(REVIEW/f'all_{direction}_walks.gif',views);views[0].save(REVIEW/f'all_{direction}_walks.png')
    status='approved' if all(read(ROOT/f'assets/characters/{who}/walk_{d}/animation.json')['status']=='approved' for who in ORDER for d in DIRECTIONS) else 'review'
    write(REVIEW/'animations.json',{'status':status,'frame_duration_ms':140,'cycle_duration_ms':560,
          'characters':list(ORDER),'new_directions':list(DIRECTIONS),'approved_front_included_for_comparison':True,
          'animations':{identity:{d:f'assets/characters/{identity}/walk_{d}/animation.json' for d in DIRECTIONS} for identity in ORDER},
          'protected_inputs_sha256':{p.relative_to(ROOT).as_posix():v for p,v in protected.items()}})
    assert all(sha(p)==v for p,v in protected.items()),'Approved assets changed'
    print('Built 12 directional walks and synchronized review GIFs. Approved idles/front walks unchanged.')


if __name__=='__main__':build()
