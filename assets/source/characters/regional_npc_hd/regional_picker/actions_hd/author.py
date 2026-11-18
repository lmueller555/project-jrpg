"""Complete native orchard-picker action drawings. Explicit whole-pose contours,
no joint solver, detached-raster limbs, interpolation or old sprite enlargement.
Carry lower/body contours trace approved adult_man_02 same-phase complete gait;
clothing/arms resolve a natural two-handed fruit grip. Canonical head protected.
"""
from pathlib import Path
from PIL import Image,ImageDraw
import json
P=Path(__file__).parent;M=P/'masters';M.mkdir(exist_ok=True)
O='#1a0e16';C='#a65b45';CH='#cc8566';CD='#713d32';T='#4b4952';TS='#35343b';TL='#716c76';SK='#e8c49d';SS='#eda052';SL='#ffe0b5';BOOT='#714b34';BL='#98704c'
REF={d:Image.open(P/'references'/f'idle_{d}.png').convert('RGBA') for d in ['front','back','right','left']}
def pts(v):return [tuple(map(int,p.split(','))) for p in v.split()]
def poly(d,q,c):d.polygon(pts(q) if isinstance(q,str) else q,fill=c,outline=O)
def padded(im):
 out=Image.new('RGBA',(80,88));out.alpha_composite(im,(16,7));return out
# Four independently plotted grip outlines, compatible two-step weight phases.
FARMS=[
['13,29 17,30 17,37 19,42 17,45 13,41 11,35','15,42 19,42 23,47 22,50 19,50 15,47','31,29 34,30 35,36 33,41 30,45 27,43 30,38','28,42 31,44 28,49 25,50 24,47'],
['13,30 17,31 18,38 20,43 18,46 14,42 11,36','16,43 20,43 24,48 23,51 20,51 16,48','31,30 34,31 35,37 33,42 30,46 27,44 30,39','28,43 31,45 28,50 25,51 24,48'],
['13,29 17,30 18,37 19,42 17,45 13,41 11,35','15,42 19,42 23,47 22,50 19,50 15,47','31,29 34,30 35,36 33,41 30,45 27,43 30,38','28,42 31,44 28,49 25,50 24,47'],
['13,28 17,29 17,36 19,41 17,44 13,40 11,34','15,41 19,41 23,46 22,49 19,49 15,46','31,28 34,29 35,35 33,40 30,44 27,42 30,37','28,41 31,43 28,48 25,49 24,46']]
PARMS=[
['23,27 27,28 29,34 29,40 27,44 24,42 25,36','25,41 28,42 27,47 24,49 22,47','22,28 26,29 29,35 31,40 29,44 25,42 23,36','26,41 30,43 28,48 25,50 22,48 23,45'],
['23,28 27,29 29,35 29,41 27,45 24,43 25,37','25,42 28,43 27,48 24,50 22,48','22,29 26,30 29,36 31,41 29,45 25,43 23,37','26,42 30,44 28,49 25,51 22,49 23,46'],
['23,27 27,28 29,34 29,40 27,44 24,42 25,36','25,41 28,42 27,47 24,49 22,47','22,28 26,29 29,35 31,40 29,44 25,42 23,36','26,41 30,43 28,48 25,50 22,48 23,45'],
['23,26 27,27 29,33 29,39 27,43 24,41 25,35','25,40 28,41 27,46 24,48 22,46','22,27 26,28 29,34 31,39 29,43 25,41 23,35','26,40 30,42 28,47 25,49 22,47 23,44']]
def torso_detail(d,b,back=False,profile=False):
 if profile:
  d.polygon([(19,29+b),(21,29+b),(20,39+b),(19,43+b)],fill=CH);d.line([(25,29+b),(27,34+b)],fill=CD);d.line([(19,41+b),(27,41+b)],fill='#59402b',width=2);d.line([(20,40+b),(27,40+b)],fill='#b18e56')
 else:
  d.polygon([(28,27+b),(32,30+b),(31,35+b),(29,37+b),(29,43+b),(26,44+b),(26,31+b)],fill=CD);d.line([(18,30+b),(18,39+b)],fill=CH);d.line([(18,41+b),(29,41+b)],fill='#59402b',width=2);d.line([(18,40+b),(29,40+b)],fill='#9f7a48')
  if back:d.line([(19,28+b),(28,28+b)],fill=CH);d.line([(23,30+b),(23,38+b)],fill=CD)
  else:
   d.rectangle((23,40+b,26,42+b),fill='#d9b967');d.point((24,41+b),fill='#59402b');d.polygon([(19,25+b),(23,29+b),(21,32+b),(17,27+b)],fill=CH);d.line([(24,30+b),(24,38+b)],fill=CD)
   for y in [33,36]:d.point((25,y+b),fill=CH)
def carry(dr,i):
 k=json.loads((P/f'carry_{dr}_contours.json').read_text())[i];im=Image.new('RGBA',(48,72));d=ImageDraw.Draw(im);b=k['bob'];a=(PARMS if dr=='right' else FARMS)[i%4]
 if dr=='right':
  for key,c in [('fl',TS),('fb',BOOT),('nl',T),('nb',BOOT)]:poly(d,k[key],c)
  poly(d,a[0],CD);poly(d,a[1],SK);poly(d,k['co'],C);torso_detail(d,b,profile=True);poly(d,a[2],C);d.line(pts(a[2])[1:3],fill=CH);poly(d,a[3],SK)
 else:
  for key,c in [('left',T),('right',TS),('lb',BOOT),('rb',BOOT)]:poly(d,k[key],c)
  # Rear hands are on the unseen front of the body; torso naturally occludes.
  if dr=='back':
   for q in [a[0],a[2]]:poly(d,q,C)
  poly(d,k['torso'],C);torso_detail(d,b,back=dr=='back')
  if dr=='front':
   for q,c in zip(a,[C,SK,C,SK]):poly(d,q,c)
  for key in ['left','right']:d.line(k[key][1:4],fill=TL)
 for key in (['fb','nb'] if dr=='right' else ['lb','rb']):d.line(k[key][1:3],fill=BL)
 im.alpha_composite(REF[dr].crop((0,0,48,28)),(0,b));return im
# Static work keys are complete unified drawings. Reused exact planted lower
# pixels represent unchanged support, not walking legs attached to a work rig.
BODY=['16,25 21,24 27,24 32,26 34,33 31,40 31,46 17,46 15,39 12,34 12,29','16,24 21,23 27,23 32,25 34,32 31,39 31,45 17,45 15,38 12,33 12,28','16,25 21,24 27,24 32,26 34,33 31,40 31,46 17,46 15,39 12,34 12,29','16,25 21,24 27,24 32,26 34,33 31,40 31,46 17,46 15,39 12,34 12,29']
REACH=[
['13,29 17,29 19,33 18,37 14,39 11,36','14,36 17,36 21,33 23,31 25,33 23,37 19,40 15,40','31,29 34,30 35,34 32,38 28,37 28,33','28,34 31,35 31,29 29,24 27,23 26,26'],
['13,28 17,28 18,31 16,34 12,35 10,32','12,32 16,32 20,29 23,26 25,28 23,32 19,35 14,36','31,28 34,29 34,32 31,35 28,33','28,31 31,32 30,27 29,23 27,22 25,24 26,28'],
['13,29 17,29 18,32 16,35 12,36 10,33','12,33 16,33 20,30 23,27 25,29 23,33 19,36 14,37','31,29 34,30 34,33 31,36 28,34','28,32 31,33 30,28 29,24 27,23 25,25 26,29'],
['13,29 17,29 19,33 18,37 14,39 11,36','14,36 17,36 21,33 23,31 25,33 23,37 19,40 15,40','31,29 34,30 35,34 32,38 28,37 28,33','28,34 31,35 31,29 29,24 27,23 26,26']]
ADMIRE=[
['13,29 17,30 19,35 17,39 13,38 11,34','14,36 18,37 22,32 23,29 21,28 19,31 16,33','31,29 34,30 35,34 32,39 28,38 28,34','28,35 31,36 29,31 27,29 25,30 25,33'],
['13,29 17,30 19,35 17,39 13,38 11,34','14,36 18,37 22,33 23,30 21,29 19,32 16,34','31,29 34,30 35,34 32,39 28,38 28,34','28,35 31,36 29,32 27,30 25,31 25,34']]
LOWER=[ADMIRE[0],
['13,29 17,30 19,36 18,40 14,40 11,35','15,38 18,39 23,36 24,33 22,32 20,35 17,36','31,29 34,30 35,35 33,40 29,40 28,35','29,38 32,39 29,35 27,33 25,34 25,37'],
['13,29 17,30 18,36 19,42 16,44 12,39 11,34','15,41 18,41 23,41 24,38 22,37 20,40 17,39','31,29 34,30 35,36 33,42 29,44 27,40 29,36','29,41 32,42 29,40 27,38 25,39 25,42'],FARMS[0]]
def standing(key,i):
 im=Image.new('RGBA',(48,72));im.alpha_composite(REF['front'].crop((16,46,33,72)),(16,46));d=ImageDraw.Draw(im);b=-1 if key=='reach' and i==1 else 0;poly(d,BODY[1 if b else 0],C);torso_detail(d,b)
 a=REACH[i] if key=='reach' else ADMIRE[i] if key=='admire' else LOWER[i]
 for q,c in zip(a,[C,SK,C,SK]):poly(d,q,c)
 im.alpha_composite(REF['front'].crop((0,0,48,28)),(0,b))
 if key=='reach':
  for q in [a[1],a[3]]:poly(d,q,SK)
 return im
# Whole crouching set-down outlines: trunk pitches toward the basket without
# changing planted soles. Both knees bend and shirt/head lower coherently.
SORT=[
{'torso':'20,29 26,28 30,32 31,39 29,47 20,47 18,40','legs':['20,44 25,44 24,53 22,61 23,66 18,66 17,61 19,53','25,44 30,44 31,52 29,60 29,66 24,66 24,60'], 'arms':['23,31 27,32 29,37 31,40 29,43 25,40 22,36','28,40 31,41 33,44 31,47 28,46','22,32 26,33 28,38 30,42 28,45 24,42 21,36','27,43 30,43 28,47 25,49 22,47 23,44'], 'head':2},
{'torso':'21,32 27,32 31,36 32,42 29,49 20,49 18,43','legs':['20,46 25,46 23,54 20,60 23,66 18,66 16,60 18,53','25,46 30,46 33,54 30,61 29,66 24,66 25,60'], 'arms':['24,34 28,35 30,40 33,43 31,46 27,43 23,39','30,43 33,44 35,47 33,50 30,49','23,35 27,36 29,41 32,45 30,48 26,45 22,39','29,46 32,46 29,49 25,50 22,48 23,45'], 'head':5},
{'torso':'22,34 28,34 32,38 33,44 29,50 20,50 18,44','legs':['20,47 25,47 23,55 19,60 23,66 18,66 15,60 18,53','25,47 30,47 34,55 30,62 29,66 24,66 25,60'], 'arms':['25,36 29,37 31,42 34,45 32,48 28,45 24,41','31,45 34,46 36,49 34,52 31,51','24,37 28,38 30,43 33,47 31,50 27,47 23,41','30,48 33,48 30,51 26,51 23,49 24,46'], 'head':7},
{'torso':'22,34 28,34 32,38 33,44 29,50 20,50 18,44','legs':['20,47 25,47 23,55 19,60 23,66 18,66 15,60 18,53','25,47 30,47 34,55 30,62 29,66 24,66 25,60'], 'arms':['25,36 29,37 31,42 34,45 32,48 28,45 24,41','31,45 34,46 36,49 34,52 31,51','24,37 28,38 30,43 33,47 31,50 27,47 23,41','30,48 33,48 30,51 27,52 24,50 24,47'], 'head':7}]
def sort(i):
 q=SORT[i];im=Image.new('RGBA',(48,72));d=ImageDraw.Draw(im)
 for a,c in zip(q['legs'],[TS,T]):poly(d,a,c)
 for a in ['18,63 23,63 24,66 28,67 28,69 18,69','24,63 29,63 30,66 34,67 34,69 24,69']:poly(d,a,BOOT)
 poly(d,q['arms'][0],CD);poly(d,q['arms'][1],SK);poly(d,q['torso'],C);d.line([(22,36+i),(22,44+i)],fill=CH);d.line([(21,45+i),(29,45+i)],fill='#59402b',width=2);poly(d,q['arms'][2],C);poly(d,q['arms'][3],SK);im.alpha_composite(REF['right'].crop((0,0,48,28)),(1,q['head']));return im
def rest(i):
 im=Image.new('RGBA',(48,72));d=ImageDraw.Draw(im)
 # Seated pelvis/thigh plane and bent calves, not a shortened standing leg.
 poly(d,'17,51 30,51 34,57 34,61 29,63 17,63 13,59 14,55',TS);poly(d,'18,53 29,53 31,57 28,60 18,60 15,57',T);d.line([(18,55),(27,55),(29,57)],fill=TL)
 poly(d,'16,59 21,59 21,66 20,69 15,69 15,64',T);poly(d,'28,59 33,59 33,66 32,69 27,69 27,64',T)
 for q in ['14,65 20,65 22,67 22,69 14,69','26,65 32,65 34,67 34,69 26,69']:poly(d,q,BOOT)
 poly(d,'17,35 22,34 28,34 32,36 34,44 31,53 17,53 14,45 13,39',C);d.line([(18,39),(18,49)],fill=CH);d.line([(28,39),(29,49)],fill=CD);d.line([(18,51),(30,51)],fill='#59402b',width=2)
 for q,c in [('13,38 17,39 18,46 20,51 17,54 13,50 11,44',C),('16,51 20,51 23,55 21,58 18,57',SK),('31,38 35,39 36,44 34,50 30,54 27,52 30,47',C),('28,51 31,53 28,58 25,58 24,55',SK)]:poly(d,q,c)
 im.alpha_composite(REF['front'].crop((0,0,48,28)),(0,10));return im
for dr in ['front','back','right','left']:
 for i in range(8):
  im=carry('right' if dr=='left' else dr,(i+4)%8 if dr=='left' else i)
  if dr=='left':im=im.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
  padded(im).save(M/f'carry_{dr}_{i:02}.png')
for key,count in [('reach',4),('admire',2),('lower',4)]:
 for i in range(count):padded(standing(key,i)).save(M/f'{key}_front_{i:02}.png')
for i in range(4):padded(sort(i)).save(M/f'sort_right_{i:02}.png')
# Rest deliberately still, no involuntary breathing/foot slide added.
padded(rest(0)).save(M/'rest_front_00.png')
