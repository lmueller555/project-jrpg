"""Liam's home break and sanctuary questions, inside the same lantern quest."""
import json
from pathlib import Path

import pygame

from lantern_actors import ResidentPose
from social import facing_toward

ROOT = Path(__file__).resolve().parent
ART = ROOT/'assets/story/lantern'
REST_STAGES = ('collecting_route', 'materials_collected', 'materials_home', 'rested',
               'paper_tried', 'brothers_spoken', 'home_break_done', 'serene_welcomed',
               'faith_discussed', 'remembrance_discussed', 'serene_heard')
REST_PREFIX = {s: (6 if s == 'serene_heard' else 5 if REST_STAGES.index(s)>=6 else 4)
               for s in REST_STAGES}
SCENES = {
    'break_invitation': ('elira_visited', 'collecting_route', None),
    'collect_frame': ('collecting_route', 'materials_collected', None),
    'home_welcome': ('materials_collected', 'materials_home', None),
    'snack': ('materials_home', 'rested', None),
    'paper_practice': ('rested', 'paper_tried', None),
    'brothers': ('paper_tried', 'brothers_spoken', None),
    'liam_questions': ('brothers_spoken', 'home_break_done', 'take_break'),
    'sanctuary_welcome': ('home_break_done', 'serene_welcomed', None),
    'returning_life': ('serene_welcomed', 'faith_discussed', None),
    'remembering': ('faith_discussed', 'remembrance_discussed', None),
    'sanctuary_close': ('remembrance_discussed', 'serene_heard', 'speak_serene'),
}
ACTIONS = {'collect_frame': 'rest_pickup', 'home_welcome': 'rest_place', 'paper_practice': 'rest_draft'}


class LanternRest:
    def __init__(self, controller):
        self.c = controller;self.game = controller.game;self.town = controller.town
        self.points = json.loads((ART/'rest_layout.json').read_text())
        for suffix in ('', '_liam', '_tomas'):
            self.points.setdefault('invitation'+suffix, controller.village_points['reflection'+suffix])
        self.lines = json.loads((ART/'rest_scene.json').read_text())
        self.art = json.loads((ART/'rest_art.json').read_text())
        self.home = self.game._scene_by_id('liam_house')
        self.sanctuary = self.game._scene_by_id('sanctuary_hall')
        self.father = next(a for a in self.home.npcs if a.data['id'] == 'liam_father')
        self.serene = controller.serene
        self.father_pose = None;self.serene_owned = False
        self.zone = None;self.work_time = 0.;self.pose_owned = False
        self.pose_meta = json.loads((ROOT/self.art['poses']['liam']).read_text())
        self.sheet = self.town.image(self.pose_meta['sheet'])
        self.actions = {kind: [(self.sheet.subsurface(f['rect']).copy(), f['duration_ms']) for f in frames]
                        for kind, frames in self.pose_meta['actions'].items()}
        self.carry = {d: {'idle': self.sheet.subsurface(spec['idle']['rect']).copy(),
                          'walk': [(self.sheet.subsurface(f['rect']).copy(), f['duration_ms']) for f in spec['walk']]}
                      for d, spec in self.pose_meta['carry'].items()}
        self.workshop_empty = self.town.image(self.art['workshop_collected'])
        self.surface_props = []
        for spec in self.art['props']:
            states = {k: self.town.image(p) for k, p in spec['states'].items()}
            self.surface_props.append({**spec, 'states': states, 'surface': next(iter(states.values()))})
            self.game._scene_by_id(spec['scene']).attach_routine_props(self)

    @property
    def active(self):return self.c.stage == 'elira_visited' or self.c.stage in REST_STAGES

    @property
    def frame_location(self):
        if self.c.stage not in REST_STAGES or self.c.stage == 'collecting_route':return 'workshop'
        return 'held' if self.c.stage == 'materials_collected' else 'home'

    @property
    def paper_location(self):return 'satchel' if self.frame_location == 'held' else self.frame_location

    def reset(self):self.zone = None;self.work_time = 0.

    def _clear_liam_pose(self):
        if not self.pose_owned:return
        for key in ('story_sprite', 'story_draw_anchor'):
            if hasattr(self.c.liam, key):delattr(self.c.liam, key)
        self.pose_owned = False

    def release(self):
        self._clear_liam_pose()
        if self.father_pose is not None:self.father_pose.release();self.father_pose = None
        if self.serene_owned:
            self.serene.story_paused = False;self.serene.story_following = False;self.serene.end_conversation()
            for key in ('story_sprite', 'story_draw_anchor'):
                if hasattr(self.serene, key):delattr(self.serene, key)
            self.serene_owned = False
        self.reset()

    def _claim_father(self):
        if self.father_pose is None:
            self.father_pose = ResidentPose(self.father, self.home)
            if 'liam_father' not in self.game.social.profiles:
                self.game.social.profiles['liam_father'] = {'conversations': []}
                self.c._quest_profiles.add('liam_father')

    def _claim_serene(self):
        if self.serene_owned:return
        self.game.regent_quest.handoff_serene()
        self.serene.story_paused = True;self.serene.story_following = True
        self.serene.end_conversation();self.serene_owned = True

    def _where(self):
        stage = self.c.stage
        if stage == 'elira_visited':return self.town, 'invitation'
        if stage == 'collecting_route':return self.town, 'collection'
        if stage in ('materials_collected', 'materials_home', 'rested', 'paper_tried', 'brothers_spoken'):return self.home, 'home'
        if stage in ('home_break_done', 'serene_welcomed', 'faith_discussed', 'remembrance_discussed'):return self.sanctuary, 'sanctuary'
        return None, None

    def restore(self):
        self.reset()
        if self.frame_location != 'workshop':self._claim_father()
        if self.c.stage in REST_STAGES and REST_PREFIX[self.c.stage]>=5:
            self._claim_serene();self.c._restore_station(self.serene, self.sanctuary, self.points['sanctuary_serene'])
            self.serene.facing = facing_toward(pygame.Vector2(self.points['sanctuary_liam'])-self.serene.position)
        world, key = self._where()
        at_visit = world is self.game.world and key is not None and self.c._near(self.points[key], 96)
        for actor, suffix, offset in ((self.c.liam, 'liam', (-28, 18)), (self.c.tomas, 'tomas', (28, 18))):
            if actor is self.c.liam and not self.c._liam_claimed:continue
            desired = self.points[key+'_'+suffix] if at_visit else self.game.player.position+offset
            self.c._restore_station(actor, self.game.world, desired)
        self.sync_props();self.render(0.)

    def target(self):
        if not self.active or not self.c._ready:return None
        world, key = self._where()
        if world is not self.game.world or key is None or not self.c._near(self.points[key], 76):return None
        people = (self.c.mira,) if key == 'collection' else (self.father,) if key == 'home' else (self.serene,) if key == 'sanctuary' else ()
        if any(a not in world.npcs for a in (*people, self.c.liam, self.c.tomas)):return None
        return next((kind for kind, (previous, _, _) in SCENES.items() if previous == self.c.stage), None)

    def finish(self, kind):
        if kind not in SCENES:return False
        previous, stage, objective = SCENES[kind]
        if self.c.stage != previous:return True
        if kind in ACTIONS:
            self.c.action = ACTIONS[kind];self.c.action_time = 0.;self.c.align_time = 0.;self.c._ready = False
            return True
        self.zone = None;self.c._transition(stage, objective)
        if stage == 'home_break_done':self._claim_serene()
        return True

    def action_update(self, seconds):
        kind = self.c.action
        key = {'rest_pickup': 'pickup_liam', 'rest_place': 'place_liam', 'rest_draft': 'work_liam'}[kind]
        world = self.town if kind == 'rest_pickup' else self.home
        if self.c._world(self.c.liam) is not world:
            self.c.action = None;self._clear_liam_pose();return
        if not self.c._move(self.c.liam, self.points[key], seconds, 44):
            self.c.align_time += seconds
            if self.c.align_time>12:self.c.action = None;self._clear_liam_pose()
            return
        self.c.liam.facing = 'left' if kind == 'rest_place' else 'right';self.c.action_time += seconds
        duration = {'rest_pickup': 1.2, 'rest_place': 1.2, 'rest_draft': 1.8}[kind]
        if self.c.action_time<duration:return
        self.c.action = None;self._clear_liam_pose();self.zone = None
        stage = {'rest_pickup': 'materials_collected', 'rest_place': 'materials_home', 'rest_draft': 'paper_tried'}[kind]
        self.c._transition(stage)
        if kind == 'rest_pickup':
            self.c._mira_owned = False;self.game.mill_quest.return_mira_to_bench();self._claim_father()

    def _optional(self, key):
        if key not in self.lines:return False
        present = {a.data['id'] for a in self.game.world.npcs}
        if any(line['speaker'] != 'caelan' and self.game.social.data['speakers'][line['speaker']].get('actor_id', line['speaker']) not in present for line in self.lines[key]):return False
        return self.c._speak(key)

    def try_conversation(self, actor):
        if not self.active:return None
        target = self.c._target()
        if actor in (self.c.liam, self.c.tomas):
            if target:return self.c.interact()
            if self.c.stage == 'serene_heard':return self._optional('rest_after')
            return self._optional('rest_liam_waiting' if actor is self.c.liam else 'rest_tomas_waiting')
        if actor is self.c.mira:
            if target == 'collect_frame':return self.c.interact()
            return self._optional('mira_before_collection' if self.frame_location == 'workshop' else 'mira_after_collection')
        if actor is self.father:
            if target in ('home_welcome', 'snack', 'paper_practice', 'brothers', 'liam_questions'):return self.c.interact()
            return self._optional('father_before_break' if self.frame_location == 'workshop' else 'father_after_break' if self.c.stage in REST_STAGES and REST_PREFIX[self.c.stage]>=5 else 'father_during_break')
        if actor is self.serene:
            if target in ('sanctuary_welcome', 'returning_life', 'remembering', 'sanctuary_close'):return self.c.interact()
            return self._optional('serene_after_visit' if self.c.stage == 'serene_heard' else 'serene_during_visit' if self.c.stage in ('serene_welcomed', 'faith_discussed', 'remembrance_discussed') else 'serene_before_visit')
        if actor is self.c.mother:return self._optional('mother_during_rest')
        return None

    def marker_for(self, identifier):
        if not self.active:return NotImplemented
        if identifier == 'liam':return '?' if self.c.stage == 'elira_visited' else None
        if identifier == 'mira_worker':return '?' if self.c.stage == 'collecting_route' else None
        if identifier == 'liam_father':return '?' if self._where()[1] == 'home' else None
        if identifier == 'mother_serene':return '?' if self._where()[1] == 'sanctuary' else None
        if identifier in ('tomas', 'halden', 'elira', 'venn_mother', 'venn_father', 'venn_child'):return None
        return NotImplemented

    def tracker_text(self):
        return {'elira_visited': 'Speak with Liam and Tomas about taking a break.',
                'collecting_route': 'Collect the frame and papers from Mira.',
                'materials_collected': 'Return to Liam’s home together.',
                'materials_home': 'Take a break with Liam’s father.',
                'rested': 'Let Liam try his paper design.',
                'paper_tried': 'Talk quietly with Tomas while Liam works.',
                'brothers_spoken': 'Listen to Liam’s questions.',
                'home_break_done': 'Visit Mother Serene in the sanctuary hall.',
                'serene_welcomed': 'Ask Serene about returning life.',
                'faith_discussed': 'Talk about remembering and celebrating.',
                'remembrance_discussed': 'Finish the conversation with Serene.',
                'serene_heard': 'You rested at home and spoke with Serene about the festival.'}.get(self.c.stage, '')

    def interaction_hint(self, target):
        if self.c.action:return {'rest_pickup': 'Collecting the frame…', 'rest_place': 'Setting the frame down…', 'rest_draft': 'Trying the paper design…'}.get(self.c.action, '')
        return {'break_invitation': 'E: Speak about taking a break', 'collect_frame': 'E: Collect the frame and papers',
                'home_welcome': 'E: Come in and set the frame down', 'snack': 'E: Take a break together',
                'paper_practice': 'E: Try the paper design', 'brothers': 'E: Speak quietly with Tomas',
                'liam_questions': 'E: Listen to Liam', 'sanctuary_welcome': 'E: Visit Mother Serene',
                'returning_life': 'E: Ask about the festival', 'remembering': 'E: Talk about remembrance',
                'sanctuary_close': 'E: Finish speaking with Serene'}.get(target, '')

    def update(self, seconds):
        if not self.active:return
        if self.c.stage in REST_STAGES and REST_PREFIX[self.c.stage]>=5:self._claim_serene()
        if self.frame_location != 'workshop':self._claim_father()
        if self.c.action in ('rest_pickup', 'rest_place', 'rest_draft'):
            self.action_update(seconds);self.render(seconds);self.sync_props();return
        if self.game.social.locked:
            self.render(seconds);self.sync_props();return
        world, key = self._where()
        if self.serene_owned and self._where()[1] == 'sanctuary':
            self.c._travel(self.serene, self.sanctuary, seconds)
            if self.c._world(self.serene) is self.sanctuary and self.c._move(self.serene, self.points['sanctuary_serene'], seconds):
                self.serene.facing = facing_toward(pygame.Vector2(self.points['sanctuary_liam'])-self.serene.position)
        if world is not self.game.world or key is None or not self.c._near(self.points[key], 90):
            self.zone = None;self.c._ready = False;self.c._follow(seconds)
        else:
            if self.zone != key:self.c.paths.clear();self.zone = key
            ready = []
            for actor, suffix in ((self.c.liam, 'liam'), (self.c.tomas, 'tomas')):
                if actor is self.c.liam and not self.c._liam_claimed:ready.append(False);continue
                arrived = self.c._travel(actor, world, seconds) and self.c._move(actor, self.points[key+'_'+suffix], seconds)
                ready.append(arrived)
                if arrived:actor.facing = 'right' if actor is self.c.liam else facing_toward(self.game.player.position-actor.position)
            if key == 'collection':
                self.c._claim_mira()
                ready.append(self.c._travel(self.c.mira, self.town, seconds) and self.c._move(self.c.mira, self.points['collection_mira'], seconds))
                self.c.mira.facing = 'left'
            if key == 'sanctuary':ready.append(self.c._world(self.serene) is self.sanctuary and self.serene.position.distance_to(self.points['sanctuary_serene'])<1)
            self.c._ready = len(ready)>=2 and all(ready)
        self.render(seconds);self.sync_props()

    def _set_pose(self, image):
        self.c.liam.story_sprite = image;self.c.liam.story_draw_anchor = tuple(self.pose_meta['draw_anchor']);self.pose_owned = True

    @staticmethod
    def _frame(frames, time, loop=True):
        duration = sum(d for _, d in frames)
        elapsed = time*1000%duration if loop else min(time*1000, duration-1)
        for image, ms in frames:
            if elapsed<ms:return image
            elapsed -= ms
        return frames[-1][0]

    def render(self, seconds):
        if self.father_pose:self.father_pose.sync()
        if self.serene_owned:
            actor = self.serene;frames = actor.walks[actor.facing]
            frame = frames[int(actor.walk_ms//140)%len(frames)] if actor.moving else actor.idles[actor.facing]
            actor.story_sprite = frame[0] if isinstance(frame, tuple) else frame;actor.story_draw_anchor = actor.draw_anchor
        if not self.active:self._clear_liam_pose();return
        self.work_time += seconds
        action = {'rest_pickup': 'pickup', 'rest_place': 'place', 'rest_draft': 'work'}.get(self.c.action)
        if action and self.c.action_time>0:
            self._set_pose(self._frame(self.actions[action], self.c.action_time, False));return
        if self.frame_location == 'held':
            spec = self.carry[self.c.liam.facing]
            self._set_pose(self._frame(spec['walk'], self.c.liam.walk_ms/1000) if self.c.liam.moving else spec['idle']);return
        if self.game.world is self.home and self.c._world(self.c.liam) is self.home:
            if self.c.dialogue == 'snack':self._set_pose(self._frame(self.actions['snack'], self.work_time));return
            if self.c.dialogue == 'paper_practice':self._set_pose(self._frame(self.actions['work'], self.work_time));return
            if self.c.stage in ('paper_tried', 'brothers_spoken') and self.c.dialogue in (None, 'brothers'):
                self._set_pose(self._frame(self.actions['work'], self.work_time));return
        self._clear_liam_pose()

    def surface_prop_visible(self, prop):
        if not self.c.eligible or self.frame_location != 'home':return False
        if prop['id'] == 'home_snack':return self.c.stage == 'materials_home'
        if prop['id'] == 'home_papers':return self.c.stage != 'materials_home'
        return True

    def sync_props(self):
        tried = self.c.stage in REST_STAGES and REST_STAGES.index(self.c.stage)>=REST_STAGES.index('paper_tried')
        for prop in self.surface_props:
            states = prop['states'];key = 'revised' if tried else 'smudged' if self.c.action == 'rest_draft' or self.c.dialogue == 'paper_practice' else 'clean'
            if prop['id'] == 'home_snack':key = 'used' if self.c.stage not in ('materials_collected', 'materials_home') else 'ready'
            prop['surface'] = states.get(key, next(iter(states.values())))
