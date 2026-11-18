"""Re-sample retained approved large directional masters at native 2x density.
This is not enlargement of old sprites. Material ranges are inherited from
the original export; new samples retain detailed contours in the master.
"""
from pathlib import Path
from PIL import Image,ImageDraw
import json,sys,copy,hashlib
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'assets/characters').is_dir())
sys.path.insert(0,str(ROOT/'tools'))
from build_tomas_idle import sample_source
def build(identity):
 src=ROOT/'assets/source/characters/liam_family'
 out=ROOT/f'assets/characters/named_hd/{identity}';out.mkdir(parents=True,exist_ok=True)
 recs={'front':json.loads((src/'export.json').read_text())['characters'][identity]}
 recs.update(json.loads((src/'turnaround_export.json').read_text())['characters'][identity])
 palette=json.loads((ROOT/f'assets/characters/{identity}/palette.json').read_text())
 source_records={}
 for d,r in recs.items():
  r=copy.deepcopy(r);r['frame_size']=[48,72]
  r['occupied_rect']=[v*2 for v in r['occupied_rect']]
  for band in r['bands']:band['native_y']=[v*2 for v in band['native_y']]
  # Native face is authored in master; tiny old 1px pupil landmarks are not enlarged.
  eyes=r['eyes']['top_pixels'];r['eyes']['top_pixels']=[]
  filename='front_idle_concepts.png' if d=='front' else 'turnaround_concepts.png'
  source=Image.open(src/filename).convert('RGBA')
  im=sample_source(source,r,palette)
  dr=ImageDraw.Draw(im)
  for x,y in eyes:
   x*=2;y*=2
   dr.point((x,y),fill=palette['eyes']['pupil']);dr.point((x,y+1),fill=palette['eyes']['iris'])
  im.save(out/f'idle_{d}.png')
  source_records[d]={'source':(src/filename).relative_to(ROOT).as_posix(),'sha256':hashlib.sha256((src/filename).read_bytes()).hexdigest(),'recipe':r,'native_eye_points':{'pupil':[[x*2,y*2] for x,y in eyes],'iris':[[x*2,y*2+1] for x,y in eyes]}}
 (ROOT/f'assets/source/characters/named_hd/{identity}/idle_recipe.json').write_text(json.dumps(source_records,indent=2)+'\n')
 return out
if __name__=='__main__':
 for name in sys.argv[1:] or [Path(__file__).parent.name]:build(name)
