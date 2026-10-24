"""Keep the female jaw fix limited and consistent across exported poses."""
import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT']='1'

from pathlib import Path
import json
import unittest
import pygame
import main

ROOT=Path(__file__).resolve().parents[1]
BEFORE=ROOT/'docs/reviews/female_profile_chin/before'
LANDMARKS={'left':{(9,11):(232,196,157,255),(10,11):(237,160,82,255),(10,12):(237,160,82,255)},
           'right':{(14,11):(232,196,157,255),(13,11):(237,160,82,255),(13,12):(237,160,82,255)}}


class FemaleProfileChin(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.game=main.Game(fullscreen=False)

    @classmethod
    def tearDownClass(cls):pygame.quit()

    def assert_only_jaw_changed(self,before,after,direction,dy=0):
        expected={(x,y+dy):color for (x,y),color in LANDMARKS[direction].items()}
        changed={(x,y):tuple(after.get_at((x,y))) for y in range(36) for x in range(24)
                 if before.get_at((x,y))!=after.get_at((x,y))}
        self.assertEqual(changed,expected)
        self.assertEqual(pygame.image.tobytes(before,'RGBA')[3::4],pygame.image.tobytes(after,'RGBA')[3::4])

    def test_idles_change_only_three_jaw_pixels_in_each_profile_and_palette(self):
        for number in (1,2,3):
            for direction in ('left','right'):
                before=pygame.image.load(str(BEFORE/f'female_{number:02}/idle_{direction}.png'))
                after=self.game.world.image(f'assets/characters/npcs/female_{number:02}/idle_{direction}.png')
                self.assert_only_jaw_changed(before,after,direction)

    def test_walks_keep_eyes_stride_and_bob_with_only_the_same_jaw_correction(self):
        for number in (1,2,3):
            for direction in ('left','right'):
                folder=ROOT/f'assets/characters/npcs/female_{number:02}/walk_{direction}'
                meta=json.loads((folder/'animation.json').read_text())
                self.assertEqual([r['duration_ms'] for r in meta['frames']],[140]*4)
                for index,frame in enumerate(meta['frames'],1):
                    before=pygame.image.load(str(BEFORE/f'female_{number:02}/walk_{direction}_{index:02}.png'))
                    after=self.game.world.image((folder/frame['file']).relative_to(ROOT).as_posix())
                    self.assert_only_jaw_changed(before,after,direction,frame['upper_body_offset'][1])

    def test_gardener_uses_corrected_heads_in_all_visible_profile_poses(self):
        a=self.game.world.npcs[1]
        recipe=main.read_json(ROOT/'assets/source/characters/npcs/female_02/gardener/recipe.json')
        checked=0
        for name,image in a.bodies.items():
            if name in recipe['work_poses']:
                pose=recipe['work_poses'][name];direction=pose['direction'];dx,dy=pose['lean']
            else:
                direction=name.split('.')[1].split('_')[0];dx=0
                dy=-1 if name.endswith(('_02','_04')) else 0
            if direction not in LANDMARKS:continue
            arms=self.game.world.image(f'assets/source/characters/npcs/female_02/gardener/parts/{name}_arms.png')
            for (x,y),color in LANDMARKS[direction].items():
                p=(12+x+dx,6+y+dy)
                if arms.get_at(p).a:continue
                self.assertEqual(tuple(image.get_at(p)),color,(name,p))
                checked+=1
        self.assertGreater(checked,60)


if __name__=='__main__':unittest.main()
