"""Live boss tells, area impacts and recovery feedback follow model state."""
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
from battle_scene import BattleScene, CombatSprites
from character_attributes import CharacterAttributes
from inventory import Inventory
from leveling import character_stats
from ui_style import UIStyle
from test_random_enemy_groups import clear_gauges


class FixedVariance:
    def randint(self, low, high):
        assert (low, high) == (95, 105)
        return 100


class VespermawLiveSceneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.display.init()
        pygame.font.init()
        pygame.display.set_mode((960, 640))
        cls.sprites = CombatSprites()

    @classmethod
    def tearDownClass(cls):pygame.quit()

    def scene(self, size=(960, 640), text=1):
        game = SimpleNamespace(window=pygame.display.set_mode(size),
            ui_surface=pygame.Surface(size), audio=AudioSettings(), inventory=Inventory())
        game.audio.set_effects(0)
        game.audio.set_text_scale(text)
        game.ui = UIStyle(game)
        game.to_canvas = lambda point: (point[0]*480/size[0], point[1]*320/size[1])
        party = []
        for identifier, name in (('player', 'Caelan'), ('mira', 'Mira'), ('lucan', 'Lucan')):
            stats = character_stats('caelan' if identifier == 'player' else identifier, 7)
            party.append({'identifier': identifier, 'name': name, 'attributes': stats,
                          'hp': stats['hp'], 'mp': stats['mp'],
                          'attack': 'bolt_shot' if identifier == 'mira' else 'attack'})
        model = BattleModel.from_bestiary(CharacterAttributes(), 'vespermaw', 7,
            party_members=party, bot_loadouts={}, rng=FixedVariance(), initial_atb=False)
        scene = BattleScene(game, model, sprites=self.sprites, battlefield='cave_echo_chamber')
        canvas = pygame.Surface((480, 320))
        scene.draw(canvas, game.ui_surface)
        return scene, canvas, game

    def start(self, scene, action):
        clear_gauges(scene.model)
        scene.model._start_action('enemy', 'vespermaw_'+action)
        scene.update(0)
        return scene.model.current_action

    def resources(self, scene):
        return deepcopy([(actor.identifier, actor.hp, actor.mp, actor.atb)
                         for actor in (*scene.model.party, *scene.model.enemies)])

    def test_roar_renders_from_the_current_mouth_to_all_hit_members_with_individual_feedback(self):
        for size, text in (((960, 640), 1), ((480, 320), 1.5)):
            with self.subTest(size=size, text=text):
                scene, canvas, game = self.scene(size, text)
                model = scene.model
                model.player.guarded = True
                before = {actor.identifier: actor.hp for actor in model.party}
                action = self.start(scene, 'confluence_roar')
                scene.update(action.impact_at/2)
                scene.draw(canvas, game.ui_surface)
                positions = scene._positions()
                geometry = scene._vespermaw_roar_geometry(positions)
                self.assertEqual({actor for actor, _ in geometry['targets']}, set(before))
                state, time = scene._pose('enemy')
                native = scene.sprites.anchors('vespermaw', state, time)['cast_origin']
                expected = positions['enemy']+(pygame.Vector2(native)-scene._enemy_art('enemy')['anchor'])*scene._actor_scale('enemy')
                self.assertEqual(geometry['origin'], expected)
                self.assertIn('Confluence Roar', scene.announcements.current['text'])
                with patch.object(scene.action_audio, 'play') as impact_audio:
                    scene.update(action.impact_at/2)
                self.assertEqual(sum(call.args[0] in ('impact', 'guard_hit')
                                     for call in impact_audio.call_args_list), 1)
                self.assertTrue(action.resolved)
                self.assertEqual(set(scene._reactions), set(before))
                self.assertEqual({entry['target'] for entry in scene._popups}, set(before))
                self.assertTrue(all(actor.hp < before[actor.identifier] for actor in model.party))
                self.assertFalse(model.player.guarded)
                saved = self.resources(scene)
                scene.draw(canvas, game.ui_surface)
                self.assertEqual(self.resources(scene), saved)

    def test_roar_skips_preexisting_ko_but_keeps_newly_hit_ko_in_the_wave(self):
        scene, canvas, game = self.scene()
        scene.model.combatant('mira').hp = 0
        scene.model.player.hp = 1
        action = self.start(scene, 'confluence_roar')
        self.assertEqual(action.targets, ('player', 'lucan'))
        scene.update(action.impact_at)
        self.assertEqual(scene.model.player.hp, 0)
        geometry = scene._vespermaw_roar_geometry(scene._positions())
        self.assertEqual({actor for actor, _ in geometry['targets']}, {'player', 'lucan'})
        self.assertNotIn('mira', scene._reactions)
        scene.draw(canvas, game.ui_surface)

    def test_roar_effect_is_clipped_and_reduced_motion_has_no_travel_clock(self):
        scene, _, _ = self.scene()
        action = self.start(scene, 'confluence_roar')
        scene.update(action.impact_at)
        scene.game.audio.set_reduced_motion(True)
        canvas = pygame.Surface((480, 320), pygame.SRCALPHA)
        positions = scene._positions()
        before = canvas.get_clip()
        scene._draw_vespermaw_roar(canvas, positions)
        first = pygame.image.tobytes(canvas, 'RGBA')
        self.assertEqual(canvas.get_clip(), before)
        self.assertTrue(pygame.Rect(0, 35, 480, scene.panel_rect.top-35)
                        .contains(canvas.get_bounding_rect()))
        scene._elapsed += 50
        canvas.fill((0, 0, 0, 0))
        scene._draw_vespermaw_roar(canvas, positions)
        self.assertEqual(pygame.image.tobytes(canvas, 'RGBA'), first)

    def test_charge_warning_tracks_the_marked_character_and_clears_after_pounce(self):
        scene, canvas, game = self.scene()
        action = self.start(scene, 'gather_resonance')
        scene.update(action.impact_at)
        target = scene.model.enemy_telegraphs['enemy']
        self.assertIn(scene.model.combatant(target).name, scene.announcements.current['text'])
        scene.update(action.duration-action.impact_at)
        self.assertEqual(scene._pose('enemy')[0], 'charged_hold')
        scene.draw(canvas, game.ui_surface)
        self.assertIn('enemy', scene.charge_aura_rects)
        scene.announcements.update(3)
        self.assertIn(scene.model.combatant(target).name, scene.announcements.current['text'])
        scene.model.combatant(target).hp = 0
        scene.update(0)
        new_target = scene.model.enemy_telegraphs['enemy']
        self.assertNotEqual(new_target, target)
        self.assertIn(scene.model.combatant(new_target).name, scene.announcements.current['text'])
        pounce = self.start(scene, 'ruinous_pounce')
        scene.update(pounce.duration)
        self.assertEqual(scene._pose('enemy')[0], 'exhausted')
        scene.draw(canvas, game.ui_surface)
        self.assertFalse(scene.charge_aura_rects)

    def test_exhaustion_notice_and_loop_stop_immediately_when_claw_starts_or_result_occurs(self):
        scene, canvas, game = self.scene()
        action = self.start(scene, 'ruinous_pounce')
        scene.update(action.duration)
        scene.announcements.clear()
        self.assertEqual(scene._pose('enemy')[0], 'exhausted')
        self.assertIn('50% more damage', scene.announcements.current['text'])
        scene.update(.3)
        self.assertGreater(scene.announcements.current['age'], 0)
        before = scene._pose('enemy')[1]
        recovery = self.start(scene, 'exhausted')
        self.assertEqual(scene._pose('enemy')[1], before)
        scene.update(recovery.duration)
        self.assertGreater(scene._pose('enemy')[1], before)
        self.start(scene, 'raking_claw')
        self.assertFalse(scene.model.enemy_recovery_states)
        self.assertFalse(scene._enemy_recovery_times)
        self.assertNotIn('50%', (scene.announcements.current or {}).get('text', ''))
        scene.draw(canvas, game.ui_surface)
        scene.model._result('defeat')
        scene.update(0)
        self.assertIsNone(scene.announcements.current)
        self.assertFalse(scene._enemy_charge_times)
        self.assertFalse(scene._enemy_recovery_times)

    def test_marked_target_fits_the_first_warning_page_at_minimum_enlarged_text(self):
        scene, _, game = self.scene((480, 320), 1.5)
        action = self.start(scene, 'gather_resonance')
        scene.update(action.impact_at)
        text = scene.announcements.current['text']
        self.assertIn('Ruinous Pounce', text)
        self.assertIn(scene.model.combatant(scene.model.enemy_telegraphs['enemy']).name, text)
        painter = game.ui.painter(game.ui_surface)
        self.assertEqual(len(painter.wrap(text, scene.announcement_rect.width-18, bold=True)), 1)

    def test_flee_command_uses_the_model_boss_restriction(self):
        scene, _, _ = self.scene()
        clear_gauges(scene.model)
        scene.model.player.atb = 1
        scene.update(0)
        self.assertIn('flee', scene._command_actions())
        self.assertIn('Cannot flee', scene._command_reason('flee'))
        self.assertFalse(scene.model.choose_action('flee'))
