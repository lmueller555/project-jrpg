"""Native Finn complete drawings. Exact original 22-world-pixel stature;
compatible stored child lower-gait outlines used below his own shorter vest.
No legacy scaling, joint animation, raster limbs or warp interpolation.
"""
from pathlib import Path
from PIL import Image,ImageDraw
import json
P=Path(__file__).parent;ROOT=P.parents[4];OUT=ROOT/'assets/characters/named_hd/finn';OUT.mkdir(parents=True,exist_ok=True)
O='#281f20';H='#785132';HS='#3d2118';HL='#a47848';S='#e8c49d';SS='#c58e69';SL='#fae2bd';C='#c3a575';CL='#e2cca2';CS='#9b7a49';V='#6e7d43';VL='#919b61';VS='#455531';T='#746050';TL='#9d7953';BOOT='#51413b';B=[0,1,0,-1,0,1,0,-1]
def pts(s):return [tuple(map(int,p.split(','))) for p in s.split()]
def poly(d,q,c):d.polygon(q,fill=c,outline=O)
def head(im,dr,b):
 d=ImageDraw.Draw(im)
 def p(q,c):poly(d,[(x,y+b) for x,y in q],c)
 def ln(q,c):d.line([(x,y+b) for x,y in q],fill=c)
 if dr in ['front','back']:
  p([(18,29),(17,27),(21,28),(24,26),(27,28),(31,28),(30,31),(33,33),(31,35),(31,40),(28,44),(21,44),(17,41),(16,36),(15,34),(17,32)],H)
  ln([(19,30),(23,29),(25,28),(28,30)],HL);ln([(17,35),(18,39),(20,41)],HS)
  if dr=='front':
   p([(20,34),(24,33),(28,34),(30,36),(29,41),(26,44),(22,43),(19,40)],S)
   ln([(28,37),(28,41),(26,42)],SS);ln([(20,37),(21,37)],O);ln([(27,37),(28,37)],O);ln([(21,38),(21,38)],'#4e7950');ln([(27,38),(27,38)],'#4e7950');ln([(23,41),(25,41)],SS)
   p([(18,31),(23,29),(29,31),(30,35),(27,34),(25,35),(22,33),(19,36)],H);ln([(21,31),(24,31),(26,32)],HL)
  else:ln([(22,31),(20,35),(22,40)],HL);ln([(27,33),(29,37),(28,41)],HS)
 else:
  p([(18,29),(18,27),(22,28),(25,26),(28,29),(31,29),(30,32),(32,34),(31,37),(33,38),(31,40),(28,43),(23,44),(19,42),(16,38),(16,33)],H)
  ln([(19,31),(23,29),(27,30)],HL)
  p([(25,34),(29,34),(30,37),(33,38),(32,40),(30,40),(28,43),(25,43),(23,40),(23,36)],S)
  ln([(24,37),(24,40)],SS);ln([(28,37),(29,37)],O);ln([(28,38),(28,38)],'#4e7950');ln([(28,41),(29,41)],SS)
  p([(23,31),(28,31),(31,33),(30,35),(27,34),(24,36),(22,36)],H);ln([(23,32),(27,32)],HL)
# Shorter six-year-old sleeves: eight complete native drawings, not old arm shifts.
A=[
['15,45 19,45 19,50 18,55 15,56 13,53','15,55 18,55 19,58 16,60 14,58','29,45 33,45 34,49 33,52 30,53 28,50','30,51 33,51 34,54 32,56 29,54'],
['15,46 19,46 20,51 19,56 16,57 13,54','16,56 19,56 20,59 17,61 15,59','29,46 33,46 34,50 33,54 30,55 28,51','30,53 33,53 34,56 32,58 29,56'],
['15,45 19,45 20,50 19,54 16,56 13,53','16,54 19,54 20,57 17,59 15,57','29,45 33,45 34,50 33,55 30,56 28,51','30,54 33,54 34,57 32,59 29,57'],
['15,44 19,44 20,49 19,52 16,54 13,51','15,52 19,52 20,55 17,57 14,55','29,44 33,44 34,49 32,55 29,56 28,51','29,54 32,54 33,57 31,59 28,57'],
['15,45 19,45 20,49 18,52 15,53 13,50','14,51 18,51 19,54 16,56 13,54','29,45 33,45 34,50 32,56 29,57 28,52','29,55 32,55 33,58 31,60 28,58'],
['15,46 19,46 20,50 19,54 16,55 13,52','15,53 19,53 20,56 17,58 14,56','29,46 33,46 34,51 33,57 30,58 28,53','30,56 33,56 34,59 32,61 29,59'],
['15,45 19,45 20,50 19,55 16,56 13,52','16,54 19,54 20,57 17,59 15,57','29,45 33,45 34,50 33,54 30,56 28,52','30,54 33,54 34,57 32,59 29,57'],
['15,44 19,44 20,49 19,56 16,57 13,53','16,55 19,55 20,58 17,60 15,58','29,44 33,44 34,49 33,52 30,54 28,50','30,52 33,52 34,55 32,57 29,55']]
def depth(dr,i=None):
 b=0 if i is None else B[i];im=Image.new('RGBA',(48,72));d=ImageDraw.Draw(im)
 low=json.loads((P/f'{dr}_lower.json').read_text())[0 if i is None else i]
 if i is None:low=[[(18,55),(23,55),(23,67),(17,67)],[(17,65),(23,65),(24,67),(24,69),(17,69)],[(26,55),(31,55),(31,67),(25,67)],[(25,65),(31,65),(33,67),(33,69),(25,69)]]
 for j,q in enumerate(low):
  poly(d,q,T if j%2==0 else BOOT)
  if j%2==0:d.line([(q[0][0]+2,60),(q[0][0]+2,63)],fill=TL)
 upper=A[0 if i is None else (i+4)%8 if dr=='back' else i]
 if i is None:upper=['15,45 19,45 19,54 16,57 13,54','15,55 18,55 18,59 15,59 14,57','29,45 33,45 34,54 32,57 29,54','30,55 33,55 34,58 32,60 29,58']
 for j,q in enumerate(upper):poly(d,pts(q),C if j%2==0 else S);d.line(pts(q)[1:3],fill=CL if j%2==0 else SL)
 poly(d,[(19,43+b),(28,43+b),(31,48+b),(30,59+b),(18,59+b),(17,48+b)],C)
 poly(d,[(19,44+b),(22,44+b),(23,48+b),(22,57+b),(18,57+b)],V);poly(d,[(26,44+b),(29,44+b),(30,57+b),(25,57+b),(25,48+b)],V)
 d.line([(20,46+b),(19,54+b)],fill=VL);d.line([(28,46+b),(29,54+b)],fill=VS);d.line([(23,49+b),(24,49+b)],fill=CL)
 if dr=='back':d.line([(19,48+b),(29,48+b)],fill=VL)
 head(im,dr,b);return im
# Own complete profile sleeve shapes; guide legs retain their full two-step paths.
PA=[['21,45 24,45 23,50 19,54 17,52','17,51 20,52 21,55 18,57 16,54','22,45 26,45 28,50 31,52 30,55 26,53 23,50','29,51 32,52 33,55 30,57 28,54'],['21,46 24,46 24,51 21,55 18,54','18,53 21,54 22,57 19,59 17,56','22,46 26,46 28,51 30,54 28,57 25,54 23,51','28,54 31,55 31,58 28,59 26,56'],['21,45 24,45 25,51 24,55 21,55','21,54 24,54 25,57 23,59 20,57','22,45 26,45 27,51 27,56 24,57 22,52','24,55 27,55 28,58 26,60 23,58'],['21,44 24,44 26,49 29,52 27,55 23,52','27,51 30,52 31,55 28,57 26,54','22,44 26,44 26,49 23,54 20,55 19,52','19,53 22,54 23,57 20,59 18,56']]
def profile(i=None):
 b=0 if i is None else B[i];im=Image.new('RGBA',(48,72));d=ImageDraw.Draw(im);g=json.loads((P/'right_guide.json').read_text())[0 if i is None else i];arms=PA[0 if i is None else i%4]
 if i is not None and i>=4:arms=[arms[2],arms[3],arms[0],arms[1]]
 if i is None:g=['20,56 24,56 24,67 19,67','19,65 24,65 25,67 25,69 18,69','','','25,56 29,56 29,67 24,67','24,65 29,65 32,67 32,69 24,69'];arms=['21,45 24,45 25,53 23,56 20,54','21,54 24,54 25,58 23,59 20,57','22,45 26,45 27,53 25,57 22,55','23,55 26,55 27,59 25,60 22,58']
 for j in [0,1,4,5]:poly(d,pts(g[j]),T if j%2==0 else BOOT)
 poly(d,pts(arms[0]),C);poly(d,pts(arms[1]),S)
 poly(d,[(20,43+b),(27,43+b),(29,48+b),(29,59+b),(19,59+b),(18,49+b)],C)
 poly(d,[(20,44+b),(23,44+b),(24,48+b),(23,57+b),(19,57+b)],V);d.line([(21,46+b),(20,54+b)],fill=VL)
 poly(d,pts(arms[2]),C);d.line(pts(arms[2])[1:3],fill=CL);poly(d,pts(arms[3]),S);head(im,'right',b);return im
for dr in ['front','back','right','left']:
 idle=depth(dr) if dr in ['front','back'] else profile()
 if dr=='left':idle=idle.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
 idle.save(OUT/f'idle_{dr}.png');bank=OUT/f'walk_{dr}';bank.mkdir(exist_ok=True)
 for i in range(8):
  im=depth(dr,i) if dr in ['front','back'] else profile(i if dr=='right' else (i+4)%8)
  if dr=='left':im=im.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
  im.save(bank/f'frame_{i+1:02}.png')
