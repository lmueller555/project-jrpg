"""Register authored Ice Reaper scenery and approved party sprites."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys

from PIL import Image, ImageChops, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.build_opening_cinematic_scenery import digest, pixel_alpha, record

SOURCE = ROOT/'assets/source/cinematics/ice_reaper_opening'
TARGET = ROOT/'assets/story/ice_reaper_opening'
SIZE = (960, 480)
PARTY = {
    'caelan': ('assets/story/opening_cinematic/actors/caelan/animation.json', 'stand_empty'),
    'mira': ('assets/story/opening_cinematic/actors/mira/animation.json', 'stand'),
    'rhea': ('assets/combat/rhea/animation.json', 'idle'),
    'lucan': ('assets/combat/lucan/animation.json', 'idle'),
}


def save_json(path, data):
    path.write_text(json.dumps(data, indent=2)+'\n', encoding='utf-8')


def native_sprite(image, height):
    image = pixel_alpha(image)
    bounds = image.getbbox()
    if bounds is None:
        raise ValueError('Empty authored ice sprite')
    image = image.crop(bounds)
    scale = height/image.height
    image = image.resize((round(image.width*scale), height), Image.Resampling.NEAREST)
    alpha = image.getchannel('A')
    image = image.convert('RGB').quantize(
        colors=96, dither=Image.Dither.NONE).convert('RGBA')
    image.putalpha(alpha)
    return image, bounds, scale


def export_party():
    records = {}
    for actor, (filename, pose) in PARTY.items():
        manifest_path = ROOT/filename
        manifest = json.loads(manifest_path.read_text())
        output = TARGET/'actors'/actor
        output.mkdir(parents=True, exist_ok=True)
        sources = []

        def copy_frame(source_name, target_name):
            source = (manifest_path.parent/source_name).resolve()
            if not source.is_relative_to(ROOT/'assets'):
                raise ValueError('Party frame leaves the asset tree')
            with Image.open(source) as image:
                if list(image.size) != manifest['canvas']:
                    raise ValueError('Party frame differs from its approved canvas')
            before = digest(source)
            shutil.copyfile(source, output/target_name)
            if digest(source) != before or digest(output/target_name) != before:
                raise AssertionError('An existing cinematic frame changed')
            sources.append(record(source))

        combat = 'animations' in manifest
        source_pose = manifest['animations'][pose]['frames'][0]['file'] if combat else manifest['poses'][pose]
        copy_frame(source_pose, 'stand.png')
        data = dict(version=1, actor=actor, canvas=manifest['canvas'],
                    anchor=manifest['anchor'], poses={'stand': 'stand.png'},
                    source_manifest=filename, copied_without_pixel_changes=True)
        if actor == 'lucan':
            loop = []
            for index, frame in enumerate(manifest['animations']['idle']['frames'], 1):
                name = f'ready_{index:02}.png'
                copy_frame(frame['file'], name)
                loop.append(dict(file=name, duration_ms=frame['duration_ms']))
            data['loops'] = {'ready': loop}
        if actor == 'caelan':
            loop = []
            for index, frame in enumerate(manifest['loops']['walk_left'], 1):
                name = f'walk_left_{index:02}.png'
                copy_frame(frame['file'], name)
                loop.append(dict(file=name, duration_ms=frame['duration_ms']))
            data['loops'] = {'walk_left': loop}
        save_json(output/'animation.json', data)
        records[actor] = dict(manifest=dict(file=filename, sha256=digest(manifest_path)), frames=sources,
                              pixel_changes=False)
    return records


def export_prison():
    with Image.open(SOURCE/'prison_generated.png') as source:
        image, _, _ = native_sprite(source, 128)
    if image.width > 84:
        raise ValueError('The ice prison needs new registration')
    registered = Image.new('RGBA', (88, 136))
    registered.alpha_composite(image, ((88-image.width)//2, 130-image.height))
    alpha = registered.getchannel('A')
    rim = ImageChops.subtract(alpha, alpha.filter(ImageFilter.MinFilter(9)))
    back = registered.copy()
    back.putalpha(alpha.point(lambda value: round(value*.55)))
    front = registered.copy()
    front.putalpha(ImageChops.lighter(
        alpha.point(lambda value: round(value*.2)),
        rim.point(lambda value: round(value*.9))))
    back.save(TARGET/'ice_prison_back.png', optimize=True)
    front.save(TARGET/'ice_prison_front.png', optimize=True)


def build():
    TARGET.mkdir(parents=True, exist_ok=True)
    names = ('environment_generated.png', 'ice_reaper_generated.png',
             'brush_generated.png', 'prison_generated.png')
    before = {name: digest(SOURCE/name) for name in names}
    with Image.open(SOURCE/names[0]) as image:
        if image.size != (1774, 887):
            raise ValueError('Environment source needs new registration')
        image.convert('RGB').resize(SIZE, Image.Resampling.NEAREST).save(
            TARGET/'environment.png', optimize=True)
    with Image.open(SOURCE/names[2]) as image:
        if image.size != (1774, 887):
            raise ValueError('Brush source needs new registration')
        brush = pixel_alpha(image).resize(SIZE, Image.Resampling.NEAREST)
        for side, box, position in (
                ('left', (0, 0, 480, 480), (0, 0)),
                ('right', (480, 0, 960, 480), (480, 0))):
            layer = Image.new('RGBA', SIZE)
            layer.alpha_composite(brush.crop(box), position)
            layer.save(TARGET/f'brush_{side}.png', optimize=True)

    with Image.open(SOURCE/names[1]) as opened:
        if opened.size != (1024, 1536):
            raise ValueError('Ice Reaper source needs new registration')
        image = opened.convert('RGBA')
        caster = image.crop((40, 430, 950, 1520))
        # The shard overlaps the wing tips' vertical rows, but not their pixels.
        # Exclude only its registered cell rather than cutting off the wings.
        alpha = caster.getchannel('A')
        ImageDraw.Draw(alpha).rectangle((360, 0, 590, 58), fill=0)
        caster.putalpha(alpha)
        caster, bounds, scale = native_sprite(caster, 110)
        pose = Image.new('RGBA', (192, 176))
        ground_x = (512-40-bounds[0])*scale
        offset = (round(96-ground_x), 168-caster.height)
        pose.alpha_composite(caster, offset)
        folder = TARGET/'actors/ice_reaper'
        folder.mkdir(parents=True, exist_ok=True)
        pose.save(folder/'charge.png', optimize=True)
        save_json(folder/'animation.json', dict(
            version=1, actor='ice_reaper', canvas=[192, 176], anchor=[96, 168],
            poses={'charge': 'charge.png'}, status='awaiting_review',
            source='assets/source/cinematics/ice_reaper_opening/ice_reaper_generated.png',
            extraction=dict(crop=[40, 430, 950, 1520], excluded_shard_cell=[400, 430, 630, 488],
                            content_bounds=list(bounds), uniform_scale=scale,
                            target_height=110, offset=list(offset))))
        shard, shard_bounds, shard_scale = native_sprite(
            image.crop((410, 0, 609, 488)), 74)
        shard.save(TARGET/'glacial_shard.png', optimize=True)

    export_prison()
    party = export_party()
    if before != {name: digest(SOURCE/name) for name in names}:
        raise AssertionError('An original generated source was modified')
    exports = [record(path) for path in sorted(TARGET.rglob('*.png'))]
    audit = dict(
        version=1, exporter='tools/build_ice_reaper_opening.py',
        canvas=list(SIZE), sources=[record(SOURCE/name) for name in names],
        new_art_status='awaiting_user_review', party=party, exports=exports,
        registration=dict(
            ice_reaper_position=[510, 260], glacial_shard_position=[510, 140],
            glacial_shard_anchor=[shard.width//2, shard.height],
            glacial_shard_crop=[410, 0, 609, 488],
            glacial_shard_content_bounds=list(shard_bounds),
            glacial_shard_scale=shard_scale,
            frozen_rhea_position=[335, 374], prison_anchor=[44, 130]),
        notes=[
            'New scenery, brush and boss artwork are authored image-generation sources.',
            'Generated source images are retained unchanged.',
            'Party frames are exact approved assets: Caelan/Mira cinematic motion, Rhea/Lucan combat art; display scale is scene metadata.',
            'Mechanical crop, alpha cleanup, nearest scaling and new-sprite palette registration only.',
            'The authored ice prison uses transparent front/back planes, not a replacement Rhea sprite.',
            'No party actors are baked into the background.',
        ])
    save_json(TARGET/'provenance.json', audit)
    print(json.dumps(dict(canvas=SIZE, exports=len(exports),
                          shard_anchor=audit['registration']['glacial_shard_anchor'])))


if __name__ == '__main__':
    build()
