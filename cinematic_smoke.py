"""Deterministic textured billows anchored in a cinematic's source artwork.

Particles grow, rise, drift and fade on the shot clock. Drawing never mutates
simulation state, so pauses, seeks, reduced motion and Gallery restarts agree.
"""
from __future__ import annotations

import math

import pygame


def _smooth(value):
    value = max(0., min(1., value))
    return value*value*(3.-2.*value)


class CinematicSmoke:
    def __init__(self, texture, emitters, bounds):
        if not isinstance(emitters, list) or not 1 <= len(emitters) <= 8:
            raise ValueError('Invalid cinematic smoke emitters')
        self.emitters = []
        self.textures = {}
        identifiers = set()
        for source in emitters:
            if not isinstance(source, dict):raise ValueError('Invalid smoke record')
            record = dict(source)
            identifier = record.get('id')
            if not isinstance(identifier, str) or not identifier or identifier in identifiers:
                raise ValueError('Duplicate or invalid smoke identifier')
            identifiers.add(identifier)
            origin = record.get('origin')
            if (not isinstance(origin, list) or len(origin) != 2
                    or any(type(v) not in (int, float) or not math.isfinite(v)
                           or not 0 <= v <= limit for v, limit in zip(origin, bounds))):
                raise ValueError('Smoke vent leaves source artwork')
            for key, low, high in (('interval', .15, 2.), ('lifetime', 1., 16.),
                    ('rise', 0., 30.), ('wind', -30., 30.), ('start_size', 1., 100.),
                    ('end_size', 1., 100.), ('opacity', 1., 255.)):
                value = record.get(key)
                if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
                    raise ValueError('Invalid smoke '+key)
            tint = record.get('tint')
            if (not isinstance(tint, list) or len(tint) != 3
                    or any(type(v) is not int or not 0 <= v <= 255 for v in tint)
                    or type(record.get('seed')) is not int):
                raise ValueError('Invalid smoke palette or seed')
            # Copy nested authored values so external metadata cannot move vents.
            record['origin'] = tuple(origin)
            record['tint'] = tuple(tint)
            self.emitters.append(record)
            image = texture.copy()
            image.fill((*tint, 255), special_flags=pygame.BLEND_RGBA_MULT)
            self.textures[identifier] = image

    def samples(self, seconds, reduced_motion=False):
        if type(seconds) not in (int, float) or not math.isfinite(seconds) or seconds < 0:
            raise ValueError('Invalid smoke clock')
        particles = []
        comfort = .6 if reduced_motion else 1.
        for record in self.emitters:
            interval, lifetime = record['interval'], record['lifetime']
            # Negative births prewarm the plume: it is already billowing when
            # the camera reveals it. Work stays bounded even after a long seek.
            first = math.floor((seconds-lifetime)/interval)
            last = math.floor(seconds/interval)
            for serial in range(first, last+1):
                age = seconds-serial*interval
                if not 0 <= age < lifetime:continue
                fraction = age/lifetime
                phase = ((serial*1103515245+record['seed']*12345)&0x7fffffff)/0x7fffffff*math.tau
                # Each lobe follows a slightly different stream through the
                # plume, rather than forming identical beads on a straight line.
                x = (record['origin'][0]+comfort*record['wind']*age
                     +comfort*math.sin(phase)*18.*fraction
                     +comfort*math.sin(age*1.3+phase)*(3.+fraction*10.)*fraction)
                y = record['origin'][1]-record['rise']*age+math.cos(phase)*fraction*7.
                size = record['start_size']+(record['end_size']-record['start_size'])*math.sqrt(fraction)
                alpha = round(record['opacity']*min(1., age/.6)*(1.-_smooth(fraction)))
                if alpha:
                    particles.append({'id':record['id'], 'serial':serial, 'age':age,
                                      'position':[x, y], 'size':size, 'alpha':alpha})
        return particles

    def draw(self, target, particles, scale, origin):
        for particle in sorted(particles, key=lambda value:value['age'], reverse=True):
            size = max(1, round(particle['size']*scale))
            x = round(origin[0]+particle['position'][0]*scale-size/2)
            y = round(origin[1]+particle['position'][1]*scale-size/2)
            if not target.get_rect().colliderect(pygame.Rect(x, y, size, size)):continue
            image = pygame.transform.scale(self.textures[particle['id']], (size, size))
            image.set_alpha(particle['alpha'])
            target.blit(image, (x, y))
