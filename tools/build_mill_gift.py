"""Register image-authored workshop, gearblade components and eight handoff drawings.

Only equal-cell extraction, alpha cleanup and uniform nearest-neighbor scaling
are applied. Actor poses are fully authored; no mirroring or joint deformation.
"""
from pathlib import Path
from statistics import median
import hashlib,json,sys,subprocess
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.build_ice_reaper_continuity_views import remove_detached_cell_bleed
SOURCE=ROOT/'assets/source/cinematics/mill_gift'
TARGET=ROOT/'assets/story/mill_gift'

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def clean(image):
 image=image.convert('RGBA');image.putalpha(image.getchannel('A').point(lambda a:255 if a>=160 else 0))
 return remove_detached_cell_bleed(image)
def fit(image,height):
 image=image.crop(image.getbbox());return image.resize((round(image.width*height/image.height),height),Image.Resampling.NEAREST)
def build():
 TARGET.mkdir(parents=True,exist_ok=True)
 audio=ROOT/'assets/audio/sfx/ice_reaper_rescue/load_shell.ogg'
 subprocess.run(['ffmpeg','-y','-v','error','-ss','0.20','-i',str(audio),'-t','0.20','-af','afade=t=in:d=0.004,afade=t=out:st=0.14:d=0.06','-c:a','libvorbis','-q:a','5',str(TARGET/'gear_click.ogg')],check=True)
 plate=Image.open(SOURCE/'workshop_generated.png').convert('RGB').resize((960,640),Image.Resampling.NEAREST)
 plate.save(TARGET/'workshop.png',optimize=True)
 source=Image.open(SOURCE/'weapon_generated.png').convert('RGBA')
 for column,(name,height) in enumerate((('blade',240),('gear',128),('blade_base',240))):
  cell=clean(source.crop((round(column*source.width/3),0,round((column+1)*source.width/3),source.height)))
  fit(cell,height).save(TARGET/(name+'.png'),optimize=True)
 source=Image.open(SOURCE/'handoff_generated.png').convert('RGBA');cells=[]
 for row in range(2):
  for col in range(4):
   box=(round(col*source.width/4),round(row*source.height/2),round((col+1)*source.width/4),round((row+1)*source.height/2))
   cells.append((clean(source.crop(box)),box))
 scale=112/median(im.getbbox()[3]-im.getbbox()[1] for im,_ in cells)
 records=[];contact=Image.new('RGB',(384*4,240*2),'#243b39');draw=ImageDraw.Draw(contact)
 for i,(cell,box) in enumerate(cells):
  bounds=cell.getbbox();resized=cell.resize((round(cell.width*scale),round(cell.height*scale)),Image.Resampling.NEAREST)
  frame=Image.new('RGBA',(256,144));offset=(128-round(cell.width*scale/2),132-round(bounds[3]*scale))
  frame.alpha_composite(resized,offset)
  filename=f'handoff_{i+1:02}.png';frame.save(TARGET/filename,optimize=True)
  records.append(dict(file=filename,source_cell=i,source_box=list(box),scale=scale,registration=list(offset),sha256=sha(TARGET/filename)))
  big=frame.resize((384,216),Image.Resampling.NEAREST);x=i%4*384;y=i//4*240
  contact.paste(big,(x,y),big);draw.text((x+5,y+220),filename,fill='white')
 contact.save(TARGET/'contact_sheet.png',optimize=True)
 hands=Image.open(SOURCE/'gear_hands_generated.png').convert('RGBA')
 hand_records=[]
 for col in range(4):
  row,column=divmod(col,2)
  box=(round(column*hands.width/2),round(row*hands.height/2),round((column+1)*hands.width/2),round((row+1)*hands.height/2))
  cell=clean(hands.crop(box));frame=cell.resize((480,320),Image.Resampling.NEAREST)
  filename=f'gear_hands_{col+1:02}.png';frame.save(TARGET/filename,optimize=True)
  hand_records.append(dict(file=filename,source_cell=col,source_box=list(box),sha256=sha(TARGET/filename)))
 sources={p.name:sha(p) for p in sorted(SOURCE.glob('*.png'))}
 manifest=dict(version=1,viewport=[480,320],plate=[960,640],pair_canvas=[256,144],pair_anchor=[128,132],
  phases=[dict(id=n,min_seconds=d) for n,d in (('reveal',3),('whole',3),('handoff',4),('gear',5),('faces',3))],
  frames=records,gear_hands=hand_records,sources=sources,audio=dict(file='gear_click.ogg',source=str(audio.relative_to(ROOT)),source_sha256=sha(audio),trim=[.2,.4],gain=.14),note=__doc__.strip())
 (TARGET/'animation.json').write_text(json.dumps(manifest,indent=2)+'\n')
 (SOURCE/'README.md').write_text('# MQ02 birthday gift cinematic\n\nImage-authored sources preserve the workshop facade and approved Caelan/Mira costume references. The weapon has a fixed grip, brass selector gear and four green/blue/red/white gems.\n\nRebuild exports with `python tools/build_mill_gift.py`. The eight paired handoff poses and four wide hand-detail frames are original drawings. Runtime selects the authored drawings and pans the camera; it does not warp bodies or demonstrate a successful elemental spell. The whole-blade and detached mechanical components are retained for consistent weapon exports. Gear feedback uses a quiet 0.20–0.40 second trim of the existing load_shell.ogg effect, whose source attribution remains in assets/audio/sfx/ice_reaper_rescue/README.md.\n')
 print(json.dumps(dict(frames=len(records),sources=sources)))
if __name__=='__main__':build()
