"""Assemble pose-specific camera-guide references; generated figures remain indivisible art."""
from pathlib import Path
import json,hashlib
from PIL import Image,ImageDraw
S=Path(__file__).resolve().parent;ROOT=S.parents[6]
SCHEDULE=json.loads((S/'authoring_schedule.json').read_text())
def task(kind,start,count=8):
    indices=list(range(start,min(start+count,133 if kind=='transition' else 48)))
    cols,rows=(4,2) if len(indices)>4 else(2,2)
    atlas=Image.new('RGB',(cols*512,rows*768),'#333333')
    states=[]
    for cell,index in enumerate(indices):
        path=S/f'guide_frames/{kind}_{index:03d}_guide.png';im=Image.open(path).convert('RGB');atlas.paste(im,((cell%cols)*512,(cell//cols)*768))
        phase=index%48;half=phase%24
        desc='compact folded passing knee; calf/boot folded back under body, NO long shin below knee' if 10<=half<=18 else ('next boot extends progressively toward landing' if half>18 else 'planted leg moves continuously back while opposite leg recovers')
        label=f'{cell+1}: frame{index}, phase{phase}: {desc}';states.append(label)
        d=ImageDraw.Draw(atlas);d.text(((cell%cols)*512+10,(cell//cols)*768+15),f'{cell+1} /phase{phase}',fill='yellow')
    guide=S/f'motion_references/{kind}_{start:03d}_{indices[-1]:03d}_camera.png';atlas.save(guide)
    elevations=[round(SCHEDULE[i]['elevation'],1) if kind=='transition' else 90 for i in indices]
    prompt=f'''Paint {len(indices)} COMPLETE indivisible Lucan running figures as a{cols}column{rows}row atlas. Read strictly LEFT TO RIGHT then TOP TO BOTTOM, camera samples {indices}, gait phases {[i%48 for i in indices]}, camera elevations {elevations} degrees. The FIRST attached image is the EXACT actual3D camera-and-pose guide for each cell; preserve its projected wholebody, each foot and knee ownership, changing arm positions and projected overlaps. Same natural adult body in every cell, not a toy or guide cylinders. SECOND image contains cropped identity/material samples ONLY.

Each image is only ONE60Hz step after the last. Never jump a limb to a later gait pose. Critical per-cell action:\n'''+ '\n'.join(states)+'''

When the guide shows a compact silver forward knee with its calf folded behind, do NOT invent a long shin and brown boot below that knee. The folded boot may be hidden by torso/hair. Do not make every frame a split-stride contact. Maintain exactly TWO complete shoulder-elbow-wrist chains, TWO hip-knee-ankle chains and at mostTWO boots; occlusion can hide a boot but cannot invent a third toe. AnatomicalRIGHT is imageLEFT, sword in RIGHT glove; LEFT arm imageRIGHT carries same oxblood/gold chevron kite shield. Shield hangs upright at all angles, its visible face narrows continuously with camera elevation into a thin curved gold rim/red back sliver at90; do not lay it flat. The head is bare swept darkbrown hair; no helmet. At steepview show crown and pauldron TOPS; head projects ahead/DOWN of hips, obscuring frontal chest/face. No face looking upward, no frontal face on an overhead model. The torso stands/runs upright, not lying prone.

Polished articulated SILVERSTEEL with restrained GOLD trim, oxblood split tabard, pale chest motif where camera permits, brown gloves/boots, youthful mature adult proportions. Match actual hair/head and rigid shoulder/plate size consistently across all cells; NEVER resize body to equal silhouette height. Natural foreshortening and compact recovery poses shorten the occupied box. Cool moonlit silver with restrained warm rim, no lighting/palette flash. Paint each completefigure freshly, not pasted bodyparts. Transparent background, no floor/shadow/borders/grid/text/guide colors. Entire hair, both boots, swordtip and shield inside generous clear cell margins.'''
    refs=[guide,S/'overhead_appearance_patches_v2.png']
    return {'id':f'{kind}_{start:03d}_{indices[-1]:03d}','output':f'{kind}_{start:03d}_{indices[-1]:03d}.png','kind':kind,'indices':indices,'grid':[cols,rows],'prompt':prompt,'references':[{'path':p.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in refs]}
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--kind',default='transition');p.add_argument('--starts',default='36,44');args=p.parse_args()
 ts=[task(args.kind,int(v)) for v in args.starts.split(',')]
 (S/f'{args.kind}_dense_tasks.json').write_text(json.dumps(ts,indent=2)+'\n');print(len(ts))
