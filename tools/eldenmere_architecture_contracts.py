"""Validate source-owned Eldenmere spatial contracts and render construction references.

Diagrams are deliberately labelled construction references, never gameplay evidence.
All coordinates in the schedule are logical; diagrams display them at 2× density.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
ROOT=Path(__file__).resolve().parents[1]
SCHEDULE=ROOT/'assets/source/maps/eldenmere/town_hd/architecture_schedule.json'
BUILDINGS={'sanctuary','mira','mill','school','halden','elira','venn','home_a','home_b','home_c','liam_house','inn','item_shop'}

def validate_schedule(schedule, town):
    """Fail fast on accidental portal/scale changes before generating artwork."""
    records=schedule['buildings'];assert len(records)==13 and {r['id'] for r in records}==BUILDINGS
    doors={r['id']:r for r in town['doors']};entities={r['id']:r for r in town['entities']}
    for r in records:
        name=r['id'];entity=entities[name];door=doors[name]
        assert entity['position']==r['position_world_logical'],name+' position'
        assert entity['logical_size']==r['logical_canvas'],name+' canvas'
        assert entity['sort_y']==r['depth_baseline_world_logical'],name+' baseline'
        for key,value in r['entrance'].items():assert door[key]==value,(name,key)
        for scene,path in r['interior_scenes'].items():assert town['interior_scenes'][scene]==path,(name,scene)
        assert r['approach_clearance_world_logical'][2]>=24,name+' clearance'
        if r['chimney']:
            for hearth in r['chimney']['hearths']:
                scene=json.loads((ROOT/town['interior_scenes'][hearth['scene']]).read_text())
                fixture=next(e for e in scene['entities'] if e['id']==hearth['entity'])
                assert fixture['position']==hearth['position_logical'],name+' retained hearth'
    assert {r['id'] for r in schedule['crossings']}=={'upper_bridge','main_bridge','mill_landing'}
    assert schedule['protected_southern_exit']==town['overworld_exit'],'southern exit'
    assert not town.get('landmark_layers'),'no town antlers/shadow'
    inn=next(r for r in records if r['id']=='inn')
    assert len(inn['floors'])==2 and inn['stairs']['reserved_on_both_floors']
    return True

def reference_diagrams():
    """Named physical planes, ground grid, and approved Caelan at native scale."""
    im=Image.new('RGB',(960,640),'#19252b');d=ImageDraw.Draw(im)
    font=ImageFont.truetype(str(ROOT/'assets/ui/fonts/DejaVuSans.ttf'),15)
    small=ImageFont.truetype(str(ROOT/'assets/ui/fonts/DejaVuSans.ttf'),13)
    def label(at,text,color='#e5e9df'):d.text(at,text,font=small,fill=color)
    d.text((24,16),'ELDENMERE: ORTHOGONAL CONSTRUCTION REFERENCE',font=font,fill='#f4d35c')
    label((24,40),'NOT A GAMEPLAY SCREENSHOT. Grid = 24 logical units; artwork shown at 2×.')
    for x in range(24,936,48):d.line((x,80,x,596),fill='#34424a')
    for y in range(80,597,48):d.line((24,y,936,y),fill='#34424a')
    # House: wall volume rises above footprint, with a modest orthogonal roof plane.
    d.rectangle((86,302,326,446),fill='#305548',outline='#77c3a8',width=2)
    d.polygon([(86,302),(326,302),(326,446),(86,446)],outline='#77c3a8')
    d.rectangle((86,214,326,358),fill='#aba894',outline='#10171c',width=2)
    d.rectangle((86,358,326,446),fill='#cfbf98',outline='#10171c',width=2)
    d.polygon([(72,206),(206,136),(340,206),(340,326),(72,326)],fill='#555f74',outline='#10171c')
    d.line((72,206,340,206),fill='#8792a5',width=2)
    for y in range(222,327,16):d.line((74,y,338,y),fill='#6e788d',width=1)
    d.rectangle((193,374,219,426),fill='#684c36',outline='#10171c',width=2)
    d.rectangle((181,426,231,446),fill='#a8977b',outline='#10171c')
    d.rectangle((86,302,326,446),outline='#77c3a8',width=2)
    label((44,106),'Vertical height rises above occupied ground.')
    label((46,464),'Green box: occupied walls, not roof alpha.','#77c3a8')
    label((46,488),'Roof/eave overhang does not enlarge collision.')
    label((46,512),'Door, sill, probe and dry approach stay distinct.')
    # Bridge: full horizontal surface, bank joints, coherent repeat boards and rails.
    d.rectangle((490,290,910,438),fill='#345e6b')
    d.rectangle((490,290,532,438),fill='#779070');d.rectangle((868,290,910,438),fill='#779070')
    d.rectangle((518,320,886,416),fill='#937048',outline='#10171c',width=2)
    for x in range(520,887,16):d.line((x,322,x,414),fill='#503b2d',width=1)
    for y in (320,416):
        d.rectangle((518,y-22,886,y-16),fill='#aa8254',outline='#10171c')
        for x in range(520,887,48):d.rectangle((x,y-26,x+6,y+3),fill='#6e5037',outline='#10171c')
    label((492,220),'Deck follows map X/Y axes, not a frontal platform.')
    label((492,244),'Repeated boards and posts keep their proportions.')
    label((492,464),'Both bank ends visibly join the dirt approach.')
    label((492,488),'Deck below actors; near rail covers lower body only.')
    caelan=Image.open(ROOT/'assets/characters/caelan/review_hd/idles/idle_front.png').convert('RGBA')
    im.paste(caelan,(254,446-caelan.height),caelan);im.paste(caelan,(690,384-caelan.height),caelan)
    label((238,552),'Caelan: approved native idle, same 2× world scale.')
    label((24,610),'No perspective convergence, distant horizon, or off-scene skyline substitution.')
    return {'docs/reviews/eldenmere_architecture_contracts/projection_reference.png':im}

def build_diagrams(check=False):
    from io import BytesIO
    stale=[]
    for path,im in reference_diagrams().items():
        b=BytesIO();im.save(b,format='PNG');target=ROOT/path
        if not target.exists() or target.read_bytes()!=b.getvalue():
            stale.append(path)
            if not check:target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b.getvalue())
    if check and stale:raise SystemExit('Stale construction diagrams: '+', '.join(stale))
    print('Construction diagrams '+('verified' if check else 'built'))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');a=p.parse_args()
    validate_schedule(json.loads(SCHEDULE.read_text()),json.loads((ROOT/'assets/maps/eldenmere/playable/map.json').read_text()))
    build_diagrams(a.check)
