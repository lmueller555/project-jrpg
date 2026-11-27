"""Full plume cycles keep vents fixed and transparent canvases invisible."""
from copy import deepcopy
import json
import os
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import pygame
from cinematic_smoke import CinematicSmoke
from fire_veinhold_opening import SCENE


class CinematicSmokeTests(unittest.TestCase):
    def setUp(self):
        pygame.init();pygame.display.set_mode((960,640))
        folder = SCENE.parent/'shot01/environment'
        self.data = json.loads((folder/'art.json').read_text())['smoke']
        self.frames = [(pygame.image.load(str(folder/f['file'])).convert_alpha(), f['duration_ms']/1000.)
                       for f in self.data['frames']]
        self.records = self.data['emitters']
        self.smoke = CinematicSmoke(self.frames, self.data['anchor'], self.records, (1024,1536))

    def tearDown(self):pygame.quit()

    def test_drawn_cycle_has_distinct_complete_frames_and_clear_canvas_edges(self):
        self.assertEqual(len(self.frames),16)
        self.assertEqual(len({pygame.image.tobytes(f,'RGBA') for f,_ in self.frames}),16)
        for frame,_ in self.frames:
            self.assertTrue(pygame.Rect(8,8,240,240).contains(frame.get_bounding_rect()))
        self.assertFalse((SCENE.parent/'shot01/environment/smoke_puff.png').exists())

    def test_clock_seeks_and_loop_preserve_both_vent_anchors_without_particle_births(self):
        first = self.smoke.samples(0)
        later = self.smoke.samples(20.13)
        self.smoke.samples(1)
        self.assertEqual(later,self.smoke.samples(20.13))
        for a,b in zip(first,self.smoke.samples(self.smoke.duration)):
            self.assertEqual(a['frame'],b['frame'])
            self.assertAlmostEqual(a['blend'],b['blend'])
            self.assertEqual(a['origin'],b['origin'])
        self.assertEqual(len(self.smoke.samples(1000000)),2)
        for before,after in zip(first,later):
            self.assertEqual(before['origin'],after['origin'])
            self.assertEqual(before['scale'],after['scale'])
            self.assertNotEqual((before['frame'],before['blend']),(after['frame'],after['blend']))

    def test_premultiplied_interpolation_does_not_dim_overlap_or_expose_hidden_rgb(self):
        image=pygame.Surface((64,64),pygame.SRCALPHA);image.fill((255,255,255,0))
        pygame.draw.rect(image,(255,255,255,255),(20,20,24,24))
        record=dict(id='test',origin=[80,90],scale=1.,opacity=255,tint=[255,255,255],phase_seconds=0.)
        stage=CinematicSmoke([(image,.25),(image.copy(),.25)],[32,52],[record],(200,200))
        target=pygame.Surface((200,200));target.fill('#0c1a36')
        stage.draw(target,stage.samples(.125),1.,(0,0))
        self.assertGreaterEqual(min(target.get_at((80,70))[:3]),253)
        self.assertEqual(target.get_at((48,38))[:3],(12,26,54))

    def test_both_complete_plumes_change_visibly_at_their_registered_vents(self):
        background=pygame.Surface((1024,650));background.fill('#0c1a36')
        a,b=background.copy(),background.copy()
        self.smoke.draw(a,self.smoke.samples(15),1.,(0,-50))
        self.smoke.draw(b,self.smoke.samples(15.5),1.,(0,-50))
        for rect in (pygame.Rect(470,50,180,230),pygame.Rect(735,35,230,240)):
            self.assertNotEqual(pygame.image.tobytes(a.subsurface(rect),'RGB'),pygame.image.tobytes(background.subsurface(rect),'RGB'))
            self.assertNotEqual(pygame.image.tobytes(a.subsurface(rect),'RGB'),pygame.image.tobytes(b.subsurface(rect),'RGB'))

    def test_invalid_art_and_nonfinite_emitters_are_rejected(self):
        for key,value in (('origin',[2000,1]),('scale',float('nan')),('opacity',256)):
            records=deepcopy(self.records);records[0][key]=value
            with self.assertRaises(ValueError):CinematicSmoke(self.frames,self.data['anchor'],records,(1024,1536))
        square=self.frames[0][0].copy();square.set_at((0,0),(255,255,255,255))
        with self.assertRaises(ValueError):CinematicSmoke([(square,.25)]*2,self.data['anchor'],self.records,(1024,1536))
        with self.assertRaises(ValueError):self.smoke.samples(float('nan'))
