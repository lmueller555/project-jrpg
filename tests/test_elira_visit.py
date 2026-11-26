"""Elira's live dialogue, actual stool/table interactions and durable ownership."""
import copy
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
from elira_visit import EliraVisit, STOOL_APPROACH, TABLE_APPROACH, TABLE_LANTERN
from npc_routines import find_path
from quests import OPENING_QUEST as QUEST


class EliraGameplayTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name)/'journey.json'
        self.game = self.make_game();self.visit = self.game.elira_visit

    def tearDown(self):pygame.quit()

    def make_game(self, title=False):
        game = main.Game(fullscreen=False, start_on_title=title, save_path=self.path,
                         settings_path=Path(self.directory.name)/'settings.json')
        game.audio.set_music(0);game.audio.set_effects(0);pygame.event.clear()
        return game

    def wait(self, seconds=1):
        for _ in range(round(seconds*60)):self.game.update(1/60, (0, 0), False)

    def key(self, key):
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=key, repeat=False))
        self.assertTrue(self.game.handle_events())

    def click(self):
        for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            pygame.event.post(pygame.event.Event(kind, button=1, pos=(2, 2)))
        self.assertTrue(self.game.handle_events())

    def finish_dialogue(self):
        for _ in range(80):
            if not self.game.social.active:return
            self.click()
        self.fail('Elira dialogue did not end')

    def ready(self):
        self.game.accept_quest(QUEST);self.game.quests.complete_objective(QUEST, 'halden')
        self.game._sync_inventory();self.game.halden_visit.restore()
        self.game.world = self.visit.home;self.game.player.position.update(210, 224)
        self.game.player.facing = 'back';self.game.transfer_cooldown = 0
        self.game.update(0, (0, 0), False)

    def deliver(self):
        self.ready();self.assertTrue(self.game.social.start(self.visit.elira))
        self.finish_dialogue();self.wait()
        self.assertTrue(self.visit.delivered)

    def walk(self, target, new_scene=None):
        game = self.game;world = game.world
        route = find_path(world, game.player.position, target, world.probe_size, None)
        self.assertIsNotNone(route, (world.data['id'], tuple(game.player.position), target))
        for corner in route:
            for _ in range(700):
                if game.world is not world:
                    self.assertEqual(game.world.data['id'], new_scene);return
                delta = pygame.Vector2(corner)-game.player.position
                if delta.length()<.03:break
                game.update(min(1/30, delta.length()/main.WALK_SPEED), delta, False)
                self.assertTrue(game.world is not world or world.can_stand(game.player.position))
            else:self.fail(('Walk stalled', game.world.data['id'], tuple(game.player.position), corner))
        if new_scene:
            for _ in range(90):
                if game.world is not world:break
                game.update(1/60, (0, 1), False)
            self.assertEqual(game.world.data['id'], new_scene)

    def retrieve(self):
        self.walk(STOOL_APPROACH);self.key(pygame.K_e)
        self.assertEqual(self.visit.action, 'retrieve');self.wait(2.7)
        self.assertEqual(self.visit.lantern, 'carried');self.assertIsNone(self.visit.action)

    def place(self):
        self.walk(TABLE_APPROACH);self.key(pygame.K_e)
        self.assertEqual(self.visit.action, 'place');self.wait(1)
        self.assertEqual(self.visit.lantern, 'table')

    def resolve(self):
        self.walk((210, 216))
        if not self.game.social.active:
            self.game.social.blocked.discard(self.visit.elira)
            self.assertTrue(self.game.social.start(self.visit.elira))
        self.assertEqual(self.game.social.script_identifier, 'elira_resolution')
        self.finish_dialogue()

    def test_queued_household_cannot_deliver_or_retrieve_and_visits_do_nothing(self):
        self.game.accept_quest(QUEST);self.game._sync_inventory()
        self.game.world = self.visit.home;self.game.player.position.update(STOOL_APPROACH)
        before = self.game.inventory.to_dict();self.key(pygame.K_e);self.wait(1)
        self.assertFalse(self.visit.delivered);self.assertEqual(self.visit.lantern, 'shelf')
        self.assertEqual(self.game.inventory.to_dict(), before)
        self.assertEqual(self.game.quests.objective_status(QUEST, 'elira'), 'queued')
        self.assertIsNone(self.visit.action)

    def test_actual_proximity_uses_elira_portrait_and_live_movement(self):
        self.ready()
        for _ in range(10):
            if self.game.social.active:break
            self.game.update(1/60, (0, -1), False)
        self.assertEqual(self.game.social.script_identifier, 'elira_arrival')
        self.assertEqual(self.game.social.page['speaker'], 'elira')
        self.assertIs(self.game.social.resolve_speaker(), self.visit.elira)
        self.assertIn('elira', self.game.social.portraits)
        previous = self.game.player.position.copy()
        self.game.update(.1, (1, 0), False)
        self.assertGreater(self.game.player.position.x, previous.x)
        self.assertFalse(self.game.household_action);self.assertTrue(self.game.social.active)

    def test_enter_cottage_through_animated_door_and_approach_elira(self):
        self.ready();self.game.world = self.game.town
        self.game.player.position.update(672, 994);self.game.player.facing = 'back'
        for _ in range(120):
            if self.game.world is self.visit.home:break
            self.game.update(1/60, (0, -1), False)
        self.assertIs(self.game.world, self.visit.home)
        self.walk((210, 216))
        self.assertEqual(self.game.social.script_identifier, 'elira_arrival')
        self.assertEqual(self.game.inventory.quantity('elira_supplies'), 1)

    def test_unread_arrival_and_walkaway_never_consume_supplies(self):
        self.ready();self.game.social.start(self.visit.elira)
        self.game.player.position.update(244, 256);self.game.update(0, (0, 0), False)
        self.assertFalse(self.game.social.locked);self.assertIsNone(self.visit.dialogue)
        self.assertEqual(self.game.inventory.quantity('elira_supplies'), 1)
        self.assertFalse(self.visit.delivered);self.assertIsNone(self.visit.action)

    def test_delivery_contact_consumes_only_elira_bundle_once(self):
        self.ready();self.game.social.start(self.visit.elira);self.finish_dialogue()
        self.wait(.3);self.assertEqual(self.game.inventory.quantity('elira_supplies'), 1)
        self.wait(.2);self.assertEqual(self.game.inventory.quantity('elira_supplies'), 0)
        self.assertTrue(self.visit.delivered)
        self.assertEqual(self.game.inventory.quantity('venn_supplies'), 1)
        self.assertEqual(self.game.quests.objective_status(QUEST, 'elira'), 'active')
        self.assertFalse(self.game.deliver_quest_item(QUEST, 'elira', 'elira'))
        self.wait();self.assertTrue(self.visit.surface_prop_visible(self.visit.surface_props[1]))

    def test_stool_contact_preserves_lantern_pixels_and_ownership(self):
        self.deliver();self.walk(STOOL_APPROACH);self.key(pygame.K_e)
        # At the last reach and first take pose the lantern is on the same pixels.
        self.visit.aligning = False;self.visit.action_time = 1.149
        self.game.update(0, (0, 0), False)
        before = pygame.Surface(self.visit.home.size)
        self.visit.home.draw(before, (0, 0), self.game.player, self.game.elapsed_ms)
        self.assertEqual(self.visit.lantern, 'shelf')
        self.visit.action_time = 1.15;self.game.update(0, (0, 0), False)
        after = pygame.Surface(self.visit.home.size)
        self.visit.home.draw(after, (0, 0), self.game.player, self.game.elapsed_ms)
        region = pygame.Rect(132, 22, 48, 65)
        self.assertEqual(pygame.image.tobytes(before.subsurface(region), 'RGB'),
                         pygame.image.tobytes(after.subsurface(region), 'RGB'))
        self.assertEqual(self.visit.lantern, 'carried')
        self.assertEqual(next(e for e in self.visit.home.entities if e['id']=='lantern_shelf')['state'], 'empty')
        self.assertFalse(self.visit.surface_prop_visible(self.visit.surface_props[0]))
        self.assertTrue(self.visit.home.can_stand(self.game.player.position))
        self.assertEqual(tuple(self.game.player.position), STOOL_APPROACH)
        self.wait(1.5);self.assertFalse(hasattr(self.game.player, 'story_position'))

    def test_full_retrieval_placement_and_read_resolution_complete_only_elira(self):
        self.deliver();self.retrieve();self.place()
        self.assertEqual(self.game.quests.objective_status(QUEST, 'elira'), 'active')
        self.assertEqual(self.game.quests.objective_status(QUEST, 'venn'), 'active')
        self.assertEqual(self.game.inventory.quantity('venn_supplies'), 1)
        self.resolve()
        self.assertEqual(self.game.quests.objective_status(QUEST, 'elira'), 'completed')
        self.assertEqual(self.game.quests.status(QUEST), 'active')
        self.assertIn('CH01_MQ01_ELIRA_DONE', self.game.social.flags)
        self.assertIsNone(self.visit._target());self.assertFalse(self.visit.interact())
        self.assertFalse(hasattr(self.game.player, 'story_sprite'))
        self.assertEqual(self.visit.surface_props[0]['position'], list(TABLE_LANTERN))
        self.game.draw()

    def test_walking_away_from_resolution_preserves_table_without_completing(self):
        self.deliver();self.retrieve();self.place();self.walk((210, 224))
        if not self.game.social.active:self.game.social.start(self.visit.elira)
        self.assertEqual(self.game.social.script_identifier, 'elira_resolution')
        self.game.player.position.update(246, 280);self.game.update(0, (0, 0), False)
        self.assertFalse(self.game.social.locked)
        self.assertEqual(self.visit.lantern, 'table')
        self.assertEqual(self.game.quests.objective_status(QUEST, 'elira'), 'active')
        self.game.player.position.update(210, 224);self.game.social.blocked.discard(self.visit.elira)
        self.game.social.start(self.visit.elira);self.finish_dialogue()
        self.assertTrue(self.visit.completed)

    def test_leaving_house_carrying_does_not_drop_duplicate_or_complete(self):
        self.deliver();self.retrieve();self.walk((102, 306), new_scene='eldenmere.playable')
        self.assertEqual(self.visit.lantern, 'carried')
        self.assertEqual(self.game.quests.objective_status(QUEST, 'elira'), 'active')
        self.game.update(.1, (1, 0), False);self.game.draw()
        self.assertIsNotNone(getattr(self.game.player, 'story_sprite', None))
        self.assertFalse(self.visit.surface_prop_visible(self.visit.surface_props[0]))
        self.assertEqual(sum(self.visit.elira in w.npcs for w in self.game.scenes.values()), 1)

    def test_reload_at_each_boundary_retains_one_lantern_and_supply_receipt(self):
        self.deliver()
        for stage in ('shelf', 'carried', 'table', 'completed'):
            if stage == 'carried':self.retrieve()
            if stage == 'table':self.place()
            if stage == 'completed':self.resolve()
            self.game.save_progress();restored = self.make_game(True)
            self.assertTrue(restored.begin_journey(True), stage)
            visit = restored.elira_visit
            self.assertEqual(visit.lantern, 'table' if stage == 'completed' else stage)
            self.assertEqual(restored.inventory.quantity('elira_supplies'), 0)
            self.assertTrue(visit.delivered)
            self.assertEqual(visit.completed, stage == 'completed')
            self.assertEqual(sum(visit.elira in w.npcs for w in restored.scenes.values()), 1)
            self.assertFalse(restored.halden_visit.owns_tomas)
            restored.draw()
            # Keep the production game used by the next stage current.
            self.game = restored;self.visit = visit;self.game.opening_fade = 0

    def test_interrupted_climb_resumes_safely_on_floor_on_either_side_of_contact(self):
        self.deliver()
        for elapsed, expected in ((.8, 'shelf'), (1.4, 'carried')):
            self.visit.restore({'version': 1, 'lantern': 'shelf'})
            self.game.player.position.update(STOOL_APPROACH);self.visit.interact()
            self.wait(elapsed);self.game.save_progress()
            restored = self.make_game(True);self.assertTrue(restored.begin_journey(True))
            self.assertEqual(restored.elira_visit.lantern, expected)
            self.assertFalse(hasattr(restored.player, 'story_position'))
            self.assertTrue(restored.world.can_stand(restored.player.position))
            self.assertIsNone(restored.elira_visit.action)

    def test_pause_and_inventory_freeze_retrieval(self):
        self.deliver();self.walk(STOOL_APPROACH);self.key(pygame.K_e);self.wait(.5)
        time = self.visit.action_time;position = self.game.player.story_position
        self.key(pygame.K_ESCAPE);self.game.update(5, (1, 0), False)
        self.assertEqual(self.visit.action_time, time);self.assertEqual(self.game.player.story_position, position)
        self.key(pygame.K_ESCAPE);self.key(pygame.K_i);self.game.update(5, (1, 0), False)
        self.assertEqual(self.visit.action_time, time);self.assertEqual(self.visit.lantern, 'shelf')
        self.key(pygame.K_i);self.wait(2.5);self.assertEqual(self.visit.lantern, 'carried')

    def test_old_saves_without_local_record_migrate_delivered_and_completed_visits(self):
        self.deliver()
        for completed in (False, True):
            if completed:self.game.quests.complete_objective(QUEST, 'elira')
            self.game.save_progress();data = json.loads(self.path.read_text());data.pop('elira_visit')
            self.path.write_text(json.dumps(data));restored = self.make_game(True)
            self.assertTrue(restored.begin_journey(True))
            self.assertEqual(restored.elira_visit.lantern, 'table' if completed else 'shelf')
            self.assertEqual(restored.inventory.quantity('elira_supplies'), 0)

    def test_invalid_progress_never_overwrites_save_and_new_game_clears_local_facts(self):
        self.deliver();self.retrieve();self.game.save_progress()
        good = json.loads(self.path.read_text())
        variants = [dict(version=True, lantern='table'), dict(version=1, lantern='missing'),
                    dict(version=1, lantern=[])]
        for record in variants:self.assertFalse(EliraVisit.valid_snapshot(record))
        bad = copy.deepcopy(good);bad['inventory']['deliveries'].remove(QUEST+'/elira')
        bad['inventory']['items']['elira_supplies'] = 1
        raw = json.dumps(bad);self.path.write_text(raw)
        broken = self.make_game(True)
        self.assertFalse(broken.has_saved_journey);self.assertEqual(self.path.read_text(), raw)
        self.game.begin_journey(False)
        self.assertEqual(self.visit.lantern, 'shelf');self.assertFalse(self.visit.delivered)
        self.assertIsNone(self.visit.action);self.assertEqual(self.game.quests.status(QUEST), 'available')
        self.assertFalse(hasattr(self.game.player, 'story_position'))

    def test_venn_can_precede_elira_without_automatic_report_or_turn_in(self):
        self.deliver();self.game.quests.complete_objective(QUEST, 'venn')
        self.game._sync_inventory();self.retrieve();self.place();self.resolve()
        self.assertEqual(self.game.quests.status(QUEST), 'ready')
        self.assertEqual(self.game.quests.marker_for('mother_serene'), '?')
        self.assertNotEqual(self.game.quests.status(QUEST), 'completed')


if __name__ == '__main__':unittest.main()
