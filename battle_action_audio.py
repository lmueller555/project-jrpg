"""Quiet action cues reusing the game's existing licensed effect recordings."""
from array import array
from pathlib import Path

import pygame

ROOT = Path(__file__).resolve().parent/'assets/audio/sfx'
SOURCES = {
    'step': ('ice_reaper_rescue/source/fps_walking.ogg', .12),
    'land': ('ice_reaper_duel/caelan_lands.ogg', .20),
    'swing': ('ice_reaper_duel/sword_windup.ogg', .24),
    'focus': ('ice_reaper_rescue/source/fps_weapon_change.ogg', .12),
    'release': ('ice_reaper_rescue/source/fps_blaster.ogg', .18),
    'impact': ('ice_reaper_rescue/source/platform_land.ogg', .22),
    'guard_hit': ('ice_reaper_rescue/shield_impact.ogg', .18),
}
LIMITS = {'step': .17, 'land': .22, 'swing': .22, 'focus': .10,
          'release': .25, 'impact': .08, 'guard_hit': .24}


class BattleActionAudio:
    """Load each cue once, play only on phase/impact events, stop on pause."""
    def __init__(self, game):
        self.game = game
        self._sounds = {}
        self._channels = []

    def play(self, cue):
        settings = getattr(self.game, 'audio', None)
        volume = getattr(settings, 'effects_volume', 0)
        if volume <= 0 or cue not in SOURCES:return
        try:
            if not pygame.mixer.get_init():pygame.mixer.init()
            path, gain = SOURCES[cue]
            if cue not in self._sounds:
                rate, sample_format, channels = pygame.mixer.get_init()
                if sample_format != -16:return
                source = pygame.mixer.Sound(str(ROOT/path))
                data = array('h')
                data.frombytes(source.get_raw()[:round(rate*LIMITS[cue])*channels*2])
                frames = len(data)//channels
                fade = max(1, round(rate*.008))
                for index in range(frames):
                    envelope = min(1., index/max(1, rate*.001), (frames-index)/fade)
                    for channel in range(channels):
                        data[index*channels+channel] = round(data[index*channels+channel]*envelope)
                self._sounds[cue] = pygame.mixer.Sound(buffer=data)
            sound = self._sounds[cue]
            sound.set_volume(volume*gain)
            channel = sound.play()
            self._channels = [old for old in self._channels if old.get_busy()]
            if channel is not None:self._channels.append(channel)
        except (pygame.error, OSError):pass

    def stop(self):
        if pygame.mixer.get_init():
            for channel in self._channels:channel.stop()
        self._channels.clear()
