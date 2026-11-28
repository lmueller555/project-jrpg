"""Register complete ImageGen drawings; no guide pixels or regional transforms.

Actual source face/neck measurements determine one whole-master density and
per-drawing translation. Registration never fits occupied figure height.
"""
from pathlib import Path
from hashlib import sha256
from statistics import median
import importlib.util,json,math,sys
import numpy as np
from PIL import Image,ImageDraw
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[6]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from cinematic_bridge_ascent import actor_states_at
from tools.audit_prologue_hands import _components
spec=importlib.util.spec_from_file_location('old_iselin_registration',ROOT/'assets/source/cinematics/fire_veinhold/face_reveal/iselin/run_v2/register_sources.py');model=importlib.util.module_from_spec(spec);spec.loader.exec_module(model)
model.SEARCH={'face':(.15,.025,.9,.38),'neck':(.15,.11,.9,.44),'belt':(.15,.25,.9,.65)}
OLD=json.loads((ROOT/'assets/source/cinematics/fire_veinhold/face_reveal/iselin/source_art_48.json').read_text())

def face_component(im):
 box=(round(im.width*.20),round(im.height*.025),round(im.width*.9),round(im.height*.46));rgba=np.asarray(im.crop(box)).astype(np.int16);r,g,b,a=(rgba[:,:,j] for j in range(4));warm=(a>180)&(r>90)&(g>60)&(b>40)&(r-g>12)&(r-b>24)&(g-b>2);items=[]
 for item in _components(warm):
  x0,y0,x1,y1=item['bounds'];fill=item['area']/max(1,(x1-x0)*(y1-y0));point=item['point']+np.asarray(box[:2])
  if item['area']>180 and fill>.30 and point[1]<im.height*.43:
   item={**item,'bounds':[int(v+box[j%2]) for j,v in enumerate(item['bounds'])],'point':point.tolist()};items.append(item)
 if not items:raise ValueError('No reviewed candidate face component')
 return max(items,key=lambda c:c['area'])

def collect(p):
 master=Image.open(p/'master.png').convert('RGBA');generation=json.loads((p/'generation.json').read_text());digest=sha256((p/'master.png').read_bytes()).hexdigest();refs=json.loads((p/'reference_manifest.json').read_text());cachepath=p/'landmark_observations.json';cache=json.loads(cachepath.read_text()) if cachepath.exists() else None
 if cache and cache.get('source_sha256')==digest:return master,generation,cache['observations']
 rows=[]
 for n,ref in enumerate(refs):
  cell=[round(v*(master.width/1024 if j%2==0 else master.height/1536)) for j,v in enumerate(ref['cell'])];im=master.crop(tuple(cell));skin=face_component(im);neck=model.measure(im,'neck');x0,y0,x1,y1=skin['bounds'];expected=[(x0+x1)/2,y1+4*(x1-x0)/93]
  if abs(neck['point'][0]-expected[0])>(x1-x0)*.27 or abs(neck['point'][1]-expected[1])>15:
   neck={'point':expected,'score':None,'template_scale':None,'method':'Observed lower face-skin edge/center, excluding false braid ornament match; inspect source overlay.'}
  rows.append({'index':ref['sample_index'],'gait_frame':ref['gait_frame'],'cell':cell,'source_neck':list(neck['point']),'neck_match':neck,'face_skin_bounds':skin['bounds'],'face_skin_width':x1-x0,'face_skin_area':skin['area'],'method':'Actual warm face component and actual collar/neck template; measurements, not desired motion targets.'})
 cachepath.write_text(json.dumps({'source_sha256':digest,'observations':rows},indent=2)+'\n');return master,generation,rows

def main():
 select={}
 names=['transition_020_023','transition_024_027_final_retry','transition_028_031_continuity_retry','transition_032_035','transition_036_039','transition_040_043_view_retry','transition_044_047_view_retry','transition_048_051_view_bridge','transition_052_055_view_bridge']
 for name in names:
  p=BASE/'batches'/name
  refs=json.loads((p/'reference_manifest.json').read_text())
  for ref in refs:select[ref['sample_index']]=p
 out=Path('/tmp/iselin_ascent_close');out.mkdir(exist_ok=True);records=[];diagnostic=[]
 for p in sorted(set(select.values())):
  master,generation,rows=collect(p);scale=1.38*64.5/median(r['face_skin_width'] for r in rows)
  if p.name=='transition_020_023':
   scale=1.38
   original=p/'trial_registration.json'
   if original.exists():
    previous={r['index']:r for r in json.loads(original.read_text())}
    for r in rows:
     r['source_neck']=previous[r['index']]['source_neck']
     r['neck_match_used_for_registration']=False
     r['registration_override']='Retains the already inspected20–23 native prototype collar point from trial_registration.json; fresh face/neck observations are diagnostics only.'
  for row in rows:
   i=row['index'];state=next(a for a in actor_states_at(i/60)['runners'] if a['id']=='iselin');f=state['frame_index'];prior=OLD['frames'][f];target=[prior['landmarks']['neck'][j]*prior['scale']+prior['origin'][j] for j in (0,1)];e=math.radians(state['view_elevation_degrees']);e0=math.radians(next(a for a in actor_states_at(0)['runners'] if a['id']=='iselin')['view_elevation_degrees']);z=(960-target[1])/500;target[1]+=500*(z*(math.cos(e0)-math.cos(e))+.12*(math.sin(e)-math.sin(e0)));origin=[target[j]-row['source_neck'][j]*scale for j in (0,1)]
   im=master.crop(tuple(row['cell']));im.putalpha(im.getchannel('A').point(lambda a:0 if a<=16 else a));sampled=im.convert('RGBa').resize(tuple(round(v*scale) for v in im.size),Image.Resampling.LANCZOS).convert('RGBA');canvas=Image.new('RGBA',(1024,1536));canvas.alpha_composite(sampled,tuple(round(v) for v in origin));filename=f'frame_{i:03d}.png';canvas.save(out/filename)
   rec={**row,'source':(p/'master.png').relative_to(BASE).as_posix(),'source_sha256':generation['sha256'],'generation_id':generation['generation_id'],'scale':scale,'origin':origin,'neck_target':target,'file':str(out/filename),'canvas':[1024,1536],'anchor':[512,960],'art_pixels_per_metre':500,'actual_elevation':state['view_elevation_degrees'],'native_scale':state['scale'],'approval_state':'candidate_pending_composed_native_review'};records.append(rec)
   marked=master.crop(tuple(row['cell'])).convert('RGBA');pen=ImageDraw.Draw(marked);pen.rectangle(row['face_skin_bounds'],outline='yellow',width=2);nx,ny=row['source_neck'];pen.ellipse((nx-3,ny-3,nx+3,ny+3),fill='red');marked.thumbnail((256,384));diagnostic.append((i,marked))
 records.sort(key=lambda r:r['index']);(BASE/'candidate_close_registration.json').write_text(json.dumps({'method':'One whole-master density from actual face model width relative to accepted20–23model, actual neck translation and angle-aware body projection. No occupied-height fit, regional transforms or blended poses.','frames':records},indent=2)+'\n')
 if diagnostic:
  sheet=Image.new('RGB',(256*8,410*((len(diagnostic)+7)//8)),'#273544');pen=ImageDraw.Draw(sheet)
  for n,(i,im) in enumerate(sorted(diagnostic,key=lambda x:x[0])):x=n%8*256;y=n//8*410;sheet.paste(im,(x,y),im);pen.text((x+5,y+388),str(i),fill='white')
  sheet.save(out/'source_measurement_sheet.jpg',quality=95)
 print('Registered',len(records),'complete candidate drawings:',out)
if __name__=='__main__':main()
