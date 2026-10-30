"""One streamed soundtrack shared by the title, exploration and encounters.

Track changes use a short, nonblocking fade-out/fade-in. Requests for the same
track preserve playback, including the title-to-Eldenmere handoff. Only music
is controlled here; environmental effects and UI cues keep their own channels.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import weakref

import pygame


ROOT = Path(__file__).resolve().parent
MUSIC_ROOT = ROOT / 'assets/music'


class GameMusic:
    _owners = weakref.WeakKeyDictionary()

    def __init__(self, game, *, catalog=None, music_root=MUSIC_ROOT, mixer=None):
        self.game = game
        self._mixer = pygame.mixer if mixer is None else mixer
        self.music_root = Path(music_root)
        self.error = None
        self.tracks = self._catalog(catalog)
        self.current_track = None
        self.desired_track = None
        self._loaded = False
        self._failed = False
        self._paused = False
        self._stream_paused = False
        self._duck = self._duck_target = 1.0
        self._envelope = 1.0
        self._fade_mode = None
        self._fade_duration = self._fade_remaining = 0.0
        self._fade_start = 1.0
        self._requested_fade = .45
        settings = getattr(game, 'audio', None)
        if settings is not None and hasattr(settings, 'bind_music'):
            settings.bind_music(self)

    def _catalog(self, catalog):
        try:
            if catalog is None:
                catalog = json.loads((self.music_root / 'tracks.json').read_text(encoding='utf-8'))
            if not isinstance(catalog, dict) or catalog.get('version') != 1:
                raise ValueError('Unsupported music catalog')
            records = catalog['tracks']
            if not isinstance(records, dict):
                raise ValueError('Invalid music catalog')
            result = {}
            for identifier, record in records.items():
                filename, gain = record['file'], record.get('gain', .45)
                if (not isinstance(identifier, str) or not isinstance(filename, str)
                        or type(gain) not in (int, float) or not math.isfinite(gain)
                        or not 0 <= gain <= 1):
                    raise ValueError('Invalid music track')
                path = (self.music_root / filename).resolve()
                if not path.is_relative_to(self.music_root.resolve()):
                    raise ValueError('Music path escapes its folder')
                result[identifier] = {'path': path, 'gain': float(gain)}
            return result
        except (OSError, ValueError, KeyError, TypeError) as error:
            self.error = str(error)
            return {}

    @property
    def playing(self):
        if not self._loaded or not self._owns_stream() or self._stream_paused:
            return False
        try:
            return bool(self._mixer.get_init() and self._mixer.music.get_busy())
        except (pygame.error, OSError):
            return False

    @property
    def paused(self):
        return self._paused

    def _owns_stream(self):
        owner = self._owners.get(self._mixer)
        return owner is not None and owner() is self

    def _claim_stream(self):
        owner = self._owners.get(self._mixer)
        previous = owner() if owner is not None else None
        if previous is not None and previous is not self:
            # Old previews/games must not stop a newer game's global stream.
            previous._loaded = False
            previous.current_track = None
            previous._fade_mode = None
            previous._failed = True
        self._owners[self._mixer] = weakref.ref(self)

    def _volume(self):
        try:
            value = float(self.game.audio.music_volume)
            return max(0.0, min(1.0, value)) if math.isfinite(value) else 0.0
        except (AttributeError, ValueError, TypeError, OverflowError):
            return 0.0

    def _ready(self):
        try:
            if not self._mixer.get_init():
                self._mixer.init()
            return bool(self._mixer.get_init())
        except (pygame.error, OSError) as error:
            self.error = str(error)
            self._failed = True
            return False

    def _clear_current(self):
        if self._owns_stream():
            try:
                if self._mixer.get_init():
                    self._mixer.music.stop()
            except (pygame.error, OSError):
                pass
            self._owners.pop(self._mixer, None)
        self.current_track = None
        self._loaded = False
        self._stream_paused = False
        self._fade_mode = None
        self._fade_remaining = 0.0

    def _start(self, identifier, fade):
        if self._volume() <= 0 or self._failed or not self._ready():
            return False
        self._claim_stream()
        try:
            self._mixer.music.load(str(self.tracks[identifier]['path']))
            self._envelope = 0.0 if fade > 0 else 1.0
            gain = self.tracks[identifier]['gain'] * self._volume() * self._duck * self._envelope
            self._mixer.music.set_volume(0.0 if self._paused else gain)
            self._mixer.music.play(-1)
            self.current_track = identifier
            self._loaded = True
            self._stream_paused = False
            self.error = None
            if fade > 0:
                self._fade_mode = 'in'
                self._fade_duration = self._fade_remaining = fade
                self._fade_start = 0.0
            else:
                self._fade_mode = None
            self._apply_pause()
            return True
        except (pygame.error, OSError) as error:
            self.error = str(error)
            self._clear_current()
            self._failed = True
            return False

    def play(self, identifier, fade_ms=450):
        """Request a looping track without restarting an unchanged request."""
        if identifier not in self.tracks:
            return False
        try:
            fade = float(fade_ms) / 1000
            if not math.isfinite(fade):
                return False
            fade = max(0.0, fade)
        except (TypeError, ValueError, OverflowError):
            return False
        if identifier == self.desired_track:
            self.refresh_volume()
            return True
        self.desired_track = identifier
        self._requested_fade = fade
        self._failed = False
        if self.current_track is None:
            self._start(identifier, fade)
        elif identifier == self.current_track:
            # Returning to the current music while it fades toward another
            # request cancels that request without rewinding the playing track.
            self._fade_mode = 'in' if fade else None
            self._fade_duration = self._fade_remaining = fade
            self._fade_start = self._envelope
            if not fade:
                self._envelope = 1.0
            self.refresh_volume()
        elif fade <= 0 or self._volume() <= 0:
            self._clear_current()
            self._start(identifier, fade)
        else:
            self._fade_mode = 'out'
            self._fade_duration = self._fade_remaining = fade
            self._fade_start = self._envelope
        return True

    def _apply_pause(self):
        if not self._loaded or not self._owns_stream():
            return
        paused = self._paused or self._volume() <= 0
        if paused != self._stream_paused:
            if paused:
                self._mixer.music.pause()
            else:
                self._mixer.music.unpause()
            self._stream_paused = paused

    def refresh_volume(self):
        """Apply preferences immediately, preserving both duck and fade gains."""
        if self.current_track is None:
            if self.desired_track is not None and not self._failed:
                self._start(self.desired_track, self._requested_fade)
            return
        if not self._owns_stream():
            return
        try:
            if not self._mixer.get_init():
                self._clear_current()
                self._failed = True
                return
            if self._volume() <= 0 and self._fade_mode == 'out':
                # An inaudible track switch can settle immediately. Unmuting
                # then starts the latest requested music, never a stale cue.
                self._clear_current()
                return
            gain = self.tracks[self.current_track]['gain']
            self._mixer.music.set_volume(gain * self._volume() * self._envelope * self._duck)
            self._apply_pause()
        except (pygame.error, OSError) as error:
            self.error = str(error)
            self._clear_current()
            self._failed = True

    def set_paused(self, paused):
        self._paused = bool(paused)
        self.refresh_volume()

    def set_ducked(self, ducked):
        self._duck_target = .6 if ducked else 1.0

    def update(self, seconds):
        try:
            seconds = max(0.0, float(seconds))
            if not math.isfinite(seconds):
                return
        except (ValueError, TypeError, OverflowError):
            return
        if not self._paused:
            self._duck += (self._duck_target - self._duck) * min(1.0, seconds / .18)
        if self.current_track is None and self.desired_track is not None and not self._failed:
            self._start(self.desired_track, self._requested_fade)
        if self._paused or self._volume() <= 0:
            self.refresh_volume()
            return
        remaining = seconds
        while self._fade_mode is not None and remaining > 0:
            portion = min(remaining, self._fade_remaining)
            self._fade_remaining = max(0.0, self._fade_remaining - portion)
            remaining -= portion
            progress = 1.0 - self._fade_remaining / self._fade_duration
            if self._fade_mode == 'out':
                self._envelope = self._fade_start * (1.0 - progress)
            else:
                self._envelope = self._fade_start + (1.0 - self._fade_start) * progress
            if self._fade_remaining > 1e-9:
                break
            mode = self._fade_mode
            self._fade_mode = None
            if mode == 'out':
                self._clear_current()
                if self.desired_track is None or not self._start(self.desired_track, self._requested_fade):
                    break
            else:
                self._envelope = 1.0
        self.refresh_volume()

    def stop(self):
        self._clear_current()
        self.desired_track = None
        self._failed = False
        self._paused = False
        self._duck = self._duck_target = 1.0

