"""Persisted audio and interface preferences shared by both menus.

The original class name remains public so older callers and settings files keep
working. Interface options live in the same atomic document as volume settings.
"""
from __future__ import annotations

import math
import weakref

import pygame

from save_game import SaveStore


class AudioSettings:
    def __init__(self, settings_path=None):
        self.store = SaveStore(settings_path)
        self.music_volume = 1.0
        self.effects_volume = 1.0
        self._last_music = 1.0
        self._last_effects = 1.0
        self.text_scale = 1.0
        self.reduced_motion = False
        self.tracker_visible = True
        self.error = None
        self._music_controller = None
        saved = self.store.load()
        if saved is not None:
            keys = ('music_volume', 'effects_volume', 'last_music', 'last_effects')
            if (type(saved.get('version')) is int and saved['version'] == 1 and
                    all(self._valid_level(saved.get(key)) for key in keys) and
                    saved['last_music'] > 0 and saved['last_effects'] > 0):
                self.music_volume = float(saved['music_volume'])
                self.effects_volume = float(saved['effects_volume'])
                self._last_music = float(saved['last_music'])
                self._last_effects = float(saved['last_effects'])
                if saved.get('text_scale', 1.0) in (1.0, 1.25, 1.5) and type(saved.get('text_scale', 1.0)) in (int, float):
                    self.text_scale = float(saved.get('text_scale', 1.0))
                if type(saved.get('reduced_motion', False)) is bool:
                    self.reduced_motion = saved.get('reduced_motion', False)
                if type(saved.get('tracker_visible', True)) is bool:
                    self.tracker_visible = saved.get('tracker_visible', True)
            else:
                self.error = 'Audio settings could not be read.'
        elif self.store.error:
            self.error = self.store.error

    @staticmethod
    def _valid_level(value):
        return type(value) in (int, float) and 0 <= value <= 1 and math.isfinite(value)

    def to_dict(self):
        return {'version': 1, 'music_volume': self.music_volume,
                'effects_volume': self.effects_volume,
                'last_music': self._last_music, 'last_effects': self._last_effects,
                'text_scale': self.text_scale, 'reduced_motion': self.reduced_motion,
                'tracker_visible': self.tracker_visible}

    def set_text_scale(self, value):
        if type(value) not in (int, float) or value not in (1, 1.25, 1.5) or value == self.text_scale:
            return False
        self.text_scale = float(value)
        self._save()
        return True

    def set_reduced_motion(self, value):
        if type(value) is not bool or value == self.reduced_motion:return False
        self.reduced_motion = value
        self._save()
        return True

    def set_tracker_visible(self, value):
        if type(value) is not bool or value == self.tracker_visible:return False
        self.tracker_visible = value
        self._save()
        return True

    def toggle_reduced_motion(self):
        return self.set_reduced_motion(not self.reduced_motion)

    def toggle_tracker(self):
        return self.set_tracker_visible(not self.tracker_visible)

    def _save(self):
        if self.store.enabled:
            self.error = None if self.store.write(self.to_dict()) else self.store.error

    def bind_music(self, controller):
        """Let this game's soundtrack apply its own track/fade/duck mix."""
        self._music_controller = weakref.ref(controller)

    def apply_music(self):
        """Refresh the soundtrack immediately; retain standalone menu support."""
        controller = self._music_controller() if self._music_controller is not None else None
        if controller is not None:
            controller.refresh_volume()
            return
        try:
            if pygame.mixer.get_init():
                pygame.mixer.music.set_volume(.45*self.music_volume)
        except pygame.error:
            pass

    def _set(self, kind, value):
        if type(value) not in (int, float) or (type(value) is float and not math.isfinite(value)):
            return False
        value = round(float(max(0.0, min(1.0, value))), 4)
        attribute = kind+'_volume'
        if value == getattr(self, attribute):
            return False
        setattr(self, attribute, value)
        if value > 0:
            setattr(self, '_last_'+kind, value)
        if kind == 'music':
            self.apply_music()
        self._save()
        return True

    def set_music(self, value):
        return self._set('music', value)

    def set_effects(self, value):
        return self._set('effects', value)

    def toggle_music(self):
        return self.set_music(0 if self.music_volume else self._last_music)

    def toggle_effects(self):
        return self.set_effects(0 if self.effects_volume else self._last_effects)
