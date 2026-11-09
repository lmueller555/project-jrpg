"""One streamed soundtrack shared by the title, exploration and encounters.

Track changes use a short, nonblocking fade-out/fade-in. Requests for the same
track preserve playback across Eldenmere and the millrace. Combat temporarily
bookmarks the current cue and resumes it at its saved playback position. Only
music is controlled here; environmental effects and UI cues keep their own
channels.
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
        self._completed = False
        self._duck = self._duck_target = 1.0
        self._envelope = 1.0
        self._fade_mode = None
        self._fade_duration = self._fade_remaining = 0.0
        self._fade_start = 1.0
        self._requested_fade = .45
        self._requested_position = 0.0
        self._position_origin = self._position_frozen = 0.0
        self._fallback_elapsed = 0.0
        self._durations = {}
        self._battle_bookmark = None
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
                loop = record.get('loop', True)
                if (not isinstance(identifier, str) or not isinstance(filename, str)
                        or type(gain) not in (int, float) or not math.isfinite(gain)
                        or not 0 <= gain <= 1 or type(loop) is not bool):
                    raise ValueError('Invalid music track')
                path = (self.music_root / filename).resolve()
                if not path.is_relative_to(self.music_root.resolve()):
                    raise ValueError('Music path escapes its folder')
                result[identifier] = {'path': path, 'gain': float(gain), 'loop': loop}
            return result
        except (OSError, ValueError, KeyError, TypeError) as error:
            self.error = str(error)
            return {}

    def _duration(self, identifier):
        """Read Vorbis timing headers without decoding a whole music track."""
        if identifier in self._durations:
            return self._durations[identifier]
        duration = None
        try:
            with self.tracks[identifier]['path'].open('rb') as source:
                header = source.read(4096)
                packet = header.find(b'\x01vorbis')
                if not header.startswith(b'OggS') or packet < 0:
                    raise ValueError('Not an Ogg Vorbis stream')
                rate = int.from_bytes(header[packet + 12:packet + 16], 'little')
                source.seek(0, 2)
                length = source.tell()
                source.seek(max(0, length - 65536))
                tail = source.read()
            # A page is at most 65,307 bytes. Validate the final page rather
            # than mistaking an OggS byte sequence inside compressed audio.
            offset = len(tail)
            while (offset := tail.rfind(b'OggS', 0, offset)) >= 0:
                if offset + 27 > len(tail):
                    continue
                count = tail[offset + 26]
                body = offset + 27 + count
                if (body <= len(tail) and tail[offset + 4] == 0
                        and tail[offset + 5] & 4
                        and tail[offset + 14:offset + 18] == header[14:18]
                        and body + sum(tail[offset + 27:body]) == len(tail)):
                    samples = int.from_bytes(tail[offset + 6:offset + 14],
                                             'little', signed=True)
                    if rate > 0 and samples > 0:
                        duration = samples / rate
                    break
        except (OSError, ValueError, KeyError):
            pass
        self._durations[identifier] = duration
        return duration

    def _bounded_position(self, identifier, position):
        position = max(0.0, position)
        duration = self._duration(identifier)
        if duration and self.tracks[identifier]['loop']:
            position %= duration
        return position

    def _decoder_position(self):
        try:
            value = self._mixer.music.get_pos()
            if type(value) in (int, float) and math.isfinite(value) and value >= 0:
                return value / 1000
        except (AttributeError, pygame.error, OSError, ValueError, OverflowError):
            pass
        return self._fallback_elapsed

    @property
    def position(self):
        """Current cue position in seconds, including an earlier resume seek."""
        if self.current_track is None:
            return self._requested_position if self.desired_track is not None else 0.0
        value = (self._position_frozen if self._stream_paused else
                 self._position_origin + self._decoder_position())
        return self._bounded_position(self.current_track, value)

    @property
    def battle_active(self):
        return self._battle_bookmark is not None

    def begin_battle(self, fade_ms=450):
        """Bookmark the interrupted cue once, then request the battle theme."""
        if self.battle_active:
            return True
        if 'battle' not in self.tracks:
            return False
        self._observe_completion()
        identifier = self.current_track or self.desired_track
        bookmark = {'track': identifier, 'position': self.position,
                    'completed': self._completed}
        if not self.play('battle', fade_ms=fade_ms):
            return False
        self._battle_bookmark = bookmark
        return True

    def end_battle(self, fade_ms=450):
        """Resume the saved cue once, fading in from the saved decoder position."""
        if not self.battle_active:
            return False
        try:
            fade = float(fade_ms) / 1000
            if not math.isfinite(fade):
                return False
            fade = max(0.0, fade)
        except (TypeError, ValueError, OverflowError):
            return False
        bookmark, self._battle_bookmark = self._battle_bookmark, None
        identifier = bookmark['track']
        if identifier is None:
            self.fade_out(fade_ms)
            return True
        if (identifier == self.current_track and self._loaded
                and not self._completed):
            # The story may already use the battle cue, or combat may have
            # ended before the old cue faded out. Never rewind that stream.
            return self.play(identifier, fade_ms=fade_ms)
        self._clear_current()
        self.desired_track = identifier
        self._requested_position = bookmark['position']
        self._requested_fade = fade
        self._failed = False
        if bookmark['completed']:
            # A previously finished one-shot must remain silent after combat.
            self.current_track = identifier
            self._completed = True
        else:
            self._start(identifier, fade)
        return True

    @property
    def playing(self):
        self._observe_completion()
        if not self._loaded or not self._owns_stream() or self._stream_paused or self._completed:
            return False
        try:
            return bool(self._mixer.get_init() and self._mixer.music.get_busy())
        except (pygame.error, OSError):
            return False

    @property
    def paused(self):
        return self._paused

    @property
    def completed(self):
        """A finished one-shot remains selected and silent until another request."""
        self._observe_completion()
        return self._completed

    def _observe_completion(self):
        if (self._completed or not self._loaded or not self._owns_stream()
                or self._paused or self._stream_paused or self._volume() <= 0
                or self.tracks[self.current_track]['loop']):
            return
        try:
            if self._mixer.get_init() and not self._mixer.music.get_busy():
                self._completed = True
                self._fade_mode = None
                self._fade_remaining = 0.0
        except (pygame.error, OSError):
            pass

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
            previous._completed = False
            previous._battle_bookmark = None
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
        self._completed = False
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
            position = self._bounded_position(identifier, self._requested_position)
            loops = -1 if self.tracks[identifier]['loop'] else 0
            if position > 0:
                self._mixer.music.play(loops, start=position)
            else:
                self._mixer.music.play(loops)
            self._fallback_elapsed = 0.0
            self._position_origin = self._position_frozen = position
            self.current_track = identifier
            self._loaded = True
            self._stream_paused = False
            self._completed = False
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
        """Request a loop or one-shot without restarting an unchanged request."""
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
        self._requested_position = 0.0
        self._requested_fade = fade
        self._failed = False
        if self.current_track is None:
            self._start(identifier, fade)
        elif self._completed:
            # A finished fanfare is already silent; returning to exploration
            # only needs the new track's fade-in, not another silent fade-out.
            self._clear_current()
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
        if not self._loaded or not self._owns_stream() or self._completed:
            return
        paused = self._paused or self._volume() <= 0
        if paused != self._stream_paused:
            if paused:
                self._position_frozen = self._position_origin + self._decoder_position()
                self._mixer.music.pause()
            else:
                self._mixer.music.unpause()
                self._position_origin = self._position_frozen - self._decoder_position()
            self._stream_paused = paused

    def refresh_volume(self):
        """Apply preferences immediately, preserving both duck and fade gains."""
        self._observe_completion()
        if self.current_track is None:
            if self.desired_track is not None and not self._failed:
                self._start(self.desired_track, self._requested_fade)
            return
        if not self._owns_stream() or self._completed:
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
        self._observe_completion()
        if self._completed and self.desired_track != self.current_track:
            # A one-shot can end naturally during its outgoing fade. Settle
            # that pending request instead of stranding it on the silent cue.
            self._clear_current()
        if self._loaded and not self._stream_paused and not self._completed:
            self._fallback_elapsed += seconds
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

    def fade_out(self, fade_ms=700):
        """Fade to silence without restarting an already pending fade."""
        try:
            fade = float(fade_ms)/1000
            if not math.isfinite(fade):return False
        except (ValueError, TypeError, OverflowError):return False
        if self.desired_track is None:return
        self.desired_track = None
        if self.current_track is None:return
        if fade <= 0:
            self._clear_current()
            return
        self._fade_mode = 'out'
        self._fade_duration = self._fade_remaining = fade
        self._fade_start = self._envelope

    def stop(self):
        self._battle_bookmark = None
        self._requested_position = 0.0
        self._clear_current()
        self.desired_track = None
        self._failed = False
        self._paused = False
        self._duck = self._duck_target = 1.0
