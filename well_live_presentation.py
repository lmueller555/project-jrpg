"""Native Pygame well layers; ordinary gameplay never imports asset-tool Pillow.

This is the runtime counterpart of the offline authoring presenter. Checked-in
native drawings supply the structure, crank, winding, hook, water and pail. Only
the straight rope and masked emergence droplets are drawn at runtime.
"""
from pathlib import Path
import json

import numpy as np
import pygame

ROOT = Path(__file__).resolve().parent
MANIFEST = 'assets/terrain/eldenmere/well_hd/mechanism/manifest.json'


def _field(state, name, default=None):
    return state.get(name, default) if isinstance(state, dict) else getattr(state, name, default)


class WellLivePresentation:
    """Read-only snapshot presentation with preloaded native components."""
    def __init__(self, world, root=ROOT):
        self.root = Path(root)
        self.world = world
        self.manifest = json.loads((self.root/MANIFEST).read_text())
        self.pack = Path(MANIFEST).parent
        self.base = json.loads((self.root/self.manifest['base_pack']).read_text())
        self.base_pack = Path(self.manifest['base_pack']).parent
        self.size = tuple(self.manifest['artwork_size'])
        self.density = self.manifest['artwork_pixels_per_world_pixel']
        if self.density != 2 or self.size != tuple(self.base['assembly']['artwork_size']):
            raise ValueError('Live well presentation density/canvas mismatch')
        self.layers = {r['id']: self._load(self.base_pack/r['file']) for r in self.base['layers']}
        self.layer_records = {r['id']: r for r in self.base['layers']}
        self.mask_sources = {r['id']: self._load(self.base_pack/r['file']) for r in self.base['masks']}
        # Mask PNGs use native grayscale values, independently of their RGBA
        # loader representation. Arrays are x/y, as required by surfarray.
        self.masks = {name: pygame.surfarray.array3d(image)[:, :, 0].copy()
                      for name, image in self.mask_sources.items()}
        self.pails = {r['units']: self._load(self.base_pack/r['file']) for r in self.base['pail']['variants']}
        self.pail_grip = tuple(self.base['pail']['grip_logical'])
        self.pail_base_offset_artwork = round((self.base['pail']['support_logical'][1]-self.pail_grip[1])*self.density)
        self.cranks = [self._load(self.pack/r['file']) for r in self.manifest['crank']['frames']]
        self.spindles = [self._load(self.pack/path) for path in self.manifest['spindle']['frames']]
        self.hook = self._load(self.pack/self.manifest['hook']['file'])
        self.water = [self._load(self.pack/path) for path in self.manifest['water']['ambient_frames']]
        self.contacts = [self._load(self.pack/path) for path in self.manifest['water']['contact_frames']]
        self.under = self._canvas()
        for name in ('contact_shadow', 'stone_far', 'water', 'supports', 'windlass'):
            image = self.layers[name].copy()
            opacity = self.layer_records[name]['opacity']
            if opacity != 1:
                alpha = pygame.surfarray.pixels_alpha(image)
                alpha[:] = np.rint(alpha*opacity).astype(np.uint8)
                del alpha
            self.under.blit(image, (0, 0))
        self.front = self._canvas()
        self.front.blit(self.layers['stone_near'], (0, 0))
        self.front.blit(self.layers['canopy'], (0, 0))
        self.static = self.under.copy()
        self.static.blit(self.front, (0, 0))
        self.water_plane_artwork = round(self.base['geometry']['anchors_logical']['water_contact'][1]*self.density)
        self.submerged_mask = self.masks['water'].copy()
        self.submerged_mask[:, :self.water_plane_artwork] = 0
        structural = np.where(pygame.surfarray.array_alpha(self.static) == 255, 255, 0).astype(np.int16)
        near_coping = np.clip(structural-self.masks['water'], 0, 255).astype(np.uint8)
        near_coping[:, :self.water_plane_artwork] = 0
        self.shaft_front_mask = self._multiply(near_coping, self.masks['aperture'])
        self.aperture_top = int(np.nonzero(self.masks['aperture'])[1].min())

    def _load(self, path):
        if hasattr(self.world, 'image'):
            return self.world.image(path.as_posix())
        return pygame.image.load(str(self.root/path))

    def _canvas(self):
        return pygame.Surface(self.size, pygame.SRCALPHA)

    @staticmethod
    def _multiply(first, second):
        return (first.astype(np.uint16)*second//255).astype(np.uint8)

    @staticmethod
    def _subtract(first, second):
        return np.maximum(first.astype(np.int16)-second, 0).astype(np.uint8)

    def pose_key(self, state, ambient_ms=0, reduced_motion=False):
        grip = _field(state, 'bucket_grip_local', (36, 74))
        origin = _field(state, 'rope_origin_local', (36, 53))
        phase = 0 if reduced_motion else int(ambient_ms//self.manifest['water']['frame_duration_ms']) % len(self.water)
        effect = min(len(self.contacts)-1, max(0, int(_field(state, 'phase_progress', 0)*len(self.contacts))))
        return (_field(state, 'phase_id', 'idle'),
                tuple(round(v*self.density) for v in grip),
                tuple(round(v*self.density) for v in origin),
                bool(_field(state, 'rope_deployed', True)),
                bool(_field(state, 'hook_visible', True)),
                _field(state, 'pail_owner', 'actor'),
                int(_field(state, 'water_units', 0)),
                _field(state, 'bucket_region', 'loading_foreground'),
                int(_field(state, 'crank_sample', 0)) % len(self.cranks),
                bool(_field(state, 'bucket_submerged', False)),
                bool(_field(state, 'water_contact', False)), phase, effect,
                bool(reduced_motion))

    def _moving(self, key):
        phase, grip, origin, rope, hook, owner, units, region, crank, submerged, contact, water_phase, effect_phase, reduced = key
        motion = self._canvas()
        hook_meta = self.manifest['hook']
        attachment = hook_meta['attachment_anchor_artwork']
        rope_anchor = hook_meta['rope_anchor_artwork']
        hook_xy = (grip[0]-attachment[0], grip[1]-attachment[1])
        rope_end = (hook_xy[0]+rope_anchor[0], hook_xy[1]+rope_anchor[1])
        if rope:
            palette = self.manifest['palette']
            pygame.draw.line(motion, palette['rope_dark'], origin, rope_end,
                             self.manifest['rope']['outline_width_artwork'])
            pygame.draw.line(motion, palette['rope_light'], origin, rope_end,
                             self.manifest['rope']['strand_width_artwork'])
        if hook:
            motion.blit(self.hook, hook_xy)
        if owner == 'well':
            if units not in self.pails:
                raise ValueError('Unsupported well pail water level')
            xy = tuple(round(grip[i]-self.pail_grip[i]*self.density) for i in (0, 1))
            motion.blit(self.pails[units], xy)
        if region == 'shaft':
            allowed = self.masks['aperture'].copy()
            allowed[:, :self.aperture_top] = 255
            alpha = pygame.surfarray.pixels_alpha(motion)
            value = self._multiply(alpha, allowed)
            value = self._subtract(value, self.shaft_front_mask)
            if submerged:
                value = self._subtract(value, self.submerged_mask)
            alpha[:] = value
            del alpha
        return motion

    def render_layers(self, state, ambient_ms=0, reduced_motion=False):
        key = self.pose_key(state, ambient_ms, reduced_motion)
        phase, grip, origin, rope, hook, owner, units, region, crank, submerged, contact, water_phase, effect_phase, reduced = key
        back = self.under.copy()
        back.blit(self.water[water_phase], (0, 0))
        back.blit(self.spindles[crank], (0, 0))
        moving = self._moving(key)
        if region != 'loading_foreground':
            back.blit(moving, (0, 0))
        front = self.front.copy()
        if region == 'loading_foreground':
            front.blit(moving, (0, 0))
        front.blit(self.cranks[crank], (0, 0))
        if contact and phase in ('lower', 'fill'):
            front.blit(self.contacts[effect_phase], (0, 0))
        if phase == 'raise' and owner == 'well' and not submerged:
            drops = self._canvas()
            for dx, dy in ((-3, 1+effect_phase), (4, 5+effect_phase)):
                x, y = grip[0]+dx, grip[1]+self.pail_base_offset_artwork+dy
                if 0 <= x < self.size[0] and 0 <= y < self.size[1]:
                    drops.set_at((x, y), self.manifest['palette']['glint'])
            alpha = pygame.surfarray.pixels_alpha(drops)
            alpha[:] = self._multiply(alpha, self.masks['water'])
            del alpha
            front.blit(drops, (0, 0))
        return back, front
