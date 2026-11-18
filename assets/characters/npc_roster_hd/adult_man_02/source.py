"""Native 48x72 authored pixel geometry. No legacy sprite resampling.
Run python source.py [output-dir]; identical source copied beside each design.
"""
from PIL import Image, ImageDraw
from pathlib import Path
import json,shutil,sys,base64,io
BASE=next((p for p in Path(__file__).resolve().parents if (p/'assets/portraits/eldenmere').is_dir()),None)
O='#1a0e16'
def pal(a,b,c):return [a,b,c]
SK=pal('#edaf78','#e8c49d','#ffe0b5')
SPECS=[('adult_man_02', 'Bram', 'man', 'male_02', ['#242027', '#38343d', '#55515b'], ['#713d32', '#a65b45', '#cc8566'], ['#35343b', '#4b4952', '#716c76'], 'tousled')]

def sprite(s,v):
 id,name,gender,legacy,h,c,t,style=s
 sk=SK if legacy else (pal('#815139','#b77a56','#dba57a') if gender=='man' else pal('#664536','#a16e50','#c99670'))
 im=Image.new('RGBA',(48,72));d=ImageDraw.Draw(im)
 def p(points,col,outline=None):d.polygon(points,fill=col,outline=outline)
 def r(box,col):d.rectangle(box,fill=col)
 def line(points,col,w=1):d.line(points,fill=col,width=w)
 front=v=='front';back=v=='back';side=v in ('left','right')
 dress=gender=='woman' and t is None
 # Complete native directional silhouette; feet planted on y69.
 if not side:
  # Long back hair is behind the shoulders, never painted over a front face.
  if style=='bob':
   p([(13,12),(34,12),(36,26),(32,30),(16,30),(11,25)],O);p([(15,13),(32,13),(33,25),(29,28),(17,27),(13,24)],h[1])
  # Legs and footwear
  if not dress:
   p([(15,43),(32,43),(33,60),(32,66),(26,66),(24,50),(22,66),(15,66),(14,59)],O)
   p([(16,45),(23,45),(22,62),(16,62)],t[1]);p([(25,45),(31,45),(31,62),(26,62)],t[0])
   line([(18,49),(18,59)],t[2]);line([(27,49),(28,58)],t[1])
  for x in [15,26]:
   p([(x,61),(x+6,61),(x+7,66),(x+7,69),(x-2,69),(x-2,67)],O)
   r((x,62,x+5,66),'#714b34');r((x-1,67,x+6,68),'#98704c');line([(x,63),(x+5,63)],'#b38a58')
  # Hands beyond sleeve edges with real thumb clusters
  for x in [11,33]:
   p([(x,35),(x+3,35),(x+4,45),(x+2,48),(x-1,46)],O)
   r((x,37,x+2,45),sk[1]);r((x,45,x+1,46),sk[0]);d.point((x+2,40),fill=sk[2])
  # Body / skirt shape
  if dress:
   p([(16,25),(20,24),(27,24),(32,25),(35,31),(33,41),(30,43),(35,61),(32,64),(15,64),(12,61),(17,43),(14,40),(12,31)],O)
   p([(17,26),(29,26),(32,31),(30,40),(28,43),(32,61),(16,61),(20,43),(16,39),(14,32)],c[1])
   p([(28,28),(32,32),(29,42),(32,61),(28,61),(25,45)],c[0]);p([(18,44),(21,45),(19,60),(15,60)],c[2])
   line([(17,59),(30,59)],c[0]);line([(22,47),(22,58)],c[2]);line([(26,48),(28,58)],c[0])
  else:
   p([(16,25),(21,24),(27,24),(32,25),(35,30),(34,37),(31,39),(32,45),(26,47),(23,45),(16,46),(15,39),(12,37),(12,30)],O)
   p([(17,26),(30,26),(33,31),(31,37),(29,38),(30,44),(25,45),(23,43),(17,44),(17,37),(14,36),(14,31)],c[1])
   p([(28,27),(32,30),(31,35),(29,37),(29,43),(26,44),(26,31)],c[0]);line([(18,30),(18,39)],c[2]);line([(15,34),(17,35)],c[2]);line([(29,35),(32,34)],c[2])
  # garment construction and belt, coherent rear/front
  line([(18,41),(29,41)],'#59402b',2);line([(18,40),(29,40)],'#9f7a48')
  if front:
   r((23,40,26,42),'#d9b967');r((24,41,25,41),'#59402b')
   p([(19,25),(23,29),(21,32),(17,27)],c[2]);p([(27,25),(24,29),(26,32),(30,27)],c[0]);line([(24,30),(24,38)],c[0]);
   for y in [33,36]:d.point((25,y),fill=c[2])
  else:
   line([(23,28),(23,37)],c[0]);line([(19,28),(28,28)],c[2]);line([(18,43),(21,44)],c[2])
  # neck and head, defined ears and jaw
  r((21,20,27,26),O);r((22,21,26,26),sk[0]);r((23,22,25,25),sk[1])
  p([(16,9),(30,9),(33,14),(32,20),(28,24),(21,24),(16,20),(14,14)],O)
  p([(17,11),(29,11),(31,15),(30,20),(27,23),(22,23),(18,20),(16,15)],sk[1]);p([(28,13),(31,15),(30,20),(27,23),(26,22)],sk[0]);line([(19,19),(20,21)],sk[2])
  if front:
   r((18,15,20,17),O);r((27,15,29,17),O);d.point((19,15),fill='#fff1d7');d.point((28,15),fill='#fff1d7');line([(23,20),(25,20)],'#a56748');d.point((24,18),fill=sk[2])
  # hairstyle is independently drawn in front and rear
  if back:
   p([(15,5),(20,2),(26,2),(32,5),(35,12),(33,21),(30,25),(25,27),(18,25),(14,21),(12,12)],O)
   p([(16,6),(21,3),(26,3),(31,6),(33,12),(31,21),(27,24),(20,23),(16,20),(14,12)],h[1]);p([(28,6),(32,12),(30,21),(26,24),(25,20)],h[0]);line([(18,8),(16,14),(18,20)],h[2]);line([(23,5),(21,11)],h[2]);line([(26,12),(27,19)],h[2]);line([(21,17),(22,23)],h[0])
  else:
   p([(12,11),(14,6),(19,4),(21,2),(27,2),(30,5),(33,6),(35,12),(33,17),(30,15),(29,10),(26,12),(24,9),(21,13),(19,11),(16,17),(13,16)],O)
   p([(14,10),(16,6),(21,5),(22,3),(26,3),(29,6),(32,7),(33,12),(31,12),(28,8),(25,10),(24,6),(20,10),(18,9),(16,14),(14,14)],h[1]);line([(16,8),(21,6),(24,4)],h[2]);line([(26,5),(30,8),(31,10)],h[2]);line([(18,11),(20,8)],h[0])
  if style=='bob':
   for x in [13,31]:p([(x,14),(x+2,15),(x+2,24),(x+1,27),(x-1,24)],h[0]);line([(x,17),(x,23)],h[2])
  if style=='pony':
   # anatomical low tied tail behind right ear in front/rear
   p([(30,19),(34,20),(35,26),(33,31),(30,29),(31,24)],O);p([(31,21),(33,21),(33,27),(32,29)],h[1]);r((30,21,33,22),'#a27851')
  if style=='crop':
   line([(14,13),(15,19)],h[0],2);line([(31,11),(32,18)],h[0],2)
 else:
  # True right-facing profile, left face authored by mirrored geometry below.
  if style=='bob':p([(18,7),(29,8),(30,25),(25,29),(17,27),(14,22)],O)
  if style=='pony':p([(15,19),(19,20),(19,28),(16,32),(13,29),(14,24)],O);p([(15,22),(17,22),(16,29)],h[1]);r((15,21,18,22),'#a27851')
  # far leg, near leg
  p([(20,44),(29,44),(29,64),(32,67),(32,69),(21,69),(19,65)],O)
  if not dress:
   r((21,47,27,63),t[0]);r((23,49,27,61),t[1]);line([(24,49),(24,58)],t[2])
  p([(20,62),(28,62),(28,65),(32,67),(32,69),(20,69)],O);r((21,63,27,66),'#714b34');r((21,67,30,68),'#98704c');line([(22,64),(27,64)],'#b38a58')
  if dress:
   p([(20,26),(27,26),(30,31),(28,41),(31,62),(28,65),(16,64),(18,43),(16,32)],O)
   p([(21,27),(26,27),(28,32),(26,42),(28,62),(18,62),(21,43),(18,32)],c[1]);p([(19,44),(22,44),(21,61),(18,61)],c[2]);line([(25,47),(26,60)],c[0]);line([(18,60),(28,60)],c[0])
  else:
   p([(19,26),(27,26),(31,31),(29,39),(29,46),(18,46),(16,34)],O)
   p([(20,27),(26,27),(29,32),(27,39),(27,44),(19,44),(18,33)],c[1]);p([(19,29),(21,29),(20,39),(19,43)],c[2]);line([(25,29),(27,34)],c[0])
  line([(19,41),(27,41)],'#68442e',2);line([(20,40),(27,40)],'#b18e56')
  # near arm occludes shirt naturally
  p([(21,29),(25,29),(27,35),(26,39),(26,47),(23,49),(21,46),(22,38),(20,35)],O)
  p([(22,30),(24,30),(25,35),(24,38),(22,36)],c[1]);line([(22,31),(22,35)],c[2]);r((23,39,25,46),sk[1]);r((22,44,22,46),sk[0]);d.point((25,41),fill=sk[2])
  r((23,21,27,27),O);r((24,22,26,26),sk[0])
  p([(21,7),(29,8),(31,12),(31,15),(34,17),(33,19),(31,20),(30,23),(25,25),(21,21),(18,15)],O)
  p([(22,10),(28,10),(29,13),(29,16),(32,17),(31,18),(29,19),(29,22),(26,23),(23,20),(21,16)],sk[1]);p([(26,20),(29,19),(29,22),(26,23)],sk[0]);r((28,14,30,15),O);d.point((29,14),fill='#f8e4c3');line([(29,20),(31,20)],'#a56748')
  p([(16,5),(21,3),(23,2),(28,3),(31,6),(32,11),(30,13),(27,9),(25,12),(23,10),(23,17),(20,20),(17,18),(15,13)],O)
  p([(18,6),(23,4),(27,4),(30,7),(30,10),(27,7),(24,9),(22,8),(21,16),(19,17),(17,12)],h[1]);line([(19,7),(23,5),(27,5)],h[2]);line([(17,10),(18,14)],h[2]);p([(21,16),(23,15),(24,18),(23,20),(21,19)],sk[0]);d.point((22,17),fill=sk[1])
  if style=='bob':
   p([(16,11),(20,13),(21,22),(23,25),(20,28),(16,26),(14,21)],O);p([(16,14),(18,15),(19,23),(21,25),(18,26),(16,23)],h[1]);line([(16,17),(17,23)],h[2])
  # Far heel and toe separated by a depth row from the planted near sole.
  p([(28,63),(30,63),(31,64),(34,65),(34,67),(32,67),(31,66),(29,65)],O)
  line([(30,64),(32,65)],'#876449');line([(32,66),(33,66)],'#b28a5d')
  # Delicate profile seam and cuff; internal rather than black bar detailing.
  line([(24,51),(25,55)], t[2] if t else c[2]);d.point((26,58),fill=t[0] if t else c[0])
  line([(22,32),(23,34)],c[2]);d.point((24,36),fill=c[0])
  if v=='left':im=im.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
 # Native material accents, clipped by the existing silhouette.
 if not side:
  for xx,yy in [(19,34),(20,37),(28,33)]:
   if im.getpixel((xx,yy))[3]:d.point((xx,yy),fill=c[2])
  if not dress:
   line([(16,48),(17,52)],t[0]);line([(21,54),(20,57)],t[2]);line([(27,52),(28,54)],t[2]);line([(27,58),(30,59)],t[0])
   line([(16,60),(20,60)],t[0]);line([(27,60),(30,60)],t[2]);d.point((18,56),fill=t[0])
  for xx in [15,26]:
   line([(xx+1,65),(xx+4,65)],'#523727');d.point((xx+4,67),fill='#bc9562')
 return im

def portrait(s):
 # New portraits are independent native busts, not enlarged sprite crops.
 _,_,g,_,h,c,_,style=s;sk=pal('#815139','#b77a56','#dba57a') if g=='man' else pal('#664536','#a16e50','#c99670')
 im=Image.new('RGB',(72,72),'#203b35');d=ImageDraw.Draw(im)
 def p(x,col):d.polygon(x,fill=col)
 p([(1,72),(5,58),(23,49),(46,49),(65,58),(71,72)],O);p([(4,72),(8,60),(24,52),(46,52),(62,60),(67,72)],c[1]);p([(48,53),(61,60),(65,72),(50,72)],c[0]);p([(26,47),(26,57),(35,64),(45,55),(44,45)],O);p([(29,45),(29,56),(35,60),(41,54),(41,45)],sk[0]);p([(18,20),(23,10),(39,8),(52,19),(52,34),(47,45),(37,51),(29,49),(21,40)],O);p([(22,21),(27,14),(38,12),(47,20),(49,32),(45,42),(37,47),(30,46),(24,38)],sk[1]);p([(44,21),(49,25),(47,36),(43,43),(37,47),(36,44),(42,39)],sk[0]);d.line([(27,35),(29,39)],fill=sk[2],width=2)
 p([(17,30),(14,22),(17,12),(24,7),(31,3),(42,5),(49,10),(55,21),(52,29),(48,24),(43,16),(36,19),(34,14),(27,23),(24,21),(22,32)],O);p([(18,21),(20,14),(26,10),(32,6),(40,7),(47,12),(51,21),(48,19),(42,12),(35,16),(34,10),(27,19),(24,17),(20,27)],h[1]);d.line([(21,16),(28,12),(32,8)],fill=h[2],width=2);d.line([(39,9),(45,13),(48,18)],fill=h[2]);d.line([(26,28),(31,27)],fill=O);d.line([(40,27),(45,28)],fill=O);d.rectangle((28,29,30,32),fill=O);d.rectangle((41,29,43,32),fill=O);d.point((29,29),fill='#fff0ce');d.point((42,29),fill='#fff0ce');d.line([(34,38),(37,38)],fill=sk[0]);d.line([(33,42),(39,42)],fill='#6e4236');d.line([(24,56),(29,63),(33,61)],fill=c[2],width=2);d.line([(46,55),(42,62),(39,61)],fill=c[0],width=2)
 # Secondary facial planes, warm cheek and brow clusters at native resolution.
 p([(24,25),(27,23),(30,23),(29,26),(25,28)],'#cf9970' if g=='man' else '#b3815d')
 p([(25,33),(28,35),(29,38),(26,37)],'#c48c66' if g=='man' else '#aa7857')
 p([(37,34),(38,38),(36,40),(34,39)],'#9c654b' if g=='man' else '#89583f')
 d.line([(34,31),(33,36),(35,37)],fill='#d5a17a' if g=='man' else '#be906b')
 d.line([(31,43),(34,44),(38,44)],fill='#cf9874' if g=='man' else '#b88567')
 d.line([(29,40),(31,41)],fill='#ad7156' if g=='man' else '#945d48')
 d.line([(25,26),(29,25),(31,26)],fill='#4c3430');d.line([(40,25),(44,26)],fill='#4c3430')
 d.point((27,30),fill='#d7bd95');d.point((40,30),fill='#d7bd95')
 d.point((30,31),fill='#6b5040');d.point((43,31),fill='#6b5040')
 # Hair bundles retain their own highlight/shadow rhythm, not surface noise.
 for pts,col in [([(19,19),(22,15),(25,13)],h[2]), ([(26,15),(30,11),(32,8)],h[2]), ([(34,9),(38,9),(43,12)],h[2]), ([(21,21),(23,18)],h[0]), ([(29,18),(32,14)],h[0]), ([(41,15),(46,20)],h[0])]:d.line(pts,fill=col)
 d.line([(22,13),(26,11),(29,9)],fill='#7a8077' if g=='man' else '#bb8475')
 d.line([(40,10),(44,13)],fill='#858b7f' if g=='man' else '#c68e7b')
 # Layered collar edge, shoulder seams, quiet cloth light and folds.
 p([(7,61),(15,57),(19,59),(13,62),(10,69),(6,70)],c[2]);p([(51,58),(60,63),(64,71),(59,71),(56,65)],c[0])
 d.line([(17,61),(16,68)],fill=c[0]);d.line([(21,65),(23,71)],fill=c[2]);d.line([(48,64),(47,71)],fill=c[2]);d.line([(53,67),(55,71)],fill='#405f60' if g=='man' else '#9b754e')
 d.line([(30,63),(35,66),(41,62)],fill=O);d.point((35,69),fill='#c3b997')
 if style=='pony':p([(16,27),(22,29),(22,42),(16,49),(12,44),(14,35)],h[0]);d.rectangle((16,31,21,33),fill='#a27851')
 return im

def main(out):
 for s in SPECS:
  id,name,g,legacy,h,c,t,style=s;folder=out;folder.mkdir(parents=True,exist_ok=True)
  for v in ['front','back','left','right']:
   im=sprite(s,v);im.save(folder/f'idle_{v}.png');assert im.getbbox()[1:4:2]==(2,70),(id,v,im.getbbox())
  if legacy:
   if BASE is not None:shutil.copyfile(BASE/f'assets/portraits/eldenmere/{legacy}_neutral.png',folder/'portrait.png')
   elif not (folder/'portrait.png').exists():raise RuntimeError('Legacy portrait must be copied unchanged from canonical assets/portraits/eldenmere; run source within repository.')
  else:portrait(s).save(folder/'portrait.png')
  data=dict(id=id,display_name=name,age_group='adult',gender=g,role='civilian',density=2,artwork_pixels_per_world_pixel=2,logical_size=[24,36],foot_anchor=[12,34.5],artwork_foot_anchor=[24,69],frames={v:f'idle_{v}.png' for v in ['front','back','left','right']},portrait='portrait.png',design_notes=f'Native 48×72 pixel geometry with 68-pixel occupied height. {style} hair; '+('preserves approved generic cut, palette, silhouette and portrait identity.' if legacy else ('low tied ponytail, belted teal overshirt and stone trousers; warm medium complexion.' if g=='man' else 'short reddish crop, ochre blouse, loose slate trousers; deep warm complexion.')),source='source.py',runtime_status='rebuilt_not_integrated',design_approval='pending')
  if legacy:data['legacy_ref']=f'assets/characters/npcs/{legacy}';data['portrait_provenance']=f'assets/portraits/eldenmere/{legacy}_neutral.png (approved existing portrait, copied unchanged)'
  (folder/'design.json').write_text(json.dumps(data,indent=2)+'\n')
if __name__=='__main__':main(Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).parent)
