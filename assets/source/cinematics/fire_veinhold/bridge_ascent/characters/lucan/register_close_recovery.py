"""Complete-image registration of bounded close recovery/carry redraws.

The physically calibrated cranium center follows the approved adult source35.
Only whole-cell alpha floor, uniform sampling and translation affect final art.
"""
from pathlib import Path
from hashlib import sha256
import json,math
S=Path(__file__).resolve().parent;ROOT=S.parents[6]


def head_target(index):
    from cinematic_bridge_ascent import actor_states_at,project_world
    state=actor_states_at(index/60);actor=state['runners'][0]
    recoil=-.012*math.cos(4*math.pi*index/48)
    crest=-.012*math.cos(4*math.pi*35/48)
    z=1.7369+(recoil-crest)*.5
    point=[actor['world_position_metres'][0],actor['world_position_metres'][1]+.16,z]
    screen=project_world(point,state['camera']);ground=actor['ground_anchor'];factor=actor['scale']
    return [512+(screen[0]-ground[0])/factor,960+(screen[1]-ground[1])/factor]


def export_rows(observations,output):
    from register_banks import export
    records=[]
    for row in observations:
        index=row['index'];source=S/'close_recovery_v2'/row['source'];scale=row['uniform_scale'];center=row['cranium_center'];target=head_target(index)
        record={'kind':'transition','index':index,'gait_frame':index%48,
                'source':source.relative_to(ROOT).as_posix(),'source_sha256':sha256(source.read_bytes()).hexdigest(),
                'cell':row['cell'],'scale':scale,'origin':[target[a]-center[a]*scale for a in(0,1)],'alpha_floor':16,
                'observed_whole_cranium_centre':center,'guide_head_centre':target,
                'rigid_registration':{'observed_main_cranium_width':row['cranium_width'],
                                      'observed_main_pauldron_pair_span':row['main_cap_pair_span'],
                                      'uncertainty_source_pixels':{'cranium_edges':5,'center':5,'main_caps':8}},
                'method':'Uniform complete-figure scale from observed rigid cranium/pauldron widths, one density per master; actual cranium center registers to the calibrated adult source35 model projected through the shot camera. No eye-template size or occupied-height fitting.'}
        
        if 'source_pose_index' in row:record.update(source_pose_index=row['source_pose_index'],source_pose_gait_frame=row['source_pose_index']%48,exposure='Adjacent complete drawn recovery pose held for two 60Hz samples; actual camera/body registration retained.')
        path=output/f'transition_{index:03d}.png';export(record).save(path);record['output_sha256']=sha256(path.read_bytes()).hexdigest();records.append(record)
    return records


def apply():
    from register_banks import OUT
    observations=json.loads((S/'close_recovery_v2/rigid_observations.json').read_text())
    rows=[dict(row,source=master['source'],uniform_scale=master['uniform_scale']) for master in observations['masters'] for row in master['rows']]
    records=export_rows(rows,OUT)
    (S/'close_recovery_registration.json').write_text(json.dumps(records,indent=2)+'\n')
    return records
