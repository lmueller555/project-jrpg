"""Selective Caelan world-pose continuity from the authored refresh atlas.

Only Caelan-owned drawings are exported. Scene timing, physical stations,
logical positions, prop ownership and the other actors retain their existing
registrations. Original prop/FX layers and manifests are retained as immutable
inputs so rebuilding never paints over previously generated results.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from hashlib import sha256
from io import BytesIO
import json
import sys
from pathlib import Path

from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from tools.build_caelan_overworld import action_frame, registered
from tools.caelan_outline import STYLE
SOURCE=ROOT/'assets/source/characters/caelan/overworld_refresh'
LEGACY=SOURCE/'legacy/dependents'
DIRECTIONS=('front','back','left','right')
SOURCE_FILE='assets/source/characters/caelan/overworld_refresh/actions_authored.png'


def encoded(image):
    stream=BytesIO();image.save(stream,format='PNG',optimize=True);return stream.getvalue()


def old(name):return Image.open(LEGACY/name).convert('RGBA')
def metadata(name):return json.loads((LEGACY/name).read_text())
def blank(size=(24,36)):return Image.new('RGBA',size)


def padded(body,size=(40,48),offset=(8,8)):
    result=blank(size);result.alpha_composite(body,offset);return result


def idle(direction):return registered(DIRECTIONS.index(direction))[0]
def walk(direction,phase):return registered(4+4*DIRECTIONS.index(direction)+phase)[0]


def lower_body(upper,lower,split=25):
    """Join independently authored upper pose and matching walking legs."""
    result=blank();result.alpha_composite(upper.crop((0,0,24,split)))
    result.alpha_composite(lower.crop((0,split,24,36)),(0,split));return result


def products():
    result={};records=[]
    def export(path,image,cells=(),anchor=None):
        result[path]=encoded(image)
        records.append(dict(file=path,source_cells=list(cells),canvas=list(image.size),
                            draw_anchor=list(anchor or (12,30)),output_sha256=sha256(result[path]).hexdigest()))
    def document(path,data):result[path]=(json.dumps(data,indent=2,ensure_ascii=False)+'\n').encode()
    def authored_meta(data):
        data=deepcopy(data)
        data['appearance_source']=SOURCE_FILE
        data['appearance_source_sha256']=sha256((ROOT/SOURCE_FILE).read_bytes()).hexdigest()
        data['appearance_registration']='Authored natural poses with native contour; existing canvas, ground anchor and event timing retained.'
        data['outline']=STYLE
        return data

    # Breakfast: matched sitting, spoon and empty-hand cup poses. Existing cup
    # remains a separately owned object; only its authored wrist is registered.
    folder='assets/story/sanctuary_opening/poses'
    export(folder+'/caelan_seated.png',action_frame(13),(13,))
    export(folder+'/caelan_seated_glance.png',action_frame(14),(14,))
    # Retain the established closed-eye pillow key: the generated action atlas
    # intentionally contains awake actions, not an invented open-eyed sleep.
    sleep=old(folder+'/caelan_sleep_head.png')
    export(folder+'/caelan_sleep_head.png',sleep,())
    sit=[idle('right'),action_frame(15),action_frame(13),action_frame(13)]
    # The final settled sitting endpoint and the glance give distinct recovery
    # keys without altering the original authored display-position sequence.
    sit[2]=action_frame(14)
    for phase,image in enumerate(sit):
        export(f'{folder}/caelan_sit/frame_{phase+1:02}.png',image,(15,13,14))
        export(f'{folder}/caelan_stand/frame_{4-phase:02}.png',image,(15,13,14))
    eat_wrists=((17,25),(18,20),(17,17),(18,25))
    cup_wrists=((19,23),(18,20),(17,17),(19,25))
    for phase in range(4):
        export(f'{folder}/caelan_eat/frame_{phase+1:02}.png',action_frame(16+phase),(16+phase,))
        export(f'{folder}/caelan_seated_cup/frame_{phase+1:02}.png',action_frame(20+phase),(20+phase,))
    for name,wrists in [('caelan_eat',eat_wrists),('caelan_seated_cup',cup_wrists)]:
        data=authored_meta(metadata(f'{folder}/{name}/animation.json'))
        for record,wrist in zip(data['frames'],wrists):record['wrist']=list(wrist)
        document(f'{folder}/{name}/animation.json',data)
    for name in ('caelan_sit','caelan_stand'):
        document(f'{folder}/{name}/animation.json',authored_meta(metadata(f'{folder}/{name}/animation.json')))
    wake=[sleep,idle('front'),action_frame(15),idle('front')]
    for phase,image in enumerate(wake):export(f'{folder}/wake_up/frame_{phase+1:02}.png',image,(15,))
    document(folder+'/wake_up/animation.json',authored_meta(metadata(folder+'/wake_up/animation.json')))
    recipe=authored_meta(metadata(folder+'/recipe.json'))
    for direction in ('front','right'):
        path=f'assets/characters/caelan/idle_{direction}.png'
        recipe['source_png_sha256'][path]=sha256(encoded(idle(direction))).hexdigest()
    recipe['notes']='Caelan uses the authored overworld refresh; Tomas, furniture, prop ownership and action timing remain registered.'
    recipe['seated']['caelan']['wrist']=[17,25]
    document(folder+'/recipe.json',recipe)
    export('assets/characters/caelan/participation_sit_front.png',action_frame(12),(12,),anchor=(12,34))

    document('assets/source/characters/caelan/participation_sit/recipe.json',{
        'output':'assets/characters/caelan/participation_sit_front.png',
        'size':[24,36],'draw_anchor':[12,34],'seat_contact':[12,25],
        'boots_baseline':34,'appearance_source':SOURCE_FILE,
        'appearance_sha256':sha256((ROOT/SOURCE_FILE).read_bytes()).hexdigest(),
        'source_cell':12,'method':'Independent authored front seated pose with natural bent knees; fixed game registration.'})

    # Sack ownership/layering is unchanged. Crouch keys are retained as future
    # pickup studies; activating them needs a separately scoped reachable station.
    bag=Image.open(ROOT/'assets/story/halden/sack.png').convert('RGBA')
    grip_boxes={'front':(6,19,17,25),'back':None,'left':(2,18,10,25),'right':(15,18,23,25)}
    def carrying(body,direction,drop=0):
        im=padded(body,(32,40),(4,4))
        point={'front':(8,17),'back':(8,17),'left':(2,16),'right':(14,16)}[direction]
        point=(point[0],point[1]+drop)
        if direction=='back':
            behind=blank((32,40));behind.alpha_composite(bag,point);behind.alpha_composite(im);return behind
        im.alpha_composite(bag,point)
        # Restore the authored palms in front of the sack instead of drawing
        # enlarged replacement hands to satisfy old exact-contact tests.
        box=grip_boxes[direction]
        palms=blank(body.size)
        for y in range(box[1],box[3]):
            for x in range(box[0],box[2]):
                color=body.getpixel((x,y));r,g,b,a=color
                if a and r>=170 and g>=110 and b>=75 and r>g*1.1 and b>g*.5:
                    palms.putpixel((x,y),color)
        im.alpha_composite(palms,(4,4))
        return im
    folder='assets/story/halden/caelan'
    for index,direction in enumerate(DIRECTIONS):
        support=action_frame(index)
        export(f'{folder}/hold_{direction}.png',carrying(support,direction),(index,),anchor=(16,34))
        for phase in range(4):
            body=lower_body(support,walk(direction,phase))
            export(f'{folder}/carry_{direction}_{phase}.png',carrying(body,direction),(index,),anchor=(16,34))
        for phase,drop in enumerate((5,3,1,0)):
            body=action_frame(4+index) if phase<2 else support
            export(f'{folder}/lift_{direction}_{phase}.png',
                   padded(body,(32,40),(4,4)) if phase<2 else carrying(body,direction,drop),
                   (4+index,index),anchor=(16,34))

    # Venn gives now have a visible natural arm gesture. Repair tools are the
    # existing separate-colored shafts/heads from the baseline, not new props.
    folder='assets/story/venn/caelan'
    tool_colors={(131,99,71),(115,126,122),(164,170,160)}
    for index,direction in enumerate(DIRECTIONS):
        export(f'{folder}/give_{direction}.png',padded(action_frame(8+index)),(8+index,),anchor=(20,38))
    for mode in ('hands','tools'):
        for phase,index in enumerate((25,25,26,25)):
            body=padded(action_frame(index));baseline=old(f'{folder}/{mode}_{phase}.png')
            prop=blank(body.size)
            for y in range(18,35):
                for x in range(25,40):
                    pixel=baseline.getpixel((x,y))
                    if pixel[3] and pixel[:3] in tool_colors:prop.putpixel((x,y),pixel)
            body.alpha_composite(prop)
            export(f'{folder}/{mode}_{phase}.png',body,(index,),anchor=(20,38))

    # Authored spell poses replace the coarse procedural arm; preserve the
    # original FX pixels and timing, shifted with the registered palm.
    def spell_atlas(folder,animations_field='animations'):
        data=authored_meta(metadata(folder+'/animation.json'))
        existing=old(folder+'/energy.png');body=blank(existing.size);energy=blank(existing.size)
        for animation in data[animations_field].values():
            for record in animation['frames']:
                x,y,w,h=record['rect'];angle=record['angle_degrees']
                index=28 if angle>=65 else 29 if angle>=15 else 30
                native=idle('right') if angle==90 else action_frame(index)
                palm=(11,24) if angle==90 else (19,18) if index==29 else (20,15) if index==30 else (14,24)
                body.alpha_composite(padded(native),(x,y))
                fx=existing.crop((x,y,x+w,y+h));previous=record.get('casting_hand',[22,27])
                destination=(palm[0]+8,palm[1]+8)
                shifted=blank((w,h));shifted.alpha_composite(fx,(destination[0]-previous[0],destination[1]-previous[1]))
                energy.alpha_composite(shifted,(x,y))
                record['casting_hand']=list(destination)
                record['appearance_source_cell']=index if angle!=90 else None
                record['joints']={'casting':[[21,25],[24,27],list(destination)]}
        composite=body.copy();composite.alpha_composite(energy)
        export(folder+'/poses.png',composite,range(28,31),anchor=(20,38))
        export(folder+'/body.png',body,range(28,31),anchor=(20,38))
        export(folder+'/casting_arm.png',blank(body.size),(),anchor=(20,38))
        export(folder+'/energy.png',energy,(),anchor=(20,38))
        export(folder+'/source_body.png',idle('right'),())
        data['source_idle_sha256']=sha256(encoded(idle('right'))).hexdigest()
        data.pop('preserved_source_regions',None)
        document(folder+'/animation.json',data)
    spell_atlas('assets/story/venn/magicks')
    spell_atlas('assets/story/mill/poses')

    # Lantern assembly uses new naturally bent working arms. Frame props and
    # their transfer remain owned by the existing quest controller.
    folder='assets/story/lantern/poses';data=authored_meta(metadata(folder+'/caelan.json'))
    frame_layer=old(folder+'/caelan_frame.png');body=blank(frame_layer.size)
    for action,frames in data['actions'].items():
        choices=(24,25,26,26,27) if action=='work' else (24,25,26,27)
        for phase,record in enumerate(frames):
            x,y,w,h=record['rect'];index=choices[phase]
            body.alpha_composite(padded(action_frame(index)),(x,y))
            record['appearance_source_cell']=index
    image=body.copy();image.alpha_composite(frame_layer)
    export(folder+'/caelan.png',image,range(24,28),anchor=(20,38))
    export(folder+'/caelan_body.png',body,range(24,28),anchor=(20,38))
    export(folder+'/caelan_working_arm.png',blank(body.size),(),anchor=(20,38))
    export(folder+'/caelan_source.png',idle('right'),())
    data['source_sha256']=sha256(encoded(idle('right'))).hexdigest()
    data.pop('preserved_source_regions',None)
    document(folder+'/caelan.json',data)

    # Elira's lantern remains the existing sprite, behind Caelan in rear view.
    # Shelf/world ownership transitions and logical ladder stations are intact.
    folder='assets/story/elira'
    lantern=Image.open(ROOT/'assets/terrain/eldenmere/elira_interior/sprites/lantern_unlit.png').convert('RGBA')
    def lantern_canvas(body,origin=None,behind=False):
        im=blank((40,64));pos=(8+(origin or (18,2))[0],24+(origin or (18,2))[1])
        if origin is not None and behind:im.alpha_composite(lantern,pos)
        im.alpha_composite(body,(8,24))
        if origin is not None and not behind:im.alpha_composite(lantern,pos)
        return im
    for index,direction in enumerate(DIRECTIONS):
        support=action_frame(index)
        origin={'front':(12,0),'back':(12,0),'left':(-5,0),'right':(16,0)}[direction]
        export(f'{folder}/hold_{direction}.png',lantern_canvas(support,origin,direction=='back'),(index,),anchor=(20,54))
        export(f'{folder}/give_{direction}.png',lantern_canvas(action_frame(8+index)),(8+index,),anchor=(20,54))
        for phase in range(4):
            body=lower_body(support,walk(direction,phase))
            export(f'{folder}/carry_{direction}_{phase}.png',lantern_canvas(body,origin,direction=='back'),(index,),anchor=(20,54))
    reach=[idle('back'),action_frame(1),action_frame(9),action_frame(31)]
    take=[action_frame(31),action_frame(9),action_frame(9),action_frame(1)]
    for phase in range(4):
        fraction=phase/3
        export(f'{folder}/reach_{phase}.png',lantern_canvas(reach[phase]),(9,31),anchor=(20,54))
        origin=(round(6+6*fraction),round(-19+19*fraction))
        export(f'{folder}/take_{phase}.png',lantern_canvas(take[phase],origin,True),(31,9,1),anchor=(20,54))
        export(f'{folder}/step_{phase}.png',lantern_canvas(walk('back',phase)),(),anchor=(20,54))
        export(f'{folder}/down_{phase}.png',lantern_canvas(lower_body(action_frame(1),walk('back',phase)),(12,0),True),(1,),anchor=(20,54))
        body=action_frame(0)
        origin=(round(18-8*fraction),round(2+6*fraction))
        export(f'{folder}/place_{phase}.png',lantern_canvas(body,origin),(0,),anchor=(20,54))
        export(f'{folder}/place_empty_{phase}.png',lantern_canvas(body),(0,),anchor=(20,54))

    manifest=dict(version=1,status='review',outline=STYLE,source=SOURCE_FILE,
                  travel_source='assets/source/characters/caelan/overworld_refresh/travel_authored.png',
                  travel_source_sha256=sha256((SOURCE/'travel_authored.png').read_bytes()).hexdigest(),
                  covered_sleep_exception='The established closed-eye pillow-head key remains until a matching closed-eye source is authored.',
                  source_sha256=sha256((ROOT/SOURCE_FILE).read_bytes()).hexdigest(),
                  builder='tools/build_caelan_overworld_dependents.py',outputs=records,
                  preserved=['scene timing','ground registrations','other characters','props and ownership cues'],
                  scope='Native overworld derivatives only; larger cinematic and combat banks are independent.',
                  interaction_followups=['Halden pickup needs a reachable station before the supplied empty-hand crouch keys can be activated.'])
    document('assets/source/characters/caelan/overworld_refresh/dependents.json',manifest)
    return result


def build(check=False):
    changed=[];output=products()
    for name,raw in output.items():
        path=ROOT/name
        if not path.exists() or path.read_bytes()!=raw:
            changed.append(name)
            if not check:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    if check and changed:raise SystemExit('Stale Caelan dependent exports: '+', '.join(changed))
    return output


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true')
    args=parser.parse_args();print(f'{len(build(args.check))} dependent exports')
