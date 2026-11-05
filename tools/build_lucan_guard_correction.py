"""Register the authored enemy-facing guard without changing any held views."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys
from statistics import median
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.build_ice_reaper_continuity_views import register, remove_detached_cell_bleed
SOURCE=ROOT/'assets/source/cinematics/ice_reaper_guard_correction/lucan_enemy_facing_generated.png'
TARGET=ROOT/'assets/story/ice_reaper_continuity/actors/lucan'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def build():
 source=Image.open(SOURCE).convert('RGBA');cells=[]
 for row in range(2):
  for col in range(8):
   box=(round(col*source.width/8),round(row*source.height/2),round((col+1)*source.width/8),round((row+1)*source.height/2))
   image=source.crop(box);image.putalpha(image.getchannel('A').point(lambda a:255 if a>=140 else 0));image=remove_detached_cell_bleed(image)
   cells.append((image,box))
 raised=[cells[i][0].getbbox()[3]-cells[i][0].getbbox()[1] for i in [5,6,7,8,9,10,11,12,13]]
 scale=88/median(raised)
 m=json.loads((TARGET/'animation.json').read_text());records=[]
 for action,indices,duration in [('brace_rear_left',range(8),180),('impact_rear_left',range(8,14),117)]:
  frames=[]
  for index,cell in enumerate(indices,1):
   image,box=cells[cell];frame,registration=register(image,scale,(128,128),(64,116))
   filename=f'{action}_{index:02}.png';frame.save(TARGET/filename,optimize=True)
   frames.append({'file':filename,'duration_ms':duration})
   records.append({'file':filename,'source':str(SOURCE.relative_to(ROOT)),'source_cell':cell,'source_box':list(box),'sha256':sha(TARGET/filename),**registration})
  m['animations'][action]['frames']=frames
  m['animations'][action]['facing_note']='Authored rear quarter: back of head toward viewer, gaze up-right toward the Ice Reaper, left-arm shield overhead; remains kneeling through impact.'
 (TARGET/'animation.json').write_text(json.dumps(m,indent=2)+'\n')
 p=TARGET/'provenance.json';d=json.loads(p.read_text());replaced={r['file'] for r in records};d['frames']=[r for r in d['frames'] if r['file'] not in replaced]+records
 d['sources'][str(SOURCE.relative_to(ROOT))]=sha(SOURCE)
 d['guard_correction']={'review':'awaiting_user_review','source':str(SOURCE.relative_to(ROOT)),'source_sha256':sha(SOURCE),'operation':'Authored frame extraction, alpha cleanup, uniform nearest scaling and foot registration. No mirroring or body deformation. Late held views are untouched.'}
 p.write_text(json.dumps(d,indent=2)+'\n')
 print(json.dumps({'frames':len(records),'uniform_scale':scale,'late_held_views':'unchanged'}))
if __name__=='__main__':build()
