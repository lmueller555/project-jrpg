"""Recover interrupted mill investigations through the real north-trail input."""
import json
import random
import unittest
from unittest.mock import PropertyMock, patch

import test_mill_trigger_geometry as geometry
from test_mill_battle_gameplay import key, read_social, finish_mill_battle
from npc_routines import find_path
from quests import MILL_QUEST
import pygame


class MillraceDepartureTests(unittest.TestCase):
    def setUp(self):
        self.h = geometry.MillTriggerGeometryTests()
        self.h.setUp()
        self.addCleanup(self.h.doCleanups)
        self.addCleanup(self.h.tearDown)
        self.g, self.c = self.h.g, self.h.c

    def tick(self, seconds=.05, direction=(0, 0)):
        self.g.update(seconds, direction, False)

    def walk(self, goal):
        """Walk without acknowledging dialogue; leaving it must not commit it."""
        world = self.g.world
        route = find_path(world, self.g.player.position, goal, world.probe_size, None)
        self.assertIsNotNone(route)
        for corner in route:
            for _ in range(700):
                delta = pygame.Vector2(corner)-self.g.player.position
                if delta.length() < .04:break
                self.tick(min(.05, delta.length()/72), delta)
                self.assertIs(self.g.world, world)
            else:self.fail(('Walking stalled', corner, tuple(self.g.player.position)))

    def until(self, predicate):
        for _ in range(300):
            if predicate():return
            self.tick()
        self.fail(('Timed out', self.c.stage, self.c.dialogue))

    def race_directions(self):
        self.h.recruit()
        self.h.approach(self.h.wheel_approach())
        self.h.event('mechanism');read_social(self.g)
        self.h.approach((1080, 370));self.h.event('race')
        while self.g.social.page['source_line'] < len(self.c.lines['race'])-1:
            key(self.g, pygame.K_SPACE)
        self.assertIn('further upstream', self.c.lines['race'][self.g.social.page['source_line']]['text'])

    def diagnosis_directions(self):
        self.race_directions()
        while self.g.social.script_identifier != 'mill_diagnosis':
            key(self.g, pygame.K_SPACE)
        while self.g.social.page['source_line'] < len(self.c.lines['diagnosis'])-1:
            key(self.g, pygame.K_SPACE)
        self.assertEqual(self.c.inspected, {'mechanism', 'race'})
        self.assertFalse(self.c._done('diagnose_mill'))

    def north(self):
        # The visible prompt starts before the player reaches the map border.
        self.walk((720, 34))
        self.until(lambda: self.c._with_mira())
        self.assertFalse(self.g.social.locked)
        self.assertEqual(self.g.nearby_world_link()['id'], 'town_to_upstream')
        self.assertTrue(self.g.world.can_stand(self.g.player.position))

    def continue_save(self):
        self.assertTrue(self.g.save_progress())
        saved = json.loads(self.h.path.read_text())
        other = type(self.g)(fullscreen=False, start_on_title=True,
                            save_path=self.h.path, settings_path=self.h.path.with_name('settings.json'))
        other.audio.set_music(0);other.audio.set_effects(0)
        pygame.event.clear()
        self.assertTrue(other.has_saved_journey)
        # Real title-menu input and fade, rather than directly restoring quest facts.
        key(other, pygame.K_DOWN);key(other, pygame.K_RETURN)
        for _ in range(30):other.update(.05, (0, 0), False)
        self.assertFalse(other.on_title)
        self.assertEqual(other.mill_quest.to_dict(), saved['mill_quest'])
        self.assertEqual(other.quests.to_dict(), saved['quests'])
        self.assertTrue(other.world.can_stand(other.player.position))
        self.g, self.c = other, other.mill_quest
        self.h.g, self.h.c = other, other.mill_quest
        return saved

    def enter(self):
        self.assertTrue(self.c.can_enter_upstream())
        self.assertEqual(self.c.interaction_hint(), '')
        # OS key repeat must not move the player or consume a dialogue page.
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e, repeat=True))
        self.assertTrue(self.g.handle_events());self.assertIs(self.g.world, self.g.town)
        key(self.g, pygame.K_e)
        self.assertIs(self.g.world, self.c.upstream)
        self.assertEqual(list(self.g.player.position), self.c.upstream.data['spawn'])
        self.assertTrue(self.g.world.can_stand(self.g.player.position))
        self.assertIsNone(self.g.nearby_world_link())
        # Extra queued presses cannot bounce back through the reciprocal trail.
        for repeat in (True, False, False):
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e, repeat=repeat))
        self.assertTrue(self.g.handle_events())
        self.assertIs(self.g.world, self.c.upstream)
        self.assertFalse(self.g.social.active)
        self.assertFalse(self.c.combat_unlocked)

    def test_interrupted_diagnosis_recovers_at_walk_up_prompt_then_enters(self):
        self.diagnosis_directions();self.north()
        self.assertEqual(self.c.interaction_hint(), 'E: Discuss the mill with Mira')
        self.assertFalse(self.g.travel_link(self.g.nearby_world_link()))
        key(self.g, pygame.K_e)
        self.assertEqual(self.g.social.script_identifier, 'mill_diagnosis')
        self.assertFalse(self.c._done('diagnose_mill'))
        read_social(self.g)
        self.assertTrue(self.c.warned)
        self.assertTrue(self.c._done('prepare_journey'))
        self.enter()
        self.until(lambda: self.g.social.script_identifier == 'mill_encounter_intro')
        self.assertFalse(self.c.combat_unlocked)
        self.assertNotIn('intake', self.c.inspected)

    def test_unacknowledged_race_directions_do_not_bypass_inspections(self):
        self.race_directions();self.north()
        self.assertEqual(self.c.inspected, {'mechanism'})
        self.assertEqual(self.c.interaction_hint(), 'E: Ask Mira about the mill')
        before = self.c.to_dict(), self.g.quests.to_dict()
        key(self.g, pygame.K_e)
        self.assertEqual(self.g.social.script_identifier, 'mill_reminder_diagnose')
        read_social(self.g)
        self.assertEqual((self.c.to_dict(), self.g.quests.to_dict()), before)
        self.assertIs(self.g.world, self.g.town)
        self.assertFalse(self.c.can_enter_upstream())
        # Return to the actual channel, complete the inspection, and depart normally.
        self.h.approach((1080, 370));self.h.event('race');read_social(self.g)
        self.north();self.enter()

    def test_continue_preserves_pending_diagnosis_and_departure_warning(self):
        self.diagnosis_directions();self.north();self.continue_save()
        self.assertEqual(self.c.interaction_hint(), 'E: Discuss the mill with Mira')
        key(self.g, pygame.K_e)
        while self.g.social.script_identifier != 'mill_warning':key(self.g, pygame.K_SPACE)
        self.assertFalse(self.c.warned)
        self.assertFalse(self.g.travel_link(self.g.town.data['world_links'][0]))
        self.continue_save()
        self.assertEqual(self.c.stage, 'warning')
        self.assertEqual(self.c.interaction_hint(), 'E: Hear Mira before leaving town')
        key(self.g, pygame.K_e)
        self.assertEqual(self.g.social.script_identifier, 'mill_warning')
        read_social(self.g);self.enter()
        self.continue_save()
        self.assertIs(self.g.world, self.c.upstream)
        self.assertFalse(self.c.encounter_cleared)
        self.until(lambda: self.g.social.script_identifier == 'mill_encounter_intro')

    def test_mira_must_catch_up_and_opening_lock_still_blocks_travel(self):
        self.diagnosis_directions();self.north()
        self.c._place_mira(self.g.town, (720, 156))
        self.assertEqual(self.c.interaction_hint(), 'Wait for Mira to catch up.')
        key(self.g, pygame.K_e)
        self.assertFalse(self.g.social.active);self.assertIs(self.g.world, self.g.town)
        self.until(lambda: self.c._with_mira())
        key(self.g, pygame.K_e);read_social(self.g)
        link = self.g.town.data['world_links'][0]
        with patch.object(type(self.g.opening), 'locks_player', new_callable=PropertyMock, return_value=True):
            self.assertFalse(self.g.travel_link(link))
            self.assertFalse(self.g.overworld_travel.enter_region())
        self.enter()

    def test_repeated_e_cannot_skip_pending_investigation_and_warning(self):
        self.diagnosis_directions();self.north()
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e, repeat=True))
        self.assertTrue(self.g.handle_events())
        self.assertFalse(self.g.social.active)
        for repeat in (False, True, False, False, True):
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e, repeat=repeat))
        self.assertTrue(self.g.handle_events())
        self.assertEqual(self.g.social.script_identifier, 'mill_diagnosis')
        self.assertFalse(self.c._done('diagnose_mill'))
        self.assertFalse(self.c.warned)
        self.assertIs(self.g.world, self.g.town)
        while self.g.social.script_identifier != 'mill_warning':key(self.g, pygame.K_SPACE)
        page = dict(self.g.social.page)
        for _ in range(5):
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e, repeat=True))
        self.assertTrue(self.g.handle_events())
        self.assertEqual(self.g.social.page, page)
        self.assertFalse(self.c.warned)
        read_social(self.g);self.enter()

    def test_normal_departure_and_return_after_encounter_keep_mira_and_progress(self):
        self.h.diagnose();self.north();self.enter()
        self.until(lambda: self.g.social.active)
        read_social(self.g);self.assertTrue(self.g.combat.active)
        self.g.combat.model.rng = random.Random(7)
        finish_mill_battle(self.g)
        self.assertTrue(self.c.encounter_cleared);self.assertTrue(self.c.aftermath_done)
        before = self.c.to_dict(), self.g.quests.to_dict()
        self.walk((180, 532));self.until(lambda: not self.g.transfer_cooldown)
        self.assertEqual(self.g.nearby_world_link()['id'], 'upstream_to_town')
        key(self.g, pygame.K_e)
        self.assertIs(self.g.world, self.g.town)
        self.assertEqual(list(self.g.player.position), [720, 60])
        self.assertTrue(self.g.world.can_stand(self.g.player.position))
        self.assertIsNone(self.g.nearby_world_link())
        self.until(lambda: self.c.mira in self.g.town.npcs)
        self.assertEqual(sum(self.c.mira in world.npcs for world in self.g.scenes.values()), 1)
        self.assertEqual((self.c.to_dict(), self.g.quests.to_dict()), before)
        self.continue_save()
        self.north()
        key(self.g, pygame.K_e)
        self.assertIs(self.g.world, self.c.upstream)
        self.assertFalse(self.c.encounter_pending)
        self.assertEqual((self.c.to_dict(), self.g.quests.to_dict()), before)


if __name__ == '__main__':unittest.main()
