"""Ada native complete dress/limb poses. Child phase plan with independently
plotted age7 torso, sleeves, hem and small bare legs; no skeletal articulation.
Each input record is full pose contours, not idle limb pixels or rescaled art.
"""
from PIL import Image,ImageDraw
from pathlib import Path
import json
P=Path(__file__).parent
O='#1a0e16';D='#4d77a0';DS='#304f70';DH='#7da5c7';S='#e8c49d';SS='#c98c64'
def pts(s):return [tuple(map(int,v.split(','))) for v in s.split()]
def body(k,direction):
 im=Image.new('RGBA',(48,72));d=ImageDraw.Draw(im);b=k['b']
 def p(q,c):d.polygon(pts(q),fill=c,outline=O)
 def leg(key,shoe):
  p(k[key],S);q=pts(k[key]);d.line([(q[0][0]+1,q[0][1]+2),(q[2][0]-1,q[2][1])],fill=SS)
  p(k[shoe],'#603b28');q=pts(k[shoe]);d.line([(q[0][0]+1,q[0][1]+1),(q[1][0]-1,q[1][1]+1)],fill='#a4774c')
 if direction in ['front','back']:
  leg('L','lb');leg('R','rb')
  for sleeve,hand in [('rs','rh'),('ls','lh')]:
   p(k[sleeve],D);p(k[hand],S);q=pts(k[sleeve]);d.line([(q[0][0]+1,q[0][1]+2),(q[2][0]-1,q[2][1]-1)],fill=DH)
  p(k['hem'],D)
  d.line([(18,51+b),(17,56+b),(16,60+b)],fill=DH)
  d.line([(28,52+b),(30,57+b),(31,60+b)],fill=DS)
  d.line([(22,55+b),(21,60+b)],fill='#648bb0');d.line([(25,55+b),(26,60+b)],fill='#416587')
  d.line([(15,61+b),(23,62+b),(32,61+b)],fill=DS)
  if direction=='front':
   d.polygon([(19,46+b),(23,47+b),(24,50+b),(20,49+b),(18,47+b)],fill='#fbeed0',outline='#bcae91')
   d.polygon([(25,47+b),(29,46+b),(30,48+b),(26,50+b),(24,50+b)],fill='#ded1ae',outline='#bcae91')
   d.point((24,52+b),fill='#d3c4a3')
  else:d.line([(20,47+b),(24,48+b),(28,47+b)],fill=DH)
 else:
  near='R' if direction=='right' else 'L';far='L' if near=='R' else 'R'
  leg(far,far.lower()+'b');p(k['f'],DS);p(k['fh'],SS);leg(near,near.lower()+'b')
  p(k['hem'],D)
  if direction=='right':
   d.line([(20,51+b),(18,57+b),(18,60+b)],fill=DH);d.line([(28,53+b),(29,59+b)],fill=DS)
   d.polygon([(25,46+b),(29,47+b),(29,49+b),(26,50+b),(24,48+b)],fill='#ded1ae',outline='#bcae91')
  else:
   d.line([(28,51+b),(30,57+b),(30,60+b)],fill=DH);d.line([(20,53+b),(19,59+b)],fill=DS)
   d.polygon([(19,47+b),(23,46+b),(24,48+b),(22,50+b),(19,49+b)],fill='#ded1ae',outline='#bcae91')
  d.line([(17,61+b),(24,62+b),(31,61+b)],fill=DS)
  p(k['s'],D);q=pts(k['s']);d.line(q[1:3],fill=DH);p(k['h'],S)
 return im
