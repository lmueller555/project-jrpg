"""Quest input, room visits and persisted journeys through the real game loop."""
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
import main
from quests import OPENING_QUEST


class QuestGameplayTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name)/'journey.json'

    def tearDown(self):
        pygame.quit()

    def game(self, *, title=False, saved=False):
        game = main.Game(fullscreen=False, start_on_title=title,
                         save_path=self.path if saved else None)
        game.title.music_enabled = False
        game.audio.set_effects(0)
        pygame.event.clear()
        return game

    def key(self, game, key):
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=key, repeat=False))
        return game.handle_events()

    def click(self, game, point):
        for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            pygame.event.post(pygame.event.Event(kind, button=1, pos=point))
        return game.handle_events()

    def canvas_click(self, game, point):
        width, height = game.window.get_size()
        scale = max(1, min(width//480, height//320))
        return self.click(game, (round((width-480*scale)//2+point[0]*scale),
                                 round((height-320*scale)//2+point[1]*scale)))

    def title_click(self, game, row):
        width, height = game.window.get_size()
        scale = min(width/640, height/360)
        return self.click(game, (round((width-640*scale)/2+row.centerx*scale),
                                 round((height-360*scale)/2+row.centery*scale)))

    def set_progress(self, game, phase):
        self.assertTrue(game.quests.accept(OPENING_QUEST))
        if phase in ('partial', 'ready', 'completed'):
            self.assertTrue(game.quests.complete_objective(OPENING_QUEST, 'halden'))
        if phase in ('ready', 'completed'):
            self.assertTrue(game.quests.complete_objective(OPENING_QUEST, 'venn'))
            self.assertTrue(game.quests.complete_objective(OPENING_QUEST, 'elira'))
        if phase == 'completed':
            self.assertTrue(game.quests.turn_in(OPENING_QUEST, 'mother_serene'))

    def test_deliberate_scaled_acceptance_checkpoints_without_waiting_for_quit(self):
        game = self.game(saved=True)
        game.window = pygame.display.set_mode((1100, 750))
        game.world = game._scene_by_id('sanctuary_dining')
        game.player.position.update(288, 231)
        game.player.facing = 'back'
        game.update(1/60, (0, -1), False)
        self.assertTrue(game.social.active)
        for _ in range(40):
            if game.social.choosing:
                break
            self.assertTrue(self.canvas_click(game, (1, 1)))
        self.assertTrue(game.social.choosing)
        self.assertEqual(game.quests.status(OPENING_QUEST), 'available')
        self.assertTrue(self.canvas_click(game, (1, 1)))
        self.assertEqual(game.quests.status(OPENING_QUEST), 'available')
        self.assertTrue(self.canvas_click(game, game.social.choice_rects[0].center))
        self.assertEqual(game.quests.status(OPENING_QUEST), 'active')
        self.assertFalse(game.social.locked)
        self.assertTrue(self.path.is_file())
        data = json.loads(self.path.read_text())
        self.assertEqual(data['quests'], game.quests.to_dict())
        self.assertIn('serene_greeted', data['dialogue_flags'])
        self.assertEqual(data['player']['scene'], 'sanctuary_dining')

    def test_journal_blocks_player_motion_conversations_and_door_transfers(self):
        game = self.game()
        game.world = game._scene_by_id('sanctuary_dining')
        game.player.position.update(288, 231)
        game.player.facing = 'back'
        before = game.player.position.copy()
        progress = game.quests.to_dict()
        self.assertTrue(self.key(game, pygame.K_j))
        self.assertTrue(game.quest_ui.journal_open)
        game.update(.2, (0, -1), True)
        self.assertEqual(game.player.position, before)
        self.assertFalse(game.social.locked)
        self.assertEqual(game.quests.to_dict(), progress)
        game.draw()

        game.world = game.town
        door = next(door for door in game.town.doors if door.data['id'] == 'sanctuary')
        door.force_open()
        game.player.position.update(door.data['anchor'])
        game.player.facing = 'back'
        before = game.player.position.copy()
        game.update(.2, (0, -1), False)
        self.assertIs(game.world, game.town)
        self.assertEqual(game.player.position, before)
        self.assertFalse(game.enter(door))
        self.assertTrue(self.key(game, pygame.K_ESCAPE))
        self.assertFalse(game.quest_ui.journal_open)
        self.assertTrue(game.enter(door))
        self.assertEqual(game.world.data['id'], 'sanctuary_hall')

    def test_j_and_escape_close_journal_without_quitting_or_opening_map(self):
        game = self.game()
        self.assertTrue(self.key(game, pygame.K_m))
        self.assertTrue(game.map_open)
        self.assertTrue(self.key(game, pygame.K_j))
        self.assertFalse(game.map_open)
        self.assertTrue(game.quest_ui.journal_open)
        self.assertTrue(self.key(game, pygame.K_m))
        self.assertFalse(game.map_open)
        self.assertTrue(game.quest_ui.journal_open)
        self.assertTrue(self.key(game, pygame.K_j))
        self.assertFalse(game.quest_ui.journal_open)
        self.assertTrue(self.key(game, pygame.K_j))
        self.assertTrue(self.key(game, pygame.K_ESCAPE))
        self.assertFalse(game.quest_ui.journal_open)
        self.assertFalse(game.map_open)

    def test_household_visits_and_map_rendering_never_complete_unfinished_tasks(self):
        game = self.game()
        for accepted in (False, True):
            with self.subTest(accepted=accepted):
                if accepted:
                    game.quests.accept(OPENING_QUEST)
                before = game.quests.to_dict()
                marker = None if accepted else '!'
                for name in ('halden', 'elira', 'venn'):
                    game.world = game.town
                    door = next(door for door in game.town.doors if door.data['id'] == name)
                    self.assertTrue(game.enter(door))
                    self.assertEqual(game.world.data['id'], name)
                    game.update(0, (0, 0), False)
                    self.assertEqual(game.quests.to_dict(), before)
                    self.assertEqual(game.quests.marker_for('mother_serene'), marker)
                game.map_open = True
                with patch.object(game.quest_ui, '_symbol') as symbol:
                    game.draw()
                    self.assertEqual(symbol.call_count, 0 if accepted else 1)
                    if not accepted:
                        self.assertEqual(symbol.call_args.args[1], '!')
                self.assertEqual(game.quests.to_dict(), before)
                game.map_open = False

    def test_continue_restores_every_progress_stage_flags_and_location_quietly(self):
        for phase in ('accepted', 'partial', 'ready', 'completed'):
            with self.subTest(phase=phase):
                game = self.game(saved=True)
                self.set_progress(game, phase)
                game.social.flags.update(('serene_greeted', 'tomas_greeted'))
                game.world = game._scene_by_id('elira')
                game.player.position.update(game.world.data['spawn'])
                game.player.facing = 'left'
                game.exterior_position.update(671.5, 966)
                # The real update checkpoints changed facts and consumes feedback.
                game.update(0, (0, 0), False)
                self.assertIsNotNone(game.quest_ui.current_notice)
                saved = json.loads(self.path.read_text())
                self.assertEqual(saved['quests'], game.quests.to_dict())

                restored = self.game(title=True, saved=True)
                self.assertTrue(restored.has_saved_journey)
                self.assertEqual(restored.quests.status(OPENING_QUEST), 'available')
                self.assertEqual(restored.social.flags, set())
                self.assertTrue(self.key(restored, pygame.K_DOWN))
                self.assertEqual(restored.title.selected, 1)
                self.assertTrue(self.key(restored, pygame.K_RETURN))
                self.assertGreater(restored.title.fade, 0)
                self.assertTrue(restored.on_title)
                restored.update(.7, (0, 0), False)
                self.assertFalse(restored.on_title)
                self.assertEqual(restored.quests.to_dict(), saved['quests'])
                self.assertEqual(restored.social.flags, set(saved['dialogue_flags']))
                self.assertEqual(restored.world.data['id'], 'elira')
                self.assertEqual(list(restored.player.position), saved['player']['position'])
                self.assertEqual(restored.player.facing, 'left')
                self.assertEqual(list(restored.exterior_position), [671.5, 966])
                self.assertFalse(restored.social.locked)
                self.assertIsNone(restored.quest_ui.current_notice)
                self.assertFalse(restored.quest_ui.notices)
                self.assertEqual(restored.quests.drain_events(), [])
                restored.update(.1, (0, 0), False)
                self.assertIsNone(restored.quest_ui.current_notice)
                restored.draw()

    def test_new_game_resets_old_progress_after_title_choice(self):
        game = self.game(saved=True)
        self.set_progress(game, 'completed')
        game.social.flags.add('serene_greeted')
        self.assertTrue(game.save_progress())
        restored = self.game(title=True, saved=True)
        self.assertTrue(restored.has_saved_journey)
        self.assertTrue(self.title_click(restored, restored.title.rows[0]))
        restored.update(.7, (0, 0), False)
        self.assertFalse(restored.on_title)
        self.assertTrue(restored.opening_cinematic.active)
        # Choosing New Game keeps the existing checkpoint intact until the
        # framing scene completes or the player uses its explicit Skip button.
        self.assertEqual(json.loads(self.path.read_text())['quests'], game.quests.to_dict())
        restored.draw()
        self.assertTrue(self.canvas_click(restored, restored.opening_cinematic.skip_rect.center))
        self.assertFalse(restored.opening_cinematic.active)
        self.assertEqual(restored.quests.status(OPENING_QUEST), 'available')
        self.assertEqual(restored.social.flags, set())
        self.assertEqual(restored.world.data['id'], 'sanctuary_bedroom')
        self.assertEqual(restored.opening.stage, 'wake')
        self.assertTrue(restored.social.scripted)
        self.assertTrue(restored.world.can_stand(restored.player.position))
        saved = json.loads(self.path.read_text())
        self.assertEqual(saved['quests'], restored.quests.to_dict())
        self.assertEqual(saved['dialogue_flags'], [])
        self.assertEqual(saved['opening'], {'version': 1, 'stage': 'wake'})

    def test_invalid_saves_disable_continue_without_overwriting_the_file(self):
        game = self.game(saved=True)
        self.assertTrue(game.save_progress())
        valid = json.loads(self.path.read_text())
        raw_cases = [b'{unfinished']
        variants = []
        for key, value in (('scene', 'missing_room'), ('position', [float('nan'), 10]),
                           ('position', [float('inf'), 10]), ('position', [True, 10]),
                           ('position', [10**400, 10])):
            data = json.loads(json.dumps(valid))
            data['player'][key] = value
            variants.append(data)
        bad_version = json.loads(json.dumps(valid))
        bad_version['version'] = True
        variants.append(bad_version)
        raw_cases.extend(json.dumps(data).encode() for data in variants)
        for raw in raw_cases:
            with self.subTest(raw=raw):
                self.path.write_bytes(raw)
                restored = self.game(title=True, saved=True)
                self.assertFalse(restored.has_saved_journey)
                self.assertIsNotNone(restored.save_error)
                self.assertTrue(self.title_click(restored, restored.title.rows[1]))
                self.assertEqual(restored.title.fade, 0)
                restored.title.selected = 0
                self.assertTrue(self.key(restored, pygame.K_DOWN))
                self.assertEqual(restored.title.selected, 2)
                restored.draw()
                self.assertEqual(self.path.read_bytes(), raw)

    def test_failed_social_checkpoint_retries_slowly_and_explicit_save_retries_now(self):
        game = self.game(saved=True)
        self.assertTrue(game.save_progress())
        checkpoint = self.path.read_bytes()
        game.world = game._scene_by_id('sanctuary_dining')
        game.player.position.update(288, 231)
        game.player.facing = 'back'
        game.update(1/60, (0, -1), False)
        for _ in range(40):
            if game.social.choosing:
                break
            self.assertTrue(self.canvas_click(game, (1, 1)))
        self.assertTrue(game.social.choosing)

        game.save_store.error = 'The journey could not be saved.'
        with patch.object(game.save_store, 'write', return_value=False) as write:
            self.assertTrue(self.canvas_click(game, game.social.choice_rects[0].center))
            self.assertEqual(game.quests.status(OPENING_QUEST), 'active')
            self.assertEqual(write.call_count, 1)
            self.assertIsNotNone(game.save_error)
            for _ in range(60):
                game.update(1/60, (0, 0), False)
            self.assertEqual(write.call_count, 1)
            game.update(9.1, (0, 0), False)
            self.assertEqual(write.call_count, 2)
            self.assertFalse(game.save_progress())
            self.assertEqual(write.call_count, 3)
        self.assertEqual(self.path.read_bytes(), checkpoint)

    def test_blocked_saved_position_falls_back_to_walkable_room_entry(self):
        game = self.game(saved=True)
        self.set_progress(game, 'partial')
        game.world = game._scene_by_id('elira')
        game.player.position.update(0, 0)
        self.assertFalse(game.world.can_stand(game.player.position))
        self.assertTrue(game.save_progress())
        progress = game.quests.to_dict()
        restored = self.game(title=True, saved=True)
        self.assertTrue(restored.has_saved_journey)
        self.assertTrue(self.title_click(restored, restored.title.rows[1]))
        restored.update(.7, (0, 0), False)
        self.assertEqual(restored.world.data['id'], 'elira')
        self.assertEqual(list(restored.player.position), restored.world.data['spawn'])
        self.assertTrue(restored.world.can_stand(restored.player.position))
        self.assertEqual(restored.quests.to_dict(), progress)

    def test_default_game_disables_disk_saves_and_starts_without_old_progress(self):
        game = self.game()
        self.set_progress(game, 'partial')
        self.assertFalse(game.save_store.enabled)
        self.assertFalse(game.save_progress())
        self.assertFalse(self.path.exists())
        fresh = self.game(title=True)
        self.assertFalse(fresh.has_saved_journey)
        self.assertEqual(fresh.quests.status(OPENING_QUEST), 'available')


if __name__ == '__main__':
    unittest.main()
