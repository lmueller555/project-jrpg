"""Real sprite clicks execute the highlighted offensive command exactly once."""
import os
import random
from types import SimpleNamespace
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

import pygame

from audio_settings import AudioSettings
from battle_model import BattleModel
from battle_scene import BattleScene
from inventory import Inventory
from ui_style import UIStyle
from test_random_enemy_groups import attributes, clear_gauges, group


class BattleClickTargetingTests(unittest.TestCase):
    def setUp(self):
        pygame.display.init()
        pygame.font.init()
        self.scale = 1
        self.origin = (0, 0)
        self.game = SimpleNamespace(
            window=pygame.display.set_mode((480, 320)),
            ui_surface=pygame.Surface((480, 320)),
            audio=AudioSettings(), inventory=Inventory(), attributes=attributes())
        self.game.audio.set_effects(0)
        self.game.ui = UIStyle(self.game)
        self.game.to_canvas = self.to_canvas
        self.canvas = pygame.Surface((480, 320))

    def tearDown(self):
        pygame.quit()

    def to_canvas(self, point):
        point = ((point[0] - self.origin[0]) / self.scale,
                 (point[1] - self.origin[1]) / self.scale)
        return point if 0 <= point[0] < 480 and 0 <= point[1] < 320 else None

    def to_window(self, point):
        return (round(point[0] * self.scale + self.origin[0]),
                round(point[1] * self.scale + self.origin[1]))

    def scene(self, *, multiple=False, enemy='bat', guest=False, draw=True,
              ready=('player',)):
        if multiple:
            model = group(learned_abilities=['aether_edge', 'aether_dart'],
                          weapon_equipped=True)
        else:
            model = BattleModel(self.game.attributes, ['aether_edge', 'aether_dart'],
                                weapon_equipped=True, enemy_id=enemy,
                                guest_id='mira' if guest else None,
                                rng=random.Random(4), initial_atb=False)
        scene = BattleScene(self.game, model,
                            battlefield='cave_hollow' if multiple else
                            'millrace' if enemy == 'ridgeback_tusker' else 'eldenmere')
        clear_gauges(model)
        for identifier in ready:
            model.combatant(identifier).atb = 1
        scene.update(0)
        if draw:self.draw(scene)
        return scene, model

    def draw(self, scene):
        scene.draw(self.canvas, self.game.ui_surface)

    def event(self, scene, kind, *, point=None, **kwargs):
        if point is not None:kwargs['pos'] = self.to_window(point)
        scene.handle_event(pygame.event.Event(kind, **kwargs))

    def click(self, scene, point):
        for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            self.event(scene, kind, point=point, button=1)

    def key(self, scene, key):
        self.event(scene, pygame.KEYDOWN, key=key, repeat=False)
        self.event(scene, pygame.KEYUP, key=key)

    def resources(self, model):
        return (model.phase, model.ready_actor,
                tuple((actor.identifier, getattr(actor, 'hp', None),
                       getattr(actor, 'mp', None), actor.atb,
                       getattr(actor, 'haste_turns', None))
                      for actor in (*model.party, *model.enemies, *model.bots)))

    def select_skill(self, scene, identifier='aether_edge'):
        self.click(scene, scene.command_rects['skills'].center)
        self.assertEqual(scene.command_menu, 'skills')
        self.event(scene, pygame.MOUSEMOTION,
                   point=scene.command_rects[identifier].center, rel=(0, 0), buttons=(0, 0, 0))
        self.assertEqual(scene._command_actions()[scene.selected], identifier)
        self.assertIsNone(scene._target_command)

    def test_single_bat_and_tusker_body_click_execute_attack_without_menu_confirmation(self):
        for enemy in ('bat', 'ridgeback_tusker'):
            with self.subTest(enemy=enemy):
                scene, model = self.scene(enemy=enemy)
                self.assertIsNone(scene._target_command)
                self.assertEqual(model.phase, 'ready')
                self.click(scene, scene.enemy_rects['enemy'].center)
                self.assertEqual((model.current_action.actor, model.current_action.action,
                                  model.current_action.target), ('player', 'attack', 'enemy'))
                self.assertEqual(model.player.atb, 0)

    def test_group_sprite_and_status_card_click_execute_selected_attack_on_actual_enemy(self):
        for hit in ('body', 'status'):
            with self.subTest(hit=hit):
                scene, model = self.scene(multiple=True)
                point = (scene.enemy_rects['enemy_4'].center if hit == 'body' else
                         scene.enemy_rows['enemy_4']['row'].center)
                self.click(scene, point)
                self.assertEqual((model.current_action.action, model.current_action.target),
                                 ('attack', 'enemy_4'))
                self.assertEqual(model.selected_target, 'enemy_4')

    def test_single_enemy_status_card_executes_the_highlighted_skill(self):
        for enemy in ('bat', 'ridgeback_tusker'):
            with self.subTest(enemy=enemy):
                scene, model = self.scene(enemy=enemy)
                self.select_skill(scene)
                mp = model.player.mp
                self.click(scene, scene.enemy_rows['enemy']['row'].center)
                self.assertEqual((model.current_action.action, model.current_action.target),
                                 ('aether_edge', 'enemy'))
                self.assertEqual(model.player.mp, mp - model.actions['aether_edge']['mp_cost'])

    def test_hovering_a_foe_selects_it_without_spending_the_highlighted_skill(self):
        scene, model = self.scene(multiple=True)
        self.select_skill(scene)
        before = self.resources(model)
        self.event(scene, pygame.MOUSEMOTION, point=scene.enemy_rects['enemy_3'].center,
                   rel=(0, 0), buttons=(0, 0, 0))
        self.assertEqual(model.selected_target, 'enemy_3')
        self.assertEqual(self.resources(model), before)
        self.assertIsNone(model.current_action)
        self.assertIsNone(scene._target_command)

    def test_highlighted_skill_casts_directly_and_pays_mp_only_on_the_clicked_target(self):
        for multiple in (False, True):
            with self.subTest(multiple=multiple):
                scene, model = self.scene(multiple=multiple)
                self.select_skill(scene)
                mp = model.player.mp
                target = 'enemy_3' if multiple else 'enemy'
                self.click(scene, scene.enemy_rects[target].center)
                self.assertEqual((model.current_action.action, model.current_action.target),
                                 ('aether_edge', target))
                self.assertEqual(model.player.mp, mp - model.actions['aether_edge']['mp_cost'])
                self.assertEqual(model.player.atb, 0)

    def test_armed_group_target_mode_still_casts_the_pending_skill_on_click(self):
        scene, model = self.scene(multiple=True)
        self.select_skill(scene)
        self.click(scene, scene.command_rects['aether_edge'].center)
        self.assertEqual(scene._target_command, 'aether_edge')
        self.assertEqual(model.phase, 'ready')
        self.click(scene, scene.enemy_rects['enemy_4'].center)
        self.assertEqual((model.current_action.action, model.current_action.target),
                         ('aether_edge', 'enemy_4'))
        self.assertIsNone(scene._target_command)

    def test_disabled_skill_click_explains_the_reason_without_falling_back_to_attack(self):
        for disabled in ('mp', 'weapon'):
            with self.subTest(disabled=disabled):
                scene, model = self.scene(multiple=True)
                self.select_skill(scene)
                if disabled == 'mp':model.player.mp = 3
                else:model.weapon_equipped = False
                before = self.resources(model)
                self.click(scene, scene.enemy_rects['enemy_2'].center)
                self.assertIsNone(model.current_action)
                self.assertEqual(self.resources(model), before)
                self.assertIn('MP' if disabled == 'mp' else 'weapon', scene._notice)

    def test_menu_containers_guard_and_back_do_not_execute_on_enemy_click(self):
        for selected in ('skills', 'guard', 'back'):
            with self.subTest(selected=selected):
                scene, model = self.scene(multiple=True)
                if selected == 'back':self.select_skill(scene)
                scene.selected = scene._command_actions().index(selected)
                before = self.resources(model)
                self.click(scene, scene.enemy_rects['enemy_3'].center)
                self.assertEqual(self.resources(model), before)
                self.assertIsNone(model.current_action)

    def test_selected_support_skill_does_not_target_or_cast_on_an_enemy(self):
        scene, model = self.scene(enemy='ridgeback_tusker', guest=True, ready=('mira',))
        self.assertTrue(model.set_rig_allocation({'weapons': 0, 'protection': 3, 'support': 3}))
        self.select_skill(scene, 'bulwark')
        self.assertEqual(model.action_reason('bulwark'), '')
        before = self.resources(model)
        self.click(scene, scene.enemy_rects['enemy'].center)
        self.assertEqual(self.resources(model), before)
        self.assertIsNone(model.current_action)

    def test_held_button_cannot_repeat_an_attack_or_queue_the_next_ready_turn(self):
        scene, model = self.scene(enemy='ridgeback_tusker')
        point = scene.enemy_rects['enemy'].center
        self.event(scene, pygame.MOUSEBUTTONDOWN, point=point, button=1)
        first = model.current_action
        self.assertIsNotNone(first)
        for _ in range(3):self.event(scene, pygame.MOUSEBUTTONDOWN, point=point, button=1)
        self.assertIs(model.current_action, first)
        scene.update(first.duration)
        clear_gauges(model);model.player.atb = 1;scene.update(0);self.draw(scene)
        self.assertTrue(model.waiting_for_player)
        self.assertIsNone(model.current_action)
        self.event(scene, pygame.MOUSEBUTTONDOWN, point=point, button=1)
        self.assertIsNone(model.current_action)
        self.event(scene, pygame.MOUSEBUTTONUP, point=point, button=1)
        self.click(scene, scene.enemy_rects['enemy'].center)
        self.assertIsNotNone(model.current_action)
        self.assertIsNot(model.current_action, first)

    def test_click_before_atb_is_ready_does_not_queue_an_attack(self):
        scene, model = self.scene(ready=())
        self.click(scene, scene.enemy_rects['enemy'].center)
        self.assertIsNone(model.current_action)
        model.player.atb = 1;scene.update(0)
        self.assertTrue(model.waiting_for_player)
        self.assertIsNone(model.current_action)

    def test_changing_ready_actor_discards_the_previous_actors_pending_skill(self):
        scene, model = self.scene(multiple=True, ready=('player', 'mira'))
        self.select_skill(scene)
        self.click(scene, scene.command_rects['aether_edge'].center)
        self.assertEqual(scene._target_command, 'aether_edge')
        mp = model.player.mp
        self.click(scene, scene.party_rows['mira']['row'].center)
        self.assertEqual(model.ready_actor, 'mira')
        self.assertIsNone(scene._target_command)
        self.click(scene, scene.enemy_rects['enemy_4'].center)
        self.assertEqual((model.current_action.actor, model.current_action.action,
                          model.current_action.target), ('mira', 'bolt_shot', 'enemy_4'))
        self.assertEqual(model.player.mp, mp)

    def test_paused_unfocused_tutorial_and_dead_targets_cannot_spend_a_turn(self):
        for blocked in ('paused', 'unfocused', 'tutorial', 'dead'):
            with self.subTest(blocked=blocked):
                scene, model = self.scene(multiple=True)
                point = scene.enemy_rects['enemy_3'].center
                if blocked == 'paused':scene.paused = True
                elif blocked == 'unfocused':scene.focused = False
                elif blocked == 'tutorial':
                    scene._tutorial_queue.append({'speaker': 'mira', 'text': 'Wait.', 'help': ''})
                else:model.combatant('enemy_3').hp = 0
                before = self.resources(model)
                self.click(scene, point)
                self.assertEqual(self.resources(model), before)
                self.assertIsNone(model.current_action)

    def test_scaled_letterboxed_click_uses_the_visible_sprite_and_ignores_margins(self):
        self.scale, self.origin = 2, (70, 50)
        self.game.window = pygame.display.set_mode((1100, 740))
        self.game.ui_surface = pygame.Surface((960, 640))
        scene, model = self.scene(multiple=True)
        before = self.resources(model)
        for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            scene.handle_event(pygame.event.Event(kind, button=1, pos=(12, 12)))
        self.assertEqual(self.resources(model), before)
        self.click(scene, scene.enemy_rects['enemy_2'].center)
        self.assertEqual((model.current_action.action, model.current_action.target),
                         ('attack', 'enemy_2'))

    def test_first_input_can_hit_an_enemy_without_requiring_a_prior_draw(self):
        scene, model = self.scene(draw=False)
        # Establish the current HUD layout, but deliberately never draw a
        # sprite or populate cached enemy rectangles before the first input.
        scene._layout(self.game.ui.painter(self.game.ui_surface))
        point = scene._hit_point('enemy', scene._positions())
        self.click(scene, point)
        self.assertEqual((model.current_action.action, model.current_action.target),
                         ('attack', 'enemy'))

    def test_sprite_padding_cannot_intercept_a_click_on_the_party_hud(self):
        self.game.audio.set_text_scale(1.5)
        scene, model = self.scene(enemy='ridgeback_tusker')
        point = scene.enemy_rects['enemy'].centerx, scene.panel_rect.top + 2
        self.assertTrue(scene.panel_rect.collidepoint(point))
        before = self.resources(model)
        self.click(scene, point)
        self.assertEqual(self.resources(model), before)
        self.assertIsNone(model.current_action)

    def test_finger_and_ground_ring_fit_actual_single_and_group_enemy_geometry(self):
        for text_scale in (1.0, 1.5):
            self.game.audio.set_text_scale(text_scale)
            for multiple, enemy in ((False, 'bat'), (False, 'ridgeback_tusker'), (True, 'bat')):
                scene, model = self.scene(multiple=multiple, enemy=enemy)
                for target in model.enemies:
                    with self.subTest(text=text_scale, enemy=target.identifier,
                                      group=multiple, sprite=enemy):
                        model.select_target(target.identifier)
                        self.draw(scene)
                        body = scene.enemy_rects[target.identifier]
                        finger = scene.target_marker_rects['finger']
                        ring = scene.target_marker_rects['ring']
                        bounds = scene._target_marker_bounds(target.identifier)
                        self.assertTrue(bounds.contains(finger), (bounds, finger))
                        self.assertTrue(bounds.contains(ring), (bounds, ring))
                        self.assertLessEqual(finger.bottom, body.top)
                        self.assertLessEqual(abs(finger.centerx - body.centerx), 2)
                        self.assertGreaterEqual(ring.centery, body.centery)

    def test_target_marker_is_hidden_when_commands_cannot_target_an_enemy(self):
        for blocked in ('charging', 'acting', 'paused', 'unfocused', 'tutorial', 'support'):
            with self.subTest(blocked=blocked):
                scene, model = self.scene(enemy='ridgeback_tusker', guest=True,
                                          ready=() if blocked == 'charging' else
                                          ('mira',) if blocked == 'support' else ('player',))
                if blocked == 'acting':
                    self.assertTrue(model.choose_action('attack', target_id='enemy'))
                elif blocked == 'paused':scene.paused = True
                elif blocked == 'unfocused':scene.focused = False
                elif blocked == 'tutorial':
                    scene._tutorial_queue.append({'speaker': 'mira', 'text': 'Wait.', 'help': ''})
                elif blocked == 'support':
                    self.assertTrue(model.set_rig_allocation({'weapons': 0, 'protection': 3, 'support': 3}))
                    self.select_skill(scene, 'bulwark')
                self.draw(scene)
                self.assertEqual(scene.target_marker_rects, {})

    def test_ground_ring_remains_static_while_the_selected_bat_flaps(self):
        scene, model = self.scene()
        rings, poses = set(), set()
        for elapsed in (.0, .13, .21, .25):
            scene.update(elapsed)
            self.draw(scene)
            rings.add(tuple(scene.target_marker_rects['ring']))
            body = scene.enemy_rects['enemy']
            poses.add(pygame.image.tobytes(self.canvas.subsurface(body), 'RGB'))
        self.assertEqual(len(rings), 1, 'A ground circle must not pulse with wingbeats')
        self.assertGreater(len(poses), 1, 'The sprite animation should continue independently')
        self.assertTrue(model.waiting_for_player)


if __name__ == '__main__':
    unittest.main()
