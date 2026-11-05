"""Register authored forward shield defense; preserve every approved held view.

The fourteen drawings are image_gen authored, then cell-extracted, alpha-cleaned,
nearest scaled and foot-registered. No mirroring or procedural pose deformation.
"""
from __future__ import annotations
import hashlib,json
from pathlib import Path
import sys
from statistics import median
from PIL import Image,ImageDraw
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.build_ice_reaper_continuity_views import register,remove_detached_cell_bleed
SOURCE=ROOT/'assets/source/cinematics/lucan_forward_guard'
TARGET=ROOT/'assets/story/ice_reaper_continuity/actors/lucan'
REVIEW=ROOT/'docs/reviews/lucan_forward_guard'

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def extract(file,columns,rows):
 image=Image.open(SOURCE/file).convert('RGBA');result=[]
 for row in range(rows):
  for col in range(columns):
   box=(round(col*image.width/columns),round(row*image.height/rows),round((col+1)*image.width/columns),round((row+1)*image.height/rows))
   tile=image.crop(box);arr=np.array(tile)
   alpha=arr[:,:,3]>=140
   # Bright RGB values in low-alpha empty background are not sprite content.
   # Remove only saturated red matte residue; the burgundy tabard is retained.
   red=(arr[:,:,0]>170)&(arr[:,:,1]<65)&(arr[:,:,2]<65)&(arr[:,:,0]>arr[:,:,1]*3)
   alpha &= ~red;arr[:,:,3]=(alpha*255).astype('uint8')
   tile=remove_detached_cell_bleed(Image.fromarray(arr))
   result.append((tile,box))
 return result

def build():
 m=json.loads((TARGET/'animation.json').read_text())
 untouched={key:json.dumps(value,sort_keys=True) for key,value in m['animations'].items() if not key.startswith(('brace_rear_left','impact_rear_left'))}
 held={p.name:sha(p) for p in TARGET.glob('hold_brace_*.png')}
 sheets=[('brace_rear_left','brace_generated.png',4,2,180,-120),('impact_rear_left','impact_generated.png',3,2,117,-110)]
 records=[];contacts=[]
 for action,file,cols,rows,duration,view in sheets:
  cells=extract(file,cols,rows)
  settled=cells[4:] if action=='brace_rear_left' else cells
  scale=68/median(im.getbbox()[3]-im.getbbox()[1] for im,_ in settled)
  frames=[]
  for i,(tile,box) in enumerate(cells,1):
   frame,registration=register(tile,scale,(128,128),(64,116))
   # Foot row is stable after integer nearest scaling, no per-axis deformation.
   bounds=frame.getbbox();dy=116-(bounds[3]-1)
   if dy:
    aligned=Image.new('RGBA',frame.size);aligned.alpha_composite(frame,(0,dy));frame=aligned
    registration['registration'][1]+=dy
   filename=f'{action}_{i:02}.png';frame.save(TARGET/filename,optimize=True)
   frames.append(dict(file=filename,duration_ms=duration))
   records.append(dict(file=filename,source=str((SOURCE/file).relative_to(ROOT)),source_cell=i-1,source_box=list(box),sha256=sha(TARGET/filename),**registration))
   contacts.append((filename,frame))
  entry=m['animations'][action];entry['frames']=frames
  entry['facing_note']='Rear left quarter, nape toward viewer and gaze up-right toward Ice Reaper. Left elbow bent forward; shield interior and rim held ahead of face toward incoming shard. Right sword arm stays low. Kneeling guard maintained through impact.'
  entry['view_azimuth_deg']=view
 (TARGET/'animation.json').write_text(json.dumps(m,indent=2)+'\n')
 p=TARGET/'provenance.json';d=json.loads(p.read_text());replaced={r['file'] for r in records};d['frames']=[r for r in d['frames'] if r['file'] not in replaced]+records
 for _,file,_,_,_,_ in sheets:d['sources'][str((SOURCE/file).relative_to(ROOT))]=sha(SOURCE/file)
 d['guard_correction']=dict(native_guard_geometry=dict(reference_file='impact_rear_left_01.png',face_center=[73,61],shield_center=[81,66],shield_contact_upper_rim=[85,54],shield_polygon=[[79,51],[84,51],[88,54],[89,61],[87,70],[83,76],[78,82],[74,79],[76,70],[76,60],[76,55]]),review='awaiting_user_review',sources={str((SOURCE/f).relative_to(ROOT)):sha(SOURCE/f) for f in ('brace_generated.png','impact_generated.png')},operation=__doc__.strip(),protected_held_views_unchanged=True)
 p.write_text(json.dumps(d,indent=2)+'\n')
 for key,value in untouched.items():assert json.dumps(m['animations'][key],sort_keys=True)==value,key
 for file,h in held.items():assert sha(TARGET/file)==h,file
 REVIEW.mkdir(parents=True,exist_ok=True)
 sheet=Image.new('RGB',(128*8*3,148*2*3),(18,27,35));draw=ImageDraw.Draw(sheet)
 for i,(name,frame) in enumerate(contacts):
  row=0 if i<8 else 1;col=i if i<8 else i-8;x=col*384;y=row*444
  big=frame.resize((384,384),Image.Resampling.NEAREST);sheet.paste(big,(x,y),big);draw.text((x+4,y+392),name,fill='white')
 sheet.save(REVIEW/'native_contact_sheet.png',optimize=True)
 print(json.dumps(dict(frames=len(records),held_views='byte-identical',review=str(REVIEW/'native_contact_sheet.png'))))
if __name__=='__main__':build()
