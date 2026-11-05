"""Action sound cues share cinematic time and own only their own channels."""
import os
from pathlib import Path
from types import SimpleNamespace
import unittest

os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

from ice_reaper_audio import CUES, IceReaperActionAudio


class Sound:
    def __init__(self, path):self.path=path
    def get_length(self):return 1.2


class Channel:
    def __init__(self):
        self.sound=None;self.paused=False;self.stops=0;self.volume=0
    def get_sound(self):return self.sound
    def set_volume(self,value):self.volume=value
    def play(self,sound,loops=0):self.sound=sound
    def pause(self):self.paused=True
    def unpause(self):self.paused=False
    def stop(self):self.stops+=1;self.sound=None


class Mixer:
    def __init__(self):self.channels=[];self.ready=True;self.busy=False
    def get_init(self):return (48000,-16,2) if self.ready else None
    def Sound(self,path):return Sound(path)
    def find_channel(self):
        if self.busy:return None
        channel=Channel();self.channels.append(channel);return channel


class IceReaperAudioTests(unittest.TestCase):
    def setUp(self):
        self.game=SimpleNamespace(audio=SimpleNamespace(effects_volume=.5))
        self.mixer=Mixer()
        self.audio=IceReaperActionAudio(self.game,mixer=self.mixer)

    def advance(self,start,end,fps=60):
        current=start
        while current < end-1e-8:
            following=min(end,current+1/fps)
            self.audio.update(current,following)
            current=following

    def test_cues_fire_exactly_once_at_30_and_60_fps(self):
        for fps in (30,60):
            self.audio.reset()
            self.advance(0,20,fps)
            self.assertEqual([event['id'] for event in self.audio.events],
                             [cue['id'] for cue in CUES])
            for event,cue in zip(self.audio.events,CUES):
                self.assertGreaterEqual(event['time']+1e-8,cue['time'])
                self.assertLessEqual(event['time']-cue['time'],1/fps+1e-8)
            self.audio.update(19.99,20)
            self.assertEqual(len(self.audio.events),len(CUES))

    def test_pause_and_focus_flag_freeze_channels_without_replaying(self):
        self.audio.update(6.99,7.01)
        voice=self.audio.voices['caelan_dash']
        self.audio.update(7.01,7.01,playing=False)
        self.assertTrue(voice.channel.paused)
        self.assertEqual(self.audio._clock,7.01)
        self.audio.refresh_volume()
        self.assertTrue(voice.channel.paused)
        self.audio.update(7.01,7.02,playing=True)
        self.assertFalse(voice.channel.paused)
        self.assertEqual(len(self.audio.events),1)

    def test_muting_stops_voices_and_does_not_bank_cues(self):
        self.audio.update(6.99,7.01)
        self.game.audio.effects_volume=0
        self.audio.refresh_volume()
        self.assertFalse(self.audio.voices)
        self.audio.update(7.01,7.16)
        self.game.audio.effects_volume=1
        self.audio.update(7.16,7.17)
        self.assertEqual([event['id'] for event in self.audio.events],['caelan_dash'])

    def test_stop_never_stops_a_channel_reused_by_another_controller(self):
        self.audio.update(6.99,7.01)
        voice=self.audio.voices['caelan_dash']
        foreign=object();voice.channel.sound=foreign
        self.audio.pause();self.audio.stop()
        self.assertIs(voice.channel.sound,foreign)
        self.assertFalse(voice.channel.paused)
        self.assertEqual(voice.channel.stops,0)

    def test_seek_discards_backlog_but_restart_rearms(self):
        self.audio.update(0,15)
        self.assertFalse(self.audio.events)
        self.audio.update(15,15.01)
        self.assertFalse(self.audio.events)
        self.audio.reset()
        self.audio.update(6.99,7.01)
        self.assertEqual(len(self.audio.events),1)
        self.audio.update(7.01,4)
        self.assertFalse(self.audio.voices)
        self.assertFalse(self.audio.events)
        self.audio.update(6.99,7.01)
        self.assertEqual(len(self.audio.events),1)

    def test_busy_or_absent_mixer_and_minimal_settings_are_safe(self):
        self.mixer.busy=True
        self.audio.update(6.99,7.01)
        self.assertFalse(self.audio.events)
        self.audio.reset();self.mixer.ready=False
        self.audio.update(6.99,7.01)
        self.assertFalse(self.audio.events)
        silent=IceReaperActionAudio(SimpleNamespace(audio=SimpleNamespace()),mixer=self.mixer)
        silent.update(6.99,7.01)
        self.assertFalse(silent.events)

    def test_assets_are_finite_nonempty_and_gains_are_bounded(self):
        import json
        root=Path(__file__).resolve().parents[1]
        manifest=json.loads((root/'assets/audio/sfx/ice_reaper_rescue/manifest.json').read_text())
        self.assertEqual(manifest['cues'],list(CUES))
        for cue in CUES:
            self.assertTrue((root/cue['file']).is_file())
            self.assertGreater((root/cue['file']).stat().st_size,1000)
            self.assertTrue(0<cue['gain']<1)
        for sound in manifest['sounds'].values():
            self.assertTrue(0<sound['duration']<4)


if __name__=='__main__':unittest.main()
