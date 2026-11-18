"""Technical export only: complete native masters, no anatomical image transforms."""
from pathlib import Path
import json,hashlib,argparse,io
ap=argparse.ArgumentParser();ap.add_argument("--check",action="store_true");args=ap.parse_args()
def emit(path,data):
 if args.check:
  if not path.exists() or path.read_bytes()!=data:raise SystemExit("Mismatch: "+str(path))
 else:
  path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
def picture(path,im,fmt="PNG",**kwargs):
 b=io.BytesIO();im.save(b,format=fmt,**kwargs);emit(path,b.getvalue())
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'assets/source/characters/regional_npc_hd/regional_picker/actions_hd'
OUT=ROOT/'assets/characters/regional_npc_hd/regional_picker/actions_hd'
DOC=ROOT/'docs/qa/regional_picker_actions'
spec={**{f'carry_{d}':(8,85,True) for d in ['front','back','right','left']},'reach_front':(4,450,False),'admire_front':(2,650,True),'lower_front':(4,250,False),'sort_right':(4,450,False),'rest_front':(1,1000,False)}
man={'version':1,'actor_id':'regional_picker','runtime_activation':False,'artwork_pixels_per_world_pixel':2,'logical_canvas':[40,44],'draw_anchor_logical':[20,38],'sequences':{}}
evidence={};board=Image.new('RGB',(800,88*len(spec)),'#777d75');draw=ImageDraw.Draw(board)
for row,(key,(count,ms,loop)) in enumerate(spec.items()):
 frames=[];proof=[];hashes=[];bounds=[]
 for i in range(count):
  name=f'{key}_{i:02}.png';src=SRC/'masters'/name;im=Image.open(src).convert('RGBA')
  assert im.size==(80,88) and im.getbbox()
  assert set(im.getchannel('A').getdata())<={0,255}
  emit(OUT/name,src.read_bytes());sha=hashlib.sha256(src.read_bytes()).hexdigest();hashes.append(sha);bounds.append(im.getbbox())
  frames.append({'file':name,'duration_ms':ms});board.paste(im,(80*i,88*row),im)
  bg=Image.new('RGB',(80,88),'#777d75');bg.paste(im,(0,0),im);proof.append(bg.resize((320,352),Image.Resampling.NEAREST))
 seq={'loop':loop,'frames':frames}
 if key=='rest_front':seq['draw_anchor_logical']=[20,44]
 man['sequences'][key]=seq;evidence[key]={'count':count,'cycle_ms':count*ms,'sha256':hashes,'alpha_bounds':bounds,'unique_pixels':len(set(hashes))}
 picture(DOC/f'{key}_4x.gif',proof[0],'GIF',save_all=True,append_images=proof[1:],duration=ms,loop=0)
 draw.text((645,88*row+25),key,fill='white')
picture(DOC/'contact_native.png',board);picture(DOC/'contact_2x.png',board.resize((1600,1584),Image.Resampling.NEAREST))
emit(OUT/'animation.json',(json.dumps(man,indent=2)+'\n').encode());emit(DOC/'measurements.json',(json.dumps(evidence,indent=2)+'\n').encode())
print('Verified without writing' if args.check else 'Exported',sum(x[0] for x in spec.values()),'complete native drawings; dormant manifest.')
