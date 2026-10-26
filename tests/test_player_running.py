"""Exercise real Shift input, gait transitions, authored clocks and collision."""
import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT']='1'
from collections import defaultdict
import unittest
from unittest.mock import patch
import pygame
import main

class PlayerRunningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.game=main.Game(fullscreen=False,start_on_title=False,save_path=None)
    @classmethod
    def tearDownClass(cls):pygame.quit()
    def setUp(self):
        self.game.player=main.Player(self.game.world)
        self.player=self.game.player
        self.player.position.update(456,936)
        self.game.map_open=False;self.game.quest_ui.journal_open=False
        self.game.pause.is_open=False;self.game.inventory_ui.is_open=False
    def key_update(self,keys,seconds):
        with patch('main.pygame.key.get_pressed',return_value=defaultdict(bool,{k:True for k in keys})):
            self.game.update(seconds)
    def test_both_shift_keys_select_all_directional_runs_at_authored_speed(self):
        for shift in (pygame.K_LSHIFT,pygame.K_RSHIFT):
            for key,facing in [(pygame.K_a,'left'),(pygame.K_d,'right'),(pygame.K_w,'back'),(pygame.K_s,'front')]:
                self.game.player=main.Player(self.game.world);self.player=self.game.player
                self.player.position.update(456,936)
                start=self.player.position.copy()
                self.key_update([key,shift],.08)
                self.assertTrue(self.player.running);self.assertEqual(self.player.facing,facing)
                self.assertIs(self.player.sprite(),self.player.runs[facing][0][0])
                self.assertAlmostEqual(self.player.position.distance_to(start),main.WALK_SPEED*main.RUN_MULTIPLIER*.08)
                self.key_update([key,shift],.03)
                self.assertIs(self.player.sprite(),self.player.runs[facing][1][0])
    def test_release_shift_direction_change_and_stop(self):
        self.key_update([pygame.K_a,pygame.K_LSHIFT],.31)
        self.assertIs(self.player.sprite(),self.player.runs['left'][3][0])
        self.key_update([pygame.K_a],.08)
        self.assertFalse(self.player.running)
        self.assertIs(self.player.sprite(),self.player.walks['left'][0][0])
        self.key_update([pygame.K_a],.08)
        self.assertIs(self.player.sprite(),self.player.walks['left'][1][0])
        self.key_update([pygame.K_d,pygame.K_RSHIFT],.02)
        self.assertIs(self.player.sprite(),self.player.runs['right'][0][0])
        self.key_update([pygame.K_RSHIFT],.1)
        self.assertFalse(self.player.running);self.assertFalse(self.player.moving)
        self.assertIs(self.player.sprite(),self.player.idles['right'])
    def test_blocked_run_is_idle_and_diagonal_speed_is_normalized(self):
        self.player.position.update(384,294)
        self.player.update((0,-1),.2,self.game.world,True)
        self.assertFalse(self.player.moving);self.assertFalse(self.player.running)
        self.assertIs(self.player.sprite(),self.player.idles['back'])
        self.player.position.update(456,936);start=self.player.position.copy()
        self.player.update((1,1),.1,self.game.world,True)
        self.assertAlmostEqual(self.player.position.distance_to(start),10.8)
    def test_pause_freezes_run_clock_and_scripted_pose_takes_precedence(self):
        self.key_update([pygame.K_d,pygame.K_LSHIFT],.11)
        sprite=self.player.sprite();position=self.player.position.copy();clock=self.player.walk_ms
        self.game.pause.is_open=True
        self.key_update([pygame.K_d,pygame.K_LSHIFT],.5)
        self.assertEqual(self.player.position,position);self.assertEqual(self.player.walk_ms,clock)
        self.assertIs(self.player.sprite(),sprite)
        self.game.pause.is_open=False
        pose=pygame.Surface((24,36),pygame.SRCALPHA);self.player.story_sprite=pose
        self.assertIs(self.player.sprite(),pose)
        self.player.story_sprite=None
        self.assertIs(self.player.sprite(),sprite)

if __name__=='__main__':unittest.main()
