"""Warnings register before movement and retain their owned mixer leases."""
import hashlib
import json
import math
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
import wave

os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')

from prologue_alert_audio import (ALARM_START,ASSETS,BRIDGE_ARRIVAL,MACHINERY_START,
                                  PrologueAlertAudio,RUSH_START,SEQUENCE_END,
                                  SIREN_PERIOD,alert_mix_at,mix_alert_audio)


class Sound:
    def __init__(self,path):self.path = Path(path)
    def get_length(self):return 2. if self.path.name.endswith('siren.wav') else 1.


class Channel:
    def __init__(self):
        self.sound = None;self.paused = False;self.stops = 0
        self.volume = (0.,0.);self.plays = []
    def get_sound(self):return self.sound
    def set_volume(self,left,right):self.volume = left,right
    def play(self,sound,loops=0,fade_ms=0):
        self.sound = sound;self.plays.append((sound,loops,fade_ms))
    def pause(self):self.paused = True
    def unpause(self):self.paused = False
    def stop(self):self.stops += 1;self.sound = None


class Mixer:
    def __init__(self):self.channels = [Channel() for _ in range(8)];self.ready = True
    def get_init(self):return (48000,-16,2) if self.ready else None
    def Sound(self,path):return Sound(path)
    def find_channel(self):return next((channel for channel in self.channels if channel.sound is None),None)


class AlertAudioTests(unittest.TestCase):
    def setUp(self):
        self.game = SimpleNamespace(audio=SimpleNamespace(effects_volume=.5))
        self.mixer = Mixer();self.audio = PrologueAlertAudio(self.game,mixer=self.mixer)

    def advance(self,before,until,fps=60):
        while before < until-1e-8:
            now = min(until,before+1/fps)
            self.audio.update(before,now);before = now
        if before < until:self.audio.update(before,until)

    def test_four_seconds_of_alarm_precede_rush_and_continue_across_shots(self):
        self.assertEqual(RUSH_START-ALARM_START,4.)
        self.assertEqual((RUSH_START-ALARM_START)/SIREN_PERIOD,2.)
        for fps in (30,60):
            with self.subTest(fps=fps):
                self.audio.stop();self.setUp()
                self.audio.start();self.advance(0,29.99,fps)
                self.assertEqual([event['id'] for event in self.audio.events],['machinery_bed.wav'])
                machinery = self.audio.voices['machinery_bed.wav']
                self.advance(29.99,30.,fps)
                near = self.audio.voices['industrial_siren.wav']
                far = self.audio.voices['distant_siren.wav']
                self.assertGreater(max(near.channel.volume),0.)
                self.advance(30.,34.,fps)
                self.assertIs(self.audio.voices['industrial_siren.wav'],near)
                self.assertEqual(len(near.channel.plays),1)
                self.assertEqual(near.channel.stops,0)
                self.assertEqual(self.audio.events[-1]['id'],'bridge_rush.wav')
                self.advance(34.,35.,fps)
                self.assertIs(self.audio.voices['machinery_bed.wav'],machinery)
                self.assertIs(self.audio.voices['industrial_siren.wav'],near)
                self.assertIs(self.audio.voices['distant_siren.wav'],far)
                self.assertEqual(near.channel.volume,(0.,0.))
                self.assertGreater(max(far.channel.volume),0.)
                self.assertNotIn('bridge_rush.wav',self.audio.voices)
                self.advance(35.,39.,fps)
                self.assertFalse(self.audio.voices)

    def test_standalone_clip_seeds_global_alarm_phase_and_current_transient(self):
        self.audio.start(25.)
        self.assertEqual(set(self.audio.voices),{'machinery_bed.wav'})
        self.audio.start(30.)
        self.assertEqual({event['id']:event['offset'] for event in self.audio.events},
                         {'machinery_bed.wav':1.,'industrial_siren.wav':0.,'distant_siren.wav':0.})
        self.audio.start(34.5)
        offsets = {event['id']:event['offset'] for event in self.audio.events}
        self.assertEqual(offsets,{'machinery_bed.wav':1.5,'industrial_siren.wav':.5,
                                 'distant_siren.wav':.5,'bridge_rush.wav':.5})
        self.audio.start(35.)
        self.assertNotIn('bridge_rush.wav',self.audio.voices)
        self.assertIn('ice_settle.wav',self.audio.voices)
        self.assertEqual(self.audio.events[1]['offset'],1.)

    def test_pause_focus_resume_do_not_advance_rearm_or_restart_siren(self):
        self.audio.start(31.25)
        voices = list(self.audio.voices.values());events = list(self.audio.events)
        self.audio.update(31.25,31.25,playing=False)
        self.assertTrue(all(voice.channel.paused for voice in voices))
        self.assertEqual(self.audio._clock,31.25)
        self.game.audio.effects_volume = .2;self.audio.refresh_volume()
        self.assertTrue(all(voice.channel.paused for voice in voices))
        self.audio.resume();self.audio.update(31.25,31.26)
        self.assertFalse(any(voice.channel.paused for voice in voices))
        self.assertEqual(self.audio.events,events)
        self.assertTrue(all(len(voice.channel.plays)==1 for voice in voices))

    def test_mute_and_unmute_rephase_alarm_without_replaying_rush(self):
        self.audio.start(33.8)
        self.game.audio.effects_volume = 0.;self.audio.refresh_volume()
        self.assertFalse(self.audio.voices)
        self.advance(33.8,35.2)
        self.game.audio.effects_volume = .8;self.audio.refresh_volume()
        self.assertEqual(set(self.audio.voices),{'machinery_bed.wav','industrial_siren.wav','distant_siren.wav'})
        self.assertFalse(any(event['id']=='bridge_rush.wav' for event in self.audio.events))
        self.assertAlmostEqual(self.audio.events[-1]['offset'],1.2)

    def test_busy_or_reassigned_channels_are_never_stolen_or_modified(self):
        self.audio.start(30.)
        voice = self.audio.voices['industrial_siren.wav']
        foreign = object();voice.channel.sound = foreign;volume = voice.channel.volume
        self.audio.pause();self.audio.refresh_volume();self.audio.stop()
        self.assertIs(voice.channel.sound,foreign)
        self.assertEqual(voice.channel.volume,volume)
        self.assertFalse(voice.channel.paused)
        self.assertEqual(voice.channel.stops,0)
        self.audio.reset()
        for channel in self.mixer.channels:channel.sound = object()
        originals = [channel.sound for channel in self.mixer.channels]
        self.audio.start(34.);self.advance(34.,34.2)
        self.assertFalse(self.audio.events)
        self.assertEqual([channel.sound for channel in self.mixer.channels],originals)

    def test_seek_does_not_emit_expired_cues_or_keep_old_voices(self):
        self.audio.start(30.)
        old = self.audio.voices['industrial_siren.wav']
        self.audio.update(30.,36.)
        self.assertEqual(old.channel.stops,1)
        self.assertEqual({event['id'] for event in self.audio.events},
                         {'machinery_bed.wav','industrial_siren.wav','distant_siren.wav'})
        self.audio.update(36.,29.)
        self.assertEqual(set(self.audio.voices),{'machinery_bed.wav'})
        self.assertEqual([event['id'] for event in self.audio.events],['machinery_bed.wav'])
        self.audio.stop();self.audio.resume();self.audio.refresh_volume()
        self.assertFalse(self.audio.voices)

    def test_invalid_time_or_missing_effects_setting_fails_silent(self):
        for invalid in (-1,float('inf'),float('nan'),'bad'):
            self.audio.start(30.);self.audio.update(30.,invalid)
            self.assertFalse(self.audio.voices)
        self.mixer.ready = False;self.audio.start(30.)
        self.assertFalse(self.audio.voices)
        quiet = PrologueAlertAudio(SimpleNamespace(),mixer=Mixer())
        quiet.start(30.);self.assertFalse(quiet.voices)

    def test_assets_reproduce_are_unclipped_and_warning_loops_share_timing(self):
        import numpy as np
        manifest = json.loads((ASSETS/'manifest.json').read_text())
        self.assertEqual(manifest['timeline']['alarm_lead_seconds'],4)
        for name,spec in manifest['sounds'].items():
            raw = (ASSETS/name).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(),spec['sha256'])
            with wave.open(str(ASSETS/name),'rb') as reader:
                self.assertEqual((reader.getframerate(),reader.getnchannels(),reader.getsampwidth()),(48000,2,2))
                samples = np.frombuffer(reader.readframes(reader.getnframes()),dtype='<i2').reshape(-1,2).astype(int)
                peak = np.max(np.abs(samples))
                self.assertGreater(peak,100);self.assertLess(peak,32767)
                self.assertEqual(spec['clipped_samples'],0)
                if spec['loop']:
                    self.assertEqual(spec['duration'],SIREN_PERIOD)
                    self.assertLess(np.max(np.abs(samples[-1]-samples[0])),
                                    np.max(np.abs(np.diff(samples,axis=0))))
        from tools.build_prologue_alert_audio import products
        for path,raw in products().items():self.assertEqual(path.read_bytes(),raw)

    def test_offline_mix_uses_same_phase_gains_and_complete_film_offsets(self):
        import numpy as np
        self.assertEqual(alert_mix_at(24.999),{})
        self.assertEqual(set(alert_mix_at(29.999)),{'machinery_bed.wav'})
        self.assertEqual(alert_mix_at(SEQUENCE_END),{})
        self.assertEqual(alert_mix_at(34.)['industrial_siren.wav'][0],.34)
        self.assertEqual(alert_mix_at(35.)['industrial_siren.wav'][0],0.)
        self.assertAlmostEqual(alert_mix_at(35.)['distant_siren.wav'][0],.115)
        silence = mix_alert_audio(20.,5.)
        self.assertEqual(np.max(np.abs(silence)),0.)
        full = mix_alert_audio(29.,10.)
        clip = mix_alert_audio(34.5,1.25)
        np.testing.assert_array_equal(clip,full[round(5.5*48000):round(6.75*48000)])
        np.testing.assert_allclose(mix_alert_audio(30.,.1),mix_alert_audio(32.,.1),atol=1e-7)
        self.assertGreater(float(np.sqrt(np.mean(full[48000:5*48000]**2))),.03)
        self.assertLess(float(np.max(np.abs(full))),1.)

    def test_real_mixer_rotates_pcm_loop_at_standalone_phase(self):
        import pygame
        pygame.mixer.init(frequency=48000,size=-16,channels=2)
        try:
            audio = PrologueAlertAudio(self.game)
            original = audio._sound('industrial_siren.wav')
            shifted = audio._sound('industrial_siren.wav',.5,loop=True)
            raw = original.get_raw();cut = round(.5*48000)*4
            self.assertEqual(shifted.get_raw(),raw[cut:]+raw[:cut])
            audio.start(35.)
            self.assertEqual(set(audio.voices),{'machinery_bed.wav','industrial_siren.wav',
                                               'distant_siren.wav','ice_settle.wav'})
            audio.stop()
        finally:pygame.mixer.quit()

    def test_machinery_stays_quiet_without_sounding_the_warning_early(self):
        import numpy as np
        self.assertEqual(MACHINERY_START,25.)
        self.audio.start(27.5)
        machinery = self.audio.voices['machinery_bed.wav']
        self.assertEqual(self.audio.events,[{'id':'machinery_bed.wav','time':27.5,'offset':.5}])
        self.assertAlmostEqual(alert_mix_at(33.)['machinery_bed.wav'][0],.12)
        self.assertAlmostEqual(alert_mix_at(35.)['machinery_bed.wav'][0],.015)
        self.assertGreater(max(machinery.channel.volume),0.)
        self.advance(27.5,35.)
        self.assertIs(self.audio.voices['machinery_bed.wav'],machinery)
        quiet = mix_alert_audio(27.5,.25)
        self.assertGreater(float(np.max(np.abs(quiet))),0.)
        self.assertLess(float(np.sqrt(np.mean(quiet*quiet))),.04)
        # Offline machinery loop phase also matches an isolated orbit preview.
        np.testing.assert_array_equal(quiet,mix_alert_audio(25.,3.)[120000:132000])


if __name__ == '__main__':unittest.main()
