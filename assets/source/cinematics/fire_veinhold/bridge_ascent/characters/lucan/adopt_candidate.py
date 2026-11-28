"""Adopt a hash-bound complete-figure native candidate without re-sampling it."""
from pathlib import Path
from hashlib import sha256
import json,sys,copy,shutil
S=Path(__file__).resolve().parent;ROOT=S.parents[6]
OUT=ROOT/'assets/story/fire_veinhold_opening/shot08/characters/lucan'


def main():
    candidate=Path(sys.argv[1]).resolve();binding_raw=(candidate/'binding.json').read_bytes();binding=json.loads(binding_raw)
    profile=OUT/'actorperformance.json';original=profile.read_bytes()
    assert sha256(original).hexdigest()==binding['production_profile_sha256'],'Production changed since native gate'
    data=json.loads((candidate/'actorperformance.json').read_text())
    assert sha256((candidate/'actorperformance.json').read_bytes()).hexdigest()==binding['candidate_profile_sha256']
    records=json.loads((candidate/'candidate_registration.json').read_text())
    assert sha256((candidate/'candidate_registration.json').read_bytes()).hexdigest()==binding['registration_sha256']
    for record in records:
        source=ROOT/record['source'];assert sha256(source.read_bytes()).hexdigest()==record['source_sha256']
    # Retain exact prior recipes/profile, never rewrite generation masters.
    archive=S/'registration_history'/binding['production_profile_sha256'][:12];archive.mkdir(parents=True,exist_ok=True)
    for name,path in [('actorperformance.json',profile),('bank_registration.json',S/'bank_registration.json'),('special_registration.json',S/'special_registration.json')]:
        dest=archive/name
        if not dest.exists():dest.write_bytes(path.read_bytes())
    existing=json.loads(original);copied={}
    for index,row in enumerate(data['transition_frames']):
        if index<16:
            data['transition_frames'][index]=copy.deepcopy(existing['transition_frames'][index]);continue
        src=Path(row['file']).resolve();name=src.name;destination=OUT/name
        if src!=destination:
            expected=data['source_sha256'][row['file']];assert sha256(src.read_bytes()).hexdigest()==expected;shutil.copyfile(src,destination);copied[name]=expected
        row['file']=name
    for row in data['overhead_cycle']['frames']:
        src=Path(row['file']).resolve();name=src.name;destination=OUT/name
        if src!=destination:
            expected=data['source_sha256'][row['file']];assert sha256(src.read_bytes()).hexdigest()==expected;shutil.copyfile(src,destination);copied[name]=expected
        row['file']=name
    names={row['file'] for row in data['transition_frames']+data['overhead_cycle']['frames']}
    data['source_sha256']={name:sha256((OUT/name).resolve().read_bytes()).hexdigest() for name in sorted(names)}
    data['source_state']='whole_figure_image_authored'
    profile.write_text(json.dumps(data,indent=2)+'\n')
    (S/'bank_registration.json').write_text(json.dumps(records,indent=2)+'\n')
    selected={'version':1,'actor':'lucan','selection_scope':'Selected whole-figure source/native registration; final composed scene acceptance recorded separately in root review documents.',
        'native_binding_sha256':sha256(binding_raw).hexdigest(),'prepared_profile_sha256':sha256(profile.read_bytes()).hexdigest(),
        'transition_records':len(data['transition_frames']),'overhead_cycle_records':len(data['overhead_cycle']['frames']),
        'used_pngs':len(names),'two_tick_source_poses':{str(row['index']):row['source_pose_gait_frame'] for row in data['transition_frames'] if 'source_pose_gait_frame'in row},
        'whole_image_operations':['complete source cell crop','alpha floor at16','uniform whole-image sampling','whole-image translation']}
    (S/'selected_performance.json').write_text(json.dumps(selected,indent=2)+'\n')
    # Trial proof images do not belong in the runtime source input folder.
    stale=OUT/'native_review'
    if stale.exists():
        dest=Path('/tmp/lucan_archived_runtime_trial_native_review')
        if dest.exists():shutil.rmtree(dest)
        shutil.move(str(stale),str(dest))
    print(json.dumps(selected))
if __name__=='__main__':main()
