"""Finite, animation-timed bird sounds owned by the arrival cinematic."""
from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path

import pygame


ROOT = Path(__file__).resolve().parent
ASSETS = ROOT/'assets/audio/sfx/regent_aerial'
BIRD_MANIFEST = ROOT/'assets/story/regent_aerial/actors/bird/animation.json'
FILES = {'hawk_call': 'hawk_call.ogg', 'wing_flap': 'wing_flap.ogg'}
GAINS = {'hawk_call': .4, 'wing_flap': .12}
CALL_TIMES = (2.4, 13.2)


@dataclass
class _Voice:
    channel: object
    sound: object
    gain: float
    ends_at: float


class RegentAerialAudio:
    """Follow the visible bird's animation clock without advancing it.

    A wing sound begins at the first downstroke frame of the authored loop.
    Pausing freezes scheduling and owned channels; seeking or a long frame
    discards missed cues instead of replaying a backlog. Sound effects never
    borrow the soundtrack or another controller's live channel.
    """

    def __init__(self, game, *, asset_root=ASSETS, bird_manifest=BIRD_MANIFEST,
                 mixer=None):
        self.game = game
        self.asset_root = Path(asset_root)
        self.mixer = pygame.mixer if mixer is None else mixer
        frames = json.loads(Path(bird_manifest).read_text())['loops']['flap_north']
        durations = [frame['duration_ms']/1000 for frame in frames]
        if (len(durations) < 4 or
                any(not math.isfinite(value) or value <= 0 for value in durations)):
            raise ValueError('Bird wingbeat requires positive downstroke frame timing')
        self.flap_period = sum(durations)
        self.downstroke = sum(durations[:3])
        self.sounds = {}
        self.voices = {}
        self._last_seconds = None
        self._seen_calls = set()
        self._paused = False
        if hasattr(game.audio, 'bind_effects'):
            game.audio.bind_effects(self)

    def _sound(self, name):
        spec = self.mixer.get_init()
        if not spec:return None
        key = (name, spec)
        if key not in self.sounds:
            try:
                self.sounds[key] = self.mixer.Sound(str(self.asset_root/FILES[name]))
            except (OSError, pygame.error):
                return None
        return self.sounds[key]

    def _stop_voices(self):
        for voice in self.voices.values():
            try:
                if voice.channel.get_sound() is voice.sound:voice.channel.stop()
            except pygame.error:
                pass
        self.voices.clear()

    def stop(self):
        """Release only this scene's channels; consumed cues stay consumed."""
        self._stop_voices()

    def reset(self):
        """Prepare a fresh playback, including a Gallery restart."""
        self.stop()
        self._last_seconds = None
        self._seen_calls.clear()
        self._paused = False

    def _maintain(self, clock, paused):
        volume = float(self.game.audio.effects_volume)
        for name, voice in list(self.voices.items()):
            try:
                if voice.channel.get_sound() is not voice.sound:
                    del self.voices[name]
                    continue
                if volume <= 0 or (not paused and clock >= voice.ends_at):
                    voice.channel.stop()
                    del self.voices[name]
                    continue
                voice.channel.set_volume(voice.gain*volume)
                if paused:voice.channel.pause()
                else:voice.channel.unpause()
            except pygame.error:
                self.voices.pop(name, None)

    def refresh_volume(self):
        """Apply the effects slider immediately, including while paused."""
        self._maintain(self._last_seconds or 0., self._paused)

    @staticmethod
    def _bird_state(snapshot):
        bird = snapshot['bird']
        x,y = bird['screen_xy']
        visible = bool(bird.get('visible', -40 < x < 520 and -40 < y < 360))
        visible &= not snapshot.get('ground_handoff', False)
        visible &= not snapshot.get('canopy', {}).get('full_occlusion', False)
        flapping = bool(bird.get('flapping', abs(bird.get('bank', 0.)) <= 10))
        return visible, flapping

    def _play(self, name):
        if name in self.voices or float(self.game.audio.effects_volume) <= 0:return False
        try:
            sound = self._sound(name)
            if sound is None:return False
            channel = self.mixer.find_channel()
            if channel is None:return False
            gain = GAINS[name]
            channel.set_volume(gain*float(self.game.audio.effects_volume))
            channel.play(sound, loops=0)
            self.voices[name] = _Voice(channel, sound, gain,
                                       self._last_seconds+sound.get_length())
            return True
        except (OSError, pygame.error):
            return False

    def update(self, seconds, snapshot, *, paused=False):
        """Use the snapshot clock also passed to the bird's animated draw."""
        self._paused = bool(paused)
        if snapshot is None:
            self.stop()
            return
        clock = float(snapshot['seconds'])
        if not math.isfinite(clock):
            self.stop()
            return
        if paused:
            self._maintain(self._last_seconds or clock, True)
            return
        if self._last_seconds is not None and clock < self._last_seconds:
            self.reset()
        previous = self._last_seconds
        self._last_seconds = clock
        self._maintain(clock, False)
        visible, flapping = self._bird_state(snapshot)
        if not visible:self.stop()
        if previous is None:
            self._seen_calls.update(cue for cue in CALL_TIMES if cue <= clock)
            return

        # Consume every missed call even while muted, banking or offscreen.
        # Only a timely, visible cue from an ordinary frame can become audible.
        due = [cue for cue in CALL_TIMES if previous < cue <= clock
               and cue not in self._seen_calls]
        self._seen_calls.update(due)
        if (not visible or float(self.game.audio.effects_volume) <= 0
                or clock-previous > .35):
            return
        if due and clock-due[-1] <= .25:self._play('hawk_call')
        before = math.floor((previous-self.downstroke)/self.flap_period)
        now = math.floor((clock-self.downstroke)/self.flap_period)
        contact = now*self.flap_period+self.downstroke
        if flapping and now > before and clock-contact <= .15:
            self._play('wing_flap')
