"""Make annotated pose-planning diagrams for ImageGen, never rendered artwork.

Only the image-authored complete drawings enter source_art_48.json/export. These
simple landmark diagrams communicate chronological arm/leg and trailing-edge
paths; no guide pixels or transformed original artwork enter the animation.
"""
from pathlib import Path
from math import cos,sin,pi
from PIL import Image,ImageDraw
P=Path(__file__).resolve().parent

def lerp(a,b,t):return a+(b-a)*t

def leg(f, side):
    # Coarse front-projected support/recovery landmarks, named anatomical sides.
    q=f%48
    keys=[(0,650,930),(8,665,920),(16,665,850),(24,650,735),(32,600,775),(40,615,845),(48,650,930)]
    for (a,ka,aa),(b,kb,ab) in zip(keys,keys[1:]):
      if a<=q<=b:
        t=(q-a)/(b-a);t=t*t*(3-2*t)
        ky,ay=lerp(ka,kb,t),lerp(aa,ab,t);break
    x=345 if side=='right' else 423
    return [(x,400),(x+(-8 if side=='right' else 8),ky),(x+(-12 if side=='right' else 12),ay)]

def build():
  for f in range(48):
    t=2*pi*f/48;r=(1-cos(t))/2;l=1-r;bob=4*sin(2*t)
    im=Image.new('RGB',(768,1024),'white');d=ImageDraw.Draw(im)
    d.text((20,12),f'POSE PLAN {f:02d}/48 - COMPLETE REDRAW; NOT FINAL ART',fill='black')
    d.text((20,32),'BLUE=anatomical RIGHT/viewer LEFT; RED=anatomical LEFT/viewer RIGHT',fill='black')
    d.ellipse((335,75+bob,433,195+bob),outline='#444444',width=5)
    d.line([(384,195+bob),(384,225+bob)],fill='#444444',width=8)
    d.polygon([(300,230+bob),(465,230+bob),(435,400+bob),(330,400+bob)],outline='#444444',width=5)
    for pts,color in [(leg(f,'right'),'#1964cc'),(leg(f+24,'left'),'#d82e35')]:
      pts=[(x,y+bob) for x,y in pts];d.line(pts,fill=color,width=10)
      for x,y in pts:d.ellipse((x-7,y-7,x+7,y+7),fill=color)
      x,y=pts[-1];d.rounded_rectangle((x-16,y-8,x+16,y+12),radius=7,outline=color,width=5)
    arms=[([(300,235+bob),(265-5*r,355+5*r+bob),(204+130*r,490-200*r+bob)],'#1964cc'), ([(465,235+bob),(503+5*l,355+5*l+bob),(539-80*l,490-200*l+bob)],'#d82e35')]
    for pts,color in arms:
      d.line(pts,fill=color,width=10)
      for x,y in pts:d.ellipse((x-8,y-8,x+8,y+8),fill=color)
    # Suggested connected trailing cloth boundary. Drawing owns its actual folds.
    hem=490-55*sin(t-pi/3);crest=300-40*sin(t-pi/2)
    d.line([(306,224+bob),(210,250),(100,crest),(65,hem-65),(120,hem),(210,hem-20),(290,365)],fill='#259b59',width=5)
    # Loose hair/trailing braid motion arrows retain distinct attachment/weight.
    hair=130-15*sin(t-pi/4)
    d.line([(370,100+bob),(260,hair),(150,hair+15)],fill='#9d59bd',width=5)
    bx=455+27*sin(t-pi/2);by=350+15*sin(t-pi/2)
    d.line([(430,145+bob),(475,230+bob),(bx+20,300+bob),(bx,by+bob)],fill='#ca8d23',width=5)
    d.text((28,990),'Reference identity/costume comes from painted figure. Guides never render.',fill='black')
    (P/'repair_guides').mkdir(exist_ok=True)
    im.save(P/'repair_guides'/f'guide_{f:02d}.png')
if __name__=='__main__':build()
