"""Persistent indoor dog routine. Runtime depends only on Pygame."""
from collections import deque
import json
from pathlib import Path
import random

import pygame
from npc_routines import find_path

ROOT=Path(__file__).resolve().parent


def read(path):return json.loads(path.read_text())


class DaisyRoutine:
    def __init__(self,record,world):
        self.data=record;self.behavior=read(ROOT/record['behavior'])
        self.animation=read(ROOT/record['animation'])
        self.position=pygame.Vector2(record['position'])
        self.probe_size=tuple(self.behavior['probe_size']);self.draw_anchor=tuple(self.animation['draw_anchor'])
        self.speed=self.behavior['speed'];self._rng=random.Random(record.get('seed'))
        self.actions={name:[(world.image(f['file']),f['duration_ms']) for f in action['frames']]
                      for name,action in self.animation['actions'].items()}
        self.idles={};self.walks={}
        for direction in ('front','left','right','back'):
            self.idles[direction]=self._pad(world.image(f'assets/characters/daisy/idle_{direction}.png'))
            path=ROOT/f'assets/characters/daisy/walk_{direction}'
            self.walks[direction]=[(self._pad(world.image((path/f['file']).relative_to(ROOT).as_posix())),f['duration_ms'])
                                   for f in read(path/'animation.json')['frames']]
        self.lying=self._pad(world.image(self.animation['lying_image']),self.animation['lying_offset'])
        self.bowls={kind:next(e for e in world.entities if e['id']==spec['id']) for kind,spec in self.behavior['bowls'].items()}
        pack=read(ROOT/next(iter(self.bowls.values()))['bowl_pack'])
        self.lip=world.image((Path(next(iter(self.bowls.values()))['bowl_pack']).parent/pack['front_overlay']).as_posix())
        self.water_masks={state:world.image((Path(next(iter(self.bowls.values()))['bowl_pack']).parent/pack[key]).as_posix(),False)
                          for state,key in (('full','content_mask'),('half_full','half_content_mask'))}
        water=read(ROOT/pack['water_palette_source'])['palette'];self.ripple_color=pygame.Color(water['water_light'])
        self.events=deque(maxlen=128);self.completed_visits={'food':0,'water':0};self.completed_wanders=0
        self.cooldowns={kind:self._sample(f'{kind}_cooldown_ms') for kind in ('food','water')}
        self.state='rest';self.state_ms=0.0;self.duration_ms=self._sample('rest_ms')
        self.facing='left';self.moving=False;self.waiting=False;self.walk_ms=0.0
        self.path=None;self.goal=None;self.role=None;self.retry_ms=0;self.blocked_ms=0
        self.active_bowl=None;self.activity=None;self.wander_elapsed=0;self.stops=0
        self._accumulator=0;self.consumed=False
        self.play_owned=False;self.play_pose=None
        self.rest_protected=False

    def available_for_activity(self):
        return (not self.play_owned and not self.rest_protected and self.active_bowl is None
                and self.state in ('rest','pause','walk') and self.activity not in ('food','water'))

    def _pad(self,image,offset=None):
        if image.get_size()==tuple(self.animation['canvas_size']):return image
        result=pygame.Surface(self.animation['canvas_size'],pygame.SRCALPHA)
        result.blit(image,offset or self.animation['native_offset']);return result

    def _sample(self,key):return self._rng.randint(*self.behavior[key])

    @property
    def blocker(self):
        w,h=self.probe_size
        return pygame.Rect(round(self.position.x)-w//2,round(self.position.y)-h//2,w,h)

    def _transition(self,state,duration=0):
        old=self.state;self.state=state;self.state_ms=0.0;self.duration_ms=duration
        self.moving=False;self.waiting=False
        self.events.append({'type':'state','from':old,'to':state})

    def begin_activity(self,kind,world):
        """Start an ordinary visit/bout; also used by deterministic review tools."""
        if kind not in ('food','water','wander'):raise ValueError(kind)
        if self.active_bowl is not None:raise ValueError('Daisy already owns a bowl')
        self.activity=kind
        if self.state=='rest':self._transition('stand_up',self.animation['actions']['stand_up']['duration_ms'])
        else:self._start_activity(world,None)

    def _due(self):
        due=[kind for kind,time in self.cooldowns.items() if time<=0]
        return min(due,key=lambda k:self.cooldowns[k]) if due else 'wander'

    def _start_activity(self,world,player):
        if self.activity=='wander':
            self.wander_elapsed=0;self.wander_limit=self._sample('wander_ms')
            self.stops=0;self.stop_limit=self._sample('wander_stops')
            self.wander_points=self._rng.sample(self.behavior['wander_points'],self.stop_limit)
            self._next_wander(world,player)
        else:
            kind=self.activity;bowl=self.bowls[kind]
            if bowl.get('reserved_by') not in (None,self.data['id']):
                self.cooldowns[kind]=5000;self._return_home();return
            bowl['reserved_by']=self.data['id'];self.active_bowl=kind;self.consumed=False
            self._walk_to(self.behavior['bowls'][kind]['station'],kind)

    def _walk_to(self,goal,role):
        self.goal=pygame.Vector2(goal);self.role=role;self.path=None;self.retry_ms=0;self.blocked_ms=0
        self._transition('walk');self.walk_ms=0

    def _next_wander(self,world,player):
        candidates=[p for p in getattr(self,'wander_points',self.behavior['wander_points']) if self.position.distance_to(p)>24
                    and all(pygame.Vector2(p).distance_to(d.data['anchor'])>self.behavior['door_clear_radius'] for d in world.doors)
                    and world.can_stand(p,self.probe_size,self,player)]
        self._rng.shuffle(candidates)
        for point in candidates:
            route=find_path(world,self.position,point,self.probe_size,self,player)
            if route is not None:
                self._walk_to(point,'wander');self.path=route;return
        self._return_home()

    def _return_home(self):self._walk_to(self.behavior['home'],'home')

    def _release(self):
        if self.active_bowl is not None:
            bowl=self.bowls[self.active_bowl]
            if bowl.get('reserved_by')==self.data['id']:bowl.pop('reserved_by',None)
        self.active_bowl=None

    def update(self,seconds,world,player_blocker=None):
        if seconds<0:raise ValueError('Negative routine time')
        if self.play_owned:return
        self._accumulator+=seconds
        count=int((self._accumulator+1e-9)*60);self._accumulator-=count/60
        for _ in range(count):self._tick(1000/60,world,player_blocker)

    def _tick(self,ms,world,player):
        self.state_ms+=ms
        for kind in self.cooldowns:self.cooldowns[kind]-=ms
        if self.activity=='wander':self.wander_elapsed+=ms
        self.moving=False
        if self.state=='rest':
            if self.state_ms>=self.duration_ms:
                self.rest_protected=False;self.begin_activity(self._due(),world)
        elif self.state=='stand_up':
            if self.state_ms>=self.duration_ms:self._start_activity(world,player)
        elif self.state=='walk':self._move(ms,world,player)
        elif self.state=='pause':
            if self.state_ms>=self.duration_ms:
                due=self._due()
                if due!='wander':self.activity=due;self._start_activity(world,player)
                elif (self.stops>=self.stop_limit and self.wander_elapsed>=self.behavior['wander_ms'][0]) or self.wander_elapsed>=self.wander_limit:
                    self.completed_wanders+=1;self._return_home()
                else:self._next_wander(world,player)
        elif self.state=='settle_down':
            if self.state_ms>=self.duration_ms:
                self.activity=None;self.facing='left';self._transition('rest',self._sample('rest_ms'))
        elif self.state.startswith('lower_'):
            if self.state_ms>=self.duration_ms:
                kind=self.active_bowl
                if self.bowls[kind]['state']=='empty':self._transition('inspect',self.behavior['inspect_ms'])
                else:self._transition('eat' if kind=='food' else 'drink',self.behavior['eat_ms' if kind=='food' else 'drink_ms'])
        elif self.state in ('eat','drink','inspect'):
            if self.state_ms>=self.duration_ms:
                kind=self.active_bowl
                if self.state!='inspect' and not self.consumed:
                    previous=self.bowls[kind]['state'];next_state={'full':'half_full','half_full':'empty','empty':'empty'}[previous]
                    if previous!='empty' and world.set_entity_state(self.bowls[kind]['id'],next_state,self.data['id']):
                        self.consumed=True;self.completed_visits[kind]+=1
                        self.events.append({'type':'consumed','kind':kind,'from':previous,'to':next_state})
                self.cooldowns[kind]=self._sample(f'{kind}_cooldown_ms')
                self._transition(f'raise_{kind}',self.animation['actions'][f'raise_{kind}']['duration_ms'])
        elif self.state.startswith('raise_'):
            if self.state_ms>=self.duration_ms:self._walk_to(self.behavior['bowls'][self.active_bowl]['clear'],'clear')

    def _arrive(self,world,player):
        if self.role=='wander':
            self.stops+=1;self._transition('pause',self._sample('pause_ms'))
        elif self.role=='home':
            self.facing='left';self._transition('settle_down',self.animation['actions']['settle_down']['duration_ms'])
        elif self.role=='clear':self._release();self._return_home()
        else:
            kind=self.active_bowl;self.facing=self.behavior['bowls'][kind]['facing']
            self._transition(f'lower_{kind}',self.animation['actions'][f'lower_{kind}']['duration_ms'])

    def _move(self,ms,world,player):
        if self.position.distance_squared_to(self.goal)<1e-8:self._arrive(world,player);return
        if self.path is None:
            self.retry_ms=max(0,self.retry_ms-ms)
            if self.retry_ms:return
            self.path=find_path(world,self.position,self.goal,self.probe_size,self,player)
            if self.path is None:
                self.waiting=True;self.blocked_ms+=ms+500;self.retry_ms=500
                if self.blocked_ms>=8000:
                    if self.role in ('food','water'):
                        self.cooldowns[self.active_bowl]=5000;self._release();self._return_home()
                    elif self.role=='wander':self._next_wander(world,player)
                return
        budget=self.speed*ms/1000
        while budget>1e-7 and self.path:
            target=pygame.Vector2(self.path[0]);delta=target-self.position;distance=delta.length()
            if distance<1e-7:self.path.popleft();continue
            direction=delta/distance;step=min(1,budget,distance);candidate=self.position+direction*step
            if not world.can_stand(candidate,self.probe_size,self,player):
                self.waiting=True;self.blocked_ms+=ms
                if self.blocked_ms>=800:self.path=None;self.retry_ms=0
                return
            self.position.update(candidate);budget-=step;self.walk_ms+=step/self.speed*1000
            self.moving=True;self.waiting=False;self.blocked_ms=0
            self.facing=('right' if direction.x>0 else 'left') if abs(direction.x)>abs(direction.y) else ('front' if direction.y>0 else 'back')
            if step+1e-7>=distance:self.path.popleft()
        if not self.path:
            self.path=None
            if self.position.distance_squared_to(self.goal)<1e-8:self._arrive(world,player)

    @property
    def action_id(self):
        if self.state in self.actions:return self.state
        if self.state=='inspect':return f'lower_{self.active_bowl}'
        return None

    @property
    def frame_index(self):
        key=self.action_id
        if key:
            spec=self.animation['actions'][key]
            if self.state=='inspect':return 3
            time=self.state_ms%spec['duration_ms'] if spec['loop'] else min(self.state_ms,spec['duration_ms']-1)
            cursor=0
            for i,(_,duration) in enumerate(self.actions[key]):
                cursor+=duration
                if time<cursor:return i
        if self.moving:
            time=self.walk_ms%560
            return min(3,int(time//140))
        return 0

    @property
    def current_action_record(self):
        return self.animation['actions'][self.action_id]['frames'][self.frame_index] if self.action_id else {}

    def sprite(self,elapsed_ms):
        if self.play_pose is not None:return self.play_pose.sprite(elapsed_ms)
        if self.state=='rest':return self.lying
        if self.action_id:return self.actions[self.action_id][self.frame_index][0]
        if self.moving:return self.walks[self.facing][self.frame_index][0]
        return self.idles[self.facing]

    def _at_bowl(self):
        return self.active_bowl is not None and (self.state.startswith(('lower_','raise_')) or self.state in ('eat','drink','inspect'))

    def draw_background(self,target,camera):
        if self.play_pose is not None:
            if self.play_pose.action and self.play_pose.action.startswith('hop_'):
                pygame.draw.ellipse(target,'#665c45',(round(self.position.x)-8-camera[0],round(self.position.y)+2-camera[1],16,3))
            return
        if not self._at_bowl() or self.state!='drink':return
        bowl=self.bowls[self.active_bowl];mask=self.water_masks.get(bowl['state'])
        if mask is None:return
        ripple=pygame.Surface((24,24),pygame.SRCALPHA)
        patterns=(((13,12),),((11,12),(14,12)),((12,13),(14,11)),())
        for point in patterns[self.frame_index]:
            if mask.get_at(point).r:ripple.set_at(point,self.ripple_color)
        target.blit(ripple,(bowl['position'][0]-camera[0],bowl['position'][1]-camera[1]))

    def draw_foreground(self,target,camera):
        if self.play_pose is not None:return
        if self._at_bowl():
            bowl=self.bowls[self.active_bowl]
            target.blit(self.lip,(bowl['position'][0]-camera[0],bowl['position'][1]-camera[1]))
