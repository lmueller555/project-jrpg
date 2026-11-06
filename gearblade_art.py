"""Registered authored gearblade poses for battle and the mill water focus.

Body movement is drawn in the source atlases. Runtime only selects a frame;
the extra battle margin protects the circular guard and extended sword tip.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pygame

ROOT = Path(__file__).resolve().parent
ART = 'assets/story/gearblade_focus'


def _reader(path):
    return pygame.image.load(str(ROOT/path)).convert_alpha()


class GearbladeFocus:
    """A 2.5-second upright cast, registered to the original mill foot anchor."""
    def __init__(self, image_reader=None):
        reader = image_reader or _reader
        self.manifest = json.loads((ROOT/ART/'world/animation.json').read_text())
        self.anchor = tuple(self.manifest['anchor'])
        self.duration = self.manifest['duration_ms']/1000
        self.sequences = {
            name: [reader(f'{ART}/world/{frame["file"]}') for frame in entry['frames']]
            for name,entry in self.manifest['animations'].items()}

    def frame(self, elapsed):
        time = max(0.,float(elapsed))
        for name in self.manifest['sequence']:
            duration = self.manifest['animations'][name]['duration_ms']/1000
            images = self.sequences[name]
            if time < duration:
                return images[min(len(images)-1,int(time/duration*len(images)))]
            time -= duration
        return self.sequences[self.manifest['sequence'][-1]][-1]


class GearbladeCombat:
    def __init__(self, image_reader=None):
        reader = image_reader or _reader
        self.manifest = json.loads((ROOT/ART/'combat/animation.json').read_text())
        self.anchor = tuple(self.manifest['anchor'])
        self.sequences = {
            name: [(reader(f'{ART}/combat/{frame["file"]}'),frame['duration_ms'])
                   for frame in entry['frames']]
            for name,entry in self.manifest['animations'].items()}

    def frame(self, state, elapsed_ms):
        if state not in self.sequences:state='idle'
        sequence = self.sequences[state]
        duration = sum(milliseconds for _,milliseconds in sequence)
        time = max(0.,float(elapsed_ms))
        if self.manifest['animations'][state]['loop']:time %= duration
        for image,milliseconds in sequence:
            if time < milliseconds:return image,self.anchor
            time -= milliseconds
        return sequence[-1][0],self.anchor


_combat = None


def prepare_combat_art():
    """Warm the immutable frame bank during scene setup, never during a draw."""
    global _combat
    if _combat is None:_combat=GearbladeCombat()
    return _combat


def combat_frame(original, state, elapsed_ms):
    """Replace an equipped Caelan frame and its anchor, retaining body scale.

    The original argument keeps the call site explicit about which actor bank
    is being replaced. The source's 36-pixel body matches the existing bank;
    the 64-pixel canvas simply adds blade margin around it.
    """
    if not isinstance(original,pygame.Surface):raise TypeError('Expected an actor surface')
    if not math.isfinite(float(elapsed_ms)):raise ValueError('Invalid animation clock')
    return prepare_combat_art().frame(state,elapsed_ms)
