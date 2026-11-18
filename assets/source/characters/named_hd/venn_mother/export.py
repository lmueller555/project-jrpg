from pathlib import Path
from PIL import Image
import json
P=Path(__file__).parent;ROOT=P.parents[4];ROLE=P.name;OUT=ROOT/'assets/characters/named_hd'/ROLE;E=ROOT/'docs/reviews/named_hd'/ROLE;proof=Image.new('RGBA',(432,288),'#777b76');rows=[]
for row,dr in enumerate(['front','back','right','left']):
 bank=OUT/f'walk_{dr}';sheet=Image.new('RGBA',(384,72));frames=[];meta=[];proof.alpha_composite(Image.open(OUT/f'idle_{dr}.png'),(0,72*row))
 for i in range(8):
  im=Image.open(bank/f'frame_{i+1:02}.png').convert('RGBA');bb=im.getbbox();assert im.size==(48,72) and set(im.getchannel('A').getdata())<={0,255};assert bb[0]>0 and bb[2]<48 and bb[1]>=1 and bb[3]<=70
  sheet.alpha_composite(im,(48*i,0));proof.alpha_composite(im,(48*(i+1),72*row));frames.append(im);meta.append({'file':f'frame_{i+1:02}.png','rect':[48*i,0,48,72],'duration_ms':70,'phase':['right_contact','right_down','left_passing','left_recovery','left_contact','left_down','right_passing','right_recovery'][i],'bounds':bb,'crown_y':bb[1],'visible_sole_y':bb[3]-1})
 assert len({im.tobytes() for im in frames})==8
 sheet.save(bank/'spritesheet.png');(bank/'animation.json').write_text(json.dumps({'version':1,'character':ROLE,'animation':f'walk.{dr}','status':'candidate','artwork_pixels_per_world_pixel':2,'frame_size':[48,72],'logical_size':[24,36],'draw_anchor':[24,60],'foot_anchor':[24,68],'cycle_ms':560,'loop':True,'spritesheet':'spritesheet.png','frames':meta},indent=2))
 for scale,name,duration in [(1,'native',70),(4,'4x',70),(4,'slow',140)]:
  fs=[]
  for im in frames:
   bg=Image.new('RGBA',(48,72),'#777b76');bg.alpha_composite(im);fs.append(bg.convert('RGB').resize((48*scale,72*scale),Image.Resampling.NEAREST))
  fs[0].save(E/f'walk_{dr}_{name}.gif',save_all=True,append_images=fs[1:],duration=duration,loop=0)
 rows.append({'direction':dr,'unique':8,'frames':meta})
proof.save(E/'walk-native.png');proof.resize((1296,864),Image.Resampling.NEAREST).save(E/'walk-3x.png');(E/'walk-checks.json').write_text(json.dumps(rows,indent=2))
