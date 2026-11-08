"""Crystal-lit cave scenes built on the ordinary world and character renderer.

The light field is separate from the hard-edged pixel scenery. Each source owns
a small, wall-clipped falloff cache; drawing only adds visible sources to a
half-resolution viewport before multiplying it into the rendered world. No
lighting operation touches the UI or changes collision.
"""
from __future__ import annotations

from collections import OrderedDict
import math

import numpy as np
import pygame

from main import World


class CaveLighting:
    SCALE = 2
    LEVELS = 20
    MAX_CACHED = 32
    PERIOD_MS = 6000
    AMBIENT = (102, 111, 132)

    def __init__(self, world):
        self.world = world
        self.sources = world.data.get('cave', {}).get('lights', [])
        # A one-byte collision view makes light visibility a small vectorized
        # operation at scene load, instead of thousands of Python ray steps.
        collision = world.blocked.to_surface(setcolor='white', unsetcolor='black')
        self._solid = pygame.surfarray.array3d(collision)[:, :, 0] > 0
        self._cache = OrderedDict()
        self._field = self._expanded = None
        self._last_levels = {}
        self.elapsed_ms = 0
        self.reduced_motion = False

    @classmethod
    def pulse(cls, elapsed_ms, phase=0., reduced_motion=False):
        # A long smooth breath, with a fixed readable state for reduced motion.
        if reduced_motion:return .75
        return .5-.5*math.cos(2*math.pi*elapsed_ms/cls.PERIOD_MS+phase)

    def _blocked(self, x, y):
        width, height = self.world.size
        return (x < 0 or y < 0 or x >= width or y >= height
                or bool(self._solid[x, y]))

    def _origin(self, source):
        x, y = (round(value) for value in source['position'])
        if not self._blocked(x, y):return x, y
        # Wall sockets can be authored just inside their solid base. Snap the
        # emission root to the nearest free floor without changing the artwork.
        for radius in range(1, 49):
            for dx, dy in ((0, radius), (-radius, 0), (radius, 0), (0, -radius)):
                if not self._blocked(x+dx, y+dy):return x+dx, y+dy
        raise ValueError('Cave light has no exposed floor root: '+str(source['position']))

    def _build(self, index):
        source = self.sources[index]
        radius = max(24, min(320, round(source.get('radius', 160))))
        diameter = 2*math.ceil(radius/self.SCALE)+1
        origin = self._origin(source)
        left = origin[0]-radius;top = origin[1]-radius
        # Clip at the first solid pixel. A second polygon reaches a short way
        # into *solid wall only*, allowing wall faces/crystals to catch light
        # while keeping a neighboring room's walkable floor dark.
        angles = np.arange(512, dtype=np.float64)*2*math.pi/512
        dx, dy = np.cos(angles), np.sin(angles)
        steps = np.arange(1, radius+1, dtype=np.float64)
        rx = np.rint(origin[0]+dx[:, None]*steps).astype(np.int32)
        ry = np.rint(origin[1]+dy[:, None]*steps).astype(np.int32)
        width, height = self.world.size
        outside = (rx < 0) | (ry < 0) | (rx >= width) | (ry >= height)
        hits = outside | self._solid[np.clip(rx, 0, width-1), np.clip(ry, 0, height-1)]
        distances = np.where(hits.any(axis=1), hits.argmax(axis=1), radius)
        floor_outline = np.column_stack(((radius+dx*distances)/self.SCALE,
                                         (radius+dy*distances)/self.SCALE)).tolist()
        wall_distances = np.minimum(radius, distances+42)
        wall_outline = np.column_stack(((radius+dx*wall_distances)/self.SCALE,
                                        (radius+dy*wall_distances)/self.SCALE)).tolist()
        visible = pygame.Surface((diameter, diameter))
        visible.fill('black');pygame.draw.polygon(visible, 'white', floor_outline)
        walls = pygame.Surface((diameter, diameter))
        walls.fill('black');pygame.draw.polygon(walls, 'white', wall_outline)
        visibility = pygame.surfarray.array3d(visible)[:, :, 0] > 0
        wall_visibility = pygame.surfarray.array3d(walls)[:, :, 0] > 0
        # Sampling whole low-resolution cells conservatively avoids thin wall
        # edge leaks when the viewport is expanded back to native resolution.
        wx = left+np.arange(diameter)*self.SCALE
        wy = top+np.arange(diameter)*self.SCALE
        solid = self._solid[np.clip(wx, 0, width-1)[:, None],
                            np.clip(wy, 0, height-1)[None, :]]
        solid |= ((wx < 0) | (wx >= width))[:, None]
        solid |= ((wy < 0) | (wy >= height))[None, :]
        visibility |= wall_visibility & solid
        axis = np.arange(diameter, dtype=np.float32)*self.SCALE-radius
        distance = np.sqrt(axis[:, None]**2+axis[None, :]**2)/radius
        color = np.array(source.get('color', (130, 210, 230)), dtype=np.float32)
        gain = max(.25, min(1.5, float(source.get('gain', 1.0))))
        frames = []
        for level in range(self.LEVELS):
            pulse = level/(self.LEVELS-1)
            # The lit radius expands a little at the crest, as well as gaining
            # brightness. Its edges always stay within the cached occlusion.
            falloff = np.clip(1-distance/(.86+.14*pulse), 0, 1)**1.35
            power = (.46+.48*pulse)*gain
            values = np.minimum(255, falloff[:, :, None]*color*power)
            values *= visibility[:, :, None]
            frames.append(pygame.surfarray.make_surface(values.astype(np.uint8)))
        return {'position':(left, top), 'rect':pygame.Rect(left, top, radius*2, radius*2),
                'frames':tuple(frames), 'origin':origin}

    def _source(self, index):
        if index not in self._cache:
            self._cache[index] = self._build(index)
            if len(self._cache) > self.MAX_CACHED:self._cache.popitem(last=False)
        else:self._cache.move_to_end(index)
        return self._cache[index]

    def prewarm(self):
        """Build authored scenes' fields during loading, never while walking.

        A scene larger than the explicit source budget needs to be split or
        have its lighting simplified; silently evicting its masks would cause
        repeated cold-cache pauses as the camera moves.
        """
        if len(self.sources) > self.MAX_CACHED:
            raise ValueError('Cave scene exceeds the cached light budget')
        for index in range(len(self.sources)):self._source(index)

    def apply(self, target, camera, elapsed_ms, *, reduced_motion=False, emissions=()):
        self.elapsed_ms = elapsed_ms
        self.reduced_motion = bool(reduced_motion)
        width, height = target.get_size()
        small_size = (math.ceil(width/self.SCALE), math.ceil(height/self.SCALE))
        if self._field is None or self._field.get_size() != small_size:
            self._field = pygame.Surface(small_size)
            self._expanded = pygame.Surface((width, height))
        ambient = tuple(self.world.data.get('cave', {}).get('ambient', self.AMBIENT))
        self._field.fill(ambient)
        viewport = pygame.Rect(camera, (width, height))
        self._last_levels = {}
        for index, source in enumerate(self.sources):
            radius = max(24, min(320, round(source.get('radius', 160))))
            sx, sy = source['position']
            if not viewport.colliderect(pygame.Rect(sx-radius-48, sy-radius-48,
                                                   radius*2+96, radius*2+96)):continue
            cached = self._source(index)
            pulse = (1. if source.get('steady') else
                     self.pulse(elapsed_ms, source.get('phase', 0.), reduced_motion))
            level = round(pulse*(self.LEVELS-1))
            self._last_levels[index] = level
            x, y = cached['position']
            self._field.blit(cached['frames'][level],
                             ((x-camera[0])//self.SCALE, (y-camera[1])//self.SCALE),
                             special_flags=pygame.BLEND_RGB_ADD)
        # Native-pixel scaling keeps occlusion boundaries crisp and never
        # interpolates light across a solid wall into an unlit room.
        pygame.transform.scale(self._field, (width, height), self._expanded)
        # Self-emission belongs to the illumination field, never a sprite
        # redraw. An actor standing in front therefore keeps its own pixels
        # and simply catches the crystal light. These native masks preserve
        # exact facet silhouettes, including tips inside an opaque wall face.
        for surface, position, pulse in emissions:
            rect = surface.get_rect(topleft=position)
            if not rect.colliderect(viewport):continue
            surface.set_alpha(round(155+85*pulse))
            self._expanded.blit(surface, (position[0]-camera[0], position[1]-camera[1]))
        target.blit(self._expanded, (0, 0), special_flags=pygame.BLEND_RGB_MULT)

    def snapshot(self):
        return {'cached_sources':len(self._cache), 'visible_sources':len(self._last_levels),
                'cached_frames':sum(len(item['frames']) for item in self._cache.values()),
                'cache_bytes':sum(frame.get_pitch()*frame.get_height()
                                  for item in self._cache.values() for frame in item['frames']),
                'levels':dict(self._last_levels), 'reduced_motion':self.reduced_motion}


class SanctuaryCaveWorld(World):
    is_sanctuary_cave = True

    def __init__(self, path, image_cache=None):
        super().__init__(path, image_cache)
        self.lighting = CaveLighting(self)
        self.lighting.prewarm()
        self._crystals = []
        emission_cache = {}
        for record in self.entities:
            index = record.get('light_index')
            if index is None:continue
            if not 0 <= index < len(self.lighting.sources):
                raise ValueError('Unknown cave crystal light: '+record['id'])
            frames = tuple(record['surfaces'])
            record['surfaces'] = [frames[0]]
            record['animation_stopped'] = True
            record['reduced_motion_frame'] = 0
            emissions = []
            for frame in frames:
                if id(frame) not in emission_cache:
                    color = pygame.surfarray.array3d(frame)
                    alpha = pygame.surfarray.array_alpha(frame)
                    # Bright mineral facets emit; muted grey/green stone
                    # sockets and transparent margins retain ordinary shading.
                    mineral = ((color.max(axis=2) >= 110)
                               & (((color.max(axis=2)-color.min(axis=2)) >= 28)
                                  | (color.min(axis=2) >= 180))
                               & (alpha > 0))
                    mask = pygame.Surface(frame.get_size(), pygame.SRCALPHA)
                    mask.fill((255, 255, 255, 0))
                    view = pygame.surfarray.pixels_alpha(mask)
                    view[:, :] = np.where(mineral, alpha, 0)
                    del view
                    emission_cache[id(frame)] = mask
                emissions.append(emission_cache[id(frame)])
            self._crystals.append((record, frames, index, tuple(emissions)))

    def location(self, position):
        landmarks = self.data.get('landmarks', [])
        if landmarks:
            nearest = min(landmarks, key=lambda item:
                          pygame.Vector2(item['position']).distance_squared_to(position))
            if pygame.Vector2(nearest['position']).distance_to(position) < nearest.get('radius', 180):
                return nearest['name']
        return self.data['name']

    def draw(self, target, camera, player, elapsed_ms, include_ui=True, party_actors=()):
        emissions = []
        for record, frames, index, masks in self._crystals:
            source = self.lighting.sources[index]
            pulse = self.lighting.pulse(elapsed_ms, source.get('phase', 0.), self.reduced_motion)
            frame = round(pulse*(len(frames)-1))
            record['surfaces'][0] = frames[frame]
            emissions.append((masks[frame], record['position'], pulse))
        # All ordinary actors and foreground objects participate before light.
        super().draw(target, camera, player, elapsed_ms, False, party_actors=party_actors)
        self.lighting.apply(target, camera, elapsed_ms, reduced_motion=self.reduced_motion,
                            emissions=emissions)

