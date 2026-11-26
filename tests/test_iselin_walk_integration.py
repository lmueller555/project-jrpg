"""Approved native travel frames retain their authored clock and actor ownership."""
import json
from pathlib import Path
import tempfile
import unittest

import pygame
from dense_art import WorldCanvas, draw_actor
from story_actor import StoryActor

ROOT = Path(__file__).resolve().parents[1]
DIRECTIONS = ('front', 'left', 'right', 'back')


class World:
    data = {'id': 'native-walk-check'}

    def image(self, path):
        return pygame.image.load(str(ROOT / path))


class IselinWalkIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.record = json.loads((ROOT / 'assets/characters/iselin/actor.json').read_text())
        self.actor = StoryActor(self.record, World())
        self.actor.story_visible = True

    def test_every_approved_frame_boundary_and_loop_uses_native_pixels(self):
        actor = self.actor
        actor.moving = True
        self.assertFalse(hasattr(actor, 'detail_walks'))
        self.assertEqual(set(actor.walks), set(DIRECTIONS))
        for direction in DIRECTIONS:
            actor.facing = direction
            self.assertEqual(actor.walk_durations[direction], (35,) * 16)
            for index in range(16):
                expected = World().image(f'assets/characters/iselin/native_walk_{direction}/frame_{index + 1:02}.png')
                for clock in (index * 35, index * 35 + 34.999, index * 35 + 560):
                    actor.walk_ms = clock
                    actual = actor.sprite(99999)
                    self.assertEqual(actual.get_size(), (24, 36))
                    self.assertEqual(pygame.image.tobytes(actual, 'RGBA'),
                                     pygame.image.tobytes(expected, 'RGBA'))

    def test_turn_stop_conversation_and_pose_precedence_keep_native_selection(self):
        actor = self.actor
        actor.moving = True
        actor.walk_ms = 70
        for direction in DIRECTIONS:
            actor.facing = direction
            self.assertIs(actor.sprite(0), actor.walks[direction][2])
        actor.request_conversation('left')
        self.assertIs(actor.sprite(0), actor.idles['left'])
        actor.end_conversation()
        actor.moving = False
        self.assertIs(actor.sprite(0), actor.idles['back'])
        pose = pygame.Surface((24, 36), pygame.SRCALPHA)
        actor.pose_animations['review'] = {'frames': (pose,), 'durations': (100,), 'loop': False}
        actor.set_pose('review')
        self.assertIs(actor.sprite(0), pose)
        actor.moving = True
        self.assertIs(actor.sprite(0), actor.walks['back'][2])
        actor.moving = False
        actor.request_conversation('right')
        self.assertIs(actor.sprite(0), actor.idles['right'])
        actor.end_conversation()
        actor.set_pose(None)
        self.assertIs(actor.sprite(0), actor.idles['back'])
        self.assertEqual(actor.draw_anchor, (12, 30))
        self.assertEqual(actor.blocker.size, (8, 4))

    def test_native_actor_preserves_normal_foreground_depth_and_display_scale(self):
        actor = self.actor
        actor.moving = True
        actor.facing = 'right'
        actor.walk_ms = 245
        canvas = WorldCanvas((70, 70))
        canvas.fill('#24302d')
        draw_actor(canvas, actor, actor.sprite(0), (19, 10), 0)
        expected = pygame.Surface((70, 70))
        expected.fill('#24302d')
        expected.blit(actor.sprite(0), (19, 10))
        cover = pygame.Surface((3, 5), pygame.SRCALPHA)
        cover.fill((0, 120, 40, 128))
        canvas.blit(cover, (30, 20))
        expected.blit(cover, (30, 20))
        target = pygame.transform.scale(canvas, (140, 140))
        canvas.present_detail(target)
        self.assertFalse(canvas.patches)
        self.assertEqual(pygame.image.tobytes(target, 'RGB'),
                         pygame.image.tobytes(pygame.transform.scale(expected, (140, 140)), 'RGB'))


    def test_other_path_list_actors_keep_their_existing_140ms_format(self):
        path = 'assets/characters/iselin/native_idles/idle_front.png'
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / 'paths.json'
            manifest.write_text(json.dumps({'idles': {'front': path}, 'walks': {'front': [path, path]}}))
            actor = StoryActor({**self.record, 'art': str(manifest)}, World())
        actor.moving = True
        actor.walk_ms = 140
        self.assertEqual(actor.walk_durations['front'], (140, 140))
        self.assertIs(actor.sprite(0), actor.walks['front'][1])

    def test_live_builder_is_reproducible_without_regenerating_approved_art(self):
        from tools.build_iselin_native_actor import products
        for path, data in products().items():
            self.assertEqual(path.read_bytes(), data, str(path))
