"""Explicit nonblocking landmark passes, in logical coordinates at native density.

Placements never define collision. Builders validate physical contact separately.
Only source art is cached; actor-dependent crops live for one draw, at viewport size.
"""
from pathlib import Path
import math
import pygame
from rendering import WorldCanvas, SurfaceCache, immutable, record_art

LAYERS = frozenset(('distant', 'ground', 'overhead'))


class LandmarkLayers:
    def __init__(self, root, records=(), *, budget=16*1024*1024):
        self.root = Path(root)
        self.records = tuple(dict(record) for record in records)
        self.sources = SurfaceCache(budget)
        self.working_bytes = 0
        for record in self.records:
            if record.get('layer') not in LAYERS:
                raise ValueError('Landmark requires an explicit distant/ground/overhead layer')
            if record.get('collision', 'none') != 'none':
                raise ValueError('Landmark artwork cannot define collision')
            if len(record['position']) != 2 or any(value <= 0 for value in record['logical_size']):
                raise ValueError('Invalid logical landmark registration')

    def image(self, record, field='image'):
        key = (field, record[field], tuple(record['logical_size']), record.get('artwork_pixels_per_world_pixel', 2))
        image = self.sources.get(key)
        if image is None:
            raw = immutable(pygame.image.load(str(self.root / record[field])).convert_alpha())
            if field == 'occlusion_mask':
                # Exported authored masks are grayscale PNGs, not RGBA alpha.
                alpha = pygame.surfarray.pixels_alpha(raw)
                alpha[:] = pygame.surfarray.array3d(raw)[:,:,0]
                del alpha
            image = record_art(raw, record, 2)
            self.sources[key] = image
        return image

    def visible(self, viewport, layer):
        # A bounded explicit registry, never the ordinary scenery root neighbourhood.
        return (record for record in self.records if record['layer'] == layer and
                self.bounds(record).colliderect(viewport))

    @staticmethod
    def bounds(record):
        x,y=record['position'];w,h=record['logical_size']
        return pygame.Rect(math.floor(x),math.floor(y),math.ceil(x+w)-math.floor(x),math.ceil(y+h)-math.floor(y))

    @staticmethod
    def visibility_points(actors):
        points = []
        for actor in actors:
            if not getattr(actor, 'story_visible', True) or getattr(actor, 'party_travelling', False):
                continue
            position = getattr(actor, 'story_position', None)
            if position is None:position = actor.position
            points.append((round(position[0]), round(position[1])-18))
        return points

    def draw(self, target, camera, layer, *, actors=(), interaction_points=()):
        viewport = pygame.Rect(camera, target.get_size())
        points = self.visibility_points(actors) + list(interaction_points)
        self.working_bytes = 0
        for record in self.visible(viewport, layer):
            image = self.image(record)
            rect = self.bounds(record)
            position = (record['position'][0]-camera[0], record['position'][1]-camera[1])
            affected = [point for point in points if rect.inflate(44, 56).collidepoint(point)] if layer == 'overhead' else []
            if not affected:
                target.blit(image, position)
                continue
            # A viewport-sized work surface preserves half-unit registration at
            # crop edges without rounding an authored origin into a logical Rect.
            work = WorldCanvas(target.get_size(),pygame.SRCALPHA) if isinstance(target,WorldCanvas) else pygame.Surface(target.get_size(),pygame.SRCALPHA)
            work.blit(image,position)
            mask = self.image(record, 'occlusion_mask') if record.get('occlusion_mask') else image
            coverage_canvas = WorldCanvas(target.get_size(),pygame.SRCALPHA) if isinstance(work,WorldCanvas) else pygame.Surface(target.get_size(),pygame.SRCALPHA)
            coverage_canvas.blit(mask,position)
            factor = 2 if isinstance(work, WorldCanvas) else 1
            raw = work.native if factor == 2 else work
            authored = coverage_canvas.native if factor == 2 else coverage_canvas
            fade = pygame.Surface(raw.get_size(), pygame.SRCALPHA)
            fade.fill((255,255,255,255))
            for x,y in affected:
                pygame.draw.ellipse(fade, (255,255,255,88),
                    ((x-camera[0]-22)*factor, (y-camera[1]-28)*factor, 44*factor, 56*factor))
            # Only authored mask coverage may change; retain surrounding contour.
            alpha = pygame.surfarray.pixels_alpha(fade)
            coverage = pygame.surfarray.array_alpha(authored)
            alpha[coverage == 0] = 255
            del alpha
            raw.blit(fade, (0,0), special_flags=pygame.BLEND_RGBA_MULT)
            if factor == 2:pygame.transform.scale(raw, work.get_size(), work)
            self.working_bytes = max(self.working_bytes, raw.get_pitch()*raw.get_height()*4 + work.get_pitch()*work.get_height()*2)
            target.blit(work, (0,0))
