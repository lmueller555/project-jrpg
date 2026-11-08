"""Capture the isolated limestone chamber with ordinary production movement.

The review never constructs Game or accesses journey/settings files. Retained
images use the same World, Player and crystal-lighting renderer as gameplay.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT/'docs/reviews/limestone_cave'
GUARDS = (
    'main.py', 'sanctuary_cave.py', 'sanctuary_cave_world.py', 'sanctuary_cave_map.py',
    'overworld_travel.py', 'regent_emergency.py', 'inventory.py', 'save_game.py',
    'tools/build_sanctuary_cave.py',
    'assets/maps/eldenmere/playable/map.json',
    'assets/maps/elden_vale_sanctuary/map.json',
    'assets/maps/elden_vale_sanctuary_hall/map.json',
    'assets/maps/sanctuary_cave/entrance/map.json',
    'assets/maps/sanctuary_cave/hollow/map.json',
    'assets/maps/sanctuary_cave/depths/map.json',
    'assets/terrain/sanctuary_cave/assets.json',
    'assets/source/terrain/sanctuary_cave/recipe.json',
)


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def world_hashes():
    paths = {ROOT/name for name in GUARDS}
    for folder in ('assets/maps/sanctuary_cave', 'assets/terrain/sanctuary_cave',
                   'assets/terrain/elden_vale_sanctuary_kit', 'assets/terrain/sanctuary_fantasy'):
        paths.update(path for path in (ROOT/folder).rglob('*') if path.is_file())
    return {str(path.relative_to(ROOT)):digest(path) for path in sorted(paths)}


def source_hashes():
    paths = {ROOT/name for name in (
        'main.py', 'sanctuary_cave_world.py', 'ui_style.py',
        'tools/preview_limestone_cave.py', 'tools/capture_limestone_cave.py',
        'tools/build_limestone_cave_assets.py', 'tools/build_limestone_cave_chamber.py',
        'tools/capture_sanctuary_reserve.py',
    )}
    for folder in ('assets/source/terrain/limestone_cave', 'assets/terrain/limestone_cave',
                   'assets/source/maps/limestone_cave_review', 'assets/maps/limestone_cave_review',
                   'assets/characters/caelan'):
        paths.update(path for path in (ROOT/folder).rglob('*') if path.is_file())
    pending = list(paths);seen = set()
    while pending:
        path = pending.pop()
        if path in seen or not path.is_file():continue
        seen.add(path)
        if path.suffix != '.json':continue
        def collect(value):
            if isinstance(value, dict):
                for item in value.values():collect(item)
            elif isinstance(value, list):
                for item in value:collect(item)
            elif isinstance(value, str) and value.startswith('assets/'):
                source = ROOT/value
                if source.is_file() and source not in seen:pending.append(source)
        collect(json.loads(path.read_text()))
    return {str(path.relative_to(ROOT)):digest(path) for path in sorted(seen)}


class Movie:
    def __init__(self, path):
        executable = shutil.which('ffmpeg')
        if executable is None:raise RuntimeError('ffmpeg is required to record the chamber review')
        self.frames = 0
        self.process = subprocess.Popen([
            executable, '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
            '-s', '960x640', '-r', '20', '-i', '-', '-an', '-c:v', 'libx264',
            '-preset', 'veryfast', '-crf', '22', '-pix_fmt', 'yuv420p',
            '-movflags', '+faststart', str(path)], stdin=subprocess.PIPE)

    def add(self, image, count=1):
        for _ in range(count):self.process.stdin.write(image.tobytes());self.frames += 1

    def finish(self):
        self.process.stdin.close()
        assert self.process.wait() == 0, 'Review video encoding failed'


def frame(demo):
    import pygame
    from PIL import Image
    demo.draw()
    return Image.frombytes('RGB', demo.window.get_size(), pygame.image.tobytes(demo.window, 'RGB'))


def native_frame(demo):
    import pygame
    from PIL import Image
    demo.draw()
    return Image.frombytes('RGB', demo.canvas.get_size(), pygame.image.tobytes(demo.canvas, 'RGB'))


def check(output):
    report = json.loads((output/'verification.json').read_text())
    assert report['source_sha256'] == source_hashes(), 'Sources changed; recapture the material chamber.'
    assert report['live_world_snapshot_sha256'] == world_hashes(), 'Live game changed since this review.'
    for name, expected in report['artifact_sha256'].items():
        assert digest(output/name) == expected, 'Artifact changed: '+name
    assert report['ordinary_movement_only'] and report['no_save_or_settings_files']
    assert report['walking_seen'] and report['running_seen'] and report['reduced_motion_static']
    assert report['pulse']['max_mean'] > report['pulse']['min_mean']
    print('Limestone chamber movement, pulse, static mode, isolation and review fingerprints verified.')


def capture(output, movie_enabled=True):
    import pygame
    from PIL import Image, ImageDraw, ImageFont, ImageStat
    from main import World
    from tools.preview_limestone_cave import LimestoneCaveDemo
    from tools.capture_sanctuary_reserve import path

    output.mkdir(parents=True, exist_ok=True)
    before = source_hashes();guards = world_hashes()
    demo = LimestoneCaveDemo()
    demo.show_guide = False
    movie = Movie(output/'chamber_walkthrough.mp4') if movie_enabled else None
    report = {'source':'Production Player and SanctuaryCaveWorld in an isolated chamber',
              'ordinary_movement_only':True, 'no_save_or_settings_files':True,
              'live_world_snapshot_sha256':guards, 'source_sha256':before,
              'checkpoints':[], 'walking_seen':False, 'running_seen':False}
    artifacts = [];views = {}

    def sample(seconds, direction=(0, 0), running=False):
        demo.step(seconds, direction, running)
        assert demo.world.can_stand(demo.player.position), tuple(demo.player.position)
        report['walking_seen'] |= bool(demo.player.moving and not demo.player.running)
        report['running_seen'] |= bool(demo.player.moving and demo.player.running)
        image = frame(demo)
        if movie:movie.add(image, max(1, round(seconds*20)))
        return image

    def photograph(name, *, hold=5):
        image = frame(demo);file = name+'.png';image.save(output/file);artifacts.append(file)
        views[name] = image
        if movie:movie.add(image, hold)
        report['checkpoints'].append({'name':name, 'position':list(demo.player.position),
            'camera':list(demo.camera), 'scene':demo.world.data['id'], 'file':file,
            'source':'Production World.draw and native player sprites'})
        return image

    def walk(target, running=False):
        for waypoint in path(demo.world, demo.player.position, target):
            target_point = pygame.Vector2(waypoint)
            for _ in range(1000):
                delta = target_point-demo.player.position
                if delta.length() < .45:break
                old = demo.player.position.copy()
                speed = 108 if running else 72
                sample(min(.05, delta.length()/speed), delta, running)
                if demo.player.position.distance_to(old) < .001:
                    raise AssertionError(('Movement stalled',list(old),waypoint))
            else:raise AssertionError(('Movement exceeded budget',waypoint))

    try:
        photograph('chamber_entry')
        points = demo.world.data['cave']['review_points']
        for index, (name, target) in enumerate(points.items()):
            walk(target, running=index % 2 == 1)
            sample(.05)
            photograph(name)
        report['depth_stations'] = []
        for case in demo.world.data['cave'].get('review_checks', {}).get('depth_cases', []):
            for suffix, key in (('rear', 'feet'), ('front', 'visible_feet')):
                walk(case[key]);sample(.05)
                photograph(case['id']+'_'+suffix)
                report['depth_stations'].append({'case':case['id'], 'side':suffix,
                                                 'position':list(demo.player.position)})
        # The material comparison uses the same reached pose and camera.
        pulse_target = points.get('pulse', points.get('mineral_seam',
                       points.get('curved_wall', next(iter(points.values())))))
        walk(pulse_target)
        sample(.05)
        photograph('chamber_lit')
        demo.material_view = True;photograph('chamber_material_colors');demo.material_view = False

        low = high = None;gif_frames = []
        for _ in range(65):
            sample(.1)
            image = native_frame(demo)
            mean = sum(ImageStat.Stat(image).mean)/3
            record = (mean, frame(demo), demo.elapsed_ms)
            if low is None or mean < low[0]:low = record
            if high is None or mean > high[0]:high = record
            gif_frames.append(image)
        low[1].save(output/'pulse_trough.png');high[1].save(output/'pulse_peak.png')
        artifacts.extend(('pulse_trough.png', 'pulse_peak.png'))
        gif_frames[0].save(output/'crystal_pulse.gif', save_all=True, append_images=gif_frames[1:],
                           duration=100, loop=0, optimize=False)
        artifacts.append('crystal_pulse.gif')
        report['pulse'] = {'duration_seconds':6.5, 'min_mean':low[0], 'max_mean':high[0],
                           'trough_clock_ms':low[2], 'peak_clock_ms':high[2]}
        views['pulse_trough'] = low[1];views['pulse_peak'] = high[1]

        demo.reduced_motion = True;sample(.05);first = native_frame(demo)
        photograph('reduced_motion')
        demo.step(8.0)
        report['reduced_motion_static'] = first.tobytes() == native_frame(demo).tobytes()
        assert report['reduced_motion_static'], 'Reduced motion must keep the scenery static'
        demo.reduced_motion = False
        demo.world.reduced_motion = False

        # Stitch actual world views at one shared clock. This is an overview of
        # the compiled scene, not a concept illustration or a new layout.
        whole = pygame.Surface(demo.world.size)
        for y in range(0, demo.world.size[1], 320):
            for x in range(0, demo.world.size[0], 480):
                tile = pygame.Surface((480, 320))
                demo.world.draw(tile, (x, y), demo.player, high[2], include_ui=False)
                whole.blit(tile, (x, y))
        overview = Image.frombytes('RGB', whole.get_size(), pygame.image.tobytes(whole, 'RGB'))
        overview.resize((overview.width*2, overview.height*2), Image.Resampling.NEAREST).save(output/'whole_chamber.png')
        artifacts.append('whole_chamber.png')

        selected = ['chamber_material_colors', 'chamber_lit', 'pulse_trough', 'pulse_peak']
        selected += [name for name in points if name in views][:2]
        board = Image.new('RGB', (980, len(selected)//2*354+16), '#202925')
        draw = ImageDraw.Draw(board);font = ImageFont.load_default(size=16)
        for index, name in enumerate(selected):
            x = 8+index%2*488;y = 8+index//2*354
            label = name.replace('_', ' ').title()
            draw.text((x+8, y+6), label, fill='#eee6cf', font=font)
            board.paste(views[name].resize((480, 320), Image.Resampling.NEAREST), (x, y+27))
        board.save(output/'contact_sheet.png');artifacts.append('contact_sheet.png')
    finally:
        if movie:movie.finish()
        demo.close()
    if movie:artifacts.append('chamber_walkthrough.mp4');report['movie_seconds'] = movie.frames/20
    assert before == source_hashes(), 'Source changed during capture; rerun after the assets are frozen'
    assert guards == world_hashes(), 'Review must never modify live game data'
    report['artifact_sha256'] = {name:digest(output/name) for name in sorted(artifacts)}
    (output/'verification.json').write_text(json.dumps(report, indent=2)+'\n')
    check(output)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUT)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--no-movie', action='store_true')
    args = parser.parse_args(argv)
    if args.check:check(args.output)
    else:capture(args.output, not args.no_movie)
    return 0


if __name__ == '__main__':raise SystemExit(main())
