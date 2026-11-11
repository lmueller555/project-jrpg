"""Authored elemental poses, clear tells and truthful free-Edge presentation."""
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
from test_random_enemy_groups import clear_gauges
from ui_style import UIStyle


class FixedVariance:
    def randint(self, low, high):
        assert (low, high) == (95, 105)
        return 100


class ElementalBattleSceneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init();pygame.display.set_mode((960, 640))
        cls.sprites = CombatSprites()

    @classmethod
    def tearDownClass(cls):pygame.quit()

    def scene(self, enemy='embravyr', *, text=1, teaching=True, gems=('water', 'fire', 'ice')):
        size = (480, 320) if text > 1 else (960, 640)
        game = SimpleNamespace(window=pygame.display.set_mode(size),
            ui_surface=pygame.Surface(size), audio=AudioSettings(), inventory=Inventory())
        game.audio.set_effects(0);game.audio.set_text_scale(text)
        game.ui = UIStyle(game)
        game.to_canvas = lambda point: (point[0]*480/size[0], point[1]*320/size[1])
        party = []
        for identifier, name in (('player', 'Caelan'), ('mira', 'Mira')):
            stats = character_stats('caelan' if identifier == 'player' else identifier, 3)
            party.append({'identifier': identifier, 'name': name, 'attributes': stats,
                          'hp': stats['hp'], 'mp': stats['mp'],
                          'attack': 'bolt_shot' if identifier == 'mira' else 'attack'})
        model = BattleModel.from_bestiary_group(CharacterAttributes(),
            [{'enemy_id': enemy, 'level': 4}], party_members=party,
            learned_abilities=('aether_edge', 'aqua_edge', 'flame_edge', 'ice_edge'),
            weapon_equipped=True, owned_gems=gems, rng=FixedVariance(),
            initial_atb=False, elemental_tutorial=teaching)
        field = 'cave_embervein' if enemy == 'embravyr' else 'cave_stillfrost'
        scene = BattleScene(game, model, sprites=self.sprites, battlefield=field)
        canvas = pygame.Surface((480, 320))
        scene.draw(canvas, game.ui_surface)
        return scene, canvas, game

    def start(self, scene, local):
        clear_gauges(scene.model)
        prefix = scene.model.enemy_bestiary_id
        scene.model._start_action('enemy', prefix+'_'+local)
        scene.update(0)
        return scene.model.current_action

    def resources(self, scene):
        return deepcopy([(actor.identifier, actor.hp, actor.mp, actor.atb)
                         for actor in (*scene.model.party, *scene.model.enemies)])

    def test_skill_labels_and_eligibility_use_encounter_cost_without_granting_gems(self):
        for teaching in (True, False):
            for enemy in ('embravyr', 'nivareth'):
                scene, canvas, game = self.scene(enemy, teaching=teaching, gems=('water',))
                scene.model.player.mp = 0
                clear_gauges(scene.model);scene.model.player.atb = 1;scene.update(0)
                scene._set_menu('skills');scene.draw(canvas, game.ui_surface)
                for skill in ('aqua_edge', 'flame_edge', 'ice_edge'):
                    self.assertTrue(scene._command_label(skill).endswith('0 MP' if teaching else '4 MP'))
                self.assertEqual(scene.model.action_reason('aqua_edge'), '' if teaching else 'Not enough MP.')
                self.assertIn('Fire gem', scene.model.action_reason('flame_edge'))
                self.assertIn('Ice gem', scene.model.action_reason('ice_edge'))
                self.assertEqual(scene.model.owned_gems, ('water',))

    def test_aoe_uses_each_party_target_one_impact_cue_and_correct_color(self):
        for enemy, local in (('embravyr', 'emberwash'), ('nivareth', 'glassfall')):
            for text in (1, 1.5):
                scene, canvas, game = self.scene(enemy, text=text)
                before = self.resources(scene)
                action = self.start(scene, local)
                self.assertEqual(action.targets, ('player', 'mira'))
                scene.update(action.impact_at*.6)
                scene.draw(canvas, game.ui_surface)
                self.assertIn(action.name, scene.announcements.current['text'])
                with patch.object(scene.action_audio, 'play') as audio:
                    scene.update(action.impact_at*.4)
                self.assertTrue(action.resolved)
                self.assertEqual({entry['target'] for entry in scene._popups}, {'player', 'mira'})
                self.assertEqual(sum(call.args[0] in ('impact', 'guard_hit') for call in audio.call_args_list), 1)
                self.assertEqual(scene.model.enemy.mp, before[-1][2]-4)
                self.assertTrue(all(member.hp < before[index][1] for index, member in enumerate(scene.model.party)))
                saved = self.resources(scene);scene.draw(canvas, game.ui_surface)
                self.assertEqual(self.resources(scene), saved)
                palette = scene.action_fx._palette(action.action)
                self.assertEqual(palette, scene.action_fx.FIRE if enemy == 'embravyr' else scene.action_fx.ICE)

    def test_held_charge_and_exhaustion_follow_authoritative_states(self):
        for enemy, prepare, strike, recover, ordinary in (
                ('embravyr', 'gather_embers', 'furnace_lunge', 'cooling', 'cinder_lash'),
                ('nivareth', 'gather_frost', 'frostspire_thrust', 'settling', 'rime_needle')):
            scene, canvas, game = self.scene(enemy)
            action = self.start(scene, prepare)
            scene.update(action.impact_at)
            self.assertIn(scene.model.combatant(scene.model.telegraphed_target).name,
                          scene.announcements.current['text'])
            scene.draw(canvas, game.ui_surface)
            self.assertTrue(scene.charge_aura_rects)
            scene.update(action.duration-action.elapsed)
            self.assertEqual(scene._pose('enemy')[0], 'charged_hold')
            attack = self.start(scene, strike);scene.update(attack.duration)
            self.assertEqual(scene.model.enemy_recovery_states, {'enemy': 1.5})
            self.assertEqual(scene._pose('enemy')[0], recover)
            self.assertIn('50% more damage', scene.announcements.current['text'])
            resting = self.start(scene, recover);scene.update(resting.duration)
            self.assertEqual(scene._pose('enemy')[0], recover)
            self.start(scene, ordinary)
            self.assertFalse(scene.model.enemy_recovery_states)
            self.assertNotIn('50%', (scene.announcements.current or {}).get('text', ''))

    def test_authored_contacts_and_silhouettes_fit_accessibility_layouts(self):
        for enemy in ('embravyr', 'nivareth'):
            for text in (1, 1.5):
                scene, canvas, game = self.scene(enemy, text=text)
                for identifier in scene.model._enemy_states['enemy'].behavior['sequence']:
                    scene.model._start_action('enemy', identifier)
                    action = scene.model.current_action
                    if action.kind == 'recover':continue
                    for fraction in (0, .5, 1):
                        action.elapsed = action.impact_at*fraction
                        state, clock = scene._pose('enemy')
                        if fraction == 1:
                            contact = scene._enemy_art('enemy')['timing'][state]['contact_ms']
                            if contact is not None:self.assertAlmostEqual(clock, contact)
                        scene.draw(canvas, game.ui_surface)
                        body = scene.enemy_rects['enemy']
                        self.assertTrue(pygame.Rect(0, 35, 480, scene.panel_rect.top-35).contains(body),
                                        (enemy, text, identifier, body))

    def test_weakness_feedback_is_seekable_bounded_and_preserves_resources(self):
        for enemy, skill in (('embravyr', 'aqua_edge'), ('nivareth', 'flame_edge')):
            scene, _, _ = self.scene(enemy)
            scene._reactions = {'enemy': {'age': .16, 'action': skill, 'guarded': False, 'lethal': False}}
            layer = pygame.Surface((480, 320), pygame.SRCALPHA)
            positions = scene._positions();saved = self.resources(scene)
            clip = layer.get_clip()
            scene._draw_elemental_effects(layer, positions)
            first = pygame.image.tobytes(layer, 'RGBA')
            self.assertTrue(pygame.Rect(0, 35, 480, scene.panel_rect.top-35).contains(layer.get_bounding_rect()))
            self.assertEqual(layer.get_clip(), clip)
            scene._elapsed += 90;layer.fill((0, 0, 0, 0))
            scene._draw_elemental_effects(layer, positions)
            self.assertEqual(pygame.image.tobytes(layer, 'RGBA'), first)
            self.assertEqual(self.resources(scene), saved)


if __name__ == '__main__':unittest.main()
