"""Write fixed-density whole-drawing registration from audited source landmarks.

This authoring helper does not change pixels, build anatomy, or move limbs.
Run measure_landmarks.py first after a source redraw; then this script.
"""
from hashlib import sha256
from pathlib import Path
import json
import math
from PIL import Image

HERE=Path(__file__).resolve().parent
FOLDER=HERE.parent

def build():
    measured=json.loads((HERE/'measured_landmarks.json').read_text())
    if [r['frame'] for r in measured] != list(range(48)):
        raise ValueError('Audit all 48 complete source drawings before registration.')
    scale=.63
    targets={'eyes':[384.,135.66], 'neck':[386.64,205.62], 'belt':[385.98,401.64]}
    weights={'eyes':.5,'neck':.2,'belt':.3}
    # Single authored weight chart after registration; no runtime added bob.
    keys=[0.,3.,-4.,-2.,0.,3.,-4.,-2.]
    def recoil(frame):
        i=frame//6;t=frame/6-i
        a,b,c,d=[keys[k%8] for k in (i-1,i,i+1,i+2)]
        return .5*(2*b+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t)
    generations={}
    for name in ['generated_keys.json','first_results.json','second_results.json',
                 'generated_helper_results.json','repair_results.json',
                 'final_fix_results.json','final4_result.json','helper_leg_repairs.json']:
        path=HERE/name
        if path.is_file():
            for record in json.loads(path.read_text()):
                path_value=record.get('path',record.get('originalpath',record.get('original_path','')))
                generations[record['frame']]=record.get('generation_id') or Path(path_value).stem
    generations[36]='exec-c881dcd3-9dfb-467a-a875-15dfebd9fafc'
    frames=[]
    for record in measured:
        frame=record['frame'];image=Image.open(FOLDER/record['source'])
        landmarks=dict(record['landmarks'])
        landmarks.update({'right_sole':None,'left_sole':None})
        if frame==0:landmarks['right_sole']=[470.,1460.]
        if frame==24:landmarks['left_sole']=[600.,1450.]
        origin=[sum(weights[n]*(targets[n][axis]-landmarks[n][axis]*scale)
                    for n in weights) for axis in (0,1)]
        offset=round(recoil(frame),4);origin[1]+=offset
        frames.append({'source':record['source'],'cell':[0,0,*image.size],
            'scale':scale,'origin':[round(v,4) for v in origin],
            'landmarks':landmarks,'landmark_match_scores':record['landmark_match_scores'],
            'generation_id':generations.get(frame,'see final source/prompt record'),
            'authored_weight_offset_y':offset,
            'notes':'One complete image-authored painted pose. Right sword elbow pumps hip/waist/sternum; left shield smaller counterbalance. Constant whole-source density and measured multi-landmark registration. Guide diagrams never render; no isolated limb transform, warped idle or crossfade.'})
    files=[*sorted((HERE/'frames').glob('frame_*.png')),
           *sorted((HERE/'frames').glob('frame_*_prompt.txt')),
           *sorted((HERE/'guides').glob('phase_*.png')),
           HERE/'guide_recipe.py',HERE/'measure_landmarks.py',HERE/'measured_landmarks.json',
           HERE/'build_profile.py',HERE/'keys.png',
           *sorted(HERE.glob('*results.json')),HERE/'generated_keys.json',
           HERE/'final4_result.json',HERE/'helper_leg_repairs.json']
    profile={'version':1,'actor':'lucan','canvas':[768,1024],
        'anchor':[384,960],'cycle_ms':800,'alpha_floor':16,'facing':'front',
        'near':'anatomical_right','far':'anatomical_left',
        'contacts':[{'frame':0,'foot':'near'},{'frame':24,'foot':'far'}],
        'approval_state':'implemented_for_ingame_review',
        'construction':'48 individually ImageGen-authored complete painted drawings. Low-resolution key sheet and joint charts are authoring guides only. Final keys and inbetweens retain full source detail; no rig, detached anatomy, pasted face or image interpolation.',
        'registration':'Fixed0.63 source-art density for every master, regardless of canvas or occupied bounds. Eyes/neck/belt template matches register each complete drawing; one authored weight chart controls support/flight recoil. Production exporter only uniformly samples and translates whole figures.',
        'registration_reference':{'source':'appearance_contact.png','target_landmarks':targets,
            'weights':weights,'fixed_source_density':scale,
            'authored_recoil_y':[round(recoil(f),4) for f in range(48)]},
        'source_sha256':{p.relative_to(FOLDER).as_posix():sha256(p.read_bytes()).hexdigest() for p in files},
        'frames':frames}
    path=FOLDER/'source_art_48.json';path.write_text(json.dumps(profile,indent=2)+'\n')
    print('Wrote',path,'48 complete authored poses / 800ms, fixed density',scale)

if __name__=='__main__':build()
