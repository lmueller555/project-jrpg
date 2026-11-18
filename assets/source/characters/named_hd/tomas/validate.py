from pathlib import Path
from PIL import Image
import argparse,json,hashlib,subprocess,sys
p=argparse.ArgumentParser();p.add_argument('--repo-root',type=Path,required=True);p.add_argument('--legacy-input-root',type=Path);a=p.parse_args();r=a.repo_root.resolve();old=(a.legacy_input_root or r).resolve();who='tomas';out=r/f'assets/characters/named_hd/{who}';expected=json.loads((out/'sha256.json').read_text());assert len(expected)==21
for face in ['front','back','left','right']:
 im=Image.open(out/f'idle_{face}.png');assert im.size==(48,72);assert set(im.getchannel('A').tobytes())<={0,255}
 oldim=Image.open(old/f'assets/characters/{who}/idle_{face}.png').convert('RGBA').resize((48,72),Image.Resampling.NEAREST);assert im.tobytes()!=oldim.tobytes()
 m=json.loads((out/f'walk_{face}/animation.json').read_text());assert sum(f['duration_ms']for f in m['frames'])==560;assert m['artwork_pixels_per_world_pixel']==2
 images=[Image.open(out/f'walk_{face}'/f['file']).convert('RGBA')for f in m['frames']];assert len({im.tobytes()for im in images})==4
 for im in images:assert im.size==(48,72);assert set(im.getchannel('A').tobytes())<={0,255}
assert (out/'portrait.png').read_bytes()==(old/f'assets/portraits/eldenmere/{who}_neutral.png').read_bytes()
for p,h in expected.items():assert hashlib.sha256((out/p).read_bytes()).hexdigest()==h,p
subprocess.run([sys.executable,str(Path(__file__).with_name('export.py')),'--repo-root',str(r),'--legacy-input-root',str(old)],check=True)
assert json.loads((out/'sha256.json').read_text())==expected
print('PASS native identity, original portrait,4 unique phases/direction,560ms cadence,21 deterministic PNGs')
