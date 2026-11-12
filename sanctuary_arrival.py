"""Player-paced MQ03 rescue staging on the live Sanctuary reserve.

Only acknowledged beats, the rescue handoff and first cave entry persist.
Camera movement, actor paths and partial pages rebuild on Continue.
"""
from pathlib import Path
import json
import pygame
import speech_bubble
from mill_gift import MillGift
from social import facing_toward
from regent_emergency import legacy_cave_entered
from sanctuary_arrival_party import sync_arrival_party
from sanctuary_arrival_blocking import SanctuaryBlocking
from sanctuary_rope import SanctuaryRope
from sanctuary_care import SanctuaryCare
from ui_style import IVORY,MUTED,GOLD
ROOT=Path(__file__).resolve().parent
RESERVE='elden_vale_sanctuary'

class CastActor:
    """A scene display actor with full-foot static-terrain navigation."""
    def __init__(self,key,world,source=None,variant='male_02',art=None):
        self.data={'id':'sanctuary_arrival_'+key};self.key=key
        self.position=pygame.Vector2();self.probe_size=(24,12)
        self.story_visible=True;self.party_travelling=False;self.moving=False
        self.facing='front';self.walk_ms=0.;self._pose=None;self.pose_ms=0.;self.route=[]
        self.pose_animations={};self.walk_durations={}
        self.carrying=False;self.carry_idles={};self.carry_walks={}
        self.draw_anchor=tuple(getattr(source,'draw_anchor', (12,30)))
        if key=='caelan':self.draw_anchor=(12,30)
        if source is not None:
            self.idles=source.idles;self.walks=source.walks
            self.walk_durations=getattr(source,'walk_durations',{})
            self.pose_animations=dict(getattr(source,'pose_animations',{}))
        else:
            self.idles={d:world.image(f'assets/characters/npcs/{variant}/idle_{d}.png') for d in ('front','back','left','right')}
            self.walks={d:[world.image(f'assets/characters/npcs/{variant}/walk_{d}/frame_{i:02}.png') for i in range(1,5)] for d in self.idles}
        if art is not None:
            self.draw_anchor=tuple(art['anchor'])
            self.idles={direction:world.image(path) for direction,path in art['idles'].items()}
            for direction,frames in art['walks'].items():
                self.walks[direction]=[world.image(frame['file']) for frame in frames]
                self.walk_durations[direction]=tuple(frame['duration_ms'] for frame in frames)
            for name,animation in art.get('poses',{}).items():
                self.pose_animations[name]={
                    'frames':tuple(world.image(frame['file']) for frame in animation['frames']),
                    'durations':tuple(frame['duration_ms'] for frame in animation['frames']),
                    'loop':animation.get('loop',False),
                    'anchor':tuple(animation.get('anchor',self._draw_anchor))}
    @property
    def draw_anchor(self):
        animation=getattr(self,'pose_animations',{}).get(getattr(self,'_pose',None),{})
        return tuple(animation.get('anchor',self._draw_anchor)) if not self.moving else self._draw_anchor
    @draw_anchor.setter
    def draw_anchor(self,value):self._draw_anchor=tuple(value)
    @property
    def pose(self):return self._pose
    @pose.setter
    def pose(self,name):
        if name!=self._pose:self.pose_ms=0.
        self._pose=name
    def advance_pose(self,seconds):
        if not self.moving:self.pose_ms+=seconds*1000
    @staticmethod
    def _frame(frames,durations,milliseconds,loop=True):
        total=sum(durations)
        clock=milliseconds%total if loop else min(milliseconds,total)
        for frame,duration in zip(frames,durations):
            if clock<duration:return frame
            clock-=duration
        return frames[-1]
    @property
    def blocker(self):return pygame.Rect(round(self.position.x)-4,round(self.position.y)-2,8,4)
    def end_conversation(self):pass
    def request_conversation(self,facing):self.facing=facing
    def sprite(self,elapsed_ms):
        if not self.moving:
            if self.pose in self.pose_animations:
                animation=self.pose_animations[self.pose]
                return self._frame(animation['frames'],animation['durations'],self.pose_ms,animation['loop'])
            if self.carrying and self.facing in self.carry_idles:return self.carry_idles[self.facing]
            return self.idles[self.facing]
        frames=self.carry_walks[self.facing] if self.carrying and self.facing in self.carry_walks else self.walks[self.facing]
        durations=self.walk_durations.get(self.facing,(140,)*len(frames))
        image=self._frame(frames,durations,self.walk_ms)
        return image[0] if isinstance(image,tuple) else image

class SanctuaryArrival(MillGift):
    """Shared cinematic input/captions, with in-world actors and checkpoint beats."""
    def __init__(self,game):
        self.game=game
        self.manifest=json.loads((ROOT/'assets/story/sanctuary_arrival/scene.json').read_text())
        self.art=json.loads((ROOT/'assets/story/sanctuary_arrival/art.json').read_text())
        self.performance=json.loads((ROOT/'assets/story/sanctuary_arrival/performance/art.json').read_text())
        self.rail=SanctuaryRope(game,self.art['rail'])
        self.care=SanctuaryCare(self,self.performance)
        self._published=[];self.actors={};self._world=None
        self.reset()
    def reset(self):
        self._sync_care_audio(stop=True)
        for world,actor in getattr(self,'_published',[]):
            if actor in world.npcs:world.npcs.remove(actor)
        for world,record in getattr(self,'_care_props',[]):
            if record in world.entities:world.entities.remove(record)
        self._care_props=[];self._line_id=None;self._pending_advance=False
        self.care.reset(0);self._page_remaining=0.;self._page_resuming=False
        self._published=[];self.actors={};self._world=None
        super().reset();self.completed=False;self.cave_entered=False;self.error=''
        self._ready=False;self._checkpoint_failed=False;self.blocking=None
        self._restore_rail()
        self._rail_pending=False;self._rail_elapsed=0.;self._rail_retreat=False
    @property
    def beat(self):return self.phase_index
    @property
    def _kit(self):return self.care.kit_owner!='stowed'
    @property
    def _runner_delivered(self):return self.care.runner_delivered
    @property
    def _delivery_remaining(self):
        if not self.care.runner_started or self.care.runner_delivered:return 0.
        return max(0.,(sum(f['duration_ms'] for f in self.performance['poses']['runner_place']['frames'])-self.care.runner_elapsed_ms)/1000)
    @property
    def _action_remaining(self):return max(self.care.remaining,self._page_remaining)
    @property
    def phase(self):return self.manifest['beats'][self.beat]
    @property
    def shot(self):return self.phase['id']
    @property
    def dialogue(self):
        line=super().dialogue
        if self.error or line is None:return None
        actor={'arrival_caretaker':'caretaker','arrival_worker':'worker_a','regent_clerk':'page'}.get(line['speaker'],line['speaker'])
        ready=self._ready or (self.game.camera.settled and self.blocking is not None and not self.blocking.busy(actor))
        return line if ready else None
    def to_dict(self):return {'version':1,'beat':self.beat,'completed':self.completed,'cave_entered':self.cave_entered}
    @staticmethod
    def valid_snapshot(data):
        return (isinstance(data,dict) and set(data)=={'version','beat','completed','cave_entered'}
                and type(data['version']) is int and data['version']==1
                and type(data['beat']) is int and 0<=data['beat']<=7
                and type(data['completed']) is bool and type(data['cave_entered']) is bool
                and (not data['completed'] or data['beat']==7))
    @staticmethod
    def valid_journey(data):
        if not isinstance(data,dict):return False
        record=data.get('sanctuary_arrival')
        if record is None:return 'sanctuary_arrival' not in data
        if not SanctuaryArrival.valid_snapshot(record):return False
        if record['beat'] or record['completed']:
            quest=data.get('regent_quest',{})
            if not isinstance(quest,dict) or quest.get('stage') not in ('sanctuary_arrival_pending','done'):return False
        if record['beat'] and not record['completed']:
            player=data.get('player')
            if not isinstance(player,dict) or player.get('scene')!=RESERVE:return False
        return True
    def restore(self,data=None,*,journey=None):
        if data is not None and not self.valid_snapshot(data):return False
        self.reset()
        if data is not None:
            self.phase_index=data['beat'];self.completed=data['completed'];self.cave_entered=data['cave_entered']
        elif journey:self.cave_entered=legacy_cave_entered(journey)
        return True
    def on_enter_scene(self,origin,transition):
        if self.game.world.data['id']=='sanctuary_cave':self.note_cave_entry()
        if self.game.world.data['id']==RESERVE:self._set_rail(1. if self.completed else 0.,self.game.world)
        if self.completed:self.sync_residents()
    def note_cave_entry(self):
        if self.cave_entered:return False
        self.cave_entered=True
        return True
    def prepare_preview(self):
        from cutscene_gallery import _regent_checkpoint,_station
        _regent_checkpoint(self.game,'sanctuary_arrival_pending')
        self.reset();self.game._sync_story_party()
        _station(self.game,self.game._scene_by_id(RESERVE),(444,642),'back')
        self.game.music.play('battle',fade_ms=0)
    def maybe_start(self):
        g=self.game
        if (not self.active and not self.completed
            and g.world.data['id']==RESERVE and g.regent_quest.stage=='sanctuary_arrival_pending'
            and not g.on_title and not g.combat.active and not g.social.locked
            and not g.opening_fade and not g.transfer_cooldown
            and not any(getattr(g,key).is_open for key in ('pause','party_ui','inventory_ui','status_ui','world_map_viewer'))):
            return self.start()
        return False
    def _make_cast(self):
        g=self.game;world=g.world;c=g.regent_quest
        self._world=world
        self._linen=world.image('assets/characters/serene/routines/props/folded_linen.png')
        self.actors={key:CastActor(key,world,source) for key,source in
                     (('caelan',g.player),('mira',g.mill_quest.mira),('lucan',c.lucan),('aldric',c.aldric),('page',c.clerk))}
        for key,variant in (('caretaker','male_03'),('worker_a','male_02'),('worker_b','male_01'),('sentry','female_02'),('runner','female_01')):
            self.actors[key]=CastActor(key,world,variant=variant,art=self.art['actors'].get(key))
        performance=self.performance
        for name,animation in performance['poses'].items():
            actor=self.actors['runner'] if name=='runner_place' else self.actors['worker_a'] if name in ('offer_arm','arm_rest') else self.actors['mira']
            actor.pose_animations[name]={
                'frames':tuple(world.image(f['file']) for f in animation['frames']),
                'durations':tuple(f['duration_ms'] for f in animation['frames']),
                'loop':False,'anchor':tuple(animation['anchor'])}
        runner=self.actors['runner']
        runner.carry_idles={direction:world.image(path) for direction,path in performance['carry_idles'].items()}
        runner.carry_walks={direction:[world.image(f['file']) for f in frames] for direction,frames in performance['carry_walks'].items()}
        runner.walk_durations={direction:tuple(f['duration_ms'] for f in frames) for direction,frames in performance['carry_walks'].items()}
        portraits=json.loads((ROOT/'assets/portraits/eldenmere/portraits.json').read_text())['portraits']
        for key,name,actor in (('arrival_caretaker','Caretaker','caretaker'),('arrival_worker','Injured worker','worker_a')):
            portrait=self.art['actors'][actor]['portrait']
            g.social.data['speakers'][key]={'name':name,'portrait':portrait,'actor_id':self.actors[actor].data['id']}
            if portrait not in g.social.portraits:
                g.social.portraits[portrait]=world.image('assets/portraits/eldenmere/'+portraits[portrait]['file'])
        for role,name,portrait in (('worker_b','Injured worker','arrival_worker_b'),('runner','Sanctuary attendant','female_01'),('sentry','Sanctuary lookout','female_02')):
            key='arrival_'+role
            g.social.data['speakers'][key]={'name':name,'portrait':portrait}
            if portrait not in g.social.portraits:g.social.portraits[portrait]=world.image('assets/portraits/eldenmere/'+portraits[portrait]['file'])
        for actor in c.sanctuary_escorts:c._hide(actor)
        starts=self.manifest['starts']
        first=self.manifest['beats'][0]['goals']
        previous=dict(first)
        if self.beat:
            for beat in self.manifest['beats'][:self.beat]:previous.update(beat['goals'])
        for key,actor in self.actors.items():
            actor.position.update(previous[key] if self.beat else starts.get(key,first[key]))
            if not world.can_stand(actor.position,actor.probe_size):
                raise ValueError('Blocked arrival staging: '+key)
        self.blocking=SanctuaryBlocking(world,self.actors,self.manifest)
    def start(self,force=False):
        if self.active or self.completed:return False
        if self.game.world.data['id']!=RESERVE:return False
        if not force and self.game.regent_quest.stage!='sanctuary_arrival_pending':return False
        self.game.regent_quest.emergency.sync_music()
        self._make_cast();self._set_rail(0.);self.active=True;self.paused=False;self.error=''
        self.focused=getattr(self.game,'_music_focused',True)
        self.sections=[b['lines'] for b in self.manifest['beats']]
        self._begin_beat();return True
    def _begin_beat(self):
        self.phase_time=0.;self.dialogue_index=0;self.page_index=0;self._ready=False
        self._checkpoint_failed=False;self.caption_layout=None
        self._line_id=None;self._pending_advance=False;self._page_remaining=0.;self._page_resuming=False
        self.care.reset(self.beat)
        self.blocking.begin(self.beat,initial=self.beat==0)
        for key,actor in self.actors.items():actor.pose=self.phase.get('poses',{}).get(key)
        self.actors['runner'].carrying=not self.care.runner_delivered
        if self.beat==4:
            # Her authored departure begins after the brief retrieval hold.
            self.blocking.tracks['mira'].finished=True
            self.actors['mira'].route=[]
            self.actors['mira'].pose='care_idle';self.actors['mira'].pose_ms=10000
            self.actors['worker_a'].pose='arm_rest';self.actors['worker_a'].pose_ms=10000
        if self.beat in (1,2,3):
            self.actors['mira'].pose='care_idle';self.actors['mira'].pose_ms=10000
            self.actors['worker_a'].pose='arm_rest';self.actors['worker_a'].pose_ms=10000
        if self.beat>0:self.actors['worker_a'].pose_ms=10000
        self._sync_care_props()
        self._focus_camera()
    def _focus_camera(self):
        # Gallery initialization and intentional room cuts may reset tracking;
        # repeating an unchanged focus preserves the director's pan clock.
        tracking=self.blocking.initial_camera() if self.blocking is not None and self.beat==0 else None
        self.game.camera.focus(tracking or self.phase['camera'],
                               0 if self.reduced_motion else .04 if tracking else 1.1,
                               anchor=(.5,.5) if self.beat==7 else (.5,.35))
    def advance(self):
        if self.error:
            if not self.paused and self.focused:
                self.error='';self._checkpoint_failed=False;self._commit_beat()
                return True
            return False
        line=self.dialogue
        if line is not None and not self.paused and self.focused and not self._batch_advanced:
            self._layout(self.game.ui.painter(self.game.ui_surface))
            self._line_action(line)
            if self._action_remaining>0:
                self._pending_advance=True;return True
            if self.page_index+1>=len(self.caption_pages) and line.get('after')=='retrieve' and self._kit:
                self.care.start('retrieve',['retrieve']);self._ready=False
                self._pending_advance=True;return True
            if self.page_index+1>=len(self.caption_pages) and line['speaker']=='regent_clerk' and self.actors['page'].pose=='read_attention':
                page=self.actors['page'];page.pose='read_resume'
                self._page_remaining=sum(page.pose_animations['read_resume']['durations'])/1000
                self._page_resuming=True;self._pending_advance=True;self._ready=False
                return True
        return super().advance()

    def _line_action(self,line):
        if line['id']==self._line_id:return
        # An early confirmation must not skip an action that has not started.
        if line.get('action')=='treat':
            if self.care.busy or not self.care.setup_started:return
            self.care.start('treat',['treat','finish']);self._ready=False
        elif line['speaker']=='regent_clerk':
            page=self.actors['page'];page.pose='read_attention'
            self._page_remaining=sum(page.pose_animations['read_attention']['durations'])/1000
        self._line_id=line['id']

    def _care_finished(self,purpose):
        if purpose=='retrieve':
            self.blocking.move_actor('mira',self.phase['movement']['mira']['waypoints'])
        if self._pending_advance:
            self._pending_advance=False;self._batch_advanced=False
            # Re-enter the input path so deferred treatment and ledger cues
            # still run before acknowledging their dialogue.
            self.advance()

    def _sync_care_props(self):
        if self._world is None:return
        world=self._world
        for oldworld,record in self._care_props:
            if record in oldworld.entities:oldworld.entities.remove(record)
        self._care_props=[]
        props=['linen_mira']
        if self.care.kit_owner=='world' and not self.completed:props.append('kit')
        if self.completed or self.care.runner_linen_placed:props.append('linen_runner')
        for key in props:
            prop=self.performance['objects'][key]
            image=world.image(prop['file'])
            support=pygame.Vector2(prop['position']);point=list(support-pygame.Vector2(prop['anchor']))
            record={'id':'arrival_'+key,'position':point,'rect':image.get_rect(topleft=point),
                    'surfaces':[image],'sort_y':support.y,'phase_offset':0,'frame_duration_ms':1000}
            world.entities.append(record);self._care_props.append((world,record))
    def _next_if_ready(self):
        if not self._ready or self._checkpoint_failed or self.dialogue_index<len(self.sections[self.beat]):return
        if self.beat==7 and not self._rail_pending:
            # Acknowledge the caretaker's promise, then show the physical action.
            self._rail_pending=True;self._ready=False
            self.blocking.move_actor('caretaker',[self.art['rail']['caretaker_position']])
            return
        self._commit_beat()

    @property
    def _rail_record(self):return self.rail.record
    def _restore_rail(self):self.rail.restore()
    def _set_rail(self,progress,world=None):
        world=self._world if world is None else world
        if world is not None:self.rail.set_progress(progress,world)
    def _commit_beat(self):
        g=self.game;before=self.to_dict();party_before=g.party.to_dict()
        levels_before=g.character_progression.to_dict();cave_before=g.sanctuary_cave.to_dict()
        last=self.beat==7
        if last:
            self.completed=True
            success=sync_arrival_party(g)
        else:self.phase_index+=1;success=True
        g.player.position.update(self.actors['caelan'].position);g.player.facing=self.actors['caelan'].facing
        if not success or not (g._is_gallery_preview or g.save_progress()):
            self.phase_index=before['beat'];self.completed=before['completed'];g.party.restore(party_before)
            g.character_progression.restore(levels_before);g.sanctuary_cave.restore(cave_before)
            self.error='Progress could not be saved. Press Enter or click to retry.'
            self._checkpoint_failed=True;return
        if last:
            self.active=False;self.finished_reason='finished'
            g.player.moving=g.player.running=False;g.player.walk_ms=0
            g.party_travel.reset();self.sync_residents();g.camera.release(.45)
            g._mouse_held=False;g.social.clear_pointer()
        else:self._begin_beat()
    def _play_care_sound(self):
        if not pygame.mixer.get_init() or self.game.audio.effects_volume<=0:return
        self._sync_care_audio(stop=True)
        self._care_sound=pygame.mixer.Sound(str(ROOT/'assets/story/sanctuary_arrival/performance/cloth.wav'))
        self._care_voice=self._care_sound.play()
        self._sync_care_audio()
    def _sync_care_audio(self,paused=False,stop=False):
        voice=getattr(self,'_care_voice',None)
        if voice is None:return
        try:
            if voice.get_sound() is not self._care_sound:self._care_voice=None;return
            if stop:voice.stop();self._care_voice=None;return
            voice.set_volume(.18*self.game.audio.effects_volume)
            if paused:voice.pause()
            else:voice.unpause()
        except pygame.error:self._care_voice=None
    def handle_event(self,event):
        handled=super().handle_event(event)
        # Gallery freezes its update clock on focus loss, so pause sound on the
        # event itself rather than waiting for another simulation frame.
        self.rail.sync_audio(self.paused or not self.focused or not self.game._music_focused)
        self._sync_care_audio(self.paused or not self.focused or not self.game._music_focused)
        return handled
    def update(self,seconds):
        frozen=self.paused or not self.focused or not self.game._music_focused
        self.rail.sync_audio(frozen)
        self._sync_care_audio(frozen)
        if not self.active or frozen:return
        seconds=max(0.,float(seconds));self.elapsed+=seconds;self.phase_time+=seconds
        self._input_armed=self.elapsed>=.1
        self.blocking.update(seconds)
        for actor in self.actors.values():actor.advance_pose(seconds)
        self.care.update(seconds)
        if self.beat==0 and not self.blocking.busy('mira') and not self.care.setup_started:
            # Movement consumed this tick; start at frame zero rather than
            # spending the same delta a second time on the placement.
            self.care.start('setup',['place','take_cloth'])
        if self._page_remaining>0:
            self._page_remaining=max(0.,self._page_remaining-seconds)
            if self._page_remaining==0:
                if self._page_resuming:
                    self._page_resuming=False
                    page=self.actors['page'];page.pose='read';page.pose_ms=10000
                    self._pending_advance=False;self._batch_advanced=False
                    super().advance()
                elif self._pending_advance:
                    self._pending_advance=False;self._batch_advanced=False
                    self.advance()
        line=self.dialogue
        if line is not None:self._line_action(line)
        self._sync_care_props()
        self._settled_facings()
        self._focus_camera();self.game.camera.update(seconds)
        keeper=self.actors['caretaker']
        if self._rail_pending and not self._rail_retreat and self.blocking.settled:
            keeper.facing=self.art['rail'].get('facing','back')
            keeper.moving=False;keeper.pose='unhook'
            self._rail_elapsed+=seconds
            keeper.pose_ms=self._rail_elapsed*1000
            duration=self.rail.duration_ms/1000
            self._set_rail(self._rail_elapsed/duration)
            if self._rail_elapsed*1000>=self.art['rail'].get('release_ms',self.art['rail'].get('contact_ms',0)):
                self.rail.play_release()
            if self._rail_elapsed>=duration:
                self._rail_retreat=True;keeper.pose=None
                self.blocking.move_actor('caretaker',[self.phase['goals']['caretaker']])
        self._ready=(self.phase_time>=self.phase['min_seconds'] and self.game.camera.settled
                     and self.blocking.settled and not self.blocking.busy('runner') and self._delivery_remaining==0
                     and self.care.runner_delivered and not self.care.busy and self._page_remaining==0
                     and (not self._rail_pending or self._rail_retreat))
        self._next_if_ready()
    def _settled_facings(self):
        if not self.actors:return
        a=self.actors
        target={'caelan':'caretaker','caretaker':'caelan','aldric':'caretaker','lucan':'caretaker',
                'mira':'worker_a','runner':'worker_b','sentry':(1008,359)}
        if self.beat==0:target['lucan']=(1008,359)
        if self.beat==2:
            for key in ('caelan','caretaker','lucan','aldric'):target[key]=(1008,359)
        if self.beat==3:target['caretaker']='aldric'
        if self.beat in (4,5):
            target.update(caelan='lucan',mira='lucan',lucan='caelan',aldric='lucan')
            if self.beat==5:target['lucan']='aldric'
        if self.beat==6:
            for key in ('caelan','caretaker','lucan','mira'):target[key]=(534,370)
        if self.beat==7:
            for key in ('caelan','lucan','mira','caretaker'):target[key]=(1008,359)
            target['aldric']='worker_a'
        line=self.dialogue
        if line is not None:
            speaker={'arrival_caretaker':'caretaker','arrival_worker':'worker_a','regent_clerk':'page'}.get(line['speaker'],line['speaker'])
            if speaker in a:
                listener='aldric' if self.beat==3 and speaker=='caretaker' else 'caretaker' if speaker=='aldric' else 'lucan' if speaker in ('caelan','mira') and self.beat==4 else 'caelan'
                if speaker not in ('mira','worker_a','page'):target[speaker]=listener
                if listener not in ('mira','worker_a','page'):target[listener]=speaker
        for key,destination in target.items():
            actor=a[key]
            if actor.moving or actor.route or key=='caretaker' and self._rail_pending and not self._rail_retreat:continue
            if key=='mira' and (self.care.busy or self.beat<4):
                actor.facing=self.performance['poses'].get(actor.pose,{}).get('facing','left')
                continue
            if key=='runner' and actor.pose=='runner_place':
                actor.facing=self.performance['poses']['runner_place'].get('facing','front')
                continue
            point=a[destination].position if isinstance(destination,str) else pygame.Vector2(destination)
            delta=point-actor.position
            if delta.length_squared():actor.facing=facing_toward(delta)
        a['worker_a'].facing=self.performance['poses'].get(a['worker_a'].pose,{}).get('facing','front')
        a['worker_b'].facing='front'
        if not a['page'].moving:a['page'].facing='left'

    def sync_residents(self):
        if not self.completed or self.game.regent_quest.stage!='sanctuary_arrival_pending':return
        g=self.game;world=g._scene_by_id(RESERVE);c=g.regent_quest
        # Same authoritative royal actors remain in the reserve; Lucan is now
        # represented by ordinary PartyTravel and is never drawn twice.
        if self._world is None:
            oldworld=g.world;g.world=world
            self._make_cast();g.world=oldworld
            goals={}
            for beat in self.manifest['beats']:goals.update(beat['goals'])
            for key,actor in self.actors.items():
                actor.position.update(goals[key]);actor.pose=self.manifest['beats'][-1].get('poses',{}).get(key)
            self.actors['worker_a'].pose_ms=10000
        for actor in self.actors.values():actor.route=[];actor.moving=False
        for key,source in (('aldric',c.aldric),('page',c.clerk)):
            c._place(source,world,self.actors[key].position);source.story_following=False
        if (getattr(g.sanctuary_cave,'lucan_departed',False)
                and g.party.is_guest('lucan')):
            # He has returned to Aldric after the completed cave outing;
            # use the canonical royal actor, never a second follower sprite.
            c._place(c.lucan,world,(844,414));c.lucan.story_following=False
            c.lucan.facing='left';c.lucan.set_pose(None)
        else:c._hide(c.lucan)
        self._settled_facings()
        for key,source in (('aldric',c.aldric),('page',c.clerk)):
            source.facing=self.actors[key].facing
            if key=='page' and hasattr(source,'set_pose'):
                source.set_pose('read',elapsed_ms=10000)
        self._set_rail(1.,world)
        for key in ('caretaker','worker_a','worker_b','sentry','runner'):
            actor=self.actors[key];actor.route=[];actor.moving=False
            if actor not in world.npcs:world.npcs.append(actor);self._published.append((world,actor))
        self.care.kit_owner='stowed';self.care.runner_delivered=True;self._sync_care_props()
        self.stage_party()
    def stage_party(self):
        # Story restoration temporarily uses town coordinates while rebuilding
        # regional owners; Continue calls this again after restoring real feet.
        g=self.game
        if g.world.data['id']!=RESERVE:return
        self._set_rail(1. if self.completed else 0.,g.world)
        # Older checkpoints can occupy the new post/rope footprint or a revised
        # resident station. Reconcile real regional feet after story restoration.
        if not g.world.can_stand(g.player.position):
            landing=g.world.data['public_approaches']['cave']
            if g.world.can_stand(landing):g.player.position.update(landing)
        if not self.completed or g.regent_quest.stage!='sanctuary_arrival_pending':return
        leader=self.manifest['beats'][-1]['goals']['caelan']
        if g.player.position.distance_to(leader)<1:
            followers=tuple(key for key in ('mira','lucan') if key in g.party.active_ids)
            g.party_travel.stage_companions(
                {key:self.actors[key].position for key in followers},
                facings={key:self.actors[key].facing for key in followers})
    def draw(self,canvas,ui_surface):
        g=self.game;old=g.player.story_visible if hasattr(g.player,'story_visible') else True
        g.player.story_visible=False
        self._world.reduced_motion=self.reduced_motion
        try:self._world.draw(canvas,g.camera.position(),g.player,self.elapsed*1000,include_ui=False,party_actors=tuple(self.actors.values()))
        finally:g.player.story_visible=old
        pygame.transform.scale(canvas,ui_surface.get_size(),ui_surface)
        painter=g.ui.painter(ui_surface);self._layout(painter)
        if self.caption_layout is not None:
            portrait=g.social.portraits[self.caption_layout.portrait_key]
            speech_bubble.draw_dialogue_frame(painter,self.caption_layout,portrait)
            speech_bubble.draw_dialogue_prose(painter,self.caption_layout,self.caption_lines,hint='Click to continue',show_indicator=True)
        painter.text(('P · Resume' if self.paused else 'P · Pause') if g._is_gallery_preview else ('Esc · Resume' if self.paused else 'Esc · Pause'),(12,310),role='small',color=MUTED,anchor='bottomleft')
        if self.error:
            painter.panel((35,100,410,65));painter.text(self.error,(45,120),role='small',color=GOLD)
        if self.paused or not self.focused:
            painter.panel((193,20,94,26));painter.text('Paused',(240,33),color=IVORY,anchor='center')
