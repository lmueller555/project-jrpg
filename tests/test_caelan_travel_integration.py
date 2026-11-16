"""Approved Caelan travel enters the native compositor without changing geometry."""
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest

os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import pygame
from main import Player, WALK_SPEED, RUN_MULTIPLIER
from rendering import WorldCanvas
from sanctuary_arrival import CastActor

ROOT=Path(__file__).resolve().parents[1]
DIRECTIONS=('front','back','left','right')

class CaelanTravelIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.world=SimpleNamespace(data={'spawn':(100,100)},
            image=lambda path:pygame.image.load(str(ROOT/path)),can_stand=lambda point:True)
        self.player=Player(self.world)

    def test_all_idle_and_walk_pixels_and_authored_frame_boundaries(self):
        p=self.player
        self.assertEqual(p.draw_anchor,(12,30))
        for direction in DIRECTIONS:
            p.facing=direction;p.moving=False
            expected=self.world.image(f'assets/characters/caelan/review_hd/idles/idle_{direction}.png')
            self.assertIsInstance(p.sprite(),WorldCanvas)
            self.assertEqual(p.sprite().get_size(),(24,36))
            self.assertEqual(pygame.image.tobytes(p.sprite().native,'RGBA'),pygame.image.tobytes(expected,'RGBA'))
            p.moving=True;p.running=False
            self.assertEqual(p.walk_durations[direction],(35,)*16)
            for i in range(16):
                expected=self.world.image(f'assets/characters/caelan/review_hd/walk_{direction}/frame_{i+1:02}.png')
                for clock in (i*35,i*35+34.999,i*35+560):
                    p.walk_ms=clock
                    self.assertIs(p.sprite(),p.walks[direction][i][0])
                    self.assertEqual(pygame.image.tobytes(p.sprite().native,'RGBA'),pygame.image.tobytes(expected,'RGBA'))

    def test_runs_preserve_hd_pixels_padding_and_authored_cadence(self):
        p=self.player;p.moving=p.running=True
        for direction in DIRECTIONS:
            p.facing=direction
            self.assertEqual(p.run_durations[direction],(25,)*16)
            for i in range(16):
                p.walk_ms=i*25
                expected=self.world.image(f'assets/characters/caelan/review_hd/run_{direction}/frame_{i+1:02}.png')
                self.assertIsInstance(p.sprite(),WorldCanvas)
                self.assertEqual(p.sprite().get_size(),(28,38) if direction in ('left','right') else (24,38))
                self.assertEqual(p.draw_anchor,(14,32) if direction in ('left','right') else (12,32))
                self.assertEqual(pygame.image.tobytes(p.sprite().native,'RGBA'),pygame.image.tobytes(expected,'RGBA'))
                p.walk_ms=i*25+24.999
                self.assertIs(p.sprite(),p.runs[direction][i][0])
            p.walk_ms=400
            self.assertIs(p.sprite(),p.runs[direction][0][0])
            p.moving=False
            self.assertEqual(p.draw_anchor,(12,30))
            p.moving=True

    def test_native_anchor_alpha_occlusion_and_plain_surface_fallback(self):
        p=self.player;p.facing='left';p.moving=True;p.walk_ms=245
        canvas=WorldCanvas((70,70));canvas.fill('#24302d')
        canvas.blit(p.sprite(),(19,10))
        expected=pygame.Surface((140,140));expected.fill('#24302d')
        expected.blit(p.sprite().native,(38,20))
        cover=pygame.Surface((3,5),pygame.SRCALPHA);cover.fill((0,120,40,128))
        canvas.blit(cover,(30,20));expected.blit(pygame.transform.scale(cover,(6,10)),(60,40))
        self.assertEqual(pygame.image.tobytes(canvas.native,'RGB'),pygame.image.tobytes(expected,'RGB'))
        plain=pygame.Surface((70,70));plain.fill('black');plain.blit(p.sprite(),(19,10))
        fallback=pygame.Surface((70,70));fallback.fill('black')
        fallback.blit(pygame.transform.scale(p.sprite().native,(24,36)),(19,10))
        self.assertEqual(pygame.image.tobytes(plain,'RGB'),pygame.image.tobytes(fallback,'RGB'))

    def test_scene_copy_uses_one_560ms_clock_and_owns_its_banks(self):
        p=self.player;actor=CastActor('caelan',self.world,p)
        actor.moving=True
        for direction in DIRECTIONS:
            actor.facing=direction
            self.assertEqual(actor.walk_durations[direction],(35,)*16)
            for i in range(16):
                actor.walk_ms=i*35+34.999
                self.assertIs(actor.sprite(9999),p.walks[direction][i][0])
            actor.walk_ms=560
            self.assertIs(actor.sprite(0),p.walks[direction][0][0])
        actor.walks['left'].clear()
        self.assertEqual(len(p.walks['left']),16)
        actor.walk_durations['left']=(140,)*4
        self.assertEqual(p.walk_durations['left'],(35,)*16)

    def test_scene_tuple_bank_without_separate_clock_also_keeps_authored_timing(self):
        source=SimpleNamespace(idles=self.player.idles,walks=self.player.walks)
        actor=CastActor('caelan',self.world,source)
        actor.moving=True;actor.walk_ms=70
        self.assertIs(actor.sprite(0),self.player.walks['front'][2][0])

    def test_explicit_scene_art_and_player_story_pose_have_priority(self):
        p=self.player
        spec=json.loads((ROOT/'assets/story/sanctuary_rescue/art.json').read_text())['actors']['caelan']
        # An explicit scene bank must suppress any inherited detailed provider.
        p.detail_idles={'front':(pygame.Surface((48,72)),(24,60))}
        p.detail_walks={'front':([pygame.Surface((48,72))]*16,(24,60))}
        actor=CastActor('caelan',self.world,p,art=spec)
        self.assertIsNone(actor.detailed_sprite(0))
        actor.moving=True;actor.walk_ms=140
        self.assertIsNone(actor.detailed_sprite(0))
        self.assertEqual(actor.walk_durations['front'],tuple(f['duration_ms'] for f in spec['walks']['front']))
        pose=pygame.Surface((40,60),pygame.SRCALPHA);p.story_sprite=pose
        p.moving=p.running=True
        self.assertIs(p.sprite(),pose)
        del p.story_sprite
        self.assertIs(p.sprite(),p.runs['front'][0][0])

    def test_stopping_turning_blocking_diagonals_and_gait_switch_keep_geometry(self):
        p=self.player
        p.update((1,0),.08,self.world)
        self.assertAlmostEqual(p.position.x,100+WALK_SPEED*.08)
        self.assertIs(p.sprite(),p.walks['right'][2][0])
        p.update((1,0),.02,self.world,True)
        self.assertEqual(p.walk_ms,20);self.assertIs(p.sprite(),p.runs['right'][0][0])
        p.update((0,-1),.035,self.world)
        self.assertEqual(p.walk_ms,35);self.assertIs(p.sprite(),p.walks['back'][1][0])
        p.update((0,0),.1,self.world)
        self.assertEqual(p.walk_ms,0);self.assertIs(p.sprite(),p.idles['back'])
        start=p.position.copy();p.update((1,1),.1,self.world,True)
        self.assertAlmostEqual(p.position.distance_to(start),WALK_SPEED*RUN_MULTIPLIER*.1)
        self.world.can_stand=lambda point:False
        p.update((-1,0),.1,self.world)
        self.assertFalse(p.moving);self.assertEqual(p.walk_ms,0)
        self.assertIs(p.sprite(),p.idles['left'])


    def test_anchor_tracks_gait_and_story_override_without_moving_world_position(self):
        p=self.player
        for direction in DIRECTIONS:
            p.facing=direction;p.moving=p.running=True
            position=tuple(p.position)
            expected=(14,32) if direction in ('left','right') else (12,32)
            self.assertEqual(p.draw_anchor,expected)
            p.running=False
            self.assertEqual(p.draw_anchor,(12,30))
            p.running=True;p.story_sprite=pygame.Surface((40,48),pygame.SRCALPHA)
            self.assertEqual(p.draw_anchor,(12,30))
            del p.story_sprite
            self.assertEqual(p.draw_anchor,expected)
            self.assertEqual(tuple(p.position),position)

    def test_superseded_travel_files_are_removed_and_current_run_banks_integrated(self):
        for d in DIRECTIONS:
            self.assertFalse((ROOT/f'assets/characters/caelan/idle_{d}.png').exists())
            for gait in ('walk','run'):
                self.assertFalse((ROOT/f'assets/characters/caelan/{gait}_{d}').exists())
            data=json.loads((ROOT/f'assets/characters/caelan/review_hd/run_{d}/animation.json').read_text())
            self.assertTrue(data['runtime_integration'])
            self.assertEqual(data['status'],'approved')

    def test_runtime_registry_separates_density_and_preserves_approved_pixels(self):
        manifest=json.loads((ROOT/'assets/characters/caelan/animation.json').read_text())
        self.assertEqual(manifest['status'],'integrated')
        self.assertNotIn('artwork_pixels_per_world_pixel',manifest)
        for d in DIRECTIONS:
            self.assertEqual(manifest['walks'][d]['artwork_pixels_per_world_pixel'],2)
            self.assertEqual(manifest['runs'][d]['artwork_pixels_per_world_pixel'],2)
            meta=json.loads((ROOT/manifest['walks'][d]['manifest']).read_text())
            self.assertTrue(meta['runtime_integration']);self.assertEqual(meta['status'],'approved')
        protected=ROOT/'assets/source/characters/caelan/walk_back_hd_review/revision_2/protected_front.json'
        for file,digest in json.loads(protected.read_text()).items():
            self.assertEqual(hashlib.sha256((ROOT/file).read_bytes()).hexdigest(),digest)
