"""Durable victory facts and retry-safe Spoils checkpoint boundaries."""
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

from aether_lattice import MAX_RP
from inventory import MAX_QUANTITY
from main import Game
from post_battle import valid_pending_snapshot
from test_mill_battle_gameplay import seed_completed_mill


class VictoryCheckpointTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix='victory-checkpoints-')
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        self.path = self.directory/'journey.json'
        self.game = Game(window_size=(960, 640), fullscreen=False,
                         start_on_title=False, save_path=self.path,
                         settings_path=self.directory/'settings.json')
        self.game.audio.set_music(0);self.game.audio.set_effects(0)
        seed_completed_mill(self.game)
        pygame.event.clear()

    def tearDown(self):pygame.quit()

    def victory(self):
        game = self.game
        game.player.position.update(game.combat.position+(0, 24))
        game.player.facing = 'back';game.camera.reset()
        self.assertTrue(game.combat.interact())
        while game.combat.transitioning:game.update(.1, (0, 0), False)
        game.combat.model.player.hp -= 7
        game.combat.model.enemy.hp = 0
        game.combat.model.phase = 'victory'
        game.update(0, (0, 0), False)
        self.assertEqual(game.combat.post_phase, 'banner')
        return game.combat

    def show_spoils(self):
        for _ in range(30):
            if self.game.combat.post_phase == 'spoils':return
            self.game.update(.1, (0, 0), False)
        self.fail('Spoils did not appear')

    def test_victory_checkpoint_precedes_grants_and_validates_with_whole_journey(self):
        owner = self.victory()
        record = owner.snapshot()
        self.assertEqual(record['stage'], 'pending')
        self.assertEqual(self.game.lattice.state()['rp'], 0)
        self.assertEqual(self.game.inventory.quantity('aether_emerald'), 0)
        data = json.loads(self.path.read_text())
        self.assertTrue(valid_pending_snapshot(record, data))
        self.assertIsNotNone(self.game._read_saved_journey())
        self.show_spoils()
        self.assertTrue(owner.spoils.ready)
        self.assertEqual(owner.snapshot()['stage'], 'awarded')
        self.assertTrue(self.game.lattice.has_receipt(record['receipt']))
        self.assertTrue(valid_pending_snapshot(owner.snapshot(), json.loads(self.path.read_text())))

    def test_saved_pending_record_cannot_invent_rewards_resources_or_receipt_state(self):
        owner = self.victory()
        data = json.loads(self.path.read_text())
        for mutate in (
            lambda r:r['rewards'].update(rp=999),
            lambda r:r['rewards']['drops'].update(aether_diamond=1),
            lambda r:r['resources'].update(hp=9999),
            lambda r:r.update(stage='awarded'),
            lambda r:r.update(receipt='battle:made_up'),
            lambda r:r.update(extra='unrecognized'),
        ):
            record = owner.snapshot();mutate(record)
            self.assertFalse(valid_pending_snapshot(record, data), record)

    def test_awarded_record_requires_applied_resources_and_actual_receipt(self):
        owner = self.victory();self.show_spoils()
        record = owner.snapshot();data = json.loads(self.path.read_text())
        self.assertTrue(valid_pending_snapshot(record, data))
        bad = deepcopy(data);bad['aether_lattice']['receipts'].remove(record['receipt'])
        self.assertFalse(valid_pending_snapshot(record, bad))
        bad = deepcopy(data);bad['character_attributes']['current_hp'] += 1
        self.assertFalse(valid_pending_snapshot(record, bad))

    def test_failed_award_checkpoint_retries_save_without_granting_again(self):
        owner = self.victory()
        with patch.object(self.game.save_store, 'write', return_value=False):
            self.show_spoils()
            self.assertEqual(owner.snapshot()['stage'], 'awarded')
            self.assertFalse(owner.spoils.ready)
            self.assertIn('saved', owner.spoils.result_error)
            self.assertEqual(self.game.lattice.state()['rp'], 20)
            self.assertEqual(self.game.inventory.quantity('aether_emerald'), 1)
        with patch.object(self.game.lattice_progression, 'award_battle_rewards', side_effect=AssertionError('duplicate grant')):
            owner.spoils.retry_requested = True
            self.game.update(0, (0, 0), False)
        self.assertTrue(owner.spoils.ready)
        self.assertTrue(valid_pending_snapshot(owner.snapshot(), json.loads(self.path.read_text())))

    def test_failed_victory_checkpoint_defers_all_grants_until_retry(self):
        with patch.object(self.game.save_store, 'write', return_value=False):
            owner = self.victory();self.show_spoils()
            self.assertEqual(owner.snapshot()['stage'], 'pending')
            self.assertFalse(owner.spoils.ready)
            self.assertEqual(self.game.lattice.state()['rp'], 0)
        owner.spoils.retry_requested = True
        self.game.update(0, (0, 0), False)
        self.assertTrue(owner.spoils.ready)
        self.assertEqual(self.game.lattice.state()['rp'], 20)

    def test_failed_exit_checkpoint_keeps_screen_and_already_awarded_receipt(self):
        owner = self.victory();self.show_spoils()
        receipt = owner.receipt_id
        with patch.object(self.game.save_store, 'write', return_value=False):
            owner.spoils.dismissed = True
            self.game.update(0, (0, 0), False)
            self.assertTrue(owner.active)
            self.assertIsNotNone(owner.snapshot())
            self.assertFalse(owner.spoils.ready)
        owner.spoils.retry_requested = True
        self.game.update(0, (0, 0), False)
        self.assertTrue(owner.spoils.ready)
        owner.spoils.dismissed = True
        self.game.update(0, (0, 0), False)
        self.assertFalse(owner.active)
        self.assertNotIn('post_battle', json.loads(self.path.read_text()))
        self.assertEqual(self.game.lattice.state()['rp'], 20)
        self.assertTrue(self.game.lattice.has_receipt(receipt))

    def test_zero_room_spoils_register_empty_receipt_without_overflow(self):
        self.assertTrue(self.game.award_battle_rewards('fixture:full', {'caelan': MAX_RP},
                                                       {'aether_emerald': MAX_QUANTITY}))
        owner = self.victory();self.show_spoils()
        self.assertEqual(owner.snapshot()['rewards'], {'rp': 0, 'drops': {}})
        self.assertTrue(owner.spoils.ready)
        self.assertTrue(self.game.lattice.has_receipt(owner.receipt_id))
        self.assertEqual(self.game.lattice.state()['rp'], MAX_RP)
        self.assertEqual(self.game.inventory.quantity('aether_emerald'), MAX_QUANTITY)
        self.assertTrue(valid_pending_snapshot(owner.snapshot(), json.loads(self.path.read_text())))


if __name__ == '__main__':unittest.main()
