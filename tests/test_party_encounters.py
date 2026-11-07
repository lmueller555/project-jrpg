"""Real encounter composition and durable resources for every active member."""
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame

from main import Game
from post_battle import valid_pending_snapshot
import test_mill_battle_gameplay as mill_fixture
from test_mill_battle_gameplay import read_social, wait_for_spoils


class PartyEncounterTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix='party-encounters-')
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        self.path = self.directory/'journey.json'
        self.game = self.new_game()
        for identifier in ('mira', 'lucan', 'rhea'):
            self.assertTrue(self.game.party.recruit(identifier))
        self.assertTrue(self.game.party.select(('caelan', 'mira', 'lucan')))
        self.game.party.characters['mira'].set_current(hp=170, mp=21)
        self.game.party.characters['lucan'].set_current(hp=110, mp=12)
        self.game.party.characters['rhea'].set_current(hp=90, mp=9)

    def tearDown(self):pygame.quit()

    def new_game(self, title=False):
        game = Game(window_size=(960, 640), fullscreen=False,
                    start_on_title=title, save_path=self.path,
                    settings_path=self.directory/'settings.json')
        game.audio.set_music(0);game.audio.set_effects(0)
        game.opening_fade = game.transfer_cooldown = 0
        pygame.event.clear()
        return game

    def start(self):
        game = self.game
        game.world = game.town
        game.player.position.update(game.combat.position+(0, 24))
        game.player.facing = 'back';game.camera.reset()
        self.assertTrue(game.combat.interact())
        game.combat.transition = None
        return game.combat

    def victory(self):
        owner = self.start()
        owner.model.player.hp -= 7
        owner.model.combatant('mira').hp = 0
        owner.model.combatant('mira').mp = 17
        owner.model.combatant('lucan').hp = 61
        owner.model.combatant('lucan').mp = 3
        owner.model.enemy.hp = 0;owner.model.phase = 'victory'
        self.assertTrue(owner._begin_victory())
        return owner

    def resources(self, game=None):
        party = (game or self.game).party
        return {identifier: (attributes.current_hp, attributes.current_mp)
                for identifier, attributes in party.characters.items()}

    def load(self):
        game = self.new_game(title=True)
        self.assertTrue(game.has_saved_journey)
        self.assertTrue(game.begin_journey(True))
        return game

    def start_mill(self):
        self.game = self.new_game()
        driver = mill_fixture.MillBattleGameplayTests()
        driver.game = self.game
        driver.diagnose()
        self.game.party.characters['mira'].set_current(hp=37, mp=9)
        driver.enter_path()
        for _ in range(500):
            if self.game.combat.active:break
            if self.game.social.active or self.game.mill_quest.encounter_cutscene_active:
                read_social(self.game)
            else:self.game.update(.05, (0, 0), False)
        self.assertTrue(self.game.combat.active)
        self.assertEqual(self.game.combat.model.combatant('mira').hp, 37)
        return self.game.combat

    def test_optional_battle_uses_three_selected_members_and_their_current_resources(self):
        owner = self.start()
        self.assertEqual([member.identifier for member in owner.model.party], ['player', 'mira', 'lucan'])
        self.assertEqual([(member.hp, member.mp) for member in owner.model.party[1:]],
                         [(170, 21), (110, 12)])
        self.assertEqual([bot.identifier for bot in owner.model.bots], ['rivet'])
        self.game.draw()

    def test_party_menu_blocks_contact_and_living_companion_can_fight_with_caelan_ko(self):
        game = self.game
        game.world = game.town
        game.player.position.update(game.combat.position+(0, 24))
        game.party_ui.open()
        self.assertFalse(game.combat.interact())
        game.party_ui.close()
        game.attributes.set_current(hp=0)
        owner = self.start()
        self.assertEqual(owner.model.player.hp, 0)
        owner.model.enemy.hp = 0;owner.model.phase = 'victory'
        self.assertTrue(owner._begin_victory())
        self.assertTrue(valid_pending_snapshot(owner.snapshot(), json.loads(self.path.read_text())))
        self.assertTrue(wait_for_spoils(game).ready)
        self.assertEqual(game.attributes.current_hp, game.attributes.value('hp')//4)

    def test_reserve_mira_does_not_deploy_rivet_or_receive_battle_resource_changes(self):
        self.assertTrue(self.game.party.select(('caelan', 'lucan', 'rhea')))
        owner = self.start()
        self.assertEqual([member.identifier for member in owner.model.party], ['player', 'lucan', 'rhea'])
        self.assertEqual(owner.model.bots, ())
        owner.model.combatant('lucan').hp = 25
        owner.model.combatant('rhea').mp = 4
        owner.model.phase = 'fled';owner.scene.dismissed = True
        self.assertTrue(owner._settle())
        self.assertEqual(self.resources()['mira'], (170, 21))
        self.assertEqual(self.resources()['lucan'], (25, 12))
        self.assertEqual(self.resources()['rhea'], (90, 4))
        self.assertEqual(self.resources(self.load()), self.resources())

    def test_defeat_preserves_optional_battle_entry_resources_for_all_members(self):
        before = self.resources()
        owner = self.start()
        for member in owner.model.party:member.hp = 0;member.mp = 0
        owner.model.phase = 'defeat';owner.scene.dismissed = True
        self.assertTrue(owner._settle())
        self.assertEqual(self.resources(), before)
        self.assertEqual(self.resources(self.load()), before)
        self.assertEqual(self.game.lattice.state()['rp'], 0)

    def test_mill_defeat_restores_viable_companion_hp_and_preserves_entry_mp(self):
        owner = self.start_mill()
        for member in owner.model.party:member.hp = 0;member.mp = 0
        owner.model.phase = 'defeat';owner.scene.dismissed = True
        self.assertTrue(owner._settle())
        mira = self.game.party.characters['mira']
        self.assertEqual((mira.current_hp, mira.current_mp), (mira.value('hp'), 9))
        self.assertFalse(self.game.mill_quest.encounter_cleared)
        self.assertEqual(self.resources(self.load())['mira'], (mira.value('hp'), 9))

    def test_mill_withdrawal_preserves_actual_companion_ko_and_spent_mp(self):
        owner = self.start_mill()
        owner.model.combatant('mira').hp = 0
        owner.model.combatant('mira').mp = 2
        owner.model.phase = 'fled';owner.scene.dismissed = True
        self.assertTrue(owner._settle())
        self.assertEqual(self.resources()['mira'], (0, 2))
        self.assertEqual(self.resources(self.load())['mira'], (0, 2))
        self.assertEqual(self.game.lattice.state()['rp'], 0)

    def test_pending_victory_resumes_same_party_and_companion_ko_then_grants_once(self):
        before = self.resources();owner = self.victory()
        record = owner.snapshot();saved = json.loads(self.path.read_text())
        self.assertTrue(valid_pending_snapshot(record, saved))
        self.assertEqual(record['party_active'], ['caelan', 'mira', 'lucan'])
        self.assertEqual(record['party_before']['mira'], {'hp': 170, 'mp': 21})
        self.assertEqual(saved['party']['characters']['mira']['current_hp'], 170)
        self.assertEqual(self.resources(), before)
        restored = self.load()
        self.assertEqual([member.identifier for member in restored.combat.model.party], ['player', 'mira', 'lucan'])
        self.assertEqual(restored.combat.model.combatant('mira').hp, 0)
        self.assertEqual(self.resources(restored)['mira'], (0, 17))
        self.assertEqual(self.resources(restored)['lucan'], (61, 3))
        self.assertEqual(self.resources(restored)['rhea'], before['rhea'])
        self.assertEqual(restored.lattice.state()['rp'], 20)
        awarded = restored.combat.snapshot()
        self.assertTrue(valid_pending_snapshot(awarded, json.loads(self.path.read_text())))
        again = self.load()
        self.assertEqual(self.resources(again), self.resources(restored))
        self.assertEqual(again.lattice.state()['rp'], 20)
        self.assertEqual(again.inventory.quantity('aether_emerald'), 1)

    def test_failed_award_save_keeps_complete_memory_state_and_retries_without_duplicate_reward(self):
        owner = self.victory()
        with patch.object(self.game.save_store, 'write', return_value=False):
            spoils = wait_for_spoils(self.game)
            self.assertFalse(spoils.ready)
            self.assertEqual(owner.snapshot()['stage'], 'awarded')
            self.assertEqual(self.resources()['mira'], (0, 17))
            self.assertEqual(self.resources()['lucan'], (61, 3))
            self.assertEqual(json.loads(self.path.read_text())['post_battle']['stage'], 'pending')
        with patch.object(self.game.lattice_progression, 'award_battle_rewards',
                          side_effect=AssertionError('duplicate reward')):
            self.assertTrue(owner._award_spoils())
        self.assertTrue(valid_pending_snapshot(owner.snapshot(), json.loads(self.path.read_text())))
        self.assertEqual(self.resources(self.load()), self.resources())
        self.assertEqual(self.game.lattice.state()['rp'], 20)

    def test_rejected_rewards_leave_all_resources_unchanged_until_successful_retry(self):
        before = self.resources();owner = self.victory()
        with patch.object(self.game.lattice_progression, 'award_battle_rewards', return_value=False):
            spoils = wait_for_spoils(self.game)
            self.assertFalse(spoils.ready)
            self.assertEqual(self.resources(), before)
        self.assertTrue(owner._award_spoils())
        self.assertEqual(self.resources()['mira'], (0, 17))
        self.assertEqual(self.resources()['lucan'], (61, 3))

    def test_party_victory_requires_matching_active_formation_resources_and_caelan_alias(self):
        owner = self.victory();saved = json.loads(self.path.read_text())
        for mutate in (
            lambda record: record.pop('party_before'),
            lambda record: record['party_resources']['caelan'].update(hp=1),
            lambda record: record['party_resources']['mira'].update(mp=999),
            lambda record: record['party_before'].pop('lucan'),
            lambda record: record.update(party_active=['caelan', 'lucan', 'mira']),
        ):
            record = owner.snapshot();mutate(record)
            self.assertFalse(valid_pending_snapshot(record, saved), record)
        altered = deepcopy(saved)
        altered['party']['characters']['mira']['current_hp'] -= 1
        self.assertFalse(valid_pending_snapshot(owner.snapshot(), altered))

    def test_caelan_first_aid_applies_when_an_optional_battle_companion_wins(self):
        owner = self.start()
        owner.model.player.hp = 0
        owner.model.combatant('mira').hp = 100
        owner.model.enemy.hp = 0;owner.model.phase = 'victory'
        self.assertTrue(owner._begin_victory())
        self.assertTrue(owner.snapshot()['incapacitated'])
        self.assertTrue(wait_for_spoils(self.game).ready)
        self.assertEqual(self.game.attributes.current_hp, self.game.attributes.value('hp')//4)
        self.assertEqual(self.resources()['mira'], (100, 21))
        self.assertTrue(valid_pending_snapshot(owner.snapshot(), json.loads(self.path.read_text())))


if __name__ == '__main__':unittest.main()
