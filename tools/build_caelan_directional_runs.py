"""Rebuild the approved front, right and back runs. Preserves approved left art."""
from pathlib import Path
import json
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'docs/reviews/caelan_directional_runs';OUT.mkdir(parents=True,exist_ok=True)
SOURCE=ROOT/'assets/source/characters/caelan'
BASE=ROOT/'assets/characters/caelan'
O='#1a0e16'; SH='#573422'; LE='#8b5531'; LH='#b67644'; P='#645450'; C='#fbeed0'; GOLD='#d3963f'; TEAL='#1f5d72'; SK='#e8c49d'; SS='#e99f55'
def blank():return Image.new('RGBA',(24,36))
def cut(im,box):
 out=blank();out.paste(im.crop(box),box[:2]);return out
def move(im,dx,dy):
 out=blank();out.alpha_composite(im,(dx,dy));return out
def limb(d,a,b,w,c):
 d.line([a,b],fill=O,width=w+2);d.line([a,b],fill=c,width=w)
def arm(j,far=False):
 im=blank();d=ImageDraw.Draw(im);s,e,h=j
 limb(d,s,e,2,GOLD if far else C);limb(d,e,(h[0]+1,h[1]+1),2,SH)
 d.rectangle((h[0]-1,h[1],h[0],h[1]+1),fill=SS if far else SK)
 return im
def leg(j,far=False,back=False):
 im=blank();d=ImageDraw.Draw(im);hip,knee,ankle,toe=j
 limb(d,hip,knee,3,SH if far else P);limb(d,knee,ankle,2,SH if far else LE)
 limb(d,ankle,toe,2,SH if far else LE);d.point(ankle,fill=LE if far else LH)
 d.line([(toe[0]-1,toe[1]),(toe[0]+1,toe[1])],fill=O)
 if back and toe[1]<32:d.line([(toe[0]-1,toe[1]),(toe[0]+1,toe[1])],fill=SH)
 return im

def body(idle,direction):
 if direction=='right':
  b=blank();d=ImageDraw.Draw(b)
  d.polygon([(10,14),(13,14),(14,17),(14,25),(10,25),(9,22),(9,17)],fill=O)
  d.polygon([(10,15),(12,15),(13,17),(13,24),(10,24)],fill=C)
  for y in range(14,25):
   for x in range(11,15):
    p=idle.getpixel((x,y))
    if p[3] and p[:3] not in [(232,196,157),(233,159,85)]:b.putpixel((x,y),p)
  d.line([(10,20),(13,20)],fill=SH,width=2)
  return b
 b=cut(idle,(8,14,16,27));d=ImageDraw.Draw(b)
 # Replace the edges of the stationary hands with tabard/outline.
 for y in range(15,26):
  for x in range(8,16):
   p=b.getpixel((x,y))
   if p[:3] in [(232,196,157),(233,159,85)]:
    b.putpixel((x,y),Image.new('RGBA',(1,1),TEAL if direction=='back' else C).getpixel((0,0)))
 # Keep the small leather hip pouch on anatomical left.
 pouch=cut(idle,(14,19,16,24) if direction=='front' else (6,19,9,24))
 b.alpha_composite(pouch)
 return b
left_meta=json.loads((BASE/'run_left/animation.json').read_text())
allframes={'left':[Image.open(BASE/'run_left'/f'frame_{i+1:02}.png').convert('RGBA') for i in range(4)]}
for direction in ['right','front','back']:
 pack=BASE/f'run_{direction}';pack.mkdir(parents=True,exist_ok=True);idle=Image.open(BASE/f'idle_{direction}.png').convert('RGBA')
 head=cut(idle,(0,0,24,14));torso=body(idle,direction);records=[];frames=[];source_sheets={}
 for i in range(4):
  dy=1 if i%2==0 else -1;layers={}
  if direction=='right':
   # Mirror joint geometry and approved limb pixels, never the character's face.
   for name in ['far_arm','far_leg','near_leg']:
    layers[name]=Image.open(ROOT/'assets/source/characters/caelan/run_left'/f'frame_{i+1:02}'/(name+'.png')).convert('RGBA').transpose(Image.Transpose.FLIP_LEFT_RIGHT)
   leaned=blank()
   for y in range(14,26):
    for x in range(24):
     p=torso.getpixel((x,y))
     if p[3]:leaned.putpixel((x+(1 if y<21 else 0),y+dy),p)
   layers['torso']=leaned
   layers['near_arm']=Image.open(ROOT/'assets/source/characters/caelan/run_left'/f'frame_{i+1:02}'/'near_arm.png').convert('RGBA').transpose(Image.Transpose.FLIP_LEFT_RIGHT)
   layers['head']=move(head,2,dy)
   joints={g:{side:[[23-x,y] for x,y in j] for side,j in left_meta['frames'][i][g].items()} for g in ['arms','legs']}
  else:
   # Frame pairs alternate left/right contact. Bent arms move in depth.
   phase=i%2
   joints_leg=({'left':[(10,26),(9,30),(8,32),(8,34)],'right':[(14,26),(15,28),(15,26),(14,27)]} if not phase else
               {'left':[(10,24),(9,26),(10,29),(10,30)],'right':[(14,24),(15,27),(15,30),(15,31)]})
   joints_arm=({'left':[(7,17),(5,21),(6,23)],'right':[(16,17),(19,20),(15,17)]} if not phase else
               {'left':[(7,15),(5,18),(8,19)],'right':[(16,15),(18,18),(15,16)]})
   if i>=2:
    joints_leg={side:[(24-x,y) for x,y in joints_leg['right' if side=='left' else 'left']] for side in ['left','right']}
    joints_arm={side:[(23-x,y) for x,y in joints_arm['right' if side=='left' else 'left']] for side in ['left','right']}
   forward='right' if i<2 else 'left'
   rear='left' if forward=='right' else 'right'
   # In the back view, arms swinging toward the travel direction pass behind the torso.
   behind=forward if direction=='back' else rear;before=rear if direction=='back' else forward
   layers['rear_arm']=arm(joints_arm[behind],True)
   for side in ['right','left']:
    layers[side+'_leg']=leg(joints_leg[side],side==('right' if i<2 else 'left'),direction=='back')
   layers['torso']=move(torso,0,dy)
   layers['forward_arm']=arm(joints_arm[before],False)
   layers['head']=move(head,0,dy)
   joints={'legs':joints_leg,'arms':joints_arm}
  im=blank()
  for name,layer in layers.items():
   source_sheets.setdefault(name,Image.new('RGBA',(96,36))).alpha_composite(layer,(24*i,0));im.alpha_composite(layer)
  im.save(pack/f'frame_{i+1:02}.png');frames.append(im)
  records.append({'file':f'frame_{i+1:02}.png','rect':[24*i,0,24,36],'duration_ms':100,'airborne':bool(i%2),'phase':['contact_a','flight_a','contact_b','flight_b'][i],'layer_order':list(layers),'joints':joints})
 sheet=Image.new('RGBA',(96,36))
 for i,im in enumerate(frames):sheet.alpha_composite(im,(24*i,0))
 source=SOURCE/f'run_{direction}';source.mkdir(parents=True,exist_ok=True)
 for name,sheet_layer in source_sheets.items():sheet_layer.save(source/(name+'.png'))
 sheet.save(pack/'spritesheet.png');(pack/'animation.json').write_text(json.dumps({'character':'caelan','animation':'run.'+direction,'status':'approved','frame_size':[24,36],'foot_anchor':[12,34],'loop':True,'image':'spritesheet.png','frames':records},indent=2)+'\n');allframes[direction]=frames
# Approval hashes are preserved separately and never refreshed by the builder.
# Review sheets retain native pixels and a shared foot baseline.
BG=(232,237,242);INK=(39,51,62);FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
font=ImageFont.truetype(FONT,21);small=ImageFont.truetype(FONT,15)
def board(t,slow=False):
 b=Image.new('RGB',(1040,470),BG);d=ImageDraw.Draw(b)
 d.text((24,12),'CAELAN / FOUR DIRECTION RUN REVIEW',font=font,fill=INK)
 d.text((24,44),'100 ms per pose · 24×36 native frames' if not slow else 'Slow motion · same native poses held for 350 ms',font=small,fill=INK)
 for j,direction in enumerate(['front','left','right','back']):
  x=24+j*255;d.text((x,76),direction.upper()+(' / APPROVED' if direction=='left' else ' / APPROVED'),font=small,fill=INK)
  im=allframes[direction][t].resize((216,324),Image.Resampling.NEAREST);b.paste(im,(x,105),im)
  d.line((x,420,x+216,420),fill=(167,180,187))
 d.text((24,448),'Left run retained exactly · all four directions approved',font=small,fill=INK)
 return b
for name,ms in [('all-directions.gif',100),('all-directions-slow.gif',350)]:
 ims=[board(i,ms==350) for i in range(4)];ims[0].save(OUT/name,save_all=True,append_images=ims[1:],duration=ms,loop=0,disposal=2,optimize=False)
for direction in ['front','right','back']:
 b=Image.new('RGB',(1040,470),BG);d=ImageDraw.Draw(b);d.text((24,12),'CAELAN / '+direction.upper()+' RUN POSES',font=font,fill=INK)
 for i,im in enumerate(allframes[direction]):
  x=24+255*i;d.text((x,65),['CONTACT A','FLIGHT A','CONTACT B','FLIGHT B'][i],font=small,fill=INK)
  big=im.resize((216,324),Image.Resampling.NEAREST);b.paste(big,(x,100),big);d.line((x,415,x+216,415),fill=(167,180,187))
 b.save(OUT/(direction+'-poses.png'))
print(OUT)
