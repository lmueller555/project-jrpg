"""Discovery receipts, modal boundaries and atomic reward failure."""
import copy
import os
from types import SimpleNamespace as NS
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
import pygame

from inventory import Inventory
from sanctuary_cave import SanctuaryCave, REWARDS


class CaveFixture:
    def __init__(self):
        self.size = (240, 180)
        self.blocked = pygame.Mask(self.size)
        self.data = {'id': 'sanctuary_cave', 'cave': {'treasures': [
            {'id': 'cave_vein_cache', 'position': [120, 70], 'approach': [120, 90],
             'reward_id': 'cave_vein_cache', 'label': 'the supply box'}]}}
        self.entities = [{'id': 'cave_vein_cache', 'state': 'closed'}]

    def set_entity_state(self, identifier, state):
        next(item for item in self.entities if item['id'] == identifier)['state'] = state


class CaveControllerTests(unittest.TestCase):
    def setUp(self):
        self.messages = []
        social = NS(locked=False)
        def speak(lines, **kwargs):
            self.messages.append(lines)
            social.locked = True
            return True
        social.start_script = speak
        world = CaveFixture()
        self.game = NS(world=world, scenes={'cave': world}, inventory=Inventory(),
                       on_title=False, social=social, pause=NS(is_open=False),
                       inventory_ui=NS(is_open=False), party_ui=NS(is_open=False),
                       world_map_viewer=NS(is_open=False), map_open=False,
                       quest_ui=NS(journal_open=False), combat=NS(active=False),
                       transfer_cooldown=0, opening_fade=0, household_action=False,
                       opening=NS(locks_player=False), opening_cinematic=NS(active=False),
                       player=NS(position=pygame.Vector2(120, 90), moving=True))
        self.checkpoints = []
        self.game.save_progress = lambda: self.checkpoints.append(self.scene.to_dict())
        self.scene = SanctuaryCave(self.game)

    def test_collection_receipt_is_durable_even_if_dialogue_cancelled(self):
        self.assertIn('Open', self.scene.interaction_hint())
        self.assertTrue(self.scene.interact())
        self.assertEqual(self.game.inventory.quantity('aether_sapphire'), 1)
        self.assertEqual(self.game.world.entities[0]['state'], 'open')
        self.assertEqual(self.checkpoints, [{'version': 1, 'opened': ['cave_vein_cache']}])
        self.game.social.locked = False  # Dismissing the receipt accepts no story.
        self.assertIn('Examine', self.scene.interaction_hint())
        self.assertTrue(self.scene.interact())
        self.assertEqual(self.game.inventory.quantity('aether_sapphire'), 1)
        self.assertEqual(len(self.checkpoints), 1)
        self.assertEqual(self.messages[-1][0]['text'], 'The container is empty.')

    def test_failed_atomic_inventory_grant_keeps_container_closed(self):
        self.game.inventory.add('aether_sapphire', 999999)
        before = self.game.inventory.to_dict()
        self.assertTrue(self.scene.interact())
        self.assertEqual(self.game.inventory.to_dict(), before)
        self.assertEqual(self.game.world.entities[0]['state'], 'closed')
        self.assertFalse(self.scene.opened)
        self.assertFalse(self.checkpoints)

    def test_modal_and_wall_boundaries_prevent_remote_opening(self):
        self.game.pause.is_open = True
        self.assertFalse(self.scene.interact())
        self.game.pause.is_open = False
        self.game.player.position.update(100, 90)
        for y in range(self.game.world.size[1]):self.game.world.blocked.set_at((110, y))
        self.assertFalse(self.scene.interact())
        self.assertFalse(self.scene.opened)
        self.assertFalse(self.game.inventory.entries())

    def test_restore_is_atomic_and_new_game_resets_cached_container_art(self):
        snapshot = {'version': 1, 'opened': ['cave_vein_cache']}
        self.assertTrue(self.scene.restore(snapshot))
        self.assertEqual(self.game.world.entities[0]['state'], 'open')
        malformed = copy.deepcopy(snapshot)
        malformed['opened'].append('unknown')
        self.assertFalse(self.scene.restore(malformed))
        self.assertEqual(self.scene.to_dict(), snapshot)
        self.scene.reset()
        self.assertEqual(self.game.world.entities[0]['state'], 'closed')
        self.assertEqual(self.scene.to_dict(), {'version': 1, 'opened': []})

    def test_save_validation_rejects_duplicate_unknown_and_malformed_receipts(self):
        valid = {'version': 1, 'opened': list(REWARDS)}
        self.assertTrue(self.scene.valid_snapshot(valid))
        for record in ({'version': True, 'opened': []}, {'version': 1, 'opened': None},
                       {'version': 1, 'opened': [[]]}, {'version': 1, 'opened': ['unknown']},
                       {'version': 1, 'opened': ['cave_vein_cache']*2},
                       {'version': 1, 'opened': [], 'extra': 0}):
            with self.subTest(record=record):self.assertFalse(self.scene.valid_snapshot(record))
        self.assertTrue(self.scene.valid_journey({'player': {'scene': 'eldenmere'}}))
        self.assertFalse(self.scene.valid_journey({'player': {'scene': 'sanctuary_cave'}}))
        self.assertTrue(self.scene.valid_journey({'player': {'scene': 'sanctuary_cave'},
                                                  'sanctuary_cave': valid}))
        self.assertFalse(self.scene.valid_journey({'player': []}))


if __name__ == '__main__':unittest.main()
