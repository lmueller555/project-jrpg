"""Rebuild the approved Caelan left-facing run and review exports. Requires Pillow."""
from pathlib import Path
import json, hashlib
from PIL import Image, ImageDraw, ImageFont
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'assets/characters/caelan/run_left'
SOURCE=ROOT/'assets/source/characters/caelan/run_left'
REVIEW=ROOT/'docs/reviews/caelan_left_run'
SOURCE.mkdir(parents=True,exist_ok=True)
REVIEW.mkdir(parents=True,exist_ok=True)
OUT.mkdir(parents=True,exist_ok=True)
BASE=ROOT/'assets/characters/caelan'
SIZE=(24,36)
O='#1a0e16'; SH='#573422'; LE='#8b5531'; LH='#b67644'; P='#645450'; C='#fbeed0'; GOLD='#d3963f'; TEAL='#1f5d72'; SK='#e8c49d'; SS='#e99f55'
def blank():return Image.new('RGBA',SIZE)
def cut(im,box):
 out=blank();out.paste(im.crop(box),box[:2]);return out
def move(im,dx,dy):
 out=blank();out.alpha_composite(im,(dx,dy));return out
def limb(d,a,b,w,c):
 d.line([a,b],fill=O,width=w+2);d.line([a,b],fill=c,width=w)
def leg(j,far=False):
 im=blank();d=ImageDraw.Draw(im);hip,knee,ankle,toe=j
 limb(d,hip,knee,3,P if not far else SH)
 limb(d,knee,ankle,2,LE if not far else SH)
 # Short boot follows the ankle-to-toe direction, preserving bent knees.
 limb(d,ankle,toe,2,LE if not far else SH)
 d.point(ankle,fill=LH if not far else LE)
 d.line([(toe[0]-1,toe[1]),(toe[0]+1,toe[1])],fill=O,width=1)
 return im
def arm(j,far=False):
 im=blank();d=ImageDraw.Draw(im);s,e,h=j
 limb(d,s,e,2,GOLD if far else C)
 limb(d,e,(h[0]+1,h[1]+1),2,SH)
 d.rectangle((h[0]-1,h[1],h[0],h[1]+1),fill=SS if far else SK)
 return im
idle=Image.open(BASE/'idle_left.png').convert('RGBA')
head=cut(idle,(0,0,24,14))
# Remove stationary arms while keeping the tabard stripe, collar and belt.
body=blank();d=ImageDraw.Draw(body)
d.polygon([(10,14),(13,14),(14,17),(14,24),(12,25),(9,25),(9,17)],fill=O)
d.polygon([(10,15),(12,15),(13,17),(13,23),(10,24)],fill=C)
d.line([(10,14),(10,24)],fill=TEAL,width=1)
d.line([(11,14),(13,15)],fill=GOLD,width=1)
d.line([(10,20),(13,20)],fill=SH,width=2)
d.point((11,20),fill=LH)
d.point((12,24),fill=GOLD)
# Contact hips are y26; flight hips y24. Head and shoulders share the same rise.
legs=[
 {'near':[(12,26),(9,29),(7,32),(5,33)],'far':[(12,26),(16,29),(18,25),(17,25)]},
 {'near':[(12,24),(15,27),(17,29),(16,31)],'far':[(12,24),(7,26),(10,28),(9,29)]},
 {'near':[(12,26),(16,29),(18,25),(17,25)],'far':[(12,26),(9,29),(7,32),(5,33)]},
 {'near':[(12,24),(7,26),(10,28),(9,29)],'far':[(12,24),(15,27),(17,29),(16,31)]},
]
arms=[
 {'near':[(11,17),(16,20),(17,17)],'far':[(10,17),(7,20),(5,17)]},
 {'near':[(11,15),(13,19),(10,18)],'far':[(10,15),(8,18),(6,16)]},
 {'near':[(11,17),(7,20),(5,17)],'far':[(10,17),(15,20),(16,17)]},
 {'near':[(11,15),(8,18),(6,16)],'far':[(10,15),(13,19),(11,18)]},
]
# Subtle wider swing: fixed shoulder, elbow +1px and hand +2px at
# contacts; intermediate poses open by 1px to preserve a smooth arc.
for phase, pair in enumerate(arms):
 for side, joints in pair.items():
  shoulder, elbow, hand = joints
  direction = -1 if elbow[0] < shoulder[0] else 1
  joints[1] = (elbow[0] + direction, elbow[1])
  joints[2] = (hand[0] + direction * (2 if phase % 2 == 0 else 1), hand[1])
frames=[];meta=[]
for i in range(4):
 dy=1 if i%2==0 else -1
 # A stepped one-pixel torso lean, with the head two pixels ahead of the idle.
 torso=blank()
 for y in range(14,26):
  dx=-1 if y<21 else 0
  for x in range(24):
   p=body.getpixel((x,y))
   if p[3]:torso.putpixel((x+dx,y+dy),p)
 layers={'far_arm':arm(arms[i]['far'],True),'far_leg':leg(legs[i]['far'],True),'near_leg':leg(legs[i]['near']), 'torso':torso,'near_arm':arm(arms[i]['near']),'head':move(head,-2,dy)}
 frame=blank()
 for name,layer in layers.items():
  (SOURCE/f'frame_{i+1:02}').mkdir(parents=True,exist_ok=True)
  layer.save(SOURCE/f'frame_{i+1:02}'/f'{name}.png');frame.alpha_composite(layer)
 frame.save(OUT/f'frame_{i+1:02}.png');frames.append(frame)
 meta.append({'file':f'frame_{i+1:02}.png','rect':[24*i,0,24,36],'duration_ms':100,'phase':['contact_near','flight_near','contact_far','flight_far'][i],'airborne':bool(i%2),'upper_body_offset':[-2,dy],'legs':legs[i],'arms':arms[i]})
sheet=Image.new('RGBA',(96,36))
for i,f in enumerate(frames):sheet.alpha_composite(f,(24*i,0))
sheet.save(OUT/'spritesheet.png')
(OUT/'animation.json').write_text(json.dumps({'character':'caelan','animation':'run.left','status':'approved','frame_size':[24,36],'foot_anchor':[12,34],'loop':True,'frames':meta,'source_idle_sha256':hashlib.sha256((BASE/'idle_left.png').read_bytes()).hexdigest()},indent=2)+'\n')
walk=[Image.open(BASE/'walk_left'/f'frame_{i+1:02}.png').convert('RGBA') for i in range(4)]
font_path='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
font=ImageFont.truetype(font_path,22);small=ImageFont.truetype(font_path,15)
BG=(232,237,242);INK=(39,51,62)
def panel(w,r,caption='Native pixel art · enlarged 8×'):
 im=Image.new('RGB',(720,470),BG);d=ImageDraw.Draw(im)
 d.text((28,18),'CAELAN / LEFT-FACING RUN STUDY',font=font,fill=INK)
 d.text((28,52),caption,font=small,fill=INK)
 for x,f,title,sub in [(90,w,'EXISTING WALK','4 × 140 ms'),(400,r,'APPROVED RUN','4 × 100 ms')]:
  d.text((x,90),title,font=small,fill=INK);d.text((x,115),sub,font=small,fill=INK)
  # Sprite art is 10x with a baseline below row 34.
  big=f.resize((192,288),Image.Resampling.NEAREST)
  im.paste(big,(x+22,145),big)
  d.line((x-12,435,x+245,435),fill=(164,179,185),width=1)
 d.text((28,450),'Approved run · original walk unchanged',font=small,fill=INK)
 return im
# Independent real-time clocks over the common 2800ms cycle.
normal=[panel(walk[(t//140)%4],frames[(t//100)%4]) for t in range(0,2800,20)]
normal[0].save(REVIEW/'walk-vs-run.gif',save_all=True,append_images=normal[1:],duration=20,loop=0,disposal=2,optimize=False)
slow=[panel(walk[i],frames[i],'Slow motion · synchronized pose inspection') for i in range(4)]
slow[0].save(REVIEW/'walk-vs-run-slow.gif',save_all=True,append_images=slow[1:],duration=350,loop=0,disposal=2,optimize=False)
board=Image.new('RGB',(1040,500),BG);d=ImageDraw.Draw(board)
d.text((24,14),'CAELAN / FOUR RUN POSES',font=font,fill=INK)
for i,f in enumerate(frames):
 x=25+i*255;b=f.resize((240,360),Image.Resampling.NEAREST);board.paste(b,(x,90),b)
 d.text((x,60),meta[i]['phase'].replace('_',' ').upper(),font=small,fill=INK)
 d.line((x,440,x+240,440),fill=(164,179,185))
d.text((24,475),'24×36 native frames · 100 ms per pose · approved',font=small,fill=INK)
board.save(REVIEW/'run-poses.png')
# Export original reference and standalone native looping sprite for reuse.

preview=[]
for f in frames:
 b=Image.new('RGBA',SIZE,(*BG,255));b.alpha_composite(f);preview.append(b.convert('RGB').resize((240,360),Image.Resampling.NEAREST))
preview[0].save(REVIEW/'run-loop.gif',save_all=True,append_images=preview[1:],duration=100,loop=0,disposal=2,optimize=False)
print(OUT)
