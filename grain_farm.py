"""Two region-owned workers and a finite, durable grain delivery.

Only completed physical beats persist. Continue reconstructs an interrupted
carry at storage; ordinary departure preserves the live controller in place.
No town actor, route graph, quest objective or streaming chunk owns this work.
"""
from pathlib import Path
import pygame

ROOT = Path(__file__).resolve().parent
ART = ROOT/'assets/characters/grain_workers'
MILL_FLAG = 'CH01_MQ02_MILL_RESTORED'
SOURCE = (-824, 192)
CART = (-824, 218)
REST = (-852, 220)
HELP = (-840, 192)
COWORKER_ROUTE = [(-852,244),(-788,244),(-788,218),(-788,244),(-852,244),REST]
SCENE_ID = 'grain_farm_extra_sack'
LINES = [
    ('loader', 'One more will fit.'),
    ('coworker', 'On the cart, yes.'),
    ('loader', 'Where else would I put it?'),
    ('coworker', 'I was thinking about the axle.'),
    ('loader', 'You could have mentioned that before I picked it up.'),
    ('coworker', 'I did. You were explaining how much would fit.'),
]


def empty_state():
    return {'loaded': 0, 'exchange_read': False, 'scene_done': False, 'greeted': []}


def valid_state(data):
    return (isinstance(data, dict) and set(data) == set(empty_state())
            and type(data['loaded']) is int and 0 <= data['loaded'] <= 2
            and type(data['exchange_read']) is bool and type(data['scene_done']) is bool
            and (not data['scene_done'] or data['exchange_read'])
            and (not data['exchange_read'] or data['loaded'] == 2)
            and isinstance(data['greeted'], list)
            and all(isinstance(role,str) and role in ('loader', 'coworker') for role in data['greeted'])
            and len(data['greeted']) == len(set(data['greeted'])))


class FarmWorker:
    def __init__(self, role, variant, position):
        self.role = role
        self.data = {'id': 'grain_'+role, 'name': 'Grain loader' if role == 'loader' else 'Grain worker'}
        self.scene_id = 'auratia.overworld'
        self.position = pygame.Vector2(position)
        self.probe_size = (10, 6)
        self.draw_anchor = (20, 38)
        self.facing = 'front'
        self.pose = 'idle'
        self.clock = 0
        self.moving = False
        self.frames = {}
        for direction in ('front','back','left','right'):
            base=ROOT/f'assets/characters/npcs/{variant}'
            self.frames['idle_'+direction]=[self._padded(base/f'idle_{direction}.png')]
            self.frames['walk_'+direction]=[self._padded(base/f'walk_{direction}/frame_{i:02}.png') for i in range(1,5)]
        for pose in ('lift','carry','look','cover','place','work','assist','assist_low','stretch'):
            self.frames[pose]=[pygame.image.load(str(ART/f'{role}_{pose}_{i}.png')).convert_alpha()
                               for i in range(4 if pose=='carry' else 2)]

    @staticmethod
    def _padded(path):
        canvas=pygame.Surface((40,44),pygame.SRCALPHA)
        canvas.blit(pygame.image.load(str(path)).convert_alpha(),(8,4))
        return canvas

    @property
    def blocker(self):
        return pygame.Rect(round(self.position.x)-5, round(self.position.y)-3,10,6)

    def sprite(self, elapsed_ms):
        key=self.pose.removesuffix('_left') if self.pose!='idle' else ('walk_' if self.moving else 'idle_')+self.facing
        frames=self.frames[key]
        index=int(self.clock/(.14 if self.moving else .6))%len(frames)
        if self.pose=='carry' and not self.moving:index=0
        image=frames[index]
        return pygame.transform.flip(image,True,False) if (self.pose=='work' and self.facing=='left') or self.pose.endswith('_left') else image


class GrainFarm:
    def __init__(self, world):
        self.world=world
        self.loader=FarmWorker('loader','male_02',SOURCE)
        self.coworker=FarmWorker('coworker','male_03',REST)
        self.actors=[self.loader,self.coworker]
        self.sack=pygame.image.load(str(ART/'sack.png')).convert_alpha()
        self.cover=pygame.image.load(str(ART/'cover.png')).convert_alpha()
        self.restore()

    def restore(self, data=None):
        self.state={**empty_state(), **(data or {})}
        self.state['greeted']=list(self.state['greeted'])
        self.loader.position.update(SOURCE)
        self.coworker.position.update(REST)
        for actor in self.actors:
            actor.clock=0;actor.pose='idle';actor.moving=False;actor.facing='front'
        self.covered=False
        self.stage='inspect'
        self.timer=0
        self.dialogue_running=False
        self.coworker_stop=0
        self.coworker_timer=0
        if self.state['scene_done']:self.stage='rest'
        elif self.state['exchange_read']:self.stage='help_approach'

    def to_dict(self):
        return {**self.state,'greeted':list(self.state['greeted'])}

    def _stage(self, name):
        self.stage=name;self.timer=0
        self.loader.moving=False;self.loader.pose='idle'

    def _walk(self, actor, target, seconds, player, carrying=False):
        delta=pygame.Vector2(target)-actor.position
        if delta.length()<.1:return True
        actor.facing=('right' if delta.x>0 else 'left') if abs(delta.x)>abs(delta.y) else ('front' if delta.y>0 else 'back')
        actor.pose='carry' if carrying else 'idle'
        actor.moving=False
        # Short substeps keep a large frame from crossing a foot or solid prop.
        remaining=min(delta.length(),22*seconds)
        while remaining>0:
            step=min(1,remaining)
            point=actor.position+delta.normalize()*step
            if not self.world.can_stand(point,actor.probe_size,actor,player):return False
            actor.position.update(point);remaining-=step;actor.moving=True
        return actor.position.distance_to(target)<.1

    def _commit(self, game, **changes):
        self.state.update(changes)
        game.save_progress()

    def _coworker_work(self, seconds, player):
        """Walk around the south of the parked cart, clear of the loading lane."""
        actor=self.coworker
        if self.coworker_stop==6:
            actor.pose='stretch';self.coworker_timer+=seconds
            if self.coworker_timer>=3:
                self.coworker_stop=0;self.coworker_timer=0
            return
        target=COWORKER_ROUTE[self.coworker_stop]
        if self._walk(actor,target,seconds,player):
            if self.coworker_stop==2:
                actor.facing='left';actor.pose='work';self.coworker_timer+=seconds
                if self.coworker_timer<3:return
            self.coworker_stop+=1;self.coworker_timer=0

    def update(self, seconds, game):
        if game.player.position.distance_to(SOURCE)>260:return
        if game.social.locked:
            if game.social.script_identifier==SCENE_ID:
                page=game.social.page
                self.loader.pose='look' if page and page.get('cue')=='axle' else 'carry'
            return
        if self.dialogue_running:
            # Walking away cancels prose without committing its completion.
            self.dialogue_running=False
            self._stage('ready')
        seconds=min(seconds,.1)
        self.timer+=seconds
        for actor in self.actors:actor.clock+=seconds;actor.moving=False
        player=self.world.probe_rect(game.player.position)
        loaded=self.state['loaded']
        if self.stage not in ('ready','help_approach','help_place','help_return','check_walk','check'):
            self._coworker_work(seconds,player)
        elif self.stage=='ready' and self.coworker_stop!=6:
            self._coworker_work(seconds,player)
        if self.stage=='inspect':
            self.loader.pose='lift'
            if self.timer>=2:
                self._stage(('uncover' if self.covered else 'lift') if MILL_FLAG in game.social.flags and loaded<2 else
                            'ready' if MILL_FLAG in game.social.flags and not self.state['scene_done'] else 'cover')
        elif self.stage=='cover':
            self.loader.pose='cover'
            if self.timer>=1:
                self.covered=True;self._stage('rest')
        elif self.stage=='uncover':
            self.loader.pose='cover'
            if self.timer>=1:
                self.covered=False;self._stage('lift')
        elif self.stage=='lift':
            self.loader.pose='lift' if self.timer<.6 else 'carry'
            if self.timer>=1.2:self._stage('carry')
        elif self.stage=='carry':
            if self._walk(self.loader,CART,seconds,player,True):self._stage('place')
        elif self.stage=='place':
            self.loader.pose='place'
            if self.timer>=1.2:
                self._commit(game,loaded=loaded+1)
                self._stage('return')
        elif self.stage=='return':
            if self._walk(self.loader,SOURCE,seconds,player):self._stage('inspect')
        elif self.stage=='ready':
            self.loader.pose='carry'
            if self.coworker_stop==6:self.coworker.facing='back';self.coworker.pose='idle'
            # The extra sack stays in the loader's grip until explicitly engaged.
        elif self.stage=='help_approach':
            self.loader.pose='carry'
            if self._walk(self.coworker,HELP,seconds,player):self._stage('help_place')
        elif self.stage=='help_place':
            pose='assist' if self.timer<.8 else 'assist_low'
            self.loader.pose='carry' if self.timer<.8 else 'lift';self.coworker.pose=pose
            if self.timer>=1.6:self._stage('help_return')
        elif self.stage=='help_return':
            if self._walk(self.coworker,REST,seconds,player):
                self.coworker_stop=6;self.coworker_timer=0;self._stage('check_walk')
        elif self.stage=='check_walk':
            if self._walk(self.loader,CART,seconds,player):self._stage('check')
        elif self.stage=='check':
            self.loader.pose='work'
            if self.timer>=2:
                self._commit(game,scene_done=True)
                self._stage('rest')
        elif self.stage=='rest':
            self.loader.pose='stretch' if self.timer<2 else 'idle'

            if self.timer>=5:
                if loaded<2 and MILL_FLAG in game.social.flags:self._stage('return')
                elif self.state['scene_done']:self._stage('quiet_check')
                else:self._stage('inspect')
        elif self.stage=='quiet_check':
            if self._walk(self.loader,CART,seconds,player):
                self.loader.pose='work'
                if self.timer>=5:self._stage('rest')

    def nearby(self, game):
        actor=min(self.actors,key=lambda a:a.position.distance_squared_to(game.player.position))
        return actor if actor.position.distance_to(game.player.position)<=34 else None

    def interaction_hint(self, game):
        actor=self.nearby(game)
        return 'E: Speak with '+actor.data['name'].lower() if actor else ''

    def interact(self, game):
        actor=self.nearby(game)
        if actor is None:return False
        if self.stage=='ready' and self.coworker_stop==6 and MILL_FLAG in game.social.flags:
            lines=[{'speaker':'grain_'+role,'text':text,**({'cue':'axle'} if i==3 else {})}
                   for i,(role,text) in enumerate(LINES)]
            def completed():
                self.dialogue_running=False
                self._commit(game,exchange_read=True)
                self._stage('help_approach')
            started=game.social.start_script(lines,on_complete=completed,identifier=SCENE_ID)
            self.dialogue_running=started
            return started
        role=actor.role
        greeting=('Mind the grain underfoot. We have enough sweeping to do.' if role=='loader' else
                  'Good day. There is room to pass on the house side.')
        text=("We're keeping this grain dry until Halden's mill is running again." if MILL_FLAG not in game.social.flags else
              'Hear that? The mill is running again. Time to get this grain ready.' if self.state['loaded']<2 else
              'Two sacks, sound lashings. This load can wait here until the carter comes.')
        lines=([{'speaker':'grain_'+role,'text':greeting}] if role not in self.state['greeted'] else [])
        lines.append({'speaker':'grain_'+role,'text':text})
        def completed():
            if role not in self.state['greeted']:
                self.state['greeted'].append(role);game.save_progress()
        return game.social.start_script(lines,on_complete=completed,identifier='grain_farm_greeting')

    def ground_blockers(self, actor=None):
        if actor in self.actors:return []
        if self.state['loaded']==2 and self.stage in ('ready','help_approach','help_place'):
            return []
        # Match the sack's ground contact, not a padded rectangle spanning the
        # whole station: that padding would obstruct the barn's approach road.
        return [pygame.Rect(SOURCE[0]-6,SOURCE[1]-6,12,4)]

    def cover_props(self):
        return [(SOURCE[1]+8,5,self.cover,(SOURCE[0]-9,SOURCE[1]-14))] if self.covered else []

    def props(self):
        """Exactly three sack records, each with one current owner/location."""
        result=[]
        loaded=self.state['loaded']
        for index in range(2,-1,-1):
            point=pygame.Vector2(SOURCE)+(0,-7+index*2)
            sort_y=SOURCE[1]+7
            if index<loaded:
                point=pygame.Vector2(-810+index*6,208-index*2);sort_y=228
            elif index==loaded and loaded<2 and self.stage in ('lift','carry','place'):
                offset=(0,-3) if self.stage=='lift' and self.timer<.6 else (10,-9) if self.stage=='place' else (0,-11)
                point=self.loader.position+offset;sort_y=self.loader.position.y+7
            elif index==2 and not self.state['scene_done'] and self.stage in ('ready','help_approach','help_place'):
                offset=(0,-11 if self.timer<.8 else -3) if self.stage=='help_place' else (0,-11)
                point=self.loader.position+offset;sort_y=self.loader.position.y+7
            result.append((sort_y,4,self.sack,(round(point.x)-6,round(point.y)-10)))
        return result
