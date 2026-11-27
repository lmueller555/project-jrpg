"""Flight effects follow real strokes, scene time and strict channel leases."""
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

from prologue_flight_audio import (ASSETS,CUES,DOWNSTROKE_PHASE,FLAP_WINDOWS,
                                   PrologueFlightAudio,WING_PERIOD,wing_phase_at)


class Sound:
    def __init__(self,path):self.path = Path(path)
    def get_length(self):return .3 if self.path.name == 'wing_feather.wav' else 2.


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


class FlightAudioTests(unittest.TestCase):
    def setUp(self):
        self.game = SimpleNamespace(audio=SimpleNamespace(effects_volume=.5))
        self.mixer = Mixer();self.audio = PrologueFlightAudio(self.game,mixer=self.mixer)

    def advance(self,before,until,fps=60):
        while before < until-1e-8:
            now = min(until,before+1/fps)
            mode = 'flap' if any(a <= now < b for a,b in FLAP_WINDOWS) else 'glide'
            self.audio.update(before,now,wing_phase=(wing_phase_at(before),wing_phase_at(now)),mode=mode)
            before = now

    def test_start_and_frame_rates_follow_all_air_cues_and_actual_downstrokes_once(self):
        self.audio.update(0,.2)
        self.assertFalse(self.audio.voices)
        for fps in (30,60):
            with self.subTest(fps=fps):
                self.audio.start();self.advance(0,25,fps)
                ids = [event['id'] for event in self.audio.events]
                self.assertEqual([identifier for identifier in ids if identifier in {cue['id'] for cue in CUES}],
                                 [cue['id'] for cue in CUES])
                wings = [event for event in self.audio.events if event['id'].startswith('wing_')]
                expected = [.5465,1.2965]+[5.0465+.75*index for index in range(11)]
                self.assertEqual(len(wings),13)
                for event,at in zip(wings,expected):
                    self.assertGreaterEqual(event['time']+1e-8,at)
                    self.assertLessEqual(event['time']-at,1/fps+1e-8)
                self.assertEqual(ids.count('wind_bed'),1)
                self.audio.update(24.99,25,wing_phase=(14.188,14.188))
                self.assertEqual([event['id'] for event in self.audio.events],ids)

    def test_renderer_phase_controls_stroke_and_glide_mode_suppresses_it(self):
        self.audio.start()
        self.audio.update(.1,.2,wing_phase=(.1,.2),mode='flap')
        self.assertEqual(len(self.audio.events),1)
        self.audio.update(.2,.3,wing_phase=(.2,.3),mode='flap')
        self.assertEqual(self.audio.events[-1]['id'],'wing_1')
        count = len(self.audio.events)
        self.audio.update(.3,.31,wing_phase=(1.2,1.3),mode='bank')
        self.assertEqual(len(self.audio.events),count)
        self.audio.update(.31,.32,wing_phase=(2.2,2.3),mode='glide')
        self.assertEqual(len(self.audio.events),count)

    def test_pause_focus_and_resume_preserve_leases_without_advancing_or_replaying(self):
        self.audio.start();self.advance(0,.92)
        before = list(self.audio.events);clock = self.audio._clock
        voices = list(self.audio.voices.values())
        self.audio.update(clock,clock,playing=False)
        self.assertTrue(all(voice.channel.paused for voice in voices))
        self.game.audio.effects_volume = .2;self.audio.refresh_volume()
        self.assertTrue(all(voice.channel.paused for voice in voices))
        self.assertEqual(self.audio._clock,clock)
        self.audio.resume();self.audio.update(clock,clock+.001)
        self.assertFalse(any(voice.channel.paused for voice in voices))
        self.assertEqual(self.audio.events,before)

    def test_effects_volume_mute_and_unmute_do_not_queue_old_transients(self):
        self.audio.start();bed = self.audio.voices['wind_bed']
        self.game.audio.effects_volume = 1.;self.audio.refresh_volume()
        louder = max(bed.channel.volume)
        self.game.audio.effects_volume = .25;self.audio.refresh_volume()
        self.assertAlmostEqual(max(bed.channel.volume),louder*.25)
        self.game.audio.effects_volume = 0.;self.audio.refresh_volume()
        self.assertFalse(self.audio.voices)
        self.advance(0,5)
        self.assertEqual([event['id'] for event in self.audio.events],['wind_bed'])
        self.game.audio.effects_volume = 1.;self.audio.refresh_volume()
        self.assertEqual(set(self.audio.voices),{'wind_bed'})
        self.audio.update(5,5.01)
        self.assertEqual([event['id'] for event in self.audio.events],['wind_bed','wind_bed'])

    def test_channel_reuse_never_pauses_changes_volume_or_stops_foreign_sound(self):
        self.audio.start();bed = self.audio.voices['wind_bed']
        foreign = object();bed.channel.sound = foreign
        volume = bed.channel.volume
        self.audio.pause();self.audio.refresh_volume();self.audio.stop()
        self.assertIs(bed.channel.sound,foreign)
        self.assertEqual(bed.channel.volume,volume)
        self.assertFalse(bed.channel.paused)
        self.assertEqual(bed.channel.stops,0)

    def test_busy_or_absent_mixer_drops_cues_without_stealing_or_later_backlog(self):
        for channel in self.mixer.channels:channel.sound = object()
        foreign = [channel.sound for channel in self.mixer.channels]
        self.audio.start();self.advance(0,3)
        self.assertFalse(self.audio.events)
        self.assertEqual([channel.sound for channel in self.mixer.channels],foreign)
        for channel in self.mixer.channels:channel.sound = None
        self.audio.update(3,3.01)
        self.assertEqual([event['id'] for event in self.audio.events],['wind_bed'])
        self.audio.reset();self.mixer.ready = False
        self.audio.start();self.advance(0,.3)
        self.assertFalse(self.audio.events)

    def test_seek_restart_stop_and_ten_second_handoff_have_no_replay_or_end_fade(self):
        self.audio.start();bed = self.audio.voices['wind_bed']
        self.audio.update(0,9.)
        self.assertEqual([event['id'] for event in self.audio.events],['wind_bed'])
        self.audio.update(9.,10.);self.audio.update(10.,10.1,mode='glide')
        self.assertIs(self.audio.voices['wind_bed'],bed)
        self.assertGreater(min(bed.channel.volume),0.)
        self.assertTrue(math.isinf(bed.ends_at))
        self.assertEqual(bed.channel.plays[0][1],-1)
        self.audio.stop();self.audio.refresh_volume();self.audio.resume()
        self.assertFalse(self.audio.voices)
        self.assertEqual(bed.channel.stops,1)
        self.audio.start();self.advance(0,.56)
        self.assertEqual([event['id'] for event in self.audio.events],['wind_bed','wing_1'])
        self.audio.update(.56,.05)
        self.assertEqual([event['id'] for event in self.audio.events],['wind_bed'])

    def test_adjacent_shot_rearms_cues_without_restarting_or_remixing_wind(self):
        self.audio.start();self.advance(0,10)
        bed = self.audio.voices['wind_bed'];channel = bed.channel
        old_volume = channel.volume
        starts = sum(event['id']=='wind_bed' for event in self.audio.events)
        self.audio.begin_shot()
        self.assertEqual(self.audio._clock,0)
        self.assertIs(self.audio.voices['wind_bed'],bed)
        self.assertEqual(channel.volume,old_volume)
        self.assertEqual(len(channel.plays),1)
        self.assertEqual(channel.stops,0)
        self.assertEqual(set(self.audio.voices),{'wind_bed'})
        self.advance(0,.9)
        self.assertEqual(sum(event['id']=='foreground_pass' for event in self.audio.events),2)
        self.assertEqual(sum(event['id']=='wind_bed' for event in self.audio.events),starts)

    def test_invalid_times_and_minimal_settings_remain_silent_and_safe(self):
        for invalid in (float('nan'),float('inf'),-1,'bad'):
            self.audio.start();self.audio.update(0,invalid)
            self.assertFalse(self.audio.voices)
        silent = PrologueFlightAudio(SimpleNamespace(),mixer=self.mixer)
        silent.start();silent.update(0,.2)
        self.assertFalse(silent.voices)

    def test_retained_sources_and_production_exports_are_finite_stereo_and_unclipped(self):
        import numpy as np
        manifest = json.loads((ASSETS/'manifest.json').read_text())
        self.assertFalse(manifest['handoff']['automatic_end_fade'])
        self.assertEqual(set(manifest['sounds']),{'wind_loop','air_pass','bank_gust',
                                                 'climb_rush','crest_gust','wing_feather'})
        root = Path(__file__).resolve().parents[1]
        source = root/manifest['source']['file']
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),manifest['source']['sha256'])
        total = 0
        for name,record in manifest['sounds'].items():
            with self.subTest(sound=name):
                path = ASSETS/(name+'.wav');total += path.stat().st_size
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),record['sha256'])
                with wave.open(str(path),'rb') as stream:
                    self.assertEqual((stream.getframerate(),stream.getnchannels(),stream.getsampwidth()),(48000,2,2))
                    value = np.frombuffer(stream.readframes(stream.getnframes()),dtype='<i2').reshape(-1,2)
                self.assertGreater(np.max(np.abs(value.astype(np.int32))),100)
                self.assertLess(np.max(np.abs(value.astype(np.int32))),32767)
                self.assertEqual(record['clipped_samples'],0)
                if name == 'wind_loop':
                    self.assertFalse(np.array_equal(value[:,0],value[:,1]))
                    self.assertLess(np.max(np.abs(value[0].astype(int)-value[-1])),
                                    np.max(np.abs(np.diff(value.astype(int),axis=0))))
        self.assertLess(total,4*1024*1024)

    def test_real_mixer_later_clip_seeds_pcm_wind_phase_and_preserves_join_lease(self):
        import pygame
        pygame.mixer.init(frequency=48000,size=-16,channels=2)
        try:
            audio = PrologueFlightAudio(self.game)
            original = audio._sound('wind_loop.wav')
            raw = original.get_raw()
            audio.start(35.)
            wind = audio.voices['wind_bed']
            # Six-second source: global35s begins at its five-second mark.
            cut = round(5.*48000)*4
            self.assertEqual(wind.sound.get_raw(),raw[cut:]+raw[:cut])
            audio.update(35.,35.1,mode='glide')
            audio.begin_shot()
            self.assertIs(audio.voices['wind_bed'],wind)
            self.assertEqual([event['id'] for event in audio.events],['wind_bed'])
            audio.stop()
            # Repeated standalone seeks retain one shifted copy at most.
            for phase in (25.,30.25,34.5,35.75):
                audio.start(phase);audio.stop()
            shifted = [key for key in audio.sounds if len(key) == 3 and key[0]=='wind_loop.wav']
            self.assertLessEqual(len(shifted),1)
        finally:pygame.mixer.quit()


if __name__ == '__main__':unittest.main()
