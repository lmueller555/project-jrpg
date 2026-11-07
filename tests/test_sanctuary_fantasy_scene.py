"""Fantasy landmarks preserve physical access and occlude at real ground depth."""
from hashlib import sha256
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest

os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
import pygame

from main import Player, World, camera_for


ROOT=Path(__file__).resolve().parents[1]
MAP=ROOT/'assets/maps/elden_vale_sanctuary/map.json'


class SanctuaryFantasySceneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init();pygame.display.set_mode((480,320))
        cls.world=World(MAP)
        cls.player=Player(cls.world)
        cls.player.facing='front'

    @classmethod
    def tearDownClass(cls):pygame.quit()

    def test_old_navigation_mask_and_public_locations_remain_usable(self):
        self.assertEqual(sha256((ROOT/self.world.data['collision']).read_bytes()).hexdigest(),
                         '7d8c27cda7f1f8774f70c0c9bc79eb8ce865b58c5c519e3b54e79011eb90cfd5')
        for name,point in self.world.data['fantasy_review_points'].items():
            with self.subTest(review=name):self.assertTrue(self.world.can_stand(point))
        self.assertEqual(self.world.data['doors'][0]['anchor'],[535,345])
        self.assertEqual(self.world.data['cave_barrier']['footprint'],[972,359,72,12])
        self.assertFalse(self.world.can_stand((1008,365)))

    def assert_depth(self,feet,point,hidden):
        self.player.position.update(feet)
        self.assertTrue(self.world.can_stand(feet))
        camera=camera_for(feet,self.world.size)
        bare=pygame.Surface((480,320));shown=bare.copy()
        invisible=SimpleNamespace(position=self.player.position,story_visible=False)
        self.world.draw(bare,camera,invisible,0,False)
        self.world.draw(shown,camera,self.player,0,False)
        local=point[0]-feet[0]+12,point[1]-feet[1]+30
        color=self.player.sprite().get_at(local)
        self.assertEqual(color.a,255)
        screen=point[0]-camera[0],point[1]-camera[1]
        scenery=bare.get_at(screen)
        self.assertNotEqual(scenery,color)
        self.assertEqual(shown.get_at(screen),scenery if hidden else color)

    def test_landmark_crown_and_crystals_cover_rear_poses_but_leave_front_poses_visible(self):
        # Independently measured actor pixels on the final assembled landmarks.
        for feet,point,hidden in (
            ((360,240),(360,220),True),
            ((360,314),(360,294),False),
            ((1078,310),(1078,290),True),
            ((1008,384),(1008,364),False),
        ):
            with self.subTest(feet=feet):self.assert_depth(feet,point,hidden)

    def test_crystal_instances_leave_the_dark_opening_clear_in_every_pose(self):
        # The middle of the cave remains dark and readable above the keeper rail.
        for entity in self.world.entities:
            if not entity['id'].startswith(('ridge_crystal','ridge_vein')):continue
            for surface in entity['surfaces']:
                for point in ((1008,328),(1008,343),(1025,345)):
                    x=point[0]-entity['position'][0];y=point[1]-entity['position'][1]
                    if 0<=x<surface.get_width() and 0<=y<surface.get_height():
                        with self.subTest(entity=entity['id'],point=point):
                            self.assertEqual(surface.get_at((x,y)).a,0)

    def test_all_ambient_animation_retains_a_static_reduced_motion_pose(self):
        animated=[record for record in self.world.data['entities'] if len(record['frames'])>1]
        self.assertGreater(len(animated),20)
        for record in animated:
            with self.subTest(entity=record['id']):self.assertEqual(record['reduced_motion_frame'],0)
        self.world.reduced_motion=True
        self.player.position.update(1008,406)
        camera=camera_for(self.player.position,self.world.size)
        first=pygame.Surface((480,320));later=first.copy()
        self.world.draw(first,camera,self.player,0,False)
        self.world.draw(later,camera,self.player,3800,False)
        self.assertEqual(pygame.image.tobytes(first,'RGB'),pygame.image.tobytes(later,'RGB'))
        self.world.reduced_motion=False


if __name__=='__main__':unittest.main()
