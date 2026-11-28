"""Native camera proofs, fixed crops about declared ground root; no size fitting."""
from pathlib import Path
import json,sys
from PIL import Image,ImageDraw
R=Path('/workspace/project-jrpg');sys.path.insert(0,str(R));from cinematic_bridge_ascent import actor_states_at
P=Path(__file__).resolve().parent.parent
rows=json.loads((P/'registered_atlases/registration_report.json').read_text());mapping={r['index']:r for r in rows if r['kind']=='transition'}
entries=json.loads((P/'entry/selection.json').read_text());mapping.update({r['index']:r for r in entries})
mapping[26]=json.loads((P/'registered_samples/entry_026_close_model_registration.json').read_text())
indices=[24,25,26,28,30,32,34,36,38,40] if len(sys.argv)<2 else [int(x) for x in sys.argv[1:]]
sheet=Image.new('RGB',(5*320,((len(indices)+4)//5)*400),'#283a49');d=ImageDraw.Draw(sheet)
for n,i in enumerate(indices):
 r=mapping[i];a=next(a for a in actor_states_at(i/60)['runners'] if a['id']=='crown_soldier');im=Image.open(P/r['file']).convert('RGBA');im.putalpha(im.getchannel('A').point(lambda x:0 if x<=16 else x));scale=a['pixels_per_metre']/r['art_pixels_per_metre'];im=im.convert('RGBa').resize((round(im.width*scale),round(im.height*scale)),Image.Resampling.LANCZOS).convert('RGBA');f=Image.new('RGBA',(960,640),'#283a49');at=[round(a['ground_anchor'][j]-r['anchor'][j]*scale) for j in range(2)];f.alpha_composite(im,at);x,y=map(round,a['ground_anchor']);crop=f.crop((x-160,y-330,x+160,y+70));sheet.paste(crop.convert('RGB'),(n%5*320,n//5*400));d.text((n%5*320+5,n//5*400+5),f"tick{i} phase{a['frame_index']} el{a['view_elevation_degrees']:.1f}",fill='white');f.convert('RGB').save(f'/tmp/crown_ascent_latest_native_{i:03d}.png')
sheet.save('/tmp/crown_ascent_latest_native_join.jpg')

