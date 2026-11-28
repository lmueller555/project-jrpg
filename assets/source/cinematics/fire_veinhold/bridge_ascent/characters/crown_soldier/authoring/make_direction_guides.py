"""Source-only camera-volume planning diagrams; never exports runtime art.

Physical point examples describe the phase18 study at500px/m. The final painted
anatomy is authored by ImageGen, not constructed by this guide.
"""
from pathlib import Path
import math
from PIL import Image,ImageDraw
HERE=Path(__file__).resolve().parent.parent
PPM=500
ROOT=(512,960)
POINTS={'hip_r':(-.12,0,1.0),'hip_l':(.12,0,1.0),'knee_r':(-.14,-.16,.60),'ankle_r':(-.13,-.53,.38),'toe_r':(-.13,-.44,.35),'knee_l':(.16,.32,.69),'ankle_l':(.17,.62,.29),'toe_l':(.17,.74,.24),'shoulder_r':(-.23,.15,1.44),'shoulder_l':(.23,.15,1.44),'elbow_r':(-.36,.18,1.10),'hand_r':(-.27,.39,1.08),'elbow_l':(.37,.10,1.15),'hand_l':(.44,.27,1.06),'helmet':(0,.24,1.70),'sword_tip':(-.62,.90,.53)}
for elevation in (30,60,90):
 th=math.radians(elevation)
 def project(p):x,f,z=p;return (ROOT[0]+round(PPM*x),ROOT[1]+round(PPM*(f*math.sin(th)-z*math.cos(th))))
 q={k:project(p) for k,p in POINTS.items()};im=Image.new('RGBA',(1024,1536));d=ImageDraw.Draw(im)
 # Torso/shoulder ground-plane volume shrinks with elevation; the helmet's
 # physical diameter remains stable. These flat colors are guide marks only.
 sx,sy=project((0,.15,1.44));hx,hy=project((0,0,1.0));d.ellipse((sx-135,min(sy,hy)-55,sx+135,max(sy,hy)+55),fill='#626b7fcc',outline='#cdd4de',width=3)
 for side in ['r','l']:
  x,y=q['shoulder_'+side];d.ellipse((x-70,y-60,x+70,y+60),fill='#8894a8',outline='white',width=3)
 for chain,col in [(['hip_r','knee_r','ankle_r','toe_r'],'#ff5555'),(['hip_l','knee_l','ankle_l','toe_l'],'#558dff'),(['shoulder_r','elbow_r','hand_r'],'#ffaaaa'),(['shoulder_l','elbow_l','hand_l'],'#99bbff')]:
  path=[q[n] for n in chain];d.line(path,fill=col,width=16)
  for x,y in path:d.ellipse((x-9,y-9,x+9,y+9),fill='#ffee77')
 x,y=q['helmet'];d.ellipse((x-85,y-85,x+85,y+85),fill='#a1aabd',outline='white',width=4)
 # Shield is held upright. Its real plane appears progressively edge-on.
 cx,cy=project((.47,.20,1.10));hw=18+round(60*math.cos(th));hh=round(135*math.sin(th)+85*math.cos(th));d.ellipse((cx-hw,cy-hh,cx+hw,cy+hh),fill='#adb8c5',outline='white',width=3)
 d.line([q['hand_r'],q['sword_tip']],fill='#d8dfe8',width=12);d.line((ROOT[0]-12,ROOT[1],ROOT[0]+12,ROOT[1]),fill='#00ff99',width=3);d.line((ROOT[0],ROOT[1]-12,ROOT[0],ROOT[1]+12),fill='#00ff99',width=3)
 d.text((20,1455),f'{elevation}deg CAMERA-VOLUME AUTHORING GUIDE ONLY / phase18 / forward is BOTTOM',fill='white');d.text((20,1480),'500px/m; groundroot[512,960];redRIGHT sword;blueLEFT shield.',fill='white');d.text((20,1505),'Preserve rigid physical sizes. Remove all guide geometry/text.',fill='white');im.save(HERE/f'authoring/locked_volume_{elevation:02d}_phase18.png')
