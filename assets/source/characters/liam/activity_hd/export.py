"""Export Liam's literal native activity drawings. Pillow only; no rig or image warp.
python assets/source/characters/liam/activity_hd/export.py --repo-root .
Legacy prop layers are deliberately reused without redesign. Actors are native HD.
"""
from pathlib import Path
import argparse,json,hashlib
from PIL import Image,ImageDraw
SRC=Path(__file__).resolve().parent

def render(f,refs,size):
 idle=Image.open(refs/f"idle_{f['face']}.png").convert('RGBA');im=Image.new('RGBA',size);off=tuple(f.get('offset',[104,72]));draw=ImageDraw.Draw(im)
 if f['kind']=='idle':im.alpha_composite(idle,off)
 elif f['kind']=='sleep':
  head=idle.crop((12,18,36,41))
  if f['closed']:
   q=ImageDraw.Draw(head)
   for x in (10,17):q.rectangle((x,15,x+1,17),fill='#f0b87e');q.line((x-1,16,x+1,16),fill='#c78053')
  im.alpha_composite(head,off)
 else:
  for sh in f['shapes']:
   pts=[(x+off[0],y+off[1]) if f.get('local_shapes') else (x,y) for x,y in sh['points']]
   if sh['kind']=='polygon':draw.polygon(pts,fill=sh['fill'],outline=sh.get('outline'))
   else:draw.line(pts,fill=sh['fill'],width=sh.get('width',1))
  dx,dy=f['head_shift'];im.alpha_composite(idle.crop((0,0,48,41)),(off[0]+dx,off[1]+dy))
 return im

def export(root,inputs=None):
 inputs=inputs or root;refs=root/'assets/characters/named_hd/liam';d=json.loads((SRC/'drawings.json').read_text());out=root/'assets/characters/liam/activity_hd';hashes={}
 def save(im,path):
  path.parent.mkdir(parents=True,exist_ok=True);im.save(path);hashes[str(path.relative_to(root))]=hashlib.sha256(path.read_bytes()).hexdigest()
 for bank in ('block_play','play_routine'):
  for action,frames in d[bank].items():
   for i,f in enumerate(frames):save(render(f,refs,(192,192)),out/bank/action/f'frame_{i+1:02}.png')
  p=out/bank/'animations.json';p.write_text((SRC/f'{bank}_manifest.json').read_text())
 for bank,new in [('poses','lantern_assembly'),('rest_poses','lantern_rest'),('finish_poses','lantern_finish')]:
  old=inputs/f'assets/story/lantern/{bank}';oldsheet=Image.open(old/'liam.png');sheet=Image.new('RGBA',(oldsheet.width*2,oldsheet.height*2))
  props=[]
  for name in ('frame','extras'):
   p=old/f'liam_{name}.png'
   if p.exists():props.append(Image.open(p).convert('RGBA'))
  for f in d['lantern'][bank]:
   x,y,w,h=f['rect'];actor=render(f,refs,(w*2,h*2));tile=Image.new('RGBA',actor.size)
   layers=[p.crop((x,y,x+w,y+h)).resize((w*2,h*2),Image.Resampling.NEAREST) for p in props]
   # Far-side lantern on rear carries is hidden by actor; all other props foreground.
   if f['face']=='back':
    for p in layers:tile.alpha_composite(p)
    tile.alpha_composite(actor)
   else:
    tile.alpha_composite(actor)
    for p in layers:tile.alpha_composite(p)
   sheet.alpha_composite(tile,(x*2,y*2))
  save(sheet,out/new/'liam.png');(out/new/'liam.json').write_text((SRC/f'{new}_manifest.json').read_text())
 (out/'sha256.json').write_text(json.dumps(hashes,indent=2)+'\n')
 return hashes
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--repo-root',type=Path,required=True);p.add_argument('--legacy-input-root',type=Path);a=p.parse_args();print('Exported',len(export(a.repo_root.resolve(),a.legacy_input_root.resolve() if a.legacy_input_root else None)),'native PNGs')
