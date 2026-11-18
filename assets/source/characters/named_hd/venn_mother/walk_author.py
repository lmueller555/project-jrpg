"""Complete named Venn walk drawings using explicitly stored compatible native
pose-contour guides. New named clothing is resolved before full-frame export.
"""
from pathlib import Path
from PIL import Image,ImageDraw
import json
import author
P=Path(__file__).parent;OUT=author.OUT;ROLE=author.ROLE;O=author.O;SK=author.SK
B=[0,1,0,-1,0,1,0,-1]
def poly(d,q,c):d.polygon(q,fill=c,outline=O)
def pts(s):return [tuple(map(int,p.split(','))) for p in s.split()]
def drawing(dr,i):
 im=Image.new('RGBA',(48,72));d=ImageDraw.Draw(im);b=B[i]
 if ROLE=='child':
  C,CH,CD,T,TL='#839eaf','#b2c7ca','#536f86','#746050','#9d7953';q=json.loads((P/f'{dr}_limbs.json').read_text())[i];up=json.loads((P/f'{dr}_upper.json').read_text())[i]
  if dr!='right':
   for j in range(4):poly(d,q[j],T if j%2==0 else '#624634')
   for j,v in enumerate(up):poly(d,pts(v),SK if j in [1,3] else C)
   d.polygon([(18,38+b),(21,38+b),(20,53+b),(17,53+b)],fill=CH);d.polygon([(29,38+b),(31,41+b),(30,54+b),(28,54+b)],fill=CD)
   if dr=='front':
    d.line([(22,40+b),(24,43+b),(26,40+b)],fill=CD)
    for y in [46,50]:d.point((24,y+b),fill=CH)
   else:d.line([(19,42+b),(29,42+b)],fill=CD)
  else:
   for j in range(6):poly(d,q[j],[T,'#51413b',CD,SK,T,'#624634'][j])
   poly(d,up,C);d.polygon([(20,38+b),(23,38+b),(22,52+b),(20,54+b)],fill=CH);poly(d,q[6],C);d.line(q[6][1:3],fill=CH);poly(d,q[7],SK)
  # Child head crown18 versus guide head18; scoped canonical feature preservation.
  h=Image.new('RGBA',(48,72));author.head(h,dr);im.alpha_composite(h,(0,b));return im
 k=json.loads((P/f'{dr}_poses.json').read_text())[i];C,CH,CD=('#ded1ae','#fbeed0','#bcae91') if ROLE=='father' else ('#4c8278','#83aaa0','#305c59')
 T,TL=('#9b7a49','#c3a575') if ROLE=='father' else ('#51413b','#9d7953')
 if dr!='right':
  for key,col in [('left',T),('right',T),('lb','#624634'),('rb','#624634'),('la',C),('ra',C),('lh',SK),('rh',SK),('torso',C)]:poly(d,k[key],col)
  d.line(k['left'][1:4],fill=TL);d.line(k['right'][1:4],fill=TL)
  d.polygon([(17,29+b),(20,30+b),(19,40+b),(16,40+b)],fill=CH);d.polygon([(29,29+b),(32,32+b),(30,41+b),(28,40+b)],fill=CD)
  if ROLE=='father':
   poly(d,[(18,27+b),(22,28+b),(23,34+b),(22,46+b),(17,46+b)],'#97614b');poly(d,[(26,28+b),(30,27+b),(32,46+b),(26,46+b),(25,34+b)],'#97614b');d.line([(19,29+b),(18,42+b)],fill='#bc8563');d.line([(29,30+b),(30,43+b)],fill='#694439')
   if dr=='front':d.rectangle((23,31+b,24,44+b),fill='#e6d9ba')
   else:d.line([(18,34+b),(30,34+b)],fill='#bc8563')
  else:
   skirts=['17,43 30,43 35,58 32,62 16,62 12,59','17,44 30,44 35,59 32,63 16,63 12,60','17,43 30,43 34,59 30,62 15,61 12,58','17,42 30,42 34,58 30,61 15,60 12,57','17,43 30,43 35,58 32,62 16,62 12,59','17,44 30,44 35,59 32,63 16,63 12,60','17,43 30,43 35,57 33,61 17,62 13,59','17,42 30,42 35,56 33,60 17,61 13,58']
   poly(d,pts(skirts[i]),C);d.line([(19,48+b),(17,58+b)],fill=CH);d.line([(29,49+b),(32,58+b)],fill=CD)
   if dr=='front':poly(d,[(19,38+b),(28,38+b),(30,58+b),(17,58+b)],'#d8c39c');d.line([(20,42+b),(19,55+b)],fill='#eee0bd');d.line([(27,44+b),(28,55+b)],fill='#ac9576')
   else:d.line([(18,40+b),(29,40+b)],fill='#ac9576')
 else:
  for key,col in [('fl',T),('fb','#51413b'),('fa',C),('fh',SK),('nl',T),('nb','#624634'),('co',C)]:poly(d,k[key],col)
  d.line(k['nl'][1:4],fill=TL)
  if ROLE=='father':poly(d,[(20,28+b),(23,29+b),(25,35+b),(24,46+b),(19,46+b)],'#97614b');d.line([(21,30+b),(20,42+b)],fill='#bc8563')
  else:
   poly(d,[(19,43+b),(29,43+b),(33,58+b),(29,61+b),(17,61+b),(15,58+b)],C);d.line([(19,48+b),(17,57+b)],fill=CH);d.rectangle((29,41+b,31,57+b),fill='#d8c39c');d.line([(30,43+b),(30,55+b)],fill='#eee0bd')
  poly(d,k['na'],C);d.line(k['na'][1:4],fill=CH);poly(d,k['nh'],SK)
 d.rectangle((22,22+b,26,28+b),fill=SK);h=Image.new('RGBA',(48,72));author.head(h,dr);im.alpha_composite(h,(0,b));return im
for dr in ['front','back','right','left']:
 bank=OUT/f'walk_{dr}';bank.mkdir(exist_ok=True)
 for i in range(8):
  im=drawing('right' if dr=='left' else dr,(i+4)%8 if dr=='left' else i)
  if dr=='left':im=im.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
  im.save(bank/f'frame_{i+1:02}.png')
design=json.loads((OUT/'design.json').read_text());design['stationary']=True;design['design_notes']+=' Four complete native walk banks supplied for standard replacement compatibility; live actor remains stationary.';(OUT/'design.json').write_text(json.dumps(design,indent=2))
