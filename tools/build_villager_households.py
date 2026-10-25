"""Assign existing villager appearances to families without cloning the gardener."""
from pathlib import Path
from build_eldenmere_stream import read_json,write_json
ROOT=Path(__file__).resolve().parents[1]
REGISTRY=ROOT/'assets/maps/eldenmere/households/households.json'
TOWN=ROOT/'assets/maps/eldenmere/playable/map.json'


def build():
    registry=read_json(REGISTRY);town=read_json(TOWN)
    for family in registry['households']:
        members=[family['mother'],family['father']];path=ROOT/town['interior_scenes'][family['home']]
        room=read_json(path);ids=[m['id'] for m in members]
        room['household']=ids;room['household_id']=family['id'];room['household_registry']=REGISTRY.relative_to(ROOT).as_posix()
        room['npcs']=[n for n in room.get('npcs',[]) if n['id'] not in ids]
        for role in ('mother','father'):
            member=family[role];partner=family['father' if role=='mother' else 'mother']['id']
            assignment={'home_scene':family['home'],'household_id':family['id'],'family_role':role,'partner_id':partner}
            if member.get('placement')=='existing_town_routine':
                actor=next(n for n in town['npcs'] if n['id']==member['id']);actor.update(assignment)
                continue
            room['npcs'].append({'id':member['id'],'name':member['label'],'kind':'stationary',
                'position':member['position'],'probe_size':[12,8],'draw_anchor':[12,30],
                'sprite':member['sprite_root']+f'/idle_{member["facing"]}.png',**assignment})
        write_json(path,room)
    town['household_registry']=REGISTRY.relative_to(ROOT).as_posix()
    write_json(TOWN,town)
    print('Assigned three parent pairs to home_a, home_b, home_c; placed five adults; existing gardener retained.')
    if isinstance(registry.get('children'),list):
        from build_village_children import build as build_children
        build_children()


if __name__=='__main__':build()
