"""Actual-camera architecture checks, without replacing production art or actors.

These are focused gameplay/rendering preservation tests. They do not certify
projection, drawing quality, or dry surface coverage; review the paired native
captures for those properties.
"""
from __future__ import annotations
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
import pygame
from PIL import Image, ImageChops, ImageDraw
from main import Game
from tools.capture_eldenmere_architecture_audit import BUILDINGS, CROSSINGS, default_fixture

ROOT=Path(__file__).resolve().parents[1]


class ArchitectureReviewGame(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary=tempfile.TemporaryDirectory(prefix='architecture-test-')
        cls.folder=Path(cls.temporary.name)
        cls.g=Game(fullscreen=False,window_size=(960,640),start_on_title=True,
                   save_path=cls.folder/'journey.json',settings_path=cls.folder/'settings.json')
        cls.g.on_title=False;cls.g.opening.restore({'version':1,'stage':'disabled'})
        cls.g.audio.set_music(0);cls.g.audio.set_effects(0)
        cls.fixture=default_fixture(ROOT)

    @classmethod
    def tearDownClass(cls):
        cls.g.music.stop();pygame.quit();cls.temporary.cleanup()

    def station(self,point,focus=None):
        g=self.g;g.world=g.town;g.player.position.update(point);g.player.facing='back'
        g.player.moving=False;g.player.running=False;g.elapsed_ms=0
        g.opening_fade=g.transfer_cooldown=0;g.camera.reset()
        if focus:g.camera.focus(focus,0)
        for door in g.town.doors:door.update(None,10)
        return g

    def pixels(self):
        self.g.draw()
        return Image.frombytes('RGB',(960,640),pygame.image.tobytes(self.g.canvas.native,'RGB'))

    def test_fixture_covers_all_thirteen_live_buildings_and_three_crossings(self):
        self.assertEqual(set(BUILDINGS),{r.data['id'] for r in self.g.town.doors})
        self.assertEqual(set(CROSSINGS),{'upper_bridge','main_bridge','mill_landing'})
        self.assertEqual(set(self.fixture['buildings']),set(BUILDINGS))
        # Serializing the fixture preserves fractional cottage threshold centers.
        self.assertEqual(json.loads(json.dumps(self.fixture)),self.fixture)
        for name,spec in self.fixture['buildings'].items():
            with self.subTest(building=name):
                self.assertTrue(self.g.town.can_stand(spec['player']))
                self.assertIn(spec['interior'],self.g.town.data['interior_scenes'])
                self.assertEqual(spec['player'][0],spec['door_anchor'][0])
                self.assertEqual(spec['player'][1]-spec['door_anchor'][1],24)

    def test_same_fixed_player_camera_and_clock_reproduce_native_entrance_pixels(self):
        g=self.g
        for name,spec in self.fixture['buildings'].items():
            with self.subTest(building=name):
                self.station(spec['player'],spec['survey_focus']);first=self.pixels()
                expected=tuple(g.camera.position())
                # Re-establish a real camera cut, not a hand-rendered art crop.
                g.camera.reset();g.camera.focus(spec['survey_focus'],0)
                self.assertEqual(tuple(g.camera.position()),expected)
                self.assertEqual(first.tobytes(),self.pixels().tobytes())
                self.assertEqual(g.canvas.native.get_size(),(960,640))

    def test_all_door_states_change_only_the_registered_door_in_actual_scene(self):
        for name,spec in self.fixture['buildings'].items():
            with self.subTest(building=name):
                g=self.station(spec['player'],spec['survey_focus'])
                door=next(d for d in g.town.doors if d.data['id']==name)
                closed=self.pixels();cx,cy=g.camera.position()
                x,y=door.data['position'];w,h=door.data['logical_size']
                outside=Image.new('L',(960,640),255)
                ImageDraw.Draw(outside).rectangle(((x-cx)*2,(y-cy)*2,(x+w-cx)*2-1,(y+h-cy)*2-1),fill=0)
                seen=[]
                for state,near,seconds in [('opening',True,.15),('open',True,.4),('closing',False,.15),('closed',False,.4)]:
                    door.update(spec['player'] if near else None,seconds)
                    self.assertEqual(door.state,state)
                    image=self.pixels();seen.append(image.tobytes())
                    difference=ImageChops.difference(closed,image).convert('L')
                    self.assertIsNone(ImageChops.multiply(difference,outside).getbbox(),(name,state))
                self.assertGreaterEqual(len(set(seen)),3,name)

    def test_all_crossing_center_routes_support_actual_walk_run_and_both_directions(self):
        for name,spec in CROSSINGS.items():
            for running in (False,True):
                for reverse in (False,True):
                    with self.subTest(crossing=name,running=running,reverse=reverse):
                        route=list(reversed(spec['route'])) if reverse else spec['route']
                        g=self.station(route[0]);target=pygame.Vector2(route[-1]);start=g.player.position.copy()
                        for _ in range(400):
                            delta=target-g.player.position
                            if delta.length()<.5:break
                            before=g.player.position.copy()
                            g.update(min(1/60,delta.length()/(108 if running else 72)),delta,running)
                            self.assertIs(g.world,g.town)
                            self.assertNotEqual(g.player.position,before)
                            self.assertTrue(g.world.can_stand(g.player.position))
                        else:self.fail((name,'movement did not finish',tuple(g.player.position)))
                        self.assertGreater(g.player.position.distance_to(start),20)

    def test_continue_at_each_crossing_restores_position_and_persistent_state(self):
        for name,spec in CROSSINGS.items():
            with self.subTest(crossing=name):
                g=self.station(spec['player']);expected=copy.deepcopy(g.journey_snapshot())
                self.assertTrue(g.save_progress(),g.save_error)
                other=Game(fullscreen=False,window_size=(960,640),start_on_title=True,
                           save_path=self.folder/'journey.json',settings_path=self.folder/'settings.json')
                try:
                    self.assertTrue(other.begin_journey(True),other.save_error)
                    actual=other.journey_snapshot()
                    for key in ('quests','party','inventory','player','overworld'):
                        self.assertEqual(actual[key],expected[key],(name,key))
                    self.assertTrue(other.world.can_stand(other.player.position))
                    other.update(.7,(0,0),False)
                    self.assertIs(other.world,other.town)
                finally:other.music.stop()


if __name__=='__main__':unittest.main()
