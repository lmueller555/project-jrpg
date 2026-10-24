"""Build dedicated bucket poses from approved female_02 appearance/stride parts.

Approved sprites, templates and town scenery are read-only inputs.
"""
import json
import math
from pathlib import Path
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'assets/source/characters/npcs/female_02/gardener'
OUTPUT=ROOT/'assets/characters/npcs/female_02/gardener'
BASE=ROOT/'assets/characters/npcs/female_02'
PARTS=ROOT/'assets/source/characters/npcs/female_02'
DIRECTIONS=('front','left','right','back')


def read(path):return json.loads(path.read_text())
def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n')
def blank(size=(24,36)):return Image.new('RGBA',size)
def opened(path):return Image.open(path).convert('RGBA')


def arm(image,points,palette):
    d=ImageDraw.Draw(image);shoulder,elbow,hand=map(tuple,points)
    d.line((shoulder,elbow,hand),fill=palette['outline'],width=4)
    d.line((shoulder,elbow),fill=palette['fabric_base'],width=3)
    d.line((shoulder[0],shoulder[1],elbow[0],elbow[1]-1),fill=palette['fabric_light'],width=1)
    d.line((elbow,hand),fill=palette['skin_shadow'],width=2)
    d.line((elbow[0],elbow[1]+1,hand[0],hand[1]),fill=palette['skin_base'],width=1)
    d.point(hand,fill=palette['skin_base'])


def body(direction,pose,frame=None,lean=(0,0),preserve_free_arm=False):
    """Keep approved head/neck, dress and stride; articulate only occupied arms."""
    recipe=read(BASE/f'walk_{direction}/recipe.json')
    palette=recipe['palette']
    folder=PARTS/f'walk_{direction}/parts'
    index=1 if frame is None else frame
    prefix=f'frame_{index:02}_'
    result=blank()
    if frame is None:
        idle=opened(BASE/f'idle_{direction}.png')
        result.paste(idle.crop((0,29,24,36)),(0,29))
    else:result.alpha_composite(opened(folder/(prefix+'legs.png')))
    result.alpha_composite(opened(folder/(prefix+'skirt.png')))
    result.alpha_composite(opened(folder/(prefix+'bodice.png')),tuple(lean))
    if preserve_free_arm:
        # Empty pail occupies anatomical right; the other arm keeps its stride.
        side='right' if direction in ('front','left') else 'left'
        result.alpha_composite(opened(folder/(prefix+side+'_arm.png')))
    if not pose['arms']:
        for side in ('left','right'):result.alpha_composite(opened(folder/(prefix+side+'_arm.png')))
    # Arm layer has room for a hand extending toward water beyond the body frame.
    arms=blank((48,48))
    for points in pose['arms']:
        shifted=[(x+12,y+6) for x,y in points]
        arm(arms,shifted,palette)
    # Some older walk metadata lists an unexported neckline layer; recover that
    # registered rectangle from the approved composite without rebuilding it.
    neckline=blank()
    x,y,w,h=recipe['neckline_rect']
    if frame in (2,4):y-=1
    source=opened(BASE/f'walk_{direction}/frame_{index:02}.png')
    if w and h:neckline.paste(source.crop((x,y,x+w,y+h)),(x,y))
    result.alpha_composite(neckline,tuple(lean))
    if frame is None:
        head=blank();head.paste(idle.crop((0,0,24,14)),(0,0))
    else:head=opened(folder/(prefix+'head.png'))
    result.alpha_composite(head,tuple(lean))
    # Keep articulated hands visible while heads/necklines cover shoulder seams.
    canvas=blank((48,48));canvas.alpha_composite(result,(12,6))
    canvas.alpha_composite(arms)
    return canvas,arms


def bucket(angle,level,palette):
    """Native pixel pail rotated around its held handle, never the whole actor."""
    image=blank((32,32));d=ImageDraw.Draw(image)
    radians=math.radians(angle);cos=math.cos(radians);sin=math.sin(radians)
    def point(x,y):return (round(12+(x-7)*cos-(y-2)*sin),round(6+(x-7)*sin+(y-2)*cos))
    def polygon(points,color):d.polygon([point(*p) for p in points],fill=palette[color])
    def line(points,color,width=1):d.line([point(*p) for p in points],fill=palette[color],width=width)
    line([(3,7),(3,3),(5,1),(8,1),(11,3),(11,7)],'outline',2)
    line([(4,7),(4,3),(6,2),(8,2),(10,3),(10,7)],'iron_light')
    polygon([(2,6),(11,6),(10,14),(4,14)],'outline')
    polygon([(3,7),(10,7),(9,13),(5,13)],'wood')
    line([(5,8),(6,13)],'wood_light');line([(8,8),(8,13)],'wood_dark')
    line([(3,8),(10,8)],'iron');line([(4,12),(10,12)],'iron')
    polygon([(3,6),(10,6),(9,8),(4,8)],'wood_dark')
    if level:
        # Filling levels expose progressively more of the blue surface.
        left=6 if level==1 else 5 if level==2 else 4
        line([(left,7),(13-left,7)],'water')
        if level==4:line([(4,6),(9,6)],'water')
        if level>1:line([(5,7),(6,7)],'water_light')
    line([(2,5),(10,5)],'iron_light')
    line([(2,6),(3,8),(10,8),(11,6)],'iron_light')
    spout=point(2 if angle<0 else 11,7)
    return image,{'grip':[12,6],'spout':list(spout)}


def build():
    recipe=read(SOURCE/'recipe.json')
    OUTPUT.mkdir(parents=True,exist_ok=True);(SOURCE/'parts').mkdir(exist_ok=True)
    poses={};animations={};buckets={}
    def export(name,direction,spec,frame=None,lean=(0,0),free=False):
        image,arms=body(direction,spec,frame,lean,free)
        image.save(OUTPUT/(name+'.png'));arms.save(SOURCE/'parts'/(name+'_arms.png'))
        poses[name]={'body':name+'.png','grip':spec['grip'],'order':spec.get('order','after')}
    for mode,directions in recipe['carry'].items():
        for direction,spec in directions.items():
            export(f'idle_{mode}.{direction}',direction,spec,free=mode=='empty')
            seq=[]
            for index in range(1,5):
                dy=-1 if index in (2,4) else 0
                bob={**spec,'grip':[spec['grip'][0],spec['grip'][1]+dy],
                     'arms':[[[x,y+dy] for x,y in limb] for limb in spec['arms']]}
                name=f'carry_{mode}.{direction}_{index:02}'
                export(name,direction,bob,index,free=mode=='empty')
                seq.append({'pose':name,'duration_ms':140})
            animations[f'carry_{mode}.{direction}']=seq
    for name,spec in recipe['work_poses'].items():
        export(name,spec['direction'],spec,lean=spec['lean'])
    animations.update(recipe['animations'])
    for direction in ('left','right'):
        animations[f'inspect.{direction}']=[{'pose':f'idle_full.{direction}','duration_ms':800}]
        animations[f'pour.{direction}']=[]
        for frame in recipe['pour_sequence']:
            name=f"raise_{direction}" if frame['pose']=='raise' else f'idle_full.{direction}'
            angle=frame['angle']*(-1 if direction=='left' else 1)
            animations[f'pour.{direction}'].append({**frame,'pose':name,'angle':angle})
    for angle in (-50,-25,0,25,50):
        for level in range(5):
            image,data=bucket(angle,level,recipe['bucket_palette'])
            name=f'bucket_{angle}_{level}'
            image.save(OUTPUT/(name+'.png'));buckets[name]={**data,'file':name+'.png'}
    write(OUTPUT/'animations.json',{
        'id':recipe['id'],'status':recipe['status'],'character':recipe['character'],
        'body_frame_size':[24,36],'action_canvas':[48,48],'body_offset':[12,6],
        'draw_anchor':[24,36],'foot_anchor':[24,40],
        'poses':poses,'animations':animations,'buckets':buckets,
        'source_recipe':'../../../../source/characters/npcs/female_02/gardener/recipe.json'
    })
    # Contact sheet includes body plus the actual bucket attachment.
    selected=['idle_empty.front','idle_full.front','idle_full.left','idle_full.right',
              'idle_full.back','fill_dip','raise_left','raise_right']
    sheet=Image.new('RGB',(48*len(selected),48),'#e8edf2')
    for i,name in enumerate(selected):
        spec=poses[name];body_image=opened(OUTPUT/spec['body'])
        angle=-50 if name=='raise_left' else 50 if name=='raise_right' else 0
        pail=opened(OUTPUT/f'bucket_{angle}_4.png')
        scene=blank((48,48));pos=(12+spec['grip'][0]-12,6+spec['grip'][1]-6)
        if spec['order']=='before':scene.alpha_composite(pail,pos)
        scene.alpha_composite(body_image)
        if spec['order']=='after':scene.alpha_composite(pail,pos)
        sheet.paste(scene,(48*i,0),scene)
    sheet.resize((sheet.width*4,192),Image.Resampling.NEAREST).save(OUTPUT/'poses_review.png')
    print(f'Built gardener: {len(poses)} body poses, {len(buckets)} bucket states; approved source sprites unchanged.')


if __name__=='__main__':build()
