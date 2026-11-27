"""Review complete source redraws at the existing fixed density and body anchor.

Only whole-image uniform sampling and translation occur here. Anatomical motion
belongs to the original ImageGen-authored masters. This helper writes candidate
exports to /tmp and does not select the production bank.
"""
from pathlib import Path
import importlib.util
import json
from PIL import Image

HERE=Path(__file__).resolve().parent
FOLDER=HERE.parent
OUTPUT=Path('/tmp/lucan_run_v3_candidates')

def main():
    spec=importlib.util.spec_from_file_location('lucan_source_landmarks',FOLDER/'run_v2/measure_landmarks.py')
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.HERE=HERE
    module.REFERENCE=FOLDER/'appearance_contact.png'
    measured=module.measure()
    original=json.loads((FOLDER/'source_art_48.json').read_text())
    targets=original['registration_reference']['target_landmarks']
    weights=original['registration_reference']['weights']
    records=[]
    OUTPUT.mkdir(exist_ok=True)
    for record in measured:
        i=record['frame'];scale=.63
        origin=[sum(weights[n]*(targets[n][axis]-record['landmarks'][n][axis]*scale)
                    for n in weights) for axis in (0,1)]
        origin[1]+=original['frames'][i]['authored_weight_offset_y']
        image=Image.open(FOLDER/record['source']).convert('RGBA')
        image.putalpha(image.getchannel('A').point(lambda a:0 if a<16 else a))
        image=image.convert('RGBa').resize((round(image.width*scale),round(image.height*scale)),
            Image.Resampling.LANCZOS).convert('RGBA')
        result=Image.new('RGBA',(768,1024))
        result.alpha_composite(image,tuple(round(v) for v in origin))
        result.save(OUTPUT/f'frame_{i:02}.png')
        records.append({**record,'scale':scale,'origin':origin})
    (HERE/'candidate_registration.json').write_text(json.dumps(records,indent=2)+'\n')
    print('Registered',len(records),'complete candidate drawings in',OUTPUT)

if __name__=='__main__':main()
