"""Approved travel art uses one authored clock at normal world size."""
import json
from pathlib import Path
import tempfile
import unittest
import pygame

from dense_art import WorldCanvas,draw_actor
from regent_actors import StoryActor

ROOT=Path(__file__).resolve().parents[1]
DIRECTIONS=('front','left','right','back')


class World:
    data={'id':'walk-review'}
    def image(self,path):return pygame.image.load(str(ROOT/path))


class IselinWalkIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.record=json.loads((ROOT/'assets/characters/iselin/actor.json').read_text())
        self.actor=StoryActor(self.record,World())
        self.actor.story_visible=True

    def test_both_resolutions_follow_all_authored_frame_boundaries_and_loop(self):
        actor=self.actor;actor.moving=True
        for direction in DIRECTIONS:
            actor.facing=direction
            self.assertEqual(actor.walk_durations[direction],(35,)*16)
            for index in range(16):
                expected=World().image(f'assets/characters/iselin/walk_{direction}/frame_{index+1:02}.png')
                for clock in (index*35,index*35+34.999,index*35+560):
                    actor.walk_ms=clock
                    detailed,anchor=actor.detailed_sprite(99999)
                    self.assertEqual(anchor,(21,60))
                    self.assertEqual(pygame.image.tobytes(detailed,'RGBA'),pygame.image.tobytes(expected,'RGBA'))
                    logical=actor.sprite(99999)
                    self.assertEqual(logical.get_size(),(21,36))
                    self.assertEqual(pygame.image.tobytes(logical,'RGBA'),
                                     pygame.image.tobytes(pygame.transform.scale(expected,(21,36)),'RGBA'))

    def test_turn_stop_conversation_and_scene_override_keep_correct_selection(self):
        actor=self.actor;actor.moving=True;actor.walk_ms=70
        for direction in DIRECTIONS:
            actor.facing=direction
            self.assertIs(actor.sprite(0),actor.walks[direction][2])
            self.assertIs(actor.detailed_sprite(0)[0],actor.detail_walks[direction][0][2])
        actor.request_conversation('left')
        self.assertIs(actor.sprite(0),actor.idles['left'])
        self.assertIs(actor.detailed_sprite(0)[0],actor.detail_idles['left'][0])
        actor.end_conversation();actor.moving=False
        self.assertIs(actor.sprite(0),actor.idles['back'])
        self.assertIs(actor.detailed_sprite(0)[0],actor.detail_idles['back'][0])
        pose=pygame.Surface((21,36),pygame.SRCALPHA)
        actor.pose_animations['review']={'frames':(pose,), 'durations':(100,), 'loop':False}
        actor.set_pose('review')
        self.assertIs(actor.sprite(0),pose)
        self.assertIsNone(actor.detailed_sprite(0))
        actor.set_pose(None);actor.story_sprite=pose;actor.moving=True
        self.assertIsNone(actor.detailed_sprite(0))
        self.assertEqual(actor.draw_anchor,(10.5,30))
        self.assertEqual(actor.blocker.size,(8,4))

    def test_native_detail_anchor_foreground_and_plain_surface_fallback(self):
        actor=self.actor;actor.moving=True;actor.facing='right';actor.walk_ms=245
        native=actor.detailed_sprite(0)[0]
        # Deliberately distinct ordinary and detail anchors exercise conversion.
        actor.draw_anchor=(12,30)
        canvas=WorldCanvas((70,70));canvas.fill('#24302d')
        draw_actor(canvas,actor,actor.sprite(0),(19,10),0)
        target=pygame.transform.scale(canvas,(140,140));canvas.present_detail(target)
        expected=pygame.Surface((140,140));expected.fill('#24302d');expected.blit(native,(41,20))
        self.assertEqual(pygame.image.tobytes(target,'RGB'),pygame.image.tobytes(expected,'RGB'))
        cover=pygame.Surface((3,5),pygame.SRCALPHA);cover.fill((0,120,40,128))
        canvas.blit(cover,(30,20));expected.blit(pygame.transform.scale(cover,(6,10)),(60,40))
        target=pygame.transform.scale(canvas,(140,140));canvas.present_detail(target)
        self.assertEqual(pygame.image.tobytes(target,'RGB'),pygame.image.tobytes(expected,'RGB'))
        canvas.reset_detail();canvas.fill('#24302d')
        actor.moving=False
        draw_actor(canvas,actor,actor.sprite(0),(19,10),0)
        target=pygame.transform.scale(canvas,(140,140));canvas.present_detail(target)
        expected.fill('#24302d');expected.blit(actor.detail_idles['right'][0],(41,20))
        self.assertEqual(pygame.image.tobytes(target,'RGB'),pygame.image.tobytes(expected,'RGB'))
        actor.moving=True
        plain=pygame.Surface((70,70));plain.fill('black')
        draw_actor(plain,actor,actor.sprite(0),(20,10),0)
        expected_plain=pygame.Surface((70,70));expected_plain.fill('black');expected_plain.blit(actor.sprite(0),(20,10))
        self.assertEqual(pygame.image.tobytes(plain,'RGB'),pygame.image.tobytes(expected_plain,'RGB'))

    def test_legacy_path_list_walk_still_uses_140ms_frames(self):
        path='assets/characters/iselin/idle_front_logical.png'
        with tempfile.TemporaryDirectory() as directory:
            manifest=Path(directory)/'legacy.json'
            manifest.write_text(json.dumps({'idles':{'front':path},'walks':{'front':[path,path]}}))
            actor=StoryActor({**self.record,'art':str(manifest)},World())
        actor.moving=True;actor.walk_ms=140
        self.assertEqual(actor.walk_durations['front'],(140,140))
        self.assertIs(actor.sprite(0),actor.walks['front'][1])
        self.assertIsNone(actor.detailed_sprite(0))

    def test_idle_rebuild_retains_registered_walks(self):
        from tools.export_iselin_idles import products
        from tools.register_iselin_walks import walk_references
        outputs=products()
        animation=json.loads(outputs['assets/characters/iselin/animation.json'])
        self.assertEqual(animation['walks'],walk_references())
