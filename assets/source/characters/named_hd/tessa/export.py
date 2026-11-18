"""Technical export only; does not draw anatomy or alter native masters."""
from pathlib import Path
from PIL import Image,ImageDraw
import json,shutil,hashlib
P=Path(__file__).parent;ROOT=P.parents[4];B=ROOT/'assets/characters/named_hd/tessa';E=ROOT/'docs/reviews/named_hd/tessa';E.mkdir(parents=True,exist_ok=True)
portrait=ROOT/'assets/portraits/eldenmere/tessa_neutral.png';shutil.copy(portrait,B/'portrait.png')
design={'id':'tessa','display_name':'Tessa','age_group':'child','age_years':10,'gender':'girl','role':'civilian','density':2,'artwork_pixels_per_world_pixel':2,'logical_size':[24,36],'draw_anchor':[12,30],'foot_anchor':[12,34],'frames':{d:f'idle_{d}.png' for d in ['front','back','left','right']},'portrait':'portrait.png','status':'candidate','design_notes':'Native 56-art-pixel occupied Tessa, preserved 28-world-pixel height: auburn single braid, green eyes, cream blouse, sage pinafore. Original approved portrait retained without changes.'}
(B/'design.json').write_text(json.dumps(design,indent=2))
checks=[]
for mode,n,ms in [('walk',8,70),('run',4,100)]:
 proof=Image.new('RGBA',(48*(n+1),72*4),'#777b76')
 for row,d in enumerate(['front','back','right','left']):
  bank=B/f'{mode}_{d}';frames=[Image.open(bank/f'frame_{i+1:02}.png').convert('RGBA') for i in range(n)];sheet=Image.new('RGBA',(48*n,72));proof.alpha_composite(Image.open(B/f'idle_{d}.png'),(0,row*72));records=[]
  for i,im in enumerate(frames):
   assert im.size==(48,72) and set(im.getchannel('A').getdata())<={0,255};bb=im.getbbox();assert bb[0]>0 and bb[1]>0 and bb[2]<48 and bb[3]<72
   sheet.alpha_composite(im,(i*48,0));proof.alpha_composite(im,((i+1)*48,row*72));records.append({'file':f'frame_{i+1:02}.png','rect':[i*48,0,48,72],'duration_ms':ms,'phase':(['right_contact','right_down','left_passing','left_recovery','left_contact','left_down','right_passing','right_recovery'] if mode=='walk' else ['right_contact','flight_left_recovery','left_contact','flight_right_recovery'])[i],'bounds':bb,'crown_y':bb[1],'lowest_visible_sole_y':bb[3]-1})
  assert len({im.tobytes() for im in frames})==n
  sheet.save(bank/'spritesheet.png');meta={'version':1,'character':'tessa','animation':f'{mode}.{d}','status':'candidate','artwork_pixels_per_world_pixel':2,'frame_size':[48,72],'logical_size':[24,36],'draw_anchor':[24,60],'foot_anchor':[24,68],'cycle_ms':ms*n,'loop':True,'spritesheet':'spritesheet.png','frames':records};(bank/'animation.json').write_text(json.dumps(meta,indent=2))
  for scale,label,duration in [(1,'native',ms),(4,'4x',ms),(4,'slow',ms*2)]:
   fs=[]
   for im in frames:
    bg=Image.new('RGBA',im.size,'#777b76');bg.alpha_composite(im);fs.append(bg.convert('RGB').resize((48*scale,72*scale),Image.Resampling.NEAREST))
   fs[0].save(E/f'{mode}_{d}_{label}.gif',save_all=True,append_images=fs[1:],duration=duration,loop=0)
  checks.append({'animation':f'{mode}.{d}','unique_frames':n,'hard_alpha':True,'cycle_ms':ms*n,'measurements':records})
 proof.save(E/f'{mode}-native.png');proof.resize((proof.width*3,proof.height*3),Image.Resampling.NEAREST).save(E/f'{mode}-3x.png')
(E/'checks.json').write_text(json.dumps({'status':'technical_pass','portrait_original_sha256':hashlib.sha256(portrait.read_bytes()).hexdigest(),'portrait_copy_sha256':hashlib.sha256((B/'portrait.png').read_bytes()).hexdigest(),'banks':checks},indent=2))
