"""Battle entry preserves the approach, input isolation and a readable reveal."""
import os
from pathlib import Path
import random
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame

from battle_transition import BattleTransition, SHADE
from main import Game
from test_mill_battle_gameplay import seed_completed_mill


class CurtainTests(unittest.TestCase):
    def setUp(self):
        self.world = pygame.Surface((480, 320));self.world.fill('#527e42')
        self.battle = pygame.Surface((480, 320));self.battle.fill('#849dc1')

    def test_world_frame_is_independent_and_starts_without_a_battle_cut(self):
        transition = BattleTransition(self.world)
        self.world.fill('magenta')
        result = self.battle.copy();transition.draw(result)
        self.assertEqual(result.get_at((240, 160)), pygame.Color('#527e42'))
        self.assertEqual(result.get_at((0, 0)), pygame.Color('#527e42'))
        self.assertTrue(transition.active)

    def test_solid_curtain_closes_then_fully_covers_before_battle_reveal(self):
        transition = BattleTransition(self.world)
        transition.update(transition.close_seconds / 2)
        result = self.battle.copy();transition.draw(result)
        self.assertEqual(result.get_at((10, 10))[:3], SHADE)
        self.assertEqual(result.get_at((470, 310)), pygame.Color('#527e42'))
        transition.update(transition.close_seconds / 2)
        result = self.battle.copy();transition.draw(result)
        self.assertEqual(transition.phase, 'covered')
        self.assertEqual(result.get_at((470, 310))[:3], SHADE)
        transition.update(transition.hold_seconds + transition.reveal_seconds / 2)
        result = self.battle.copy();transition.draw(result)
        self.assertEqual(transition.phase, 'revealing')
        self.assertNotEqual(result.get_at((240, 160))[:3], SHADE)
        self.assertNotEqual(result.get_at((240, 160)), self.battle.get_at((240, 160)))
        transition.update(transition.reveal_seconds)
        result = self.battle.copy();transition.draw(result)
        self.assertEqual(pygame.image.tobytes(result, 'RGB'), pygame.image.tobytes(self.battle, 'RGB'))

    def test_reduced_motion_uses_a_short_uniform_fade(self):
        transition = BattleTransition(self.world, reduced_motion=True)
        self.assertLess(transition.duration, .3)
        transition.update(transition.close_seconds / 2)
        result = self.battle.copy();transition.draw(result)
        self.assertEqual(result.get_at((20, 20)), result.get_at((460, 300)))
        self.assertNotEqual(result.get_at((20, 20)), self.world.get_at((20, 20)))

    def test_transition_can_resize_and_pause_without_advancing_its_frame(self):
        transition = BattleTransition(self.world)
        transition.update(.12)
        elapsed = transition.elapsed
        transition.update(5, paused=True)
        self.assertEqual(transition.elapsed, elapsed)
        for size in ((480, 320), (960, 640), (800, 600), (320, 480)):
            target = pygame.Surface(size)
            transition.draw(target)
            self.assertEqual(target.get_at((0, 0))[:3], SHADE)
            self.assertEqual(target.get_at((size[0]-1, size[1]-1)), pygame.Color('#527e42'))

    def test_frame_time_is_validated_and_partitioned_updates_agree(self):
        transition = BattleTransition(self.world)
        for bad in (None, '1', True):
            with self.assertRaises(TypeError):transition.update(bad)
        for bad in (-1, float('nan'), float('inf')):
            with self.assertRaises(ValueError):transition.update(bad)
        other = BattleTransition(self.world)
        transition.update(.45)
        for _ in range(9):other.update(.05)
        self.assertAlmostEqual(transition.elapsed, other.elapsed)
        self.assertEqual(transition.phase, other.phase)


class EncounterEntryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='battle-transition-test-')
        self.addCleanup(temporary.cleanup)
        directory = Path(temporary.name)
        self.game = Game(window_size=(960, 640), fullscreen=False, start_on_title=False,
                         save_path=directory/'journey.json', settings_path=directory/'settings.json')
        self.game.audio.set_music(0);self.game.audio.set_effects(0)
        seed_completed_mill(self.game)
        self.game.world = self.game.town
        self.game.player.position.update(self.game.combat.position + (0, 24))
        self.game.camera.reset()
        pygame.event.clear()

    def tearDown(self):pygame.quit()

    def start(self):
        self.assertTrue(self.game.combat.interact(rng=random.Random(7)))
        self.assertTrue(self.game.combat.transitioning)
        return self.game.combat, self.game.combat.scene

    def event(self, kind, **kwargs):
        self.game.combat.handle_event(pygame.event.Event(kind, **kwargs))

    def test_actual_world_capture_and_all_clocks_remain_frozen_through_entry(self):
        game = self.game
        game.canvas.fill('magenta')
        owner, scene = self.start()
        self.assertNotEqual(owner.transition.world_frame.get_at((240, 160)), pygame.Color('magenta'))
        elapsed = game.elapsed_ms
        position = tuple(game.player.position)
        villagers = [tuple(npc.position) for npc in game.persistent_npcs]
        duration = owner.transition.duration
        for _ in range(12):game.update(duration / 12, (1, 0), True)
        if owner.transitioning:game.update(.000001, (1, 0), True)
        self.assertFalse(owner.transitioning)
        self.assertEqual(scene._elapsed, 0)
        self.assertTrue(all(actor.atb == 0 for actor in (*scene.model.party, scene.model.enemy)))
        self.assertEqual(game.elapsed_ms, elapsed)
        self.assertEqual(tuple(game.player.position), position)
        self.assertEqual([tuple(npc.position) for npc in game.persistent_npcs], villagers)
        game.update(.1, (1, 0), True)
        self.assertGreater(scene.model.player.atb, 0)
        self.assertEqual(game.elapsed_ms, elapsed)

    def test_held_key_during_entry_cannot_commit_after_reveal_until_released(self):
        owner, scene = self.start()
        scene.model.update(10)
        self.assertTrue(scene.model.waiting_for_player)
        self.event(pygame.KEYDOWN, key=pygame.K_RETURN, repeat=False)
        self.assertTrue(scene.model.waiting_for_player)
        owner.update(owner.transition.duration)
        self.event(pygame.KEYDOWN, key=pygame.K_RETURN, repeat=False)
        self.assertTrue(scene.model.waiting_for_player)
        self.event(pygame.KEYUP, key=pygame.K_RETURN)
        self.event(pygame.KEYDOWN, key=pygame.K_RETURN, repeat=False)
        self.assertEqual(scene.model.phase, 'acting')

    def test_held_click_during_entry_cannot_commit_after_reveal_until_released(self):
        owner, scene = self.start()
        scene.model.update(10)
        owner.draw(self.game.canvas, self.game.ui_surface)
        # The production inverse transform is used by BattleScene; use its
        # matching display scale for an actual command hit after the reveal.
        rect = scene.command_rects['attack']
        point = (rect.centerx * 2, rect.centery * 2)
        self.event(pygame.MOUSEBUTTONDOWN, button=1, pos=point)
        owner.update(owner.transition.duration)
        self.event(pygame.MOUSEBUTTONDOWN, button=1, pos=point)
        self.assertTrue(scene.model.waiting_for_player)
        self.event(pygame.MOUSEBUTTONUP, button=1, pos=point)
        self.event(pygame.MOUSEBUTTONDOWN, button=1, pos=point)
        self.assertEqual(scene.model.phase, 'acting')

    def test_focus_and_escape_pause_entry_and_require_explicit_resume(self):
        owner, scene = self.start()
        owner.update(.1)
        elapsed = owner.transition.elapsed
        self.event(pygame.WINDOWFOCUSLOST)
        owner.update(2)
        self.assertEqual(owner.transition.elapsed, elapsed)
        self.assertFalse(scene.focused)
        self.event(pygame.WINDOWFOCUSGAINED)
        owner.update(2)
        self.assertTrue(scene.paused)
        self.assertEqual(owner.transition.elapsed, elapsed)
        owner.draw(self.game.canvas, self.game.ui_surface)
        self.event(pygame.KEYDOWN, key=pygame.K_ESCAPE, repeat=False)
        self.event(pygame.KEYUP, key=pygame.K_ESCAPE)
        owner.update(.1)
        self.assertFalse(scene.paused)
        self.assertGreater(owner.transition.elapsed, elapsed)

    def test_entry_and_reset_request_music_without_restarting_scene_clocks(self):
        self.game.music = SimpleNamespace(play=Mock())
        owner, scene = self.start()
        self.game.music.play.assert_called_once_with('battle')
        owner.reset()
        self.assertFalse(owner.active)
        self.assertIsNone(owner.transition)
        self.game.music.play.assert_called_with('eldenmere')
        self.assertEqual(scene._elapsed, 0)


if __name__ == '__main__':unittest.main()
