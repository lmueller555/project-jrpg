"""Find MQ02 by its visible objects and map edges, then use the real E input.

Approaches come from rendered art and road ends rather than reading the quest's
own interaction coordinates. This catches the misplaced-hotspot failure that a
walk-to-layout-coordinate playthrough cannot detect.
"""
import json
import os
from pathlib import Path
import tempfile
import unittest

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import pygame
import main
from npc_routines import find_path
from quests import OPENING_QUEST, MILL_QUEST

ROOT = Path(__file__).resolve().parents[1]


class MillTriggerGeometryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)/'journey.json'
        self.g = main.Game(fullscreen=False, start_on_title=False, save_path=self.path,
                           settings_path=Path(self.temp.name)/'settings.json')
        self.g.audio.set_music(0);self.g.audio.set_effects(0);pygame.event.clear()
        self.c = self.g.mill_quest
        self.assertTrue(self.g.accept_quest(OPENING_QUEST))
        for identifier in ('halden', 'elira', 'venn'):
            self.assertTrue(self.g.quests.complete_objective(OPENING_QUEST, identifier))
        self.g._sync_inventory();self.g.halden_visit.restore();self.g.elira_visit.restore();self.g.venn_visit.restore()
        self.assertTrue(self.g.quests.turn_in(OPENING_QUEST, 'mother_serene'))
        self.assertTrue(self.g.quests.unlock(MILL_QUEST))
        self.g.opening_conclusion.restore({'version': 1, 'stage': 'done'})
        self.g.opening.restore({'version': 1, 'stage': 'disabled'})
        self.g.opening_fade = 0;self.g.transfer_cooldown = 0
        self.g.social.blocked.clear();self.g.quests.drain_events();self.g.quest_ui.reset()

    def tearDown(self):pygame.quit()

    def tick(self, seconds=.05, direction=(0, 0)):
        self.g.update(seconds, direction, False)

    def until(self, predicate, seconds=60):
        for _ in range(round(seconds/.05)):
            if predicate():return
            self.tick()
        self.fail(('Timed out', self.c.stage, self.c.action, self.g.world.data['id'],
                   tuple(self.g.player.position), tuple(self.c.mira.position)))

    def walk(self, goal):
        world = self.g.world
        route = find_path(world, self.g.player.position, goal, world.probe_size, None)
        self.assertIsNotNone(route, (world.data['id'], tuple(self.g.player.position), tuple(goal)))
        for corner in route:
            for _ in range(700):
                if self.g.social.active:self.read()
                delta = pygame.Vector2(corner)-self.g.player.position
                if delta.length()<.04:break
                self.tick(min(.05, delta.length()/72), delta)
                self.assertIs(self.g.world, world)
            else:self.fail(('Walking stalled', corner, tuple(self.g.player.position)))

    def key(self):
        self.g.transfer_cooldown = 0
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e))
        self.assertTrue(self.g.handle_events())

    def read(self):
        for _ in range(160):
            if not self.g.social.active:return
            self.g.social.advance()
        self.fail('Dialogue did not end')

    def approach(self, position):
        self.walk(position)
        self.until(lambda: self.c.mira in self.g.world.npcs and
                   self.c.mira.position.distance_to(self.g.player.position)<=76)
        if self.g.social.active:self.read()

    def event(self, kind):
        self.assertIn('E:', self.c.interaction_hint())
        self.key()
        self.assertEqual(self.g.social.script_identifier, 'mill_'+kind)

    def recruit(self):
        # Only the start of the route is seeded; no MQ02 progress is fabricated.
        self.g.player.position.update(self.c.mira.position+(0, 28))
        self.key();self.assertEqual(self.g.social.script_identifier, 'mill_reunion')
        self.read();self.assertTrue(self.c.active)

    def visible(self, identifier):
        prop = next(p for p in self.c.surface_props if p['id'] == identifier)
        return prop['surface'].get_bounding_rect().move(prop['position'])

    def wheel(self):
        mill = next(e for e in self.g.town.entities if e['id'] == 'mill')
        spec = json.loads((ROOT/'assets/terrain/eldenmere/watermill/mill.json').read_text())['wheel']
        return pygame.Rect(spec['position'], spec['size']).move(mill['position'])

    def wheel_approach(self):
        rect = self.wheel()
        return rect.left-4, rect.bottom+24

    def diagnose(self):
        self.recruit();self.approach(self.wheel_approach())
        self.event('mechanism');self.read()
        # Stand on the near bank below the visible channel leaving the wheel.
        self.approach((1080, 370));self.event('race');self.read()
        self.assertEqual(self.g.quests.objective_status(MILL_QUEST, 'diagnose_mill'), 'completed')

    def cross(self, upstream):
        goal = (720, 12) if upstream else (180, self.g.world.size[1]-30)
        self.approach(goal)
        link = self.g.nearby_world_link();self.assertIsNotNone(link)
        self.key()
        self.assertEqual(self.g.world.data['id'], 'upstream' if upstream else self.g.town.data['id'])
        self.assertTrue(self.g.world.can_stand(self.g.player.position))
        self.assertIsNone(self.g.nearby_world_link(), 'Arrival must not immediately offer the return trip')
        self.until(lambda: self.c.mira in self.g.world.npcs)
        self.assertEqual(sum(self.c.mira in world.npcs for world in self.g.scenes.values()), 1)

    def reach_intake(self):
        self.diagnose();self.cross(True)
        rect = self.visible('intake_screen')
        self.approach((rect.left-17, rect.bottom-9));self.event('intake');self.read()

    def prepare(self):
        self.reach_intake();rect = self.visible('bypass')
        self.approach((rect.left-12, rect.bottom-10));self.event('prepare');self.read()
        self.until(lambda: self.c.prepared);self.assertFalse(self.c.mill_restored)

    def cast(self):
        self.prepare();rect = self.visible('inspection_pool')
        self.approach((rect.left+10, rect.bottom+6));self.event('spell_intro');self.read()
        self.until(lambda: self.c.spell_done);self.read()
        self.assertTrue(self.c.encouraged)

    def repair(self):
        self.cast();rect = self.visible('lever')
        self.approach((rect.left-16, rect.bottom-13));self.event('repair');self.read()
        self.until(lambda: self.c.restored)

    def reject_empty_ground(self, position):
        self.approach(position)
        self.assertIsNone(self.c._target(), ('Trigger on empty ground', position, self.c._target()))
        self.assertEqual(self.c.interaction_hint(), '')

    def test_interaction_geometry_follows_actual_wheel_and_visible_prop_pixels(self):
        self.assertEqual(self.c.interaction_bounds('mechanism'), self.wheel())
        self.assertEqual(self.c.interaction_bounds('verify'), self.wheel())
        for kind, identifier in (('intake', 'intake_screen'), ('prepare', 'bypass'),
                                  ('spell_intro', 'inspection_pool'), ('repair', 'lever')):
            with self.subTest(kind=kind):
                self.assertEqual(self.c.interaction_bounds(kind), self.visible(identifier))

    def test_trails_reach_map_edges_and_reciprocal_spawns_are_clear(self):
        town_link = self.g.town.data['world_links'][0]
        upstream_link = self.c.upstream.data['world_links'][0]
        self.assertLessEqual(town_link['position'][1], self.g.town.data['tile_size'])
        self.assertLessEqual(self.c.upstream.size[1]-upstream_link['position'][1],
                             2*self.c.upstream.data['tile_size'])
        self.assertTrue(self.g.town.can_stand(town_link['position']))
        self.assertTrue(self.c.upstream.can_stand(upstream_link['position']))
        for origin, link, destination, reverse in (
                (self.g.town, town_link, self.c.upstream, upstream_link),
                (self.c.upstream, upstream_link, self.g.town, town_link)):
            with self.subTest(origin=origin.data['id']):
                self.assertTrue(destination.can_stand(link['spawn']))
                self.assertGreater(pygame.Vector2(link['spawn']).distance_to(reverse['position']), reverse['radius'])

    def test_former_town_hotspot_no_longer_offers_or_activates_travel(self):
        self.recruit();self.approach((720, 168))
        self.assertIsNone(self.g.nearby_world_link())
        world = self.g.world;position = self.g.player.position.copy()
        self.key();self.assertIs(self.g.world, world);self.assertEqual(self.g.player.position, position)

    def test_real_e_crosses_both_physical_boundaries_with_same_mira(self):
        self.diagnose();mira = self.c.mira
        self.cross(True);self.cross(False)
        self.assertIs(self.c.mira, mira)
        self.assertFalse(self.c.restored)

    def test_inspections_are_found_at_wheel_and_channel_instead_of_empty_yard(self):
        self.recruit();self.reject_empty_ground((960, 384))
        self.approach(self.wheel_approach())
        self.event('mechanism');self.g.social.cancel()
        self.assertNotIn('mechanism', self.c.inspected)
        self.g.social.blocked.clear();self.event('mechanism');self.read()
        self.approach((1080, 370));self.event('race');self.read()
        self.assertEqual(self.g.quests.objective_status(MILL_QUEST, 'diagnose_mill'), 'completed')

    def test_intake_inspection_is_beside_visible_screen_and_cancel_safe(self):
        self.diagnose();self.cross(True);self.reject_empty_ground((456, 240))
        rect = self.visible('intake_screen');self.approach((rect.left-17, rect.bottom-9))
        self.event('intake');self.g.social.cancel()
        self.assertNotIn('intake', self.c.inspected)
        self.g.social.blocked.clear();self.event('intake');self.read()
        self.assertIn('intake', self.c.inspected)

    def test_bypass_prompt_is_at_handle_and_action_walks_to_existing_contact(self):
        self.reach_intake();self.reject_empty_ground((456, 288))
        rect = self.visible('bypass');self.approach((rect.left-12, rect.bottom-10))
        self.event('prepare');self.g.social.cancel();self.assertFalse(self.c.prepared)
        self.g.social.blocked.clear();self.event('prepare');self.read()
        self.assertEqual(self.c.action, 'prepare');self.assertFalse(self.c.prepared)
        self.until(lambda: self.c.prepared)
        self.assertLess(self.g.player.position.distance_to((456, 288)), .3)
        self.assertLess(self.c.mira.position.distance_to(self.c.layout['mira_bypass']), .3)
        self.assertFalse(self.c.restored)

    def test_pool_can_be_used_from_below_without_cutting_through_stone(self):
        self.prepare();self.reject_empty_ground((456, 336))
        rect = self.visible('inspection_pool');self.approach((rect.left+10, rect.bottom+6))
        start = self.g.player.position.copy()
        self.event('spell_intro');self.read();self.assertEqual(self.c.action, 'spell')
        visited = []
        for _ in range(400):
            if self.c.spell_done:break
            self.tick();visited.append(tuple(self.g.player.position))
            self.assertTrue(self.g.world.can_stand(self.g.player.position), tuple(self.g.player.position))
        self.assertTrue(self.c.spell_done);self.assertGreater(len(set(visited)), 3)
        self.assertNotEqual(self.g.player.position, start)
        self.assertLess(self.g.player.position.distance_to((480, 336)), .3)
        self.assertFalse(self.c.restored);self.read()

    def test_haul_prompt_is_at_visible_lever_and_preserves_rope_contacts(self):
        self.cast();self.reject_empty_ground((456, 384))
        rect = self.visible('lever');self.approach((rect.left-16, rect.bottom-13))
        self.event('repair');self.g.social.cancel();self.assertFalse(self.c.restored)
        self.g.social.blocked.clear();self.event('repair');self.read()
        self.until(lambda: self.c.restored)
        self.assertLess(self.g.player.position.distance_to((456, 384)), .3)
        self.assertLess(self.c.mira.position.distance_to(self.c.layout['mira_lever']), .3)

    def test_return_inspection_uses_same_wheel_and_final_speakers_are_present(self):
        self.repair();self.cross(False);self.reject_empty_ground((984, 408))
        self.approach(self.wheel_approach());self.event('verify');self.read()
        self.assertTrue(self.c.verified);self.assertFalse(self.c.resolved)
        self.assertIn(self.c.halden, self.g.world.npcs)
        self.assertIn(self.c.mira, self.g.world.npcs)
        self.assertLess(self.c.halden.position.distance_to(self.g.player.position), 44)
        self.event('resolution');self.read()
        self.assertTrue(self.c.resolved)
        self.assertEqual(self.g.quests.status(MILL_QUEST), 'completed')
        self.assertEqual(sum(self.c.mira in world.npcs for world in self.g.scenes.values()), 1)


if __name__ == '__main__':unittest.main()
