"""The classroom map is reachable, inspectable, and isolated from world input."""
import os
os.environ.update(SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy',
                  PYGAME_HIDE_SUPPORT_PROMPT='1')

import json
import unittest

import pygame

import main
from npc_routines import find_path


class SchoolWorldMapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.game = main.Game(fullscreen=False, start_on_title=False)
        cls.room = cls.game._scene_by_id('school')
        cls.game.audio.effects_volume = 0

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        game = self.game
        game.social.cancel()
        game.pause.close()
        game.inventory_ui.close()
        game.world_map_viewer.close()
        game.map_open = False
        game.quest_ui.journal_open = False
        game.opening.stage = 'disabled'
        game.opening_fade = 0
        game.transfer_cooldown = 0
        game.world = self.room
        game.player.position.update(self.room.data['world_map_display']['position'])
        game.player.moving = False
        game.camera.reset()
        pygame.event.clear()

    def press(self, key):
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=key, repeat=False))

    def test_authored_approach_is_beside_map_and_reachable_from_door(self):
        room = self.room
        display = room.data['world_map_display']
        source = json.loads((main.ROOT/room.data['source_room']).read_text())
        self.assertEqual(display, source['world_map_display'])
        self.assertEqual(display['position'], room.data['destinations'][display['entity_id']])
        self.assertTrue(room.can_stand(display['position']))
        self.assertIsNotNone(find_path(room, room.data['spawn'], display['position'], room.probe_size, None))
        entity = next(e for e in room.entities if e['id'] == display['entity_id'])
        self.assertEqual(entity['position'], [96, 28])
        self.assertEqual(entity['surfaces'][0].get_size(), (42, 40))
        image = self.game.town.image('assets/world/auratia/wall_map.png')
        self.assertEqual(pygame.image.tobytes(entity['surfaces'][0], 'RGBA'),
                         pygame.image.tobytes(image, 'RGBA'))
        self.assertLessEqual(abs(display['position'][0]-(96+21)), display['radius'])
        self.assertLessEqual(display['position'][1]-(28+40), 30)

    def test_actual_e_interaction_opens_original_art(self):
        self.assertIsNotNone(self.game.nearby_world_map())
        self.press(pygame.K_e)
        self.assertTrue(self.game.handle_events())
        viewer = self.game.world_map_viewer
        self.assertTrue(viewer.is_open)
        self.assertEqual(viewer.image.get_size(), (1448, 1086))
        self.assertEqual(self.game.player.facing, 'back')
        self.assertFalse(self.game.social.active)

    def test_map_is_unavailable_in_other_scenes_or_far_from_wall(self):
        self.game.world = self.game.town
        self.assertIsNone(self.game.nearby_world_map())
        self.assertFalse(self.game.try_inspect_world_map())
        self.game.world = self.room
        self.game.player.position.update(self.room.data['spawn'])
        self.assertIsNone(self.game.nearby_world_map())
        self.assertFalse(self.game.try_inspect_world_map())

    def test_viewer_freezes_player_npcs_doors_and_quest_clocks(self):
        game = self.game
        self.assertTrue(game.try_inspect_world_map())
        position = game.player.position.copy()
        actors = [(npc.position.copy(), npc.facing) for npc in game.persistent_npcs]
        doors = [door.progress for scene in game.scenes.values() for door in scene.doors]
        elapsed = game.elapsed_ms
        quests = game.quests.to_dict()
        game.update(.75, (1, 0), True)
        self.assertEqual(game.player.position, position)
        self.assertEqual(game.elapsed_ms, elapsed)
        self.assertEqual([(npc.position, npc.facing) for npc in game.persistent_npcs], actors)
        self.assertEqual([door.progress for scene in game.scenes.values() for door in scene.doors], doors)
        self.assertEqual(game.quests.to_dict(), quests)
        self.assertFalse(game.enter(game.world.doors[0]))

    def test_close_consumes_remaining_event_batch_without_opening_other_menus(self):
        game = self.game
        self.assertTrue(game.try_inspect_world_map())
        for key in (pygame.K_ESCAPE, pygame.K_i, pygame.K_m, pygame.K_j, pygame.K_e):
            self.press(key)
        self.assertTrue(game.handle_events())
        self.assertFalse(game.world_map_viewer.is_open)
        self.assertFalse(game.pause.is_open)
        self.assertFalse(game.inventory_ui.is_open)
        self.assertFalse(game.map_open)
        self.assertFalse(game.quest_ui.journal_open)
        self.assertFalse(game.social.active)

    def test_existing_dialogue_and_menus_take_precedence(self):
        game = self.game
        game.social.start_script([{'speaker': 'caelan', 'text': 'An atlas of Auratia.'}],
                                 identifier='world_map_test')
        self.assertFalse(game.try_inspect_world_map())
        game.social.cancel()
        for owner, field in ((game, 'map_open'), (game.quest_ui, 'journal_open'),
                             (game.pause, 'is_open'), (game.inventory_ui, 'is_open')):
            with self.subTest(menu=field, owner=type(owner).__name__):
                setattr(owner, field, True)
                self.assertIsNone(game.nearby_world_map())
                self.assertFalse(game.try_inspect_world_map())
                setattr(owner, field, False)


if __name__ == '__main__':
    unittest.main()
