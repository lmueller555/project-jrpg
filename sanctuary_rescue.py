"""Saved rescue performance around Vespermaw, using the production cave renderer.

Only acknowledged rescue milestones persist. Interrupted movement and physical
work replay from that milestone's coherent starting arrangement, never from an
uncommitted tool/rock transfer. Combat rewards remain owned by SanctuaryBoss.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pygame
import speech_bubble
from mill_gift import MillGift, smooth
from npc_routines import find_path
from sanctuary_arrival import CastActor
from social import facing_toward
from ui_style import IVORY, MUTED, GOLD

ROOT=Path(__file__).resolve().parent
ASSETS=ROOT/'assets/story/sanctuary_rescue'
CAVE='sanctuary_cave'
RESERVE='elden_vale_sanctuary'
STAGES=('undiscovered','discovered','confrontation','freed','treated','greenwell','handoff','evacuated')


class SanctuaryRescue(MillGift):
    def __init__(self,game):
        self.game=game
        self.manifest=json.loads((ASSETS/'scene.json').read_text())
        self._click_channel=None;self._click_sound=None
        self._published=[];self._published_props=[];self.actors={};self._world=None
        self.art=None
        self.reset()

    def reset(self):
        self._unpublish()
        super().reset()
        self.stage='undiscovered';self.error='';self.mode=None
        self._world=None;self.actors={};self._routes={};self._ready=False
        self._camera_center=None;self._camera_origin=None;self._camera_zoom=1.
        self._camera_origin_zoom=1.;self._camera_elapsed=0.
        self._action_elapsed=0.;self._cue_done=False;self._sound_done=False
        self._reduced_cut_elapsed=999.
        self._escort_route=[];self._escort_midpoint=None
        self._worker_free=False;self._treated=False;self._departure_choice=False
        self._retry=None;self._on_complete=None

    @property
    def phase(self):return self.manifest['beats'][self.phase_index]
    @property
    def shot(self):return self.phase['id']
    @property
    def locks_player(self):return self.active
    @property
    def waiting(self):return self.stage=='greenwell' and self.game.world.data.get('id')==CAVE
    @property
    def dialogue(self):
        if not self.active or not self._ready or self.error:return None
        return super().dialogue

    def to_dict(self):return {'version':1,'stage':self.stage}

    @staticmethod
    def valid_snapshot(record):
        return (isinstance(record,dict) and set(record)=={'version','stage'}
                and type(record['version']) is int and record['version']==1
                and isinstance(record['stage'],str) and record['stage'] in STAGES)

    @staticmethod
    def valid_journey(data):
        if not isinstance(data,dict):return False
        record=data.get('sanctuary_rescue')
        if record is None:return 'sanctuary_rescue' not in data
        if not SanctuaryRescue.valid_snapshot(record):return False
        stage=record['stage'];boss=data.get('sanctuary_boss') or {}
        cave=data.get('sanctuary_cave') or {};player=data.get('player') or {}
        if not all(isinstance(item,dict) for item in (boss,cave,player)):return False
        if stage in ('freed','treated','greenwell','handoff','evacuated') and not boss.get('defeated'):return False
        if stage in ('freed','treated','greenwell','handoff') and (boss.get('pending') is not None or data.get('post_battle') is not None):return False
        if stage in ('discovered','freed','treated','greenwell') and player.get('scene')!=CAVE:return False
        if (stage=='confrontation' and player.get('scene')!=CAVE
                and (boss.get('defeated') or boss.get('pending') is not None or data.get('post_battle') is not None)):return False
        if stage=='discovered' and (boss.get('defeated') or boss.get('pending') is not None):return False
        if stage=='handoff' and player.get('scene')!=RESERVE:return False
        if stage=='evacuated' and not cave.get('lucan_departed'):return False
        if stage!='evacuated' and cave.get('lucan_departed'):return False
        return True

    def restore(self,record=None,*,journey=None):
        if record is not None and not self.valid_snapshot(record):return False
        self.reset()
        if record is not None:self.stage=record['stage']
        elif journey:
            if (journey.get('sanctuary_cave') or {}).get('lucan_departed'):self.stage='evacuated'
            elif ((journey.get('sanctuary_arrival') or {}).get('completed')
                  and ((journey.get('sanctuary_boss') or {}).get('defeated')
                   or (journey.get('sanctuary_boss') or {}).get('pending') is not None)
                  and (journey.get('player') or {}).get('scene')==CAVE):self.stage='confrontation'
        self._worker_free=self.stage in ('freed','treated','greenwell','handoff','evacuated')
        self._treated=self.stage in ('treated','greenwell','handoff','evacuated')
        return True

    def _available(self):
        g=self.game
        return (not g.on_title and not g.combat.active
                and not g.social.locked and not g.social.active
                and not g.opening_cinematic.active and not g.opening.locks_player
                and not g.household_action and not g.transfer_cooldown and not g.opening_fade
                and not getattr(g,'game_over',False)
                and not getattr(getattr(g,'save_menu',None),'is_open',False)
                and not g.map_open and not g.quest_ui.journal_open
                and getattr(g,'_music_focused',True)
                and not any(getattr(getattr(g,name,None),'is_open',False)
                            for name in ('pause','party_ui','inventory_ui','status_ui','world_map_viewer')))

    def _checkpoint(self):
        g=self.game
        return not g.save_store.enabled or g.save_progress()

    def _set_stage(self,stage):
        old=self.stage;position=tuple(self.game.player.position);facing=self.game.player.facing
        self.stage=stage
        if self.actors and 'caelan' in self.actors:
            self.game.player.position.update(self.actors['caelan'].position)
            self.game.player.facing=self.actors['caelan'].facing
        if self._checkpoint():return True
        self.stage=old;self.game.player.position.update(position);self.game.player.facing=facing
        return False

    def _load_art(self):
        if self.art is None:self.art=json.loads((ASSETS/'art.json').read_text())

    def _make_cast(self):
        self._load_art();g=self.game;world=g.world;self._world=world
        self._unpublish()
        sources={'caelan':g.player,'mira':g.mill_quest.mira,'lucan':g.regent_quest.lucan}
        self.actors={key:CastActor(key,world,sources.get(key),variant='male_02',art=self.art.get('actors',{}).get(key))
                     for key in ('caelan','mira','lucan','worker')}
        if world.data['id']==RESERVE:
            self.actors['caretaker']=CastActor('caretaker',world,variant='male_03',art=self.art.get('actors',{}).get('caretaker'))
        # Existing arrival portraits retain character identity; the rescued man
        # is a distinct scene actor, never the earlier injured worker instance.
        profiles=g.social.data['speakers'];portrait='male_02'
        portrait_path=ROOT/'assets/portraits/eldenmere/portraits.json'
        portraits=json.loads(portrait_path.read_text())['portraits']
        for key,name,portrait in (('rescue_worker','Trapped worker','male_02'),
                                  ('rescue_caretaker','Caretaker','male_03')):
            profiles[key]={'name':('Injured worker' if key=='rescue_worker' and self._worker_free else name),'portrait':portrait}
            if portrait not in g.social.portraits:
                g.social.portraits[portrait]=world.image('assets/portraits/eldenmere/'+portraits[portrait]['file'])

    def _station(self,actor,point):
        if not self._world.can_stand(point,actor.probe_size):
            raise ValueError('Blocked rescue station: '+str(point))
        actor.position.update(point);actor.route=[];actor.moving=False

    def _initial_positions(self,index):
        positions={}
        if index<6:
            positions.update(self.manifest['beats'][0]['goals'])
            if index>0:
                for beat in self.manifest['beats'][1:index]:positions.update(beat['goals'])
        elif index<15:
            for beat in self.manifest['beats'][:index]:positions.update(beat['goals'])
            if index==6:positions.update(self.manifest['beats'][6]['goals'])
        elif index>=18:positions.update(self.manifest['beats'][13]['goals'])
        else:positions.update(self.manifest['beats'][15]['goals'])
        for key,actor in self.actors.items():
            self._station(actor,positions.get(key,self.manifest['worker_position']))
            actor.facing='left' if key=='worker' else 'right'
        self.actors['worker'].pose='seated' if self._worker_free else 'pinned'

    def _start(self,index,mode,on_complete=None):
        if self.active:return False
        self._make_cast();self._initial_positions(index)
        self.active=True;self.paused=False;self.focused=True;self.error='';self.mode=mode
        self.elapsed=0.;self.phase_index=index;self._on_complete=on_complete
        self.sections=[beat['lines'] for beat in self.manifest['beats']]
        current=self.game.camera.position()
        self._camera_center=pygame.Vector2(current[0]+240,current[1]+112)
        self._camera_zoom=1.;self._begin_phase()
        self.game.player.moving=self.game.player.running=False
        return True

    def start_before(self,on_complete=None):
        if self.game.world.data.get('id')!=CAVE or not self._available():return False
        boss=self.game.sanctuary_boss
        if boss.defeated or boss.pending is not None:return False
        callback=on_complete or boss._begin_battle
        if not getattr(self.game.sanctuary_arrival,'completed',False):return bool(callback())
        if self.stage=='confrontation':return bool(callback())
        if self.stage not in ('undiscovered','discovered'):return False
        old=self.stage;self.stage='discovered'
        if not self._checkpoint():self.stage=old;return False
        return self._start(0,'before',callback)

    def maybe_start(self):
        if self.active:return False
        if self.game.on_title:return False
        self.sync_waiting()
        if not self._available():return False
        g=self.game;boss=g.sanctuary_boss
        if not getattr(g.sanctuary_arrival,'completed',False):return False
        if boss.pending is not None or g.combat.snapshot() is not None:return False
        if self.stage=='handoff' and g.world.data.get('id')==RESERVE:return self._start(15,'handoff')
        if g.world.data.get('id')!=CAVE:return False
        if self.stage=='discovered':return self.start_before()
        if boss.defeated and self.stage in ('undiscovered','discovered','confrontation','freed','treated'):
            index={'freed':9,'treated':10}.get(self.stage,6)
            self._worker_free=index>=9;self._treated=index>=10
            return self._start(index,'after')
        return False

    def _support_banks(self,enabled=True):
        actor=self.actors.get('lucan')
        spec=self.art.get('actors',{}).get('lucan',{})
        if actor is None or not enabled or 'supported_walks' not in spec:return
        actor.idles={d:self._world.image(path) for d,path in spec['supported_idles'].items()}
        actor.walks={d:[self._world.image(frame['file']) for frame in frames] for d,frames in spec['supported_walks'].items()}
        actor.walk_durations={d:tuple(frame['duration_ms'] for frame in frames) for d,frames in spec['supported_walks'].items()}
        actor.draw_anchor=tuple(spec.get('supported_anchor',(20,34)))

    def _route(self,actor,point):
        if actor.position.distance_to(point)<.01:return []
        return self._checked_path(actor.position,point,actor.probe_size)

    def _checked_path(self,start,point,probe):
        start=pygame.Vector2(start);end=pygame.Vector2(point)
        steps=max(1,math.ceil(start.distance_to(end)))
        if all(self._world.can_stand(start.lerp(end,i/steps),probe) for i in range(steps+1)):
            return [tuple(end)]
        route=find_path(self._world,start,end,probe,None)
        if route is None:raise ValueError('Blocked rescue route '+str((tuple(start),point)))
        return list(route)

    def _begin_phase(self):
        self.phase_time=0.;self.dialogue_index=0;self.page_index=0
        self.caption_layout=None;self.caption_pages=[];self.caption_lines=[]
        self._ready=False;self._routes={};self._action_elapsed=0.;self._cue_done=False;self._sound_done=False
        self._camera_origin=pygame.Vector2(self._camera_center)
        if self.reduced_motion:self._camera_zoom=self.phase.get('zoom',1.)
        self._camera_origin_zoom=self._camera_zoom;self._camera_elapsed=0.
        self._escort_route=[];self._escort_midpoint=None;self._reduced_cut_elapsed=999.
        for key,actor in self.actors.items():
            actor.pose=self.phase.get('poses',{}).get(key)
            actor.pose_ms=0;actor.moving=False
        worker=self.actors['worker']
        if 'worker' not in self.phase.get('poses',{}):worker.pose='seated' if self._worker_free else 'pinned'
        self._support_banks(self.phase_index>=6)
        if self.phase.get('action')=='escort':
            self._escort_midpoint=(worker.position+self.actors['lucan'].position)/2
            target=pygame.Vector2(self.phase['goals']['worker'])-pygame.Vector2(12,0)
            self._escort_route=self._checked_path(self._escort_midpoint,target,(48,12))
            if self._escort_route is None:raise ValueError('No supported rescue evacuation route')
            self._escort_route=list(self._escort_route)
        for key,point in self.phase.get('goals',{}).items():
            if key in self.actors and not (self.phase.get('action')=='escort' and key in ('worker','lucan')):
                self._routes[key]=self._route(self.actors[key],point)
        self.actors['worker'].facing='left'
        for key in ('caelan','mira','lucan'):
            self.actors[key].facing='right' if self.phase_index not in (4,5) else 'left'

    def _move(self,actor,route,seconds,speed=58.):
        actor.moving=False;budget=seconds*speed
        while route and budget>1e-9:
            delta=pygame.Vector2(route[0])-actor.position;distance=delta.length()
            if distance<1e-8:actor.position.update(route.pop(0));continue
            travel=min(distance,budget,1.)
            candidate=actor.position+delta*(travel/distance)
            if not self._world.can_stand(candidate,actor.probe_size):raise ValueError('Rescue crossed blocked terrain')
            actor.position.update(candidate);actor.facing=facing_toward(delta);actor.moving=True
            actor.walk_ms+=travel/speed*1000;budget-=travel
        return bool(route)

    def _move_escort(self,seconds):
        if not self._escort_route:return
        worker=self.actors['worker'];lucan=self.actors['lucan']
        budget=seconds*38.;moved=0.;direction=None
        while self._escort_route and budget>1e-9:
            delta=pygame.Vector2(self._escort_route[0])-self._escort_midpoint;distance=delta.length()
            if distance<1e-8:self._escort_midpoint.update(self._escort_route.pop(0));continue
            travel=min(distance,budget,1.);candidate=self._escort_midpoint+delta*(travel/distance)
            if not self._world.can_stand(candidate,(48,12)):raise ValueError('Supported evacuation crossed terrain')
            self._escort_midpoint.update(candidate);budget-=travel;moved+=travel;direction=facing_toward(delta)
        worker.position.update(self._escort_midpoint+pygame.Vector2(12,0))
        lucan.position.update(self._escort_midpoint-pygame.Vector2(12,0))
        for actor in (worker,lucan):
            actor.pose=None;actor.moving=bool(moved)
            if direction:actor.facing=direction
            actor.walk_ms+=moved/38.*1000

    def update(self,seconds):
        self._sync_audio()
        if not self.active or self.paused or not self.focused or not getattr(self.game,'_music_focused',True):return
        seconds=max(0.,float(seconds));self.elapsed+=seconds;self.phase_time+=seconds
        self._input_armed=self.elapsed>=.1
        if self.error:return
        for actor in self.actors.values():actor.moving=False
        for key,route in self._routes.items():self._move(self.actors[key],route,seconds)
        if self.phase.get('action')=='escort':self._move_escort(seconds)
        moving=any(self._routes.values()) or bool(self._escort_route)
        if not moving:
            self._action_elapsed+=seconds
            for actor in self.actors.values():actor.advance_pose(seconds)
            cue=self.phase.get('cue_seconds',0.)
            if self._action_elapsed>=cue and not self._cue_done:
                self._cue_done=True
                if self.phase.get('action')=='free':
                    self._worker_free=True;self.actors['worker'].pose='seated';self.actors['worker'].pose_ms=0
                    self.game.social.data['speakers']['rescue_worker']['name']='Injured worker'
                if self.phase.get('action')=='treat':self._treated=True
        self._camera_elapsed+=seconds;self._reduced_cut_elapsed+=seconds
        duration=self.phase.get('pan_seconds',1.)
        blend=1. if self.reduced_motion or duration==0 else smooth(self._camera_elapsed/duration)
        target=pygame.Vector2(self.phase['camera'])
        if self.phase.get('action')=='escort':
            points=[actor.position for actor in self.actors.values()]
            target=pygame.Vector2(sum(p.x for p in points)/len(points),sum(p.y for p in points)/len(points))
            if self.reduced_motion:
                # Stable compositions with brief masked cuts replace tracking.
                if self._camera_center.distance_to(target)>100.:
                    self._camera_center=pygame.Vector2(target);self._reduced_cut_elapsed=0.
                blend=0.
            else:blend=1.-math.exp(-4.*seconds)
            self._camera_origin=pygame.Vector2(self._camera_center)
            self._camera_origin_zoom=self._camera_zoom
        self._camera_center=self._camera_origin.lerp(target,blend)
        self._camera_zoom=self._camera_origin_zoom+(self.phase.get('zoom',1.)-self._camera_origin_zoom)*blend
        if not self._sound_done and self.phase_time>=.25:
            self._sound_done=True;self._play_phase_sound()
        self._ready=(not moving and self._action_elapsed>=self.phase['min_seconds']
                     and (self.reduced_motion or self._camera_elapsed>=duration))
        self._next_if_ready()

    def _next_if_ready(self):
        if not self.active or self.error or not self._ready or self.dialogue_index<len(self.sections[self.phase_index]):return
        self._finish_phase()

    def _finish_phase(self):
        phase=self.phase;index=self.phase_index
        target=phase['stage']
        if index==5:
            old=self.game.sanctuary_boss.intro_seen
            self.game.sanctuary_boss.intro_seen=True
            if not self._set_stage('confrontation'):
                self.game.sanctuary_boss.intro_seen=old;return self._save_error(self._finish_phase)
            callback=self._on_complete;self._on_complete=None
            self._finish_view();self.sync_waiting()
            if callback is not None and not callback():
                self.active=True;self.mode='before';self._on_complete=callback
                self._save_error(self._finish_phase)
            return
        if index in (8,9,14):
            if not self._set_stage(target):return self._save_error(self._finish_phase)
        if index==14:
            self._finish_view();self.sync_waiting();return
        if index==19:
            self.active=False;self.stop_audio()
            return self._transfer_departure()
        if index==17:
            if not self.game.complete_cave_rescue_departure():return self._save_error(self._finish_phase)
            self._finish_view();self.sync_waiting();return
        self.phase_index+=1;self._begin_phase()

    def _save_error(self,retry):
        self.error='Progress could not be saved. Press Enter or click to retry.'
        self._retry=retry
        return False

    def advance(self):
        if self.error:
            if self.paused or not self.focused or self._batch_advanced:return False
            self._batch_advanced=True;self.error='';retry=self._retry;self._retry=None
            if retry:retry()
            return True
        return super().advance()

    def _finish_view(self):
        self.active=False;self.mode=None;self.finished_reason='finished';self.stop_audio()
        if self.actors and self._world is self.game.world:
            self.game.player.position.update(self.actors['caelan'].position)
            self.game.player.facing=self.actors['caelan'].facing
        self.game.player.moving=self.game.player.running=False
        self.game.party_travel.reset();self.game.camera.reset()
        self.game.social.clear_pointer();self.game._mouse_held=False

    def _unpublish(self):
        for world,actor in getattr(self,'_published',[]):
            if actor in world.npcs:world.npcs.remove(actor)
        self._published=[]
        for world,record in getattr(self,'_published_props',[]):
            if record in world.entities:world.entities.remove(record)
        self._published_props=[]

    def sync_waiting(self):
        if self.active or self.game.on_title:return
        g=self.game
        scene=g.world.data.get('id')
        waiting_cave=(scene==CAVE and self.stage in ('discovered','confrontation','greenwell','evacuated'))
        wanted=(waiting_cave or self.stage=='evacuated' and scene==RESERVE)
        if not wanted:self._unpublish();return
        if self._world is not g.world or not self.actors:
            self._make_cast()
        if self.stage=='greenwell':
            stations={'worker':(1996,828),'lucan':(1972,828)}
        elif scene==RESERVE:stations={'worker':(968,414)}
        elif self.stage=='evacuated':stations={}
        else:stations={'worker':(2130,405)}
        self._unpublish();self._support_banks()
        for key,position in stations.items():
            actor=self.actors[key];self._station(actor,position)
            actor.pose=('seated' if self._worker_free else 'pinned') if key=='worker' else None;actor.facing='left' if key=='worker' else 'right'
            actor.pose_ms=10000
            if actor not in g.world.npcs:g.world.npcs.append(actor)
            self._published.append((g.world,actor))
        for record in self._sync_props():
            g.world.entities.append(record);self._published_props.append((g.world,record))

    def interaction_hint(self):
        if not self.waiting or not self._available():return ''
        return 'E: speak to Lucan about the evacuation' if self.game.player.position.distance_to((1972,828))<=42 else ''

    def interact(self):
        if not self.interaction_hint():return False
        self.game.player.moving=self.game.player.running=False
        return self.game.social.start_choice(
            [{'speaker':'lucan','text':'He’s ready to move. Shall we take him back?'}],
            [{'text':'Return to the Sanctuary','action':'return'}, {'text':'Prepare first','action':'prepare'}],
            self._choose_departure,identifier='sanctuary_rescue_departure',prompt='Escort the worker outside?')

    def _choose_departure(self,action):
        if action!='return' or not self.waiting:return
        return self._start(18,'departure')

    def _transfer_departure(self):
        g=self.game;destination=g._scene_by_id(RESERVE)
        landing=g.overworld_travel._landing(destination,(1000,438))
        if landing is None:return
        origin=g.world;position=tuple(g.player.position);facing=g.player.facing
        self._unpublish();self.stage='handoff'
        g.overworld_travel._commit(destination,landing,'left',{'id':'rescue_evacuation'},checkpoint=False)
        if not self._checkpoint():
            self.stage='greenwell';g.world=origin;g.player.position.update(position);g.player.facing=facing
            g.transfer_cooldown=0.;g.camera.reset();g.party_travel.reset()
            g.sanctuary_arrival.sync_residents();g._sync_world_music();self.sync_waiting()
            g.social.start_script([{'speaker':'lucan','text':'We could not record our progress. Speak to me to try again.'}],identifier='rescue_transfer_error')
            return
        self._start(15,'handoff')

    def _play_phase_sound(self):
        purpose=self.phase.get('sound')
        if purpose not in ('growl','cough','stone','cloth'):return
        try:
            from array import array
            import random
            from sanctuary_boss_entry import growl_samples
            mixer=pygame.mixer.get_init()
            if mixer is None or mixer[1]!=-16:return
            rate,_,channels=mixer
            if purpose=='growl':samples=growl_samples(rate,channels)
            else:
                # Original short foley: filtered grains for shifting stone,
                # soft cloth friction, and two breath-like worker coughs.
                duration={'stone':1.5,'cloth':.9,'cough':.75}[purpose]
                rng=random.Random(716+sum(map(ord,purpose)));samples=array('h');low=0.
                for index in range(round(rate*duration)):
                    t=index/rate;noise=rng.uniform(-1.,1.);low+=.08*(noise-low)
                    envelope=math.sin(math.pi*t/duration)**2
                    if purpose=='stone':value=(low*.8+noise*.08)*envelope
                    elif purpose=='cloth':value=noise*.13*envelope
                    else:
                        breath=max(0.,math.sin(2*math.pi*t/duration))**2
                        breath+=.7*max(0.,math.sin(2*math.pi*(t-.28)/duration))**6
                        value=(low*.7+noise*.05)*breath*envelope
                    samples.extend([round(max(-1.,min(1.,value))*32767)]*channels)
            self._click_sound=pygame.mixer.Sound(buffer=samples)
            self._click_channel=self._click_sound.play();self._sync_audio()
        except pygame.error:pass

    def _prop(self,name):
        record=self.art.get('props',{}).get(name)
        if not record:return None
        if isinstance(record,str):return self._world.image(record),(0,0)
        return self._world.image(record['file']),tuple(record.get('anchor',(0,0)))

    def _sync_props(self):
        # Props join the same world depth ordering and lighting as the actors.
        props=[]
        if self._world.data['id']==CAVE:
            item=self._prop('rock')
            if item:
                lifted=self._worker_free
                point=(2107,397) if lifted else (2123,406)
                if self.active and self.phase.get('action')=='free':
                    progress=min(1.,self._action_elapsed/max(.01,self.phase['cue_seconds']))
                    if progress<.55:
                        q=smooth(progress/.55);point=(2123-8*q,406-12*q)
                    else:
                        q=smooth((progress-.55)/.45);point=(2115-8*q,394+3*q)
                props.append(('rock',item,point,point[1]+2))
            if self.active and self.phase.get('action')=='free' and self._action_elapsed<4.1:
                item=self._prop('tool')
                if item:props.append(('tool',item,(2118,398),409))
        if self._treated and (self.stage!='evacuated' or self._world.data['id']==RESERVE):
            item=self._prop('dressing')
            if item:props.append(('dressing',item,tuple(self.actors['worker'].position+pygame.Vector2(-2,-7)),self.actors['worker'].position.y+1))
        records=[]
        for name,(image,anchor),point,sort_y in props:
            position=(round(point[0]-anchor[0]),round(point[1]-anchor[1]))
            records.append(dict(id='rescue_'+name,position=position,rect=image.get_rect(topleft=position),surfaces=[image],sort_y=sort_y,phase_offset=0,frame_duration_ms=1000))
        return records

    def draw(self,canvas,ui_surface):
        if not self.active:return
        g=self.game;world=self._world;size=canvas.get_size()
        zoom=max(1.,self._camera_zoom);width=round(size[0]/zoom);height=round(size[1]/zoom)
        center=self._camera_center
        origin=(round(center.x-width/2),round(center.y-height*.35))
        origin=(max(0,min(world.size[0]-width,origin[0])),max(0,min(world.size[1]-height,origin[1])))
        old=getattr(g.player,'story_visible',True);g.player.story_visible=False
        hidden=[]
        for actor in world.npcs:
            if actor in self.actors.values():continue
            identifier=getattr(actor,'key',None)
            if identifier=='caretaker':
                hidden.append((actor,getattr(actor,'story_visible',True)));actor.story_visible=False
        records=self._sync_props()
        if self.phase.get('reveal'):
            image=world.image('assets/combat/vespermaw/idle_01.png').copy()
            image.set_alpha(round(smooth((self.phase_time-.5)/1.5)*255))
            position=(1950-64,420-128)
            records.append(dict(id='rescue_boss_reveal',position=position,rect=image.get_rect(topleft=position),surfaces=[image],sort_y=420,phase_offset=0,frame_duration_ms=1000))
        world.entities.extend(records)
        try:
            world.reduced_motion=self.reduced_motion
            frame=pygame.Surface(size)
            world.draw(frame,origin,g.player,self.elapsed*1000,include_ui=False,party_actors=tuple(self.actors.values()))
            pygame.transform.scale(frame.subsurface((0,0,width,height)),size,canvas)
        finally:
            g.player.story_visible=old
            for actor,visible in hidden:actor.story_visible=visible
            for record in records:
                if record in world.entities:world.entities.remove(record)
        fade=0.
        if self.reduced_motion and self.phase_time<.3:fade=1.-self.phase_time/.3
        if self.reduced_motion and self._reduced_cut_elapsed<.25:
            fade=max(fade,1.-self._reduced_cut_elapsed/.25)
        if self.phase_index==15 and self.phase_time<.6:fade=max(fade,1.-self.phase_time/.6)
        if self.phase_index==19 and not self._escort_route:
            fade=max(fade,smooth(self._action_elapsed/self.phase['min_seconds']))
        if fade:
            veil=pygame.Surface(size,pygame.SRCALPHA);veil.fill((0,0,0,round(255*fade)));canvas.blit(veil,(0,0))
        pygame.transform.scale(canvas,ui_surface.get_size(),ui_surface)
        painter=g.ui.painter(ui_surface);self._layout(painter)
        if self.caption_layout is not None:
            speech_bubble.draw_dialogue_frame(painter,self.caption_layout,g.social.portraits[self.caption_layout.portrait_key])
            speech_bubble.draw_dialogue_prose(painter,self.caption_layout,self.caption_lines,hint='Click to continue',show_indicator=True)
        painter.text('Esc · Resume' if self.paused else 'Esc · Pause',(12,310),role='small',color=MUTED,anchor='bottomleft')
        if self.error:
            painter.panel((35,100,410,65));painter.text(self.error,(45,120),role='small',color=GOLD)
        if self.paused or not self.focused:
            painter.panel((193,20,94,26));painter.text('Paused',(240,33),color=IVORY,anchor='center')
