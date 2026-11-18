"""Target worker native body. Explicit whole sleeve/arm contours and own shirt.
Shared articulated contour studies disclosed; no source pixels, rig or warp.
"""
from PIL import Image,ImageDraw
from pathlib import Path
import json
from author_head import draw as head
ACTOR='regent_survivor'
O='#1a0e16';S='#e8c49d';SS='#c98c64';SL='#f5d9b0'
MOTION=json.loads((Path(__file__).parent/'motion_contours.json').read_text())
ARMS=json.loads((Path(__file__).parent/'arm_contours.json').read_text())
def pts(s):return [tuple(map(int,p.split(','))) for p in s.split()]
def draw(direction,index=None):
 survivor=ACTOR=='regent_survivor';side=direction in ['left','right'];i=0 if index is None else index;b=0 if index is None else [0,1,1,0,0,1,1,0][i]
 CD,C,CL=('#394955','#596e7d','#8197a5') if survivor else ('#344c37','#547953','#80986b')
 PD,P,PL=('#594334','#7e6049','#a58565') if survivor else ('#5b4130','#896348','#b48c5c')
 im=Image.new('RGBA',(48,72));d=ImageDraw.Draw(im)
 def p(v,c):d.polygon(v,fill=c,outline=O)
 def l(v,c,w=1):d.line(v,fill=c,width=w)
 def r(v,c):d.rectangle(v,fill=c)
 q=MOTION[direction][i]
 if index is None:
  q={'L':[(25,44),(32,44),(32,58),(31,64),(25,64)],'R':[(16,44),(23,44),(23,57),(22,64),(16,64)],'lb':[(25,59),(31,59),(31,65),(34,67),(33,69),(24,69),(24,66)],'rb':[(16,59),(22,59),(22,65),(24,67),(23,69),(14,69),(14,66)]}
 for leg,boot,col in [('L','lb',PD),('R','rb',P)]:
  p(q[leg],col);l(q[leg][1:4],PL);p(q[boot],'#3d2118');l(q[boot][1:4],'#775238')
 # Shifted left phase is needed because left foot guides exchange identity.
 a=ARMS['side'][(i+4)%8 if direction=='left' else i] if side else ARMS['depth'][i]
 if index is None:
  a=['14,29 18,30 17,37 15,43 14,48 9,48 8,45 10,36','31,29 35,30 38,36 39,45 37,49 33,48 31,42 30,36','9,48 14,48 15,51 13,53 10,52 8,50','33,48 37,49 38,52 35,54 32,52 32,50'] if not side else ['21,29 26,29 28,35 27,42 28,48 24,50 21,47 21,40 19,34','24,50 28,48 30,51 28,54 25,53 23,52','29,30 33,32 33,40 34,47 30,49 28,45 27,38','30,49 34,47 36,50 34,53 31,52 29,51']
 def parsed(v):
  q=pts(v);return [(47-x,y) for x,y in q] if direction=='left' else q
 if side and not (survivor and direction=='right'):p(parsed(a[2]),SS);p(parsed(a[3]),SS)
 if side:
  torso=[(18,28+b),(24,27+b),(30,29+b),(32,35+b),(30,42+b),(32,47+b),(18,48+b),(16,44+b),(18,38+b)]
  if direction=='left':torso=[(47-x,y) for x,y in torso]
  p(torso,C)
  l(parsed(f'20,{31+b} 21,{38+b} 20,{45+b}'),CL,2);l(parsed(f'29,{32+b} 28,{41+b}'),CD,2)
  l(parsed(f'18,{46+b} 31,{46+b}'),'#4b3626',2)
  sleeve,hand=parsed(a[0]),parsed(a[1])
  if not (survivor and direction=='left'):p(sleeve,S);l(sleeve[1:4],SS);p(hand,S)
  cuff=parsed(f'20,{29+b} 26,{29+b} 28,{35+b} 26,{39+b} 21,{38+b} 19,{34+b}')
  p(cuff,C);l(cuff[1:4],CL)
 else:
  p([(16,28+b),(21,27+b),(28,27+b),(33,29+b),(34,38+b),(31,43+b),(33,47+b),(15,48+b),(14,44+b),(16,38+b)],C)
  l([(19,32+b),(19,40+b),(17,45+b)],CL,2);l([(29,33+b),(30,41+b),(28,45+b)],CD,2)
  if direction=='front':p([(20,27+b),(24,30+b),(28,27+b),(28,31+b),(24,34+b),(20,31+b)],CD)
  else:l([(20,29+b),(24,30+b),(29,29+b)],CL)
  r((15,46+b,32,48+b),'#4b3626');r((23,46+b,26,48+b),'#b99c58')
  for n,(sleeve,hand) in enumerate([(a[0],a[2]),(a[1],a[3])]):
   if survivor and n==(1 if direction=='front' else 0):continue
   p(pts(sleeve),S);l(pts(sleeve)[1:4],SS);p(pts(hand),S)
  p([(14,29+b),(18,30+b),(18,35+b),(16,39+b),(10,38+b),(10,35+b)],C);l([(14,31+b),(16,34+b)],CL)
  p([(31,29+b),(35,30+b),(38,35+b),(37,39+b),(31,38+b),(30,34+b)],CD);l([(33,31+b),(35,35+b)],C)
 if survivor:
  # New wrapped anatomical left forearm; guarded bent hand rests across ribs.
  if direction=='front':
   p([(32,38+b),(37,39+b),(36,44+b),(28,47+b),(23,46+b),(23,42+b),(30,42+b)],S)
   p([(31,39+b),(36,40+b),(35,44+b),(30,45+b),(29,42+b)],'#a79878');l([(31,40+b),(35,41+b)],'#eee4c7');l([(30,42+b),(34,43+b)],'#d8cdb0')
  elif direction=='back':
   p([(10,39+b),(15,39+b),(16,44+b),(12,47+b),(9,45+b)],'#a79878');l([(10,41+b),(15,41+b)],'#d8cdb0',2)
  elif direction=='left':
   p([(23,38+b),(27,40+b),(24,45+b),(17,45+b),(15,42+b),(19,40+b)],S);p([(21,39+b),(26,41+b),(23,44+b),(19,43+b)],'#a79878');l([(21,40+b),(24,41+b)],'#eee4c7')
  else:l([(18,39+b),(19,43+b)],'#a79878',2)
  for x,y in [(19,37),(29,41),(17,44),(25,50),(30,54)]:
   if im.getpixel((x,y+b))[3]:r((x,y+b,x+1,y+b),'#a68d6d')
 im.alpha_composite(head(direction,b));return im
