"""One coordinated, persistent household play routine; runtime needs only Pygame."""
from collections import deque
import json
import math
from pathlib import Path
import random

import pygame
from npc_routines import find_path

ROOT=Path(__file__).resolve().parent
META='assets/characters/liam_family/play_routine/animations.json'


def read(path):return json.loads((ROOT/path).read_text())


class PlayPose:
    def __init__(self,world,character):
        self.character=character;self.draw_anchor=(64,66) if character=='liam' else (32,42)
        self.size=(96,96) if character=='liam' else (64,48)
        self.offset=(52,36) if character=='liam' else (16,12)
        self.idles={};self.walks={};self.runs={};self.actions={}
        for direction in ('front','left','right','back'):
            self.idles[direction]=self.pad(world.image(f'assets/characters/{character}/idle_{direction}.png'))
            for verb,dest in (('walk',self.walks),('run',self.runs)):
                folder=f'assets/characters/{character}/{verb}_{direction}'
                dest[direction]=[(self.pad(world.image(f'{folder}/{f["file"]}')),f['duration_ms']) for f in read(f'{folder}/animation.json')['frames']]
        for key,spec in read(META)['actions'].items():
            if (character=='daisy')==(key.startswith(('hop_','wag_'))):
                self.actions[key]=[(world.image(f['file']),f['duration_ms']) for f in spec['frames']]
        if character=='daisy':
            for key in ('stand_up','settle_down'):
                spec=read('assets/characters/daisy/house_routines/animations.json')['actions'][key]
                self.actions[key]=[(world.image(f['file']),f['duration_ms']) for f in spec['frames']]
        self.facing='front';self.moving=False;self.running=False;self.walk_ms=0;self.action=None;self.action_ms=0

    def pad(self,image):
        canvas=pygame.Surface(self.size,pygame.SRCALPHA);canvas.blit(image,self.offset);return canvas

    def sprite(self,elapsed_ms=0):
        if self.action:
            frames=self.actions[self.action];time=min(self.action_ms,sum(d for _,d in frames)-1)
        elif self.moving:
            frames=(self.runs if self.running else self.walks)[self.facing]
            time=self.walk_ms%sum(d for _,d in frames)
        else:return self.idles[self.facing]
        for image,duration in frames:
            if time<duration:return image
            time-=duration
        return frames[-1][0]


class PlayActor(PlayPose):
    opens_doors=True
    def __init__(self,record,world):
        super().__init__(world,record['id']);self.data=record
        self.position=pygame.Vector2(record['position']);self.probe_size=tuple(record['probe_size'])
        self.sort_y=None
        self.work_renderer=None

    @property
    def blocker(self):return pygame.Rect(round(self.position.x)-self.probe_size[0]//2,round(self.position.y)-self.probe_size[1]//2,*self.probe_size)

    def draw_foreground(self,target,camera):
        if self.work_renderer is not None:self.work_renderer.draw_held(target,camera)


class LiamDaisyPlay:
    def __init__(self,game,home,config):
        self.game=game;self.home=home;self.town=game.town;self.config=read(config)
        self.liam=next(a for a in home.npcs if a.data['id']=='liam')
        self.daisy=next(a for a in home.npcs if a.data['id']=='daisy')
        self.dog_pose=PlayPose(home,'daisy');self._rng=random.Random()
        self.worlds={self.liam:home,self.daisy:home};self.routes={};self.events=deque(maxlen=256)
        self.state='cooldown';self.state_ms=0;self.cooldown_ms=self._rng.randint(*self.config['initial_delay_ms'])
        self.completed_cycles=0;self.drink_choice=None;self._forced_choice=None;self._accumulator=0
        self.track=[(round((296+62*math.cos(-math.pi/2+i*math.pi/12))/2)*2,
                     round((590+30*math.sin(-math.pi/2+i*math.pi/12))/2)*2) for i in range(24)]
        self.liam_index=1;self.daisy_index=-1;self.last_index=self.config['laps']*24
        self.liam_owner=None

    @property
    def active(self):return self.state!='cooldown'

    def begin(self,drink=None):
        """Request an ordinary cycle; optional outcome selection is for review/tests."""
        if self.active:return False
        self._forced_choice=drink;self.cooldown_ms=0;return True

    def pose(self,actor):return self.liam if actor is self.liam else self.dog_pose
    def player(self,world):return world.probe_rect(self.game.player.position) if world is self.game.world else None

    def _state(self,name):
        self.state=name;self.state_ms=0;self.events.append({'state':name})
        for pose in (self.liam,self.dog_pose):pose.moving=False;pose.action=None;pose.action_ms=0

    def _action(self,actor,name,time):
        pose=self.pose(actor);pose.action=name;pose.action_ms=time;pose.moving=False

    def _move(self,actor,goal,speed=36,direct=False):
        world=self.worlds[actor];pose=self.pose(actor);pose.action=None;pose.moving=False
        goal=tuple(goal)
        if actor.position.distance_squared_to(goal)<1e-6:return True
        record=self.routes.get(actor)
        if record is None or record['goal']!=goal:
            record={'goal':goal,'path':None,'retry':0};self.routes[actor]=record
        record['retry']=max(0,record['retry']-1/60)
        if record['path'] is None:
            if record['retry']:return False
            record['path']=deque([goal]) if direct else find_path(world,actor.position,goal,actor.probe_size,actor,self.player(world))
            if record['path'] is None:record['retry']=.5;return False
        budget=speed/60
        while budget>1e-7 and record['path']:
            delta=pygame.Vector2(record['path'][0])-actor.position;distance=delta.length()
            if distance<1e-7:record['path'].popleft();continue
            direction=delta/distance;step=min(1,budget,distance);candidate=actor.position+direction*step
            if not world.can_stand(candidate,actor.probe_size,actor,self.player(world)):
                record['path']=None;record['retry']=.3
                # A bounded collision-aware detour replaces an obstructed oval segment.
                if direct:record['path']=find_path(world,actor.position,goal,actor.probe_size,actor,self.player(world))
                return False
            actor.position.update(candidate);budget-=step;pose.moving=True
            pose.running=speed>50;pose.walk_ms+=step/speed*1000
            pose.facing=('right' if direction.x>0 else 'left') if abs(direction.x)>abs(direction.y) else ('front' if direction.y>0 else 'back')
            if step>=distance-1e-7:record['path'].popleft()
        return actor.position.distance_squared_to(goal)<1e-6

    def _transfer(self,actor,origin_door):
        origin=self.worlds[actor];door=next(d for d in origin.doors if d.data['id']==origin_door)
        if actor.position.distance_to((door.data['anchor'][0],door.data['entry_y']))>1.5:return False
        if door.data['requires_open'] and door.state!='open':return False
        destination=self.home if origin is self.town else self.town
        arrival=door.data['spawn']
        if not destination.can_stand(arrival,actor.probe_size,actor,self.player(destination)):return False
        origin.npcs.remove(actor);destination.npcs.append(actor);actor.position.update(arrival)
        self.worlds[actor]=destination;self.routes.pop(actor,None)
        next(d for d in destination.doors if d.data['id']==door.data['arrival_door']).force_open()
        self.events.append({'transfer':actor.data['id'],'scene':destination.data['id']})
        return True

    def _available(self):
        if self.liam_owner is not None:return False
        bone=getattr(self.daisy,'bone_routine',None)
        if bone is not None and bone.active:
            bone.request_release();return False
        return (self.liam_owner is None and not self.daisy.play_owned
                and not self.daisy.rest_protected
                and self.worlds[self.daisy] is self.home and self.daisy.active_bowl is None
                and self.daisy.state in ('rest','pause'))

    def _start(self):
        d=self.daisy
        # Find a reachable nearby invitation spot without moving Daisy artificially.
        for dx,dy in ((-28,0),(28,0),(0,-24),(0,24)):
            point=(round((d.position.x+dx)/2)*2,round((d.position.y+dy)/2)*2)
            if find_path(self.home,self.liam.position,point,self.liam.probe_size,self.liam,self.player(self.home)) is not None:
                self.invite_spot=point;break
        else:return False
        self.was_lying=d.state=='rest';d.play_owned=True;d.play_pose=None;d.opens_doors=True
        self.drink_choice=None;self._state('find_daisy');return True

    def update(self,seconds):
        self._accumulator+=seconds;count=int((self._accumulator+1e-9)*60);self._accumulator-=count/60
        for _ in range(count):self._tick()

    def _tick(self):
        ms=1000/60;self.state_ms+=ms
        if self.state=='cooldown':
            self.cooldown_ms-=ms
            if self.cooldown_ms<=0 and self._available():self._start()
            return
        d=self.daisy;l=self.liam
        if self.state!='daisy_return':
            for kind in d.cooldowns:d.cooldowns[kind]-=ms
        for pose in (l,self.dog_pose):pose.moving=False
        if self.state=='find_daisy':
            if self._move(l,self.invite_spot,44):self._state('stand_daisy' if self.was_lying else 'invite')
        elif self.state=='stand_daisy':
            d.play_pose=self.dog_pose;self._action(d,'stand_up',self.state_ms)
            if self.state_ms>=720:self._state('invite')
        elif self.state=='invite':
            d.play_pose=self.dog_pose;self.dog_pose.facing='right' if l.position.x>d.position.x else 'left'
            l.facing='left' if l.position.x>d.position.x else 'right'
            self._action(l,f'invite_{l.facing}',self.state_ms)
            if self.state_ms>=2000:self._state('hop')
        elif self.state=='hop':
            self._action(d,f'hop_{self.dog_pose.facing}',self.state_ms%560)
            if self.state_ms>=1120:self._state('wag')
        elif self.state=='wag':
            self._action(d,f'wag_{self.dog_pose.facing}',self.state_ms%720)
            if self.state_ms>=1080:self._state('exit_liam')
        elif self.state=='exit_liam':
            # Daisy queues clear of both the threshold and Liam's route.
            self._move(d,(228,288))
            if self._move(l,(252,306),44) and self._transfer(l,'courtyard'):self._state('exit_daisy')
        elif self.state=='exit_daisy':
            self._move(l,(314,552),44)
            if self._move(d,(252,306)) and self._transfer(d,'courtyard'):self._state('line_up')
        elif self.state=='line_up':
            a=self._move(l,self.track[0],44);b=self._move(d,self.track[22])
            if a and b:
                self.liam_index=1;self.daisy_index=-1;self._state('chase')
        elif self.state=='chase':
            # Shared route, with a trailing distance. Stop the leader if Daisy is delayed.
            gap=l.position.distance_to(d.position)
            if self.liam_index<=self.last_index:
                if gap<58 and self._move(l,self.track[self.liam_index%24],self._run_speed(l),True):self.liam_index+=1
            else:self._move(l,(330,548),44)
            if gap>24 or self.liam_index>self.last_index:
                if self._move(d,self.track[self.daisy_index%24],self._run_speed(d),True):self.daisy_index+=1
            if self.liam_index>self.last_index and self.daisy_index>self.last_index:self._state('return_liam')
        elif self.state=='return_liam':
            self._move(d,(314,558))
            if self._move(l,(288,534),44) and self._transfer(l,'liam_house'):self._state('return_daisy')
        elif self.state=='return_daisy':
            self._move(l,(224,286),44)
            if self._move(d,(288,534)) and self._transfer(d,'liam_house'):
                self.drink_choice=self._rng.random()<self.config['drink_probability'] if self._forced_choice is None else self._forced_choice
                self._forced_choice=None;self.events.append({'drink_choice':self.drink_choice})
                d.play_pose=None;d.state='play';d.activity=None
                if self.drink_choice:d.begin_activity('water',self.home)
                else:d._return_home()
                self._state('daisy_return');self.liam_bed_state='walk';self.liam_bed_ms=0
        elif self.state=='daisy_return':
            self._bed_tick(ms)
            if d.state!='rest':d._tick(ms,self.home,self.player(self.home))
            else:
                for kind in d.cooldowns:d.cooldowns[kind]-=ms
            if self.liam_bed_state=='asleep' and d.state=='rest':
                self.rest_duration=self._rng.randint(*self.config['rest_ms']);self._state('nap')
                l.action='settle_bed';l.action_ms=1199
        elif self.state=='nap':
            l.action='settle_bed';l.action_ms=1199
            # Keep Daisy resting until both have had their post-play nap.
            if self.state_ms>=self.rest_duration:self._state('wake_liam')
        elif self.state=='wake_liam':
            self._action(l,'leave_bed',self.state_ms)
            if self.state_ms>=880:
                l.sort_y=None;l.action=None;l.facing='front'
                d.play_owned=False;d.play_pose=None;d.opens_doors=False;d.activity=None
                d._transition('rest',d._sample('rest_ms'))
                self.completed_cycles+=1;self.cooldown_ms=self._rng.randint(*self.config['cooldown_ms']);self._state('cooldown')

    def _run_speed(self,actor):
        return 56 if abs(actor.position.x-296)>52 else 64

    def _bed_tick(self,ms):
        l=self.liam
        if self.liam_bed_state=='walk':
            if self._move(l,(88,246),44):
                self.liam_bed_state='settle';self.liam_bed_ms=0
                l.sort_y=next(e['sort_y'] for e in self.home.entities if e['id']=='liam_bed')+1
        else:
            self.liam_bed_ms+=ms;self._action(l,'settle_bed',self.liam_bed_ms)
            if self.liam_bed_ms>=1200:self.liam_bed_state='asleep'

    def draw(self,target,camera,world):
        if self.state!='invite' or self.worlds[self.liam] is not world:return
        font=self.game.small_font;text=font.render('Want to play, Daisy?',False,'#45382d')
        x=round(self.liam.position.x)-camera[0];y=round(self.liam.position.y)-camera[1]-43
        rect=text.get_rect(midbottom=(x,y)).inflate(10,8)
        pygame.draw.rect(target,'#fff1cc',rect);pygame.draw.rect(target,'#6e573f',rect,1)
        pygame.draw.polygon(target,'#fff1cc',[(x-3,rect.bottom-1),(x+3,rect.bottom-1),(x,rect.bottom+4)])
        target.blit(text,text.get_rect(center=rect.center))
