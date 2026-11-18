"""Export Crown worker's complete native authored drawings, not scaled legacy pixels."""
from pathlib import Path
import sys,json,hashlib,shutil
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1];SRC=ROOT/'assets/source/characters/named_hd/regent_survivor';OUT=ROOT/'assets/characters/named_hd/regent_survivor';REVIEW=ROOT/'docs/reviews/named_hd/regent_survivor'
sys.path.insert(0,str(SRC))
from author_body import draw,MOTION
def idle(dr):return draw(dr)
def walk(dr,i):return draw(dr,i)
DIRECTIONS=['front','right','back','left'];PHASE=['right_contact','right_down','left_passing','left_recovery','left_contact','left_down','right_passing','right_recovery']
def savej(path,data):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,indent=2)+'\n')


def build():
 data={'walk':{dr:[dict(k,b=[0,1,1,0,0,1,1,0][i]) for i,k in enumerate(MOTION[dr])] for dr in DIRECTIONS}};OUT.mkdir(parents=True,exist_ok=True);REVIEW.mkdir(parents=True,exist_ok=True)
 idleboard=Image.new('RGBA',(192,72),'#58615a')
 for di,dr in enumerate(DIRECTIONS):
  standing=idle(dr);standing.save(OUT/f'idle_{dr}.png');idleboard.alpha_composite(standing,(48*di,0))
  bank=OUT/f'walk_{dr}';bank.mkdir(exist_ok=True);r=REVIEW/dr;r.mkdir(parents=True,exist_ok=True)
  strip=Image.new('RGBA',(384,72));frames=[];records=[]
  for i,k in enumerate(data['walk'][dr]):
   im=walk(dr,i);im.save(bank/f'frame_{i+1:02}.png');strip.alpha_composite(im,(48*i,0));frames.append(im)
   records.append(dict(file=f'frame_{i+1:02}.png',rect=[48*i,0,48,72],duration_ms=[70,140,140,70,70,140,140,70][i],phase=PHASE[i],body_bob=k['b']))
  strip.save(bank/'spritesheet.png');strip.save(SRC/f'walk_{dr}_native_master.png')
  savej(bank/'animation.json',dict(version=1,character='regent_survivor',animation='walk.'+dr,frame_size=[48,72],logical_size=[24,36],frame_count=8,artwork_pixels_per_world_pixel=2,draw_anchor=[24,60],foot_anchor=[24,68],cycle_ms=840,loop=True,frames=records,artwork_status='native_candidate',runtime_integration=False))
  comp=Image.new('RGBA',(480,72),'#58615a');old=Image.open(SRC/f'reference/idle_{dr}.png').convert('RGBA').resize((48,72),Image.Resampling.NEAREST)
  comp.alpha_composite(old,(0,0));comp.alpha_composite(standing,(48,0));comp.alpha_composite(strip,(96,0));comp.save(r/'native_comparison.png');comp.resize((1920,288),Image.Resampling.NEAREST).save(r/'comparison_4x.png')
  numbered=Image.new('RGB',(1920,320),'#58615a');numbered.paste(comp.convert('RGB').resize((1920,288),Image.Resampling.NEAREST),(0,24));nd=ImageDraw.Draw(numbered)
  for j,label in enumerate(['legacy','new idle']+[str(i+1)+': '+phase for i,phase in enumerate(PHASE)]):nd.text((j*192+4,5),label,fill='white')
  numbered.save(r/'numbered.png')
  landmarks=[]
  for i,k in enumerate(data['walk'][dr]):
   frame=frames[i];crown=frame.getbbox()[1];neck=[24,30+k['b']];hem=[24,50+k['b']]
   assert frame.getpixel(tuple(neck))[3]
   landmarks.append(dict(frame=i+1,crown_y=crown,neck=neck,right_sole=k['rt'],left_sole=k['lt'],belt=[24,47+k['b']],belt_note='Belt central point may be concealed in profile by near sleeve; no visibility assertion.',coat_center=hem,occlusion='Coat covers hip/knee roots; profile far hand and boots overlap legitimately.'))
  savej(r/'landmarks.json',landmarks)
  for name,scale,ms in [('native.gif',1,70),('normal.gif',4,70),('slow.gif',4,140)]:
   ff=[]
   for im in frames:
    bg=Image.new('RGBA',(48,72),'#58615a');bg.alpha_composite(im);ff.append(bg.convert('RGB').resize((48*scale,72*scale),Image.Resampling.NEAREST))
   ff[0].save(r/name,save_all=True,append_images=ff[1:],duration=[v*(2 if ms==140 else 1) for v in [70,140,140,70,70,140,140,70]],loop=0,disposal=2)
  seam=Image.new('RGBA',(192,72),'#58615a')
  for j,i in enumerate([6,7,0,1]):seam.alpha_composite(frames[i],(j*48,0))
  seam.resize((768,288),Image.Resampling.NEAREST).save(r/'seam_7_8_1_2.png')
 idleboard.save(REVIEW/'idles_native.png');idleboard.resize((768,288),Image.Resampling.NEAREST).save(REVIEW/'idles_4x.png')
 shutil.copyfile(SRC/'reference/portrait.png',OUT/'portrait.png')
 refs={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (SRC/'reference').iterdir() if p.is_file()}
 savej(SRC/'provenance.json',dict(canonical_id='regent_survivor',references=refs,motion_guide='Approved shopkeeper_01 native leg/foot coordinates retained at native scale; own short shirt, trouser and hair. Arm contour studies reused explicitly from same-task Page, with bare forearm/short sleeve redrawing; survivor guarded left chain replaces, never overlays, the ordinary arm. No guide pixels copied.',construction='Four native directional head drawings and target body/arm/leg contours. No old limb pixels or scaled legacy art.',authored_inputs=['author_head.py','author_body.py','motion_contours.json','arm_contours.json'],portrait='Existing cinematic portrait retained byte-exact; original dialogue registry unchanged.'))
 savej(OUT/'design.json',dict(id='regent_survivor',display_name='Crown worker',density=2,artwork_pixels_per_world_pixel=2,logical_size=[24,36],frame_size=[48,72],draw_anchor=[12,30],foot_anchor=[12,34],frames={dr:f'idle_{dr}.png' for dr in DIRECTIONS},portrait='portrait.png',idles={dr:dict(file=f'assets/characters/named_hd/regent_survivor/idle_{dr}.png',artwork_pixels_per_world_pixel=2,logical_size=[24,36]) for dr in DIRECTIONS},design_notes='Gray swept hair, forehead dressing, bluegray short-sleeve shirt, brown trousers, guarded wrapped anatomical left forearm. Native66px occupied height; body remains injury guarded.',version=1,status='candidate_pending_independent_review',runtime_integration=False))
 print('Crown worker: four native idles,32 walk poses and retained portrait exported')
if __name__=='__main__':build()
