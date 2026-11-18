"""Whole-body authored Caelan choreography, registered once at load time.

The source atlases are unchanged image_gen outputs. Runtime sampling only
removes detached alpha fringe, uses one nearest-neighbour scale per atlas,
and places each complete drawing on the existing 64-pixel combat canvas.
The action timeline owns travel and jump height; this bank owns body poses.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pygame

ROOT = Path(__file__).resolve().parent
ART = 'assets/combat/caelan_motion'
MOTION_STATES = frozenset((
    'run', 'plant', 'slash', 'followthrough', 'retreat', 'land',
    'cast_prepare', 'cast_release', 'cast_recover', 'guard_enter',
    'guard_impact', 'hurt_recover',
))


def _reader(path):
    return pygame.image.load(str(ROOT / path)).convert_alpha()


class CombatMotionArt:
    """A cached body bank for equipped sword moves and unarmed punches."""

    def __init__(self, image_reader=None, legacy=None):
        reader = image_reader or _reader
        self.manifest = json.loads((ROOT / ART / 'animation.json').read_text())
        self.anchor = tuple(self.manifest['anchor'])
        self.sequences = {}
        self.records = {}
        for family, specification in self.manifest['variants'].items():
            atlas = reader(f'{ART}/{specification["file"]}')
            scale = specification['scale']
            drawings = []
            for record in specification['drawings']:
                source = atlas.subsurface(record['source_rect']).copy()
                # The generated translucent fringe can include detached
                # flecks. Keep the connected whole body, including its blade.
                mask = pygame.mask.from_surface(source, 127).connected_component()
                opaque = mask.to_surface(setcolor=(255, 255, 255, 255),
                                         unsetcolor=(0, 0, 0, 0))
                source.blit(opaque, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                drawing = pygame.transform.scale(source, tuple(
                    max(1, round(value * scale)) for value in source.get_size()))
                image = pygame.Surface(self.manifest['canvas'], pygame.SRCALPHA)
                foot = record['source_foot']
                image.blit(drawing, (round(self.anchor[0] - foot[0] * scale),
                                     round(self.anchor[1] - foot[1] * scale)))
                drawings.append(image)
            self.records[family] = specification['drawings']
            self.sequences[family] = {
                name: [(drawings[frame['drawing']], frame['duration_ms'],
                        frame['drawing']) for frame in entry['frames']]
                for name, entry in self.manifest['animations'].items()}
        # A legacy bank retains all sixteen original drawings plus the four
        # focus and eight Aether Edge drawings. It never dispatches back here.
        if legacy is None:
            from gearblade_art import GearbladeCombat
            legacy = GearbladeCombat(image_reader=reader, include_motion=False)
        self.legacy = legacy

    def _selection(self, state, elapsed_ms, armed):
        time = float(elapsed_ms)
        if not math.isfinite(time):
            raise ValueError('Invalid animation clock')
        family = 'armed' if armed else 'unarmed'
        if state not in self.sequences[family]:
            state = 'idle'
        sequence = self.sequences[family][state]
        duration = sum(frame[1] for frame in sequence)
        time = max(0., time)
        if self.manifest['animations'][state]['loop']:
            time %= duration
        for index, (_, milliseconds, _) in enumerate(sequence):
            if time < milliseconds:
                return family, state, index
            time -= milliseconds
        return family, state, len(sequence) - 1

    def frame(self, state, elapsed_ms, armed=True, owned_gems=None):
        """Return the selected 64x64 surface and its fixed floor anchor."""
        if armed and state not in MOTION_STATES:
            return self.legacy.frame(state, elapsed_ms, owned_gems=owned_gems)
        family, state, index = self._selection(state, elapsed_ms, armed)
        image = self.sequences[family][state][index][0]
        if armed:
            from gearblade_art import with_owned_gems
            image = with_owned_gems(image, self.anchors(state, elapsed_ms, armed), owned_gems)
        return image, self.anchor

    def anchors(self, state, elapsed_ms, armed=True):
        """Frame-local body, hand and sword points on the same pose clock."""
        if armed and state not in MOTION_STATES:
            result = self.legacy.anchors(state, elapsed_ms)
            result['foot'] = self.anchor
            result['cast_origin'] = result['blade_tip']
            result['armed'] = True
            return result
        family, state, index = self._selection(state, elapsed_ms, armed)
        drawing = self.sequences[family][state][index][2]
        result = {name: tuple(point) for name, point in
                  self.records[family][drawing]['anchors'].items()}
        x, y = result['guard']
        result['gems'] = {'nature': (x, y - 3), 'water': (x + 3, y),
                          'fire': (x, y + 3), 'ice': (x - 3, y)}
        result.update(foot=self.anchor, frame_index=index, drawing_index=drawing,
                      armed=bool(armed), facing='left')
        return result


def prepare_combat_motion_art():
    """Warm all drawings during scene setup; frame selection never reads disk."""
    from gearblade_art import prepare_combat_art
    return prepare_combat_art().motion


def frame(state, elapsed_ms, armed=True, owned_gems=None):
    return prepare_combat_motion_art().frame(state, elapsed_ms, armed, owned_gems)


def anchors(state, elapsed_ms, armed=True):
    return prepare_combat_motion_art().anchors(state, elapsed_ms, armed)
