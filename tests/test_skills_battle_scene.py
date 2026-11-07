"""Skills navigation, encounter ownership and direct spellblade attack UI."""
import os
import random
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame

from audio_settings import AudioSettings
from battle_model import BattleModel
from battle_scene import ACTION_LABELS, BattleScene, MP_BLUE
from character_attributes import CharacterAttributes
from ui_style import MUTED, Painter, UIStyle


class EmptySprites:
    def __init__(self):
        self.image = pygame.Surface((48, 48), pygame.SRCALPHA)

    def frame(self, actor, state, elapsed_ms):
        return self.image, (24, 42)


class SkillsBattleSceneTests(unittest.TestCase):
    def setUp(self):
        pygame.display.init()
        pygame.font.init()
        self.game = SimpleNamespace(window=pygame.display.set_mode((480, 320)),
                                    ui_surface=pygame.Surface((480, 320)),
                                    audio=AudioSettings(), attributes=CharacterAttributes())
        self.game.audio.set_effects(0)
        self.game.ui = UIStyle(self.game)
        self.game.to_canvas = lambda point: point
        self.canvas = pygame.Surface((480, 320))
        self.make_scene()

    def tearDown(self):pygame.quit()

    def make_scene(self, *, armed=True, learned=('aether_edge',), party=False, tutorial=False):
        self.model = BattleModel(self.game.attributes, learned, rng=random.Random(4),
                                 weapon_equipped=armed,
                                 guest_id='mira' if party else None,
                                 enemy_id='ridgeback_tusker' if party else 'bat')
        self.scene = BattleScene(self.game, self.model, sprites=EmptySprites(),
                                 battlefield='millrace' if party else 'eldenmere',
                                 tutorial=tutorial)
        self.draw()

    def draw(self):self.scene.draw(self.canvas, self.game.ui_surface)

    def ready(self):
        for member in self.model.party:member.atb = 1
        self.scene.update(0)
        self.draw()

    def key(self, key, repeat=False):
        self.scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key, repeat=repeat))

    def click(self, point):
        for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            self.scene.handle_event(pygame.event.Event(kind, button=1, pos=point))

    def resources(self):
        return (self.model.phase, tuple((member.hp, member.mp, member.atb)
                                        for member in self.model.party),
                self.model.enemy.hp, self.model.enemy.mp, self.model.enemy.atb)

    def texts(self):
        records = []
        original = Painter.text

        def capture(painter, text, *args, **kwargs):
            bounds = original(painter, text, *args, **kwargs)
            records.append((str(text), bounds, kwargs.get('color')))
            return bounds

        with patch.object(Painter, 'text', capture):self.draw()
        return records

    def open_skills(self):
        self.click(self.scene.command_rects['skills'].center)
        self.assertEqual(self.scene.command_menu, 'skills')
        self.assertEqual(list(self.scene.command_rects), ['aether_edge', 'back'])

    def test_unarmed_skills_are_grey_and_explain_selection_without_spending_turn(self):
        self.make_scene(armed=False, learned=(), party=True)
        self.ready()
        before = self.resources()
        self.key(pygame.K_DOWN)
        self.assertEqual(self.scene._notice, 'Requires a weapon.')
        records = self.texts()
        self.assertEqual(next(color for text, _, color in records if text == 'Skills'), MUTED)
        self.assertIn('Requires a weapon.', [text for text, _, _ in records])
        self.key(pygame.K_RETURN)
        self.click(self.scene.command_rects['skills'].center)
        self.assertEqual(self.scene.command_menu, 'root')
        self.assertIsNone(self.model.current_action)
        self.scene.update(100)
        self.assertEqual(self.resources(), before)

    def test_keyboard_menu_and_visible_back_cost_nothing_then_cast_spends_once(self):
        self.ready()
        before = self.resources()
        self.key(pygame.K_DOWN)
        self.key(pygame.K_RETURN, repeat=True)
        self.assertEqual(self.scene.command_menu, 'root')
        self.key(pygame.K_RETURN)
        self.assertEqual(self.scene.command_menu, 'skills')
        self.scene.update(100)
        self.assertEqual(self.resources(), before)
        self.assertIn('4 MP', self.scene._detail_text())
        self.click(self.scene.command_rects['back'].center)
        self.assertEqual(self.scene.command_menu, 'root')
        self.assertEqual(self.resources(), before)
        self.key(pygame.K_RETURN)
        self.key(pygame.K_RETURN)
        self.assertEqual((self.model.current_action.action, self.model.current_action.target),
                         ('aether_edge', 'enemy'))
        self.assertEqual(self.model.player.mp, before[1][0][1]-4)
        self.assertEqual(self.model.player.atb, 0)
        self.assertEqual(self.scene.command_menu, 'root')

    def test_held_click_cannot_cross_menu_boundary(self):
        self.ready()
        before = self.resources()
        point = self.scene.command_rects['skills'].center
        down = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=point)
        self.scene.handle_event(down)
        for _ in range(3):self.scene.handle_event(down)
        self.assertEqual(self.scene.command_menu, 'skills')
        self.assertIsNone(self.model.current_action)
        self.assertEqual(self.resources(), before)
        self.scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=point))
        self.click(self.scene.command_rects['aether_edge'].center)
        self.assertEqual(self.model.current_action.action, 'aether_edge')

    def test_insufficient_mp_greys_skill_but_does_not_disable_menu_or_back(self):
        self.ready()
        self.model.player.mp = 3
        before = self.resources()
        self.open_skills()
        records = self.texts()
        self.assertEqual(next(color for text, _, color in records if text == 'Aether Edge'), MUTED)
        self.click(self.scene.command_rects['aether_edge'].center)
        self.assertEqual(self.scene._notice, 'Not enough MP.')
        self.assertEqual(self.resources(), before)
        self.click(self.scene.command_rects['back'].center)
        self.assertEqual(self.scene.command_menu, 'root')
        self.assertEqual(self.resources(), before)

    def test_escape_backs_out_then_pauses_and_focus_pause_preserves_menu(self):
        self.ready()
        self.open_skills()
        self.key(pygame.K_ESCAPE)
        self.assertEqual(self.scene.command_menu, 'root')
        self.assertFalse(self.scene.paused)
        self.key(pygame.K_ESCAPE)
        self.assertTrue(self.scene.paused)
        self.key(pygame.K_ESCAPE)
        self.open_skills()
        self.scene.handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        self.scene.handle_event(pygame.event.Event(pygame.WINDOWFOCUSGAINED))
        self.key(pygame.K_ESCAPE)
        self.assertFalse(self.scene.paused)
        self.assertEqual(self.scene.command_menu, 'skills')
        self.key(pygame.K_ESCAPE)
        self.assertEqual(self.scene.command_menu, 'root')

    def test_member_changes_new_ready_and_result_clear_submenu(self):
        self.make_scene(party=True)
        self.ready()
        self.open_skills()
        self.key(pygame.K_TAB)
        self.assertEqual(self.model.ready_actor, 'mira')
        self.assertEqual(self.scene.command_menu, 'root')
        self.assertNotIn('aether_edge', self.scene.command_rects)
        self.click(self.scene.command_rects['skills'].center)
        self.assertEqual(self.scene.command_menu, 'skills')
        self.assertIn('overclock', self.scene.command_rects)
        self.click(self.scene.party_rows['player']['row'].center)
        self.open_skills()
        self.click(self.scene.command_rects['aether_edge'].center)
        self.scene.update(self.model.current_action.duration)
        self.assertEqual(self.model.ready_actor, 'mira')
        self.assertEqual(self.scene.command_menu, 'root')
        self.click(self.scene.party_rows['player']['row'].center)
        self.assertEqual(self.model.ready_actor, 'mira')
        # A model-side ready selection must also discard the prior member's menu.
        self.model.player.atb = 1
        self.assertTrue(self.model.select_ready('player'))
        self.draw()
        self.open_skills()
        self.model.phase = 'defeat'
        self.draw()
        self.assertEqual(self.scene.command_menu, 'root')

    def test_member_switch_reflows_different_command_counts_before_next_input(self):
        self.make_scene(party=True, learned=('aether_edge', 'aether_dart'))
        self.ready()
        player_attack = self.scene.command_rects['attack'].copy()
        self.assertEqual(len(self.scene.command_rects), 5)
        before = self.resources()
        # No draw occurs between these events: each selection must publish its
        # own command bounds, including the smaller guest command panel.
        self.click(self.scene.party_rows['mira']['row'].center)
        self.assertEqual(self.model.ready_actor, 'mira')
        self.assertEqual(len(self.scene.command_rects), 4)
        mira_attack = self.scene.command_rects['attack'].copy()
        self.assertEqual(player_attack.top, mira_attack.top)
        self.key(pygame.K_TAB)
        self.assertEqual(self.scene.command_rects['attack'], player_attack)
        self.assertIn('aether_dart', self.scene.command_rects)
        self.key(pygame.K_TAB)
        self.assertEqual(self.scene.command_rects['attack'], mira_attack)
        self.assertNotIn('aether_dart', self.scene.command_rects)
        self.assertEqual(self.resources(), before)
        self.click(self.scene.command_rects['attack'].center)
        self.assertEqual((self.model.current_action.actor, self.model.current_action.action),
                         ('mira', 'bolt_shot'))
        self.assertEqual(self.model.player.atb, 1)
        self.assertEqual(self.model.combatant('mira').atb, 0)

    def test_guidance_keeps_escape_pause_and_acknowledgement_out_of_commands(self):
        self.make_scene(tutorial=True)
        self.ready()
        before = self.resources()
        self.assertTrue(self.scene.tutorial_active)
        self.click(self.scene.command_rects['skills'].center)
        self.assertEqual(self.scene.command_menu, 'root')
        self.key(pygame.K_ESCAPE)
        self.assertTrue(self.scene.paused)
        self.key(pygame.K_ESCAPE)
        self.key(pygame.K_RETURN)
        self.assertFalse(self.scene.tutorial_active)
        self.assertEqual(self.resources(), before)
        self.assertEqual(self.scene.command_menu, 'root')

    def test_two_party_rows_commands_and_skill_help_fit_native_large_text(self):
        for learned in (('aether_edge',), ('aether_edge', 'aether_dart')):
            self.make_scene(party=True, learned=learned)
            self.ready()
            for scale in (1.0, 1.5):
                self.game.audio.set_text_scale(scale)
                for menu in ('root', 'skills'):
                    with self.subTest(learned=learned, scale=scale, menu=menu):
                        self.scene._set_menu('root')
                        if menu == 'skills':self.open_skills()
                        records = self.texts()
                        self.assertTrue(self.canvas.get_rect().contains(self.scene.panel_rect))
                        self.assertEqual(len(self.scene.party_rows), 2)
                        for row in self.scene.party_rows.values():
                            for rect in row.values():self.assertTrue(self.scene.panel_rect.contains(rect))
                        for identifier, rect in self.scene.command_rects.items():
                            self.assertTrue(self.scene.panel_rect.contains(rect))
                            for line in self.scene._command_lines[identifier]:
                                label = next(bounds for text, bounds, _ in records
                                             if text == line and rect.contains(bounds))
                                self.assertTrue(rect.contains(label), (identifier, rect, label))
                            self.assertFalse(any(rect.colliderect(row['row'])
                                                 for row in self.scene.party_rows.values()))
                        for text, rect, _ in records:
                            self.assertTrue(self.canvas.get_rect().contains(rect), (text, rect))
                        if menu == 'skills':
                            help_rects = [rect for text, rect, _ in records
                                          if text.startswith('4 MP') or 'weapon strikes' in text]
                            self.assertTrue(help_rects)
                            for rect in help_rects:
                                self.assertTrue(self.canvas.get_rect().contains(rect))
                                self.assertLessEqual(rect.bottom, self.scene.panel_rect.top)
                            self.key(pygame.K_ESCAPE)

    def test_edge_uses_an_attack_arc_and_one_enemy_damage_popup_without_charges(self):
        self.ready();self.open_skills()
        self.click(self.scene.command_rects['aether_edge'].center)
        self.scene.update(.9)
        self.assertEqual(self.scene._pose('player')[0],'aether_edge')
        enemy_hp=self.model.enemy.hp
        with patch.object(self.scene.gear_fx, 'draw', wraps=self.scene.gear_fx.draw) as effects:self.draw()
        self.assertTrue(effects.called)
        self.scene.update(self.model.current_action.impact_at-.9)
        self.assertLess(self.model.enemy.hp,enemy_hp)
        self.assertEqual(self.model.player.aether_edge_hits,0)
        self.assertEqual(self.scene._popups[-1]['target'],'enemy')
        self.assertEqual(self.scene._popups[-1]['text'],str(self.model.current_action.damage))
        for scale in (1.,1.5):
            self.game.audio.set_text_scale(scale)
            records=self.texts()
            self.assertFalse(any('strikes' in text or 'Enchant' in text for text,_,_ in records))


if __name__ == '__main__':unittest.main()
