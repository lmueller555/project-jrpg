"""Mechanical native exports and articulated work poses on approved body layers.

Original generated prop sheet and approved appearance parts remain unchanged.
Run with Pillow. Registration: 40x44 canvas, actor ground anchor (20,38).
No live town NPC or flattened whole-body warp is used.
"""
from pathlib import Path
import json
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'assets/characters/garden_workers'
SOURCE = ROOT/'assets/source/characters/garden_workers'
CROPS = {
    'barrel': ((80,60,450,520),(23,28)),
    'basket': ((575,185,975,495),(19,15)),
    'can': ((1060,180,1525,490),(22,15)),
    'plant': ((150,625,425,940),(13,16)),
    'apple': ((680,710,850,910),(6,7)),
    'turnip': ((1130,625,1430,940),(8,9)),
}
# Hands are registered to the prop silhouette, not the transparent cell edge.
# Root controller uses bottom-center prop anchors; coordinates here are canvas.
POSES = {
    'carry': ([(15,27),(24,27)], 0),
    'carry_can': ([(10,20),(20,27)], 0),
    'water': ([(19,20),(29,27)], 1),
    'fill': ([(6,18),(13,13)], 1),
    'weed': ([(23,32),(29,32)], 4),
    'reach': ([(20,14),(24,14)], 0),
    'sort': ([(23,32),(29,32)], 3),
    'admire': ([(18,18),(23,18)], 0),
    'rest': ([(16,31),(24,31)], 5),
}


def color(palette, group, shade, fallback):
    return palette.get(group,{}).get(shade,fallback)


def layer(variant, direction, name):
    return Image.open(ROOT/f'assets/source/characters/npcs/{variant}/walk_{direction}/parts/{name}.png').convert('RGBA')


def body(variant, direction, phase, moving, crouch):
    """Keep feet registered; only waist/torso folds compress for work."""
    image = Image.new('RGBA',(40,44))
    frame = phase+1 if moving else 2  # planted passing pose, never walk while working
    if variant.startswith('female'):
        parts = [(f'frame_{frame:02}_legs',0), (f'frame_{frame:02}_skirt',0),
                 (f'frame_{frame:02}_bodice',crouch), (f'frame_{frame:02}_head',crouch)]
    else:
        parts = [(f'frame_{frame:02}_legs' if moving else 'idle_legs',0),
                 ('waist',0),('shirt',crouch),('head',crouch)]
    for name, offset in parts:
        image.alpha_composite(layer(variant,direction,name),(8,4+offset))
    return image


def arms(image, palette, direction, hands, crouch, phase, pose):
    d = ImageDraw.Draw(image)
    shoulders = {'front':[(16,19),(23,19)], 'back':[(16,19),(23,19)],
                 'right':[(19,20),(22,20)], 'left':[(17,20),(20,20)]}[direction]
    cloth = palette.get('dress',palette.get('shirt',{}))
    for index,(shoulder,hand) in enumerate(zip(shoulders,hands)):
        shoulder = (shoulder[0],shoulder[1]+crouch)
        # One-pixel leaf/soil contact changes; feet and head remain still.
        hand = (hand[0],hand[1]+(phase%2 if pose in ('weed','water','reach') else 0))
        elbow = ((shoulder[0]+hand[0])//2 + (-2 if index==0 else 2),
                 (shoulder[1]+hand[1])//2 + (2 if hand[1]<=shoulder[1] else 0))
        d.line([shoulder,elbow,hand],fill='#1a0e16',width=3)
        d.line([shoulder,elbow],fill=cloth.get('base','#a65b45'),width=2)
        d.point(shoulder,fill=cloth.get('light','#cd8260'))
        d.line([elbow,hand],fill='#eda052',width=2)
        d.point(hand,fill='#e8c49d')


def seated(image, palette, female):
    image.paste((0,0,0,0),(10,29,30,44))
    d = ImageDraw.Draw(image)
    cloth = palette.get('dress' if female else 'trousers',{})
    d.polygon([(15,29),(24,29),(27,34),(24,36),(14,35),(13,32)],
              fill=cloth.get('shadow','#35343b'))
    d.polygon([(16,29),(23,29),(25,33),(23,34),(15,33)],
              fill=cloth.get('base','#4b4952'))
    d.line([(16,30),(22,30),(24,32)],fill=cloth.get('light','#68646e'))
    for x in (15,24):
        d.line([(x,34),(x,37)],fill='#84512e',width=2)
        d.line([(x-1,38),(x+2,38)],fill='#1a0e16',width=2)
        d.point((x,37),fill='#9d6238')


def review():
    names = tuple(POSES)
    native = Image.new('RGB',(len(names)*56,260),'#788264')
    d = ImageDraw.Draw(native)
    for row,role in enumerate(('gardener','picker')):
        for col,pose in enumerate(names):
            p = (col*56+8,row*100+18)
            im = Image.open(OUT/f'{role}_{pose}_right_0.png')
            native.paste(im,p,im)
            key, offset = {'carry':('plant',(0,-7)), 'carry_can':('can',(0,-7)),
                'water':('can',(9,-7)), 'fill':('can',(-16,-15)), 'weed':('turnip',(6,-3)),
                'sort':('apple',(6,-3)), 'reach':('apple',(2,-22)),
                'admire':('apple',(0,-18))}.get(pose,(None,None))
            if key:
                prop=Image.open(OUT/(key+'.png'))
                if pose=='fill':prop=prop.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
                xy=(p[0]+20+offset[0]-prop.width//2,p[1]+38+offset[1]-prop.height)
                native.paste(prop,xy,prop)
            d.text((col*56+2,row*100+68),pose,fill='white')
    for col,key in enumerate(CROPS):
        im=Image.open(OUT/(key+'.png'));native.paste(im,(col*56+10,216),im)
        d.text((col*56+2,245),key,fill='white')
    native.save(SOURCE/'contacts_native.png')
    native.resize((native.width*3,native.height*3),Image.Resampling.NEAREST).save(SOURCE/'contacts_3x.png')


def build():
    OUT.mkdir(parents=True,exist_ok=True)
    sheet=Image.open(SOURCE/'props_generation.png').convert('RGBA')
    for key,(box,size) in CROPS.items():
        im=sheet.crop(box)
        # Remove generated near-transparent edge glow, preserve textured RGB.
        im.putalpha(im.getchannel('A').point(lambda a:255 if a>=128 else 0))
        im=im.crop(im.getbbox()).resize(size,Image.Resampling.NEAREST)
        im.save(OUT/(key+'.png'))
    for role,variant in [('gardener','female_01'),('picker','male_02')]:
        data=json.loads((ROOT/f'assets/characters/npcs/{variant}/palette.json').read_text())
        palette=data.get('material_overrides',data.get('materials'))
        for direction in ('front','back','left','right'):
            for pose,(hands,crouch) in POSES.items():
                moving=pose in ('carry','carry_can')
                for phase in range(4 if moving else 2):
                    image=body(variant,direction,phase,moving,crouch)
                    if pose=='rest':seated(image,palette,variant.startswith('female'))
                    arms(image,palette,direction,hands,crouch,phase,pose)
                    image.save(OUT/f'{role}_{pose}_{direction}_{phase}.png')
    metadata={'status':'implementation visual review; user approval pending',
        'source':'assets/source/characters/garden_workers/props_generation.png',
        'export_crops':CROPS,'alpha_threshold':128,'resampling':'nearest',
        'body_sources':['approved female_01 layered walks','approved male_02 layered walks'],
        'poses':'new articulated occupied arms and seated legs on approved appearance layers; no live town actors reused',
        'canvas':[40,44],'anchor':[20,38],
        'prop_anchor':'bottom center','pose_hand_canvas':{p:h for p,(h,c) in POSES.items()},
        'can_nozzle_from_bottom_center':[10,-13],
        'prop_offsets':{'carry_can':[0,-7],'carry_plant':[0,-7],'water_can':[9,-7],'fill_can':[-16,-15]},
        'review':'assets/source/characters/garden_workers/contacts_native.png'}
    (OUT/'art.json').write_text(json.dumps(metadata,indent=2)+'\n')
    review()

if __name__=='__main__':build()
