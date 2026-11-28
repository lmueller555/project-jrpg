from pathlib import Path
from hashlib import sha256
import sys,json,numpy as np
sys.path.insert(0,'/workspace/project-jrpg')
from PIL import Image
from tools.build_prologue_bridge_ascent import WorldRenderer,FigureCompositor,guard_records,_world_sources,_entry
from cinematic_bridge_ascent import actor_states_at,guard_states_at,REINFORCEMENTS,GATE
out=Path('/workspace/project-jrpg/docs/reviews/veinhold_bridge_ascent/guard_exit_probe');rows=[];sources={};w=WorldRenderer();c=FigureCompositor()
for t in (6.25,6.75,8):
 index=round(t*60);env,depth=w.render(index);s=actor_states_at(t);states=guard_states_at(t)
 for id in ('carcovian_reinforcement_7','carcovian_reinforcement_8'):
  rec=next(r for r in guard_records(index) if r['id']==id);sources[str(rec['path'])]=_entry(rec['path'])
  pre=c.compose(env,np.full_like(depth,np.inf),s,[rec],shadows=False);post=c.compose(env,depth,s,[rec],shadows=False)
  a=np.max(np.abs(np.asarray(pre).astype(int)-np.asarray(env).astype(int)),2);b=np.max(np.abs(np.asarray(post).astype(int)-np.asarray(env).astype(int)),2)
  world=next(g['world_position_metres'] for g in states if g['id']==id)
  rows.append({'seconds':t,'id':id,'world':world,'before_depth_body_pixels':int(np.count_nonzero(a)), 'after_depth_body_pixels':int(np.count_nonzero(b)),'contrast_gt5_body_pixels':int(np.count_nonzero(b>5)),'max_rgb_change':int(b.max()),'outside_near_roof':world[1]<GATE['near_y']})
  stem=f'approved316_320_{id[-1]}_{index:04d}'
  for suffix,mask in (('pre',a),('post',b)):Image.fromarray(np.uint8(np.clip(mask*12,0,255))).save(out/f'{stem}_{suffix}_bodymask.png')
  post.save(out/f'{stem}_native.png');post.crop((450,545,510,640)).resize((240,380),Image.Resampling.NEAREST).save(out/f'{stem}_native_x4.png')
profile=Path('/workspace/project-jrpg/assets/story/fire_veinhold_opening/shot08/guards/guardperformance.json')
(out/'approved_stage_current_sources.json').write_text(json.dumps({'method':'Current source-only complete live PNG body contribution; contact shadows disabled. Actual depth before/after; no environmental alpha/gate masking bypass in production.','reinforcements':REINFORCEMENTS,'gate':GATE,'environment_sources':_world_sources(),'guard_profile':_entry(profile),'actual_used_live_pngs':sources,'records':rows},indent=2)+'\n')
print(rows)
