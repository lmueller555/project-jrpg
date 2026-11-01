"""Optional gestures preserve collision, actor ownership and first checkpoints."""
import json
import math
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
import pygame

from main import Game
from overworld_travel import OverworldTravel
from purposeful_wildlife import valid_state as valid_wildlife
from regional_participation import (BENCH_POSITION, STAND_POSITION, CAT_SCRIPT,
    MASONRY_SCRIPT, empty_state, valid_state, valid_context, progress_state)
from tools.capture_lantern_quest import seed_previous_quests


class RegionalParticipationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.g = self.make_game()
        seed_previous_quests(self.g)
        self.g.world = self.g.overworld_world
        self.c = self.g.world.participation
        self.g.player.position.update(STAND_POSITION)

    def tearDown(self):pygame.quit()

    def make_game(self, title=False):
        g = Game(fullscreen=False, start_on_title=title,
                 save_path=self.root/'journey.json', settings_path=self.root/'settings.json')
        g.audio.set_music(0);g.audio.set_effects(0)
        g.opening_fade = g.transfer_cooldown = 0
        return g

    def complete_dialogue(self):
        while self.g.social.active:self.g.social.advance()

    def seat(self):
        self.assertEqual(self.c.selected_target(self.g), 'bench')
        self.assertTrue(self.c.interact(self.g))
        self.assertTrue(self.c.locks_player)

    def test_sitting_uses_clear_feet_and_one_positional_contact(self):
        self.assertTrue(self.g.world.can_stand(STAND_POSITION))
        self.assertFalse(self.g.world.can_stand(BENCH_POSITION))
        with mock.patch.object(self.g.regional_audio, 'play', return_value=False) as play:
            self.seat()
            self.assertEqual(play.call_count, 1)
            source = play.call_args.args[0]
            self.assertEqual(source.point(), BENCH_POSITION)
            self.assertEqual(source.sound, 'creak')
            self.assertGreater(source.cooldown, 0)
            for _ in range(20):self.c.update(.1, self.g)
            self.assertEqual(play.call_count, 1)
            repeated = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e, repeat=True)
            self.assertTrue(self.c.handle_event(self.g, repeated))
            self.assertTrue(self.c.locks_player)
        self.assertEqual(tuple(self.g.player.position), STAND_POSITION)
        self.assertIs(self.g.player.story_sprite, self.c.sit_sprite)
        self.assertNotEqual(self.g.player.story_position, self.g.player.position)
        self.assertEqual(self.c.interaction_hint(self.g), 'E: Stand up')
        self.assertTrue(self.c.handle_event(self.g, pygame.event.Event(
            pygame.KEYDOWN, key=pygame.K_ESCAPE)))
        self.assertFalse(self.c.locks_player)
        self.assertIsNone(self.g.player.story_sprite)
        self.assertTrue(self.g.world.can_stand(self.g.player.position))

    def test_pause_keeps_seat_and_movement_or_travel_releases_it(self):
        self.seat();snapshot = self.c.to_dict()
        self.g.pause.is_open = True
        self.c.update(8000., self.g)
        self.assertEqual(snapshot, self.c.to_dict())
        self.assertFalse(self.c.request_movement(self.g, (1, 0)))
        self.assertFalse(self.c.handle_event(self.g, pygame.event.Event(
            pygame.KEYDOWN, key=pygame.K_ESCAPE)))
        self.g.pause.is_open = False
        self.assertTrue(self.c.request_movement(self.g, (1, 0)))
        self.assertFalse(self.c.locks_player)
        self.seat()
        self.c.before_travel(self.g)
        self.g.world = self.g.town
        self.c.update(0, self.g)
        self.assertFalse(self.c.locks_player)
        self.assertIsNone(self.g.player.story_sprite)

    def test_dynamic_obstruction_gets_clear_nearby_standing_point(self):
        self.seat()
        clear = self.g.world.can_stand
        def blocked_approach(point, *args, **kwargs):
            return math.dist(point, STAND_POSITION) > 2 and clear(point, *args, **kwargs)
        with mock.patch.object(self.g.world, 'can_stand', side_effect=blocked_approach):
            self.assertTrue(self.c.cancel(self.g))
            self.assertTrue(self.g.world.can_stand(self.g.player.position))
        self.assertLess(self.g.player.position.distance_to(STAND_POSITION), 12)
        self.assertFalse(self.c.locks_player)

    def test_interruption_releases_own_pose_without_erasing_new_owner(self):
        self.seat()
        foreign = pygame.Surface((24, 36), pygame.SRCALPHA)
        foreign_position = pygame.Vector2(1830, -500)
        self.g.player.story_sprite = foreign
        self.g.player.story_position = foreign_position
        self.c.update(0, self.g)
        self.assertFalse(self.c.locks_player)
        self.assertIs(self.g.player.story_sprite, foreign)
        self.assertIs(self.g.player.story_position, foreign_position)

    def test_restore_rebinds_exact_pose_without_replaying_audio(self):
        self.seat();snapshot = self.c.to_dict()
        self.c.restore(snapshot)
        self.assertIsNone(self.g.player.story_sprite)
        with mock.patch.object(self.g.regional_audio, 'play') as play:
            self.c.update(0, self.g)
            self.assertFalse(play.called)
        self.assertEqual(snapshot, self.c.to_dict())
        self.assertIs(self.g.player.story_sprite, self.c.sit_sprite)
        self.g.player.position.x += 40
        self.c.update(0, self.g)
        self.assertFalse(self.c.locks_player)
        self.assertNotEqual(tuple(self.g.player.position), STAND_POSITION)

    def test_cat_acknowledgement_keeps_wildlife_and_worker_owners(self):
        cat = self.g.world.wildlife.by_id['farm_cat']
        worker = self.g.world.wildlife.worker
        self.g.player.position.update(-420, 1200)
        garden = self.g.world.garden_orchard.to_dict()
        self.assertIn('farm cat', self.c.interaction_hint(self.g))
        self.assertTrue(self.c.interact(self.g))
        self.assertEqual(self.g.social.script_identifier, CAT_SCRIPT)
        self.complete_dialogue()
        self.assertIs(cat, self.g.world.wildlife.by_id['farm_cat'])
        self.assertEqual(cat.state['mode'], 'stretch')
        self.assertTrue(self.c.state['cat_greeted'])
        self.assertEqual(garden, self.g.world.garden_orchard.to_dict())
        self.assertFalse(worker.wildlife_owned)
        self.assertTrue(valid_wildlife(self.g.world.wildlife.to_dict()))
        self.assertFalse(self.c.interact(self.g))
        for _ in range(450):
            self.g.world.wildlife.update(.1, self.g)
            self.c.update(.1, self.g)
            self.assertTrue(valid_wildlife(self.g.world.wildlife.to_dict()))
        self.assertEqual(garden, self.g.world.garden_orchard.to_dict())

    def test_cat_moving_or_worker_loan_hides_the_same_target_it_rejects(self):
        self.g.player.position.update(-420, 1200)
        cat = self.g.world.wildlife.by_id['farm_cat']
        cat.state['mode'] = 'walk'
        self.assertEqual(self.c.interaction_hint(self.g), '')
        self.assertFalse(self.c.interact(self.g))
        cat.state['mode'] = 'sleep'
        self.g.world.wildlife.vignette['phase'] = 'visit'
        self.assertEqual(self.c.interaction_hint(self.g), '')
        self.assertFalse(self.c.interact(self.g))

    def test_cancelled_cat_greeting_keeps_the_exact_animal_snapshot(self):
        self.g.player.position.update(-420, 1200)
        before = self.g.world.wildlife.to_dict()
        self.assertTrue(self.c.interact(self.g))
        self.assertEqual(self.c.interaction_hint(self.g), '')
        self.assertFalse(self.c.interact(self.g))
        self.assertTrue(self.g.social.cancel_script())
        self.assertEqual(before, self.g.world.wildlife.to_dict())
        self.assertFalse(self.c.state['cat_greeted'])
        self.assertEqual(self.c.state['cat_cooldown'], 0)

    def test_masonry_inspection_observes_without_changing_crew_or_quests(self):
        self.g.player.position.update(-2420, 640)
        crew = self.g.world.bridge_crew
        before = crew.to_dict();quests = self.g.quests.to_dict()
        flags = set(self.g.social.flags)
        self.assertTrue(self.g.world.can_stand(self.g.player.position))
        self.assertEqual(self.c.selected_target(self.g), 'masonry')
        self.assertIn('unfinished masonry', self.c.interaction_hint(self.g))
        self.assertTrue(self.c.interact(self.g))
        self.assertEqual(self.g.social.script_identifier, MASONRY_SCRIPT)
        self.complete_dialogue()
        self.assertTrue(self.c.state['masonry_read'])
        self.assertEqual(before, crew.to_dict())
        self.assertEqual(quests, self.g.quests.to_dict())
        self.assertEqual(flags, self.g.social.flags)
        crew.stage = 'request'
        self.assertEqual(self.c.interaction_hint(self.g), '')
        self.assertFalse(self.c.interact(self.g))
        crew.stage = 'ready'
        crew.mason.position.update(self.g.player.position+(20, 0))
        self.assertEqual(self.c.interaction_hint(self.g), '')
        self.assertFalse(self.c.interact(self.g))

    def test_busy_ui_hides_and_rejects_interaction(self):
        for owner, key in ((self.g.pause, 'is_open'), (self.g, 'map_open'),
                           (self.g.inventory_ui, 'is_open'),
                           (self.g.quest_ui, 'journal_open')):
            with self.subTest(key=key):
                original = getattr(owner, key)
                setattr(owner, key, True)
                self.assertEqual(self.c.interaction_hint(self.g), '')
                self.assertFalse(self.c.interact(self.g))
                setattr(owner, key, original)
        with mock.patch.object(type(self.g.combat), 'active',
                               new_callable=mock.PropertyMock, return_value=True):
            self.assertEqual(self.c.interaction_hint(self.g), '')
            self.assertFalse(self.c.interact(self.g))

    def test_exact_first_seat_checkpoint_after_long_idle_continues(self):
        self.c.update(90000., self.g)
        self.assertTrue(self.g.save_progress())
        path = self.g.save_store.path;writes = []
        original = self.g.save_store.write
        def first(payload):
            result = original(payload)
            if not writes:writes.append(path.read_bytes())
            return result
        with mock.patch.object(self.g.save_store, 'write', side_effect=first) as write:
            self.seat()
        self.assertEqual(write.call_count, 1)
        payload = json.loads(writes[0])
        self.assertTrue(OverworldTravel.valid_journey(payload))
        self.assertEqual(payload['overworld']['participation'], self.c.to_dict())
        self.assertEqual(path.read_bytes(), writes[0])
        resumed = self.make_game(True)
        self.assertTrue(resumed.has_saved_journey, resumed.save_error)
        self.assertTrue(resumed.begin_journey(True))
        self.assertEqual(resumed.world.participation.to_dict(), self.c.to_dict())
        self.assertEqual(tuple(resumed.player.position), STAND_POSITION)
        self.assertIs(resumed.player.story_sprite, resumed.world.participation.sit_sprite)
        self.assertTrue(resumed.world.can_stand(resumed.player.position))

    def test_first_cat_contact_after_long_idle_continues_exactly(self):
        self.g.player.position.update(-420, 1200)
        cat = self.g.world.wildlife.by_id['farm_cat']
        cat.state.update(clock=59.95, elapsed=20.)
        self.assertTrue(self.g.save_progress())
        self.assertTrue(self.c.interact(self.g))
        path = self.g.save_store.path;writes = []
        original = self.g.save_store.write
        def first(payload):
            result = original(payload)
            if not writes:writes.append(path.read_bytes())
            return result
        with mock.patch.object(self.g.save_store, 'write', side_effect=first) as write:
            self.complete_dialogue()
        self.assertEqual(write.call_count, 1)
        payload = json.loads(writes[0])
        self.assertTrue(OverworldTravel.valid_journey(payload))
        self.assertTrue(valid_wildlife(payload['overworld']['wildlife']))
        self.assertEqual(payload['overworld']['participation'], self.c.to_dict())
        expected = self.g.world.wildlife.to_dict()
        self.assertEqual(path.read_bytes(), writes[0])
        resumed = self.make_game(True)
        self.assertTrue(resumed.has_saved_journey, resumed.save_error)
        self.assertTrue(resumed.begin_journey(True))
        self.assertEqual(resumed.world.wildlife.to_dict(), expected)
        self.assertEqual(resumed.world.participation.to_dict(), self.c.to_dict())

    def test_state_validation_rejects_cross_scene_seat_and_nonfinite_timers(self):
        state = empty_state()
        self.assertTrue(valid_state(state))
        state.update(seated=True, sat=True)
        player = {'scene': 'auratia.overworld', 'position': list(STAND_POSITION), 'facing': 'front'}
        self.assertTrue(valid_context(state, player))
        for change in ({'scene': 'eldenmere'}, {'position': list(BENCH_POSITION)}, {'facing': 'back'}):
            self.assertFalse(valid_context(state, {**player, **change}))
        for timer in (float('nan'), float('inf'), -1., 9., True):
            broken = {**state, 'cat_cooldown': timer}
            self.assertFalse(valid_state(broken))
        self.assertFalse(valid_state({**state, 'sat': False}))
        self.assertFalse(valid_state({**state, 'cat_cooldown': 2.}))
        self.assertFalse(valid_state({**state, 'unexpected': False}))

    def test_cooldown_snapshot_is_exact_but_does_not_dirty_idle_progress(self):
        self.c.state.update(cat_greeted=True, cat_cooldown=8.)
        before = self.c.to_dict();progress = self.c.progress_dict()
        self.c.update(100000., self.g)
        self.assertTrue(valid_state(self.c.to_dict()))
        self.assertLess(self.c.to_dict()['cat_cooldown'], before['cat_cooldown'])
        self.assertEqual(progress, self.c.progress_dict())
        self.assertEqual(progress, progress_state(before))
        self.assertNotEqual(before, self.c.to_dict())


if __name__ == '__main__':unittest.main()
