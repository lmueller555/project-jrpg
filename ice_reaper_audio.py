"""Finite, animation-timed action effects owned by the Ice Reaper preview."""
from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path

import pygame

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / 'assets/audio/sfx/ice_reaper_rescue'

# Absolute cinematic seconds; music remains on its own real-time clock.
CUES = (
    {'id': 'caelan_dash', 'time': 7.00, 'file': 'assets/audio/sfx/ice_reaper_rescue/snow_dash.ogg', 'gain': .47},
    {'id': 'lucan_dash', 'time': 7.15, 'file': 'assets/audio/sfx/ice_reaper_rescue/snow_dash.ogg', 'gain': .43},
    {'id': 'fire_slash', 'time': 8.30, 'file': 'assets/audio/sfx/ice_reaper_rescue/flame_slash.ogg', 'gain': .49},
    {'id': 'prison_crack', 'time': 8.50, 'file': 'assets/audio/sfx/ice_reaper_rescue/prison_crack.ogg', 'gain': .40},
    {'id': 'shield_impact', 'time': 9.00, 'file': 'assets/audio/sfx/ice_reaper_rescue/shield_impact.ogg', 'gain': .60},
    {'id': 'load_shell', 'time': 11.50, 'file': 'assets/audio/sfx/ice_reaper_rescue/load_shell.ogg', 'gain': .37},
    {'id': 'close_breech', 'time': 12.20, 'file': 'assets/audio/sfx/ice_reaper_rescue/close_breech.ogg', 'gain': .42},
    {'id': 'launcher_fire', 'time': 14.20, 'file': 'assets/audio/sfx/ice_reaper_rescue/launcher_fire.ogg', 'gain': .57},
    {'id': 'shard_explosion', 'time': 14.70, 'file': 'assets/audio/sfx/ice_reaper_rescue/shard_explosion.ogg', 'gain': .54},
    {'id': 'ice_creak', 'time': 15.45, 'file': 'assets/audio/sfx/ice_reaper_rhea_closeup/ice_creak.ogg', 'gain': .12},
    {'id': 'awakening', 'time': 16.60, 'file': 'assets/audio/sfx/ice_reaper_rescue/awakening.ogg', 'gain': .34},
    {'id': 'prison_burst', 'time': 17.30, 'file': 'assets/audio/sfx/ice_reaper_rescue/prison_burst.ogg', 'gain': .58},
    {'id': 'rune_bloom', 'time': 17.50, 'file': 'assets/audio/sfx/ice_reaper_rescue/rune_bloom.ogg', 'gain': .43},
    {'id': 'staff_sweep', 'time': 24.00, 'file': 'assets/audio/sfx/ice_reaper_duel/staff_sweep.ogg', 'gain': .34},
    {'id': 'wind_burst', 'time': 24.10, 'file': 'assets/audio/sfx/ice_reaper_duel/wind_burst.ogg', 'gain': .47},
    {'id': 'caelan_lands', 'time': 25.05, 'file': 'assets/audio/sfx/ice_reaper_duel/caelan_lands.ogg', 'gain': .34},
    {'id': 'lucan_lands', 'time': 25.15, 'file': 'assets/audio/sfx/ice_reaper_duel/lucan_lands.ogg', 'gain': .37},
    {'id': 'ice_sword_forms', 'time': 25.72, 'file': 'assets/audio/sfx/ice_reaper_duel/ice_sword_forms.ogg', 'gain': .31},
    {'id': 'fireball_1', 'time': 25.80, 'file': 'assets/audio/sfx/ice_reaper_duel/fireball_ignite.ogg', 'gain': .14},
    {'id': 'fireball_2', 'time': 25.95, 'file': 'assets/audio/sfx/ice_reaper_duel/fireball_ignite.ogg', 'gain': .14},
    {'id': 'fireball_3', 'time': 26.10, 'file': 'assets/audio/sfx/ice_reaper_duel/fireball_ignite.ogg', 'gain': .14},
    {'id': 'fireball_4', 'time': 26.25, 'file': 'assets/audio/sfx/ice_reaper_duel/fireball_ignite.ogg', 'gain': .14},
    {'id': 'fireball_5', 'time': 26.40, 'file': 'assets/audio/sfx/ice_reaper_duel/fireball_ignite.ogg', 'gain': .14},
    {'id': 'fireball_6', 'time': 26.55, 'file': 'assets/audio/sfx/ice_reaper_duel/fireball_ignite.ogg', 'gain': .14},
    {'id': 'fire_presence', 'time': 26.70, 'file': 'assets/audio/sfx/ice_reaper_duel/fire_presence.ogg', 'gain': .115},
    {'id': 'sword_windup', 'time': 29.55, 'file': 'assets/audio/sfx/ice_reaper_duel/sword_windup.ogg', 'gain': .31},
    {'id': 'charge_launch', 'time': 30.30, 'file': 'assets/audio/sfx/ice_reaper_duel/charge_launch.ogg', 'gain': .52},
)


@dataclass
class _Voice:
    channel: object
    sound: object
    gain: float
    ends_at: float


class IceReaperActionAudio:
    """One-shot effects with explicit channel ownership and pause/focus support.

    ``update`` receives the scene's previous/current absolute seconds. Crossing a
    cue during ordinary playback emits it once. Seeks and long stalls consume
    missed cues silently, so resumed playback never emits an effect backlog.
    No operation changes the soundtrack or another controller's sounds.
    """
    def __init__(self, game, *, asset_root=ASSETS, mixer=None):
        self.game = game
        self.asset_root = Path(asset_root)
        self.mixer = pygame.mixer if mixer is None else mixer
        self.sounds = {}
        self.voices = {}
        self._seen = set()
        self._paused = False
        self._clock = 0.
        self.events = []
        if hasattr(game.audio, 'bind_effects'):
            game.audio.bind_effects(self)
        # Decode before the action; a missing mixer remains a silent no-op.
        for cue in CUES:
            self._sound(cue)

    @property
    def volume(self):
        return max(0., min(1., float(getattr(self.game.audio, 'effects_volume', 0.))))

    def _sound(self, cue):
        spec = self.mixer.get_init()
        if not spec:
            return None
        relative = Path(cue['file'])
        folder = self.asset_root if relative.parent.name == ASSETS.name else self.asset_root.parent/relative.parent.name
        path = folder/relative.name
        key = (path, spec)
        if key not in self.sounds:
            try:
                self.sounds[key] = self.mixer.Sound(str(path))
            except (OSError, pygame.error):
                return None
        return self.sounds[key]

    def _maintain(self):
        for identifier, voice in list(self.voices.items()):
            try:
                if voice.channel.get_sound() is not voice.sound:
                    self.voices.pop(identifier, None)
                    continue
                if self.volume <= 0 or (not self._paused and self._clock >= voice.ends_at):
                    voice.channel.stop()
                    self.voices.pop(identifier, None)
                    continue
                voice.channel.set_volume(voice.gain*self.volume)
                if self._paused:
                    voice.channel.pause()
                else:
                    voice.channel.unpause()
            except pygame.error:
                self.voices.pop(identifier, None)

    def refresh_volume(self):
        self._maintain()

    def _play(self, cue):
        if self.volume <= 0:
            return
        try:
            sound = self._sound(cue)
            channel = self.mixer.find_channel() if sound is not None else None
            if channel is None:
                return
            channel.set_volume(cue['gain']*self.volume)
            channel.play(sound, loops=0)
            self.voices[cue['id']] = _Voice(channel, sound, cue['gain'],
                                          self._clock+sound.get_length())
            self.events.append({'id': cue['id'], 'time': self._clock})
        except (OSError, pygame.error):
            return

    def update(self, previous_elapsed, elapsed, playing=True):
        try:
            before, now = float(previous_elapsed), float(elapsed)
        except (TypeError, ValueError):
            self.stop()
            return
        if not math.isfinite(before) or not math.isfinite(now):
            self.stop()
            return
        if not playing:
            self.pause()
            return
        if now < before or now < self._clock:
            self.reset()
            self._seen.update(cue['id'] for cue in CUES if cue['time'] <= now)
        self._clock = now
        self._paused = False
        self._maintain()
        due = [cue for cue in CUES if before < cue['time'] <= now and cue['id'] not in self._seen]
        self._seen.update(cue['id'] for cue in due)
        if now-before > .35:
            return
        for cue in due:
            self._play(cue)

    def pause(self):
        self._paused = True
        self._maintain()

    def resume(self):
        self._paused = False
        self._maintain()

    def stop(self):
        for voice in self.voices.values():
            try:
                if voice.channel.get_sound() is voice.sound:
                    voice.channel.stop()
            except pygame.error:
                pass
        self.voices.clear()

    def reset(self):
        self.stop()
        self._seen.clear()
        self.events.clear()
        self._clock = 0.
        self._paused = False
