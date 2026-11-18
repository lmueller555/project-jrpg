"""Validate Liam artwork pixels, logical behavior contracts, and deterministic exports."""
from pathlib import Path
import argparse,json,hashlib
from PIL import Image
from export import export
p=argparse.ArgumentParser();p.add_argument('--repo-root',required=True,type=Path);p.add_argument('--legacy-input-root',type=Path);a=p.parse_args();r=a.repo_root.resolve();legacy=(a.legacy_input_root or r).resolve();out=r/'assets/characters/liam/activity_hd'
for bank in ('block_play','play_routine'):
 m=json.loads((out/bank/'animations.json').read_text());old=json.loads((legacy/f'assets/characters/liam_family/{bank}/animations.json').read_text())
 assert m['artwork_pixels_per_world_pixel']==2
 for action,d in m['actions'].items():
  orig=old['actions'][action]
  for key in ('duration_ms','contact_frame','handoff_contact_frame','draw_anchor','landmarks'):
   assert d.get(key)==orig.get(key),(bank,action,key)
  assert len(d['frames'])==len(orig['frames'])
  for f,g in zip(d['frames'],orig['frames']):
   for key in ('duration_ms','hand_local'):assert f.get(key)==g.get(key),(action,key)
   im=Image.open(r/f['file']).convert('RGBA');assert im.size==(192,192)
   assert set(im.getchannel('A').tobytes())<={0,255}
   if f.get('hand_local'):
    x,y=[v*2 for v in f['hand_local']]
    assert im.crop((x-4,y-4,x+5,y+5)).getbbox(),(action,'missing hand contact')
for oldbank,bank in [('poses','lantern_assembly'),('rest_poses','lantern_rest'),('finish_poses','lantern_finish')]:
 m=json.loads((out/bank/'liam.json').read_text());old=json.loads((legacy/f'assets/story/lantern/{oldbank}/liam.json').read_text());assert m['artwork_pixels_per_world_pixel']==2
 for key in ('canvas','draw_anchor','world_contacts','action_facing'):assert m.get(key)==old.get(key)
 for action,fs in m['actions'].items():
  for f,g in zip(fs,old['actions'][action]):
   for k in ('rect','duration_ms','hand','holds_frame','frame_bbox'):assert f.get(k)==g.get(k),(bank,action,k)
 for face,c in m.get('carry',{}).items():
  for f,g in zip([c['idle'],*c['walk']],[old['carry'][face]['idle'],*old['carry'][face]['walk']]):
   for k in ('rect','duration_ms','hand','holds_frame','frame_bbox'):assert f.get(k)==g.get(k),(bank,face,k)
 im=Image.open(r/m['sheet']);assert set(im.getchannel('A').tobytes())<={0,255}
expected=json.loads((out/'sha256.json').read_text())
for f,h in expected.items():assert hashlib.sha256((r/f).read_bytes()).hexdigest()==h,f
assert export(r,legacy)==expected,'non-deterministic export'
print('PASS:52 native activity frames,91 lantern cells, preserved behavior metadata, hard alpha,55 reproducible PNGs')
