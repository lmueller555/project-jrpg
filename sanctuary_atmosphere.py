"""Small, cached native scenery for the reserve's living confluence.

Particles participate in ordinary world depth sorting. Their visible positions
never become full-screen overlays, and they introduce no collision or save data.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pygame


ROOT = Path(__file__).resolve().parent


class SanctuaryAtmosphere:
    MAX_MOTES = 12
    MAX_PETALS = 5

    def __init__(self, world):
        self.world = world
        data = world.data.get('fantasy_effects', {})
        self.grove = data.get('grove', world.data.get('confluence_motes', {}))
        self.enabled = True
        self.records = []
        self.elapsed_ms = 0.
        self.reduced_motion = False
        self._motes = self._mote_frames()
        self._petals = self._petal_frames()
        count = max(0, min(self.MAX_MOTES, int(self.grove.get('count', 0))))
        petal_count = max(0, min(self.MAX_PETALS, int(self.grove.get('petal_count', 4)))) if count else 0
        self._specs = [('mote', index) for index in range(count)]
        self._specs.extend(('petal', index) for index in range(petal_count))
        for kind, index in self._specs:
            surface = self._motes[index % len(self._motes)] if kind == 'mote' else self._petals[index % len(self._petals)][0]
            record = {'id': f'confluence_{kind}_{index}', 'position': (0, 0),
                      'sort_y': 0, 'sort_priority': -2,
                      'surfaces': [surface], 'rect': surface.get_rect(),
                      'frame_duration_ms': 1000, 'phase_offset': 0,
                      'animation_stopped': True, 'atmosphere_kind': kind}
            self.records.append(record)
        self.update(0, reduced_motion=False)

    @staticmethod
    def _mote_frames():
        frames = []
        for index in range(8):
            surface = pygame.Surface((5, 5), pygame.SRCALPHA)
            alpha = 52+index*12
            # Sparse pixel glints retain crisp material-scale silhouettes.
            surface.set_at((2, 2), (222, 241, 209, min(235, alpha+70)))
            for point in ((1, 2), (3, 2), (2, 1), (2, 3)):
                surface.set_at(point, (144, 208, 181, alpha//3))
            frames.append(surface)
        return tuple(frames)

    def _petal_frames(self):
        path = self.grove.get('petal_manifest')
        result = []
        if path:
            manifest = json.loads((ROOT/path).read_text())
            for name in ('petal_white', 'petal_cyan', 'petal_amethyst'):
                module = manifest.get('modules', {}).get(name)
                if module is None:continue
                frames = []
                for record in module['frames']:
                    file = record if isinstance(record, str) else record['image']
                    frames.append(self.world.image(file))
                if frames:result.append(tuple(frames))
        if not result:
            # Older reserve snapshots remain usable without the expansion pack.
            for color in ('#d3ead8', '#a6d8d0', '#d0badb'):
                surface = pygame.Surface((5, 5), pygame.SRCALPHA)
                pygame.draw.line(surface, color, (1, 2), (3, 1), 1)
                surface.set_at((2, 3), pygame.Color(color))
                result.append((surface,))
        return tuple(result)

    def update(self, elapsed_ms, *, reduced_motion=False):
        self.elapsed_ms = max(0., float(elapsed_ms))
        self.reduced_motion = bool(reduced_motion)
        time = 0. if self.reduced_motion else self.elapsed_ms/1000
        cx, cy = self.grove.get('center', (0, 0))
        rx, ry = self.grove.get('radius', (0, 0))
        ceiling = self.grove.get('sort_y', cy+ry)
        for record, (kind, index) in zip(self.records, self._specs):
            phase = index*2.399963
            if kind == 'mote':
                x = cx+math.cos(phase)*rx*.68+math.sin(time*.24+phase)*3
                y = cy+math.sin(phase)*ry*.62+math.cos(time*.21+phase)*2
                frame = round((.5+.5*math.sin(time*.55+phase))*7)
                surface = self._motes[frame]
            else:
                # Fixed cyclic paths, independent phases; no growing particle pool.
                fall = ((time*.035+index*.231) % 1)
                x = cx+math.cos(phase)*rx*.60+math.sin(time*.28+phase)*7
                y = cy-ry*.70+fall*ry*1.28
                frames = self._petals[index % len(self._petals)]
                surface = frames[int(time*1.2+index) % len(frames)]
            position = round(x-surface.get_width()/2), round(y-surface.get_height()/2)
            record['position'] = position
            record['rect'] = surface.get_rect(topleft=position)
            # Sorting at the visible particle's y keeps overlapping upper-body
            # pixels behind actors; canopy and roofs retain their own depth.
            record['sort_y'] = min(round(y), ceiling)
            record['surfaces'][0] = surface

    def snapshot(self):
        return {'motes': sum(kind == 'mote' for kind, _ in self._specs),
                'petals': sum(kind == 'petal' for kind, _ in self._specs),
                'elapsed_ms': self.elapsed_ms, 'reduced_motion': self.reduced_motion,
                'positions': [list(record['position']) for record in self.records],
                'cached_surfaces': len(self._motes)+sum(map(len, self._petals))}
