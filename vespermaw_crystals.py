"""Simulation-clock elemental wall lenses; no weakness or counter UI."""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pygame

ROOT = Path(__file__).resolve().parent
BATTLE_SUPPORTS = {'fire': (94, 102), 'ice': (240, 93), 'water': (386, 102)}


def crystal_origin(element, vertical_offset=0):
    """Native battle-coordinate emission point, matching the embedded lens."""
    x, y = BATTLE_SUPPORTS[element]
    return x, y-28-vertical_offset


class ElementalCrystals:
    def __init__(self, root=ROOT):
        root = Path(root)
        manifest = json.loads((root/'assets/terrain/limestone_cave/elemental_crystals/assets.json').read_text())
        self.frames = {}
        self.glows = {}
        for element, record in manifest['modules'].items():
            self.frames[element] = [pygame.image.load(str(root/path)).convert_alpha()
                                    for path in record['frames']]
            yy, xx = np.mgrid[-72:73, -96:97]
            falloff = np.maximum(0, 1-np.sqrt((xx/96)**2+(yy/72)**2))**1.7
            rgba = np.zeros((145,193,4),dtype=np.uint8)
            rgba[:,:,:3] = record['color']
            rgba[:,:,3] = np.rint(falloff*95).astype(np.uint8)
            self.glows[element] = pygame.image.frombytes(rgba.tobytes(),(193,145),'RGBA').convert_alpha()

    @staticmethod
    def strengths(elapsed_ms, state, reduced_motion=False):
        state = state or {}
        element = state.get('element')
        strengths = {key: 0. for key in BATTLE_SUPPORTS}
        pulse = 1. if reduced_motion else .80+.20*math.sin(max(0,elapsed_ms)*math.tau/2100)**2
        if element in strengths:strengths[element] = pulse
        source, destination = state.get('from'), state.get('to')
        if source in strengths and destination in strengths and source != destination:
            progress = max(0., min(1., state.get('progress',0.)))
            commit = max(.01, min(1.,state.get('commit',.66)))
            q = min(1.,progress/commit)
            q = q*q*(3-2*q)
            strengths[source] = (1-q)*pulse
            strengths[destination] = q*pulse
        return strengths

    def draw(self, target, elapsed_ms, state=None, reduced_motion=False, vertical_offset=0):
        strengths = self.strengths(elapsed_ms,state,reduced_motion)
        for element, strength in strengths.items():
            if strength <= 0:continue
            cx, cy = crystal_origin(element,vertical_offset)
            glow = self.glows[element]
            glow.set_alpha(round(255*strength))
            target.blit(glow,(cx-96,cy-72))
            frame = self.frames[element][min(7,round(7*strength))]
            frame.set_alpha(round(255*strength))
            support = BATTLE_SUPPORTS[element]
            target.blit(frame,(support[0]-32,support[1]-72-vertical_offset))
