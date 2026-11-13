"""One-time optional Aether guardians through production Game entry and saves.

Earlier quests and the Aqua discovery are explicit fixtures. Encounter choices,
loading, focus awards, acquisition prose and Continue use the live owners.
"""
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

import pygame

from elemental_bosses import REGISTRY, definition, valid_ticket
from leveling import total_xp_for_level
from main import Game
from post_battle import battle_reward_definition, valid_pending_snapshot
from sanctuary_cave import RESERVE_ENTRY_APPROACH
from tools.capture_mq03_emergency import Driver
from test_mill_battle_gameplay import click, finish_spoils_presentation, key, wait_for_spoils


class ElementalCaveGameplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory(prefix='elemental-story-') as directory:
            driver = Driver(directory)
            driver.meal();driver.attack_report();driver.departure()
            driver.rejoin_mira();driver.arrive()
            game = driver.game
            # Arrival now owns the rescue choreography and Lucan's recruitment.
            for _ in range(2400):
                if game.sanctuary_arrival.completed:break
                driver.tick(.2)
                if game.sanctuary_arrival.dialogue:key(game, pygame.K_SPACE)
            assert game.sanctuary_arrival.completed
            if not game.character_abilities.has_weapon():
                assert game.character_abilities.acquire_weapon('caelan', 'caelan_gearblade')
            game.character_abilities.learn_ability('caelan', 'aqua_edge')
            assert game.cave_lesson.restore({'version': 1, 'resonance_seen': True,
                                              'battle_cleared': True, 'deferred': False})
            # Public EXP and recovery APIs establish a labelled rested level-four
            # permanent pair. The recruited level-five guest retains his level.
            active = tuple(key for key in game.party.active_ids if key != 'lucan')
            end_hp = {identifier: game.party.characters[identifier].current_hp for identifier in active}
            assert game.character_progression.apply(game.character_progression.preview(
                total_xp_for_level(4), active, end_hp))
            for identifier in active:
                assert game.character_progression[identifier].level == 4
                game.party.characters[identifier].recover()
            game.player.position.update(RESERVE_ENTRY_APPROACH)
            game.opening_fade = game.transfer_cooldown = 0
            assert game.sanctuary_cave.interact()
            game.opening_fade = game.transfer_cooldown = 0
            assert game.save_progress()
            cls.journey = json.loads(driver.save.read_text())
        pygame.quit()

    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix='elemental-gameplay-')
        self.addCleanup(directory.cleanup)
        self.addCleanup(pygame.quit)
        self.directory = Path(directory.name)
        self.path = self.directory/'journey.json'
        self.path.write_text(json.dumps(self.journey))
        self.game = self.load()

    def load(self):
        game = Game(window_size=(960, 640), fullscreen=False, start_on_title=True,
                    save_path=self.path, settings_path=self.directory/'settings.json')
        game.audio.set_music(0);game.audio.set_effects(0)
        self.assertTrue(game.has_saved_journey, game.save_error)
        self.assertTrue(game.begin_journey(True), game.save_error)
        game.opening_fade = game.transfer_cooldown = 0
        pygame.event.clear()
        return game

    def resources(self, game=None):
        game = game or self.game
        return {identifier: {'hp': game.party.characters[identifier].current_hp,
                             'mp': game.party.characters[identifier].current_mp}
                for identifier in game.party.active_ids}

    def durable(self):
        game = self.game
        return deepcopy({'party': game.party.to_dict(), 'levels': game.character_progression.to_dict(),
            'abilities': game.character_abilities.to_dict(), 'inventory': game.inventory.to_dict(),
            'rewards': game.battle_rewards.to_dict(), 'elementals': game.elemental_bosses.to_dict()})

    def story(self):
        game = self.game
        return deepcopy({'quests': game.quests.to_dict(), 'regent': game.regent_quest.to_dict(),
            'active': list(game.party.active_ids), 'members': game.party.members,
            'event': game.party.current_event_id, 'treasures': game.sanctuary_cave.to_dict(),
            'random': game.cave_random_encounters.to_dict(), 'vespermaw': game.sanctuary_boss.to_dict()})

    def position(self, enemy_id):
        game = self.game
        entry = definition(enemy_id)
        self.assertTrue(game.world.can_stand(entry['approach']), entry)
        game.player.position.update(entry['approach'])
        game.player.facing = 'back'
        game.player.moving = game.player.running = False
        game.party_travel.reset();game.camera.reset()
        return entry

    def choose(self, action):
        game = self.game
        for _ in range(80):
            if game.social.choosing:break
            self.assertTrue(game.social.active, game.social.script_identifier)
            key(game, pygame.K_SPACE)
        self.assertTrue(game.social.choosing)
        index = next(index for index, option in enumerate(game.social.choice_options)
                     if option['action'] == action)
        game.draw();click(game, game.social.choice_rects[index].center)

    def offer(self, enemy_id):
        self.position(enemy_id)
        self.assertTrue(self.game.elemental_bosses.interact())
        self.assertEqual(self.game.social.script_identifier, 'elemental_boss_offer_'+enemy_id)

    def start(self, enemy_id, *, seed=7):
        self.offer(enemy_id)
        with patch('elemental_bosses.random.SystemRandom') as source:
            source.return_value.randrange.return_value = seed
            self.choose('enter')
        self.assertTrue(self.game.combat.active)
        self.assertEqual(self.game.combat.kind, 'elemental_boss')
        ticket = self.game.elemental_bosses.pending
        self.assertTrue(valid_ticket(ticket))
        self.assertEqual(ticket['enemy_id'], enemy_id)
        self.assertEqual(ticket['level'], 5)
        self.assertEqual(ticket['receipt'], 'boss:'+enemy_id)
        self.assertEqual(json.loads(self.path.read_text())['elemental_bosses']['pending'], ticket)
        return ticket

    def enter_battle(self, game=None):
        game = game or self.game
        owner = game.combat
        for _ in range(100):
            if owner.entry_phase == 'loading':break
            game.update(.05, (0, 0), False)
        self.assertEqual(owner.entry_phase, 'loading')
        self.assertIsNone(owner.model)
        game.update(.05, (0, 0), False)
        self.assertIsNone(owner.model, 'Loading must be drawn before combat construction')
        game.draw();game.update(.01, (0, 0), False)
        self.assertIsNotNone(owner.model, getattr(owner.entry, 'error', ''))
        for _ in range(40):
            if not owner.transitioning:return owner.model
            game.update(.05, (0, 0), False)
        self.fail('The authored elemental battle reveal did not finish')

    def test_previous_curve_pending_guardian_spoils_preserve_original_exp(self):
        from bestiary import build_enemy
        self.start('embravyr');self.enter_battle()
        before = {key: self.game.character_progression[key].total_xp for key in self.game.party.active_ids}
        def previous_enemy(*args, **kwargs):
            result = build_enemy(*args, **kwargs)
            result['xp_reward'] = 940
            return result
        with patch('post_battle.build_enemy', side_effect=previous_enemy):self.victory()
        self.assertEqual(self.game.combat.snapshot()['progression']['amount'], 940)
        self.game = self.load();self.award()
        for key, total in before.items():
            self.assertEqual(self.game.character_progression[key].total_xp,
                             total+(0 if key == 'lucan' else 940))

    def victory(self, *, caelan_ko=False):
        owner = self.game.combat
        if caelan_ko:owner.model.player.hp = 0
        owner.model.enemy.hp = 0
        owner.model._result('victory')
        self.assertTrue(owner._begin_victory())
        self.assertEqual(owner.snapshot()['stage'], 'pending')
        self.assertTrue(valid_pending_snapshot(owner.snapshot(), json.loads(self.path.read_text())))
        return owner

    def award(self):
        spoils = wait_for_spoils(self.game)
        self.assertTrue(spoils.awarded, spoils.result_error)
        self.assertFalse(spoils.result_error)
        return spoils

    def finish_spoils(self):
        game = self.game
        self.award();finish_spoils_presentation(game)
        game.draw();click(game, game.combat.spoils.continue_rect.center)
        game.update(0, (0, 0), False)
        self.assertFalse(game.combat.active)

    def read_acquisition(self, *, expected=None, complete=True):
        game = self.game
        pages = []
        for _ in range(200):
            if not game.social.active:game.update(.05, (0, 0), False)
            if game.social.active:
                self.assertTrue(game.social.script_identifier.startswith('elemental_focus_acquisition_'))
                if expected:self.assertEqual(game.social.script_identifier, 'elemental_focus_acquisition_'+expected)
                pages.append(' '.join(game.social.page['lines']))
                if not complete:return pages
                key(game, pygame.K_SPACE)
            elif not any(state['pending_acquisition'] for state in game.elemental_bosses.bosses.values()):
                return pages
        self.fail('The acquired focus presentation did not complete')

    def beat_and_collect(self, enemy_id):
        ticket = self.start(enemy_id)
        self.enter_battle();self.victory();self.finish_spoils()
        pages = self.read_acquisition(expected=enemy_id)
        return ticket, pages

    def play_actual_battle(self, enemy_id):
        game, model, scene = self.game, self.game.combat.model, self.game.combat.scene
        trace = []
        original = model.drain_events
        def observe():
            batch = original();trace.extend(deepcopy(batch));return batch
        with patch.object(model, 'drain_events', side_effect=observe):
            for _ in range(16000):
                if scene.tutorial_active:key(game, pygame.K_SPACE)
                elif model.ended:break
                elif model.waiting_for_player:
                    marked = model.telegraphed_target
                    if marked in model.ready_members and model.ready_actor != marked:
                        game.draw();click(game, scene.party_rows[marked]['row'].center)
                    actor = model.ready_actor
                    if actor == marked:command = 'guard'
                    elif actor != 'player':
                        command = 'attack'
                    elif enemy_id == 'embravyr':
                        command = 'ice_edge' if 'ice_edge' in model.skill_actions() else 'aqua_edge'
                    elif 'flame_edge' in model.skill_actions():command = 'flame_edge'
                    else:command = 'attack'
                    wanted = {'aqua_edge': 'water', 'flame_edge': 'fire', 'ice_edge': 'ice'}.get(command)
                    if wanted is not None and model.active_gem != wanted:
                        key(game, pygame.K_g)
                        for _ in range(4):
                            if scene.gear.preview_gem == wanted:break
                            key(game, pygame.K_RIGHT)
                        self.assertEqual(scene.gear.preview_gem, wanted)
                        key(game, pygame.K_RETURN);game.update(.1, (0, 0), False);key(game, pygame.K_TAB)
                        self.assertEqual(model.active_gem, wanted)
                    game.draw()
                    if command in ('aqua_edge', 'flame_edge', 'ice_edge'):
                        click(game, scene.command_rects['skills'].center);game.draw()
                    self.assertEqual(model.action_reason(command), '')
                    click(game, scene.command_rects[command].center)
                    if scene._target_command is not None:key(game, pygame.K_RETURN)
                else:game.update(.05, (0, 0), False)
            else:self.fail(('The actual elemental battle did not finish', enemy_id, model.phase))
        self.assertEqual(model.phase, 'victory')
        self.assertEqual(model.player.mp, 0)
        return trace

    def test_zero_mp_actual_party_wins_both_orders_with_earned_gems_and_carried_resources(self):
        for order in (('embravyr', 'nivareth'), ('nivareth', 'embravyr')):
            with self.subTest(order=order):
                self.path.write_text(json.dumps(self.journey));self.game = self.load()
                self.game.attributes.set_current(mp=0)
                for enemy_id in order:
                    self.start(enemy_id, seed=0);self.enter_battle()
                    self.assertEqual(self.game.combat.model.player.mp, 0)
                    self.assertEqual([member.identifier for member in self.game.combat.model.party], ['player', 'mira', 'lucan'])
                    trace = self.play_actual_battle(enemy_id)
                    self.assertTrue(any(event['type'] == 'impact' and event.get('actor') == 'player' for event in trace))
                    self.finish_spoils();self.read_acquisition(expected=enemy_id)
                    self.assertIn(definition(enemy_id)['gem'], self.game.character_abilities.owned_gems())
                self.assertEqual(self.game.elemental_bosses.victory_order, list(order))
                self.assertEqual(set(self.game.character_abilities.owned_gems()), {'water', 'fire', 'ice'})

    def test_fire_then_ice_and_ice_then_fire_install_exact_focus_and_skills_once(self):
        for order in (('embravyr', 'nivareth'), ('nivareth', 'embravyr')):
            with self.subTest(order=order):
                self.path.write_text(json.dumps(self.journey));self.game = self.load()
                story = self.story()
                for index, enemy_id in enumerate(order):
                    entry = definition(enemy_id)
                    xp = {identifier: self.game.character_progression[identifier].total_xp
                          for identifier in self.game.party.active_ids}
                    ticket, pages = self.beat_and_collect(enemy_id)
                    reward = battle_reward_definition('elemental_boss', ticket)
                    self.assertEqual(reward['xp'], 460)
                    self.assertEqual(self.game.inventory.quantity(entry['item']), 1)
                    self.assertIn(entry['gem'], self.game.character_abilities.owned_gems())
                    self.assertIn(entry['skill'], self.game.character_abilities.known_abilities())
                    self.assertEqual(self.game.character_abilities.active_gem(), entry['gem'])
                    self.assertTrue(self.game.battle_rewards.has_receipt(entry['receipt']))
                    self.assertTrue(self.game.elemental_bosses.bosses[enemy_id]['defeated'])
                    self.assertFalse(self.game.elemental_bosses.bosses[enemy_id]['pending_acquisition'])
                    self.assertEqual(self.game.elemental_bosses.victory_order, list(order[:index+1]))
                    self.assertTrue(any('focus is part of the blade now.' in page for page in pages))
                    for identifier, old in xp.items():
                        self.assertEqual(self.game.character_progression[identifier].total_xp,
                                         old+(0 if identifier == 'lucan' else 460))
                    self.assertEqual(self.story(), story)
                    self.assertTrue(self.game.save_progress())
                    self.game = self.load()
                    self.assertFalse(self.game.elemental_bosses.nearby(enemy_id))
                self.assertEqual(set(self.game.character_abilities.owned_gems()), {'water', 'fire', 'ice'})

    def test_each_partial_completion_survives_continue_and_leaves_other_guardian_available(self):
        for enemy_id in REGISTRY:
            with self.subTest(enemy=enemy_id):
                self.path.write_text(json.dumps(self.journey));self.game = self.load()
                self.beat_and_collect(enemy_id)
                other = next(key for key in REGISTRY if key != enemy_id)
                before = self.durable()
                self.game = self.load()
                self.assertEqual(self.durable(), before)
                self.assertFalse(self.game.elemental_bosses.bosses[other]['defeated'])
                self.position(other)
                self.assertEqual(self.game.elemental_bosses.nearby(other), other)
                self.assertEqual(self.game.elemental_bosses.victory_order, [enemy_id])

    def test_entry_continue_keeps_enemy_level_seed_resources_and_initial_atb(self):
        for enemy_id in REGISTRY:
            with self.subTest(enemy=enemy_id):
                self.path.write_text(json.dumps(self.journey));self.game = self.load()
                before = self.resources()
                ticket = self.start(enemy_id, seed=71)
                model = self.enter_battle()
                self.assertEqual(model.enemy_bestiary_id, enemy_id)
                self.assertEqual(self.game.combat.scene.battlefield, ticket['battlefield'])
                initial = deepcopy(model.initial_atb_values)
                self.assertTrue(initial and all(0 <= value <= .5 for value in initial.values()))
                self.game = self.load()
                self.assertEqual(self.game.elemental_bosses.pending, ticket)
                restored = self.enter_battle()
                self.assertEqual(restored.initial_atb_values, initial)
                self.assertEqual(self.resources(), before)
                self.assertEqual(restored.action_mp_cost('aqua_edge', 'player'), 0)
                self.assertEqual(restored.action_mp_cost('aether_edge', 'player'), 4)
                self.assertEqual(restored.action_mp_cost('arc_discharge', 'mira'), 5)

    def test_spoils_and_acquisition_continue_never_duplicate_focus_exp_or_receipt(self):
        ticket = self.start('embravyr');self.enter_battle();self.victory()
        self.game = self.load()
        self.assertEqual(self.game.combat.post_phase, 'spoils')
        self.assertTrue(self.game.combat.spoils.awarded)
        self.assertEqual(self.game.inventory.quantity('red_focus_gem'), 1)
        awarded = self.durable()
        self.game = self.load()
        self.assertEqual(self.durable(), awarded)
        self.finish_spoils()
        self.read_acquisition(expected='embravyr', complete=False)
        self.assertTrue(self.game.elemental_bosses.bosses['embravyr']['pending_acquisition'])
        self.assertTrue(self.game.save_progress())
        self.game = self.load()
        self.assertIsNone(self.game.elemental_bosses.pending)
        self.read_acquisition(expected='embravyr')
        self.assertEqual(self.game.inventory.quantity('red_focus_gem'), 1)
        self.assertTrue(self.game.battle_rewards.has_receipt(ticket['receipt']))
        before = self.durable()
        self.game = self.load();self.game.update(.05, (0, 0), False)
        self.assertFalse(self.game.social.active)
        self.assertEqual(self.durable(), before)

    def test_failed_award_save_rolls_back_gem_skill_exp_receipt_and_selected_focus(self):
        self.start('embravyr');self.enter_battle();self.victory()
        before = self.durable()
        with patch.object(self.game.save_store, 'write', return_value=False):
            spoils = wait_for_spoils(self.game)
        self.assertTrue(spoils.result_error)
        self.assertFalse(spoils.awarded)
        self.assertEqual(self.game.combat.snapshot()['stage'], 'pending')
        self.assertEqual(self.durable(), before)
        self.assertEqual(self.game.character_abilities.active_gem(), 'water')
        self.assertNotIn('fire', self.game.character_abilities.owned_gems())
        self.assertNotIn('flame_edge', self.game.character_abilities.known_abilities())
        spoils.retry_requested = True
        self.game.update(0, (0, 0), False)
        self.assertTrue(spoils.awarded)
        self.assertEqual(self.game.inventory.quantity('red_focus_gem'), 1)
        self.assertTrue(self.game.elemental_bosses.bosses['embravyr']['defeated'])
        once = self.durable()
        for _ in range(3):self.game.update(0, (0, 0), False)
        self.assertEqual(self.durable(), once)
        self.assertIsNotNone(self.game._read_saved_journey(), self.game.save_error)

    def test_failed_focus_install_or_skill_grant_rolls_back_whole_reward_transaction(self):
        for method in ('grant_gem', 'learn_ability', 'set_active_gem'):
            with self.subTest(failure=method):
                self.path.write_text(json.dumps(self.journey));self.game = self.load()
                self.start('embravyr');self.enter_battle();self.victory()
                before = self.durable()
                with patch.object(self.game.character_abilities, method, return_value=False):
                    spoils = wait_for_spoils(self.game)
                self.assertTrue(spoils.result_error)
                self.assertEqual(self.durable(), before)
                self.assertEqual(self.game.combat.snapshot()['stage'], 'pending')
                spoils.retry_requested = True
                self.game.update(0, (0, 0), False)
                self.assertTrue(spoils.awarded)
                self.assertEqual(self.game.inventory.quantity('red_focus_gem'), 1)
                self.assertIn('flame_edge', self.game.character_abilities.known_abilities())
                self.assertIsNotNone(self.game._read_saved_journey(), self.game.save_error)

    def test_failed_loading_checkpoint_retains_intro_ticket_until_retry(self):
        ticket = self.start('nivareth')
        owner = self.game.combat
        for _ in range(100):
            if owner.entry_phase == 'loading':break
            self.game.update(.05, (0, 0), False)
        self.game.draw()
        before = self.game.elemental_bosses.to_dict()
        with patch.object(self.game.save_store, 'write', return_value=False):
            self.game.update(.01, (0, 0), False)
        self.assertIsNone(owner.model)
        self.assertTrue(owner.entry.error)
        self.assertEqual(self.game.elemental_bosses.to_dict(), before)
        self.assertEqual(self.game.elemental_bosses.pending, ticket)
        owner.entry.retry_requested = True
        self.game.update(0, (0, 0), False)
        self.assertIsNotNone(owner.model, getattr(owner.entry, 'error', ''))
        self.assertTrue(self.game.elemental_bosses.bosses['nivareth']['intro_seen'])
        self.assertEqual(self.game.elemental_bosses.pending, ticket)

    def test_ko_caelan_receives_guaranteed_focus_but_no_exp_and_presentation_waits(self):
        self.start('nivareth');self.enter_battle()
        xp = {key: self.game.character_progression[key].total_xp for key in self.game.party.active_ids}
        self.victory(caelan_ko=True);self.finish_spoils()
        game = self.game
        self.assertEqual(game.attributes.current_hp, 0)
        self.assertEqual(game.character_progression['caelan'].total_xp, xp['caelan'])
        self.assertEqual(game.character_progression['mira'].total_xp, xp['mira']+460)
        self.assertEqual(game.inventory.quantity('white_focus_gem'), 1)
        self.assertIn('ice', game.character_abilities.owned_gems())
        self.assertIn('ice_edge', game.character_abilities.known_abilities())
        self.assertTrue(game.elemental_bosses.bosses['nivareth']['pending_acquisition'])
        for _ in range(3):game.update(.1, (0, 0), False)
        self.assertFalse(game.social.active)
        self.game = self.load()
        self.assertEqual(self.game.attributes.current_hp, 0)
        self.assertFalse(self.game.social.active)
        self.assertTrue(self.game.elemental_bosses.bosses['nivareth']['pending_acquisition'])
        self.game.attributes.set_current(hp=1)
        self.game.update(.05, (0, 0), False)
        self.read_acquisition(expected='nivareth')
        self.assertFalse(self.game.elemental_bosses.bosses['nivareth']['pending_acquisition'])

    def test_flee_preserves_spent_resources_and_leaves_guardian_and_focus_unearned(self):
        ticket = self.start('embravyr');model = self.enter_battle()
        model.player.hp -= 17;model.player.mp -= 4
        expected = {'hp': model.player.hp, 'mp': model.player.mp}
        before = (self.game.inventory.to_dict(), self.game.character_progression.to_dict(),
                  self.game.battle_rewards.to_dict())
        model._result('fled');self.game.combat.scene.dismissed = True
        self.assertTrue(self.game.combat._settle())
        self.assertFalse(self.game.combat.active)
        self.assertIsNone(self.game.elemental_bosses.pending)
        self.assertEqual(self.resources()['caelan'], expected)
        self.assertFalse(self.game.elemental_bosses.bosses['embravyr']['defeated'])
        self.assertEqual((self.game.inventory.to_dict(), self.game.character_progression.to_dict(),
                          self.game.battle_rewards.to_dict()), before)
        self.assertEqual(tuple(self.game.player.position), tuple(definition('embravyr')['retreat']))
        self.assertFalse(self.game.battle_rewards.has_receipt(ticket['receipt']))
        self.game = self.load()
        self.position('embravyr')
        self.assertEqual(self.game.elemental_bosses.nearby('embravyr'), 'embravyr')

    def test_failed_flee_save_rolls_back_resources_position_and_ticket_then_retries(self):
        ticket = self.start('nivareth');model = self.enter_battle()
        model.player.hp -= 13;model.player.mp -= 4
        spent = {'hp': model.player.hp, 'mp': model.player.mp}
        before = self.durable()
        position, facing = tuple(self.game.player.position), self.game.player.facing
        owner = self.game.combat
        model._result('fled');owner.scene.dismissed = True
        with patch.object(self.game.save_store, 'write', return_value=False):
            self.assertFalse(owner._settle())
        self.assertTrue(owner.active)
        self.assertEqual(self.durable(), before)
        self.assertEqual(self.game.elemental_bosses.pending, ticket)
        self.assertEqual(tuple(self.game.player.position), position)
        self.assertEqual(self.game.player.facing, facing)
        self.assertEqual((model.player.hp, model.player.mp), (spent['hp'], spent['mp']))
        self.assertTrue(owner.scene.result_error)
        owner.scene.dismissed = True
        self.assertTrue(owner._settle())
        self.assertFalse(owner.active)
        self.assertIsNone(self.game.elemental_bosses.pending)
        self.assertEqual(self.resources()['caelan'], spent)
        self.assertEqual(self.game.inventory.to_dict(), before['inventory'])
        self.assertEqual(self.game.character_progression.to_dict(), before['levels'])
        self.assertEqual(self.game.battle_rewards.to_dict(), before['rewards'])
        self.assertNotIn('ice', self.game.character_abilities.owned_gems())
        self.assertEqual(tuple(self.game.player.position), tuple(definition('nivareth')['retreat']))
        self.assertIsNotNone(self.game._read_saved_journey(), self.game.save_error)

    def test_defeat_opens_game_over_and_manual_load_restores_prebattle_journey(self):
        self.game.attributes.set_current(hp=71, mp=3)
        self.game.party.characters['mira'].set_current(hp=95, mp=4)
        self.position('nivareth')
        self.assertTrue(self.game.saves.manual(1))
        before, story = self.durable(), self.story()
        ticket = self.start('nivareth');self.enter_battle()
        saved = self.path.read_bytes()
        for member in self.game.combat.model.party:member.hp = member.mp = 0
        self.game.combat.model._result('defeat');self.game.combat.scene.dismissed = True
        self.assertTrue(self.game.combat._settle())
        self.assertTrue(self.game.game_over)
        self.assertFalse(self.game.combat.active)
        self.assertEqual(self.path.read_bytes(), saved)
        self.assertEqual(self.resources(), ticket['party_resources'])
        self.assertTrue(self.game.saves.load(self.game.saves.latest('manual')))
        self.assertFalse(self.game.game_over)
        self.assertIsNone(self.game.elemental_bosses.pending)
        self.assertEqual(self.durable(), before)
        self.assertEqual(self.story(), story)

    def test_material_items_do_not_install_focus_and_normal_encounter_edge_costs_stay_four(self):
        self.assertTrue(self.game.inventory.add_many({'aether_ruby': 1, 'aether_opal': 1}))
        self.assertEqual(self.game.character_abilities.owned_gems(), ('water',))
        self.assertNotIn('flame_edge', self.game.character_abilities.known_abilities())
        self.beat_and_collect('embravyr')
        self.assertIn('fire', self.game.character_abilities.owned_gems())
        self.assertTrue(self.game.character_abilities.set_active_gem('water'))
        counter = self.game.cave_random_encounters
        counter.reset(41)
        ticket = counter.advance(100000, (456, 1280))
        self.assertIsNotNone(ticket)
        self.game.player.position.update(ticket['position'])
        self.assertTrue(self.game.combat.start_cave(ticket))
        model = self.enter_battle()
        self.assertEqual(model.action_mp_cost('aqua_edge', 'player'), 4)
        self.assertEqual(model.action_mp_cost('flame_edge', 'player'), 4)
        self.assertEqual(model.action_mp_cost('aether_edge', 'player'), 4)
        self.assertFalse(model.elemental_tutorial)

    def test_old_pending_vespermaw_entry_remains_independent_of_new_optional_state(self):
        from sanctuary_boss import APPROACH
        game = self.game
        game.player.position.update(APPROACH)
        game.player.facing = 'back'
        game.player.moving = game.player.running = False
        game.party_travel.reset();game.camera.reset()
        self.assertTrue(game.sanctuary_boss.interact())
        with patch('sanctuary_boss.random.SystemRandom') as source:
            source.return_value.randrange.return_value = 71
            self.choose('enter')
        self.assertEqual(game.combat.kind, 'cave_boss')
        ticket = game.sanctuary_boss.pending
        before = (self.resources(), game.character_progression.to_dict(), game.inventory.to_dict(),
                  game.battle_rewards.to_dict())
        legacy = json.loads(self.path.read_text())
        legacy.pop('elemental_bosses')
        self.path.write_text(json.dumps(legacy))
        self.game = self.load()
        self.assertEqual(self.game.combat.kind, 'cave_boss')
        self.assertEqual(self.game.sanctuary_boss.pending, ticket)
        self.assertIsNone(self.game.elemental_bosses.pending)
        self.assertEqual(self.game.elemental_bosses.victory_order, [])
        model = self.enter_battle()
        self.assertEqual(model.enemy_bestiary_id, 'vespermaw')
        self.assertEqual(model.enemy.hp, 1877)
        self.assertFalse(model.elemental_tutorial)
        self.assertEqual(model.action_mp_cost('aqua_edge', 'player'), 4)
        self.assertEqual((self.resources(), self.game.character_progression.to_dict(),
                          self.game.inventory.to_dict(), self.game.battle_rewards.to_dict()), before)

    def test_old_journey_preserves_completed_vespermaw_and_adds_fresh_optional_guardians(self):
        game = self.game
        self.assertTrue(game.battle_rewards.award_battle_rewards('boss:vespermaw',
            {'aether_amethyst': 1, 'aether_sapphire': 1}))
        self.assertTrue(game.sanctuary_boss.restore({'version': 1, 'intro_seen': True,
                                                  'defeated': True, 'pending': None}))
        self.assertTrue(game.save_progress())
        legacy = json.loads(self.path.read_text())
        legacy.pop('elemental_bosses')
        self.path.write_text(json.dumps(legacy))
        before = (game.sanctuary_boss.to_dict(), game.inventory.to_dict(),
                  game.battle_rewards.to_dict(), self.resources(), game.character_progression.to_dict())
        self.game = self.load()
        self.assertEqual((self.game.sanctuary_boss.to_dict(), self.game.inventory.to_dict(),
                          self.game.battle_rewards.to_dict(), self.resources(),
                          self.game.character_progression.to_dict()), before)
        self.assertEqual(self.game.elemental_bosses.victory_order, [])
        self.assertTrue(all(not record['defeated'] for record in self.game.elemental_bosses.bosses.values()))
        self.assertEqual(self.game.character_abilities.owned_gems(), ('water',))


if __name__ == '__main__':unittest.main()
