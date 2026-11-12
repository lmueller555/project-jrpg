"""Actual cave input, a free first Aqua cast and durable introductory progress."""
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

from main import Game
from overworld_travel import HALL_ID, RELIEF_ID, RESERVE_ID
from sanctuary_cave import RESERVE_ENTRY_APPROACH
from tools.capture_mq03_emergency import Driver
from tools.capture_sanctuary_reserve import path as clear_path, walk
from test_mill_battle_gameplay import (
    click, finish_spoils_presentation, key,
    wait_for_spoils,
)


class AquaProgressionGameplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # The supported completed-Mill fixture skips earlier quests; MQ03 and
        # the Sanctuary journey then use production dialogue and walking.
        with tempfile.TemporaryDirectory(prefix='aqua-story-') as directory:
            driver = Driver(directory)
            driver.meal();driver.attack_report();driver.departure()
            driver.rejoin_mira();driver.arrive()
            game = driver.game
            # The arrival cinematic now owns the cave handoff. Complete its
            # real dialogue/actions before testing the introductory battle.
            for _ in range(4000):
                if game.sanctuary_arrival.completed:break
                if game.sanctuary_arrival.dialogue is not None:key(game, pygame.K_SPACE)
                driver.tick(.05)
            else:raise AssertionError('Sanctuary arrival did not complete')
            # This fixture predates the gift. Public acquisition models its
            # already-earned blade without awarding any cave progression.
            if not game.character_abilities.has_weapon():
                assert game.character_abilities.acquire_weapon('caelan', 'caelan_gearblade')
            assert game.save_progress()
            cls.journey = json.loads(driver.save.read_text())
        pygame.quit()

    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix='aqua-gameplay-')
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

    def read(self, game=None):
        game = game or self.game
        texts = []
        for _ in range(1000):
            if not game.social.locked:return texts
            if game.social.active:
                texts.append(game.social.page.get('text', ' '.join(game.social.page['lines'])))
                self.assertFalse(game.social.choosing)
                key(game, pygame.K_SPACE)
            game.update(.05, (0, 0), False)
        self.fail(('Unread cave conversation', game.social.script_identifier))

    def enter_cave(self, *, read=True):
        game = self.game
        game.player.position.update(RESERVE_ENTRY_APPROACH)
        game.player.moving = game.player.running = False
        self.assertTrue(game.sanctuary_cave.interact())
        game.opening_fade = game.transfer_cooldown = 0
        game.update(.05, (0, 0), False)
        self.assertEqual(game.world.data['id'], 'sanctuary_cave')
        if read:self.read()
        return game.cave_lesson

    def trigger(self):
        game = self.game
        self.assertTrue(game.world.can_stand((456, 1280)))
        game.player.position.update(456, 1280)
        game.player.moving = game.player.running = False
        game.camera.reset()
        game.cave_random_encounters.reset(41)
        state = game.cave_random_encounters.to_dict()
        state['remaining'] = 1.;state['was_safe'] = False
        self.assertTrue(game.cave_random_encounters.restore(state))
        game.update(.05, (1, 0), False)
        self.assertTrue(game.combat.active)
        ticket = game.cave_random_encounters.pending
        self.assertEqual(ticket['lesson'], 'aqua_edge')
        self.assertEqual(ticket['formation'], 'bat_pair')
        self.assertEqual(ticket['members'], [{'enemy_id': 'cave_bat', 'level': 2}]*2)
        self.assertEqual(json.loads(self.path.read_text())['cave_random_encounters']['pending'], ticket)
        return ticket

    def load_battle(self, game=None):
        game = game or self.game
        owner = game.combat
        for _ in range(60):
            if owner.entry_phase == 'loading':break
            game.update(.05, (0, 0), False)
        self.assertEqual(owner.entry_phase, 'loading')
        self.assertIsNone(owner.model)
        game.draw()
        game.update(.01, (0, 0), False)
        self.assertIsNotNone(owner.model, getattr(owner.entry, 'error', ''))
        for _ in range(30):
            if not owner.transitioning:break
            game.update(.05, (0, 0), False)
        return owner.model

    def cast_aqua(self, game=None):
        game = game or self.game
        scene, model = game.combat.scene, game.combat.model
        for _ in range(1000):
            if scene.tutorial_active:
                key(game, pygame.K_SPACE)
            elif model.waiting_for_player:
                self.assertEqual(model.ready_actor, 'player')
                self.assertEqual(model.skill_actions(), ['aqua_edge'])
                self.assertEqual(model.action_reason('aqua_edge'), '')
                game.draw();click(game, scene.command_rects['skills'].center)
                game.draw();click(game, scene.command_rects['aqua_edge'].center)
                # Group targeting requires one final explicit target confirm.
                key(game, pygame.K_RETURN)
                break
            else:game.update(.05, (0, 0), False)
        else:self.fail('The cave lesson never offered Aqua Edge')
        for _ in range(1000):
            if model.aqua_edge_discovered:
                return scene
            if scene.tutorial_active:key(game, pygame.K_SPACE)
            game.update(.05, (0, 0), False)
        self.fail('The real Aqua animation never discovered the skill')

    def test_first_entry_resonates_once_without_teaching_or_spending_resources(self):
        before = self.resources()
        lesson = self.enter_cave(read=False)
        self.assertTrue(self.game.social.active)
        self.assertIn('resonan', self.game.social.script_identifier)
        self.assertNotIn('aqua_edge', self.game.character_abilities.known_abilities())
        self.read()
        self.assertTrue(lesson.to_dict()['resonance_seen'])
        self.assertEqual(self.resources(), before)
        self.assertTrue(self.game.save_progress())
        restored = self.load()
        restored.update(.1, (0, 0), False)
        self.assertFalse(restored.social.active)
        self.assertTrue(restored.cave_lesson.to_dict()['resonance_seen'])
        self.assertNotIn('aqua_edge', restored.character_abilities.known_abilities())

    def test_entry_confidence_shares_resonance_lock_and_stows_blade(self):
        game = self.game
        lesson = self.enter_cave(read=False)
        self.assertEqual({actor.identifier for actor in game.party_travel.actors()},
                         {'mira', 'lucan'})
        self.assertTrue(lesson.blade_presented)
        self.assertTrue(hasattr(game.player, 'story_sprite'))
        speakers = []
        lines = {}
        for _ in range(100):
            if not game.social.locked:break
            page = game.social.page
            source = page['source_line']
            if source not in lines:
                speakers.append(page['speaker'])
                lines[source] = True
            self.assertTrue(lesson.locks_player)
            self.assertFalse(game.combat.active)
            if source >= 5:
                self.assertFalse(lesson.blade_presented)
                self.assertFalse(hasattr(game.player, 'story_sprite'))
                self.assertEqual(game.player.facing, 'back' if source == 13 else 'left')
            else:
                self.assertTrue(lesson.blade_presented)
            key(game, pygame.K_SPACE)
            game.update(.05, (1, 0), False)
        else:self.fail('Cave entry did not finish')
        self.assertEqual(speakers, ['caelan', 'mira']+['caelan']*4+['mira']+
                         ['caelan']*2+['mira', 'caelan', 'mira', 'caelan', 'lucan'])
        self.assertTrue(lesson.resonance_seen)
        self.assertFalse(lesson.locks_player)
        self.assertFalse(hasattr(game.player, 'story_sprite'))

    def test_zero_mp_first_cast_unlocks_and_continue_retains_same_pending_bats(self):
        self.game.attributes.set_current(mp=0)
        self.enter_cave()
        ticket = self.trigger()
        model = self.load_battle()
        self.assertEqual(model.player.mp, 0)
        self.assertEqual(model.action_mp_cost('aqua_edge', 'player'), 0)
        self.assertEqual([member.identifier for member in model.party], ['player', 'mira', 'lucan'])
        self.assertTrue(all(0 <= value <= .5 for value in model.initial_atb_values.values()))
        self.assertFalse(any(enemy.hp < enemy.max_hp for enemy in model.enemies))
        scene = self.cast_aqua()
        self.assertEqual(scene.model.player.mp, 0)
        self.assertIn('aqua_edge', self.game.character_abilities.known_abilities())
        self.assertIn('aether_edge', self.game.character_abilities.known_abilities())
        self.assertEqual(self.game.character_abilities.owned_gems(), ('water',))
        self.assertFalse(self.game.cave_lesson.to_dict()['battle_cleared'])
        self.assertEqual(model.action_mp_cost('aqua_edge', 'player'), 0)
        saved = json.loads(self.path.read_text())
        self.assertEqual(saved['character_attributes']['current_mp'], 0)
        self.assertIn('aqua_edge', saved['character_abilities']['learned_abilities']['caelan'])
        rewards = self.game.battle_rewards.to_dict()
        restored = self.load()
        self.assertEqual(restored.cave_random_encounters.pending, ticket)
        resumed = self.load_battle(restored)
        self.assertFalse(resumed.aqua_edge_guided)
        self.assertIn('aqua_edge', resumed.skill_actions('player'))
        self.assertEqual(resumed.player.mp, 0)
        self.assertEqual(resumed.action_mp_cost('aqua_edge', 'player'), 0)
        self.assertEqual(restored.battle_rewards.to_dict(), rewards)

    def test_pending_tutorial_continue_preserves_ticket_and_free_cast_before_learning(self):
        self.game.attributes.set_current(mp=0)
        self.enter_cave();ticket = self.trigger()
        first = self.load_battle()
        restored = self.load()
        self.assertEqual(restored.cave_random_encounters.pending, ticket)
        resumed = self.load_battle(restored)
        self.assertEqual(resumed.initial_atb_values, first.initial_atb_values)
        self.assertTrue(resumed.aqua_edge_guided)
        self.assertEqual(resumed.action_mp_cost('aqua_edge', 'player'), 0)
        self.cast_aqua(restored)
        self.assertIn('aqua_edge', restored.character_abilities.known_abilities())
        self.assertEqual(restored.attributes.current_mp, 0)

    def test_level_one_story_party_can_win_the_two_bat_lesson_starting_at_zero_mp(self):
        self.game.attributes.set_current(mp=0)
        self.enter_cave();ticket = self.trigger();model = self.load_battle()
        self.assertEqual(self.game.character_progression['caelan'].level, 1)
        self.assertEqual(self.game.character_progression['mira'].level, 1)
        used_aqua = 0
        for _ in range(12000):
            owner, game = self.game.combat, self.game
            scene = owner.scene
            if scene.tutorial_active:
                key(game, pygame.K_SPACE)
            elif model.ended:break
            elif model.waiting_for_player:
                actor = model.ready_actor
                action = ('aqua_edge' if actor == 'player' else
                          'attack')
                game.draw()
                if action == 'aqua_edge':
                    click(game, scene.command_rects['skills'].center)
                    game.draw()
                self.assertEqual(model.action_reason(action), '')
                click(game, scene.command_rects[action].center)
                if scene._target_command is not None:key(game, pygame.K_RETURN)
                if action == 'aqua_edge':used_aqua += 1
            else:game.update(.05, (0, 0), False)
        else:self.fail(('The two-bat lesson did not finish', model.phase))
        self.assertEqual(model.phase, 'victory')
        self.assertGreater(used_aqua, 0)
        self.assertEqual(model.player.mp, 0)
        self.assertIn('aqua_edge', self.game.character_abilities.known_abilities())
        wait_for_spoils(self.game)
        self.assertTrue(self.game.cave_lesson.battle_cleared)
        self.assertTrue(self.game.battle_rewards.has_receipt(ticket['receipt']))

    def test_intro_victory_persists_then_normal_encounters_resume_without_extra_gems(self):
        self.enter_cave();ticket = self.trigger();self.load_battle();self.cast_aqua()
        self.read_tutorial()
        owner = self.game.combat
        for enemy in owner.model.enemies:enemy.hp = 0
        owner.model._result('victory')
        self.assertTrue(owner._begin_victory())
        wait_for_spoils(self.game)
        finish_spoils_presentation(self.game)
        self.game.draw();click(self.game, owner.spoils.continue_rect.center)
        self.game.update(0, (0, 0), False)
        self.assertFalse(owner.active)
        self.assertTrue(self.game.cave_lesson.to_dict()['battle_cleared'])
        self.assertIsNone(self.game.cave_random_encounters.pending)
        self.assertTrue(self.game.battle_rewards.has_receipt(ticket['receipt']))
        self.assertEqual(self.game.character_abilities.owned_gems(), ('water',))
        totals = self.game.character_progression.to_dict()
        rewards = self.game.battle_rewards.to_dict()
        self.game = self.load()
        self.assertTrue(self.game.cave_lesson.to_dict()['battle_cleared'])
        self.assertEqual(self.game.character_progression.to_dict(), totals)
        self.assertEqual(self.game.battle_rewards.to_dict(), rewards)
        self.game.cave_random_encounters.reset(91)
        state = self.game.cave_random_encounters.to_dict()
        state['remaining'] = 1;state['was_safe'] = False
        self.assertTrue(self.game.cave_random_encounters.restore(state))
        self.game.player.position.update(456, 1280)
        self.game.update(.05, (1, 0), False)
        self.assertTrue(self.game.combat.active)
        self.assertNotIn('lesson', self.game.cave_random_encounters.pending)
        normal = self.load_battle()
        self.assertFalse(normal.aqua_edge_guided)
        self.assertEqual(normal.action_mp_cost('aqua_edge', 'player'), 4)

    def choose_retry(self, action='retry'):
        game = self.game
        self.assertTrue(game.cave_lesson.interact())
        for _ in range(100):
            if game.social.choosing:break
            key(game, pygame.K_SPACE)
        self.assertTrue(game.social.choosing)
        index = next(index for index, item in enumerate(game.social.choice_options)
                     if item['action'] == action)
        click(game, game.social.choice_rects[index].center)
        game.update(0, (0, 0), False)

    def test_flee_preserves_discovery_and_same_ticket_with_free_retry(self):
        self.game.attributes.set_current(mp=0)
        self.enter_cave();ticket = self.trigger();self.load_battle();self.cast_aqua()
        self.read_tutorial()
        owner = self.game.combat
        before = self.game.battle_rewards.to_dict()
        owner.model._result('fled')
        owner.scene.dismissed = True
        self.assertTrue(owner._settle())
        self.assertFalse(owner.active)
        self.assertEqual(self.game.cave_random_encounters.pending, ticket)
        self.assertTrue(self.game.cave_lesson.to_dict()['deferred'])
        self.assertFalse(self.game.cave_lesson.to_dict()['battle_cleared'])
        self.assertIn('aqua_edge', self.game.character_abilities.known_abilities())
        self.assertEqual(self.game.battle_rewards.to_dict(), before)
        self.game = self.load()
        self.assertFalse(self.game.combat.active)
        self.assertEqual(self.game.cave_random_encounters.pending, ticket)
        self.choose_retry('prepare')
        self.assertFalse(self.game.combat.active)
        self.choose_retry()
        resumed = self.load_battle()
        self.assertFalse(resumed.aqua_edge_guided)
        self.assertEqual(resumed.action_mp_cost('aqua_edge', 'player'), 0)
        self.assertEqual(resumed.player.mp, 0)
        self.assertEqual(self.game.cave_random_encounters.pending, ticket)

    def test_defeat_preserves_entry_resources_and_retries_unlearned_lesson(self):
        self.game.attributes.set_current(hp=17, mp=0)
        self.enter_cave();ticket = self.trigger();self.load_battle()
        owner = self.game.combat
        before = self.resources()
        rewards = self.game.battle_rewards.to_dict()
        for member in owner.model.party:member.hp = 0
        owner.model._result('defeat');owner.scene.dismissed = True
        self.assertTrue(owner._settle())
        self.assertFalse(owner.active)
        self.assertEqual(self.resources(), before)
        self.assertEqual(self.game.cave_random_encounters.pending, ticket)
        self.assertTrue(self.game.cave_lesson.to_dict()['deferred'])
        self.assertNotIn('aqua_edge', self.game.character_abilities.known_abilities())
        self.assertEqual(self.game.battle_rewards.to_dict(), rewards)
        self.game = self.load()
        self.assertEqual(self.resources(), before)
        self.assertFalse(self.game.combat.active)
        self.choose_retry()
        model = self.load_battle()
        self.assertTrue(model.aqua_edge_guided)
        self.assertEqual(model.player.hp, 17)
        self.assertEqual(model.player.mp, 0)
        self.cast_aqua()
        self.assertIn('aqua_edge', self.game.character_abilities.known_abilities())

    def test_failed_intro_reward_save_rolls_back_clear_and_rewards_then_retries_once(self):
        self.enter_cave();ticket = self.trigger();self.load_battle();self.cast_aqua()
        self.read_tutorial()
        owner = self.game.combat
        before = (self.game.character_progression.to_dict(),
                  self.game.battle_rewards.to_dict(), self.game.inventory.to_dict(),
                  self.resources(), self.game.cave_lesson.to_dict())
        for enemy in owner.model.enemies:enemy.hp = 0
        owner.model._result('victory');self.assertTrue(owner._begin_victory())
        with patch.object(self.game.save_store, 'write', return_value=False):
            spoils = wait_for_spoils(self.game)
        self.assertTrue(spoils.result_error)
        self.assertFalse(spoils.awarded)
        self.assertEqual(owner.snapshot()['stage'], 'pending')
        self.assertEqual((self.game.character_progression.to_dict(),
                          self.game.battle_rewards.to_dict(), self.game.inventory.to_dict(),
                          self.resources(), self.game.cave_lesson.to_dict()), before)
        self.assertFalse(json.loads(self.path.read_text())['cave_lesson']['battle_cleared'])
        spoils.retry_requested = True
        self.game.update(0, (0, 0), False)
        self.assertTrue(spoils.awarded)
        self.assertTrue(self.game.cave_lesson.to_dict()['battle_cleared'])
        self.assertTrue(self.game.battle_rewards.has_receipt(ticket['receipt']))
        totals = self.game.character_progression.to_dict()
        rewards = self.game.battle_rewards.to_dict()
        for _ in range(3):self.game.update(0, (0, 0), False)
        self.assertEqual(self.game.character_progression.to_dict(), totals)
        self.assertEqual(self.game.battle_rewards.to_dict(), rewards)
        restored = self.load()
        self.assertEqual(restored.combat.post_phase, 'spoils')
        self.assertTrue(restored.cave_lesson.to_dict()['battle_cleared'])
        self.assertEqual(restored.character_progression.to_dict(), totals)
        self.assertEqual(restored.battle_rewards.to_dict(), rewards)

    def test_failed_discovery_save_retries_without_awarding_progress_or_refunding_cast(self):
        self.game.attributes.set_current(mp=0)
        self.enter_cave();ticket = self.trigger();self.load_battle()
        before = self.resources()
        with patch.object(self.game.save_store, 'write', return_value=False):
            scene = self.cast_aqua()
        self.assertTrue(scene.result_error)
        self.assertNotIn('aqua_edge', self.game.character_abilities.known_abilities())
        self.assertEqual(self.resources(), before)
        self.assertNotIn('aqua_edge', json.loads(self.path.read_text())[
            'character_abilities'].get('learned_abilities', {}).get('caelan', []))
        self.game.update(0, (0, 0), False)
        self.assertFalse(scene.result_error)
        self.assertIn('aqua_edge', self.game.character_abilities.known_abilities())
        self.assertEqual(self.game.attributes.current_mp, 0)
        self.assertEqual(self.game.cave_random_encounters.pending, ticket)
        self.assertFalse(self.game.battle_rewards.has_receipt(ticket['receipt']))
        self.assertTrue(self.game._read_saved_journey())

    def test_unarmed_or_ko_caelan_does_not_trigger_or_drain_encounter_budget(self):
        self.enter_cave()
        game = self.game
        game.player.position.update(456, 1280)
        for unarmed in (True, False):
            with self.subTest(unarmed=unarmed):
                if unarmed:self.assertTrue(game.character_abilities.equip_weapon('caelan', None))
                else:
                    self.assertTrue(game.character_abilities.equip_weapon('caelan', 'caelan_gearblade'))
                    game.attributes.set_current(hp=0, mp=0)
                state = game.cave_random_encounters.to_dict()
                self.assertTrue(game.cave_lesson.ready_reason())
                game.update(.2, (1, 0), False)
                self.assertFalse(game.combat.active)
                self.assertEqual(game.cave_random_encounters.to_dict(), state)
        self.assertTrue(game.world.can_stand(game.player.position))
        self.assertFalse(game.cave_lesson.to_dict()['battle_cleared'])
        self.assertTrue(game.character_abilities.has_weapon())
        game.attributes.set_current(hp=1, mp=0)
        self.assertIsNone(game.cave_lesson.ready_reason())
        self.trigger();self.load_battle();self.cast_aqua()
        self.assertIn('aqua_edge', game.character_abilities.known_abilities())

    def test_legacy_visited_cave_learns_aqua_without_replaying_quest_or_first_encounter(self):
        self.enter_cave();self.trigger();self.load_battle();self.cast_aqua()
        self.read_tutorial()
        owner = self.game.combat
        for enemy in owner.model.enemies:enemy.hp = 0
        owner.model._result('victory');self.assertTrue(owner._begin_victory())
        wait_for_spoils(self.game);finish_spoils_presentation(self.game)
        self.game.draw();click(self.game, owner.spoils.continue_rect.center)
        self.game.update(0, (0, 0), False)
        legacy = json.loads(self.path.read_text())
        legacy.pop('cave_lesson')
        legacy['character_abilities'].pop('gear_gems')
        legacy['character_abilities']['gear_focus'] = {'caelan': 'fire'}
        legacy['character_abilities'].pop('learned_abilities', None)
        self.path.write_text(json.dumps(legacy))
        before = (deepcopy(legacy['quests']), deepcopy(legacy['party']),
                  deepcopy(legacy['battle_rewards']), deepcopy(legacy['inventory']),
                  deepcopy(legacy['character_levels']))
        restored = self.load()
        self.assertIn('aether_edge', restored.character_abilities.known_abilities())
        self.assertIn('aqua_edge', restored.character_abilities.known_abilities())
        self.assertEqual(restored.character_abilities.owned_gems(), ('water',))
        self.assertEqual(restored.character_abilities.active_gem(), 'water')
        self.assertTrue(restored.cave_lesson.to_dict()['battle_cleared'])
        self.assertTrue(restored.cave_lesson.to_dict()['resonance_seen'])
        restored.update(.1, (0, 0), False)
        self.assertFalse(restored.social.active)
        self.assertFalse(restored.combat.active)
        self.assertEqual((restored.quests.to_dict(), restored.party.to_dict(),
                          restored.battle_rewards.to_dict(), restored.inventory.to_dict(),
                          restored.character_progression.to_dict()), before)

    def test_completed_legacy_mill_with_missing_blade_migrates_without_resource_reset(self):
        game = self.game
        game.attributes.set_current(hp=9, mp=0)
        game.party.characters['mira'].set_current(hp=28, mp=1)
        # An old cave withdrawal left a real selected-and-finished counter,
        # without a victory reward or any new lesson state.
        ticket = game.cave_random_encounters.advance(100000, (456, 1280))
        self.assertIsNotNone(ticket)
        self.assertTrue(game.cave_random_encounters.finish(ticket['receipt']))
        self.assertTrue(game.save_progress())
        legacy = json.loads(self.path.read_text())
        legacy.pop('cave_lesson')
        legacy['inventory']['items'].pop('caelan_gearblade', None)
        state = legacy['character_abilities']
        state['characters']['caelan'] = {'equipped_weapon': None,
                                         'first_weapon_acquired': False}
        for key in ('gear_gems', 'gear_focus', 'deferred_weapon_training', 'learned_abilities'):
            state.pop(key, None)
        self.assertTrue(legacy['mill_quest']['legacy_bypass'])
        self.path.write_text(json.dumps(legacy))
        before = (self.resources(), legacy['quests'], legacy['character_levels'],
                  legacy['battle_rewards'])
        self.game = self.load()
        restored = self.game
        self.assertEqual((self.resources(), restored.quests.to_dict(),
                          restored.character_progression.to_dict(),
                          restored.battle_rewards.to_dict()), before)
        self.assertEqual(restored.inventory.quantity('caelan_gearblade'), 1)
        self.assertTrue(restored.character_abilities.has_weapon())
        self.assertEqual(restored.character_abilities.owned_gems(), ('water',))
        self.assertIn('aether_edge', restored.character_abilities.known_abilities())
        self.assertIn('aqua_edge', restored.character_abilities.known_abilities())
        self.assertTrue(restored.cave_lesson.battle_cleared)
        self.assertFalse(restored.social.active)
        self.assertFalse(restored.combat.active)

    def settle(self):
        for _ in range(30):
            if not self.game.opening_fade and not self.game.transfer_cooldown:return
            self.game.update(.05, (0, 0), False)
        self.fail('The scene transfer did not finish')

    def route(self, goal):
        game = self.game
        scene = game.world.data['id']
        points = clear_path(game.world, game.player.position, goal)
        walk(game, points, scene)
        self.assertEqual(game.world.data['id'], scene)
        self.assertTrue(game.world.can_stand(game.player.position))
        self.assertFalse(game.combat.active)

    def doorway(self, identifier, destination):
        game = self.game
        origin = game.world
        door = next(door for door in origin.doors if door.data['id'] == identifier)
        x, y = door.data['anchor']
        north = door.data['entry_side'] == 'north'
        self.route((x, y+24 if north else y-24))
        for _ in range(60):
            if game.world is not origin:break
            game.update(.04, (0, -1 if north else 1), False)
        self.assertEqual(game.world.data['id'], destination)
        self.settle()

    def test_deferred_lesson_survives_real_cave_exit_bed_rest_continue_and_return(self):
        self.game.attributes.set_current(hp=27, mp=0)
        self.enter_cave();ticket = self.trigger();self.load_battle();self.cast_aqua()
        self.read_tutorial()
        owner = self.game.combat
        owner.model._result('fled');owner.scene.dismissed = True
        self.assertTrue(owner._settle())
        before = (self.game.battle_rewards.to_dict(), self.game.inventory.to_dict(),
                  self.game.quests.to_dict(), self.game.character_progression.to_dict())
        exit_link = next(item for item in self.game.world.data['cave']['links']
                         if item['id'] == 'reserve')
        self.route(exit_link['approach'])
        key(self.game, pygame.K_e)
        self.assertEqual(self.game.world.data['id'], RESERVE_ID)
        self.settle()
        self.assertEqual(self.game.cave_random_encounters.pending, ticket)
        self.assertIsNotNone(self.game._read_saved_journey(), self.game.save_error)
        self.doorway('sanctuary_hall', HALL_ID)
        self.doorway('relief_room', RELIEF_ID)
        self.route(self.game.world.data['relief_room']['bed_approach'])
        self.assertTrue(self.game.bed_rest.interact())
        for _ in range(30):
            if self.game.social.choosing:break
            key(self.game, pygame.K_SPACE)
        self.assertTrue(self.game.social.choosing)
        index = next(index for index, item in enumerate(self.game.social.choice_options)
                     if item['action'] == 'rest')
        click(self.game, self.game.social.choice_rects[index].center)
        self.read();self.settle()
        for values in self.game.party.available_ids:
            attributes = self.game.party.characters[values]
            self.assertEqual(attributes.current_hp, attributes.value('hp'))
            self.assertEqual(attributes.current_mp, attributes.value('mp'))
        self.assertEqual(json.loads(self.path.read_text())['player']['scene'], RELIEF_ID)
        self.game = self.load()
        self.assertEqual(self.game.world.data['id'], RELIEF_ID)
        self.assertEqual(self.game.cave_random_encounters.pending, ticket)
        self.assertTrue(self.game.cave_lesson.deferred)
        self.doorway('hall', HALL_ID)
        self.doorway('reserve_exit', RESERVE_ID)
        self.route(RESERVE_ENTRY_APPROACH)
        key(self.game, pygame.K_e);self.settle()
        self.assertEqual(self.game.world.data['id'], 'sanctuary_cave')
        self.route(ticket['position'])
        self.choose_retry()
        model = self.load_battle()
        self.assertFalse(model.aqua_edge_guided)
        self.assertEqual(model.action_mp_cost('aqua_edge', 'player'), 0)
        self.assertEqual(self.game.cave_random_encounters.pending, ticket)
        self.assertEqual((self.game.battle_rewards.to_dict(), self.game.inventory.to_dict(),
                          self.game.quests.to_dict(), self.game.character_progression.to_dict()), before)

    def read_tutorial(self):
        for _ in range(100):
            if not self.game.combat.scene.tutorial_active:return
            key(self.game, pygame.K_SPACE)
        self.fail('Tutorial dialogue did not finish')


if __name__ == '__main__':unittest.main()
