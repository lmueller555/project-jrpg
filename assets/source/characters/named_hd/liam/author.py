"""Liam's original cocoa forelock, ochre tunic and teal scarf at native scale."""
from pathlib import Path
import sys
from PIL import Image, ImageDraw
root=Path(sys.argv[1]); out=Path(sys.argv[2])
out.mkdir(parents=True,exist_ok=True)
ink='#281d23'; deep='#49302b'; mid='#704c35'; light='#9e7145'; high='#c1935e'
skin='#f0b87e'; shade='#c78053'; sheen='#ffd39d'; eye='#252b2b'; neck='#357381'; necklight='#659995'
cloth='#c69232'; clothhi='#deb454'; clsh='#936822'; outline='#35281f'
pants='#474043'; pantslit='#645354'; boot='#724a35'; bootlite='#9b6847'
D=('front','back','left','right')

def load(p):return Image.open(root/p).convert('RGBA')

def head(direction):
 im=Image.new('RGBA',(48,72)); d=ImageDraw.Draw(im)
 def p(x,k):d.polygon(x,fill=k)
 if direction in ('front','back'):
  p([(19,20),(23,18),(27,18),(28,20),(32,21),(34,25),(35,30),(32,34),(31,38),(27,41),(20,41),(17,38),(15,34),(15,26),(17,22)],ink)
  p([(20,21),(24,19),(27,20),(31,22),(33,26),(33,32),(30,36),(28,37),(20,36),(17,32),(17,26)],deep)
  p([(19,23),(24,20),(27,21),(30,23),(31,27),(30,32),(27,34),(22,36),(18,32),(17,28)],mid)
  p([(18,25),(22,22),(27,22),(29,24),(25,24),(23,28),(20,27),(18,30)],light)
  d.line([(21,24),(24,22),(27,23)],fill=high,width=1)
  p([(30,21),(33,24),(34,27),(32,25)],light)
  if direction=='front':
   p([(17,32),(19,33),(20,30),(24,29),(27,26),(27,29),(32,31),(32,35),(31,38),(27,40),(22,40),(19,38)],skin)
   p([(19,34),(21,36),(22,39),(27,40),(23,40),(20,38)],shade)
   d.line([(24,31),(27,30),(30,32)],fill=sheen)
   d.point((22,34),fill=eye);d.point((29,34),fill=eye);d.point((27,36),fill=shade)
   d.line((24,38,27,38),fill=shade)
  else:
   p([(17,30),(19,31),(22,35),(27,35),(31,32),(33,29),(32,35),(30,38),(27,39),(20,38),(17,35)],mid)
   d.line([(20,29),(22,33),(24,34)],fill=light);d.line([(31,26),(29,31),(27,32)],fill=light)
   d.line((23,39,27,39),fill=shade)
 else:
  p([(22,19),(27,18),(30,20),(33,21),(35,24),(36,28),(34,34),(31,36),(29,38),(27,40),(20,40),(18,37),(16,37),(16,34),(15,33),(17,29),(19,24)],ink)
  p([(23,20),(27,19),(30,21),(33,23),(34,27),(33,32),(30,35),(27,37),(21,35),(18,34),(18,29),(20,25)],deep)
  p([(22,21),(28,20),(31,23),(32,27),(30,31),(27,33),(20,34),(18,31),(20,25)],mid)
  p([(21,24),(24,22),(29,22),(30,24),(25,24),(23,27),(19,28)],light)
  d.line((24,22,28,22),fill=high)
  p([(19,29),(23,28),(25,26),(26,27),(24,31),(26,33),(24,37),(27,38),(23,39),(20,38),(20,36),(17,35),(18,33)],skin)
  d.line((20,36,22,38),fill=shade);d.point((20,32),fill=eye);d.point((18,34),fill=sheen)
  if direction=='right':im=im.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
 return im

def body(direction):
 im=Image.new('RGBA',(48,72)); d=ImageDraw.Draw(im)
 def p(x,k):d.polygon(x,fill=k,outline=ink)
 if direction in ('front','back'):
  p([(16,52),(24,52),(24,64),(22,67),(16,67)],pants)
  p([(24,52),(32,52),(32,67),(26,67),(24,63)],pantslit)
  p([(17,63),(22,63),(23,68),(15,68),(15,65)],boot)
  p([(27,63),(32,63),(33,65),(33,68),(25,68)],boot)
  d.line((16,66,20,66),fill=bootlite);d.line((29,66,32,66),fill=bootlite)
  p([(20,39),(28,39),(32,42),(34,49),(32,53),(31,57),(16,57),(16,54),(13,52),(14,45),(16,42)],cloth)
  d.polygon([(28,42),(31,43),(32,47),(30,49),(30,55),(27,56)],fill=clsh)
  d.line((18,45,18,53),fill=clothhi)
  p([(14,48),(17,49),(17,53),(15,54),(13,52)],skin)
  p([(31,49),(34,48),(34,52),(33,54),(31,54)],shade)
  p([(20,39),(28,39),(29,41),(26,44),(21,43),(19,42)],neck)
  d.line((21,40,27,40),fill=necklight)
  if direction=='front':
   d.rectangle((22,48,23,50),fill=clsh);d.point((22,48),fill=clothhi)
  else:d.line((22,45,22,54),fill=clsh)
 else:
  p([(22,52),(27,52),(27,64),(25,67),(21,67)],pantslit)
  p([(25,53),(31,53),(31,65),(30,67),(25,67)],pants)
  p([(20,64),(26,64),(27,67),(26,68),(18,68),(18,66)],boot)
  p([(26,64),(30,64),(31,67),(31,68),(24,68)],boot)
  p([(22,39),(27,39),(30,43),(31,52),(28,57),(20,57),(20,53),(19,50),(20,44)],cloth)
  d.polygon([(28,43),(30,44),(30,52),(27,55),(26,49)],fill=clsh)
  d.line((21,44,22,47),fill=clothhi)
  p([(23,49),(26,49),(26,53),(25,55),(23,54)],skin)
  p([(21,39),(27,39),(28,40),(24,43),(20,42)],neck)
  d.line((22,40,25,40),fill=necklight)
  if direction=='right':im=im.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
 return im

if __name__=='__main__':
 for face in D:
  im=body(face);im.alpha_composite(head(face));im.save(out/f'idle_{face}.png')

# Phase-compatible approved child silhouette guide at identical native height.
# Liam's head, neckwear and mid-tunic decoration are independently painted.
from PIL import ImageColor
import json, shutil, hashlib
colors={
'241f20':ink, '57735a':cloth,'82a06f':clothhi,'384b3f':clsh,'afbe8a':'#e6bd62',
'75644b':pants, 'a08b65':pantslit,'624634':boot,'9b7650':bootlite,
'4c382e':'#4c3029','5d4231':boot,'94714b':bootlite,
'c89375':skin,'ce8462':shade,'ffdab4':sheen,
}
palette={tuple(bytes.fromhex(k)):ImageColor.getrgb(v) for k,v in colors.items()}

def walk(face,i):
 file=f'assets/characters/npc_roster_hd/child_boy_04/walk_{face}/frame_{i+1:02}.png'
 guide=load(file)
 dy=guide.getbbox()[1]-18
 im=Image.new('RGBA',(48,72)); src=guide.load();a=im.load()
 for y in range(39+dy,72):
  for x in range(48):
   col=src[x,y]
   if col[3]:
    if col[:3] in palette:a[x,y]=(*palette[col[:3]],255)
    elif y>=42+dy:a[x,y]=(*ImageColor.getrgb(neck if y<46+dy else cloth),255)
 layer=Image.new('RGBA',(48,72)); d=ImageDraw.Draw(layer)
 xc=23
 if face in ('front','back'):
  d.polygon([(17,50+dy),(31,50+dy),(31,56+dy),(17,56+dy)],fill=cloth,outline=ink)
  d.line((18,51+dy,18,55+dy),fill=clothhi);d.line((30,51+dy,30,55+dy),fill=clsh)
  if face=='front':d.rectangle((21,53+dy,22,54+dy),fill=clsh)
  d.polygon([(19,39+dy),(28,39+dy),(29,42+dy),(24,44+dy),(19,42+dy)],fill=neck,outline=ink)
  d.line((21,41+dy,26,41+dy),fill=necklight)
 else:
  front,back=(19,29) if face=='left' else (18,28)
  d.polygon([(front,40+dy),(back,40+dy),(back,41+dy),(front+4,44+dy),(front,43+dy)],fill=neck,outline=ink)
  d.line((front+2,42+dy,front+4,42+dy),fill=necklight)
  d.line((23,54+dy,26,55+dy),fill=clsh)
 im.alpha_composite(layer)
 im.alpha_composite(head(face),(0,dy))
 # Shift the foot only if cropped beyond the canonical native sole 68.
 d=ImageDraw.Draw(im);d.rectangle((0,69,47,71),fill=(0,0,0,0))
 return im,file

# These independent silhouette outlines are running stances, not a faster walk.
# Three-quarter leg compression, airborne pass, opposing elbows and lead/trail.
profile_runs=(
 (((26,51),(31,56),(34,63),(32,66),(29,65),(26,60),(23,57)),
  ((22,51),(24,56),(18,61),(15,66),(10,67),(9,65),(13,62),(16,57)),0),
 (((25,50),(31,55),(35,57),(35,60),(30,62),(25,58),(22,55)),
  ((22,50),(26,52),(23,56),(21,59),(23,63),(19,64),(17,59),(17,56)),-2),
 (((23,51),(24,56),(18,61),(15,66),(10,67),(9,65),(13,62),(16,57)),
  ((27,51),(31,56),(34,63),(32,66),(29,65),(26,60),(23,57)),0),
 (((22,50),(25,52),(23,56),(21,59),(23,63),(19,64),(17,59),(17,56)),
  ((25,50),(31,55),(35,57),(35,60),(30,62),(25,58),(22,55)),-2),
)
axial_runs=(
 (((25,52),(31,52),(30,57),(27,58),(28,61),(25,62),(24,58)),
  ((16,52),(23,52),(23,61),(21,68),(15,68),(16,60)),0),
 (((24,51),(30,51),(30,56),(28,58),(29,62),(25,62),(23,56)),
  ((16,51),(22,51),(24,55),(23,58),(20,62),(17,61),(18,56)),-2),
 (((16,52),(22,52),(23,58),(22,62),(19,61),(20,58),(17,57)),
  ((25,52),(32,52),(32,60),(33,68),(27,68),(25,62)),0),
 (((16,51),(22,51),(23,56),(22,62),(18,62),(19,58),(16,56)),
  ((25,51),(31,51),(30,56),(30,61),(27,62),(24,58),(24,55)),-2),
)

def run(face,i):
 profile=face in ('left','right'); far,near,bob=(profile_runs if profile else axial_runs)[i]
 if face=='right':
  far=tuple((47-x,y) for x,y in far);near=tuple((47-x,y) for x,y in near)
 base,_=walk(face,0 if i<2 else 4)
 torso=base.crop((0,18,48,57))
 im=Image.new('RGBA',(48,72));d=ImageDraw.Draw(im)
 for pts,c in ((far,pants),(near,pantslit)):
  d.polygon(pts,fill=c,outline=ink)
  foot=pts[3:6]
  d.line(foot,fill=boot,width=2)
 im.alpha_composite(torso,(0,18+bob))
 # Distinct compact running fists read at the edges, not clipped walking cuffs.
 d=ImageDraw.Draw(im)
 if profile:
  x=(15 if i<2 else 33) if face=='left' else (32 if i<2 else 14)
  p=((x,46+bob),(x+3,45+bob),(x+5,47+bob),(x+4,50+bob),(x+1,49+bob))
  d.polygon(p,fill=skin,outline=ink)
 return im

def export_motions():
 for f in D:
  for verb,n,ms in (('walk',8,70),('run',4,100)):
   folder=out/f'{verb}_{f}';folder.mkdir(exist_ok=True)
   frames=[]
   for i in range(n):
    im,guide=walk(f,i) if verb=='walk' else (run(f,i),None)
    name=f'frame_{i+1:02}.png';im.save(folder/name)
    record={'file':name,'duration_ms':ms,'bounds':im.getbbox()}
    if guide:record['approved_motion_guide']=guide
    frames.append(record)
   data={'character':'liam','animation':f'{verb}.{f}','artwork_pixels_per_world_pixel':2,
         'frame_size':[48,72],'logical_size':[24,36],'draw_anchor':[24,60],
         'foot_anchor':[24,68],'loop':True,'cycle_ms':n*ms,'frames':frames}
   (folder/'animation.json').write_text(json.dumps(data,indent=2)+'\n')
 portrait=root/'assets/portraits/eldenmere/liam_neutral.png'
 shutil.copyfile(portrait,out/'portrait.png')
 data={'id':'liam','display_name':'Liam','age_years':8,'artwork_pixels_per_world_pixel':2,
       'logical_size':[24,36],'draw_anchor':[12,30],'foot_anchor':[12,34],
       'frames':{d:f'idle_{d}.png' for d in D},'portrait':'portrait.png',
       'portrait_sha256':hashlib.sha256(portrait.read_bytes()).hexdigest(),
       'status':'integrated'}
 (out/'design.json').write_text(json.dumps(data,indent=2)+'\n')

if __name__=='__main__':export_motions()
