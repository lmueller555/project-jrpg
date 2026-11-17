"""Production Game proof for native exterior walls and material ownership.

This complements, rather than replaces, the paired native visual review. It uses
ordinary Game.update for the two old wall-overlap routes and Game.draw for the
normal/reduced material comparison; no replacement scenery is inserted.
"""
from __future__ import annotations
import gc
import os
from pathlib import Path
import tempfile
import unittest
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
import pygame
from PIL import Image,ImageChops,ImageDraw
from main import Game
from tools.capture_eldenmere_architecture_audit import default_fixture
from tools.eldenmere_architecture_art import generate_architecture
ROOT=Path(__file__).resolve().parents[1]


class ExteriorProductionGame(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary=tempfile.TemporaryDirectory(prefix='exterior-integration-')
        cls.folder=Path(cls.temporary.name)
        cls.g=Game(fullscreen=False,window_size=(960,640),start_on_title=True,
                   save_path=cls.folder/'journey.json',settings_path=cls.folder/'settings.json')
        cls.g.on_title=False;cls.g.opening.restore({'version':1,'stage':'disabled'})
        cls.g.audio.set_music(0);cls.g.audio.set_effects(0)
        cls.fixture=default_fixture(ROOT)
        cls.entities={e['id']:e for e in cls.g.town.data['entities']}

    @classmethod
    def tearDownClass(cls):
        cls.g.music.stop();pygame.quit();cls.temporary.cleanup();del cls.g;gc.collect()

    def station(self,position,focus=None,reduced=False,clock=0):
        g=self.g;g.world=g.town;g.player.position.update(position)
        g.player.facing='back';g.player.moving=g.player.running=False;g.player.walk_ms=0
        g.opening_fade=g.transfer_cooldown=0;g.elapsed_ms=clock
        g.party_travel.reset();g.audio.set_reduced_motion(reduced)
        g.town.reset_grass(reduced_motion=reduced);g.camera.reset()
        if focus:g.camera.focus(focus,0)
        for door in g.town.doors:door.update(None,10)
        return g

    def native(self):
        self.g.draw()
        return Image.frombytes('RGB',(960,640),pygame.image.tobytes(self.g.canvas.native,'RGB'))

    def test_old_mill_and_school_wall_overlap_routes_support_real_walk_run_both_ways(self):
        self.assertEqual(self.g.town.probe_size,(24,12))
        for name,points in {'mill':[[948,378],[948,312]],'school':[[552,684],[588,684]]}.items():
            for running in (False,True):
                for reverse in (False,True):
                    route=list(reversed(points)) if reverse else points
                    g=self.station(route[0]);self.assertTrue(g.town.can_stand(g.player.position))
                    goal=pygame.Vector2(route[-1]);steps=0
                    for _ in range(300):
                        delta=goal-g.player.position
                        if delta.length()<.5:break
                        old=g.player.position.copy()
                        g.update(min(1/60,delta.length()/(108 if running else 72)),delta,running)
                        self.assertIs(g.world,g.town)
                        self.assertNotEqual(g.player.position,old,(name,running,reverse))
                        self.assertTrue(g.world.can_stand(g.player.position));steps+=1
                    else:self.fail(('perimeter stalled',name,running,reverse))
                    self.assertGreater(steps,10)
                    # Actual wall contact rows are inside the retained blocker;
                    # no new blocker or transparency-on-overlap hides the fix.
                    drawing=generate_architecture(name);left=drawing.metadata['wall_ground_bounds_logical'][0]
                    self.assertGreaterEqual(left,24)

    def test_actual_native_roof_pixels_match_normal_reduced_for_all_thirteen_buildings(self):
        for name,spec in self.fixture['buildings'].items():
            with self.subTest(building=name):
                g=self.station(spec['player'],spec['survey_focus'])
                normal=self.native();camera=g.camera.position()
                self.station(spec['player'],spec['survey_focus'],reduced=True)
                reduced=self.native();self.assertEqual(g.camera.position(),camera)
                drawing=generate_architecture(name);entity=self.entities[name]
                ox,oy=[round((value-origin)*2) for value,origin in zip(entity['position'],camera)]
                mask=Image.new('L',(960,640));mask.paste(drawing.material_masks['roof'],(ox,oy))
                emitter=drawing.metadata['smoke_emitter_logical']
                if emitter:
                    x,y=emitter
                    ImageDraw.Draw(mask).rectangle((ox+x*2-6,0,ox+x*2+10,oy+y*2+2),fill=0)
                delta=ImageChops.difference(normal,reduced).convert('L')
                self.assertIsNone(ImageChops.multiply(delta,mask).getbbox(),name)
                self.assertIsNotNone(mask.getbbox(),name)

    def test_actual_fixed_shop_merchandise_is_stationary_across_ambient_and_reduced_modes(self):
        spec=self.fixture['buildings']['item_shop'];entity=self.entities['item_shop'];seen=[]
        for reduced in (False,True):
            for clock in (0,200,1400,3400):
                self.station(spec['player'],spec['survey_focus'],reduced=reduced,clock=clock)
                native=self.native();camera=self.g.camera.position()
                x=round((entity['position'][0]+70-camera[0])*2);y=round((entity['position'][1]+136-camera[1])*2)
                seen.append(native.crop((x,y,x+156,y+96)).tobytes())
        self.assertEqual(len(set(seen)),1)


if __name__=='__main__':unittest.main()
