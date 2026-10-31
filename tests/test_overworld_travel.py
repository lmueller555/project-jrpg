"""Real Game transitions, saved journeys and borrowed story actors at two scales."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import PropertyMock, patch

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import pygame

import main
from overworld_travel import OverworldTravel, TOWN_EXIT, TOWN_RETURN, WORLD_ID
from quests import OPENING_QUEST, MILL_QUEST, REGENT_QUEST, LANTERN_QUEST
from tools.capture_lantern_quest import seed_previous_quests


class OverworldTravelTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)/'journey.json'

    def tearDown(self):
        pygame.quit()

    def game(self, title=False):
        game = main.Game(fullscreen=False, start_on_title=title, save_path=self.path,
                         settings_path=Path(self.temp.name)/'settings.json')
        game.audio.set_music(0)
        game.audio.set_effects(0)
        game.opening_fade = game.transfer_cooldown = 0
        pygame.event.clear()
        return game

    def depart(self, game):
        game.world = game.town
        game.player.position.update(TOWN_EXIT)
        game.opening_fade = game.transfer_cooldown = 0
        self.assertTrue(game.overworld_travel.enter_region())

    def complete_opening(self, game):
        self.assertTrue(game.accept_quest(OPENING_QUEST))
        for objective in ('halden', 'elira', 'venn'):
            self.assertTrue(game.quests.complete_objective(OPENING_QUEST, objective))
        game._sync_inventory()
        game.halden_visit.restore();game.elira_visit.restore();game.venn_visit.restore()
        self.assertTrue(game.quests.turn_in(OPENING_QUEST, 'mother_serene'))
        self.assertTrue(game.quests.unlock(MILL_QUEST))
        game.opening_conclusion.restore({'version': 1, 'stage': 'done'})

    def complete_mill(self, game):
        self.complete_opening(game)
        self.assertTrue(game.accept_quest(MILL_QUEST))
        for objective in game.quests.definitions[MILL_QUEST]['objectives']:
            self.assertTrue(game.quests.complete_objective(MILL_QUEST, objective['id']))
        self.assertTrue(game.quests.turn_in(MILL_QUEST, 'mira_worker'))
        game.mill_quest.restore({'version': 1, 'inspected': ['mechanism', 'race', 'intake'],
                                'prepared': True, 'spell_done': True, 'encouraged': True,
                                'restored': True, 'verified': True, 'resolved': True})
        self.assertTrue(game.quests.unlock(REGENT_QUEST))
        game.regent_quest.restore()

    def test_automatic_roundtrip_uses_south_entrance_and_singleton(self):
        game = self.game()
        scene_paths = set(game.scenes)
        game.player.position.update(TOWN_EXIT)
        game.update(.01, (0, 0), False)
        world = game.world
        self.assertEqual(world.data['id'], WORLD_ID)
        self.assertEqual(tuple(game.player.position), (288, -600))
        self.assertEqual(set(game.scenes), scene_paths)
        self.assertIs(game._scene_by_id(WORLD_ID), world)
        self.assertEqual(tuple(game.exterior_position), TOWN_EXIT)
        game.update(.4, (0, 0), False)
        game.player.position.update(world.town_entry_rect.centerx, world.town_entry_rect.bottom+6)
        game.update(.01, (0, 0), False)
        self.assertIs(game.world, game.town)
        self.assertEqual(tuple(game.player.position), TOWN_RETURN)
        self.assertEqual(game.player.facing, 'back')
        game.update(.5, (0, 0), False)
        self.assertIs(game.world, game.town)
        self.depart(game)
        self.assertIs(game.world, world)

    def test_contact_requires_leave_before_reentry(self):
        game = self.game()
        self.depart(game)
        game.transfer_cooldown = 0
        entry = game.world.town_entry_rect
        game.player.position.update(entry.centerx, entry.bottom+6)
        self.assertFalse(game.overworld_travel.update())
        game.player.position.update(game.world.town_exit)
        self.assertFalse(game.overworld_travel.update())
        game.player.position.update(entry.centerx, entry.bottom+6)
        self.assertTrue(game.overworld_travel.update())
        # Leaving the contact while cooldown is active still rearms it.
        self.assertGreater(game.transfer_cooldown, 0)
        game.overworld_travel.update()
        game.player.position.update(TOWN_EXIT)
        game.transfer_cooldown = 0
        self.assertTrue(game.overworld_travel.update())

    def test_miniature_contact_from_every_side_returns_to_south_road(self):
        game = self.game()
        for side in ('north', 'south', 'west', 'east'):
            with self.subTest(side=side):
                self.depart(game)
                game.update(.4, (0, 0), False)
                world = game.world
                entry = world.town_entry_rect
                positions = {'north': (entry.centerx, entry.top-6),
                             'south': (entry.centerx, entry.bottom+6),
                             'west': (entry.left-12, entry.centery),
                             'east': (entry.right+12, entry.centery)}
                game.player.position.update(positions[side])
                self.assertTrue(world.can_stand(game.player.position))
                self.assertTrue(game.overworld_travel.update())
                self.assertIs(game.world, game.town)
                self.assertEqual(tuple(game.player.position), TOWN_RETURN)

    def test_modals_dialogue_and_actions_block_atomic_transfers(self):
        game = self.game()
        game.player.position.update(TOWN_EXIT)
        for owner, name in ((game.pause, 'is_open'), (game.inventory_ui, 'is_open'),
                            (game, 'map_open'), (game.quest_ui, 'journal_open'),
                            (game.world_map_viewer, 'is_open'), (game.combat, 'active'),
                            (game.opening_cinematic, 'active')):
            mocked = (patch.object(type(owner), name, new_callable=PropertyMock, return_value=True)
                      if isinstance(getattr(type(owner), name, None), property)
                      else patch.object(owner, name, True))
            with self.subTest(lock=name), mocked:
                self.assertFalse(game.overworld_travel.enter_region())
                self.assertIs(game.world, game.town)
        self.assertTrue(game.social.start_script([{'speaker': 'caelan', 'text': 'A moment.'}]))
        self.assertFalse(game.overworld_travel.enter_region())
        game.social.cancel_script()
        game.mill_quest.action = 'prepare'
        self.assertFalse(game.overworld_travel.enter_region())
        game.mill_quest.action = None
        world = game.overworld_world
        with patch.object(world, 'can_stand', return_value=False):
            self.assertFalse(game.overworld_travel.enter_region())
        self.assertIs(game.world, game.town)
        self.assertEqual(tuple(game.player.position), TOWN_EXIT)

    def test_region_continue_and_discovery_survive_town_return(self):
        game = self.game()
        self.depart(game)
        game.update(.4, (0, 0), False)
        landmark = next(item for item in game.world.data['landmarks'] if item['id'] != 'eldenmere')
        game.player.position.update(landmark['position'])
        game.overworld_travel.update()
        self.assertIn(landmark['id'], game.overworld_travel.discovered)
        position = tuple(game.player.position)
        self.assertTrue(game.save_progress())
        restored = self.game(True)
        self.assertIsNone(restored._overworld_world)
        self.assertTrue(restored.has_saved_journey)
        self.assertTrue(restored.begin_journey(True))
        self.assertEqual(restored.world.data['id'], WORLD_ID)
        self.assertEqual(tuple(restored.player.position), position)
        self.assertIn(landmark['id'], restored.overworld_travel.discovered)
        restored.opening_fade = restored.transfer_cooldown = 0
        self.assertTrue(restored.overworld_travel.enter_town())
        self.assertIn(landmark['id'], restored.saved_journey['overworld']['discovered'])

    def test_legacy_save_needs_no_region_metadata_or_eager_world(self):
        game = self.game()
        game.save_progress()
        record = json.loads(self.path.read_text())
        record.pop('overworld')
        self.path.write_text(json.dumps(record))
        restored = self.game(True)
        self.assertTrue(restored.has_saved_journey)
        self.assertIsNone(restored._overworld_world)
        self.assertTrue(restored.begin_journey(True))
        self.assertEqual(restored.overworld_travel.discovered, {'eldenmere'})
        for invalid in ({'version': True, 'region': 'elden_vale_start'},
                        {'version': 1, 'region': 'wrong'},
                        {'version': 1, 'region': 'elden_vale_start', 'discovered': ['made_up']}):
            broken = copy.deepcopy(record);broken['overworld'] = invalid
            self.assertFalse(OverworldTravel.valid_journey(broken))
        record['player']['scene'] = WORLD_ID
        self.assertFalse(OverworldTravel.valid_journey(record))

    def test_guard_exchanges_do_not_produce_clearance_or_bridge_repairs(self):
        game = self.game()
        self.depart(game)
        game.transfer_cooldown = 0
        gate = game.world.gates[0]
        for guard in gate['guard_positions']:
            game.player.position.update(guard[0], guard[1]+24)
            self.assertTrue(game.overworld_travel.interact())
            self.assertIsNotNone(game.social.resolve_speaker())
            game.social.cancel_script()
        self.assertNotIn('CH01_OPENING_REGION_RELEASED', game.social.flags)
        self.assertNotIn('ELDEN_VALE_WEST_BRIDGE_REPAIRED', game.social.flags)

    def test_virtual_party_owners_and_instances_survive_region_and_continue(self):
        for phase in ('halden', 'mill', 'regent', 'lantern'):
            with self.subTest(phase=phase):
                self.path.unlink(missing_ok=True)
                game = self.game()
                if phase == 'halden':
                    game.accept_quest(OPENING_QUEST);game.halden_visit.restore()
                elif phase == 'mill':
                    self.complete_opening(game)
                    game.accept_quest(MILL_QUEST)
                    game.quests.complete_objective(MILL_QUEST, 'meet_mira')
                    game.mill_quest.restore()
                elif phase == 'regent':
                    self.complete_mill(game)
                    game.accept_quest(REGENT_QUEST)
                    game.quests.complete_objective(REGENT_QUEST, 'meet_visitors')
                    game.regent_quest.restore({'version': 1, 'stage': 'met'})
                else:
                    seed_previous_quests(game)
                    game.accept_quest(LANTERN_QUEST)
                    game.quests.complete_objective(LANTERN_QUEST, 'join_preparations')
                    game.lantern_quest.restore({'version': 1, 'stage': 'permitted'})
                actors = [actor for actor, _ in game.overworld_travel._party()]
                self.assertTrue(actors)
                progress = game.quests.to_dict()
                self.depart(game)
                game.update(.4, (0, 0), False)
                self.assertEqual(game.quests.to_dict(), progress)
                self.assertTrue(all(actor not in game.world.npcs for actor in actors))
                game.save_progress()
                continued = self.game(True)
                self.assertTrue(continued.has_saved_journey)
                self.assertTrue(continued.begin_journey(True))
                continued.opening_fade = continued.transfer_cooldown = 0
                self.assertTrue(continued.overworld_travel.enter_town())
                for actor, _ in continued.overworld_travel._party():
                    self.assertIn(actor, continued.town.npcs)
                    self.assertLess(actor.position.distance_to(continued.player.position), 150)
                    self.assertEqual(sum(actor in scene.npcs for scene in continued.scenes.values()), 1)
                game.transfer_cooldown = 0
                self.assertTrue(game.overworld_travel.enter_town())
                self.assertEqual([actor for actor, _ in game.overworld_travel._party()], actors)
                self.assertEqual(game.quests.to_dict(), progress)


if __name__ == '__main__':
    unittest.main()
