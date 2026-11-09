"""Original, quiet reward cues on leased effects channels, never the score.

The short ascending counting ticks and soft four-note level-up bell are
generated from sine partials. No uploaded music or third-party recordings are
used. Only channels still playing this instance's sounds may be controlled.
"""
from __future__ import annotations

from array import array
import math

import pygame


DURATIONS = {'fill': .36, 'level_up': .88}
GAINS = {'fill': .16, 'level_up': .38}


def _samples(cue, rate, channels):
    """Make signed 16-bit PCM at the device's native rate and channel count."""
    if cue == 'fill':
        notes = ((0., 659.255, .085, .28), (.12, 739.989, .085, .28),
                 (.24, 830.609, .085, .28))
    else:
        notes = ((0., 523.251, .27, .30), (.09, 659.255, .28, .28),
                 (.18, 783.991, .32, .27), (.30, 1046.502, .55, .34))
    result = array('h')
    for index in range(round(rate * DURATIONS[cue])):
        t = index / rate
        value = 0.
        for start, frequency, duration, strength in notes:
            age = t - start
            if not 0 <= age < duration:
                continue
            envelope = min(1., age / .004, (duration - age) / .025)
            envelope *= math.exp(-age * (22 if cue == 'fill' else 5))
            phase = 2 * math.pi * frequency * age
            value += strength * envelope * (math.sin(phase)
                                            + .12 * math.sin(phase * 2)
                                            + .035 * math.sin(phase * 4))
        sample = round(max(-1., min(1., value)) * 32767)
        result.extend((sample,) * channels)
    return result


class SpoilsAudio:
    """A bounded fill loop and one-shot bell, independent of music settings.

    Muting drops one-shots and stops their channels. Unmuting may resume an
    ongoing fill animation, but never queues or replays an old level-up cue.
    """

    def __init__(self, game, *, mixer=None):
        self.game = game
        self._mixer = pygame.mixer if mixer is None else mixer
        self._sounds = {}
        self._fill = None
        self._voices = []
        self._fill_requested = False
        self._paused = False
        settings = getattr(game, 'audio', None)
        if settings is not None and hasattr(settings, 'bind_effects'):
            settings.bind_effects(self)

    def _volume(self):
        value = getattr(getattr(self.game, 'audio', None), 'effects_volume', 0.)
        if type(value) not in (int, float) or not math.isfinite(value):
            return 0.
        return max(0., min(1., value))

    @staticmethod
    def _owned(voice):
        if voice is None:
            return False
        channel, sound, _ = voice
        try:
            return channel.get_sound() is sound and channel.get_busy()
        except pygame.error:
            return False

    def _prune(self):
        self._voices = [voice for voice in self._voices if self._owned(voice)]
        if not self._owned(self._fill):
            self._fill = None

    def _sound(self, cue):
        if not self._mixer.get_init():
            self._mixer.init()
        spec = self._mixer.get_init()
        if not spec or spec[1] != -16:
            return None
        rate, _, channels = spec
        key = cue, tuple(spec)
        if key not in self._sounds:
            self._sounds[key] = self._mixer.Sound(buffer=_samples(cue, rate, channels))
        return self._sounds[key]

    def _play(self, cue):
        if self._paused or self._volume() <= 0:
            return None
        try:
            sound = self._sound(cue)
            if sound is None:
                return None
            # No force flag: a level-up cue must never steal combat or UI FX.
            channel = self._mixer.find_channel()
            if channel is None:
                return None
            channel.set_volume(GAINS[cue] * self._volume())
            channel.play(sound, loops=-1 if cue == 'fill' else 0,
                         fade_ms=24 if cue == 'fill' else 5)
            return channel, sound, cue
        except (pygame.error, OSError):
            return None

    def start_fill(self):
        self._fill_requested = True
        self._prune()
        if self._fill is None:
            self._fill = self._play('fill')

    def stop_fill(self):
        self._fill_requested = False
        if self._owned(self._fill):
            try:
                self._fill[0].fadeout(40)
                self._voices.append(self._fill)
            except pygame.error:
                pass
        self._fill = None
        self._prune()

    def level_up(self):
        self.stop_fill()
        voice = self._play('level_up')
        if voice is not None:
            self._voices.append(voice)

    def set_paused(self, paused):
        paused = bool(paused)
        if self._paused == paused:
            return
        self._paused = paused
        self._prune()
        for voice in ([self._fill] if self._fill is not None else []) + self._voices:
            try:
                if paused:
                    voice[0].pause()
                elif self._volume() > 0:
                    voice[0].unpause()
            except pygame.error:
                pass
        if not paused:
            self.refresh_volume()

    def refresh_volume(self):
        self._prune()
        volume = self._volume()
        voices = ([self._fill] if self._fill is not None else []) + self._voices
        for channel, _, cue in voices:
            try:
                if volume <= 0:
                    channel.stop()
                else:
                    channel.set_volume(GAINS[cue] * volume)
            except pygame.error:
                pass
        if volume <= 0:
            self._fill = None
            self._voices.clear()
        elif self._fill_requested and not self._paused and self._fill is None:
            self._fill = self._play('fill')

    def stop(self):
        """Release only owned voices; future volume changes cannot restart them."""
        self._fill_requested = False
        self._prune()
        for channel, _, _ in ([self._fill] if self._fill is not None else []) + self._voices:
            try:
                channel.stop()
            except pygame.error:
                pass
        self._fill = None
        self._voices.clear()
