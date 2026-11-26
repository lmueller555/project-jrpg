"""The live regent uses every approved native idle at the cast's world scale."""
import json
from pathlib import Path
import unittest

import pygame
from dense_art import WorldCanvas, draw_actor
from story_actor import StoryActor

ROOT = Path(__file__).resolve().parents[1]
DIRECTIONS = ('front', 'left', 'right', 'back')


class World:
    data = {'id': 'native-idle-check'}

    def image(self, path):
        return pygame.image.load(str(ROOT / path))


class IdleTests(unittest.TestCase):
    def test_all_live_facings_and_conversation_preserve_approved_pixels(self):
        record = json.loads((ROOT / 'assets/characters/iselin/actor.json').read_text())
        actor = StoryActor(record, World())
        actor.story_visible = True
        self.assertEqual(set(actor.idles), set(DIRECTIONS))
        self.assertEqual(actor.draw_anchor, (12, 30))
        self.assertEqual(actor.blocker.size, (8, 4))
        self.assertFalse(hasattr(actor, 'detailed_sprite'))
        for direction in DIRECTIONS:
            expected = World().image(f'assets/characters/iselin/native_idles/idle_{direction}.png')
            actor.facing = direction
            self.assertEqual(actor.sprite(0).get_size(), (24, 36))
            self.assertEqual(pygame.image.tobytes(actor.sprite(0), 'RGBA'),
                             pygame.image.tobytes(expected, 'RGBA'))
            actor.facing = 'front'
            actor.request_conversation(direction)
            self.assertEqual(pygame.image.tobytes(actor.sprite(0), 'RGBA'),
                             pygame.image.tobytes(expected, 'RGBA'))
            actor.end_conversation()

    def test_native_idle_uses_the_ordinary_foreground_path(self):
        record = json.loads((ROOT / 'assets/characters/iselin/actor.json').read_text())
        actor = StoryActor(record, World())
        canvas = WorldCanvas((60, 60))
        canvas.fill('#24302d')
        draw_actor(canvas, actor, actor.sprite(0), (20, 10), 0)
        self.assertFalse(canvas.patches)
        expected = pygame.Surface((60, 60))
        expected.fill('#24302d')
        expected.blit(actor.idles['front'], (20, 10))
        self.assertEqual(pygame.image.tobytes(canvas, 'RGB'),
                         pygame.image.tobytes(expected, 'RGB'))

    def test_approved_directional_silhouettes_remain_hard_alpha_and_asymmetric(self):
        from PIL import Image, ImageOps
        frames = {d: Image.open(ROOT / f'assets/characters/iselin/native_idles/idle_{d}.png').convert('RGBA')
                  for d in DIRECTIONS}
        for image in frames.values():
            self.assertEqual(image.size, (24, 36))
            self.assertEqual(image.getchannel('A').getextrema(), (0, 255))
            self.assertEqual(image.getbbox()[1::2], (1, 35))
        self.assertNotEqual(frames['left'].tobytes(), ImageOps.mirror(frames['right']).tobytes())
