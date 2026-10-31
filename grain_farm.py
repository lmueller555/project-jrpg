"""Two region-owned workers and a finite, durable grain delivery.

Only completed physical beats persist. Continue reconstructs an interrupted
carry at storage; ordinary departure preserves the live controller in place.
No town actor, route graph, quest objective or streaming chunk owns this work.
"""
import json
import math
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
DIRECTIONS = ('front', 'back', 'left', 'right')
PICKUP_SECONDS = 1.2
PLACE_SECONDS = 1.2
PUSH_SECONDS = .6
LOWER_SECONDS = .8
RECOVER_SECONDS = .4
REQUIRED_CLIPS = {
    'loader': {'inspect_front', 'cover_front', 'lift_front', 'look_left',
               'place_right', 'push_right', 'work_right', 'stretch_front',
               'recover_front',
               *('hold_'+d for d in DIRECTIONS), *('carry_'+d for d in DIRECTIONS)},
    'coworker': {'work_left', 'assist_right', 'assist_low_right', 'recover_right', 'stretch_front'},
}


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
    """Registered full-body clips; pose changes never redraw individual limbs.

    The controller finalizes movement and facing before ``advance`` compares
    clip identities. A blocked walk therefore settles into its authored hold
    instead of repeatedly restarting a stride on transient ``moving`` writes.
    """
    def __init__(self, role, variant, position, *, asset_root=ART,
                 required_clips=None, identifier_prefix='grain', name=None):
        self.role = role
        self.data = {'id': identifier_prefix+'_'+role,
                     'name': name or ('Grain loader' if role == 'loader' else 'Grain worker')}
        self.scene_id = 'auratia.overworld'
        self.position = pygame.Vector2(position)
        self.probe_size = (10, 6)
        self.draw_anchor = (20, 38)
        self.facing = 'front'
        self.pose = 'idle'
        self.clock = 0
        self.moving = False
        self.reverse = False
        self.action_duration = None
        self._selection = None
        self.clips = {}
        for direction in DIRECTIONS:
            base=ROOT/f'assets/characters/npcs/{variant}'
            self.clips['idle_'+direction] = {'loop': False, 'frames': [
                {'image': self._padded(base/f'idle_{direction}.png'), 'duration_ms': 1000}]}
            self.clips['walk_'+direction] = {'loop': True, 'frames': [
                {'image': self._padded(base/f'walk_{direction}/frame_{i:02}.png'), 'duration_ms': 140}
                for i in range(1, 5)]}
        manifest_path = Path(asset_root)/role/'animation.json'
        data = json.loads(manifest_path.read_text())
        required = REQUIRED_CLIPS[role] if required_clips is None else required_clips
        if (data.get('version') != 1 or data.get('canvas') != [40, 44]
                or data.get('anchor') != [20, 38]
                or not required <= set(data.get('sequences', {}))):
            raise ValueError('Incomplete grain-worker animation manifest: '+role)
        for key, clip in data['sequences'].items():
            if type(clip.get('loop')) is not bool or not clip.get('frames'):
                raise ValueError('Invalid grain-worker clip: '+key)
            frames = []
            for metadata in clip['frames']:
                duration = metadata.get('duration_ms')
                if (type(duration) not in (int, float) or not math.isfinite(duration)
                        or duration <= 0):raise ValueError('Invalid grain-worker frame duration')
                path = (manifest_path.parent/metadata['file']).resolve()
                if not path.is_relative_to(manifest_path.parent.resolve()):
                    raise ValueError('Grain-worker frame leaves its asset directory')
                image = pygame.image.load(str(path)).convert_alpha()
                if image.get_size() != (40, 44):
                    raise ValueError('Incorrect grain-worker frame dimensions')
                for point in [metadata.get(key) for key in
                              ('sack_offset', 'cloth_offset', 'stone_offset', 'cup_offset', 'tool_offset')]+[
                              *metadata.get('hands', [])]:
                    if point is not None and (len(point) != 2 or any(
                            type(n) not in (int, float) or not math.isfinite(n) for n in point)):
                        raise ValueError('Invalid grain-worker attachment')
                if any(metadata.get(key, 'front') not in ('front', 'back')
                       for key in ('sack_layer', 'stone_layer', 'cup_layer')):
                    raise ValueError('Invalid worker attachment layer')
                frames.append({**metadata, 'image': image})
            self.clips[key] = {**clip, 'frames': frames}

    @staticmethod
    def _padded(path):
        canvas=pygame.Surface((40,44),pygame.SRCALPHA)
        canvas.blit(pygame.image.load(str(path)).convert_alpha(),(8,4))
        return canvas

    @property
    def blocker(self):
        return pygame.Rect(round(self.position.x)-5, round(self.position.y)-3,10,6)

    @property
    def animation_key(self):
        if self.pose == 'idle':return ('walk_' if self.moving else 'idle_')+self.facing
        if self.pose == 'carry':return ('carry_' if self.moving else 'hold_')+self.facing
        return {'inspect': 'inspect_front', 'cover': 'cover_front',
                'lift': 'lift_front', 'lower': 'lift_front', 'look': 'look_left',
                'place': 'place_right', 'push': 'push_right',
                'recover': 'recover_front' if self.role == 'loader' else 'recover_right',
                'work': 'work_'+self.facing, 'assist': 'assist_right',
                'assist_low': 'assist_low_right', 'stretch': 'stretch_front'}[self.pose]

    def restart(self):
        self.clock = 0.
        self._selection = None

    def advance(self, seconds):
        selection = (self.animation_key, self.reverse, self.action_duration)
        if selection != self._selection:
            self.clock = 0.
            self._selection = selection
        elif self.animation_key.startswith(('hold_', 'cup_hold_')):
            self.clock = 0.
        else:self.clock += max(0., seconds)

    @property
    def frame_index(self):
        clip = self.clips[self.animation_key]
        indices = list(range(len(clip['frames'])))
        if self.reverse:indices.reverse()
        total = sum(frame['duration_ms'] for frame in clip['frames'])/1000
        time = (self.clock/self.action_duration*total
                if self.action_duration is not None else self.clock)
        if clip['loop'] and self.action_duration is None:time %= total
        for index in indices:
            duration = clip['frames'][index]['duration_ms']/1000
            if time < duration:return index
            time -= duration
        return indices[-1]

    @property
    def attachment(self):
        return {key: value for key, value in self.clips[self.animation_key]['frames'][self.frame_index].items()
                if key != 'image'}

    @property
    def hand_positions(self):
        return [self.position+point for point in self.attachment.get('hands', [])]

    def sprite(self, elapsed_ms):
        return self.clips[self.animation_key]['frames'][self.frame_index]['image']


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
        self._audio_contacts=set()
        self.stage='inspect'
        self.timer=0
        self.dialogue_running=False
        self.coworker_stop=0
        self.coworker_timer=0
        if self.state['scene_done']:self.stage='rest'
        elif self.state['exchange_read']:self.stage='help_approach'
        self._prepare_stage_pose()
        for actor in self.actors:actor.advance(0)

    def to_dict(self):
        return {**self.state,'greeted':list(self.state['greeted'])}

    def _stage(self, name):
        self.stage=name;self.timer=0
        self._audio_contacts.clear()
        self.loader.moving=False
        self.loader.restart()
        if name in ('help_place', 'help_recover'):self.coworker.restart()
        self._prepare_stage_pose()

    @staticmethod
    def _act(actor, pose, facing=None, *, duration=None, reverse=False):
        actor.pose = pose
        actor.reverse = reverse
        actor.action_duration = duration
        if facing is not None:actor.facing = facing

    def _prepare_stage_pose(self):
        """Enter a physical beat with its first pose, not a one-frame idle pop."""
        stage = self.stage
        if stage == 'inspect':self._act(self.loader, 'inspect', 'front')
        elif stage in ('cover', 'uncover'):
            self._act(self.loader, 'cover', 'front', duration=1., reverse=stage == 'uncover')
        elif stage in ('lift', 'lift_spare'):
            self._act(self.loader, 'lift', 'front', duration=PICKUP_SECONDS)
        elif stage in ('carry', 'ready', 'help_approach', 'help_place'):
            self._act(self.loader, 'carry', 'front')
            if stage == 'help_place':self._act(self.coworker, 'assist', 'right')
        elif stage == 'place':self._act(self.loader, 'place', 'right', duration=PLACE_SECONDS)
        elif stage == 'help_recover':
            self._act(self.loader, 'recover', 'front', duration=RECOVER_SECONDS)
            self._act(self.coworker, 'recover', 'right', duration=RECOVER_SECONDS)
        elif stage in ('check', 'quiet_work'):self._act(self.loader, 'work', 'right')
        elif stage == 'rest':self._act(self.loader, 'stretch', 'front')
        else:self._act(self.loader, 'idle', 'back' if stage == 'return' else 'front')

    def _walk(self, actor, target, seconds, player, carrying=False):
        delta=pygame.Vector2(target)-actor.position
        if delta.length()<.1:return True
        actor.facing=('right' if delta.x>0 else 'left') if abs(delta.x)>abs(delta.y) else ('front' if delta.y>0 else 'back')
        self._act(actor, 'carry' if carrying else 'idle')
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

    def _sound(self, game, key, name, actor):
        audio=getattr(game,'regional_audio',None)
        if audio:audio.emit('farm_'+key,name,lambda:actor.position,'farm')

    @staticmethod
    def _contact_frame(actor, tool=False):
        """The painted hand/tool's contact extreme, independent of clip rate."""
        frames=actor.clips[actor.animation_key]['frames']
        def score(frame):
            hands=frame.get('hands',[])
            reach=max(((-p[0] if actor.facing=='left' else p[0]) for p in hands),default=0)
            if tool:
                return (frame.get('tool_offset',(0,-1000))[1],
                        max((p[1] for p in hands),default=-1000))
            return reach
        return max(range(len(frames)),key=lambda index:score(frames[index]))

    def _sync_audio(self, game, previous_frames):
        """Emit from the sampled physical contact, never the legacy .6s beat."""
        loader=self.loader;frame=loader.attachment
        key=(loader.animation_key,loader.frame_index)
        entered=previous_frames[loader]!=key
        if self.stage in ('lift','lift_spare') and frame.get('gripped') is True:
            if 'cloth' not in self._audio_contacts:
                self._sound(game,'cloth','rustle',loader);self._audio_contacts.add('cloth')
        elif self.stage in ('cover','uncover'):
            contact=0 if self.stage=='uncover' else len(loader.clips['cover_front']['frames'])-1
            if loader.frame_index==contact and 'cloth' not in self._audio_contacts:
                self._sound(game,'cloth','rustle',loader);self._audio_contacts.add('cloth')
        if (self.stage=='place' and frame.get('sack_offset')==[14,-10]
                and 'place' not in self._audio_contacts):
            self._sound(game,'place','sack',loader);self._audio_contacts.add('place')
        if (self.stage=='help_place' and loader.pose=='lower' and frame.get('gripped') is False
                and 'extra_place' not in self._audio_contacts):
            self._sound(game,'extra_place','sack',loader);self._audio_contacts.add('extra_place')
        for actor in self.actors:
            current=(actor.animation_key,actor.frame_index)
            if (actor.pose=='work' and current!=previous_frames[actor]
                    and actor.frame_index==self._contact_frame(actor)):
                self._sound(game,'lash','creak',actor)

    def _coworker_work(self, seconds, player):
        """Walk around the south of the parked cart, clear of the loading lane."""
        actor=self.coworker
        if self.coworker_stop==6:
            self._act(actor, 'stretch', 'front');self.coworker_timer+=seconds
            if self.coworker_timer>=3:
                self.coworker_stop=0;self.coworker_timer=0
            return
        target=COWORKER_ROUTE[self.coworker_stop]
        if self._walk(actor,target,seconds,player):
            if self.coworker_stop==2:
                self._act(actor, 'work', 'left');self.coworker_timer+=seconds
                if self.coworker_timer<3:return
            self.coworker_stop+=1;self.coworker_timer=0

    def update(self, seconds, game):
        if game.player.position.distance_to(SOURCE)>260:return
        if game.social.locked:
            for actor in self.actors:actor.moving=False
            if game.social.script_identifier==SCENE_ID:
                page=game.social.page
                self._act(self.loader, 'look' if page and page.get('cue')=='axle' else 'carry', 'front')
            # The held load stays owned by its carrier. A small authored look
            # can settle while prose is read; work and movement clocks do not.
            for actor in self.actors:
                actor.advance(min(max(seconds, 0.), .1) if actor.pose == 'look' else 0)
            return
        if self.dialogue_running:
            # Walking away cancels prose without committing its completion.
            self.dialogue_running=False
            self._stage('ready')
        previous_frames={actor:(actor.animation_key,actor.frame_index) for actor in self.actors}
        seconds=min(seconds,.1)
        self.timer+=seconds
        for actor in self.actors:actor.moving=False
        player=self.world.probe_rect(game.player.position)
        loaded=self.state['loaded']
        if self.stage not in ('ready','help_approach','help_place','help_recover','help_return','check_walk','check'):
            self._coworker_work(seconds,player)
        elif self.stage=='ready' and self.coworker_stop!=6:
            self._coworker_work(seconds,player)
        if self.stage=='inspect':
            self._act(self.loader, 'inspect', 'front')
            if self.timer>=2:
                self._stage(('uncover' if self.covered else 'lift') if MILL_FLAG in game.social.flags and loaded<2 else
                            'lift_spare' if MILL_FLAG in game.social.flags and not self.state['scene_done'] else 'cover')
        elif self.stage=='cover':
            self._act(self.loader, 'cover', 'front', duration=1.)
            if self.timer>=1:
                self.covered=True;self._stage('rest')
        elif self.stage=='uncover':
            self._act(self.loader, 'cover', 'front', duration=1., reverse=True)
            if self.timer>=1:
                self.covered=False;self._stage('lift')
        elif self.stage in ('lift', 'lift_spare'):
            self._act(self.loader, 'lift', 'front', duration=PICKUP_SECONDS)
            if self.timer>=PICKUP_SECONDS:
                self._stage('ready' if self.stage == 'lift_spare' else 'carry')
        elif self.stage=='carry':
            if self._walk(self.loader,CART,seconds,player,True):self._stage('place')
        elif self.stage=='place':
            if loaded == 1 and self.timer >= PLACE_SECONDS:
                self._act(self.loader, 'push', 'right', duration=PUSH_SECONDS)
            else:self._act(self.loader, 'place', 'right', duration=PLACE_SECONDS)
            # The second sack is set on the bed before a short supported
            # slide. Its final slot is beyond a safe two-handed carry reach.
            if self.timer >= PLACE_SECONDS+(PUSH_SECONDS if loaded == 1 else 0):
                self._commit(game,loaded=loaded+1)
                self._stage('return')
        elif self.stage=='return':
            if self._walk(self.loader,SOURCE,seconds,player):self._stage('inspect')
        elif self.stage=='ready':
            self._act(self.loader, 'carry', 'front')
            if self.coworker_stop==6:self._act(self.coworker, 'idle', 'back')
            # The extra sack stays in the loader's grip until explicitly engaged.
        elif self.stage=='help_approach':
            self._act(self.loader, 'carry', 'front')
            if self._walk(self.coworker,HELP,seconds,player):self._stage('help_place')
        elif self.stage=='help_place':
            if self.timer < .8:
                self._act(self.loader, 'carry', 'front')
                self._act(self.coworker, 'assist', 'right')
            else:
                self._act(self.loader, 'lower', 'front', duration=LOWER_SECONDS, reverse=True)
                self._act(self.coworker, 'assist_low', 'right', duration=LOWER_SECONDS)
            if self.timer>=.8+LOWER_SECONDS:self._stage('help_recover')
        elif self.stage=='help_recover':
            self._act(self.loader, 'recover', 'front', duration=RECOVER_SECONDS)
            self._act(self.coworker, 'recover', 'right', duration=RECOVER_SECONDS)
            if self.timer>=RECOVER_SECONDS:self._stage('help_return')
        elif self.stage=='help_return':
            if self._walk(self.coworker,REST,seconds,player):
                self.coworker_stop=6;self.coworker_timer=0;self._stage('check_walk')
        elif self.stage=='check_walk':
            if self._walk(self.loader,CART,seconds,player):self._stage('check')
        elif self.stage=='check':
            self._act(self.loader, 'work', 'right')
            if self.timer>=2:
                self._commit(game,scene_done=True)
                self._stage('rest')
        elif self.stage=='rest':
            self._act(self.loader, 'stretch' if self.timer<2 else 'idle', 'front')

            if self.timer>=5:
                if loaded<2 and MILL_FLAG in game.social.flags:self._stage('return')
                elif self.state['scene_done']:self._stage('quiet_check')
                else:self._stage('inspect')
        elif self.stage=='quiet_check':
            if self._walk(self.loader,CART,seconds,player):
                self._stage('quiet_work')
        elif self.stage=='quiet_work':
            self._act(self.loader, 'work', 'right')
            if self.timer>=2:self._stage('rest')
        for actor in self.actors:actor.advance(seconds)
        self._sync_audio(game,previous_frames)

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
        if self.stage in ('cover', 'uncover'):
            metadata = self.loader.attachment
            offset = metadata.get('cloth_offset')
            if offset is None:
                hands = metadata.get('hands', [])
                offset = (sum(p[0] for p in hands)/len(hands),
                          sum(p[1] for p in hands)/len(hands)) if hands else (0, -14)
            point = self.loader.position+offset
            return [(self.loader.position.y+8,5,self.cover,
                     (round(point.x)-9,round(point.y)-4))]
        if not self.covered:return []
        final = self.loader.clips['cover_front']['frames'][-1]
        offset = final.get('cloth_offset', (0, -14))
        point = pygame.Vector2(SOURCE)+offset
        return [(SOURCE[1]+8,5,self.cover,(round(point.x)-9,round(point.y)-4))]

    def props(self):
        """Exactly three sack records, each with one current owner/location."""
        result=[]
        loaded=self.state['loaded']
        for index in range(2,-1,-1):
            point=pygame.Vector2(SOURCE)+(0,-7+index*2)
            sort_y=SOURCE[1]+7
            if index<loaded:
                point=pygame.Vector2(-810+index*6,208-index*2);sort_y=228
            elif ((index==loaded and loaded<2 and self.stage in ('lift','carry','place')) or
                  (index==2 and not self.state['scene_done'] and
                   self.stage in ('lift_spare','ready','help_approach','help_place'))):
                metadata = self.loader.attachment
                offset = metadata.get('sack_offset')
                gripped = metadata.get('gripped', metadata.get('sack_gripped', True))
                # A placed sack stays on the bed after the hands release;
                # only pickup/lowering reach frames defer to the ground pile.
                if offset is not None and (gripped or self.stage == 'place'):
                    point=self.loader.position+offset
                    sort_y=self.loader.position.y+(5 if metadata.get('sack_layer') == 'back' else 7)
            result.append((sort_y,4,self.sack,(round(point.x)-6,round(point.y)-10)))
        return result
