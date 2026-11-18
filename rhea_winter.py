"""Scene-specific Rhea wardrobe and authored magical hair/cloth animation.

Selection is a pure function of view and the cinematic clock. All body poses
and cloth shapes come from drawings; the renderer never stretches her anatomy.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pygame


ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT/'assets/story/rhea_winter/manifest.json'
VIEWS = {'front', 'front_left', 'left', 'rear_left', 'rear',
         'rear_right', 'right', 'front_right'}
EXPRESSIONS = {'neutral_closed', 'strain_begin', 'strain_mid', 'strain_peak',
               'opening_01', 'opening_02', 'angry_open', 'angry_hold'}


class RheaWinterSprites:
    BREAKOUT = 17.3

    def __init__(self, read_image, manifest_path=MANIFEST):
        self.path = Path(manifest_path)
        self.root = self.path.parent
        self.manifest = json.loads(self.path.read_text())
        self.data = dict(anchor=tuple(self.manifest['anchor']),
                         body_pixels=self.manifest['body_pixels'])
        if (self.manifest['canvas'] != [128, 128]
                or self.data['anchor'] != (64, 116)
                or self.data['body_pixels'] != 82):
            raise ValueError('Rhea winter drawings must preserve scene registration')
        self._read_image = read_image
        self.rested = self._views('rested', animated=False)
        self.energy = self._views('energy', animated=True)
        opening = self.manifest['opening']
        self.opening = self._image(opening['file'], tuple(opening['canvas']))
        self.opening_anchor = tuple(opening['anchor'])
        if self.opening.get_size() != (64, 64) or self.opening_anchor != (32, 54):
            raise ValueError('Rhea opening winter sprite must preserve combat-scale registration')
        self.awakening = self.manifest['awakening']
        # A nested frames table allows the expression source/mask metadata to
        # travel with the eight facial drawings, rather than duplicate it.
        expressions = self.awakening.get('frames', self.awakening)
        if set(expressions) != EXPRESSIONS:
            raise ValueError('Rhea winter awakening requires all eight expressions')
        self.expressions = {name:self._image(entry['file'])
                            for name,entry in expressions.items()}
        self.expression_entries = expressions
        self.actions = {}
        for name, entry in self.manifest['actions'].items():
            self.actions[name] = self._sequence(entry)
        if not {'staff_sweep', 'cast', 'cast_rear'} <= self.actions.keys():
            raise ValueError('Rhea winter action drawings are incomplete')

    def _image(self, filename, canvas=(128, 128)):
        path = (self.root/filename).resolve()
        if not path.is_relative_to(self.root.resolve()):
            raise ValueError('Rhea winter image leaves its asset folder')
        image = self._read_image(path)
        if image.get_size() != canvas:
            raise ValueError(f'Rhea winter image has an unregistered canvas: {filename}')
        return image

    def _sequence(self, entry):
        frames = entry['frames']
        if not frames:
            raise ValueError('Rhea winter animation has no drawings')
        sequence = []
        for frame in frames:
            duration = frame.get('duration_ms', 140)/1000
            if not math.isfinite(duration) or duration <= 0:
                raise ValueError('Rhea winter frame duration must be positive')
            sequence.append((self._image(frame['file']), duration))
        return sequence

    def _views(self, family, *, animated):
        records = self.manifest[family]
        if set(records) != VIEWS:
            raise ValueError(f'Rhea winter {family} needs all eight directional views')
        return {name:self._sequence(entry) if animated else [(self._image(entry['file']), 1.)]
                for name,entry in records.items()}

    @staticmethod
    def _nearest(records, azimuth):
        return min(records, key=lambda name:abs(
            (azimuth-records[name]['view_azimuth_deg']+180)%360-180))

    @staticmethod
    def frame(sequence, elapsed, *, reduced=False):
        if reduced:
            return sequence[0][0], 0
        clock = max(0., elapsed) % sum(duration for _,duration in sequence)
        for index,(image,duration) in enumerate(sequence):
            if clock < duration:
                return image, index
            clock -= duration
        return sequence[-1][0], len(sequence)-1

    def hold(self, azimuth, elapsed, *, reduced=False):
        energized = elapsed >= self.BREAKOUT-1e-10
        family = 'energy' if energized else 'rested'
        name = self._nearest(self.manifest[family], azimuth)
        sequence = self.energy[name] if energized else self.rested[name]
        image, index = self.frame(sequence, elapsed-self.BREAKOUT, reduced=reduced)
        return image, self.data, f'winter_{family}_{name}_{index:02d}'

    def action(self, action, azimuth, progress, elapsed, *, reduced=False):
        names = [name for name in self.actions if name == action or name.startswith(action+'_')]
        if not names:
            return self.hold(azimuth, elapsed, reduced=reduced)
        name = self._nearest({name:self.manifest['actions'][name] for name in names}, azimuth)
        sequence = self.actions[name]
        index = min(len(sequence)-1, max(0, int(progress*len(sequence))))
        return sequence[index][0], self.data, name

    def eye_positions(self, expression):
        return self.expression_entries[expression].get('eyes', [])

    def draw_energy(self, canvas, camera, position, elapsed, *, reduced=False):
        """Sparse rising motes reinforce the outward pressure in the drawings."""
        if elapsed < self.BREAKOUT or reduced:
            return
        strength = min(1., (elapsed-self.BREAKOUT)/.25)
        layer = pygame.Surface(canvas.get_size(), pygame.SRCALPHA)
        clock = elapsed-self.BREAKOUT
        for index in range(7):
            height = ((clock*.38+index*.237) % 1.)*2.15
            angle = index*2.4+clock*.35
            radius = .22+.23*height
            point = pygame.Vector3(position)+pygame.Vector3(
                math.cos(angle)*radius, height, math.sin(angle)*radius)
            projected = camera.project(point)
            if projected is None:
                continue
            x, y, depth = projected
            fade = math.sin(height/2.15*math.pi)*strength
            size = max(1, min(2, round(camera.focal/depth*.012)))
            pygame.draw.circle(layer, (60, 255, 119, round(105*fade)),
                               (round(x),round(y)), size)
        canvas.blit(layer, (0, 0))
