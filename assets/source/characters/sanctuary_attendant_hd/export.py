"""Native whole carry drawings from explicit matching roster dress/gait contours.
No limb rotation, sprite warp or runtime composited linen overlay.
"""
from PIL import Image,ImageDraw
from pathlib import Path
import json
SRC=Path(__file__).parent;ROOT=SRC.parents[3]
OUT=ROOT/'assets/characters/named_hd/sanctuary_attendant'
REF=ROOT/'assets/characters/npc_roster_hd/adult_woman_01'
K=json.loads((SRC/'carry_contours.json').read_text())
O='#211a23';C='#4d77a0';S='#304f70';L='#7da5c7';SK='#e8c49d'
def carry(face,k):
 im=Image.new('RGBA',(48,72));d=ImageDraw.Draw(im);b=k['bob']
 def poly(points,c):d.polygon([tuple(p) for p in points],fill=c,outline=O)
 for key in (['lb','rb'] if face in ('front','back') else ['fb','nb']):
  poly(k[key],'#714b34');d.line([tuple(p) for p in k[key][1:4]],fill='#98704c')
 poly(k['dress'],C)
 for key,color in [('foldlight',L),('foldshade',S),('fold',L)]:
  if key in k:d.polygon([tuple(p) for p in k[key]],fill=color)
 d.line([(19,44+b),(21,54),(19,61)],fill=S)
 d.line([(18,41+b),(30,41+b)],fill='#65482f',width=2)
 if face=='front':
  poly([(14,29+b),(18,30+b),(19,36+b),(17,39+b),(13,36+b)],C)
  poly([(30,30+b),(34,29+b),(35,36+b),(31,40+b),(28,37+b)],S)
  poly([(13,35+b),(17,35+b),(18,42+b),(22,44+b),(19,48+b),(13,44+b)],SK)
  poly([(31,35+b),(35,35+b),(35,44+b),(29,48+b),(26,44+b),(30,42+b)],SK)
  poly([(13,40+b),(30,39+b),(36,44+b),(35,50+b),(12,50+b),(11,45+b)],'#ddd9b8')
  d.line([(13,45+b),(34,45+b)],fill='#aaa783');d.line([(15,41+b),(29,41+b)],fill='#faf2d1')
  d.line([(14,48+b),(17,48+b)],fill=SK,width=2);d.line([(30,48+b),(33,48+b)],fill=SK,width=2)
 elif face=='back':
  # Hands are on the far/front of torso; no linen drawn through the back.
  poly([(13,29+b),(17,29+b),(18,36+b),(16,40+b),(13,38+b)],C)
  poly([(30,29+b),(34,29+b),(35,38+b),(32,40+b),(30,36+b)],S)
  d.line([(14,37+b),(16,41+b)],fill=SK,width=2);d.line([(32,37+b),(33,41+b)],fill=SK,width=2)
 else:
  if face=='left':
   arm=[(22,29),(27,30),(28,37),(25,44),(17,48),(13,45),(21,40)]
   sleeve=[(22,28),(27,29),(28,35),(23,37),(20,34)]
   linen=[(5,40),(18,39),(24,43),(23,50),(4,50),(3,44)]
   crease=[(5,45),(22,45)];highlight=[(7,41),(17,41)]
  else:
   arm=[(21,29),(26,29),(28,34),(27,40),(35,44),(34,48),(24,45),(20,38)]
   sleeve=[(21,28),(26,29),(28,34),(24,37),(20,35)]
   linen=[(29,39),(42,40),(45,44),(44,50),(25,50),(24,43)]
   crease=[(26,45),(43,45)];highlight=[(30,41),(40,41)]
  poly([(x,y+b) for x,y in linen],'#ddd9b8');d.line([(x,y+b) for x,y in crease],fill='#aaa783');d.line([(x,y+b) for x,y in highlight],fill='#faf2d1')
  poly([(x,y+b) for x,y in arm],SK);poly([(x,y+b) for x,y in sleeve],C)
 im.alpha_composite(Image.open(REF/f'idle_{face}.png').convert('RGBA').crop((0,0,48,28)),(0,b))
 return im

def export():
 OUT.mkdir(exist_ok=True,parents=True)
 for face,keys in K.items():
  (OUT/f'carry_walk_{face}').mkdir(exist_ok=True)
  carry(face,keys[2]).save(OUT/f'carry_idle_{face}.png')
  for i,k in enumerate(keys):carry(face,k).save(OUT/f'carry_walk_{face}/frame_{i:02}.png')
 im=Image.open(SRC/'place_master.png').convert('RGBA');im.putalpha(im.getchannel('A').point(lambda a:255 if a>=190 else 0))
 crops=[]
 for i in range(12):
  col=i%4;row=i//4;p=im.crop((col*im.width//4,row*im.height//3,(col+1)*im.width//4,(row+1)*im.height//3));crops.append(p.crop(p.getbbox()))
 factor=68/crops[0].height;(OUT/'runner_place').mkdir(exist_ok=True)
 for i,p in enumerate(crops):
  p=p.resize((round(p.width*factor),round(p.height*factor)),Image.Resampling.NEAREST)
  # Retain fixed boot baseline, never independently stretch bending poses.
  boot_box=p.crop((0,p.height-4,p.width,p.height)).getbbox()
  boot_right=boot_box[2] if boot_box else p.width
  c=Image.new('RGBA',(128,128));c.alpha_composite(p,(78-boot_right,84-p.height));c.save(OUT/f'runner_place/frame_{i:02}.png')
if __name__=='__main__':export()
