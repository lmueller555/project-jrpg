"""Finish, carry and safely put away Liam's first lantern in the same afternoon."""
import json
from pathlib import Path

import pygame

from lantern_actors import ResidentPose
from quests import LANTERN_QUEST
from social import facing_toward

ROOT = Path(__file__).resolve().parent
ART = ROOT/'assets/story/lantern'
FINISH_STAGES = ('finish_invited', 'home_rejoined', 'purpose_chosen', 'panel_ready',
                 'fit_ready', 'covered', 'lantern_finished', 'school_met',
                 'mother_shown', 'homeward', 'put_away', 'done')
FINISH_PREFIX = {s: 8 if s == 'done' else 7 if FINISH_STAGES.index(s)>=6 else 6 for s in FINISH_STAGES}
SCENES = {
    'finish_invitation': ('serene_heard', 'finish_invited', None),
    'home_return': ('finish_invited', 'home_rejoined', None),
    'purpose': ('home_rejoined', 'purpose_chosen', None),
    'final_panel': ('purpose_chosen', 'panel_ready', None),
    'dry_fit': ('panel_ready', 'fit_ready', None),
    'fasten_covering': ('fit_ready', 'covered', None),
    'finished_lantern': ('covered', 'lantern_finished', 'finish_lantern'),
    'school_welcome': ('lantern_finished', 'school_met', None),
    'show_mother': ('school_met', 'mother_shown', None),
    'homeward': ('mother_shown', 'homeward', None),
    'put_away': ('homeward', 'put_away', None),
    'farewell': ('put_away', 'done', 'show_mother'),
}
ACTIONS = {'dry_fit': 'finish_prepare', 'fasten_covering': 'finish_cover',
           'finished_lantern': 'finish_pickup', 'put_away': 'finish_place'}


class LanternFinish:
    def __init__(self, controller):
        self.c = controller;self.game = controller.game;self.town = controller.town
        self.home = controller.rest.home;self.school = controller.school;self.sanctuary = controller.rest.sanctuary
        self.points = json.loads((ART/'finish_layout.json').read_text())
        self.lines = json.loads((ART/'finish_scene.json').read_text())
        self.art = json.loads((ART/'finish_art.json').read_text())
        self.pose_meta = json.loads((ROOT/self.art['poses']['liam']).read_text())
        sheet = self.town.image(self.pose_meta['sheet'])
        self.actions = {k: [(sheet.subsurface(f['rect']).copy(), f['duration_ms']) for f in frames]
                        for k, frames in self.pose_meta['actions'].items()}
        self.carry = {d: {'idle': sheet.subsurface(spec['idle']['rect']).copy(),
                          'walk': [(sheet.subsurface(f['rect']).copy(), f['duration_ms']) for f in spec['walk']]}
                      for d, spec in self.pose_meta['carry'].items()}
        self.surface_props = []
        for spec in self.art['props']:
            states = {k: self.town.image(p) for k, p in spec['states'].items()}
            self.surface_props.append({**spec, 'states': states, 'surface': next(iter(states.values()))})
            self.game._scene_by_id(spec['scene']).attach_routine_props(self)
        self.zone = None;self.pose_owned = False

    @property
    def active(self):return self.c.stage == 'serene_heard' or self.c.stage in FINISH_STAGES

    @property
    def frame_location(self):
        return 'held' if self.c.stage in ('lantern_finished', 'school_met', 'mother_shown', 'homeward') else 'home'

    @property
    def frame_form(self):
        if self.c.stage in ('serene_heard', 'finish_invited', 'home_rejoined', 'purpose_chosen'):return 'bare'
        if self.c.stage == 'panel_ready':return 'panel'
        if self.c.stage == 'fit_ready':return 'partial'
        return 'finished'

    @property
    def paper_location(self):return 'home'

    def reset(self):self.zone = None

    def release(self):self._clear_pose();self.reset()

    def _clear_pose(self):
        if not self.pose_owned:return
        for key in ('story_sprite', 'story_draw_anchor'):
            if hasattr(self.c.liam, key):delattr(self.c.liam, key)
        self.pose_owned = False

    def _where(self):
        if self.c.stage == 'serene_heard':return self.sanctuary, 'invitation'
        if self.c.stage in ('lantern_finished', 'school_met', 'mother_shown'):return self.school, 'school'
        if self.c.stage in FINISH_STAGES and self.c.stage != 'done':return self.home, 'home'
        return None, None

    def _static_cast(self):
        c = self.c
        c.rest._claim_father();c.rest._claim_serene()
        c._restore_station(c.serene, self.sanctuary, self.points['serene_after'])
        c.serene.story_following = False;c.serene.facing = 'left'

    def restore(self):
        self.reset();self._static_cast()
        c = self.c
        if c.stage == 'done':
            # Reconstruct the afternoon without reserving the ambient child.
            c.game.regent_quest.handoff_tomas()
            c.tomas.story_paused = True;c.tomas.story_following = False
            c._restore_station(c.tomas, self.sanctuary, self.points['tomas_after'])
            c._restore_station(c.liam, self.home, self.points['home_liam'])
            c.liam.story_following = False
        else:
            world, key = self._where()
            at_visit = world is self.game.world and key and c._near(self.points[key], 96)
            for actor, suffix, offset in ((c.liam, 'liam', (-28, 18)), (c.tomas, 'tomas', (28, 18))):
                if actor is c.liam and not c._liam_claimed:continue
                desired = self.points[key+'_'+suffix] if at_visit else self.game.player.position+offset
                c._restore_station(actor, self.game.world, desired)
        self.sync_props();self.render(0.)

    def target(self):
        if not self.active or self.c.stage == 'done' or not self.c._ready:return None
        world, key = self._where()
        if world is not self.game.world or key is None or not self.c._near(self.points[key], 76):return None
        required = (self.c.serene,) if key == 'invitation' else (self.c.father,) if key == 'home' else (self.c.mother,)
        if any(a not in world.npcs for a in (*required, self.c.liam, self.c.tomas)):return None
        return next((kind for kind, (previous, _, _) in SCENES.items() if previous == self.c.stage), None)

    def finish(self, kind):
        if kind not in SCENES:return False
        previous, stage, objective = SCENES[kind]
        if self.c.stage != previous:return True
        if kind in ACTIONS:
            self.c.action = ACTIONS[kind];self.c.action_time = 0.;self.c.align_time = 0.;self.c._ready = False
        elif kind == 'farewell':
            if not self.game.quests.complete_and_turn_in(LANTERN_QUEST, 'show_mother'):return True
            self.c.stage = 'done';self.c._ready = False
            self.game.social.flags.add('CH01_MQ04_COMPLETE')
            self._clear_pose();self.c.rest._clear_liam_pose()
            self.c.shared.release_liam(self.c, reset=False);self.c._liam_claimed = False
            self.c.tomas.story_following = True
            self.c.paths.clear();self.c.retries.clear();self.c._save()
        else:
            self.zone = None;self.c._transition(stage, objective)
        return True

    def action_update(self, seconds):
        c = self.c;kind = c.action
        suffix = kind.removeprefix('finish_')
        station = 'pickup_liam' if suffix == 'pickup' else 'place_liam' if suffix == 'place' else 'work_liam'
        if c._world(c.liam) is not self.home:
            c.action = None;self._clear_pose();return
        if not c._move(c.liam, self.points[station], seconds, 44):
            c.align_time += seconds
            if c.align_time>12:c.action = None;self._clear_pose()
            return
        c.liam.facing = self.pose_meta['action_facing'][suffix];c.action_time += seconds
        duration = {'prepare': 1.8, 'cover': 2.4, 'pickup': 1.2, 'place': 1.2}[suffix]
        if c.action_time<duration:return
        c.action = None;self._clear_pose();self.zone = None
        scene = next(k for k, action in ACTIONS.items() if action == kind)
        _, stage, objective = SCENES[scene];c._transition(stage, objective)

    def _optional(self, key):
        if key not in self.lines:return False
        present = {a.data['id'] for a in self.game.world.npcs}
        if any(line['speaker'] != 'caelan' and self.game.social.data['speakers'][line['speaker']].get('actor_id', line['speaker']) not in present for line in self.lines[key]):return False
        return self.c._speak(key)

    def try_conversation(self, actor):
        if not self.active:return None
        c = self.c;target = c._target();done = c.stage == 'done'
        if actor in (c.liam, c.tomas):
            if target:return c.interact()
            return self._optional('liam_done' if done and actor is c.liam else 'tomas_done' if done else
                                  'liam_finished' if actor is c.liam and self.frame_form == 'finished' else
                                  'finish_liam_waiting' if actor is c.liam else 'finish_tomas_waiting')
        if actor is c.father:
            if target and self._where()[1] == 'home':return c.interact()
            return self._optional('father_done' if done or c.stage == 'put_away' else 'father_finished_home' if self.frame_form == 'finished' else
                                  'father_before_finish' if c.stage in ('serene_heard', 'finish_invited') else 'father_during_finish')
        if actor is c.mother:
            if target in ('school_welcome', 'show_mother', 'homeward'):return c.interact()
            return self._optional('mother_done' if done else 'mother_after_show' if c.stage in ('mother_shown', 'homeward', 'put_away') else 'mother_before_show')
        if actor is c.serene:return self._optional('serene_done' if done else 'serene_finish_waiting')
        if actor is c.mira:return self._optional('mira_done')
        if actor is c.elira:return self._optional('elira_done') if done else None
        return None

    def marker_for(self, identifier):
        if not self.active:return NotImplemented
        world, key = self._where()
        owner = {'invitation': 'liam', 'home': 'liam_father', 'school': 'liam_mother'}.get(key)
        if identifier in ('liam', 'tomas', 'liam_father', 'liam_mother', 'mother_serene', 'mira_worker', 'elira', 'halden', 'venn_mother', 'venn_father', 'venn_child'):
            return '?' if identifier == owner else None
        return NotImplemented

    def tracker_text(self):
        return {'serene_heard': 'Speak with Liam about finishing his lantern.',
                'finish_invited': 'Return to Liam’s home to finish his lantern.',
                'home_rejoined': 'Listen to Liam’s idea for his lantern.',
                'purpose_chosen': 'Help Liam draw the final window and stairs.',
                'panel_ready': 'Try the paper against the tower frame.',
                'fit_ready': 'Fasten the covering with Liam’s father.',
                'covered': 'Let Liam inspect and lift his finished lantern.',
                'lantern_finished': 'Carry the lantern to Liam’s mother at school.',
                'school_met': 'Let Liam show his mother what he made.',
                'mother_shown': 'Say goodbye before taking the lantern home.',
                'homeward': 'Return home and put the lantern somewhere safe.',
                'put_away': 'Say goodbye to Liam and his father.',
                'done': 'Liam’s finished lantern is safe at home for tomorrow’s festival.'}.get(self.c.stage, '')

    def interaction_hint(self, target):
        if self.c.action:return {'finish_prepare': 'Fitting the paper…', 'finish_cover': 'Fastening the covering…',
                                 'finish_pickup': 'Trying the finished lantern…', 'finish_place': 'Putting the lantern away…'}.get(self.c.action, '')
        return {kind: 'E: '+text for kind, text in (
            ('finish_invitation', 'Speak with Liam'), ('home_return', 'Return to the preparation table'),
            ('purpose', 'Listen to Liam’s idea'), ('final_panel', 'Draw the final panel'),
            ('dry_fit', 'Try the covering'), ('fasten_covering', 'Fasten the paper'),
            ('finished_lantern', 'Try the finished lantern'), ('school_welcome', 'Greet Liam’s mother'),
            ('show_mother', 'Show Mother the lantern'), ('homeward', 'Say goodbye to Mother'),
            ('put_away', 'Put the lantern away safely'), ('farewell', 'Say goodbye'))}.get(target, '')

    def update(self, seconds):
        c = self.c
        if c.stage == 'done':
            if not self.game.social.locked:
                arrived = c._travel(c.tomas, self.sanctuary, seconds) and c._move(c.tomas, self.points['tomas_after'], seconds)
                c.tomas.story_following = not arrived
                if arrived:c.tomas.facing = 'right'
            c.rest.render(seconds);self.sync_props();return
        c.rest._claim_father();c.rest._claim_serene();c.serene.story_following = False
        if c.action in ACTIONS.values():self.action_update(seconds);self.render(seconds);self.sync_props();return
        if self.game.social.locked:self.render(seconds);self.sync_props();return
        world, key = self._where()
        if world is not self.game.world or key is None or not c._near(self.points[key], 90):
            self.zone = None;c._ready = False;c._follow(seconds)
        else:
            if self.zone != key:c.paths.clear();self.zone = key
            ready = []
            for actor, suffix in ((c.liam, 'liam'), (c.tomas, 'tomas')):
                if actor is c.liam and not c._liam_claimed:ready.append(False);continue
                arrived = c._travel(actor, world, seconds) and c._move(actor, self.points[key+'_'+suffix], seconds)
                ready.append(arrived)
                if arrived:actor.facing = 'right' if actor is c.liam and key == 'home' else facing_toward(self.game.player.position-actor.position)
            if key == 'invitation':ready.append(c._world(c.serene) is self.sanctuary)
            c._ready = len(ready)>=2 and all(ready)
        self.render(seconds);self.sync_props()

    def render(self, seconds):
        self.c.rest.render(seconds)
        if not self.active or self.c.stage == 'done':self._clear_pose();return
        action = self.c.action.removeprefix('finish_') if self.c.action in ACTIONS.values() else None
        image = None
        if action and self.c.action_time>0:image = self.c.rest._frame(self.actions[action], self.c.action_time, False)
        elif self.frame_location == 'held':
            actor = self.c.liam;spec = self.carry[actor.facing]
            image = self.c.rest._frame(spec['walk'], actor.walk_ms/1000) if actor.moving else spec['idle']
        if image is None:self._clear_pose();return
        self.c.liam.story_sprite = image;self.c.liam.story_draw_anchor = tuple(self.pose_meta['draw_anchor']);self.pose_owned = True

    def surface_prop_visible(self, prop):
        if not self.c.eligible or not self.active:return False
        if prop['id'] == 'home_lantern':
            return self.frame_location == 'home' and not (self.c.action == 'finish_place' and self.c.action_time>0)
        return self.c.stage in ('purpose_chosen', 'panel_ready', 'fit_ready')

    def sync_props(self):
        for prop in self.surface_props:
            key = self.frame_form if prop['id'] == 'home_lantern' else 'draft' if self.c.stage == 'purpose_chosen' else 'final'
            prop['surface'] = prop['states'].get(key, next(iter(prop['states'].values())))
