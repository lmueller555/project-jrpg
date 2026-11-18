"""Complete named pose drawings from explicit compatible native contour guides.
No old pixels are stretched; no procedural skeletal transform is performed.
"""
from PIL import Image,ImageDraw,ImageFilter
from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parents[5]
NAME=Path(__file__).resolve().parent.name
SOURCE=Path(__file__).parent
OUT=ROOT/'assets/characters/named_hd'/NAME
DATA=json.loads((SOURCE/'pose_contours.json').read_text())
O='#24211e';BLUE='#535d6c';BLUES='#343b4b';BLUEH='#748091'
SKIN='#c48f61';SKINH='#e0b17f';SKINS='#996945'
APRON='#cbbc98';APS='#9c896b';APH='#e0d2ad'
PLUM='#744a57';PLUMS='#53303e';PLUMH='#956772';SAGE='#777b54';SAGES='#52563b';SAGEH='#999c70'
PHASES=['right_contact','right_down','left_passing','left_recovery','left_contact','left_down','right_passing','right_recovery']
def draw_halden(k,face,i):
 im=Image.new('RGBA',(48,72));d=ImageDraw.Draw(im);b=k['b']
 def poly(pts,c):d.polygon([tuple(p) for p in pts],fill=c,outline=O)
 def leg(key,color):
  mask=Image.new('L',(48,72));q=ImageDraw.Draw(mask);q.polygon([tuple(p) for p in k[key]],fill=255)
  if 'calf'+key in k:q.polygon([tuple(p) for p in k['calf'+key]],fill=255)
  im.paste(O,(0,0),mask);im.paste(color,(0,0),mask.filter(ImageFilter.MinFilter(3)))
 def arm(s,h):
  # Complete contiguous forearm silhouette, sleeve rolls at natural elbow.
  mask=Image.new('L',(48,72));q=ImageDraw.Draw(mask);q.polygon([tuple(p) for p in s],fill=255);q.polygon([tuple(p) for p in h],fill=255)
  im.paste(O,(0,0),mask);inner=mask.filter(ImageFilter.MinFilter(3));im.paste(SKIN,(0,0),inner)
  sleeve=inner.copy();ImageDraw.Draw(sleeve).rectangle((0,30+b,47,71),fill=0);im.paste(BLUE,(0,0),sleeve)
  d.line([tuple(p) for p in s[1:4]],fill=BLUEH);d.line([tuple(p) for p in h[1:3]],fill=SKINH)
 for key,c in [('L','#514031'),('R','#67513c')]:leg(key,c)
 for key,c in [('lb','#352e28'),('rb','#45392f')]:poly(k[key],c);d.line([tuple(p) for p in k[key][1:4]],fill='#75604b')
 if face in ['front','back']:
  poly([(17,16+b),(30,16+b),(34,21+b),(32,35+b),(31,39+b),(16,39+b),(14,32+b),(13,22+b)],BLUE)
  d.line([(17,22+b),(18,33+b)],fill=BLUEH);d.line([(30,22+b),(30,34+b)],fill=BLUES)
  arm(k['sr'],k['hr']);arm(k['sl'],k['hl'])
  if face=='front':
   poly([(18,23+b),(29,23+b),(31,35+b),(32,49+b),(30,54+b),(17,54+b),(15,50+b),(17,35+b)],APRON)
   d.line([(18,19+b),(18,26+b)],fill=APH,width=2);d.line([(29,19+b),(29,26+b)],fill=APH,width=2)
   d.line([(17,36+b),(30,36+b)],fill=APS);d.line([(19,39+b),(18,50+b)],fill=APH);d.line([(27,39+b),(28,51+b)],fill=APS)
   d.line([(18,52+b),(30,52+b)],fill=APS);d.line([(20,27+b),(27,27+b),(27,32+b),(20,32+b)],fill=APS)
  else:
   for x in [18,29]:d.line([(x,18+b),(x,35+b)],fill=APRON,width=2)
   d.line([(16,36+b),(32,36+b)],fill=APRON,width=2)
   poly([(24,36+b),(18,38+b),(19,41+b),(24,38+b),(29,41+b),(30,38+b)],APRON)
   d.line([(24,38+b),(21,49+b)],fill=APRON,width=2);d.line([(25,38+b),(28,48+b)],fill=APS,width=2)
 else:
  # Own facing source drives head and apron orientation; no finished-pixel mirroring.
  arm(k['f'],k['fh'])
  poly([(20,17+b),(27,17+b),(29,23+b),(29,35+b),(28,39+b),(18,39+b),(17,29+b),(18,22+b)],BLUE)
  if face=='right':
   poly([(27,22+b),(30,22+b),(31,35+b),(33,51+b),(29,54+b),(24,53+b),(25,37+b)],APRON)
   d.line([(28,18+b),(28,25+b)],fill=APH,width=2);d.line([(28,40+b),(29,51+b)],fill=APS)
   d.line([(18,36+b),(31,36+b)],fill=APRON);d.line([(18,37+b),(16,46+b)],fill=APRON,width=2)
  else:
   poly([(18,22+b),(21,22+b),(22,37+b),(23,53+b),(18,54+b),(14,51+b),(17,35+b)],APRON)
   d.line([(19,18+b),(19,25+b)],fill=APH,width=2);d.line([(18,40+b),(17,51+b)],fill=APS)
   d.line([(17,36+b),(29,36+b)],fill=APRON);d.line([(29,37+b),(31,46+b)],fill=APRON,width=2)
  arm(k['s'],k['h'])
 head=Image.open(OUT/f'idle_{face}.png').convert('RGBA').crop((0,0,48,19));im.alpha_composite(head,(0,b))
 return im

def draw_elira(k,face,i):
 im=Image.new('RGBA',(48,72));d=ImageDraw.Draw(im);b=k['bob']
 def poly(pts,c,outline=O):d.polygon([tuple(p) for p in pts],fill=c,outline=outline)
 def arm(key):
  pts=k[key];poly(pts,PLUM);d.line([tuple(p) for p in pts[1:4]],fill=PLUMH)
  # Four-pixel hand tips follow the authored complete wrist, not a pivoted limb.
  mask=Image.new('L',(48,72));md=ImageDraw.Draw(mask);md.polygon([tuple(p) for p in pts],fill=255)
  y=max(p[1] for p in pts)-4
  md.rectangle((0,0,47,y-1),fill=0);im.paste(SKIN,(0,0),mask.filter(ImageFilter.MinFilter(3)))
 for key in ['fb','nb','lb','rb']:
  if key in k:poly(k[key],'#49392e');d.line([tuple(p) for p in k[key][1:4]],fill='#735d46')
 if face in ['left','right']:arm('fa')
 poly(k['dress'],PLUM)
 # Fine vertical cloth folds; separate from outer silhouette contour.
 dressmask=Image.new('L',(48,72));ImageDraw.Draw(dressmask).polygon([tuple(p) for p in k['dress']],fill=255)
 fold=Image.new('RGBA',(48,72));fd=ImageDraw.Draw(fold)
 for x,c in [(18,PLUMH),(23,PLUMS),(29,PLUMH)]:fd.line([(x,38+b),(x-1,58)],fill=c,width=1)
 im.alpha_composite(Image.composite(fold,Image.new('RGBA',im.size),dressmask))
 if face=='front':
  poly([(18,31+b),(29,31+b),(32,46+b),(32,57),(16,57),(15,47+b)],APRON)
  d.line([(18,36+b),(30,36+b)],fill=APS);d.line([(18,39+b),(17,54)],fill=APH);d.line([(27,39+b),(29,54)],fill=APS);d.line([(17,55),(30,55)],fill=APS)
  arm('ra');arm('la')
 elif face=='back':
  d.line([(16,34+b),(31,34+b)],fill=APRON,width=2);poly([(23,34+b),(19,36+b),(20,39+b),(24,36+b),(29,39+b),(29,36+b)],APRON)
  d.line([(23,37+b),(21,48+b)],fill=APRON,width=2);d.line([(25,37+b),(28,47+b)],fill=APS,width=2);arm('ra');arm('la')
 else:
  if face=='right':
   poly([(29,31+b),(33,33+b),(34,45+b),(34,56),(28,57),(27,46+b)],APRON)
   d.line([(30,38+b),(31,53)],fill=APH);d.line([(19,34+b),(33,34+b)],fill=APRON);d.line([(19,35+b),(17,47+b)],fill=APRON,width=2)
  else:
   poly([(15,33+b),(19,31+b),(21,46+b),(20,57),(14,56),(14,45+b)],APRON)
   d.line([(17,38+b),(16,53)],fill=APH);d.line([(14,34+b),(29,34+b)],fill=APRON);d.line([(29,35+b),(31,47+b)],fill=APRON,width=2)
  arm('na')
 # Named source has her face, low bun, short green shawl, and upper apron.
 # Only upper costume is preserved; old idle forearms are below this boundary.
 head=Image.open(OUT/f'idle_{face}.png').convert('RGBA').crop((0,0,48,31));im.alpha_composite(head,(0,b))
 return im

def cloth_detail(im,face,b):
 # Preserve source-native material clusters only within newly drawn matching cloth.
 # This is texture registration, not whole-idle warping or limb manufacture.
 ref=Image.open(OUT/f'idle_{face}.png').convert('RGBA')
 linen={tuple(bytes.fromhex(c[1:])) for c in [APRON,APS,APH]}
 blue={tuple(bytes.fromhex(c[1:])) for c in [BLUE,BLUES,BLUEH]}
 plum={tuple(bytes.fromhex(c[1:])) for c in [PLUM,PLUMS,PLUMH]}
 for y in range(20,59):
  for x in range(12,36):
   dst=im.getpixel((x,y));src=ref.getpixel((x,y-b));r,g,bb,aa=src
   if aa!=255:continue
   fabric=((dst[:3] in linen and r>125 and g>110 and bb>65 and r>=g>=bb and r-bb<95)
     or (NAME=='halden' and dst[:3] in blue and bb>=r and bb>=g and bb-r<70)
     or (NAME=='elira' and dst[:3] in plum and r>g and bb>g and r-g<85))
   if fabric:im.putpixel((x,y),src)
 return im

for face,keys in DATA['directions'].items():
 folder=OUT/f'walk_{face}';folder.mkdir(parents=True,exist_ok=True);master=Image.new('RGBA',(384,72));frames=[]
 for i,k in enumerate(keys):
  im=(draw_halden if NAME=='halden' else draw_elira)(k,face,i);im=cloth_detail(im,face,k.get('b',k.get('bob')));fn=f'frame_{i+1:02}.png';im.save(folder/fn);master.alpha_composite(im,(48*i,0));frames.append({'file':fn,'duration_ms':70,'phase':PHASES[i],'rect':[48*i,0,48,72]})
 master.save(folder/'spritesheet.png');master.save(SOURCE/f'walk_{face}_master.png')
 meta={'version':1,'character':NAME,'animation':'walk.'+face,'frame_size':[48,72],'logical_size':[24,36],'artwork_pixels_per_world_pixel':2,'draw_anchor':[24,60],'foot_anchor':[24,69],'loop':True,'cycle_ms':560,'spritesheet':'spritesheet.png','frames':frames,'source':f'assets/source/characters/named_hd/{NAME}/walk_{face}_master.png'}
 (folder/'animation.json').write_text(json.dumps(meta,indent=2)+'\n')
 ims=[Image.open(folder/f['file']) for f in frames]
 for fn,factor,duration in [('normal.gif',2,70),('half_speed.gif',4,140)]:
  bg=[]
  for im in ims:
   pic=Image.new('RGBA',im.size,'#65705d');pic.alpha_composite(im);bg.append(pic.convert('RGB').resize((48*factor,72*factor),Image.Resampling.NEAREST))
  bg[0].save(folder/fn,save_all=True,append_images=bg[1:],duration=duration,loop=0,disposal=2)
