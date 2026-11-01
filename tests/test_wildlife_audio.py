"""Finite wildlife PCM and coexistence with regional work sounds."""
import math
import os
from types import SimpleNamespace as NS
from unittest import TestCase, mock

os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import pygame

from audio_settings import AudioSettings
from regional_audio import DURATIONS, RegionalAudio, Source, samples


class WildlifePCMTests(TestCase):
    def test_finite_original_pcm_is_quiet_deterministic_and_smoothly_bounded(self):
        fingerprints = set()
        for name in ('sheep','bird','wings'):
            for rate in (8000,22050,48000):
                with self.subTest(name=name,rate=rate):
                    pcm = samples(name,rate,1)
                    self.assertEqual(len(pcm),round(rate*DURATIONS[name]))
                    self.assertLessEqual(len(pcm)/rate,.55+1/rate)
                    self.assertEqual(pcm,samples(name,rate,1))
                    peak = max(abs(value) for value in pcm)
                    rms = math.sqrt(sum(value*value for value in pcm)/len(pcm))
                    self.assertGreater(peak,500)
                    self.assertLess(peak,6000)
                    self.assertGreater(rms,100)
                    self.assertLess(rms,2000)
                    self.assertEqual(pcm[0],0)
                    self.assertLessEqual(abs(pcm[-1]),1)
                    stereo = samples(name,rate,2)
                    self.assertEqual(stereo[::2],pcm)
                    self.assertEqual(stereo[1::2],pcm)
            fingerprints.add(pcm.tobytes())
        self.assertEqual(len(fingerprints),3)


class Channel:
    def __init__(self):
        self.sound = None;self.gain = 0;self.loops = None

    def get_sound(self):return self.sound
    def stop(self):self.sound = None
    def set_volume(self,value):self.gain = value
    def play(self,sound,loops=0):self.sound = sound;self.loops = loops


class WildlifeAllocationTests(TestCase):
    def setUp(self):
        self.g = NS(audio=AudioSettings(None),player=NS(position=pygame.Vector2()),
            overworld_travel=NS(active=True),on_title=False,opening_cinematic=NS(active=False),
            regent_arrival=NS(active=False,state='done'),combat=NS(active=False),pause=NS(is_open=False),
            inventory_ui=NS(is_open=False),world_map_viewer=NS(is_open=False),map_open=False,
            quest_ui=NS(journal_open=False),_music_focused=True,world=NS(region={'terrain':{}}))
        self.a = RegionalAudio(self.g);self.channels = []
        def channel():
            result = Channel();self.channels.append(result);return result
        patcher = mock.patch('regional_audio.pygame.mixer.find_channel',side_effect=channel)
        patcher.start();self.addCleanup(patcher.stop)
        patcher = mock.patch.object(self.a,'_sound',side_effect=lambda name:object())
        patcher.start();self.addCleanup(patcher.stop)

    def wildlife(self,key='gather',name='sheep',position=(0,0)):
        return Source(key,name,'wildlife',position,gain=.3,near=24,far=140,
                      priority=1,cooldown=4)

    def test_all_wildlife_share_one_finite_voice_below_work_priority(self):
        for key in ('water','foliage'):
            self.assertTrue(self.a.play(Source(key,'river',key,(0,0),ambient=True)))
        self.assertTrue(self.a.play(self.wildlife()))
        self.assertEqual(self.channels[-1].loops,0)
        self.assertFalse(self.a.play(self.wildlife('scatter','wings')))
        self.assertFalse(self.a.play(self.wildlife('landing','bird')))
        self.assertTrue(self.a.emit('sack','sack',(0,0),'farm'))
        self.assertEqual(len(self.a.voices),4)
        self.assertTrue(self.a.emit('cup','cup',(0,0),'ceramic',3))
        self.assertEqual(set(self.a.voices),{'water','foliage','sack','cup'})
        self.assertFalse(self.a.play(self.wildlife('another_gather')))

    def test_each_wildlife_sound_expires_without_loop_or_backlog(self):
        for name in ('sheep','bird','wings'):
            with self.subTest(name=name):
                self.a.reset()
                self.assertTrue(self.a.play(self.wildlife(name,name)))
                channel = self.channels[-1]
                self.assertEqual(channel.loops,0)
                self.a.update(DURATIONS[name])
                self.assertIsNone(channel.sound)
                self.assertFalse(self.a.voices)
                self.a.update(20)
                self.assertFalse(self.a.voices)

    def test_live_source_attenuates_and_distant_attempt_is_discarded(self):
        position = pygame.Vector2()
        self.assertTrue(self.a.play(self.wildlife(position=lambda:position)))
        channel = self.channels[-1]
        self.assertAlmostEqual(channel.gain,.3)
        position.update(82,0);self.a.update(0)
        self.assertAlmostEqual(channel.gain,.15)
        position.update(140,0);self.a.update(0)
        self.assertIsNone(channel.sound)
        self.assertFalse(self.a.play(self.wildlife('distant','bird',tuple(position))))
        self.g.player.position.update(position);self.a.update(5)
        self.assertFalse(self.a.voices)

    def test_mute_pause_title_and_reset_cannot_replay_a_consumed_cue(self):
        for owner,field in ((self.g.pause,'is_open'),(self.g,'map_open'),
                            (self.g.quest_ui,'journal_open'),(self.g,'on_title')):
            with self.subTest(field=field):
                self.a.reset();self.assertTrue(self.a.play(self.wildlife()))
                setattr(owner,field,True);self.a.update(.1)
                self.assertFalse(self.a.voices)
                self.assertFalse(self.a.play(self.wildlife('during_pause','bird')))
                setattr(owner,field,False);self.a.update(5)
                self.assertFalse(self.a.voices)
        self.assertTrue(self.a.play(self.wildlife()))
        self.g.audio.set_effects(0)
        self.assertFalse(self.a.voices)
        self.assertFalse(self.a.play(self.wildlife('muted','wings')))
        self.g.audio.set_effects(1);self.a.update(5)
        self.assertFalse(self.a.voices)
        self.assertTrue(self.a.play(self.wildlife()))
        self.a.reset()
        self.assertFalse(self.a.voices)
        self.assertFalse(self.a.cooldowns)
