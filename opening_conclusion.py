"""MQ01 report, real sanctuary arrival, and a durable handoff to Mira."""
from collections import deque
import json
from pathlib import Path
import pygame
from halden_visit import point
from npc_routines import find_path
from quests import OPENING_QUEST, MILL_QUEST
from social import facing_toward

ROOT=Path(__file__).resolve().parent
STAGES=('idle','arrival','waiting','done')

class OpeningConclusion:
    def __init__(self,game):
        self.game=game;self.stage='idle';self.dialogue=False
        self.serene=next(n for n in game.persistent_npcs if n.data['id']=='mother_serene')
        self.halden=game.halden_visit.halden
        self.hall=game._scene_by_id('sanctuary_hall')
        self.worlds={self.halden:game.halden_visit.home}
        self.paths={};self.retries={};self.settled=False
        self.lines=json.loads((ROOT/'assets/story/opening_conclusion.json').read_text())
        self.halden.walks={d:[game.town.image(f'assets/story/halden/walk_{d}_{i}.png') for i in range(4)]
                           for d in ('front','left','right','back')}
    @property
    def locks_player(self):return False
    @property
    def mill_stopped(self):return self.stage!='idle'
    def to_dict(self):return {'version':1,'stage':self.stage}
    @staticmethod
    def valid_journey(data):
        state=data['opening_conclusion']
        if (not isinstance(state,dict) or set(state)!={'version','stage'} or
                type(state['version']) is not int or state['version']!=1 or state['stage'] not in STAGES):return False
        from quests import QuestLog
        quests=QuestLog()
        if not quests.restore(data.get('quests')):return False
        status=quests.status(OPENING_QUEST)
        if state['stage']!='idle' and status not in ('ready','completed'):return False
        if state['stage']=='done' and (status!='completed' or quests.status(MILL_QUEST)=='locked'):return False
        if state['stage']!='done' and quests.status(MILL_QUEST)!='locked':return False
        return True
    def _world(self,actor):
        return self.game._routine_worlds[actor] if actor is self.serene else self.worlds[actor]
    def _place(self,actor,world,position):
        old=self._world(actor)
        if actor in old.npcs:old.npcs.remove(actor)
        if actor not in world.npcs:world.npcs.append(actor)
        actor.position.update(position);actor.scene_id=world.data['id'];actor.moving=False
        if actor is self.serene:self.game._routine_worlds[actor]=world
        else:self.worlds[actor]=world
        self.paths.pop(actor,None)
    def _landing(self,world,preferred,actor):
        avoid=world.probe_rect(self.game.player.position) if world is self.game.world else None
        for radius in (0,16,24,32,48):
            for dx,dy in ((0,radius),(radius,0),(0,-radius),(-radius,0)):
                p=(preferred[0]+dx,preferred[1]+dy)
                if world.can_stand(p,actor.probe_size,actor,avoid):return p
        return None
    def _stop_mill(self):
        for record in self.game.town.entities:
            if record['id']=='mill':record['animation_stopped']=self.mill_stopped
    def restore(self,data=None):
        self.paths.clear();self.retries.clear();self.dialogue=False;self.settled=False
        self.serene.story_paused=False;self.serene.story_sprite=None;self.halden.end_conversation()
        # Old turn-ins retain completion and receive only their missing arrival.
        self.stage=data['stage'] if data else ('arrival' if self.game.quests.status(OPENING_QUEST)=='completed' else 'idle')
        home=self.game.halden_visit.home
        self._place(self.halden,home,(192,176))
        if self.stage=='idle' and self.game.quests.status(OPENING_QUEST)=='completed':self.stage='arrival'
        if self.stage in ('arrival','waiting','done'):
            self.serene.story_paused=True
            if self.stage in ('waiting','done'):
                for actor,goal in [(self.serene,(184,230)),(self.halden,(224,230))]:
                    landing=self._landing(self.hall,goal,actor)
                    if landing is not None:self._place(actor,self.hall,landing)
                self.serene.select_step('move_to_hall_table',position=tuple(self.serene.position),scene_id=self.serene.scene_id)
                self.serene.story_sprite=self.serene.idles[self.serene.facing]
                self.settled=True
            else:self._begin_arrival()
        if self.stage=='done':self._release_serene()
        self._stop_mill()
    def _save(self):
        self._stop_mill();self.game.save_progress()
    def reported(self):
        if self.stage!='idle' or self.game.quests.status(OPENING_QUEST)!='ready':return
        self.game.social.flags.add('CH01_MQ01_REPORTED')
        self.stage='arrival';self._begin_arrival();self._save()
    def _begin_arrival(self):
        self.serene.story_paused=True
        self.serene.select_step('move_to_hall_table',position=tuple(self.serene.position),scene_id=self.serene.scene_id)
        # His trip from home is offscreen. Only the courtyard-to-hall entrance is staged.
        goal=(386,326);landing=self._landing(self.game.town,goal,self.halden)
        if landing is not None:self._place(self.halden,self.game.town,landing)
    def _move(self,actor,goal,dt):
        world=self._world(actor);goal=point(goal);actor.moving=False
        if actor.position.distance_to(goal)<1:return True
        avoid=world.probe_rect(self.game.player.position) if world is self.game.world else None
        self.retries[actor]=max(0,self.retries.get(actor,0)-dt)
        cached=self.paths.get(actor)
        if cached is None or cached[0]!=goal:
            if self.retries[actor]>0:return False
            route=find_path(world,actor.position,goal,actor.probe_size,actor,avoid)
            if route is None:self.retries[actor]=.4;return False
            self.paths[actor]=(goal,deque(route));cached=self.paths[actor]
        route=cached[1];budget=max(0,dt)*56
        while route and budget>1e-7:
            delta=pygame.Vector2(route[0])-actor.position;distance=delta.length()
            if distance<1e-7:route.popleft();continue
            travel=min(1,budget,distance);candidate=actor.position+delta/distance*travel
            if not world.can_stand(candidate,actor.probe_size,actor,avoid):
                self.paths.pop(actor,None);self.retries[actor]=.2;return False
            actor.position.update(candidate);actor.facing=facing_toward(delta)
            actor.moving=True;actor.walk_ms+=travel/56*1000;budget-=travel
            if travel>=distance-1e-7:route.popleft()
        return actor.position.distance_to(goal)<1
    def _enter_hall(self,actor,dt):
        world=self._world(actor)
        if world is self.hall:return True
        door=next((d for d in world.doors if (ROOT/d.data['destination']).resolve()==self.hall.path),None)
        if door is None:return False
        if not self._move(actor,door.data['anchor'],dt):return False
        if door.data['requires_open'] and door.state!='open':return False
        avoid=self.hall.probe_rect(self.game.player.position) if self.game.world is self.hall else None
        if not self.hall.can_stand(door.data['spawn'],actor.probe_size,actor,avoid):return False
        self._place(actor,self.hall,door.data['spawn'])
        arrival=next(d for d in self.hall.doors if d.data['id']==door.data['arrival_door']);arrival.force_open()
        return True
    def update(self,dt):
        if self.stage not in ('arrival','waiting'):return
        if self.game.quest_ui.journal_open or self.game.map_open:return
        for actor in (self.serene,self.halden):actor.moving=False
        if self.stage=='arrival':
            ready=[]
            for actor,goal in [(self.serene,(184,230)),(self.halden,(224,230))]:
                ready.append(self._enter_hall(actor,dt) and self._move(actor,goal,dt))
            if all(ready):
                self.stage='waiting';self.settled=True;self._save()
        frames=self.serene.walks[self.serene.facing]
        self.serene.story_sprite=(frames[int(self.serene.walk_ms//140)%len(frames)][0] if self.serene.moving else self.serene.idles[self.serene.facing])
        if self.stage=='waiting' and not self.game.social.locked and self.game.world is self.hall:
            if self.game.player.position.distance_to(self.serene.position)<38:self._speak()
    def _speak(self):
        if self.game.social.locked:return False
        self.serene.facing=facing_toward(self.game.player.position-self.serene.position)
        self.serene.conversation_facing=self.serene.facing
        self.halden.facing=facing_toward(self.game.player.position-self.halden.position)
        result=self.game.social.start_script(self.lines['mill_arrival'],self._finish,'opening_mill_arrival')
        self.dialogue=result
        return result
    def _finish(self):
        if self.stage!='waiting':return
        self.dialogue=False;self.stage='done'
        self.game.quests.turn_in(OPENING_QUEST,'mother_serene')
        self.game.quests.unlock(MILL_QUEST)
        self.game.social.flags.update({'CH01_MQ01_REPORTED','CH01_MQ01_COMPLETE'})
        self.game.social.blocked.update((self.serene,self.halden))
        self._release_serene();self._save()
    def _release_serene(self):
        self.serene.end_conversation();self.serene.story_paused=False
        self.serene.story_sprite=None
        self.serene.select_step('move_to_hall_table',position=tuple(self.serene.position),scene_id='sanctuary_hall',facing='front')
    def can_speak(self,identifier):
        if identifier in ('mother_serene','halden') and self.stage in ('arrival','waiting'):return False
        return True
    def try_conversation(self,actor):return None
    def on_dialogue_cancelled(self,identifier):
        if identifier=='opening_mill_arrival':self.dialogue=False
    def tracker_text(self):
        if self.stage in ('arrival','waiting'):return 'Meet Mother Serene and Halden in the sanctuary hall.'
        return ''
    def interaction_hint(self):return ''
    def interact(self):return False
    def draw_world(self,canvas,camera):pass
