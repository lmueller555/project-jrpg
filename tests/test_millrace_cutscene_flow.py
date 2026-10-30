"""Production MQ02 arrival staging, camera cues and transient recovery."""
import json
import os
from pathlib import Path
import unittest

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame
import test_mill_battle_gameplay as mill_fixture
from mill_quest import FACTS


class MillraceCutsceneFlowTests(unittest.TestCase):
    def setUp(self):
        self.fixture = mill_fixture.MillBattleGameplayTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.addCleanup(self.fixture.tearDown)
        self.fixture.diagnose()
        self.quest = self.fixture.enter_path()
        self.game = self.fixture.game

    def tick(self, seconds=.05):
        self.game.update(seconds, (0, 0), False)

    def conversation(self):
        for _ in range(200):
            if self.game.social.active:
                self.assertEqual(self.game.social.script_identifier, 'mill_encounter_intro')
                return
            self.tick()
        self.fail('The arriving party did not reach the boar conversation')

    def warning(self):
        self.conversation()
        for _ in range(100):
            page = self.game.social.page
            if page and page.get('cue') == 'mill_return_to_party':
                self.tick(0)
                self.assertEqual(self.quest.encounter_cutscene_phase, 'pan_back')
                return
            mill_fixture.key(self.game, pygame.K_SPACE)
            self.tick()
        self.fail('The final warning was not presented')

    def battle(self):
        for _ in range(300):
            if self.game.combat.active:return
            if self.game.social.active:mill_fixture.key(self.game, pygame.K_SPACE)
            self.tick()
        self.fail('The returned party did not enter battle')

    def test_arrival_stops_both_actors_and_holds_the_boar_before_any_fight(self):
        self.assertEqual(tuple(self.game.player.position), tuple(self.quest.upstream.data['spawn']))
        self.assertTrue(self.quest.encounter_cutscene_active)
        self.conversation()
        positions = tuple(self.game.player.position), tuple(self.quest.mira.position)
        camera = self.game.camera.position()
        self.assertEqual(self.quest.encounter_cutscene_phase, 'conversation')
        self.assertTrue(self.game.camera.scripted)
        self.assertTrue(self.game.camera.settled)
        self.assertGreater(camera[0], 0)
        self.game.update(1, (1, -1), True)
        self.assertEqual(positions, (tuple(self.game.player.position), tuple(self.quest.mira.position)))
        self.assertEqual(camera, self.game.camera.position())
        self.assertFalse(self.game.player.moving)
        self.assertFalse(self.quest.mira.moving)
        self.assertFalse(hasattr(self.game.player, 'story_sprite'))
        self.assertFalse(hasattr(self.quest.mira, 'story_sprite'))
        self.assertFalse(self.game.combat.active)
        self.assertEqual(self.game.music.desired_track, 'eldenmere')

    def test_fast_warning_acknowledgement_still_waits_for_the_return_pan(self):
        self.warning()
        start = self.game.camera.position()
        mill_fixture.key(self.game, pygame.K_SPACE)
        self.assertFalse(self.game.social.active)
        self.tick(.2)
        self.assertNotEqual(start, self.game.camera.position())
        self.assertFalse(self.game.combat.active)
        self.assertEqual(self.game.music.desired_track, 'eldenmere')
        self.assertTrue(self.quest.locks_player)
        self.battle()
        self.assertFalse(self.game.camera.scripted)
        self.assertEqual(self.game.camera.position(), (0, 256))
        self.assertEqual(self.game.music.desired_track, 'battle')
        self.assertTrue(self.game.combat.transitioning)

    def test_slow_reader_keeps_warning_and_party_shot_until_acknowledgement(self):
        self.warning()
        for _ in range(20):self.tick()
        self.assertTrue(self.game.camera.settled)
        self.assertTrue(self.game.social.active)
        self.assertFalse(self.game.combat.active)
        self.assertEqual(self.game.music.desired_track, 'eldenmere')
        self.assertIn('come back to me', self.game.social.page['lines'][0])
        mill_fixture.key(self.game, pygame.K_SPACE)
        self.tick(0)
        self.assertTrue(self.game.combat.active)
        self.assertEqual(self.game.music.desired_track, 'battle')

    def test_script_completion_between_ticks_cannot_skip_or_strand_the_return(self):
        self.conversation()
        while self.game.social.active:self.game.social.advance()
        self.tick(.05)
        self.assertEqual(self.quest.encounter_cutscene_phase, 'pan_back')
        self.assertFalse(self.game.combat.active)
        self.assertEqual(self.game.music.desired_track, 'eldenmere')
        self.battle()
        self.assertEqual(self.game.music.desired_track, 'battle')

    def test_cancel_releases_camera_and_locks_and_requires_an_explicit_retry(self):
        self.conversation()
        self.game.social.cancel()
        self.assertFalse(self.quest.encounter_cutscene_active)
        self.assertFalse(self.quest.locks_player)
        self.assertFalse(self.game.camera.scripted)
        self.assertEqual(self.game.music.desired_track, 'eldenmere')
        self.tick(1)
        self.assertFalse(self.game.social.active)
        self.assertFalse(self.game.combat.active)
        self.assertTrue(self.quest.begin_encounter(self.game.combat.start_mill))
        self.assertFalse(self.quest.begin_encounter(self.game.combat.start_mill))
        self.assertEqual(self.quest.encounter_cutscene_phase, 'noticing')

    def test_transfer_and_reload_clear_transient_shots_without_new_quest_facts(self):
        self.conversation()
        facts = self.quest.to_dict()
        self.assertTrue(self.game.save_progress())
        saved = json.loads(self.fixture.path.read_text())
        self.assertEqual(set(saved['mill_quest']), {'version', 'inspected', *FACTS})
        self.assertNotIn('post_battle', saved)
        restored = self.fixture.new_game(title=True)
        self.assertTrue(restored.begin_journey(True))
        self.assertFalse(restored.camera.scripted)
        self.assertFalse(restored.combat.active)
        self.assertEqual(tuple(restored.player.position), tuple(restored.mill_quest.upstream.data['spawn']))
        self.assertEqual(restored.mill_quest.to_dict(), facts)
        self.assertEqual(restored.music.desired_track, 'eldenmere')
        for _ in range(60):
            restored.update(.05, (0, 0), False)
            if restored.mill_quest.encounter_cutscene_active:break
        self.assertTrue(restored.mill_quest.encounter_cutscene_active)
        self.game.world = self.game.town
        self.tick()
        self.assertFalse(self.quest.encounter_cutscene_active)
        self.assertFalse(self.game.camera.scripted)

    def test_reduced_motion_uses_static_shots_but_preserves_order(self):
        self.game.audio.set_reduced_motion(True)
        self.conversation()
        self.assertTrue(self.game.camera.settled)
        self.assertEqual(self.game.music.desired_track, 'eldenmere')
        self.warning()
        self.assertTrue(self.game.camera.settled)
        self.assertFalse(self.game.combat.active)
        mill_fixture.key(self.game, pygame.K_SPACE)
        self.tick(0)
        self.assertTrue(self.game.combat.active)
        self.assertEqual(self.game.music.desired_track, 'battle')

    def test_enabling_reduced_motion_mid_pan_completes_the_shot_after_resume(self):
        for _ in range(100):
            self.tick()
            if self.quest.encounter_cutscene_phase == 'pan_to_boar':break
        self.assertFalse(self.game.camera.settled)
        mill_fixture.key(self.game, pygame.K_ESCAPE)
        paused = self.game.camera.position()
        self.game.audio.set_reduced_motion(True)
        self.tick(1)
        self.assertEqual(self.game.camera.position(), paused)
        self.game.pause.close()
        self.tick(0)
        self.assertTrue(self.game.camera.settled)
        self.assertEqual(self.quest.encounter_cutscene_phase, 'conversation')
        self.assertEqual(self.game.music.desired_track, 'eldenmere')

    def test_flee_returns_without_automatically_replaying_the_entry_cutscene(self):
        self.battle()
        mill_fixture.finish_mill_battle(self.game, command='flee', dismiss=True)
        mill_fixture.read_social(self.game)
        for _ in range(30):self.tick()
        self.assertFalse(self.game.combat.active)
        self.assertFalse(self.quest.encounter_cutscene_active)
        self.assertTrue(self.quest.encounter_pending)
        self.assertTrue(self.quest.begin_encounter(self.game.combat.start_mill))


if __name__ == '__main__':unittest.main()
