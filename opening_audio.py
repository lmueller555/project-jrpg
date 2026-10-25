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
        durations = {'stream': 2.0, 'bell': 1.8, 'knock': .95, 'birds': .55}
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
            samples.extend([max(-32767, min(32767, round(value)))]*channels)
        return samples

    def _sound(self, name, spec):
        key = (name, *spec)
        if key not in self._sounds:
            sound = pygame.mixer.Sound(buffer=self._samples(name, *spec))
            sound.set_volume({'stream': .13, 'bell': .14, 'knock': .18, 'birds': .09}[name])
            self._sounds[key] = sound
        return self._sounds[key]

    def _play(self, name, spec, **options):
        sound = self._sound(name, spec)
        channel = sound.play(**options)
        if channel is not None:self._channels.append((channel, sound))
        return channel

    def update(self, seconds):
        stage = getattr(getattr(self.game, 'opening', None), 'stage', 'disabled')
        enabled = getattr(getattr(self.game, 'title', None), 'music_enabled', True)
        if not enabled or stage not in self.EARLY_STAGES or getattr(self.game, 'on_title', False):
            self._stop(gentle=True)
            return
        spec = self._spec()
        if spec is None:return
        try:
            # Drop channel references after a cue finishes or another sound
            # reuses that channel. Reset must never stop somebody else's audio.
            self._channels = [(channel, sound) for channel, sound in self._channels
                              if channel.get_sound() is sound]
            stream = self._sound('stream', spec)
            if self._stream_channel is None or self._stream_channel.get_sound() is not stream:
                self._stream_channel = self._play('stream', spec, loops=-1, fade_ms=600)
            if stage == 'wake' and not self._wake_played:
                self._wake_played = True
                self._play('bell', spec)
                self._play('knock', spec)
            self._elapsed += max(0.0, seconds)
            if self._elapsed >= self._next_bird:
                self._play('birds', spec)
                self._bird_count += 1
                self._next_bird = self._elapsed+6.8+(self._bird_count % 3)*1.6
        except (pygame.error, OSError):
            self._audio_failed = True
            self._stop()
