import math
from pathlib import Path
from PIL import Image,ImageDraw
p=Path(__file__).resolve().parent
(p/'guides').mkdir(exist_ok=True)
# Art-directing diagrams only. Final assets are complete ImageGen redraws.
knees=[(475,970),(480,1010),(480,1060),(475,1010),(475,970),(475,890),(475,820),(475,890)]
ankles=[(470,1370),(480,1360),(500,1310),(485,1160),(480,1090),(485,1080),(485,1040),(470,1290)]
def cat(points,f):
 n=int(f//6); u=f/6-n
 a,b,c,d=[points[i%8] for i in (n-1,n,n+1,n+2)]
 return tuple(.5*((2*b[j])+(-a[j]+c[j])*u+(2*a[j]-5*b[j]+4*c[j]-d[j])*u*u+(-a[j]+3*b[j]-3*c[j]+d[j])*u*u*u) for j in (0,1))
for f in range(48):
 t=2*math.pi*f/48;c=math.cos(t);bob=4*math.cos(2*t)
 im=Image.new('RGB',(1086,1448),'#e5e7eb');d=ImageDraw.Draw(im)
 d.ellipse((477,30,609,218),outline='#64748b',width=5)
 neck=(543,247+bob);hips=[(490,650+bob),(596,650+bob)]
 shoulders=[(420,310+bob),(666,310+bob)]
 d.line([neck,(543,544+bob),*hips[::-1],hips[0]],fill='#64748b',width=7)
 d.line(shoulders,fill='#64748b',width=7)
 rhs=[shoulders[0],(375-15*c,520+20*c+bob),(410-95*c,555+155*c+bob)]
 lhs=[shoulders[1],(715+8*c,510-10*c+bob),(676+12*c,505-35*c+bob)]
 rk=cat(knees,f);ra=cat(ankles,f);lk0=cat(knees,(f+24)%48);la0=cat(ankles,(f+24)%48)
 lk=(1086-lk0[0],lk0[1]);la=(1086-la0[0],la0[1])
 chains=[(rhs,'#dc2626'),(lhs,'#2563eb'),([hips[0],rk,ra],'#dc2626'),([hips[1],lk,la],'#2563eb')]
 for points,col in chains:
  d.line(points,fill=col,width=10)
  for x,y in points:d.ellipse((x-12,y-12,x+12,y+12),fill=col)
 hand=rhs[-1];d.line([hand,(hand[0]-250,hand[1]+400)],fill='#475569',width=8)
 # Worn shield always belongs to the left forearm. Diagram only.
 hx,hy=lhs[-1];poly=[(hx-60,hy-120),(hx+85,hy-100),(hx+110,hy+130),(hx+20,hy+220),(hx-60,hy+140)]
 d.line(poly+[poly[0]],fill='#475569',width=6)
 d.text((40,25),f'Phase{f:02d}/48 FRONT. Red=anatomicalRIGHT. Blue=anatomicalLEFT.',fill='#111827')
 d.text((40,55),'Guide only: redraw entire painted knight, never copy these lines or colors.',fill='#111827')
 im.save(p/'guides'/f'phase_{f:02d}.png')
