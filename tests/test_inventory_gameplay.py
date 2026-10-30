"""Real inventory input, acceptance, migration, delivery and save boundaries."""
import json
import os
from pathlib import Path
import tempfile
import unittest

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame
import main
from inventory import Inventory
from quests import OPENING_QUEST


class InventoryGameplayTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name)/'journey.json'
        self.game = self.new_game()
        pygame.event.clear()

    def tearDown(self):pygame.quit()

    def new_game(self, title=False):
        game = main.Game(fullscreen=False, start_on_title=title, save_path=self.path)
        game.audio.set_music(0)
        game.audio.set_effects(0)
        return game

    def key(self, key):
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=key, repeat=False))
        self.assertTrue(self.game.handle_events())

    def click(self, logical):
        width, height = self.game.window.get_size()
        scale = max(1, min(width//480, height//320))
        point = ((width-480*scale)//2+logical[0]*scale, (height-320*scale)//2+logical[1]*scale)
        for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            pygame.event.post(pygame.event.Event(kind, button=1, pos=point))
        self.assertTrue(self.game.handle_events())

    def offer(self):
        self.game.world = self.game._scene_by_id('sanctuary_dining')
        self.game.player.position.update(288, 231)
        actor = next(n for n in self.game.persistent_npcs if n.data['id'] == 'mother_serene')
        self.assertTrue(self.game.social.start(actor))
        for _ in range(80):
            if self.game.social.choosing:return
            self.game.social.advance()
        self.fail('No quest acceptance choices')

    def test_clicked_acceptance_grants_supplies_and_checkpoints_once(self):
        self.offer()
        self.click(self.game.social.choice_rects[0].center)
        self.assertEqual(self.game.inventory.quantity('halden_medicine'), 1)
        self.assertEqual(len(self.game.inventory.entries('key_items')), 3)
        self.assertFalse(self.game.accept_quest(OPENING_QUEST))
        saved = json.loads(self.path.read_text())
        self.assertEqual(saved['inventory'], self.game.inventory.to_dict())
        restored = self.new_game(title=True)
        self.assertTrue(restored.begin_journey(True))
        self.assertEqual(restored.inventory.quantity('halden_medicine'), 1)

    def test_decline_or_walkaway_does_not_grant_items(self):
        self.offer()
        self.click(self.game.social.choice_rects[1].center)
        self.assertEqual(self.game.inventory.entries(), [])
        self.offer()
        self.game.player.position.update(288, 280)
        self.game.update(0, (0, 0), False)
        self.assertEqual(self.game.inventory.entries(), [])
        self.assertEqual(self.game.quests.status(OPENING_QUEST), 'available')

    def test_delivery_removes_medicine_once_and_preserves_other_halden_tasks(self):
        self.assertTrue(self.game.accept_quest(OPENING_QUEST))
        before = self.game.inventory.to_dict()
        self.assertFalse(self.game.deliver_quest_item(OPENING_QUEST, 'elira', 'elira'))
        self.assertFalse(self.game.deliver_quest_item(OPENING_QUEST, 'halden', 'elira'))
        self.assertEqual(self.game.inventory.to_dict(), before)
        self.assertTrue(self.game.deliver_quest_item(OPENING_QUEST, 'halden', 'halden'))
        self.assertEqual(self.game.inventory.quantity('halden_medicine'), 0)
        self.assertEqual(self.game.quests.objective_status(OPENING_QUEST, 'halden'), 'active')
        self.assertFalse(self.game.deliver_quest_item(OPENING_QUEST, 'halden', 'halden'))
        restored = self.new_game(title=True)
        self.assertTrue(restored.begin_journey(True))
        self.assertEqual(restored.inventory.quantity('halden_medicine'), 0)
        self.assertTrue(restored.inventory.was_delivered(OPENING_QUEST, 'halden'))
        self.assertEqual(restored.inventory.quantity('elira_supplies'), 1)

    def test_old_saves_receive_only_outstanding_supplies_quietly(self):
        for completed in ([], ['halden'], ['halden', 'elira', 'venn']):
            with self.subTest(completed=completed):
                game = self.new_game()
                game.quests.accept(OPENING_QUEST)
                for objective in completed:game.quests.complete_objective(OPENING_QUEST, objective)
                game.save_progress()
                saved = json.loads(self.path.read_text())
                saved.pop('inventory')
                self.path.write_text(json.dumps(saved))
                restored = self.new_game(title=True)
                self.assertTrue(restored.begin_journey(True))
                for objective, item in (('halden', 'halden_medicine'), ('elira', 'elira_supplies'), ('venn', 'venn_supplies')):
                    self.assertEqual(restored.inventory.quantity(item), 0 if objective in completed else 1)
                self.assertIsNone(restored.quest_ui.current_notice)

    def test_invalid_inventory_keeps_existing_save_intact(self):
        self.game.accept_quest(OPENING_QUEST)
        self.game.save_progress()
        saved = json.loads(self.path.read_text())
        saved['inventory']['items']['halden_medicine'] = -1
        raw = json.dumps(saved)
        self.path.write_text(raw)
        restored = self.new_game(title=True)
        self.assertFalse(restored.has_saved_journey)
        self.assertIsNotNone(restored.save_error)
        self.assertEqual(self.path.read_text(), raw)

    def test_inventory_is_modal_and_all_categories_work_at_large_text(self):
        self.game.accept_quest(OPENING_QUEST)
        self.game.audio.set_text_scale(1.5)
        self.key(pygame.K_i)
        before = (self.game.elapsed_ms, self.game.player.position.copy())
        self.game.update(2, (1, 0), True)
        self.assertEqual((self.game.elapsed_ms, self.game.player.position), before)
        for size in ((480, 320), (1440, 810), (1920, 1080)):
            self.game.window = pygame.display.set_mode(size)
            for index, tab in enumerate(self.game.inventory_ui.tabs):
                self.click(tab.center)
                self.game.draw()
                self.assertEqual(self.game.inventory_ui.category_index, index)
                self.assertTrue(pygame.Rect(0, 0, 480, 320).contains(tab))
        self.click(self.game.inventory_ui.close_rect.center)
        self.assertFalse(self.game.inventory_ui.is_open)

    def test_pause_inventory_returns_to_pause_and_cannot_advance_dialogue(self):
        self.offer()
        page = self.game.social.page_index
        self.key(pygame.K_ESCAPE)
        self.click(self.game.pause.rows[self.game.pause.options.index('Inventory')].center)
        self.assertTrue(self.game.inventory_ui.is_open)
        self.assertEqual(self.game.pause.overlay, 'inventory')
        self.key(pygame.K_ESCAPE)
        self.assertFalse(self.game.inventory_ui.is_open)
        self.assertTrue(self.game.pause.is_open)
        self.assertIsNone(self.game.pause.overlay)
        self.assertEqual(self.game.social.page_index, page)
        self.key(pygame.K_ESCAPE)
        self.assertFalse(self.game.pause.is_open)

    def test_ordinary_room_visits_never_consume_supplies(self):
        self.game.accept_quest(OPENING_QUEST)
        before = self.game.inventory.to_dict()
        for scene in ('halden', 'elira', 'venn'):
            self.game.world = self.game._scene_by_id(scene)
            self.game.player.position.update(self.game.world.data['spawn'])
            self.game.update(0, (0, 0), False)
            self.assertEqual(self.game.inventory.to_dict(), before)

    def test_acceptance_checkpoint_contains_supplies_before_followup_scene(self):
        self.game.world = self.game._scene_by_id('sanctuary_dining')
        self.game.player.position.update(288, 231)
        self.game.opening.restore({'version': 1, 'stage': 'assignment'})
        self.offer()
        self.click(self.game.social.choice_rects[0].center)
        saved = json.loads(self.path.read_text())
        self.assertEqual(saved['opening']['stage'], 'acceptance')
        self.assertEqual(saved['inventory']['items']['halden_medicine'], 1)
        self.assertEqual(self.game.social.script_identifier, 'opening_acceptance')

    def test_missing_granted_supplies_without_delivery_receipt_are_invalid(self):
        self.game.accept_quest(OPENING_QUEST)
        self.game.save_progress()
        saved = json.loads(self.path.read_text())
        saved['inventory']['items'].pop('halden_medicine')
        self.path.write_text(json.dumps(saved))
        restored = self.new_game(title=True)
        self.assertFalse(restored.has_saved_journey)

    def test_new_game_resets_items_and_delivery_receipts(self):
        self.game.accept_quest(OPENING_QUEST)
        self.game.deliver_quest_item(OPENING_QUEST, 'halden', 'halden')
        self.assertTrue(self.game.begin_journey(False, show_cinematic=False))
        self.assertEqual(self.game.inventory.entries(), [])
        self.assertFalse(self.game.inventory.was_delivered(OPENING_QUEST, 'halden'))
        self.assertEqual(self.game.quests.status(OPENING_QUEST), 'available')

    def test_inventory_close_consumes_queued_clicks_before_underlying_offer(self):
        self.offer()
        self.key(pygame.K_i)
        self.assertTrue(self.game.inventory_ui.is_open)
        width, height = self.game.window.get_size()
        scale = max(1, min(width//480, height//320))
        for logical in (self.game.inventory_ui.close_rect.center, self.game.social.choice_rects[0].center):
            point = ((width-480*scale)//2+logical[0]*scale, (height-320*scale)//2+logical[1]*scale)
            for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
                pygame.event.post(pygame.event.Event(kind, button=1, pos=point))
        self.game.handle_events()
        self.assertFalse(self.game.inventory_ui.is_open)
        self.assertTrue(self.game.social.choosing)
        self.assertEqual(self.game.inventory.entries(), [])
        self.assertEqual(self.game.quests.status(OPENING_QUEST), 'available')

    def test_future_equipment_and_item_definitions_render_without_gameplay_stubs(self):
        catalog=Inventory().catalog
        for identifier,category in (('sword','weapons'),('coat','armor'),('tonic','items')):
            catalog['items'][identifier]={'name':identifier.title(), 'category':category,
                                          'description':'A test definition for the item catalog.'}
        catalog['items']['sword'].update(equipment_slot='weapon',stats={'attack':3})
        self.game.inventory=Inventory(catalog)
        for item in ('sword','coat','tonic'):self.game.inventory.add(item,2)
        self.game.inventory_ui.open()
        self.game.window=pygame.display.set_mode((480,320))
        self.game.audio.set_text_scale(1.5)
        for index,identifier in enumerate(('sword','coat','tonic')):
            self.click(self.game.inventory_ui.tabs[index].center)
            self.game.draw()
            self.assertEqual(self.game.inventory_ui.selected,identifier)
            self.assertEqual(self.game.inventory.quantity(identifier),2)


if __name__ == '__main__':unittest.main()
