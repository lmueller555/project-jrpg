"""Native named Venn directional artwork. Static complete drawings authored at
2 art pixels/world pixel. Does not enlarge legacy raster artwork.
"""
from pathlib import Path
from PIL import Image,ImageDraw
import json,shutil,hashlib
ROLE='mother'
P=Path(__file__).parent;ROOT=P.parents[4];OUT=ROOT/f'assets/characters/named_hd/venn_{ROLE}';OUT.mkdir(parents=True,exist_ok=True)
O='#281f24';SK='#e8c49d';SS='#c58e69';SL='#fae2bd';HAIR='#785132' if ROLE!='mother' else '#383039';HS='#3d2118' if ROLE!='mother' else '#231e26';HL='#a47848' if ROLE!='mother' else '#57414b'
def poly(d,q,c):d.polygon(q,fill=c,outline=O)
def head(im,dr):
 d=ImageDraw.Draw(im);child=ROLE=='child';top=18 if child else 2
 def p(q,c):poly(d,[(x,y+top) for x,y in q],c)
 def ln(q,c,w=1):d.line([(x,y+top) for x,y in q],fill=c,width=w)
 if dr in ['front','back']:
  if ROLE=='mother':p([(19,0),(27,0),(31,3),(33,8),(32,16),(29,21),(18,21),(15,17),(14,10),(16,4)],HAIR)
  else:p([(18,2),(20,0),(24,1),(27,0),(30,3),(32,4),(31,7),(33,9),(31,13),(30,17),(27,21),(21,21),(17,17),(15,12),(14,8),(16,4)],HAIR)
  ln([(18,5),(21,3),(26,2),(29,4)],HL)
  if dr=='front':
   p([(19,9),(23,7),(28,9),(30,12),(29,17),(26,21),(22,21),(18,17),(17,13)],SK)
   ln([(28,12),(29,16),(27,19)],SS);ln([(19,13),(20,13)],O);ln([(27,13),(28,13)],O)
   ln([(20,14),(20,14)],'#805736' if ROLE=='mother' else '#4e7950');ln([(27,14),(27,14)],'#805736' if ROLE=='mother' else '#4e7950');ln([(23,18),(25,18)],SS)
   p([(16,6),(21,3),(28,4),(31,8),(30,11),(27,9),(24,10),(22,8),(19,11),(16,13)],HAIR);ln([(19,7),(23,5),(27,6)],HL)
   if ROLE=='father':ln([(20,18),(21,20),(25,22),(28,19)],'#8d6951');ln([(23,19),(25,19)],SS)
  else:ln([(19,7),(18,13),(21,17)],HS);ln([(24,4),(25,9),(28,13)],HL);ln([(22,19),(27,19)],HS)
 else:
  p([(19,1),(23,0),(28,1),(31,4),(32,8),(31,13),(33,15),(30,18),(27,21),(22,21),(18,17),(15,12),(15,7),(17,3)],HAIR)
  ln([(18,6),(22,3),(27,3)],HL)
  p([(25,9),(29,9),(30,12),(34,14),(33,16),(30,16),(29,19),(26,21),(23,18),(22,13)],SK);ln([(23,12),(23,17),(26,19)],SS);ln([(28,13),(29,13)],O);ln([(28,14),(28,14)],'#805736' if ROLE=='mother' else '#4e7950');ln([(28,18),(29,18)],SS)
  p([(22,4),(27,3),(31,6),(31,9),(28,8),(25,10),(22,10),(21,13)],HAIR);ln([(23,6),(27,5)],HL)
  if ROLE=='mother':p([(16,10),(20,12),(21,19),(19,22),(16,20),(15,16)],HAIR);ln([(17,13),(18,18)],HL)
  if ROLE=='father':ln([(25,20),(28,20),(30,17)],'#8d6951')
def body(dr):
 im=Image.new('RGBA',(48,72));d=ImageDraw.Draw(im);side=dr=='right';child=ROLE=='child'
 if child:
  C,CH,CD='#839eaf','#b2c7ca','#536f86';pants='#746050';ph='#9d7953';top=38;hem=55
 elif ROLE=='father':C,CH,CD='#ded1ae','#fbeed0','#bcae91';pants='#9b7a49';ph='#c3a575';top=26;hem=48
 else:C,CH,CD='#4c8278','#83aaa0','#305c59';pants='#51413b';ph='#9d7953';top=26;hem=59
 if side:
  for q,col in [([(20,hem),(24,hem),(24,65),(23,68),(19,68)],pants),([(18,65),(23,65),(25,67),(25,69),(18,69)],'#51413b'),([(25,hem),(29,hem),(29,65),(28,68),(24,68)],pants),([(24,65),(29,65),(32,67),(32,69),(24,69)],'#624634')]:poly(d,q,col)
  d.line([(26,hem+2),(26,63)],fill=ph)
  poly(d,[(20,top),(27,top),(30,top+8),(29,hem),(19,hem),(18,top+10)],C);d.polygon([(20,top+2),(22,top+3),(21,hem-2),(19,hem-2)],fill=CH)
  if ROLE=='father':poly(d,[(20,28),(23,29),(25,35),(24,46),(19,46)],'#97614b');d.line([(21,30),(20,42)],fill='#bc8563')
  if ROLE=='mother':poly(d,[(19,44),(29,44),(33,59),(29,61),(17,61),(15,58)],C);d.rectangle((29,41,31,57),fill='#d8c39c');d.line([(30,43),(30,55)],fill='#eee0bd')
  poly(d,[(22,top+2),(26,top+3),(28,top+13),(26,top+18),(22,top+16)],C);d.line([(25,top+5),(26,top+12)],fill=CH)
  poly(d,[(23,top+17),(27,top+17),(28,top+22),(26,top+24),(23,top+22)],SK);d.line([(24,top+19),(24,top+21)],fill=SL)
 else:
  for x in [18,27]:
   poly(d,[(x,hem),(x+5,hem),(x+4,65),(x+4,68),(x-1,68)],pants);d.line([(x+1,hem+2),(x+1,63)],fill=ph);poly(d,[(x-1,65),(x+4,65),(x+6,67),(x+6,69),(x-2,69),(x-2,67)],'#624634');d.line([(x,67),(x+3,67)],fill='#9d7953')
  for x in [12,31]:
   poly(d,[(x,top+2),(x+5,top+3),(x+6,top+12),(x+4,top+18),(x,top+17),(x-1,top+10)],C);d.line([(x+1,top+5),(x+1,top+13)],fill=CH);poly(d,[(x,top+17),(x+4,top+17),(x+5,top+22),(x+3,top+24),(x,top+22)],SK)
  poly(d,[(18,top),(29,top),(33,top+8),(31,hem),(17,hem),(15,top+9)],C);d.polygon([(18,top+3),(21,top+4),(20,hem-2),(17,hem-2)],fill=CH);d.polygon([(29,top+3),(31,top+8),(30,hem-1),(28,hem-2)],fill=CD)
  if ROLE=='father':
   poly(d,[(18,27),(22,28),(23,34),(22,46),(17,46)],'#97614b');poly(d,[(26,28),(30,27),(32,46),(26,46),(25,34)],'#97614b');d.line([(19,29),(18,42)],fill='#bc8563');d.line([(29,30),(30,43)],fill='#694439')
   if dr=='front':d.rectangle((23,31,24,44),fill='#e6d9ba')
   else:d.line([(18,34),(30,34)],fill='#bc8563')
  elif ROLE=='mother':
   poly(d,[(17,44),(31,44),(36,59),(32,62),(16,62),(12,59)],C);d.line([(19,48),(17,58)],fill=CH);d.line([(29,49),(32,58)],fill=CD)
   if dr=='front':poly(d,[(19,38),(28,38),(30,58),(17,58)],'#d8c39c');d.line([(20,42),(19,55)],fill='#eee0bd');d.line([(27,44),(28,55)],fill='#ac9576')
   else:d.line([(18,40),(29,40)],fill='#ac9576')
  elif dr=='front':
   d.line([(22,40),(24,43),(26,40)],fill=CD)
   for y in [46,50]:d.point((24,y),fill=CH)
  else:d.line([(19,42),(29,42)],fill=CD)
 
 if ROLE!='child':d.rectangle((22,22,26,28),fill=SK)
 head(im,dr);return im
for dr in ['front','back','right','left']:
 im=body('right' if dr=='left' else dr)
 if dr=='left':im=im.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
 im.save(OUT/f'idle_{dr}.png')
REF=(ROOT/'assets/portraits/eldenmere')/f'venn_{ROLE}_neutral.png';shutil.copy(REF,OUT/'portrait.png')
design={'id':f'venn_{ROLE}','display_name':{'father':'Mr. Venn','mother':'Mrs. Venn','child':'Venn child'}[ROLE],'stationary':True,'density':2,'artwork_pixels_per_world_pixel':2,'logical_size':[24,36],'draw_anchor':[12,30],'foot_anchor':[12,34],'frames':{dr:f'idle_{dr}.png' for dr in ['front','back','left','right']},'portrait':'portrait.png','status':'candidate','design_notes':'Native complete named directional idles preserving original occupied height and palette; no unused gait invented. Original approved portrait retained byte-identically.'};(OUT/'design.json').write_text(json.dumps(design,indent=2))
E=ROOT/f'docs/reviews/named_hd/venn_{ROLE}';E.mkdir(parents=True,exist_ok=True);sheet=Image.new('RGBA',(192,72),'#777b76');measure={}
for i,dr in enumerate(['front','back','right','left']):
 im=Image.open(OUT/f'idle_{dr}.png');bb=im.getbbox();assert bb[3]-bb[1]==(52 if ROLE=='child' else 68);assert set(im.getchannel('A').getdata())<={0,255};sheet.alpha_composite(im,(48*i,0));measure[dr]={'bounds':bb,'occupied_height_world':(bb[3]-bb[1])/2}
sheet.save(E/'idles-native.png');sheet.resize((1152,432),Image.Resampling.NEAREST).save(E/'idles-6x.png');(E/'checks.json').write_text(json.dumps({'status':'technical_pass','idles':measure,'portrait_sha256':hashlib.sha256(REF.read_bytes()).hexdigest(),'portrait_exact_copy':REF.read_bytes()==(OUT/'portrait.png').read_bytes()},indent=2))
