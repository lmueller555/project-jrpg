"""Soundtrack ownership, transitions and preferences without real-time waits."""
import os
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

from pathlib import Path
from types import SimpleNamespace
import hashlib
import json
import unittest

import pygame

from audio_settings import AudioSettings
from game_music import GameMusic


CATALOG = {'version': 1, 'tracks': {
    'eldenmere': {'file': 'runtime/eldenmere_theme.ogg', 'gain': .45},
    'battle': {'file': 'runtime/kindled_courage.ogg', 'gain': .6},
    'victory': {'file': 'runtime/triumphal_fanfare.ogg', 'gain': .45, 'loop': False},
    'opening_leitmotif': {'file': 'runtime/dare_to_dream_leitmotif.ogg',
                         'gain': .45, 'loop': True},
    'royalty': {'file': 'runtime/royalty_of_the_realm.ogg', 'gain': .45, 'loop': True},
}}


class FakeMusic:
    def __init__(self):
        self.loads = []
        self.plays = []
        self.play_volumes = []
        self.stops = 0
        self.pauses = 0
        self.unpauses = 0
        self.busy = False
        self.paused = False
        self.volume = 1.0
        self.failure = None

    def load(self, path):
        if self.failure:
            raise self.failure
        self.loads.append(path)
        self.busy = False

    def play(self, loops):
        self.plays.append(loops)
        self.play_volumes.append(self.volume)
        self.busy, self.paused = True, False

    def stop(self):
        self.stops += 1
        self.busy, self.paused = False, False

    def pause(self):
        self.pauses += 1
        self.paused = True

    def unpause(self):
        self.unpauses += 1
        self.paused = False

    def set_volume(self, value):
        self.volume = value

    def get_busy(self):
        return self.busy and not self.paused


class FakeMixer:
    def __init__(self, ready=True, failure=None):
        self.music = FakeMusic()
        self.ready = ready
        self.failure = failure
        self.initializations = 0

    def get_init(self):
        return (44100, -16, 2) if self.ready else None

    def init(self):
        self.initializations += 1
        if self.failure:
            raise self.failure
        self.ready = True


class SoundtrackTests(unittest.TestCase):
    def make_music(self, mixer=None):
        game = SimpleNamespace(audio=AudioSettings())
        mixer = FakeMixer() if mixer is None else mixer
        music = GameMusic(game, catalog=CATALOG, mixer=mixer)
        self.addCleanup(music.stop)
        return game, music, mixer.music

    def test_same_track_across_title_world_and_millrace_is_not_restarted(self):
        game, music, stream = self.make_music()
        self.assertIsNone(music.current_track)
        self.assertEqual(stream.plays, [])
        music.play('eldenmere', fade_ms=900)
        music.update(.9)
        for _ in range(6):
            music.play('eldenmere')
            music.update(.25)
        self.assertEqual(len(stream.loads), 1)
        self.assertEqual(stream.plays, [-1])
        self.assertTrue(music.playing)
        self.assertAlmostEqual(stream.volume, .45)

    def test_battle_change_fades_old_track_then_starts_and_fades_new_one(self):
        game, music, stream = self.make_music()
        music.play('eldenmere', fade_ms=0)
        music.play('battle', fade_ms=400)
        self.assertEqual(music.desired_track, 'battle')
        self.assertEqual(music.current_track, 'eldenmere')
        music.update(.2)
        self.assertAlmostEqual(stream.volume, .225)
        self.assertEqual(len(stream.loads), 1)
        music.play('battle', fade_ms=400)
        music.update(.2)
        self.assertEqual(music.current_track, 'battle')
        self.assertEqual(len(stream.loads), 2)
        self.assertAlmostEqual(stream.volume, 0)
        music.update(.2)
        self.assertAlmostEqual(stream.volume, .3)
        music.update(.2)
        self.assertAlmostEqual(stream.volume, .6)

    def test_aborted_encounter_cancels_pending_battle_cue_without_rewind(self):
        game, music, stream = self.make_music()
        music.play('eldenmere', fade_ms=0)
        music.play('battle', fade_ms=400)
        music.update(.1)
        music.play('eldenmere', fade_ms=200)
        music.update(1)
        self.assertEqual((music.current_track, music.desired_track), ('eldenmere', 'eldenmere'))
        self.assertEqual(len(stream.loads), 1)
        self.assertAlmostEqual(stream.volume, .45)

    def test_muting_pauses_and_unmuting_resumes_without_reloading(self):
        game, music, stream = self.make_music()
        music.play('eldenmere', fade_ms=0)
        game.audio.set_music(.7)
        self.assertAlmostEqual(stream.volume, .315)
        game.audio.toggle_music()
        self.assertFalse(music.playing)
        self.assertEqual(stream.pauses, 1)
        music.update(5)
        game.audio.toggle_music()
        self.assertTrue(music.playing)
        self.assertEqual(stream.unpauses, 1)
        self.assertEqual(stream.plays, [-1])
        self.assertAlmostEqual(stream.volume, .315)

    def test_muted_start_does_not_initialize_audio_and_keeps_latest_request(self):
        mixer = FakeMixer(ready=False)
        game, music, stream = self.make_music(mixer)
        game.audio.set_music(0)
        music.play('eldenmere')
        music.play('battle')
        music.update(10)
        self.assertEqual(mixer.initializations, 0)
        self.assertEqual(stream.plays, [])
        game.audio.set_music(.5)
        music.update(1)
        self.assertEqual(music.current_track, 'battle')
        self.assertEqual(len(stream.loads), 1)
        self.assertAlmostEqual(stream.volume, .3)

    def test_preference_volume_keeps_current_track_gain_and_duck(self):
        game, music, stream = self.make_music()
        music.play('battle', fade_ms=0)
        music.set_ducked(True)
        music.update(.18)
        game.audio.set_music(.5)
        self.assertAlmostEqual(stream.volume, .6 * .6 * .5)
        game.audio.set_effects(0)
        self.assertAlmostEqual(stream.volume, .6 * .6 * .5)
        music.set_ducked(False)
        music.update(.18)
        self.assertAlmostEqual(stream.volume, .3)

    def test_focus_pause_freezes_fades_and_resumes_without_reload(self):
        game, music, stream = self.make_music()
        music.play('eldenmere', fade_ms=0)
        music.play('battle', fade_ms=400)
        music.update(.1)
        before = stream.volume
        music.set_paused(True)
        music.update(5)
        self.assertEqual(music.current_track, 'eldenmere')
        self.assertEqual(stream.volume, before)
        self.assertEqual(stream.pauses, 1)
        music.set_paused(False)
        music.update(.3)
        self.assertEqual(music.current_track, 'battle')
        self.assertEqual(stream.unpauses, 1)

    def test_stop_during_transition_cannot_start_queued_music_later(self):
        game, music, stream = self.make_music()
        music.play('eldenmere', fade_ms=0)
        music.play('battle')
        music.stop()
        music.update(5)
        self.assertIsNone(music.current_track)
        self.assertIsNone(music.desired_track)
        self.assertEqual(len(stream.loads), 1)

    def test_track_requested_while_unfocused_starts_silent_and_paused(self):
        game, music, stream = self.make_music()
        music.set_paused(True)
        music.play('battle', fade_ms=0)
        self.assertEqual(stream.play_volumes, [0])
        self.assertTrue(stream.paused)
        self.assertFalse(music.playing)
        music.set_paused(False)
        self.assertTrue(music.playing)
        self.assertAlmostEqual(stream.volume, .6)
        self.assertEqual(stream.plays, [-1])

    def test_muting_mid_transition_starts_latest_track_when_unmuted(self):
        game, music, stream = self.make_music()
        music.play('eldenmere', fade_ms=0)
        music.play('battle')
        music.update(.1)
        game.audio.set_music(0)
        self.assertIsNone(music.current_track)
        music.play('eldenmere')
        game.audio.set_music(.4)
        music.update(1)
        self.assertEqual(music.current_track, 'eldenmere')
        self.assertEqual(len(stream.loads), 2)
        self.assertAlmostEqual(stream.volume, .18)

    def test_missing_device_and_unreadable_track_do_not_break_game(self):
        mixer = FakeMixer(ready=False, failure=pygame.error('no audio output'))
        game, music, stream = self.make_music(mixer)
        music.play('eldenmere')
        for _ in range(3):
            music.update(1)
        self.assertFalse(music.playing)
        self.assertEqual(mixer.initializations, 1)
        self.assertIn('no audio output', music.error)
        other = FakeMixer()
        other.music.failure = pygame.error('unreadable asset')
        game2, music2, stream2 = self.make_music(other)
        music2.play('battle')
        music2.update(2)
        self.assertFalse(music2.playing)
        self.assertIn('unreadable asset', music2.error)

    def test_unknown_track_and_invalid_catalog_cannot_replace_active_music(self):
        game, music, stream = self.make_music()
        music.play('eldenmere', fade_ms=0)
        self.assertFalse(music.play('unknown'))
        self.assertEqual(music.desired_track, 'eldenmere')
        self.assertFalse(music.play('battle', fade_ms=float('nan')))
        bad = GameMusic(SimpleNamespace(audio=AudioSettings()),
                        catalog={'version': 1, 'tracks': {'bad': {'file': '../escape.ogg'}}},
                        mixer=FakeMixer())
        self.assertFalse(bad.play('bad'))
        self.assertIn('escapes', bad.error)

    def test_stale_game_cannot_stop_a_new_games_shared_stream(self):
        mixer = FakeMixer()
        game, first, stream = self.make_music(mixer)
        first.play('eldenmere', fade_ms=0)
        game2, second, _ = self.make_music(mixer)
        second.play('battle', fade_ms=0)
        stopped = stream.stops
        first.stop()
        self.assertEqual(stream.stops, stopped)
        self.assertEqual(second.current_track, 'battle')
        self.assertTrue(second.playing)

    def test_victory_interrupts_battle_once_then_stays_silent_after_eof(self):
        game, music, stream = self.make_music()
        music.play('battle', fade_ms=0)
        music.play('victory', fade_ms=0)
        self.assertEqual(stream.plays, [-1, 0])
        self.assertEqual(music.current_track, 'victory')
        self.assertTrue(music.playing)
        stream.busy = False  # SDL_mixer reports the natural one-shot ending.
        music.update(.1)
        self.assertTrue(music.completed)
        self.assertFalse(music.playing)
        self.assertEqual((music.current_track, music.desired_track), ('victory', 'victory'))
        loads, pauses, unpauses = len(stream.loads), stream.pauses, stream.unpauses
        for _ in range(3):
            music.play('victory', fade_ms=0)
            game.audio.set_music(.5)
            game.audio.toggle_music()
            game.audio.toggle_music()
            music.set_paused(True)
            music.set_paused(False)
            music.set_ducked(True)
            music.update(10)
        self.assertEqual(stream.plays, [-1, 0])
        self.assertEqual(len(stream.loads), loads)
        self.assertEqual((stream.pauses, stream.unpauses), (pauses, unpauses))
        self.assertEqual(music.desired_track, 'victory')

    def test_pausing_a_fanfare_is_not_mistaken_for_natural_completion(self):
        game, music, stream = self.make_music()
        music.play('victory', fade_ms=0)
        music.set_paused(True)
        self.assertFalse(stream.get_busy())
        music.update(20)
        self.assertFalse(music.completed)
        music.set_paused(False)
        self.assertTrue(music.playing)
        self.assertEqual(stream.plays, [0])
        self.assertEqual(stream.unpauses, 1)
        stream.busy = False
        self.assertTrue(music.completed)

    def test_muting_an_unfinished_fanfare_retains_its_playback_position(self):
        game, music, stream = self.make_music()
        music.play('victory', fade_ms=0)
        game.audio.set_music(0)
        music.update(10)
        self.assertFalse(music.completed)
        self.assertFalse(music.playing)
        game.audio.set_music(.8)
        self.assertTrue(music.playing)
        self.assertEqual(stream.plays, [0])
        self.assertAlmostEqual(stream.volume, .36)

    def test_leaving_finished_fanfare_starts_world_music_without_a_silent_out_fade(self):
        game, music, stream = self.make_music()
        music.play('victory', fade_ms=0)
        stream.busy = False
        self.assertTrue(music.completed)
        music.play('eldenmere', fade_ms=400)
        self.assertEqual(music.current_track, 'eldenmere')
        self.assertFalse(music.completed)
        self.assertEqual(stream.plays, [0, -1])
        music.update(.4)
        self.assertAlmostEqual(stream.volume, .45)

    def test_another_battle_can_play_a_new_fanfare_after_leaving_spoils(self):
        game, music, stream = self.make_music()
        music.play('victory', fade_ms=0)
        stream.busy = False
        music.update(.1)
        music.play('eldenmere', fade_ms=0)
        music.play('battle', fade_ms=0)
        music.play('victory', fade_ms=0)
        self.assertEqual(stream.plays, [0, -1, -1, 0])
        self.assertFalse(music.completed)
        self.assertTrue(music.playing)

    def test_repeat_metadata_requires_a_real_boolean(self):
        bad = GameMusic(SimpleNamespace(audio=AudioSettings()),
                        catalog={'version': 1, 'tracks': {'bad': {'file': 'bad.ogg', 'loop': 0}}},
                        mixer=FakeMixer())
        self.assertFalse(bad.play('bad'))
        self.assertEqual(bad.tracks, {})

    def test_opening_leitmotif_repeats_and_pause_resumes_without_restarting(self):
        game, music, stream = self.make_music()
        music.play('opening_leitmotif', fade_ms=0)
        self.assertEqual(stream.plays, [-1])
        self.assertEqual(Path(stream.loads[0]).name, 'dare_to_dream_leitmotif.ogg')
        music.update(210)  # Longer than the complete authored 199-second cue.
        music.set_paused(True)
        music.update(60)
        self.assertTrue(stream.paused)
        self.assertFalse(music.completed)
        music.set_paused(False)
        music.play('opening_leitmotif')
        music.update(210)
        self.assertEqual(len(stream.loads), 1)
        self.assertEqual(stream.plays, [-1])
        self.assertEqual((stream.pauses, stream.unpauses), (1, 1))
        self.assertTrue(music.playing)
        self.assertEqual(music.desired_track, 'opening_leitmotif')

    def test_shipped_opening_track_is_the_user_leitmotif_and_matches_provenance(self):
        root = Path(__file__).resolve().parents[1] / 'assets/music'
        catalog = json.loads((root/'tracks.json').read_text())
        track = catalog['tracks']['opening_leitmotif']
        self.assertEqual(track['file'], 'runtime/dare_to_dream_leitmotif.ogg')
        self.assertIs(track['loop'], True)
        audit = json.loads((root/'runtime/provenance.json').read_text())
        record = next(item for item in audit['tracks']
                      if item['identifier'] == 'opening_leitmotif')
        self.assertEqual(record['source'], 'Dare to Dream Leitmotif.m4a')
        self.assertEqual(record['source_git_blob_sha'],
                         'c057902f21e2d84ac786f5f4ee37ac98f3c073e2')
        self.assertEqual(record['source_decoded_frames'],
                         record['verification']['decoded_frames'])
        self.assertEqual(record['boundaries']['removed_tail_frames'], 0)
        self.assertIs(record['verification']['pygame_stream_with_repeat'], True)
        self.assertEqual(hashlib.sha256((root/track['file']).read_bytes()).hexdigest(),
                         record['verification']['sha256'])


if __name__ == '__main__':
    unittest.main()
