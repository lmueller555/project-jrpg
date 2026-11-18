"""Export complete native kitchen-gardener drawings without anatomical transforms."""
from pathlib import Path
from hashlib import sha256
from io import BytesIO
import argparse,json
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'assets/source/characters/regional_npc_hd/regional_gardener/actions_hd'
PACK='assets/characters/regional_npc_hd/regional_gardener/actions_hd'
SPEC={**{f'{pose}_{d}':(8,85,True) for pose in ('carry','carry_can') for d in ('front','back','left','right')},
      'fill_front':(4,550,False),'water_right':(4,600,False),'weed_right':(4,600,True),'sort_right':(4,450,False),'weed_front':(4,1000,True)}
def doc(data):return (json.dumps(data,indent=2)+'\n').encode()
def png(im):
 b=BytesIO();im.save(b,format='PNG');return b.getvalue()
def products():
 recipe_raw=(SRC/'recipe.json').read_bytes();recipe=json.loads(recipe_raw)
 if recipe['runtime_activation'] or recipe['actor_id']!='regional_gardener':raise ValueError('Wrong dormant scope')
 for r in recipe['sources']:
  if sha256((SRC/r['file']).read_bytes()).hexdigest()!=r['sha256']:raise ValueError('Changed source '+r['file'])
 out={};records=[];sequences={};board=Image.new('RGB',(800,120*len(SPEC)+32),'#e3e6da');draw=ImageDraw.Draw(board)
 draw.text((8,8),'REGIONAL BLUE KITCHEN GARDENER / DORMANT SOURCE / NOT GAMEPLAY',fill='#243529')
 for row,(key,(count,ms,loop)) in enumerate(SPEC.items()):
  frames=[];proof=[]
  for i in range(count):
   file=f'{key}_{i:02}.png';data=(SRC/'masters'/file).read_bytes();im=Image.open(BytesIO(data)).convert('RGBA')
   if im.size!=(80,88) or not im.getbbox() or set(im.getchannel('A').tobytes())-{0,255}:raise ValueError('Wrong native source body')
   out[PACK+'/'+file]=data;frames.append({'file':file,'duration_ms':ms});records.append({'file':file,'sha256':sha256(data).hexdigest()})
   board.paste(im,(i*80,row*120+32),im)
   view=Image.new('RGB',(120,112),'#e3e6da');view.paste(im,(20,0),im);proof.append(view)
  sequences[key]={'loop':loop,'frames':frames};draw.text((644,row*120+64),key,fill='#243529')
  for slow,label in ((1,'normal'),(2,'half_speed')):
   durations=[(80 if i%2==0 else 90) if ms==85 and slow==1 else ms*slow for i in range(count)]
   b=BytesIO();proof[0].save(b,format='GIF',save_all=True,append_images=proof[1:],duration=durations,loop=0,disposal=2)
   out[PACK+'/review/'+key+'_'+label+'.gif']=b.getvalue()
 out[PACK+'/native_contact.png']=png(board)
 meta={'version':1,'actor_id':'regional_gardener','runtime_activation':False,'artwork_pixels_per_world_pixel':2,
       'logical_canvas':[40,44],'draw_anchor_logical':[20,38],'sequences':sequences,'frames':records,
       'source_recipe':str((SRC/'recipe.json').relative_to(ROOT)),'source_recipe_sha256':sha256(recipe_raw).hexdigest(),
       'source_authorship':'Explicit complete-pose long-dress drawings; canonical same-phase two-step cloth/boot motion guides and protected own head. Natural occupied grip contours and supported bends. No limb raster transforms, rig or resized legacy body.',
       'activation_gates':['Actual source can/produce/basket hand registration and rear/side depth in live work.','Natural filling excursion, kneeling harvest, set-down and sheep-care/patting review.','Existing interrupted/repeated work and Save/Continue state/ownership must pass unchanged.'],
       'scope':'Blue regional kitchen gardener only. Separate sage Eldenmere Sanctuary gardener is excluded.'}
 out[PACK+'/animation.json']=doc(meta)
 return out
def build(check=False):
 out=products();stale=[]
 for file,data in out.items():
  p=ROOT/file
  if not p.is_file() or p.read_bytes()!=data:
   stale.append(file)
   if not check:p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
 if check and stale:raise SystemExit('Stale kitchen action exports: '+', '.join(stale))
 print(str(len(out))+' native kitchen-gardener exports '+('verified' if check else 'built'));return out
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');a=p.parse_args();build(a.check)
