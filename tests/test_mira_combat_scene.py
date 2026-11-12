"""Mira releases at her authored muzzle and braces on guarded impacts."""
from copy import deepcopy
import os
import random
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
from character_attributes import CharacterAttributes
from mira_combat_art import MiraCombatArt
from battle_sprite_fixtures import FieldSprites
from ui_style import UIStyle


def fixture_manifest():
    """Two different postrelease muzzles detect an incorrectly moving origin."""
    timings = (100, 100, 80, 40, 80, 160, 120, 120)
    muzzles = ((14, 34), (12, 33), (10, 32), (8, 31),
               (11, 30), (12, 32), (13, 33), (14, 34))
    frames = [{'file': f'attack_{i}.png', 'duration_ms': duration,
               'anchors': {'floor': [32, 54], 'muzzle': list(muzzle),
                           'controller': [30, 34]}}
              for i, (duration, muzzle) in enumerate(zip(timings, muzzles))]
    return {'canvas': [64, 64], 'anchor': [32, 54], 'animations': {
        'attack': {'loop': False, 'release_ms': 280, 'contact_ms': 400, 'frames': frames},
        'idle': {'loop': True, 'frames': [deepcopy(frames[0]), deepcopy(frames[1])]},
        'bulwark': {'loop': False, 'contact_ms': 620, 'frames': [
            {**deepcopy(frames[0]), 'duration_ms': 620,
             'anchors': {'floor': [32, 54], 'muzzle': [14, 34], 'projector': [12, 32]}},
            {**deepcopy(frames[1]), 'duration_ms': 480,
             'anchors': {'floor': [32, 54], 'muzzle': [12, 33], 'projector': [8, 29]}}]},
    }}


class MiraAnchorTests(unittest.TestCase):
    def setUp(self):
        self.art = MiraCombatArt(data=fixture_manifest())

    def test_pose_selection_matches_frame_boundaries_loop_and_finished_hold(self):
        self.assertEqual(self.art.anchors('attack', 279.99)['muzzle'], (10, 32))
        self.assertEqual(self.art.anchors('attack', 280)['muzzle'], (8, 31))
        self.assertEqual(self.art.anchors('attack', 320)['muzzle'], (11, 30))
        self.assertEqual(self.art.anchors('attack', 10000)['muzzle'], (14, 34))
        self.assertEqual(self.art.anchors('idle', 200)['muzzle'], (14, 34))
        self.assertEqual(self.art.anchors('unknown', -10)['muzzle'], (14, 34))

    def test_projectile_has_no_prerelease_or_postimpact_existence(self):
        floor, target = (404, 151), (173, 158)
        self.assertIsNone(self.art.shot(.27999, .4, floor, target)['projectile'])
        release = self.art.shot(.28, .4, floor, target)
        self.assertEqual(release['origin'], (356, 105))
        self.assertEqual(release['projectile'], release['origin'])
        middle = self.art.shot(.34, .4, floor, target)
        self.assertNotEqual(middle['muzzle'], release['muzzle'])
        self.assertEqual(middle['origin'], release['origin'])
        self.assertAlmostEqual(middle['fraction'], .5)
        self.assertEqual(middle['projectile'], (264.5, 131.5))
        self.assertIsNone(self.art.shot(.4, .4, floor, target)['projectile'])
        self.assertIsNone(self.art.shot(.35, .4, floor, target, resolved=True)['projectile'])

    def test_anchor_metadata_is_copied_and_invalid_clocks_are_rejected(self):
        data = fixture_manifest()
        art = MiraCombatArt(data=data)
        data['animations']['attack']['frames'][3]['anchors']['muzzle'][0] = 999
        self.assertEqual(art.anchors('attack', 280)['muzzle'], (8, 31))
        for time in (True, float('nan'), float('inf'), '280'):
            with self.subTest(time=time), self.assertRaises(ValueError):
                art.anchors('attack', time)
        for release in (0, 400, 500):
            data = fixture_manifest()
            data['animations']['attack']['release_ms'] = release
            with self.subTest(release=release), self.assertRaises(ValueError):
                MiraCombatArt(data=data)


class MiraCombatSceneTests(unittest.TestCase):
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
        self.model = BattleModel(self.game.attributes, (), guest_id='mira',
                                 enemy_id='ridgeback_tusker', rng=random.Random(4))
        self.sprites = FieldSprites()
        self.scene = BattleScene(self.game, self.model, sprites=self.sprites, battlefield='millrace')
        self.scene.mira_art = MiraCombatArt(data=fixture_manifest())
        self.mira = self.model.combatant('mira')
        self.scene.draw(self.canvas, self.game.ui_surface)

    def tearDown(self):
        pygame.quit()

    def choose(self, command):
        if command == 'bulwark':
            self.assertTrue(self.model.set_rig_allocation({'weapons': 0, 'protection': 3, 'support': 3}))
        self.mira.atb = 1
        self.scene.update(0)
        self.scene.draw(self.canvas, self.game.ui_surface)
        if command == 'bulwark':
            self.click(self.scene.command_rects['skills'].center)
        self.click(self.scene.command_rects[command].center)
        return self.model.current_action

    def click(self, point):
        for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            self.scene.handle_event(pygame.event.Event(kind, button=1, pos=point))

    def test_shot_releases_after_aim_and_damage_still_occurs_once_at_point_four(self):
        hp = self.model.enemy.hp
        home = self.scene._home_positions()['mira'].copy()
        action = self.choose('attack')
        self.assertEqual((action.action, action.duration, action.impact_at), ('bolt_shot', .8, .4))
        self.scene.update(.279)
        self.assertIsNone(self.scene._mira_shot()['projectile'])
        self.assertEqual(self.model.enemy.hp, hp)
        self.scene.update(.001)
        shot = self.scene._mira_shot()
        self.assertEqual(shot['projectile'], shot['origin'])
        self.assertEqual(shot['target'], tuple(self.scene._hit_point('enemy')))
        self.scene.update(.119)
        self.assertIsNotNone(self.scene._mira_shot()['projectile'])
        self.assertEqual(self.model.enemy.hp, hp)
        self.scene.update(.001)
        self.assertTrue(action.resolved)
        self.assertLess(self.model.enemy.hp, hp)
        self.assertIsNone(self.scene._mira_shot()['projectile'])
        damaged_hp = self.model.enemy.hp
        self.scene.update(.2)
        self.assertEqual(self.model.enemy.hp, damaged_hp)
        self.assertEqual(self.scene._positions()['mira'], home)

    def test_guard_entry_and_held_guard_have_distinct_states_from_guarded_impact(self):
        action = self.choose('guard')
        self.assertEqual(self.scene._pose('mira')[0], 'guard_enter')
        self.scene.update(action.duration)
        self.assertTrue(self.mira.guarded)
        self.assertEqual(self.scene._pose('mira')[0], 'guard')
        self.scene._reactions['mira'] = {'age': .1, 'guarded': True,
                                         'lethal': False, 'action': 'tusk_strike'}
        self.assertEqual(self.scene._pose('mira'), ('guard_impact', 100.))
        self.scene._reactions['mira']['guarded'] = False
        self.assertEqual(self.scene._pose('mira'), ('hurt', 100.))
        self.scene._reactions['mira']['age'] = .4
        self.assertEqual(self.scene._pose('mira')[0], 'guard')

    def test_pause_and_focus_freeze_release_clock_and_reduced_motion_keeps_bolt(self):
        self.choose('attack')
        self.scene.update(.34)
        before = self.scene._mira_shot()
        self.scene.paused = True
        self.scene.update(20)
        self.assertEqual(self.scene._mira_shot(), before)
        self.scene.paused = False
        self.scene.focused = False
        self.scene.update(20)
        self.assertEqual(self.scene._mira_shot(), before)
        self.scene.focused = True
        self.game.audio.reduced_motion = True
        self.assertEqual(self.scene._mira_shot(), before)
        with patch('battle_scene.pygame.draw.line', wraps=pygame.draw.line) as lines:
            self.scene._draw_mira_effects(self.canvas)
        self.assertEqual(lines.call_count, 2)

    def test_release_cue_is_once_after_threshold_and_drawing_does_not_restart_it(self):
        self.choose('attack')
        with patch.object(self.scene.action_audio, 'play') as cues:
            self.scene.update(.279)
            self.assertFalse(cues.called)
            self.scene.update(.001)
            self.scene._draw_mira_effects(self.canvas)
            self.scene._draw_mira_effects(self.canvas)
            self.scene.update(.01)
        self.assertEqual([call.args for call in cues.call_args_list], [('focus',)])

    def test_bulwark_projector_uses_current_drawing_anchor_and_actual_impact(self):
        action = self.choose('bulwark')
        self.scene.update(action.impact_at-.001)
        self.assertEqual(self.mira.barrier, 0)
        self.scene.update(.001)
        self.assertGreater(self.mira.barrier, 0)
        point = self.scene.mira_art.world_anchor('bulwark', 620, 'projector',
                                                 self.scene._positions()['mira'])
        geometry = self.scene._rig_skill_geometry()
        self.assertEqual(tuple(geometry['attachment']), point)
        self.assertEqual(geometry['target_id'], 'mira')
        self.assertIsNone(geometry['fraction'])
        self.scene._draw_rig_skill_effects(self.canvas, self.scene._positions())
        self.game.audio.reduced_motion = True
        self.scene._draw_rig_skill_effects(self.canvas, self.scene._positions())
        self.assertEqual(self.mira.barrier, 37)


if __name__ == '__main__':
    unittest.main()
