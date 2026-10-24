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


class RoutineNPC:
    """A data-driven actor that can keep one schedule across several rooms.

    The game owns scene membership.  A transfer step asks the supplied callback
    to move this same object to the destination world, and advances only after
    that callback succeeds.  This keeps schedules independent of ``Game`` while
    ensuring an actor is never cloned or reset at a doorway.
    """
    DIRECTIONS=('front','left','right','back')
    STEP_TYPES=frozenset(('move','action','wait','transfer'))

    def __init__(self,record,world,scene_id=None):
        self.data=record
        self.behavior=read_json(ROOT/record['behavior'])
        self.animation=read_json(ROOT/record['animation'])
        self.steps=self.behavior['steps']
        if not self.steps:raise ValueError(f'Routine {record["id"]!r} has no steps')
        self.scene_id=scene_id or record.get('scene') or self.behavior['start_scene']
        self.position=pygame.Vector2(record.get('position',self.behavior['start_position']))
        self.probe_size=tuple(record.get('probe_size',self.behavior.get('probe_size',(12,8))))
        self.speed=float(self.behavior.get('speed',48))
        if self.speed<=0:raise ValueError(f'Routine {record["id"]!r} speed must be positive')

        self.canvas_size=tuple(self.animation.get('action_canvas',
                                                  self.animation.get('frame_size',(48,48))))
        base_anchor=tuple(record.get('draw_anchor',(12,34)))
        self.draw_anchor=tuple(self.animation.get('draw_anchor',base_anchor))
        self.body_offset=tuple(self.animation.get(
            'body_offset',(self.draw_anchor[0]-base_anchor[0],
                           self.draw_anchor[1]-base_anchor[1])))

        self.idles={};self.walks={};self.actions={};self.action_metadata={}
        self.action_records={};self.surface_props=[]
        self._load_images(world)
        self._validate_steps()
        self.step_index=0;self.state_ms=0.0;self.walk_ms=0.0
        self.facing=self.steps[0].get('facing','front')
        self.moving=False;self.waiting=False;self.completed_cycles=0
        self.path=None;self.waypoint_index=0;self.blocked_seconds=0.0;self.retry_seconds=0.0
        self.events=deque(maxlen=64)
        self._accumulator=0.0

    def _asset_path(self,raw,folder=None):
        """Return an image path relative to ROOT, accepting either JSON style."""
        raw=Path(raw)
        if raw.is_absolute():candidates=(raw,)
        elif raw.parts[:1]==('assets',):candidates=(ROOT/raw,)
        else:candidates=((folder/raw) if folder is not None else ROOT/raw,ROOT/raw)
        path=next((candidate for candidate in candidates if candidate.is_file()),candidates[0])
        try:return path.relative_to(ROOT).as_posix()
        except ValueError:return path.as_posix()

    def _load_images(self,world):
        metadata_path=ROOT/self.data['animation']
        metadata_folder=metadata_path.parent
        sprite_root=Path(self.animation.get('sprite_root',self.data['sprite_root']))
        if not sprite_root.is_absolute():sprite_root=ROOT/sprite_root

        for direction in self.DIRECTIONS:
            idle=world.image((sprite_root/f'idle_{direction}.png').relative_to(ROOT).as_posix())
            self.idles[direction]=self._padded(idle)
            walk_folder=sprite_root/f'walk_{direction}'
            walk_data=read_json(walk_folder/'animation.json')
            frames=[]
            for frame in walk_data['frames']:
                image=world.image((walk_folder/frame['file']).relative_to(ROOT).as_posix())
                frames.append((self._padded(image),int(frame['duration_ms'])))
            self.walks[direction]=frames

        # Early drafts used ``actions: {key: [frames]}``; the richer approved
        # export uses ``animations: {key: {frames, facing, duration_ms}}``.
        # Normalizing both here keeps the runtime and review export decoupled.
        raw_actions=self.animation.get('animations',self.animation.get('actions',{}))
        for name,specification in raw_actions.items():
            metadata=specification if isinstance(specification,dict) else {}
            records=metadata.get('frames',[]) if metadata else specification
            frames=[]
            for frame in records:
                path=self._asset_path(frame['file'],metadata_folder)
                image=world.image(path)
                frame_duration=int(frame['duration_ms'])
                if frame_duration<=0:
                    raise ValueError(f'Routine action {name!r} has a nonpositive frame duration')
                frames.append((self._padded(image),frame_duration))
            if not frames:raise ValueError(f'Routine action {name!r} has no frames')
            duration=sum(frame[1] for frame in frames)
            declared=int(metadata.get('duration_ms',duration))
            if declared!=duration:
                raise ValueError(f'Routine action {name!r} duration is {declared}, frames total {duration}')
            self.actions[name]=frames
            self.action_metadata[name]=metadata
            self.action_records[name]=records

        # Workstation props belong to their rooms rather than Serene's body
        # sprite.  Keeping their data on the persistent actor lets every room
        # ask the same schedule which copy is currently visible.
        behavior_folder=(ROOT/self.data['behavior']).parent
        for record in self.behavior.get('surface_props',[]):
            image_path=record.get('file',record.get('image'))
            if not image_path:
                raise ValueError(f'Surface prop {record.get("id", "<unknown>")!r} needs a file')
            prop=dict(record)
            prop['surface']=world.image(self._asset_path(image_path,behavior_folder))
            self.surface_props.append(prop)

    def _padded(self,image):
        if image.get_size()==self.canvas_size:return image
        canvas=pygame.Surface(self.canvas_size,pygame.SRCALPHA)
        canvas.blit(image,self.body_offset)
        return canvas

    def _validate_steps(self):
        seen=set()
        for index,step in enumerate(self.steps):
            label=f'Routine step {index}'
            if not isinstance(step,dict):raise ValueError(f'{label} must be an object')
            if not step.get('id'):raise ValueError(f'{label} needs an id')
            if step['id'] in seen:raise ValueError(f'Duplicate routine step id {step["id"]!r}')
            seen.add(step['id'])
            kind=step.get('type')
            if kind not in self.STEP_TYPES:raise ValueError(f'{label} has unknown type {kind!r}')
            if kind=='move' and not step.get('waypoints'):
                raise ValueError(f'Move step {step["id"]!r} needs waypoints')
            if kind=='action' and step.get('animation') not in self.actions:
                raise ValueError(f'Action step {step["id"]!r} names a missing animation')
            if 'duration_ms' in step and int(step['duration_ms'])<=0:
                raise ValueError(f'Step {step["id"]!r} has a nonpositive duration_ms')
            if kind=='wait' and int(step.get('duration_ms',0))<=0:
                raise ValueError(f'Wait step {step["id"]!r} needs a positive duration_ms')
            if kind=='transfer' and ('scene' not in step or 'position' not in step):
                raise ValueError(f'Transfer step {step["id"]!r} needs scene and position')
            if 'facing' in step and step['facing'] not in self.DIRECTIONS:
                raise ValueError(f'Step {step["id"]!r} has invalid facing {step["facing"]!r}')

        prop_ids=set()
        step_types={step['id']:step['type'] for step in self.steps}
        for prop in self.surface_props:
            label=f'Surface prop {prop.get("id", "<unknown>")!r}'
            if not prop.get('id'):raise ValueError('Surface prop needs an id')
            if prop['id'] in prop_ids:raise ValueError(f'Duplicate surface prop id {prop["id"]!r}')
            prop_ids.add(prop['id'])
            if not prop.get('scene'):raise ValueError(f'{label} needs a scene')
            if len(prop.get('position',()))!=2:raise ValueError(f'{label} needs a two-value position')
            action_steps=self._surface_prop_steps(prop)
            unknown=set(action_steps)-set(step_types)
            if unknown:raise ValueError(f'{label} names unknown action steps {sorted(unknown)!r}')
            if any(step_types[step_id]!='action' for step_id in action_steps):
                raise ValueError(f'{label} may only name action steps')

    @property
    def blocker(self):
        width,height=self.probe_size
        return pygame.Rect(round(self.position.x)-width//2,round(self.position.y)-height//2,
                           width,height)

    @property
    def state(self):return self.steps[self.step_index]['id']

    @property
    def step(self):return self.steps[self.step_index]

    @property
    def action_id(self):return self.step.get('animation') if self.step['type']=='action' else None

    @property
    def frame_index(self):
        if self.action_id:return self._frame_index(self.actions[self.action_id],self.state_ms)
        if self.moving:return self._frame_index(self.walks[self.facing],self.walk_ms)
        return 0

    @property
    def current_action_record(self):
        """Authored metadata for the action image currently on screen."""
        if not self.action_id:return {}
        return self.action_records[self.action_id][self.frame_index]

    @property
    def current_action_frame_metadata(self):
        """Compatibility name for inspection and focused runtime tests."""
        return self.current_action_record

    @staticmethod
    def _surface_prop_steps(prop):
        action_steps=prop.get('action_steps',prop.get('action_step',()))
        if isinstance(action_steps,str):action_steps=(action_steps,)
        return tuple(action_steps)

    def surface_prop_visible(self,prop):
        """Whether a room-owned prop should be drawn in the current frame.

        The prop stays on its furniture for the whole schedule. During its own
        action, one authored frame flag atomically moves ownership between the
        surface sprite and actor sprite, preventing duplicates and blank gaps.
        """
        action_steps=self._surface_prop_steps(prop)
        if self.state not in action_steps or not self.action_id:return True
        return self.current_action_record.get('prop_owner','surface')!='actor'

    def visible_surface_props(self,scene_id):
        """Visible, nonblocking workstation props in one scene."""
        return [prop for prop in self.surface_props
                if prop['scene']==scene_id and self.surface_prop_visible(prop)]

    def _duration(self,step=None):
        step=self.step if step is None else step
        if 'duration_ms' in step:return int(step['duration_ms'])
        if step['type']=='action':return sum(duration for _,duration in self.actions[step['animation']])
        return 0

    def _step_facing(self,step,default):
        if 'facing' in step:return step['facing']
        if step['type']=='action':return self.action_metadata[step['animation']].get('facing',default)
        return default

    def _advance(self):
        old=self.step
        self.step_index=(self.step_index+1)%len(self.steps)
        if self.step_index==0:
            self.completed_cycles+=1
            self.events.append({'type':'cycle','cycle':self.completed_cycles})
        self.state_ms=0.0;self.walk_ms=0.0;self.path=None;self.waypoint_index=0
        self.blocked_seconds=0.0;self.retry_seconds=0.0;self.moving=False;self.waiting=False
        self.facing=self._step_facing(self.step,self.facing)
        self.events.append({'type':'step','from':old['id'],'to':self.state})

    def select_step(self,step_id,position=None,scene_id=None,facing=None):
        """Select one named step for deterministic review and focused tests.

        Review coordinates from the behavior file are used when available.
        Scene membership remains the caller's responsibility, just as it is for
        a normal transfer callback.
        """
        try:index=next(i for i,step in enumerate(self.steps) if step['id']==step_id)
        except StopIteration as error:raise KeyError(f'Unknown routine step {step_id!r}') from error
        review=self.behavior.get('review',{}).get(step_id,{})
        if position is None:position=review.get('station')
        if scene_id is None:scene_id=review.get('scene')
        self.step_index=index
        if position is not None:self.position.update(position)
        if scene_id is not None:self.scene_id=scene_id
        self.state_ms=0.0;self.walk_ms=0.0;self.path=None;self.waypoint_index=0
        self.blocked_seconds=0.0;self.retry_seconds=0.0;self.moving=False;self.waiting=False
        self._accumulator=0.0
        default_facing=self._step_facing(self.step,self.facing)
        self.facing=facing or default_facing
        if self.facing not in self.DIRECTIONS:raise ValueError(f'Invalid facing {self.facing!r}')
        return self

    def update(self,seconds,world,player_blocker=None,transfer=None):
        """Advance the schedule; return True only when a transfer succeeds."""
        if seconds<0:raise ValueError('Routine update seconds must be nonnegative')
        self._accumulator+=seconds
        count=int((self._accumulator+1e-9)*60)
        self._accumulator-=count/60
        for index in range(count):
            if self._tick(1/60,world,player_blocker,transfer):
                # Remaining ticks belong to the destination world.  Keep them
                # for the next call instead of simulating there with this world.
                self._accumulator+=(count-index-1)/60
                return True
        return False

    def _tick(self,seconds,world,player_blocker,transfer):
        step=self.step;kind=step['type']
        if kind=='move':
            self._move(seconds,world,player_blocker)
            return False
        self.moving=False;self.waiting=False
        self.facing=self._step_facing(step,self.facing)
        if kind=='transfer':
            if transfer is None or not transfer(self,step):
                self.waiting=True
                return False
            self.scene_id=step['scene'];self.position.update(step['position'])
            self.events.append({'type':'transfer','scene':self.scene_id,
                                'position':tuple(self.position)})
            self._advance()
            return True
        self.state_ms+=seconds*1000
        if self.state_ms+1e-7>=self._duration(step):self._advance()
        return False

    def _move(self,seconds,world,player):
        step=self.step;waypoints=step['waypoints']
        self.moving=False;self.waiting=False
        if self.waypoint_index>=len(waypoints):self._advance();return
        goal=waypoints[self.waypoint_index]
        if self.position.distance_squared_to(goal)<1e-8:
            self.waypoint_index+=1;self.path=None
            if self.waypoint_index>=len(waypoints):self._advance()
            return
        if self.path is None:
            self.retry_seconds=max(0.0,self.retry_seconds-seconds)
            if self.retry_seconds>1e-8:self.waiting=True;return
            self.path=find_path(world,self.position,goal,self.probe_size,self,player)
            if self.path is None:self.retry_seconds=.5;self.waiting=True;return
        speed=float(step.get('speed',self.speed))
        if speed<=0:raise ValueError(f'Move step {step["id"]!r} speed must be positive')
        budget=speed*seconds
        while budget>1e-7 and self.path:
            target=pygame.Vector2(self.path[0]);delta=target-self.position;distance=delta.length()
            if distance<1e-7:self.path.popleft();continue
            direction=delta/distance;travel=min(1.0,budget,distance)
            candidate=self.position+direction*travel
            if not world.can_stand(candidate,self.probe_size,self,player):
                self.waiting=True;self.blocked_seconds+=seconds
                if self.blocked_seconds>=.8:
                    alternate=find_path(world,self.position,goal,self.probe_size,self,player)
                    if alternate is not None:self.path=alternate
                    self.blocked_seconds=0.0
                return
            self.position.update(candidate);budget-=travel
            self.walk_ms+=travel/speed*1000
            self.facing=(('right' if direction.x>0 else 'left') if abs(direction.x)>abs(direction.y)
                         else ('front' if direction.y>0 else 'back'))
            self.moving=True;self.blocked_seconds=0.0
            if travel+1e-7>=distance:self.path.popleft()
        if not self.path:
            self.path=None
            if self.position.distance_squared_to(goal)<1e-8:
                self.waypoint_index+=1
                if self.waypoint_index>=len(waypoints):self._advance()

    @staticmethod
    def _frame_index(frames,time_ms):
        duration=sum(duration for _,duration in frames)
        cursor=time_ms%duration
        for index,(_,frame_duration) in enumerate(frames):
            if cursor<frame_duration:return index
            cursor-=frame_duration
        return len(frames)-1

    def sprite(self,elapsed_ms):
        if self.action_id:
            frames=self.actions[self.action_id]
            return frames[self._frame_index(frames,self.state_ms)][0]
        if self.moving:
            frames=self.walks[self.facing]
            return frames[self._frame_index(frames,self.walk_ms)][0]
        return self.idles[self.facing]


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
