"""Author Tomas's sanctuary tasks using approved pixel parts and joint poses.

Run with the asset Python (Pillow). Existing idles, walks and room artwork are
read-only inputs. The small furniture additions use the approved cottage kit.
"""
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'assets/characters/tomas/routines'
SOURCE=ROOT/'assets/source/characters/tomas/routines'
BODY=ROOT/'assets/source/characters/tomas'
OFFSET=(20,6)
SIZE=(64,48)
M=json.loads((ROOT/'assets/characters/tomas/palette.json').read_text())['materials']
ROOM='sanctuary_dining'
TOWN='eldenmere.playable'


def write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,indent=2)+'\n')


def blank():return Image.new('RGBA',SIZE)
def opened(path):return Image.open(path).convert('RGBA')
def point(p):return p[0]+OFFSET[0],p[1]+OFFSET[1]


def bundle():
    im=Image.new('RGBA',(9,7));d=ImageDraw.Draw(im)
    d.rectangle((0,1,8,6),fill=M['outline'][0])
    d.rectangle((1,2,7,5),fill=M['linen'][1])
    d.line((1,2,7,2),fill=M['linen'][2])
    d.rectangle((3,1,4,6),fill=M['leather'][1])
    d.line((1,5,7,5),fill=M['linen'][0])
    return im


def mechanism(angle=0):
    """A tiny fixed-base model: only its wheel, peg and crank move."""
    im=Image.new('RGBA',(13,17));d=ImageDraw.Draw(im)
    dark=M['outline'][0];wood=M['leather'][1];light=M['linen'][1]
    d.rectangle((0,13,12,16),fill=dark)
    d.rectangle((1,14,11,15),fill=wood)
    d.line((1,13,1,6),fill=dark,width=3)
    d.line((1,12,1,6),fill=wood)
    d.ellipse((2,2,10,12),fill=dark)
    d.ellipse((3,3,9,11),fill=M['hair'][0])
    for a in (angle,angle+math.pi/2):
        dx=round(3*math.cos(a));dy=round(3*math.sin(a))
        d.line((6-dx,7-dy,6+dx,7+dy),fill=light)
    d.point((6,7),fill=M['buckle'][0])
    peg=(6+round(4*math.cos(angle)),7+round(4*math.sin(angle)))
    d.rectangle((peg[0],peg[1],peg[0]+1,peg[1]+1),fill=M['buckle'][0])
    # A lower crank makes the hand movement distinct from the wheel spokes.
    crank=(11+round(math.cos(angle)),9+round(3*math.sin(angle)))
    d.line((9,9,*crank),fill=dark,width=2)
    d.point(crank,fill=light)
    return im


def parts(direction,walk=None):
    base=blank();folder=BODY/f'walk_{direction}/parts'
    if walk is None:
        legs=BODY/('layers' if direction=='front' else f'idle_{direction}_layers')/'legs_and_boots.png'
        base.alpha_composite(opened(legs),OFFSET)
        for name in ('waist','tunic_hem','upper_body'):
            base.alpha_composite(opened(folder/f'{name}.png'),OFFSET)
        head=opened(folder/'head.png')
    else:
        for name in ('legs','left_knee_patch','waist','tunic_hem','upper_body'):
            base.alpha_composite(opened(folder/f'frame_{walk:02}_{name}.png'),OFFSET)
        head=opened(folder/f'frame_{walk:02}_head.png')
    return base,head


def arm(im,joints):
    d=ImageDraw.Draw(im);s,e,h=map(point,joints)
    d.line((s,e,h),fill=M['outline'][0],width=3,joint='curve')
    d.line((s,e),fill=M['linen'][0],width=2)
    d.line((e,h),fill=M['linen'][1],width=2)
    d.point((e[0],e[1]-1),fill=M['linen'][2])
    d.line((h[0],h[1]-1,h[0],h[1]+1),fill=M['skin'][0],width=2)


def frame(direction,arms,prop=None,head_offset=(0,0),walk=None):
    im,head=parts(direction,walk)
    # North-facing carried objects stay behind the torso and head. Profiles
    # show the hands and bundle in front of the chest, with head drawn last.
    if prop and direction=='back':
        back=blank();back.alpha_composite(prop[0],point(prop[1]));back.alpha_composite(im);im=back
    if prop and direction!='back':im.alpha_composite(prop[0],point(prop[1]))
    for joints in arms:arm(im,joints)
    im.alpha_composite(head,(OFFSET[0]+head_offset[0],OFFSET[1]+head_offset[1]))
    return im


REST_L=[[(11,17),(12,21),(12,24)]]
REACH_L=[[(11,17),(8,17),(5,19)]]
BOX_REACH=[[(11,17),(7,14),(5,15)]]
HOLD_L=[[(11,17),(6,20),(3,20)]]
REST_R=[[(13,17),(13,21),(13,24)]]


def build():
    OUT.mkdir(parents=True,exist_ok=True);(OUT/'props').mkdir(exist_ok=True)
    bundle().save(OUT/'props/bundle.png');mechanism().save(OUT/'props/mechanism.png')
    # A small open wooden storage box, with a clearly visible top surface.
    crate=Image.new('RGBA',(24,24));d=ImageDraw.Draw(crate)
    d.rectangle((0,3,23,22),fill=M['outline'][0]);d.rectangle((1,4,22,21),fill=M['leather'][0])
    d.polygon(((1,4),(18,1),(23,4),(5,9)),fill=M['leather'][1])
    d.rectangle((2,10,21,19),fill=M['leather'][1])
    d.line((2,13,21,13),fill=M['leather'][0]);d.line((2,17,21,17),fill=M['leather'][0])
    d.line((3,9,3,20),fill=M['hair'][1]);d.line((20,8,20,20),fill=M['hair'][1])
    crate.save(OUT/'props/storage_box.png')
    stack=Image.new('RGBA',(16,10));stack.alpha_composite(bundle(),(1,3));stack.alpha_composite(bundle(),(5,0));stack.save(OUT/'props/stack.png')
    actions={};source={}

    def export(name,direction,specs):
        directory=OUT/name;directory.mkdir(exist_ok=True);records=[];source[name]=[]
        for i,s in enumerate(specs,1):
            phase,ms,arms,owner,prop,head=s
            im=frame(direction,arms,prop,head)
            im.save(directory/f'frame_{i:02}.png')
            records.append({'file':f'{name}/frame_{i:02}.png','phase':phase,'duration_ms':ms,'prop_owner':owner})
            source[name].append({'phase':phase,'duration_ms':ms,'arms':arms,'prop_owner':owner,
                                 'prop_anchor':prop[1] if prop else None,'head_offset':head})
        actions[name]={'facing':direction,'duration_ms':sum(s[1] for s in specs),'frames':records}

    def s(phase,ms,arms=REST_L,owner='surface',prop=None,head=(0,0)):
        return phase,ms,arms,owner,prop,head

    # Prop anchors are registered in world space with the room-owned copies.
    # At station [160,262], body top-left is [148,232], bundle is [147,248].
    export('prepare','left',[
        s('check_stack',700),s('reach_to_neaten',250,REACH_L),
        s('straighten_bundle',350,REACH_L,'actor',(bundle(),(-1,16))),
        s('press_fold',350,[[(11,17),(8,19),(5,20)]],'actor',(bundle(),(-1,17))),
        s('align_with_stack',350,REACH_L,'actor',(bundle(),(-1,16))),
        s('release_on_table',400,REACH_L),s('check_work',600),
        s('reach_for_delivery',250,REACH_L),
        s('lift_from_table',250,REACH_L,'actor',(bundle(),(-1,14))),
        s('bring_to_chest',250,HOLD_L,'actor',(bundle(),(-2,17))),
    ])
    export('store_bundle','left',[
        s('hold_at_storage',250,HOLD_L,'actor',(bundle(),(-2,17))),
        s('reach_over_box',300,BOX_REACH,'actor',(bundle(),(-3,9))),
        s('lower_to_box',300,BOX_REACH,'actor',(bundle(),(-3,10))),
        s('release_to_storage',350,BOX_REACH),s('hands_clear',500),
    ])
    export('fetch_bundle','left',[
        s('check_next_bundle',400),s('reach_storage',250,BOX_REACH),
        s('lift_from_box',250,BOX_REACH,'actor',(bundle(),(-3,10))),
        s('hold_for_return',250,HOLD_L,'actor',(bundle(),(-2,17))),
    ])
    export('return_bundle','left',[
        s('hold_at_table',250,HOLD_L,'actor',(bundle(),(-2,17))),
        s('reach_table',300,REACH_L,'actor',(bundle(),(-1,14))),
        s('lower_to_stack',250,REACH_L,'actor',(bundle(),(-1,16))),
        s('release_to_table',350,REACH_L),s('hands_clear',450),
    ])
    # [104,262] registers model [108,242] to native [16,10].
    # Keep the fixed base still while the crank hand follows a small circle.
    tink=[s('consider_the_model',700,REST_R)]
    for turn in range(2):
        for n in range(8):
            a=n*math.pi/4
            # Model sits just left of the station's hand; use a small profile
            # reach, never scale or stretch the approved body.
            tink.append(s('turn_crank',150,[[(13,17),(20,18),(27+round(math.cos(a)),19+round(3*math.sin(a))) ]],
                          'actor',(mechanism(a),(16,10))))
    tink += [s('wheel_catches',500,[[(13,17),(20,18),(28,19)]],'actor',(mechanism(0),(16,10)),(1,1)),
             s('lean_in_to_adjust',400,[[(13,17),(21,17),(27,14)]],'actor',(mechanism(0),(16,10)),(1,1))]
    for n in range(8):
        a=n*math.pi/4
        tink.append(s('try_again',140,[[(13,17),(20,18),(27+round(math.cos(a)),19+round(3*math.sin(a)))]],
                      'actor',(mechanism(a),(16,10))))
    tink += [s('stop_and_inspect',500,REST_R,'actor',(mechanism(0),(16,10))),s('leave_model_on_bench',650,REST_R)]
    export('tinker','right',tink)
    # Separate idle directions make his outdoor glance readable at native scale.
    look=[]
    for direction,ms,phase in [('front',700,'take_in_the_courtyard'),('right',1100,'look_toward_the_workshop'),
                              ('front',700,'pause'),('left',900,'watch_the_village_path'),('front',700,'settle')]:
        im=blank();im.alpha_composite(opened(ROOT/f'assets/characters/tomas/idle_{direction}.png'),OFFSET)
        directory=OUT/'courtyard_look';directory.mkdir(exist_ok=True)
        i=len(look)+1;im.save(directory/f'frame_{i:02}.png')
        look.append({'file':f'courtyard_look/frame_{i:02}.png','duration_ms':ms,'phase':phase,'prop_owner':'surface'})
    actions['courtyard_look']={'facing':'front','duration_ms':sum(x['duration_ms'] for x in look),'frames':look}
    walks={}
    for direction in ('front','left','right','back'):
        arms={'front':[[(7,17),(7,21),(9,21)],[(16,17),(17,21),(15,21)]],
              'back':[[(7,17),(6,19),(9,19)],[(16,17),(18,19),(15,19)]],
              'left':HOLD_L,'right':[[(13,17),(18,20),(21,20)]]}[direction]
        anchor={'front':(8,18),'back':(8,15),'left':(-2,17),'right':(17,17)}[direction]
        records=[]
        for i in range(1,5):
            # The original coordinated bob is baked into every walking part.
            dy=-1 if i in (2,4) else 0
            moved=[[(x,y+dy) for x,y in joints] for joints in arms]
            im=frame(direction,moved,(bundle(),(anchor[0],anchor[1]+dy)),walk=i)
            directory=OUT/f'carry_{direction}';directory.mkdir(exist_ok=True)
            im.save(directory/f'frame_{i:02}.png')
            records.append({'file':f'carry_{direction}/frame_{i:02}.png','duration_ms':140})
        walks[direction]=records
    write(OUT/'animations.json',{'status':'review','character':'tomas','frame_size':list(SIZE),
          'body_offset':list(OFFSET),'draw_anchor':[32,36],'sprite_root':'assets/characters/tomas',
          'animations':actions,'walk_sets':{'bundle':walks}})
    write(SOURCE/'poses.json',{'body_offset':list(OFFSET),'frame_size':list(SIZE),'actions':source,
          'approved_inputs':'assets/source/characters/tomas/walk_DIRECTION/parts',
          'notes':'Authored three-joint sleeve poses; approved head, torso, legs, palette and walk timing retained.'})
    build_schedule()
    register()
    print('Built Tomas work poses, carry walks, props, schedule and dialogue.')


def build_schedule():
    steps=[]
    def add(id,kind,**kw):steps.append({'id':id,'type':kind,**kw})
    def move(id,points,carry=False):add(id,'move',waypoints=points,**({'walk_set':'bundle','speed':36} if carry else {}))
    def action(id,name=None,facing='left'):add(id,'action',animation=name or id,facing=facing)
    action('prepare')
    move('carry_to_storage',[[200,262],[200,256]],True)
    action('store_bundle')
    move('walk_to_model',[[200,300],[104,300],[104,262]])
    action('tinker',facing='right')
    add('think_about_model','wait',facing='right',duration_range_ms=[2500,4500])
    move('walk_to_hall',[[104,300],[216,300],[216,294]])
    add('enter_hall','transfer',scene='sanctuary_hall',position=[264,90],facing='front',departure_door='hall',arrival_door='dining')
    move('cross_hall',[[264,120],[216,120],[216,294],[208,294]])
    add('enter_courtyard','transfer',scene=TOWN,position=[386,306],facing='front',departure_door='courtyard',arrival_door='sanctuary')
    move('walk_to_courtyard_pause',[[386,406],[418,406]])
    action('courtyard_look',facing='front')
    add('courtyard_break','wait',facing='front',duration_range_ms=[12000,20000])
    move('return_to_sanctuary',[[386,406],[386,306]])
    add('return_to_hall','transfer',scene='sanctuary_hall',position=[208,294],facing='back',departure_door='sanctuary',arrival_door='courtyard')
    move('return_through_hall',[[216,294],[216,120],[264,120],[264,90]])
    add('return_to_dining','transfer',scene=ROOM,position=[216,294],facing='back',departure_door='dining',arrival_door='hall')
    move('walk_to_storage',[[216,300],[200,300],[200,256]])
    action('fetch_bundle')
    move('carry_to_table',[[200,300],[160,300],[160,262]],True)
    action('return_bundle')
    add('check_preparations','wait',facing='left',duration_range_ms=[1800,3200])

    # The single loose bundle has one owner throughout the complete cycle.
    # It is brought back from storage at the end; nothing respawns off-screen.
    table=True;stored=False
    for step in steps:
        id=step['id']
        if id=='prepare':table=True;stored=False
        if id=='carry_to_storage':table=False
        if id=='store_bundle':stored=True
        if id=='carry_to_table':stored=False
        if id=='return_bundle':table=True
        step['surface_visibility']={'table_bundle':table,'stored_bundle':stored}
    props=[
        {'id':'table_bundle','position':[147,248],'action_steps':['prepare','return_bundle'],'image':'bundle'},
        {'id':'stored_bundle','position':[185,236],'action_steps':['store_bundle','fetch_bundle'],'image':'bundle'},
        {'id':'model','position':[108,242],'action_step':'tinker','image':'mechanism'},
        {'id':'spare_stack','position':[131,246],'image':'stack'},
    ]
    for p in props:
        p.update(scene=ROOM,sort_y=260,sort_priority=1.5)
        p['image']=f"assets/characters/tomas/routines/props/{p['image']}.png"
    write(ROOT/'assets/maps/eldenmere/routines/tomas.json',{
        'id':'tomas_sanctuary_schedule','status':'review','start_scene':ROOM,'start_position':[160,262],
        'probe_size':[10,6],'speed':44,'steps':steps,'surface_props':props,
        'review':{'prepare':{'scene':ROOM,'station':[160,262]},
                  'store_bundle':{'scene':ROOM,'station':[200,256]},
                  'tinker':{'scene':ROOM,'station':[104,262]},
                  'courtyard_look':{'scene':TOWN,'station':[418,406]}}})


def register():
    path=ROOT/'assets/maps/eldenmere/playable/map.json';data=json.loads(path.read_text())
    record={'id':'tomas','name':'Tomas','routine':'sanctuary_schedule','scene':ROOM,'position':[160,262],
            'probe_size':[10,6],'draw_anchor':[12,30],'sprite_root':'assets/characters/tomas',
            'animation':'assets/characters/tomas/routines/animations.json','behavior':'assets/maps/eldenmere/routines/tomas.json'}
    data['persistent_npcs']=[x for x in data['persistent_npcs'] if x['id']!='tomas']+[record]
    write(path,data)
    path=ROOT/'assets/maps/eldenmere/building_interiors/rooms/sanctuary_dining/map.json';data=json.loads(path.read_text())
    additions=[('tomas_work_table',[108,240],260,'assets/terrain/eldenmere/cottage_furniture/sprites/table.png'),
               ('tomas_storage_box',[174,228],252,'assets/characters/tomas/routines/props/storage_box.png')]
    data['entities']=[x for x in data['entities'] if not x['id'].startswith('tomas_')]
    for id,pos,sort,pathimg in additions:
        data['entities'].append({'id':id,'position':pos,'sort_y':sort,'sort_priority':0,
                                 'frames':[pathimg],'frame_duration_ms':300,'phase_offset':0})
    collision=Image.open(path.parent/'collision.png').copy();d=ImageDraw.Draw(collision)
    d.rectangle((108,266,155,283),fill=255);d.rectangle((174,240,197,251),fill=255)
    collision.save(path.parent/'collision_with_tomas.png')
    data['collision']=(path.parent/'collision_with_tomas.png').relative_to(ROOT).as_posix()
    write(path,data)
    path=ROOT/'assets/dialogue/eldenmere.json';data=json.loads(path.read_text())
    data['speakers']['tomas']={'name':'Tomas','portrait':'tomas'}
    def line(who,text):return {'speaker':who,'text':text}
    data['characters']['tomas']={'conversations':[
        {'id':'tomas_repeat','requires':['tomas_greeted'],'lines':[
            line('tomas','One more adjustment. Then I really am getting back to the preparations.'),
            line('caelan','Should I tell Mother Serene that?'),line('tomas','Tell her the preparations are progressing. That covers both things.')]},
        {'id':'tomas_greeting','status':'approved',
         'script_reference':'docs/narrative/game_01/TOMAS_AMBIENT_DIALOGUE.md',
         'sets':['tomas_greeted'],'lines':[
            line('tomas','Caelan, can you look at this?'),
            line('caelan',"What's wrong?"),
            line('tomas',"It turns most of the way, then it sticks. I can't see what's catching."),
            line('caelan','Is the pin bent?'),
            line('tomas','I thought so, but it looks straight.'),
            line('caelan','Have you shown Mira?'),
            line('tomas','Not yet. I wanted to get it working myself.'),
            line('caelan','You can still ask her.'),
            line('tomas',"I know. I will if I can't find it.")]}]}
    data['note']='Serene breakfast dialogue, approved Tomas opening exchange and existing repeat dialogue; no quest starts. Flags persist for the running session.'
    write(path,data)


if __name__=='__main__':build()
