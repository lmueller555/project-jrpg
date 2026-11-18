"""Eight complete native directional poses for Liam's father.
Own source head and collar, clay tunic, ivory sleeves and low waist. Compatible
approved full-pose motion contours retained as explicit per-frame source, with
new named costume drawings; no idle deformation or finished-image reflection.
"""
from PIL import Image,ImageDraw
from pathlib import Path
import json,hashlib
P=Path(__file__).parent
ROOT=next(p for p in P.parents if (p/'assets/characters').is_dir())
OUT=ROOT/'assets/characters/named_hd/liam_father'
O='#1a0e16';G='#a6523b';GS='#803d31';GL='#ca7c50'
T='#51413b';TS='#352a29';TL='#746050';B='#84512e';BL='#9d6238';SK='#e8c49d'
def draw(d,k,i,I):
 im=Image.new('RGBA',(48,72));dr=ImageDraw.Draw(im);b=k['bob']
 def poly(key,c):dr.polygon(k[key],fill=c,outline=O)
 side=d in ('left','right')
 if not side:
  for key,c in [('left',T),('right',TS),('lb',B),('rb',B)]:poly(key,c)
  for key in ('la','ra'):
   poly(key,'#ded1ae')
   dr.line(k[key][1:4],fill='#fbeed0')
  # Hands extend only beyond ivory cuff, not as long bare forearms.
  for key in ('lh','rh'):
   pts=k[key];bottom=max(y for x,y in pts)
   skin=Image.new('RGBA',(48,72));ImageDraw.Draw(skin).polygon(pts,fill=SK,outline=O)
   im.alpha_composite(skin.crop((0,bottom-3,48,bottom+1)),(0,bottom-3))
  torso=[(15,27+b),(21,25+b),(28,25+b),(33,28+b),(35,34+b),(32,38+b),(31,51+b),(26,52+b),(23,50+b),(16,51+b),(15,38+b),(12,34+b)]
  dr.polygon(torso,fill=G,outline=O)
  dr.polygon([(28,29+b),(32,31+b),(31,43+b),(30,50+b),(27,50+b),(26,32+b)],fill=GS)
  dr.line([(18,32+b),(18,41+b)],fill=GL)
  dr.line([(16,45+b),(31,45+b)],fill='#3d2118',width=2)
  dr.line([(17,44+b),(30,44+b)],fill='#84512e')
  if d=='front':
   dr.rectangle((23,44+b,26,46+b),fill='#b99b55');dr.point((24,45+b),fill='#3d2118')
   im.alpha_composite(I.crop((19,26,29,35)),(19,26+b))
  else:
   dr.line([(23,28+b),(23,40+b)],fill=GS);dr.line([(18,48+b),(29,48+b)],fill=GL)
  for key in ('lb','rb'):dr.line(k[key][1:4],fill=BL)
  for key in ('left','right'):dr.line(k[key][1:4],fill=TL)
 else:
  for key,c in [('fl',TS),('fb',B),('fa','#ded1ae'),('fh',SK),('nl',T),('nb',B)]:poly(key,c)
  # Longer hip-length shirt is reconstructed at the father's own waist.
  co=[(19,27+b),(26,26+b),(30,30+b),(29,38+b),(30,48+b),(27,52+b),(18,51+b),(17,44+b),(17,33+b)]
  if d=='left':co=[(47-x,y) for x,y in co]
  dr.polygon(co,fill=G,outline=O)
  dr.line([(20,32+b),(21,41+b)],fill=GL)
  dr.line([(19,45+b),(28,45+b)],fill='#3d2118',width=2)
  dr.line([(19,44+b),(28,44+b)],fill='#84512e')
  poly('na','#ded1ae');dr.line(k['na'][1:4],fill='#fbeed0');poly('nh',SK)
  # Short clay shoulder cover over the full ivory sleeve.
  shoulder=k['na'][:3]+[k['na'][-1]]
  dr.polygon(shoulder,fill=G,outline=O);dr.line(shoulder[1:3],fill=GL)
  for key in ('nb','fb'):dr.line(k[key][1:4],fill=BL)
  dr.line(k['nl'][1:4],fill=TL)
 im.alpha_composite(I.crop((0,0,48,28)),(0,b))
 return im
def build():
 for d in ('front','back','left','right'):
  data=json.loads((P/f'poses_{d}.json').read_text());I=Image.open(OUT/f'idle_{d}.png')
  frames=[draw(d,k,i,I) for i,k in enumerate(data['K'])]
  export(d,frames,data)
def export(d,frames,data):
 folder=OUT/f'walk_{d}';folder.mkdir(parents=True,exist_ok=True)
 sheet=Image.new('RGBA',(384,72));records=[]
 for i,(im,k) in enumerate(zip(frames,data['K'])):
  name=f'frame_{i+1:02}.png';im.save(folder/name);sheet.alpha_composite(im,(48*i,0))
  records.append({'file':name,'rect':[48*i,0,48,72],'duration_ms':70,'phase':k['phase'],'support_leg':k['support'],'bob_artwork_y':k['bob'],'sha256':hashlib.sha256((folder/name).read_bytes()).hexdigest()})
 sheet.save(folder/'spritesheet.png')
 sheet.save(P/f'walk_{d}_master.png')
 manifest={'version':1,'character':'liam_father','animation':f'walk.{d}','artwork_pixels_per_world_pixel':2,'frame_size':[48,72],'logical_size':[24,36],'draw_anchor':[24,60],'foot_anchor':[24,69],'cycle_ms':560,'loop':True,'spritesheet':'spritesheet.png','source':(P/f'walk_{d}_master.png').relative_to(ROOT).as_posix(),'frames':records}
 (folder/'animation.json').write_text(json.dumps(manifest,indent=2)+'\n')
 frames[0].save(folder/'normal.gif',save_all=True,append_images=frames[1:],duration=70,loop=0,disposal=2)
 enlarged=[im.resize((192,288),Image.Resampling.NEAREST) for im in frames]
 enlarged[0].save(folder/'half_speed.gif',save_all=True,append_images=enlarged[1:],duration=140,loop=0,disposal=2)
 board=Image.new('RGB',(864,144),'#56615a');idle=Image.open(OUT/f'idle_{d}.png');board.paste(idle.resize((96,144),Image.Resampling.NEAREST),(0,0),idle.resize((96,144),Image.Resampling.NEAREST))
 for i,im in enumerate(frames):
  tile=im.resize((96,144),Image.Resampling.NEAREST);board.paste(tile,((i+1)*96,0),tile)
 board.save(folder/'review.png')
if __name__=='__main__':build()
