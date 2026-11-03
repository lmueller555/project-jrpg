"""Finite masonry sorting and an opt-in tea break at the near bank.

Regional actors and props belong to this controller, never streamed chunks.
Completed placements and tea beats persist; interrupted carries restart at the
last safe station. The ruined crossing and all story flags are read-only.
"""
from pathlib import Path
import pygame
from grain_farm import FarmWorker, GrainFarm, DIRECTIONS, held_prop_sort

ROOT = Path(__file__).resolve().parent
ART = ROOT/'assets/characters/bridge_workers'
SOURCE = (-2376, 616)
STACK = (-2344, 616)
REJECT = (-2312, 616)
KETTLE = (-2304, 584)
HELP = (-2356, 616)
SEAT = (-2400, 600)
BARRIER = (-2400, 616)
SAFE = (-2363, 610)
REACH = (-2372, 616)
WORK_STONE = (-2368, 609)
TOOL_REST = (-2366, 601)
SCENE_ID = 'bridge_crew_tea'
HANDOFF = pygame.Rect(-2387, 600, 40, 22)
CUP_ACTION_SECONDS = 1.


def empty_state():
    return {'sorted': 0, 'tea_beat': 0, 'request_read': False, 'greeted': [],
            'cup_phase': 'kettle'}


def legacy_cup_phase(data):
    beat=data.get('tea_beat',0)
    if beat == 2:return 'tray'
    if beat in (3,4):return 'mason'
    return 'tender' if beat == 1 and data.get('request_read',False) else 'kettle'


def valid_state(data):
    return (isinstance(data, dict) and {'sorted','tea_beat','greeted'} <= set(data) <= set(empty_state())
            and type(data['sorted']) is int and 0 <= data['sorted'] <= 3
            and type(data['tea_beat']) is int and 0 <= data['tea_beat'] <= 5
            and (not data['tea_beat'] or data['sorted'] == 3)
            and type(data.get('request_read', False)) is bool
            and (not data.get('request_read', False) or data['tea_beat'] >= 1)
            and ('request_read' not in data or data['tea_beat'] < 2 or data['request_read'])
            and isinstance(data.get('cup_phase',legacy_cup_phase(data)),str)
            and data.get('cup_phase',legacy_cup_phase(data)) in {
                0:('kettle',),1:('kettle','tender','stone','tender_from_stone'),
                2:('tray',),3:('mason',),4:('mason','tender_return'),5:('kettle',)
            }[data['tea_beat']]
            and (data.get('cup_phase') not in ('stone','tender_from_stone') or data.get('request_read',False))
            and isinstance(data['greeted'], list)
            and all(isinstance(x, str) and x in ('mason', 'tender') for x in data['greeted'])
            and len(data['greeted']) == len(set(data['greeted'])))


class BridgeWorker(FarmWorker):
    """The shared full-body player plus role-specific stone/cup actions."""
    REQUIRED = {
        'mason': {'inspect_front','lift_front','recover_front','place_front',
                  'work_right','measure_left','measure_right','stretch_front',
                  'receive_right','offer_right','sit_down_front','sit_front',
                  'drink_front','stand_front',
                  *('hold_'+d for d in DIRECTIONS), *('carry_'+d for d in DIRECTIONS),
                  *('cup_hold_'+d for d in DIRECTIONS), *('cup_'+d for d in DIRECTIONS)},
        'tender': {'pickup_right','offer_left','receive_left','measure_left',
                   'measure_right','work_right','stretch_front',
                   *('cup_hold_'+d for d in DIRECTIONS), *('cup_'+d for d in DIRECTIONS)},
    }

    def __init__(self, role, variant, position):
        super().__init__(role, variant, position, asset_root=ART,
                         required_clips=self.REQUIRED[role], identifier_prefix='bridge',
                         name='Bridge mason' if role == 'mason' else 'Bridge surveyor')
        if role == 'tender':
            frames=self.clips['offer_left']['frames']
            for name,subset in (('set_stone',frames[:2]),('take_stone',frames[1:3]),
                                ('set_tray',frames[2:])):
                self.clips[name]={'loop':False,'frames':subset}

    @property
    def animation_key(self):
        if self.pose == 'idle':return ('walk_' if self.moving else 'idle_')+self.facing
        if self.pose == 'carry':return ('carry_' if self.moving else 'hold_')+self.facing
        if self.pose == 'cup':return ('cup_' if self.moving else 'cup_hold_')+self.facing
        if self.pose in ('work','measure'):return self.pose+'_'+self.facing
        if self.pose in ('offer','receive'):
            return self.pose+('_right' if self.role == 'mason' else '_left')
        if self.pose in ('set_stone','take_stone','set_tray'):return self.pose
        return {'inspect':'inspect_front','lift':'lift_front','recover':'recover_front',
                'place':'place_front','stretch':'stretch_front','pickup':'pickup_right',
                'sit_down':'sit_down_front','sit':'sit_front','drink':'drink_front',
                'stand_up':'stand_front'}[self.pose]


class BridgeCrew:
    _act = staticmethod(GrainFarm._act)
    AMBIENT = frozenset(('inspect','lift','carry','place','stone_recover','return',
                         'ready','barrier','barrier_look','barrier_return'))

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
        if data and 'cup_phase' not in data:self.state['cup_phase']=legacy_cup_phase(data)
        self.state['greeted'] = list(self.state['greeted'])
        if data and 'request_read' not in data:self.state['request_read'] = data['tea_beat'] >= 2
        self.mason.position.update(SOURCE);self.tender.position.update(KETTLE)
        for actor in self.actors:
            actor.restart();actor.pose='idle';actor.facing='front';actor.moving=False
            actor.reverse=False;actor.action_duration=None
        self.timer=0.;self.route=0;self.work_timer=0.
        beat=self.state['tea_beat']
        self.stage='inspect' if self.state['sorted']<3 else 'ready'
        if beat == 1:
            phase=self.state['cup_phase']
            if phase == 'kettle':self.stage='tea_pickup'
            else:
                self.tender.position.update(HELP)
                self.stage=({'stone':'stone_wait','tender_from_stone':'tray_setdown'}.get(phase)
                            or ('wobble' if self.state['request_read'] else 'request'))
        elif beat in (2,3,4):
            self.tender.position.update(HELP)
            self.stage={2:'reach',3:'exchange',4:'sit_walk'}[beat]
            if beat in (2,3):self.mason.position.update(REACH)
            elif self.state['cup_phase']=='tender_return':self.stage='tray_return'
        self.dialogue_running=False
        self._audio_contacts=set()
        self._prepare_stage_pose()
        for actor in self.actors:actor.advance(0)

    def to_dict(self):return {**self.state,'greeted':list(self.state['greeted'])}

    def _stage(self, stage):
        self.stage=stage;self.timer=0.
        self._audio_contacts.clear()
        self.mason.moving=False
        # Sorting is the mason's beat. The surveyor's independent walk must
        # not briefly become an idle every time a stone changes ownership.
        if stage not in self.AMBIENT:self.tender.moving=False
        self._prepare_stage_pose()

    def _prepare_stage_pose(self):
        stage=self.stage
        if stage in self.AMBIENT:
            pose={'inspect':'inspect','lift':'lift','carry':'carry','place':'place',
                  'stone_recover':'recover','return':'idle','ready':'stretch',
                  'barrier':'idle','barrier_look':'measure','barrier_return':'idle'}[stage]
            facing=('right' if stage in ('carry','barrier_return') else
                    'left' if stage in ('return','barrier','barrier_look') else 'front')
            duration={'lift':1.4,'place':1.2,'stone_recover':.4}.get(stage)
            self._act(self.mason,pose,facing,duration=duration)
            return
        self._act(self.mason,'work','right')
        if stage == 'tea_home':self._act(self.tender,'idle')
        elif stage in ('tea_pickup','tray_place'):
            self._act(self.tender,'pickup','right',duration=1.,reverse=stage=='tray_place')
        elif stage in ('tea_across','tea_down','tea_side','request','tray_return','tray_up','tray_across'):
            self._act(self.tender,'cup','left' if stage=='request' else self.tender.facing)
        elif stage in ('wobble','stone_pickup','tray_setdown'):
            self._act(self.tender,{'wobble':'set_stone','stone_pickup':'take_stone',
                                  'tray_setdown':'set_tray'}[stage],'left',duration=CUP_ACTION_SECONDS)
        elif stage == 'stone_wait':self._act(self.tender,'idle','left')
        elif stage == 'reach_walk':
            self._act(self.mason,'idle','right');self._act(self.tender,'idle','left')
        elif stage == 'reach':
            self._act(self.mason,'receive','right',duration=2.);self._act(self.tender,'idle','left')
        elif stage == 'exchange':
            self._act(self.mason,'cup','right');self._act(self.tender,'idle','left')
        elif stage in ('sit_walk','stand'):
            self._act(self.mason,'cup','left' if stage=='sit_walk' else 'right')
            self._act(self.tender,'idle','left')
        elif stage == 'sit_down':
            self._act(self.mason,'sit_down','front',duration=1.);self._act(self.tender,'idle','left')
        elif stage == 'sit':
            self._act(self.mason,'drink','front',duration=3.2);self._act(self.tender,'idle','left')
        elif stage == 'tool_return':
            self._act(self.mason,'sit','front');self._act(self.tender,'idle')
        elif stage == 'stand_up':
            self._act(self.mason,'stand_up','front',duration=1.);self._act(self.tender,'idle','left')
        elif stage == 'cup_return':
            self._act(self.mason,'offer','right',duration=1.)
            self._act(self.tender,'receive','left',duration=1.)

    def _commit(self, game, **changes):
        self.state.update(changes);game.save_progress()

    def _walk(self, actor, target, seconds, player, pose='idle'):
        delta=pygame.Vector2(target)-actor.position
        self._act(actor,pose);actor.moving=False
        if delta.length()<.1:return True
        actor.facing=('right' if delta.x>0 else 'left') if abs(delta.x)>abs(delta.y) else ('front' if delta.y>0 else 'back')
        remaining=min(delta.length(),22*seconds)
        while remaining>0:
            step=min(1,remaining);point=actor.position+delta.normalize()*step
            if not self.world.can_stand(point,actor.probe_size,actor,player):return False
            actor.position.update(point);remaining-=step;actor.moving=True
        return actor.position.distance_to(target)<.1

    def _script(self, game, lines, completed):
        def done():self.dialogue_running=False;completed()
        self.dialogue_running=game.social.start_script(lines,on_complete=done,identifier=SCENE_ID)
        return self.dialogue_running

    def _ambient_tender(self, seconds, player):
        route=[(-2336,584),(-2376,584),KETTLE]
        if self._walk(self.tender,route[self.route],seconds,player):
            self._act(self.tender,'measure','left');self.work_timer+=seconds
            if self.work_timer>3:self.route=(self.route+1)%3;self.work_timer=0

    def stone_destination(self, index=None):
        index=self.state['sorted'] if index is None else index
        return pygame.Vector2(REJECT if index==2 else (STACK[0]+index*7-7,STACK[1]))

    def update(self, seconds, game):
        if game.player.position.distance_to(SOURCE)>260:return
        if game.social.locked:
            for actor in self.actors:actor.moving=False;actor.advance(0)
            return
        if self.dialogue_running:self.dialogue_running=False
        previous_frames={actor:(actor.animation_key,actor.frame_index) for actor in self.actors}
        seconds=min(max(seconds,0),.1);self.timer+=seconds
        for actor in self.actors:actor.moving=False
        player=self.world.probe_rect(game.player.position)
        stage=self.stage
        if stage in self.AMBIENT:self._ambient_tender(seconds,player)
        if stage == 'inspect':
            self._act(self.mason,'inspect','front')
            if self.timer>=2:self._stage('lift')
        elif stage == 'lift':
            self._act(self.mason,'lift','front',duration=1.4)
            if self.timer>=1.4:self._stage('carry')
        elif stage == 'carry':
            if self._walk(self.mason,self.stone_destination(),seconds,player,'carry'):self._stage('place')
        elif stage == 'place':
            self._act(self.mason,'place','front',duration=1.2)
            if self.timer>=1.2:
                self._commit(game,sorted=self.state['sorted']+1);self._stage('stone_recover')
        elif stage == 'stone_recover':
            self._act(self.mason,'recover','front',duration=.4)
            if self.timer>=.4:self._stage('return')
        elif stage == 'return':
            if self._walk(self.mason,SOURCE,seconds,player):self._stage('inspect' if self.state['sorted']<3 else 'ready')
        elif stage == 'ready':
            self._act(self.mason,'stretch' if self.timer<2 else 'work','front' if self.timer<2 else 'right')
            if self.timer>8:self._stage('barrier')
        elif stage == 'barrier':
            if self._walk(self.mason,BARRIER,seconds,player):self._stage('barrier_look')
        elif stage == 'barrier_look':
            self._act(self.mason,'measure','left')
            if self.timer>=3:self._stage('barrier_return')
        elif stage == 'barrier_return':
            if self._walk(self.mason,SOURCE,seconds,player):self._stage('ready')
        elif stage == 'tea_home':
            if self._walk(self.tender,KETTLE,seconds,player):self._stage('tea_pickup')
        elif stage == 'tea_pickup':
            self._act(self.tender,'pickup','right',duration=1.)
            if self.timer>=1:
                self._commit(game,cup_phase='tender');self._stage('tea_across')
        elif stage == 'tea_across':
            if self._walk(self.tender,(-2336,584),seconds,player,'cup'):self._stage('tea_down')
        elif stage == 'tea_down':
            if self._walk(self.tender,(-2336,616),seconds,player,'cup'):self._stage('tea_side')
        elif stage == 'tea_side':
            if self._walk(self.tender,HELP,seconds,player,'cup'):self._stage('request')
        elif stage == 'request':self._act(self.tender,'cup','left')
        elif stage == 'wobble':
            if self.timer>=CUP_ACTION_SECONDS:
                self._commit(game,cup_phase='stone')
                self._cup_sound(game,'bridge_cup_stone')
                self._stage('stone_wait')
        elif stage == 'stone_wait':
            if self.timer>=.6:self._stage('stone_pickup')
        elif stage == 'stone_pickup':
            if self.timer>=CUP_ACTION_SECONDS:
                self._commit(game,cup_phase='tender_from_stone');self._stage('tray_setdown')
        elif stage == 'tray_setdown':
            if self.timer>=CUP_ACTION_SECONDS:
                self._commit(game,tea_beat=2,cup_phase='tray')
                self._cup_sound(game,'bridge_cup_tray')
                self._stage('reach_walk')
        elif stage == 'reach_walk':
            if self._walk(self.mason,REACH,seconds,player):self._stage('reach')
        elif stage == 'reach':
            self._act(self.mason,'receive','right',duration=2.)
            if self.timer>=2:
                self._commit(game,tea_beat=3,cup_phase='mason');self._stage('exchange')
        elif stage == 'exchange':self._act(self.mason,'cup','right')
        elif stage == 'sit_walk':
            if self._walk(self.mason,SEAT,seconds,player,'cup'):self._stage('sit_down')
        elif stage == 'sit_down':
            self._act(self.mason,'sit_down','front',duration=1.)
            if self.timer>=1:self._stage('sit')
        elif stage == 'sit':
            self._act(self.mason,'drink','front',duration=3.2)
            if self._walk(self.tender,SOURCE,seconds,player):
                self._act(self.tender,'work','right')
                if self.timer>5:self._stage('tool_return')
        elif stage == 'tool_return':
            if self._walk(self.tender,HELP,seconds,player):self._stage('stand_up')
        elif stage == 'stand_up':
            self._act(self.mason,'stand_up','front',duration=1.)
            if self.timer>=1:self._stage('stand')
        elif stage == 'stand':
            if self._walk(self.mason,SOURCE,seconds,player,'cup'):self._stage('cup_return')
        elif stage == 'cup_return':
            self._act(self.mason,'offer','right',duration=1.)
            self._act(self.tender,'receive','left',duration=1.)
            if self.timer>=1:
                self._commit(game,cup_phase='tender_return');self._stage('tray_return')
        elif stage == 'tray_return':
            if self._walk(self.tender,(-2336,616),seconds,player,'cup'):self._stage('tray_up')
        elif stage == 'tray_up':
            if self._walk(self.tender,(-2336,584),seconds,player,'cup'):self._stage('tray_across')
        elif stage == 'tray_across':
            if self._walk(self.tender,KETTLE,seconds,player,'cup'):self._stage('tray_place')
        elif stage == 'tray_place':
            self._act(self.tender,'pickup','right',duration=1.,reverse=True)
            if self.timer>=1:
                self._commit(game,tea_beat=5,cup_phase='kettle')
                self._cup_sound(game,'bridge_cup_return')
                self._stage('ready')
        for actor in self.actors:actor.advance(seconds)
        self._sync_audio(game,previous_frames)

    def _sync_audio(self,game,previous_frames):
        audio=getattr(game,'regional_audio',None)
        if not audio:return
        actor=self.working_tool_actor()
        current=(actor.animation_key,actor.frame_index)
        if (actor.pose=='work' and current!=previous_frames[actor]
                and actor.frame_index==GrainFarm._contact_frame(actor,tool=True)):
            audio.emit('bridge_tool','stone',lambda:actor.position,'masonry')

    def _cup_sound(self,game,key):
        audio=getattr(game,'regional_audio',None)
        if audio:audio.emit(key,'cup',tuple(self.cup_position),'ceramic',3)

    def working_tool_actor(self):
        """The same physical owner drives the prop and its material sound."""
        return next((actor for actor in self.actors if actor.pose=='work'),self.mason)

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
            def request_done():self._commit(game,request_read=True);self._stage('wobble')
            return self._script(game,[{'speaker':'bridge_tender','text':'Tea. You can spare a moment.'},
                {'speaker':'bridge_mason','text':'Leave it on that stone. Just this edge to check.'}],request_done)
        if self.stage=='exchange':
            def done():self._commit(game,tea_beat=4);self._stage('sit_walk')
            return self._script(game,[{'speaker':'bridge_mason','text':'You moved it.'},
                {'speaker':'bridge_tender','text':'The stone was moving it first.'}],done)
        role=actor.role
        text=('These sound pieces can be kept. The cracked ones stay separate. Nothing goes back into the span yet.' if role=='mason' else
              'We measure from this bank. There is still no safe crossing.')
        def done():
            if role not in self.state['greeted']:self.state['greeted'].append(role);game.save_progress()
        return game.social.start_script([{'speaker':'bridge_'+role,'text':text}],on_complete=done,identifier='bridge_crew_greeting')

    def ground_blockers(self,actor=None):
        blocks=[pygame.Rect(-2318,568,28,7),pygame.Rect(-2413,594,26,3),
                pygame.Rect(-2435,631,38,3),pygame.Rect(SAFE[0]-12,SAFE[1]-5,24,4)]
        if actor not in self.actors and self.state['tea_beat'] in (1,2,3,4):blocks.append(HANDOFF)
        return blocks

    def stone_position(self,index):
        if index<self.state['sorted']:
            return self.stone_destination(index)+(0,-2)
        point=pygame.Vector2(SOURCE)+(index*3-3,-2)
        if index==self.state['sorted'] and self.stage in ('carry','place'):
            frame=self.mason.held_attachment('stone');offset=frame.get('stone_offset')
            if offset is not None:
                point=self.mason.position+offset
        return point

    @property
    def cup_owner(self):
        phase=self.state['cup_phase']
        if phase in ('tender','tender_from_stone','tender_return'):return self.tender
        if phase == 'mason':return self.mason
        return None

    def _cup_attachment(self):
        actor=self.cup_owner
        if actor is None:return {}
        if self.stage in ('wobble','tray_setdown','cup_return','tray_place'):
            return actor.held_attachment('cup')
        return actor.attachment

    @property
    def cup_position(self):
        phase=self.state['cup_phase']
        if phase == 'tray':return pygame.Vector2(SAFE)+(0,-7)
        if phase == 'stone':
            return pygame.Vector2(WORK_STONE)+(int(self.timer*6)%2 if self.stage=='stone_wait' else 0,-9)
        actor=self.cup_owner
        if actor is not None:
            offset=self._cup_attachment().get('cup_offset')
            if offset is not None:
                return actor.position+offset
        return pygame.Vector2(KETTLE)+(8,-11)

    @property
    def tool_position(self):
        actor=self.working_tool_actor()
        if actor.pose=='work' and actor.attachment.get('tool_offset') is not None:
            return actor.position+actor.attachment['tool_offset']
        return pygame.Vector2(TOOL_REST)

    @staticmethod
    def _held_sort(actor,kind):
        return held_prop_sort(actor,actor.attachment.get(kind+'_layer'))

    def props(self):
        result=[]
        def add(key,point,sort=None):
            image=self.art[key];x,y=point
            result.append((y if sort is None else sort,4,image,
                           (round(x)-image.get_width()//2,round(y)-image.get_height())))
        add('tray',(-2304,577));add('kettle',(-2307,575));add('bench',(-2400,603),598)
        add('barrier',(-2416,634),634)
        add('keep_mark',(-2344,604));add('reject_mark',(-2312,604))
        for index in range(3):
            point=self.stone_position(index)
            active=index==self.state['sorted'] and self.stage in ('carry','place')
            layer=self.mason.held_attachment('stone').get('stone_layer') if active else None
            add('stone',point,held_prop_sort(self.mason,layer) if active else point.y+1)
        wobble=int(self.timer*6)%2 if self.stage=='stone_wait' else 0
        add('stone',(WORK_STONE[0]+wobble,WORK_STONE[1]))
        add('tray',SAFE)
        owner=self.cup_owner
        add('cup',self.cup_position,held_prop_sort(owner,self._cup_attachment().get('cup_layer')) if owner else self.cup_position.y+1)
        tool_actor=self.working_tool_actor()
        owner=tool_actor if tool_actor.pose=='work' else None
        add('tool',self.tool_position,self._held_sort(owner,'tool') if owner else self.tool_position.y+1)
        return result
