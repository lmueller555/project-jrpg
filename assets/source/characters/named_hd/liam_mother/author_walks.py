"""Complete native drawings for Liam's mother in her own braid/dress/apron.
Eight distinct complete-pose contours per direction, not a joint-based rig.
Head/braid are protected canonical appearance, not substituted generic art.
"""
from PIL import Image,ImageDraw
from pathlib import Path
import json,hashlib,shutil
P=Path(__file__).parent
ROOT=next(p for p in P.parents if (p/'assets/characters').is_dir())
OUT=ROOT/'assets/characters/named_hd/liam_mother'
O='#1a0e16';C='#3e7778';S='#294f50';L='#6aa0a0';SK='#e8c49d';SH='#eda052';B='#84512e';BL='#9d6238'
AP=[
[(18,43),(28,43),(31,56),(30,60),(16,60),(16,57)],
[(18,44),(28,44),(31,57),(29,61),(16,61),(16,57)],
[(19,43),(28,43),(30,56),(29,60),(17,60),(17,56)],
[(19,42),(28,42),(31,56),(30,60),(17,60),(17,55)],
[(19,43),(28,43),(31,57),(31,61),(17,60),(17,55)],
[(19,44),(28,44),(30,57),(30,61),(17,60),(17,56)],
[(18,43),(28,43),(30,56),(29,60),(16,60),(16,56)],
[(18,42),(28,42),(30,55),(29,60),(16,60),(16,56)]]
def draw(d,k,i,I):
 im=Image.new('RGBA',(48,72));dr=ImageDraw.Draw(im);b=k['bob']
 def poly(key,c):dr.polygon(k[key],fill=c,outline=O)
 side=d in ('left','right')
 if not side:
  for key in ('lb','rb'):poly(key,B);dr.line(k[key][1:4],fill=BL)
  for key in ('la','ra'):
   poly(key,C)
   # Long fitted sleeve ends at the actual hand, not bare forearm.
   pts=k[key];bottom=max(y for x,y in pts)
   mask=Image.new('RGBA',(48,72));md=ImageDraw.Draw(mask)
   md.polygon(pts,fill=SK,outline=O)
   im.alpha_composite(mask.crop((0,bottom-3,48,bottom+1)),(0,bottom-3))
  poly('dress',C);dr.polygon(k['foldlight'],fill=L);dr.polygon(k['foldshade'],fill=S)
  if d=='front':
   dr.polygon(AP[i],fill='#ded1ae',outline='#bcae91')
   dr.line([(21,45+b),(20,55),(19,58)],fill='#fbeed0')
   dr.line([(26,46+b),(28,56),(27,59)],fill='#bcae91')
  else:dr.line([(20,44+b),(18,56),(17,61)],fill=S)
  dr.line([(17,41+b),(30,41+b)],fill='#ded1ae',width=2)
  im.alpha_composite(I.crop((18,28,30,39)),(18,28+b))
 else:
  for key in ('fb','nb'):poly(key,B);dr.line(k[key][1:4],fill=BL)
  poly('fa',S);poly('fh',SH);poly('dress',C);dr.polygon(k['fold'],fill=L)
  # Own front apron wraps around the forward-facing edge, never around back.
  apron=[(26,42+b),(29,43+b),(32,57),(30,60),(25,59),(24,49)] if d=='right' else [(21,42+b),(18,43+b),(15,57),(17,60),(22,59),(23,49)]
  dr.polygon(apron,fill='#ded1ae',outline='#bcae91')
  dr.line([(26 if d=='right' else 21,46+b),(28 if d=='right' else 19,57)],fill='#fbeed0')
  dr.line([(19,41+b),(28,41+b)],fill='#ded1ae',width=2)
  poly('na',C);dr.line(k['na'][1:4],fill=L);poly('nh',SK)
 im.alpha_composite(I.crop((0,0,48,28)),(0,b))
 # The original braid is physically on her right. Retain only hair material,
 # preserving differing visibility in each authored directional source.
 hair={tuple(bytes.fromhex(x[1:]))+(255,) for x in ['#3d2118','#71452c','#a47545']}
 for y in range(28,44):
  for x in range(48):
   if I.getpixel((x,y)) in hair:im.putpixel((x,y+b),I.getpixel((x,y)))
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
 manifest={'version':1,'character':'liam_mother','animation':f'walk.{d}','artwork_pixels_per_world_pixel':2,'frame_size':[48,72],'logical_size':[24,36],'draw_anchor':[24,60],'foot_anchor':[24,69],'cycle_ms':560,'loop':True,'spritesheet':'spritesheet.png','source':(P/f'walk_{d}_master.png').relative_to(ROOT).as_posix(),'frames':records}
 (folder/'animation.json').write_text(json.dumps(manifest,indent=2)+'\n')
 frames[0].save(folder/'normal.gif',save_all=True,append_images=frames[1:],duration=70,loop=0,disposal=2)
 enlarged=[im.resize((192,288),Image.Resampling.NEAREST) for im in frames]
 enlarged[0].save(folder/'half_speed.gif',save_all=True,append_images=enlarged[1:],duration=140,loop=0,disposal=2)
 board=Image.new('RGB',(864,144),'#56615a');idle=Image.open(OUT/f'idle_{d}.png');board.paste(idle.resize((96,144),Image.Resampling.NEAREST),(0,0),idle.resize((96,144),Image.Resampling.NEAREST))
 for i,im in enumerate(frames):
  tile=im.resize((96,144),Image.Resampling.NEAREST);board.paste(tile,((i+1)*96,0),tile)
 board.save(folder/'review.png')
if __name__=='__main__':build()
