"""Pippa native complete dress/limb poses. Child phase plan with independently
plotted age8 torso, sleeves, hem and small bare legs; no skeletal articulation.
Each input record is full pose contours, not idle limb pixels or rescaled art.
"""
from PIL import Image,ImageDraw
from pathlib import Path
import json
P=Path(__file__).parent
O='#1a0e16';D='#805477';DS='#51364f';DH='#ad80a0';S='#e8c49d';SS='#c98c64'
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
  d.line([(18,47+b),(18,53+b),(16,60+b)],fill=DH)
  d.line([(28,47+b),(29,54+b),(31,60+b)],fill=DS)
  d.line([(22,55+b),(21,60+b)],fill='#986a90');d.line([(25,55+b),(26,60+b)],fill='#6c4567')
  d.line([(15,61+b),(23,62+b),(32,61+b)],fill=DS)
  # Pippa's dress has a small blue-gray neckline, not Ada's cream collar.
  d.line([(20,43+b),(24,45+b),(28,43+b)],fill='#8197a5')
  d.line([(23,47+b),(23,50+b)],fill='#51364f')
  d.point((24,47+b),fill='#ad80a0')
 else:
  near='R' if direction=='right' else 'L';far='L' if near=='R' else 'R'
  leg(far,far.lower()+'b');p(k['f'],DS);p(k['fh'],SS);leg(near,near.lower()+'b')
  p(k['hem'],D)
  if direction=='right':
   d.line([(20,51+b),(18,57+b),(18,60+b)],fill=DH);d.line([(28,53+b),(29,59+b)],fill=DS)
   d.polygon([(25,42+b),(29,43+b),(29,45+b),(26,46+b),(24,44+b)],fill='#596e7d',outline='#394955')
  else:
   d.line([(28,51+b),(30,57+b),(30,60+b)],fill=DH);d.line([(20,53+b),(19,59+b)],fill=DS)
   d.polygon([(19,43+b),(23,42+b),(24,44+b),(22,46+b),(19,45+b)],fill='#596e7d',outline='#394955')
  d.line([(17,61+b),(24,62+b),(31,61+b)],fill=DS)
  p(k['s'],D);q=pts(k['s']);d.line(q[1:3],fill=DH);p(k['h'],S)
 return im
