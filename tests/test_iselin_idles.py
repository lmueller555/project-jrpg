import json
from pathlib import Path
import unittest
import pygame
from regent_actors import StoryActor
from dense_art import WorldCanvas, draw_actor

ROOT=Path(__file__).resolve().parents[1]


class IdleTests(unittest.TestCase):
    def test_all_facings_and_conversation_use_registered_detail(self):
        class World:
            data={'id':'review'}
            def image(self,path):return pygame.image.load(str(ROOT/path))
        actor=StoryActor(json.loads((ROOT/'assets/characters/iselin/actor.json').read_text()),World())
        actor.story_visible=True
        for direction in ('front','left','right','back'):
            actor.facing=direction
            self.assertEqual(actor.sprite(0).get_size(),(21,36))
            self.assertEqual(actor.detailed_idle(0)[0].get_size(),(42,72))
            canvas=WorldCanvas((60,60));canvas.fill('black')
            draw_actor(canvas,actor,actor.sprite(0),(20.5,10),0)
            self.assertTrue(canvas.patches)
            actor.request_conversation(direction)
            self.assertIs(actor.detailed_idle(0)[0],actor.detail_idles[direction][0])
            actor.end_conversation()
            self.assertEqual(actor.blocker.size,(8,4))

    def test_source_exports_are_registered_and_not_mirrored(self):
        from PIL import Image,ImageOps
        frames={d:Image.open(ROOT/f'assets/characters/iselin/idle_{d}_42x72.png').convert('RGBA')
                for d in ('front','left','right','back')}
        for image in frames.values():
            self.assertEqual(image.size,(42,72))
            self.assertEqual(image.getchannel('A').getextrema(),(0,255))
            self.assertEqual(image.getbbox()[1::2],(2,70))
        self.assertNotEqual(frames['left'].tobytes(),ImageOps.mirror(frames['right']).tobytes())
