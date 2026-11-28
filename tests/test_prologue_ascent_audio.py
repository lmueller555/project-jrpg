"""The crane continues existing voices while their actual listener recedes."""
from hashlib import sha256
import json
import math
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import wave

import numpy as np

from prologue_alert_audio import (ASCENT_START, ASSETS, BREATH_GAIN, BREATH_PERIOD,
                                  FRONTAL_STEP_PAN, GROUP_PERIOD, SEQUENCE_END, PrologueAlertAudio,
                                  alert_mix_at, mix_alert_audio, running_contact_events,
                                  step_mix_at)
from tests.test_prologue_alert_audio import Mixer, RUN_TIMING


class BridgeAscentAudioTests(unittest.TestCase):
    def setUp(self):
        self.game = SimpleNamespace(audio=SimpleNamespace(effects_volume=.5,reduced_motion=False))
        self.mixer = Mixer()
        self.audio = PrologueAlertAudio(self.game,mixer=self.mixer,run_timing=RUN_TIMING)

    def advance(self,start,end,fps=60):
        while start < end-1e-8:
            now = min(end,start+1/fps)
            self.audio.update(start,now)
            start = now
        if start < end:self.audio.update(start,end)

    def test_existing_pcm_prefix_and_all_twelve_wave_masters_remain_unchanged(self):
        path = Path(__file__).parent/'fixtures/prologue_ascent_audio/preserved_prefix.json'
        before = json.loads(path.read_text())
        self.assertEqual(len(before['sounds_sha256']),12)
        for filename,digest in before['sounds_sha256'].items():
            self.assertEqual(sha256((ASSETS/filename).read_bytes()).hexdigest(),digest)
        for reduced in (False,True):
            prefix = mix_alert_audio(39.,8.,run_timing=RUN_TIMING,reduced_motion=reduced)
            self.assertEqual(sha256(prefix.tobytes()).hexdigest(),before['mix_sha256'])

    def test_appended_shot_and_contact_schedule_share_the_fifty_five_second_clock(self):
        from fire_veinhold_opening import available_shots,sequence_duration
        from cinematic_bridge_ascent import read_ascent_timing
        shot = available_shots()[-1]
        self.assertEqual((shot['id'],shot['duration']),('bridge_ascent',8))
        self.assertEqual((ASCENT_START,SEQUENCE_END,sequence_duration()),(47.,55.,55.))
        cues = running_contact_events(RUN_TIMING)
        late = [cue for cue in cues if cue['time'] >= ASCENT_START]
        self.assertEqual(len(late),60)
        self.assertEqual(len({cue['id'] for cue in cues}),len(cues))
        self.assertTrue(all(cue['time'] < SEQUENCE_END for cue in cues))
        for actor in read_ascent_timing():
            actor_cues = [cue for cue in late if cue['actor'] == actor['id']]
            self.assertEqual(len(actor_cues),20)
            for cue in actor_cues:
                phase = (cue['time']-ASCENT_START+actor['phase_offset_seconds'])%.8
                expected = 0. if cue['foot'] == 'near' else .4
                error = abs(phase-expected)
                self.assertLess(min(error,abs(error-.8)),1e-8)

    def test_loading_acoustic_curves_does_not_load_images_advance_time_or_claim_channels(self):
        with patch('pygame.image.load',side_effect=AssertionError('Audio loaded a picture')):
            self.audio.prepare_ascent()
        self.assertEqual(self.audio._clock,0.)
        self.assertEqual(self.audio.events,[])
        self.assertFalse(self.audio.voices)
        self.assertTrue(all(not channel.plays for channel in self.mixer.channels))

    def test_existing_leases_and_current_contact_tails_survive_the_crane_handoff(self):
        self.audio.start(46.99)
        leases = {name:self.audio.voices[name] for name in
                  ('machinery_bed.wav','distant_siren.wav','running_breath.wav')}
        iselin = self.audio.voices['run:iselin:near:9']
        plays = len(iselin.channel.plays)
        volume = iselin.channel.volume
        self.audio.update(46.99,47.)
        self.assertTrue(all(self.audio.voices[name] is voice for name,voice in leases.items()))
        self.assertIs(self.audio.voices['run:iselin:near:9'],iselin)
        self.assertEqual(len(iselin.channel.plays),plays)
        self.assertEqual(iselin.channel.volume,volume)
        self.assertIn('run:lucan:near:10',self.audio.voices)
        self.assertEqual(alert_mix_at(47.)['running_breath.wav'],(BREATH_GAIN,0.))
        self.audio.start(47.)
        offsets = {event['id']:event['offset'] for event in self.audio.events}
        self.assertEqual(offsets['machinery_bed.wav'],0.)
        self.assertEqual(offsets['distant_siren.wav'],1.)
        self.assertAlmostEqual(offsets['running_breath.wav'],5.%BREATH_PERIOD)
        self.assertAlmostEqual(offsets['run:iselin:near:9'],1/6)
        self.assertEqual(offsets['run:lucan:near:10'],0.)

    def test_close_sources_recede_and_stereo_follows_actual_projected_positions(self):
        from cinematic_bridge_ascent import actor_states_at,project_world
        for reduced in (False,True):
            for name in ('lucan','iselin','crown_soldier'):
                entry = step_mix_at(name,47.,reduced)
                self.assertEqual(entry[1],FRONTAL_STEP_PAN[name])
                previous_distance = None
                for local in (2.2,4.,5.8,7.99):
                    state = actor_states_at(local,reduced)
                    actor = next(row for row in state['runners'] if row['id'] == name)
                    camera = state['camera'];point = actor['world_position_metres']
                    distance = math.dist(camera['position'],point)
                    gain,pan = step_mix_at(name,47.+local,reduced)
                    projected = project_world(point,camera)
                    expected_pan = max(-.85,min(.85,(projected[0]-480.)/480.))
                    self.assertAlmostEqual(pan,expected_pan,places=7)
                    self.assertLess(gain,entry[0]*.15)
                    if previous_distance is not None:self.assertGreater(distance,previous_distance)
                    previous_distance = distance
                self.assertLess(step_mix_at(name,54.99,reduced)[0],entry[0]*.01)
            breath_fraction = alert_mix_at(49.2,reduced)['running_breath.wav'][0]/BREATH_GAIN
            foot_fraction = step_mix_at('lucan',49.2,reduced)[0]/step_mix_at('lucan',47.,reduced)[0]
            self.assertLess(breath_fraction,foot_fraction)

    def test_standalone_pcm_matches_the_full_reel_slice_and_contains_fading_steps(self):
        for reduced in (False,True):
            full = mix_alert_audio(46.8,8.2,run_timing=RUN_TIMING,reduced_motion=reduced)
            clip = mix_alert_audio(47.,8.,run_timing=RUN_TIMING,reduced_motion=reduced)
            np.testing.assert_array_equal(clip,full[9600:])
            isolated = mix_alert_audio(48.375,1.125,run_timing=RUN_TIMING,reduced_motion=reduced)
            np.testing.assert_array_equal(isolated,clip[66000:120000])
            ambience = mix_alert_audio(47.,8.,run_timing=(),reduced_motion=reduced)
            footsteps = clip-ambience
            early = float(np.sqrt(np.mean(footsteps[:48000]**2)))
            late = float(np.sqrt(np.mean(footsteps[-48000:]**2)))
            self.assertGreater(early,late*20)
            self.assertGreater(float(np.max(np.abs(clip))),.01)
            self.assertLess(float(np.max(np.abs(clip))),1.)

    def test_live_contact_volume_and_offline_pcm_use_the_same_camera_envelope(self):
        cue = next(cue for cue in running_contact_events(RUN_TIMING)
                   if cue['actor']=='lucan' and cue['foot']=='near' and cue['time']>49.)
        moment = cue['time']+.04
        self.audio.start(moment)
        voice = self.audio.voices[cue['id']]
        timing = ({**RUN_TIMING[0],'contacts':({'foot':'near','time_seconds':0.},)},)
        picture = mix_alert_audio(moment,1/48000,run_timing=timing)
        background = mix_alert_audio(moment,1/48000,run_timing=())
        with wave.open(str(ASSETS/cue['file']),'rb') as reader:
            reader.setpos(round(.04*reader.getframerate()))
            source = np.frombuffer(reader.readframes(1),dtype='<i2')/32767.
        expected = source*np.asarray(voice.channel.volume)/self.game.audio.effects_volume
        np.testing.assert_allclose((picture-background)[0],expected,atol=3e-8,rtol=1e-5)

    def test_frame_rates_pause_mute_seek_and_completion_preserve_channel_ownership(self):
        for fps in (15,30,60,120):
            self.setUp()
            wind = object();self.mixer.channels[-1].sound = wind
            self.audio.start(47.)
            self.advance(47.,55.,fps)
            steps = [sound for channel in self.mixer.channels for sound,_,_ in channel.plays
                     if '_step_' in sound.path.name]
            self.assertEqual(len(steps),61)  #60 new contacts plus Iselin's entry tail.
            ids = [event['id'] for event in self.audio.events if event['id'].startswith('run:')]
            self.assertEqual(len(ids),len(set(ids)))
            self.assertFalse(self.audio.voices)
            self.assertIs(self.mixer.channels[-1].sound,wind)
        self.audio.start(47.2)
        events = list(self.audio.events)
        self.audio.update(47.2,47.2,playing=False)
        self.assertTrue(all(voice.channel.paused for voice in self.audio.voices.values()))
        self.audio.resume();self.audio.update(47.2,47.21)
        self.assertEqual(self.audio.events,events)
        self.game.audio.effects_volume = 0.;self.audio.refresh_volume()
        self.assertFalse(self.audio.voices)
        self.audio.update(47.21,50.)
        self.game.audio.effects_volume = .5;self.audio.refresh_volume()
        self.assertFalse(any(voice.actor for voice in self.audio.voices.values()))
        self.assertAlmostEqual(next(event['offset'] for event in reversed(self.audio.events)
                              if event['id']=='running_breath.wav'),(50.-42.)%BREATH_PERIOD)
        self.audio.update(50.,48.333)
        self.assertEqual(self.audio._clock,48.333)
        self.assertTrue(all(not event['id'].startswith('run:') or event['offset']<.22
                            for event in self.audio.events))
        self.audio.stop();self.audio.resume();self.audio.refresh_volume()
        self.assertFalse(self.audio.voices)

    def test_factory_sources_follow_their_positions_and_remain_audible_behind_camera(self):
        from cinematic_bridge_ascent import acoustic_sources_at,actor_states_at,project_world
        from prologue_alert_audio import _ascent_acoustic_table
        camera = actor_states_at(0.)['camera']
        sources = acoustic_sources_at(0.)
        before,entry = alert_mix_at(47.-1e-8),alert_mix_at(47.)
        for name,filename in (('warning','distant_siren.wav'),('machinery','machinery_bed.wav')):
            self.assertIsNone(project_world(sources[name],camera))
            self.assertAlmostEqual(entry[filename][0],before[filename][0])
            self.assertEqual(entry[filename][1],before[filename][1])
            self.assertGreater(alert_mix_at(54.9)[filename][0],0.)
            self.assertLess(alert_mix_at(54.9)[filename][0],entry[filename][0]*.9)
        # Source azimuth must follow the actual shared source positions rather
        # than a constant rear-facing pan or positive projection-depth test.
        original = acoustic_sources_at
        def shifted(local,reduced=False):
            points = original(local,reduced)
            points['warning'][0] = 100.
            points['machinery'][0] = -100.
            return points
        try:
            with patch('cinematic_bridge_ascent.acoustic_sources_at',side_effect=shifted):
                _ascent_acoustic_table.cache_clear()
                moved = alert_mix_at(51.)
                self.assertLess(moved['distant_siren.wav'][1],-.1)
                self.assertGreater(moved['machinery_bed.wav'][1],.1)
        finally:
            _ascent_acoustic_table.cache_clear()

    def test_single_group_loop_fits_with_wind_and_three_simultaneous_party_contacts(self):
        manifest = json.loads((ASSETS/'manifest.json').read_text())
        from cinematic_bridge_ascent import reinforcement_states_at
        self.assertAlmostEqual(GROUP_PERIOD,3*.8)
        self.assertEqual(manifest['reinforcement_group']['phase_offsets'],
                         [actor['cycle_phase'] for actor in reinforcement_states_at(0.)])
        self.assertNotIn('reinforcement_group.wav',alert_mix_at(47.-1e-8))
        self.assertEqual(alert_mix_at(47.)['reinforcement_group.wav'][0],0.)
        self.assertGreater(alert_mix_at(48.)['reinforcement_group.wav'][0],0.)
        self.assertLess(alert_mix_at(48.)['reinforcement_group.wav'][0],.01)
        # Synthetic timing stresses the exact eight-channel allocation without
        # claiming that the staggered production actors all contact together.
        together = tuple({**actor,'phase_offset_seconds':0.} for actor in RUN_TIMING)
        self.audio = PrologueAlertAudio(self.game,mixer=self.mixer,run_timing=together)
        wind = object();self.mixer.channels[-1].sound = wind
        self.audio.start(47.)
        self.assertEqual(sum(channel.sound is not None for channel in self.mixer.channels),8)
        self.assertEqual(sum(voice.actor is not None for voice in self.audio.voices.values()),3)
        group = self.audio.voices['reinforcement_group.wav']
        self.advance(47.,49.,120)
        self.assertIs(self.audio.voices['reinforcement_group.wav'],group)
        group_plays = [entry for channel in self.mixer.channels for entry in channel.plays
                       if entry[0].path.name=='reinforcement_group.wav']
        self.assertEqual(len(group_plays),1)
        self.assertEqual(group_plays[0][1],-1)
        self.audio.stop()
        self.assertIs(self.mixer.channels[-1].sound,wind)
        self.assertTrue(all(channel.sound is None for channel in self.mixer.channels[:-1]))

    def test_group_loop_keeps_global_phase_through_pause_mute_and_backward_seek(self):
        name = 'reinforcement_group.wav'
        self.audio.start(48.37)
        group = self.audio.voices[name]
        self.assertAlmostEqual(next(event['offset'] for event in self.audio.events
                                    if event['id']==name),1.37)
        self.audio.pause();self.audio.update(48.37,48.37,playing=False)
        self.assertTrue(group.channel.paused)
        self.audio.resume();self.audio.update(48.37,48.38)
        self.assertIs(self.audio.voices[name],group)
        self.assertEqual(len(group.channel.plays),1)
        self.game.audio.effects_volume = 0.;self.audio.refresh_volume()
        self.assertFalse(self.audio.voices)
        self.audio.update(48.38,50.2)
        self.game.audio.effects_volume = .5;self.audio.refresh_volume()
        self.assertAlmostEqual(next(event['offset'] for event in reversed(self.audio.events)
                                    if event['id']==name),(50.2-47.)%GROUP_PERIOD)
        self.audio.update(50.2,48.13)
        self.assertAlmostEqual(next(event['offset'] for event in self.audio.events
                                    if event['id']==name),1.13)
        self.assertFalse(any(voice.actor and voice.ends_at<=48.13
                             for voice in self.audio.voices.values()))
        self.audio.stop();self.audio.refresh_volume()
        self.assertFalse(self.audio.voices)


if __name__ == '__main__':unittest.main()
