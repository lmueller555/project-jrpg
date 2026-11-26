"""Approved Iselin art remains usable through the neutral native actor."""
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest

import pygame

from story_actor import StoryActor
from tools.scenario_fixtures import make_game

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT/'docs/reviews/iselin_native_integration'


class NativeIntegrationTests(unittest.TestCase):
    def test_approved_native_art_and_portrait_are_preserved_byte_for_byte(self):
        baseline = json.loads((REVIEW/'approved_assets.json').read_text())
        self.assertEqual(baseline['png_count'], 69)
        for path, digest in baseline['sha256'].items():
            with self.subTest(path=path):
                self.assertEqual(sha256((ROOT/path).read_bytes()).hexdigest(), digest)

    def test_neutral_actor_draws_approved_native_art_in_the_real_world(self):
        with tempfile.TemporaryDirectory() as directory:
            game = make_game(directory, embedded=False)
            try:
                record = json.loads((ROOT/'assets/characters/iselin/actor.json').read_text())
                actor = StoryActor(record, game.town)
                actor.story_visible = True
                actor.position.update(384, 480)
                game.town.npcs.append(actor)
                game.world = game.town
                game.player.position.update(550, 432)
                game.camera.focus(actor.position, duration=0)
                self.assertEqual(actor.draw_anchor, (12, 30))
                self.assertEqual(actor.blocker.size, (8, 4))
                for direction in ('front', 'left', 'right', 'back'):
                    self.assertEqual(actor.walk_durations[direction], (35,)*16)
                    actor.facing = direction;actor.moving = True;actor.walk_ms = 105
                    self.assertIs(actor.sprite(0), actor.walks[direction][3])
                    actor.request_conversation(direction)
                    self.assertIs(actor.sprite(0), actor.idles[direction])
                    game.draw()
                    self.assertFalse(game.canvas.patches)
                    actor.end_conversation()
            finally:
                game.music.stop();pygame.quit()


if __name__ == '__main__':unittest.main()
