"""The well's real footprint, walkable square, depth and restrained animation."""
import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT']='1'

import unittest
from unittest.mock import patch
import pygame
import main


class WellSquare(unittest.TestCase):
    def setUp(self):
        self.game=main.Game(fullscreen=False);self.world=self.game.town
        self.well=next(e for e in self.world.entities if e['id']=='well')
        self.meta=main.read_json(main.ROOT/'assets/terrain/eldenmere/well/well.json')

    def tearDown(self):pygame.quit()

    def test_well_is_solid_without_tunnelling_from_any_side(self):
        self.assertEqual(self.meta['ground_rect'],[504,840,48,48])
        self.assertFalse(self.world.can_stand((528,864)))
        player=self.game.player
        for start,direction,axis,limit,less in [
            ((528,816),(0,1),1,834,True),((528,924),(0,-1),1,894,False),
            ((480,864),(1,0),0,492,True),((576,864),(-1,0),0,564,False)]:
            with self.subTest(start=start):
                player.position.update(start)
                player.update(direction,2,self.world,True)
                self.assertTrue(self.world.can_stand(player.position))
                if less:self.assertLessEqual(player.position[axis],limit)
                else:self.assertGreaterEqual(player.position[axis],limit)

    def test_full_ring_and_south_connection_are_walkable(self):
        player=self.game.player
        corners=[(480,816),(576,816),(576,924),(480,924),(480,816)]
        player.position.update(corners[0])
        for target in corners[1:]:
            delta=pygame.Vector2(target)-player.position
            player.update(delta,delta.length()/main.WALK_SPEED,self.world)
            self.assertLess(player.position.distance_to(target),.01)
        player.position.update(528,924)
        player.update((0,1),1.5,self.world)
        self.assertAlmostEqual(player.position.y,1032)
        for name in ('well_north','well_south','well_west','well_east','well_square_south'):
            self.assertTrue(self.world.can_stand(self.world.data['destinations'][name]),name)

    def test_water_moves_while_structure_rope_and_crank_stay_fixed(self):
        frames=self.well['surfaces'];first=frames[0]
        self.assertEqual(len(frames),6)
        self.assertEqual(first.get_size(),(84,96))
        self.assertGreater(len({pygame.image.tobytes(f,'RGBA') for f in frames}),1)
        mask=self.world.image('assets/source/terrain/eldenmere/well/parts/water_mask.png',False)
        for frame in frames:
            for y in range(96):
                for x in range(84):
                    self.assertEqual(frame.get_at((x,y)).a,first.get_at((x,y)).a)
                    if frame.get_at((x,y))!=first.get_at((x,y)):
                        self.assertEqual(mask.get_at((x,y)).r,255)

    def test_roof_occludes_from_behind_and_player_draws_in_front(self):
        player=self.game.player
        marker=pygame.Surface((24,36),pygame.SRCALPHA);marker.fill('#ff00ff')
        target=pygame.Surface(main.VIEW_SIZE);camera=(408,768)
        with patch.object(player,'sprite',return_value=marker):
            player.position.update(528,828)
            self.world.draw(target,camera,player,0)
            self.assertNotEqual(target.get_at((120,52))[:3],(255,0,255))
            player.position.update(528,900)
            self.world.draw(target,camera,player,0)
            self.assertEqual(target.get_at((120,112))[:3],(255,0,255))

    def test_square_preserves_building_access_and_gathering_space(self):
        layout=main.read_json(main.ROOT/self.world.data['layout_source'])
        self.assertEqual(layout['plaza_rect_tiles'],[16,32,10,8])
        gathering=pygame.Rect(layout['gathering_rect'])
        self.assertFalse(gathering.colliderect(pygame.Rect(self.meta['ground_rect'])))
        for y in range(gathering.top+6,gathering.bottom-5,12):
            for x in range(gathering.left+12,gathering.right-11,24):
                self.assertTrue(self.world.can_stand((x,y)))
        for door in self.world.doors:
            self.assertTrue(self.world.can_stand(pygame.Vector2(door.data['anchor'])+(0,12)),door.data['id'])
        self.assertEqual(next(l['name'] for l in self.world.data['landmarks'] if l['id']=='commons'),'Well square')


if __name__=='__main__':unittest.main()
