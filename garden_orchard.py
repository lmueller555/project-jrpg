"""Two regional workers, finite harvests, and one opt-in act of care.

The small authored programs describe local work, not a day/night scheduler.
Every portable object has exactly one derived location. Saves retain the current
step, contact time and feet, so Continue never rewinds a carried object or cue.
"""
from pathlib import Path
import copy
import math
import pygame
from grain_farm import FarmWorker

ROOT=Path(__file__).resolve().parent
ART=ROOT/'assets/characters/garden_workers'
GARDEN=(-526,1190)
ORCHARD=(-145,-250)
SCENE_ID='garden_quiet_care'
HAND=(0,-7)


def walk(point, carry=None):return {'target':point,'carry':carry}
def beat(pose, duration=1.8, **kwargs):return {'pose':pose,'duration':duration,**kwargs}
def pick(key, pose='weed'):return beat(pose,kind='pickup',item=key,**({'sound':'leaves'} if key!='can' else {}))
def put(key, point):return beat('sort',kind='put',item=key,point=point,sound='basket',contact=1.8)

GARDEN_WORK=[
 pick('can'), beat('fill',2.2,sound='water'),
 walk((-526,1158),'can'), beat('water',2.4,sound='water',pour=True),
 walk((-526,1126),'can'), beat('water',2.4,sound='water',pour=True),
 walk(GARDEN,'can'), put('can',(-526,1187)),
 walk((-526,1158)), beat('weed',2.4,sound='leaves'),pick('turnip_0'),
 walk((-526,1196),'turnip_0'),walk((-518,1196),'turnip_0'),put('turnip_0',(-512,1187)),walk((-526,1196)),
 walk((-526,1126)),beat('weed',2.4,sound='leaves'),pick('turnip_1'),
 walk((-526,1196),'turnip_1'),walk((-514,1196),'turnip_1'),put('turnip_1',(-508,1187)),walk((-526,1196)),walk((-526,1174)),
]
# Existing tree row at y=-300, clear east/west aisle at y=-278.
ORCHARD_WORK=[]
for i,x in enumerate((-170,-240,-100)):
 approach=[walk((-180,-250)),walk((-180,-282)),walk((x,-282))] if i==2 else [walk((x,-250)),walk((x,-282))]
 leave=[walk((-180,-282),'apple_'+str(i)),walk((-180,-250),'apple_'+str(i))] if i==2 else [walk((x,-250),'apple_'+str(i))]
 ORCHARD_WORK += approach+[pick('apple_'+str(i),'reach'),
                  beat('admire',2.5 if i==2 else 1.6,sound='leaves'),beat('carry',1.,lower=True)]+leave+[walk(ORCHARD,'apple_'+str(i)),
                  walk(((-153+i*4 if i!=1 else -127)-6,-247),'apple_'+str(i)),
                  put('apple_'+str(i),(-153+i*4,-258) if i!=1 else (-127,-258))]
ORCHARD_WORK += [walk((-96,-250)),walk((-96,-263)),beat('rest',5)]
GARDEN_SCENE=[walk((-526,1174)),pick('plant'),walk((-552,1174),'plant'),walk((-552,1144),'plant'),
              put('plant',(-546,1141)),beat('weed',2.2,sound='leaves'),walk((-552,1164)),beat('idle',3)]
PROGRAMS={'gardener':GARDEN_WORK,'picker':ORCHARD_WORK}
STARTS={'gardener':GARDEN,'picker':ORCHARD}
INITIAL={'can':(-526,1187),'plant':(-516,1171),
         'turnip_0':(-520,1155),'turnip_1':(-520,1123),
         'apple_0':(-168,-304),'apple_1':(-238,-304),'apple_2':(-98,-304)}
ITEM_ROLES={key:('picker' if key.startswith('apple') else 'gardener') for key in INITIAL}


def empty_state():
 return {role:{'phase':'work','step':0,'elapsed':0.,'position':list(point),
               'read':False,'greeted':False} for role,point in STARTS.items()}


def valid_state(data):
 if not isinstance(data,dict) or set(data)!=set(STARTS):return False
 for role,s in data.items():
  if not isinstance(s,dict) or set(s)!=set(empty_state()[role]):return False
  if s['phase'] not in ('work','ready','scene','rest'):return False
  if type(s['read']) is not bool or type(s['greeted']) is not bool:return False
  if type(s['step']) is not int or s['step']<0:return False
  if role=='picker' and s['phase']=='scene':return False
  if s['phase']=='scene' and not s['read']:return False
  if role=='picker' and s['phase']=='ready':return False
  if role=='gardener' and ((s['phase']=='rest' and not s['read']) or (s['phase'] in ('work','ready') and s['read'])):return False
  program=GARDEN_SCENE if s['phase']=='scene' else PROGRAMS[role]
  if s['phase'] in ('ready','rest'):
   if s['step']!=0:return False
  elif s['step']>=len(program):return False
  if type(s['elapsed']) not in (float,int) or not math.isfinite(s['elapsed']) or not 0<=s['elapsed']<=10:return False
  limit=program[s['step']].get('duration',0) if s['phase'] in ('work','scene') else 0
  if s['elapsed']>limit:return False
  p=s['position']
  if not isinstance(p,list) or len(p)!=2 or any(type(v) not in (int,float) or not math.isfinite(v) for v in p):return False
  bounds=(-560,1110,-505,1200) if role=='gardener' else (-250,-290,-85,-240)
  if not(bounds[0]<=p[0]<=bounds[2] and bounds[1]<=p[1]<=bounds[3]):return False
 return True


class GardenWorker(FarmWorker):
 def __init__(self,role,variant,point):
  self.role=role;self.data={'id':'regional_'+role,'name':'Kitchen gardener' if role=='gardener' else 'Orchard picker'}
  self.scene_id='auratia.overworld';self.position=pygame.Vector2(point)
  self.probe_size=(10,6);self.draw_anchor=(20,38)
  self.facing='front';self.pose='idle';self.clock=0.;self.moving=False;self.frames={}
  for direction in ('front','back','left','right'):
   base=ROOT/f'assets/characters/npcs/{variant}'
   self.frames['idle_'+direction]=[self._padded(base/f'idle_{direction}.png')]
   self.frames['walk_'+direction]=[self._padded(base/f'walk_{direction}/frame_{i:02}.png') for i in range(1,5)]
   for pose in ('carry','carry_can','fill','water','weed','reach','sort','admire','rest'):
    self.frames[pose+'_'+direction]=[pygame.image.load(str(ART/f'{role}_{pose}_{direction}_{i}.png')).convert_alpha() for i in range(4 if pose in ('carry','carry_can') else 2)]

 def sprite(self,elapsed_ms):
  key=('walk' if self.moving else 'idle') if self.pose=='idle' else self.pose
  frames=self.frames[key+'_'+self.facing]
  return frames[int(self.clock/(.17 if self.moving else .65))%len(frames)]


class GardenOrchard:
 def __init__(self,world):
  self.world=world
  self.actors=[GardenWorker('gardener','female_01',GARDEN),GardenWorker('picker','male_02',ORCHARD)]
  self.art={key:pygame.image.load(str(ART/(key+'.png'))).convert_alpha() for key in ('barrel','basket','can','plant','apple','turnip')}
  self.restore()

 def restore(self,data=None):
  self.state=copy.deepcopy(data if data is not None else empty_state())
  for actor in self.actors:
   actor.position.update(self.state[actor.role]['position']);actor.clock=0;actor.moving=False
   self._pose(actor)

 def to_dict(self):
  result=copy.deepcopy(self.state)
  for a in self.actors:result[a.role]['position']=list(a.position)
  return result

 def action(self,role):
  s=self.state[role]
  if s['phase'] not in ('work','scene'):return None
  return (GARDEN_SCENE if s['phase']=='scene' else PROGRAMS[role])[s['step']]

 def _pose(self,a):
  action=self.action(a.role)
  a.draw_anchor=(20,44) if a.role=='picker' and (action is None or action.get('pose')=='rest') else (20,38)
  if action is None:a.pose='rest' if a.role=='picker' else 'idle';a.facing='front';return
  a.pose=action.get('pose',('carry_can' if action.get('carry')=='can' else 'carry') if action.get('carry') else 'idle')
  if 'target' not in action:a.facing='right' if a.pose in ('water','weed','sort') else 'front'
  # Sorting/admiring a fruit keeps it in occupied hands, including between steps.

 def _walk(self,a,target,dt,player):
  delta=pygame.Vector2(target)-a.position
  if delta.length()<.01:return True
  a.facing=('right' if delta.x>0 else 'left') if abs(delta.x)>abs(delta.y) else ('front' if delta.y>0 else 'back')
  remaining=min(delta.length(),22*dt)
  while remaining>0:
   step=min(1,remaining);point=a.position+delta.normalize()*step
   if not self.world.can_stand(point,a.probe_size,a,player):return False
   a.position.update(point);remaining-=step;a.moving=True
  return a.position.distance_to(target)<.01

 def _sound(self,game,a,name):
  # Physical contacts use the shared allocator, never a controller-owned channel.
  game.regional_audio.emit('garden_'+a.role+'_'+name,name,tuple(a.position),'garden_work')

 def update(self,seconds,game):
  if game.social.locked:return
  dt=min(max(seconds,0),.1);player=self.world.probe_rect(game.player.position)
  for a in self.actors:
   a.moving=False
   if game.player.position.distance_to(STARTS[a.role])>260:continue
   s=self.state[a.role];a.clock+=dt;self._pose(a);action=self.action(a.role)
   if action is None:continue
   if 'target' in action:
    finished=self._walk(a,action['target'],dt,player)
   else:
    before=s['elapsed'];s['elapsed']=min(action['duration'],before+dt)
    # Commit the contact time immediately. Continue at this beat cannot replay it.
    if before<action.get('contact',.75)<=s['elapsed'] and action.get('sound'):
     self._sound(game,a,action['sound']);game.save_progress()
    finished=s['elapsed']>=action['duration']
   s['position']=list(a.position)
   if finished:
    s['step']+=1;s['elapsed']=0.
    program=GARDEN_SCENE if s['phase']=='scene' else PROGRAMS[a.role]
    if s['step']==len(program):s['phase']='rest' if s['phase']=='scene' or a.role=='picker' else 'ready';s['step']=0
    self._pose(a);game.save_progress()

 def _locations(self,role):
  s=self.state[role];positions={k:pygame.Vector2(p) for k,p in INITIAL.items() if ITEM_ROLES[k]==role}
  def apply(actions):
   for action in actions:
    if action.get('kind')=='pickup':positions[action['item']]='hand'
    if action.get('kind')=='put':positions[action['item']]=pygame.Vector2(action['point'])
  apply(PROGRAMS[role][:s['step']] if s['phase']=='work' else PROGRAMS[role])
  if role=='gardener' and s['phase'] in ('scene','rest'):apply(GARDEN_SCENE[:s['step']] if s['phase']=='scene' else GARDEN_SCENE)
  return positions

 def portable_positions(self):
  result={}
  for a in self.actors:
   s=self.state[a.role];action=self.action(a.role);positions=self._locations(a.role)
   hand=a.position+HAND
   if a.pose=='admire':hand=a.position+(0,-18)
   elif a.pose=='water':hand=a.position+(9,-7)
   elif a.pose=='reach':hand=a.position+(2,-22)
   elif a.pose=='fill':
    t=s['elapsed']/action['duration'];hand=a.position+pygame.Vector2(HAND).lerp((-16,-15),math.sin(math.pi*t))
   if action and action.get('lower'):hand=a.position+pygame.Vector2(0,-18).lerp(HAND,min(1,s['elapsed']/action['duration']))
   for key,p in positions.items():
    if isinstance(p,str):p=hand.copy()
    if action and action.get('item')==key:
     t=min(1,s['elapsed']/action['duration'])
     if action.get('kind')=='pickup':p=p.lerp(hand,t)
     elif action.get('kind')=='put':p=hand.lerp(pygame.Vector2(action['point']),t)
    result[key]=(p, a.position.y+6 if isinstance(positions[key],str) or action and action.get('item')==key else p.y+(8 if key.startswith(('apple','turnip')) else 0))
  return result

 def props(self):
  result=[]
  def add(key,p,sort=None):
   im=self.art[key];result.append((p[1] if sort is None else sort,4,im,(round(p[0])-im.get_width()//2,round(p[1])-im.get_height())))
  add('barrel',(-549,1191));add('basket',(-510,1192));add('basket',(-149,-254));add('basket',(-127,-254))
  for key,(p,z) in self.portable_positions().items():
   if key=='can' and self.actors[0].pose=='fill':
    im=pygame.transform.flip(self.art['can'],True,False)
    result.append((z,4,im,(round(p.x)-im.get_width()//2,round(p.y)-im.get_height())))
   else:add(key.split('_')[0],p,z)
  a=self.actors[0];action=self.action('gardener');s=self.state['gardener']
  if action and action.get('pour') and .5<s['elapsed']<1.8:
   # Small animated droplets connect the spout to the crop roots.
   stream=pygame.Surface((12,15),pygame.SRCALPHA)
   for i in range(3):pygame.draw.line(stream,(126,169,174,210),(i*3,(int(s['elapsed']*18)+i*4)%10),(i*3+1,(int(s['elapsed']*18)+i*4)%10+2))
   result.append((a.position.y+7,5,stream,(round(a.position.x)+17,round(a.position.y)-20)))
  return result

 def ground_blockers(self,actor=None):
  return [pygame.Rect(-560,1187,22,5),pygame.Rect(-519,1189,18,4),pygame.Rect(-158,-257,18,4),pygame.Rect(-136,-257,18,4)]

 def nearby(self,game):
  a=min(self.actors,key=lambda a:a.position.distance_squared_to(game.player.position))
  return a if a.position.distance_to(game.player.position)<=34 else None

 def interaction_hint(self,game):
  a=self.nearby(game)
  return ('E: Speak with '+a.data['name'].lower()) if a else ''

 def interact(self,game):
  a=self.nearby(game)
  if a is None:return False
  s=self.state[a.role]
  if a.role=='gardener' and s['phase']=='ready' and not s['read']:
   lines=[('regional_gardener','Everything else has taken. This one still folds up at noon.'),
          ('caelan','Would it do better by the hedge?'),
          ('regional_gardener','A little shade, perhaps. I was hoping it would manage here.'),
          ('regional_gardener','No sense making it prove anything. Let me move it.')]
   def done():
    s.update(read=True,phase='scene',step=0,elapsed=0.);game.save_progress()
   return game.social.start_script([{'speaker':who,'text':text} for who,text in lines],on_complete=done,identifier=SCENE_ID)
  greeting=('Morning. There is just room to pass at the end of the bed.' if a.role=='gardener' else 'Mind the baskets. That one is for the bruised fruit.')
  text=(('Rainwater for the roots; patience for the rest.' if s['phase']=='work' else 'It can take its time here. I will check it again later.') if a.role=='gardener' else
        ('A bruise is no reason to waste a good apple. Those will stew nicely.' if s['phase']=='work' else 'I saved the finest one for last. Almost too handsome to eat. Almost.'))
  lines=([{'speaker':a.data['id'],'text':greeting}] if not s['greeted'] else [])+[{'speaker':a.data['id'],'text':text}]
  def done():s['greeted']=True;game.save_progress()
  return game.social.start_script(lines,on_complete=done,identifier='garden_orchard_greeting')
