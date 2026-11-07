"""Caelan's staged actions share the model clock and battlefield projection."""
from copy import deepcopy
import json
import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame

from audio_settings import AudioSettings
from battle_choreography import load_choreography
from battle_model import BattleModel, ENEMY_PATH
from battle_scene import BattleScene
from character_attributes import CharacterAttributes
from test_aether_edge_battle_model import FixedVariance
from ui_style import Painter, UIStyle


class SpriteFixture:
    def __init__(self):
        self.image = pygame.Surface((48, 48), pygame.SRCALPHA)
        pygame.draw.rect(self.image, '#d8c49b', (14, 6, 20, 36))

    def frame(self, actor, state, elapsed_ms):
        return self.image, (24, 42)


class ChoreographySceneTests(unittest.TestCase):
    def setUp(self):
        pygame.display.init()
        pygame.font.init()
        self.game = SimpleNamespace(window=pygame.display.set_mode((960, 640)),
                                    ui_surface=pygame.Surface((960, 640)),
                                    audio=AudioSettings(), attributes=CharacterAttributes())
        self.game.audio.set_effects(0)
        self.game.ui = UIStyle(self.game)
        self.game.to_canvas = lambda point: (point[0]/2, point[1]/2)
        self.canvas = pygame.Surface((480, 320))
        self.profiles = load_choreography()
        self.make_scene()

    def tearDown(self):
        pygame.quit()

    def make_scene(self, *, armed=True, enemy='bat', enemy_hp=1000000, party=False):
        enemies = json.loads(ENEMY_PATH.read_text())
        enemies['enemies'][enemy]['attributes'].update(hp=enemy_hp, speed=0)
        self.model = BattleModel(self.game.attributes, ['aether_edge', 'aether_dart'],
                                 weapon_equipped=armed, enemy_id=enemy,
                                 guest_id='mira' if party else None,
                                 enemy_data=enemies, rng=FixedVariance())
        self.scene = BattleScene(self.game, self.model, sprites=SpriteFixture(),
                                 battlefield='millrace' if enemy != 'bat' else 'eldenmere')
        self.draw()

    def draw(self):
        self.scene.draw(self.canvas, self.game.ui_surface)

    def click(self, point):
        for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            self.scene.handle_event(pygame.event.Event(kind, button=1,
                                                      pos=(point[0]*2, point[1]*2)))

    def choose(self, command):
        self.model.player.atb = 1
        self.scene.update(0)
        self.draw()
        if command == 'aether_edge':
            self.click(self.scene.command_rects['skills'].center)
        self.assertIn(command, self.scene._command_actions())
        for _ in self.scene._command_actions():
            if command in self.scene.command_rects:break
            self.scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN))
            self.draw()
        self.assertIn(command, self.scene.command_rects)
        self.click(self.scene.command_rects[command].center)
        self.assertEqual(self.model.current_action.action, command)
        return self.model.current_action

    def test_real_menu_actions_follow_distinct_phases_and_pose_clocks(self):
        expected = {
            'attack': ['prepare', 'approach', 'plant', 'strike', 'followthrough', 'retreat', 'land'],
            'aether_edge': ['focus', 'prepare', 'approach', 'plant', 'strike', 'followthrough', 'retreat', 'land'],
            'aether_dart': ['prepare', 'release', 'recover'],
            'guard': ['prepare', 'brace', 'recover'],
        }
        for armed in (False, True):
            for command, phases in expected.items():
                if command == 'aether_edge' and not armed:
                    continue
                with self.subTest(armed=armed, command=command):
                    self.make_scene(armed=armed)
                    action = self.choose(command)
                    observed = []
                    for phase in self.profiles[command]['phases']:
                        midpoint = (phase['start']+phase['end'])/2
                        self.scene.update(midpoint-action.elapsed)
                        sample = self.scene._choreography()
                        observed.append(sample.phase)
                        self.assertEqual(self.scene._pose('player'), (sample.pose, sample.pose_ms))
                        self.assertGreater(sample.phase_progress, 0)
                        self.assertLess(sample.phase_progress, 1)
                    self.assertEqual(observed, phases)

    def test_lethal_impact_applies_once_then_lands_before_victory(self):
        for command in ('attack', 'aether_edge'):
            with self.subTest(command=command):
                self.make_scene(enemy_hp=1)
                home = self.scene._ground_positions()['player'].copy()
                action = self.choose(command)
                self.scene.update(action.impact_at-1e-4)
                self.assertEqual(self.model.enemy.hp, 1)
                self.assertFalse(action.resolved)
                self.scene.update(1e-4)
                self.assertTrue(action.resolved)
                self.assertEqual(self.model.enemy.hp, 0)
                self.assertEqual(self.model.phase, 'acting')
                self.assertEqual(len([p for p in self.scene._popups if p['text'].isdigit()]), 1)
                self.assertEqual(self.scene._pose('enemy')[0], 'hurt')
                self.scene.update(.18)
                self.assertEqual(self.scene._pose('enemy')[0], 'defeat')
                land_start = self.profiles[command]['phases'][-1]['start']
                self.scene.update(land_start-action.elapsed)
                self.assertEqual(self.scene._ground_positions()['player'], home)
                self.assertEqual(self.scene._positions()['player'], home)
                self.assertEqual(self.scene._pose('player')[0], 'land')
                self.assertEqual(self.model.phase, 'acting')
                self.scene.update(action.duration-action.elapsed)
                self.assertEqual(self.model.phase, 'victory')
                self.assertEqual(self.scene._positions()['player'], home)
                self.assertEqual(self.scene._pose('player')[0], 'victory')
                self.assertEqual(self.model.last_action.damage, action.damage)

    def test_retreat_hop_raises_feet_while_shadow_stays_on_the_floor(self):
        for command in ('attack', 'aether_edge'):
            with self.subTest(command=command):
                self.make_scene()
                self.choose(command)
                phase = next(p for p in self.profiles[command]['phases'] if p['name'] == 'retreat')
                self.scene.update((phase['start']+phase['end'])/2)
                floor = self.scene._ground_positions()['player']
                feet = self.scene._positions()['player']
                self.assertGreater(floor.y-feet.y, 7)
                self.assertEqual(feet.x, floor.x)
                with patch.object(self.scene, '_draw_shadow', wraps=self.scene._draw_shadow) as shadows:
                    self.scene._draw_field(self.canvas)
                player_shadow = next(call for call in shadows.call_args_list if call.args[1] == 'player')
                self.assertEqual(player_shadow.args[2], floor)

    def test_dart_prepares_at_home_releases_then_hits_at_the_projectile_boundary(self):
        home = self.scene._ground_positions()['player'].copy()
        action = self.choose('aether_dart')
        hp = self.model.enemy.hp
        self.scene.update(.74)
        self.assertEqual(self.scene._pose('player')[0], 'cast_prepare')
        self.assertIsNone(self.scene._choreography().projectile_progress)
        self.scene.update(.18)
        self.assertEqual(self.scene._pose('player')[0], 'cast_release')
        self.assertGreater(self.scene._choreography().projectile_progress, 0)
        self.assertLess(self.scene._choreography().projectile_progress, 1)
        self.assertEqual(self.model.enemy.hp, hp)
        self.assertEqual(self.scene._ground_positions()['player'], home)
        self.scene.update(action.impact_at-action.elapsed)
        self.assertEqual(self.scene._choreography().projectile_progress, 1)
        self.assertEqual(self.scene._pose('player')[0], 'cast_recover')
        self.assertLess(self.model.enemy.hp, hp)
        self.assertEqual(self.model.player.mp, 26)

    def test_event_reactions_do_not_depend_on_damage_popup_visibility(self):
        for enemy, identifier in (('bat', 'bite'), ('ridgeback_tusker', 'tusker_charge')):
            for guarded in (False, True):
                with self.subTest(enemy=enemy, guarded=guarded):
                    self.make_scene(enemy=enemy)
                    if guarded:
                        guard = self.choose('guard')
                        self.scene.update(guard.duration)
                    self.model._start_action('enemy', identifier)
                    action = self.model.current_action
                    self.scene.update(action.impact_at)
                    self.assertIn('player', self.scene._reactions)
                    self.assertEqual(self.scene._reactions['player']['guarded'], guarded)
                    self.scene._popups.clear()
                    self.assertEqual(self.scene._pose('player')[0], 'guard_impact' if guarded else 'hurt_recover')
                    self.scene.update(.12)
                    self.assertIn(self.scene._pose('player')[0], ('hurt', 'hurt_recover', 'guard_impact'))
                    self.scene.update(.8)
                    self.assertNotIn('player', self.scene._reactions)

    def test_camera_frames_world_but_menu_bounds_and_labels_stay_fixed(self):
        action = self.choose('attack')
        bounds = deepcopy((self.scene.panel_rect, self.scene.gear.rect, self.scene.party_rows,
                           self.scene.command_rects))
        self.scene.update(action.impact_at)
        zoom, offset = self.scene._camera()
        self.assertGreater(zoom, 1)
        self.assertLessEqual(zoom, 1.08)
        point = self.scene._positions()['player']
        self.assertNotEqual(self.scene._project(point), point)
        self.draw()
        self.assertEqual((self.scene.panel_rect, self.scene.gear.rect, self.scene.party_rows,
                          self.scene.command_rects), bounds)
        self.assertEqual(len(offset), 2)

    def test_damage_popups_use_the_same_camera_projection_as_actors(self):
        self.make_scene(enemy='ridgeback_tusker', party=True)
        action = self.choose('aether_edge')
        self.scene.update(action.impact_at)
        damage = str(action.damage)
        positions = []
        text = Painter.text

        def capture(painter, value, point, *args, **kwargs):
            if str(value) == damage:
                positions.append(point)
            return text(painter, value, point, *args, **kwargs)

        with patch.object(Painter, 'text', capture):
            self.draw()
        self.assertEqual(len(positions), 2)
        # The foreground number is centered above the same projected target.
        projected = self.scene._project(self.scene._positions()['enemy'])
        self.assertAlmostEqual(positions[-1][0], projected.x)
        self.assertLess(positions[-1][1], projected.y)

    def test_pause_freezes_action_phase_camera_and_event_reaction_clocks(self):
        action = self.choose('attack')
        self.scene.update(action.impact_at+.05)
        self.scene.handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        before = deepcopy((action.elapsed, self.scene._elapsed, self.scene._choreography(),
                           self.scene._camera(), self.scene._reactions, self.scene._popups))
        self.scene.update(100)
        self.draw()
        self.assertEqual((action.elapsed, self.scene._elapsed, self.scene._choreography(),
                          self.scene._camera(), self.scene._reactions, self.scene._popups), before)

    def test_reduced_motion_preserves_contact_and_poses_with_static_camera_and_feet(self):
        self.game.audio.set_reduced_motion(True)
        self.make_scene()
        home = self.scene._positions()['player'].copy()
        action = self.choose('aether_edge')
        self.scene.update(action.impact_at)
        self.assertEqual(self.scene._positions()['player'], home)
        self.assertEqual(self.scene._camera(), (1, (0, 0)))
        self.assertEqual(self.scene._pose('player')[0], 'aether_edge')
        self.assertTrue(action.resolved)
        self.assertGreater(action.damage, 0)
        self.scene.update(action.duration-action.elapsed)
        self.assertIsNone(self.model.current_action)
        self.assertEqual(self.scene._positions()['player'], home)

    def test_hover_only_slows_gauge_fill_and_never_the_committed_action(self):
        for command in ('attack', 'aether_edge', 'aether_dart', 'guard'):
            with self.subTest(command=command):
                self.make_scene()
                action = self.choose(command)
                point = self.scene.gear.rect.center
                self.scene.handle_event(pygame.event.Event(pygame.MOUSEMOTION,
                    pos=(point[0]*2, point[1]*2), rel=(0, 0), buttons=(0, 0, 0)))
                self.assertEqual(self.scene.atb_multiplier, .25)
                self.scene.update(action.duration)
                self.assertIsNone(self.model.current_action)
                self.assertEqual(self.model.last_action.elapsed, action.duration)

    def test_frame_partition_does_not_change_phase_damage_or_return_position(self):
        for target in (.3, .72, 1.08, 1.4):
            snapshots = []
            for small_frames in (False, True):
                self.make_scene()
                action = self.choose('attack')
                if small_frames:
                    for _ in range(int(target/.01)):
                        self.scene.update(.01)
                    remainder = target-int(target/.01)*.01
                    if remainder > 1e-12:
                        self.scene.update(remainder)
                else:
                    self.scene.update(target)
                snapshots.append((self.model.phase, self.model.enemy.hp, action.damage,
                                  self.scene._positions()['player'], self.scene._pose('player')[0],
                                  self.scene._positions()['enemy'], self.scene._pose('enemy')[0],
                                  {actor: round(record['age'], 8)
                                   for actor, record in self.scene._reactions.items()}))
            with self.subTest(target=target):
                self.assertEqual(snapshots[0][:3], snapshots[1][:3])
                self.assertLess(snapshots[0][3].distance_to(snapshots[1][3]), 1e-8)
                self.assertEqual(snapshots[0][4], snapshots[1][4])
                self.assertLess(snapshots[0][5].distance_to(snapshots[1][5]), 1e-8)
                self.assertEqual(snapshots[0][6:], snapshots[1][6:])


if __name__ == '__main__':
    unittest.main()
