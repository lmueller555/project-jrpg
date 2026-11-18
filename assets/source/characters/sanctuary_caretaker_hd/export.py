"""Uniform sampling and registration of complete caregiver drawings."""
from PIL import Image
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];SRC=Path(__file__).parent
OUT=ROOT/'assets/characters/named_hd/sanctuary_caretaker'
def read(n):
 im=Image.open(SRC/n).convert('RGBA');im.putalpha(im.getchannel('A').point(lambda a:255 if a>=190 else 0));return im

def export():
 OUT.mkdir(parents=True,exist_ok=True)
 im=read('identity_master.png')
 crops=[]
 for i in range(4):
  p=im.crop((i*im.width//4,0,(i+1)*im.width//4,im.height));crops.append(p.crop(p.getbbox()))
 factor=60/crops[0].height
 for name,p in zip(['front','back','left','right'],crops):
  p=p.resize((round(p.width*factor),round(p.height*factor)),Image.Resampling.NEAREST);c=Image.new('RGBA',(48,72));c.alpha_composite(p,((48-p.width)//2,68-p.height));c.save(OUT/f'idle_{name}.png')
 im=read('unhook_master.png');frames=[]
 for i in range(12):
  col=i%4;row=i//4;p=im.crop((col*im.width//4,row*im.height//3,(col+1)*im.width//4,(row+1)*im.height//3));frames.append(p.crop(p.getbbox()))
 factor=60/frames[0].height
 (OUT/'unhook').mkdir(exist_ok=True)
 for i,p in enumerate(frames+[frames[-1]]*4):
  p=p.resize((round(p.width*factor),round(p.height*factor)),Image.Resampling.NEAREST)
  # Fixed back-of-body line; forward reach changes crop width, never body origin.
  c=Image.new('RGBA',(80,96));c.alpha_composite(p,(50-p.width,88-p.height));c.save(OUT/'unhook'/f'frame_{i:02}.png')
if __name__=='__main__':export()
