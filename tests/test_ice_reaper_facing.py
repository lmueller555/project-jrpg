"""World-facing and camera-view contracts for the moving rescue camera."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
from pathlib import Path
import unittest
import pygame
from ice_reaper_action import IceReaperActionStage, PerspectiveCamera

ROOT=Path(__file__).resolve().parents[1]

class IceReaperFacingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init();pygame.display.set_mode((480,320))
        cls.stage=IceReaperActionStage(ROOT/'assets/story/ice_reaper_rescue',strict=True)

    @classmethod
    def tearDownClass(cls):pygame.quit()

    def test_heading_follows_intent_not_the_camera(self):
        for actor in ('mira',):
            for time in (9.5,10.5,11.,18.,19.9):
                positions=self.stage.actor_positions(time)
                intended=positions['ice_reaper']-positions[actor];intended.y=0
                self.assertGreater(self.stage.actor_heading(actor,time).dot(intended.normalize()),.999)
        heading=self.stage.actor_heading('caelan',9.8)
        self.assertEqual(heading,self.stage.actor_heading('caelan',11.))
        self.assertEqual(heading,self.stage.actor_heading('caelan',19.))

    def test_frozen_rhea_keeps_party_heading_then_turns_after_release(self):
        for time in (5.,9.5,11.,16.299):
            self.assertEqual(self.stage.actor_heading('rhea',time),pygame.Vector3(0,0,1))
        positions=self.stage.actor_positions(17.2)
        intended=positions['ice_reaper']-positions['rhea'];intended.y=0
        self.assertGreater(self.stage.actor_heading('rhea',17.2).dot(intended.normalize()),.999)
        previous=self.stage.actor_heading('rhea',16.3)
        # The approved burst now carries her turn into the .65-second retreat.
        for i in range(1,40):
            heading=self.stage.actor_heading('rhea',16.3+i/60)
            self.assertLess(previous.angle_to(heading),7.)
            previous=heading

    def test_signed_view_angles_distinguish_both_sides_and_back(self):
        actor='rhea';time=10.;position=self.stage.actor_positions(time)[actor]
        heading=self.stage.actor_heading(actor,time)
        right=pygame.Vector3(heading.z,0,-heading.x)
        for direction,expected in ((heading,0),(right,90),(-heading,180),(-right,-90)):
            camera=PerspectiveCamera(tuple(position+direction*5+pygame.Vector3(0,2,0)),tuple(position))
            angle,elevation=self.stage.view_angles(actor,camera,position,time)
            self.assertAlmostEqual(abs(angle) if expected==180 else angle,expected)
            self.assertGreater(elevation,0)

    def test_rhea_does_not_remain_front_facing_through_half_orbit(self):
        position=self.stage.actor_positions(10.)['rhea']
        first=self.stage.view_angles('rhea',self.stage.camera(9.5),position,10.)[0]
        last=self.stage.view_angles('rhea',self.stage.camera(10.999),position,10.)[0]
        angular_distance=abs((last-first+180)%360-180)
        self.assertGreater(angular_distance,120)

    def test_facing_does_not_force_boss_to_rear_at_a_timestamp(self):
        self.assertEqual(self.stage._action('ice_reaper',17.749)[0],'recharge')
        self.assertEqual(self.stage._action('ice_reaper',17.751)[0],'recharge')
        position=self.stage.actor_positions(19.)['ice_reaper']
        heading=self.stage.actor_heading('ice_reaper',19.)
        front=PerspectiveCamera(tuple(position+heading*5+pygame.Vector3(0,2,0)),tuple(position))
        rear=PerspectiveCamera(tuple(position-heading*5+pygame.Vector3(0,2,0)),tuple(position))
        self.assertAlmostEqual(self.stage.view_angles('ice_reaper',front,position,19.)[0],0)
        self.assertAlmostEqual(abs(self.stage.view_angles('ice_reaper',rear,position,19.)[0]),180)

    def test_boss_holds_angle_specific_pose_between_shard_attacks(self):
        selected=[]
        for time in (9.5,10.2,10.8):
            camera=self.stage.camera(time);position=self.stage.actor_positions(time)['ice_reaper']
            action,local,duration=self.stage._action('ice_reaper',time)
            self.assertEqual(action,'ready');self.assertIsNone(duration)
            selected.append(self.stage.sequence_key('ice_reaper',action,local,duration,camera,position,time))
        self.assertGreater(len(set(selected)),1)

    def test_held_view_uses_signed_direction_without_mirroring_equipment(self):
        data=self.stage.actors['rhea'];original=data['sequences'];manifest=data['manifest']
        try:
            image=pygame.Surface((128,128),pygame.SRCALPHA)
            data['sequences']={key:[(image.copy(),.1)] for key in ('ready','frozen_right','frozen_left')}
            data['manifest']={'animations':{}}
            pos=self.stage.actor_positions(10.)['rhea'];heading=self.stage.actor_heading('rhea',10.)
            right=pygame.Vector3(heading.z,0,-heading.x)
            for direction,key in ((right,'frozen_right'),(-right,'frozen_left')):
                camera=PerspectiveCamera(tuple(pos+direction*4),tuple(pos))
                chosen=self.stage.sequence_key('rhea','ready',0,None,camera,pos,10.)
                self.assertEqual(chosen,key)
        finally:data['sequences']=original;data['manifest']=manifest

    def test_foreground_boss_is_same_projected_body_as_normal_shot(self):
        for time in (18.2,19.3):
            camera=self.stage.camera(time);position=self.stage.actor_positions(time)['ice_reaper']
            standard=pygame.Surface((480,320),pygame.SRCALPHA)
            foreground=pygame.Surface((480,320),pygame.SRCALPHA)
            self.stage._billboard(standard,'ice_reaper',position,camera,time)
            self.stage._foreground_boss(foreground,camera,time)
            self.assertEqual(pygame.image.tobytes(standard,'RGBA'),pygame.image.tobytes(foreground,'RGBA'))

if __name__=='__main__':unittest.main()
