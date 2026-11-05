"""A face-height forward guard catches the straight attack aimed into Rhea's ice."""
import json
import os
from pathlib import Path
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

import pygame

from ice_reaper_action import IceReaperActionStage as Stage


ROOT = Path(__file__).resolve().parents[1]


class LucanForwardInterceptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((480,320))
        cls.stage = Stage(ROOT/'assets/story/ice_reaper_rescue', strict=True)
        cls.folder = ROOT/'assets/story/ice_reaper_continuity/actors/lucan'
        cls.landmarks = json.loads((cls.folder/'provenance.json').read_text())[
            'guard_correction']['native_guard_geometry']

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_straight_attack_still_threatens_rhea_and_arrives_at_nine_seconds(self):
        release, target = Stage.first_shard_release(), Stage.first_shard_target()
        self.assertEqual(release, pygame.Vector3(3.6,8.3,-8))
        self.assertEqual(target, pygame.Vector3(-3,.4,0))
        rhea = Stage.actor_positions(8.9)['rhea']
        self.assertEqual((target.x,target.z),(rhea.x,rhea.z))
        self.assertTrue(.15 < target.y < 1.85)
        contact = Stage.first_shard_shield_contact()
        incoming = target-release
        self.assertLess((contact-release).cross(incoming).length(),1e-8)
        self.assertLess(contact.distance_to(release.lerp(target,.8625)),1e-8)
        self.assertLess(Stage.first_shard_tip(9.).distance_to(contact),1e-8)
        self.assertGreater((target-contact).dot(incoming),0)

    def test_board_is_in_front_of_lucan_and_within_a_bent_arms_reach(self):
        foot = Stage.lucan_guard_position()
        contact = Stage.first_shard_shield_contact()
        facing = Stage.actor_heading('lucan',8.9)
        horizontal = contact-foot
        horizontal.y = 0
        # The previous overhead contact was .59 units behind his facing.
        self.assertGreater(horizontal.dot(facing),.3)
        left = pygame.Vector3(-facing.z,0,facing.x)
        self.assertGreater(horizontal.dot(left),.35)
        self.assertLess(contact.distance_to(foot+pygame.Vector3(0,1.05,0)),.85)
        self.assertLess(foot.z, Stage.actor_positions(8.9)['rhea'].z)
        self.assertLess(abs(foot.x+3),.4)

    def test_projected_attack_hits_the_opaque_forward_rim_through_first_recoil(self):
        contact = Stage.first_shard_shield_contact()
        for time in (8.99,9.,9.05,9.12,9.16):
            with self.subTest(time=time):
                camera = Stage.camera(time)
                position = Stage.actor_positions(time)['lucan']
                foot = camera.project(position)
                point = camera.project(contact)
                action,local,duration = self.stage._action('lucan',time)
                image,data = self.stage._sequence('lucan',action,local,duration,
                                                 camera,position,time=time)
                scale = camera.focal*1.85/foot[2]/data['body_pixels']
                native = (round(data['anchor'][0]+(point[0]-foot[0])/scale),
                          round(data['anchor'][1]+(point[1]-foot[1])/scale))
                self.assertEqual(list(native),self.landmarks['shield_contact_upper_rim'])
                self.assertGreater(image.get_at(native).a,200)
                face = self.landmarks['face_center']
                shield = self.landmarks['shield_center']
                self.assertGreater(shield[0],face[0])
                threat = camera.project(Stage.first_shard_release())
                self.assertGreater(threat[0]-point[0],0)

    def test_settled_guard_keeps_the_reviewed_held_pose_scale(self):
        held = self.stage.actors['lucan']['sequences']['hold_brace_right'][0][0]
        for filename in ('brace_rear_left_08.png','impact_rear_left_01.png'):
            image = pygame.image.load(str(self.folder/filename))
            self.assertLessEqual(abs(image.get_bounding_rect().height-held.get_bounding_rect().height),2)
            self.assertEqual(image.get_bounding_rect().bottom,117)

    def test_restaging_does_not_move_other_characters_or_the_rescue_camera(self):
        positions = Stage.actor_positions(8.5)
        expected = {'rhea':(-3,0,0),'caelan':(-1.5,0,1.25),
                    'mira':(7,0,10),'ice_reaper':(2,6.6,-8)}
        for actor,point in expected.items():
            self.assertLess(positions[actor].distance_to(point),1e-8)
        camera = Stage.camera(8.5)
        self.assertEqual(tuple(camera.position),(7.,4.7,15.))
        self.assertEqual(tuple(camera.target),(-1.7,1.9,.5))
        self.assertEqual(camera.focal,650)


if __name__ == '__main__':
    unittest.main()
