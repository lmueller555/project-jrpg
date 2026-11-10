"""Durable story-boss entry, rewards and return use their own saved receipt."""
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

from leveling import CharacterLevel, character_stats, total_xp_for_level
from main import Game
from post_battle import battle_reward_definition, valid_pending_snapshot
from sanctuary_boss import BATTLEFIELD, RECEIPT, SCENE_ID
from sanctuary_cave import RESERVE_ENTRY_APPROACH
from test_mill_battle_gameplay import wait_for_spoils
from tools.capture_mq03_emergency import Driver


class VespermawEncounterOwnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory(prefix='boss-owner-story-') as directory:
            driver = Driver(directory)
            driver.meal();driver.attack_report();driver.departure()
            driver.rejoin_mira();driver.arrive()
            game = driver.game
            # Explicit earlier-discovery fixture; production input still owns
            # the boss approach and every settlement/Continue below.
            owner = game.character_abilities
            if not owner.has_weapon():assert owner.acquire_weapon('caelan', 'caelan_gearblade')
            assert owner.learn_ability('caelan', 'aqua_edge')
            assert game.cave_lesson.restore({'version': 1, 'resonance_seen': True,
                                             'battle_cleared': True, 'deferred': False})
            game.player.position.update(RESERVE_ENTRY_APPROACH)
            game.opening_fade = game.transfer_cooldown = 0
            assert game.sanctuary_cave.interact()
            game.opening_fade = game.transfer_cooldown = 0
            game.player.position.update(2060, 300)
            assert game.world.can_stand(game.player.position)
            assert game.save_progress()
            cls.journey = json.loads(driver.save.read_text())
        pygame.quit()

    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix='boss-owner-')
        self.addCleanup(directory.cleanup)
        self.addCleanup(pygame.quit)
        self.directory = Path(directory.name)
        self.path = self.directory/'journey.json'
        self.path.write_text(json.dumps(self.journey))
        self.game = self.load()
        self.game.social.cancel_script()
        # A labelled full-formation fixture exercises three-participant reward
        # settlement; the actual MQ03 route itself only requires Caelan/Mira.
        if 'lucan' not in self.game.party.members:
            self.assertTrue(self.game.party.recruit('lucan'))
        self.assertTrue(self.game.party.select(('caelan', 'mira', 'lucan')))
        for identifier in self.game.party.active_ids:
            attributes = self.game.party.characters[identifier]
            attributes._attributes = character_stats(identifier, 6)
            attributes.set_current(hp=attributes.value('hp')-25, mp=13)
            self.game.character_progression.records[identifier] = CharacterLevel(
                identifier, total_xp_for_level(6))
        self.game.player.facing = 'back'
        self.ticket = {
            'version': 1, 'enemy_id': 'vespermaw', 'level': 7, 'receipt': RECEIPT,
            'scene': SCENE_ID, 'position': list(self.game.player.position), 'facing': 'back',
            'battlefield': BATTLEFIELD, 'combat_seed': 71,
            'party_active': list(self.game.party.active_ids),
            'party_resources': self.resources()}
        self.assertTrue(self.game.sanctuary_boss.restore(
            {'version': 1, 'defeated': False, 'intro_seen': False, 'pending': self.ticket}))
        self.counter = deepcopy(self.game.cave_random_encounters.to_dict())

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

    def totals(self, game=None):
        game = game or self.game
        return {identifier: game.character_progression[identifier].total_xp
                for identifier in game.party.active_ids}

    def persisted(self):return json.loads(self.path.read_text())

    def start(self):
        self.assertTrue(self.game.combat.start_boss(self.ticket))
        owner = self.game.combat
        self.assertEqual(owner.kind, 'cave_boss')
        self.assertEqual(owner.checkpoint_position, tuple(self.ticket['position']))
        return owner

    def load_battle(self, game=None):
        game = game or self.game
        owner = game.combat
        for _ in range(100):
            if owner.entry_phase == 'loading':break
            owner.update(.1)
        self.assertEqual(owner.entry_phase, 'loading')
        self.assertIsNone(owner.model)
        owner.update(.1)
        self.assertIsNone(owner.model)
        game.draw()
        self.assertTrue(owner.entry.loading_presented)
        owner.update(.01)
        self.assertIsNotNone(owner.model, getattr(owner.entry, 'error', ''))
        owner.transition = None
        return owner.model

    def victory(self):
        owner = self.start()
        model = self.load_battle()
        model.player.hp, model.player.mp = 47, 7
        model.combatant('mira').hp = 0
        model.combatant('lucan').hp = 61
        model.enemy.hp = 0
        model._result('victory')
        self.assertTrue(owner._begin_victory())
        return owner

    def finish_presentation(self, spoils):
        spoils.finish_animation()
        for _ in range(10):
            if spoils.presentation_complete:return
            for event_type in (pygame.KEYDOWN, pygame.KEYUP):
                spoils.handle_event(pygame.event.Event(event_type, key=pygame.K_RETURN, repeat=False))
        self.fail('Level-up presentation did not finish')

    def test_entry_is_checkpointed_and_continue_restarts_same_formation_and_atb(self):
        before = self.resources()
        owner = self.start()
        checkpoint = self.persisted()
        self.assertEqual(checkpoint['sanctuary_boss']['pending'], self.ticket)
        self.assertIsNone(checkpoint.get('post_battle'))
        model = self.load_battle()
        atb = [actor.atb for actor in (*model.party, model.enemy)]
        self.assertTrue(all(0 <= value <= .5 for value in atb))
        self.assertEqual(model.enemy.hp, 1877)
        self.assertEqual(self.resources(), before)
        self.assertEqual(owner.scene.battlefield, BATTLEFIELD)
        restored = self.load()
        self.assertEqual(restored.combat.kind, 'cave_boss')
        resumed = self.load_battle(restored)
        self.assertEqual([actor.atb for actor in (*resumed.party, resumed.enemy)], atb)
        self.assertEqual(self.resources(restored), before)
        self.assertEqual(restored.cave_random_encounters.to_dict(), self.counter)

    def test_failed_intro_acknowledgement_save_retains_entry_until_retry(self):
        owner = self.start()
        for _ in range(100):
            if owner.entry_phase == 'loading':break
            owner.update(.1)
        self.game.draw()
        before = self.game.sanctuary_boss.to_dict()
        self.assertFalse(before['intro_seen'])
        with patch.object(self.game.save_store, 'write', return_value=False):
            owner.update(.01)
        self.assertIsNone(owner.model)
        self.assertTrue(owner.entry.error)
        self.assertEqual(self.game.sanctuary_boss.to_dict(), before)
        self.assertEqual(self.persisted()['sanctuary_boss'], before)
        owner.entry.retry_requested = True
        owner.update(0)
        self.assertIsNotNone(owner.model, getattr(owner.entry, 'error', ''))
        self.assertTrue(self.game.sanctuary_boss.intro_seen)
        self.assertEqual(self.resources(), self.ticket['party_resources'])

    def test_victory_commits_exact_rewards_and_preserves_ko_without_first_aid(self):
        totals = self.totals()
        inventory = {key: self.game.inventory.quantity(key)
                     for key in ('aether_amethyst', 'aether_sapphire')}
        owner = self.victory()
        self.assertEqual(owner.snapshot()['stage'], 'pending')
        self.assertFalse(self.game.sanctuary_boss.defeated)
        self.assertTrue(valid_pending_snapshot(owner.snapshot(), self.persisted()))
        wait_for_spoils(self.game)
        self.assertTrue(self.game.sanctuary_boss.defeated)
        self.assertTrue(self.game.battle_rewards.has_receipt(RECEIPT))
        self.assertEqual(self.totals(), {key: value+(0 if key == 'mira' else 520)
                                        for key, value in totals.items()})
        self.assertEqual(self.resources()['caelan'], {'hp': 47, 'mp': 7})
        self.assertEqual(self.resources()['mira']['hp'], 0)
        for key, amount in inventory.items():self.assertEqual(self.game.inventory.quantity(key), amount+1)
        self.assertTrue(valid_pending_snapshot(owner.snapshot(), self.persisted()))
        self.assertEqual(self.game.cave_random_encounters.to_dict(), self.counter)

    def test_ko_leader_stays_ko_and_receives_no_exp_on_victory_or_continue(self):
        totals = self.totals()
        owner = self.start();model = self.load_battle()
        model.player.hp = 0
        model.combatant('mira').hp = 51
        model.combatant('lucan').hp = 0
        model.enemy.hp = 0
        model._result('victory')
        self.assertTrue(owner._begin_victory())
        self.assertEqual(owner.snapshot()['resources']['hp'], 0)
        wait_for_spoils(self.game)
        self.assertEqual(self.game.attributes.current_hp, 0)
        self.assertEqual(self.totals(), {key: value+(520 if key == 'mira' else 0)
                                        for key, value in totals.items()})
        restored = self.load()
        self.assertEqual(restored.attributes.current_hp, 0)
        self.assertEqual(restored.party.characters['mira'].current_hp, 51)
        self.assertEqual(self.totals(restored), self.totals())

    def test_failed_award_save_rolls_back_complete_boss_transaction_then_retries_once(self):
        owner = self.victory()
        before = (self.resources(), self.totals(), self.game.inventory.to_dict(),
                  self.game.battle_rewards.to_dict(), self.game.sanctuary_boss.to_dict())
        with patch.object(self.game.save_store, 'write', return_value=False):
            spoils = wait_for_spoils(self.game)
        self.assertFalse(spoils.ready)
        self.assertEqual(owner.snapshot()['stage'], 'pending')
        self.assertEqual((self.resources(), self.totals(), self.game.inventory.to_dict(),
                          self.game.battle_rewards.to_dict(), self.game.sanctuary_boss.to_dict()), before)
        spoils.retry_requested = True
        self.game.update(0, (0, 0), False)
        self.assertTrue(spoils.ready)
        self.assertTrue(self.game.sanctuary_boss.defeated)
        after = (self.resources(), self.totals(), self.game.inventory.to_dict())
        restored = self.load()
        self.assertEqual((self.resources(restored), self.totals(restored), restored.inventory.to_dict()), after)
        self.assertEqual(len([value for value in restored.battle_rewards.to_dict()['receipts']
                              if value == RECEIPT]), 1)

    def test_continue_pending_and_failed_finish_do_not_duplicate_or_reset_random_budget(self):
        owner = self.victory()
        restored = self.load()
        self.assertTrue(restored.sanctuary_boss.defeated)
        owner = restored.combat
        spoils = wait_for_spoils(restored)
        self.finish_presentation(spoils)
        earned = (self.resources(restored), self.totals(restored), restored.inventory.to_dict())
        with patch.object(restored.save_store, 'write', return_value=False):
            self.assertFalse(owner._finish_spoils())
        self.assertIsNotNone(restored.sanctuary_boss.pending)
        self.assertEqual(owner.snapshot()['stage'], 'awarded')
        self.assertTrue(restored.sanctuary_boss.defeated)
        # An error requires the existing explicit Retry before Continue.
        spoils.retry_requested = True
        restored.update(0, (0, 0), False)
        self.assertTrue(spoils.ready)
        self.assertTrue(owner._finish_spoils())
        self.assertFalse(owner.active)
        self.assertIsNone(restored.sanctuary_boss.pending)
        self.assertEqual((self.resources(restored), self.totals(restored), restored.inventory.to_dict()), earned)
        self.assertEqual(restored.cave_random_encounters.to_dict(), self.counter)
        final = self.load()
        self.assertTrue(final.sanctuary_boss.defeated)
        self.assertFalse(final.combat.active)

    def test_defeat_restores_entry_resources_and_calls_retry_owner_without_rewards(self):
        resources, levels = self.resources(), self.totals()
        inventory = self.game.inventory.to_dict()
        owner = self.start();model = self.load_battle()
        for member in model.party:member.hp = member.mp = 0
        model._result('defeat')
        with patch.object(self.game.sanctuary_boss, 'battle_defeated') as callback:
            self.assertTrue(owner._settle())
        callback.assert_called_once_with(self.ticket)
        self.assertEqual(self.resources(), resources)
        self.assertEqual(self.totals(), levels)
        self.assertEqual(self.game.inventory.to_dict(), inventory)
        self.assertFalse(self.game.battle_rewards.has_receipt(RECEIPT))
        self.assertFalse(self.game.sanctuary_boss.defeated)
        self.assertEqual(self.game.sanctuary_boss.pending, self.ticket)
        self.assertEqual(self.game.cave_random_encounters.to_dict(), self.counter)

    def test_forged_boss_rewards_ticket_resources_or_completion_flags_are_rejected(self):
        owner = self.victory()
        record, data = owner.snapshot(), self.persisted()
        self.assertTrue(valid_pending_snapshot(record, data))
        wrong_amount = deepcopy(record)
        wrong_amount['progression'] = self.game.character_progression.preview(
            60, record['party_active'], record['progression']['end_hp'])
        self.assertFalse(valid_pending_snapshot(wrong_amount, data))
        for field, mutate in (
            ('before', lambda value: value['encounter']['party_resources']['caelan'].update(hp=1)),
            ('level', lambda value: value['encounter'].update(level=8)),
            ('drop', lambda value: value['rewards']['drops'].update(aether_emerald=1)),
        ):
            with self.subTest(field=field):
                bad = deepcopy(record);mutate(bad)
                self.assertFalse(valid_pending_snapshot(bad, data))
        wrong_state = deepcopy(data);wrong_state['sanctuary_boss']['defeated'] = True
        self.assertFalse(valid_pending_snapshot(record, wrong_state))
        self.assertEqual(battle_reward_definition('cave_boss', self.ticket),
                         {'drops': {'aether_amethyst': 1, 'aether_sapphire': 1}, 'xp': 520})
