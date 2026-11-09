"""Battle announcements and heavy-attack warnings follow real combat state."""
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
from inventory import Inventory
from ui_style import Painter, UIStyle
from test_random_enemy_groups import attributes, clear_gauges, group


class BattleFeedbackTests(unittest.TestCase):
    def setUp(self):
        pygame.display.init()
        pygame.font.init()
        self.game = SimpleNamespace(
            window=pygame.display.set_mode((960, 640)),
            ui_surface=pygame.Surface((960, 640)), audio=AudioSettings(),
            inventory=Inventory(), attributes=attributes())
        self.game.audio.set_effects(0)
        self.game.ui = UIStyle(self.game)
        self.game.to_canvas = lambda point: (point[0] / 2, point[1] / 2)
        self.canvas = pygame.Surface((480, 320))

    def tearDown(self):
        pygame.quit()

    def scene(self, species='ridgeback_tusker', *, guest=False, members=None):
        options = dict(learned_abilities=['aether_edge', 'aether_dart'],
                       weapon_equipped=True, rng=random.Random(7), initial_atb=False)
        if members is not None:
            model = group(members=members, **options)
        elif species in ('veylume', 'lithrusk', 'cave_bat'):
            model = BattleModel.from_bestiary(self.game.attributes, species, 3, **options)
        else:
            model = BattleModel(self.game.attributes, enemy_id=species,
                                guest_id='mira' if guest else None, **options)
        scene = BattleScene(self.game, model, battlefield=(
            'cave_hollow' if members is not None or species in ('veylume', 'lithrusk', 'cave_bat')
            else 'millrace' if species == 'ridgeback_tusker' else 'eldenmere'))
        clear_gauges(model)
        scene.update(0)
        scene.announcements.clear()
        self.draw(scene)
        return scene, model

    def draw(self, scene):
        scene.draw(self.canvas, self.game.ui_surface)

    def ready(self, scene, actor='player'):
        clear_gauges(scene.model)
        scene.model.combatant(actor).atb = 1
        scene.update(0)
        self.assertEqual(scene.model.ready_actor, actor)

    def enemy_turn(self, scene, actor='enemy', *, finish=True):
        clear_gauges(scene.model)
        scene.model.combatant(actor).atb = 1
        scene.update(0)
        action = scene.model.current_action
        self.assertIsNotNone(action)
        self.assertEqual(action.actor, actor)
        if finish:scene.update(action.duration)
        return action

    def hold_charge(self, scene, actor='enemy'):
        self.enemy_turn(scene, actor)
        action = self.enemy_turn(scene, actor)
        self.assertEqual(action.kind, 'prepare')
        self.assertIn(actor, scene.charging_enemies)
        return action

    def resources(self, model):
        return (model.phase, model.ready_actor,
                tuple((actor.identifier, actor.hp, actor.mp, actor.atb)
                      for actor in (*model.party, *model.enemies)),
                tuple((bot.identifier, bot.atb, bot.haste_turns) for bot in model.bots))

    def current_text(self, scene):
        current = scene.announcements.current
        return '' if current is None else current['text']

    def test_basic_party_and_autonomous_bot_attacks_do_not_fill_the_announcement_box(self):
        scene, model = self.scene(guest=True)
        for actor in ('player', 'mira'):
            with self.subTest(actor=actor):
                self.ready(scene, actor)
                scene.announcements.clear()
                self.assertTrue(model.choose_action('attack'))
                scene.update(0)
                self.assertIsNone(scene.announcements.current)
                scene.update(model.current_action.duration)
        clear_gauges(model)
        scene.announcements.clear()
        model.bot_for().atb = 1
        scene.update(0)
        self.assertEqual(model.current_action.actor, 'rivet')
        self.assertIsNone(scene.announcements.current)

    def test_enemy_basic_attacks_stay_quiet_but_named_specials_are_announced(self):
        for species in ('bat', 'ridgeback_tusker', 'cave_bat', 'lithrusk', 'veylume'):
            with self.subTest(species=species):
                scene, model = self.scene(species)
                self.enemy_turn(scene, finish=False)
                self.assertIsNone(scene.announcements.current)
                self.assertEqual(scene.charging_enemies, ())
        scene, model = self.scene('bat')
        self.enemy_turn(scene)
        special = self.enemy_turn(scene, finish=False)
        self.assertEqual(special.name, 'Wing Gust')
        self.assertIn('Wing Gust', self.current_text(scene))

    def test_named_player_skill_is_readable_after_its_animation_and_basic_attacks_do_not_replace_it(self):
        scene, model = self.scene()
        self.ready(scene)
        self.assertTrue(model.choose_action('aether_edge'))
        scene.update(0)
        self.assertIn('Aether Edge', self.current_text(scene))
        scene.update(model.current_action.duration)
        self.assertIn('Aether Edge', self.current_text(scene))
        self.ready(scene)
        self.assertTrue(model.choose_action('attack'))
        scene.update(0)
        self.assertIn('Aether Edge', self.current_text(scene))

    def test_skill_name_draws_immediately_after_a_menu_click_before_an_update(self):
        scene, model = self.scene()
        self.ready(scene)
        self.draw(scene)

        def click(point):
            physical = (point[0] * 2, point[1] * 2)
            for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
                scene.handle_event(pygame.event.Event(kind, button=1, pos=physical))

        click(scene.command_rects['skills'].center)
        self.draw(scene)
        before = scene._elapsed
        click(scene.command_rects['aether_edge'].center)
        self.assertEqual(model.current_action.action, 'aether_edge')
        labels = []
        original = Painter.text

        def record(painter, text, *args, **kwargs):
            labels.append(str(text))
            return original(painter, text, *args, **kwargs)

        with patch.object(Painter, 'text', record):self.draw(scene)
        self.assertEqual(scene._elapsed, before)
        self.assertTrue(any('Aether Edge' in label for label in labels))
        current = self.current_text(scene)
        scene.update(0)
        self.assertEqual(self.current_text(scene), current)

    def test_guard_resolution_reports_a_defensive_event_in_the_top_box(self):
        scene, model = self.scene()
        self.ready(scene)
        self.assertTrue(model.choose_action('guard'))
        scene.update(model.current_action.impact_at)
        self.assertTrue(model.player.guarded)
        self.assertIn('Guard', self.current_text(scene))

    def test_overclock_and_actual_haste_expiry_produce_special_event_feedback(self):
        scene, model = self.scene(guest=True)
        self.ready(scene, 'mira')
        self.assertTrue(model.choose_action('overclock'))
        scene.update(0)
        self.assertIn('Overclock', self.current_text(scene))
        scene.update(model.current_action.duration)
        bot = model.bot_for()
        bot.haste_turns = 1
        clear_gauges(model)
        scene.announcements.clear()
        bot.atb = 1
        scene.update(0)
        scene.update(model.current_action.duration)
        self.assertEqual(bot.haste_turns, 0)
        self.assertIsNotNone(scene.announcements.current)
        self.assertIn('Rivet', self.current_text(scene))

    def test_incoming_warning_precedes_queued_haste_feedback_after_overclock_title(self):
        scene, model = self.scene(guest=True)
        self.hold_charge(scene)
        self.ready(scene, 'mira')
        self.assertTrue(model.choose_action('overclock'))
        scene.update(0)
        self.assertIn('Overclock', self.current_text(scene))
        scene.update(model.current_action.duration)
        self.assertGreater(model.bot_for().haste_turns, 0)
        # A normal player decision freezes ATB while announcement time can
        # advance. The queued Haste notice must not conceal the armed charge.
        self.ready(scene)
        current = scene.announcements.current
        self.assertEqual(current['kind'], 'ability')
        scene.update(current['duration'] - current['age'] + .01)
        incoming = scene.announcements.current
        self.assertEqual(incoming['kind'], 'warning')
        self.assertEqual(incoming['actor'], 'enemy')
        self.assertEqual(incoming['action'], 'tusker_charge')
        self.assertIn('Bankbreaker Charge', incoming['text'])
        self.assertIn(model.combatant(incoming['target']).name, incoming['text'])

    def test_authored_emote_is_presented_without_spending_resources_or_a_turn(self):
        scene, model = self.scene()
        self.ready(scene)
        before = deepcopy(self.resources(model))
        scene.announce('The cavern shudders!', actor='enemy')
        self.assertIn('The cavern shudders!', self.current_text(scene))
        self.draw(scene)
        scene.update(.5)
        self.assertEqual(self.resources(model), before)

    def test_tusker_aura_starts_during_preparation_and_survives_until_the_heavy_hit_lands(self):
        scene, model = self.scene()
        self.enemy_turn(scene)
        preparation = self.enemy_turn(scene, finish=False)
        self.assertEqual(preparation.kind, 'prepare')
        self.assertIn('enemy', scene.charging_enemies)
        self.draw(scene)
        self.assertIn('enemy', scene.charge_aura_rects)
        scene.update(preparation.duration)
        self.ready(scene)
        warning = next(row for row in scene.announcements.warnings if row['actor'] == 'enemy')
        self.assertEqual(warning['action'], 'tusker_charge')
        self.assertEqual(warning['target'], model.telegraphed_target)
        self.assertIn('Bankbreaker Charge', warning['text'])
        self.assertIn(model.combatant(warning['target']).name, warning['text'])
        self.assertTrue(model.choose_action('guard'))
        scene.update(model.current_action.duration)
        release = self.enemy_turn(scene, finish=False)
        self.assertEqual(release.action, 'tusker_charge')
        self.assertIn('enemy', scene.charging_enemies)
        scene.update(release.impact_at)
        self.draw(scene)
        self.assertNotIn('enemy', scene.charging_enemies)
        self.assertNotIn('enemy', scene.charge_aura_rects)

    def test_multiple_prepared_enemies_have_independent_warnings_and_auras(self):
        members = [{'enemy_id': 'veylume', 'level': 3},
                   {'enemy_id': 'veylume', 'level': 3},
                   {'enemy_id': 'cave_bat', 'level': 3}]
        scene, model = self.scene(members=members)
        self.hold_charge(scene, 'enemy')
        self.hold_charge(scene, 'enemy_2')
        self.draw(scene)
        self.assertEqual(set(scene.charging_enemies), {'enemy', 'enemy_2'})
        self.assertEqual(set(scene.charge_aura_rects), {'enemy', 'enemy_2'})
        warnings = {row['actor']: row for row in scene.announcements.warnings}
        self.assertEqual(set(warnings), {'enemy', 'enemy_2'})
        self.assertIn('Veylume A', warnings['enemy']['text'])
        self.assertIn('Veylume B', warnings['enemy_2']['text'])
        release = self.enemy_turn(scene, 'enemy', finish=False)
        scene.update(release.impact_at)
        self.draw(scene)
        self.assertNotIn('enemy', scene.charge_aura_rects)
        self.assertIn('enemy_2', scene.charge_aura_rects)
        model.combatant('enemy_2').hp = 0
        scene.update(0)
        self.draw(scene)
        self.assertEqual(scene.charging_enemies, ())
        self.assertEqual(scene.announcements.warnings, ())

    def test_veylume_warning_retargets_after_the_original_party_member_is_ko(self):
        members = [{'enemy_id': 'veylume', 'level': 3},
                   {'enemy_id': 'cave_bat', 'level': 3}]
        scene, model = self.scene(members=members)
        self.hold_charge(scene)
        old_target = model.enemy_telegraphs['enemy']
        model.combatant(old_target).hp = 0
        scene.update(0)
        warnings = scene.announcements.warnings
        self.assertEqual(len(warnings), 1)
        self.assertNotEqual(warnings[0]['target'], old_target)
        self.assertGreater(model.combatant(warnings[0]['target']).hp, 0)
        self.assertIn(model.combatant(warnings[0]['target']).name, warnings[0]['text'])

    def test_other_named_abilities_do_not_clear_an_enemy_waiting_for_its_next_turn(self):
        scene, model = self.scene('veylume')
        self.hold_charge(scene)
        self.ready(scene)
        self.assertTrue(model.choose_action('aether_edge'))
        scene.update(0)
        self.assertIn('Aether Edge', self.current_text(scene))
        self.assertEqual(scene.charging_enemies, ('enemy',))
        self.assertEqual(scene.announcements.warnings[0]['action'], 'veylume_veinflash')

    def test_targeting_finger_and_floor_ring_coexist_with_a_charged_enemy(self):
        scene, model = self.scene('veylume')
        self.hold_charge(scene)
        self.ready(scene)
        self.draw(scene)
        self.assertEqual(set(scene.target_marker_rects), {'ring', 'finger'})
        self.assertIn('enemy', scene.charge_aura_rects)
        self.assertTrue(scene.enemy_rects['enemy'].width)

    def test_pause_and_focus_loss_freeze_message_and_aura_clocks(self):
        scene, model = self.scene('veylume')
        self.hold_charge(scene)
        self.ready(scene)
        scene.announcements.clear()
        scene.announce('Hold your ground.', actor='player')
        for focus in (True, False):
            with self.subTest(focused=focus):
                scene.focused = focus
                scene.paused = True
                self.draw(scene)
                before = (scene._elapsed, deepcopy(scene.announcements.current),
                          pygame.image.tobytes(self.canvas, 'RGB'))
                scene.update(10)
                self.draw(scene)
                self.assertEqual((scene._elapsed, scene.announcements.current,
                                  pygame.image.tobytes(self.canvas, 'RGB')), before)

    def test_reduced_motion_keeps_a_static_visible_red_warning(self):
        scene, model = self.scene('veylume')
        self.hold_charge(scene)
        self.ready(scene)
        self.game.audio.set_reduced_motion(True)
        self.draw(scene)
        region = scene.charge_aura_rects['enemy']
        self.assertTrue(region.width * region.height)
        first = pygame.image.tobytes(self.canvas.subsurface(region), 'RGB')
        scene.update(.8)
        self.draw(scene)
        self.assertEqual(scene.charge_aura_rects['enemy'], region)
        self.assertEqual(pygame.image.tobytes(self.canvas.subsurface(region), 'RGB'), first)

    def test_victory_and_defeat_clear_charging_feedback(self):
        for outcome in ('victory', 'defeat', 'fled'):
            with self.subTest(outcome=outcome):
                scene, model = self.scene('veylume')
                self.hold_charge(scene)
                model._result(outcome)
                scene.update(0)
                self.draw(scene)
                self.assertEqual(scene.charging_enemies, ())
                self.assertEqual(scene.announcements.warnings, ())
                self.assertEqual(scene.charge_aura_rects, {})

    def test_top_announcement_and_charging_effects_fit_normal_and_large_text(self):
        members = [{'enemy_id': 'veylume', 'level': 3},
                   {'enemy_id': 'veylume', 'level': 3},
                   {'enemy_id': 'cave_bat', 'level': 3},
                   {'enemy_id': 'lithrusk', 'level': 3}]
        for dimensions in ((480, 320), (960, 640)):
            self.game.window = pygame.display.set_mode(dimensions)
            self.game.ui_surface = pygame.Surface(dimensions)
            for text_scale in (1., 1.5):
                with self.subTest(size=dimensions, text=text_scale):
                    self.game.audio.set_text_scale(text_scale)
                    scene, model = self.scene(members=members)
                    self.hold_charge(scene)
                    self.ready(scene)
                    self.draw(scene)
                    panel = scene.announcement_rect
                    self.assertTrue(pygame.Rect(0, 0, 480, 35).contains(panel))
                    for row in scene.enemy_rows.values():
                        self.assertFalse(panel.colliderect(row['row']))
                    field = pygame.Rect(0, 35, 480, scene.panel_rect.top - 35)
                    for region in scene.charge_aura_rects.values():
                        self.assertTrue(field.contains(region), (field, region))

    def test_long_emote_pages_remain_inside_the_top_box_at_large_text(self):
        self.game.window = pygame.display.set_mode((480, 320))
        self.game.ui_surface = pygame.Surface((480, 320))
        self.game.audio.set_text_scale(1.5)
        scene, model = self.scene()
        self.ready(scene)
        text = ('Crimson sparks climb the chamber walls while radiant crystals '
                'answer the gathering storm beneath the ancient sanctuary.')
        scene.announce(text, actor='enemy')
        duration = scene.announcements.current['duration']
        words = set()
        original = Painter.text

        def record(painter, label, *args, **kwargs):
            rect = original(painter, label, *args, **kwargs)
            panel = painter.area(scene.announcement_rect)
            if rect.height and rect.width and panel.collidepoint(rect.center):
                self.assertTrue(panel.contains(rect), (str(label), rect, panel))
                words.update(str(label).split())
            return rect

        with patch.object(Painter, 'text', record):
            for _ in range(16):
                self.draw(scene)
                scene.update(duration / 16)
        self.assertTrue(set(text.split()).issubset(words), (set(text.split()) - words, words))

    def test_large_text_charge_warning_keeps_its_arrow_with_the_target(self):
        self.game.window = pygame.display.set_mode((480, 320))
        self.game.ui_surface = pygame.Surface((480, 320))
        self.game.audio.set_text_scale(1.5)
        scene, model = self.scene()
        self.hold_charge(scene)
        self.ready(scene)
        scene.announcements.clear()
        warning = scene.announcements.current
        self.assertEqual(warning['kind'], 'warning')
        self.assertEqual(warning['target'], 'player')
        labels = []
        original = Painter.text

        def record(painter, text, *args, **kwargs):
            rect = original(painter, text, *args, **kwargs)
            panel = painter.area(scene.announcement_rect)
            if rect.width and rect.height and panel.collidepoint(rect.center):
                self.assertTrue(panel.contains(rect), (str(text), rect, panel))
                self.assertFalse(str(text).rstrip().endswith('→'), str(text))
                labels.append(str(text))
            return rect

        with patch.object(Painter, 'text', record):
            for _ in range(20):
                self.draw(scene)
                scene.update(warning['duration'] / 20)
        self.assertTrue(any('→ Caelan' in text for text in labels), labels)
        self.assertTrue(set(warning['text'].split()).issubset(
            {word for text in labels for word in text.split()}), labels)


if __name__ == '__main__':
    unittest.main()
