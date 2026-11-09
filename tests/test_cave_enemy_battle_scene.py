"""Authored cave sprites play through real battle clocks and compact layouts."""
from copy import deepcopy
import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import pygame

from audio_settings import AudioSettings
from battle_model import BattleModel
from battle_scene import BattleScene
from battle_action_fx import BattleActionEffects
from character_attributes import CharacterAttributes
from inventory import Inventory
from leveling import character_stats
from ui_style import UIStyle


class FixedVariance:
    def randint(self, low, high):
        assert (low, high) == (95, 105)
        return 100


def player(level):
    attributes = CharacterAttributes()
    saved = attributes.to_dict()
    saved['attributes'] = character_stats('caelan', level)
    saved['attributes']['hp'] = 9999
    saved['current_hp'] = 9999
    saved['current_mp'] = saved['attributes']['mp']
    assert attributes.restore(saved)
    return attributes


def party(level):
    result = []
    for identifier, name in (('player', 'Caelan'), ('mira', 'Mira'), ('lucan', 'Lucan')):
        stats = character_stats('caelan' if identifier == 'player' else identifier, level)
        stats['hp'] = 9999
        result.append({'identifier': identifier, 'name': name, 'attributes': stats,
                       'hp': 9999, 'mp': stats['mp'],
                       'attack': 'bolt_shot' if identifier == 'mira' else 'attack'})
    return result


class CaveEnemyBattleSceneTests(unittest.TestCase):
    def setUp(self):
        pygame.display.init()
        pygame.font.init()
        self.game = SimpleNamespace(window=pygame.display.set_mode((960, 640)),
                                    ui_surface=pygame.Surface((960, 640)),
                                    audio=AudioSettings(), inventory=Inventory())
        self.game.audio.set_effects(0)
        self.game.ui = UIStyle(self.game)
        self.game.to_canvas = lambda point: (point[0]/2, point[1]/2)
        self.canvas = pygame.Surface((480, 320))

    def tearDown(self):
        pygame.quit()

    def encounter(self, actor, level, three_party=True):
        self.game.attributes = player(level)
        options = {'party_members': party(level), 'bot_loadouts': {}} if three_party else {}
        model = BattleModel.from_bestiary(self.game.attributes, actor, level,
                                          rng=FixedVariance(), **options)
        scene = BattleScene(self.game, model)
        self.draw(scene)
        return model, scene

    def draw(self, scene):
        scene.draw(self.canvas, self.game.ui_surface)

    def start_enemy_turn(self, scene):
        scene.model.enemy.atb = 1
        scene.update(0)
        self.assertEqual(scene.model.current_action.actor, 'enemy')
        return scene.model.current_action

    def enemy_bounds(self, scene, state=None, time=None):
        state, time = scene._pose('enemy') if state is None else (state, time)
        image, anchor = scene.sprites.frame(scene.model.enemy_sprite_id, state, time)
        scale = scene._actor_scale('enemy')
        scaled = pygame.transform.scale(image, (round(image.get_width()*scale),
                                                 round(image.get_height()*scale)))
        point = scene._positions()['enemy']
        return scaled.get_bounding_rect().move(round(point.x-anchor[0]*scale),
                                               round(point.y-anchor[1]*scale))

    def assert_in_field(self, scene, bounds):
        self.assertGreater(bounds.width*bounds.height, 0)
        field = pygame.Rect(0, 64, 480, scene.panel_rect.top-64)
        self.assertTrue(field.contains(bounds), (bounds, field))

    def test_real_species_art_fits_native_and_large_text_three_member_layouts(self):
        for actor, level in (('lithrusk', 2), ('veylume', 3)):
            model, scene = self.encounter(actor, level)
            self.assertEqual(model.enemy_sprite_id, actor)
            for dimensions in ((480, 320), (960, 640)):
                self.game.window = pygame.display.set_mode(dimensions)
                self.game.ui_surface = pygame.Surface(dimensions)
                for text_scale in (1, 1.5):
                    self.game.audio.set_text_scale(text_scale)
                    self.draw(scene)
                    art = scene.sprites.actors[actor]
                    for state, (frames, _) in art['animations'].items():
                        time = 0
                        for index, (_, duration) in enumerate(frames):
                            with self.subTest(actor=actor, size=dimensions, text=text_scale,
                                              state=state, frame=index):
                                self.assert_in_field(scene, self.enemy_bounds(scene, state, time))
                            time += duration

    def test_action_specific_poses_use_the_impact_clock_and_return_to_idle(self):
        designs = (('lithrusk', 2, ('claw_clamp', 'shell_bash')),
                   ('lithrusk', 3, ('claw_clamp', 'shell_bash')),
                   ('veylume', 3, ('static_spark', 'gather_charge', 'veinflash')),
                   ('veylume', 4, ('static_spark', 'gather_charge', 'veinflash')))
        for actor, level, states in designs:
            model, scene = self.encounter(actor, level)
            for expected in states:
                with self.subTest(actor=actor, level=level, state=expected):
                    action = self.start_enemy_turn(scene)
                    if actor == 'lithrusk':
                        self.assertEqual(scene._pose('enemy')[0], 'walk')
                    scene.update(action.impact_at)
                    state, time = scene._pose('enemy')
                    self.assertEqual(state, expected)
                    self.assertAlmostEqual(time, action.impact_at*1000)
                    self.assertIn(state, scene.sprites.actors[actor]['animations'])
                    self.draw(scene)
                    self.assert_in_field(scene, self.enemy_bounds(scene))
                    scene.update(action.duration-action.elapsed)
                    self.draw(scene)
                    self.assertEqual(scene._pose('enemy')[0],
                                     'charged_hold' if expected == 'gather_charge' else 'idle')

    def test_veylume_charge_holds_until_release_and_pause_and_reduced_motion_freeze_it(self):
        model, scene = self.encounter('veylume', 3)
        for _ in range(2):
            action = self.start_enemy_turn(scene)
            scene.update(action.duration)
        self.assertEqual(scene._pose('enemy')[0], 'charged_hold')
        self.assertIn('charged_hold', scene.sprites.actors['veylume']['animations'])
        self.assertTrue(scene.sprites.actors['veylume']['animations']['charged_hold'][1])
        before = (scene._elapsed, scene._pose('enemy'), model.enemy.mp,
                  tuple(member.hp for member in model.party), model.telegraphed_target)
        scene.paused = True
        scene.update(10)
        self.draw(scene)
        self.assertEqual((scene._elapsed, scene._pose('enemy'), model.enemy.mp,
                          tuple(member.hp for member in model.party), model.telegraphed_target), before)
        scene.paused = False
        self.game.audio.set_reduced_motion(True)
        scene.update(.1)
        first = scene._pose('enemy')
        position = scene._positions()['enemy']
        scene.update(.1)
        self.assertEqual(first, scene._pose('enemy'))
        self.assertEqual(position, scene._positions()['enemy'])
        flash = self.start_enemy_turn(scene)
        self.assertEqual(flash.action, 'veylume_veinflash')
        scene.update(flash.impact_at)
        self.assertEqual(scene._pose('enemy')[0], 'veinflash')

    def test_actual_player_impacts_play_complete_hurt_then_authored_defeat(self):
        for actor, level in (('lithrusk', 2), ('veylume', 3)):
            model, scene = self.encounter(actor, level, three_party=False)
            before = deepcopy(self.game.attributes.to_dict())
            model._start_action('player', 'attack')
            action = model.current_action
            scene.update(action.impact_at)
            self.assertEqual(scene._pose('enemy')[0], 'hurt')
            scene.update(.45)
            self.assertEqual(scene._pose('enemy')[0], 'hurt', 'The last hurt poses must not be truncated')
            scene.update(.06)
            self.assertEqual(scene._pose('enemy')[0], 'idle')
            if model.current_action is not None:
                scene.update(model.current_action.duration-model.current_action.elapsed)
            model.enemy.hp = 1
            model._start_action('player', 'attack')
            action = model.current_action
            scene.update(action.impact_at)
            self.assertEqual(model.enemy.hp, 0)
            self.assertEqual(scene._pose('enemy')[0], 'hurt')
            scene.update(.19)
            self.assertEqual(scene._pose('enemy')[0], 'defeat')
            self.draw(scene)
            self.assert_in_field(scene, self.enemy_bounds(scene))
            scene.update(2)
            self.draw(scene)
            state, time = scene._pose('enemy')
            self.assertEqual(state, 'defeat')
            actual, _ = scene.sprites.frame(actor, state, time)
            final, _ = scene.sprites.frame(actor, 'defeat', 1000000)
            self.assertEqual(pygame.image.tobytes(actual, 'RGBA'), pygame.image.tobytes(final, 'RGBA'))
            self.assertEqual(self.game.attributes.to_dict(), before)

    def test_both_new_shadows_remain_on_the_authored_ground_plane(self):
        widths = {}
        for actor, level in (('lithrusk', 2), ('veylume', 3)):
            _, scene = self.encounter(actor, level)
            point = scene._ground_positions()['enemy']
            layer = pygame.Surface((480, 320), pygame.SRCALPHA)
            scene._draw_shadow(layer, 'enemy', point)
            bounds = layer.get_bounding_rect()
            self.assertLessEqual(abs(bounds.centery-round(point.y)), 1)
            self.assertLessEqual(abs(bounds.centerx-round(point.x)), 1)
            widths[actor] = bounds.width
        self.assertGreater(widths['lithrusk'], widths['veylume']*1.5)

    def test_electric_projectiles_are_seekable_and_end_at_the_exact_impact(self):
        fx = BattleActionEffects()
        anchors = {'cast_origin': (130, 110), 'release_origin': (130, 110),
                   'target_hit': (350, 130)}
        for identifier, impact in (('veylume_static_spark', .45), ('veylume_veinflash', .55)):
            action = SimpleNamespace(action=identifier, kind='magical', duration=1,
                                     impact_at=impact, elapsed=0, resolved=False)
            release = fx.release_at(action)
            self.assertIsNone(fx.sample((100, 150), (350, 160), action, release-.001, anchors)['projectile'])
            first = fx.sample((100, 150), (350, 160), action, release, anchors)
            self.assertEqual(first['projectile']['point'], anchors['release_origin'])
            arrival = fx.sample((100, 150), (350, 160), action, impact-1e-9, anchors)
            self.assertAlmostEqual(arrival['projectile']['point'][0], 350, places=5)
            self.assertAlmostEqual(arrival['projectile']['point'][1], 130, places=5)
            self.assertIsNone(fx.sample((100, 150), (350, 160), action, impact, anchors)['projectile'])
            middle = (release+impact)/2
            def render(value):
                image = pygame.Surface((480, 320), pygame.SRCALPHA)
                fx.draw(image, (100, 150), (350, 160), value, middle, anchors)
                return pygame.image.tobytes(image, 'RGBA')
            expected = render(action)
            action.resolved = True
            self.assertIsNone(fx.sample((100, 150), (350, 160), action, middle, anchors)['projectile'])
            action.resolved = False
            with patch('pygame.image.load', side_effect=AssertionError('Effects must not read art per frame')):
                fx.sample((100, 150), (350, 160), action, 10, anchors)
                self.assertEqual(render(action), expected)
            generic = SimpleNamespace(**vars(action))
            generic.action = 'ordinary_magic'
            self.assertNotEqual(render(generic), expected, 'Electric bolts must have their own color and shape')

    def test_reduced_motion_charge_is_static_local_and_can_be_scrubbed(self):
        fx = BattleActionEffects()
        def render(age, reduced):
            image = pygame.Surface((160, 120), pygame.SRCALPHA)
            fx.draw_electric_charge(image, (80, 60), age, reduced_motion=reduced)
            return image
        first = render(.1, True)
        self.assertTrue(first.get_bounding_rect())
        self.assertLessEqual(first.get_bounding_rect().width, 30)
        self.assertLessEqual(first.get_bounding_rect().height, 30)
        self.assertEqual(pygame.image.tobytes(first, 'RGBA'),
                         pygame.image.tobytes(render(10, True), 'RGBA'))
        expected = pygame.image.tobytes(render(.35, False), 'RGBA')
        for age in (8, .1, .7, 2):
            render(age, False)
        self.assertEqual(pygame.image.tobytes(render(.35, False), 'RGBA'), expected)


if __name__ == '__main__':
    unittest.main()
