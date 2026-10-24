"""Checks of Mira's readable, stationary work cycle in the actual town."""
import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT']='1'

import unittest
from unittest.mock import patch
import pygame
import main


class MiraBench(unittest.TestCase):
    def setUp(self):
        self.game=main.Game(fullscreen=False,start_on_title=False)
        self.world=self.game.town
        self.mira=self.world.npcs[0]

    def tearDown(self):pygame.quit()

    def test_pose_boundaries_loop_and_fitting_stay_synchronized(self):
        mira=self.mira
        self.assertEqual(mira.duration_ms,8000)
        time=0
        for sprite,fitting,record in mira.frames:
            with self.subTest(pose=record['pose'],time=time):
                self.assertIs(mira.frame(time)[0],sprite)
                self.assertIs(mira.frame(time+record['duration_ms']-.01)[1],fitting)
                self.assertIs(mira.frame(time+8000)[0],sprite)
            time+=record['duration_ms']
        poses={frame[2]['pose']:frame for frame in mira.frames}
        self.assertIsNot(poses['wrench_high'][0],poses['wrench_pull'][0])
        self.assertNotEqual(pygame.image.tobytes(poses['test_a'][1],'RGBA'),
                            pygame.image.tobytes(poses['test_b'][1],'RGBA'))
        self.assertEqual(sum(f[2]['pose']=='wrench_pull' for f in mira.frames),3)

    def test_feet_fixed_and_tool_attached_to_the_bench_fitting(self):
        source=self.world.image('assets/source/characters/mira/directions/appearance_back.png')
        feet=pygame.image.tobytes(source.subsurface((0,30,24,6)),'RGBA')
        for sprite,_,_ in self.mira.frames:
            self.assertEqual(sprite.get_size(),(24,36))
            self.assertEqual(pygame.image.tobytes(sprite.subsurface((0,30,24,6)),'RGBA'),feet)
        recipe=main.read_json(main.ROOT/'assets/source/characters/mira/work_bench/recipe.json')
        self.assertEqual(recipe['station'],list(self.mira.position))
        x,y=self.mira.position-pygame.Vector2(self.mira.animation['draw_anchor'])
        for name in ('wrench_high','wrench_mid','wrench_pull'):
            pose=recipe['poses'][name]
            pivot=pygame.Vector2(pose['tool_pivot'])+(x,y)
            self.assertTrue(pygame.Rect(self.mira.data['fitting_position'],(12,9)).collidepoint(pivot))
        high=recipe['poses']['wrench_high']['working_arm'][-1]
        low=recipe['poses']['wrench_pull']['working_arm'][-1]
        self.assertGreaterEqual(pygame.Vector2(high).distance_to(low),6)

    def test_collision_stops_player_and_preserves_bench_and_door_access(self):
        mira=self.mira
        self.assertIsNone(self.world.blocked.overlap(pygame.Mask(mira.blocker.size,fill=True),mira.blocker.topleft))
        self.assertFalse(self.world.can_stand(mira.position))
        player=self.game.player
        player.position.update(610,480)
        player.update((0,-1),1,self.world)
        self.assertGreaterEqual(player.position.y,456)
        self.assertTrue(self.world.can_stand(player.position))
        for point in ((594,456),(624,456),(636,438),(636,450)):
            self.assertTrue(self.world.can_stand(point),point)
        # Actual walk from the south still enters Mira's shop.
        player.position.update(636,480)
        for _ in range(90):
            self.game.update(1/60,(0,-1),False)
            if self.game.world is not self.world:break
        self.assertEqual(self.game.world.data['id'],'mira')

    def test_scene_changes_keep_one_mira_and_do_not_restart_the_routine(self):
        self.game.update(2.6,(0,0),False)
        door=next(d for d in self.world.doors if d.data['id']=='mira')
        self.game.enter(door)
        self.assertEqual(self.game.world.npcs,[])
        self.game.update(.7,(0,0),False)
        self.game.enter(self.game.world.doors[0])
        self.assertIs(self.game.world.npcs[0],self.mira)
        self.assertEqual(len(self.game.world.npcs),2)
        self.assertIs(self.mira.frame(self.game.elapsed_ms)[0],self.mira.frame(3300)[0])
        self.assertEqual(list(self.mira.position),[610,448])

    def test_player_can_pass_behind_and_in_front_of_mira(self):
        player=self.game.player
        marker=pygame.Surface((24,36),pygame.SRCALPHA);marker.fill('#ff00ff')
        target=pygame.Surface(main.VIEW_SIZE)
        camera=(500,320)
        with patch.object(player,'sprite',return_value=marker):
            player.position.update(610,442)
            self.world.draw(target,camera,player,0)
            self.assertNotEqual(target.get_at((110,120))[:3],(255,0,255))
            player.position.update(610,454)
            self.world.draw(target,camera,player,0)
            self.assertEqual(target.get_at((110,120))[:3],(255,0,255))


if __name__=='__main__':unittest.main()
