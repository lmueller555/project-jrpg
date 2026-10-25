"""Independent, persisted music and effects levels shared by both menus."""
from __future__ import annotations

import math

import pygame

from save_game import SaveStore


class AudioSettings:
    def __init__(self, settings_path=None):
        self.store = SaveStore(settings_path)
        self.music_volume = 1.0
        self.effects_volume = 1.0
        self._last_music = 1.0
        self._last_effects = 1.0
        self.error = None
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
                'last_music': self._last_music, 'last_effects': self._last_effects}

    def _save(self):
        if self.store.enabled:
            self.error = None if self.store.write(self.to_dict()) else self.store.error

    def apply_music(self):
        """Keep the original theme's mix level; the setting is its multiplier."""
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
