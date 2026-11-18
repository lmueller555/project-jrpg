"""Rasterize explicit native Tomas activity drawings; dormant, no live bindings.

Literal whole-pose plans preserve the named bank's face and material identity.
No legacy sprite enlargement, skeleton solve, rotated limb strips or mirroring.
Regent cinematic keys are audited and explicitly retained without changes.
"""
from pathlib import Path
import json,hashlib,argparse,io
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'assets/source/characters/tomas/activity_hd'
TARGET=ROOT/'assets/characters/tomas/activity_hd'
CANONICAL=ROOT/'assets/characters/named_hd/tomas'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def encode(im):
 b=io.BytesIO();im.save(b,format='PNG');return b.getvalue()
def document(d):return (json.dumps(d,indent=2)+'\n').encode()
def shapes(im,items,offset):
 d=ImageDraw.Draw(im)
 for s in items:
  points=[(x+offset[0],y+offset[1]) for x,y in s['points']]
  if s.get('line'):d.line(points,fill=s['fill'],width=1)
  else:d.polygon(points,fill=s['fill'],outline=s.get('outline'))
def draw(p):
 im=Image.new('RGBA',p['size']);offset=p['offset']
 base=Image.open(CANONICAL/f"idle_{p['face']}.png").convert('RGBA')
 if p.get('idle'):im.alpha_composite(base,offset);return im
 shapes(im,p.get('under',[]),offset)
 if p.get('native_legs'):im.alpha_composite(base.crop((0,50,48,72)),(offset[0],offset[1]+50))
 shapes(im,p['shapes'],offset)
 dx,dy=p.get('head_shift',[0,0]);im.alpha_composite(base.crop((0,0,48,30)),(offset[0]+dx,offset[1]+dy))
 return im

def outputs():
 out={};plans=json.loads((SOURCE/'drawings.json').read_text())
 for name,p in plans.items():out[TARGET/name]=encode(draw(p))
 props=json.loads((SOURCE/'props.json').read_text())
 for name,size in [('bundle',(18,14)),('mechanism',(26,34)),('sack',(32,36))]:
  im=Image.new('RGBA',size);shapes(im,props[name],(0,0));out[TARGET/('sack/sack.png' if name=='sack' else f'routines/props/{name}.png')]=encode(im)
 stack=Image.new('RGBA',(32,20));shapes(stack,props['bundle'],(2,6));shapes(stack,props['bundle'],(10,0));out[TARGET/'routines/props/stack.png']=encode(stack)
 # The storage box is environmental dressing, not an actor-owned pose; existing
 # world HD prop is retained and not overwritten by this dormant package.
 old=json.loads((ROOT/'assets/characters/tomas/routines/animations.json').read_text())
 old.update(artwork_pixels_per_world_pixel=2,logical_size=[64,48],frame_size=[128,96],status='dormant_native_activity')
 out[TARGET/'routines/animations.json']=document(old)
 opening=ROOT/'assets/story/sanctuary_opening/poses'
 for folder in ('tomas_sit','tomas_stand','tomas_eat','tomas_plate_push'):
  p=opening/folder/'animation.json'
  if p.exists():
   data=json.loads(p.read_text());data.update(artwork_pixels_per_world_pixel=2,logical_size=[24,36],frame_size=[48,72]);out[TARGET/f'breakfast/{folder}/animation.json']=document(data)
 out[TARGET/'breakfast/art.json']=document(dict(artwork_pixels_per_world_pixel=2,logical_size=[24,36],frame_size=[48,72],draw_anchor=[12,30],poses=[n.removeprefix('breakfast/') for n in plans if n.startswith('breakfast/')]))
 sack=json.loads((ROOT/'assets/story/halden/art.json').read_text());sack.update(artwork_pixels_per_world_pixel=2,logical_size=[32,40],frame_size=[64,80],carry_canvas=[32,40],artwork_carry_canvas=[64,80]);out[TARGET/'sack/art.json']=document(sack)
 # Approved cinematic originals have their own projection and sufficiently
 # detailed source at actual scene scales. Preserve them byte-for-byte in place;
 # do not relabel their density or make an incidental costume correction.
 cinema=ROOT/'assets/story/regent_arrival/actors/tomas'
 out[TARGET/'cinematic_audit.json']=document({'decision':'retain_originals_in_place',
     'reason':'Distinct cinematic projection; existing approved 80x96 bank remains unchanged.',
     'files':{p.relative_to(ROOT).as_posix():sha(p) for p in sorted(cinema.glob('*')) if p.is_file()}})
 # Contact boards are native frames at 2x display enlargement for inspection.
 for bank in ('routines','breakfast','sack'):
  files=[p for p in out if p.suffix=='.png' and p.relative_to(TARGET).parts[0]==bank and 'props' not in p.parts]
  cell=(160,110) if bank=='routines' else (80,90) if bank in ('breakfast','sack') else (170,202)
  board=Image.new('RGB',(cell[0]*8,cell[1]*((len(files)+7)//8)),'#64736b');d=ImageDraw.Draw(board)
  for i,p in enumerate(files):
   im=Image.open(io.BytesIO(out[p]));x=(i%8)*cell[0];y=(i//8)*cell[1];board.paste(im,(x,y),im);d.text((x,y+cell[1]-12),p.parent.name[:8]+'/'+p.stem[-2:],fill='#ffffff')
  out[TARGET/f'{bank}/review.png']=encode(board)
 # Normal and half-speed reviews preserve authored per-frame durations.
 clips={}
 routine=json.loads(out[TARGET/'routines/animations.json'])
 for name,record in routine['animations'].items():clips['routines/'+name]=[(TARGET/'routines'/f['file'],f['duration_ms']) for f in record['frames']]
 for direction,frames in routine['walk_sets']['bundle'].items():clips['routines/carry_'+direction]=[(TARGET/'routines'/f['file'],f['duration_ms']) for f in frames]
 for name in ('tomas_eat','tomas_sit','tomas_stand'):
  meta=json.loads(out[TARGET/f'breakfast/{name}/animation.json']);clips['breakfast/'+name]=[(TARGET/f'breakfast/{name}'/f['file'],f['duration_ms']) for f in meta['frames']]
 clips['breakfast/tomas_plate_push']=[(TARGET/f'breakfast/tomas_plate_push/frame_{i:02}.png',180) for i in range(1,5)]
 for face in ('front','back','left','right'):
  for name,ms in [('carry',140),('lift',180)]:clips[f'sack/{name}_{face}']=[(TARGET/f'sack/{name}_{face}_{i}.png',ms) for i in range(4)]
 for name,frames in clips.items():
  for speed in (1,2):
   images=[]
   for path,ms in frames:
    im=Image.open(io.BytesIO(out[path])).convert('RGBA');bg=Image.new('RGBA',im.size,'#64736b');bg.alpha_composite(im)
    images.append(bg.convert('RGB').resize((im.width*2,im.height*2),Image.Resampling.NEAREST))
   buffer=io.BytesIO();images[0].save(buffer,format='GIF',save_all=True,append_images=images[1:],duration=[ms*speed for _,ms in frames],loop=0,disposal=2)
   out[TARGET/f'reviews/{name.replace("/","_")}_{"normal" if speed==1 else "half"}.gif']=buffer.getvalue()
 provenance={'version':1,'status':'dormant','exporter':'tools/export_tomas_activity_hd.py','canonical_idles':{p.name:sha(p) for p in CANONICAL.glob('idle_*.png')},'drawings_sha256':sha(SOURCE/'drawings.json'),'exports':{p.relative_to(TARGET).as_posix():hashlib.sha256(v).hexdigest() for p,v in out.items()}}
 out[TARGET/'provenance.json']=document(provenance)
 return out
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');a=parser.parse_args()
 for p,data in outputs().items():
  if a.check:
   if not p.exists() or p.read_bytes()!=data:raise SystemExit('Export differs: '+str(p))
  else:p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
