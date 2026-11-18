"""Side-effect-free native presentation of the staged well mechanism.

The controller owns time, readiness, transfers and water. This renderer reads
only immutable snapshots and uses the retained structural/pail drawings. Nothing
in the ordinary World or Gardener selects this implementation before PR 4.
"""
from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

ROOT = Path(__file__).resolve().parent
MANIFEST = 'assets/terrain/eldenmere/well_hd/mechanism/manifest.json'


def _field(snapshot, name, default=None):
    return snapshot.get(name, default) if isinstance(snapshot, dict) else getattr(snapshot, name, default)


class WellMechanismPresentation:
    """Preloaded 2× components and a bounded cache of quantized native poses."""
    def __init__(self, root=ROOT):
        self.root = Path(root)
        self.manifest = json.loads((self.root/MANIFEST).read_text())
        self.pack = Path(MANIFEST).parent
        self.base = json.loads((self.root/self.manifest['base_pack']).read_text())
        self.base_pack = Path(self.manifest['base_pack']).parent
        self.size = tuple(self.manifest['artwork_size'])
        self.density = self.manifest['artwork_pixels_per_world_pixel']
        if self.density != 2 or self.size != tuple(self.base['assembly']['artwork_size']):
            raise ValueError('Staged well presentation density/canvas mismatch')
        self.layers = {r['id']: self._load(self.base_pack/r['file']) for r in self.base['layers']}
        self.layer_records = {r['id']: r for r in self.base['layers']}
        self.masks = {r['id']: self._load(self.base_pack/r['file'], 'L') for r in self.base['masks']}
        self.pails = {r['units']: self._load(self.base_pack/r['file']) for r in self.base['pail']['variants']}
        self.pail_grip = tuple(self.base['pail']['grip_logical'])
        self.pail_base_offset_artwork = round((self.base['pail']['support_logical'][1]-self.pail_grip[1])*self.density)
        self.cranks = [self._load(self.pack/r['file']) for r in self.manifest['crank']['frames']]
        self.spindles = [self._load(self.pack/path) for path in self.manifest['spindle']['frames']]
        self.hook = self._load(self.pack/self.manifest['hook']['file'])
        self.water = [self._load(self.pack/path) for path in self.manifest['water']['ambient_frames']]
        self.contacts = [self._load(self.pack/path) for path in self.manifest['water']['contact_frames']]
        self.crank_mask = self._load(self.pack/self.manifest['crank']['coverage_mask'], 'L')
        self.spindle_mask = self._load(self.pack/self.manifest['spindle']['coverage_mask'], 'L')
        self.under = Image.new('RGBA', self.size)
        for name in ('contact_shadow', 'stone_far', 'water', 'supports', 'windlass'):
            layer = self.layers[name].copy(); opacity = self.layer_records[name]['opacity']
            if opacity != 1: layer.putalpha(layer.getchannel('A').point(lambda a: round(a*opacity)))
            self.under.alpha_composite(layer)
        self.front = Image.new('RGBA', self.size)
        self.front.alpha_composite(self.layers['stone_near'])
        self.front.alpha_composite(self.layers['canopy'])
        self.static = self.under.copy(); self.static.alpha_composite(self.front)
        self.water_plane_artwork = round(self.base['geometry']['anchors_logical']['water_contact'][1]*self.density)
        # Water covers only the part of a submerged load below its surface.
        below = Image.new('L', self.size)
        ImageDraw.Draw(below).rectangle((0, self.water_plane_artwork, self.size[0]-1, self.size[1]-1), fill=255)
        self.submerged_mask = ImageChops.multiply(below, self.masks['water'])
        # The retained master assigns a few front coping-edge pixels to far
        # masonry. They are still solid occluders, never transparent holes
        # through which a submerged pail can paint over the rim.
        structural_alpha = self.static.getchannel('A').point(lambda a: 255 if a == 255 else 0)
        near_coping = ImageChops.multiply(below, ImageChops.subtract(structural_alpha, self.masks['water']))
        self.shaft_front_mask = ImageChops.multiply(near_coping, self.masks['aperture'])
        self.limit = self.manifest['cache']['composite_entries']
        self._cache = OrderedDict(); self._hits = self._misses = 0

    def _load(self, path, mode='RGBA'):
        with Image.open(self.root/path) as image:
            return image.convert(mode)

    def _signature(self, state, ambient_ms, reduced):
        grip = _field(state, 'bucket_grip_local', (36, 74))
        origin = _field(state, 'rope_origin_local', (36, 53))
        water_phase = 0 if reduced else int(ambient_ms//self.manifest['water']['frame_duration_ms']) % len(self.water)
        contact = min(len(self.contacts)-1, max(0, int(_field(state, 'phase_progress', 0)*len(self.contacts))))
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
                bool(_field(state, 'water_contact', False)), water_phase, contact,
                bool(reduced))

    def _moving(self, signature):
        phase, grip, origin, rope, hook, owner, units, region, crank, submerged, contact, water_phase, effect_phase, reduced = signature
        motion = Image.new('RGBA', self.size)
        palette = self.manifest['palette']
        hook_meta = self.manifest['hook']
        attach = hook_meta['attachment_anchor_artwork']; rope_anchor = hook_meta['rope_anchor_artwork']
        hook_xy = (grip[0]-attach[0], grip[1]-attach[1])
        rope_end = (hook_xy[0]+rope_anchor[0], hook_xy[1]+rope_anchor[1])
        if rope:
            draw = ImageDraw.Draw(motion)
            draw.line((*origin, *rope_end), fill=palette['rope_dark'], width=self.manifest['rope']['outline_width_artwork'])
            draw.line((*origin, *rope_end), fill=palette['rope_light'], width=self.manifest['rope']['strand_width_artwork'])
        if hook:
            motion.alpha_composite(self.hook, hook_xy)
        if owner == 'well':
            if units not in self.pails: raise ValueError('Unsupported well pail water level')
            pail = self.pails[units]
            xy = (round(grip[0]-self.pail_grip[0]*self.density),
                  round(grip[1]-self.pail_grip[1]*self.density))
            motion.alpha_composite(pail, xy)
        if region == 'shaft':
            # The whole motion may remain above the mouth; only its lower
            # portion is restricted by the actual opening and near wall.
            allowed = self.masks['aperture'].copy()
            top = Image.new('L', self.size)
            aperture_top = self.masks['aperture'].getbbox()[1]
            ImageDraw.Draw(top).rectangle((0, 0, self.size[0]-1, aperture_top-1), fill=255)
            allowed = ImageChops.lighter(allowed, top)
            motion.putalpha(ImageChops.multiply(motion.getchannel('A'), allowed))
            motion.putalpha(ImageChops.subtract(motion.getchannel('A'), self.shaft_front_mask))
            if submerged:
                motion.putalpha(ImageChops.subtract(motion.getchannel('A'), self.submerged_mask))
        return motion

    def render(self, snapshot, ambient_ms=0, reduced_motion=False):
        """Return a caller-owned native RGBA image without advancing simulation."""
        key = self._signature(snapshot, ambient_ms, reduced_motion)
        cached = self._cache.get(key)
        if cached is not None:
            self._hits += 1; self._cache.move_to_end(key)
            return cached.copy()
        self._misses += 1
        phase, grip, origin, rope, hook, owner, units, region, crank, submerged, contact, water_phase, effect_phase, reduced = key
        image = self.under.copy()
        image.alpha_composite(self.water[water_phase])
        image.alpha_composite(self.spindles[crank])
        moving = self._moving(key)
        if region != 'loading_foreground': image.alpha_composite(moving)
        image.alpha_composite(self.front)
        if region == 'loading_foreground': image.alpha_composite(moving)
        image.alpha_composite(self.cranks[crank])
        if contact and phase in ('lower', 'fill'):
            image.alpha_composite(self.contacts[effect_phase])
        if phase == 'raise' and owner == 'well' and not submerged:
            drops = Image.new('RGBA', self.size); draw = ImageDraw.Draw(drops)
            # Water drips belong to the emerging pail; never overwrite stone.
            for dx, dy in ((-3, 1+effect_phase), (4, 5+effect_phase)):
                x, y = grip[0]+dx, grip[1]+self.pail_base_offset_artwork+dy
                if 0 <= x < self.size[0] and 0 <= y < self.size[1]: draw.point((x, y), fill=self.manifest['palette']['glint'])
            drops.putalpha(ImageChops.multiply(drops.getchannel('A'), self.masks['water']))
            image.alpha_composite(drops)
        self._cache[key] = image
        while len(self._cache) > self.limit: self._cache.popitem(last=False)
        return image.copy()

    def dynamic_mask(self, snapshot):
        """Owned native effect coverage, for depth and structural regression checks."""
        signature = self._signature(snapshot, 0, False)
        mechanism = ImageChops.lighter(self.crank_mask, self.spindle_mask)
        return ImageChops.lighter(ImageChops.lighter(self.masks['water'], mechanism),
                                 self._moving(signature).getchannel('A'))

    def cache_info(self):
        return {'entries': len(self._cache), 'limit': self.limit,
                'hits': self._hits, 'misses': self._misses,
                'composite_bytes': len(self._cache)*self.size[0]*self.size[1]*4,
                'artwork_size': list(self.size), 'density': self.density}
