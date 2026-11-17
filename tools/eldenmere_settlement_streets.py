"""Ground-only Eldenmere street composition at two artwork pixels/world unit.

The settlement recipe owns explicit logical geometry. Source references are
provenance, not a second geometry override. Flat treatments guide movement;
they never change collision, navigation, entities, doors, or gameplay state.
The town composer applies this pass before masonry, stairs, water and crossings.
"""
from copy import deepcopy
from hashlib import sha256
import json
import math
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

DENSITY = 2
TILE = 24
NATIVE_TILE = TILE * DENSITY
ROLES = frozenset(('primary', 'secondary', 'residential', 'junction', 'doorstep', 'desire'))
MATERIALS = frozenset(('dirt', 'stone'))
COMMON_KEYS = frozenset(('id', 'material', 'role', 'shape', 'source_ref', 'note'))
SHAPE_KEYS = {'route': frozenset(('points', 'width')),
              'rect': frozenset(('rect', 'under_fixture')),
              'doorstep': frozenset(('door', 'width', 'depth'))}
OFFSETS = ((0,-1),(1,-1),(1,0),(1,1),(0,1),(-1,1),(-1,0),(-1,-1))
WELL_LAYOUT = 'assets/maps/eldenmere/well_square/layout.json'


def _number(value, label):
    if (type(value) not in (int, float) or not math.isfinite(value) or
            not float(value * DENSITY).is_integer()):
        raise ValueError(f'{label}: expected a finite native-half logical coordinate')
    return value


def _coordinates(value, length, label):
    if not isinstance(value, (list, tuple)) or len(value) != length:
        raise ValueError(f'{label}: expected {length} logical coordinates')
    return [_number(entry, label) for entry in value]


def _town_size(town):
    size = _coordinates(town['size_pixels'], 2, 'town size')
    if any(type(value) is not int or value <= 0 for value in size):
        raise ValueError('Street composition requires positive integer logical town dimensions')
    return size


def _file(root, relative):
    if not isinstance(relative, str):
        raise ValueError('Street source reference must be a repository-relative filename')
    path = Path(relative)
    if path.is_absolute():
        raise ValueError('Street source reference must be repository-relative')
    result = (root / path).resolve()
    if not result.is_relative_to(root.resolve()) or not result.is_file():
        raise ValueError(f'Street source reference is missing or leaves the repository: {relative}')
    return result


def _reference(root, reference, label):
    if not isinstance(reference, dict) or set(reference) != {'file', 'path'}:
        raise ValueError(f'{label}: source_ref requires only file and path')
    path = reference['path']
    if not isinstance(path, list) or any(type(key) not in (str, int) for key in path):
        raise ValueError(f'{label}: source_ref.path must contain JSON keys or indices')
    value = json.loads(_file(root, reference['file']).read_text())
    try:
        for key in path:
            value = value[key]
    except (KeyError, IndexError, TypeError) as error:
        raise ValueError(f'{label}: source reference no longer resolves') from error
    return deepcopy(reference)


def _validate_fixture_underlay(root, town, recipe, source, rect):
    """Authorize only the source well's unchanged support beneath civic paving.

    Collision continues to describe the well's solid base. This exception lets
    its authoritative ground rectangle receive the same flat stone as the
    surrounding square, without granting arbitrary streets access to blockers.
    """
    name = source['id']
    if (recipe.get('status') not in ('commons_dressing', 'household_dressing') or
            source.get('under_fixture') != 'well' or
            name != 'settlement.street.commons.well_base' or
            source.get('shape') != 'rect' or source.get('material') != 'stone'):
        raise ValueError(f'{name}: unsupported fixture underlay activation')
    if (town.get('layout_source') != WELL_LAYOUT or
            source.get('source_ref') != {'file': WELL_LAYOUT, 'path': ['well_ground_rect']}):
        raise ValueError(f'{name}: fixture underlay requires the canonical well layout source')
    layout = json.loads(_file(root, WELL_LAYOUT).read_text())
    expected = _coordinates(layout.get('well_ground_rect'), 4, name+' source well support')
    if expected[2:] != [48, 48] or rect != expected:
        raise ValueError(f'{name}: fixture underlay must equal the source well support')
    position = _coordinates(layout.get('well_position'), 2, name+' source well position')
    instances = [entity for entity in town.get('entities', []) if entity.get('id') == 'well']
    if (len(instances) != 1 or
            _coordinates(instances[0].get('position'), 2, name+' well position') != position):
        raise ValueError(f'{name}: fixture underlay requires the unchanged source well instance')


def resolve_streets(root, town, recipe):
    """Validate and resolve only explicitly enabled flat street treatments.

    Route points are logical centers; rectangles use exclusive right/bottom
    edges. A doorstep names an existing loaded-town door, then resolves a small
    rectangle at its authoritative threshold. No source/map data is mutated.
    """
    root = Path(root)
    status = recipe.get('status')
    if status not in ('framework_only', 'ground_only', 'courtyard_dressing', 'workyard_dressing', 'commons_dressing', 'household_dressing'):
        raise ValueError('Unsupported settlement street activation status')
    if recipe.get('placements') != [] and status not in ('courtyard_dressing','workyard_dressing','commons_dressing','household_dressing'):
        raise ValueError('Street composition cannot activate placements or runtime objects')
    if status in ('courtyard_dressing','workyard_dressing','commons_dressing','household_dressing'):
        config = recipe.get('courtyard_dressing')
        if not isinstance(config, dict) or config.get('district') != 'serene_terrace':
            raise ValueError('Courtyard street pass requires reviewed Serene terrace activation')
    if status in ('workyard_dressing','commons_dressing','household_dressing'):
        config=recipe.get('workyard_dressing')
        if not isinstance(config,dict) or config.get('district')!='workshop_mill':
            raise ValueError('Workyard street pass requires reviewed workshop/mill activation')
    if status in ('commons_dressing','household_dressing'):
        config=recipe.get('commons_dressing')
        if not isinstance(config,dict) or config.get('district')!='commons_households':
            raise ValueError('Commons street pass requires reviewed civic activation')
    if status=='household_dressing':
        config=recipe.get('household_dressing')
        if (not isinstance(config,dict) or config.get('district')!='commons_households'
                or not isinstance(config.get('parcels'),list) or not config['parcels']):
            raise ValueError('Household street pass requires reviewed cottage parcel activation')
    treatments = recipe.get('ground_treatments')
    if not isinstance(treatments, list):
        raise ValueError('Settlement ground_treatments must be a list')
    if status == 'framework_only' and treatments:
        raise ValueError('Framework-only settlement cannot activate ground treatments')
    width, height = _town_size(town)
    doors = {door['id']: door for door in town.get('doors', [])}
    result, seen = [], set()
    for source in treatments:
        if not isinstance(source, dict):
            raise ValueError('Street treatment must be an object')
        name = source.get('id')
        if (not isinstance(name, str) or not name.startswith('settlement.street.') or
                name == 'settlement.street.' or name in seen):
            raise ValueError(f'{name}: street ID must be unique in settlement.street.*')
        seen.add(name)
        shape = source.get('shape')
        if not isinstance(shape, str) or shape not in SHAPE_KEYS:
            raise ValueError(f'{name}: unsupported street shape {shape}')
        unknown = set(source) - COMMON_KEYS - SHAPE_KEYS[shape]
        if unknown:
            raise ValueError(f'{name}: unsupported street treatment keys {sorted(unknown)}')
        if (not isinstance(source.get('material'), str) or source['material'] not in MATERIALS or
                not isinstance(source.get('role'), str) or source['role'] not in ROLES):
            raise ValueError(f'{name}: unsupported street material or role')
        resolved = deepcopy(source)
        if 'source_ref' in source:
            resolved['source_ref'] = _reference(root, source['source_ref'], name)
        if shape == 'route':
            points = source.get('points')
            if not isinstance(points, list) or len(points) < 2:
                raise ValueError(f'{name}: route needs at least two points')
            points = [_coordinates(point, 2, name+' point') for point in points]
            if any(not (0 <= x <= width and 0 <= y <= height) for x, y in points):
                raise ValueError(f'{name}: route leaves town bounds')
            if any(a == b for a, b in zip(points, points[1:])):
                raise ValueError(f'{name}: route has a zero-length segment')
            route_width = _number(source.get('width'), name+' width')
            if not 12 <= route_width <= 72:
                raise ValueError(f'{name}: route width must be 12..72 logical units')
            resolved.update(points=points, width=route_width)
        else:
            if shape == 'doorstep':
                door_id = source.get('door')
                door = doors.get(door_id) if isinstance(door_id, str) else None
                if door is None:
                    raise ValueError(f'{name}: unknown loaded-town door {source.get("door")}')
                step_width = _number(source.get('width'), name+' width')
                depth = _number(source.get('depth'), name+' depth')
                if not 24 <= step_width <= 48 or not 12 <= depth <= 36:
                    raise ValueError(f'{name}: doorstep width must be 24..48 and depth 12..36')
                anchor_x, anchor_y = _coordinates(door['anchor'], 2, name+' door anchor')
                rect = [anchor_x-step_width/2, anchor_y-6, step_width, depth]
                rect = _coordinates(rect, 4, name+' resolved doorstep')
                resolved.update(shape='rect', source_shape='doorstep', rect=rect)
            else:
                rect = _coordinates(source.get('rect'), 4, name+' rectangle')
                resolved['rect'] = rect
            x, y, w, h = rect
            if min(w,h) <= 0 or x < 0 or y < 0 or x+w > width or y+h > height:
                raise ValueError(f'{name}: rectangle leaves town bounds or is empty')
            if 'under_fixture' in source:
                _validate_fixture_underlay(root, town, recipe, source, rect)
        result.append(resolved)
    return result


def _mask(size, records):
    """Rasterize hard native coverage; route caps/joints remain comfortably rounded."""
    out = Image.new('L', size)
    draw = ImageDraw.Draw(out)
    for record in records:
        if record['shape'] == 'rect':
            x,y,w,h = (round(v*DENSITY) for v in record['rect'])
            draw.rectangle((x,y,x+w-1,y+h-1), fill=255)
        else:
            points = [(round(x*DENSITY),round(y*DENSITY)) for x,y in record['points']]
            width = round(record['width']*DENSITY)
            # Pillow lines preserve native pixels, without antialiasing or a
            # logical-resolution intermediate. Explicit caps join bent routes.
            draw.line(points, fill=255, width=width, joint='curve')
            radius = width/2
            for x,y in points:
                draw.ellipse((x-radius,y-radius,x+radius-1,y+radius-1), fill=255)
    return out


def _tile_mask(cells, x, y):
    value = 0
    for index, (dx,dy) in enumerate(OFFSETS):
        if ((x+dx,y+dy) in cells and
                (not (dx and dy) or ((x+dx,y) in cells and (x,y+dy) in cells))):
            value |= 1 << index
    return value


def paint_streets(base, root, town, recipe, materials, blocked):
    """Return a new native base and evidence; never write files or map geometry.

    ``report['coverage_mask']`` is a native binary PIL L image for diagnostics
    and intentional-diff checks. Remove that one field before JSON export. All
    other report fields are serializable. Source textures retain native scale.
    """
    root = Path(root)
    treatments = resolve_streets(root, town, recipe)
    size = tuple(v*DENSITY for v in _town_size(town))
    if not isinstance(base, Image.Image) or base.mode != 'RGBA' or base.size != size:
        raise ValueError('Street base must be native 2x RGBA at the logical town dimensions')
    if (not isinstance(blocked, Image.Image) or blocked.mode != 'L' or
            blocked.size != tuple(town['size_pixels'])):
        raise ValueError('Street blocked mask must be logical-size L collision data')
    allowed = blocked.point(lambda value: 0 if value else 255).resize(size, Image.Resampling.NEAREST)
    masks = {}
    for material in MATERIALS:
        ordinary = [record for record in treatments
                    if record['material'] == material and 'under_fixture' not in record]
        underlays = [record for record in treatments
                    if record['material'] == material and 'under_fixture' in record]
        clipped = ImageChops.multiply(_mask(size, ordinary), allowed)
        # resolve_streets has already proved that each underlay is precisely
        # the original well's 48x48 support; all other coverage stays clipped.
        masks[material] = ImageChops.lighter(clipped, _mask(size, underlays))
    result = base.copy()
    coverage = Image.new('L', size)
    dependencies, images = {}, {}

    def path(relative):
        file = _file(root, relative)
        name = file.relative_to(root.resolve()).as_posix()
        dependencies[name] = sha256(file.read_bytes()).hexdigest()
        return file

    def load(relative):
        name = str(relative)
        if name not in images:
            with Image.open(path(name)) as source:
                native = source.convert('RGBA')
            if native.size != (NATIVE_TILE,NATIVE_TILE):
                raise ValueError(f'Street tile is not native 48x48 artwork: {name}')
            if set(native.getchannel('A').tobytes()) - {0,255}:
                raise ValueError(f'Street tile has nonbinary alpha: {name}')
            images[name] = native
        return images[name]

    for record in treatments:
        if 'source_ref' in record:
            path(record['source_ref']['file'])

    if any(mask.getbbox() for mask in masks.values()):
        dirt_manifest = 'assets/terrain/eldenmere/grass_dirt_hd/tileset.json'
        dirt_pack = json.loads(path(dirt_manifest).read_text())
        if dirt_pack['artwork_pixels_per_world_pixel'] != DENSITY:
            raise ValueError('Street dirt bank must retain native 2x density')
        dirt_record = next(record for record in dirt_pack['tiles'] if record['mask'] == 255)
        dirt_path = (Path(dirt_manifest).parent/dirt_record['file']).as_posix()
        native_dirt = load(dirt_path)
        # The current Materials owner supplies this bank. Verify the supplied
        # object agrees with the source record whose hash is being reported.
        if materials.dirt[255].convert('RGBA').tobytes() != native_dirt.tobytes():
            raise ValueError('Street Materials dirt binding disagrees with its maintained source')
        pattern = Image.new('RGBA', size)
        for y in range(0,size[1],NATIVE_TILE):
            for x in range(0,size[0],NATIVE_TILE):
                pattern.alpha_composite(native_dirt,(x,y))
        substrate = ImageChops.lighter(masks['dirt'],masks['stone'])
        overlay = pattern.copy()
        overlay.putalpha(ImageChops.multiply(overlay.getchannel('A'),substrate))
        result.alpha_composite(overlay)
        coverage = ImageChops.lighter(coverage,overlay.getchannel('A'))

    if masks['stone'].getbbox():
        manifest = 'assets/terrain/eldenmere/stone_paving_hd/tileset.json'
        bank = json.loads(path(manifest).read_text())
        if bank['artwork_pixels_per_world_pixel'] != DENSITY or bank['texture_phase_count'] != 4:
            raise ValueError('Street paving requires native four-phase stone artwork')
        records = {record['mask']:record for record in bank['tiles']}
        cells = {(x,y) for y in range((size[1]+NATIVE_TILE-1)//NATIVE_TILE)
                 for x in range((size[0]+NATIVE_TILE-1)//NATIVE_TILE)
                 if masks['stone'].crop((x*NATIVE_TILE,y*NATIVE_TILE,
                                         (x+1)*NATIVE_TILE,(y+1)*NATIVE_TILE)).getbbox()}
        overlay = Image.new('RGBA',size)
        for x,y in sorted(cells):
            record = records[_tile_mask(cells,x,y)]
            phase = x%2+2*(y%2)
            origin = (x*NATIVE_TILE,y*NATIVE_TILE)
            overlay.alpha_composite(load((Path(manifest).parent/record['contact_files']['dirt']).as_posix()),origin)
            overlay.alpha_composite(load((Path(manifest).parent/record['body_files'][phase]).as_posix()),origin)
        overlay.putalpha(ImageChops.multiply(overlay.getchannel('A'),masks['stone']))
        result.alpha_composite(overlay)
        coverage = ImageChops.lighter(coverage,overlay.getchannel('A'))

    cartography = [{key:deepcopy(record[key]) for key in
                   ('id','material','role','shape','points','width','rect','door') if key in record}
                  for record in treatments]
    native_pixels = coverage.histogram()[255]
    report = dict(treatments=treatments, cartography=cartography,
                  painted_native_pixels=native_pixels, painted_logical_area=native_pixels/4,
                  coverage_sha256=sha256(coverage.tobytes()).hexdigest(),
                  coverage_bounds_native=list(coverage.getbbox()) if coverage.getbbox() else None,
                  source_dependencies_sha256=dict(sorted(dependencies.items())), coverage_mask=coverage)
    return result, report
