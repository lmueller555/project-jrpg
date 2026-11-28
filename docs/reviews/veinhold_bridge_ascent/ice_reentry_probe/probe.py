import sys,json,numpy as np
from pathlib import Path
from PIL import Image,ImageDraw
sys.path.insert(0,'/workspace/project-jrpg')
from tools.build_prologue_bridge_ascent import WorldRenderer,FigureCompositor,guard_records
from cinematic_bridge_ascent import actor_states_at,guard_states_at
out=Path('/workspace/project-jrpg/docs/reviews/veinhold_bridge_ascent/ice_reentry_probe');out.mkdir(exist_ok=True)
w=WorldRenderer();c=FigureCompositor();rows=[];pics=[]
for i in (252,258,264,270,276,282,288,300,348,480):
 env,depth=w.render(i);state=actor_states_at(i/60);records=[r for r in guard_records(i) if r['id'].startswith('carcovian_guard_')]
 composite=c.compose(env,depth,state,records,shadows=False)
 diff=np.max(np.abs(np.asarray(composite).astype(int)-np.asarray(env).astype(int)),2)
 previous=w._frost;w._frost=lambda *a,**k:None
 bare,_=w.render(i);w._frost=previous
 frost=np.max(np.abs(np.asarray(bare).astype(int)-np.asarray(env).astype(int)),2)
 rows.append({'index':i,'seconds':i/60,'frozen_body_changed_pixels':int(np.count_nonzero(diff)),
              'floor_and_rail_frost_changed_pixels':int(np.count_nonzero(frost)),
              'frost_max_rgb_difference':int(frost.max()),
              'frozen_world_positions':[g['world_position_metres'] for g in guard_states_at(i/60) if g['kind']=='frozen']})
 composite.save(out/f'frame_{i:04d}.png')
 Image.fromarray(np.uint8(np.clip(frost*12,0,255))).save(out/f'frost_difference_{i:04d}.png')
 pics.append((i,composite.crop((430,0,530,100)).resize((400,400),Image.Resampling.NEAREST)))
sheet=Image.new('RGB',(2000,850),'#0c1a2b');p=ImageDraw.Draw(sheet)
for k,(i,pic) in enumerate(pics):
 x=(k%5)*400;y=(k//5)*425;sheet.paste(pic,(x,y));p.text((x+10,y+403),f'{i/60:.1f}s native100x100->4xNEAREST',fill='white')
sheet.save(out/'reentry_native_x4.png')
(out/'contributors.json').write_text(json.dumps({'method':'Actual complete frozen PNG source-only contribution, no contactshadows; frost difference compares same world render with bounded frost material disabled. No pose/position changes.','records':rows},indent=2)+'\n')
print(rows)
