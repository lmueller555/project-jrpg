"""Survivor silence and dialogue-driven Kindled Courage ownership."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
from types import SimpleNamespace as NS
import unittest
from audio_settings import AudioSettings
from game_music import GameMusic
from regent_emergency import RegentEmergency
from test_game_music import FakeMixer, CATALOG

class EmergencyMusicTests(unittest.TestCase):
    def setUp(self):
        self.game=NS(audio=AudioSettings(), combat=NS(active=False),
                     social=NS(script_identifier=None,page=None))
        self.mixer=FakeMixer()
        self.game.music=GameMusic(self.game,catalog=CATALOG,mixer=self.mixer)
        self.addCleanup(self.game.music.stop)
        self.owner=NS(game=self.game,actors={},stage='interruption')
        self.scene=RegentEmergency(self.owner)
        self.game.music.play('eldenmere',fade_ms=0)

    def test_fade_silence_two_survivor_lines_then_loop_without_restart(self):
        music=self.game.music
        self.scene.sync_music();music.update(.35)
        self.assertGreater(self.mixer.music.volume,0)
        self.assertLess(self.mixer.music.volume,.45)
        self.scene.sync_music();music.update(.35)
        self.assertIsNone(music.current_track)
        self.owner.stage='attack_report'
        self.game.social.script_identifier='regent_attack_report'
        for line in (0,1,2):
            self.game.social.page={'source_line':line}
            self.scene.sync_music();music.update(3)
            self.assertIsNone(music.current_track)
        self.game.social.page={'source_line':3}
        self.scene.sync_music();music.update(.5)
        self.assertEqual(music.current_track,'battle')
        loads=len(self.mixer.music.loads)
        # Cancellation and rereading do not rewind the started score.
        self.game.social.page={'source_line':0}
        for stage in ('attack_report','departure','rejoin_mira','sanctuary_travel','sanctuary_arrival_pending'):
            self.owner.stage=stage
            self.scene.sync_music();music.update(1)
        self.assertEqual(len(self.mixer.music.loads),loads)
        self.assertEqual(self.mixer.music.plays[-1],-1)

    def test_restore_report_restarts_silent_opening_later_checkpoints_restore_courage(self):
        self.owner.stage='attack_report'
        self.scene.sync_music(restoring=True)
        self.assertIsNone(self.game.music.current_track)
        for stage in ('departure','rejoin_mira','sanctuary_travel','sanctuary_arrival_pending'):
            self.owner.stage=stage
            self.scene.sync_music(restoring=True)
            self.assertEqual(self.game.music.current_track,'battle')
        self.owner.stage='done'
        self.game.music.play('eldenmere',fade_ms=0)
        self.scene.sync_music()
        self.assertEqual(self.game.music.desired_track,'eldenmere')
