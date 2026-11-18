"""Seekable, local mechanical-bolt flight and impact, in battle world pixels.

The scene supplies the authored muzzle and authoritative impact event. No random
state, timers, asset reads, camera impulse, or combat mutation belongs here.
The sampled projectile point is its leading steel tip, not its centre.
"""
from __future__ import annotations

import math
import pygame


GLINT_SECONDS = .055
SPARK_SECONDS = .115
FLECK_SECONDS = .28
DUST_SECONDS = .48


def _xy(point):return round(point[0]), round(point[1])


def _color(rgb, alpha):return (*rgb, round(255*max(0., min(1., alpha))))


def _heading(origin, target):
    delta = pygame.Vector2(target)-origin
    return delta.normalize() if delta.length_squared() else pygame.Vector2(-1, 0)


class BoltShotEffects:
    """A short physical silhouette and moving smear, never a glowing orb."""
    OUTLINE = (49, 41, 33)
    BRASS = (184, 131, 66)
    STEEL = (194, 204, 201)
    LIGHT = (247, 229, 179)
    DUST = (139, 119, 87)

    def __init__(self):self._layer = None

    def _canvas(self, canvas):
        if self._layer is None or self._layer.get_size() != canvas.get_size():
            self._layer = pygame.Surface(canvas.get_size(), pygame.SRCALPHA)
        self._layer.fill((0, 0, 0, 0))
        return self._layer

    def flight(self, shot, *, reduced_motion=False):
        """Sample short-lived fragments at their historical moving emission point."""
        point = shot.get('projectile')
        if point is None:return None
        tip = pygame.Vector2(point)
        origin, target = pygame.Vector2(shot['origin']), pygame.Vector2(shot['target'])
        heading = _heading(origin, target)
        normal = pygame.Vector2(-heading.y, heading.x)
        fraction = max(0., min(1., shot['fraction']))
        tail = tip-heading*11
        fragments = []
        if not reduced_motion:
            # Each fragment is emitted from the travelling tail, then loses
            # forward velocity and peels sideways. Old emissions die in 35 ms;
            # there is no full muzzle-to-target laser or parked trail sprite.
            for emission, side, life in ((.10, 1, .27), (.28, -1, .24),
                                         (.46, 1, .29), (.65, -1, .23), (.82, 1, .18)):
                age = fraction-emission
                if not 0 <= age < life:continue
                start = origin.lerp(target, emission)-heading*10
                center = start+heading*(age*(target-origin).length()*.25)+normal*(side*(1+age*12))
                fragments.append({'point': tuple(center), 'alpha': (1-age/life)*.55,
                                  'length': 2+age*6})
        return {'tip': tuple(tip), 'tail': tuple(tail), 'heading': tuple(heading),
                'normal': tuple(normal), 'fraction': fraction,
                'smear_length': 0 if reduced_motion else min(16., fraction*60),
                'fragments': fragments, 'reduced_motion': bool(reduced_motion)}

    def draw_flight(self, canvas, shot, *, reduced_motion=False):
        sample = self.flight(shot, reduced_motion=reduced_motion)
        if sample is None:return None
        layer = self._canvas(canvas)
        tip, tail = pygame.Vector2(sample['tip']), pygame.Vector2(sample['tail'])
        heading, normal = pygame.Vector2(sample['heading']), pygame.Vector2(sample['normal'])
        smear = sample['smear_length']
        if smear:
            pygame.draw.polygon(layer, _color(self.BRASS, .27),
                [_xy(tail-heading*smear), _xy(tail+normal*2), _xy(tail-normal*2)])
            pygame.draw.line(layer, _color(self.LIGHT, .38), _xy(tail-heading*min(smear, 9)), _xy(tail), 1)
        for record in sample['fragments']:
            point = pygame.Vector2(record['point'])
            pygame.draw.line(layer, _color(self.BRASS, record['alpha']), _xy(point),
                             _xy(point-heading*record['length']), 1)
        # Dark, pointed contour; brass shaft; steel cutting head. Its leading
        # vertex is exactly the impact-bound tip supplied by the shot clock.
        contour = [tip, tip-heading*4+normal*2, tail+normal,
                   tail-heading, tail-normal, tip-heading*4-normal*2]
        pygame.draw.polygon(layer, (*self.OUTLINE, 255), [_xy(p) for p in contour])
        pygame.draw.line(layer, (*self.BRASS, 255), _xy(tail), _xy(tip-heading*4), 2)
        pygame.draw.polygon(layer, (*self.STEEL, 255),
            [_xy(tip), _xy(tip-heading*4+normal), _xy(tip-heading*3-normal)])
        pygame.draw.line(layer, (*self.LIGHT, 255), _xy(tail+normal), _xy(tip-heading*4+normal), 1)
        canvas.blit(layer, (0, 0))
        return sample

    def impact(self, point, age, direction=(-1, 0), *, reduced_motion=False):
        """Contact glint, directional fast sparks, weighted flecks, slower dust."""
        if isinstance(age, bool) or not isinstance(age, (float, int)) or not math.isfinite(age):
            raise ValueError('Invalid bolt impact age')
        point = pygame.Vector2(point)
        heading = _heading((0, 0), direction)
        normal = pygame.Vector2(-heading.y, heading.x)
        glint = 1-age/GLINT_SECONDS if 0 <= age < GLINT_SECONDS else 0.
        sparks, flecks, dust = [], [], []
        if 0 <= age < SPARK_SECONDS:
            for along, sideways in ((-75, -42), (-105, 12), (-58, 65), (33, -58))[:2 if reduced_motion else 4]:
                velocity = heading*along+normal*sideways
                p = point+velocity*age
                sparks.append({'point': tuple(p), 'end': tuple(p-velocity*.018),
                               'alpha': (1-age/SPARK_SECONDS)*.9})
        if not reduced_motion and 0 <= age < FLECK_SECONDS:
            for along, sideways, lift in ((-24, -12, 38), (-42, 9, 26), (18, 14, 32)):
                p = point+heading*(along*age)+normal*(sideways*age)
                p.y += -lift*age+190*age*age
                flecks.append({'point': tuple(p), 'alpha': 1-age/FLECK_SECONDS,
                               'fall': -lift+380*age})
        if not reduced_motion and .018 <= age < DUST_SECONDS:
            phase = (age-.018)/(DUST_SECONDS-.018)
            for index in range(3):
                p = point-heading*(2+index*2+phase*7)+normal*((index-1)*(1+phase*3))
                p.y += phase*5
                dust.append({'point': tuple(p), 'radius': 1+round(phase*2),
                             'alpha': (1-phase)**2*.34})
        return {'point': tuple(point), 'heading': tuple(heading), 'normal': tuple(normal),
                'glint': glint, 'sparks': sparks, 'flecks': flecks, 'dust': dust,
                'reduced_motion': bool(reduced_motion)}

    def draw_impact(self, canvas, point, age, direction=(-1, 0), *, reduced_motion=False):
        sample = self.impact(point, age, direction, reduced_motion=reduced_motion)
        if not any((sample['glint'], sample['sparks'], sample['flecks'], sample['dust'])):return sample
        layer = self._canvas(canvas)
        point = pygame.Vector2(point)
        heading, normal = pygame.Vector2(sample['heading']), pygame.Vector2(sample['normal'])
        # Dust sits behind the sharper, heavier material, all within a few
        # world pixels of the shoulder. No radial ring or screen-size flash.
        for record in sample['dust']:
            p, radius = record['point'], record['radius']
            pygame.draw.ellipse(layer, _color(self.DUST, record['alpha']),
                (round(p[0])-radius, round(p[1])-1, radius*2+1, 3))
        for record in sample['flecks']:
            p = pygame.Vector2(record['point'])
            pygame.draw.line(layer, _color(self.OUTLINE, record['alpha']), _xy(p),
                             _xy(p+(1, 1 if record['fall'] > 0 else -1)), 2)
            pygame.draw.line(layer, _color(self.BRASS, record['alpha']), _xy(p), _xy(p+(1, 0)), 1)
        for record in sample['sparks']:
            pygame.draw.line(layer, _color(self.LIGHT, record['alpha']),
                             _xy(record['point']), _xy(record['end']), 1)
        if sample['glint']:
            strength = sample['glint']
            pygame.draw.line(layer, _color(self.LIGHT, strength),
                             _xy(point-heading*3), _xy(point+heading*2), 2)
            pygame.draw.line(layer, _color(self.STEEL, strength*.85),
                             _xy(point-normal*3), _xy(point+normal*3), 1)
        canvas.blit(layer, (0, 0))
        return sample
