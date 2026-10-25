"""Quiet morning ambience and diegetic cues for the sanctuary opening."""
from array import array
import math
import random

import pygame


class MorningAudio:
    """Own only the channels returned by this controller's sounds.

    These are distant world sounds, not a score. No global music controls or
    reserved channels are used, and synthesis never consumes an NPC's RNG.
    """
    EARLY_STAGES = frozenset(('wake', 'explore', 'breakfast'))
    LEVELS = {'stream': .13, 'bell': .14, 'knock': .18, 'birds': .09,
              'bedsheet': .16, 'footstep': .15, 'chair': .13,
              'plate': .14, 'bite': .075, 'cup': .13}
    EVENT_ALIASES = {'cloth': 'bedsheet', 'bed': 'bedsheet',
                     'chair_pull': 'chair', 'chair_sit': 'chair',
                     'chair_stand': 'chair', 'plate_contact': 'plate',
                     'cup_contact': 'cup'}

    def __init__(self, game):
        self.game = game
        self._sounds = {}
        self._channels = []
        self._fading_channels = []
        self._stream_channel = None
        self._wake_played = False
        self._elapsed = 0.0
        self._next_bird = 3.8
        self._bird_count = 0
        self._audio_failed = False
        self._paused = False
        self._ambient_active = False
        self._last_volume = None

    def _effects_volume(self):
        settings = getattr(self.game, 'audio', None)
        if settings is not None:
            return max(0.0, min(1.0, float(settings.effects_volume)))
        return float(getattr(getattr(self.game, 'title', None), 'music_enabled', True))

    def _refresh_volume(self):
        volume = self._effects_volume()
        if volume != self._last_volume:
            for (name, *_), sound in self._sounds.items():
                sound.set_volume(self.LEVELS[name]*volume)
            self._last_volume = volume
        return volume

    def _stop(self, gentle=False):
        owned = self._channels if gentle else self._channels+self._fading_channels
        for channel, sound in owned:
            try:
                # A finished cue's free channel may now belong to a quest sound.
                if channel.get_sound() is sound:
                    if gentle:
                        channel.fadeout(250)
                        self._fading_channels.append((channel, sound))
                    else:channel.stop()
            except pygame.error:
                pass
        self._channels.clear()
        if not gentle:self._fading_channels.clear()
        self._stream_channel = None

    def reset(self):
        self._stop()
        self._wake_played = False
        self._elapsed = 0.0
        self._next_bird = 3.8
        self._bird_count = 0
        self._audio_failed = False
        self._paused = False
        self._ambient_active = False

    def prepare(self):
        """Cache PCM during the title transition without playing any cues."""
        if self._refresh_volume() <= 0:return False
        spec = self._spec()
        if spec is None:return False
        try:
            for name in self.LEVELS:
                self._sound(name, spec)
            return True
        except (pygame.error, OSError):
            self._audio_failed = True
            return False

    def set_paused(self, paused):
        """Freeze only channels still playing this controller's own sounds."""
        volume = self._refresh_volume()
        paused = bool(paused)
        if volume <= 0:
            self._stop()
        if paused == self._paused:return
        self._paused = paused
        for channel, sound in self._channels+self._fading_channels:
            try:
                if channel.get_sound() is sound:
                    if paused:channel.pause()
                    else:channel.unpause()
            except pygame.error:
                pass

    def _spec(self):
        if self._audio_failed:return None
        try:
            if not pygame.mixer.get_init():pygame.mixer.init()
            spec = pygame.mixer.get_init()
            if not spec or spec[1] != -16 or not 1 <= spec[2] <= 8:
                self._audio_failed = True
                return None
            return spec[0], spec[2]
        except (pygame.error, OSError):
            self._audio_failed = True
            return None

    @staticmethod
    def _samples(name, rate, channels):
        durations = {'stream': 2.0, 'bell': 1.8, 'knock': .95, 'birds': .55,
                     'bedsheet': .25, 'footstep': .14, 'chair': .32,
                     'plate': .20, 'bite': .12, 'cup': .20}
        count = round(rate*durations[name])
        samples = array('h')
        rng = random.Random(6813)
        if name == 'stream':
            # Crossfade one continuous filtered-noise segment back into itself.
            # At the loop boundary its samples remain adjacent in the source,
            # rather than jumping between two unrelated noise values.
            fade = max(1, round(rate*.12))
            values = []
            low = 0.0
            for _ in range(count+fade):
                white = rng.uniform(-1, 1)
                low += .18*(white-low)
                values.append(4600*(.65*low+.18*white))
            for i in range(count):
                if i < fade:
                    blend = .5-.5*math.cos(math.pi*i/fade)
                    value = values[count+i]*(1-blend)+values[i]*blend
                else:value = values[i]
                samples.extend([round(value)]*channels)
            return samples
        for i in range(count):
            t = i/rate
            value = 0.0
            if name == 'bell':
                attack = min(1.0, t/.025)
                release = min(1.0, (1.8-t)/.12)
                envelope = attack*release*math.exp(-3.3*t)
                partials = (math.sin(2*math.pi*440*t)+
                            .44*math.sin(2*math.pi*1213*t)+
                            .18*math.sin(2*math.pi*1808*t))
                value = 9000*envelope*partials/1.62
            elif name == 'knock':
                for onset in (.42, .66):
                    local = t-onset
                    if 0 <= local < .16:
                        envelope = min(1.0, local/.003)*math.exp(-38*local)
                        resonances = (.60*math.sin(2*math.pi*185*local)+
                                      .25*math.sin(2*math.pi*92*local)+
                                      .15*rng.uniform(-1, 1))
                        value += 13000*envelope*resonances
            elif name == 'birds':
                for onset in (0, .23):
                    local = t-onset
                    if 0 <= local < .17:
                        envelope = math.sin(math.pi*local/.17)**2
                        phase = 2*math.pi*(1800*local+2100*local*local)
                        value += 7200*envelope*math.sin(phase)
            elif name in ('plate', 'cup'):
                # A small damped ceramic contact, softened to avoid a UI beep.
                duration = durations[name]
                attack = min(1.0, t/.003)
                release = min(1.0, (duration-t)/.025)
                frequency = 1430 if name == 'plate' else 1180
                value = (4800*attack*release*math.exp(-32*t)*
                         (math.sin(2*math.pi*frequency*t)+
                          .24*math.sin(2*math.pi*frequency*2.61*t)))
            elif name == 'chair':
                envelope = math.sin(math.pi*t/durations[name])**2
                creak = (math.sin(2*math.pi*(105*t+85*t*t))+
                         .28*math.sin(2*math.pi*265*t))
                value = 3900*envelope*(.78*creak+.22*rng.uniform(-1, 1))
            elif name == 'footstep':
                envelope = min(1.0, t/.008)*math.exp(-35*t)
                release = min(1.0, (durations[name]-t)/.025)
                value = 6700*envelope*release*(
                    .74*math.sin(2*math.pi*125*t)+.26*rng.uniform(-1, 1))
            elif name in ('bedsheet', 'bite'):
                duration = durations[name]
                envelope = math.sin(math.pi*t/duration)**2
                texture = rng.uniform(-1, 1)
                if name == 'bite':
                    texture *= math.exp(-12*t)
                value = (2300 if name == 'bedsheet' else 1600)*envelope*texture
            samples.extend([max(-32767, min(32767, round(value)))]*channels)
        return samples

    def _sound(self, name, spec):
        key = (name, *spec)
        if key not in self._sounds:
            sound = pygame.mixer.Sound(buffer=self._samples(name, *spec))
            sound.set_volume(self.LEVELS[name]*self._effects_volume())
            self._sounds[key] = sound
        return self._sounds[key]

    def _play(self, name, spec, **options):
        sound = self._sound(name, spec)
        channel = sound.play(**options)
        if channel is not None:self._channels.append((channel, sound))
        return channel

    def update(self, seconds):
        volume = self._refresh_volume()
        if self._paused:
            if volume <= 0:self._stop()
            return
        opening = getattr(self.game, 'opening', None)
        drain = getattr(opening, 'drain_sound_events', None)
        events = drain() if callable(drain) else []
        cues = [self.EVENT_ALIASES.get(event, event) for event in events
                if isinstance(event, str)]
        cues = [name for name in cues if name in self.LEVELS]
        stage = getattr(getattr(self.game, 'opening', None), 'stage', 'disabled')
        if volume <= 0 or getattr(self.game, 'on_title', False):
            # Muted actions are consumed now rather than replayed on unmute.
            if stage == 'wake':self._wake_played = True
            self._stop(gentle=True)
            self._ambient_active = False
            return
        early = stage in self.EARLY_STAGES
        if not early:
            if self._ambient_active:self._stop(gentle=True)
            self._ambient_active = False
            if not cues:return
        spec = self._spec()
        if spec is None:return
        try:
            # Drop channel references after a cue finishes or another sound
            # reuses that channel. Reset must never stop somebody else's audio.
            self._channels = [(channel, sound) for channel, sound in self._channels
                              if channel.get_sound() is sound]
            self._fading_channels = [(channel, sound) for channel, sound in self._fading_channels
                                     if channel.get_sound() is sound]
            for name in cues:
                self._play(name, spec)
            if early:
                self._ambient_active = True
                stream = self._sound('stream', spec)
                if self._stream_channel is None or self._stream_channel.get_sound() is not stream:
                    self._stream_channel = self._play('stream', spec, loops=-1, fade_ms=600)
            if stage == 'wake' and not self._wake_played:
                self._wake_played = True
                self._play('bell', spec)
                self._play('knock', spec)
            if early:self._elapsed += max(0.0, seconds)
            if early and self._elapsed >= self._next_bird:
                self._play('birds', spec)
                self._bird_count += 1
                self._next_bird = self._elapsed+6.8+(self._bird_count % 3)*1.6
        except (pygame.error, OSError):
            self._audio_failed = True
            self._stop()
