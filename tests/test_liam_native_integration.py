"""Liam's named replacement must never fall back to legacy action bodies."""
import os
import tempfile
import unittest
from pathlib import Path
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')

import pygame
from main import Game
from rendering import WorldCanvas


class LiamNativeIntegration(unittest.TestCase):
    def test_home_and_all_lantern_sections_use_one_native_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            game=Game(fullscreen=False,start_on_title=False,save_path=root/'save.json',
                      settings_path=root/'settings.json')
            try:
                play=game.play_routines[0];liam=play.liam;context=game.lantern_quest
                self.assertEqual(liam.roster_art.design_id,'liam')
                self.assertIs(context.liam,liam)
                self.assertEqual(liam.draw_anchor,(64,66))
                for bank in (liam.idles,liam.walks,liam.runs):
                    for direction,s in bank.items():
                        frame=s if isinstance(s,pygame.Surface) else s[0][0]
                        self.assertIsInstance(frame,WorldCanvas,direction)
                        self.assertEqual(frame.native.get_size(),(192,192))
                for name,frames in liam.actions.items():
                    for frame,_ in frames:
                        self.assertIsInstance(frame,WorldCanvas,name)
                        self.assertEqual(frame.native.get_size(),(192,192))
                self.assertTrue(all(not isinstance(frame,WorldCanvas)
                    for action in play.dog_pose.actions.values() for frame,_ in action))
                for actions in (context.poses['liam'][1],context.rest.actions,context.finish_part.actions):
                    for name,frames in actions.items():
                        for frame,_ in frames:
                            self.assertIsInstance(frame,WorldCanvas,name)
                            self.assertEqual(frame.native.get_size(),(80,96))
                self.assertEqual(
                    Path(liam.roster_art.portrait_path).read_bytes(),
                    Path('assets/portraits/eldenmere/liam_neutral.png').read_bytes())
            finally:
                pygame.quit()
