"""Reference-only atlas assembly and exact whole-figure ImageGen briefs."""
from pathlib import Path
import json,hashlib
from PIL import Image,ImageDraw
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[6]
schedule=json.loads((HERE/'authoring_schedule.json').read_text())
tasks=[]
for start in (24,28,32):
    indices=list(range(start,start+4))
    atlas=Image.new('RGB',(1024,1536),'#333333')
    for cell,index in enumerate(indices):
        im=Image.open(HERE/f'guide_frames/transition_{index:03d}_guide.png').convert('RGB')
        atlas.paste(im,((cell%2)*512,(cell//2)*768))
    guide=HERE/f'motion_references/camera_{start:03d}_{start+3:03d}.png';atlas.save(guide)
    angles=[round(schedule[i]['elevation'],2) for i in indices]
    prompt=f'''Draw a 2-column by 2-row atlas of FOUR COMPLETE naturally proportioned adult Lucan running figures. Reading order top-left, top-right, bottom-left, bottom-right is actual camera transition samples {indices}, gait phases {[i%48 for i in indices]}; camera elevations {angles} degrees. Each cell is a complete indivisible newly painted figure, never parts.

PRIMARY FIRST REFERENCE is the actual requested-phase 3D camera/pose guide. Match each cell's own two hip-knee-ankle chains, contact/recovery foot positions and camera projection. The guide is only primitive anatomical blocking: replace it with Lucan's detailed believable adult body and polished plate, do not paint a toy/cylinder human. The SECOND cropped material sheet gives appearance only; it must never override the primary guide's phase or limb position. Frame-to-frame motion must follow the guide continuously, no later recovery pose pulled early, no fixed feet while torso changes.

Lucan is a youthful dark-haired BARE-HEADED male, detailed swept brown hair, polished articulated silver steel with restrained gold edging, oxblood split tabard, pale chest emblem, brown leather gloves/boots. Preserve one consistent adult body: same head, shoulder, plate, torso and actual limb lengths across cells. All body/equipment foreshortening comes from the specified viewpoint; do not shrink a tucked pose or fit every silhouette to one height. Show progressively more crown/shoulder top and less frontal chest as the camera rises.

Exactly TWO arms, TWO connected legs and TWO boots: no extra toes beneath the belt. His anatomicalRIGHT sword arm is imageLEFT, anatomicallyLEFT shield arm imageRIGHT; both have own coherent shoulder-elbow-wrist chains. Right glove grips the sword hilt, left glove/forearm owns the oxblood/gold chevron kite shield. Shield remains carried upright, gradually narrowing as the camera elevates; never laid flat to show its emblem. Preserve adult anatomy and rigid plate while elbows/knees articulate naturally. Smooth sequential gait, near/far ownership correct. The whole pose must include hair, both boots, sword point and shield with generous transparent margins, no clipping, no grid/text/labels, no ground/background/floor/shadow, no diagram colors. Same cool moonlight with restrained warm rim, no palette changes.'''
    refs=[guide,HERE/'early_appearance_patches.png']
    tasks.append({'id':f'transition_{start:03d}_{start+3:03d}','output':f'transition_{start:03d}_{start+3:03d}.png','indices':indices,'grid':[2,2],'prompt':prompt,'references':[{'path':p.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in refs]})
(HERE/'transition_tasks_024_035.json').write_text(json.dumps(tasks,indent=2)+'\n')
print('Prepared3camera-specific complete figure briefs')
