from pathlib import Path
from copy import deepcopy
import sys,json,numpy as np
from PIL import Image,ImageDraw
sys.path.insert(0,'/workspace/project-jrpg')
from tools.build_prologue_bridge_ascent import WorldRenderer,FigureCompositor,guard_records
from cinematic_bridge_ascent import actor_states_at,guard_states_at,GATE
out=Path('/workspace/project-jrpg/docs/reviews/veinhold_bridge_ascent/guard_exit_probe');out.mkdir(exist_ok=True)
w=WorldRenderer();c=FigureCompositor();rows=[]
for t in (5,5.25,5.5,5.75,6,6.25,6.5,6.75,7,7.25,7.5,7.75,8):
 index=round(t*60);env,depth=w.render(index);records=guard_records(index)
 for label,starts in [('current_324_328',(324,328)),('trial_316_320',(316,320))]:
  s=actor_states_at(t);s['guards']=deepcopy(guard_states_at(t))
  for j,start in enumerate(starts):s['guards'][-2+j]['world_position_metres'][1]=start-4*t
  for j in (6,7):
   ident=f'carcovian_reinforcement_{j+1}';rec=next(r for r in records if r['id']==ident)
   pre=c.compose(env,np.full_like(depth,np.inf),s,[rec],shadows=False)
   post=c.compose(env,depth,s,[rec],shadows=False)
   a=np.max(np.abs(np.asarray(pre).astype(int)-np.asarray(env).astype(int)),2)
   b=np.max(np.abs(np.asarray(post).astype(int)-np.asarray(env).astype(int)),2)
   world=s['guards'][-2+(j-6)]['world_position_metres']
   row={'time':t,'configuration':label,'id':ident,'world':world,'predepth_body_pixels':int(np.count_nonzero(a)),
       'postdepth_body_pixels':int(np.count_nonzero(b)),'postdepth_contrast_pixels_gt5':int(np.count_nonzero(b>5)),
       'maximum_rgb_change':int(b.max()),'outside_gate_near_edge':world[1]<GATE['near_y']}
   rows.append(row)
   if t in (5.25,5.75,6.25,6.75,7.25,8):
    suffix=f'{label}_{ident[-1]}_{index:04d}'
    Image.fromarray(np.uint8(np.clip(a*12,0,255))).save(out/f'{suffix}_pre_mask.png')
    Image.fromarray(np.uint8(np.clip(b*12,0,255))).save(out/f'{suffix}_post_mask.png')
    post.crop((450,545,510,640)).resize((240,380),Image.Resampling.NEAREST).save(out/f'{suffix}_native_x4.png')
(out/'contributors.json').write_text(json.dumps({'gate':GATE,'method':'Exact actual guarded PNG premultiplied composition, shadows disabled; pre vs post same raised-geometry depth mask.','records':rows},indent=2)+'\n')
for config in ('current_324_328','trial_316_320'):
 for ident in ('carcovian_reinforcement_7','carcovian_reinforcement_8'):
  group=[r for r in rows if r['configuration']==config and r['id']==ident]
  print(config,ident, 'first-surviving',next((r['time'] for r in group if r['postdepth_contrast_pixels_gt5']>0),None),'at8',group[-1])
