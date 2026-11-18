"""Tessa native 2x drawings; no legacy sprite enlargement or limb transforms.
Static whole-pose contour guides are traced from compatible girl01/girl02 child
walks; new auburn single braid, cream blouse and unsplit sage pinafore are native.
"""
from pathlib import Path
from PIL import Image,ImageDraw
import json
P=Path(__file__).parent; ROOT=P.parents[4];OUT=ROOT/'assets/characters/named_hd/tessa';OUT.mkdir(parents=True,exist_ok=True)
O='#251c22';HS='#4b2928';H='#854b39';HL='#b6754e';S='#e8c49d';SS='#c58e69';SL='#fae2bd';C='#ded1ae';CL='#fbeed0';CS='#bcae91';D='#6e9275';DS='#405b49';DL='#a0b9a2';BOOT='#624232'
BOB=[0,1,0,-1,0,1,0,-1]
def poly(d,p,c):d.polygon(p,fill=c,outline=O)
def points(s):return [tuple(map(int,v.split(','))) for v in s.split()]
def head(im,direction,b=0):
 d=ImageDraw.Draw(im)
 def p(v,c):poly(d,[(x,y+b) for x,y in v],c)
 def line(v,c,w=1):d.line([(x,y+b) for x,y in v],fill=c,width=w)
 if direction in ['front','back']:
  p([(19,14),(28,14),(32,17),(34,23),(33,31),(29,36),(24,38),(19,35),(15,30),(14,24),(16,18)],H)
  line([(18,20),(21,17),(27,16),(30,18)],HL);line([(16,25),(17,31),(20,34)],HS)
  if direction=='front':
   p([(20,23),(27,22),(30,25),(30,32),(27,36),(23,37),(19,34),(17,29)],S)
   line([(28,26),(29,30),(27,34)],SS);line([(19,28),(20,26)],SL)
   p([(16,21),(21,18),(28,18),(32,23),(29,25),(26,23),(23,24),(20,23),(17,27)],H)
   line([(19,21),(23,20),(27,20)],HL)
   for x in [20,27]:line([(x,28),(x+1,28)],O);line([(x,29),(x+1,29)],'#3f784b')
   line([(23,33),(25,33)],SS)
  else:
   line([(20,21),(19,28),(22,34)],HS);line([(24,18),(24,29),(26,34)],HL)
 else:
  p([(20,14),(28,15),(32,19),(32,27),(34,29),(32,31),(29,35),(25,38),(20,35),(16,30),(15,22),(17,17)],H)
  line([(19,18),(23,16),(27,17)],HL)
  p([(25,23),(29,23),(30,26),(34,28),(33,30),(30,30),(30,33),(27,36),(24,35),(23,30)],S)
  line([(24,26),(24,31),(26,34)],SS);line([(29,27),(30,27)],O);line([(29,28),(30,28)],'#3f784b')
  p([(22,18),(28,18),(31,22),(30,25),(27,23),(24,24),(21,27)],H);line([(23,20),(28,20)],HL)
  line([(17,24),(18,30),(21,33)],HS)
 # Braid: native alternating woven clusters, anatomically left over front shoulder;
 # central rear fall and trailing profile; not twin-braid roster identity.
 bx=32 if direction=='front' else 24 if direction=='back' else 17
 start=29 if direction=='front' else 32 if direction=='back' else 27
 for y in range(start,48,4):
  p([(bx,y),(bx+2,y+1),(bx+2,y+3),(bx,y+5),(bx-2,y+3),(bx-2,y+1)],H)
  line([(bx-1,y+1),(bx+1,y+2)],HL);line([(bx+1,y+3),(bx,y+4)],HS)
 line([(bx-2,49),(bx+2,49)],DS);line([(bx,50),(bx,51)],HL)
def depth(dr,i=None,run=False):
 im=Image.new('RGBA',(48,72));d=ImageDraw.Draw(im);b=0 if i is None else ([0,-2,0,-2][i] if run else BOB[i])
 if i is None:
  q=[[(18,55),(23,55),(23,66),(24,69),(17,69),(17,66)],[(17,65),(23,65),(24,67),(24,69),(17,69)],[(26,55),(31,55),(31,66),(32,69),(25,69),(25,66)],[(25,65),(31,65),(33,67),(33,69),(25,69)],[(12,38),(17,38),(17,48),(15,53),(11,52)],[(12,52),(15,52),(16,55),(14,57),(11,56)],[(30,38),(35,38),(36,48),(35,53),(31,52)],[(31,52),(35,52),(36,55),(34,57),(31,56)]]
 else:q=json.loads((P/f'{dr}_contours.json').read_text())[i]
 if run:q=json.loads((P/f'run_{dr}_contours.json').read_text())[i]
 for j in range(4):
  poly(d,q[j],S if j%2==0 else BOOT)
  if j%2:d.line(q[j][1:3],fill='#9d7452')
 for j in range(4,8):
  poly(d,q[j],C if j%2==0 else S);d.line(q[j][1:3],fill=CL if j%2==0 else SL)
 poly(d,[(17,37+b),(29,37+b),(32,49+b),(30,54+b),(17,54+b),(15,48+b)],C)
 d.polygon([(19,39+b),(21,39+b),(21,49+b),(27,49+b),(27,39+b),(29,39+b),(30,55+b),(17,55+b)],fill=D,outline=DS)
 # Eight whole skirt outlines retain weight, gentle cloth follow, no split.
 skirts=['17,50 30,50 35,61 31,63 16,63 12,61','17,51 30,51 35,62 31,64 16,64 12,62','17,50 30,50 34,61 30,63 15,62 12,60','17,49 30,49 34,60 30,62 15,61 12,59','17,50 30,50 35,61 31,63 16,63 12,61','17,51 30,51 35,62 31,64 16,64 12,62','17,50 30,50 35,60 32,62 17,63 13,61','17,49 30,49 35,59 32,61 17,62 13,60']
 poly(d,points(skirts[0 if i is None else i]),D);d.line([(21,53+b),(19,60+b)],fill=DL);d.line([(28,53+b),(31,60+b)],fill=DS);d.line([(16,61+b),(31,61+b)],fill=DL)
 head(im,dr,b);return im
def profile(i=None,run=False):
 im=Image.new('RGBA',(48,72));d=ImageDraw.Draw(im);b=0 if i is None else ([0,-2,0,-2][i] if run else BOB[i])
 q=json.loads((P/'right_contours.json').read_text())[0 if i is None else i]
 if i is None:q=['20,54 24,54 24,65 24,68 19,68','19,65 24,65 25,67 25,69 18,69','21,38 25,38 26,46 24,49 21,47','22,47 25,47 25,53 23,54 21,52','25,54 29,54 29,65 29,68 24,68','24,65 29,65 32,67 32,69 24,69','22,38 26,39 28,48 26,52 22,49','23,50 27,50 28,55 26,57 23,55']
 if run:q=json.loads((P/'run_right_contours.json').read_text())[i]
 for j in range(6):poly(d,points(q[j]),[S,BOOT,C,S,S,BOOT][j])
 poly(d,[(19,37+b),(28,37+b),(30,48+b),(28,54+b),(18,54+b)],C)
 poly(d,[(20,39+b),(22,39+b),(23,50+b),(28,51+b),(32,61+b),(27,63+b),(17,63+b),(15,61+b),(18,50+b)],D)
 d.line([(20,52+b),(18,60+b)],fill=DL);d.line([(27,53+b),(29,60+b)],fill=DS)
 poly(d,points(q[6]),C);d.line(points(q[6])[1:3],fill=CL);poly(d,points(q[7]),S);d.line(points(q[7])[1:3],fill=SL)
 head(im,'right',b);return im
for dr in ['front','back','right','left']:
 idle=depth(dr) if dr in ['front','back'] else profile()
 if dr=='left':idle=idle.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
 idle.save(OUT/f'idle_{dr}.png')
 bank=OUT/f'walk_{dr}';bank.mkdir(exist_ok=True)
 for i in range(8):
  im=depth(dr,i) if dr in ['front','back'] else profile(i if dr=='right' else (i+4)%8)
  if dr=='left':im=im.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
  im.save(bank/f'frame_{i+1:02}.png')

for dr in ['front','back','right','left']:
 bank=OUT/f'run_{dr}';bank.mkdir(exist_ok=True)
 for i in range(4):
  im=depth(dr,i,True) if dr in ['front','back'] else profile(i if dr=='right' else (i+2)%4,True)
  if dr=='left':im=im.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
  im.save(bank/f'frame_{i+1:02}.png')
