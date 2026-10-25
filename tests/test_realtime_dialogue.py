"""Real input, live movement and quest safety for world-space conversations."""
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
from quests import OPENING_QUEST


class RealtimeDialogueTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.save_path = Path(self.directory.name)/'journey.json'
        self.game = main.Game(fullscreen=False, start_on_title=False,
                              save_path=self.save_path)
        self.game.audio.set_music(0)
        self.game.audio.set_effects(0)
        self.actor = next(actor for actor in self.game.persistent_npcs
                          if actor.data['id'] == 'mother_serene')
        self.game.world = self.game._scene_by_id('sanctuary_dining')
        self.game.player.position.update(288, 231)
        self.game.player.facing = 'back'
        self.game.camera.reset()
        pygame.event.clear()

    def tearDown(self):
        pygame.quit()

    def approach(self):
        self.game.update(1/60, (0, -1), False)
        self.assertTrue(self.game.social.active)

    def key(self, key):
        for kind in (pygame.KEYDOWN, pygame.KEYUP):
            pygame.event.post(pygame.event.Event(kind, key=key, repeat=False))
        self.assertTrue(self.game.handle_events())

    def click_window(self, point):
        for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            pygame.event.post(pygame.event.Event(kind, button=1, pos=point))
        self.assertTrue(self.game.handle_events())

    def click_canvas(self, point):
        width, height = self.game.window.get_size()
        scale = max(1, min(width//480, height//320))
        self.click_window((round((width-480*scale)//2+point[0]*scale),
                           round((height-320*scale)//2+point[1]*scale)))

    def reach_choice(self):
        for _ in range(40):
            if self.game.social.choosing:
                return
            self.assertTrue(self.game.social.active)
            self.click_canvas((1, 1))
        self.fail('Quest offer did not expose its explicit choices')

    def test_player_moves_while_speaker_pauses_and_other_routines_continue(self):
        self.approach()
        initial = self.game.player.position.copy()
        actor_clock = self.actor.state_ms
        gardener = next(npc for npc in self.game.town.npcs
                        if isinstance(npc, main.Gardener))
        garden_clock = gardener.state_ms
        elapsed = self.game.elapsed_ms
        for _ in range(6):
            self.game.update(1/60, (1, 0), False)
        self.assertTrue(self.game.social.active)
        self.assertGreater(self.game.player.position.x, initial.x+6)
        self.assertTrue(self.game.player.moving)
        self.assertEqual(self.actor.state_ms, actor_clock)
        self.assertGreater(self.game.elapsed_ms, elapsed)
        self.assertNotEqual(gardener.state_ms, garden_clock)
        self.assertEqual(self.game.camera.framing_height, 320)

    def test_normal_conversation_never_reframes_the_camera(self):
        expected = self.game.camera.position()
        self.approach()
        for _ in range(30):
            self.game.update(1/60, (0, 0), False)
        self.assertEqual(self.game.camera.position(), expected)
        self.assertEqual(self.game.camera.framing_height, 320)
        self.reach_choice()
        self.game.draw()
        self.assertEqual(self.game.camera.position(), expected)
        self.assertEqual(self.game.camera.framing_height, 320)

    def test_alternating_lines_follow_the_actual_speaker(self):
        self.approach()
        self.assertEqual(self.game.social.page['speaker'], 'serene')
        self.assertIs(self.game.social.resolve_speaker(), self.actor)
        self.click_canvas((1, 1))
        self.assertEqual(self.game.social.page['speaker'], 'caelan')
        self.assertIs(self.game.social.resolve_speaker(), self.game.player)
        before = pygame.Vector2(self.game.social.anchor_position())
        self.game.update(.08, (1, 0), False)
        after = pygame.Vector2(self.game.social.anchor_position())
        self.assertGreater(after.x, before.x)
        # The head follows the approved one-pixel walk bob.
        self.assertLessEqual(abs(after.y-before.y), 2)

    def test_walking_away_does_not_accept_quest_or_set_conversation_flags(self):
        self.approach()
        self.reach_choice()
        for _ in range(45):
            self.game.update(1/60, (0, 1), False)
        self.assertFalse(self.game.social.locked)
        self.assertFalse(self.actor.conversation_requested)
        self.assertFalse(self.actor.conversation_ready)
        self.assertNotIn('serene_greeted', self.game.social.flags)
        self.assertEqual(self.game.quests.status(OPENING_QUEST), 'available')
        self.game.player.position.update(288, 231)
        self.game.player.facing = 'back'
        self.approach()
        self.assertEqual(self.game.social.conversation['id'], 'serene_quest_offer')

    def test_walking_away_from_report_does_not_turn_quest_in(self):
        self.assertTrue(self.game.quests.accept(OPENING_QUEST))
        for identifier in ('halden', 'elira', 'venn'):
            self.assertTrue(self.game.quests.complete_objective(OPENING_QUEST, identifier))
        self.approach()
        self.assertEqual(self.game.social.conversation['id'], 'serene_quest_report')
        self.click_canvas((1, 1))
        self.game.player.position.update(288, 280)
        self.game.update(1/60, (0, 0), False)
        self.assertFalse(self.game.social.locked)
        self.assertEqual(self.game.quests.status(OPENING_QUEST), 'ready')
        self.assertEqual(self.game.quests.marker_for('mother_serene'), '?')

    def test_pending_prop_handoff_can_be_abandoned_without_losing_held_item(self):
        self.actor.state_ms = 1100
        self.assertEqual(self.actor.current_action_record['prop_owner'], 'actor')
        self.game.update(1/60, (0, -1), False)
        self.assertTrue(self.game.social.pending)
        self.game.player.position.update(288, 280)
        self.game.update(1/60, (0, 0), False)
        self.assertFalse(self.game.social.locked)
        self.assertFalse(self.actor.conversation_requested)
        for _ in range(15):
            self.game.update(1/60, (0, 0), False)
        self.assertFalse(self.actor.conversation_ready)
        self.assertNotIn('serene_greeted', self.game.social.flags)

    def test_quest_options_ignore_outside_clicks_and_follow_scaled_letterboxing(self):
        self.approach()
        self.reach_choice()
        for size in ((1100, 750), (1440, 810), (800, 800)):
            with self.subTest(size=size):
                self.game.window = pygame.display.set_mode(size)
                self.game.draw()
                rects = self.game.social.choice_rects
                self.assertEqual(len(rects), 2)
                self.assertFalse(rects[0].colliderect(rects[1]))
                for rect in rects:
                    self.assertTrue(pygame.Rect(0, 0, 480, 320).contains(rect))
                self.click_window((0, 0))
                self.click_canvas((1, 1))
                self.key(pygame.K_SPACE)
                self.key(pygame.K_e)
                self.assertTrue(self.game.social.choosing)
                self.assertEqual(self.game.quests.status(OPENING_QUEST), 'available')
        self.click_canvas(self.game.social.choice_rects[0].center)
        self.assertFalse(self.game.social.active)
        self.assertEqual(self.game.quests.status(OPENING_QUEST), 'active')
        saved = json.loads(self.save_path.read_text())
        self.assertEqual(saved['quests'], self.game.quests.to_dict())
        self.assertIn('serene_greeted', saved['dialogue_flags'])

    def test_declining_stays_available_and_nearby_motion_does_not_retrigger(self):
        self.approach()
        self.reach_choice()
        self.game.draw()
        self.click_canvas(self.game.social.choice_rects[1].center)
        self.assertFalse(self.game.social.locked)
        self.assertEqual(self.game.quests.status(OPENING_QUEST), 'available')
        self.assertIn(self.actor, self.game.social.blocked)
        for _ in range(5):
            self.game.update(1/60, (0, -1), False)
        self.assertFalse(self.game.social.locked)
        self.game.player.position.update(288, 280)
        self.game.update(1/60, (0, 0), False)
        self.game.player.position.update(288, 231)
        self.game.player.facing = 'back'
        self.approach()

    def test_map_and_journal_intercept_clicks_without_advancing_conversation(self):
        self.approach()
        page = self.game.social.page_index
        self.key(pygame.K_m)
        self.assertTrue(self.game.map_open)
        self.click_canvas((1, 1))
        self.assertEqual(self.game.social.page_index, page)
        self.key(pygame.K_ESCAPE)
        self.assertFalse(self.game.map_open)
        self.key(pygame.K_j)
        self.assertTrue(self.game.quest_ui.journal_open)
        self.click_canvas((1, 1))
        self.assertEqual(self.game.social.page_index, page)
        self.key(pygame.K_ESCAPE)
        self.assertFalse(self.game.quest_ui.journal_open)
        self.click_canvas((1, 1))
        self.assertEqual(self.game.social.page_index, page+1)

    def test_pause_freezes_live_dialogue_and_resume_doubleclick_has_no_fallthrough(self):
        self.approach()
        page = self.game.social.page_index
        self.key(pygame.K_ESCAPE)
        self.assertTrue(self.game.pause.is_open)
        position = self.game.player.position.copy()
        clock = self.game.elapsed_ms
        for _ in range(10):
            self.game.update(.05, (1, 0), True)
        self.assertEqual(self.game.player.position, position)
        self.assertEqual(self.game.elapsed_ms, clock)
        width, height = self.game.window.get_size()
        scale = max(1, min(width//480, height//320))
        x, y = self.game.pause.rows[0].center
        point = (round((width-480*scale)//2+x*scale),
                 round((height-320*scale)//2+y*scale))
        for _ in range(2):
            for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
                pygame.event.post(pygame.event.Event(kind, button=1, pos=point))
        self.assertTrue(self.game.handle_events())
        self.assertFalse(self.game.pause.is_open)
        self.assertEqual(self.game.social.page_index, page)
        self.click_canvas((1, 1))
        self.assertEqual(self.game.social.page_index, page+1)

    def test_door_transfer_cancels_unfinished_conversation_without_progress(self):
        self.approach()
        door = self.game.world.doors[0]
        destination = self.game._load_scene(main.ROOT/door.data['destination'])
        self.assertTrue(destination.can_stand(door.data['spawn']))
        self.assertTrue(self.game.enter(door))
        self.assertIs(self.game.world, destination)
        self.assertFalse(self.game.social.locked)
        self.assertFalse(self.actor.conversation_requested)
        self.assertNotIn('serene_greeted', self.game.social.flags)
        self.assertEqual(self.game.quests.status(OPENING_QUEST), 'available')

    def test_opening_acceptance_choices_work_without_movement_or_camera_lock(self):
        self.assertTrue(self.game.opening.restore({'version': 1, 'stage': 'assignment'}))
        self.game.player.position.update(288, 231)
        self.game.player.facing = 'back'
        self.approach()
        self.reach_choice()
        self.game.draw()
        self.click_canvas(self.game.social.choice_rects[0].center)
        self.assertEqual(self.game.quests.status(OPENING_QUEST), 'active')
        self.assertEqual(self.game.opening.stage, 'acceptance')
        self.assertTrue(self.game.social.scripted)
        self.assertFalse(self.game.opening.locks_player)
        before = self.game.player.position.copy()
        self.game.update(.08, (1, 0), False)
        self.assertGreater(self.game.player.position.x, before.x)
        self.assertEqual(self.game.camera.framing_height, 320)
        for _ in range(30):
            if not self.game.social.scripted:
                break
            self.click_canvas((1, 1))
            self.game.update(1/60, (0, 0), False)
        self.assertEqual(self.game.opening.stage, 'done')
        self.assertEqual(self.game.quests.status(OPENING_QUEST), 'active')
        self.assertFalse(self.game.opening.locks_player)

    def test_walking_away_from_breakfast_invitation_keeps_it_available_in_room(self):
        self.assertTrue(self.game.opening.restore({'version': 1, 'stage': 'breakfast'}))
        self.assertEqual(self.game.social.script_identifier, 'opening_greeting')
        self.assertFalse(self.game.opening.locks_player)
        before = self.game.player.position.copy()
        for _ in range(40):
            self.game.update(1/60, (0, -1), False)
        self.assertGreater(before.y-self.game.player.position.y, 36)
        self.assertFalse(self.game.social.locked)
        self.assertEqual(self.game.opening.stage, 'explore')
        self.assertFalse(self.game.opening.in_action)
        self.assertFalse(hasattr(self.game.player, 'story_sprite'))
        self.assertEqual(self.game.quests.status(OPENING_QUEST), 'available')
        # Returning to the table can resume the invitation without having to
        # exit/reenter the building or being pulled into the chair remotely.
        self.game.player.position.update(108, 225)
        self.assertIn('join breakfast', self.game.opening.interaction_hint())
        position = self.game.player.position.copy()
        self.key(pygame.K_e)
        self.assertEqual(self.game.social.script_identifier, 'opening_greeting')
        self.assertEqual(self.game.player.position, position)
        self.assertFalse(self.game.opening.locks_player)

    def test_leaving_accepted_quest_banter_releases_cast_and_preserves_acceptance(self):
        self.assertTrue(self.game.opening.restore({'version': 1, 'stage': 'assignment'}))
        self.game.player.position.update(288, 231)
        self.game.player.facing = 'back'
        self.approach()
        self.reach_choice()
        self.click_canvas(self.game.social.choice_rects[0].center)
        self.assertEqual(self.game.opening.stage, 'acceptance')
        for _ in range(45):
            self.game.update(1/60, (0, 1), False)
        self.assertFalse(self.game.social.locked)
        self.assertEqual(self.game.opening.stage, 'done')
        self.assertEqual(self.game.quests.status(OPENING_QUEST), 'active')
        cast = [actor for actor in self.game.persistent_npcs
                if actor.data['id'] in ('mother_serene', 'tomas')]
        self.assertEqual(len(cast), 2)
        self.assertTrue(all(not actor.story_paused for actor in cast))
        before = [(actor.state, actor.state_ms, tuple(actor.position)) for actor in cast]
        for _ in range(12):
            self.game.update(1/60, (0, 0), False)
        self.assertNotEqual([(actor.state, actor.state_ms, tuple(actor.position)) for actor in cast], before)
        self.assertEqual(self.game.quests.states[OPENING_QUEST]['completed_objectives'], [])
        saved = json.loads(self.save_path.read_text())
        self.assertEqual(saved['opening']['stage'], 'done')
        self.assertEqual(saved['quests'], self.game.quests.to_dict())


if __name__ == '__main__':
    unittest.main()
