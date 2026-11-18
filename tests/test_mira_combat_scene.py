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
        self.assertEqual(shot['target'], tuple(self.scene._bolt_hit_point('enemy')))
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

    def test_event_owned_bolt_contact_is_same_shoulder_and_recoil_does_not_slide_feet(self):
        action = self.choose('attack')
        home = self.scene._home_positions()['enemy'].copy()
        target = tuple(self.scene._mira_shot()['target'])
        with patch.object(self.scene.action_audio, 'play') as cues:
            self.scene.update(.45)
            record = self.scene._reactions['enemy']
            self.assertAlmostEqual(record['age'], .05)
            self.assertEqual(record['point'], target)
            self.assertEqual(self.scene._pose('enemy')[0], 'bolt_hurt')
            self.assertEqual(self.scene._ground_positions()['enemy'], home)
            self.assertEqual(self.scene._camera(), (1., (0., 0.)))
            self.scene.draw(self.canvas, self.game.ui_surface)
            self.scene.draw(self.canvas, self.game.ui_surface)
            self.scene.update(.1)
        self.assertEqual([call.args for call in cues.call_args_list], [('mira_clack',), ('bolt_impact',)])
        self.game.audio.reduced_motion = True
        self.assertEqual(self.scene._ground_positions()['enemy'], home)
        self.assertEqual(self.scene._reactions['enemy']['point'], target)
        self.scene.update(.2)
        self.assertEqual(self.scene._pose('enemy')[0], 'idle')

    def test_guarded_lethal_and_other_action_reactions_keep_existing_pose_paths(self):
        for action, guarded, lethal in (('bolt_shot', True, False),
                                        ('bolt_shot', False, True), ('attack', False, False)):
            with self.subTest(action=action, guarded=guarded, lethal=lethal):
                self.scene._reactions['enemy'] = dict(age=.05, action=action,
                                                      guarded=guarded, lethal=lethal)
                self.assertEqual(self.scene._pose('enemy')[0], 'hurt')
        self.scene._reactions['enemy'] = dict(age=.19, action='bolt_shot', guarded=False, lethal=True)
        self.model.enemy.hp = 0
        self.assertEqual(self.scene._pose('enemy')[0], 'defeat')

    def test_guarded_bolt_keeps_guard_cue_and_generic_hurt(self):
        self.model.enemy.guarded = True
        self.choose('attack')
        with patch.object(self.scene.action_audio, 'play') as cues:
            self.scene.update(.4)
        record = self.scene._reactions['enemy']
        self.assertTrue(record['guarded'])
        self.assertEqual(self.scene._pose('enemy')[0], 'hurt')
        self.assertEqual([call.args for call in cues.call_args_list], [('mira_clack',), ('guard_hit',)])

    def test_lethal_bolt_keeps_ordinary_hurt_then_defeat(self):
        self.model.enemy.hp = 1
        self.choose('attack')
        self.scene.update(.4)
        self.assertTrue(self.scene._reactions['enemy']['lethal'])
        self.assertEqual(self.scene._pose('enemy')[0], 'hurt')
        self.scene.update(.18)
        self.assertEqual(self.scene._pose('enemy')[0], 'defeat')

    def test_non_tusker_shots_use_registered_body_geometry_in_compact_layouts(self):
        for species, level in (('cave_bat', 2), ('lithrusk', 2), ('veylume', 3),
                               ('vespermaw', 7), ('embravyr', 5), ('nivareth', 5)):
            model = BattleModel.from_bestiary(self.game.attributes, species, level, guest_id='mira')
            scene = BattleScene(self.game, model)
            for text_scale in (1., 1.5):
                with self.subTest(species=species, text_scale=text_scale):
                    self.game.audio.set_text_scale(text_scale)
                    scene.draw(self.canvas, self.game.ui_surface)
                    point = scene._bolt_hit_point('enemy')
                    self.assertEqual(point, scene._hit_point('enemy'))
                    self.assertTrue(scene.enemy_rects['enemy'].collidepoint(point))
                    self.assertFalse(scene._bolt_recoil('enemy', dict(
                        action='bolt_shot', guarded=False, lethal=False)))
                    self.assertEqual(scene._bolt_recoil_pose('enemy', 300.), 'bolt_hurt')

    def test_tusker_idle_phase_selects_matching_raised_recoil_without_new_clock(self):
        scene = BattleScene(self.game, self.model)
        for clock, expected in ((0., 'bolt_hurt'), (239.9, 'bolt_hurt'),
                                (240., 'bolt_hurt_raised'), (479.9, 'bolt_hurt_raised'),
                                (480., 'bolt_hurt_low3'), (720., 'bolt_hurt_low4'),
                                (1200., 'bolt_hurt_raised')):
            self.assertEqual(scene._bolt_recoil_pose('enemy', clock), expected)

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
        with patch.object(self.scene.bolt_fx, 'draw_flight', wraps=self.scene.bolt_fx.draw_flight) as flight:
            self.scene._draw_mira_effects(self.canvas)
        self.assertTrue(flight.call_args.kwargs['reduced_motion'])
        self.assertIsNotNone(flight.call_args.args[1]['projectile'])

    def test_release_cue_is_once_after_threshold_and_drawing_does_not_restart_it(self):
        self.choose('attack')
        with patch.object(self.scene.action_audio, 'play') as cues:
            self.scene.update(.279)
            self.assertFalse(cues.called)
            self.scene.update(.001)
            self.scene._draw_mira_effects(self.canvas)
            self.scene._draw_mira_effects(self.canvas)
            self.scene.update(.01)
        self.assertEqual([call.args for call in cues.call_args_list], [('mira_clack',)])

    def test_skipped_whole_action_keeps_one_clack_without_replaying_on_draw(self):
        self.choose('attack')
        with patch.object(self.scene.action_audio,'play') as cues:
            self.scene.update(.8)
            self.scene._draw_mira_effects(self.canvas)
            self.scene.update(0)
        self.assertEqual([call.args for call in cues.call_args_list].count(('mira_clack',)),1)

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
