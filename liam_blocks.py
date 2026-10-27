"""Five conserved wooden toys, with coordinated child/dog activity ownership."""
from collections import deque
import random
import pygame
from liam_daisy_play import read
from ui_style import draw_ambient_speech

META='assets/characters/liam_family/block_play/animations.json'
PACK='assets/terrain/eldenmere/liam_home/blocks/blocks.json'


class LiamBlocks:
    def __init__(self,game,home,shared,config):
        self.game=game;self.home=home;self.shared=shared;self.liam=shared.liam;self.daisy=shared.daisy
        self.config=read(config);self.meta=read(META);self.pack=read(PACK);self._rng=random.Random()
        self.blocks=[];self.surface_props=[]
        for spec,center in zip(self.pack['blocks'],self.config['block_centers']):
            surface=home.image(spec['image']);anchor=pygame.Vector2(spec['draw_anchor'])
            block={**spec,'state':'box','center':pygame.Vector2(center),'surface':surface,'anchor':anchor}
            prop={'id':spec['id'],'scene':home.data['id'],'surface':surface,'position':[0,0],'sort_y':209,'sort_priority':1}
            block['prop']=prop;self.blocks.append(block);self.surface_props.append(prop)
        for name,spec in self.meta['actions'].items():
            frames=[(home.image(f['file']),f['duration_ms']) for f in spec['frames']]
            if name.startswith('curious_'):shared.dog_pose.actions[name]=frames
            else:self.liam.actions[name]=frames
        home.attach_routine_props(self)
        self.state='cooldown';self.state_ms=0;self._accumulator=0;self.completed_cycles=0
        self.cooldown_ms=self._rng.randint(*self.config['initial_delay_ms'])
        self.events=deque(maxlen=256);self.forgotten_id=None;self.current=None;self.held=None
        self.accident_rolled=False;self.accident_selected=False;self.dog_owned=False;self.dog_returning=False
        self.forget_selected=False;self._forced_accident=None;self._forced_forget=None
        self._contact_done=False;self.mode='build';self.index=0;self.release_requested=False
        self.box=next(e for e in home.entities if e['id']=='liam_block_box')
        self.lip=home.image(self.pack['front_overlay'])
        self._sync_props()

    @property
    def active(self):return self.state!='cooldown'

    def request_release(self):
        """Finish any current contact, then put every loose block away."""
        self.release_requested=True
        if self.active and self.mode=='cleanup':
            queued={id(block) for block in self.queue}
            extra=[block for block in self.blocks
                   if block['state'] in ('placed','scattered','forgotten') and
                   block is not self.current and id(block) not in queued]
            self.queue.extend(extra)
            if extra and self.state=='leave_play_area':self._next_loose()
        if not self.active and any(b['state']!='box' for b in self.blocks):
            self.shared.liam_owner=self;self.liam.work_renderer=self
            self._begin_release()

    def _begin_release(self):
        self.mode='cleanup';self.accident_selected=False;self.forget_selected=False
        self._forced_accident=None;self._forced_forget=None
        self.queue=[b for b in reversed(self.blocks) if b['state'] in ('placed','scattered','forgotten')]
        if self.dog_owned and not self.dog_returning:
            self.daisy.play_pose=None;self.daisy.state='play';self.daisy.activity=None
            self.daisy._return_home();self.dog_returning=True
        kneeling=bool(self.liam.action and self.liam.action.startswith(('kneel_','take_','place_','collect_','return_')))
        if self.held is not None:
            self.current=self.held
            self._state('yield_rise' if kneeling else 'carry_to_box')
        elif kneeling:self._state('yield_rise')
        else:self._next_loose()

    def reset_for_story(self):
        """Restore the unpersisted toy activity for New Game/Continue staging."""
        for block,center in zip(self.blocks,self.config['block_centers']):
            block['state']='box';block['center'].update(center)
        self.current=None;self.held=None;self.forgotten_id=None;self.queue=[]
        if self.dog_owned:
            self.daisy.play_owned=False;self.daisy.play_pose=None
            self.daisy.activity=None;self.daisy._return_home()
        self.dog_owned=False;self.dog_returning=False;self.release_requested=False
        self.liam.work_renderer=None;self.liam.action=None;self.liam.sort_y=None
        if self.shared.liam_owner is self:self.shared.liam_owner=None
        self.cooldown_ms=self._rng.randint(*self.config['cooldown_ms']);self._state('cooldown');self._sync_props()

    def begin(self,accident=None,forget=None):
        """Request a normal session; optional decisions are for review and tests."""
        if self.active or self.shared.active or self.shared.liam_owner is not None or self.shared.pending_liam_owner is not None:return False
        self._forced_accident=accident;self._forced_forget=forget;self.cooldown_ms=0;return True

    def surface_prop_visible(self,prop):
        return next(b for b in self.blocks if b['id']==prop['id'])['state'] in ('placed','scattered','forgotten')

    def _sync_props(self):
        for block in self.blocks:
            block['prop']['position']=list(block['center']-block['anchor'])
            block['prop']['sort_y']=209 if block['state']=='placed' else block['center'].y+3
        count=sum(b['state']=='box' for b in self.blocks)
        if self.box['state']!=str(count):self.home.set_entity_state('liam_block_box',str(count))

    def _state(self,name):
        self.state=name;self.state_ms=0;self._contact_done=False
        self.liam.action=None;self.liam.moving=False
        self.events.append({'state':name})

    def _action(self,name,time=None):
        self.liam.action=name;self.liam.action_ms=self.state_ms if time is None else time;self.liam.moving=False

    def _frame(self):
        spec=self.meta['actions'][self.liam.action];time=min(self.liam.action_ms,spec['duration_ms']-1)
        for index,frame in enumerate(spec['frames']):
            if time<frame['duration_ms']:return index,frame
            time-=frame['duration_ms']
        return 3,spec['frames'][-1]

    def _handoff(self,action,operation):
        self._action(action);spec=self.meta['actions'][action]
        if not self._contact_done and self._frame()[0]>=spec['contact_frame']:
            self._contact_done=True;operation();self._sync_props()
        return self.state_ms>=spec['duration_ms']

    def _hold(self,direction):
        self.liam.facing=direction;self._action(f'kneel_{direction}',719)

    def _move(self,goal):return self.shared._move(self.liam,goal,36)

    def _available(self):
        return (not self.shared.active and self.shared.liam_owner is None and
                self.shared.pending_liam_owner is None and self.shared.worlds[self.liam] is self.home)

    def _start(self):
        self.shared.liam_owner=self;self.liam.work_renderer=self
        self.release_requested=False
        self.mode='recover' if self.forgotten_id else 'build';self.index=0
        self.accident_rolled=False;self.accident_selected=False;self.dog_owned=False;self.dog_returning=False
        self.current=next((b for b in self.blocks if b['id']==self.forgotten_id),self.blocks[0])
        self.held=None;self._state('approach_loose' if self.forgotten_id else 'approach_box')

    def _maybe_accident(self):
        if self.accident_rolled or sum(b['state']=='placed' for b in self.blocks)<3:return
        d=self.daisy
        if d.position.distance_to(self.config['building_center'])>self.config['nearby_radius']:return
        bone=getattr(d,'bone_routine',None)
        if bone is not None and bone.active:
            bone.request_release();return
        if d.rest_protected:return
        if (self.shared.worlds[d] is not self.home or d.play_owned or d.active_bowl is not None
                or d.state not in ('rest','pause','walk') or d.activity in ('food','water')):return
        if d.position.distance_to(self.config['building_center'])>self.config['nearby_radius']:return
        self.accident_rolled=True
        self.accident_selected=(self._rng.random()<self.config['accident_probability'] if self._forced_accident is None else self._forced_accident)
        self.events.append({'accident_roll':self.accident_selected})
    def _claim_dog(self):
        # An early probability decision must not freeze Daisy on a future
        # placement point. Borrow her only once all five blocks are finished.
        d=self.daisy
        bone=getattr(d,'bone_routine',None)
        if bone is not None and bone.active:
            bone.request_release();return False
        if d.rest_protected:return False
        if (d.play_owned or d.active_bowl is not None or self.shared.worlds[d] is not self.home
                or d.state not in ('rest','pause','walk') or d.activity in ('food','water')):return False
        self.was_lying=d.state=='rest'
        self.dog_owned=True;d.play_owned=True;d.play_pose=None if self.was_lying else self.shared.dog_pose
        self.shared.dog_pose.action=None;self.shared.dog_pose.moving=False;self.shared.dog_pose.facing='left'
        self.dog_stand_ms=0;return True

    def _cleanup(self):
        self.forget_selected=(self._rng.random()<self.config['forget_probability'] if self._forced_forget is None else self._forced_forget)
        self._forced_accident=None;self._forced_forget=None
        self.forgotten_id=self.blocks[1]['id'] if self.forget_selected else None
        if self.forgotten_id:
            self.blocks[1]['state']='forgotten';self.events.append({'forgotten':self.forgotten_id})
        self.queue=[b for b in reversed(self.blocks) if b['state'] in ('placed','scattered')]
        self.mode='cleanup';self._next_loose()

    def _next_loose(self):
        if self.queue:
            self.current=self.queue.pop(0);self._state('approach_loose')
        else:self.current=None;self._state('leave_play_area')

    def _take(self):
        self.current['state']='held';self.held=self.current;self.events.append({'take':self.current['id']})

    def _place(self):
        self.current['state']='placed';self.current['center'].update(self.config['block_centers'][self.index])
        self.held=None;self.events.append({'place':self.current['id']})

    def _collect(self):
        self.current['state']='held';self.held=self.current;self.events.append({'collect':self.current['id']})

    def _return(self):
        self.current['state']='box';self.held=None;self.events.append({'return':self.current['id']})
        if self.current['id']==self.forgotten_id:self.forgotten_id=None

    def update(self,seconds):
        self._accumulator+=seconds;count=int((self._accumulator+1e-9)*60);self._accumulator-=count/60
        for _ in range(count):self._tick(1000/60)
        self._sync_props()

    def _tick(self,ms):
        self.state_ms+=ms
        if self.state=='cooldown':
            self.cooldown_ms-=ms
            if self.cooldown_ms<=0 and self._available():self._start()
            return
        if self.release_requested and self.mode!='cleanup' and self.state not in ('take','place','bump','collect','return_block'):
            self._begin_release()
        if not self.release_requested and self.state in ('take','carry_to_build','kneel_build','place','admire'):self._maybe_accident()
        d=self.daisy;l=self.liam
        if self.dog_owned:
            if self.dog_returning:
                d._tick(ms,self.home,self.shared.player(self.home))
                if d.state=='rest':
                    d.duration_ms=self._rng.randint(*self.config['dog_rest_ms']);d.play_owned=False;d.play_pose=None
                    d.rest_protected=True
                    self.dog_owned=False;self.dog_returning=False
            else:
                for key in d.cooldowns:d.cooldowns[key]-=ms
                self.shared.dog_pose.moving=False
        if self.state=='yield_rise':
            self._action('rise_left' if self.liam.facing=='left' else 'rise_right')
            if self.state_ms>=720:
                if self.held is not None:self._state('carry_to_box')
                else:self._next_loose()
        elif self.state=='approach_box':
            if self._move(self.pack['box_access']):self._state('kneel_box')
        elif self.state=='kneel_box':
            self._action('kneel_left')
            if self.state_ms>=720:self._state('take')
        elif self.state=='take':
            if self._handoff('take_left',self._take):self._state('rise_with_block')
        elif self.state=='rise_with_block':
            self._action('rise_left')
            if self.state_ms>=720:self._state('carry_to_build')
        elif self.state=='carry_to_build':
            center=pygame.Vector2(self.config['block_centers'][self.index]);goal=center-pygame.Vector2(10,-9)
            if self._move(goal):self._state('kneel_build')
        elif self.state=='kneel_build':
            self._action('kneel_right')
            if self.state_ms>=720:self._state('place')
        elif self.state=='place':
            if self._handoff('place_right',self._place):
                self.index+=1
                if self.index==5:self.admire_ms=self._rng.randint(*self.config['admire_ms']);self._state('admire')
                else:self.current=self.blocks[self.index];self._state('rise_for_box')
        elif self.state=='rise_for_box':
            self._action('rise_right')
            if self.state_ms>=720:self._state('approach_box')
        elif self.state=='admire':
            self._hold('right')
            if self.accident_selected:
                if self._claim_dog():self._state('daisy_approach')
            elif self.state_ms>=self.admire_ms:self._cleanup()
        elif self.state=='daisy_approach':
            self._hold('right')
            d.play_pose=self.shared.dog_pose
            if self.was_lying and self.dog_stand_ms<720:
                self.dog_stand_ms+=ms;self.shared._action(d,'stand_up',self.dog_stand_ms)
            elif self.shared._move(d,self.config['dog_contact_station'],30):self._state('bump')
        elif self.state=='bump':
            self._hold('right');self.shared._action(d,'curious_nudge_left',self.state_ms)
            spec=self.meta['actions']['curious_nudge_left'];contact=sum(f['duration_ms'] for f in spec['frames'][:spec['contact_frame']])
            if self.state_ms>=contact:
                if not self._contact_done:
                    self._contact_done=True
                    for b in self.blocks:b['state']='scattered'
                    self.events.append({'knockdown':True});self.fall_start=self.state_ms
                phase=min(3,int((self.state_ms-self.fall_start)//120))
                self.fall_phase=phase
                for b,start,end in zip(self.blocks,self.config['block_centers'],self.config['scatter_centers']):
                    t=(phase+1)/4;b['center'].update(pygame.Vector2(start).lerp(end,t))
            if self.state_ms>=spec['duration_ms']+480:
                for b,end in zip(self.blocks,self.config['scatter_centers']):b['center'].update(end)
                self._state('react')
        elif self.state=='react':
            self._action('react');self.shared.dog_pose.action=None;self.shared.dog_pose.facing='left'
            if self.state_ms>=self.meta['actions']['react']['duration_ms']:
                d.play_pose=None;d.state='play';d.activity=None;d._return_home();self.dog_returning=True
                self._cleanup()
        elif self.state=='approach_loose':
            goal=self.current['center']-pygame.Vector2(10,-9)
            if self._move(goal):self._state('kneel_loose')
        elif self.state=='kneel_loose':
            self._action('kneel_right')
            if self.state_ms>=720:self._state('collect')
        elif self.state=='collect':
            if self._handoff('collect_right',self._collect):self._state('rise_loose')
        elif self.state=='rise_loose':
            self._action('rise_right')
            if self.state_ms>=720:self._state('carry_to_box')
        elif self.state=='carry_to_box':
            if self._move(self.pack['box_access']):self._state('kneel_return')
        elif self.state=='kneel_return':
            self._action('kneel_left')
            if self.state_ms>=720:self._state('return_block')
        elif self.state=='return_block':
            if self._handoff('return_left',self._return):self._state('rise_return')
        elif self.state=='rise_return':
            self._action('rise_left')
            if self.state_ms>=720:
                if self.mode=='recover':self.mode='build';self.index=0;self.current=self.blocks[0];self._state('approach_box')
                else:self._next_loose()
        elif self.state=='leave_play_area':
            if self._move(self.config['idle_position']) and not self.dog_owned:
                self.completed_cycles+=1;self.shared.liam_owner=None;l.work_renderer=None;l.action=None;l.facing='front'
                self.release_requested=False
                self.cooldown_ms=self._rng.randint(*self.config['cooldown_ms']);self._state('cooldown')

    def draw_held(self,target,camera):
        if self.held is None:return
        if self.liam.action in self.meta['actions']:
            _,frame=self._frame();hand=pygame.Vector2(frame['hand_local'])
        else:
            # A small, fixed carry at chest height, changing sides with facing.
            hand=pygame.Vector2(60 if self.liam.facing=='left' else 68,59)
        center=self.liam.position-pygame.Vector2(self.liam.draw_anchor)+hand
        target.blit(self.held['surface'],center-self.held['anchor']-pygame.Vector2(camera))
        if self.state in ('take','return_block'):
            target.blit(self.lip,pygame.Vector2(self.pack['box_position'])-pygame.Vector2(camera))

    def draw(self,target,camera,world):
        if self.state!='react' or world is not self.home:return
        # Ambient speech never locks the player or opens click-to-advance dialogue.
        lines=['Daisy! You knocked it down.','Go lie down.']
        draw_ambient_speech(self.game,target,camera,self.liam,lines)
