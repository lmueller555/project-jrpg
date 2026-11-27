"""Owned effects for the prologue's continuous mountain-flight opening shot.

The wind loop can continue across the shot boundary. Its caller
owns the eventual cut, pause/focus policy and any soundtrack; this module
never resizes the mixer, steals channels or controls music.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path

import pygame


ROOT = Path(__file__).resolve().parent
ASSETS = ROOT/'assets/audio/sfx/fire_veinhold/shot01'
WING_PERIOD = .75
DOWNSTROKE_PHASE = .25
FLAP_WINDOWS = ((0.,2.),(5.,13.25))
CUES = (
    {'id':'foreground_pass','time':.85,'file':'air_pass.wav','gain':.29,'pan':-.45},
    {'id':'bank_gust','time':2.70,'file':'bank_gust.wav','gain':.36,'pan':.38},
    {'id':'climb_rush','time':5.45,'file':'climb_rush.wav','gain':.32,'pan':-.18},
    {'id':'crest_gust','time':14.65,'file':'crest_gust.wav','gain':.30,'pan':.12},
)
HANDOFF = {'shot_duration':25.,'wind_continues':True,'wind_file':'wind_loop.wav',
           'stop_owner':'cinematic controller','wing_period':WING_PERIOD,
           'downstroke_phase':DOWNSTROKE_PHASE,'flap_windows':FLAP_WINDOWS,
           'first_phase_offset_seconds':.391,'second_phase_offset_seconds':.141}


def wing_phase_at(seconds):
    """Match the source animation's neutral-frame-aligned flap/glide joins."""
    if seconds < 2:return (seconds+.391)/WING_PERIOD
    if seconds < 5:return 3.188
    if seconds < 13.25:return 3+(seconds-5+.141)/WING_PERIOD
    return 14.188


@dataclass
class _Voice:
    channel: object
    sound: object
    gain: float
    pan: float
    ends_at: float = math.inf


class PrologueFlightAudio:
    """Scene-time one-shots and a persistent stereo wind lease.

    ``wing_phase`` accepts unwrapped cycles, preferably ``(before, now)``.
    A scalar current phase is also supported. Without an explicit phase the
    authored .75-second flight cycle supplies it. Only crossings of the actual
    downstroke inside the two flap windows sound; glides remain quiet.
    Long seeks consume missed cues without emitting an audible backlog.
    """
    def __init__(self,game,*,asset_root=ASSETS,mixer=None):
        self.game = game
        self.asset_root = Path(asset_root)
        self.mixer = pygame.mixer if mixer is None else mixer
        self.sounds = {}
        self.voices = {}
        self.events = []
        self._active = False
        self._paused = False
        self._clock = 0.
        self._wind_offset = 0.
        self._seen = set()
        self._last_phase = None
        self._last_wing_time = -math.inf
        self._wing_serial = 0
        audio = getattr(game,'audio',None)
        if hasattr(audio,'bind_effects'):audio.bind_effects(self)
        for name in ('wind_loop.wav','wing_feather.wav',*(cue['file'] for cue in CUES)):
            self._sound(name)

    @property
    def volume(self):
        value = getattr(getattr(self.game,'audio',None),'effects_volume',0.)
        try:return max(0.,min(1.,float(value))) if math.isfinite(float(value)) else 0.
        except (TypeError,ValueError):return 0.

    def _sound(self,name):
        try:
            spec = self.mixer.get_init()
            if not spec:return None
            key = name,spec
            if key not in self.sounds:self.sounds[key] = self.mixer.Sound(str(self.asset_root/name))
            return self.sounds[key]
        except (OSError,pygame.error):return None

    @staticmethod
    def _wind_gain(seconds):
        points = ((0.,.27),(2.,.31),(5.,.29),(8.,.34),(10.,.30))
        for (a,ga),(b,gb) in zip(points,points[1:]):
            if seconds <= b:
                ratio = max(0.,min(1.,(seconds-a)/(b-a)))
                ratio = ratio*ratio*(3-2*ratio)
                return ga+(gb-ga)*ratio
        return points[-1][1]

    def _maintain(self):
        for identifier,voice in list(self.voices.items()):
            try:
                if voice.channel.get_sound() is not voice.sound:
                    self.voices.pop(identifier,None);continue
                if self.volume <= 0 or (not self._paused and self._clock >= voice.ends_at):
                    voice.channel.stop();self.voices.pop(identifier,None);continue
                wind_time = self._clock+self._wind_offset
                gain = (self._wind_gain(wind_time) if identifier == 'wind_bed' else voice.gain)*self.volume
                pan = .12*math.sin(wind_time*.55) if identifier == 'wind_bed' else voice.pan
                voice.channel.set_volume(gain*min(1.,1-pan),gain*min(1.,1+pan))
                if self._paused:voice.channel.pause()
                else:voice.channel.unpause()
            except pygame.error:self.voices.pop(identifier,None)

    def _play(self,identifier,name,gain,pan=0.,*,loop=False):
        if not self._active or self._paused or self.volume <= 0:return
        try:
            sound = self._sound(name)
            channel = self.mixer.find_channel() if sound is not None else None
            if channel is None:return
            channel.set_volume(gain*self.volume*min(1.,1-pan),gain*self.volume*min(1.,1+pan))
            channel.play(sound,loops=-1 if loop else 0,fade_ms=90 if loop else 0)
            self.voices[identifier] = _Voice(channel,sound,gain,pan,
                math.inf if loop else self._clock+sound.get_length())
            self.events.append({'id':identifier,'time':self._clock})
            self.events[:] = self.events[-256:]
        except (OSError,pygame.error):return

    def _ensure_wind(self):
        if 'wind_bed' not in self.voices:
            self._play('wind_bed','wind_loop.wav',self._wind_gain(self._clock+self._wind_offset),loop=True)

    def start(self,global_elapsed=0):
        try:now = float(global_elapsed)
        except (TypeError,ValueError):self.stop();return
        if not math.isfinite(now) or now < 0:self.stop();return
        self.reset()
        self._active = True;self._clock = now
        self._seen.update(cue['id'] for cue in CUES if cue['time'] <= now)
        self._ensure_wind()

    def begin_shot(self,local_elapsed=0):
        """Rearm an adjacent flight clip while retaining the current wind lease."""
        try:now = float(local_elapsed)
        except (TypeError,ValueError):self.stop();return
        if not math.isfinite(now) or now < 0:self.stop();return
        if not self._active:
            self.start(now);return
        wind_time = self._clock+self._wind_offset
        for identifier,voice in list(self.voices.items()):
            if identifier == 'wind_bed':continue
            try:
                if voice.channel.get_sound() is voice.sound:voice.channel.stop()
            except pygame.error:pass
            self.voices.pop(identifier,None)
        self._clock = now;self._wind_offset = wind_time-now
        self._seen = {cue['id'] for cue in CUES if cue['time'] <= now}
        self._last_phase = None;self._last_wing_time = -math.inf
        self._maintain();self._ensure_wind()

    def _wing_crossing(self,before,now,wing_phase,mode):
        try:
            if isinstance(wing_phase,(tuple,list)) and len(wing_phase) == 2:
                first,last = map(float,wing_phase)
            elif wing_phase is not None:
                last = float(wing_phase)
                first = self._last_phase
                if first is None:first = wing_phase_at(before)
                if 0 <= first <= 1 and 0 <= last <= 1 and first-last > .5:last += 1
            else:first,last = wing_phase_at(before),wing_phase_at(now)
            self._last_phase = float(wing_phase) if isinstance(wing_phase,(int,float)) else last
        except (TypeError,ValueError):return
        if (mode in ('bank','glide') or not math.isfinite(first) or not math.isfinite(last)
                or last <= first or last-first > 1):return
        boundary = math.floor(first-DOWNSTROKE_PHASE)+1+DOWNSTROKE_PHASE
        if not first < boundary <= last:return
        at = before+(now-before)*(boundary-first)/(last-first)
        if not any(start <= at < end for start,end in FLAP_WINDOWS):return
        if at-self._last_wing_time < .2:return
        self._last_wing_time = at;self._wing_serial += 1
        self._play(f'wing_{self._wing_serial}','wing_feather.wav',.22,pan=-.08)

    def update(self,previous,current,playing=True,wing_phase=None,mode=None):
        if not self._active:return
        try:before,now = float(previous),float(current)
        except (TypeError,ValueError):self.stop();return
        if not math.isfinite(before) or not math.isfinite(now) or min(before,now) < 0:
            self.stop();return
        if not playing:self.pause();return
        if now < before or now < self._clock:
            self.start(now);return
        self._paused = False
        # Repeated draw/update calls must not replay a stroke or transient.
        before = max(before,self._clock)
        self._clock = now
        self._maintain();self._ensure_wind()
        due = [cue for cue in CUES if before < cue['time'] <= now and cue['id'] not in self._seen]
        self._seen.update(cue['id'] for cue in CUES if cue['time'] <= now)
        if now-before > .35 or now <= before:return
        for cue in due:self._play(cue['id'],cue['file'],cue['gain'],cue['pan'])
        self._wing_crossing(before,now,wing_phase,mode)

    def refresh_volume(self):
        self._maintain()
        self._ensure_wind()

    def pause(self):
        self._paused = True;self._maintain()

    def resume(self):
        self._paused = False;self._maintain();self._ensure_wind()

    def stop(self):
        self._active = False
        for voice in self.voices.values():
            try:
                if voice.channel.get_sound() is voice.sound:voice.channel.stop()
            except pygame.error:pass
        self.voices.clear()

    def reset(self):
        self.stop();self.events.clear();self._seen.clear()
        self._clock = 0.;self._wind_offset = 0.;self._paused = False;self._last_phase = None
        self._last_wing_time = -math.inf;self._wing_serial = 0
