from PIL import Image,ImageDraw,ImageChops
from pathlib import Path
import argparse
ap=argparse.ArgumentParser();ap.add_argument('--game-root',type=Path,required=True);args=ap.parse_args()
ROOT=Path(__file__).resolve().parents[3]
P=ROOT/'assets/source/characters/regional_npc_hd/regional_picker/actions_hd';M=P/'masters'
a=Image.open(args.game_root/'assets/characters/garden_workers/apple.png').convert('RGBA');a=a.resize((a.width*2,a.height*2),Image.Resampling.NEAREST)
keys=['carry_front','carry_back','carry_right','carry_left','reach_front','admire_front','lower_front','sort_right','rest_front']
board=Image.new('RGB',(800,88*len(keys)), '#777d75');d=ImageDraw.Draw(board)
for y,k in enumerate(keys):
 for i,f in enumerate(sorted(M.glob(k+'_*'))):
  im=Image.open(f).convert('RGBA'); ox,oy=(40,62)
  if k=='reach_front':ox,oy=44,32
  if k=='admire_front':ox,oy=40,40
  if k=='lower_front':ox,oy=40,round(40+22*i/3)
  if k!='rest_front':
   prop=Image.new('RGBA',im.size);prop.alpha_composite(a,(ox-a.width//2,oy-a.height))
   if k=='carry_back':prop.alpha_composite(im);im=prop
   else:im.alpha_composite(prop)
  board.paste(im,(i*80,y*88),im)
 d.text((645,y*88+25),k,fill='white')
board.resize((1600,1584),Image.Resampling.NEAREST).save(Path(__file__).with_name('prop_context_2x.png'))
l=Image.open(P/'references/idle_left.png');r=Image.open(P/'references/idle_right.png').transpose(Image.Transpose.FLIP_LEFT_RIGHT)
print('profile symmetry bytes',l.tobytes()==r.tobytes())
