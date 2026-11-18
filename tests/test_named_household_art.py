"""Native named home art and quest-owned temporary poses share the same bank."""
import os
import tempfile
import unittest
from pathlib import Path
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')

import pygame
from main import Game
from rendering import WorldCanvas
from tools.capture_lantern_quest import seed_previous_quests


class NamedHouseholdArt(unittest.TestCase):
    def test_tessa_home_and_festival_use_same_native_bank(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            game=Game(fullscreen=False,start_on_title=False,save_path=root/'save.json',
                      settings_path=root/'settings.json')
            try:
                home=game._scene_by_id('home_a')
                actor=next(n for n in home.npcs if n.data['id']=='tessa')
                art=actor.roster_art
                self.assertEqual(art.design_id,'tessa')
                self.assertIsInstance(actor.sprite(0),WorldCanvas)
                self.assertEqual(art.foot_anchor,(12,34))
                self.assertEqual(actor.position,pygame.Vector2(actor.data['position']))
                self.assertEqual(actor.blocker.size,tuple(actor.data['probe_size']))
                self.assertEqual(Path(art.portrait_path).read_bytes(),
                                 Path('assets/portraits/eldenmere/tessa_neutral.png').read_bytes())
                seed_previous_quests(game)
                school=game._scene_by_id('school')
                self.assertIn(actor,school.npcs)
                self.assertIs(game.lantern_quest.children['tessa'],actor)
                self.assertIs(actor.story_sprite,art.idles[actor.facing])
                self.assertEqual(actor.story_draw_anchor,(12,30))
                self.assertTrue(all(frame.native.get_size()==(48,72) for frame,_ in art.walks['front']))
            finally:
                pygame.quit()
