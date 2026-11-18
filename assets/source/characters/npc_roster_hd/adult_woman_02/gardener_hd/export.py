"""Rasterize complete native action pose drawing records. No limb rig or image warps.
Usage: python export.py REPO_ROOT
"""
from pathlib import Path
import sys,json,hashlib
from PIL import Image,ImageDraw
S=Path(__file__).resolve().parent
ROOT=Path(sys.argv[1]).resolve()
OUT=ROOT/'assets/characters/npc_roster_hd/adult_woman_02/gardener_hd'
OUT.mkdir(parents=True,exist_ok=True)
inputs=ROOT/'assets/characters/npc_roster_hd/adult_woman_02'
old=ROOT/'assets/characters/npcs/female_02/gardener/animations.json'
m=json.loads(old.read_text());drawings=json.loads((S/'drawings.json').read_text())
for name,pose in drawings['poses'].items():
 face=pose['direction'];idle=Image.open(inputs/f'idle_{face}.png').convert('RGBA')
 im=Image.new('RGBA',(96,96));d=ImageDraw.Draw(im)
 if pose.get('full_idle'):im.alpha_composite(idle,(24,12))
 else:
  for shape in pose['shapes']:
   args={'fill':shape['fill']};points=list(map(tuple,shape['points']))
   if shape['kind']=='polygon':d.polygon(points,outline=shape.get('outline'),**args)
   else:d.line(points,width=shape.get('width',1),**args)
  im.alpha_composite(idle.crop(tuple(pose['head_crop'])),tuple(pose['head_xy']))
 im.save(OUT/(name+'.png'))
 m['poses'][name]['body']=name+'.png'
 m['poses'][name]['sha256']=hashlib.sha256((OUT/(name+'.png')).read_bytes()).hexdigest()
m['bucket_bank']='assets/characters/npcs/female_02/gardener'
m.update(character='adult_woman_02',status='integrated',artwork_pixels_per_world_pixel=2,body_artwork_size=[96,96],body_logical_size=[48,48],source_recipe='assets/source/characters/npc_roster_hd/adult_woman_02/gardener_hd/drawings.json',coordinate_units='logical_world_pixels')
(OUT/'animations.json').write_text(json.dumps(m,indent=2)+'\n')
print('Exported',len(drawings['poses']),'complete native bodies')
