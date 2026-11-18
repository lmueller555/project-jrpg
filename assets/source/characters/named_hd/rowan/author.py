"""Rowan native named drawing. Compatible complete broad-child motion contour
traces are explicit JSON sources, not joint rig or flattened idle warps.
"""
from pathlib import Path
from PIL import Image,ImageDraw
import json
P=Path(__file__).parent;ROOT=P.parents[4];OUT=ROOT/'assets/characters/named_hd/rowan';OUT.mkdir(parents=True,exist_ok=True)
O='#241f24';H='#38343d';HS='#222027';HL='#55515b';S='#e8c49d';SS='#c58e69';SL='#fae2bd';C='#a65b45';CL='#cd8260';CS='#713d32';T='#4b4952';TL='#68646e';BOOT='#624634';B=[0,1,0,-1,0,1,0,-1]
def pts(s):return [tuple(map(int,p.split(','))) for p in s.split()]
def poly(d,q,c):d.polygon(q,fill=c,outline=O)
def head(im,dr,b):
 d=ImageDraw.Draw(im)
 def p(q,c):poly(d,[(x,y+b) for x,y in q],c)
 def ln(q,c):d.line([(x,y+b) for x,y in q],fill=c)
 if dr in ['front','back']:
  p([(18,16),(28,16),(32,19),(33,24),(31,30),(28,35),(22,36),(18,33),(15,28),(14,22),(16,18)],H)
  ln([(17,20),(21,18),(27,18),(30,20)],HL)
  if dr=='front':
   p([(19,24),(24,22),(29,24),(31,28),(29,33),(26,36),(22,35),(18,31)],S)
   ln([(29,27),(29,31),(27,33)],SS);ln([(19,28),(20,28)],O);ln([(27,28),(28,28)],O);ln([(20,29),(20,29)],'#98703a');ln([(27,29),(27,29)],'#98703a');ln([(23,33),(25,33)],SS)
   p([(16,20),(21,18),(28,18),(32,21),(31,25),(28,23),(25,24),(23,22),(20,24),(17,27)],H)
   ln([(19,21),(23,20),(27,21)],HL);ln([(16,24),(17,28)],HS)
  else:ln([(19,22),(18,27),(21,31)],HS);ln([(24,19),(26,22),(29,23)],HL);ln([(24,31),(28,32)],HS)
 else:
  p([(19,16),(27,16),(31,19),(32,23),(31,27),(33,29),(31,32),(28,35),(24,36),(19,33),(16,29),(15,24),(16,19)],H)
  ln([(18,20),(22,18),(27,18)],HL)
  p([(25,24),(29,24),(30,27),(34,29),(33,31),(30,31),(29,34),(26,36),(23,33),(22,28)],S)
  ln([(23,27),(23,31),(25,33)],SS);ln([(28,28),(29,28)],O);ln([(28,29),(28,29)],'#98703a');ln([(28,33),(29,33)],SS)
  p([(21,19),(27,18),(31,21),(31,24),(28,23),(25,25),(22,25),(21,28)],H);ln([(22,21),(26,20),(28,21)],HL)
  ln([(17,24),(18,29),(20,31)],HS)
def depth(dr,i=None):
 im=Image.new('RGBA',(48,72));d=ImageDraw.Draw(im);b=0 if i is None else B[i];idx=0 if i is None else i
 low=json.loads((P/f'{dr}_limbs.json').read_text())[idx];upper=json.loads((P/f'{dr}_upper.json').read_text())[idx]
 if i is None:
  low=[[(18,54),(23,54),(23,67),(17,67)],[(17,65),(23,65),(24,67),(24,69),(17,69)],[(26,54),(31,54),(31,67),(25,67)],[(25,65),(31,65),(33,67),(33,69),(25,69)]]
  upper=['13,36 17,37 18,45 17,51 14,53 11,50','13,51 16,51 17,55 15,57 12,55','32,36 36,37 37,45 36,51 33,53 31,50','33,51 36,51 37,55 35,57 32,55',upper[-1]]
 for j,q in enumerate(low):
  poly(d,q,T if j%2==0 else BOOT)
  if j%2==0:d.line([(q[0][0]+2,57),(q[0][0]+2,62)],fill=TL)
 for j,q in enumerate(upper):
  poly(d,pts(q),S if j in [1,3] else C)
  if j in [0,2]:d.line(pts(q)[1:3],fill=CL)
  elif j in [1,3]:d.line(pts(q)[1:3],fill=SL)
 d.polygon([(18,37+b),(21,38+b),(21,53+b),(17,53+b)],fill=CL);d.polygon([(29,37+b),(31,40+b),(31,54+b),(28,54+b)],fill=CS)
 d.line([(18,54+b),(30,54+b)],fill=CS)
 if dr=='front':
  d.line([(23,37+b),(24,42+b),(26,37+b)],fill=CS)
  for y in [43,47,51]:d.point((24,y+b),fill=CL)
 else:d.line([(19,39+b),(29,39+b)],fill=CS)
 head(im,dr,b);return im
def profile(i=None):
 im=Image.new('RGBA',(48,72));d=ImageDraw.Draw(im);b=0 if i is None else B[i];idx=0 if i is None else i
 q=json.loads((P/'right_limbs.json').read_text())[idx];torso=json.loads((P/'right_upper.json').read_text())[idx]
 if i is None:q=[[(20,54),(24,54),(24,67),(19,67)],[(19,65),(24,65),(25,67),(25,69),(18,69)],[(21,36),(25,37),(26,46),(24,50),(21,48)],[(22,48),(25,48),(26,54),(23,56),(21,53)],[(25,54),(29,54),(29,67),(24,67)],[(24,65),(29,65),(32,67),(32,69),(24,69)],[(22,36),(26,37),(28,46),(26,51),(22,49)],[(23,50),(27,50),(28,54),(26,57),(23,55)]]
 for j in range(6):poly(d,q[j],[T,BOOT,CS,S,T,BOOT][j])
 poly(d,torso,C);d.polygon([(20,37+b),(23,38+b),(22,52+b),(20,54+b)],fill=CL);d.line([(27,42+b),(27,54+b)],fill=CS)
 poly(d,q[6],C);d.line(q[6][1:3],fill=CL);poly(d,q[7],S);d.line(q[7][1:3],fill=SL);head(im,'right',b);return im
for dr in ['front','back','right','left']:
 idle=depth(dr) if dr in ['front','back'] else profile()
 if dr=='left':idle=idle.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
 idle.save(OUT/f'idle_{dr}.png');bank=OUT/f'walk_{dr}';bank.mkdir(exist_ok=True)
 for i in range(8):
  im=depth(dr,i) if dr in ['front','back'] else profile(i if dr=='right' else (i+4)%8)
  if dr=='left':im=im.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
  im.save(bank/f'frame_{i+1:02}.png')
