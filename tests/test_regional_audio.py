"""Numerical mixing and controller lifecycle, independent of an audio device."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
from types import SimpleNamespace as NS
from unittest import TestCase, mock
import pygame
from regional_audio import RegionalAudio, Source, distance_gain, samples
from audio_settings import AudioSettings


class Channel:
    def __init__(self):self.sound=None;self.gain=0;self.stops=0
    def get_sound(self):return self.sound
    def stop(self):self.stops+=1;self.sound=None
    def set_volume(self,v):self.gain=v
    def play(self,sound,**kw):self.sound=sound


class RegionalAudioTests(TestCase):
    def setUp(self):
        self.g=NS(audio=AudioSettings(None),player=NS(position=pygame.Vector2()),
            overworld_travel=NS(active=True),on_title=False,opening_cinematic=NS(active=False),
            regent_arrival=NS(active=False,state='done'),combat=NS(active=False),pause=NS(is_open=False),
            inventory_ui=NS(is_open=False),world_map_viewer=NS(is_open=False),map_open=False,
            quest_ui=NS(journal_open=False),_music_focused=True,world=NS(region={'terrain':{}}))
        self.a=RegionalAudio(self.g);self.channels=[]
        def channel():
            c=Channel();self.channels.append(c);return c
        self.p=mock.patch('regional_audio.pygame.mixer.find_channel',side_effect=channel);self.p.start();self.addCleanup(self.p.stop)
        self.p2=mock.patch.object(self.a,'_sound',side_effect=lambda n:object());self.p2.start();self.addCleanup(self.p2.stop)
    def source(self,key='one',**kw):return Source(key,'sack','work',(0,0),**kw)
    def test_smooth_gain_exact_cutoff(self):
        self.assertEqual([distance_gain(d,20,100) for d in (0,20,60,100,101)],[1,1,.5,0,0])
        self.assertGreater(distance_gain(99.99,20,100),0)
    def test_source_moves_and_camera_is_irrelevant(self):
        p=pygame.Vector2();s=Source('moving','sack','work',lambda:p)
        self.a.play(s);c=self.channels[-1];self.g.camera=NS(position=(10000,10000));self.a.refresh_volume()
        self.assertEqual(c.gain,.5)
        p.x=106;self.a.refresh_volume();self.assertAlmostEqual(c.gain,.25)
        p.x=180;self.a.refresh_volume();self.assertIsNone(c.sound);self.assertFalse(self.a.voices)
    def test_hysteresis_never_escapes_cutoff(self):
        s=self.source(ambient=True)
        self.g.player.position.x=170;self.assertFalse(self.a.play(s))
        self.g.player.position.x=160;self.assertTrue(self.a.play(s))
        self.g.player.position.x=175;self.a.refresh_volume();self.assertTrue(self.a.voices)
        self.g.player.position.x=180;self.a.refresh_volume();self.assertFalse(self.a.voices)
    def test_two_per_class_one_per_family_and_priority(self):
        for i in range(8):self.a.play(Source(str(i),'sack',str(i),(0,0),ambient=i<4))
        self.assertEqual(len(self.a.voices),4)
        self.assertEqual(sum(v[0].ambient for v in self.a.voices.values()),2)
        self.assertFalse(self.a.play(Source('equal','sack','4',(0,0))))
        self.assertTrue(self.a.play(Source('urgent','cup','4',(0,0),priority=3)))
        self.assertNotIn('4',self.a.voices)
    def test_cooldown(self):
        s=self.source();self.a.play(s);self.a.stop();self.assertFalse(self.a.play(s))
        self.a.update(.7);self.assertTrue(self.a.play(s))
    def test_muted_and_distant_cues_are_not_queued(self):
        self.g.audio.set_effects(0);self.assertFalse(self.a.play(self.source()))
        self.g.audio.set_effects(1);self.a.update(1);self.assertFalse(self.a.voices)
        self.g.player.position.x=200;self.assertFalse(self.a.play(self.source()))
        self.g.player.position.x=0;self.a.update(1);self.assertFalse(self.a.voices)
    def test_effects_change_immediately_and_mute_releases(self):
        self.a.play(self.source());c=self.channels[-1]
        self.g.audio.set_effects(.2);self.assertEqual(c.gain,.1)
        self.g.audio.set_effects(0);self.assertIsNone(c.sound)
    def test_pauses_transfers_title_and_script_ownership(self):
        for owner,field in [(self.g.pause,'is_open'),(self.g,'map_open'),(self.g.quest_ui,'journal_open'),
            (self.g.inventory_ui,'is_open'),(self.g.world_map_viewer,'is_open'),(self.g,'on_title'),
            (self.g.regent_arrival,'active'),(self.g.opening_cinematic,'active'),(self.g.combat,'active')]:
            self.a.reset();self.a.play(self.source());setattr(owner,field,True);self.a.update(.1)
            self.assertFalse(self.a.voices);setattr(owner,field,False);self.a.update(.1);self.assertFalse(self.a.voices)
        self.a.reset();self.a.play(self.source());self.g.overworld_travel.active=False;self.a.update(.1);self.assertFalse(self.a.voices)
    def test_reused_channel_is_never_stopped_or_adjusted(self):
        self.a.play(self.source());c=self.channels[-1];other=object();c.sound=other;c.gain=.7
        self.a.refresh_volume();self.assertIs(c.sound,other);self.assertEqual(c.gain,.7);self.assertEqual(c.stops,0)
    def test_no_device_and_play_failure(self):
        self.p2.stop()
        with mock.patch('pygame.mixer.get_init',return_value=None):self.assertFalse(self.a.play(self.source()))
        with mock.patch('pygame.mixer.get_init',side_effect=pygame.error('no device')):self.assertFalse(self.a.play(self.source()))
        self.assertTrue(self.a.failed)
    def test_expired_oneshot_releases_even_when_clock_runs_offline(self):
        self.a.play(self.source());self.a.update(.5);self.assertFalse(self.a.voices)
    def test_nearest_river_and_real_patch_geometry_without_chunks(self):
        self.g.world.region={'terrain':{'rivers':[{'points':[(0,0),(0,10)],'width':2}],
            'fields':[{'crop':'grain','polygon':[(10,0),(20,0),(20,10),(10,10)]}]}}
        self.g.player.position.update(48,120)
        sources=list(self.a.ambient_sources());self.assertEqual(len(sources),2)
        self.assertEqual(sources[0].point(),(24,120));self.assertEqual(sources[1].point(),(240,120))
        self.a.update(.1);self.g.player.position.update(48,180);self.a.update(.1)
        self.assertEqual(self.a.voices['river'][0].point(),(24,180))
    def test_original_pcm_safe_and_distinct(self):
        from regional_audio import DURATIONS
        fingerprints=set()
        for name in DURATIONS:
            pcm=samples(name,8000,1);self.assertLess(max(abs(x) for x in pcm),20000)
            self.assertGreater(max(abs(x) for x in pcm),500);fingerprints.add(pcm.tobytes())
        self.assertEqual(len(fingerprints),len(DURATIONS))
