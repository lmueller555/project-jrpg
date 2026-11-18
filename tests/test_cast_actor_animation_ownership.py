"""Scene actors must not rewrite the player's travel animation format."""
import gc
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
import tempfile

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import pygame

from main import Player
from sanctuary_arrival import CastActor
from tools.capture_sanctuary_rescue import make_game, seed_victory, advance_until

ROOT = Path(__file__).resolve().parents[1]
DIRECTIONS = ('front', 'back', 'left', 'right')


class CastActorAnimationOwnershipTests(unittest.TestCase):
    def test_authored_actor_keeps_player_animation_banks_and_cadence_unchanged(self):
        surface = pygame.Surface((24, 36), pygame.SRCALPHA)
        world = SimpleNamespace(data={'spawn': (100, 100)},
                                image=lambda _: surface, can_stand=lambda _: True)
        player = Player(world)
        player.walk_durations = {'front': (140, 140, 140, 140)}
        player.pose_animations = {'rest': {'frames': (surface,), 'durations': (100,),
                                           'anchor': (12, 30), 'loop': False}}
        original_idles = dict(player.idles)
        original_walks = {direction: list(frames) for direction, frames in player.walks.items()}
        original_runs = {direction: list(frames) for direction, frames in player.runs.items()}
        original_durations = dict(player.walk_durations)
        original_pose = dict(player.pose_animations['rest'])
        art = json.loads((ROOT/'assets/story/sanctuary_rescue/art.json').read_text())['actors']['caelan']

        actor = CastActor('caelan', world, player, art=art)

        self.assertEqual(player.idles, original_idles)
        self.assertEqual(player.walks, original_walks)
        self.assertEqual(player.runs, original_runs)
        for direction in DIRECTIONS:
            self.assertEqual([duration for _, duration in player.walks[direction]], [140] * 4)
            self.assertEqual([duration for _, duration in player.runs[direction]], [100] * 4)
        self.assertEqual(player.walk_durations, original_durations)
        self.assertEqual(player.pose_animations['rest'], original_pose)
        self.assertIsNot(actor.walks, player.walks)
        self.assertIsNot(actor.walk_durations, player.walk_durations)
        for direction in DIRECTIONS:
            player.facing = direction
            player.moving = True
            for running in (False, True):
                player.running = running
                player.walk_ms = 150
                self.assertIsInstance(player.sprite(), pygame.Surface)

    def test_unmodified_actor_also_owns_its_mutable_containers(self):
        surface = pygame.Surface((24, 36), pygame.SRCALPHA)
        source = SimpleNamespace(idles={'front': surface}, walks={'front': [surface]},
                                 walk_durations={'front': (140,)},
                                 pose_animations={'rest': {'frames': (surface,), 'durations': (140,)}})
        actor = CastActor('worker', SimpleNamespace(), source)
        actor.idles['front'] = pygame.Surface((1, 1))
        actor.walks['front'].append(surface)
        actor.walk_durations['front'] = (100,)
        actor.pose_animations['rest']['loop'] = True
        self.assertIs(source.idles['front'], surface)
        self.assertEqual(source.walks['front'], [surface])
        self.assertEqual(source.walk_durations['front'], (140,))
        self.assertNotIn('loop', source.pose_animations['rest'])


class RescueMovementReturnTests(unittest.TestCase):
    def test_normal_walk_run_and_world_draw_after_pool_handoff_and_reset(self):
        directory = tempfile.TemporaryDirectory(prefix='cast-ownership-')
        self.addCleanup(directory.cleanup)
        game = make_game(directory.name, embedded=False)
        owner = game.sanctuary_rescue
        def cleanup():
            owner.reset()
            game.music.stop()
            pygame.quit()
            gc.collect()
        self.addCleanup(cleanup)
        original_walks = {direction: list(frames) for direction, frames in game.player.walks.items()}
        original_runs = {direction: list(frames) for direction, frames in game.player.runs.items()}
        seed_victory(game)
        advance_until(game, lambda: owner.stage == 'greenwell' and not owner.active)

        def move_and_draw(label):
            origin = tuple(game.player.position)
            self.assertEqual(game.player.walks, original_walks)
            self.assertEqual(game.player.runs, original_runs)
            for facing, direction in (('left', (-1, 0)), ('right', (1, 0)),
                                      ('front', (0, 1)), ('back', (0, -1))):
                for running in (False, True):
                    with self.subTest(stage=label, facing=facing, running=running):
                        game.player.position.update(origin)
                        game.update(.02, direction, running)
                        self.assertTrue(game.player.moving)
                        self.assertEqual(game.player.facing, facing)
                        self.assertIsInstance(game.player.sprite(), pygame.Surface)
                        game.draw()
            game.player.position.update(origin)
            game.player.moving = game.player.running = False

        move_and_draw('greenwell')
        self.assertTrue(game.save_progress())
        game.saved_journey = game._read_saved_journey()
        self.assertIsNotNone(game.saved_journey)
        self.assertTrue(game.begin_journey(True))
        game.transfer_cooldown = game.opening_fade = 0.
        game.update(.02, (0, 0), False)
        self.assertEqual(owner.stage, 'greenwell')
        self.assertFalse(owner.active)
        move_and_draw('greenwell Continue')
        owner._choose_departure('return')
        advance_until(game, lambda: owner.stage == 'evacuated' and not owner.active)
        game.transfer_cooldown = game.opening_fade = 0.
        move_and_draw('caretaker handoff')
        owner.reset()
        move_and_draw('scene reset')


if __name__ == '__main__':
    unittest.main()
