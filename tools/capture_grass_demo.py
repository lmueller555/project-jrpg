"""Record the playable grass prototype using the production Player and world.

The scene is isolated from game journeys. Every review position is reached by
ordinary walking/running; captures never substitute a character pose or bend.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT/'docs/reviews/grass_demo'
FPS = 20
SIZE = (960, 640)
BASE_COMMIT = '948e96553dba03b652ba634de22bb809d4d5dcfd'
GUARDS = (
    'assets/maps/eldenmere/playable/map.json',
    'assets/maps/elden_vale_sanctuary/map.json',
    'assets/maps/elden_vale_sanctuary_hall/map.json',
    'assets/terrain/eldenmere/grass_dirt/palette.json',
    'assets/terrain/eldenmere/grass_dirt/tileset.json',
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hashes():
    paths = {ROOT/name for name in (
        'main.py', 'interactive_grass.py', 'grass_demo.py',
        'tools/preview_grass.py', 'tools/capture_grass_demo.py',
        'tools/build_grass_demo_assets.py', 'tools/build_grass_demo_scene.py',
        'assets/maps/grass_demo/map.json', 'assets/terrain/grass_demo/assets.json')}
    for folder in ('assets/source/terrain/grass_demo', 'assets/source/maps/grass_demo'):
        paths.update(path for path in (ROOT/folder).rglob('*') if path.is_file())
    pending = list(paths)
    seen = set()
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
    for direction in ('front', 'back', 'left', 'right'):
        seen.add(ROOT/f'assets/characters/caelan/idle_{direction}.png')
        for gait in ('walk', 'run'):
            seen.update(path for path in (ROOT/f'assets/characters/caelan/{gait}_{direction}').rglob('*')
                        if path.is_file() and path.suffix in ('.json', '.png'))
    return {str(path.relative_to(ROOT)): digest(path) for path in sorted(seen)}


def unchanged_worlds():
    hashes = {}
    for name in GUARDS:
        expected = hashlib.sha256(subprocess.check_output(
            ['git', 'show', BASE_COMMIT+':'+name], cwd=ROOT)).hexdigest()
        assert digest(ROOT/name) == expected, 'Existing map or grass pack changed: '+name
        hashes[name] = expected
    return hashes


def height_comparison(output):
    """Compare unoccupied native art at one scale and visible-ground baseline.

    This is an explicitly labeled asset board, separate from the actual gameplay
    photographs. Alpha bounds measure height, rather than transparent canvases.
    """
    from PIL import Image, ImageDraw, ImageFont
    manifest = json.loads((ROOT/'assets/terrain/grass_demo/assets.json').read_text())
    character = Image.open(ROOT/'assets/characters/caelan/idle_front.png').convert('RGBA')
    character_bounds = character.getbbox()
    character_height = character_bounds[3]-character_bounds[1]
    anchor_y = manifest['tall_grass']['anchor'][1]
    variants = []
    for name, variant in manifest['tall_grass']['variants'].items():
        idle = []
        all_records = list(variant['idle'])
        for frames in variant['parted'].values():all_records.extend(frames)
        heights, foreground_tops = [], []
        for record in all_records:
            rear = Image.open(ROOT/record['rear']).convert('RGBA')
            front = Image.open(ROOT/record['front']).convert('RGBA')
            combined = Image.alpha_composite(rear, front)
            bounds = combined.getbbox()
            heights.append(bounds[3]-bounds[1])
            front_bounds = front.getbbox()
            if front_bounds:foreground_tops.append(front_bounds[1])
            if record in variant['idle']:idle.append((bounds[3]-bounds[1], combined))
        height, image = max(idle, key=lambda pair: pair[0])
        variants.append({'id': name, 'visible_height': height,
                         'all_pose_max_height': max(heights),
                         'ratio_to_caelan': height/character_height,
                         'foreground_max_above_anchor': anchor_y-min(foreground_tops),
                         'image': image})
    factor, baseline = 6, 320
    board = Image.new('RGB', (960, 390), manifest['palette']['base'])
    painter = ImageDraw.Draw(board)
    title_font = ImageFont.load_default(size=19)
    label_font = ImageFont.load_default(size=16)
    small_font = ImageFont.load_default(size=14)
    painter.rectangle((0, 0, 959, 76), fill='#123c2d')
    painter.text((20, 12), 'Native height study: unoccupied grass and Caelan',
                 fill='#eef1d9', font=title_font)
    painter.text((20, 43), 'All art enlarged 6x | visible alpha bounds | common ground baseline',
                 fill='#cbdac2', font=small_font)
    halfway = baseline-character_height*factor/2
    for x in range(20, 940, 14):
        painter.line((x, round(halfway), min(939, x+7), round(halfway)), fill='#acc6a0')
    painter.text((744, round(halfway)-22), 'Half Caelan height', fill='#e5edcf', font=small_font)
    painter.line((20, baseline+1, 940, baseline+1), fill='#f0e2ae', width=2)
    art = [('Caelan', character, character_height),
           *[(variant['id'].title(), variant['image'], variant['visible_height']) for variant in variants]]
    for index, (label, image, height) in enumerate(art):
        crop = image.crop(image.getbbox())
        crop = crop.resize((crop.width*factor, crop.height*factor), Image.Resampling.NEAREST)
        center = 100+index*180
        board.paste(crop, (center-crop.width//2, baseline-crop.height), crop)
        text = f'{label}: {height}px'
        width = painter.textlength(text, font=label_font)
        painter.text((center-width/2, 338), text, fill='#f0efd9', font=label_font)
        if index:
            text = f'{100*height/character_height:.0f}% of Caelan'
            width = painter.textlength(text, font=small_font)
            painter.text((center-width/2, 362), text, fill='#d9e5c8', font=small_font)
    board.save(output/'height_comparison.png')
    return {'source': 'native unoccupied rear/front art and idle_front character; alpha-cropped',
            'character_visible_height': character_height, 'enlargement': factor,
            'common_visible_ground_baseline': True,
            'variants': [{key: value for key, value in variant.items() if key != 'image'}
                         for variant in variants]}


def check(output):
    report = json.loads((output/'verification.json').read_text())
    assert report['source_sha256'] == source_hashes(), 'Sources changed; recapture the prototype.'
    assert report['existing_world_sha256'] == unchanged_worlds()
    for name, expected in report['artifact_sha256'].items():
        assert digest(output/name) == expected, 'Artifact changed: '+name
    assert report['ordinary_movement_only'] and report['no_save_or_settings_files']
    assert report['walking_seen'] and report['running_seen']
    assert report['standing_occupied_seen'] and report['fully_recovered_after_exit']
    assert report['max_strength'] >= 1.9, 'Running did not produce stronger parting.'
    assert report['max_occupied'] > 0
    assert report['upper_body_pixel_checks'] > 0
    assert report['upper_body_occluded_pixels'] == 0
    assert report['leg_overlap_frames'] > 0
    assert 25 <= report['movie']['seconds'] <= 55
    assert report['movie']['size'] == list(SIZE)
    height = report['height_comparison']
    assert height['common_visible_ground_baseline']
    for variant in height['variants']:
        assert variant['all_pose_max_height'] <= math.ceil(height['character_visible_height']/2)
        assert variant['foreground_max_above_anchor'] <= 5
    print('Grass demo movement, occupancy, recovery, original worlds and capture hashes verified.')


def capture(output, movie_enabled=True):
    import pygame
    from PIL import Image, ImageDraw
    from tools.preview_grass import GrassDemo

    output.mkdir(parents=True, exist_ok=True)
    before = source_hashes()
    guards = unchanged_worlds()
    demo = GrassDemo(window_size=SIZE)
    route = demo.world.data.get('review_route', demo.world.data.get('demo_route'))
    assert route, 'Demo scene needs an authored review route.'
    report = {'source': 'GrassDemo with production Player and GrassDemoWorld',
              'ordinary_movement_only': True, 'no_save_or_settings_files': True,
              'existing_world_sha256': guards, 'source_sha256': before,
              'checkpoints': [], 'walking_seen': False, 'running_seen': False,
              'standing_occupied_seen': False, 'max_strength': 0., 'max_occupied': 0,
              'upper_body_pixel_checks': 0, 'upper_body_occluded_pixels': 0,
              'leg_overlap_frames': 0}
    artifact_names = []
    run_motion_shot = False
    frame_count = 0
    encoder = None
    if movie_enabled:
        encoder = subprocess.Popen([
            'ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pixel_format', 'rgb24',
            '-video_size', f'{SIZE[0]}x{SIZE[1]}', '-framerate', str(FPS), '-i', '-', '-an',
            '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p',
            str(output/'grass_walk.mp4')], stdin=subprocess.PIPE)

    def sample(seconds, direction=(0, 0), running=False):
        nonlocal frame_count
        demo.step(seconds, direction, running=running)
        demo.draw()
        snapshot = demo.world.grass.snapshot()
        clumps = snapshot['clumps']
        occupied = sum(bool(item['occupants']) for item in clumps)
        report['max_occupied'] = max(report['max_occupied'], occupied)
        report['max_strength'] = max(report['max_strength'],
                                     max((item['strength'] for item in clumps), default=0))
        report['walking_seen'] |= bool(demo.player.moving and not demo.player.running)
        report['running_seen'] |= bool(demo.player.moving and demo.player.running)
        report['standing_occupied_seen'] |= bool(not demo.player.moving and occupied)
        if occupied:
            # Compare the actual actor's opaque pixels with grass drawing off.
            # This checks every occupied movie frame, including gait changes.
            bare = pygame.Surface(demo.canvas.get_size())
            demo.world.grass.enabled = False
            try:
                demo.world.draw(bare, demo.camera, demo.player, demo.elapsed_ms, include_ui=False)
            finally:demo.world.grass.enabled = True
            sprite = demo.player.sprite()
            mask = pygame.mask.from_surface(sprite)
            anchor = demo.world.data['player_draw_anchor']
            x0 = round(demo.player.position.x)-anchor[0]-demo.camera[0]
            y0 = round(demo.player.position.y)-anchor[1]-demo.camera[1]
            changed_legs = False
            for y in range(sprite.get_height()):
                for x in range(sprite.get_width()):
                    if not mask.get_at((x, y)):continue
                    point = x+x0, y+y0
                    different = bare.get_at(point) != demo.canvas.get_at(point)
                    if y < 25:
                        report['upper_body_pixel_checks'] += 1
                        report['upper_body_occluded_pixels'] += different
                    elif different:changed_legs = True
            report['leg_overlap_frames'] += changed_legs
            assert report['upper_body_occluded_pixels'] == 0, 'Grass covered Caelan above his legs.'
        if encoder is not None:
            encoder.stdin.write(pygame.image.tobytes(demo.window, 'RGB'))
        frame_count += 1

    def hold(seconds):
        for _ in range(math.ceil(seconds*FPS)):sample(1/FPS)

    def walk(target, running=False):
        nonlocal run_motion_shot
        speed = 108 if running else 72
        target = pygame.Vector2(target)
        for _ in range(2000):
            delta = target-demo.player.position
            if delta.length() < .02:return
            previous = demo.player.position.copy()
            sample(min(1/FPS, delta.length()/speed), delta, running)
            if (running and not run_motion_shot
                    and any(item['occupants'] and item['strength'] >= 1.9
                            for item in demo.world.grass.snapshot()['clumps'])):
                shot('running_through_grass_motion')
                run_motion_shot = True
            assert demo.world.can_stand(demo.player.position)
            assert demo.player.position != previous, ('Blocked demo route', previous, target)
        raise AssertionError(('Review route exceeded budget', target))

    def shot(name):
        filename = name+'.png'
        demo.draw()
        pygame.image.save(demo.window, str(output/filename))
        artifact_names.append(filename)
        snapshot = demo.world.grass.snapshot()
        active = [item for item in snapshot['clumps'] if item['occupants'] or item['strength'] > 0]
        report['checkpoints'].append({'name': name, 'file': filename,
                                     'position': list(demo.player.position),
                                     'facing': demo.player.facing,
                                     'running': demo.player.running,
                                     'elapsed_ms': demo.elapsed_ms, 'active_clumps': active})

    try:
        hold(.1)
        shot('arrival')
        for index, record in enumerate(route):
            target = record.get('position', record.get('point'))
            walk(target, record.get('mode', 'walk') == 'run')
            name = record.get('name', record.get('id', f'route_{index+1}'))
            if record.get('shot'):shot(name)
            seconds = float(record.get('hold_seconds', record.get('hold', 0)))
            if seconds:
                hold(seconds)
                if record.get('shot'):shot(name+'_held')
        hold(1)
        snapshot = demo.world.grass.snapshot()
        report['fully_recovered_after_exit'] = all(not item['occupants'] and item['strength'] < 1e-7
                                                  for item in snapshot['clumps'])
        assert report['fully_recovered_after_exit'], 'Review route should end on clear ground.'
        if frame_count/FPS < 32:hold(32-frame_count/FPS)
        shot('recovered')
        # Bounded production drawing produces a complete scene overview.
        overview = pygame.Surface(demo.world.size)
        for y in range(0, demo.world.size[1], 320):
            for x in range(0, demo.world.size[0], 480):
                tile = pygame.Surface((480, 320))
                demo.world.draw(tile, (x, y), demo.player, demo.elapsed_ms, include_ui=False)
                overview.blit(tile, (x, y))
        pygame.image.save(overview, str(output/'overview.png'))
        artifact_names.append('overview.png')
        if encoder is not None:
            encoder.stdin.close()
            assert encoder.wait() == 0, 'Video encoding failed.'
            encoder = None
            artifact_names.append('grass_walk.mp4')
        report['movie'] = {'file': 'grass_walk.mp4' if movie_enabled else None,
                           'fps': FPS, 'frames': frame_count, 'seconds': frame_count/FPS,
                           'size': list(SIZE)}
        assert 25 <= report['movie']['seconds'] <= 55, report['movie']
        photos = {item['name']: item for item in report['checkpoints']}
        selected = [photos[name] for name in ('current_grass_held', 'richer_lawn_held',
                                              'standing_in_grass_held',
                                              'running_through_grass_motion')]
        board = Image.new('RGB', (960, 688), '#1f3326')
        painter = ImageDraw.Draw(board)
        for index, item in enumerate(selected):
            x, y = (index % 2)*480, (index//2)*344
            with Image.open(output/item['file']) as photo:
                board.paste(photo.convert('RGB').resize((480, 320), Image.Resampling.NEAREST), (x, y+24))
            painter.text((x+8, y+7), item['name'].replace('_', ' '), fill='#e1e8c5')
        board.save(output/'contact_sheet.png')
        artifact_names.append('contact_sheet.png')
        report['height_comparison'] = height_comparison(output)
        artifact_names.append('height_comparison.png')
        assert source_hashes() == before, 'Source files changed during capture.'
        assert unchanged_worlds() == guards
        report['artifact_sha256'] = {name: digest(output/name) for name in artifact_names}
        (output/'verification.json').write_text(json.dumps(report, indent=2)+'\n')
        (output/'README.md').write_text('''# Playable grass demonstration

![Grass demonstration](contact_sheet.png)

[Full field](overview.png) · [Walking, running and standing](grass_walk.mp4)

![Grass height compared with Caelan](height_comparison.png)

The height study places unoccupied grass and Caelan on one visible ground
baseline at the same enlargement. It measures the opaque pixels, not the
transparent sprite canvases. The gameplay photographs separately show the
short foreground blades covering legs while the torso stays readable. Every
occupied movie frame is also compared with grass drawing disabled: opaque
head and torso pixels must remain identical, while leg overlap is observed.

This isolated prototype uses the actual game Player, camera and World rendering.
The review walks and runs through authored grass patches, holds still while the
grass remains displaced, then leaves it to recover. Every review position is
reached through ordinary movement; no character poses or bend states are staged.

The deeper emerald palette and lawn, meadow and woodland materials remain in
the demonstration. Eldenmere and the Sanctuary have not received the new pack.
The launcher never opens game journeys or settings files.

Run `python tools/preview_grass.py` to explore. Use WASD or arrows to move,
Shift to run, R to reset, M for reduced motion and Escape to exit.

Regenerate with `python tools/capture_grass_demo.py`; verify retained source,
artifact and original-world hashes with `python tools/capture_grass_demo.py --check`.
The [verification record](verification.json) contains actual positions, occupied
grass states, recovery, timings and the immutable source fingerprints.
''')
    finally:
        if encoder is not None:
            encoder.stdin.close()
            encoder.wait()
        demo.close()
    print(json.dumps({'movie': report['movie'], 'shots': len(report['checkpoints']),
                      'max_occupied': report['max_occupied'], 'max_strength': report['max_strength']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=OUT)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--no-movie', action='store_true')
    args = parser.parse_args()
    if args.check:check(args.out)
    else:capture(args.out, not args.no_movie)
