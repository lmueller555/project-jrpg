"""Play the sanctuary morning through real title, input, doors and checkpoints."""
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
from npc_routines import find_path
from quests import OPENING_QUEST


class OpeningGameplayTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name)/'journey.json'

    def tearDown(self):
        pygame.quit()

    def game(self, title=True):
        game = main.Game(fullscreen=False, start_on_title=title, save_path=self.path)
        game.title.music_enabled = False
        game.audio.set_effects(0)
        pygame.event.clear()
        return game

    def key(self, game, key):
        for kind in (pygame.KEYDOWN, pygame.KEYUP):
            pygame.event.post(pygame.event.Event(kind, key=key, repeat=False))
        self.assertTrue(game.handle_events())

    def click(self, game, point):
        width, height = game.window.get_size()
        scale = max(1, min(width//480, height//320))
        position = (round((width-480*scale)//2+point[0]*scale),
                    round((height-320*scale)//2+point[1]*scale))
        for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            pygame.event.post(pygame.event.Event(kind, button=1, pos=position))
        self.assertTrue(game.handle_events())

    def new_game(self):
        game = self.game()
        self.key(game, pygame.K_RETURN)
        game.update(.7, (0, 0), False)
        self.assertFalse(game.on_title)
        # This fixture exercises the sanctuary morning. Take the production
        # Skip path through the new framing scene before reading that morning.
        self.assertTrue(game.opening_cinematic.active)
        game.draw()
        self.click(game, game.opening_cinematic.skip_rect.center)
        self.assertFalse(game.opening_cinematic.active)
        self.assertEqual(game.world.data['id'], 'sanctuary_bedroom')
        self.assertEqual(game.opening.stage, 'wake')
        return game

    def finish_script(self, game):
        # Advance prose as fast as real input permits, while allowing required
        # wake-up poses to finish before returning exploration control.
        for _ in range(600):
            if game.social.scripted:
                self.key(game, pygame.K_SPACE)
            elif game.opening.stage != 'wake':
                break
            game.update(1/60, (0, 0), False)
        self.assertFalse(game.social.scripted)
        self.assertFalse(game.social.locked)
        self.assertNotEqual(game.opening.stage, 'wake')

    def walk_to(self, game, target, *, new_scene=None, allow_dialogue=False):
        world = game.world
        route = find_path(world, game.player.position, target,
                          world.probe_size, None)
        self.assertIsNotNone(route, (world.data['id'], tuple(game.player.position), target))
        for point in route:
            for _ in range(600):
                if game.world is not world:
                    self.assertEqual(game.world.data['id'], new_scene)
                    return
                if allow_dialogue and game.social.locked:
                    return
                delta = pygame.Vector2(point)-game.player.position
                if delta.length() < .02:
                    break
                before = game.player.position.copy()
                seconds = min(1/30, delta.length()/main.WALK_SPEED)
                game.update(seconds, delta, False)
                self.assertTrue(world.can_stand(game.player.position) or game.world is not world)
                if game.world is world and game.player.position == before and game.social.locked:
                    self.assertTrue(allow_dialogue)
                    return
            else:
                self.fail(('Walk stalled', world.data['id'], tuple(game.player.position), point))
        if new_scene is not None:
            # A north door may still be opening when Caelan reaches its sensor.
            door = next(door for door in world.doors
                        if tuple(door.data['anchor']) == tuple(target))
            direction = (0, -1) if door.data['entry_side'] == 'north' else (0, 1)
            for _ in range(90):
                if game.world is not world:
                    break
                game.update(1/60, direction, False)
            self.assertEqual(game.world.data['id'], new_scene)

    def enter_breakfast(self, game):
        self.finish_script(game)
        game.update(.6, (0, 0), False)
        self.assertEqual(game.opening.stage, 'explore')
        self.walk_to(game, (144, 306), new_scene='sanctuary_hall')
        self.walk_to(game, (264, 78), new_scene='sanctuary_dining')
        self.assertEqual(game.opening.stage, 'breakfast')
        self.wait_for_breakfast_dialogue(game)

    def wait_for_breakfast_dialogue(self, game):
        for _ in range(900):
            if game.social.scripted:
                break
            game.update(1/60, (0, 0), False)
        self.assertTrue(game.social.scripted)
        # The invitation is spoken at the entrance before walking or sitting.
        self.assertEqual(game.social.script_identifier, 'opening_greeting')

    def finish_breakfast(self, game):
        for _ in range(2400):
            if game.opening.stage == 'assignment':
                break
            if game.social.scripted:
                self.key(game, pygame.K_SPACE)
            game.update(1/60, (0, 0), False)
        self.assertEqual(game.opening.stage, 'assignment')
        self.assertFalse(game.social.locked)
        self.assertTrue(game.world.can_stand(game.player.position))

    def approach_serene(self, game):
        actor = next(actor for actor in game.persistent_npcs
                     if actor.data['id'] == 'mother_serene')
        for _ in range(8):
            if game.social.locked:
                break
            self.assertIs(game._routine_worlds[actor], game.world)
            target = (round(actor.position.x/2)*2, round((actor.position.y+16)/2)*2)
            self.walk_to(game, target, allow_dialogue=True)
            if not game.social.locked:
                game.update(1/60, actor.position-game.player.position, False)
        self.assertTrue(game.social.locked)
        for _ in range(400):
            if game.social.active:
                break
            game.update(1/60, (0, 0), False)
        self.assertTrue(game.social.active)
        self.assertEqual(game.social.conversation['id'], 'serene_quest_offer')
        for _ in range(40):
            if game.social.choosing:
                break
            self.click(game, (1, 1))
        self.assertTrue(game.social.choosing)

    def continue_game(self):
        game = self.game()
        self.assertTrue(game.has_saved_journey)
        self.key(game, pygame.K_DOWN)
        self.assertEqual(game.title.selected, 1)
        self.key(game, pygame.K_RETURN)
        game.update(.7, (0, 0), False)
        self.assertFalse(game.on_title)
        return game

    def assert_single_cast(self, game):
        for actor in game.persistent_npcs:
            memberships = sum(scene.npcs.count(actor) for scene in game.scenes.values())
            self.assertEqual(memberships, 1, actor.data['id'])

    def test_new_game_wakes_in_bedroom_and_gates_quest_until_breakfast(self):
        game = self.new_game()
        self.assertTrue(game.social.scripted)
        self.assertEqual(game.social.script_identifier, 'opening_wake')
        self.assertFalse(game.opening.can_speak('mother_serene'))
        self.assertIsNone(game.quest_ui._marker_for('mother_serene'))
        self.assertEqual(game.quest_ui._journal_rows(), [])
        position = game.player.position.copy()
        game.update(.5, (1, 0), True)
        self.assertEqual(game.player.position, position)
        self.assertEqual(game.quests.status(OPENING_QUEST), 'available')
        game.draw()
        self.finish_script(game)
        self.assertEqual(game.opening.stage, 'explore')
        self.assertFalse(game.opening.locks_player)
        self.assertTrue(game.player.story_visible if hasattr(game.player, 'story_visible') else True)
        self.assert_single_cast(game)

    def test_walk_real_doors_have_breakfast_then_deliberately_accept_assignment(self):
        game = self.new_game()
        self.enter_breakfast(game)
        self.assertFalse(game.opening.can_speak('mother_serene'))
        self.assertIsNone(game.quest_ui._marker_for('mother_serene'))
        game.draw()
        self.finish_breakfast(game)
        self.assertEqual(game.quest_ui._marker_for('mother_serene'), '!')
        self.assertEqual(game.quests.status(OPENING_QUEST), 'available')
        self.approach_serene(game)
        self.key(game, pygame.K_SPACE)
        self.click(game, (1, 1))
        self.assertEqual(game.quests.status(OPENING_QUEST), 'available')
        self.click(game, game.social.choice_rects[0].center)
        self.assertEqual(game.quests.status(OPENING_QUEST), 'active')
        # The choice itself checkpoints the follow-up, including an immediate
        # quit before the first subsequent update frame.
        self.assertEqual(game.opening.stage, 'acceptance')
        saved = json.loads(self.path.read_text())
        self.assertEqual(saved['opening']['stage'], 'acceptance')
        self.assertTrue(game.social.scripted)
        self.assertEqual(game.social.script_identifier, 'opening_acceptance')
        game = self.continue_game()
        self.assertEqual(game.opening.stage, 'acceptance')
        self.assertEqual(game.social.script_identifier, 'opening_acceptance')
        self.assertEqual(game.social.page_index, 0)
        self.assertEqual(game.quests.status(OPENING_QUEST), 'active')
        self.assertIsNone(game.quest_ui.current_notice)
        self.assertEqual(game.quests.drain_events(), [])
        self.finish_script(game)
        self.assertEqual(game.opening.stage, 'done')
        self.assertIn('Halden', game.quests.tracker_text())
        self.assertEqual(game.quests.states[OPENING_QUEST]['completed_objectives'], [])
        self.assertIsNone(game.quest_ui._marker_for('mother_serene'))
        self.assert_single_cast(game)
        saved = json.loads(self.path.read_text())
        self.assertEqual(saved['opening']['stage'], 'done')
        game.draw()
        restored = self.continue_game()
        self.assertEqual(restored.opening.stage, 'done')
        self.assertEqual(restored.quests.status(OPENING_QUEST), 'active')
        self.assertFalse(restored.social.locked)
        self.assertIsNone(restored.quest_ui.current_notice)

    def test_declining_keeps_assignment_available_for_a_later_approach(self):
        game = self.new_game()
        self.enter_breakfast(game)
        self.finish_breakfast(game)
        self.approach_serene(game)
        self.click(game, game.social.choice_rects[1].center)
        game.update(1/60, (0, 0), False)
        self.assertEqual(game.opening.stage, 'assignment')
        self.assertEqual(game.quests.status(OPENING_QUEST), 'available')
        self.assertFalse(game.social.locked)
        self.assertEqual(game.quest_ui._marker_for('mother_serene'), '!')
        self.walk_to(game, (288, 264))
        self.approach_serene(game)
        self.assertTrue(game.social.choosing)
        self.assertEqual(game.quests.status(OPENING_QUEST), 'available')

    def test_optional_bed_rest_offer_uses_e_without_advancing_the_story(self):
        game = self.new_game()
        self.finish_script(game)
        game.update(.6, (0, 0), False)
        # The real bedside remains reachable after the authored wake-up.
        self.walk_to(game, game.world.data['destinations']['bed'])
        self.assertEqual(game.bed_rest.interaction_hint(), 'E: rest')
        progress = game.quests.to_dict()
        position = game.player.position.copy()
        self.key(game, pygame.K_e)
        self.assertTrue(game.social.scripted)
        self.assertEqual(game.social.script_identifier, 'bed_rest_offer')
        self.assertEqual(game.social.page['speaker'], 'caelan')
        game.update(.2, (1, 0), True)
        self.assertGreater(game.player.position.x, position.x)
        self.assertTrue(game.social.scripted)
        game.social.advance()
        self.assertTrue(game.social.choosing)
        self.click(game, game.social.choice_rects[1].center)
        self.assertFalse(game.social.locked)
        self.assertEqual(game.opening.stage, 'explore')
        self.assertEqual(game.quests.to_dict(), progress)

    def test_continue_replays_only_unfinished_wake_or_breakfast_scene(self):
        game = self.new_game()
        for _ in range(2):
            self.key(game, pygame.K_SPACE)
        self.assertTrue(game.save_progress())
        restored = self.continue_game()
        self.assertEqual(restored.opening.stage, 'wake')
        self.assertEqual(restored.social.page_index, 0)
        self.assertEqual(restored.social.script_identifier, 'opening_wake')
        self.assert_single_cast(restored)
        self.enter_breakfast(restored)
        self.key(restored, pygame.K_SPACE)
        self.assertTrue(restored.save_progress())
        breakfast = self.continue_game()
        self.assertEqual(breakfast.opening.stage, 'breakfast')
        self.assertEqual(breakfast.world.data['id'], 'sanctuary_dining')
        self.wait_for_breakfast_dialogue(breakfast)
        self.assertEqual(breakfast.social.page_index, 0)
        self.assertEqual(breakfast.social.script_identifier, 'opening_greeting')
        self.assert_single_cast(breakfast)
        self.assertIsNone(breakfast.quest_ui.current_notice)
        self.finish_breakfast(breakfast)
        self.assertTrue(breakfast.save_progress())
        assignment = self.continue_game()
        self.assertEqual(assignment.opening.stage, 'assignment')
        self.assertFalse(assignment.social.locked)
        self.assertEqual(assignment.world.data['id'], 'sanctuary_dining')
        self.assert_single_cast(assignment)

    def test_continue_exploration_keeps_location_without_replaying_wake(self):
        game = self.new_game()
        self.finish_script(game)
        game.update(.6, (0, 0), False)
        self.walk_to(game, (144, 306), new_scene='sanctuary_hall')
        self.assertTrue(game.save_progress())
        position = game.player.position.copy()
        restored = self.continue_game()
        self.assertEqual(restored.opening.stage, 'explore')
        self.assertEqual(restored.world.data['id'], 'sanctuary_hall')
        self.assertEqual(restored.player.position, position)
        self.assertFalse(restored.social.locked)
        self.assertIsNone(restored.quest_ui._marker_for('mother_serene'))
        self.assert_single_cast(restored)

    def test_legacy_checkpoint_preserves_progress_location_and_ambient_behavior(self):
        game = self.game(title=False)
        game.quests.accept(OPENING_QUEST)
        game.quests.complete_objective(OPENING_QUEST, 'halden')
        game.social.flags.add('tomas_greeted')
        game.world = game._scene_by_id('elira')
        game.player.position.update(game.world.data['spawn'])
        self.assertTrue(game.save_progress())
        snapshot = json.loads(self.path.read_text())
        del snapshot['opening']
        self.path.write_text(json.dumps(snapshot))
        restored = self.continue_game()
        self.assertEqual(restored.opening.stage, 'disabled')
        self.assertEqual(restored.world.data['id'], 'elira')
        self.assertEqual(restored.quests.to_dict(), snapshot['quests'])
        self.assertIn('tomas_greeted', restored.social.flags)
        self.assertFalse(restored.social.locked)
        self.assertTrue(restored.opening.can_speak('mother_serene'))
        self.assertIsNone(restored.quest_ui.current_notice)

    def test_invalid_opening_checkpoint_disables_continue_without_touching_save(self):
        game = self.new_game()
        snapshot = json.loads(self.path.read_text())
        for opening in ({'version': 1, 'stage': 'unknown'},
                        {'version': True, 'stage': 'wake'},
                        {'version': 1}, None):
            with self.subTest(opening=opening):
                data = dict(snapshot, opening=opening)
                raw = json.dumps(data)
                self.path.write_text(raw)
                restored = self.game()
                self.assertFalse(restored.has_saved_journey)
                self.assertIsNotNone(restored.save_error)
                self.assertEqual(self.path.read_text(), raw)
                self.assertEqual(restored.title.fade, 0)


if __name__ == '__main__':
    unittest.main()
