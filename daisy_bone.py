"""A single persistent dog toy with contact-based transfers and safe yielding."""
from collections import deque
import random
import pygame
from liam_daisy_play import read
from npc_routines import find_path

META='assets/characters/daisy/bone_play/animations.json'
PACK='assets/terrain/eldenmere/liam_home/bone/bone.json'


class BonePose:
    action=None
    def __init__(self,owner):self.owner=owner
    def sprite(self,elapsed_ms):return self.owner.sprite()


class DaisyBone:
    def __init__(self,game,home,shared,config):
        self.game=game;self.home=home;self.shared=shared;self.daisy=shared.daisy
        self.config=read(config);self.meta=read(META);self.pack=read(PACK);self._rng=random.Random()
        self.actions={name:[(home.image(f['file']),home.image(f['bone_file'])) for f in spec['frames']]
                      for name,spec in self.meta['actions'].items()}
        self.idles={name:(home.image(f['file']),home.image(f['bone_file'])) for name,f in self.meta['idle_frames'].items()}
        self.variants={name:home.image(spec['image']) for name,spec in self.pack['variants'].items()}
        self.bone={'id':'daisy_bone','state':'ground','position':pygame.Vector2(self.config['initial_position']),'orientation':'horizontal'}
        self.surface_props=[{'id':'daisy_bone','scene':home.data['id'],'surface':self.variants['horizontal'],
                             'position':[0,0],'sort_y':0,'sort_priority':1}]
        home.attach_routine_props(self);self.daisy.bone_routine=self;self.view=BonePose(self)
        self.state='cooldown';self.state_ms=0;self._accumulator=0;self.completed_cycles=0
        self.cooldown_ms=self._rng.randint(*self.config['cooldown_ms']);self.events=deque(maxlen=256)
        self.release_requested=False;self.kind='rug';self.playful=False;self.current_action=None
        self.contact_done=False;self.drop_point=None;self.paw_finished=False;self._update_prop()

    @property
    def active(self):return self.state!='cooldown'

    def surface_prop_visible(self,prop):return self.bone['state']=='ground'

    def _update_prop(self):
        spec=self.pack['variants'][self.bone['orientation']];prop=self.surface_props[0]
        prop.update(surface=self.variants[self.bone['orientation']],
                    position=list(self.bone['position']-pygame.Vector2(spec['draw_anchor'])),
                    sort_y=self.bone['position'].y+2)

    def _available(self):
        d=self.daisy
        return (not self.shared.active and self.shared.worlds[d] is self.home and d.available_for_activity()
                and d.state in ('rest','pause') and d._due()=='wander'
                and not any(r.active and r.accident_selected for r in self.game.block_routines))

    def begin(self,kind='rug',playful=None,drop_point=None):
        """Begin a normal toy session; selectors make review branches reproducible."""
        if kind not in ('rug','relocate'):raise ValueError(kind)
        if drop_point is not None and not self.valid_drop(drop_point):raise ValueError('Unsafe bone drop point')
        if self.active or not self._available():return False
        self.kind=kind;self.playful=self._rng.random()<.5 if playful is None else bool(playful)
        self.drop_point=pygame.Vector2(drop_point) if drop_point is not None else None
        self.pickup_position=self.bone['position'].copy()
        self.release_requested=False;self.paw_finished=False;self.daisy.play_owned=True
        self.was_lying=self.daisy.state=='rest';self.daisy.play_pose=self.view
        self._state('stand' if self.was_lying else 'approach');return True

    def request_release(self):
        if self.active:self.release_requested=True

    def _state(self,name):
        self.state=name;self.state_ms=0;self.contact_done=False;self.current_action=None
        self.shared.dog_pose.moving=False;self.events.append({'state':name})
        mapping={'pickup':'pickup_left','drop':'drop_left','bow':'play_bow','shake':'shake_left',
                 'settle':'settle_bone','chew':'chew_left','release_paws':'release_paws','nudge':'nudge_left'}
        self.current_action=mapping.get(name)
        if self.current_action:self.shared.dog_pose.facing='left'

    def _spec(self):return self.meta['actions'][self.current_action]

    @property
    def frame_index(self):
        if not self.current_action:
            return min(3,int(self.shared.dog_pose.walk_ms%560//140))
        spec=self._spec();time=self.state_ms
        if self.state in ('chew','shake'):time%=spec['duration_ms']
        else:time=min(time,spec['duration_ms']-1)
        for index,frame in enumerate(spec['frames']):
            if time<frame['duration_ms']:return index
            time-=frame['duration_ms']
        return 3

    @property
    def current_frame_record(self):
        if self.current_action:return self._spec()['frames'][self.frame_index]
        pose=self.shared.dog_pose
        if not pose.moving:return self.meta['idle_frames'][pose.facing]
        return self.meta['actions'][f'carry_walk_{pose.facing}']['frames'][self.frame_index]

    def _world_bone(self):
        return self.daisy.position-pygame.Vector2(self.daisy.draw_anchor)+self.current_frame_record['bone_local']

    def _sync_bone(self):
        if self.bone['state'] in ('mouth','paws'):
            self.bone['position'].update(self._world_bone())
        self._update_prop()

    def _transfer(self,state):
        before=self.bone['state'];self.bone['position'].update(self._world_bone());self.bone['state']=state
        if state=='ground':self._snap_ground()
        self.bone['orientation']='horizontal'
        self.events.append({'transfer':self.bone['id'],'from':before,'to':state,'position':list(self.bone['position'])})

    def _snap_ground(self):
        self.bone['position'].update(*(round(v) for v in self.bone['position']))

    def _contact(self,state):
        if not self.contact_done and self.frame_index>=self._spec()['contact_frame']:
            self.contact_done=True;self._transfer(state)

    def _move(self,goal):
        return self.shared._move(self.daisy,goal,self.config['speed'])

    def valid_drop(self,point):
        p=pygame.Vector2(point)
        if p.x%2 or p.y%2!=1:return False
        station=p+pygame.Vector2(10,1)
        if not self.home.can_stand(station,self.daisy.probe_size,self.daisy,self.shared.player(self.home)):return False
        # Check the complete toy footprint, not just Daisy's approach point.
        if not self.home.can_stand(p,(10,6),self.daisy,self.shared.player(self.home)):return False
        if any(p.distance_to(d.data['anchor'])<self.config['door_clear_radius'] for d in self.home.doors):return False
        for entity in self.home.entities:
            if entity.get('bowl_kind') and entity['rect'].inflate(12,10).collidepoint(p):return False
        for routine in self.game.block_routines:
            if routine.active and p.distance_to(routine.config['building_center'])<28:return False
            if any(b['state'] in ('placed','scattered','forgotten') and p.distance_to(b['center'])<12 for b in routine.blocks):return False
        return True

    def _choose_drop(self):
        if self.drop_point is not None and self.valid_drop(self.drop_point):return self.drop_point.copy()
        nearby=self.daisy.position+pygame.Vector2(-10,-1)
        nearby.update(round(nearby.x/2)*2,round((nearby.y-1)/2)*2+1)
        candidates=[]
        for dx,dy in ((0,0),(-12,0),(12,0),(0,-12),(0,12),(-24,0),(24,0)):
            candidates.append(nearby+pygame.Vector2(dx,dy))
        candidates.extend(pygame.Vector2(p) for p in self.config['drop_points'])
        if self.kind=='relocate' and not self.release_requested:
            candidates=[p for p in candidates if p.distance_to(self.pickup_position)>=24]
        if not self.release_requested:self._rng.shuffle(candidates)
        for point in candidates:
            if self.valid_drop(point) and find_path(self.home,self.daisy.position,point+pygame.Vector2(10,1),self.daisy.probe_size,self.daisy,self.shared.player(self.home)) is not None:return point
        return None

    def _finish(self,interrupted=False):
        if self.bone['state']!='ground':raise RuntimeError('Cannot release Daisy while she owns the bone')
        d=self.daisy;d.play_owned=False;d.play_pose=None;d.moving=False
        if interrupted:
            # Initialize the normal pause's wander bookkeeping before yielding.
            d.activity='wander';d._start_activity(self.home,self.shared.player(self.home));d._transition('pause',2000)
            due=d._due()
            if due!='wander':d.begin_activity(due,self.home)
        else:d.activity=None;d._transition('rest',d._sample('rest_ms'))
        self.completed_cycles+=1;self.cooldown_ms=self._rng.randint(*self.config['cooldown_ms']);self._state('cooldown')
        self.release_requested=False

    def update(self,seconds):
        self._accumulator+=seconds;count=int((self._accumulator+1e-9)*60);self._accumulator-=count/60
        for _ in range(count):self._tick(1000/60)
        self._update_prop()

    def _tick(self,ms):
        self.state_ms+=ms
        if not self.active:
            self.cooldown_ms-=ms
            if self.cooldown_ms<=0 and self._available():self.begin('rug' if self._rng.random()<.7 else 'relocate')
            return
        d=self.daisy
        for kind in d.cooldowns:d.cooldowns[kind]-=ms
        if d._due()!='wander':self.request_release()
        self.shared.dog_pose.moving=False
        if self.state=='stand':
            if self.state_ms>=720:self._state('approach')
        elif self.state=='approach':
            if self.release_requested:self._finish(True)
            elif self._move(self.bone['position']+pygame.Vector2(10,1)):self._state('pickup')
        elif self.state=='pickup':
            self._contact('mouth')
            if self.state_ms>=self._spec()['duration_ms']:self._state('carry')
        elif self.state=='carry':
            if self.release_requested or self.kind=='relocate':
                point=self._choose_drop()
                if point is not None:
                    self.drop_point=point
                    if self._move(point+pygame.Vector2(10,1)):self._state('drop')
            elif self._move(d.behavior['home']):self._state('bow' if self.playful else 'settle')
        elif self.state in ('bow','shake'):
            if self.state_ms>=self._spec()['duration_ms']*(2 if self.state=='shake' else 1):
                self._state('carry' if self.release_requested else ('shake' if self.state=='bow' else 'settle'))
        elif self.state=='settle':
            self._contact('paws')
            if self.state_ms>=self._spec()['duration_ms']:
                self.chew_ms=self._rng.randint(*self.config['chew_ms']);self._state('chew')
        elif self.state=='chew':
            cycle=self._spec()['duration_ms']
            if (self.release_requested and self.state_ms>=cycle) or self.state_ms>=self.chew_ms:self._state('release_paws')
        elif self.state=='release_paws':
            self._contact('ground')
            if self.state_ms>=self._spec()['duration_ms']:
                self._state('rise' if self.release_requested else ('nudge' if self.playful else 'rest_done'))
        elif self.state=='nudge':
            # The same ground object moves only the two pixels authored by the nose.
            if self.frame_index>=self._spec()['contact_frame']:
                self.bone['position'].update(self._world_bone())
                self._snap_ground()
            if self.state_ms>=self._spec()['duration_ms']:self._state('rise' if self.release_requested else 'rest_done')
        elif self.state=='drop':
            self._contact('ground')
            if self.state_ms>=self._spec()['duration_ms']:
                if self.release_requested:self._finish(True)
                else:self._state('wag_after_drop')
        elif self.state=='wag_after_drop':
            if self.release_requested:self._finish(True)
            elif self.state_ms>=720:self._state('return_home')
        elif self.state=='return_home':
            if self.release_requested:self._finish(True)
            elif self._move(d.behavior['home']):self._state('settle_empty')
        elif self.state=='settle_empty':
            if self.state_ms>=720:
                if self.release_requested:self._state('rise')
                else:self._finish(False)
        elif self.state=='rise':
            if self.state_ms>=720:self._finish(True)
        elif self.state=='rest_done':
            if self.release_requested:self._state('rise')
            else:self._finish(False)
        if self.active:self._sync_bone()

    def sprite(self):
        d=self.daisy;pose=self.shared.dog_pose
        original={'stand':'stand_up','rise':'stand_up','settle_empty':'settle_down'}
        if self.state in original:
            frames=d.actions[original[self.state]];index=min(3,int(self.state_ms//180));return frames[index][0]
        if self.state=='rest_done':return d.lying
        if self.state=='wag_after_drop':
            pose.action='wag_left';pose.action_ms=self.state_ms%720;return pose.sprite()
        key=self.current_action
        if key is None:
            if self.bone['state']=='mouth':key=f'carry_walk_{pose.facing}' if pose.moving else None
            else:return d.walks[pose.facing][self.frame_index][0] if pose.moving else d.idles[pose.facing]
        index=self.frame_index if self.current_action or pose.moving else 0
        body,overlay=self.actions[key][index] if key else self.idles[pose.facing]
        if self.bone['state'] in ('mouth','paws'):
            body=body.copy();body.blit(overlay,(0,0))
        return body
