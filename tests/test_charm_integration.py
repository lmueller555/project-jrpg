"""Regional charm wiring preserves input batches, journeys, and preview isolation."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

import pygame

from main import Game
from overworld_travel import OverworldTravel, WORLD_ID


class CharmIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='charm-integration-')
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name)/'journey.json'
        self.settings_path = Path(self.directory.name)/'settings.json'
        self.games = []

    def tearDown(self):
        for game in self.games:
            if game.gallery_session is not None:game.gallery_session.close()
            game.opening_audio.reset();game.regional_audio.reset();game.music.stop()
        self.games.clear()
        pygame.quit()

    def game(self, *, title=False, region=False):
        game = Game(fullscreen=False, start_on_title=title, save_path=self.path,
                    settings_path=self.settings_path)
        game.audio.set_music(0);game.audio.set_effects(0)
        game.opening_fade = game.transfer_cooldown = 0
        self.games.append(game)
        if region:game.world = game.overworld_world
        pygame.event.clear()
        return game

    @staticmethod
    def key(key, *, repeat=False):
        return pygame.event.Event(pygame.KEYDOWN, key=key, repeat=repeat)

    def sit(self, game):
        from regional_participation import STAND_POSITION
        game.player.position.update(STAND_POSITION)
        self.assertTrue(game.handle_events([self.key(pygame.K_e)]))
        self.assertTrue(game.world.participation.state['seated'])

    def test_final_dialogue_e_consumes_remaining_world_interactions_in_batch(self):
        game = self.game()
        self.assertTrue(game.social.start_script(
            [{'speaker': 'road_guard', 'text': 'A short final page.'}], identifier='charm_batch'))
        with patch.object(game.overworld_travel, 'interact', return_value=True) as interact:
            game.handle_events([self.key(pygame.K_e), self.key(pygame.K_e)])
        self.assertFalse(game.social.locked)
        interact.assert_not_called()

    def test_double_e_sits_once_and_next_double_e_stands_without_resitting(self):
        from regional_participation import STAND_POSITION
        game = self.game(region=True)
        controller = game.world.participation
        game.player.position.update(STAND_POSITION)
        with patch.object(controller, 'interact', wraps=controller.interact) as interact:
            game.handle_events([self.key(pygame.K_e), self.key(pygame.K_e)])
            self.assertEqual(interact.call_count, 1)
        self.assertTrue(controller.state['seated'])
        self.assertLess(game.player.position.distance_to(STAND_POSITION), .001)
        self.assertIs(game.player.story_sprite, controller.sit_sprite)
        with patch.object(game.overworld_travel, 'interact', wraps=game.overworld_travel.interact) as interact:
            game.handle_events([self.key(pygame.K_e), self.key(pygame.K_e)])
            interact.assert_not_called()
        self.assertFalse(controller.state['seated'])
        self.assertTrue(game.world.can_stand(game.player.position))
        self.assertLess(game.player.position.distance_to(STAND_POSITION), .001)

    def test_guard_proximity_uses_live_actor_feet_instead_of_authored_posts(self):
        game = self.game(region=True)
        gate = game.world.gates[0]
        guards = [actor for actor in game.world.npcs
                  if actor.data['id'].startswith('road_guard:'+gate['id']+':')]
        original = [actor.position.copy() for actor in guards]
        try:
            for actor in guards:actor.position += (320, 120)
            game.player.position.update(guards[0].position+(0, 24))
            self.assertIs(game.overworld_travel.nearby_guard(), gate)
            game.player.position.update(original[0]+(0, 24))
            self.assertIsNone(game.overworld_travel.nearby_guard())
        finally:
            for actor, position in zip(guards, original):actor.position.update(position)

    def test_seated_journey_requires_matching_player_scene_position_and_facing(self):
        game = self.game(region=True)
        self.sit(game)
        self.assertTrue(game.save_progress())
        original = copy.deepcopy(game.saved_journey)
        self.assertTrue(OverworldTravel.valid_journey(original))
        for field, value in (('scene', game.town.data['id']),
                             ('position', [0, 0]), ('facing', 'back')):
            with self.subTest(field=field):
                data = copy.deepcopy(original)
                data['player'][field] = value
                self.assertFalse(OverworldTravel.valid_journey(data))

    def test_first_regional_save_and_legacy_missing_charm_fields_continue(self):
        game = self.game(region=True)
        game.player.position.update(game.world.data['spawn'])
        self.assertTrue(game.save_progress())
        current = copy.deepcopy(game.saved_journey)
        self.assertIn('checkpoint_charm', current['overworld'])
        self.assertIn('participation', current['overworld'])
        for legacy in (False, True):
            with self.subTest(legacy=legacy):
                payload = copy.deepcopy(current)
                if legacy:
                    del payload['overworld']['checkpoint_charm']
                    del payload['overworld']['participation']
                self.path.write_text(json.dumps(payload), encoding='utf-8')
                resumed = self.game(title=True)
                self.assertTrue(resumed.has_saved_journey, resumed.save_error)
                self.assertIsNone(resumed._overworld_world)
                self.assertTrue(resumed.begin_journey(True))
                self.assertEqual(resumed.world.data['id'], WORLD_ID)
                self.assertEqual(resumed.world.checkpoint_charm.state['stage'], 'idle')
                self.assertFalse(resumed.world.participation.state['seated'])
                self.assertIn('checkpoint_charm', resumed.saved_journey['overworld'])
                self.assertIn('participation', resumed.saved_journey['overworld'])

    def test_seated_continue_restores_pose_after_story_staging(self):
        game = self.game(region=True)
        self.sit(game)
        self.assertTrue(game.save_progress())
        expected = copy.deepcopy(game.saved_journey)
        resumed = self.game(title=True)
        self.assertTrue(resumed.has_saved_journey, resumed.save_error)
        self.assertTrue(resumed.begin_journey(True))
        self.assertEqual(list(resumed.player.position), expected['player']['position'])
        self.assertEqual(resumed.player.facing, expected['player']['facing'])
        self.assertEqual(resumed.world.participation.to_dict(), expected['overworld']['participation'])
        self.assertIs(resumed.player.story_sprite, resumed.world.participation.sit_sprite)

    def test_cosmetic_clock_and_cooldown_updates_do_not_dirty_game_progress(self):
        from checkpoint_charm import WITNESS
        game = self.game(region=True)
        game.player.position.update(WITNESS)
        game.world.participation.state['cat_greeted'] = True
        game.world.participation.state['cat_cooldown'] = 8.
        self.assertTrue(game.overworld_travel.interact())
        # Discover the checkpoint before measuring cosmetic updates.
        game.update(.01, (0, 0), False)
        self.assertTrue(game.save_progress())
        before = game._progress_signature()
        scene_before = game.world.checkpoint_charm.to_dict()
        with patch.object(game.save_store, 'write', wraps=game.save_store.write) as write:
            for _ in range(10):game.update(.01, (0, 0), False)
            write.assert_not_called()
        self.assertGreater(game.elapsed_ms, 0)
        self.assertLess(game.world.participation.state['cat_cooldown'], 8.)
        self.assertNotEqual(game.world.checkpoint_charm.to_dict(), scene_before)
        self.assertEqual(game._progress_signature(), before)

    def test_checkpoint_gallery_restart_completion_and_escape_preserve_parent(self):
        seed = self.game(region=True)
        self.assertTrue(seed.save_progress())
        game = self.game(title=True)
        world = game.overworld_world
        before = (game._progress_signature(), copy.deepcopy(game.saved_journey),
                  world.checkpoint_charm.to_dict(), world.participation.to_dict(),
                  tuple((id(actor), tuple(actor.position)) for actor in world.npcs))
        saved_bytes = self.path.read_bytes()
        settings_bytes = self.settings_path.read_bytes()
        self.assertTrue(game.open_gallery())
        self.assertTrue(game.launch_gallery_scene('checkpoint_borrowed_seat'))
        first = game.gallery_session
        self.assertIsNot(first.game.world, world)
        self.assertFalse(first.game.save_store.enabled)
        game.update(.1)
        self.assertTrue(game.handle_events([self.key(pygame.K_r), self.key(pygame.K_e)]))
        second = game.gallery_session
        self.assertIsNot(second, first)
        self.assertTrue(first.closed)
        self.assertIsNot(second.game.world, first.game.world)
        controller = second.game.world.checkpoint_charm
        for _ in range(1200):
            if game.gallery_session is None:break
            if second.game.social.active:
                game.handle_events([self.key(pygame.K_e), self.key(pygame.K_e)])
            game.update(.1, (1, 0), True)
        else:self.fail('Checkpoint Gallery scene did not return to its catalogue')
        self.assertEqual(controller.state['stage'], 'done')
        self.assertFalse(second.game.social.locked)
        self.assertTrue(game.on_gallery)
        self.assertTrue(game.launch_gallery_scene('checkpoint_borrowed_seat'))
        escaped = game.gallery_session
        self.assertTrue(game.handle_events([self.key(pygame.K_ESCAPE), self.key(pygame.K_e)]))
        self.assertIsNone(game.gallery_session)
        self.assertTrue(escaped.closed)
        self.assertEqual(self.path.read_bytes(), saved_bytes)
        self.assertEqual(self.settings_path.read_bytes(), settings_bytes)
        after = (game._progress_signature(), game.saved_journey,
                 world.checkpoint_charm.to_dict(), world.participation.to_dict(),
                 tuple((id(actor), tuple(actor.position)) for actor in world.npcs))
        self.assertEqual(after, before)

    def test_checkpoint_gallery_exit_releases_contact_voice_and_preserves_other_audio(self):
        game = self.game(title=True)
        game.audio.set_effects(1)
        self.assertTrue(game.open_gallery())
        self.assertTrue(game.launch_gallery_scene('checkpoint_borrowed_seat'))
        child = game.gallery_session.game
        sentinel = pygame.mixer.Sound(buffer=bytes(4096))
        unrelated = sentinel.play(loops=-1)
        self.assertIsNotNone(unrelated)
        try:
            for _ in range(180):
                if child.social.active:game.handle_events([self.key(pygame.K_SPACE)])
                game.update(.1)
                if any(key.startswith('checkpoint_contact_') for key in child.regional_audio.voices):break
            else:self.fail('The production checkpoint contact never acquired an audio voice')
            owned = [(channel, sound) for _, channel, sound, _
                     in child.regional_audio.voices.values()]
            self.assertTrue(game.handle_events([self.key(pygame.K_ESCAPE)]))
            self.assertFalse(child.regional_audio.voices)
            self.assertFalse(child.regional_audio.cooldowns)
            self.assertTrue(all(channel.get_sound() is not sound or not channel.get_busy()
                                for channel, sound in owned))
            self.assertIs(unrelated.get_sound(), sentinel)
            self.assertTrue(unrelated.get_busy())
            self.assertTrue(game.on_gallery)
        finally:sentinel.stop()


if __name__ == '__main__':unittest.main()
