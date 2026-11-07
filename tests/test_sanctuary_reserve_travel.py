"""Sanctuary scale changes, durable journeys and town-owned companions."""
import json
import os
from pathlib import Path
import tempfile
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import pygame

from main import Game
from overworld_travel import (HALL_ID, RESERVE_ID, WORLD_ID, TOWN_EXIT,
                              OverworldTravel)
from quests import MILL_QUEST, OPENING_QUEST


class SanctuaryReserveTravelTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.save = Path(self.temporary.name)/'journey.json'

    def tearDown(self):pygame.quit()

    def game(self, title=False):
        game = Game(fullscreen=False, start_on_title=title, save_path=self.save,
                    settings_path=self.save.with_name('settings.json'))
        game.audio.set_music(0);game.audio.set_effects(0)
        game.opening_fade = game.transfer_cooldown = 0
        pygame.event.clear()
        return game

    def region(self, game):
        game.world = game.town;game.player.position.update(TOWN_EXIT)
        game.opening_fade = game.transfer_cooldown = 0
        self.assertTrue(game.overworld_travel.enter_region())
        game.update(.4, (0,0), False)
        return game.world

    def reserve(self, game):
        region = self.region(game)
        contact = game.overworld_travel.reserve_contact(region)
        game.player.position.update(contact.centerx, contact.bottom+32)
        game.overworld_travel.update()
        for _ in range(50):
            game.update(.05, (0,-1), False)
            if game.world.data['id'] == RESERVE_ID:break
        self.assertEqual(game.world.data['id'], RESERVE_ID)
        return game.world

    def walk_out(self, game):
        point = pygame.Vector2(game.world.data['reserve_exit']['position'])
        for _ in range(100):
            game.update(.05, point-game.player.position, False)
            if game.world.data['id'] == WORLD_ID:break
        self.assertEqual(game.world.data['id'], WORLD_ID)

    def test_automatic_roundtrip_has_clear_landings_and_no_contact_loop(self):
        game = self.game();reserve = self.reserve(game)
        self.assertEqual(tuple(game.player.position), tuple(reserve.data['spawn']))
        self.assertEqual(game.player.facing, 'back')
        self.assertIs(game._scene_by_id(RESERVE_ID), reserve)
        game.update(.6, (0,0), False)
        self.assertIs(game.world, reserve)
        self.walk_out(game)
        region = game.world
        contact = game.overworld_travel.reserve_contact(region)
        self.assertFalse(contact.colliderect(region.probe_rect(game.player.position).inflate(2,2)))
        self.assertTrue(region.can_stand(game.player.position))
        self.assertEqual(game.player.facing, 'front')
        game.update(.6, (0,0), False)
        self.assertIs(game.world, region)

    def test_modal_blocks_contact_and_freezes_the_reserve_clock(self):
        game = self.game();region = self.region(game)
        contact = game.overworld_travel.reserve_contact(region)
        game.player.position.update(contact.center)
        game.map_open = True
        self.assertFalse(game.overworld_travel.enter_reserve())
        game.map_open = False
        self.assertTrue(game.overworld_travel.enter_reserve())
        game.update(.4, (0,0), False)
        before = game.elapsed_ms
        game.map_open = True;game.update(1., (1,0), False)
        self.assertEqual(game.elapsed_ms, before)
        game.map_open = False;game.quest_ui.journal_open = True
        game.update(1., (1,0), False)
        self.assertEqual(game.elapsed_ms, before)

    def test_reserve_and_hall_continue_in_the_saved_scene(self):
        for scene_id in (RESERVE_ID, HALL_ID):
            with self.subTest(scene=scene_id):
                game = self.game();self.reserve(game)
                game.world = game._scene_by_id(scene_id)
                game.player.position.update(game.world.data['spawn'])
                game.update(.4, (0,0), False)
                position = tuple(game.player.position)
                facts = (game.quests.to_dict(), game.inventory.to_dict(), set(game.social.flags))
                self.assertTrue(game.save_progress())
                restored = self.game(True)
                self.assertTrue(restored.has_saved_journey)
                self.assertTrue(restored.begin_journey(True))
                self.assertEqual(restored.world.data['id'], scene_id)
                self.assertEqual(tuple(restored.player.position), position)
                self.assertTrue(restored.world.can_stand(restored.player.position))
                self.assertEqual((restored.quests.to_dict(), restored.inventory.to_dict(),
                                  set(restored.social.flags)), facts)
                self.assertEqual(restored.music.desired_track, 'eldenmere')

    def test_legacy_positions_newly_occupied_by_native_objects_restore_safely(self):
        # Both were clear in the preceding scene exports. The native tree and
        # reading stand now occupy them. Preserve the remote scene and facts
        # while using its established safe entry rather than resetting to town.
        for scene_id,historical_position in ((RESERVE_ID,(144,276)),(HALL_ID,(194,224))):
            with self.subTest(scene=scene_id):
                game = self.game();self.reserve(game)
                game.world = game._scene_by_id(scene_id)
                game.player.position.update(game.world.data['spawn'])
                self.assertFalse(game.world.can_stand(historical_position))
                self.assertTrue(game.save_progress())
                record = json.loads(self.save.read_text())
                record['player']['position'] = list(historical_position)
                self.save.write_text(json.dumps(record)+'\n')
                facts = (game.quests.to_dict(),game.inventory.to_dict(),game.attributes.to_dict(),
                         game.party.to_dict(),game.character_abilities.to_dict())
                restored = self.game(True)
                self.assertTrue(restored.begin_journey(True))
                self.assertEqual(restored.world.data['id'],scene_id)
                self.assertEqual(tuple(restored.player.position),tuple(restored.world.data['spawn']))
                self.assertTrue(restored.world.can_stand(restored.player.position))
                self.assertEqual((restored.quests.to_dict(),restored.inventory.to_dict(),
                                  restored.attributes.to_dict(),restored.party.to_dict(),
                                  restored.character_abilities.to_dict()),facts)

    def test_old_region_save_inside_the_new_portal_waits_for_leave_and_return(self):
        game = self.game();region = self.region(game)
        contact = game.overworld_travel.reserve_contact(region)
        game.player.position.update(contact.center)
        self.assertTrue(game.save_progress())
        record = json.loads(self.save.read_text())
        record['overworld']['discovered'] = ['eldenmere']
        self.save.write_text(json.dumps(record))
        restored = self.game(True)
        self.assertTrue(restored.begin_journey(True))
        restored.update(.6, (0,0), False)
        self.assertEqual(restored.world.data['id'], WORLD_ID)
        restored.player.position.update(contact.centerx, contact.bottom+32)
        restored.overworld_travel.update()
        restored.player.position.update(contact.center)
        self.assertTrue(restored.overworld_travel.update())
        self.assertEqual(restored.world.data['id'], RESERVE_ID)

    def test_active_mill_party_stays_owned_and_frozen_through_reserve_and_hall_continue(self):
        game = self.game()
        self.assertTrue(game.accept_quest(OPENING_QUEST))
        for objective in ('halden', 'elira', 'venn'):
            self.assertTrue(game.quests.complete_objective(OPENING_QUEST, objective))
        game._sync_inventory()
        game.halden_visit.restore();game.elira_visit.restore();game.venn_visit.restore()
        self.assertTrue(game.quests.turn_in(OPENING_QUEST, 'mother_serene'))
        self.assertTrue(game.quests.unlock(MILL_QUEST))
        game.opening_conclusion.restore({'version':1, 'stage':'done'})
        self.assertTrue(game.accept_quest(MILL_QUEST))
        self.assertTrue(game.quests.complete_objective(MILL_QUEST, 'meet_mira'))
        game.mill_quest.restore()
        actors = [actor for actor, _ in game.overworld_travel._party()]
        self.assertIn(game.mill_quest.mira, actors)
        self.reserve(game)
        facts = (game.quests.to_dict(), game.mill_quest.to_dict())
        stations = [(actor, actor.position.copy(), actor.scene_id) for actor in actors]
        for scene_id in (RESERVE_ID, HALL_ID):
            game.world = game._scene_by_id(scene_id)
            game.player.position.update(game.world.data['spawn'])
            game.update(1., (0,0), False)
            self.assertEqual((game.quests.to_dict(), game.mill_quest.to_dict()), facts)
            for actor, position, owner_scene in stations:
                self.assertEqual(actor.position, position);self.assertEqual(actor.scene_id, owner_scene)
                self.assertNotIn(actor, game.world.npcs)
        self.assertTrue(game.save_progress())
        restored = self.game(True);self.assertTrue(restored.begin_journey(True))
        restored.opening_fade = restored.transfer_cooldown = 0
        self.assertEqual(restored.world.data['id'], HALL_ID)
        self.assertEqual((restored.quests.to_dict(), restored.mill_quest.to_dict()), facts)
        self.assertTrue(restored.enter(next(door for door in restored.world.doors
                                            if door.data['id'] == 'reserve_exit')))
        restored.transfer_cooldown = 0
        self.assertTrue(restored.overworld_travel.leave_reserve())
        restored.transfer_cooldown = 0
        self.assertTrue(restored.overworld_travel.enter_town())
        for actor, _ in restored.overworld_travel._party():
            self.assertIn(actor, restored.town.npcs)
            self.assertLess(actor.position.distance_to(restored.player.position), 150)
            self.assertEqual(sum(actor in scene.npcs for scene in restored.scenes.values()), 1)

    def test_new_remote_scene_requires_valid_regional_record(self):
        game = self.game();self.reserve(game);self.assertTrue(game.save_progress())
        record = json.loads(self.save.read_text())
        self.assertTrue(OverworldTravel.valid_journey(record))
        record.pop('overworld')
        self.assertFalse(OverworldTravel.valid_journey(record))


if __name__ == '__main__':unittest.main()
