"""Player-paced MQ03 rescue staging on the live Sanctuary reserve.

Only acknowledged beats, the rescue handoff and first cave entry persist.
Camera movement, actor paths and partial pages rebuild on Continue.
"""
from pathlib import Path
import json
import pygame
import speech_bubble
from mill_gift import MillGift,smooth
from npc_routines import find_path
from social import facing_toward
from regent_emergency import legacy_cave_entered
from sanctuary_arrival_party import sync_arrival_party
from ui_style import IVORY,MUTED,GOLD
ROOT=Path(__file__).resolve().parent
RESERVE='elden_vale_sanctuary'

class CastActor:
    """A scene display actor with full-foot static-terrain navigation."""
    def __init__(self,key,world,source=None,variant='male_02'):
        self.data={'id':'sanctuary_arrival_'+key};self.key=key
        self.position=pygame.Vector2();self.probe_size=(24,12)
        self.story_visible=True;self.party_travelling=False;self.moving=False
        self.facing='front';self.walk_ms=0.;self.pose=None;self.route=[]
        self.draw_anchor=tuple(getattr(source,'draw_anchor', (12,30)))
        if key=='caelan':self.draw_anchor=(12,30)
        if source is not None:self.idles=source.idles;self.walks=source.walks
        else:
            self.idles={d:world.image(f'assets/characters/npcs/{variant}/idle_{d}.png') for d in ('front','back','left','right')}
            self.walks={d:[world.image(f'assets/characters/npcs/{variant}/walk_{d}/frame_{i:02}.png') for i in range(1,5)] for d in self.idles}
        self._poses={}
        if key.startswith('worker'):
            self._poses['injured']=world.image('assets/story/regent_emergency/poses/rest_front.png')
        if key=='mira':
            for name,file in (('tend','inspect'),('set_down','reach'),('retrieve','withdraw')):
                self._poses[name]=world.image(f'assets/characters/mira/work_bench/{file}.png')
        if key=='page':
            source=world.image('assets/story/regent_arrival/actors/clerk/read_left.png')
            reading=pygame.Surface((24,36),pygame.SRCALPHA)
            reading.blit(pygame.transform.scale(source,(28,34)),(-2,1))
            self._poses['read']=reading
    @property
    def blocker(self):return pygame.Rect(round(self.position.x)-4,round(self.position.y)-2,8,4)
    def end_conversation(self):pass
    def request_conversation(self,facing):self.facing=facing
    def sprite(self,elapsed_ms):
        if not self.moving and self.pose in self._poses:return self._poses[self.pose]
        frames=self.walks[self.facing] if self.moving else None
        image=frames[int(self.walk_ms//140)%len(frames)] if frames else self.idles[self.facing]
        return image[0] if isinstance(image,tuple) else image
    def goal(self,point,world):
        path=find_path(world,self.position,point,self.probe_size,None)
        if path is None:raise ValueError(f'Blocked arrival route: {self.key} to {point}')
        self.route=list(path)
    def update(self,seconds,world):
        remaining=seconds*76;self.moving=False
        while self.route and remaining>0:
            delta=pygame.Vector2(self.route[0])-self.position
            if delta.length()<.05:self.route.pop(0);continue
            direction=delta.normalize();step=min(1.,remaining,delta.length())
            candidate=self.position+direction*step
            if not world.can_stand(candidate,self.probe_size):
                raise ValueError('Arrival actor crossed solid terrain: '+self.key)
            self.position=candidate;remaining-=step;self.moving=True
            self.facing=facing_toward(direction);self.walk_ms+=step/76*1000

class SanctuaryArrival(MillGift):
    """Shared cinematic input/captions, with in-world actors and checkpoint beats."""
    def __init__(self,game):
        self.game=game
        self.manifest=json.loads((ROOT/'assets/story/sanctuary_arrival/scene.json').read_text())
        self._published=[];self.actors={};self._world=None
        self.reset()
    def reset(self):
        for world,actor in getattr(self,'_published',[]):
            if actor in world.npcs:world.npcs.remove(actor)
        self._published=[];self.actors={};self._world=None
        super().reset();self.completed=False;self.cave_entered=False;self.error=''
        self._ready=False;self._checkpoint_failed=False
        self._restore_rail()
        self._rail_pending=False;self._rail_elapsed=0.;self._rail_retreat=False
    @property
    def beat(self):return self.phase_index
    @property
    def phase(self):return self.manifest['beats'][self.beat]
    @property
    def shot(self):return self.phase['id']
    @property
    def dialogue(self):return super().dialogue if self._ready and not self.error else None
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
            self.actors[key]=CastActor(key,world,variant=variant)
        for key,name,portrait in (('arrival_caretaker','Caretaker','male_03'),('arrival_worker','Injured worker','regent_survivor')):
            g.social.data['speakers'][key]={'name':name,'portrait':portrait}
        for actor in c.sanctuary_escorts:c._hide(actor)
        starts={'caelan':[444,642],'mira':[412,642],'lucan':[476,632],'aldric':[444,680],'page':[476,680]}
        first=self.manifest['beats'][0]['goals']
        previous=dict(first)
        if self.beat:
            for beat in self.manifest['beats'][:self.beat]:previous.update(beat['goals'])
        for key,actor in self.actors.items():
            actor.position.update(previous[key] if self.beat else starts.get(key,first[key]))
            if not world.can_stand(actor.position,actor.probe_size):
                raise ValueError('Blocked arrival staging: '+key)
    def start(self,force=False):
        if self.active or self.completed:return False
        if self.game.world.data['id']!=RESERVE:return False
        if not force and self.game.regent_quest.stage!='sanctuary_arrival_pending':return False
        self.game.regent_quest.emergency.sync_music()
        self._make_cast();self.active=True;self.paused=False;self.error=''
        self.focused=getattr(self.game,'_music_focused',True)
        self.sections=[b['lines'] for b in self.manifest['beats']]
        self._begin_beat();return True
    def _begin_beat(self):
        self.phase_time=0.;self.dialogue_index=0;self.page_index=0;self._ready=False
        self._checkpoint_failed=False;self.caption_layout=None
        self._mira_departure=None
        for key,point in self.phase['goals'].items():self.actors[key].goal(point,self._world)
        for key,actor in self.actors.items():actor.pose=self.phase.get('poses',{}).get(key)
        if self.beat==4:
            # Finish taking up the kit at the worker before walking to Lucan.
            self._mira_departure=self.phase['goals']['mira']
            self.actors['mira'].route=[];self.actors['mira'].pose='retrieve'
        self._focus_camera()
    def _focus_camera(self):
        # Gallery initialization and intentional room cuts may reset tracking;
        # repeating an unchanged focus preserves the director's pan clock.
        self.game.camera.focus(self.phase['camera'],0 if self.reduced_motion else 1.1,
                               anchor=(.5,.5) if self.beat==7 else (.5,.35))
    def advance(self):
        if self.error:
            if not self.paused and self.focused:
                self.error='';self._checkpoint_failed=False;self._commit_beat()
                return True
            return False
        return super().advance()
    def _next_if_ready(self):
        if not self._ready or self._checkpoint_failed or self.dialogue_index<len(self.sections[self.beat]):return
        if self.beat==7 and not self._rail_pending:
            # Acknowledge the caretaker's promise, then show the physical action.
            self._rail_pending=True;self._ready=False
            self.actors['caretaker'].goal((1056,390),self._world)
            return
        self._commit_beat()

    def _restore_rail(self):
        original=getattr(self,'_rail_original',None)
        record=getattr(self,'_rail_record',None)
        if original is not None and record is not None:
            record.update(position=list(original['position']),rect=original['rect'].copy(),
                          surfaces=list(original['surfaces']),sort_y=original['sort_y'])
        self._rail_original=None;self._rail_record=None;self._rail_progress=None

    def _set_rail(self,progress,world=None):
        world=self._world if world is None else world
        if world is None:return
        if self._rail_record is None:
            self._rail_record=next(e for e in world.entities if e['id']=='reserve_cave_keeper_rail')
            r=self._rail_record
            self._rail_original={'position':list(r['position']),'rect':r['rect'].copy(),
                                 'surfaces':tuple(r['surfaces']),'sort_y':r['sort_y']}
        original=self._rail_original;image=original['surfaces'][0]
        progress=smooth(max(0.,min(1.,progress)))
        if progress==self._rail_progress:return
        self._rail_progress=progress
        angle=-80*progress
        surface=pygame.transform.rotate(image,angle)
        pivot=pygame.Vector2(image.get_width(),31)
        hinge=pygame.Vector2(original['position'])+pivot
        offset=(pivot-pygame.Vector2(image.get_size())/2).rotate(-angle)
        rect=surface.get_rect(center=(round(hinge.x-offset.x),round(hinge.y-offset.y)))
        self._rail_record.update(position=list(rect.topleft),rect=rect,surfaces=[surface],sort_y=original['sort_y'])
    def _commit_beat(self):
        g=self.game;before=self.to_dict();party_before=g.party.to_dict()
        last=self.beat==7
        if last:
            self.completed=True
            success=sync_arrival_party(g)
        else:self.phase_index+=1;success=True
        g.player.position.update(self.actors['caelan'].position);g.player.facing=self.actors['caelan'].facing
        if not success or not (g._is_gallery_preview or g.save_progress()):
            self.phase_index=before['beat'];self.completed=before['completed'];g.party.restore(party_before)
            self.error='Progress could not be saved. Press Enter or click to retry.'
            self._checkpoint_failed=True;return
        if last:
            self.active=False;self.finished_reason='finished'
            g.player.moving=g.player.running=False;g.player.walk_ms=0
            g.party_travel.reset();self.sync_residents();g.camera.release(.45)
            g._mouse_held=False;g.social.clear_pointer()
        else:self._begin_beat()
    def update(self,seconds):
        if not self.active or self.paused or not self.focused or not self.game._music_focused:return
        seconds=max(0.,float(seconds));self.elapsed+=seconds;self.phase_time+=seconds
        self._input_armed=self.elapsed>=.1
        if self._mira_departure is not None and self.phase_time>=.8:
            self.actors['mira'].pose=None
            self.actors['mira'].goal(self._mira_departure,self._world);self._mira_departure=None
        for actor in self.actors.values():actor.update(seconds,self._world)
        self._settled_facings()
        self._focus_camera();self.game.camera.update(seconds)
        # Background errands continue independently of the principal tableau.
        runner=self.actors['runner']
        if not runner.route and self.beat<6 and self.phase_time>3:
            runner.goal((600,380) if runner.position.x>650 else (740,366),self._world)
        if self._rail_pending and not self._rail_retreat and not self.actors['caretaker'].route:
            self._rail_elapsed+=seconds
            self._set_rail(self._rail_elapsed/.9)
            if self._rail_elapsed>=.9:
                self._rail_retreat=True
                self.actors['caretaker'].goal(self.phase['goals']['caretaker'],self._world)
        self._ready=(self.phase_time>=self.phase['min_seconds'] and self.game.camera.settled
                     and all(not a.route for key,a in self.actors.items() if key!='runner')
                     and (not self._rail_pending or self._rail_retreat) and self._mira_departure is None)
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
        for key,destination in target.items():
            actor=a[key]
            if actor.moving or actor.route:continue
            point=a[destination].position if isinstance(destination,str) else pygame.Vector2(destination)
            delta=point-actor.position
            if delta.length_squared():actor.facing=facing_toward(delta)
        for key in ('worker_a','worker_b'):a[key].facing='front'
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
        for key,source in (('aldric',c.aldric),('page',c.clerk)):
            c._place(source,world,self.actors[key].position);source.story_following=False
        c._hide(c.lucan)
        self._set_rail(1.,world)
        for key in ('caretaker','worker_a','worker_b','sentry','runner'):
            actor=self.actors[key];actor.route=[];actor.moving=False
            if actor not in world.npcs:world.npcs.append(actor);self._published.append((world,actor))
        self.stage_party()
    def stage_party(self):
        # Story restoration temporarily uses town coordinates while rebuilding
        # regional owners; Continue calls this again after restoring real feet.
        if not self.completed or self.game.regent_quest.stage!='sanctuary_arrival_pending':return
        g=self.game
        if g.world.data['id']!=RESERVE:return
        leader=self.manifest['beats'][-1]['goals']['caelan']
        if g.player.position.distance_to(leader)<1:
            g.party_travel.stage_companions(
                {key:self.actors[key].position for key in ('mira','lucan')},
                facings={key:self.actors[key].facing for key in ('mira','lucan')})
    def draw(self,canvas,ui_surface):
        g=self.game;old=g.player.story_visible if hasattr(g.player,'story_visible') else True
        g.player.story_visible=False
        self._world.reduced_motion=self.reduced_motion
        try:self._world.draw(canvas,g.camera.position(),g.player,self.elapsed*1000,include_ui=False,party_actors=tuple(self.actors.values()))
        finally:g.player.story_visible=old
        # Small physical care supplies remain grounded beside the workers.
        camera=g.camera.position()
        if self.beat<4 or self._mira_departure is not None:
            x,y=self.manifest['beats'][0]['goals']['mira'];offset=(15,-5)
        else:
            mira=self.actors['mira'];x,y=mira.position
            offset=(-12,-14) if mira.facing in ('left','back') else (8,-14)
        rect=pygame.Rect(round(x-camera[0]+offset[0]),round(y-camera[1]+offset[1]),10,6)
        pygame.draw.rect(canvas,'#604d35',rect);canvas.blit(self._linen,(rect.x+2,rect.y+1))
        runner=self.actors['runner']
        canvas.blit(self._linen,(round(runner.position.x-camera[0]-3),round(runner.position.y-camera[1]-16)))
        pygame.transform.scale(canvas,ui_surface.get_size(),ui_surface)
        painter=g.ui.painter(ui_surface);self._layout(painter)
        if self.caption_layout is not None:
            portrait=g.social.portraits[self.caption_layout.portrait_key]
            speech_bubble.draw_dialogue_frame(painter,self.caption_layout,portrait)
            speech_bubble.draw_dialogue_prose(painter,self.caption_layout,self.caption_lines,hint='Click to continue',show_indicator=True)
        painter.text('Esc · Resume' if self.paused else 'Esc · Pause',(12,310),role='small',color=MUTED,anchor='bottomleft')
        if self.error:
            painter.panel((35,100,410,65));painter.text(self.error,(45,120),role='small',color=GOLD)
        if self.paused or not self.focused:
            painter.panel((193,20,94,26));painter.text('Paused',(240,33),color=IVORY,anchor='center')
