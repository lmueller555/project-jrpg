"""Read-only native asset catalogue for Eldenmere's settlement composer.

Pack delivery status, exact live bindings and future reuse are separate facts.
This module validates source canvases but never places, transforms or activates
artwork. Collision remains a reviewed map contract, not image-alpha coverage.
"""
from __future__ import annotations

from hashlib import sha256
import json
import math
from pathlib import Path

from PIL import Image


PACKS = (
    ('grass_dirt_hd', 'assets/terrain/eldenmere/grass_dirt_hd/tileset.json', 'ground'),
    ('stone_paving_hd', 'assets/terrain/eldenmere/stone_paving_hd/tileset.json', 'ground'),
    ('terraces_hd', 'assets/terrain/eldenmere/terraces_hd/tileset.json', 'elevation'),
    ('vegetation_hd', 'assets/terrain/vegetation_hd/plants.json', 'vegetation'),
    ('exteriors_hd', 'assets/terrain/eldenmere/exteriors_hd/manifest.json', 'ordinary_props'),
    ('business_exteriors_hd', 'assets/terrain/eldenmere/business_exteriors_hd/manifest.json', 'ordinary_props'),
    ('workyard_props', 'assets/terrain/eldenmere/workyard_props/manifest.json', 'ordinary_props'),
    ('growing_fields', 'assets/terrain/eldenmere/growing_fields/manifest.json', 'ordinary_props'),
)


def _uses(pack_id, record):
    name = record['id']
    family = record.get('family', '')
    if pack_id == 'growing_fields':
        return {
            'vegetables_east_west': ('flat rows of young vegetables in reviewed growing plots; native repetition and material contacts only, no harvest or growth mechanic',),
            'furrows_east_west': ('flat tilled or fallow strips within existing growing plots; no raised bed, new channel or physical barrier',),
        }[name]
    if pack_id == 'workyard_props':
        return {
            'grain_sack': ('dry grain/flour deliveries at a reviewed mill storage edge; no pickup ownership',),
            'empty_crate': ('ordinary workshop, mill or growing-plot storage with explicit physical supports; no chest or loot cue',),
            'toolbox': ('stationary repair storage distinct from functional fittings and carried quest tools',),
        }[name]
    if pack_id == 'vegetation_hd':
        if family in ('broadleaf', 'conifer', 'woodland'):
            return ('shade and woodland margins outside required sightlines',)
        if family == 'orchard':
            return ('small orchard or household fruit-tree edges',)
        if family in ('tall_reeds', 'rushes', 'bank_flowers'):
            return ('existing damp river margins; preserve bank clearance',)
        if family in ('boulder', 'rock_cluster', 'fallen_log', 'stump', 'exposed_roots'):
            return ('sparse grounded landscape edges after physical-footprint review',)
        return ('low plot edges, maintained frontage and grass/flower margins',)
    if name.startswith(('sign_', 'awning_', 'windowbox_')) or record.get('mount') == 'wall':
        return ('explicit building-mounted dressing; verify attachment and doorway clearance',)
    if name in ('fence_panel', 'garden_gate'):
        return ('partial parcel edges with reviewed physical supports and open access',)
    if name in ('porch_bench', 'stool'):
        return ('resting-space edges outside actor gathering and travel areas',)
    if name in ('firewood', 'sheltered_firewood', 'wood_shavings', 'broom'):
        return ('household or working-yard storage with retained owner separation',)
    if name in ('travel_boots', 'travel_pack'):
        return ('ordinary arrival-frontage dressing; no pickup or service behavior',)
    return ('household garden and provision grouping after clearance review',)


class _Catalogue:
    def __init__(self, root, town=None):
        self.root = Path(root).resolve()
        self.dependencies = {}
        self.verified_images = {}
        self.assets = []
        self.packs = []
        self.consumer_binding_basis = ('provided_working_town_metadata' if town is not None
                                       else 'checked_in_town_metadata')
        # A composer passes its working map. The standalone observation path is
        # deliberately not a producer dependency either: hashing generated map
        # or manifest output would introduce a build-order/self-reference cycle.
        self.town = town if town is not None else self.read(
            'assets/maps/eldenmere/playable/map.json', dependency=False)
        self.recipe = self.read('assets/source/maps/eldenmere/town_hd/recipe.json')
        self.geometry = self.read('assets/source/maps/eldenmere/courtyard_hd/geometry.json')

    def path(self, value, parent=Path(), *, dependency=True):
        value = Path(value)
        if value.is_absolute():
            raise ValueError(f'Inventory path must be repository-relative: {value}')
        absolute = (self.root/parent/value).resolve()
        if not absolute.is_relative_to(self.root):
            raise ValueError(f'Inventory path escapes repository: {value}')
        if not absolute.is_file():
            raise ValueError(f'Inventory source is missing: {absolute.relative_to(self.root)}')
        relative = absolute.relative_to(self.root).as_posix()
        if dependency and relative not in self.dependencies:
            self.dependencies[relative] = sha256(absolute.read_bytes()).hexdigest()
        return relative

    def read(self, value, *, dependency=True):
        return json.loads((self.root/self.path(value, dependency=dependency)).read_text(encoding='utf-8'))

    def image(self, value, logical_size, density, parent=Path()):
        path = self.path(value, parent)
        if density != 2:
            raise ValueError(f'Settlement candidate must declare native 2x density: {path}')
        if (len(logical_size) != 2 or any(type(v) not in (int, float)
                or not math.isfinite(v) or v <= 0 for v in logical_size)):
            raise ValueError(f'Invalid logical canvas for {path}: {logical_size}')
        expected = tuple(round(value*density) for value in logical_size)
        if any(value*density != pixel for value, pixel in zip(logical_size, expected)):
            raise ValueError(f'Logical canvas does not map to whole artwork pixels: {path}')
        if path not in self.verified_images:
            with Image.open(self.root/path) as source:
                self.verified_images[path] = source.size
        if self.verified_images[path] != expected:
            raise ValueError(f'Native canvas mismatch: {path}: '
                             f'{self.verified_images[path]} != {expected}')
        return path

    def live_bindings(self, paths):
        """Only exact source-image references prove a standalone live binding."""
        paths = set(paths)
        return [{'kind': 'town_entity', 'id': record['id']}
                for record in self.town.get('entities', [])
                if paths.intersection(record.get('frames', []))
                or record.get('reduced_motion_image') in paths]

    def add(self, pack_id, manifest_path, pack, name, family, size, images,
            *, record=None, uses=(), kind='sprite', source_selector=None, bindings=()):
        record = record or {}
        density = record.get('artwork_pixels_per_world_pixel', pack['artwork_pixels_per_world_pixel'])
        parent = Path(manifest_path).parent
        paths = [self.image(value, size, density, parent) for value in images]
        if not paths:
            raise ValueError(f'Inventory asset has no image: {pack_id}:{name}')
        live = self.live_bindings(paths) + list(bindings)
        item = {
            'id': f'{pack_id}:{name}', 'kind': kind, 'family': family,
            'manifest': manifest_path, 'source_selector': source_selector,
            'image': paths[0], 'logical_size': list(size),
            'artwork_pixels_per_world_pixel': density,
            'native_image_count': len(set(paths)), 'intended_uses': list(uses),
            'reuse_status': 'already_bound_in_town' if live else 'available_candidate',
            'current_bindings': sorted(live, key=lambda value: json.dumps(value, sort_keys=True)),
            'collision_policy': record.get('collision', 'Map-owned geometry; no automatic footprint.'),
            'interaction_cues': False,
        }
        for key in ('draw_anchor_logical', 'ground_rect_logical', 'depth_baseline_logical',
                    'mount', 'allowed_surfaces', 'height_logical', 'ports',
                    'walkable_rect_logical', 'elevation_change_logical', 'floor_phase_rule'):
            if key in record:
                item[key] = record[key]
        frames = record.get('frames', [])
        if frames:
            durations = [frame['duration_ms'] for frame in frames
                         if isinstance(frame, dict) and 'duration_ms' in frame]
            item['animation'] = {
                'frame_count': len(frames),
                'kind': record.get('animation_kind', record.get('animation', 'authored_frames')),
                'frame_duration_ms': record.get('frame_duration_ms', record.get('duration_ms')),
                'authored_duration_values_ms': sorted(set(durations)),
                'reduced_motion': 'Use the manifest idle/still state; validate at integration.',
            }
        self.assets.append(item)
        return item

    def materials(self, pack_id, manifest, pack):
        size = pack['logical_tile_size']
        consumer = 'tools/eldenmere_hd_materials.py'
        self.path(consumer)
        if pack_id == 'grass_dirt_hd':
            for family, paths in pack['materials'].items():
                for index, value in enumerate(paths):
                    binding = ({'kind': 'town_ground_compositor', 'owner': consumer,
                                'selection': ['materials', family, index]},) if family == 'grass' else ()
                    self.add(pack_id, manifest, pack, f'{family}.{Path(value).stem}', family,
                             size, [value], kind='material', uses=('lawns and route surfaces',),
                             source_selector=['materials', family, index], bindings=binding)
            self.add(pack_id, manifest, pack, 'dirt_blob47', 'dirt_transition', size,
                     [record['file'] for record in pack['tiles']], kind='transition_set',
                     uses=('coherent dirt-to-grass contacts',), source_selector=['tiles'],
                     bindings=({'kind': 'town_ground_compositor', 'owner': consumer,
                                'selection': ['tiles']},))
        else:
            self.add(pack_id, manifest, pack, 'paving_blob47', 'paving_transition', size,
                     [value for record in pack['tiles'] for value in record['body_files']]
                     + [value for record in pack['tiles'] for value in record['contact_files'].values()],
                     kind='transition_set', uses=('paved islands with authored contacts',),
                     source_selector=['tiles'])
            for index, value in enumerate(pack['interior_phases']):
                self.add(pack_id, manifest, pack, f'phase_{index}', 'paving', size, [value],
                         kind='material', uses=('globally phased paving',),
                         source_selector=['interior_phases', index])
            # The retained pattern is two standard tiles across on each axis.
            self.add(pack_id, manifest, pack, 'pattern', 'paving', [2*v for v in size],
                     [pack['surface_pattern']], kind='material', uses=('globally phased paving',),
                     source_selector=['surface_pattern'],
                     bindings=({'kind': 'town_ground_compositor', 'owner': consumer,
                                'selection': ['surface_pattern']},))
            self.add(pack_id, manifest, pack, 'moss_accents', 'moss', pack['logical_quarter_size'],
                     pack['moss_accents'], kind='accent_set', uses=('sheltered paving edges',),
                     source_selector=['moss_accents'])

    def terraces(self, pack_id, manifest, pack):
        for index, record in enumerate(pack['wall_modules']):
            bindings = [{'kind': 'town_masonry', 'id': entry.get('id', f'masonry.{offset}'),
                         'source': 'assets/source/maps/eldenmere/courtyard_hd/geometry.json'}
                        for offset, entry in enumerate(self.geometry['masonry'])
                        if record['style'] == 'maintained' and entry['tile'] == record['module']]
            self.add(pack_id, manifest, pack, record['id'], 'terrace_wall',
                     record['logical_size'], [record['file']], record=record,
                     uses=('existing terrace edges',), source_selector=['wall_modules', index], bindings=bindings)
        for index, record in enumerate(pack['stair_variants']):
            bindings = [{'kind': 'town_stairs',
                         'source': 'assets/source/maps/eldenmere/courtyard_hd/geometry.json'}]
            self.add(pack_id, manifest, pack, f'stairs.{record["id"]}', 'stairs',
                     record['logical_size'], [record['file']], record=record,
                     uses=('reviewed existing elevation transitions',),
                     source_selector=['stair_variants', index],
                     bindings=bindings if record['id'] == 'maintained' and self.geometry['stairs'] else ())
        for index, record in enumerate(pack['landings']):
            name = '.'.join(str(record[k]) for k in ('stair_variant', 'surface', 'end', 'texture_phase'))
            self.add(pack_id, manifest, pack, f'landing.{name}', 'landing',
                     record['logical_size'], [record['file']], record=record,
                     uses=('stair-to-ground contact after clearance review',), source_selector=['landings', index])
        for index, record in enumerate(pack['terrace_prefabs']):
            self.add(pack_id, manifest, pack, f'prefab.{record["id"]}', 'terrace_assembly',
                     record['logical_size'], [record['file']], record=record, kind='prefab',
                     uses=('reference assembly only until elevation and route geometry are reviewed',),
                     source_selector=['terrace_prefabs', index])

    def props(self, pack_id, manifest, pack, key):
        for index, record in enumerate(pack[key]):
            frames = [value['file'] if isinstance(value, dict) else value
                      for value in record.get('frames', [])]
            bindings = []
            if pack_id == 'growing_fields':
                paths = {(Path(manifest).parent/value).as_posix()
                         for value in [record['idle'], *frames]}
                bindings = [{'kind': 'town_ground_entity', 'id': entry['id'],
                             'source': 'settlement_growing.ground_entities'}
                            for entry in (self.town.get('settlement_growing') or {}).get('ground_entities', [])
                            if paths.intersection(entry.get('frames', []))]
            item = self.add(pack_id, manifest, pack, record['id'],
                            record.get('family', record.get('mount', 'ordinary_prop')),
                            record['logical_size'], [record['idle'], *frames], record=record,
                            uses=_uses(pack_id, record),
                            source_selector=[key, index], bindings=bindings)
            for field in ('fixed', 'backing', 'semantic_mask'):
                if record.get(field):
                    item[field] = self.image(record[field], record['logical_size'],
                                             item['artwork_pixels_per_world_pixel'], Path(manifest).parent)

    def build(self):
        for pack_id, manifest, role in PACKS:
            pack = self.read(manifest)
            self.packs.append({'id': pack_id, 'manifest': manifest,
                               'sha256': self.dependencies[manifest], 'role': role,
                               'source_integration_status': pack.get('integration_status'),
                               'source_visual_approval': pack.get('visual_approval'),
                               'artwork_pixels_per_world_pixel': pack['artwork_pixels_per_world_pixel']})
            if role == 'ground':
                self.materials(pack_id, manifest, pack)
            elif role == 'elevation':
                self.terraces(pack_id, manifest, pack)
            else:
                self.props(pack_id, manifest, pack, 'plants' if role == 'vegetation' else 'props')
        excluded = [{'id': record['id'], 'source': 'assets/maps/eldenmere/playable/map.json',
                     'policy': 'Existing owned fixture; never replace with an unowned decorative clone.'}
                    for record in self.town['entities']
                    if record['id'] == 'well' or record['id'].startswith('workshop.')]
        return {
            'version': 1, 'id': 'eldenmere.settlement.asset_inventory',
            'activation': 'catalogue_only; no placement or asset activation',
            'units': 'logical world units; native artwork is 2x',
            'policy': 'Availability and current use are not visual approval or collision registration.',
            'live_consumer_registry': {'file': 'assets/maps/eldenmere/town_hd/manifest.json',
                                       'role': 'Runtime selector; pack delivery status does not replace its explicit integration records.'},
            'consumer_binding_basis': self.consumer_binding_basis,
            'packs': self.packs, 'assets': sorted(self.assets, key=lambda value: value['id']),
            'gaps': [
                {'id': 'town_scale_cultivated_beds', 'status': 'native_flat_field_bank_available; placement_and_contact_review_required',
                 'need': 'Review coherent native young-vegetable and tilled/fallow surfaces at town scale; these are flat fills, not raised beds or mature crop clusters.',
                 'reuse_first': ['growing_fields:vegetables_east_west', 'growing_fields:furrows_east_west', 'grass_dirt_hd:dirt_blob47'],
                 'gameplay': 'Decorative land use; no harvest, growth simulation or reward is implied.'},
                {'id': 'mill_delivery_storage', 'status': 'native_storage_bank_available; placement_review_required',
                 'need': 'Use the native grain sack and empty crate bank only after reviewing apron scale, supports and ownership; functional fixtures and enlarged regional miniatures remain excluded.',
                 'reuse_first': ['workyard_props:grain_sack', 'workyard_props:empty_crate'],
                 'gameplay': 'No new pickup, service or work controller is implied.'},
            ],
            'excluded_functional_instances': sorted(excluded, key=lambda value: value['id']),
            'validation': {'native_images_verified': len(self.verified_images),
                           'source_pixels_rescaled': False, 'files_written': False},
            'dependencies_sha256': dict(sorted(self.dependencies.items())),
        }


def inventory(root: Path, town=None) -> dict:
    """Catalogue source art without writing files or depending on map outputs.

    Producers pass their working ``town`` dictionary. With no town argument,
    standalone review observes checked-in bindings, still excluding generated
    town map/manifest hashes from producer dependencies.
    """
    return _Catalogue(root, town=town).build()
