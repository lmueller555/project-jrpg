"""Read-only authoring diagnostic: selected47 against unchanged runtime46/0.

The production compositor and root review own native/composed acceptance.
"""
from pathlib import Path
from hashlib import sha256
import json,sys
from PIL import Image,ImageDraw
P=Path(__file__).resolve().parent;ROOT=P.parents[7];sys.path.insert(0,str(ROOT))
from cinematic_bridge_ascent import actor_states_at
old=ROOT/'assets/story/fire_veinhold_opening/shot08/characters/lucan'
r=next(f for f in json.loads((P/'selection.json').read_text())['frames'] if f['phase']==47)
im=Image.open(P/r['source']).convert('RGBA');im.putalpha(im.getchannel('A').point(lambda a:0 if a<=16 else a))
im=im.convert('RGBa').resize((round(im.width*r['uniform_scale']),round(im.height*r['uniform_scale'])),Image.Resampling.LANCZOS).convert('RGBA')
new=Image.new('RGBA',(1024,1536));origin=[512-r['crown_center'][0]*r['uniform_scale'],1040-r['crown_center'][1]*r['uniform_scale']]
new.alpha_composite(im,tuple(round(v) for v in origin));state=actor_states_at(2.2)['runners'][0];scale=state['scale'];binding=[]
sheet=Image.new('RGB',(1440,900),'#203040');d=ImageDraw.Draw(sheet)
for c,(label,phase,fig) in enumerate((('unchanged46',46,Image.open(old/'overhead_046.png').convert('RGBA')),('selected47',47,new),('unchanged0',0,Image.open(old/'overhead_000.png').convert('RGBA')))):
 fixed=Image.new('RGBA',(960,640),'#203040');thumb=fig.convert('RGBa').resize((round(fig.width*scale),round(fig.height*scale)),Image.Resampling.LANCZOS).convert('RGBA')
 fixed.alpha_composite(thumb,(round(state['ground_anchor'][0]-512*scale),round(state['ground_anchor'][1]-960*scale)))
 fixed.convert('RGB').save(P/f'seam_native_{label}.png');sheet.paste(fixed.convert('RGB').resize((480,320)),(c*480,0));d.text((c*480+6,5),label+' fixed2.2s native (half-display)',fill='white')
 crop=fig.crop((256,736,800,1280));bg=Image.new('RGBA',crop.size,'#203040');bg.alpha_composite(crop);bg=bg.convert('RGB');bg.thumbnail((470,550));sheet.paste(bg,(c*480,345))
 d.text((c*480+6,326),'SOURCE500ppm fixedcrop, no silhouettefit',fill='white')
 binding.append({'label':label,'phase':phase,'native_pixels_per_metre':state['pixels_per_metre'],'complete_rgba_sha256':sha256(fig.tobytes()).hexdigest()})
sheet.save(P/'seam_46_47_0_final_review.jpg',quality=96)
(P/'seam_46_47_0_final_binding.json').write_text(json.dumps({'camera_time':2.2,'selection_sha256':sha256((P/'selection.json').read_bytes()).hexdigest(),'new47_registration':{'uniform_scale':r['uniform_scale'],'origin':origin,'observed_crown_center':r['crown_center']},'frames':binding,'purpose':'Authoring diagnostic only; parent production compositor/native acceptance remains authoritative.'},indent=2)+'\n')
