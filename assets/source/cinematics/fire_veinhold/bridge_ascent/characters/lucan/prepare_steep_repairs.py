from pathlib import Path
import json,hashlib
from PIL import Image
s=Path(__file__).resolve().parent;root=s.parents[6]
sel={0:'overhead_000_007b.png',8:'overhead_008_015.png',16:'overhead_016_023.png',24:'overhead_024_031.png',32:'overhead_032_039_alpha.png',40:'overhead_040_047.png'}
ts=json.loads((s/'transition_dense_tasks.json').read_text());results=[]
for t in ts:
 if t['indices'][0] not in(76,84,92,100):continue
 start=t['indices'][0];atlas=Image.new('RGBA',(2048,1536))
 for c,i in enumerate(t['indices']):
  phase=i%48;bank=phase//8*8;im=Image.open(s/sel[bank]).convert('RGBA');w,h=im.width//4,im.height//2;local=phase-bank;im=im.crop((local%4*w,local//4*h,(local%4+1)*w,(local//4+1)*h));im.thumbnail((490,740));atlas.alpha_composite(im,(c%4*512+(512-im.width)//2,c//4*768+(768-im.height)//2))
 p=s/f'motion_references/overhead_matched_{start:03d}_{start+7:03d}.png';atlas.save(p)
 t['id']+='b';t['output']=t['output'].replace('.png','b.png');refs=[root/t['references'][0]['path'],p,s/'overhead_appearance_patches_v4.png'];t['references']=[{'path':p.relative_to(root).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in refs]
 t['prompt']='Draw8 COMPLETE Lucan wholefigures in4columns2rows. FIRST actual3Dguide supplies exact phase/camera. SECOND supplies exact SAME phase wholefigures from90degree overhead: re-draw them at the FIRST guide actual slightly tilted overhead camera, preserving limb ownership and natural adult identity. THIRD is cropped top-surface materials ONLY. No frontal appearance references are supplied.\n\n'+t['prompt']+'\n\nCRITICAL WHOLEMODEL CAMERA CORRECTION: these are already NEAR VERTICAL overhead views. The dark head crown must appear AHEAD/BELOW the red hips in EVERY CELL, as in the primary3Dguide, never above a long frontal breastplate. Neck, face and breastplate front are naturally occluded by top of head and shoulder armor. See TOPS of head/shoulders and back/tabard behind/up image. Do NOT put a frontal runner with bowed head beneath an overhead label. At90 there would be no visible chin, eyes or breastplate front. Here only the small actual view difference in the primaryguide is allowed. Upright shield reveals only a thin curved gold rim/red back sliver, NOT full kite front. Folded passing knee is a kneecap with calf tucked under body, not long front shin. Two leg chains only. Preserve the exact corresponding8phase foot movements from first and second references, one60Hz tick each. Whole art transparent, no clipping.'
 results.append(t)
(s/'steep_repair_tasks.json').write_text(json.dumps(results,indent=2)+'\n')
