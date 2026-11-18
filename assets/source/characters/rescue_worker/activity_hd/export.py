"""Native-density registration of retained complete injured-worker drawings.
No legacy game sprite enlargement, body warp, limb rig or new character identity.
"""
from pathlib import Path
from PIL import Image
from collections import deque
from copy import deepcopy
import json,hashlib,argparse
SRC=Path(__file__).resolve().parent
BASE='assets/characters/rescue_worker/activity_hd'

def main_component(image):
 width,height=image.size;pending=bytearray(v>=128 for v in image.getchannel('A').tobytes());largest=[]
 for start in range(width*height):
  if not pending[start]:continue
  pending[start]=0;queue=deque([start]);members=[]
  while queue:
   at=queue.popleft();members.append(at);x,y=at%width,at//width
   for dy in (-1,0,1):
    for dx in (-1,0,1):
     xx,yy=x+dx,y+dy
     if (dx or dy)and 0<=xx<width and 0<=yy<height:
      q=yy*width+xx
      if pending[q]:pending[q]=0;queue.append(q)
  if len(members)>len(largest):largest=members
 if len(largest)<1000:raise ValueError('Missing complete worker source drawing')
 alpha=bytearray(width*height)
 for at in largest:alpha[at]=255
 result=image.copy();result.putalpha(Image.frombytes('L',image.size,bytes(alpha)));return result

def products(root):
 old=root/'assets/story/sanctuary_rescue';source=root/'assets/source/story/sanctuary_rescue'
 actor=deepcopy(json.loads((old/'art.json').read_text())['actors']['worker']);registration=json.loads((source/'registration.json').read_text());needed=set(actor['idles'].values())
 for fs in actor['walks'].values():needed.update(f['file']for f in fs)
 for pose in actor['poses'].values():needed.update(f['file']for f in pose['frames'])
 assert len(needed)==23
 files={};audit=[];lookup={};sheets={}
 for rec in registration['frames']:
  if rec['file']not in needed:continue
  path=source/rec['source'];expected=registration['sources'][rec['source']]
  assert hashlib.sha256(path.read_bytes()).hexdigest()==expected,'Changed retained identity source'
  if rec['source']not in sheets:sheets[rec['source']]=Image.open(path).convert('RGBA')
  cell=main_component(sheets[rec['source']].crop(tuple(rec['source_rect'])));assert cell.getbbox()==tuple(rec['source_bounds'])
  body=cell.crop(tuple(rec['source_bounds']));scale=rec['scale']*2;body=body.resize((round(body.width*scale),round(body.height*scale)),Image.Resampling.NEAREST)
  # Preserve recorded origins rather than realigning each pose to its feet.
  origin=tuple(v*2 for v in rec['destination']);im=Image.new('RGBA',(80,80));im.alpha_composite(body,origin)
  assert origin[0]>=0 and origin[1]>=0 and origin[0]+body.width<=80 and origin[1]+body.height<=80
  relative=Path(rec['file']).relative_to('assets/story/sanctuary_rescue');out=f'{BASE}/{relative}';files[out]=im;lookup[rec['file']]=out
  audit.append({**rec,'legacy_file':rec['file'],'file':out,'scale':scale,'destination':list(origin),'canvas':[80,80],'draw_anchor':[40,68],'source_sha256':expected})
 assert set(lookup)==needed
 actor['idles']={d:lookup[f]for d,f in actor['idles'].items()}
 for fs in actor['walks'].values():
  for f in fs:f['file']=lookup[f['file']]
 for pose in actor['poses'].values():
  pose['artwork_pixels_per_world_pixel']=2
  for f in pose['frames']:f['file']=lookup[f['file']]
 actor['travel_artwork_pixels_per_world_pixel']=2
 # Frame-size/anchor metadata remain world units, as CastActor expects.
 actor['frame_size']=[40,40];actor['anchor']=[20,34]
 portraits=json.loads((root/'assets/portraits/eldenmere/portraits.json').read_text())['portraits'];portrait=root/'assets/portraits/eldenmere'/portraits['male_02']['file']
 extra={f'{BASE}/actor.json':actor,f'{BASE}/identity.json':dict(id='rescue_worker',display_name='Trapped worker / Injured worker',portrait=f'{BASE}/portrait.png',portrait_sha256=hashlib.sha256(portrait.read_bytes()).hexdigest(),legacy_portrait_key='male_02',status='candidate'),f'{BASE}/registration.json':dict(version=1,source_registration='assets/source/story/sanctuary_rescue/registration.json',frames=audit)}
 return files,extra,portrait

def export(root,inputs=None):
 files,meta,portrait=products(inputs or root);hashes={}
 for relative,im in files.items():
  path=root/relative;path.parent.mkdir(parents=True,exist_ok=True);im.save(path);hashes[relative]=hashlib.sha256(path.read_bytes()).hexdigest()
 p=root/f'{BASE}/portrait.png';p.write_bytes(portrait.read_bytes());hashes[f'{BASE}/portrait.png']=hashlib.sha256(p.read_bytes()).hexdigest()
 for relative,data in meta.items():(root/relative).write_text(json.dumps(data,indent=2)+'\n')
 (root/f'{BASE}/sha256.json').write_text(json.dumps(hashes,indent=2)+'\n');return hashes
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--repo-root',required=True,type=Path);p.add_argument('--input-root',type=Path);a=p.parse_args();print('Exported',len(export(a.repo_root.resolve(),a.input_root.resolve()if a.input_root else None)),'native worker/portrait PNGs')
