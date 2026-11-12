"""Live controls obey charging windows, including exact frame boundaries."""
import os
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import pygame

from audio_settings import AudioSettings
from battle_model import BattleModel, load_actions, load_enemies
from battle_scene import BattleScene
from character_attributes import CharacterAttributes
from ui_style import UIStyle


class EmptySprites:
    def __init__(self):self.image = pygame.Surface((48, 48), pygame.SRCALPHA)
    def frame(self, actor, state, elapsed_ms):return self.image, (24, 42)


class InteractableChargingTests(unittest.TestCase):
    def setUp(self):
        pygame.display.init();pygame.font.init()
        pygame.display.set_mode((960, 640))

    def tearDown(self):pygame.quit()

    def scene(self):
        game = SimpleNamespace(window=pygame.display.get_surface(),
            ui_surface=pygame.Surface((960, 640)), audio=AudioSettings(),
            attributes=CharacterAttributes())
        game.audio.set_effects(0)
        game.ui = UIStyle(game)
        game.to_canvas = lambda point: (point[0]/2, point[1]/2)
        game.character_abilities = SimpleNamespace(set_active_gem=Mock(return_value=True))
        game.save_progress = Mock()
        enemies = {'version':1, 'enemies':load_enemies(load_actions())}
        enemies['enemies']['ridgeback_tusker']['attributes'].update(hp=1000000, str=0, mag=0)
        model = BattleModel(game.attributes, ('aether_edge',),
            weapon_equipped=True, guest_id='mira', enemy_id='ridgeback_tusker',
            enemy_data=enemies)
        scene = BattleScene(game, model, sprites=EmptySprites(), battlefield='millrace')
        scene.draw(pygame.Surface((480, 320)), game.ui_surface)
        return scene, game

    @staticmethod
    def key(scene, key):
        scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key, repeat=False))

    def seat_gem(self, scene):
        self.key(scene, pygame.K_g)
        self.key(scene, pygame.K_RIGHT)
        desired = scene.gear.preview_gem
        self.assertNotEqual(desired, scene.model.active_gem)
        self.key(scene, pygame.K_RETURN)
        self.assertTrue(scene.gear.settling)
        return desired

    def test_ready_and_acting_lock_both_controls_until_the_turn_finishes(self):
        for actor in ('player', 'mira'):
            with self.subTest(actor=actor):
                scene, _ = self.scene();model = scene.model
                self.assertTrue(scene.gear_enabled);self.assertTrue(scene.rig_enabled)
                model.combatant(actor).atb = 1
                scene.update(0)
                self.assertEqual(model.phase, 'ready')
                self.assertFalse(scene.gear_enabled);self.assertFalse(scene.rig_enabled)
                self.assertFalse(model.set_active_gem('fire'))
                self.assertFalse(model.set_rig_allocation({'weapons':3,'protection':2,'support':1}))
                self.key(scene, pygame.K_g);self.key(scene, pygame.K_m)
                self.assertFalse(scene.gear.focused);self.assertFalse(scene.rig.focused)
                self.assertEqual(scene.atb_multiplier, 1)
                self.assertTrue(model.choose_action('guard'))
                self.assertEqual(model.combatant(actor).atb, 0)
                self.assertFalse(scene.gear_enabled);self.assertFalse(scene.rig_enabled)
                scene.update(model.current_action.duration)
                self.assertEqual(model.phase, 'charging')
                self.assertTrue(scene.gear_enabled);self.assertTrue(scene.rig_enabled)

    def test_pending_gem_seat_obeys_same_cutoff_at_coarse_and_fine_frame_rates(self):
        for first_full in ('player', 'mira', 'enemy'):
            for boundary, commits in ((.08, False), (.1, False), (.12, True)):
                outcomes=[]
                for steps in ((.2,), (.01,)*20):
                    with self.subTest(actor=first_full,boundary=boundary,steps=len(steps)):
                        scene, game = self.scene();model = scene.model
                        participant = model.combatant(first_full)
                        participant.atb = 1-model.atb_rate(participant)*boundary
                        desired=self.seat_gem(scene)
                        for seconds in steps:scene.update(seconds)
                        expected=desired if commits else 'water'
                        self.assertEqual(model.active_gem, expected)
                        self.assertEqual(scene.gear.active_gem, expected)
                        self.assertFalse(scene.gear.busy)
                        self.assertFalse(model.gear_settling)
                        self.assertEqual(game.save_progress.call_count, int(commits))
                        self.assertEqual(game.character_abilities.set_active_gem.call_count,int(commits))
                        self.assertFalse(scene.gear_enabled);self.assertFalse(scene.rig_enabled)
                        outcomes.append((model.phase,model.active_gem))
                self.assertEqual(outcomes[0],outcomes[1])

    def test_unconfirmed_routing_and_drag_do_not_carry_into_the_next_turn(self):
        scene, _ = self.scene();model = scene.model
        allocation=model.rig_allocation
        self.key(scene, pygame.K_m)
        self.key(scene, pygame.K_LEFT)
        self.assertTrue(scene.rig.dirty)
        model.player.atb=1
        scene.update(0)
        self.assertFalse(scene.rig.dirty)
        self.assertFalse(scene.rig.focused)
        self.assertEqual(model.rig_allocation,allocation)
        self.assertTrue(model.choose_action('guard'))
        scene.update(model.current_action.duration)
        self.assertFalse(scene.rig.dirty)
        self.assertEqual(model.rig_allocation,allocation)
        self.assertTrue(scene.rig_enabled)
        # A held drag is abandoned when an enemy begins acting too.
        rect=scene.gear.rect
        top=(rect.centerx*2,(rect.top+rect.height*9/48)*2)
        scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=top))
        self.assertTrue(scene.gear.dragging)
        model.enemy.atb=1
        scene.update(0)
        self.assertEqual(model.phase,'acting')
        self.assertFalse(scene.gear.dragging)
        self.assertFalse(scene.gear.focused)
        self.assertEqual(model.active_gem,'water')

    def test_confirmed_routing_determines_skills_and_cannot_be_changed_in_command_menu(self):
        scene, _ = self.scene();model=scene.model
        allocation={'weapons':3,'protection':1,'support':2}
        self.assertTrue(model.set_rig_allocation(allocation))
        model.combatant('mira').atb=1
        scene.update(0)
        scene._set_menu('skills')
        self.assertFalse(model.action_reason('charged_bolt'))
        self.assertTrue(model.action_reason('impact_bolt'))
        self.assertFalse(model.set_rig_allocation({'weapons':2,'protection':2,'support':2}))
        self.assertEqual(model.rig_allocation,allocation)
        self.assertTrue(model.choose_action('charged_bolt'))
        self.assertEqual(model.current_action.rig_allocation,allocation)

    def test_vespermaw_free_transformation_is_not_a_configuration_window(self):
        scene, game = self.scene()
        model=BattleModel.from_bestiary(game.attributes,'vespermaw',7,
            weapon_equipped=True,guest_id='mira')
        scene=BattleScene(game,model,battlefield='cave_echo_chamber')
        scene.draw(pygame.Surface((480,320)),game.ui_surface)
        model.vespermaw_turns=2
        model.enemy.atb=1
        scene.update(0)
        self.assertEqual(model.current_action.action,'vespermaw_attune')
        self.assertFalse(scene.gear_enabled);self.assertFalse(scene.rig_enabled)
        self.assertFalse(model.set_active_gem('fire'))
        self.assertFalse(model.set_rig_allocation({'weapons':3,'protection':2,'support':1}))
        point=tuple(value*2 for value in scene.gear.rect.center)
        scene.handle_event(pygame.event.Event(pygame.MOUSEMOTION,pos=point,rel=(0,0),buttons=(0,0,0)))
        self.assertFalse(scene.gear_hover_available)
        self.assertEqual(scene.atb_multiplier,1)
        scene.update(.3)
        self.assertAlmostEqual(model.current_action.elapsed,.3)


if __name__=='__main__':unittest.main()
