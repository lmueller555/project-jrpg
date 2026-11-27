"""Veinhold effects convey extraction and emergency with distinct colors."""
from copy import deepcopy
import json
import os
import unittest
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
import pygame
from cinematic_facility import CinematicFacility
from fire_veinhold_opening import SCENE


class CinematicFacilityTests(unittest.TestCase):
    def setUp(self):
        pygame.init();pygame.display.set_mode((960,640))
        self.data=json.loads((SCENE.parent/'shot01/environment/art.json').read_text())['facility']
        self.facility=CinematicFacility(self.data,(1024,1536))

    def tearDown(self):pygame.quit()

    def test_power_packets_travel_toward_reservoir_and_warning_beacons_change(self):
        first,later=self.facility.samples(0),self.facility.samples(1)
        for a,b,source in zip(first['conduits'],later['conduits'],self.data['conduits']):
            endpoint=source['points'][-1]
            self.assertLess(pygame.Vector2(b['to']).distance_to(endpoint),pygame.Vector2(a['to']).distance_to(endpoint))
        self.assertNotEqual(first['beacons'],later['beacons'])
        self.assertEqual(first,self.facility.samples(0))

    def test_reduced_motion_uses_steady_red_lights_and_static_power_accents(self):
        self.assertEqual(self.facility.samples(0,True),self.facility.samples(20,True))
        target=pygame.Surface((1024,650));target.fill('#0c1a36')
        state=self.facility.samples(3,True);self.facility.draw(target,state,1.,(0,0))
        point=tuple(self.data['beacons'][0]['origin']);red=target.get_at(point)
        self.assertGreater(red.r,red.g*4)
        amber=target.get_at(tuple(round(v) for v in state['conduits'][0]['from']))
        self.assertGreater(amber.g,amber.r*.5)

    def test_off_art_landmarks_fail_before_playback(self):
        invalid=deepcopy(self.data);invalid['beacons'][0]['origin']=[float('inf'),1]
        with self.assertRaises(ValueError):CinematicFacility(invalid,(1024,1536))
