"""Live well reservation and native depth passes, driven by one mechanism clock.

The gardener advances the controller after real station arrivals. Drawing reads
its frozen snapshot and never consults actor animation time or transfers a pail.
"""
from collections import OrderedDict
from pathlib import Path

import pygame

from rendering import artwork, layer as render_layer, surface_bytes
from well_mechanism import WellMechanism
from well_live_presentation import WellLivePresentation

ROOT = Path(__file__).resolve().parent


class DrawingWell:
    """Exclusive operator reservation and bounded native well presentation."""
    CACHE_ENTRIES = 48

    def __init__(self, world):
        self.world = world
        self.mechanism = self.model = WellMechanism()
        self.presentation = WellLivePresentation(world, root=ROOT)
        contract = self.model.contract
        binding = getattr(world, 'data', {}).get('well_runtime', {})
        self.position = tuple(contract['well_world_origin'])
        if tuple(binding.get('world_origin_logical', self.position)) != self.position:
            raise ValueError('Live well origin differs from the shared mechanism contract')
        depths = binding.get('depth_baselines_logical', {})
        self.depths = (depths.get('back', 840), depths.get('front', 896))
        if self.depths[0] >= self.depths[1]:
            raise ValueError('Live well depth passes must be ordered far then near')
        geometry = contract['geometry']
        self.data = {
            'canvas_size': list(self.presentation.base['geometry']['logical_size']),
            'loading_position': contract['stations']['loading']['feet_world_logical'],
            'operator_position': contract['stations']['operator']['feet_world_logical'],
            'loading_grip': geometry['loading_grip_local'],
            'parked_bucket_grip': geometry['guided_grip_local'],
            'lowered_bucket_grip': geometry['lowered_grip_local'],
            'rope_origin': geometry['rope_origin_local'],
            'crank_pivot': geometry['crank_pivot_local'],
            'phases_ms': contract['phase_durations_ms'],
        }
        self.owner = None
        self.token = None
        self._poses = OrderedDict()
        self._cache_hits = self._cache_misses = 0

    def reserve(self, actor, water_units=0):
        if self.owner is not None:
            return self.token if self.owner is actor else None
        actor_id = actor.data['id']
        token = self.model.reserve(actor_id, actor_id+'.pail', water_units=water_units)
        if token is not None:
            self.owner, self.token = actor, token
        return token

    def signal_ready(self, actor, station):
        return self.owner is actor and self.model.signal_ready(self.token, station)

    def update(self, seconds):
        """Called by the operator's simulation update, never by the renderer."""
        self.model.update(seconds)

    def snapshot(self):
        return self.model.snapshot()

    def drain_events(self):
        return self.model.drain_events()

    def release(self, actor):
        """A full pail leaves with its actor only after completed retrieval."""
        if self.owner is not actor or not self.snapshot().completed:
            return False
        self.owner = self.token = None
        return True

    def reset(self):
        """Reset only with the ambient actor's coordinated reset_cycle()."""
        recovery = self.model.reset()
        self.owner = self.token = None
        return recovery

    @property
    def state(self): return self.snapshot().phase_id

    @property
    def time(self): return self.snapshot().phase_elapsed_ms

    @property
    def progress(self): return self.snapshot().phase_progress

    @property
    def crank_index(self): return self.snapshot().crank_sample

    @property
    def bucket_grip(self): return pygame.Vector2(self.snapshot().bucket_grip_local)

    @property
    def bucket_on_rope(self): return self.snapshot().pail_owner == 'well'

    @property
    def bucket_at_handoff(self):
        state = self.snapshot()
        return state.bucket_region == 'loading_foreground' and state.pail_owner == 'well'

    @property
    def rope_deployed(self): return self.snapshot().rope_deployed

    @property
    def rope_end(self): return pygame.Vector2(self.snapshot().rope_end_local)

    @property
    def draw_level(self): return self.snapshot().water_units

    @staticmethod
    def _native_surface(image):
        return artwork(image, density=2)

    def _layers(self, elapsed_ms):
        state = self.snapshot()
        reduced = bool(getattr(self.world, 'reduced_motion', False))
        key = self.presentation.pose_key(state, elapsed_ms, reduced)
        pair = self._poses.pop(key, None)
        if pair is None:
            self._cache_misses += 1
            pair = tuple(self._native_surface(image) for image in
                         self.presentation.render_layers(state, elapsed_ms, reduced))
        else:
            self._cache_hits += 1
        self._poses[key] = pair
        while len(self._poses) > self.CACHE_ENTRIES:
            self._poses.popitem(last=False)
        return pair

    def draw_layers(self, elapsed_ms):
        """Independent logical/native surfaces with world depth and origin."""
        return tuple((depth, surface.copy(), self.position)
                     for depth, surface in zip(self.depths, self._layers(elapsed_ms)))

    def sprite(self, elapsed_ms):
        """Combined compatibility view; live World uses the two depth passes."""
        image = render_layer(self.data['canvas_size'], pygame.SRCALPHA)
        for surface in self._layers(elapsed_ms): image.blit(surface, (0, 0))
        return image

    def cache_info(self):
        return {'entries': len(self._poses), 'limit': self.CACHE_ENTRIES,
                'surface_bytes': sum(surface_bytes(surface) for pair in self._poses.values()
                                     for surface in pair),
                'max_surface_bytes': self.CACHE_ENTRIES*2*72*88*4*5,
                'hits': self._cache_hits, 'misses': self._cache_misses}
