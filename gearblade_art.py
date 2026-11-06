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
        # The imagegen atlas remains unchanged on disk. Registration happens
        # once when the renderer loads it, just as an actor atlas is sampled.
        images = {}
        atlases = {}
        def read_frame(frame):
            key = frame.get('drawing', frame['file'])
            if key in images:return images[key]
            path = f'{ART}/combat/{frame["file"]}'
            if 'source_rect' in frame:
                if path not in atlases:atlases[path] = reader(path)
                source = atlases[path].subsurface(frame['source_rect']).copy()
                # imagegen's transparent background carries a faint alpha
                # fringe. A cached runtime mask removes only that fringe;
                # authored pixels on disk remain completely unchanged.
                opaque = pygame.mask.from_surface(source,127).to_surface(
                    setcolor=(255,255,255,255),unsetcolor=(0,0,0,0))
                source.blit(opaque,(0,0),special_flags=pygame.BLEND_RGBA_MULT)
                scale = self.manifest['atlas_registration']['scale']
                size = tuple(round(value*scale) for value in source.get_size())
                drawing = pygame.transform.scale(source,size)
                image = pygame.Surface(self.manifest['canvas'],pygame.SRCALPHA)
                foot = frame['source_foot']
                image.blit(drawing,(round(self.anchor[0]-foot[0]*scale),
                                    round(self.anchor[1]-foot[1]*scale)))
            else:image = reader(path)
            images[key] = image
            return image
        self.sequences = {
            name: [(read_frame(frame),frame['duration_ms'])
                   for frame in entry['frames']]
            for name,entry in self.manifest['animations'].items()}

    def _selection(self, state, elapsed_ms):
        if not math.isfinite(float(elapsed_ms)):raise ValueError('Invalid animation clock')
        if state not in self.sequences:state='idle'
        sequence = self.sequences[state]
        duration = sum(milliseconds for _,milliseconds in sequence)
        time = max(0.,float(elapsed_ms))
        if self.manifest['animations'][state]['loop']:time %= duration
        for index,(_,milliseconds) in enumerate(sequence):
            if time < milliseconds:return state,index
            time -= milliseconds
        return state,len(sequence)-1

    def frame(self, state, elapsed_ms):
        state,index = self._selection(state,elapsed_ms)
        return self.sequences[state][index][0],self.anchor

    def anchors(self, state, elapsed_ms):
        """Return frame-local weapon anchors, in the unscaled 64-pixel canvas.

        The same frame selection drives body and effects. Callers translate
        each point by the actor's floor position minus ``self.anchor`` and
        apply the actor display scale (two in battle).
        """
        state,index = self._selection(state,elapsed_ms)
        record = self.manifest['animations'][state]['frames'][index]
        result = {name:tuple(point) for name,point in record['anchors'].items()}
        x,y = result['guard']
        result['gems'] = {'nature':(x,y-3),'water':(x+3,y),
                          'fire':(x,y+3),'ice':(x-3,y)}
        result['frame_index'] = index
        return result


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


def anchors(state, elapsed_ms):
    """Registered weapon points for the current equipped combat drawing."""
    return prepare_combat_art().anchors(state,elapsed_ms)
