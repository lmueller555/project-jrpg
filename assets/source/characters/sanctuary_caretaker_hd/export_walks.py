from pathlib import Path
import importlib.util,json
from PIL import Image
SRC=Path(__file__).parent;ROOT=SRC.parents[3];OUT=ROOT/'assets/characters/named_hd/sanctuary_caretaker'
for face in ['front','back','left','right']:
 spec=importlib.util.spec_from_file_location(face,SRC/f'walk_{face}.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 out=OUT/f'walk_{face}';out.mkdir(exist_ok=True);frames=[];sheet=Image.new('RGBA',(384,72))
 for i,k in enumerate(m.K):
  im=m.draw(k);im.save(out/f'frame_{i:02}.png');sheet.alpha_composite(im,(i*48,0));frames.append(im)
 sheet.save(out/'spritesheet.png')
 for fn,ms in [('normal.gif',70),('half_speed.gif',140)]:
  bg=[]
  for im in frames:
   c=Image.new('RGBA',(48,72),'#65705d');c.alpha_composite(im);bg.append(c.convert('RGB').resize((144,216),Image.Resampling.NEAREST))
  bg[0].save(out/fn,save_all=True,append_images=bg[1:],duration=ms,loop=0)
