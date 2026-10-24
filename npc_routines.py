"""Moving ambient NPC routines. Runtime uses only Pygame and checked-in art."""
from collections import deque
import heapq
import itertools
import json
import random
from pathlib import Path

import pygame

ROOT=Path(__file__).resolve().parent


def read_json(path):return json.loads(path.read_text())


def find_path(world,start,goal,size,actor,avoid=None):
    """Cardinal 2px A*: the same solid geometry as the player, with own feet.

    Fixed task waypoints keep travel on the lanes/stairs. A bounded local search
    can detour around the player; it never crosses water or climbs terrace walls.
    """
    step=2
    start=tuple(round(v/step)*step for v in start)
    goal=tuple(goal)
    if not world.can_stand(goal,size,actor,avoid):return None
    if start==goal:return deque([goal])
    serial=itertools.count()
    def heuristic(p):return abs(p[0]-goal[0])+abs(p[1]-goal[1])
    bounds=pygame.Rect(min(start[0],goal[0])-96,min(start[1],goal[1])-96,
                       abs(start[0]-goal[0])+193,abs(start[1]-goal[1])+193)
    queue=[(heuristic(start),heuristic(start),next(serial),start)]
    parents={start:None};costs={start:0}
    while queue and len(costs)<15000:
        _,_,_,p=heapq.heappop(queue)
        if p==goal:
            route=[]
            while p!=start:route.append(p);p=parents[p]
            route.reverse()
            # Retain only corners; the mover checks every intervening pixel.
            compact=[]
            for point in route:
                if len(compact)>1:
                    a,b=compact[-2:]
                    if (a[0]==b[0]==point[0]) or (a[1]==b[1]==point[1]):compact[-1]=point;continue
                compact.append(point)
            return deque(compact)
        for q in ((p[0]+step,p[1]),(p[0]-step,p[1]),(p[0],p[1]+step),(p[0],p[1]-step)):
            cost=costs[p]+step
            if cost>=costs.get(q,float('inf')) or not bounds.collidepoint(q):continue
            if not world.can_stand(q,size,actor,avoid):continue
            parents[q]=p;costs[q]=cost;h=heuristic(q)
            heapq.heappush(queue,(cost+h,h,next(serial),q))
    return None


class Gardener:
    """A persistent fill/carry/pour cycle, with collision-aware task progress."""
    def __init__(self,record,world,rng=None):
        self.data=record
        self.behavior=read_json(ROOT/record['behavior'])
        self.animation=read_json(ROOT/record['animation'])
        self.water_capacity=self.animation['water_capacity']
        self.well=world.well
        self._rng=rng if rng is not None else random.Random()
        self.rest_duration_ms=self._new_rest_duration()
        self.draw_anchor=self.animation['draw_anchor']
        self.position=pygame.Vector2(record['position'])
        self.probe_size=tuple(record['probe_size'])
        folder=Path(record['animation']).parent
        self.bodies={name:world.image((folder/pose['body']).as_posix()) for name,pose in self.animation['poses'].items()}
        self.buckets={name:world.image((folder/pose['file']).as_posix()) for name,pose in self.animation['buckets'].items()}
        self.steps=self._steps()
        self.step_index=0;self.state_ms=0.0;self.walk_ms=0.0
        self.facing='right';self.moving=False;self.waiting=False
        self.water_units=0;self.completed_cycles=0
        self.events=deque(maxlen=64);self.watered_beds=[]
        self.path=None;self.waypoint_index=0;self.blocked_seconds=0.0;self.retry_seconds=0.0
        self._sprite_cache={}
        self._accumulator=0.0

    @property
    def blocker(self):
        w,h=self.probe_size
        return pygame.Rect(round(self.position.x)-w//2,round(self.position.y)-h//2,w,h)

    @property
    def state(self):return self.steps[self.step_index]['id']

    @property
    def rest_remaining_ms(self):return max(0,self.rest_duration_ms-self.state_ms) if self.state=='rest' else 0

    def _new_rest_duration(self):return self._rng.randint(*self.behavior['rest_range_ms'])

    def _steps(self):
        b=self.behavior
        steps=[{'id':'rest','animation':'rest','facing':'right'},
               {'id':'pickup','animation':'pickup','facing':'right'},
               {'id':'to_well','waypoints':b['outbound_waypoints']},
               {'id':'well_attach','facing':'back'},
               {'id':'well_hook','facing':'back'},
               {'id':'well_settle','facing':'back'},
               {'id':'well_to_crank','waypoints':[self.well.data['operator_position']]},
               {'id':'well_grip','facing':'left'},
               {'id':'well_lower','facing':'left'},
               {'id':'well_fill','facing':'left'},
               {'id':'well_raise','facing':'left'},
               {'id':'well_lock','facing':'left'},
               {'id':'well_to_loading','waypoints':[self.well.data['loading_position']]},
               {'id':'well_catch','facing':'back'},
               {'id':'well_unhook','facing':'back'},
               {'id':'well_take','facing':'back'},
               {'id':'return_to_sanctuary','waypoints':b['return_waypoints']}]
        for index,bed in enumerate(b['beds']):
            via=[bed['position']]
            if index==0:via=[[340,334],bed['position']]
            if index==2:via=[*b['garden_crossing'],bed['position']]
            if 'via' in bed:via=[*bed['via'],bed['position']]
            steps.extend([
                {'id':'approach_'+bed['id'],'waypoints':via},
                {'id':'inspect_'+bed['id'],'animation':'inspect.'+bed['facing'],'facing':bed['facing'],'bed':bed},
                {'id':'water_'+bed['id'],'animation':bed.get('pour_animation','pour.'+bed['facing']),'facing':bed['facing'],'bed':bed},
            ])
        steps.extend([{'id':'return_to_rest','waypoints':b['rest_waypoints']},
                      {'id':'setdown','animation':'setdown','facing':'right'}])
        return steps

    def _advance(self):
        old=self.steps[self.step_index]
        if old['id']=='well_fill':
            self.water_units=self.water_capacity
            self.events.append({'type':'filled','position':tuple(self.position),'units':self.water_capacity})
        if old['id']=='well_take':self.well.release(self)
        if old['id'].startswith('water_'):
            self.water_units=max(0,self.water_units-1)
            self.watered_beds.append(old['bed']['id'])
            self.events.append({'type':'watered','bed':old['bed']['id'],'units':self.water_units})
        self.step_index=(self.step_index+1)%len(self.steps)
        if self.step_index==0:
            self.completed_cycles+=1
            self.rest_duration_ms=self._new_rest_duration()
            self.events.append({'type':'cycle','cycle':self.completed_cycles,'rest_duration_ms':self.rest_duration_ms})
        if self.state=='pickup':self.watered_beds=[]
        self.state_ms=0;self.walk_ms=0;self.path=None;self.waypoint_index=0
        self.blocked_seconds=0;self.retry_seconds=0;self.moving=False;self.waiting=False
        self.facing=self.steps[self.step_index].get('facing',self.facing)

    def update(self,seconds,world,player_blocker=None):
        # Stable movement/action timing even when headless tests pass a large dt.
        self._accumulator+=seconds
        count=int((self._accumulator+1e-9)*60)
        self._accumulator-=count/60
        for _ in range(count):
            dt=1/60
            step=self.steps[self.step_index]
            if 'waypoints' in step:self._move(dt,world,player_blocker)
            else:
                self.moving=False;self.waiting=False
                if self.state.startswith('well_'):
                    if not self.well.reserve(self):self.waiting=True;continue
                    self.state_ms+=dt*1000
                    if self.state=='well_fill':
                        self.water_units=min(self.water_capacity,int(self.well.progress*(self.water_capacity+1)))
                    if self.state_ms+1e-7>=self.well.data['phases_ms'][self.state]:self._advance()
                    continue
                self.state_ms+=dt*1000
                duration=sum(f['duration_ms'] for f in self.animation['animations'][step['animation']])
                if self.state=='rest':duration=self.rest_duration_ms
                if self.state_ms+1e-7>=duration:self._advance()

    def _move(self,seconds,world,player):
        step=self.steps[self.step_index]
        self.moving=False;self.waiting=False
        if self.waypoint_index>=len(step['waypoints']):self._advance();return
        goal=step['waypoints'][self.waypoint_index]
        if self.position.distance_squared_to(goal)<1e-8:
            self.waypoint_index+=1;self.path=None;return
        if self.path is None:
            self.retry_seconds=max(0,self.retry_seconds-seconds)
            if self.retry_seconds:self.waiting=True;return
            self.path=find_path(world,self.position,goal,self.probe_size,self)
            if self.path is None:self.retry_seconds=1;self.waiting=True;return
        loaded=self.water_units and not self.state.startswith('well_')
        speed=self.behavior['loaded_speed'] if loaded else self.behavior['empty_speed']
        budget=speed*seconds
        while budget>1e-7 and self.path:
            delta=pygame.Vector2(self.path[0])-self.position
            distance=delta.length()
            if distance<1e-7:self.path.popleft();continue
            direction=delta/distance;travel=min(1.0,budget,distance)
            candidate=self.position+direction*travel
            if not world.can_stand(candidate,self.probe_size,self,player):
                self.waiting=True;self.blocked_seconds+=seconds
                if self.blocked_seconds>=.8:
                    # Detour only after a clear pause. In a single-file passage,
                    # keep the original path and wait instead of shoving past.
                    alternate=find_path(world,self.position,goal,self.probe_size,self,player)
                    if alternate is not None:self.path=alternate
                    self.blocked_seconds=0
                return
            self.position.update(candidate);budget-=travel
            self.walk_ms+=travel/60*1000
            self.facing=('right' if direction.x>0 else 'left') if abs(direction.x)>abs(direction.y) else ('front' if direction.y>0 else 'back')
            self.moving=True;self.blocked_seconds=0
        if not self.path:self.path=None

    def pose(self):
        step=self.steps[self.step_index]
        if self.state.startswith('well_') and 'waypoints' not in step:
            if self.state=='well_attach':
                return f'well_attach_back_{min(6,int(self.well.progress*7))}',{'level':self.water_units}
            if self.state=='well_hook':
                return 'well_attach_back_6',{'level':self.water_units}
            if self.state=='well_settle':
                return f'well_release_back_{min(4,int(self.well.progress*5))}',{'hidden_bucket':True}
            if self.state=='well_catch':
                return f'well_catch_back_{min(6,int(self.well.progress*7))}',{'hidden_bucket':True}
            if self.state=='well_unhook':
                return 'well_unhook_back',{'level':self.water_units}
            if self.state=='well_take':
                return f'well_take_back_{min(6,int(self.well.progress*7))}',{'level':self.water_units}
            if self.state in ('well_grip','well_lower','well_fill','well_raise','well_lock'):
                prefix='well_heavy_left_' if self.state=='well_raise' else 'well_crank_left_'
                return prefix+str(self.well.crank_index),{'hidden_bucket':True}
        if 'waypoints' in step:
            mode='full' if self.water_units and not self.state.startswith('well_') else 'empty'
            key=(f'carry_{mode}.' if self.moving else f'idle_{mode}.')+self.facing
            if not self.moving:return key,{}
            frames=self.animation['animations'][key];time=self.walk_ms%560
        else:
            frames=self.animation['animations'][step['animation']];time=self.state_ms
        for frame in frames:
            if time<frame['duration_ms']:return frame['pose'],frame
            time-=frame['duration_ms']
        return frames[-1]['pose'],frames[-1]

    def bucket_placement(self):
        name,frame=self.pose();pose=self.animation['poses'][name]
        level=frame.get('level',self.water_units)
        angle=frame.get('angle',0)
        key=f'bucket_{angle}_{level}';bucket=self.animation['buckets'][key]
        xy=pygame.Vector2(self.animation['body_offset'])+pose['grip']-pygame.Vector2(bucket['grip'])
        return name,frame,pose,key,xy

    def sprite(self,elapsed_ms):
        name,frame,pose,key,xy=self.bucket_placement()
        if frame.get('hidden_bucket') or (self.state.startswith('well_') and 'waypoints' in self.steps[self.step_index]):
            return self.bodies[name]
        if self.state in ('well_attach','well_hook','well_unhook','well_take'):
            # One pail, registered to both hands before removing its hook.
            image=self.bodies[name].copy()
            image.blit(self.buckets[key],xy)
            return image
        submerged=frame.get('effect')=='ripple'
        cache_key=(name,key,submerged)
        if cache_key not in self._sprite_cache:
            canvas=pygame.Surface(self.animation['action_canvas'],pygame.SRCALPHA)
            if pose['order']=='before':canvas.blit(self.buckets[key],xy)
            canvas.blit(self.bodies[name],(0,0))
            if pose['order']=='after':
                bucket_image=self.buckets[key]
                if submerged:
                    bucket_image=bucket_image.copy()
                    bucket_image.fill((0,0,0,0),(0,16,32,16))
                canvas.blit(bucket_image,xy)
            self._sprite_cache[cache_key]=canvas
        image=self._sprite_cache[cache_key]
        effect=frame.get('effect')
        if not effect:return image
        image=image.copy();phase=int(elapsed_ms//100)%4
        ink='#b9d9d2';blue='#598e9f'
        bucket=self.animation['buckets'][key]
        if effect=='pour':
            origin=xy+bucket['spout']
            world_origin=self.position-pygame.Vector2(self.draw_anchor)
            target=pygame.Vector2(self.steps[self.step_index]['bed']['root'])-world_origin
            middle=origin.lerp(target,.5);middle.y-=1
            points=[tuple(round(v) for v in p) for p in (origin,middle,target)]
            pygame.draw.lines(image,blue,False,points,2)
            pygame.draw.lines(image,ink,False,points,1)
            t=(phase+1)/5
            drop=origin.lerp(target,t)
            image.set_at((round(drop.x),round(drop.y)),pygame.Color(blue))
            x,y=points[-1]
            for dx,dy in ((-2,-(phase%2)),(2,-((phase+1)%2))):
                if 0<=x+dx<48 and 0<=y+dy<48:image.set_at((x+dx,y+dy),pygame.Color(ink))
        elif effect=='ripple':
            # Contact stays in the brook while the gardener's foot probe is dry.
            center=self.position-pygame.Vector2(self.draw_anchor)
            contact=pygame.Vector2(self.behavior['source_contact'])-center
            radius=4+phase
            x,y=round(contact.x),round(contact.y)
            pygame.draw.line(image,ink,(x-radius,y-1),(x-4,y-2),1)
            pygame.draw.line(image,ink,(x+4,y-2),(x+radius,y-1),1)
        elif effect=='drips':
            base=xy+pygame.Vector2(13,18)
            for n in range(2):
                x,y=round(base.x+n*2),round(base.y+(phase+n)%4)
                if 0<=x<48 and 0<=y<48:image.set_at((x,y),pygame.Color(ink))
        return image
