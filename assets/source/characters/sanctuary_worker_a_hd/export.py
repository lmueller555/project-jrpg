"""Sample whole drawings uniformly; never transform individual limbs."""
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[4];SRC=Path(__file__).parent
OUT=ROOT/'assets/characters/named_hd/sanctuary_worker_a'
def read(name):
 im=Image.open(SRC/name).convert('RGBA');im.putalpha(im.getchannel('A').point(lambda a:255 if a>=190 else 0));return im

def export():
 OUT.mkdir(parents=True,exist_ok=True)
 im=read('identity_master.png');ranges=[(0,430),(430,780),(780,1120),(1120,1480),(1480,im.width)]
 crops=[im.crop((a,0,b,im.height)) for a,b in ranges];crops=[p.crop(p.getbbox()) for p in crops];factor=60/crops[0].height
 for name,p in zip(['idle_front','idle_back','idle_left','idle_right','injured'],crops):
  p=p.resize((round(p.width*factor),round(p.height*factor)),Image.Resampling.NEAREST)
  canvas=Image.new('RGBA',(48,72));canvas.alpha_composite(p,((48-p.width)//2,68-p.height));canvas.save(OUT/f'{name}.png')
 injured_height=round(crops[4].height*factor)
 im=read('offer_master.png');frames=[]
 for i in range(8):
  col=i%4;row=i//4;p=im.crop((col*im.width//4,row*im.height//2,(col+1)*im.width//4,(row+1)*im.height//2));frames.append(p.crop(p.getbbox()))
 factor=injured_height/frames[0].height
 for i,p in enumerate(frames):
  p=p.resize((round(p.width*factor),round(p.height*factor)),Image.Resampling.NEAREST)
  canvas=Image.new('RGBA',(128,128));canvas.alpha_composite(p,(50,88-p.height))
  for name,n in [('offer_arm',i),('arm_rest',7-i)]:
   (OUT/name).mkdir(exist_ok=True);canvas.save(OUT/name/f'frame_{n:02}.png')
if __name__=='__main__':export()
