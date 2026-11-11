"""Independent enemies, actual target commands and four-enemy battle rendering."""
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
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
from cave_battlefield import CAVE_BATTLEFIELDS, CaveBattlefield
from bestiary import build_enemy
from character_attributes import CharacterAttributes
from inventory import Inventory
from leveling import character_stats
from ui_style import UIStyle


MEMBERS = [
    {'enemy_id': 'cave_bat', 'level': 3},
    {'enemy_id': 'cave_bat', 'level': 3},
    {'enemy_id': 'lithrusk', 'level': 3},
    {'enemy_id': 'veylume', 'level': 4},
]


def attributes():
    source = CharacterAttributes()
    saved = source.to_dict()
    saved['attributes'] = character_stats('caelan', 3)
    saved['attributes']['hp'] = 9999
    saved['current_hp'] = 9999
    saved['current_mp'] = saved['attributes']['mp']
    assert source.restore(saved)
    return source


def profiles():
    rows = []
    for identifier, name in (('player', 'Caelan'), ('mira', 'Mira'), ('lucan', 'Lucan')):
        values = character_stats('caelan' if identifier == 'player' else identifier, 3)
        values['hp'] = 9999
        rows.append({'identifier': identifier, 'name': name, 'attributes': values,
                     'hp': 9999, 'mp': values['mp'],
                     'attack': 'bolt_shot' if identifier == 'mira' else 'attack'})
    return rows


def group(members=None, **options):
    options.setdefault('party_members', profiles())
    options.setdefault('rng', random.Random(7))
    options.setdefault('initial_atb', False)
    return BattleModel.from_bestiary_group(attributes(), deepcopy(MEMBERS if members is None else members),
                                          **options)


def clear_gauges(model):
    for actor in (*model.party, *model.enemies):
        actor.atb = 0


class RandomEnemyGroupTests(unittest.TestCase):
    def enemy_turn(self, model, identifier):
        clear_gauges(model)
        model.combatant(identifier).atb = 1
        model.update(0)
        self.assertIsNotNone(model.current_action)
        self.assertEqual(model.current_action.actor, identifier)
        action = model.current_action
        model.update(action.duration)
        self.assertTrue(action.resolved)
        return action

    def test_initial_atb_is_seeded_independent_and_limited_to_half_full(self):
        seen = set()
        for seed in range(16):
            first = group(initial_atb=True, initial_atb_seed=seed, rng=random.Random(1))
            second = group(initial_atb=True, initial_atb_seed=seed, rng=random.Random(987))
            gauges = tuple(actor.atb for actor in (*first.party, *first.enemies))
            self.assertTrue(all(0 <= value <= .5 for value in gauges), gauges)
            self.assertGreater(len(set(gauges)), 1, 'Actors must not share one initial roll')
            self.assertEqual(gauges, tuple(actor.atb for actor in
                                          (*second.party, *second.enemies)))
            seen.add(gauges)
        self.assertGreater(len(seen), 12)
        self.assertTrue(all(actor.atb == 0 for actor in (*group().party, *group().enemies)))

    def test_groups_have_distinct_combatants_and_preserve_species_stats_and_total_xp(self):
        authored = deepcopy(MEMBERS)
        model = group(authored)
        self.assertEqual([enemy.identifier for enemy in model.enemies],
                         ['enemy', 'enemy_2', 'enemy_3', 'enemy_4'])
        self.assertIs(model.enemy, model.enemies[0])
        expected_xp = 0
        for actor, member in zip(model.enemies, authored):
            resolved = build_enemy(member['enemy_id'], member['level'])
            self.assertEqual(actor.attributes, resolved['combat']['attributes'])
            self.assertEqual(model.enemy_sprite_id_for(actor.identifier), resolved['presentation']['sprite_id'])
            self.assertIs(model.combatant(actor.identifier), actor)
            expected_xp += resolved['xp_reward']
        self.assertEqual(model.enemy_xp_reward, expected_xp)
        self.assertEqual(model.encounter_rewards, {'drops': {}})
        model.enemies[0].attributes['str'] = 999
        model.enemy_records['enemy']['combat']['attributes']['hp'] = 1
        self.assertEqual(authored, MEMBERS)
        self.assertNotEqual(model.enemies[1].value('str'), 999)

    def test_formation_limits_levels_and_target_ids_are_validated(self):
        for members in ([], MEMBERS+[MEMBERS[0]], [{'enemy_id': 'cave_bat', 'level': 4}],
                        [{'enemy_id': 'missing', 'level': 3}]):
            with self.subTest(members=members), self.assertRaises((ValueError, TypeError)):
                group(members)
        model = group()
        self.assertFalse(model.select_target('mira'))
        self.assertFalse(model.select_target('missing'))
        model.combatant('enemy_2').hp = 0
        self.assertFalse(model.select_target('enemy_2'))
        self.assertTrue(model.select_target('enemy_3'))
        self.assertEqual(model.selected_target, 'enemy_3')

    def test_each_enemy_owns_its_action_sequence_and_mp(self):
        model = group()
        first, second, moth = model.enemies[0], model.enemies[1], model.enemies[3]
        self.assertEqual(self.enemy_turn(model, second.identifier).action, 'cave_bat_bite')
        self.assertEqual(self.enemy_turn(model, first.identifier).action, 'cave_bat_bite')
        before = first.mp, second.mp, moth.mp
        self.assertEqual(self.enemy_turn(model, second.identifier).action, 'cave_bat_wing_gust')
        self.assertEqual((first.mp, second.mp, moth.mp), (before[0], before[1]-2, before[2]))
        self.assertEqual(self.enemy_turn(model, first.identifier).action, 'cave_bat_wing_gust')
        self.assertEqual(self.enemy_turn(model, moth.identifier).action, 'veylume_static_spark')

    def test_two_casters_hold_independent_preparations_and_retarget_defeated_characters(self):
        model = group([{'enemy_id': 'veylume', 'level': 3},
                       {'enemy_id': 'veylume', 'level': 4}])
        for enemy in model.enemies:
            self.enemy_turn(model, enemy.identifier)
            self.assertEqual(self.enemy_turn(model, enemy.identifier).action, 'veylume_gather_charge')
        locks = dict(model.enemy_telegraphs)
        self.assertEqual(set(locks), {'enemy', 'enemy_2'})
        self.assertEqual(set(model.enemy_prepared_actions), set(locks))
        target = locks['enemy']
        model.combatant(target).hp = 0
        model.update(0)
        self.assertNotEqual(model.enemy_telegraphs['enemy'], target)
        self.assertGreater(model.combatant(model.enemy_telegraphs['enemy']).hp, 0)
        other_mp = model.combatant('enemy_2').mp
        flash = self.enemy_turn(model, 'enemy')
        self.assertEqual(flash.action, 'veylume_veinflash')
        self.assertNotEqual(flash.target, target)
        self.assertEqual(model.combatant('enemy_2').mp, other_mp)
        self.assertNotIn('enemy', model.enemy_telegraphs)
        self.assertIn('enemy_2', model.enemy_telegraphs)
        self.assertEqual(self.enemy_turn(model, 'enemy_2').action, 'veylume_veinflash')
        self.assertFalse(model.enemy_telegraphs)

    def test_attacks_hit_selected_targets_and_victory_waits_for_every_enemy(self):
        model = group()
        for identifier in ('enemy_3', 'enemy', 'enemy_4', 'enemy_2'):
            clear_gauges(model)
            model.player.atb = 1
            model.update(0)
            self.assertTrue(model.waiting_for_player)
            self.assertTrue(model.select_target(identifier))
            target = model.combatant(identifier)
            target.hp = 1
            others = {enemy.identifier: enemy.hp for enemy in model.enemies
                      if enemy.identifier != identifier}
            self.assertTrue(model.choose_action('attack', target_id=identifier))
            self.assertEqual(model.current_action.target, identifier)
            model.update(model.current_action.duration)
            self.assertEqual(target.hp, 0)
            self.assertEqual({enemy.identifier: enemy.hp for enemy in model.enemies
                              if enemy.identifier != identifier}, others)
            self.assertEqual(model.phase == 'victory', not model.living_enemies)
        self.assertEqual(model.phase, 'victory')

    def test_defeated_enemies_never_receive_turns_even_with_a_full_gauge(self):
        model = group()
        clear_gauges(model)
        model.enemy.hp = 0
        model.enemy.atb = 1
        model.combatant('enemy_2').atb = 1
        model.update(0)
        self.assertEqual(model.current_action.actor, 'enemy_2')
        self.assertNotIn(model.enemy, model.living_enemies)

    def test_miras_shot_uses_selected_enemy_and_retargets_after_its_defeat(self):
        model = group( initial_atb=True, initial_atb_seed=9)
        mira = model.combatant('mira')
        self.assertTrue(0 <= mira.atb <= .5)
        self.assertIn(mira.identifier, model.initial_atb_values)
        self.assertEqual(set(model.initial_atb_values), {a.identifier for a in (*model.party, *model.enemies)})
        target = model.combatant('enemy_4');target.hp = 1
        self.assertTrue(model.select_target(target.identifier))
        clear_gauges(model);mira.atb = 1
        model.update(0)
        self.assertTrue(model.choose_action('attack'))
        self.assertEqual((model.current_action.actor, model.current_action.target),
                         ('mira', target.identifier))
        model.update(model.current_action.duration)
        self.assertEqual(target.hp, 0)
        self.assertNotEqual(model.phase, 'victory')
        clear_gauges(model);mira.atb = 1
        model.update(0)
        self.assertTrue(model.choose_action('attack'))
        self.assertIn(model.current_action.target,
                      [enemy.identifier for enemy in model.living_enemies])
        self.assertFalse(hasattr(model, 'bots'))

    def test_spellblade_damage_and_guard_apply_to_the_actual_group_target(self):
        model = group(weapon_equipped=True, learned_abilities=('aether_edge',))
        clear_gauges(model)
        model.player.atb = 1
        model.update(0)
        before = {enemy.identifier: enemy.hp for enemy in model.enemies}
        mp = model.player.mp
        self.assertTrue(model.choose_action('aether_edge', target_id='enemy_4'))
        self.assertEqual(model.current_action.target, 'enemy_4')
        model.update(model.current_action.duration)
        self.assertEqual(model.player.mp, mp-4)
        self.assertLess(model.combatant('enemy_4').hp, before['enemy_4'])
        self.assertTrue(all(enemy.hp == before[enemy.identifier] for enemy in model.enemies[:3]))

        baseline = group()
        ordinary = self.enemy_turn(baseline, 'enemy_4')
        guarded = group()
        for member in guarded.party:
            clear_gauges(guarded)
            member.atb = 1
            guarded.update(0)
            self.assertTrue(guarded.choose_action('guard', actor_id=member.identifier))
            guarded.update(guarded.current_action.duration)
        hit = self.enemy_turn(guarded, 'enemy_4')
        self.assertEqual(hit.target, ordinary.target)
        self.assertEqual(hit.damage, ordinary.damage//2)
        self.assertFalse(guarded.combatant(hit.target).guarded)
        self.assertTrue(all(member.guarded for member in guarded.party
                            if member.identifier != hit.target))


class RandomEnemyGroupSceneTests(unittest.TestCase):
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

    def draw(self, scene):
        scene.draw(self.canvas, self.game.ui_surface)

    def test_four_distinct_sprites_labels_and_hp_rows_fit_both_native_and_large_text(self):
        model = group()
        scene = BattleScene(self.game, model)
        for dimensions in ((480, 320), (960, 640)):
            self.game.window = pygame.display.set_mode(dimensions)
            self.game.ui_surface = pygame.Surface(dimensions)
            for text_scale in (1, 1.5):
                self.game.audio.set_text_scale(text_scale)
                self.draw(scene)
                self.assertEqual(set(scene.enemy_rows), {enemy.identifier for enemy in model.enemies})
                self.assertEqual(set(scene.enemy_rects), set(scene.enemy_rows))
                for identifier, rect in scene.enemy_rects.items():
                    with self.subTest(dimensions=dimensions, text=text_scale, actor=identifier):
                        self.assertTrue(pygame.Rect(0, 35, 480, scene.panel_rect.top-35).contains(rect), rect)
                        self.assertTrue(pygame.Rect(0, 0, 480, scene.panel_rect.top).contains(
                            scene.enemy_rows[identifier]['row']))
                        self.assertFalse(rect.colliderect(scene.commands_panel))
                        for status in scene.enemy_rows.values():
                            self.assertFalse(rect.colliderect(status['name']))
                            self.assertFalse(rect.colliderect(status['hp']))
                for identifier in scene.enemy_rows:
                    self.assertTrue(model.select_target(identifier))
                    self.draw(scene)

    def test_keyboard_and_mouse_target_confirmation_use_actual_enemy_ids(self):
        model = group()
        scene = BattleScene(self.game, model)
        clear_gauges(model)
        model.player.atb = 1
        scene.update(0)
        self.draw(scene)
        before = tuple(enemy.hp for enemy in model.enemies)
        scene.selected = scene._command_actions().index('attack')
        scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, repeat=False))
        self.assertTrue(model.waiting_for_player)
        self.assertEqual(scene._target_command, 'attack')
        scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT, repeat=False))
        selected = model.selected_target
        self.assertNotEqual(selected, 'enemy')
        scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, repeat=False))
        self.assertEqual(model.current_action.target, selected)
        scene.update(model.current_action.duration)
        self.assertLess(model.combatant(selected).hp, before[1])
        clear_gauges(model)
        model.player.atb = 1
        scene.update(0)
        self.draw(scene)
        scene.selected = scene._command_actions().index('attack')
        scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, repeat=False))
        point = scene.enemy_rows['enemy_4']['row'].center
        physical = (point[0]*2, point[1]*2)
        scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=physical))
        scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=physical))
        self.assertEqual(model.current_action.target, 'enemy_4')

    def test_all_cave_battlefields_animate_on_the_scene_clock_and_hold_for_reduced_motion(self):
        bank = []
        for identifier in sorted(CAVE_BATTLEFIELDS):
            scene = BattleScene(self.game, group(), battlefield=identifier)
            self.draw(scene)
            field = scene._cave_field
            self.assertIsInstance(field, CaveBattlefield)
            self.assertEqual(scene.battlefield, identifier)
            self.assertEqual(field.data['source_scene'], 'sanctuary_cave')
            self.assertEqual(field.data['size'], [480, 320])
            self.assertTrue(field.data['source_rooms'])
            self.assertGreater(len(field.frames), 1)
            first = pygame.image.tobytes(field.frame(0), 'RGB')
            crest = pygame.image.tobytes(field.frame(3000), 'RGB')
            self.assertNotEqual(first, crest)
            bank.append(first)
            with patch('pygame.image.load', side_effect=AssertionError('Animation must use cached frames')):
                self.assertEqual(first, pygame.image.tobytes(field.frame(6000), 'RGB'))
                held = pygame.image.tobytes(field.frame(0, True), 'RGB')
                self.assertEqual(held, pygame.image.tobytes(field.frame(19321, True), 'RGB'))
                scene.paused = True
                clock = scene._elapsed
                scene.update(5)
                self.assertEqual(scene._elapsed, clock)
                scene.paused = False
                self.game.audio.set_reduced_motion(True)
                with patch.object(field, 'draw', wraps=field.draw) as rendered:
                    self.draw(scene)
                    self.assertTrue(rendered.call_args.args[2])
                    scene._elapsed += 1
                    self.draw(scene)
                    self.assertEqual(rendered.call_args.args[1], scene._elapsed*1000)
                    self.assertTrue(rendered.call_args.args[2])
                self.game.audio.set_reduced_motion(False)
        self.assertEqual(len(set(bank)), len(CAVE_BATTLEFIELDS),
                         'Every authored cave location needs distinct scenery')

    def test_cave_battlefields_retain_real_location_and_native_asset_provenance(self):
        root = Path(__file__).resolve().parents[1]
        cave = json.loads((root/'assets/maps/sanctuary_cave/map.json').read_text())['cave']
        rooms = {room['id'] for room in cave['rooms']}
        for identifier in CAVE_BATTLEFIELDS:
            data = CaveBattlefield(identifier).data
            self.assertTrue(set(data['source_rooms']) <= rooms)
            self.assertTrue(data['animation']['pulse'])
            self.assertGreater(data['animation']['microcrystal_count'], 0)
            colors = set(data['animation']['crystal_colors'])
            self.assertTrue(colors)
            self.assertLessEqual(colors, {'red', 'blue', 'green', 'white', 'orange', 'purple'})
            sources = data['build']['source_sha256']
            self.assertTrue(any(name.startswith('assets/terrain/limestone_cave/') for name in sources))
            for name, expected in sources.items():
                self.assertEqual(sha256((root/name).read_bytes()).hexdigest(), expected, name)


if __name__ == '__main__':
    unittest.main()
