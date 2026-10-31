"""Finite masonry sorting and an opt-in tea break at the near bank.

Regional actors and props belong to this controller, never streamed chunks.
Completed placements and tea beats persist; interrupted carries restart at the
last safe station. The ruined crossing and all story flags are read-only.
"""
from pathlib import Path
import pygame
from grain_farm import FarmWorker

ROOT = Path(__file__).resolve().parent
ART = ROOT/'assets/characters/bridge_workers'
SOURCE = (-2376, 616)
STACK = (-2344, 616)
REJECT = (-2312, 616)
KETTLE = (-2304, 584)
HELP = (-2360, 616)
SEAT = (-2400, 600)
BARRIER = (-2400, 616)
SAFE = (-2360, 607)
SCENE_ID = 'bridge_crew_tea'
HANDOFF = pygame.Rect(-2387, 600, 40, 22)


def empty_state():
    return {'sorted': 0, 'tea_beat': 0, 'greeted': []}


def valid_state(data):
    return (isinstance(data, dict) and set(data) == set(empty_state())
            and type(data['sorted']) is int and 0 <= data['sorted'] <= 3
            and type(data['tea_beat']) is int and 0 <= data['tea_beat'] <= 5
            and (not data['tea_beat'] or data['sorted'] == 3)
            and isinstance(data['greeted'], list)
            and all(isinstance(x, str) and x in ('mason', 'tender') for x in data['greeted'])
            and len(data['greeted']) == len(set(data['greeted'])))


class BridgeWorker(FarmWorker):
    def __init__(self, role, variant, position):
        self.role = role
        self.data = {'id': 'bridge_'+role, 'name': 'Bridge mason' if role == 'mason' else 'Bridge surveyor'}
        self.scene_id = 'auratia.overworld'
        self.position = pygame.Vector2(position)
        self.probe_size = (10, 6)
        self.draw_anchor = (20, 38)
        self.facing = 'front'; self.pose = 'idle'; self.clock = 0; self.moving = False
        self.frames = {}
        base = ROOT/f'assets/characters/npcs/{variant}'
        for direction in ('front', 'back', 'left', 'right'):
            self.frames['idle_'+direction] = [self._padded(base/f'idle_{direction}.png')]
            self.frames['walk_'+direction] = [self._padded(base/f'walk_{direction}/frame_{i:02}.png') for i in range(1,5)]
        for pose in ('lift','carry','work','stretch','measure','cup','offer','receive','drink','sit'):
            self.frames[pose] = [pygame.image.load(str(ART/f'{role}_{pose}_{i}.png')).convert_alpha()
                                 for i in range(4 if pose in ('carry','cup') else 2)]


    def sprite(self, elapsed_ms):
        if self.pose == 'cup' and not self.moving:return self.frames['cup'][0]
        return super().sprite(elapsed_ms)


class BridgeCrew:
    def __init__(self, world):
        self.world = world
        self.mason = BridgeWorker('mason', 'male_01', SOURCE)
        self.tender = BridgeWorker('tender', 'male_03', KETTLE)
        self.actors = [self.mason, self.tender]
        self.art = {name: pygame.image.load(str(ART/(name+'.png'))).convert_alpha()
                    for name in ('stone','cup','kettle','bench','tray','tool','barrier','keep_mark','reject_mark')}
        self.restore()

    def restore(self, data=None):
        self.state = {**empty_state(), **(data or {})}
        self.state['greeted'] = list(self.state['greeted'])
        self.mason.position.update(SOURCE); self.tender.position.update(KETTLE)
        for actor in self.actors:
            actor.clock = 0; actor.pose = 'idle'; actor.facing = 'front'; actor.moving = False
        self.timer = 0; self.route = 0; self.work_timer = 0
        beat = self.state['tea_beat']
        self.stage = 'inspect' if self.state['sorted'] < 3 else 'ready'
        if beat == 1:self.stage = 'tea_pickup'
        elif beat in (2,3,4):
            self.tender.position.update(HELP)
            self.stage = {2:'reach',3:'exchange',4:'sit_walk'}[beat]
        elif beat == 5:self.stage = 'ready'
        self.dialogue_running = False

    def to_dict(self):return {**self.state, 'greeted':list(self.state['greeted'])}

    def _stage(self, stage):
        self.stage = stage; self.timer = 0
        for actor in self.actors:actor.pose = 'idle'; actor.moving = False

    def _commit(self, game, **changes):
        self.state.update(changes); game.save_progress()

    def _walk(self, actor, target, seconds, player, pose='idle'):
        delta = pygame.Vector2(target)-actor.position
        actor.pose = pose; actor.moving = False
        if delta.length() < .1:return True
        actor.facing = ('right' if delta.x>0 else 'left') if abs(delta.x)>abs(delta.y) else ('front' if delta.y>0 else 'back')
        remaining = min(delta.length(), 22*seconds)
        while remaining > 0:
            step = min(1, remaining); point = actor.position+delta.normalize()*step
            if not self.world.can_stand(point, actor.probe_size, actor, player):return False
            actor.position.update(point); remaining -= step; actor.moving = True
        return actor.position.distance_to(target) < .1

    def _script(self, game, lines, completed):
        def done():
            self.dialogue_running = False; completed()
        self.dialogue_running = game.social.start_script(lines, on_complete=done, identifier=SCENE_ID)
        return self.dialogue_running

    def update(self, seconds, game):
        if game.player.position.distance_to(SOURCE)>260 or game.social.locked:return
        # A cancelled page leaves its physical beat available on the next E.
        if self.dialogue_running:self.dialogue_running = False
        seconds = min(seconds,.1); self.timer += seconds
        for actor in self.actors:actor.clock += seconds; actor.moving = False
        player = self.world.probe_rect(game.player.position)
        stage = self.stage
        if stage in ('inspect','lift','carry','place','return','ready','barrier','barrier_return'):
            route = [(-2336,584),(-2376,584),KETTLE]
            if self._walk(self.tender,route[self.route],seconds,player):
                self.tender.pose = 'measure';self.work_timer += seconds
                if self.work_timer>3:self.route=(self.route+1)%3;self.work_timer=0
        if stage == 'inspect':
            self.mason.pose = 'lift'
            if self.timer >= 2:self._stage('lift')
        elif stage == 'lift':
            self.mason.pose = 'lift' if self.timer<.7 else 'carry'
            if self.timer>=1.4:self._stage('carry')
        elif stage == 'carry':
            if self._walk(self.mason,REJECT if self.state['sorted']==2 else STACK,seconds,player,'carry'):self._stage('place')
        elif stage == 'place':
            self.mason.pose = 'lift'
            if self.timer>=1.2:
                self._commit(game,sorted=self.state['sorted']+1);self._stage('return')
        elif stage == 'return':
            if self._walk(self.mason,SOURCE,seconds,player):self._stage('inspect' if self.state['sorted']<3 else 'ready')
        elif stage == 'ready':
            self.mason.pose = 'stretch' if self.timer<2 else 'work'
            if self.timer>8:self._stage('barrier')
        elif stage == 'barrier':
            if self._walk(self.mason,BARRIER,seconds,player):
                self.mason.facing = 'left'
                self.mason.pose = 'idle' if self.timer<3 else 'measure'
                if self.timer>5:self._stage('barrier_return')
        elif stage == 'barrier_return':
            if self._walk(self.mason,SOURCE,seconds,player):self._stage('ready')
        elif stage == 'tea_home':
            if self._walk(self.tender,KETTLE,seconds,player):self._stage('tea_pickup')
        elif stage == 'tea_pickup':
            self.mason.pose = 'work'; self.tender.pose = 'work' if self.timer<.5 else 'cup'
            if self.timer>1:self._stage('tea_across')
        elif stage == 'tea_across':
            if self._walk(self.tender,(-2336,584),seconds,player,'cup'):self._stage('tea_down')
        elif stage == 'tea_down':
            if self._walk(self.tender,(-2336,616),seconds,player,'cup'):self._stage('tea_side')
        elif stage == 'tea_side':
            if self._walk(self.tender,HELP,seconds,player,'cup'):self._stage('request')
        elif stage == 'request':self.mason.pose='work';self.tender.pose='cup'
        elif stage == 'wobble':
            self.mason.pose='work';self.tender.pose='offer'
            if self.timer>2:
                self._commit(game,tea_beat=2);self._stage('reach')
        elif stage == 'reach':
            self.mason.pose='receive';self.tender.pose='offer'
            if self.timer>2:
                self._commit(game,tea_beat=3);self._stage('exchange')
        elif stage == 'exchange':self.mason.pose='receive';self.tender.pose='offer'
        elif stage == 'sit_walk':
            if self._walk(self.mason,SEAT,seconds,player,'cup'):self._stage('sit')
        elif stage == 'sit':
            self.mason.pose='drink'
            if self._walk(self.tender,SOURCE,seconds,player):
                self.tender.pose='work'
                if self.timer>5:self._stage('tool_return')
        elif stage == 'tool_return':
            self.mason.pose='sit'
            if self._walk(self.tender,HELP,seconds,player):self._stage('stand')
        elif stage == 'stand':
            if self._walk(self.mason,SOURCE,seconds,player,'cup'):self._stage('cup_return')
        elif stage == 'cup_return':
            self.mason.pose='receive';self.tender.pose='offer'
            if self.timer>1:self._stage('tray_return')
        elif stage == 'tray_return':
            if self._walk(self.tender,(-2336,616),seconds,player,'cup'):self._stage('tray_up')
        elif stage == 'tray_up':
            if self._walk(self.tender,(-2336,584),seconds,player,'cup'):self._stage('tray_across')
        elif stage == 'tray_across':
            if self._walk(self.tender,KETTLE,seconds,player,'cup'):self._stage('tray_place')
        elif stage == 'tray_place':
            self.tender.pose = 'cup' if self.timer<.5 else 'work'
            if self.timer>1:
                self._commit(game,tea_beat=5);self._stage('ready')

    def nearby(self,game):
        actor=min(self.actors,key=lambda a:a.position.distance_squared_to(game.player.position))
        return actor if actor.position.distance_to(game.player.position)<=34 else None

    def interaction_hint(self,game):
        actor=self.nearby(game)
        return ('E: Share a quiet moment' if self.stage in ('request','exchange') else 'E: Speak with '+actor.data['name'].lower()) if actor else ''

    def interact(self,game):
        actor=self.nearby(game)
        if actor is None:return False
        if (self.stage=='ready' and self.state['tea_beat']==0
                and not HANDOFF.colliderect(self.world.probe_rect(game.player.position))):
            self._commit(game,tea_beat=1);self._stage('tea_home');return True
        if self.stage=='request':
            return self._script(game,[{'speaker':'bridge_tender','text':'Tea. You can spare a moment.'},
                {'speaker':'bridge_mason','text':'Leave it on that stone. Just this edge to check.'}],lambda:self._stage('wobble'))
        if self.stage=='exchange':
            def done():self._commit(game,tea_beat=4);self._stage('sit_walk')
            return self._script(game,[{'speaker':'bridge_mason','text':'You moved it.'},
                {'speaker':'bridge_tender','text':'The stone was moving it first.'}],done)
        role=actor.role
        text=('These sound pieces can be kept. The cracked ones stay separate. Nothing goes back into the span yet.' if role=='mason' else
              'We measure from this bank. There is still no safe crossing.')
        def done():
            if role not in self.state['greeted']:
                self.state['greeted'].append(role);game.save_progress()
        return game.social.start_script([{'speaker':'bridge_'+role,'text':text}],on_complete=done,identifier='bridge_crew_greeting')

    def ground_blockers(self,actor=None):
        # Stations sit north of the main road; hands reach over their small bases.
        blocks = [pygame.Rect(-2318,568,28,7), pygame.Rect(-2413,594,26,3),
                  pygame.Rect(-2435,631,38,3), pygame.Rect(-2372,602,24,4)]
        if actor not in self.actors and self.state['tea_beat'] in (1,2,3,4):blocks.append(HANDOFF)
        return blocks

    def props(self):
        result=[]
        def add(key,point,sort=None):
            image=self.art[key];x,y=point
            result.append((y if sort is None else sort,4,image,(round(x)-image.get_width()//2,round(y)-image.get_height())))
        add('tray',(-2304,577));add('kettle',(-2307,575));add('bench',(-2400,603),598)
        add('barrier',(-2416,634),634)
        add('keep_mark',(-2344,604));add('reject_mark',(-2312,604))
        for index in range(3):
            p=pygame.Vector2(SOURCE)+(index*3-3,-2)
            if index<self.state['sorted']:p=pygame.Vector2(REJECT)+(0,-2) if index==2 else pygame.Vector2(STACK)+(index*7-7,-2)
            elif index==self.state['sorted'] and self.stage in ('lift','carry','place'):
                p=self.mason.position+(0,-11 if self.stage=='carry' or self.stage=='lift' and self.timer>=.7 else -3)
            add('stone',p,p.y+18)
        # The shaky piece and steady tray remain visibly distinct.
        add('stone',(-2368+(1 if self.stage=='wobble' and int(self.timer*6)%2 else 0),609))
        add('tray',SAFE)
        stage=self.stage
        cup=pygame.Vector2(KETTLE)+(8,-11)
        if stage=='tea_pickup':cup=cup.lerp(self.tender.position+(-1,-11),min(1,self.timer))
        elif stage=='tray_place':cup=(self.tender.position+(-1,-11)).lerp(cup,min(1,self.timer))
        elif stage in ('tea_across','tea_down','tea_side','request'):cup=self.tender.position+(-1,-11)
        elif stage=='wobble':
            t=min(1,max(0,(self.timer-.8)/1.2))
            cup=(self.tender.position+(-1,-11)).lerp(pygame.Vector2(-2368,600),min(1,self.timer/.8)) if self.timer<.8 else pygame.Vector2(-2368,600).lerp(pygame.Vector2(SAFE)+(0,-7),t)
        elif stage=='reach':
            cup=(pygame.Vector2(SAFE)+(0,-7)).lerp(self.mason.position+(9,-11),min(1,self.timer/2))
        elif stage in ('exchange','sit_walk','sit','tool_return','stand','cup_return'):
            cup=self.mason.position+((0,-13) if stage=='sit' else (9,-11) if stage in ('exchange','cup_return') else (-1,-11))
        elif stage in ('tray_return','tray_up','tray_across'):cup=self.tender.position+(-1,-11)
        if stage=='cup_return':cup=(self.mason.position+(9,-11)).lerp(self.tender.position+(-1,-11),min(1,self.timer))
        add('cup',cup,cup.y+24)
        tool=self.tender if stage=='sit' and self.tender.position.distance_to(SOURCE)<.1 else self.mason
        point=tool.position+(9,-10) if tool.pose=='work' else pygame.Vector2(SOURCE)+(10,-3)
        add('tool',point,point.y+18)
        return result
