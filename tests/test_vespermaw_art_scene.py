"""A labelled art-only specimen uses scene geometry without enabling boss rules."""
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import pygame

from audio_settings import AudioSettings
from battle_action_fx import target_reaction
from battle_model import BattleModel
from battle_scene import BattleScene, CombatSprites
from character_attributes import CharacterAttributes
from inventory import Inventory
from leveling import character_stats
from ui_style import UIStyle


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT/'assets/combat/vespermaw'


class VespermawArtSceneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.display.init()
        pygame.font.init()
        pygame.display.set_mode((960, 640))
        cls.sprites = CombatSprites()
        cls.sprites._load_actor('vespermaw')
        cls.manifest = json.loads((ART/'animation.json').read_text())

    @classmethod
    def tearDownClass(cls):pygame.quit()

    def scene(self, *, text_scale=1, size=(960, 640)):
        game = SimpleNamespace(window=pygame.display.set_mode(size),
            ui_surface=pygame.Surface(size), audio=AudioSettings(), inventory=Inventory())
        game.audio.set_effects(0)
        game.audio.set_text_scale(text_scale)
        game.ui = UIStyle(game)
        game.to_canvas = lambda point: (point[0]*480/size[0], point[1]*320/size[1])
        attributes = CharacterAttributes()
        members = []
        for identifier, name in (('player', 'Caelan'), ('mira', 'Mira'), ('lucan', 'Lucan')):
            stats = character_stats('caelan' if identifier == 'player' else identifier, 7)
            members.append({'identifier': identifier, 'name': name, 'attributes': stats,
                            'hp': stats['hp'], 'mp': stats['mp'],
                            'attack': 'bolt_shot' if identifier == 'mira' else 'attack'})
        # The specimen deliberately retains Bat rules: only the visual bank is
        # replaced. Vespermaw's canonical unsupported combat remains gated.
        model = BattleModel(attributes, enemy_id='bat', party_members=members)
        model.enemy_sprite_id = 'vespermaw'
        scene = BattleScene(game, model, sprites=self.sprites, battlefield='cave_depths')
        canvas = pygame.Surface((480, 320))
        scene.draw(canvas, game.ui_surface)
        return scene, canvas, game

    def test_manifest_points_and_frames_sample_the_same_clock_and_return_detached_points(self):
        for state, animation in self.manifest['animations'].items():
            elapsed = 0
            for index, record in enumerate(animation['frames']):
                with self.subTest(state=state, frame=index):
                    expected = self.sprites.actors['vespermaw']['animations'][state][0][index][0]
                    image, floor = self.sprites.frame('vespermaw', state, elapsed)
                    self.assertIs(image, expected)
                    points = self.sprites.anchors('vespermaw', state, elapsed)
                    self.assertEqual(points['floor'], tuple(self.manifest['anchor']))
                    for name, point in record.get('anchors', {}).items():
                        self.assertEqual(points[name], tuple(point))
                    points['floor'] = (0, 0)
                    self.assertEqual(self.sprites.anchors('vespermaw', state, elapsed)['floor'], floor)
                elapsed += record['duration_ms']
            end, _ = self.sprites.frame('vespermaw', state, elapsed)
            sequence = self.sprites.actors['vespermaw']['animations'][state][0]
            self.assertIs(end, sequence[0 if animation['loop'] else -1][0])

    def test_every_pose_fits_native_and_large_text_battlefield_with_three_companions(self):
        for size in ((480, 320), (960, 640)):
            for text_scale in (1, 1.5):
                scene, canvas, game = self.scene(text_scale=text_scale, size=size)
                area = scene._enemy_body_area('enemy')
                point = scene._home_positions()['enemy']
                scale = scene._actor_scale('enemy')
                for state, animation in self.manifest['animations'].items():
                    elapsed = 0
                    for index, record in enumerate(animation['frames']):
                        with self.subTest(size=size, text=text_scale, state=state, frame=index):
                            image, anchor = self.sprites.frame('vespermaw', state, elapsed)
                            rendered = pygame.transform.scale(image, (
                                max(1, round(image.get_width()*scale)),
                                max(1, round(image.get_height()*scale))))
                            rect = rendered.get_bounding_rect().move(
                                round(point.x-anchor[0]*scale), round(point.y-anchor[1]*scale))
                            self.assertGreater(rect.width*rect.height, 0)
                            self.assertTrue(area.contains(rect), (rect, area))
                        elapsed += record['duration_ms']
                self.assertIn('vespermaw', scene._shadows)
                scene.draw(canvas, game.ui_surface)

    def test_action_art_contact_clock_maps_to_the_authoritative_impact(self):
        scene, _, _ = self.scene()
        for state in ('raking_claw', 'confluence_roar', 'gather_resonance', 'ruinous_pounce'):
            animation = self.manifest['animations'][state]
            native = sum(frame['duration_ms'] for frame in animation['frames'])
            contact = animation.get('contact_ms')
            if contact is None:contact = native*.4
            action = SimpleNamespace(animation=state, elapsed=0., impact_at=.4, duration=1.)
            self.assertEqual(scene._vespermaw_pose(action), (state, 0.))
            action.elapsed = action.impact_at
            self.assertEqual(scene._vespermaw_pose(action), (state, contact))
            action.elapsed = action.duration
            self.assertEqual(scene._vespermaw_pose(action), (state, native-1))

    def test_charged_hold_and_idle_honor_reduced_motion_without_changing_art(self):
        scene, _, _ = self.scene()
        scene.model.telegraphed_target = 'player'
        scene._enemy_charge_times['enemy'] = .5
        scene._elapsed = 1.25
        self.assertEqual(scene._pose('enemy'), ('charged_hold', 750.))
        scene.game.audio.set_reduced_motion(True)
        self.assertEqual(scene._pose('enemy'), ('charged_hold', 0))
        scene.model.telegraphed_target = None
        self.assertEqual(scene._pose('enemy'), ('idle', 0))
        reaction_duration = target_reaction('vespermaw', 0)['duration']
        scene._reactions['enemy'] = {'age': reaction_duration/2, 'guarded': False, 'lethal': False}
        hurt_duration = sum(frame['duration_ms'] for frame in self.manifest['animations']['hurt']['frames'])
        self.assertEqual(scene._pose('enemy'), ('hurt', hurt_duration/2))
