"""Playable prototype behavior uses actual feet, sprites and independent maps."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import pygame

from tools.preview_grass import GrassDemo
from tools.capture_grass_demo import unchanged_worlds


ROOT = Path(__file__).resolve().parents[1]


class GrassDemoIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.demo = GrassDemo()
        self.addCleanup(self.demo.close)

    def move(self, target, running=False, observe=None):
        target = pygame.Vector2(target)
        speed = 108 if running else 72
        for _ in range(2000):
            delta = target-self.demo.player.position
            if delta.length() < .02:return
            previous = self.demo.player.position.copy()
            self.demo.step(min(1/30, delta.length()/speed), delta, running=running)
            self.assertTrue(self.demo.world.can_stand(self.demo.player.position))
            self.assertNotEqual(previous, self.demo.player.position)
            if observe:observe(self.demo.world.grass.snapshot())
        self.fail(('Ordinary movement exceeded budget', target))

    def stand_in_patch(self):
        self.move((240, 312))
        self.move((408, 312))
        self.demo.step(.4)

    def test_real_input_walks_runs_stands_and_focus_freezes_time(self):
        start = self.demo.player.position.copy()
        self.demo.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_d, repeat=False))
        self.demo.step(.1, self.demo.input_direction())
        self.assertAlmostEqual(self.demo.player.position.x-start.x, 7.2)
        before = self.demo.player.position.copy()
        self.demo.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_LSHIFT, repeat=False))
        self.demo.step(.1, self.demo.input_direction(), running=True)
        self.assertAlmostEqual(self.demo.player.position.x-before.x, 10.8)
        self.assertTrue(self.demo.player.running)
        self.assertIn(self.demo.player.sprite(), [frame for frame, _ in self.demo.player.runs['right']])
        self.demo.handle_event(pygame.event.Event(pygame.KEYUP, key=pygame.K_d))
        self.demo.step(.1, self.demo.input_direction())
        self.assertFalse(self.demo.player.moving)
        self.demo.handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        previous = self.demo.elapsed_ms, tuple(self.demo.player.position), self.demo.world.grass.snapshot()
        self.demo.step(1, (1, 0), True)
        self.assertEqual((self.demo.elapsed_ms, tuple(self.demo.player.position),
                          self.demo.world.grass.snapshot()), previous)

    def test_standing_holds_grass_without_retriggering_then_exit_recovers(self):
        self.stand_in_patch()
        active = [item for item in self.demo.world.grass.snapshot()['clumps'] if item['occupants']]
        self.assertTrue(active)
        activations = {item['id']: item['activations'] for item in active}
        self.demo.step(2)
        held = {item['id']: item for item in self.demo.world.grass.snapshot()['clumps']}
        for identifier, count in activations.items():
            self.assertEqual(held[identifier]['activations'], count)
            self.assertGreaterEqual(held[identifier]['strength'], .99)
            self.assertTrue(held[identifier]['occupants'])
        self.assertFalse(self.demo.player.moving)
        self.move((552, 312))
        self.demo.step(1.2)
        for item in self.demo.world.grass.snapshot()['clumps']:
            self.assertEqual(item['occupants'], 0)
            self.assertAlmostEqual(item['strength'], 0.)

    def test_running_produces_stronger_bending_with_the_authored_run_sprite(self):
        maxima = []
        for running in (False, True):
            self.demo.reset()
            self.move((552, 336))
            maximum = [0.]
            def observe(snapshot):
                maximum[0] = max(maximum[0], max(item['strength'] for item in snapshot['clumps']))
            self.move((264, 336), running=running, observe=observe)
            maxima.append(maximum[0])
        self.assertAlmostEqual(maxima[0], 1.)
        self.assertGreaterEqual(maxima[1], 1.9)
        self.assertTrue(self.demo.player.running)
        self.assertIn(self.demo.player.sprite(), [frame for frame, _ in self.demo.player.runs['left']])

    def test_parted_grass_leaves_the_head_visible_and_overlaps_some_lower_body_pixels(self):
        self.stand_in_patch()
        world, player = self.demo.world, self.demo.player
        world.grass.enabled = False
        self.demo.draw()
        bare = self.demo.canvas.copy()
        world.grass.enabled = True
        self.demo.draw()
        covered = self.demo.canvas.copy()
        sprite = player.sprite()
        mask = pygame.mask.from_surface(sprite)
        anchor = world.data['player_draw_anchor']
        x0 = round(player.position.x)-anchor[0]-self.demo.camera[0]
        y0 = round(player.position.y)-anchor[1]-self.demo.camera[1]
        head = legs = changed_legs = 0
        for y in range(sprite.get_height()):
            for x in range(sprite.get_width()):
                if not mask.get_at((x, y)):continue
                point = x+x0, y+y0
                if y < 14:
                    head += 1
                    self.assertEqual(bare.get_at(point), covered.get_at(point), ('Head covered', x, y))
                elif y >= 23:
                    legs += 1
                    changed_legs += bare.get_at(point) != covered.get_at(point)
        self.assertGreater(head, 20)
        self.assertGreater(legs, 10)
        self.assertGreater(changed_legs, 0, 'Grass should overlap boots or legs at an occupied root')

    def test_dense_patch_walk_and_run_edges_keep_actual_head_pixels_clear(self):
        representatives = {}
        for clump in self.demo.world.grass.clumps:
            representatives.setdefault(clump.variant, clump)
        # Each target is approached through real movement. The north-facing
        # target includes the old failing slender/back (-4,+8) edge pose.
        approaches = {
            'back': ((-4, 20), (-4, 8)),
            'front': ((0, -12), (0, -2)),
            'left': ((14, 0), (4, 0)),
            'right': ((-14, 0), (-4, 0))}
        for variant, clump in representatives.items():
            root = pygame.Vector2(clump.position)
            for running in (False, True):
                for facing, (start, finish) in approaches.items():
                    with self.subTest(variant=variant, running=running, facing=facing):
                        self.move(root+start)
                        self.move(root+finish, running=running)
                        player, world = self.demo.player, self.demo.world
                        self.assertEqual(player.facing, facing)
                        self.assertTrue(player.moving)
                        self.assertEqual(player.running, running)
                        world.grass.enabled = False
                        self.demo.draw()
                        bare = self.demo.canvas.copy()
                        world.grass.enabled = True
                        self.demo.draw()
                        covered = self.demo.canvas
                        sprite = player.sprite()
                        mask = pygame.mask.from_surface(sprite)
                        anchor = world.data['player_draw_anchor']
                        x0 = round(player.position.x)-anchor[0]-self.demo.camera[0]
                        y0 = round(player.position.y)-anchor[1]-self.demo.camera[1]
                        for y in range(14):
                            for x in range(sprite.get_width()):
                                if mask.get_at((x, y)):
                                    point = x+x0, y+y0
                                    self.assertEqual(bare.get_at(point), covered.get_at(point),
                                                     ('Moving head covered', x, y))

    def test_isolated_preview_preserves_existing_worlds_and_can_launch_from_another_directory(self):
        expected = unchanged_worlds()
        with patch('main.SaveStore', side_effect=AssertionError('Preview opened a journey store')), \
                patch('main.AudioSettings', side_effect=AssertionError('Preview opened settings')):
            isolated = GrassDemo()
            isolated.step(.1, (1, 0))
            isolated.draw()
            isolated.close()
        with tempfile.TemporaryDirectory(prefix='grass-preview-') as directory:
            screenshot = Path(directory)/'preview.png'
            result = subprocess.run([sys.executable, str(ROOT/'tools/preview_grass.py'),
                                     '--headless', '--frames', '3', '--screenshot', str(screenshot)],
                                    cwd=directory, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual({path.name for path in Path(directory).iterdir()}, {'preview.png'})
            self.assertTrue(screenshot.is_file())
        self.assertEqual(unchanged_worlds(), expected)


if __name__ == '__main__':unittest.main()
