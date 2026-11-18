from pathlib import Path
from PIL import Image
import argparse,json,hashlib
from export import export,BASE
p=argparse.ArgumentParser();p.add_argument('--repo-root',required=True,type=Path);p.add_argument('--input-root',type=Path);a=p.parse_args();r=a.repo_root.resolve();old=(a.input_root or r).resolve();out=r/BASE;m=json.loads((out/'actor.json').read_text());orig=json.loads((old/'assets/story/sanctuary_rescue/art.json').read_text())['actors']['worker'];reg=json.loads((out/'registration.json').read_text())['frames'];lookup={f['legacy_file']:f['file']for f in reg}
assert m['anchor']==orig['anchor']==[20,34];assert m['frame_size']==orig['frame_size']==[40,40];assert m['travel_artwork_pixels_per_world_pixel']==2
for d,fs in m['walks'].items():
 assert m['idles'][d]==lookup[orig['idles'][d]]
 assert [f['duration_ms']for f in fs]==[f['duration_ms']for f in orig['walks'][d]]==[220]*4
 assert len({(r/f['file']).read_bytes()for f in fs})==4
for name,pose in m['poses'].items():
 assert pose['anchor']==orig['poses'][name]['anchor'];assert pose['loop']==orig['poses'][name]['loop'];assert pose['artwork_pixels_per_world_pixel']==2
 assert pose['frames']==[{**f,'file':lookup[f['file']]}for f in orig['poses'][name]['frames']]
for rec in reg:
 im=Image.open(r/rec['file']);assert im.size==(80,80);assert set(im.getchannel('A').tobytes())<={0,255};legacy=Image.open(old/rec['legacy_file']).convert('RGBA').resize((80,80),Image.Resampling.NEAREST);assert im.tobytes()!=legacy.tobytes()
expected=json.loads((out/'sha256.json').read_text());assert len(expected)==24
for path,h in expected.items():assert hashlib.sha256((r/path).read_bytes()).hexdigest()==h
assert export(r,old)==expected
print('PASS23 native frames,original portrait,exact anchors/tempo/poses,24 reproducible PNGs')
