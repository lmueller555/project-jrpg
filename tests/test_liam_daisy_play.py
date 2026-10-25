"""Coordinated scene ownership, contact art, real collision and both endings."""
import os
os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1')
import hashlib
import json
import random
import unittest

import pygame
from PIL import Image
import main


class LiamDaisyPlayTests(unittest.TestCase):
    def setUp(self):
        self.game=main.Game(fullscreen=False,start_on_title=False);self.r=self.game.play_routines[0]
        self.game.player.position.update(430,600)

    def tearDown(self):pygame.quit()

    def until(self,predicate,limit=100):
        for i in range(limit*60):
            before={a:(self.r.worlds[a],a.position.copy()) for a in (self.r.liam,self.r.daisy)}
            self.game.update(1/60,(0,0),False)
            for a,(oldworld,oldpos) in before.items():
                w=self.r.worlds[a]
                self.assertEqual(sum(n is a for scene in self.game.scenes.values() for n in scene.npcs),1)
                self.assertTrue(w.can_stand(a.position,a.probe_size,a), (self.r.state,a.data['id'],tuple(a.position)))
                if w is oldworld:self.assertLessEqual(a.position.distance_to(oldpos),64/60+1e-6)
            if predicate():return i/60
        self.fail((self.r.state,tuple(self.r.liam.position),tuple(self.r.daisy.position)))

    def test_both_natural_random_endings_with_exact_three_laps_and_portals(self):
        for seed,drink in ((1,True),(0,False)):
            with self.subTest(drink=drink):
                r=self.r;r._rng=random.Random(seed);r.begin()
                self.until(lambda:r.state=='nap')
                self.assertIs(r.drink_choice,drink)
                self.assertEqual(r.daisy.bowls['water']['state'],'half_full' if drink else 'full')
                self.assertEqual((r.liam_index,r.daisy_index),(73,73))
                self.assertAlmostEqual(r.daisy.position.distance_to((108,282)),0)
                self.assertAlmostEqual(r.liam.position.distance_to((88,246)),0)
                self.assertTrue(r.liam.sort_y>next(e['sort_y'] for e in r.home.entities if e['id']=='liam_bed'))
                transfers=[e for e in r.events if 'transfer' in e]
                self.assertEqual([(e['transfer'],e['scene']) for e in transfers],
                                 [('liam','eldenmere.playable'),('daisy','eldenmere.playable'),('liam','liam_house'),('daisy','liam_house')])
                self.assertIsNone(r.daisy.active_bowl)
                r.rest_duration=50
                self.until(lambda:r.state=='cooldown',limit=5)
                self.assertFalse(r.daisy.play_owned);self.assertIsNone(r.daisy.play_pose)
                self.assertGreaterEqual(r.cooldown_ms,480000);self.assertLessEqual(r.cooldown_ms,720000)
                self.assertIsNone(r.liam.sort_y)
                if drink:
                    self.game=main.Game(fullscreen=False,start_on_title=False);self.r=self.game.play_routines[0]
                    self.game.player.position.update(430,600)

    def test_waits_for_existing_meal_and_empty_water_inspection(self):
        r=self.r;r.daisy.begin_activity('food',r.home);r.begin(drink=True)
        self.until(lambda:r.daisy.state=='eat',limit=10)
        self.assertEqual(r.state,'cooldown');self.assertFalse(r.daisy.play_owned)
        self.until(lambda:r.state=='find_daisy',limit=20)
        self.assertEqual(r.daisy.bowls['food']['state'],'half_full')
        self.assertTrue(r.home.set_entity_state('daisy_water_bowl','empty'))
        self.until(lambda:r.state=='nap')
        self.assertEqual(r.daisy.bowls['water']['state'],'empty')
        self.assertEqual(r.daisy.completed_visits['water'],0)
        self.assertTrue(any(e.get('to')=='inspect' for e in r.daisy.events))

    def test_blocked_arrival_waits_without_cloning_or_crossing_player(self):
        r=self.r;r.begin(drink=False)
        self.game.player.position.update(287.5,546)
        self.until(lambda:r.state=='exit_liam',limit=15)
        for _ in range(180):
            self.game.update(1/60,(0,0),False)
            self.assertIs(r.worlds[r.liam],r.home)
        self.game.player.position.update(430,600)
        self.until(lambda:r.state=='nap')

    def test_obstructed_chase_detours_then_completes(self):
        r=self.r;r.begin(drink=False);self.until(lambda:r.state=='chase',limit=20)
        self.game.player.position.update(358,590)
        for _ in range(600):
            self.game.update(1/60,(0,0),False)
            for actor in (r.liam,r.daisy):
                if r.worlds[actor] is self.game.town:self.assertFalse(actor.blocker.colliderect(self.game.town.probe_rect(self.game.player.position)))
        self.game.player.position.update(430,600)
        self.until(lambda:r.state=='nap',limit=80)

    def test_nap_holds_when_bedside_is_occupied_and_releases_normal_daisy_behavior(self):
        r=self.r;r.begin(drink=False);self.until(lambda:r.state=='return_daisy',limit=40)
        self.game.world=r.home;self.game.player.position.update(88,246)
        self.until(lambda:r.daisy.state=='rest',limit=30)
        for _ in range(3600):self.game.update(1/60,(0,0),False)
        self.assertEqual(r.state,'daisy_return');self.assertEqual(r.daisy.state,'rest')
        self.game.player.position.update(220,300)
        self.until(lambda:r.state=='nap',limit=20)
        r.rest_duration=30;self.until(lambda:r.state=='cooldown',limit=5)
        r.daisy.duration_ms=1;r.cooldown_ms=999999
        self.game.update(.1,(0,0),False)
        self.assertEqual(r.daisy.state,'stand_up')

    def test_four_pose_layers_protected_art_and_pillow_registration(self):
        meta=json.loads((main.ROOT/'assets/characters/liam_family/play_routine/animations.json').read_text())
        for action,spec in meta['actions'].items():
            self.assertEqual(len(spec['frames']),4);unique=set()
            for frame in spec['frames']:
                im=Image.open(main.ROOT/frame['file']).convert('RGBA');unique.add(im.tobytes())
                rebuilt=Image.new('RGBA',im.size)
                for path in frame['layers_from_repo_root']:rebuilt.alpha_composite(Image.open(main.ROOT/path).convert('RGBA'))
                self.assertEqual(rebuilt.tobytes(),im.tobytes())
                self.assertEqual(set(im.getchannel('A').tobytes()),{0,255})
            self.assertEqual(len(unique),4,action)
        for path,sha in meta['approved_png_sha256'].items():self.assertEqual(hashlib.sha256((main.ROOT/path).read_bytes()).hexdigest(),sha)
        bed=meta['actions']['settle_bed'];self.assertEqual(bed['landmarks']['head_on_pillow_world'],[60,225])
        last=Image.open(main.ROOT/bed['frames'][-1]['file']).convert('RGBA')
        wood=Image.open(main.ROOT/'assets/terrain/eldenmere/cottage_furniture/sprites/bed.png').convert('RGBA')
        # The quilt and footboard are exact approved pixels over Liam's body.
        for y in range(29,72):
            for x in range(48):
                pixel=wood.getpixel((x,y))
                if pixel[3]:self.assertEqual(last.getpixel((x+12,y+24)),pixel)
        self.assertEqual(self.r.config['drink_probability'],.5)
        self.assertEqual(self.r.config['laps'],3)


if __name__=='__main__':unittest.main()
