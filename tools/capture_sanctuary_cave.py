"""Review the Sanctuary cave through ordinary movement and production input.

The only fixture is a supported completed-MQ01/MQ02 journey. MQ03, regional
travel, cave transfers, discoveries and Continue use the game controllers.
Every capture uses disposable saves and settings, never a player's journey.
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
import tempfile

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pygame
from PIL import Image, ImageDraw, ImageStat

from main import camera_for
from sanctuary_cave import RESERVE_ENTRY_APPROACH
from tools.capture_mq03_emergency import Driver, cast_visibility
from tools.capture_overworld_sanctuary import frame

OUT = ROOT/'docs/reviews/sanctuary_cave'
SCENES = ('sanctuary_cave_entrance', 'sanctuary_cave_hollow', 'sanctuary_cave_depths')
REVIEW_STATIONS = {
    SCENES[0]:{'cave_entrance':(240,690), 'vein_gallery':(390,440), 'reflecting_grotto':(840,730)},
    SCENES[1]:{'splitstone_hollow':(310,760), 'keeper_recess':(875,720), 'deep_gallery':(720,325)},
    SCENES[2]:{'quiet_shelf':(400,440), 'echo_chamber':(795,300)},
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hashes():
    names = {
        'main.py', 'sanctuary_cave.py', 'sanctuary_cave_world.py',
        'sanctuary_cave_map.py', 'map_ui.py', 'overworld_travel.py',
        'regent_quest.py', 'regent_emergency.py', 'party_travel.py',
        'inventory.py', 'save_game.py', 'game_music.py', 'social.py',
        'tools/build_sanctuary_cave.py', 'tools/capture_sanctuary_cave.py',
        'tools/capture_mq03_emergency.py', 'tools/capture_sanctuary_reserve.py',
        'tools/capture_overworld_sanctuary.py', 'assets/items/catalog.json',
        'assets/maps/elden_vale_sanctuary/map.json',
    }
    for folder in ('assets/maps/sanctuary_cave', 'assets/terrain/sanctuary_cave',
                   'assets/source/terrain/sanctuary_cave'):
        names.update(path.relative_to(ROOT).as_posix()
                     for path in (ROOT/folder).rglob('*') if path.is_file())
    pending = [ROOT/name for name in names if (ROOT/name).is_file()]
    seen = set()
    while pending:
        path = pending.pop()
        if path in seen:continue
        seen.add(path)
        if path.suffix != '.json':continue
        def collect(value):
            if isinstance(value, dict):
                for item in value.values():collect(item)
            elif isinstance(value, list):
                for item in value:collect(item)
            elif isinstance(value, str) and value.startswith('assets/'):
                other = ROOT/value
                if other.is_file() and other not in seen:pending.append(other)
        collect(json.loads(path.read_text()))
    return {path.relative_to(ROOT).as_posix():digest(path) for path in sorted(seen)}


class Movie:
    """Sample traversed simulation at three-times speed; held views remain clear."""
    def __init__(self, output):
        executable = shutil.which('ffmpeg')
        if executable is None:raise RuntimeError('ffmpeg is required to record the cave review')
        self.frames = 0
        self.clock = 0.
        self.process = subprocess.Popen([
            executable, '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
            '-s', '960x640', '-r', '20', '-i', '-', '-an', '-c:v', 'libx264',
            '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p',
            '-movflags', '+faststart', str(output)], stdin=subprocess.PIPE)

    def sample(self, game, seconds):
        self.clock += seconds
        if self.clock < .15:return
        self.clock %= .15
        self.add(frame(game))

    def add(self, image, count=1):
        for _ in range(count):
            self.process.stdin.write(image.tobytes())
            self.frames += 1

    def finish(self):
        self.process.stdin.close()
        assert self.process.wait() == 0, 'Cave video encoding failed'


def settle(driver):
    driver.until(lambda:not driver.game.opening_fade and not driver.game.transfer_cooldown)


def finish_dialogue(driver):
    while driver.game.social.active:
        assert not driver.game.social.choosing, 'Cave review dialogue must be linear'
        driver.game.social.advance()
    driver.tick()


def press(driver, key):
    event = pygame.event.Event(pygame.KEYDOWN, key=key, repeat=False)
    assert driver.game.handle_events([event])
    driver.tick()


def photograph(driver, output, name, movie=None):
    game = driver.game
    game.location_seconds = 0
    game.quest_ui.current_notice = None
    game.quest_ui.notices.clear()
    image = frame(game)
    image.save(output/name)
    if movie:movie.add(image, 12)
    return {'file':name, 'scene':game.world.data['id'],
            'position':list(game.player.position), 'size':list(image.size),
            'source':'Production Game.draw'}


def walk(driver, point, *, running=False):
    settle(driver)
    driver.walk(point, running=running)


def use_link(driver, destination, output=None, movie=None):
    origin = driver.game.world.data['id']
    link = next(record for record in driver.game.world.data['cave']['links']
                if record['destination'] == destination)
    walk(driver, link['position'])
    view = None
    if output is not None:
        name = 'passage_'+origin.removeprefix('sanctuary_cave_')+'_to_'+destination.removeprefix('sanctuary_cave_')+'.png'
        view = photograph(driver, output, name, movie)
    press(driver, pygame.K_e)
    assert driver.game.world.data['id'] == destination, ('Transfer failed', link)
    settle(driver)
    return view


def collect(driver, record):
    walk(driver, record.get('approach', record['position']))
    before = driver.game.inventory.to_dict()
    press(driver, pygame.K_e)
    finish_dialogue(driver)
    assert before != driver.game.inventory.to_dict(), ('Treasure was not awarded', record['id'])
    after = driver.game.inventory.to_dict()
    press(driver, pygame.K_e)
    finish_dialogue(driver)
    assert after == driver.game.inventory.to_dict(), ('Treasure awarded twice', record['id'])
    return {'id':record['id'], 'position':list(driver.game.player.position),
            'scene':driver.game.world.data['id'], 'repeat_did_not_award':True}


def record_pulse(driver, output, movie):
    """Measure a complete real-time cycle at one unchanged standing position."""
    game = driver.game
    game.location_seconds = 0
    game.quest_ui.current_notice = None
    game.quest_ui.notices.clear()
    low = high = None
    animation = []
    for index in range(65):
        driver.tick(.1)
        image = frame(game)
        # The native world excludes static UI; brightness changes reflect light.
        canvas = Image.frombytes('RGB', game.canvas.get_size(), pygame.image.tobytes(game.canvas, 'RGB'))
        mean = sum(ImageStat.Stat(canvas).mean)/3
        sample = (mean, image, game.elapsed_ms)
        if low is None or mean < low[0]:low = sample
        if high is None or mean > high[0]:high = sample
        if index%2 == 0:
            animation.append(image.resize((480,320),Image.Resampling.NEAREST)
                             .quantize(colors=192,dither=Image.Dither.NONE))
        if movie:movie.add(image, 2)
    low[1].save(output/'pulse_trough.png')
    high[1].save(output/'pulse_peak.png')
    animation[0].save(output/'crystal_pulse.gif',save_all=True,
                      append_images=animation[1:],duration=200,loop=0,optimize=True)
    assert high[0] > low[0]+.5, ('Crystal light does not change the scene', low[0], high[0])
    return {'position':list(game.player.position), 'scene':game.world.data['id'],
            'sampled_seconds':6.5, 'trough_mean_rgb':low[0], 'peak_mean_rgb':high[0],
            'trough_elapsed_ms':low[2], 'peak_elapsed_ms':high[2]}


def contact_sheet(output, names):
    columns = 2
    cell = (480, 342)
    sheet = Image.new('RGB', (columns*cell[0], math.ceil(len(names)/columns)*cell[1]), '#19262b')
    draw = ImageDraw.Draw(sheet)
    for index, name in enumerate(names):
        image = Image.open(output/name).convert('RGB')
        image.thumbnail((480, 320), Image.Resampling.NEAREST)
        x = index%columns*cell[0]
        y = index//columns*cell[1]
        sheet.paste(image, (x, y+22))
        draw.text((x+8, y+5), name.replace('.png','').replace('_',' ').title(), fill='#e9e0bf')
    sheet.save(output/'contact_sheet.png')


def capture(output=OUT, movie_enabled=True):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    before = source_hashes()
    report = {'fixture':'Completed MQ01/MQ02 only; MQ03 and arrival played normally',
              'ordinary_movement':True, 'disposable_save_and_settings':True,
              'views':{}, 'treasures':[], 'continues':[], 'source_sha256':before}
    movie = Movie(output/'sanctuary_cave.mp4') if movie_enabled else None
    try:
        with tempfile.TemporaryDirectory(prefix='sanctuary-cave-review-') as temporary:
            driver = Driver(temporary)
            driver.meal();driver.attack_report();driver.departure();driver.rejoin_mira();driver.arrive()
            assert driver.quest.stage == 'sanctuary_arrival_pending'
            initial_quests = driver.game.quests.to_dict()
            initial_party = driver.game.party.to_dict()
            if movie:driver.observer = lambda seconds:movie.sample(driver.game, seconds)
            # Entry is an authored interaction at the existing cave apron.
            entry = driver.game.world.data.get('public_approaches', {}).get('cave', RESERVE_ENTRY_APPROACH)
            walk(driver, entry)
            report['views']['reserve_entrance'] = photograph(driver,output,'reserve_entrance.png',movie)
            press(driver, pygame.K_e)
            assert driver.game.world.data['id'] == SCENES[0]
            settle(driver)
            for index, scene_id in enumerate(SCENES):
                assert driver.game.world.data['id'] == scene_id
                data = driver.game.world.data['cave']
                report['views'][scene_id+'_entry'] = photograph(driver,output,scene_id+'_entry.png',movie)
                for route in data.get('routes', {}).values():
                    for point in route:walk(driver,point)
                for treasure in data.get('treasures', []):
                    report['treasures'].append(collect(driver, treasure))
                review = data.get('review_points', REVIEW_STATIONS[scene_id])
                for key, point in review.items():
                    walk(driver,driver.clear(driver.game.world,point))
                    report['views'][key] = photograph(driver,output,key+'.png',movie)
                if not review:
                    report['views'][scene_id] = photograph(driver,output,scene_id+'.png',movie)
                if index == 1:
                    report['pulse'] = record_pulse(driver, output, movie)
                    game = driver.game
                    game.audio.reduced_motion = True
                    game.world.reduced_motion = True
                    for _ in range(80):driver.tick(.05)
                    first = photograph(driver,output,'reduced_motion.png',movie)
                    frozen = pygame.image.tobytes(game.canvas, 'RGB')
                    driver.tick(2)
                    frame(game)
                    assert pygame.image.tobytes(game.canvas, 'RGB') == frozen, 'Reduced motion changed cave scenery'
                    game.audio.reduced_motion = False
                    game.world.reduced_motion = False
                    report['reduced_motion_static'] = True
                press(driver, pygame.K_m)
                report['views'][scene_id+'_map'] = photograph(driver,output,scene_id+'_map.png',movie)
                press(driver, pygame.K_m)
                current = driver.game.inventory.to_dict()
                opened = driver.game.sanctuary_cave.to_dict()
                feet = tuple(driver.game.player.position)
                driver.continue_saved()
                assert driver.game.world.data['id'] == scene_id
                assert tuple(driver.game.player.position) == feet
                assert driver.game.inventory.to_dict() == current
                assert driver.game.sanctuary_cave.to_dict() == opened
                assert driver.game.music.desired_track == 'battle'
                report['continues'].append(scene_id)
                report['views'][scene_id+'_continued'] = photograph(driver,output,scene_id+'_continued.png')
                if index < 2:
                    view = use_link(driver, SCENES[index+1], output, movie)
                    report['views'][Path(view['file']).stem] = view
            report['cast_at_depths'] = cast_visibility(driver.game)
            assert len(report['treasures']) == 6, report['treasures']
            for destination in (SCENES[1], SCENES[0], 'elden_vale_sanctuary'):
                view = use_link(driver, destination, output, movie)
                report['views'][Path(view['file']).stem] = view
            assert driver.quest.stage == 'sanctuary_arrival_pending'
            assert driver.game.quests.to_dict() == initial_quests
            assert driver.game.party.to_dict() == initial_party
            assert driver.game.music.desired_track == 'battle'
            report['round_trip_complete'] = True
            report['quest_and_party_unchanged'] = True
            report['views']['returned_to_reserve'] = photograph(driver,output,'returned_to_reserve.png',movie)
            report['transitions'] = driver.transitions
            report['opened'] = driver.game.sanctuary_cave.to_dict()
        if movie:
            movie.finish()
            report['movie'] = {'file':'sanctuary_cave.mp4', 'frames':movie.frames,
                               'fps':20, 'seconds':movie.frames/20, 'movement_speedup':3}
            movie = None
        names = ['vein_gallery.png','reflecting_grotto.png','splitstone_hollow.png',
                 'keeper_recess.png','deep_gallery.png','echo_chamber.png',
                 'pulse_trough.png','pulse_peak.png']
        contact_sheet(output,names)
        assert before == source_hashes(), 'Production sources changed during capture; rerun on final sources'
        report['artifact_sha256'] = {path.name:digest(path) for path in output.iterdir()
                                    if path.suffix in ('.png','.mp4','.gif')}
        (output/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps({'views':len(report['views']), 'treasures':len(report['treasures']),
                          'continues':report['continues'], 'movie':report.get('movie')},indent=2))
    finally:
        if movie:
            movie.process.stdin.close()
            movie.process.wait()
        pygame.quit()


def check(output):
    report = json.loads((output/'verification.json').read_text())
    assert report['source_sha256'] == source_hashes(), 'Cave sources changed; recapture'
    assert report['round_trip_complete'] and report['quest_and_party_unchanged']
    assert report['continues'] == list(SCENES)
    assert len(report['treasures']) == 6 and all(row['repeat_did_not_award'] for row in report['treasures'])
    assert report['reduced_motion_static']
    for name,value in report['artifact_sha256'].items():assert digest(output/name) == value, name
    print('Cave routes, six treasure receipts, pulse, reduced motion, Continue and review fingerprints verified.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUT)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--no-movie', action='store_true')
    args = parser.parse_args()
    check(args.output) if args.check else capture(args.output, not args.no_movie)
