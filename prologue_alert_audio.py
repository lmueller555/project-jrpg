"""Scene-clock emergency sound for the orbit, bridge rush and frozen aftermath.

The existing flight controller owns the continuous wind. This owner leases only
free effects channels, never changes music/mixer allocation, and keeps warnings
continuous across the authored clip boundaries. Standalone clips seed themselves
from their full-reel offset, including the warning loop's sample phase.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import wave

import pygame


ROOT = Path(__file__).resolve().parent
ASSETS = ROOT/'assets/story/fire_veinhold_opening/continuation/audio'
MACHINERY_START = 25.
ALARM_START = 30.
RUSH_START = 34.
BRIDGE_ARRIVAL = 35.
RUNNING_START = 39.
SEQUENCE_END = 42.
STEP_DURATION = .22
RUN_SCENE = ROOT/'assets/story/fire_veinhold_opening/shot06/scene.json'
STEP_MIX = {'lucan':(.30,.16),'iselin':(.21,-.03),'crown_soldier':(.16,-.40)}
STEP_SOUNDS = tuple(f'{actor}_step_{foot}.wav'
                    for actor in STEP_MIX for foot in ('near','far'))
SIREN_PERIOD = 2.
LOOPS = (('machinery_bed.wav',MACHINERY_START),
         ('industrial_siren.wav',ALARM_START),('distant_siren.wav',ALARM_START))
TRANSIENTS = (('bridge_rush.wav',RUSH_START,1.),('ice_settle.wav',BRIDGE_ARRIVAL,1.4))


def _smooth(value):
    value = max(0.,min(1.,value))
    return value*value*(3.-2.*value)


def alert_mix_at(seconds):
    """Return filename → (gain, pan) for the same production/offline mix."""
    if not math.isfinite(seconds) or not MACHINERY_START <= seconds < SEQUENCE_END:return {}
    travel = _smooth(seconds-RUSH_START)
    result = {'machinery_bed.wav':(.12-.105*travel,.08*(1-travel))}
    if seconds >= ALARM_START:
        result.update({'industrial_siren.wav':(.34*(1-travel),.12*(1-2*travel)),
                       'distant_siren.wav':(.115*travel,-.12)})
    if RUSH_START <= seconds < BRIDGE_ARRIVAL:result['bridge_rush.wav'] = (.53,-.1+.2*travel)
    if BRIDGE_ARRIVAL <= seconds < BRIDGE_ARRIVAL+1.4:result['ice_settle.wav'] = (.20,.14)
    return result


def running_contact_events(timing=None):
    """Schedule single steps from the renderer's authored contact metadata.

    Positive animation offsets advance the same cycle in picture and sound.
    Parsing happens once per owner/capture, never on the per-frame audio path.
    A checkout without the optional running assets retains its earlier audio.
    """
    if timing is None:
        if not RUN_SCENE.is_file():return ()
        from cinematic_bridge_run import read_run_timing
        timing = read_run_timing(RUN_SCENE)
    result = []
    for actor in timing:
        name = actor['id']
        if name not in STEP_MIX:raise ValueError('Unknown running Foley actor')
        cycle = float(actor['cycle_seconds'])
        offset = float(actor['phase_offset_seconds'])
        if not math.isfinite(cycle) or cycle <= 0 or not math.isfinite(offset):
            raise ValueError('Invalid running Foley timing')
        gain,pan = STEP_MIX[name]
        for contact in actor['contacts']:
            foot = contact['foot'];phase = float(contact['time_seconds'])
            if foot not in ('near','far') or not math.isfinite(phase) or not 0 <= phase < cycle:
                raise ValueError('Invalid authored foot contact')
            first = (phase-offset)%cycle
            if abs(first-cycle) < 1e-8:first = 0.
            for repeat in range(math.ceil((SEQUENCE_END-RUNNING_START)/cycle)+1):
                local = first+repeat*cycle
                if local >= SEQUENCE_END-RUNNING_START-1e-8:break
                at = RUNNING_START+local
                result.append({'id':f'run:{name}:{foot}:{repeat}', 'actor':name,
                    'foot':foot,'file':f'{name}_step_{foot}.wav',
                    'time':at,'duration':STEP_DURATION,'gain':gain,'pan':pan})
    return tuple(sorted(result,key=lambda cue:(cue['time'],cue['id'])))


@dataclass
class _Voice:
    channel: object
    sound: object
    ends_at: float = math.inf
    gain: float | None = None
    pan: float = 0.


class PrologueAlertAudio:
    def __init__(self,game,*,asset_root=ASSETS,mixer=None,run_timing=None):
        self.game = game
        self.asset_root = Path(asset_root)
        self.mixer = pygame.mixer if mixer is None else mixer
        self.sounds = {};self.voices = {};self.events = []
        self._active = False;self._paused = False;self._clock = 0.
        self._seen = set()
        self.run_contacts = running_contact_events(run_timing)
        audio = getattr(game,'audio',None)
        if hasattr(audio,'bind_effects'):audio.bind_effects(self)
        for name in (*(item[0] for item in LOOPS),*(item[0] for item in TRANSIENTS),*STEP_SOUNDS):
            self._sound(name)

    @property
    def volume(self):
        try:
            value = float(getattr(getattr(self.game,'audio',None),'effects_volume',0.))
            return max(0.,min(1.,value)) if math.isfinite(value) else 0.
        except (TypeError,ValueError):return 0.

    def _sound(self,name,offset=0.,*,loop=False):
        try:
            spec = self.mixer.get_init()
            if not spec:return None
            base = (name,spec,0)
            if base not in self.sounds:self.sounds[base] = self.mixer.Sound(str(self.asset_root/name))
            original = self.sounds[base]
            if offset <= 1e-7 or not hasattr(original,'get_raw'):return original
            raw = original.get_raw()
            # get_raw() uses the mixer's converted PCM format, including mono.
            stride = abs(spec[1])//8*spec[2]
            count = len(raw)//stride
            frame = min(count,round(offset*spec[0]))
            if loop:frame %= max(1,count)
            key = name,spec,frame
            if frame == 0:return original
            if key not in self.sounds:
                cut = frame*stride
                shifted = raw[cut:]+raw[:cut] if loop else raw[cut:]
                if not shifted:return None
                self.sounds[key] = self.mixer.Sound(buffer=shifted)
                # Seeks must not accumulate an unbounded collection of PCM copies.
                for other in list(self.sounds):
                    if other[0] == name and other[2] and other != key:self.sounds.pop(other)
            return self.sounds[key]
        except (OSError,pygame.error,ValueError):return None

    def _play(self,name,*,offset=0.,loop=False,ends_at=math.inf,identifier=None,gain=None,pan=0.):
        if not self._active or self._paused or self.volume <= 0:return
        try:
            sound = self._sound(name,offset,loop=loop)
            channel = self.mixer.find_channel() if sound is not None else None
            if channel is None:return
            channel.set_volume(0.,0.)
            channel.play(sound,loops=-1 if loop else 0,fade_ms=35 if loop else 0)
            identifier = name if identifier is None else identifier
            self.voices[identifier] = _Voice(channel,sound,ends_at,gain,pan)
            self.events.append({'id':identifier,'time':self._clock,'offset':offset})
            self.events[:] = self.events[-64:]
        except (OSError,pygame.error):pass

    def _release(self,name):
        voice = self.voices.pop(name,None)
        if voice is None:return
        try:
            if voice.channel.get_sound() is voice.sound:voice.channel.stop()
        except pygame.error:pass

    def _maintain(self):
        mix = alert_mix_at(self._clock)
        for name,voice in list(self.voices.items()):
            try:
                if voice.channel.get_sound() is not voice.sound:
                    self.voices.pop(name,None);continue
                if self.volume <= 0 or not mix or (not self._paused and self._clock >= voice.ends_at):
                    self._release(name);continue
                gain,pan = (mix.get(name,(0.,0.)) if voice.gain is None
                            else (voice.gain,voice.pan))
                gain *= self.volume
                voice.channel.set_volume(gain*min(1.,1-pan),gain*min(1.,1+pan))
                if self._paused:voice.channel.pause()
                else:voice.channel.unpause()
            except pygame.error:self.voices.pop(name,None)

    def _ensure_loops(self):
        if not self._active or self._paused or self._clock >= SEQUENCE_END:return
        for name,start in LOOPS:
            if self._clock >= start and name not in self.voices:
                self._play(name,offset=(self._clock-start)%SIREN_PERIOD,loop=True)

    @staticmethod
    def _valid_time(value):
        try:
            result = float(value)
            return result if math.isfinite(result) and result >= 0 else None
        except (TypeError,ValueError):return None

    def start(self,global_elapsed=0.):
        now = self._valid_time(global_elapsed)
        self.reset()
        if now is None:return
        self._active = now < SEQUENCE_END;self._clock = now
        if not self._active:return
        self._ensure_loops()
        for name,at,duration in TRANSIENTS:
            if now >= at:self._seen.add(name)
            # Standalone mid-shot playback begins at the proper sound sample.
            if at <= now < at+duration:
                self._play(name,offset=now-at,ends_at=at+duration)
        for cue in self.run_contacts:
            at = cue['time']
            if now >= at:self._seen.add(cue['id'])
            if at <= now < at+cue['duration']:
                self._play_step(cue,now-at)
        self._maintain()

    def _play_step(self,cue,offset):
        self._play(cue['file'],offset=offset,ends_at=cue['time']+cue['duration'],
                   identifier=cue['id'],gain=cue['gain'],pan=cue['pan'])

    def update(self,previous,current,playing=True):
        if not self._active:return
        before,now = self._valid_time(previous),self._valid_time(current)
        if before is None or now is None:self.stop();return
        if not playing:self.pause();return
        if now < before or now < self._clock:
            self.start(now);return
        self._paused = False
        before = max(before,self._clock)
        self._clock = now
        if now >= SEQUENCE_END:
            self._maintain();return
        # Large seeks re-phase loops; ordinary clip transitions retain leases.
        if now-before > .35:
            for name,_ in LOOPS:self._release(name)
        self._maintain();self._ensure_loops()
        for name,at,duration in TRANSIENTS:
            if before < at <= now and name not in self._seen:
                self._seen.add(name)
                if now-before <= .35 and now < at+duration:
                    self._play(name,offset=now-at,ends_at=at+duration)
        for cue in self.run_contacts:
            at = cue['time']
            if before < at <= now and cue['id'] not in self._seen:
                self._seen.add(cue['id'])
                if now-before <= .35 and now < at+cue['duration']:
                    self._play_step(cue,now-at)
        self._maintain()

    def refresh_volume(self):
        self._maintain();self._ensure_loops();self._maintain()

    def pause(self):
        self._paused = True;self._maintain()

    def resume(self):
        self._paused = False;self._maintain();self._ensure_loops();self._maintain()

    def stop(self):
        self._active = False
        for name in list(self.voices):self._release(name)

    def reset(self):
        self.stop();self.events.clear();self._seen.clear()
        self._clock = 0.;self._paused = False


def mix_alert_audio(start_seconds,duration,*,sample_rate=48000,asset_root=ASSETS,run_timing=None):
    """Reconstruct effects from production exports for review movies.

    This is an offline reconstruction, not a recording of mixer hardware.
    Uses the same gains, pan, source phase and clip offsets as the live owner.
    """
    import numpy as np
    if (not math.isfinite(start_seconds) or not math.isfinite(duration)
            or min(start_seconds,duration) < 0 or sample_rate <= 0):
        raise ValueError('Invalid prologue audio capture interval')
    count = round(duration*sample_rate)
    times = start_seconds+np.arange(count)/sample_rate
    result = np.zeros((count,2),dtype=np.float64)
    travel = np.clip(times-RUSH_START,0,1);travel = travel*travel*(3-2*travel)
    active = (times>=MACHINERY_START)&(times<SEQUENCE_END)
    tracks = (
        ('machinery_bed.wav',.12-.105*travel,.08*(1-travel),MACHINERY_START,True),
        ('industrial_siren.wav',.34*(1-travel),.12*(1-2*travel),ALARM_START,True),
        ('distant_siren.wav',.115*travel,np.full(count,-.12),ALARM_START,True),
        ('bridge_rush.wav',np.full(count,.53),-.1+.2*travel,RUSH_START,False),
        ('ice_settle.wav',np.full(count,.20),np.full(count,.14),BRIDGE_ARRIVAL,False))
    for name,gain,pan,at,loop in tracks:
        with wave.open(str(Path(asset_root)/name),'rb') as reader:
            rate,channels,width = reader.getframerate(),reader.getnchannels(),reader.getsampwidth()
            if channels != 2 or width != 2:raise ValueError('Expected stereo PCM16 prologue effects')
            sound = np.frombuffer(reader.readframes(reader.getnframes()),dtype='<i2').reshape(-1,2)/32767.
        positions = np.rint((times-at)*rate).astype(np.int64)
        mask = active&(times>=at)
        if loop:positions %= len(sound)
        else:mask &= positions<len(sound)
        positions = np.clip(positions,0,len(sound)-1)
        level = np.column_stack((gain*np.minimum(1,1-pan),gain*np.minimum(1,1+pan)))
        result[mask] += sound[positions[mask]]*level[mask]
    # Integer output-frame positions make isolated clips sample-identical to
    # the same interval sliced from the complete film, including contact edges.
    output_frames = round(start_seconds*sample_rate)+np.arange(count)
    steps = {}
    contacts = (running_contact_events(run_timing)
                if start_seconds < SEQUENCE_END and start_seconds+duration > RUNNING_START else ())
    for cue in contacts:
        key = cue['file']
        if key not in steps:
            with wave.open(str(Path(asset_root)/key),'rb') as reader:
                rate,channels,width = reader.getframerate(),reader.getnchannels(),reader.getsampwidth()
                if channels != 2 or width != 2:raise ValueError('Expected stereo PCM16 running Foley')
                sound = np.frombuffer(reader.readframes(reader.getnframes()),dtype='<i2').reshape(-1,2)/32767.
                steps[key] = rate,sound
        rate,sound = steps[key]
        positions = np.rint((output_frames-round(cue['time']*sample_rate))*rate/sample_rate).astype(np.int64)
        mask = active&(positions>=0)&(positions<len(sound))
        gain,pan = cue['gain'],cue['pan']
        level = np.array((gain*min(1,1-pan),gain*min(1,1+pan)))
        result[mask] += sound[positions[mask]]*level
    return result.astype(np.float32)
