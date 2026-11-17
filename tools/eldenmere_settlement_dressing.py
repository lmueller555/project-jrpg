"""Resolve the reviewed household courtyard's native dressing without writing a map.

The source recipe owns placements and explicit physical supports. Asset alpha is
used for conservative artwork-overlap checks, never as an automatic collision
mask. The town composer remains the only owner that applies these records.
"""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

from PIL import Image

from tools.eldenmere_settlement import (_file, _numbers, _overlap, _rect, _select,
                                       validate_placements)

PREFIX = 'settlement.courtyard.'
DISTRICT = 'serene_terrace'
STATUS = 'courtyard_dressing'
PLACEMENT_KEYS = {'id', 'asset', 'district', 'position', 'collision', 'footprint', 'occlusion'}
CONFIG_KEYS = {'district', 'scope_rect', 'retire_grass_ids', 'garden_cells'}
LOW_FAMILIES = {'flowers', 'groundcover'}


def _native_numbers(value, length, label):
    result = _numbers(value, length, label)
    if any(not float(v*2).is_integer() for v in result):
        raise ValueError(label+': coordinates must register to native half-units')
    return result


def _contained(inner, outer):
    x, y, w, h = inner
    ox, oy, ow, oh = outer
    return x >= ox and y >= oy and x+w <= ox+ow and y+h <= oy+oh


def _empty():
    return dict(district=None, scope_rect=None, placements=[], entities=[],
                solid_footprints=[], retired_grass_ids=[], retired_grass_records=[],
                garden_cells=[], dependencies_sha256={})


def resolve_dressing(root, town, recipe, catalogue, protections, *, image_loader=None):
    """Return validated native entities, supports, garden cells and provenance.

    ``image_loader`` optionally resolves freshly composed existing PNGs from the
    town export buffer. No supplied object or source file is changed. Containers
    and fences need deliberate integer physical footprints and tall occlusion;
    only low flower/groundcover scenery may be nonblocking.
    """
    root = Path(root).resolve()
    status = recipe.get('status')
    placements = recipe.get('placements')
    if status not in ('framework_only', 'ground_only', STATUS):
        raise ValueError('Unsupported settlement dressing activation status')
    if not isinstance(placements, list):
        raise ValueError('Settlement placements must be a list')
    if status != STATUS:
        if placements or recipe.get('courtyard_dressing'):
            raise ValueError('Settlement status cannot activate courtyard dressing')
        previous = town.get('settlement_dressing') or {}
        if not isinstance(previous, dict):
            raise ValueError('Invalid previous courtyard ownership report')
        if previous.get('entities') or previous.get('retired_grass_ids') or previous.get('retired_grass_records'):
            raise ValueError('Courtyard deactivation requires explicit owned-entity and grass cleanup')
        return _empty()
    if recipe.get('version') != 1 or recipe.get('scene') != 'eldenmere.playable' or town.get('id') != 'eldenmere.playable':
        raise ValueError('Courtyard dressing requires the version1 Eldenmere town recipe')
    config = recipe.get('courtyard_dressing')
    if not isinstance(config, dict) or set(config) != CONFIG_KEYS:
        raise ValueError('Courtyard dressing requires only the reviewed configuration keys')
    if config['district'] != DISTRICT:
        raise ValueError('Courtyard dressing can activate only serene_terrace')
    scope = _native_numbers(config['scope_rect'], 4, 'courtyard scope')
    _rect(scope, 'courtyard scope')
    districts = [d for d in recipe.get('districts', []) if d.get('id') == DISTRICT]
    if len(districts) != 1 or not _contained(scope, _rect(districts[0]['rect'], 'courtyard district')):
        raise ValueError('Courtyard scope must remain inside the reviewed district')
    width, height = _numbers(town['size_pixels'], 2, 'town size')
    if not _contained(scope, [0, 0, width, height]):
        raise ValueError('Courtyard scope leaves town bounds')
    if len(placements) > 64:
        raise ValueError('Courtyard dressing is limited to64 reviewed placements')

    previous = town.get('settlement_dressing') or {}
    if not isinstance(previous, dict):
        raise ValueError('Invalid previous courtyard ownership report')
    owned = set()
    for entity in previous.get('entities', []):
        if not isinstance(entity, dict) or not isinstance(entity.get('id'), str) or not entity['id'].startswith(PREFIX):
            raise ValueError('Previous courtyard ownership may contain only courtyard entities')
        if entity['id'] in owned:
            raise ValueError('Duplicate previous courtyard ownership')
        owned.add(entity['id'])
    for entity in town.get('entities', []):
        if entity['id'].startswith(PREFIX) and entity['id'] not in owned:
            raise ValueError('Unowned existing courtyard namespace instance '+entity['id'])
    validation_town = {**town, 'entities': [e for e in town.get('entities', []) if e['id'] not in owned]}
    assets = {record['id']: record for record in catalogue['assets']}
    dependencies, pictures = {}, {}

    def read(relative):
        path = _file(root, relative)
        dependencies[path.relative_to(root).as_posix()] = sha256(path.read_bytes()).hexdigest()
        return path

    def picture(relative, density, logical_size, *, dependency=True, pending=False):
        key = (relative, density, tuple(logical_size), pending)
        if key not in pictures:
            if pending and image_loader is not None:
                source = image_loader(relative)
                if not isinstance(source, Image.Image):
                    raise ValueError('Courtyard image loader must return native PIL artwork')
                native = source.convert('RGBA')
            else:
                path = read(relative) if dependency else _file(root, relative)
                with Image.open(path) as source:
                    native = source.convert('RGBA')
            if density not in (1, 2) or native.size != tuple(v*density for v in logical_size):
                raise ValueError('Courtyard artwork canvas/density mismatch: '+relative)
            if dependency and set(native.getchannel('A').tobytes()) - {0, 255}:
                raise ValueError('Courtyard artwork requires hard alpha: '+relative)
            bbox = native.getbbox()
            pictures[key] = None if bbox is None else [v/density for v in bbox]
        return pictures[key]

    def occupied(record, *, source=False):
        density = record.get('artwork_pixels_per_world_pixel', town.get('artwork_pixels_per_world_pixel', 1))
        logical_size = record.get('logical_size')
        frames = record.get('frames', [])
        if logical_size is None or not frames:
            raise ValueError('Existing courtyard-area artwork lacks canvas/frame metadata: '+record['id'])
        bounds = []
        for path in [*frames, *([record['reduced_motion_image']] if record.get('reduced_motion_image') else [])]:
            bbox = picture(path, density, logical_size, dependency=source, pending=not source)
            if bbox is not None:
                bounds.append(bbox)
        if not bounds:
            raise ValueError('Courtyard artwork is empty: '+record['id'])
        x, y = record['position']
        left, top = min(b[0] for b in bounds), min(b[1] for b in bounds)
        right, bottom = max(b[2] for b in bounds), max(b[3] for b in bounds)
        return [x+left, y+top, right-left, bottom-top]

    enriched, entities, solids, seen = [], [], [], set()
    for placement in placements:
        if not isinstance(placement, dict) or set(placement)-PLACEMENT_KEYS:
            raise ValueError('Unsupported courtyard placement fields')
        name = placement.get('id')
        if not isinstance(name, str) or not name.startswith(PREFIX) or name == PREFIX or name in seen:
            raise ValueError('Courtyard placement IDs must be unique in '+PREFIX+'*')
        seen.add(name)
        if placement.get('district') != DISTRICT:
            raise ValueError(name+': placement leaves authorized courtyard district')
        asset_name = placement.get('asset')
        if not isinstance(asset_name, str):
            raise ValueError(name+': asset must name a catalogued native source')
        asset = assets.get(asset_name)
        if asset is None:
            raise ValueError(name+': unknown native courtyard asset')
        if asset.get('artwork_pixels_per_world_pixel') != 2:
            raise ValueError(name+': courtyard art must be native2x')
        position = _native_numbers(placement.get('position'), 2, name+' position')
        logical_size = _native_numbers(asset['logical_size'], 2, name+' logical size')
        if not _contained([*position, *logical_size], scope):
            raise ValueError(name+': artwork canvas leaves courtyard scope')
        is_low = asset['id'].startswith('vegetation_hd:') and asset.get('family') in LOW_FAMILIES
        if is_low:
            if placement.get('collision') != 'none' or placement.get('occlusion') not in ('ground', 'low'):
                raise ValueError(name+': flowers/groundcover must remain low nonblocking scenery')
        elif placement.get('collision') != 'solid' or placement.get('occlusion') != 'tall':
            raise ValueError(name+': containers and fences need solid supports and tall occlusion')

        manifest_path = asset.get('manifest')
        manifest = json.loads(read(manifest_path).read_text())
        selector = asset.get('source_selector')
        if not isinstance(selector, list) or not selector or '*' in selector:
            raise ValueError(name+': courtyard asset needs one exact source selector')
        selected = _select(manifest, selector)
        if len(selected) != 1 or not isinstance(selected[0][0], dict):
            raise ValueError(name+': asset source must resolve one metadata record')
        source = selected[0][0]
        if source.get('id') != asset['id'].split(':', 1)[1] or source.get('logical_size') != asset['logical_size']:
            raise ValueError(name+': native source identity/canvas changed')
        density = source.get('artwork_pixels_per_world_pixel', manifest.get('artwork_pixels_per_world_pixel'))
        if density != 2 or source.get('mount', 'ground') != 'ground':
            raise ValueError(name+': only native ground-mounted courtyard assets are authorized')
        parent = Path(manifest_path).parent
        idle = (parent/source['idle']).as_posix()
        if idle != asset['image']:
            raise ValueError(name+': catalogue idle disagrees with native source')
        if is_low:
            source_frames = source.get('frames', [])
            if not source_frames or any(not isinstance(frame, dict) for frame in source_frames):
                raise ValueError(name+': vegetation needs authored frame records')
            durations = {frame.get('duration_ms') for frame in source_frames}
            if len(durations) != 1 or any(type(v) is not int or v <= 0 for v in durations):
                raise ValueError(name+': vegetation must retain its source frame cadence')
            frames = [(parent/frame['file']).as_posix() for frame in source_frames]
            duration = next(iter(durations))
        else:
            frames, duration = [idle], 600
        depth = _native_numbers([source.get('depth_baseline_logical')], 1, name+' source depth')[0]
        if not 0 <= depth <= logical_size[1]:
            raise ValueError(name+': source depth leaves its canvas')
        entity = dict(id=name, position=position, sort_y=position[1]+depth,
                      frames=frames, frame_duration_ms=duration,
                      phase_offset=int(sha256(name.encode()).hexdigest()[:8], 16) % len(frames),
                      artwork_pixels_per_world_pixel=2, logical_size=logical_size)
        if is_low:
            entity.update(reduced_motion_frame=0, reduced_motion_image=idle)
        occupied_rect = occupied(entity, source=True)
        item = deepcopy(placement)
        item.update(position=position, logical_size=logical_size, occupied_rect=occupied_rect,
                    depth_baseline_logical=depth)
        if placement.get('collision') == 'solid':
            footprint = _native_numbers(placement.get('footprint'), 4, name+' support')
            _rect(footprint, name+' support')
            world_rect = [position[0]+footprint[0], position[1]+footprint[1], *footprint[2:]]
            if any(not float(v).is_integer() for v in world_rect):
                raise ValueError(name+': physical support must use integer logical mask geometry')
            if not _overlap(world_rect, occupied_rect):
                raise ValueError(name+': physical support misses the occupied artwork')
            item['world_footprint'] = [int(v) for v in world_rect]
            solids.append({'id': name, 'rect': item['world_footprint']})
        enriched.append(item)
        entities.append(entity)

    validate_placements(placements, protections, catalogue, validation_town)
    occupied_existing = []
    for record in validation_town.get('entities', []):
        if 'logical_size' not in record:
            raise ValueError('Existing artwork needs an explicit logical canvas for courtyard protection: '+record['id'])
        if _overlap([*record['position'], *record['logical_size']], scope):
            occupied_existing.append((record['id'], occupied(record)))
    for index, record in enumerate(enriched):
        rect = record['occupied_rect']
        for name, other in occupied_existing:
            if _overlap(rect, other):
                raise ValueError(record['id']+': artwork overlaps existing occupied asset '+name)
        for earlier in enriched[:index]:
            if _overlap(rect, earlier['occupied_rect']):
                raise ValueError(record['id']+': artwork overlaps proposed placement '+earlier['id'])

    retire = config['retire_grass_ids']
    if not isinstance(retire, list) or any(not isinstance(name, str) for name in retire) or len(set(retire)) != len(retire):
        raise ValueError('Retired courtyard grass IDs must be a unique explicit list')
    grass = {record['id']: record for record in town.get('grass', {}).get('instances', [])}
    prior_records = {record['id']: record for record in previous.get('retired_grass_records', [])}
    prior_ids = set(previous.get('retired_grass_ids', []))
    retired_records = []
    for name in retire:
        record = grass.get(name) or prior_records.get(name)
        if record is None:
            if name in prior_ids and previous.get('scope_rect') == scope:
                continue
            raise ValueError('Retired courtyard grass no longer resolves: '+name)
        x, y = _native_numbers(record['position'], 2, name+' grass position')
        if not _contained([x-12, y-28, 24, 32], scope):
            raise ValueError('Retired grass artwork leaves courtyard scope: '+name)
        retired_records.append(deepcopy(record))
    cells = config['garden_cells']
    if not isinstance(cells, list):
        raise ValueError('Courtyard garden cells must be an explicit list')
    garden, used = [], set()
    for cell in cells:
        if (not isinstance(cell, list) or len(cell) != 2 or
                any(type(v) is not int for v in cell) or tuple(cell) in used):
            raise ValueError('Garden cells must be unique integer tile pairs')
        if not _contained([cell[0]*24, cell[1]*24, 24, 24], scope):
            raise ValueError('Garden soil leaves courtyard scope')
        used.add(tuple(cell));garden.append(list(cell))
    return dict(district=DISTRICT, scope_rect=scope, placements=enriched, entities=entities,
                solid_footprints=solids, retired_grass_ids=list(retire),
                retired_grass_records=retired_records, garden_cells=garden,
                dependencies_sha256=dict(sorted(dependencies.items())))
