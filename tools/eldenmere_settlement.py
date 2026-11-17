"""Build-time settlement catalogue, clearances, streets and scoped dressing.

Coordinates are logical. Selectors scale their geometry from tiles if requested;
padding is always logical. Routes protect the swept footprint of each segment,
not their enclosing rectangle. Each delivery explicitly enables its bounded
composition; the courtyard alone currently authorizes new prop supports.
"""
from copy import deepcopy
from hashlib import sha256
import json
import math
from pathlib import Path

from tools.eldenmere_settlement_inventory import inventory

RECIPE = 'assets/source/maps/eldenmere/settlement/recipe.json'
MANIFEST = 'assets/maps/eldenmere/settlement/manifest.json'
TOWN_ID = 'eldenmere.playable'


def _file(root, name):
    path = Path(name)
    if path.is_absolute() or '..' in path.parts:
        raise ValueError(f'Settlement source must be repository-relative: {name}')
    result = (root / path).resolve()
    if not result.is_relative_to(root.resolve()):
        raise ValueError(f'Settlement source escapes repository: {name}')
    if not result.is_file():
        raise ValueError(f'Missing settlement source: {name}')
    return result


def _numbers(value, length, label):
    if (not isinstance(value, (list, tuple)) or len(value) != length or
            any(type(v) not in (int, float) or not math.isfinite(v) for v in value)):
        raise ValueError(f'{label}: expected {length} finite logical coordinates')
    return list(value)


def _rect(value, label):
    result = _numbers(value, 4, label)
    if result[2] <= 0 or result[3] <= 0:
        raise ValueError(f'{label}: rectangle dimensions must be positive')
    return result


def _select(value, path, trail=()):
    if not path:
        return [(value, list(trail))]
    key, *rest = path
    if key == '*':
        if isinstance(value, dict):
            children = value.items()
        elif isinstance(value, list):
            children = enumerate(value)
        else:
            raise ValueError(f'Settlement selector wildcard requires a collection at {trail}')
        result = []
        for child_key, child in children:
            result.extend(_select(child, rest, (*trail, child_key)))
        return result
    try:
        child = value[key]
    except (KeyError, IndexError, TypeError) as error:
        raise ValueError(f'Settlement selector no longer resolves: {[*trail, key]}') from error
    return _select(child, rest, (*trail, key))


def _protection(identifier, shape, geometry, padding, roles, **evidence):
    padding = _numbers(padding, 2, identifier+' padding')
    if any(v < 0 for v in padding):
        raise ValueError(f'{identifier}: padding cannot be negative')
    if shape == 'point':
        geometry = _numbers(geometry, 2, identifier)
    elif shape == 'rect':
        geometry = _rect(geometry, identifier)
    elif shape == 'route':
        if not isinstance(geometry, list) or len(geometry) < 2:
            raise ValueError(f'{identifier}: route needs at least two points')
        geometry = [_numbers(point, 2, identifier) for point in geometry]
    else:
        raise ValueError(f'{identifier}: unsupported protection shape {shape}')
    if not roles or not set(roles) <= {'movement', 'sightline'}:
        raise ValueError(f'{identifier}: invalid protection roles')
    return dict(id=identifier, shape=shape, geometry=geometry,
                padding=padding, roles=list(roles), **evidence)


def resolve_protections(root, town, recipe):
    """Resolve maintained JSON geometry plus explicitly reviewed code regions."""
    root = Path(root)
    result = []
    half = [v/2 for v in town.get('player_probe_size', [24, 12])]
    for door in town.get('doors', []):
        radius = max(door['open_radius'], door['close_radius'], door['entry_half_width'])
        result.append(_protection('door.'+door['id'], 'point', door['anchor'],
                                  [radius+half[0], radius+half[1]], ['movement', 'sightline'],
                                  source='loaded town', source_path=['doors', door['id'], 'anchor']))
    contact = town.get('overworld_exit')
    if contact:
        result.append(_protection('travel.southern_exit', 'rect', contact['rect'], half,
                                  ['movement', 'sightline'], source='loaded town',
                                  source_path=['overworld_exit', 'rect']))
        result.append(_protection('travel.southern_return', 'point', contact['return_position'],
                                  half, ['movement', 'sightline'], source='loaded town',
                                  source_path=['overworld_exit', 'return_position']))
    for link in town.get('world_links', []):
        radius = link.get('radius', 0)
        result.append(_protection('travel.'+link['id'], 'point', link['position'],
                                  [radius+half[0], radius+half[1]], ['movement', 'sightline'],
                                  source='loaded town', source_path=['world_links', link['id']]))
    entities = {record['id']: record for record in town.get('entities', [])}
    for name in recipe.get('protected_town_entities', []):
        if name not in entities:
            raise ValueError(f'Owned settlement fixture no longer resolves: {name}')
        entity = entities[name]
        geometry = [*entity['position'], *entity['logical_size']]
        result.append(_protection('entity.'+name, 'rect', geometry, [0,0],
                                  ['movement', 'sightline'], source='loaded town',
                                  source_path=['entities', name],
                                  note='Reserve existing owned artwork; new dressing may not replace or overlap it.'))
    for selector in recipe.get('protected_selectors', []):
        identifier = selector['id']
        if selector.get('scene') != TOWN_ID:
            raise ValueError(f'{identifier}: protection must explicitly belong to {TOWN_ID}')
        source = selector['source']
        document = json.loads(_file(root, source).read_text())
        records = _select(document, selector['path'])
        requested = selector.get('filter')
        if requested:
            found = set()
            selected = []
            for record, trail in records:
                if not isinstance(record, dict):
                    raise ValueError(f'{identifier}: filter requires object records')
                value = record.get(requested['field'])
                if value in requested['values']:
                    found.add(value)
                    selected.append((record, trail))
            if found != set(requested['values']):
                raise ValueError(f'{identifier}: missing requested records {set(requested["values"])-found}')
            records = selected
        if not records:
            raise ValueError(f'{identifier}: selector is empty')
        units = selector.get('units', 'logical')
        if units not in ('logical', 'tiles'):
            raise ValueError(f'{identifier}: unknown coordinate units {units}')
        factor = document.get('tile_size_px', town.get('tile_size', 24)) if units == 'tiles' else 1
        for index, (record, trail) in enumerate(records):
            extracted = _select(record, selector.get('geometry_path', []))
            if len(extracted) != 1:
                raise ValueError(f'{identifier}: geometry_path must resolve one shape per record')
            geometry = extracted[0][0]
            shape = selector['shape']
            if shape == 'route':
                geometry = [[v*factor for v in point] for point in geometry]
            elif isinstance(geometry, (list, tuple)):
                geometry = [v*factor for v in geometry]
            name = identifier if len(records) == 1 else f'{identifier}.{index}'
            result.append(_protection(name, shape, geometry, selector['padding'], selector['roles'],
                                      source=source, source_path=trail+selector.get('geometry_path', []),
                                      note=selector.get('note', '')))
    for reviewed in recipe.get('reviewed_regions', []):
        if reviewed.get('scene') != TOWN_ID:
            raise ValueError(f'{reviewed["id"]}: reviewed region must belong to {TOWN_ID}')
        path = _file(root, reviewed['source'])
        if sha256(path.read_bytes()).hexdigest() != reviewed['source_sha256']:
            raise ValueError(f'{reviewed["id"]}: code-owned geometry changed; review {reviewed["symbol"]}')
        result.append(_protection(reviewed['id'], 'rect', reviewed['rect'], reviewed['padding'],
                                  reviewed['roles'], source=reviewed['source'],
                                  source_symbol=reviewed['symbol'], note=reviewed['note']))
    names = [record['id'] for record in result]
    if len(names) != len(set(names)):
        raise ValueError('Duplicate settlement protection IDs')
    return result


def _overlap(a, b):
    return (a[0] < b[0]+b[2] and b[0] < a[0]+a[2] and
            a[1] < b[1]+b[3] and b[1] < a[1]+a[3])


def _line_hits(a, b, rect):
    """Slab intersection against a rectangle, including conservative edge contact."""
    low, high = 0., 1.
    for axis in (0, 1):
        delta = b[axis]-a[axis]
        start, end = rect[axis], rect[axis]+rect[axis+2]
        if not delta:
            if not start <= a[axis] <= end:
                return False
            continue
        first, last = sorted(((start-a[axis])/delta, (end-a[axis])/delta))
        low, high = max(low, first), min(high, last)
        if low > high:
            return False
    return True


def intersects(rect, protection, *, visibility=False, anchor=(12, 30)):
    """Test an occupied rectangle against a footprint-swept source geometry."""
    px, py = protection['padding']
    # Visibility includes a standing body's height above its feet. Padding in
    # movement contracts already includes the actor's horizontal footprint.
    above, below = (anchor[1], 6) if visibility else (0, 0)
    expanded = [rect[0]-px, rect[1]-py-below,
                rect[2]+2*px, rect[3]+2*py+above+below]
    shape, geometry = protection['shape'], protection['geometry']
    if shape == 'route':
        return any(_line_hits(a, b, expanded) for a, b in zip(geometry, geometry[1:]))
    if shape == 'point':
        return (expanded[0] <= geometry[0] <= expanded[0]+expanded[2] and
                expanded[1] <= geometry[1] <= expanded[1]+expanded[3])
    return _overlap(expanded, geometry)


def validate_placements(placements, protections, catalogue, town):
    """Validate future top-left logical instances; never mutate/apply them."""
    assets = {record['id']: record for record in catalogue['assets']}
    existing = {record['id'] for record in town.get('entities', [])}
    seen = set()
    width, height = town['size_pixels']
    result = []
    for placement in placements:
        name = placement.get('id', '')
        if not name.startswith('settlement.') or name in seen or name in existing:
            raise ValueError(f'{name}: instance ID must be unique in the settlement namespace')
        seen.add(name)
        asset = assets.get(placement.get('asset'))
        if asset is None:
            raise ValueError(f'{name}: unknown semantic asset {placement.get("asset")}')
        if asset.get('artwork_pixels_per_world_pixel') != 2 or not asset.get('image'):
            raise ValueError(f'{name}: placement requires a native 2x image asset')
        x, y = _numbers(placement['position'], 2, name+' position')
        w, h = _numbers(asset['logical_size'], 2, name+' size')
        if min(w, h) <= 0 or x < 0 or y < 0 or x+w > width or y+h > height:
            raise ValueError(f'{name}: artwork bounds leave the town')
        collision = placement.get('collision', 'none')
        if collision not in ('none', 'solid'):
            raise ValueError(f'{name}: unsupported collision policy')
        footprint = placement.get('footprint')
        if collision == 'solid' and footprint is None:
            raise ValueError(f'{name}: solid instance needs an explicit local footprint')
        if footprint is not None:
            fx, fy, fw, fh = _rect(footprint, name+' footprint')
            if fx < 0 or fy < 0 or fx+fw > w or fy+fh > h:
                raise ValueError(f'{name}: footprint lies outside artwork bounds')
            if collision == 'solid':
                for protected in protections:
                    if 'movement' in protected['roles'] and intersects([x+fx, y+fy, fw, fh], protected):
                        raise ValueError(f'{name}: footprint blocks {protected["id"]}')
        occlusion = placement.get('occlusion', 'tall')
        if occlusion not in ('ground', 'low', 'tall'):
            raise ValueError(f'{name}: invalid occlusion role')
        if collision == 'solid' and occlusion == 'ground':
            raise ValueError(f'{name}: ground dressing cannot be a solid obstacle')
        if occlusion == 'tall':
            for protected in protections:
                if ('sightline' in protected['roles'] and
                        intersects([x,y,w,h], protected, visibility=True,
                                   anchor=town.get('player_draw_anchor', [12,30]))):
                    raise ValueError(f'{name}: artwork obscures {protected["id"]}')
        result.append(deepcopy(placement))
    return result


def validate_district_reports(*reports):
    """Review new district proposals together, before either owns map instances."""
    seen=set();earlier=[]
    for report in reports:
        if report is None:continue
        for entity in [*report.get('entities',[]),*report.get('ground_entities',[])]:
            if entity['id'] in seen:raise ValueError('Duplicate district entity '+entity['id'])
            seen.add(entity['id'])
        for placement in report.get('placements',[]):
            rect=_rect(placement['occupied_rect'],placement['id'])
            for other in earlier:
                if _overlap(rect,other['occupied_rect']):
                    raise ValueError(placement['id']+': artwork overlaps another district '+other['id'])
        earlier.extend(report.get('placements',[]))


def framework(root, town, recipe_path=RECIPE, *, image_loader=None):
    """Emit reproducible build metadata; return no replacement map or artwork."""
    root = Path(root)
    path = _file(root, recipe_path)
    recipe = json.loads(path.read_text())
    if recipe.get('version') != 1 or recipe.get('status') not in ('framework_only', 'ground_only', 'courtyard_dressing', 'workyard_dressing'):
        raise ValueError('Unsupported settlement recipe version/status')
    if ((recipe['status'] not in ('courtyard_dressing','workyard_dressing') and recipe.get('placements') != []) or
            (recipe['status'] == 'framework_only' and recipe.get('ground_treatments') != [])):
        raise ValueError('Settlement framework cannot activate placements or ground treatments')
    if town.get('id') != TOWN_ID or recipe.get('scene') != TOWN_ID:
        raise ValueError(f'Settlement framework must use the loaded {TOWN_ID} scene')
    protections = resolve_protections(root, town, recipe)
    catalogue = inventory(root, town=town)
    from tools.eldenmere_settlement_dressing import resolve_dressing, resolve_workyards
    resolved_dressing = resolve_dressing(root, town, recipe, catalogue, protections, image_loader=image_loader)
    resolved_workyards = resolve_workyards(root, town, recipe, catalogue, protections, image_loader=image_loader)
    dressing = resolved_dressing if recipe['status'] in ('courtyard_dressing','workyard_dressing') else None
    workyards = resolved_workyards if recipe['status']=='workyard_dressing' else None
    validate_district_reports(dressing,workyards)
    if dressing is None:
        validate_placements(recipe['placements'], protections, catalogue, town)
    from tools.eldenmere_settlement_streets import resolve_streets
    treatments = resolve_streets(root, town, recipe)
    network, street_sources = resolve_street_network(root, town, recipe, treatments)
    dependencies = dict(catalogue['dependencies_sha256'])
    dependencies[recipe_path] = sha256(path.read_bytes()).hexdigest()
    if dressing is not None:
        dependencies.update(dressing['dependencies_sha256'])
    if workyards is not None:
        dependencies.update(workyards['dependencies_sha256'])
    for source in street_sources:
        dependencies[source] = sha256(_file(root, source).read_bytes()).hexdigest()
    for record in protections:
        if record['source'] != 'loaded town':
            source = record['source']
            dependencies[source] = sha256(_file(root, source).read_bytes()).hexdigest()
    # These facts track current loaded owners without pinning whole generated
    # map bytes, so a facade-only rebuild does not invalidate geometry review.
    interfaces = {key: deepcopy(town.get(key)) for key in
                  ('id','size_pixels','spawn','player_probe_size','player_draw_anchor',
                   'destinations','overworld_exit','world_links','interior_scenes')}
    interfaces['doors'] = [{key: deepcopy(door.get(key)) for key in
                           ('id','host','anchor','entry_y','entry_side','entry_half_width',
                            'open_radius','close_radius','destination','spawn','arrival_door')}
                          for door in town.get('doors', [])]
    return dict(version=1, id=recipe['id'], status=recipe['status'],
                coordinate_space='logical town units; selector padding remains logical',
                active_placements=len(recipe['placements']), active_ground_treatments=len(treatments),
                dressing=dressing, workyards=workyards,
                ground_treatments=treatments, street_network=network,
                recipe=recipe_path, districts=deepcopy(recipe['districts']),
                district_geometry=recipe['district_geometry'],
                placement_notes=deepcopy(recipe.get('placement_notes', [])),
                protected_spaces=protections, interfaces=interfaces,
                inventory=catalogue, dependencies_sha256=dict(sorted(dependencies.items())),
                excluded_coordinate_contexts=deepcopy(recipe.get('excluded_coordinate_contexts', [])))


def resolve_street_network(root, town, recipe, treatments):
    """Compile cartography from live route sources and the same painted treatments."""
    result = []
    sources = set()
    by_id = {record['id']: record for record in treatments}
    seen = set()
    items = recipe.get('street_network', [])
    if not isinstance(items, list):
        raise ValueError('Street network must be a list')
    for item in items:
        if not isinstance(item, dict):
            raise ValueError('Street network entries must be objects')
        if 'treatment' in item:
            if set(item) != {'treatment'} or item['treatment'] not in by_id:
                raise ValueError('Street network must reference an active ground treatment')
            record = deepcopy(by_id[item['treatment']])
        else:
            if item.get('units') not in ('logical', 'tiles'):
                raise ValueError('Invalid cartographic street coordinate units')
            source = item['source_ref']['file']
            selected = _select(json.loads(_file(root, source).read_text()), item['source_ref']['path'])
            if len(selected) != 1:
                raise ValueError('Street network source must resolve one route or rectangle')
            selected = selected[0][0]
            if 'source_id' in item and (not isinstance(selected, dict) or selected.get('id') != item['source_id']):
                raise ValueError('Cartographic source identity changed; review '+item['id'])
            sources.add(source)
            scale = 24 if item.get('units') == 'tiles' else 1
            record = {key: item[key] for key in ('id', 'role', 'material')}
            if item['geometry'] == 'road':
                record.update(points=[[v*scale for v in p] for p in selected['points']],
                              width=selected['width']*scale)
            elif item['geometry'] == 'points':
                record.update(points=[[v*scale for v in p] for p in selected], width=item['width'])
            elif item['geometry'] == 'rect':
                record['rect'] = [v*scale for v in selected]
            else:
                raise ValueError('Unsupported cartographic street geometry')
        name = record['id']
        if not isinstance(name, str) or not name.startswith('settlement.street.') or name in seen:
            raise ValueError('Cartographic street ID must be unique in settlement.street.*')
        seen.add(name)
        if 'rect' in record:
            x, y, w, h = _rect(record['rect'], name)
            if x < 0 or y < 0 or x+w > town['size_pixels'][0] or y+h > town['size_pixels'][1]:
                raise ValueError('Cartographic rectangle leaves town '+name)
            if w >= h:
                record.update(points=[[x+h/2, y+h/2], [x+w-h/2, y+h/2]], width=h)
            else:
                record.update(points=[[x+w/2, y+w/2], [x+w/2, y+h-w/2]], width=w)
        points = [_numbers(point, 2, name) for point in record['points']]
        if len(points) < 2 or any(not (0 <= x <= town['size_pixels'][0] and
                                     0 <= y <= town['size_pixels'][1]) for x, y in points):
            raise ValueError('Cartographic street leaves town '+name)
        if record['role'] not in ('primary','secondary','residential','junction','doorstep','desire'):
            raise ValueError('Invalid cartographic street role '+name)
        width = _numbers([record['width']], 1, name+' width')[0]
        if record['material'] not in ('stone', 'dirt') or width <= 0:
            raise ValueError('Invalid cartographic street material/width '+name)
        result.append({key: deepcopy(record[key]) for key in ('id','role','material','points','width','rect')
                       if key in record})
    return result, sources
