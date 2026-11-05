"""Physical and authored-motion checks for the 15-second rescue extension."""
import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
from pathlib import Path
import unittest
import pygame
from ice_reaper_action import IceReaperActionStage, PerspectiveCamera

ROOT=Path(__file__).resolve().parents[1]

class IceReaperActionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init();pygame.display.set_mode((480,320))
        cls.stage=IceReaperActionStage(ROOT/'assets/story/ice_reaper_rescue',strict=True)

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_contacts_keep_the_two_attacks_and_prison_states_distinct(self):
        self.assertEqual(self.stage.telemetry(8.49)['prison'],'intact')
        self.assertEqual(self.stage.telemetry(8.5)['prison'],'cracked')
        self.assertEqual(self.stage.telemetry(8.99)['first_shard'],'flight')
        self.assertEqual(self.stage.telemetry(9.)['first_shard'],'intercepted')
        self.assertEqual(self.stage.telemetry(14.69)['second_shard'],'forming')
        self.assertEqual(self.stage.telemetry(14.7)['second_shard'],'destroyed')
        self.assertEqual(self.stage.telemetry(16.29)['prison'],'cracked')
        self.assertEqual(self.stage.telemetry(16.3)['prison'],'shattered')

    def test_swordsman_arrives_right_of_prison_and_lands_beyond_it(self):
        p=self.stage.actor_positions(7.5)
        self.assertGreater(p['caelan'].x,p['rhea'].x)
        p=self.stage.actor_positions(9.4)
        self.assertLess(p['caelan'].x,p['rhea'].x)

    def test_orbit_reverses_position_and_rhea_remains_panorama_focus(self):
        c1=self.stage.camera(9.5);c2=self.stage.camera(10.999999)
        center=pygame.Vector3(-2,1.7,1)
        a=pygame.Vector3(c1.position)-center;b=pygame.Vector3(c2.position)-center
        self.assertAlmostEqual(a.x,-b.x,places=4)
        self.assertAlmostEqual(a.z,-b.z,places=4)
        for time in (18.3,19,19.99):
            camera=self.stage.camera(time)
            x,y,depth=camera.project(camera.target)
            self.assertAlmostEqual(x,240);self.assertAlmostEqual(y,158)
        self.assertEqual(self.stage._action('ice_reaper',19)[0],'ready_rear')

    def test_continuous_camera_boundaries_do_not_change_lens_or_position(self):
        for boundary in (9.5,11.,12.8,17.2):
            before=self.stage.camera(boundary-.000001)
            after=self.stage.camera(boundary)
            self.assertLess(pygame.Vector3(before.position).distance_to(after.position),.001)
            self.assertAlmostEqual(before.focal,after.focal,places=3)

    def test_active_brace_and_slash_keep_their_authored_frames(self):
        camera=self.stage.camera(8)
        for actor,action,start,end,count in (('caelan','slash',7.5,9.15,10),('lucan','brace',7.5,9,8)):
            position=self.stage.actor_positions(8)[actor]
            images=[]
            for i in range(count):
                local=(i+.1)/count*(end-start)
                image,_=self.stage._sequence(actor,action,local,end-start,camera,position)
                images.append(pygame.image.tobytes(image,'RGBA'))
            self.assertEqual(len(set(images)),count)

    def test_shard_can_aim_at_an_offscreen_target(self):
        camera=self.stage.camera(5.8)
        self.assertIsNone(camera.project((-.8,1.35,1.15)))
        canvas=pygame.Surface((480,320));canvas.fill('black')
        self.stage._draw_shard(canvas,camera,(2,11.4,-8),(-.8,1.35,1.15))
        self.assertGreater(pygame.surfarray.array3d(canvas).sum(),0)

    def test_random_access_render_is_identical_after_other_shots(self):
        for reduced in (False,True):
            for time in (8.5,13.9,16.8,19.4):
                canvas=pygame.Surface((480,320))
                self.stage.draw(canvas,time,reduced)
                original=pygame.image.tobytes(canvas,'RGBA')
                self.stage.draw(canvas,11.8,reduced)
                self.stage.reset()
                self.stage.draw(canvas,time,reduced)
                self.assertEqual(original,pygame.image.tobytes(canvas,'RGBA'))

if __name__=='__main__':unittest.main()
