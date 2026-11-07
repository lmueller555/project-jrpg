"""Compact status rows preserve the battlefield, controls and hidden bot clocks."""
import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')

import pygame

from audio_settings import AudioSettings
from battle_model import BattleModel
from battle_scene import BattleScene
from character_attributes import CharacterAttributes
from inventory import Inventory
from ui_style import Painter, UIStyle
from test_three_member_battle import profiles


class CompactBattleUITests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.game=SimpleNamespace(window=pygame.display.set_mode((960,640)),
            ui_surface=pygame.Surface((960,640)),audio=AudioSettings(),
            attributes=CharacterAttributes(),inventory=Inventory())
        self.game.audio.set_effects(0)
        self.game.ui=UIStyle(self.game)
        self.game.to_canvas=lambda point:(point[0]/2,point[1]/2)
        self.canvas=pygame.Surface((480,320))

    def tearDown(self):pygame.quit()

    def scene(self,ids=('player','mira','lucan'),*,maximum=False):
        model=BattleModel(self.game.attributes,['aether_dart','aether_edge'],
            weapon_equipped=True,party_members=profiles(*ids,maximum=maximum))
        scene=BattleScene(self.game,model)
        scene.draw(self.canvas,self.game.ui_surface)
        return scene

    def test_normal_window_reclaims_battlefield_without_shrinking_the_gear(self):
        scene=self.scene()
        self.assertLessEqual(scene.panel_rect.height,110)
        self.assertEqual(scene.panel_rect.bottom,312)
        self.assertEqual(scene.gear.rect.size,(48,48))
        self.assertEqual(scene.panel_rect.height,3*scene._status_height)
        for row in scene.party_rows.values():
            self.assertGreaterEqual(row['interactable'].height,2*scene._status_height-8)
            self.assertLessEqual(row['row'].bottom,row['interactable'].top)

    def test_inline_rows_fit_all_party_sizes_and_accessible_text(self):
        for size in ((480,320),(960,640),(1440,960)):
            self.game.window=pygame.display.set_mode(size)
            self.game.ui_surface=pygame.Surface(size)
            for scale in (1.0,1.25,1.5):
                self.game.audio.set_text_scale(scale)
                for ids in (('player',),('player','mira'),('player','edran','rhea')):
                    with self.subTest(size=size,text=scale,ids=ids):
                        scene=self.scene(ids,maximum=True)
                        self.assertTrue(self.canvas.get_rect().contains(scene.panel_rect))
                        self.assertEqual(scene.gear.rect.size,(48,48))
                        self.assertEqual(scene.panel_rect.height,3*scene._status_height)
                        for row in scene.party_rows.values():
                            self.assertGreaterEqual(row['atb'].left,row['name'].right+2)
                            self.assertLessEqual(abs(row['atb'].centery-row['name'].centery),1)
                            self.assertGreaterEqual(row['atb'].width,24)
                            for key in ('hp','mp'):
                                self.assertGreater(row[key].width,0)
                                self.assertLess(row[key].right,row[key+'_text'].left)
                                self.assertLessEqual(abs(row[key].centery-row[key+'_text'].centery),1)
                                self.assertTrue(row['row'].contains(row[key]))
                                self.assertTrue(row['row'].contains(row[key+'_text']))
                            self.assertTrue(row['row'].contains(row['name']))
                            self.assertTrue(row['row'].contains(row['atb']))
                        self.assertTrue(scene.party_rows['player']['interactable'].contains(scene.gear.rect))

    def test_every_command_stays_reachable_after_compaction_and_resize(self):
        scene=self.scene(('player',))
        scene.model.player.atb=1
        scene.update(0)
        for size,scale in (((960,640),1.0),((480,320),1.5)):
            self.game.window=pygame.display.set_mode(size)
            self.game.ui_surface=pygame.Surface(size)
            self.game.audio.set_text_scale(scale)
            seen=set()
            for _ in range(len(scene._command_actions())+1):
                scene.draw(self.canvas,self.game.ui_surface)
                seen.update(scene.command_rects)
                selected=scene._command_actions()[scene.selected]
                self.assertIn(selected,scene.command_rects)
                for rect in scene.command_rects.values():
                    self.assertTrue(scene.commands_panel.contains(rect))
                scene.handle_event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_DOWN))
            self.assertEqual(seen,set(scene._command_actions()))

    def test_bot_hud_is_absent_while_autonomous_and_haste_state_are_preserved(self):
        scene=self.scene(('player','mira'))
        bot=scene.model.bot_for('mira')
        bot.atb=.35;bot.haste_turns=8
        rendered=[]
        original=Painter.text
        def record(painter,text,*args,**kwargs):
            rendered.append(str(text))
            return original(painter,text,*args,**kwargs)
        before=(bot.atb,bot.haste_turns)
        with patch.object(Painter,'text',record):
            scene.draw(self.canvas,self.game.ui_surface)
        self.assertEqual(scene.bot_status,{})
        self.assertFalse(any(text=='Rivet ATB' or text.startswith('Haste ·') for text in rendered))
        self.assertEqual((bot.atb,bot.haste_turns),before)
        scene.update(.1)
        self.assertGreater(bot.atb,before[0])
        self.assertEqual(bot.haste_turns,8)

    def test_gear_keyboard_input_still_targets_the_resized_interaction_area(self):
        scene=self.scene()
        initial=scene.model.active_gem
        for key in (pygame.K_g,pygame.K_RIGHT,pygame.K_RETURN):
            scene.handle_event(pygame.event.Event(pygame.KEYDOWN,key=key))
        scene.update(.1)
        self.assertNotEqual(scene.model.active_gem,initial)
        self.assertFalse(scene.model.gear_settling)
        self.assertTrue(scene.party_rows['player']['interactable'].contains(scene.gear.rect))
