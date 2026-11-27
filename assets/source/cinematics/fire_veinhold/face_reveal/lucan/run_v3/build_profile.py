"""Select the reviewed complete drawings and reproduce their body registration.

This exporter-side authoring helper never creates or deforms anatomy. It uses
constant whole-master density and measured body points; original ImageGen PNGs
and the previous revision remain unchanged.
"""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json
from PIL import Image

HERE = Path(__file__).resolve().parent
FOLDER = HERE.parent

def build():
    profile = deepcopy(json.loads((HERE/'baseline_source_art_48.json').read_text()))
    selected = json.loads((HERE/'selected_generation_records.json').read_text())
    measurements = {r['frame']:r for r in json.loads((HERE/'candidate_registration.json').read_text())}
    if set(map(int, selected)) != set(measurements):
        raise ValueError('Every selected complete drawing needs a measured registration.')
    for label, generation in selected.items():
        i = int(label)
        path = FOLDER/generation['source']
        if sha256(path.read_bytes()).hexdigest() != generation['source_sha256']:
            raise ValueError('Selected source changed after review: '+str(path))
        for source in generation['reference_inputs']:
            retained = FOLDER/source['retained_source']
            if sha256(retained.read_bytes()).hexdigest() != source['sha256']:
                raise ValueError('Retained ImageGen reference changed: '+str(retained))
        measured = measurements[i]
        with Image.open(path) as image:
            cell = [0,0,*image.size]
        old = profile['frames'][i]
        profile['frames'][i] = {
            'source':generation['source'], 'cell':cell,
            'scale':measured['scale'], 'origin':measured['origin'],
            'landmarks':measured['landmarks'],
            'landmark_match_scores':measured['landmark_match_scores'],
            'generation_id':generation['generation_id'],
            'authored_weight_offset_y':old['authored_weight_offset_y'],
            'notes':'Complete image-authored continuity repair or explicitly recorded whole-pose chronology selection. Actual body landmarks register the entire drawing at fixed density; no per-limb transform, source-bound fitting, pasted upper region or temporal pixel interpolation.'}
    sources = {FOLDER/r['source'] for r in profile['frames']}
    sources.update({HERE/'baseline_source_art_48.json', HERE/'selected_generation_records.json',
        HERE/'candidate_registration.json', HERE/'measured_landmarks.json',
        HERE/'register_candidates.py', HERE/'measure_reviewed_landmarks.py', Path(__file__).resolve(),
        FOLDER/'run_v2/measure_landmarks.py', FOLDER/'appearance_contact.png',
        HERE/'chronology.json'})
    for generation in selected.values():
        sources.add(FOLDER/generation['prompt_file'])
        sources.update(FOLDER/r['retained_source'] for r in generation['reference_inputs'])
    for name in ['README.md','reviewed_landmarks.json','motion_review.json']:
        if (HERE/name).is_file():
            sources.add(HERE/name)
    profile.update({
        'approval_state':'implemented_for_in_game_review',
        'construction':'48 complete painted drawings over800ms. Scoped v3 whole-image ImageGen repairs restore leg exchanges and the35 sword-arm transition; explicit complete-pose chronology places the former midpoint at39 and the existing later pose at41. No duplicated runtime pose, isolated-limb rig, pasted protected pixels or frame interpolation.',
        'registration':'Existing768x1024 canvas and384,960 anchor. Fixed0.63 uniform source density; measured eyes/neck/belt register whole drawings with the existing authored weight chart. Body/model redraws remove incompatible source proportion changes; no occupied-height or boot-based scaling.',
        'source_sha256':{p.relative_to(FOLDER).as_posix():sha256(p.read_bytes()).hexdigest() for p in sorted(sources)},
        'continuity_review':{'selected_source_records':'run_v3/selected_generation_records.json',
            'whole_pose_chronology':'run_v3/chronology.json',
            'actual_landmark_review':'run_v3/reviewed_landmarks.json',
            'foot_lock_limit':'Frontal detailed drawings are upright billboards with mostly cropped soles. Actual3D support-point ground locking at4m/s is not established by this source/shot review.'}})
    (FOLDER/'source_art_48.json').write_text(json.dumps(profile,indent=2)+'\n')
    print('Selected',len(selected),'reviewed complete sources in48-pose /800ms profile.')

if __name__ == '__main__':
    build()
