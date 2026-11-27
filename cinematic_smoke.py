"""Complete authored plume cycles with fixed vent registration and clean alpha.

Adjacent drawings blend in premultiplied space: no moving puff tiles, births,
rectangular particle quads or opacity dip between frames. The scene owns time.
"""
from __future__ import annotations

import math
import pygame


class CinematicSmoke:
    def __init__(self, frames, anchor, emitters, bounds):
        if not isinstance(frames, list) or not 2 <= len(frames) <= 64:
            raise ValueError('Invalid drawn plume cycle')
        size = frames[0][0].get_size()
        for image, duration in frames:
            if image.get_size() != size or not math.isfinite(duration) or duration <= 0:
                raise ValueError('Invalid plume frame')
            rect = image.get_bounding_rect(min_alpha=1)
            if not rect.width or not pygame.Rect(8, 8, size[0]-16, size[1]-16).contains(rect):
                raise ValueError('Plume must have transparent canvas margins')
        if (not isinstance(anchor, list) or len(anchor) != 2
                or any(type(v) is not int or not 0 <= v < limit for v, limit in zip(anchor, size))):
            raise ValueError('Invalid plume vent anchor')
        if not isinstance(emitters, list) or not 1 <= len(emitters) <= 8:
            raise ValueError('Invalid plume emitters')
        self.anchor = tuple(anchor)
        self.frames = frames
        self.duration = sum(duration for _, duration in frames)
        self.emitters, self.art = [], {}
        for record in emitters:
            identifier = record.get('id')
            if not isinstance(identifier, str) or not identifier or identifier in self.art:
                raise ValueError('Invalid plume identifier')
            origin, tint = record.get('origin'), record.get('tint')
            if (not isinstance(origin, list) or len(origin) != 2
                    or any(type(v) not in (int, float) or not math.isfinite(v)
                           or not 0 <= v <= limit for v, limit in zip(origin, bounds))):
                raise ValueError('Invalid plume position')
            for key, low, high in (('scale', .1, 3.), ('opacity', 1., 255.), ('phase_seconds', 0., 100.)):
                value = record.get(key)
                if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
                    raise ValueError('Invalid plume '+key)
            if not isinstance(tint, list) or len(tint) != 3 or any(type(v) is not int or not 0 <= v <= 255 for v in tint):
                raise ValueError('Invalid plume tint')
            self.emitters.append(dict(record, origin=tuple(origin), tint=tuple(tint)))
            colored = []
            for image, _ in frames:
                image = image.copy()
                image.fill((*tint, 255), special_flags=pygame.BLEND_RGBA_MULT)
                image = image.premul_alpha()
                opacity = round(record['opacity'])
                image.fill((opacity,)*4, special_flags=pygame.BLEND_RGBA_MULT)
                colored.append(image)
            self.art[identifier] = colored

    def samples(self, seconds, reduced_motion=False):
        if type(seconds) not in (int, float) or not math.isfinite(seconds) or seconds < 0:
            raise ValueError('Invalid plume clock')
        result = []
        for record in self.emitters:
            time = (seconds*(.7 if reduced_motion else 1.)+record['phase_seconds']) % self.duration
            for index, (_, duration) in enumerate(self.frames):
                if time < duration:break
                time -= duration
            result.append({'id':record['id'], 'frame':index, 'next_frame':(index+1)%len(self.frames),
                           'blend':time/duration, 'origin':record['origin'], 'scale':record['scale']})
        return result

    def draw(self, target, states, scale, origin):
        for state in states:
            first, second = self.art[state['id']][state['frame']].copy(), self.art[state['id']][state['next_frame']].copy()
            weight = round(state['blend']*255)
            first.fill((255-weight,)*4, special_flags=pygame.BLEND_RGBA_MULT)
            second.fill((weight,)*4, special_flags=pygame.BLEND_RGBA_MULT)
            first.blit(second, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
            factor = scale*state['scale']
            image = pygame.transform.scale(first, (round(first.get_width()*factor), round(first.get_height()*factor)))
            point = tuple(round(offset+(position-anchor*state['scale'])*scale)
                          for offset, position, anchor in zip(origin, state['origin'], self.anchor))
            if target.get_rect().colliderect(image.get_rect(topleft=point)):
                target.blit(image, point, special_flags=pygame.BLEND_PREMULTIPLIED)
