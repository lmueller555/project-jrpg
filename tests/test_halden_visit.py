"""Play the first household through production input, collision and checkpoints."""
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
from halden_visit import SOURCES, STORAGE, HaldenVisit, town_path
from npc_routines import find_path
from quests import OPENING_QUEST as QUEST


class HaldenGameplayTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name)/'journey.json'
        self.game = self.make_game();self.visit = self.game.halden_visit

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

    def finish_dialogue(self):
        for _ in range(100):
            if not self.game.social.active:return
            # Real click-to-advance, including letterboxing at the default size.
            for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
                pygame.event.post(pygame.event.Event(kind, button=1, pos=(2, 2)))
            self.assertTrue(self.game.handle_events())
        self.fail('Dialogue did not finish')

    def accepted(self, room='halden', position=(192, 200)):
        self.assertTrue(self.game.accept_quest(QUEST))
        self.game.world = self.game._scene_by_id(room)
        self.game.player.position.update(position)
        self.visit.restore();self.game.transfer_cooldown = 0
        self.game.quests.drain_events()
        self.game.update(0, (0, 0), False)

    def medicine(self):
        self.accepted()
        self.assertTrue(self.game.social.start(self.visit.halden))
        self.finish_dialogue();self.wait()
        self.assertTrue(self.visit.medicine)

    def walk(self, target, new_scene=None):
        game = self.game;world = game.world
        path = find_path(world, game.player.position, target, world.probe_size, None)
        self.assertIsNotNone(path, (world.data['id'], tuple(game.player.position), target))
        self.walk_path(path, new_scene)
        if new_scene and game.world is world:
            door = next(d for d in world.doors if pygame.Vector2(d.data['anchor']).distance_to(target)<2)
            direction = (0, -1) if door.data['entry_side'] == 'north' else (0, 1)
            for _ in range(90):
                if game.world is not world:break
                game.update(1/60, direction, False)
        if new_scene:self.assertEqual(game.world.data['id'], new_scene)

    def walk_path(self, path, new_scene=None):
        game = self.game;world = game.world
        for corner in path:
            for _ in range(1200):
                if game.world is not world:
                    self.assertEqual(game.world.data['id'], new_scene);return
                delta = pygame.Vector2(corner)-game.player.position
                if delta.length()<.05:break
                dt = min(1/30, delta.length()/main.WALK_SPEED)
                game.update(dt, delta, False)
                self.assertTrue(world.can_stand(game.player.position) or game.world is not world)
            else:self.fail(('Player stalled', game.world.data['id'], tuple(game.player.position), corner))

    def store_player_sack(self, i):
        self.walk((SOURCES[i][0], SOURCES[i][1]+18))
        self.key(pygame.K_e);self.wait(.8)
        self.assertEqual(self.visit.carried, i)
        self.walk((STORAGE[i][0], STORAGE[i][1]+22))
        self.key(pygame.K_e);self.wait(.8)
        self.assertIn(i, self.visit.stored);self.assertIsNone(self.visit.carried)

    def sacks(self):
        self.store_player_sack(0)
        self.walk((128, 292));self.key(pygame.K_e)
        self.assertEqual(self.visit.tomas_job, 'approach')
        self.walk((170, 210))
        for _ in range(1200):
            if self.visit.tomas_job is None:break
            self.game.update(1/60, (0, 0), False)
        self.assertIn(1, self.visit.stored)
        self.store_player_sack(2)

    def test_unaccepted_and_visits_alone_never_deliver_or_start_following(self):
        self.game.world = self.visit.home;self.game.player.position.update(178, 294)
        self.wait(1)
        self.assertFalse(self.visit.owns_tomas)
        self.accepted(position=(178, 294));before = self.game.inventory.to_dict()
        self.wait(4)
        self.assertEqual(self.game.inventory.to_dict(), before)
        self.assertEqual(self.visit.stored, set())
        self.assertEqual(self.game.quests.objective_status(QUEST, 'elira'), 'queued')

    def test_walkaway_from_arrival_does_not_consume_medicine(self):
        self.accepted();self.assertTrue(self.game.social.start(self.visit.halden))
        self.game.player.position.update(192, 246);self.game.update(0, (0, 0), False)
        self.assertFalse(self.game.social.locked);self.assertFalse(self.visit.medicine)
        self.assertEqual(self.game.inventory.quantity('halden_medicine'), 1)
        self.assertIsNone(self.visit.action)

    def test_handoff_removes_one_item_at_contact_and_never_completes_sacks(self):
        self.accepted();self.game.social.start(self.visit.halden);self.finish_dialogue()
        self.wait(.3);self.assertEqual(self.game.inventory.quantity('halden_medicine'), 1)
        self.wait(.2);self.assertEqual(self.game.inventory.quantity('halden_medicine'), 0)
        self.wait();self.assertEqual(self.game.quests.objective_status(QUEST, 'halden'), 'active')
        self.assertEqual(self.game.inventory.quantity('elira_supplies'), 1)
        self.assertEqual(self.game.inventory.quantity('venn_supplies'), 1)
        self.assertFalse(self.game.deliver_quest_item(QUEST, 'halden', 'halden'))

    def test_three_sacks_real_movement_and_goodbye_before_unlock(self):
        self.medicine();self.sacks()
        self.assertEqual(self.visit.stored, {0, 1, 2})
        self.assertEqual(self.game.quests.objective_status(QUEST, 'elira'), 'queued')
        self.walk((192, 198));self.wait(.5)
        if not self.game.social.active:
            self.game.social.blocked.discard(self.visit.halden)
            self.assertTrue(self.game.social.start(self.visit.halden))
        self.assertEqual(self.game.social.script_identifier, 'halden_conclusion')
        self.finish_dialogue();self.assertTrue(self.visit.concluded)
        self.assertEqual(self.game.quests.objective_status(QUEST, 'halden'), 'active')
        self.wait(.1)
        if not self.game.social.active:
            self.walk((round(self.visit.tomas.position.x/2)*2+24, round(self.visit.tomas.position.y/2)*2))
            self.wait(.1)
        self.assertEqual(self.game.social.script_identifier, 'halden_goodbye')
        self.finish_dialogue()
        self.assertEqual(self.game.quests.objective_status(QUEST, 'halden'), 'active')
        # Keep Caelan out of the exit path; departure is visible, not a teleport.
        self.walk((176, 210))
        for _ in range(1800):
            if self.game.quests.objective_status(QUEST, 'halden') == 'completed':break
            self.game.update(1/60, (0, 0), False)
        self.assertEqual(self.visit.tomas.scene_id, 'eldenmere.playable')
        self.assertEqual(self.game.quests.objective_status(QUEST, 'halden'), 'completed')
        self.assertEqual(self.game.quests.objective_status(QUEST, 'elira'), 'active')
        self.assertEqual(self.game.quests.objective_status(QUEST, 'venn'), 'active')
        self.assertIn('CH01_MQ01_TOMAS_DEPARTED', self.game.social.flags)
        before = self.game.quests.to_dict();self.wait(.2)
        self.assertEqual(self.game.quests.to_dict(), before)

    def test_tomas_carries_exactly_one_sack_and_lifts_with_conserved_prop(self):
        self.medicine();self.game.player.position.update(128, 292)
        self.key(pygame.K_e);self.game.player.position.update(176, 210)
        seen = set()
        for _ in range(1400):
            job = self.visit.tomas_job
            if job is None:break
            self.game.update(1/60, (0, 0), False);seen.add(job)
            prop = self.visit.surface_props[1]
            self.assertEqual(int(self.visit.surface_prop_visible(prop))+int(self.visit.tomas_held == 1), 1)
            self.assertTrue(self.visit.home.can_stand(self.visit.tomas.position, self.visit.tomas.probe_size, self.visit.tomas))
        self.assertEqual(seen, {'approach', 'lift', 'carry', 'store'})
        self.assertEqual(self.visit.stored, {1});self.assertIsNone(self.visit.carried)

    def test_checkpoint_restores_carried_and_stored_sacks_without_new_medicine(self):
        self.medicine();self.store_player_sack(0)
        self.walk((152, 292));self.key(pygame.K_e);self.wait(.8)
        self.game.save_progress();restored = self.make_game(True)
        self.assertTrue(restored.begin_journey(True))
        visit = restored.halden_visit
        self.assertEqual(visit.stored, {0});self.assertEqual(visit.carried, 2)
        self.assertEqual(restored.inventory.quantity('halden_medicine'), 0)
        self.assertTrue(visit.owns_tomas)
        self.assertEqual(sum(visit.tomas in w.npcs for w in restored.scenes.values()), 1)
        restored.update(1/60, (0, 0), False)
        self.assertIsNotNone(getattr(restored.player, 'story_sprite', None))
        restored.draw()

    def test_pause_and_inventory_freeze_handoff_and_tomas(self):
        self.accepted();self.game.social.start(self.visit.halden);self.finish_dialogue()
        self.key(pygame.K_ESCAPE);self.game.update(5, (1, 0), False)
        self.assertEqual(self.visit.action_time, 0);self.assertFalse(self.visit.medicine)
        self.key(pygame.K_ESCAPE);self.key(pygame.K_i)
        self.game.update(5, (1, 0), False)
        self.assertEqual(self.visit.action_time, 0);self.assertFalse(self.visit.medicine)
        self.key(pygame.K_i);self.wait();self.assertTrue(self.visit.medicine)

    def test_follower_uses_opening_doors_and_never_blocks_player(self):
        self.accepted('sanctuary_dining', (216, 282))
        actor = self.visit.tomas
        self.walk((216, 306), new_scene='sanctuary_hall')
        self.walk((216, 252));self.wait(4)
        self.assertEqual(actor.scene_id, 'sanctuary_hall')
        self.assertEqual(sum(actor in w.npcs for w in self.game.scenes.values()), 1)
        self.assertTrue(self.game.world.can_stand(actor.position))
        self.walk((208, 306), new_scene='eldenmere.playable')
        self.walk((386, 336));self.wait(4)
        self.assertEqual(actor.scene_id, 'eldenmere.playable')
        self.assertTrue(self.game.world.can_stand(actor.position, actor.probe_size, actor))

    def test_return_path_to_sanctuary_respects_town_geometry(self):
        self.accepted('eldenmere.playable', (1030, 662));actor = self.visit.tomas
        self.visit._place_tomas(self.game.town, (1008, 642))
        route = town_path(self.game.town, actor.position, (386, 294), actor, None)
        self.assertIsNotNone(route)
        cursor = actor.position.copy()
        for corner in route:
            delta = pygame.Vector2(corner)-cursor;length = delta.length()
            for i in range(1, int(length)+1):
                self.assertTrue(self.game.town.can_stand(cursor+delta*(i/length), actor.probe_size, actor))
            cursor.update(corner)

    def test_accepted_escort_walks_from_breakfast_to_halden_then_returns_to_work(self):
        from test_opening_gameplay import OpeningGameplayTests
        helper = OpeningGameplayTests()
        self.game.begin_journey(False)
        helper.enter_breakfast(self.game);helper.finish_breakfast(self.game)
        helper.approach_serene(self.game)
        for _ in range(50):
            if self.game.social.choosing:break
            self.game.social.advance()
        self.assertTrue(self.game.social.choosing)
        self.game.social.click(self.game.social.choice_rects[0].center)
        self.finish_dialogue();self.wait(.1)
        self.assertTrue(self.visit.owns_tomas)
        self.assertEqual(self.game.opening.stage, 'done')
        self.walk((216, 306), new_scene='sanctuary_hall')
        self.walk((208, 306), new_scene='eldenmere.playable')
        actor = self.visit.tomas
        # The player uses the same solid ground, with a full-sized player probe.
        class Probe:
            probe_size = self.game.town.probe_size
        route = town_path(self.game.town, self.game.player.position, (1008, 630), Probe(), None)
        self.assertIsNotNone(route)
        self.walk_path(route, new_scene='halden')
        if self.game.world is self.game.town:
            for _ in range(60):
                self.game.update(1/60, (0, -1), False)
                if self.game.world is self.visit.home:break
        self.assertIs(self.game.world, self.visit.home)
        self.walk((178, 244));self.wait(5)
        self.assertEqual(actor.scene_id, 'halden')
        self.assertFalse(self.visit.medicine)
        # Exercise the complete off-screen return rather than only its route.
        self.visit.concluded = True;self.visit.departed = True;self.visit.stored = {0, 1, 2}
        self.game.inventory.deliver(QUEST, 'halden', 'halden');self.visit._sync_props()
        for _ in range(15000):
            self.game.update(1/30, (0, 0), False)
            if not self.visit.owns_tomas:break
        self.assertFalse(self.visit.owns_tomas)
        self.assertEqual(actor.scene_id, 'sanctuary_hall')
        self.assertEqual(actor.state, 'return_through_hall')
        self.assertFalse(actor.story_paused)
        self.assertEqual(sum(actor in w.npcs for w in self.game.scenes.values()), 1)

    def test_invalid_cross_quest_save_rejected_and_new_game_resets_progress(self):
        self.medicine();self.store_player_sack(0);self.game.save_progress()
        data = json.loads(self.path.read_text());bad = copy.deepcopy(data)
        bad['halden_visit']['stored_sacks'] = [0, 0]
        self.assertFalse(HaldenVisit.valid_snapshot(bad['halden_visit']))
        bad = copy.deepcopy(data);bad['halden_visit']['concluded'] = True
        self.path.write_text(json.dumps(bad));broken = self.make_game(True)
        self.assertFalse(broken.has_saved_journey)
        self.assertTrue(self.game.begin_journey(False))
        self.assertEqual(self.visit.stored, set());self.assertFalse(self.visit.owns_tomas)
        self.assertIsNone(self.visit.carried);self.assertFalse(self.visit.medicine)


if __name__ == '__main__':unittest.main()
