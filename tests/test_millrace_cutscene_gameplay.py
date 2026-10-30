"""Real millrace arrival, camera choreography, dialogue and battle handoff."""
import json
import os
import unittest

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame
import test_mill_battle_gameplay as fixture
from quests import MILL_QUEST


class MillraceCutsceneGameplayTests(unittest.TestCase):
    def setUp(self):
        self.h = fixture.MillBattleGameplayTests()
        self.h.setUp()
        self.addCleanup(self.h.doCleanups)
        self.addCleanup(self.h.tearDown)
        self.g = self.h.game
        self.c = self.g.mill_quest

    def tick(self, seconds=.05, direction=(0, 0), running=False):
        self.g.update(seconds, direction, running)

    def until(self, predicate, limit=250):
        for _ in range(limit):
            if predicate():return
            self.tick()
        self.fail(('Cutscene did not reach state', self.c.encounter_cutscene_phase,
                   self.g.social.script_identifier, self.g.camera.position()))

    def enter(self):
        self.h.diagnose()
        self.h.place((720, 12), self.g.town)
        fixture.key(self.g, pygame.K_e)
        self.assertIs(self.g.world, self.c.upstream)
        self.arrival = tuple(self.g.player.position)
        self.start_camera = self.g.camera.position()
        self.assertGreater(self.arrival[1], 384)  # Beyond the former northward trigger.
        self.until(lambda: self.c.encounter_cutscene_active)
        self.assertFalse(self.g.combat.active)

    def conversation(self):
        self.enter()
        self.until(lambda: self.g.social.active)
        self.assertEqual(self.g.social.script_identifier, 'mill_encounter_intro')
        self.assertEqual(self.c.encounter_cutscene_phase, 'conversation')
        self.assertTrue(self.g.camera.settled)

    def warning(self):
        self.conversation()
        for _ in range(80):
            page = self.g.social.page
            if page and page.get('cue') == 'mill_return_to_party':
                self.tick(0)
                self.assertEqual(self.c.encounter_cutscene_phase, 'pan_back')
                return
            self.assertEqual(self.g.music.desired_track, 'eldenmere')
            fixture.key(self.g, pygame.K_SPACE)
            self.tick(0)
        self.fail('Mira did not give her return warning')

    def test_arrival_stops_both_actors_before_the_old_distant_trigger(self):
        self.enter()
        self.until(lambda: self.c.encounter_cutscene_phase == 'pan_to_boar')
        actors = tuple(self.g.player.position), tuple(self.c.mira.position)
        for _ in range(24):
            self.tick(.05, (0, -1), True)
            self.assertEqual(tuple(self.g.player.position), self.arrival)
            self.assertEqual((tuple(self.g.player.position), tuple(self.c.mira.position)), actors)
        self.assertTrue(self.g.social.active)
        self.assertFalse(self.g.player.moving)
        self.assertFalse(self.c.mira.moving)
        self.assertEqual(sum(self.c.mira in world.npcs for world in self.g.scenes.values()), 1)

    def test_camera_moves_to_boar_then_holds_during_player_paced_dialogue(self):
        self.conversation()
        camera = self.g.camera.position()
        self.assertNotEqual(camera, self.start_camera)
        self.assertTrue(self.g.camera.scripted)
        boar = pygame.Vector2(self.c.points['combat_position'])-pygame.Vector2(camera)
        self.assertTrue(0 < boar.x < 480 and 0 < boar.y < 160)
        page = dict(self.g.social.page)
        for _ in range(20):self.tick(.1, (-1, 0), True)
        self.assertEqual(self.g.camera.position(), camera)
        self.assertEqual(self.g.social.page, page)
        self.assertEqual(tuple(self.g.player.position), self.arrival)
        self.assertEqual(self.g.music.desired_track, 'eldenmere')
        self.assertFalse(self.g.combat.active)

    def test_fast_warning_acknowledgement_cannot_skip_return_pan_or_start_music_early(self):
        self.warning()
        self.assertFalse(self.g.camera.settled)
        fixture.key(self.g, pygame.K_SPACE)
        self.tick(.1)
        self.assertFalse(self.g.combat.active)
        self.assertEqual(self.g.music.desired_track, 'eldenmere')
        self.until(lambda: self.g.combat.active)
        self.assertTrue(self.g.camera.settled)
        self.assertFalse(self.g.camera.scripted)
        self.assertFalse(self.c.encounter_cutscene_active)
        self.assertEqual(self.g.music.desired_track, 'battle')
        self.assertTrue(self.g.combat.transitioning)
        self.assertTrue(all(actor.atb == 0 for actor in
                            (*self.g.combat.model.party, self.g.combat.model.enemy)))

    def test_returned_camera_waits_for_the_player_to_acknowledge_the_warning(self):
        self.warning()
        self.until(lambda: self.g.camera.settled)
        self.tick(.5)
        self.assertTrue(self.g.social.active)
        self.assertFalse(self.g.combat.active)
        self.assertEqual(self.g.music.desired_track, 'eldenmere')
        fixture.key(self.g, pygame.K_SPACE)
        self.until(lambda: self.g.combat.active)
        self.assertEqual(self.g.music.desired_track, 'battle')

    def test_pan_rejects_extra_interaction_and_menu_keys_without_skipping_prose(self):
        self.enter()
        self.until(lambda: self.c.encounter_cutscene_phase == 'pan_to_boar')
        for key in (pygame.K_i, pygame.K_m, pygame.K_j, pygame.K_e, pygame.K_SPACE):
            fixture.key(self.g, key)
        self.assertFalse(self.g.inventory_ui.is_open)
        self.assertFalse(self.g.quest_ui.journal_open)
        self.assertFalse(self.g.map_open)
        self.assertFalse(self.g.social.active)
        self.assertFalse(self.g.combat.active)
        self.until(lambda: self.g.social.active)
        self.assertEqual(self.g.social.page['source_line'], 0)

    def test_pause_and_lost_focus_freeze_the_pan_and_resume_it(self):
        self.enter();self.until(lambda: self.c.encounter_cutscene_phase == 'pan_to_boar')
        self.tick(.15)
        shot = self.g.camera.position()
        fixture.key(self.g, pygame.K_ESCAPE)
        self.tick(2)
        self.assertEqual(self.g.camera.position(), shot)
        self.assertFalse(self.g.social.active)
        fixture.key(self.g, pygame.K_ESCAPE)
        pygame.event.post(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        self.assertTrue(self.g.handle_events())
        self.tick(2)
        self.assertEqual(self.g.camera.position(), shot)
        pygame.event.post(pygame.event.Event(pygame.WINDOWFOCUSGAINED))
        self.assertTrue(self.g.handle_events())
        self.until(lambda: self.g.social.active)
        self.assertNotEqual(self.g.camera.position(), shot)

    def test_cutscene_prose_remains_readable_and_leaves_the_boar_visible_at_large_text(self):
        self.conversation()
        self.g.window = pygame.display.set_mode((480, 320), pygame.RESIZABLE)
        self.g.audio.set_text_scale(1.5)
        self.g.draw()
        panel = self.g.social.bubble.layout().panel
        self.assertTrue(pygame.Rect(0, 0, 480, 320).contains(panel))
        ground_y = self.c.points['combat_position'][1]-self.g.camera.position()[1]
        self.assertGreater(panel.top, ground_y+10)
        self.assertIn('Mira', json.dumps(self.c.lines['encounter_intro']))

    def test_quit_during_a_pan_restarts_staging_at_safe_entry_without_camera_or_music_facts(self):
        self.enter();self.until(lambda: self.c.encounter_cutscene_phase == 'pan_to_boar')
        self.tick(.2)
        pygame.event.post(pygame.event.Event(pygame.QUIT))
        self.assertFalse(self.g.handle_events())
        saved = json.loads(self.h.path.read_text())
        self.assertNotIn('camera', saved)
        self.assertNotIn('encounter_cutscene_phase', saved['mill_quest'])
        self.assertNotIn('mill_return_to_party', json.dumps(saved))
        other = self.h.new_game(True)
        self.assertTrue(other.begin_journey(True))
        self.assertEqual(list(other.player.position), other.mill_quest.upstream.data['spawn'])
        self.assertEqual(other.music.desired_track, 'eldenmere')
        self.assertFalse(other.combat.active)
        for _ in range(180):
            if other.social.active:break
            other.update(.05, (0, 0), False)
        self.assertEqual(other.social.script_identifier, 'mill_encounter_intro')
        self.assertEqual(other.social.page['source_line'], 0)

    def test_cancel_releases_staging_and_camera_without_completing_encounter(self):
        self.conversation()
        self.assertTrue(self.g.social.cancel())
        self.tick(0)
        self.assertFalse(self.c.encounter_cutscene_active)
        self.assertFalse(self.c.locks_player)
        self.assertFalse(self.g.camera.scripted)
        self.assertTrue(self.c.encounter_pending)
        self.assertFalse(self.g.combat.active)
        self.assertEqual(self.g.music.desired_track, 'eldenmere')
        self.assertTrue(self.c.begin_encounter(self.g.combat.start_mill))
        self.until(lambda: self.g.social.active)
        self.assertEqual(self.g.social.page['source_line'], 0)

    def test_cancel_during_return_pan_releases_the_camera_immediately(self):
        self.warning()
        self.tick(.1)
        self.assertFalse(self.g.camera.settled)
        self.assertTrue(self.g.social.cancel())
        self.tick(0)
        self.assertFalse(self.g.camera.scripted)
        self.assertFalse(self.c.encounter_cutscene_active)
        self.assertFalse(self.c.locks_player)
        self.assertFalse(self.g.combat.active)
        self.assertEqual(self.g.music.desired_track, 'eldenmere')
        self.tick(1)
        self.assertFalse(self.g.social.active)
        self.assertFalse(self.g.combat.active)

    def restore_spoils(self, awarded):
        self.h.start()
        fixture.finish_mill_battle(self.g, dismiss=False)
        if awarded:fixture.wait_for_spoils(self.g)
        saved = json.loads(self.h.path.read_text())
        self.assertEqual(saved['post_battle']['stage'], 'awarded' if awarded else 'pending')
        pygame.event.post(pygame.event.Event(pygame.QUIT))
        self.assertFalse(self.g.handle_events())
        other = self.h.new_game(True)
        self.assertTrue(other.begin_journey(True))
        self.assertTrue(other.combat.active)
        self.assertEqual(other.combat.post_phase, 'spoils')
        self.assertFalse(other.mill_quest.encounter_cutscene_active)
        self.assertFalse(other.camera.scripted)
        self.assertFalse(other.social.active)
        self.assertTrue(other.combat.spoils.awarded)
        other.draw();fixture.click(other, other.combat.spoils.continue_rect.center)
        other.update(0, (0, 0), False)
        self.assertFalse(other.combat.active)
        self.assertFalse(other.mill_quest.encounter_cutscene_active)
        self.assertFalse(other.camera.scripted)
        self.assertEqual(other.social.script_identifier, 'mill_aftermath')
        fixture.read_social(other)
        self.assertTrue(other.mill_quest.aftermath_done)

    def test_unawarded_spoils_reload_bypasses_the_arrival_cutscene(self):
        self.restore_spoils(False)

    def test_awarded_spoils_reload_bypasses_the_arrival_cutscene(self):
        self.restore_spoils(True)

    def test_reduced_motion_keeps_both_required_shots_and_warning_acknowledgement(self):
        self.g.audio.set_reduced_motion(True)
        self.conversation()
        self.assertTrue(self.g.camera.settled)
        fixture.read_social(self.g)
        self.assertTrue(self.g.combat.active)
        self.assertTrue(self.g.camera.settled)
        self.assertFalse(self.g.camera.scripted)
        self.assertEqual(self.g.music.desired_track, 'battle')

    def test_completed_legacy_mill_never_replays_the_arrival_cutscene(self):
        fixture.seed_completed_mill(self.g)
        self.g.world = self.c.upstream
        self.g.player.position.update(self.c.upstream.data['spawn'])
        self.g.opening_fade = self.g.transfer_cooldown = 0
        self.c.on_enter_scene(self.g.town, {})
        for _ in range(40):self.tick(.05)
        self.assertFalse(self.c.encounter_cutscene_active)
        self.assertFalse(self.g.camera.scripted)
        self.assertFalse(self.g.social.active)
        self.assertFalse(self.g.combat.active)
        self.assertEqual(self.g.music.desired_track, 'eldenmere')
        self.assertEqual(self.g.quests.status(MILL_QUEST), 'completed')


if __name__ == '__main__':unittest.main()
