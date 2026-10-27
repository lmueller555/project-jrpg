"""Walk MQ02 using visible-object approaches, both road ends and real E input.

Only MQ01 is seeded. The reusable input driver comes from the geometry
regressions; all MQ02 progress uses production Game callbacks and clocks.
Output is confined to work/mill-trigger-check; historical reviews stay intact.
"""
import json
import os
from pathlib import Path
import sys

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT/'tests'))
import pygame
from test_mill_trigger_geometry import MillTriggerGeometryTests
from quests import MILL_QUEST

OUT = ROOT/'work/mill-trigger-check'


class Route(MillTriggerGeometryTests):
    def __init__(self):
        super().__init__()
        self.transitions = [];self.pages = [];self.events = []
        self.stills = [];self.alignment_samples = 0;self.identity_checks = 0
        self.continues = []

    def still(self, name):
        # Let genuine transient notices finish so they do not cover the object.
        for _ in range(160):
            if self.g.quest_ui.current_notice is None and not self.g.quest_ui.notices:break
            if self.g.social.active:self.read()
            self.tick(.05)
        self.g.draw();pygame.image.save(self.g.ui_surface, OUT/(name+'.png'))
        self.stills.append(name+'.png')

    def identity(self):
        self.assertEqual([actor for world in self.g.scenes.values() for actor in world.npcs
                          if actor.data['id'] == 'mira_worker'], [self.c.mira])
        self.identity_checks += 1

    def tick(self, seconds=.05, direction=(0, 0)):
        origin = self.g.world.data['id']
        was_aligning = bool(self.c.action) and self.c.action_time == 0
        super().tick(seconds, direction)
        if self.g.world.data['id'] != origin:
            self.transitions.append([origin, self.g.world.data['id']]);self.identity()
        if was_aligning:
            self.assertTrue(self.g.world.can_stand(self.g.player.position), tuple(self.g.player.position))
            self.alignment_samples += 1

    def read(self):
        for _ in range(160):
            if not self.g.social.active:return
            self.pages.append({'script': self.g.social.script_identifier,
                               'page': self.g.social.page_index,
                               'speaker': self.g.social.page['speaker']})
            self.g.social.advance()
        self.fail('Dialogue did not end')

    def event(self, kind):
        self.identity();self.still(kind+'_prompt')
        self.events.append({'kind': kind, 'scene': self.g.world.data['id'],
                            'player': list(self.g.player.position),
                            'mira': list(self.c.mira.position),
                            'hint': self.c.interaction_hint(),
                            'object_bounds': (list(self.c.interaction_bounds(kind))
                                              if kind not in ('resolution',) else None)})
        super().event(kind)

    def cross(self, upstream):
        # Use the first walkable approach before the sprite reaches the edge.
        goal = (720, 32) if upstream else (180, self.g.world.size[1]-30)
        self.approach(goal);self.still('town_boundary' if upstream else 'upstream_boundary')
        link = self.g.nearby_world_link();self.assertIsNotNone(link)
        if upstream:self.continue_saved('legacy_town_station', (720, 168))
        origin = self.g.world.data['id'];self.key()
        self.transitions.append([origin, self.g.world.data['id']])
        self.assertEqual(self.g.world.data['id'], 'upstream' if upstream else self.g.town.data['id'])
        self.assertTrue(self.g.world.can_stand(self.g.player.position))
        self.assertIsNone(self.g.nearby_world_link())
        self.until(lambda: self.c.mira in self.g.world.npcs)
        self.identity()
        if upstream:self.continue_saved('legacy_intake_station', (456, 240))

    def continue_saved(self, name, position=None):
        """Read genuine current quest facts with a previous release's standing spot."""
        self.assertTrue(self.g.save_progress())
        saved = json.loads(self.path.read_text())
        if position is not None:
            saved['player']['position'] = list(position)
            if saved['player']['scene'] == self.g.town.data['id']:
                saved['exterior_position'] = list(position)
        path = self.path.with_name(name+'.json');path.write_text(json.dumps(saved))
        other = type(self.g)(fullscreen=False, start_on_title=True, save_path=path,
                             settings_path=self.path.with_name('continue_settings.json'))
        other.audio.set_music(0);other.audio.set_effects(0)
        self.assertTrue(other.begin_journey(True), other.save_error)
        self.assertEqual(other.mill_quest.to_dict(), saved['mill_quest'])
        self.assertEqual(other.world.data['id'], saved['player']['scene'])
        self.assertTrue(other.world.can_stand(other.player.position))
        if position is not None:self.assertLess(other.player.position.distance_to(position), .1)
        if name == 'completed':
            for _ in range(200):other.update(.05, (0, 0), False)
            self.assertEqual(other.quests.status(MILL_QUEST), 'completed')
            self.assertFalse(other.social.active)
            self.assertIsNone(other.quest_ui.current_notice)
            self.assertFalse(other.quest_ui.notices)
            self.assertTrue(other.mill_quest.restored)
        self.assertEqual(sum(other.mill_quest.mira in world.npcs for world in other.scenes.values()), 1)
        self.continues.append({'name': name, 'scene': other.world.data['id'],
                               'position': list(other.player.position),
                               'mill_progress_preserved': True})

    def run_route(self):
        OUT.mkdir(parents=True, exist_ok=True);self.setUp()
        try:
            self.repair();self.cross(False)
            self.reject_empty_ground((984, 408))
            self.approach(self.wheel_approach());self.event('verify');self.read()
            self.assertTrue(self.c.verified);self.assertFalse(self.c.resolved)
            self.event('resolution');self.read()
            self.assertEqual(self.g.quests.status(MILL_QUEST), 'completed')
            self.assertTrue(self.c.resolved);self.identity();self.still('completed')
            self.assertEqual(self.transitions, [['eldenmere.playable', 'upstream'],
                                                ['upstream', 'eldenmere.playable']])
            main = ('reunion', 'mechanism', 'race', 'diagnosis', 'intake', 'prepare',
                    'spell_intro', 'encouragement', 'repair', 'verify', 'resolution')
            for kind in main:
                identifier = 'mill_'+kind
                expected = len(self.g.social._make_pages(self.c.lines[kind]))
                actual = sum(p['script'] == identifier for p in self.pages)
                self.assertEqual(actual, expected, ('Unread/replayed scene', kind, actual, expected))
            self.assertGreater(self.alignment_samples, 0)
            self.continue_saved('completed')
            proof = {'quest_id': MILL_QUEST, 'completed': True,
                     'seeded': 'MQ01 completed and MQ02 available only',
                     'input': 'normal walking, E key events, acknowledged dialogue and production action clocks',
                     'events': self.events, 'dialogue_pages': len(self.pages),
                     'main_scenes': list(main), 'pages': self.pages,
                     'world_transitions': self.transitions,
                     'safe_action_alignment_samples': self.alignment_samples,
                     'single_mira_checks': self.identity_checks,
                     'continued_saves': self.continues,
                     'completed_objectives': self.g.quests.states[MILL_QUEST]['completed_objectives'],
                     'quest_snapshot': self.c.to_dict(), 'stills': self.stills}
            (OUT/'verification.json').write_text(json.dumps(proof, indent=2)+'\n')
            print('Verified MQ02:', len(main), 'main scenes,', len(self.pages), 'dialogue pages,',
                  len(self.transitions), 'real E-key world transitions.')
            print('Single Mira and safe collision-aware action alignment verified.')
            print('Evidence:', OUT/'verification.json')
        finally:self.tearDown();self.doCleanups()


if __name__ == '__main__':Route().run_route()
