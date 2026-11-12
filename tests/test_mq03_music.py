"""Survivor silence and dialogue-driven Kindled Courage ownership."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
from types import SimpleNamespace as NS
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
from audio_settings import AudioSettings
from game_music import GameMusic
from regent_emergency import RegentEmergency, legacy_cave_entered
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

    def test_completed_arrival_still_uses_emergency_music_until_first_cave_entry(self):
        self.game.sanctuary_arrival=NS(completed=True,cave_entered=False)
        self.owner.stage='sanctuary_arrival_pending'
        self.scene.sync_music();self.game.music.update(1)
        self.assertEqual(self.game.music.current_track,'battle')

    def test_first_cave_entry_permanently_releases_emergency_ownership(self):
        self.game.sanctuary_arrival=NS(completed=True,cave_entered=True)
        loads=len(self.mixer.music.loads)
        for stage in ('interruption','attack_report','departure','rejoin_mira','sanctuary_travel','sanctuary_arrival_pending'):
            self.owner.stage=stage
            self.scene.sync_music(restoring=True);self.game.music.update(1)
            self.assertEqual(self.game.music.current_track,'eldenmere')
        self.assertEqual(len(self.mixer.music.loads),loads)
        # Normal battle bookmarking remains intact after the story override ends.
        self.assertTrue(self.game.music.begin_battle(fade_ms=0))
        self.scene.sync_music();self.assertEqual(self.game.music.current_track,'battle')
        self.assertTrue(self.game.music.end_battle(fade_ms=0))
        self.scene.sync_music();self.assertEqual(self.game.music.current_track,'eldenmere')

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


class LegacyCaveMusicEvidenceTests(unittest.TestCase):
    def test_default_or_completed_old_quest_alone_does_not_invent_a_cave_visit(self):
        for record in ({}, {'regent_quest':{'version':3,'stage':'done'}},
                       {'player':{'scene':'eldenmere'}},
                       {'cave_lesson':{'version':1,'resonance_seen':False,'battle_cleared':False,'deferred':False}},
                       {'sanctuary_cave':{'version':1,'opened':[]}}):
            self.assertFalse(legacy_cave_entered(record))

    def test_legitimate_old_scene_lesson_discovery_and_boss_facts_release_override(self):
        cases=[{'player':{'scene':scene}} for scene in
               ('sanctuary_cave','sanctuary_cave_entrance','sanctuary_cave_hollow','sanctuary_cave_depths')]
        cases += [
            {'cave_lesson':{'version':1,'resonance_seen':True,'battle_cleared':False,'deferred':False}},
            {'sanctuary_cave':{'version':1,'opened':['cave_vein_cache']}},
            {'sanctuary_boss':{'version':1,'defeated':True,'intro_seen':True,'pending':None}},
            {'cave_random_encounters':{'version':1,'identity':5,'rng_state':11,'sequence':1,
              'threshold':500.,'remaining':500.,'was_safe':None,'pending':None}}]
        for record in cases:
            before=deepcopy(record)
            # No map or encounter configuration is consulted by this migration.
            with patch.object(Path,'read_text',side_effect=AssertionError('Unexpected asset read')):
                self.assertTrue(legacy_cave_entered(record),record)
            self.assertEqual(record,before)

    def test_malformed_or_unacknowledged_facts_are_not_used_as_evidence(self):
        cases=[None, [], {'player':{'scene':[]}},
               {'cave_lesson':{'resonance_seen':True}},
               {'cave_lesson':{'version':True,'resonance_seen':True,'battle_cleared':False,'deferred':False}},
               {'sanctuary_cave':{'version':1,'opened':['unknown_cache']}},
               {'sanctuary_boss':{'version':1,'defeated':True,'intro_seen':False,'pending':None}},
               {'cave_random_encounters':{'sequence':1}}]
        for record in cases:self.assertFalse(legacy_cave_entered(record),record)
