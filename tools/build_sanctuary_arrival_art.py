"""Export the Sanctuary response cast and a grounded, hand-operated rope.

The retained design sheet establishes three distinct faces and wardrobes. Native
exports use explicit source rectangles and fixed foot registration. The rope is
an independently animated object: the wooden posts never move between frames.
"""
from __future__ import annotations

import argparse
from collections import deque
from hashlib import sha256
from io import BytesIO
import json
import math
from pathlib import Path
import random
import struct
import wave

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/story/sanctuary_arrival_polish'
ART = ROOT/'assets/story/sanctuary_arrival/art'
MANIFEST = ROOT/'assets/story/sanctuary_arrival/art.json'
DIRECTIONS = ('front', 'back', 'left', 'right')

# Clear gutters around the retained pixel designs; no adjacent pose is cropped.
CELLS = {
    'caretaker': ((60,89,139,268),(176,89,254,268),(294,89,369,268),(402,89,481,268)),
    'worker_a': ((569,89,650,268),(685,89,764,268),(795,89,872,268),(907,89,986,268)),
    'worker_b': ((1066,89,1147,268),(1182,89,1262,268),(1295,89,1375,268),(1412,89,1492,268)),
}
REST_CELLS = {'worker_a': (712,283,826,428), 'worker_b': (1187,282,1364,430)}
PORTRAIT_CELLS = {'caretaker': (110,679,431,1000), 'worker_a': (606,679,927,1000),
                  'worker_b': (1110,679,1431,1000)}
PALETTE = {'outline':'#272728','sleeve_shadow':'#9d997c','sleeve':'#d6c6a1',
           'sleeve_light':'#e5d4ac','skin_shadow':'#bd814c','skin':'#e9ac62',
           'rope_shadow':'#6d613d','rope':'#a4935b','rope_light':'#cec38a'}


def png(image):
    stream=BytesIO();image.save(stream,format='PNG');return stream.getvalue()


def green_matte(image):
    """Remove only connected dark-green gutter pixels, preserving green cloth."""
    image=image.convert('RGBA');width,height=image.size
    px=image.load();outside=set();todo=deque()
    def background(x,y):
        r,g,b,_=px[x,y]
        return g>=r*1.08 and g>=b*.98 and r<85 and g<110 and b<100
    for x in range(width):todo.extend(((x,0),(x,height-1)))
    for y in range(height):todo.extend(((0,y),(width-1,y)))
    while todo:
        x,y=todo.popleft()
        if not (0<=x<width and 0<=y<height) or (x,y) in outside:continue
        if not background(x,y):continue
        outside.add((x,y))
        todo.extend(((x-1,y),(x+1,y),(x,y-1),(x,y+1)))
    for x,y in outside:px[x,y]=(0,0,0,0)
    return image


def native(image, *, height=30, canvas=(24,36), foot=34):
    image=green_matte(image);bounds=image.getbbox()
    if bounds is None:raise ValueError('Empty design cell')
    image=image.crop(bounds)
    width=max(1,round(image.width*height/image.height))
    image=image.resize((width,height),Image.Resampling.NEAREST)
    if width>canvas[0]:raise ValueError('Native pose exceeds canvas')
    result=Image.new('RGBA',canvas)
    result.alpha_composite(image,((canvas[0]-width)//2,foot-height))
    return result


def walking(idle, template, phase):
    """Articulated legacy contact legs retain the new identity's native torso."""
    image=Image.new('RGBA',(24,36))
    # Existing contact poses establish actual walking feet, not whole-image bob.
    legs=template.crop((0,26,24,36)).convert('RGBA')
    image.alpha_composite(legs,(0,26))
    upper=idle.crop((0,0,24,27))
    image.alpha_composite(upper,(0,-1 if phase in (1,3) else 0))
    return image


def arm_pose(idle, grip, index):
    """Native reaching arm is registered to a fixed body and authored grip."""
    result=Image.new('RGBA',(40,48));body=idle.copy()
    # Move the near arm from its standing position into the reaching silhouette.
    # The small tunic patch fills the old sleeve without changing torso/feet.
    d=ImageDraw.Draw(body)
    if 1 <= index <= 10:
        d.rectangle((13,18,15,24),fill=PALETTE['sleeve_shadow'])
        d.line((13,18,13,24),fill=PALETTE['sleeve'])
    if 1 <= index <= 10:
        shoulder=(25,26)
        elbow=(round((shoulder[0]+grip[0])*.5),round((shoulder[1]+grip[1])*.5)+2)
        draw=ImageDraw.Draw(result)
        draw.line((shoulder,elbow,grip),fill=PALETTE['outline'],width=5)
        draw.line((shoulder,elbow,grip),fill=PALETTE['sleeve_shadow'],width=3)
        draw.line(((shoulder[0]-1,shoulder[1]-1),(elbow[0]-1,elbow[1]-1),grip),fill=PALETTE['sleeve'],width=2)
    result.alpha_composite(body,(14,10))
    if 1 <= index <= 10:
        draw=ImageDraw.Draw(result)
        draw.rectangle((grip[0]-1,grip[1]-1,grip[0]+1,grip[1]+1),fill=PALETTE['skin_shadow'])
        draw.line((grip[0]-1,grip[1]-1,grip[0]+1,grip[1]-1),fill=PALETTE['skin'],width=2)
    return result


def bezier(points, steps=100):
    result=[]
    for step in range(steps+1):
        t=step/steps
        if len(points)==3:
            a,b,c=points
            p=((1-t)**2*a[0]+2*(1-t)*t*b[0]+t*t*c[0],
               (1-t)**2*a[1]+2*(1-t)*t*b[1]+t*t*c[1])
        else:
            a,b,c,d=points
            p=tuple((1-t)**3*a[k]+3*(1-t)**2*t*b[k]+3*(1-t)*t*t*c[k]+t**3*d[k] for k in (0,1))
        point=(round(p[0]),round(p[1]))
        if not result or point!=result[-1]:result.append(point)
    return result


def rope_frame(index):
    image=Image.new('RGBA',(72,48));draw=ImageDraw.Draw(image)
    end_points=[(66,17)]*4+[(66,18),(67,21),(68,25),(68,29),(68,33),(67,36),
                            (60,40),(48,43),(35,44),(24,44),(18,43),(18,43)]
    end=end_points[index]
    if index<4:points=bezier(((7,17),(36,33),end))
    elif index<10:
        # Gravity increases the sag while the caretaker guides the free end.
        points=bezier(((7,17),(28,37+index*.4),(51,39),end))
    elif index<14:
        points=bezier(((7,17),(7,43),(max(12,end[0]-10),44),end))
    else:
        points=bezier(((7,17),(7,30),(8,37),(12,40)))
        # One loose coil settles beside the fixed post after the free end falls.
        coil=[]
        for n in range(48):
            theta=math.pi*1.15+math.tau*n/47
            coil.append((round(15+8*math.cos(theta)),round(40+3*math.sin(theta))))
        points+=coil
        points.extend(((19,42),(22,41),(23,40)))
    draw.line(points,fill=PALETTE['rope_shadow'],width=3,joint='curve')
    draw.line(points,fill=PALETTE['rope'],width=2,joint='curve')
    highlight=[(x,y-1) for x,y in points]
    draw.line(highlight,fill=PALETTE['rope_light'],width=1,joint='curve')
    return image,end


def release_sound():
    stream=BytesIO();rate=22050;rng=random.Random(1303);frames=[];low=0.
    for n in range(round(rate*.23)):
        t=n/rate;noise=rng.uniform(-1,1);low+=.22*(noise-low)
        tick=.15*math.exp(-95*t)*(math.sin(2*math.pi*530*t)+.4*math.sin(2*math.pi*810*t))
        fibre=.055*math.sin(math.pi*min(1,t/.23))**2*low
        v=max(-1,min(1,tick+fibre));frames.append(struct.pack('<h',round(v*32767)))
    with wave.open(stream,'wb') as out:
        out.setnchannels(1);out.setsampwidth(2);out.setframerate(rate);out.writeframes(b''.join(frames))
    return stream.getvalue()


def products():
    recipe=json.loads((SOURCE/'recipe.json').read_text())
    for record in recipe['sources']:
        if sha256((ROOT/record['path']).read_bytes()).hexdigest()!=record['sha256']:
            raise ValueError('Sanctuary identity reference changed: '+record['path'])
    source=Image.open(SOURCE/'care_identity_design.png').convert('RGBA');out={};images={}
    def export(path,image):
        path=ART/path;out[path]=png(image);images[path.relative_to(ART).as_posix()]=image
        return path.relative_to(ROOT).as_posix()
    actors={}
    for role,cells in CELLS.items():
        idles={};walks={}
        native_idles={}
        for direction,rect in zip(DIRECTIONS,cells):
            idle=native(source.crop(rect));native_idles[direction]=idle
            idles[direction]=export(Path(role)/('idle_'+direction+'.png'),idle)
            if role=='caretaker':
                paths=[]
                for i in range(4):
                    leg_source=Image.open(ROOT/f'assets/characters/npcs/male_03/walk_{direction}/frame_{i+1:02}.png').convert('RGBA')
                    paths.append({'file':export(Path(role)/f'walk_{direction}/frame_{i:02}.png',walking(idle,leg_source,i)),
                                  'duration_ms':140})
                walks[direction]=paths
            else:walks[direction]=[{'file':idles[direction],'duration_ms':200}]
        portrait=source.crop(PORTRAIT_CELLS[role]).convert('RGB').resize((72,72),Image.Resampling.NEAREST)
        portrait_file=export(Path('portraits')/(role+'.png'),portrait)
        poses={}
        if role in REST_CELLS:
            canvas=(24,36) if role=='worker_a' else (32,36)
            rest=native(source.crop(REST_CELLS[role]),height=24,canvas=canvas)
            poses['injured']={'frames':[{'file':export(Path(role)/'injured.png',rest),'duration_ms':1000}],
                              'loop':True,'anchor':[canvas[0]//2,30]}
        else:
            grips=[(26,31),(21,24),(15,18),(12,12),(12,13),(13,16),(14,20),(14,24),(14,28),(13,31),(21,32),(26,31)]
            durations=[100]*10+[200,400]
            poses['unhook']={'frames':[{'file':export(Path(role)/f'unhook/frame_{i:02}.png',arm_pose(native_idles['left'],grip,i)),
                                       'duration_ms':duration,'grip':list(grip)} for i,(grip,duration) in enumerate(zip(grips,durations))],
                             'loop':False,'anchor':[26,40]}
        actors[role]={'anchor':[12,30],'frame_size':[24,36],'idles':idles,'walks':walks,'poses':poses,
                      'portrait':'arrival_'+role,'portrait_file':portrait_file,'stationary':role!='caretaker'}
    original=Image.open(ROOT/'assets/terrain/elden_vale_sanctuary_kit/cave_keeper_rail.png').convert('RGBA')
    posts=Image.new('RGBA',(72,48))
    for rect in ((2,12,10,36),(62,12,70,36)):posts.alpha_composite(original.crop(rect),rect[:2])
    # Small, fixed wooden pegs make the reachable fastening visibly legible.
    draw=ImageDraw.Draw(posts);draw.line((64,16,67,16),fill='#c3ad76');draw.line((64,17,67,17),fill='#665233')
    posts_file=export(Path('rail')/'posts.png',posts)
    ropes=[]
    for index in range(16):
        rope,end=rope_frame(index)
        ropes.append({'file':export(Path('rail')/f'rope_{index:02}.png',rope),'duration_ms':100,'free_end':list(end)})
    closed=images['rail/rope_00.png'].copy();closed.alpha_composite(posts)
    export(Path('rail')/'closed.png',closed)
    opened=images['rail/rope_15.png'].copy();opened.alpha_composite(posts)
    export(Path('rail')/'open.png',opened)
    sound=ART/'rail/rope_release.wav';out[sound]=release_sound()
    rail={'position':[972,359],'frame_size':[72,48],'posts':posts_file,'rope_frames':ropes,
          'caretaker_position':[1052,404],'facing':'left','contact_point':[66,17],
          'grip_world':[1038,376],'contact_ms':300,'release_ms':400,'duration_ms':1600,
          'guided_until_ms':1000,'sound':sound.relative_to(ROOT).as_posix(),
          'post_footprints':[[4,29,6,4],[62,29,6,4]],'closed_rope_footprint':[10,29,52,4],
          'closed':(ART/'rail/closed.png').relative_to(ROOT).as_posix(),
          'open':(ART/'rail/open.png').relative_to(ROOT).as_posix()}
    manifest={'version':1,'actors':actors,'rail':rail,
              'source_recipe':'assets/source/story/sanctuary_arrival_polish/recipe.json',
              'design':'Native Sanctuary care identities and fixed-post rope release; pixel registration is explicit.'}
    out[MANIFEST]=(json.dumps(manifest,indent=2)+'\n').encode()
    # Rebuilding also repairs these dedicated registrations; generic villagers
    # and portraits owned by other quests retain their existing records.
    registry_path=ROOT/'assets/portraits/eldenmere/portraits.json'
    registry=json.loads(registry_path.read_text())
    registry['portraits']['regent_page']={
        'name':'Page','expression':'attentive',
        'file':'../../story/regent_arrival/actors/portraits/clerk.png',
        'sprite_root':'assets/story/regent/actors/regent_clerk',
        'source':'assets/story/regent_arrival/actors/portraits/clerk.png','native_size':[72,72]}
    for role,name in (('caretaker','Sanctuary caretaker'),('worker_a','Injured Crown worker'),('worker_b','Resting Crown worker')):
        registry['portraits']['arrival_'+role]={
            'name':name,'expression':'concerned' if role=='caretaker' else 'injured',
            'file':'../../story/sanctuary_arrival/art/portraits/'+role+'.png',
            'sprite_root':'assets/story/sanctuary_arrival/art/'+role,
            'source':'assets/source/story/sanctuary_arrival_polish/care_identity_design.png',
            'native_size':[72,72],
            'derivation_recipe':'assets/source/story/sanctuary_arrival_polish/recipe.json'}
    out[registry_path]=(json.dumps(registry,indent=2)+'\n').encode()
    return out


def build(check=False):
    for path,body in products().items():
        if check:
            if not path.exists() or path.read_bytes()!=body:raise ValueError('Stale Sanctuary polish asset: '+str(path.relative_to(ROOT)))
        else:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(body)
    print(('Verified' if check else 'Built')+' Sanctuary care identities and rope-release assets')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');args=parser.parse_args();build(args.check)
