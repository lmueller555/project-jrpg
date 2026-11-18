"""Complete native grain-loader drawings in the approved adult_man_02 design.
Explicit full-pose contours, no anatomical transforms, rig, sprite scaling or
legacy-source sampling. Uniform (24,23) canvas placement is registration only.
"""
from pathlib import Path
from PIL import Image,ImageDraw
import json,hashlib,copy
S=Path(__file__).parent;ROOT=S.parents[5]
W=json.loads((S/'canonical_walk_contours.json').read_text())
O='#1a0e16';R='#a65b45';RS='#713d32';RH='#cc8566';P='#4b4952';PS='#35343b';PH='#716c76';B='#714b34';BH='#98704c';SK='#e8c49d';SS='#c08d69'
# Independently plotted complete stationary body outlines, all native pixels.
STAND={
 'front':{'left':[(16,44),(23,44),(23,54),(22,64),(17,65),(16,55)],'right':[(25,44),(31,44),(32,54),(31,65),(25,65),(24,54)],'lb':[(16,62),(22,62),(23,66),(23,69),(13,69),(13,67)],'rb':[(25,62),(31,62),(32,66),(34,67),(34,69),(25,69)],'torso':[(16,25),(21,24),(27,24),(32,25),(34,30),(33,37),(30,40),(31,45),(17,45),(15,39),(12,35),(12,30)]},
 'back':{'left':[(16,44),(23,44),(23,54),(22,64),(17,65),(16,55)],'right':[(25,44),(31,44),(32,54),(31,65),(25,65),(24,54)],'lb':[(16,62),(22,62),(23,66),(23,69),(14,69),(14,65)],'rb':[(25,62),(31,62),(32,66),(32,69),(25,69)],'torso':[(16,25),(21,24),(27,24),(32,25),(34,30),(33,37),(30,40),(31,45),(17,45),(15,39),(12,35),(12,30)]},
 'right':{'fl':[(20,44),(25,44),(25,55),(23,65),(18,65),(18,54)],'fb':[(18,62),(23,62),(24,66),(24,69),(16,69),(16,67)],'nl':[(23,44),(29,44),(29,54),(28,63),(32,65),(29,67),(23,64),(22,54)],'nb':[(23,62),(29,62),(32,65),(35,67),(35,69),(22,69),(22,65)],'co':[(19,26),(26,25),(30,29),(29,36),(29,44),(27,47),(18,46),(17,40),(17,32)]},
 'left':{'fl':[(27,44),(22,44),(22,55),(24,65),(29,65),(29,54)],'fb':[(24,62),(29,62),(31,67),(31,69),(23,69),(23,66)],'nl':[(24,44),(18,44),(18,54),(19,63),(15,65),(18,67),(24,64),(25,54)],'nb':[(18,62),(24,62),(25,65),(25,69),(12,69),(12,67),(16,65)],'co':[(28,26),(21,25),(17,29),(18,36),(18,44),(20,47),(29,46),(30,40),(30,32)]}}
# Whole contiguous arm contours, with authored sleeves inside each silhouette.
# These are static supported/carry poses, not detached animated limb parts.
FRONT_HOLD=[([(13,29),(17,30),(17,36),(18,41),(16,45),(13,44),(11,38)],[(13,28),(17,29),(18,34),(13,36)]), ([(31,30),(35,29),(36,36),(35,43),(32,45),(30,42),(31,36)],[(31,29),(35,28),(36,34),(31,36)])]
BACK_HOLD=[([(13,29),(17,30),(18,36),(17,42),(14,43),(12,38)],[(13,28),(17,29),(18,35),(13,37)]), ([(30,30),(34,29),(36,37),(34,43),(31,42),(30,36)],[(30,29),(34,28),(35,35),(31,37)])]
RIGHT_HOLD=[([(23,28),(27,29),(29,35),(33,39),(35,42),(33,45),(29,43),(25,38),(22,33)],[(23,27),(27,28),(30,34),(26,36),(22,32)]), ([(22,29),(26,29),(28,35),(28,39),(35,41),(37,43),(35,46),(25,44),(22,40),(20,34)],[(22,28),(26,28),(28,34),(24,37),(20,34)])]
LEFT_HOLD=[([(24,28),(20,29),(18,35),(14,39),(12,42),(14,45),(18,43),(22,38),(25,33)],[(24,27),(20,28),(17,34),(21,36),(25,32)]), ([(25,29),(21,29),(19,35),(19,39),(12,41),(10,43),(12,46),(22,44),(25,40),(27,34)],[(25,28),(21,28),(19,34),(23,37),(27,34)])]
HOLDS={'front':FRONT_HOLD,'back':BACK_HOLD,'right':RIGHT_HOLD,'left':LEFT_HOLD}
FRONT_REST=[([(13,30),(17,30),(17,38),(16,46),(13,48),(11,45),(12,38)],[(13,29),(17,29),(18,35),(12,36)]), ([(31,30),(35,30),(36,37),(36,45),(33,48),(31,46),(32,38)],[(31,29),(35,29),(36,35),(31,36)])]
# Full crouching drawings: shoulders/hips/knees/boots and both arms all planned
# together. No point is derived from another frame by interpolation or warping.
CROUCH=[
 {'head':(0,14),'left':[(16,52),(23,53),(23,58),(18,63),(17,66),(12,65),(12,60)],'right':[(25,53),(31,52),(36,60),(35,65),(30,66),(29,62),(24,58)],'torso':[(15,40),(20,38),(28,38),(33,40),(35,46),(32,53),(27,56),(20,56),(15,53),(12,46)],'arms': [([(14,43),(18,44),(18,49),(20,55),(22,59),(19,61),(16,57),(13,51),(11,47)],[(14,41),(18,42),(19,47),(13,49)]), ([(30,44),(34,43),(36,47),(33,54),(30,60),(27,61),(25,59),(28,54),(30,49)],[(30,42),(34,41),(36,46),(30,49)])]},
 {'head':(0,9),'left':[(16,49),(23,49),(23,55),(20,61),(21,65),(16,66),(13,63),(14,56)],'right':[(25,49),(31,49),(34,56),(34,63),(31,66),(26,65),(27,61),(24,55)],'torso':[(16,34),(21,33),(27,33),(32,34),(35,41),(32,49),(28,52),(19,52),(15,49),(12,41)],'arms':[([(14,36),(18,37),(18,43),(19,48),(20,53),(17,55),(14,52),(12,44)],[(14,35),(18,36),(19,41),(13,43)]), ([(30,37),(34,36),(36,44),(33,51),(30,55),(27,53),(29,48),(30,43)],[(30,36),(34,35),(35,41),(30,43)])]},
 {'head':(0,4),'left':[(16,46),(23,46),(23,55),(21,64),(16,65),(14,60),(15,53)],'right':[(25,46),(31,46),(33,53),(33,61),(31,65),(26,65),(25,55)],'torso':[(16,29),(21,28),(27,28),(32,29),(35,35),(33,42),(30,47),(31,49),(17,49),(15,44),(12,36)],'arms':[([(13,33),(17,34),(17,40),(17,44),(14,46),(12,44),(11,39)],[(13,32),(17,33),(18,38),(12,40)]), ([(31,34),(35,33),(36,39),(35,44),(32,46),(30,44),(31,40)],[(31,33),(35,32),(36,38),(31,40)])]},
 {'head':(0,0),'left':STAND['front']['left'],'right':STAND['front']['right'],'torso':STAND['front']['torso'],'arms':FRONT_HOLD}]
# Right-facing supported placement / push poses. Explicit upper body tilt and
# elbow paths keep feet fixed without stretching arms to historic cue points.
PLACE_ARMS=[RIGHT_HOLD,
 [([(24,29),(28,30),(31,36),(36,40),(39,43),(37,46),(33,43),(28,39)],[(24,28),(28,29),(32,35),(28,37)]), ([(23,30),(27,30),(29,36),(31,41),(39,44),(41,46),(39,49),(29,46),(25,42),(22,35)],[(23,29),(27,29),(30,35),(25,38)])],
 [([(26,31),(30,31),(33,36),(39,40),(44,43),(43,46),(38,44),(31,40),(25,35)],[(26,30),(30,30),(34,35),(29,38)]), ([(25,31),(29,32),(31,38),(33,43),(42,45),(44,47),(42,50),(31,47),(27,43),(24,36)],[(25,30),(29,31),(32,37),(27,39)])],
 [([(25,30),(29,30),(31,36),(34,40),(36,43),(34,46),(30,43),(26,39)],[(25,29),(29,29),(32,35),(27,38)]), ([(24,30),(28,31),(29,37),(28,43),(25,46),(22,44),(23,38)],[(24,29),(28,30),(30,35),(25,38)])]]
PUSH_ARMS=[
 [([(24,29),(28,29),(32,31),(39,32),(43,31),(44,34),(41,36),(32,35),(26,34)],[(24,28),(28,28),(33,30),(31,35),(25,34)]),RIGHT_HOLD[1]],
 [([(26,29),(30,29),(34,31),(41,31),(45,30),(46,33),(43,35),(34,35),(28,34)],[(26,28),(30,28),(35,30),(33,35),(27,34)]),PLACE_ARMS[1][1]],
 [([(28,28),(32,28),(36,30),(43,30),(46,29),(47,32),(44,34),(36,34),(30,33)],[(28,27),(32,27),(37,29),(35,34),(29,33)]),PLACE_ARMS[1][1]],
 [([(28,28),(32,28),(37,30),(43,30),(46,29),(47,32),(44,34),(36,34),(30,33)],[(28,27),(32,27),(37,29),(35,34),(29,33)]),PLACE_ARMS[1][1]]]
LEAN=[STAND['right']['co'],[(21,27),(28,26),(32,30),(31,37),(29,44),(27,47),(18,46),(18,40),(19,33)],[(23,28),(30,27),(34,31),(32,38),(29,44),(27,47),(18,46),(18,40),(21,34)],[(23,27),(30,26),(34,30),(32,37),(29,44),(27,47),(18,46),(18,40),(21,33)]]

def full_spec(face,body=None,arms=None,head=(0,0),bob=0):
 body=copy.deepcopy(body or STAND[face]);body['bob']=bob
 return {'face':face,'head':list(head),'body':body,'arms':copy.deepcopy(arms or HOLDS[face])}

def draw(spec):
 face=spec['face'];k=spec['body'];b=k.get('bob',0);im=Image.new('RGBA',(48,88));d=ImageDraw.Draw(im)
 def poly(pts,c):d.polygon([tuple(p) for p in pts],fill=c,outline=O)
 def arm(pair,near):
  skin,sleeve=pair;poly(skin,SK if near else SS);poly(sleeve,R if near else RS)
  d.line([tuple(p) for p in sleeve[1:3]],fill=RH if near else R)
 if face in ('front','back'):
  for key,c in [('left',P),('right',PS),('lb',B),('rb',B)]:poly(k[key],c)
  for key in ('left','right'):d.line([tuple(p) for p in k[key][1:4]],fill=PH if key=='left' else P)
  for key in ('lb','rb'):d.line([tuple(p) for p in k[key][1:3]],fill=BH)
  poly(k['torso'],R);d.line([tuple(p) for p in k['torso'][1:4]],fill=RH)
  arm(spec['arms'][0],True);arm(spec['arms'][1],True)
  # Native shirt placket/collar, not the former leather vest.
  y=spec['head'][1]
  if face=='front':
   d.line([(24,30+y),(24,39+y)],fill=RS);d.point((25,33+y),fill=RH);d.point((25,36+y),fill=RH)
   d.line([(18,29+y),(21,31+y)],fill=RH);d.line([(27,30+y),(30,28+y)],fill=RS)
  else:d.line([(18,29+y),(30,29+y)],fill=RS)
  belt_y=max(y for x,y in k['torso'])-3
  d.line([(18,belt_y),(29,belt_y)],fill='#523a2c',width=2)
  if face=='front':d.rectangle((23,belt_y-1,25,belt_y+1),fill='#b68e55');d.point((24,belt_y),fill='#523a2c')
 else:
  for key,c in [('fl',PS),('fb','#503a2d')]:poly(k[key],c)
  arm(spec['arms'][0],False)
  for key,c in [('nl',P),('nb',B),('co',R)]:poly(k[key],c)
  d.line([tuple(p) for p in k['nl'][1:4]],fill=PH);d.line([tuple(p) for p in k['nb'][1:3]],fill=BH)
  d.line([tuple(p) for p in k['co'][1:4]],fill=RH);d.line([(20,42+b),(28,42+b)],fill='#523a2c',width=2)
  arm(spec['arms'][1],True)
 # Exact approved head/neck pixels; native translated origin, never rescaled.
 hx,hy=spec['head'];headface=spec.get('head_face',face)
 im.alpha_composite(Image.open(S/'identity'/f'idle_{headface}.png').convert('RGBA').crop((0,0,48,28)),(hx,hy))
 canvas=Image.new('RGBA',(96,104));canvas.alpha_composite(im,(24,23));return canvas

specs={}
for face in ('front','back','left','right'):
 specs[f'hold_{face}_0.png']=full_spec(face)
 for i,phase in enumerate([0,2,4,6]):
  k=copy.deepcopy(W[face][phase]);specs[f'carry_{face}_{i}.png']=full_spec(face,k,HOLDS[face],(0,k['bob']),k['bob'])
for i in range(4):
 c=CROUCH[i];k=copy.deepcopy(STAND['front']);k.update({n:c[n] for n in ('left','right','torso')})
 specs[f'lift_front_{i}.png']=full_spec('front',k,c['arms'],c['head'])
 # Full-body recovery follows supported crouch-to-stand, with empty hands.
 specs[f'recover_front_{i}.png']=full_spec('front',k,c['arms'] if i<3 else FRONT_REST,c['head'])
 k=copy.deepcopy(STAND['right']);k['co']=LEAN[i]
 specs[f'place_right_{i}.png']=full_spec('right',k,PLACE_ARMS[i],[(0,0),(2,1),(4,2),(4,1)][i])
 k=copy.deepcopy(STAND['right']);k['co']=LEAN[i]
 specs[f'push_right_{i}.png']=full_spec('right',k,PUSH_ARMS[i],[(0,0),(2,1),(4,0),(4,0)][i])
for i in range(2):
 cover=copy.deepcopy(FRONT_HOLD)
 if i==1:cover[0]=([(13,29),(17,30),(17,36),(16,40),(14,45),(11,44),(11,38)],[(13,28),(17,29),(18,34),(13,36)])
 specs[f'cover_front_{i}.png']=full_spec('front',arms=cover)
 specs[f'inspect_front_{i}.png']=full_spec('front',arms=FRONT_REST if i==0 else FRONT_HOLD)
 specs[f'look_left_{i}.png']=full_spec('front',arms=FRONT_HOLD);specs[f'look_left_{i}.png']['head_face']='front' if i==0 else 'left'
 specs[f'work_right_{i}.png']=full_spec('right',arms=RIGHT_HOLD if i==0 else PLACE_ARMS[1])
 # Quiet supported hands-on-hips stretch (not an overhead prop-use gesture).
 arms=[([(13,30),(17,31),(16,36),(12,40),(18,42),(18,45),(12,44),(8,41),(9,37)],[(13,29),(17,30),(18,34),(12,37)]), ([(31,31),(35,30),(39,37),(39,41),(34,44),(29,45),(29,42),(35,40),(32,36)],[(31,30),(35,29),(38,34),(33,37)])]
 specs[f'stretch_front_{i}.png']=full_spec('front',arms=arms if i==0 else FRONT_REST)

out=S/'refined_masters';out.mkdir(exist_ok=True)
recipe=json.loads((S/'recipe.json').read_text());recipe['refined_masters']={}
for filename,spec in specs.items():
 path=out/filename;draw(spec).save(path)
 recipe['refined_masters']['poses/'+filename]={'file':'refined_masters/'+filename,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
recipe['method']='Native complete-pose contour redraws matching adult_man_02; refined_masters override retained historical cells without resizing bodies or changing logical metadata.'
recipe['refinement']={'identity':'adult_man_02','method':'Complete native contours with exact canonical head pixels, rust collared shirt, charcoal trousers, brown boots. No resized chibi source, geometric limb rig or runtime compositing.','author':'author.py','author_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'contours_sha256':hashlib.sha256((S/'canonical_walk_contours.json').read_bytes()).hexdigest(),'identity_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((S/'identity').glob('*.png'))},'body_origin_artwork':[24,23],'anchor_artwork':[48,92],'artwork_canvas':[96,104],'metadata':'Existing filenames/timing/prop positions/ownership remain unchanged. Native body-only source; props remain separate.'}
(S/'recipe.json').write_text(json.dumps(recipe,indent=2)+'\n');(S/'pose_drawings.json').write_text(json.dumps(specs,indent=2)+'\n')
print('authored',len(specs),'complete frames')
