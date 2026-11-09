"""Short local cave introduction with live crystal lighting and an original growl."""
from array import array
import math
import random

import pygame

from cave_battle_entry import CaveBattleEntry


def growl_samples(rate, channels):
    """Original deterministic voiced/noise synthesis, with a bounded soft envelope."""
    rng = random.Random(7341)
    values = array('h')
    low = 0.
    duration = 1.6
    for index in range(round(rate*duration)):
        t = index/rate
        low += .08*(rng.uniform(-1, 1)-low)
        phase = 2*math.pi*(76*t-9*t*t+1.3*math.sin(2*math.pi*3.7*t))
        voice = .23*math.sin(phase)+.09*math.sin(phase*2)+.05*math.sin(phase*3)
        sample = (voice+.25*low)*math.sin(math.pi*t/duration)**2
        value = round(max(-1., min(1., sample))*32767)
        values.extend([value]*channels)
    return values


class SanctuaryBossEntry(CaveBattleEntry):
    def __init__(self, world_frame, focus, *, intro_seen, reduced_motion=False, audio_settings=None):
        super().__init__(world_frame, focus, 'Echo Chamber', reduced_motion=reduced_motion)
        self.intro_seen = intro_seen
        self.duration = (.35 if intro_seen else 1.2 if reduced_motion else 3.2)
        self.audio_settings = audio_settings
        self._growled = False
        self._channel = None
        self._sound = None
        if audio_settings is not None:audio_settings.bind_effects(self)

    def refresh_volume(self):
        if self._channel is not None:
            self._channel.set_volume(.55*getattr(self.audio_settings, 'effects_volume', 1.))

    def stop_audio(self):
        if self._channel is not None:self._channel.stop()
        self._channel = None

    def update(self, seconds):
        super().update(seconds)
        if self._channel is not None:
            if self.paused or not self.focused or self.error:self._channel.pause()
            else:self._channel.unpause()
        if (not self.intro_seen and not self._growled and self.elapsed >= .25
                and not self.paused and self.focused and not self.error):
            self._growled = True
            try:
                mixer = pygame.mixer.get_init()
                if mixer is not None and mixer[1] == -16:
                    self._sound = pygame.mixer.Sound(buffer=growl_samples(mixer[0], mixer[2]))
                    self._channel = self._sound.play()
                    self.refresh_volume()
            except pygame.error:
                pass

    def draw(self, game, canvas, ui_surface):
        if self.phase == 'cutscene' and not self.intro_seen:
            progress = min(1., self.elapsed/self.duration)
            origin = pygame.Vector2(game.camera.position())
            if not self.reduced_motion:
                ease = math.sin(min(1., progress/.8)*math.pi/2)**2
                origin = origin.lerp((1820, 140), .8*ease)
            frame = pygame.Surface(canvas.get_size())
            game.world.draw(frame, origin, game.player, game.elapsed_ms+self.elapsed*1000,
                            include_ui=False, party_actors=game.party_travel.actors())
            self.world_frame = frame
        super().draw(game, canvas, ui_surface)
