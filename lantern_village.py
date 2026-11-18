"""The village preparation visits within Liam's continuous lantern quest.

This section borrows no new people and owns no earlier repair or memorial prop.
Only fully read scene callbacks advance the version-one committed stage.
"""
import json
from pathlib import Path

import pygame
from social import facing_toward

ROOT = Path(__file__).resolve().parent
ART = ROOT/'assets/story/lantern'
VILLAGE_STAGES = ('outing', 'mill_met', 'mill_visited', 'venn_met',
                  'neighbours_visited', 'elira_welcomed', 'elira_remembering',
                  'elira_remembered', 'elira_ready_to_leave', 'elira_farewell', 'elira_visited')
VILLAGE_PREFIX = {s: (4 if s == 'elira_visited' else 3 if VILLAGE_STAGES.index(s) >= 4 else 2)
                  for s in VILLAGE_STAGES}
SCENES = {
    'departure': ('frame_ready', 'outing', None),
    'mill_arrival': ('outing', 'mill_met', None),
    'mill_flour': ('mill_met', 'mill_visited', None),
    'venn_arrival': ('mill_visited', 'venn_met', None),
    'venn_preparations': ('venn_met', 'neighbours_visited', 'visit_neighbours'),
    'elira_welcome': ('neighbours_visited', 'elira_welcomed', None),
    'elira_lantern': ('elira_welcomed', 'elira_remembering', None),
    'elira_memory': ('elira_remembering', 'elira_remembered', None),
    'elira_company': ('elira_remembered', 'elira_ready_to_leave', None),
    'elira_goodbye': ('elira_ready_to_leave', 'elira_farewell', None),
    'reflection': ('elira_farewell', 'elira_visited', 'visit_elira'),
}


class LanternVillage:
    def __init__(self, controller):
        self.c = controller;self.game = controller.game;self.town = controller.town
        self.points = json.loads((ART/'village_layout.json').read_text())
        self.lines = json.loads((ART/'village_scene.json').read_text())
        self.art = json.loads((ART/'village_art.json').read_text())
        self.halden = self.game.mill_quest.halden
        self.venn_home = self.game.venn_visit.home;self.family = self.game.venn_visit.family
        self.elira_home = self.game.elira_visit.home;self.elira = self.game.elira_visit.elira
        self.actors = (self.halden, *self.family.values(), self.elira)
        self.gathered = False;self.zone = None
        self.surface_props = []
        for spec in self.art['props']:
            states = {key: self.town.image(path) for key, path in spec['states'].items()}
            self.surface_props.append({**spec, 'states': states, 'surface': next(iter(states.values()))})
            self.game._scene_by_id(spec['scene']).attach_routine_props(self)

    @property
    def active(self):return self.c.stage in VILLAGE_STAGES

    def reset(self):self.gathered = False;self.zone = None

    def _where(self):
        stage = self.c.stage
        if stage in ('outing', 'mill_met'):return self.town, 'mill'
        if stage in ('mill_visited', 'venn_met'):return self.venn_home, 'venn'
        if stage in ('neighbours_visited', 'elira_welcomed', 'elira_remembering',
                     'elira_remembered', 'elira_ready_to_leave'):return self.elira_home, 'elira'
        if stage == 'elira_farewell':return self.town, 'reflection'
        return None, None

    def restore(self):
        self.reset()
        world, key = self._where()
        at_visit = world is self.game.world and key is not None and self.c._near(self.points[key], 96)
        for actor, offset in ((self.c.liam, (-28, 18)), (self.c.tomas, (28, 18))):
            if actor is self.c.liam and not self.c._liam_claimed:continue
            desired = self.points[key+'_'+('liam' if actor is self.c.liam else 'tomas')] if at_visit else self.game.player.position+offset
            self.c._restore_station(actor, self.game.world, desired)
        self.sync_props()

    def finish(self, kind):
        if kind not in SCENES:return False
        previous, stage, objective = SCENES[kind]
        if self.c.stage != previous:return True
        if kind == 'departure':
            # The work fitting stays at the original bench. The same Mira must
            # actually walk there before her ordinary work animation resumes.
            self.c._mira_owned = False
            self.game.mill_quest.return_mira_to_bench()
            self.c._gathering = False
        self.reset();self.c._transition(stage, objective)
        return True

    def target(self):
        if self.c.stage == 'frame_ready':
            return 'departure' if self.game.world is self.town and self.c._near(self.c.points['workshop'], 72) else None
        if not self.active or not self.c._ready:return None
        world, key = self._where()
        if world is not self.game.world or key is None or not self.c._near(self.points[key], 72):return None
        # A scene includes only people who have actually arrived through the
        # room doors. Visiting an empty station cannot read absent speakers.
        people = ((self.halden,) if key == 'mill' else tuple(self.family.values()) if key == 'venn'
                  else (self.elira,) if key == 'elira' else ())
        if any(a not in world.npcs for a in (*people, self.c.liam, self.c.tomas)):return None
        return next((kind for kind, (previous, _, _) in SCENES.items() if previous == self.c.stage), None)

    def _optional(self, key):
        if key not in self.lines:return False
        present = {a.data['id'] for a in self.game.world.npcs}
        for line in self.lines[key]:
            speaker = line['speaker']
            if speaker == 'caelan':continue
            identifier = self.game.social.data['speakers'][speaker].get('actor_id', speaker)
            if identifier not in present:return False
        return self.c._speak(key)

    def try_conversation(self, actor):
        if not self.active and self.c.stage != 'frame_ready':return None
        target = self.c._target()
        world, key = self._where()
        if actor is self.c.mira:
            if self.c.stage == 'frame_ready':return self.c.interact() if target == 'departure' else self._optional('departure_after')
            return self._optional('departure_after')
        if actor is self.halden:
            if target in ('mill_arrival', 'mill_flour'):return self.c.interact()
            return self._optional('mill_after_visit' if self.c.stage not in ('frame_ready', 'outing', 'mill_met') else 'mill_before_visit')
        if actor in self.family.values():
            if target in ('venn_arrival', 'venn_preparations'):return self.c.interact()
            visited = self.c.stage in VILLAGE_STAGES and VILLAGE_PREFIX[self.c.stage] >= 3
            return self._optional('venn_child_after' if visited and actor is self.family['child'] else 'venn_after_visit' if visited else 'venn_before_visit')
        if actor is self.elira:
            if target and target.startswith('elira_'):return self.c.interact()
            return self._optional('elira_after_visit' if self.c.stage in ('elira_farewell', 'elira_visited') else
                                  'elira_during_visit' if self.c.stage in ('elira_welcomed', 'elira_remembering', 'elira_remembered', 'elira_ready_to_leave') else 'elira_before_visit')
        if actor in (self.c.liam, self.c.tomas):
            if target:return self.c.interact()
            if self.c.stage == 'frame_ready':return self._optional('village_liam_waiting' if actor is self.c.liam else 'village_tomas_waiting')
            if self.c.stage == 'elira_visited':return self._optional('village_after' if actor is self.c.liam else 'village_after')
            if self.c.stage in ('mill_visited', 'venn_met'):return self._optional('walk_after_mill')
            if self.c.stage in ('neighbours_visited', 'elira_welcomed', 'elira_remembering', 'elira_remembered', 'elira_ready_to_leave'):
                return self._optional('walk_after_venn') if self.game.world is self.town else self._optional('elira_before_visit' if self.c.stage == 'neighbours_visited' else 'elira_during_visit')
            return self._optional('village_liam_waiting' if actor is self.c.liam else 'village_tomas_waiting')
        return None

    def marker_for(self, identifier):
        if self.c.stage == 'frame_ready' and identifier == 'mira_worker':return '?'
        if not self.active:return NotImplemented
        if identifier == 'halden':return '?' if self.c.stage in ('outing', 'mill_met') else None
        if identifier in ('venn_mother', 'venn_father', 'venn_child'):return '?' if self.c.stage in ('mill_visited', 'venn_met') and identifier == 'venn_mother' else None
        if identifier == 'elira':return '?' if self._where()[1] == 'elira' else None
        if identifier == 'liam':return '?' if self.c.stage == 'elira_farewell' else None
        if identifier in ('mira_worker', 'tomas'):return None
        return NotImplemented

    def tracker_text(self):
        return {'outing': 'Visit Halden at the working mill with Liam and Tomas.',
                'mill_met': 'Hear how Halden is preparing the festival flour.',
                'mill_visited': 'Visit the Venn family together.',
                'venn_met': 'Spend time with the Venn family’s preparations.',
                'neighbours_visited': 'Visit Elira with Liam and Tomas.',
                'elira_welcomed': 'Look at Elira’s memorial lantern together.',
                'elira_remembering': 'Listen to Elira’s memory.',
                'elira_remembered': 'Stay with Elira a little longer.',
                'elira_ready_to_leave': 'Say goodbye to Elira.',
                'elira_farewell': 'Step outside Elira’s cottage together.',
                'elira_visited': 'You visited the village preparations and spent time with Elira.'}.get(self.c.stage, '')

    def interaction_hint(self, target):
        return {'departure': 'E: Speak with Mira before the village outing',
                'mill_arrival': 'E: Visit Halden at the mill', 'mill_flour': 'E: Hear about the festival preparations',
                'venn_arrival': 'E: Visit the Venn family', 'venn_preparations': 'E: Spend time with the family',
                'elira_welcome': 'E: Visit Elira', 'elira_lantern': 'E: Look at Elira’s lantern',
                'elira_memory': 'E: Listen to Elira', 'elira_company': 'E: Stay and talk with Elira',
                'elira_goodbye': 'E: Say goodbye', 'reflection': 'E: Speak with Liam outside'}.get(target, '')

    def update(self, seconds):
        if not self.active:return
        world, key = self._where()
        if self.game.social.locked:return
        if world is not self.game.world or key is None or not self.c._near(self.points[key], 86):
            self.reset();self.c._ready = False;self.c._follow(seconds);self.sync_props();return
        if self.zone != key:self.c.paths.clear();self.zone = key
        ready = []
        for actor, suffix in ((self.c.liam, 'liam'), (self.c.tomas, 'tomas')):
            if actor is self.c.liam and not self.c._liam_claimed:ready.append(False);continue
            arrived = self.c._travel(actor, world, seconds) and self.c._move(actor, self.points[key+'_'+suffix], seconds)
            ready.append(arrived)
            if arrived:
                toward = (self.elira.position if key == 'elira' else self.family['child'].position if key == 'venn'
                          else self.halden.position if key == 'mill' else self.game.player.position)
                actor.facing = facing_toward(pygame.Vector2(toward)-actor.position)
        self.gathered = self.c._ready = all(ready)
        self.sync_props()

    def surface_prop_visible(self, prop):
        return self.c.eligible and (self.active or self.game.quests.objective_status('CH01_MQ04', 'visit_elira') == 'completed')

    def sync_props(self):
        prepared = self.game.quests.objective_status('CH01_MQ04', 'visit_neighbours') == 'completed'
        for prop in self.surface_props:
            states = prop['states'];key = 'selected' if prepared else 'unselected'
            prop['surface'] = states.get(key, next(iter(states.values())))
