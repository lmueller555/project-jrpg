"""Cave exploration owns its cue; battles bookmark and resume it normally."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

import pygame

from main import Game
from quests import REGENT_QUEST
from sanctuary_cave import RESERVE_ENTRY_APPROACH, RESERVE_ID, SCENE_ID
from tools.capture_mq03_emergency import earlier_quest_fixture


ROOT = Path(__file__).resolve().parents[1]


class SanctuaryCaveMusicTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix='cave-music-')
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        self.path = self.directory/'journey.json'
        self.backend = MagicMock()
        self.backend.get_busy.return_value = True
        self.backend.get_pos.return_value = 0
        stream = patch('pygame.mixer.music', self.backend)
        stream.start()
        self.addCleanup(stream.stop)
        self.games = []

    def tearDown(self):
        for game in self.games:
            game.combat.reset()
            game.regional_audio.reset()
            game.opening_audio.reset()
            game.music.stop()
        pygame.quit()

    def game(self, *, title=False):
        game = Game(fullscreen=False, start_on_title=title, save_path=self.path,
                    settings_path=self.directory/'settings.json')
        game.audio.set_effects(0)
        self.games.append(game)
        return game

    def tick(self, game, seconds=0):
        game.update(seconds, (0, 0), False)

    def enter(self, *, emergency=True):
        game = self.game()
        earlier_quest_fixture(game)
        if emergency:
            self.assertTrue(game.accept_quest(REGENT_QUEST))
            for objective in ('meet_visitors', 'accompany_visit', 'welcome_party'):
                self.assertTrue(game.quests.complete_objective(REGENT_QUEST, objective))
            self.assertTrue(game.regent_quest.restore(
                {'version': 3, 'stage': 'sanctuary_arrival_pending'}))
            self.assertTrue(game._sync_story_party())
            game.regent_quest.emergency.sync_music(restoring=True)
        # This suite isolates music after the fully acknowledged arrival scene.
        arrival=getattr(game,'sanctuary_arrival',None)
        if arrival is not None:
            self.assertTrue(arrival.restore({'version':1,'beat':7,'completed':True,'cave_entered':False}))
        self.assertTrue(game.cave_lesson.restore(
            {'version': 1, 'resonance_seen': True, 'battle_cleared': True, 'deferred': False}))
        if 'aqua_edge' not in game.character_abilities.known_abilities():
            self.assertTrue(game.character_abilities.learn_ability('caelan', 'aqua_edge'))
        reserve = game._scene_by_id(RESERVE_ID)
        self.assertTrue(game.overworld_travel._commit(
            reserve, RESERVE_ENTRY_APPROACH, 'back', {'id': 'music_test_arrival'}))
        game.opening_fade = game.transfer_cooldown = 0
        self.assertTrue(game.sanctuary_cave.interact())
        self.assertEqual(game.world.data['id'], SCENE_ID)
        game.opening_fade = game.transfer_cooldown = 0
        self.tick(game, 1)
        return game

    def start_encounter(self, game):
        game.cave_random_encounters.reset(41)
        ticket = game.cave_random_encounters.advance(1000, (456, 1280))
        self.assertIsNotNone(ticket)
        game.player.position.update(ticket['position'])
        self.backend.get_pos.return_value = 13750
        self.assertTrue(game.combat.start_cave(ticket))
        self.assertEqual(game.music.desired_track, 'battle')
        for _ in range(60):
            if game.combat.entry_phase == 'loading':
                break
            self.tick(game, .05)
        self.assertEqual(game.combat.entry_phase, 'loading')
        game.draw()
        self.tick(game, .01)
        self.assertIsNotNone(game.combat.model, game.combat.entry_phase)
        for _ in range(60):
            if not game.combat.transitioning:
                break
            self.tick(game, .05)
        return game.combat

    def test_entering_during_mq03_selects_the_cave_loop_without_changing_story(self):
        game = self.enter()
        self.assertEqual(game.regent_quest.stage, 'sanctuary_arrival_pending')
        self.assertEqual(game.quests.status(REGENT_QUEST), 'active')
        self.assertEqual(game.music.current_track, 'sanctuary_cave')
        self.assertEqual(game.music.desired_track, 'sanctuary_cave')
        self.assertEqual(Path(self.backend.load.call_args.args[0]).name,
                         'elden_vale_sanctuary_cave.ogg')
        self.backend.play.assert_called_with(-1)
        self.assertFalse(game.combat.active)

    def test_cave_rooms_share_one_uninterrupted_stream_including_elemental_branches(self):
        game = self.enter()
        starts = self.backend.play.call_count
        world = game.world
        for point in world.data['cave']['navigation_points'].values():
            game.player.position.update(point)
            self.tick(game)
            self.assertIs(game.world, world)
            self.assertEqual(game.music.desired_track, 'sanctuary_cave')
        self.assertEqual(self.backend.play.call_count, starts)

    def test_first_cave_exit_restores_normal_area_music_even_during_mq03(self):
        for emergency in (False, True):
            with self.subTest(emergency=emergency):
                game = self.enter(emergency=emergency)
                self.assertEqual(game.music.desired_track, 'sanctuary_cave')
                link = next(link for link in game.world.data['cave']['links']
                            if link['destination'] == RESERVE_ID)
                game.player.position.update(link.get('approach', link['position']))
                self.assertTrue(game.sanctuary_cave.interact())
                self.assertEqual(game.world.data['id'], RESERVE_ID)
                self.assertEqual(game.music.desired_track, 'eldenmere')
                self.tick(game, 1)
                self.assertEqual(game.music.current_track, 'eldenmere')

    def test_continue_selects_cave_music_before_any_first_update(self):
        game = self.enter()
        self.assertTrue(game.save_progress())
        other = self.game(title=True)
        self.assertTrue(other.has_saved_journey, other.save_error)
        self.assertTrue(other.begin_journey(True), other.save_error)
        self.assertEqual(other.music.current_track, 'sanctuary_cave')
        self.assertTrue(other.sanctuary_arrival.cave_entered)
        self.assertEqual(other.music.desired_track, 'sanctuary_cave')
        self.assertFalse(other.combat.active)

    def test_focus_mute_and_volume_controls_do_not_reload_the_cave_stream(self):
        game = self.enter()
        starts = self.backend.play.call_count
        game.handle_events([pygame.event.Event(pygame.WINDOWFOCUSLOST)])
        self.tick(game, 1)
        self.backend.pause.assert_called()
        game.handle_events([pygame.event.Event(pygame.WINDOWFOCUSGAINED)])
        self.tick(game)
        self.backend.unpause.assert_called()
        game.audio.set_music(0)
        self.tick(game, 1)
        game.audio.set_music(.5)
        self.tick(game, 1)
        self.assertAlmostEqual(self.backend.set_volume.call_args.args[0], .45*.5)
        self.assertEqual(self.backend.play.call_count, starts)

    def test_victory_spoils_and_reloaded_spoils_use_the_cave_cue(self):
        game = self.enter()
        owner = self.start_encounter(game)
        for enemy in owner.model.enemies:
            enemy.hp = 0
        owner.model._result('victory')
        self.assertTrue(owner._begin_victory())
        self.assertEqual(game.music.desired_track, 'sanctuary_cave')
        self.assertAlmostEqual(self.backend.play.call_args.kwargs['start'], 13.75)
        for _ in range(100):
            if owner.post_phase == 'spoils' and owner.spoils.awarded:
                break
            self.tick(game, .05)
        self.assertEqual(owner.post_phase, 'spoils')
        self.assertTrue(owner.spoils.awarded)
        starts = self.backend.play.call_count
        for _ in range(3):
            self.tick(game, .1)
        self.assertEqual(self.backend.play.call_count, starts)
        other = self.game(title=True)
        self.assertTrue(other.has_saved_journey, other.save_error)
        self.assertTrue(other.begin_journey(True), other.save_error)
        self.assertEqual(other.combat.post_phase, 'spoils')
        self.assertEqual(other.music.current_track, 'sanctuary_cave')
        self.assertEqual(other.music.desired_track, 'sanctuary_cave')

    def test_flee_and_defeat_resume_the_bookmarked_cave_position(self):
        for outcome in ('fled', 'defeat'):
            with self.subTest(outcome=outcome):
                game = self.enter()
                owner = self.start_encounter(game)
                owner.model._result(outcome)
                owner.scene.dismissed = True
                self.assertTrue(owner._settle())
                self.assertFalse(owner.active)
                self.assertEqual(game.music.desired_track, 'sanctuary_cave')
                self.assertAlmostEqual(self.backend.play.call_args.kwargs['start'], 13.75)
                starts = self.backend.play.call_count
                self.tick(game, .1)
                self.assertEqual(self.backend.play.call_count, starts)
                game.music.stop()

    def test_pending_encounter_continue_bookmarks_cave_not_the_title_theme(self):
        game = self.enter()
        self.start_encounter(game)
        other = self.game(title=True)
        self.assertTrue(other.has_saved_journey, other.save_error)
        self.assertTrue(other.begin_journey(True), other.save_error)
        self.assertTrue(other.combat.active)
        self.assertEqual(other.music.desired_track, 'battle')
        other.music.update(1)
        self.assertTrue(other.music.end_battle())
        self.assertEqual(other.music.desired_track, 'sanctuary_cave')

    def test_runtime_cue_and_provenance_match_the_replacement_upload(self):
        catalog = json.loads((ROOT/'assets/music/tracks.json').read_text())
        self.assertEqual(catalog['tracks']['sanctuary_cave'],
                         {'file': 'runtime/elden_vale_sanctuary_cave.ogg', 'gain': .45})
        audit = json.loads((ROOT/'assets/music/runtime/provenance.json').read_text())
        record = next(item for item in audit['tracks'] if item['identifier'] == 'sanctuary_cave')
        original = (ROOT/'assets/music'/record['source']).read_bytes()
        self.assertEqual(record['source_sha256'], hashlib.sha256(original).hexdigest())
        self.assertEqual(record['source_git_blob_sha'],
                         '220628c072a322cf4f0ec205708db3d3287c770e')
        self.assertEqual(record['boundaries']['removed_tail_frames'], 0)
        self.assertEqual(record['boundaries']['boundary_declick_ms'], 0)
        self.assertEqual(record['verification']['sha256'], hashlib.sha256(
            (ROOT/'assets/music'/record['runtime']).read_bytes()).hexdigest())
        self.assertTrue(record['verification']['pygame_stream_with_repeat'])


if __name__ == '__main__':
    unittest.main()
