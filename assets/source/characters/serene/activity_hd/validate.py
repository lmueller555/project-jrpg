from pathlib import Path
import argparse,json,hashlib
from PIL import Image
from export import export
p=argparse.ArgumentParser();p.add_argument('--repo-root',type=Path,required=True);p.add_argument('--legacy-input-root',type=Path);p.add_argument('--base-root',type=Path);a=p.parse_args();r=a.repo_root.resolve();old=(a.legacy_input_root or r).resolve();base=(a.base_root or r).resolve();out=r/'assets/characters/serene/activity_hd';m=json.loads((out/'routines/animations.json').read_text());orig=json.loads((old/'assets/characters/serene/routines/animations.json').read_text())
for k in ['frame_size','action_canvas','body_frame_size','body_offset','draw_anchor','foot_anchor','actions','animations','surface_props']:assert m[k]==orig[k],k
assert m['artwork_pixels_per_world_pixel']==2
for p in (out/'routines').rglob('frame*.png'):
 im=Image.open(p);assert im.size==(96,96);assert set(im.getchannel('A').tobytes())<={0,255}
for p in (out/'story').glob('*.png'):
 im=Image.open(p);assert im.size==(48,72);assert set(im.getchannel('A').tobytes())<={0,255}
expected=json.loads((out/'sha256.json').read_text());assert len(expected)==46
for p,h in expected.items():assert hashlib.sha256((r/p).read_bytes()).hexdigest()==h
assert export(r,old,base)==expected
print('PASS:44 routine+2 story PNGs, exact behavior/ownership metadata, hard alpha, reproducible')
