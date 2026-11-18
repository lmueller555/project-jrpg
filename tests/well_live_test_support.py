"""Disposable actual-Game fixtures shared by the live-well integration checks."""
from copy import deepcopy
import os
from pathlib import Path
import random
import tempfile
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import pygame

import main
from npc_routines import Gardener
from rendering import snapshot


class LiveWellCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        folder = Path(self.temp.name)
        self.game = main.Game(fullscreen=False, start_on_title=False,
                              save_path=folder/'journey.json',
                              settings_path=folder/'settings.json')
        self.world = self.game.town
        self.game.world = self.world
        self.game.opening.stage = 'done'
        self.game.player.position.update(480, 924)
        self.well = self.world.well
        self.well.reset()
        old = next(actor for actor in self.world.npcs
                   if actor.data['id'] == 'sanctuary_gardener')
        self.actor = Gardener(old.data, self.world, random.Random(1234))
        self.world.npcs[self.world.npcs.index(old)] = self.actor

    def tearDown(self):
        self.game.music.stop()
        pygame.quit()
        self.temp.cleanup()

    def start_trip(self):
        # Omit only the initial ambient rest in this disposable fixture.
        self.actor.state_ms = self.actor.rest_duration_ms-1000
        self.game.update(1+1/60, (0, 0), False)

    def until(self, predicate, limit=120, dt=1/60):
        for _ in range(round(limit/dt)):
            if predicate():
                return
            self.game.update(dt, (0, 0), False)
        self.fail(f'Timed out: {self.actor.state}, '
                  f'{self.well.snapshot().phase_id}, {tuple(self.actor.position)}')

    def to_phase(self, phase, limit=60):
        if self.actor.state == 'rest':
            self.start_trip()
        self.until(lambda: self.well.snapshot().phase_id == phase, limit)

    def signature(self):
        return (self.well.snapshot().to_dict(), self.actor.state,
                tuple(self.actor.position), self.actor.state_ms,
                self.actor.walk_ms, self.actor.water_units,
                deepcopy(list(self.actor.events)))

    def native(self, camera=(408, 768)):
        self.world.draw(self.game.canvas, camera, self.game.player,
                        self.game.elapsed_ms, include_ui=False)
        return snapshot(self.game.canvas)
