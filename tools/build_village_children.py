"""Place five child characters and individual compact beds in their family homes."""
from pathlib import Path
from PIL import Image
from build_eldenmere_stream import read_json,write_json
ROOT=Path(__file__).resolve().parents[1]
REGISTRY=ROOT/'assets/maps/eldenmere/households/households.json'
TOWN=ROOT/'assets/maps/eldenmere/playable/map.json'


def box(r):
    x,y,w,h=r;return x,y,x+w,y+h


def build():
    registry=read_json(REGISTRY);town=read_json(TOWN)
    if not isinstance(registry.get('children'),list):return
    from build_schoolgirls import build as build_girls
    from build_schoolboys import build as build_boys
    from build_compact_child_beds import build as build_beds
    build_girls();build_boys();build_beds()
    beds=read_json(ROOT/'assets/terrain/eldenmere/child_beds/beds.json')
    for family in registry['households']:
        children=family.get('children',[]);path=ROOT/town['interior_scenes'][family['home']];room=read_json(path)
        ids=[c['id'] for c in children];parents=[family['mother']['id'],family['father']['id']]
        room['household']=parents+ids
        room['npcs']=[a for a in room['npcs'] if a['id'] not in ids]
        room['entities']=[e for e in room['entities'] if e.get('owner_child') not in ids]
        for identifier in ids:room['destinations'].pop(identifier+'_bed',None)
        base=read_json(ROOT/room['source_room']);mask=Image.new('L',tuple(room['size_pixels']),255)
        mask.paste(0,box(base['floor_rect']))
        if base.get('partition_rect'):mask.paste(255,box(base['partition_rect']))
        for o in base['objects']:
            if o.get('floor_rect'):mask.paste(255,box(o['floor_rect']))
        for child in children:
            c=read_json(ROOT/child['sprite_root']/'character.json')
            assert c['age_years']==child['age_years']
            room['npcs'].append({'id':child['id'],'name':child['name'],'kind':'stationary',
                'position':child['position'],'probe_size':[10,6],'draw_anchor':[12,30],
                'sprite':child['sprite_root']+'/idle_front.png','sprite_root':child['sprite_root'],
                'age_years':child['age_years'],'parents':parents,'family_role':'child',
                'home_scene':family['home'],'household_id':family['id']})
            bed=child['bed'];x,y=bed['position'];fx,fy,fw,fh=beds['floor_rect']
            rect=[x+fx,y+fy,fw,fh];identifier=child['id']+'_bed'
            room['entities'].append({'id':identifier,'owner_child':child['id'],'position':[x,y],
                'sort_y':rect[1]+rect[3],'sort_priority':0,'frames':[beds['variants'][bed['variant']]['image']],
                'frame_duration_ms':300,'phase_offset':0,'floor_rect':rect,'bed_variant':bed['variant']})
            mask.paste(255,box(rect));room['destinations'][identifier]=bed['access']
        target=path.parent/'collision.png';mask.save(target);room['collision']=target.relative_to(ROOT).as_posix()
        write_json(path,room)
    print('Placed Tessa, Finn, Rowan, Ada and Pippa with five compact twin beds in their own homes.')


if __name__=='__main__':build()
