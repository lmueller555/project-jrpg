"""Validate the frozen complete native drawings; --repo-root supplies canon refs."""
from pathlib import Path
from PIL import Image
import argparse,hashlib,json,subprocess,sys
p=argparse.ArgumentParser();p.add_argument('--repo-root',type=Path,required=True);a=p.parse_args()
s=Path(__file__).resolve().parent;recipe=json.loads((s/'recipe.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
legacy=json.loads((a.repo_root/'assets/characters/bridge_workers/mason/animation.json').read_text())
expected={'poses/'+f['file'] for seq in legacy['sequences'].values() for f in seq['frames']}
assert set(recipe['refined_masters'])==expected
before={k:sha(s/v['file']) for k,v in recipe['refined_masters'].items()}
subprocess.run([sys.executable,str(s/'export_refined.py')],check=True)
for key,record in recipe['refined_masters'].items():
 im=Image.open(s/record['file']).convert('RGBA');assert im.size==(96,104)
 assert set(im.getchannel('A').getdata())=={0,255}
 x0,y0,x1,y1=im.getbbox();assert 0<x0<x1<96 and 0<y0<y1<104
 assert sha(s/record['file'])==before[key]==record['sha256']
for record in recipe['reference_dependencies']:assert sha(a.repo_root/record['file'])==record['sha256']
for direction in ('front','back','left','right'):
 assert len({before[f'poses/carry_{direction}_{i}.png'] for i in range(4)})==4
 ref=Image.open(a.repo_root/f'assets/characters/npc_roster_hd/adult_man_01/idle_{direction}.png').convert('RGBA')
 out=Image.open(s/f'refined_masters/hold_{direction}_0.png').convert('RGBA')
 for y in range(27):
  for x in range(48):
   if ref.getpixel((x,y))[3]:assert ref.getpixel((x,y))==out.getpixel((x+24,y+23))
print('PASS:85 exact filenames and exports, density/alpha/bounds, approved reference hashes, four head identities and four-phase gaits')
