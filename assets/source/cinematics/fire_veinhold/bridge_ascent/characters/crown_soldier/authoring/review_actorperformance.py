"""Actual manifest/camera review. Fixed root crops; no occupied-size fitting."""
from pathlib import Path
import json,sys
from PIL import Image,ImageDraw
R=next(p for p in Path(__file__).resolve().parents if (p/'AGENTS.md').exists());sys.path.insert(0,str(R))
from cinematic_bridge_ascent import actor_states_at
P=Path(__file__).resolve().parent.parent
O=R/'assets/story/fire_veinhold_opening/shot08/characters/crown_soldier'
M=json.loads((O/'actorperformance.json').read_text())
def draw(row,t):
 a=next(x for x in actor_states_at(t)['runners'] if x['id']=='crown_soldier');im=Image.open(O/row['file']).convert('RGBA');z=a['pixels_per_metre']/row.get('art_pixels_per_metre',500);im=im.convert('RGBa').resize((max(1,round(im.width*z)),max(1,round(im.height*z))),Image.Resampling.LANCZOS).convert('RGBA');anchor=row.get('anchor',[512,960]);f=Image.new('RGBA',(960,640),'#283a49');f.alpha_composite(im,tuple(round(a['ground_anchor'][j]-anchor[j]*z) for j in range(2)));return f,a
frames=[]
for i,row in enumerate(M['transition_frames']):
 f,a=draw(row,i/60);x,y=map(round,a['ground_anchor']);crop=f.crop((x-160,y-330,x+160,y+70)).convert('RGB');d=ImageDraw.Draw(crop);d.text((5,5),f"tick{i} phase{row['logical_phase']}/art{row['authored_phase']}",fill='white');frames.append(crop)
for page,start in enumerate(range(24,133,24)):
 group=frames[start:start+24];s=Image.new('RGB',(6*320,4*400),'#283a49')
 for n,im in enumerate(group):s.paste(im,(n%6*320,n//6*400))
 s.save(f'/tmp/crown_full_transition_native_page{page}.jpg')

for label,indices in [('a',[48,50,52,54,56,58,64,66,68,70,72,74]),('b',[80,82,84,86,88,90,100,102,104,106,108,110]),('c',[118,120,122,124,126,128,130,132])]:
 s=Image.new('RGB',(3*320,((len(indices)+2)//3)*400),'#283a49')
 for n,index in enumerate(indices):s.paste(frames[index],(n%3*320,n//3*400))
 s.save('/tmp/crown_corrected_later_native_'+label+'.jpg')

frames[0].save('/tmp/crown_transition_native_normal.gif',save_all=True,append_images=frames[1:],duration=[17 if i%3!=2 else 16 for i in range(133)],loop=0)
frames[0].save('/tmp/crown_transition_native_slow.gif',save_all=True,append_images=frames[1:],duration=70,loop=0)
far=[]
for i,row in enumerate(M['overhead_cycle']['frames']):
 f,a=draw(row,2.2);x,y=map(round,a['ground_anchor']);crop=f.crop((x-80,y-80,x+80,y+80)).convert('RGB');d=ImageDraw.Draw(crop);d.text((3,3),f"phase{i}",fill='white');far.append(crop)
s=Image.new('RGB',(8*160,6*160),'#283a49')
for n,im in enumerate(far):s.paste(im,(n%8*160,n//8*160))
s.save('/tmp/crown_overhead_native_all48.jpg');far[0].save('/tmp/crown_overhead_native_normal.gif',save_all=True,append_images=far[1:],duration=[17 if i%3!=2 else 16 for i in range(48)],loop=0);far[0].save('/tmp/crown_overhead_native_slow.gif',save_all=True,append_images=far[1:],duration=70,loop=0)
print('Wrote5 transition native contact sheets, normal/slow GIFs, and48phase native far cycle.')

