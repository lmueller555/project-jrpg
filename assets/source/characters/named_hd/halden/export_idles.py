"""Registered native export of the retained four-view generated source."""
from PIL import Image
from pathlib import Path
import json
P=Path(__file__).parent;ROOT=P.parents[4];OUT=ROOT/'assets/characters/named_hd'/P.name
m=json.loads((P/'idle_export.json').read_text());master=Image.open(P/m['source']).convert('RGBA')
for face,box in m['bounds'].items():
 im=master.crop(box);im.putalpha(im.getchannel('A').point(lambda a:255 if a>=m['alpha_threshold'] else 0))
 im=im.resize((round(im.width*m['scale']),round(im.height*m['scale'])),Image.Resampling.NEAREST)
 out=Image.new('RGBA',(48,72));out.alpha_composite(im,((48-im.width)//2,2));out.save(OUT/f'idle_{face}.png')
