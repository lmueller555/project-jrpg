"""Source-registered Fire Veinhold power flow and slow emergency beacons."""
from __future__ import annotations

import math
import pygame


def _point(value, bounds):
    if (not isinstance(value, list) or len(value) != 2
            or any(type(v) not in (int, float) or not math.isfinite(v)
                   or not 0 <= v <= limit for v, limit in zip(value, bounds))):
        raise ValueError('Facility landmark leaves source artwork')
    return tuple(value)


def _along(points, fraction):
    lengths = [math.dist(a, b) for a, b in zip(points, points[1:])]
    remaining = max(0., min(1., fraction))*sum(lengths)
    for a, b, length in zip(points, points[1:], lengths):
        if remaining <= length:
            return tuple(x+(y-x)*remaining/length for x, y in zip(a, b))
        remaining -= length
    return points[-1]


class CinematicFacility:
    def __init__(self, data, bounds):
        self.beacons, self.conduits = [], []
        if not isinstance(data, dict):raise ValueError('Invalid facility metadata')
        for record in data['beacons']:
            phase = record['phase']
            if type(phase) not in (int, float) or not math.isfinite(phase):
                raise ValueError('Invalid warning beacon phase')
            self.beacons.append((_point(record['origin'], bounds), phase))
        for record in data['conduits']:
            points = tuple(_point(p, bounds) for p in record['points'])
            phase = record['phase']
            if (not 2 <= len(points) <= 32 or any(a == b for a, b in zip(points, points[1:]))
                    or type(phase) not in (int, float) or not math.isfinite(phase)):
                raise ValueError('Invalid aether conduit')
            self.conduits.append((record['id'], points, phase))
        if not 1 <= len(self.beacons) <= 32 or not 1 <= len(self.conduits) <= 8:
            raise ValueError('Invalid facility effect count')
        self.center = _point(data['reservoir']['center'], bounds)
        self.radii = _point(data['reservoir']['radii'], (200, 100))
        if min(self.radii) <= 0:raise ValueError('Invalid reservoir interior')

    def samples(self, seconds, reduced_motion=False):
        if type(seconds) not in (int, float) or not math.isfinite(seconds) or seconds < 0:
            raise ValueError('Invalid facility clock')
        beacons = [{'origin':point, 'strength':.7 if reduced_motion else
                    .3+.7*(.5+.5*math.sin(seconds*math.tau/3.2+phase))**3}
                   for point, phase in self.beacons]
        conduits = []
        for identifier, points, phase in self.conduits:
            fraction = .6 if reduced_motion else (seconds*.16+phase)%1.
            conduits.append({'id':identifier, 'from':_along(points, fraction-.035),
                             'to':_along(points, fraction+.035)})
        embers = []
        clock = 0. if reduced_motion else seconds
        for index in range(14):
            angle = index*2.399963+clock*.12
            radius = math.sqrt((index+.5)/14.)*.86
            embers.append((self.center[0]+self.radii[0]*radius*math.cos(angle),
                           self.center[1]+self.radii[1]*radius*math.sin(angle)-2.*math.sin(clock*.8+index)))
        return {'beacons':beacons, 'conduits':conduits, 'embers':embers}

    @staticmethod
    def _halo(target, center, radius, color, strength):
        radius = max(2, round(radius))
        halo = pygame.Surface((radius*2+1, radius*2+1), pygame.SRCALPHA)
        for r in range(radius, 0, -1):
            weight = (1.-r/radius)**2*strength
            pygame.draw.circle(halo, tuple(round(c*weight) for c in color), (radius, radius), r)
        target.blit(halo, (round(center[0])-radius, round(center[1])-radius), special_flags=pygame.BLEND_RGB_ADD)

    def draw(self, target, state, scale, origin):
        def project(point):return tuple(round(o+p*scale) for o, p in zip(origin, point))
        for record in state['beacons']:
            point = project(record['origin'])
            if not target.get_rect().inflate(30, 30).collidepoint(point):continue
            self._halo(target, point, 8*scale, (190, 16, 8), record['strength'])
            pygame.draw.circle(target, (round(150+105*record['strength']), 36, 24), point, max(1, round(scale)))
        for record in state['conduits']:
            pygame.draw.line(target, (255, 208, 95), project(record['from']), project(record['to']), max(1, round(scale)))
        for ember in state['embers']:
            pygame.draw.circle(target, (255, 220, 126), project(ember), max(1, round(scale)))
