"""Resolve reviewed settlement district dressing without writing a map.

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
WORKYARD_PREFIX = 'settlement.workyards.'
WORKYARD_DISTRICT = 'workshop_mill'
WORKYARD_STATUS = 'workyard_dressing'
COMMONS_PREFIX = 'settlement.commons.'
COMMONS_DISTRICT = 'commons_households'
COMMONS_STATUS = 'commons_dressing'
HOUSEHOLD_PREFIX = 'settlement.households.'
HOUSEHOLD_STATUS = 'household_dressing'
HOUSEHOLD_PARCELS = frozenset(('liam_house', 'home_a', 'home_b', 'home_c', 'elira'))
DRESSING_STATUSES = (STATUS, WORKYARD_STATUS, COMMONS_STATUS, HOUSEHOLD_STATUS)
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


def _empty(cell_key='garden_cells'):
    report = dict(district=None, scope_rect=None, placements=[], entities=[],
                  solid_footprints=[], retired_grass_ids=[], retired_grass_records=[])
    report[cell_key] = []
    report['dependencies_sha256'] = {}
    return report


def _combined_placements(recipe):
    """Partition only the explicitly enabled districts of the current delivery."""
    placements = recipe.get('placements')
    if not isinstance(placements, list):
        raise ValueError('Settlement placements must be a list')
    status = recipe.get('status')
    districts = (DISTRICT, WORKYARD_DISTRICT, COMMONS_DISTRICT) if status in (COMMONS_STATUS, HOUSEHOLD_STATUS) else (DISTRICT, WORKYARD_DISTRICT)
    for placement in placements:
        if not isinstance(placement, dict) or placement.get('district') not in districts:
            if status in (COMMONS_STATUS, HOUSEHOLD_STATUS):
                raise ValueError('Commons delivery can activate only serene_terrace, workshop_mill and commons_households')
            raise ValueError('Workyard delivery can activate only serene_terrace and workshop_mill')
        if (isinstance(placement.get('id'), str) and placement['id'].startswith(HOUSEHOLD_PREFIX)
                and status != HOUSEHOLD_STATUS):
            raise ValueError('Settlement status cannot activate household dressing')
    return placements


def resolve_dressing(root, town, recipe, catalogue, protections, *, image_loader=None):
    """Retain the courtyard API and ledger when later deliveries are active."""
    if recipe.get('status') in (WORKYARD_STATUS, COMMONS_STATUS, HOUSEHOLD_STATUS):
        placements = _combined_placements(recipe)
        recipe = {**recipe, 'status': STATUS,
                  'placements': [p for p in placements if p['district'] == DISTRICT]}
    return _resolve_region(root, town, recipe, catalogue, protections,
                           image_loader=image_loader)


def resolve_workyards(root, town, recipe, catalogue, protections, *, image_loader=None):
    """Resolve workyard props and native ground separately from the courtyard.

    ``ground_entities`` contains flat residue to bake before actors, rather than
    append to the world's depth-sorted entity list. All placements still share
    the same source and occupied-artwork validation.
    """
    status = recipe.get('status')
    if status not in ('framework_only', 'ground_only', *DRESSING_STATUSES):
        raise ValueError('Unsupported settlement workyard activation status')
    placements = _combined_placements(recipe) if status in DRESSING_STATUSES else recipe.get('placements')
    if not isinstance(placements, list):
        raise ValueError('Settlement placements must be a list')
    if status in ('framework_only', 'ground_only') and placements:
        raise ValueError('Settlement status cannot activate workyard dressing')
    selected = [p for p in placements if isinstance(p, dict) and p.get('district') == WORKYARD_DISTRICT]
    view = {**recipe, 'status': WORKYARD_STATUS if status in (WORKYARD_STATUS, COMMONS_STATUS, HOUSEHOLD_STATUS) else 'ground_only',
            'placements': selected}
    report = _resolve_region(root, town, view, catalogue, protections, image_loader=image_loader,
                             district=WORKYARD_DISTRICT, prefix=WORKYARD_PREFIX,
                             activation_status=WORKYARD_STATUS, config_key='workyard_dressing',
                             ledger_key='settlement_workyards', cell_key='ground_cells')
    flat_ids = {placement['id'] for placement in report['placements']
                if placement['asset'] == 'exteriors_hd:wood_shavings'}
    report['ground_entities'] = [entity for entity in report['entities'] if entity['id'] in flat_ids]
    report['entities'] = [entity for entity in report['entities'] if entity['id'] not in flat_ids]
    return report


def resolve_commons(root, town, recipe, catalogue, protections, *, image_loader=None):
    """Resolve the civic delivery without replacing earlier district ownership."""
    status = recipe.get('status')
    if status not in ('framework_only', 'ground_only', *DRESSING_STATUSES):
        raise ValueError('Unsupported settlement commons activation status')
    placements = _combined_placements(recipe) if status in DRESSING_STATUSES else recipe.get('placements')
    if not isinstance(placements, list):
        raise ValueError('Settlement placements must be a list')
    if status in ('framework_only', 'ground_only') and placements:
        raise ValueError('Settlement status cannot activate commons dressing')
    selected = [p for p in placements if isinstance(p, dict) and p.get('district') == COMMONS_DISTRICT
                and not (isinstance(p.get('id'), str) and p['id'].startswith(HOUSEHOLD_PREFIX))]
    view = {**recipe, 'status': COMMONS_STATUS if status in (COMMONS_STATUS, HOUSEHOLD_STATUS) else 'ground_only',
            'placements': selected}
    return _resolve_region(root, town, view, catalogue, protections, image_loader=image_loader,
                           district=COMMONS_DISTRICT, prefix=COMMONS_PREFIX,
                           activation_status=COMMONS_STATUS, config_key='commons_dressing',
                           ledger_key='settlement_commons', cell_key='ground_cells')


def resolve_households(root, town, recipe, catalogue, protections, *, image_loader=None):
    """Resolve only named cottage parcels, retaining the separate civic owner.

    The shared resolver still owns all artwork, collision and lifecycle checks.
    Parcel metadata adds a stricter authorization boundary inside the broader
    commons district; it never grants access to the spaces between these plots.
    """
    status = recipe.get('status')
    if status not in ('framework_only', 'ground_only', *DRESSING_STATUSES):
        raise ValueError('Unsupported settlement household activation status')
    placements = _combined_placements(recipe) if status in DRESSING_STATUSES else recipe.get('placements')
    if not isinstance(placements, list):
        raise ValueError('Settlement placements must be a list')
    if status in ('framework_only', 'ground_only') and placements:
        raise ValueError('Settlement status cannot activate household dressing')
    selected = [p for p in placements if isinstance(p, dict)
                and isinstance(p.get('id'), str) and p['id'].startswith(HOUSEHOLD_PREFIX)]
    view = {**recipe, 'status': HOUSEHOLD_STATUS if status == HOUSEHOLD_STATUS else 'ground_only',
            'placements': selected}
    options = dict(image_loader=image_loader, district=COMMONS_DISTRICT, prefix=HOUSEHOLD_PREFIX,
                   activation_status=HOUSEHOLD_STATUS, config_key='household_dressing',
                   ledger_key='settlement_households', cell_key='ground_cells', title='Household')
    if status != HOUSEHOLD_STATUS:
        report = _resolve_region(root, town, view, catalogue, protections, **options)
        report['parcels'] = []
        return report
    config = recipe.get('household_dressing')
    required = (CONFIG_KEYS - {'garden_cells'}) | {'ground_cells', 'parcels'}
    if not isinstance(config, dict) or set(config) != required:
        raise ValueError('Household dressing requires only the reviewed configuration keys')
    scope = _native_numbers(config['scope_rect'], 4, 'household scope')
    _rect(scope, 'household scope')
    sources = config['parcels']
    if not isinstance(sources, list) or not 1 <= len(sources) <= len(HOUSEHOLD_PARCELS):
        raise ValueError('Household dressing needs explicitly named cottage parcels')
    parcels = {}
    for source in sources:
        if not isinstance(source, dict) or set(source) != {'id', 'scope_rect'}:
            raise ValueError('Household parcels require only id and scope_rect')
        name = source['id']
        if not isinstance(name, str) or name not in HOUSEHOLD_PARCELS or name in parcels:
            raise ValueError('Household parcel IDs must uniquely name reviewed cottage owners')
        rect = _native_numbers(source['scope_rect'], 4, name+' parcel scope')
        _rect(rect, name+' parcel scope')
        if not _contained(rect, scope) or any(_overlap(rect, previous) for previous in parcels.values()):
            raise ValueError('Household parcels must be disjoint and contained by their reviewed scope')
        parcels[name] = rect
    membership = {}
    stripped = []
    for placement in selected:
        parcel = placement.get('parcel')
        if not isinstance(parcel, str) or parcel not in parcels:
            raise ValueError('Every household placement must name one reviewed parcel')
        membership[placement['id']] = parcel
        stripped.append({key: value for key, value in placement.items() if key != 'parcel'})
    view = {**view, 'placements': stripped,
            'household_dressing': {key: value for key, value in config.items() if key != 'parcels'}}
    report = _resolve_region(root, town, view, catalogue, protections, **options)
    for placement in report['placements']:
        parcel = membership[placement['id']]
        if not _contained([*placement['position'], *placement['logical_size']], parcels[parcel]):
            raise ValueError(placement['id']+': artwork canvas leaves its named household parcel')
        placement['parcel'] = parcel
    for x, y in report['ground_cells']:
        fringe = [(x-1)*24, (y-1)*24, 72, 72]
        if not any(_contained(fringe, parcel) for parcel in parcels.values()):
            raise ValueError('Household ground and its transition rim must fit one reviewed parcel')
    for record in report['retired_grass_records']:
        x, y = _native_numbers(record['position'], 2, record['id']+' grass position')
        if not any(_contained([x-12, y-28, 24, 32], parcel) for parcel in parcels.values()):
            raise ValueError('Retired grass artwork must fit one reviewed household parcel')
    report['parcels'] = [{'id': name, 'scope_rect': rect} for name, rect in parcels.items()]
    return report


def _resolve_region(root, town, recipe, catalogue, protections, *, image_loader=None,
                    district=DISTRICT, prefix=PREFIX, activation_status=STATUS,
                    config_key='courtyard_dressing', ledger_key='settlement_dressing',
                    cell_key='garden_cells', title=None):
    """Return validated native entities, supports, garden cells and provenance.

    ``image_loader`` optionally resolves freshly composed existing PNGs from the
    town export buffer. No supplied object or source file is changed. Containers
    and fences need deliberate integer physical footprints and tall occlusion;
    only low flower/groundcover and explicitly flat workyard residue may be
    nonblocking.
    """
    root = Path(root).resolve()
    title = title or {DISTRICT: 'Courtyard', WORKYARD_DISTRICT: 'Workyard', COMMONS_DISTRICT: 'Commons'}[district]
    noun = title.lower()
    status = recipe.get('status')
    placements = recipe.get('placements')
    if status not in ('framework_only', 'ground_only', activation_status):
        raise ValueError('Unsupported settlement dressing activation status')
    if not isinstance(placements, list):
        raise ValueError('Settlement placements must be a list')
    if status != activation_status:
        if placements or recipe.get(config_key):
            raise ValueError(f'Settlement status cannot activate {noun} dressing')
        previous = town.get(ledger_key) or {}
        if not isinstance(previous, dict):
            raise ValueError(f'Invalid previous {noun} ownership report')
        remaining = any(isinstance(entity, dict) and isinstance(entity.get('id'), str)
                        and entity['id'].startswith(prefix) for entity in town.get('entities', []))
        if (previous.get('entities') or previous.get('ground_entities') or previous.get('retired_grass_ids')
                or previous.get('retired_grass_records') or remaining):
            raise ValueError(f'{title} deactivation requires explicit owned-entity and grass cleanup')
        return _empty(cell_key)
    if recipe.get('version') != 1 or recipe.get('scene') != 'eldenmere.playable' or town.get('id') != 'eldenmere.playable':
        raise ValueError(f'{title} dressing requires the version 1 Eldenmere town recipe')
    config = recipe.get(config_key)
    if not isinstance(config, dict) or set(config) != ((CONFIG_KEYS - {'garden_cells'}) | {cell_key}):
        raise ValueError(f'{title} dressing requires only the reviewed configuration keys')
    if config['district'] != district:
        raise ValueError(f'{title} dressing can activate only {district}')
    scope = _native_numbers(config['scope_rect'], 4, noun+' scope')
    _rect(scope, noun+' scope')
    districts = [d for d in recipe.get('districts', []) if d.get('id') == district]
    if len(districts) != 1 or not _contained(scope, _rect(districts[0]['rect'], noun+' district')):
        raise ValueError(f'{title} scope must remain inside the reviewed district')
    width, height = _numbers(town['size_pixels'], 2, 'town size')
    if not _contained(scope, [0, 0, width, height]):
        raise ValueError(f'{title} scope leaves town bounds')
    if len(placements) > 64:
        raise ValueError(f'{title} dressing is limited to 64 reviewed placements')

    previous = town.get(ledger_key) or {}
    if not isinstance(previous, dict):
        raise ValueError(f'Invalid previous {noun} ownership report')
    owned = set()
    prior_entities = previous.get('entities', [])
    prior_ground = previous.get('ground_entities', [])
    if not isinstance(prior_entities, list) or not isinstance(prior_ground, list):
        raise ValueError(f'Invalid previous {noun} entity ownership lists')
    for entity in [*prior_entities, *prior_ground]:
        if not isinstance(entity, dict) or not isinstance(entity.get('id'), str) or not entity['id'].startswith(prefix):
            raise ValueError(f'Previous {noun} ownership may contain only {noun} entities')
        if entity['id'] in owned:
            raise ValueError(f'Duplicate previous {noun} ownership')
        owned.add(entity['id'])
    for entity in town.get('entities', []):
        if entity['id'].startswith(prefix) and entity['id'] not in owned:
            raise ValueError(f'Unowned existing {noun} namespace instance '+entity['id'])
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
                    raise ValueError(f'{title} image loader must return native PIL artwork')
                native = source.convert('RGBA')
            else:
                path = read(relative) if dependency else _file(root, relative)
                with Image.open(path) as source:
                    native = source.convert('RGBA')
            if density not in (1, 2) or native.size != tuple(v*density for v in logical_size):
                raise ValueError(f'{title} artwork canvas/density mismatch: '+relative)
            if dependency and set(native.getchannel('A').tobytes()) - {0, 255}:
                raise ValueError(f'{title} artwork requires hard alpha: '+relative)
            bbox = native.getbbox()
            pictures[key] = None if bbox is None else [v/density for v in bbox]
        return pictures[key]

    def occupied(record, *, source=False):
        density = record.get('artwork_pixels_per_world_pixel', town.get('artwork_pixels_per_world_pixel', 1))
        logical_size = record.get('logical_size')
        frames = record.get('frames', [])
        if logical_size is None or not frames:
            raise ValueError(f'Existing {noun} artwork lacks canvas/frame metadata: '+record['id'])
        bounds = []
        for path in [*frames, *([record['reduced_motion_image']] if record.get('reduced_motion_image') else [])]:
            bbox = picture(path, density, logical_size, dependency=source, pending=not source)
            if bbox is not None:
                bounds.append(bbox)
        if not bounds:
            raise ValueError(f'{title} artwork is empty: '+record['id'])
        x, y = record['position']
        left, top = min(b[0] for b in bounds), min(b[1] for b in bounds)
        right, bottom = max(b[2] for b in bounds), max(b[3] for b in bounds)
        return [x+left, y+top, right-left, bottom-top]

    enriched, entities, solids, seen = [], [], [], set()
    for placement in placements:
        if not isinstance(placement, dict) or set(placement)-PLACEMENT_KEYS:
            raise ValueError(f'Unsupported {noun} placement fields')
        name = placement.get('id')
        if not isinstance(name, str) or not name.startswith(prefix) or name == prefix or name in seen:
            raise ValueError(f'{title} placement IDs must be unique in '+prefix+'*')
        seen.add(name)
        if placement.get('district') != district:
            raise ValueError(name+f': placement leaves authorized {noun} district')
        asset_name = placement.get('asset')
        if not isinstance(asset_name, str):
            raise ValueError(name+': asset must name a catalogued native source')
        asset = assets.get(asset_name)
        if asset is None:
            raise ValueError(name+f': unknown native {noun} asset')
        if asset.get('artwork_pixels_per_world_pixel') != 2:
            raise ValueError(name+f': {noun} art must be native 2x')
        position = _native_numbers(placement.get('position'), 2, name+' position')
        logical_size = _native_numbers(asset['logical_size'], 2, name+' logical size')
        if not _contained([*position, *logical_size], scope):
            raise ValueError(name+f': artwork canvas leaves {noun} scope')
        is_vegetation = asset['id'].startswith('vegetation_hd:') and asset.get('family') in LOW_FAMILIES
        is_flat = asset['id'] == 'exteriors_hd:wood_shavings'
        is_low = is_vegetation or is_flat
        if is_flat:
            if district != WORKYARD_DISTRICT or placement.get('collision') != 'none' or placement.get('occlusion') != 'ground':
                raise ValueError(name+': wood shavings require flat nonblocking workyard placement')
        elif is_vegetation:
            if placement.get('collision') != 'none' or placement.get('occlusion') not in ('ground', 'low'):
                raise ValueError(name+': flowers/groundcover must remain low nonblocking scenery')
        elif placement.get('collision') != 'solid' or placement.get('occlusion') != 'tall':
            raise ValueError(name+': containers and fences need solid supports and tall occlusion')

        manifest_path = asset.get('manifest')
        manifest = json.loads(read(manifest_path).read_text())
        selector = asset.get('source_selector')
        if not isinstance(selector, list) or not selector or '*' in selector:
            raise ValueError(name+f': {noun} asset needs one exact source selector')
        selected = _select(manifest, selector)
        if len(selected) != 1 or not isinstance(selected[0][0], dict):
            raise ValueError(name+': asset source must resolve one metadata record')
        source = selected[0][0]
        if source.get('id') != asset['id'].split(':', 1)[1] or source.get('logical_size') != asset['logical_size']:
            raise ValueError(name+': native source identity/canvas changed')
        density = source.get('artwork_pixels_per_world_pixel', manifest.get('artwork_pixels_per_world_pixel'))
        if density != 2 or source.get('mount', 'ground') != 'ground':
            raise ValueError(name+f': only native ground-mounted {noun} assets are authorized')
        parent = Path(manifest_path).parent
        idle = (parent/source['idle']).as_posix()
        if idle != asset['image']:
            raise ValueError(name+': catalogue idle disagrees with native source')
        is_laundry = asset['id'] == 'exteriors_hd:laundry_line'
        if is_vegetation:
            source_frames = source.get('frames', [])
            if not source_frames or any(not isinstance(frame, dict) for frame in source_frames):
                raise ValueError(name+': vegetation needs authored frame records')
            durations = {frame.get('duration_ms') for frame in source_frames}
            if len(durations) != 1 or any(type(v) is not int or v <= 0 for v in durations):
                raise ValueError(name+': vegetation must retain its source frame cadence')
            frames = [(parent/frame['file']).as_posix() for frame in source_frames]
            duration = next(iter(durations))
        elif is_laundry:
            source_frames = source.get('frames')
            duration = source.get('frame_duration_ms')
            if (not isinstance(source_frames, list) or len(source_frames) < 2
                    or any(not isinstance(frame, str) for frame in source_frames)
                    or type(duration) is not int or duration <= 0
                    or source.get('animation') != 'cloth'
                    or source.get('cycle_ms') != len(source_frames)*duration):
                raise ValueError(name+': laundry must retain its authored cloth frames and cadence')
            frames = [(parent/frame).as_posix() for frame in source_frames]
        else:
            frames, duration = [idle], 600
        depth = _native_numbers([source.get('depth_baseline_logical')], 1, name+' source depth')[0]
        if not 0 <= depth <= logical_size[1]:
            raise ValueError(name+': source depth leaves its canvas')
        entity = dict(id=name, position=position, sort_y=position[1]+depth,
                      frames=frames, frame_duration_ms=duration,
                      phase_offset=int(sha256(name.encode()).hexdigest()[:8], 16) % len(frames),
                      artwork_pixels_per_world_pixel=2, logical_size=logical_size)
        if is_low or is_laundry:
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
            raise ValueError(f'Existing artwork needs an explicit logical canvas for {noun} protection: '+record['id'])
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
        raise ValueError(f'Retired {noun} grass IDs must be a unique explicit list')
    grass = {record['id']: record for record in town.get('grass', {}).get('instances', [])}
    prior_records = {record['id']: record for record in previous.get('retired_grass_records', [])}
    prior_ids = set(previous.get('retired_grass_ids', []))
    retired_records = []
    for name in retire:
        record = grass.get(name) or prior_records.get(name)
        if record is None:
            if name in prior_ids and previous.get('scope_rect') == scope:
                continue
            raise ValueError(f'Retired {noun} grass no longer resolves: '+name)
        x, y = _native_numbers(record['position'], 2, name+' grass position')
        if not _contained([x-12, y-28, 24, 32], scope):
            raise ValueError(f'Retired grass artwork leaves {noun} scope: '+name)
        retired_records.append(deepcopy(record))
    cells = config[cell_key]
    if not isinstance(cells, list):
        raise ValueError(f'{title} {cell_key} must be an explicit list')
    garden, used = [], set()
    for cell in cells:
        if (not isinstance(cell, list) or len(cell) != 2 or
                any(type(v) is not int for v in cell) or tuple(cell) in used):
            raise ValueError(f'{title} ground cells must be unique integer tile pairs')
        if not _contained([cell[0]*24, cell[1]*24, 24, 24], scope):
            raise ValueError(f'Ground treatment leaves {noun} scope')
        used.add(tuple(cell));garden.append(list(cell))
    report = dict(district=district, scope_rect=scope, placements=enriched, entities=entities,
                  solid_footprints=solids, retired_grass_ids=list(retire),
                  retired_grass_records=retired_records)
    report[cell_key] = garden
    report['dependencies_sha256'] = dict(sorted(dependencies.items()))
    return report
