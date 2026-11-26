"""Capture real bridge movement in a disposable, quest-seeded production Game.

The fixture completes retained MQ01/MQ02 and stages explicit bridge phases.
It is not a playthrough of the future opening or its unimplemented attack.
Only selected runs are filmed; the complete lane/direction/gait matrix is
checked through ordinary Game.update movement and recorded in capture.json.
"""
from __future__ import annotations

import argparse
import csv
from hashlib import sha256
import json
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

from bridge_condition import BridgeCondition
from main import Game, RUN_MULTIPLIER, WALK_SPEED
from tools.scenario_fixtures import seed_mill_completed


FPS = 30
OUT = ROOT/'docs/reviews/bridge_playable_crossing'
BRIDGE_X = -2664
LANES = (666, 696, 726)


class Capture:
    def __init__(self, directory, output, *, video=True):
        self.output = Path(output)
        self.output.mkdir(parents=True, exist_ok=True)
        self.game = Game(window_size=(960, 640), fullscreen=False, start_on_title=False,
                         save_path=Path(directory)/'journey.json',
                         settings_path=Path(directory)/'settings.json')
        self.game.audio.set_music(0)
        self.game.audio.set_effects(0)
        seed_mill_completed(self.game)
        self.world = self.game.overworld_world
        self.game.world = self.world
        assert tuple(self.world.probe_size) == (24, 12)
        pygame.event.clear()
        self.cases, self.stills, self.clips = [], [], []
        self.video_frames = 0
        self.encoder = None
        if video:
            if shutil.which('ffmpeg') is None:
                raise RuntimeError('ffmpeg is required unless --no-video is selected')
            self.encoder = subprocess.Popen([
                'ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
                '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '960x640',
                '-r', str(FPS), '-i', '-', '-an', '-c:v', 'libx264',
                '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p',
                '-movflags', '+faststart', str(self.output/'crossing.mp4')],
                stdin=subprocess.PIPE)

    def stage(self, phase, position, *, reduced=False):
        g = self.game
        g.overworld_travel.restore_bridge_condition(
            {'bridge_condition': BridgeCondition(phase).to_dict()})
        g.world = self.world
        g.player.position.update(position)
        g.player.moving = g.player.running = False
        g.player.walk_ms = 0
        g.opening_fade = g.transfer_cooldown = 0
        g.social.cancel_script()
        g.social.blocked.clear()
        g.quest_ui.reset()
        g.audio.set_reduced_motion(reduced)
        g.camera.reset()
        assert g.world.can_stand(g.player.position), (phase, position)

    def frame(self, direction=(0, 0), running=False, *, film=False):
        g = self.game
        g.update(1/FPS, direction, running)
        assert g.world is self.world, 'Fixture unexpectedly transferred scenes'
        clear = g.world.can_stand(g.player.position)
        assert clear, ('Player left safe ground', tuple(g.player.position))
        if film:
            g.draw()
            if self.encoder is not None:
                self.encoder.stdin.write(pygame.image.tobytes(g.window, 'RGB'))
            self.video_frames += 1
        return {'position': [round(value, 6) for value in g.player.position],
                'clear_full_probe': clear}

    def still(self, name):
        g = self.game
        g.draw()
        native = pygame.Surface(g.canvas.get_size())
        native.blit(g.canvas, (0, 0))
        g.canvas.present_detail(native)
        paths = []
        for suffix, surface in (('native', native), ('window', g.window)):
            path = self.output/(name+'_'+suffix+'.png')
            pygame.image.save(surface, path)
            paths.append({'file': path.name, 'pixels': list(surface.get_size()),
                          'sha256': sha256(path.read_bytes()).hexdigest()})
        self.stills.append({'name': name, 'position': list(g.player.position),
                            'condition': g.overworld_travel.bridge_condition.to_dict(),
                            'reduced_motion': g.audio.reduced_motion,
                            'camera': list(g.camera.position()), 'files': paths})

    def crossing(self, phase, lane, direction, running, *, film=False, reduced=False,
                 capture_still=False):
        start_x, target_x = (-2904, -2424) if direction > 0 else (-2424, -2904)
        name = f'{phase}_{"run" if running else "walk"}_{"right" if direction > 0 else "left"}_{lane}'
        if reduced:name += '_reduced'
        self.stage(phase, (start_x, lane), reduced=reduced)
        begin_frame = self.video_frames
        samples = []
        centered = False
        joins = set()
        for frame in range(FPS*9):
            before = self.game.player.position.x
            sample = self.frame((direction, 0), running, film=film)
            sample['frame'] = frame
            samples.append(sample)
            after = self.game.player.position.x
            assert (after-before)*direction > 0, ('Blocked crossing', name, sample)
            if (film or capture_still) and not centered and (before-BRIDGE_X)*(after-BRIDGE_X) <= 0:
                self.still(name+'_center')
                centered = True
            if film and phase == 'intact' and lane == 696 and not running:
                for join in (-2868, -2460):
                    if join not in joins and (before-join)*(after-join) <= 0:
                        self.still(name+f'_join_{abs(join)}')
                        joins.add(join)
            if (after-target_x)*direction >= 0:
                break
        else:
            raise AssertionError(('Crossing did not reach the opposite approach', name))
        self.cases.append({'id': name, 'kind': 'crossing', 'phase': phase, 'lane_y': lane,
                           'direction': direction, 'running': running, 'reduced_motion': reduced,
                           'start': [start_x, lane], 'target_x': target_x,
                           'end': list(self.game.player.position), 'samples': samples,
                           'completed': True})
        if film:self.clips.append({'case': name, 'first_frame': begin_frame,
                                   'end_frame': self.video_frames})

    def destroyed(self, lane, direction, *, film=False):
        start_x = -2828 if direction > 0 else -2500
        name = f'destroyed_{"west" if direction > 0 else "east"}_approach_{lane}'
        self.stage('destroyed', (start_x, lane))
        begin_frame = self.video_frames
        samples = [self.frame((direction, 0), True, film=film) for _ in range(FPS*2)]
        end = list(self.game.player.position)
        assert abs(end[0]-samples[-10]['position'][0]) < .01, ('Approach did not stop', name)
        assert end[0] < -2700 if direction > 0 else end[0] > -2628
        if film:self.still(name+'_blocked')
        self.cases.append({'id': name, 'kind': 'destroyed_approach', 'phase': 'destroyed',
                           'lane_y': lane, 'direction': direction, 'running': True,
                           'start': [start_x, lane], 'end': end, 'samples': samples,
                           'gap_crossed': False, 'blocked': True})
        if film:self.clips.append({'case': name, 'first_frame': begin_frame,
                                   'end_frame': self.video_frames})

    def far_bank(self):
        terminal = self.world.region['far_bank']['terminal_tile']
        self.stage('intact', tuple(value*24 for value in terminal))
        begin_frame = self.video_frames
        for _ in range(FPS*2):self.frame(film=True)
        self.still('far_bank_road_terminus')
        self.clips.append({'case': 'far_bank_road_terminus', 'first_frame': begin_frame,
                           'end_frame': self.video_frames})
        self.cases.append({'id': 'far_bank_road_terminus', 'kind': 'stationary_fixture',
                           'position': list(self.game.player.position),
                           'clear_full_probe': self.world.can_stand(self.game.player.position),
                           'destination_ready': self.world.region['far_bank']['future_exit']['destination_ready'],
                           'world_unchanged': self.game.world is self.world})
        g = self.game
        g.handle_events([pygame.event.Event(pygame.KEYDOWN, key=pygame.K_m, repeat=False),
                         pygame.event.Event(pygame.KEYUP, key=pygame.K_m)])
        assert g.map_open
        atlas = g.map_ui._regional()
        atlas.zoom = 3.2
        atlas.center.update(-134, 52)
        atlas._clamp()
        g.draw()
        path = self.output/'far_bank_atlas.png'
        pygame.image.save(g.window, path)
        self.stills.append({'name': 'far_bank_atlas', 'position': list(g.player.position),
                            'map_center_tiles': list(atlas.center), 'map_zoom': atlas.zoom,
                            'files': [{'file': path.name, 'pixels': list(g.window.get_size()),
                                       'sha256': sha256(path.read_bytes()).hexdigest()}]})
        begin_frame = self.video_frames
        for _ in range(FPS):self.frame(film=True)
        self.clips.append({'case': 'far_bank_atlas', 'first_frame': begin_frame,
                           'end_frame': self.video_frames})
        g.handle_events([pygame.event.Event(pygame.KEYDOWN, key=pygame.K_m, repeat=False),
                         pygame.event.Event(pygame.KEYUP, key=pygame.K_m)])
        assert not g.map_open

    def run(self):
        filmed = {('intact', 696, 1, False), ('restored', 726, -1, True)}
        stills = filmed | {('intact', 666, -1, True), ('restored', 726, -1, False),
                           ('restored', 696, 1, True)}
        for phase in ('intact', 'restored'):
            for lane in LANES:
                for direction in (1, -1):
                    for running in (False, True):
                        self.crossing(phase, lane, direction, running,
                                      film=(phase, lane, direction, running) in filmed,
                                      capture_still=(phase, lane, direction, running) in stills)
        for lane in LANES:
            for direction in (1, -1):self.destroyed(lane, direction, film=lane == 696)
        self.far_bank()
        # Reduced motion uses the same ordinary route through both joins.
        self.crossing('intact', 696, 1, True, film=True, reduced=True)
        metadata = {'version': 1,
                    'method': 'Quest-seeded disposable production Game; retained MQ01/MQ02 are fixture prerequisites. Explicit bridge phases and starting stations are seeded between cases. Each recorded movement step uses Game.update at 30 Hz; screenshots/video use Game.draw. No attack or new-opening playthrough is claimed.',
                    'command': 'python tools/capture_bridge_crossing.py',
                    'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                    'source_state': 'Working tree capture before the implementation commit.',
                    'runtime_sha256': {name: sha256((ROOT/name).read_bytes()).hexdigest()
                                       for name in ('main.py', 'overworld_world.py',
                                                    'overworld_travel.py', 'bridge_condition.py',
                                                    'overworld_map.py', 'overworld_minimap.py')},
                    'region_sha256': sha256((ROOT/'assets/maps/overworld/elden_vale/region.json').read_bytes()).hexdigest(),
                    'art_manifest_sha256': sha256((ROOT/'assets/terrain/overworld/elden_vale/bridge/art.json').read_bytes()).hexdigest(),
                    'fps': FPS, 'probe_size': list(self.world.probe_size),
                    'walk_speed': WALK_SPEED, 'run_multiplier': RUN_MULTIPLIER,
                    'video': 'crossing.mp4' if self.encoder is not None else None,
                    'video_silent': True, 'video_frames': self.video_frames,
                    'video_seconds': self.video_frames/FPS,
                    'all_movement_samples_clear': True, 'cases': self.cases,
                    'clips': self.clips, 'stills': self.stills,
                    'save_isolation': 'All Game save/settings/library paths are under a TemporaryDirectory; no parent journey is opened.'}
        return metadata

    def close(self):
        if self.encoder is not None:
            self.encoder.stdin.close()
            code = self.encoder.wait()
            if code:raise RuntimeError(f'ffmpeg exited with status {code}')
        g = self.game
        g.music.stop();g.opening_audio.reset();g.regional_audio.reset()
        pygame.quit()


def write_samples(metadata, output):
    """Keep every movement observation in a compact, independently hashed CSV."""
    path = Path(output)/'movement_samples.csv'
    columns = ('case_id', 'frame', 'x', 'y', 'clear_full_probe')
    count = 0
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.writer(stream, lineterminator='\n')
        writer.writerow(columns)
        for case in metadata['cases']:
            samples = case.pop('samples', [])
            case['sample_count'] = len(samples)
            case['all_samples_clear'] = all(sample['clear_full_probe'] for sample in samples)
            for frame, sample in enumerate(samples):
                writer.writerow((case['id'], sample.get('frame', frame),
                                 *sample['position'], str(sample['clear_full_probe']).lower()))
            count += len(samples)
    metadata['movement_samples'] = {'file': path.name, 'columns': list(columns),
                                    'rows': count, 'sha256': sha256(path.read_bytes()).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUT)
    parser.add_argument('--no-video', action='store_true')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='bridge-crossing-capture-') as directory:
        capture = Capture(directory, args.output, video=not args.no_video)
        try:
            metadata = capture.run()
        finally:
            capture.close()
    if metadata['video'] is not None:
        metadata['video_sha256'] = sha256((args.output/metadata['video']).read_bytes()).hexdigest()
    write_samples(metadata, args.output)
    (args.output/'capture.json').write_text(json.dumps(metadata, indent=2)+'\n')
    print(json.dumps({'cases': len(metadata['cases']), 'stills': len(metadata['stills']),
                      'video_seconds': metadata['video_seconds'], 'output': str(args.output)}))


if __name__ == '__main__':
    main()
