"""Capture the real arrival, crossroads pan and handoff without staging shots.

Only earlier quest work is supplied by the existing mill-report fixture. The
unread report is acknowledged through its normal input helper; subsequent
clocks, phases, dialogue pages and actor stations belong to production Game.
SDL dummy has no hardware loopback. Music is reconstructed from the shipped
looping OGGs and actual MixerTrace commands/PCM; effects are muted, not faked.

Writes only this tool's named evidence files, never existing art or READMEs.
--check validates recorded input and artifact hashes without rewriting metadata.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import contextmanager
import copy
from dataclasses import asdict
from datetime import datetime, timezone
import gc
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
from unittest.mock import patch
import wave

sys.dont_write_bytecode = True
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'tests')]

import numpy as np
import pygame
from PIL import Image, ImageDraw

from main import Game
from quests import MILL_QUEST, REGENT_QUEST
from regent_arrival import RegentArrival
from test_regent_arrival import acknowledge_report, seed_mill_report
from tools.capture_battle_music_transition import MixerTrace, RATE

FPS = 30
SIZE = (480, 320)
# A picosecond avoids 24 * (1/30) becoming .7999999999999999 at a .8s
# boundary. This is a fixed ordinary update delta, NOT an assigned scene clock.
# Its total bias is reported; video/PCM always use exactly 30fps / 1600 samples.
STEP = 1/FPS + 1e-12
OUTPUT = ROOT/'docs/reviews/regent_crossroads'
SCRIPT = Path(__file__).resolve()
PAN_SHOT = 'road_pan'
SEQUENCE_SHOTS = {'locals', PAN_SHOT, 'bridge_damage', 'relief'}
STILLS = {
    'gate_approach': ((.6, 'gate_approach_0600ms.png'),),
    'gate_greeting': ((1., 'gate_greeting_1000ms.png'),),
    'gate_admission': ((1.2, 'gate_admission_1200ms.png'),
                       (2.5, 'gate_admission_2500ms.png'),
                       (4., 'gate_admission_4000ms.png')),
    PAN_SHOT: ((0., 'pan_0000ms.png'), (.2, 'pan_0200ms.png'),
               (.4, 'pan_0400ms.png'), (.6, 'pan_0600ms.png')),
    'bridge_damage': ((0., 'bridge_cut_0800ms.png'),
                      (1., 'bridge_damage_1000ms.png')),
    'relief': ((0., 'relief_hard_cut.png'), (1., 'relief_1000ms.png')),
}
EXTRA_STILLS = {'locals_first.png', 'locals_last_question.png',
                'pan_last_0767ms.png', 'saved_world.png',
                'descent_clerk_negative_clock.png'}
OWNED = ({name for targets in STILLS.values() for _, name in targets}
         | EXTRA_STILLS | {'full_arrival.mp4', 'crossroads_sequence.mp4',
                           'gate_clerk.png', 'contact_sheet.jpg', 'motion_sheet.jpg',
                           'capture_report.json', 'audio_events.json'})


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def digest(path):
    with Path(path).open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def json_value(value):
    if isinstance(value, pygame.Vector2):
        return list(value)
    if isinstance(value, dict):
        return {str(key): json_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [json_value(item) for item in value]
    if isinstance(value, set):
        return sorted(json_value(item) for item in value)
    if isinstance(value, np.generic):
        return value.item()
    return value


def json_digest(value):
    payload = json.dumps(json_value(value), sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(payload.encode()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(json_value(value), indent=2, allow_nan=False)+'\n')


def key(game, value):
    require(game.handle_events([
        pygame.event.Event(pygame.KEYDOWN, key=value, repeat=False),
        pygame.event.Event(pygame.KEYUP, key=value)]), 'Input unexpectedly quit')


def click_skip(game):
    game.draw()
    center = game.regent_arrival.skip_rect.center
    _, size, origin = game._ensure_ui_surface()
    point = tuple(round(origin[i]+center[i]*size[i]/SIZE[i]) for i in (0, 1))
    require(game.handle_events([
        pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=point),
        pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=point)]), 'Skip quit')


def world_state(game):
    """Independent frozen-world receipt, including cached regional simulation."""
    cached = game._overworld_world
    return json_value({
        'world': game.world.data['id'],
        'player': {'position': list(game.player.position), 'facing': game.player.facing,
                   'moving': game.player.moving, 'walk_ms': game.player.walk_ms},
        'elapsed_ms': game.elapsed_ms, 'camera': list(game.camera.position()),
        'residents': [(world.data['id'], actor.data['id'], list(actor.position),
                       getattr(actor, 'walk_ms', None), getattr(actor, 'clock', None))
                      for world in game.scenes.values() for actor in world.npcs],
        'doors': [(world.data['id'], door.data['id'], door.progress, door.target_open)
                  for world in game.scenes.values() for door in world.doors],
        'cached_residents': ([(actor.data['id'], list(actor.position),
                               getattr(actor, 'clock', None)) for actor in cached.npcs]
                             if cached is not None else None),
        'cached_wildlife': cached.wildlife.to_dict() if cached is not None else None,
        'inventory': game.inventory.to_dict(), 'attributes': game.attributes.to_dict(),
        'quests': game.quests.to_dict(), 'mill': game.mill_quest.to_dict(),
        'regent': game.regent_quest.to_dict(), 'flags': sorted(game.social.flags),
    })


def visual_state(scene):
    return json_value({
        'active': scene.active, 'state': scene.state, 'shot': scene.shot,
        'phase_time': scene.phase_time, 'elapsed': scene.elapsed,
        'dialogue': scene.dialogue_index, 'page': scene.page_index,
        'camera': list(scene.camera_position), 'pan': asdict(scene.road_pan_sample),
        'actors': [(a['id'], list(scene.actor_position(a)), scene.actor_pose(a),
                    scene._actor_scale(a)) for a in scene.phase['actors']],
        'reference_clock': scene._reference_clock,
        'reference_camera': scene._reference_camera,
    })


def native_frame(game):
    require(game.window.get_size() == SIZE, 'Full capture must be native, not rescaled')
    require(game.ui_surface.get_size() == SIZE, 'UI must be rasterized at native size')
    return Image.frombytes('RGB', SIZE, pygame.image.tobytes(game.window, 'RGB'))


def stop_game(game):
    if game.gallery_session is not None:
        game.gallery_session.close(resume_music=False)
    game.regent_arrival.audio.stop()
    game.regent_arrival.bird_audio.stop()
    game.opening_audio.reset()
    game.regional_audio.reset()
    game.music.stop()
    for sound in game.ui._sounds.values():
        sound.stop()


@contextmanager
def disposable_game(directory, *, title=False, music=False):
    directory.mkdir(parents=True, exist_ok=True)
    game = Game(window_size=SIZE, fullscreen=False, start_on_title=title,
                save_path=directory/'journey.json', settings_path=directory/'settings.json')
    game.audio.set_effects(0)
    if not music:
        game.audio.set_music(0)
    pygame.event.clear()
    try:
        yield game
    finally:
        stop_game(game)


class ReadOnlyGuard:
    """Protect pre-existing output art, project Python, source actors and saves."""

    def __init__(self, output):
        self.output = output
        self.python = {p.relative_to(ROOT).as_posix(): digest(p)
                       for p in ROOT.rglob('*.py')
                       if not any(part in {'.venv', 'venv', '__pycache__', '.git'}
                                  for part in p.relative_to(ROOT).parts)}
        self.existing = {p.name: digest(p) for p in output.iterdir()
                         if p.is_file() and p.name not in OWNED}
        self.saves = self.save_hashes()
        path = ROOT/'assets/source/cinematics/regent_arrival/actors/clerk_walk/protected_originals.json'
        self.originals = json.loads(path.read_text())
        require(all((ROOT/name).is_file() and digest(ROOT/name) == value
                    for name, value in self.originals.items()), 'Original actor guard already differs')

    @staticmethod
    def save_hashes():
        return {p.relative_to(ROOT).as_posix(): digest(p)
                for p in (ROOT/'saves').rglob('*') if p.is_file()}

    def verify(self):
        require(all((ROOT/name).is_file() and digest(ROOT/name) == value
                    for name, value in self.python.items()), 'Project Python changed during capture')
        require(all((self.output/name).is_file() and digest(self.output/name) == value
                    for name, value in self.existing.items()), 'Existing review file changed')
        require(all((ROOT/name).is_file() and digest(ROOT/name) == value
                    for name, value in self.originals.items()), 'Protected original actor changed')
        require(self.save_hashes() == self.saves, 'A normal save/settings file changed')
        return {'all_end_hashes_equal': True, 'project_python_files': len(self.python),
                'protected_original_actor_pngs': len(self.originals),
                'normal_save_files': len(self.saves),
                'preserved_existing_review_sha256': self.existing,
                'protected_originals_manifest_sha256': json_digest(self.originals),
                'normal_save_snapshot_sha256': json_digest(self.saves)}


class RuntimeInputs:
    """Observe real Python calls, runtime JSON reads and PNG loads, not builders.

    Review files, source-authoring folders, test files and report outputs never
    enter render_input_sha256. Capture/fixture code has separate fingerprints.
    Wrappers forward original arguments/results and do not alter game state.
    """

    def __init__(self, guard):
        self.guard = guard
        self.inputs = {}
        self.code = set()
        self.code_cache = {}
        self.image_loads = Counter()
        self.previous_profile = None

    def remember(self, path):
        path = Path(path).resolve()
        if not path.is_relative_to(ROOT/'assets') or path.suffix not in ('.json', '.png'):
            return
        if path.is_relative_to(ROOT/'assets/source'):
            return
        name = path.relative_to(ROOT).as_posix()
        if name not in self.inputs:
            self.inputs[name] = digest(path)

    def profile(self, frame, event, _argument):
        if event != 'call':
            return
        code = frame.f_code
        if code not in self.code_cache:
            name = code.co_filename
            path = Path(name) if not name.startswith('<') else None
            relative = (path.relative_to(ROOT) if path is not None and path.is_absolute()
                        and path.is_relative_to(ROOT) else None)
            self.code_cache[code] = (relative.as_posix() if relative is not None
                                     and relative.suffix == '.py'
                                     and relative.parts[0] not in ('tools', 'tests', 'docs') else None)
        name = self.code_cache[code]
        if name is not None:
            self.code.add(name)

    @contextmanager
    def observe(self):
        original_read = Path.read_text
        original_load = pygame.image.load

        def read(path, *args, **kwargs):
            self.remember(path)
            return original_read(path, *args, **kwargs)

        def load(filename, *args, **kwargs):
            path = Path(filename).resolve() if isinstance(filename, (str, Path)) else None
            if path is not None:
                self.remember(path)
                if path.is_relative_to(ROOT):
                    self.image_loads[path.relative_to(ROOT).as_posix()] += 1
            return original_load(filename, *args, **kwargs)

        self.previous_profile = sys.getprofile()
        try:
            with patch.object(Path, 'read_text', read), patch.object(pygame.image, 'load', load):
                sys.setprofile(self.profile)
                yield
        finally:
            sys.setprofile(self.previous_profile)

    def fingerprints(self):
        result = dict(self.inputs)
        result.update({name: self.guard.python[name] for name in self.code})
        require(all((ROOT/name).is_file() and digest(ROOT/name) == value
                    for name, value in result.items()), 'Actual runtime inputs changed; recapture')
        return dict(sorted(result.items()))


class ClerkObserver:
    """Read the exact Surface returned to the real ground actor drawer."""

    def __init__(self, scene):
        self.scene = scene
        self.frame_number = 0
        self.outer_shot = None
        self.outer_time = 0.
        self.aerial = None
        self.observed = []
        self.cards = {}
        self.coverage = {}
        self.negative_frames = set()

    def begin_frame(self, number):
        self.frame_number = number
        self.outer_shot = self.scene.shot
        self.outer_time = self.scene.phase_time
        self.aerial = self.scene.aerial_snapshot() if self.scene.phase['scene'] == 'aerial' else None
        self.observed = []

    @contextmanager
    def observe(self):
        original = self.scene._frame

        def frame(actor):
            image = original(actor)
            if actor['id'] == 'clerk':
                scene = self.scene
                pose = scene.actor_pose(actor)
                loop = scene.actor_art['clerk']['loops'].get(pose, ())
                index = next((i for i, (surface, _) in enumerate(loop) if surface is image), None)
                position = list(scene.actor_position(actor))
                screen = (self.aerial['projected_actors']['clerk']['screen_xy']
                          if self.aerial is not None and self.aerial['ground_handoff']
                          else list(scene.actor_position(actor)-scene.camera_position))
                record = {'render_shot': scene.shot, 'pose': pose, 'frame_index': index,
                          'position': position, 'screen_foot': screen,
                          'scale': scene._actor_scale(actor),
                          'reference_clock': scene._reference_clock,
                          'route': actor.get('route'),
                          'route_distance': (scene.actor_route_distance(actor)
                                             if actor.get('route') else None)}
                self.observed.append(record)
                if index is not None:
                    self.coverage.setdefault((self.outer_shot, pose), set()).add(index)
                    if scene._reference_clock is not None and scene._reference_clock < 0:
                        self.negative_frames.add(index)
            return image

        with patch.object(self.scene, '_frame', frame):
            yield

    def collect_card(self, image):
        if not self.observed:
            return
        record = self.observed[-1]
        pose, index = record['pose'], record['frame_index']
        if index is None or pose not in ('walk_left', 'walk_left_back', 'walk_back'):
            return
        if self.outer_shot not in ('gate_approach', 'gate_admission', 'town_approach'):
            return
        x, y = record['screen_foot']
        if not (32 <= x <= 448 and 98 <= y <= 308):
            return
        identity = (pose, index)
        if identity not in self.cards:
            crop = image.crop((round(x)-32, round(y)-98, round(x)+32, round(y)+6))
            self.cards[identity] = (crop.resize((128, 208), Image.Resampling.NEAREST),
                                    {'shot': self.outer_shot, 'phase_second': self.outer_time,
                                     'video_frame': self.frame_number, **record})

    def summary(self):
        return {'method': 'Read-only wrapper around the production _frame return Surface; identity-matched runtime loop index',
                'coverage': [{'shot': shot, 'pose': pose, 'indices': sorted(values)}
                             for (shot, pose), values in sorted(self.coverage.items())],
                'negative_descent_clock_frame_indices': sorted(self.negative_frames),
                'motion_card_sources': [record for _, record in self.cards.values()]}


def encoder(path):
    return subprocess.Popen([
        'ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pixel_format', 'rgb24',
        '-video_size', '480x320', '-framerate', str(FPS), '-i', '-', '-an',
        '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '22', '-pix_fmt', 'yuv420p',
        '-movflags', '+faststart', str(path)], stdin=subprocess.PIPE)


def close_encoder(process):
    if process is not None:
        if process.stdin is not None and not process.stdin.closed:
            process.stdin.close()
        require(process.wait() == 0, 'ffmpeg raw-video encoding failed')


def contact_sheet(path, frames, columns=3):
    require(bool(frames), f'No frames for {path.name}')
    sheet = Image.new('RGB', (columns*480, math.ceil(len(frames)/columns)*344), '#22382f')
    draw = ImageDraw.Draw(sheet)
    for index, (label, image) in enumerate(frames):
        x, y = index % columns*480, index//columns*344
        sheet.paste(image, (x, y))
        draw.text((x+7, y+323), label, fill='#f1e7cf')
    if path.suffix == '.jpg':
        sheet.save(path, quality=86, subsampling=2, optimize=True)
    else:
        sheet.save(path, optimize=True)


def clerk_sheet(path, stills, observer):
    """Unaltered in-game frames above; labeled nearest-neighbor crops below."""
    names = ('gate_approach_0600ms.png', 'gate_greeting_1000ms.png',
             'gate_admission_1200ms.png', 'gate_admission_2500ms.png',
             'gate_admission_4000ms.png', 'descent_clerk_negative_clock.png')
    width = 3*480
    sheet = Image.new('RGB', (width, 2*344+3*242), '#22382f')
    draw = ImageDraw.Draw(sheet)
    for index, name in enumerate(names):
        x, y = index % 3*480, index//3*344
        sheet.paste(stills[name], (x, y))
        draw.text((x+6, y+323), name, fill='#f1e7cf')
    for row, pose in enumerate(('walk_left', 'walk_left_back', 'walk_back')):
        for index in range(8):
            card = observer.cards.get((pose, index))
            x, y = index*180, 2*344+row*242
            if card is not None:
                image, source = card
                sheet.paste(image, (x+26, y))
                draw.text((x+5, y+209), f'{pose} / f{index}', fill='#f1e7cf')
                draw.text((x+5, y+224), f"{source['shot']} {source['phase_second']:.2f}s", fill='#f1e7cf')
            else:
                draw.text((x+5, y+30), f'{pose} / f{index}\nnot observed in crop', fill='#f1e7cf')
    sheet.save(path, optimize=True)


def compressed_mixer_events(events):
    """Keep every non-volume command and every applied-volume transition.

    Consecutive quantized-equal volume commands are run-length encoded. Their
    requested range is diagnostic; reconstruction used the actual applied gain.
    """
    result = []
    for event in events:
        if (result and event['event'] == 'volume' and result[-1]['event'] == 'volume'
                and event['applied'] == result[-1]['applied']):
            previous = result[-1]
            previous['last_time'] = event['time']
            previous['count'] += 1
            previous['last_requested'] = event['requested']
            previous['requested_min'] = min(previous['requested_min'], event['requested'])
            previous['requested_max'] = max(previous['requested_max'], event['requested'])
        else:
            record = dict(event)
            if event['event'] == 'volume':
                record.update(last_time=event['time'], count=1,
                              last_requested=event['requested'],
                              requested_min=event['requested'], requested_max=event['requested'])
            result.append(record)
    return result


def write_pcm(trace, path, frame_count):
    count = 0
    peak = squared = 0.
    pcm_hash = hashlib.sha256()
    with wave.open(str(path), 'wb') as target:
        target.setparams((2, 2, RATE, 0, 'NONE', 'not compressed'))
        for block in trace.blocks:
            peak = max(peak, float(np.max(np.abs(block))))
            squared += float(np.sum(block.astype(np.float64)**2))
            pcm = np.round(block*32767).astype('<i2').tobytes()
            pcm_hash.update(pcm)
            target.writeframes(pcm)
            count += len(block)
    require(count == frame_count*(RATE//FPS), 'PCM and native video frames differ')
    require(0 < peak < 1, 'Reconstructed music is silent or clipped')
    return {'rate': RATE, 'channels': 2, 'sample_width_bytes': 2,
            'sample_frames': count, 'samples_per_video_frame': RATE//FPS,
            'pcm_s16le_sha256': pcm_hash.hexdigest(), 'float_peak': peak,
            'float_rms': math.sqrt(squared/(count*2))}


def mux_music(silent, soundtrack, target):
    subprocess.run([
        'ffmpeg', '-y', '-v', 'error', '-i', str(silent), '-i', str(soundtrack),
        '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '128k',
        '-metadata', 'comment=Music reconstructed from production mixer commands; not hardware loopback; effects muted',
        '-movflags', '+faststart', '-shortest', str(target)], check=True)


def probe_video(path, expected_frames):
    result = subprocess.run([
        'ffprobe', '-v', 'error', '-count_frames', '-show_entries',
        'stream=codec_type,codec_name,width,height,pix_fmt,avg_frame_rate,nb_frames,nb_read_frames,sample_rate,channels:format=duration,size',
        '-of', 'json', str(path)], check=True, stdout=subprocess.PIPE, text=True)
    data = json.loads(result.stdout)
    video = next(stream for stream in data['streams'] if stream['codec_type'] == 'video')
    audio = next((stream for stream in data['streams'] if stream['codec_type'] == 'audio'), None)
    require((video['width'], video['height']) == SIZE, 'Encoded video is not native')
    require(video['avg_frame_rate'] == '30/1', 'Encoded video is not 30fps')
    require(int(video['nb_read_frames']) == expected_frames, 'Encoded video lost frames')
    require(video['codec_name'] == 'h264' and video['pix_fmt'] == 'yuv420p', 'Unexpected video codec')
    require(audio is not None and audio['codec_name'] == 'aac'
            and audio['sample_rate'] == str(RATE) and audio['channels'] == 2,
            'Missing reconstructed stereo AAC soundtrack')
    require(abs(float(data['format']['duration'])-expected_frames/FPS) < .07,
            'Encoded duration does not match the complete frame interval')
    return data


def drive_to(game, predicate, *, limit=6000):
    """Smoke-only fast reading: ordinary update, key input and draw, never seek."""
    scene = game.regent_arrival
    updates = 0
    frozen = world_state(game)
    seen = []
    for _ in range(limit):
        if not seen or seen[-1] != scene.shot:
            seen.append(scene.shot)
        if predicate():
            return {'updates': updates, 'phases': seen}
        require(scene.active, 'Smoke ended before its requested observation')
        game.update(.1, (0, 0), False)
        if scene.active and scene.dialogue is not None:
            key(game, pygame.K_SPACE)
        else:
            game.handle_events([])
        game.draw()
        require(world_state(game) == frozen, 'Smoke advanced the frozen world')
        updates += 1
    raise AssertionError('Smoke timed out through normal input')


def start_pending(game):
    # Materialize the regional cache before the durable pending restore.
    game.overworld_world
    require(game.has_saved_journey and game.begin_journey(True), 'Pending restore failed')
    scene = game.regent_arrival
    require(scene.active and scene.shot == 'mill_close' and scene.phase_time == 0.,
            'Pending restore did not restart normally')
    return scene


def smoke_checks(directory, pending, completed):
    results = {}
    replay_dir = directory/'pause_reload_skip'
    replay_dir.mkdir()
    path = replay_dir/'journey.json'
    path.write_bytes(pending)
    with disposable_game(replay_dir, title=True) as game:
        scene = start_pending(game)
        route = drive_to(game, lambda: scene.shot == PAN_SHOT and scene.phase_time >= .35)
        before = visual_state(scene)
        frozen = world_state(game)
        for mode in ('escape', 'focus'):
            if mode == 'escape':
                key(game, pygame.K_ESCAPE)
            else:
                game.handle_events([pygame.event.Event(pygame.WINDOWFOCUSLOST)])
            game.update(0, (0, 0), False)
            game.draw()
            paused_pixels = pygame.image.tobytes(game.window, 'RGB')
            game.update(50., (1, 1), True)
            key(game, pygame.K_SPACE)
            game.draw()
            require(visual_state(scene) == before and world_state(game) == frozen,
                    f'{mode} did not freeze pan, actors, quests and regional simulation')
            require(pygame.image.tobytes(game.window, 'RGB') == paused_pixels,
                    f'{mode} changed the paused render')
            require(game.music.paused and not game.pause.is_open, 'Wrong pause owner')
            if mode == 'escape':
                key(game, pygame.K_ESCAPE)
            else:
                game.handle_events([pygame.event.Event(pygame.WINDOWFOCUSGAINED)])
            game.update(0, (0, 0), False)
            require(not game.music.paused, 'Music did not resume')
            results[f'{mode}_pause_mid_pan'] = {'passed': True, 'phase_second': scene.phase_time,
                                                'large_paused_update_seconds': 50.}
        expected_inventory = copy.deepcopy(game.inventory.to_dict())
        require(not game.handle_events([pygame.event.Event(pygame.QUIT)]), 'Quit did not save')
        reloaded_bytes = path.read_bytes()
        require(RegentArrival.valid_journey(json.loads(reloaded_bytes)), 'Invalid pending checkpoint')
        results['pending_saved_mid_pan'] = {'passed': True, **route,
                                            'sha256': hashlib.sha256(reloaded_bytes).hexdigest()}
    gc.collect()
    with disposable_game(replay_dir, title=True) as game:
        scene = start_pending(game)
        require(game.inventory.to_dict() == expected_inventory, 'Reload repeated a reward')
        results['pending_reload_restarts_at_mill_close'] = {'passed': True,
                                                           'phase_second': scene.phase_time}
        route = drive_to(game, lambda: scene.shot == PAN_SHOT and scene.phase_time >= .35)
        inventory = copy.deepcopy(game.inventory.to_dict())
        quests = copy.deepcopy(game.quests.to_dict())
        attributes = copy.deepcopy(game.attributes.to_dict())
        key(game, pygame.K_ESCAPE)
        click_skip(game)
        require(not scene.active and scene.state == 'seen' and scene.finished_reason == 'skipped',
                'Mid-pan Skip did not finish normally')
        require(game.quests.status(REGENT_QUEST) == 'available' and game.regent_quest.stage == 'idle'
                and game.inventory.to_dict() == inventory and game.quests.to_dict() == quests
                and game.attributes.to_dict() == attributes, 'Skip accepted MQ03 or changed rewards')
        require(json.loads(path.read_text())['regent_arrival'] == {'version': 1, 'state': 'seen'},
                'Skip did not persist seen')
        require(not game.music.paused and game.music.desired_track == 'eldenmere'
                and not scene.audio.channels and not scene.bird_audio.voices, 'Skip leaked audio')
        results['skip_paused_mid_pan_preserves_handoff'] = {'passed': True, **route}
    gc.collect()

    large_dir = directory/'large_update'
    large_dir.mkdir()
    (large_dir/'journey.json').write_bytes(pending)
    with disposable_game(large_dir, title=True) as game:
        scene = start_pending(game)
        drive_to(game, lambda: scene.shot == PAN_SHOT and scene.phase_time >= .3)
        before = world_state(game)
        game.update(90., (1, 1), True)
        game.draw()
        require(scene.shot == 'bridge_damage' and scene.phase_time == 0.
                and scene.dialogue_index == scene.page_index == 0, 'Large pan delta skipped the account')
        require(world_state(game) == before, 'Large pan delta advanced the world')
        game.update(90., (1, 1), True)
        game.draw()
        require(scene.shot == 'bridge_damage' and scene.dialogue_index == scene.page_index == 0
                and scene.dialogue == scene.phase['dialogue'][0], 'Unread account was auto-consumed')
        require(world_state(game) == before, 'Unread account advanced the world')
        results['large_pan_update_stops_at_unread_bridge'] = {'passed': True,
                                                             'update_seconds': [90., 90.]}
        click_skip(game)
    gc.collect()

    reduced_dir = directory/'reduced_motion'
    reduced_dir.mkdir()
    (reduced_dir/'journey.json').write_bytes(pending)
    with disposable_game(reduced_dir, title=True) as game:
        game.audio.set_reduced_motion(True)
        scene = start_pending(game)
        route = drive_to(game, lambda: scene.shot == PAN_SHOT)
        before = world_state(game)
        sample = asdict(scene.road_pan_sample)
        game.draw()
        camera = tuple(scene.crossroads_data['camera_bridge'])
        require(tuple(scene.camera_position) == camera and sample['progress'] == 1.
                and sample['blur_px'] == 0. and sample['streak_count'] == 0
                and not sample['active'] and sample['camera_velocity'] == (0., 0.),
                'Reduced motion did not cut cleanly to the bridge')
        photo = scene.scenery['crossroads']['background'].subsurface(pygame.Rect(*camera, *SIZE))
        require(pygame.image.tobytes(game.canvas, 'RGB') == pygame.image.tobytes(photo, 'RGB'),
                'Reduced-motion endpoint changed scenery pixels')
        game.update(1/FPS, (1, 1), True)
        game.draw()
        require(scene.shot == 'bridge_damage' and scene.phase_time == 0.
                and world_state(game) == before, 'Reduced-motion cut did not stop at the unread account')
        results['reduced_motion_one_update_cut_no_blur'] = {'passed': True, **route,
                                                          'sample_at_real_pan_entry': sample}
        click_skip(game)
    gc.collect()

    gallery_dir = directory/'gallery'
    gallery_dir.mkdir()
    gallery_path = gallery_dir/'journey.json'
    gallery_path.write_bytes(completed)
    with disposable_game(gallery_dir, title=True) as title:
        settings_path = gallery_dir/'settings.json'
        original_save = gallery_path.read_bytes()
        original_settings = settings_path.read_bytes()
        require(title.open_gallery() and title.launch_gallery_scene('regent_arrival'),
                'Gallery could not launch arrival')
        session = title.gallery_session
        child = session.game
        require(not child.save_store.enabled and not child.save_progress(), 'Gallery can save')
        scene = child.regent_arrival
        frozen = world_state(child)
        observed = []
        frames = 0
        for _ in range(6000):
            if title.gallery_session is None:
                break
            if not observed or observed[-1] != scene.shot:
                observed.append(scene.shot)
            title.update(.1, (0, 0), False)
            if title.gallery_session is not None and scene.active and scene.dialogue is not None:
                key(title, pygame.K_SPACE)
            if title.gallery_session is not None:
                if not observed or observed[-1] != scene.shot:
                    observed.append(scene.shot)
                if scene.active:
                    require(world_state(child) == frozen, 'Gallery advanced its frozen world')
            title.draw()
            frames += 1
        else:
            raise AssertionError('Gallery failed to finish through ordinary input')
        require(title.gallery_session is None and title.on_gallery and session.closed
                and session.playback.finished, 'Gallery did not return to its catalogue')
        require(observed == [phase['id'] for phase in scene.data['phases']], 'Gallery missed a phase')
        require(gallery_path.read_bytes() == original_save
                and settings_path.read_bytes() == original_settings, 'Gallery changed temp save/settings bytes')
        results['gallery_complete_and_preserves_temp_bytes'] = {
            'passed': True, 'updates': frames, 'phases': observed,
            'save_sha256_before_and_after': hashlib.sha256(original_save).hexdigest(),
            'settings_sha256_before_and_after': hashlib.sha256(original_settings).hexdigest()}
    gc.collect()
    return results


def sample_frame(scene, frame_number, observer):
    camera = list(scene.camera_position)
    sample = {'video_frame': frame_number, 'video_second': round(frame_number/FPS, 6),
              'shot': scene.shot, 'phase_second': scene.phase_time,
              'camera': camera, 'fade_alpha': scene.fade_alpha,
              'dialogue_index': scene.dialogue_index, 'page_index': scene.page_index,
              'actors': [{'id': a['id'], 'pose': scene.actor_pose(a),
                          'position': list(scene.actor_position(a)), 'scale': scene._actor_scale(a),
                          'route': a.get('route'),
                          'route_distance': scene.actor_route_distance(a) if a.get('route') else None}
                         for a in scene.phase['actors']],
              'clerk_actual_draw': list(observer.observed)}
    if scene.phase['scene'] == 'crossroads':
        projection = scene.crossroads_data['projection']
        origin, scale = projection['origin_tiles'], projection['pixels_per_tile']
        offset = projection.get('offset_pixels', (0, 0))
        sample['viewport_center_tile'] = [(camera[i]+SIZE[i]/2-offset[i])/scale[i]+origin[i]
                                           for i in (0, 1)]
        if scene.shot == PAN_SHOT:
            sample['road_pan_sample'] = asdict(scene.road_pan_sample)
        elif scene.shot == 'bridge_damage':
            sample['geographic_road_reference_tile'] = scene.crossroads_data['bridge_tile']
        else:
            sample['geographic_road_reference_tile'] = scene.crossroads_data['junction_tile']
    if observer.aerial is not None:
        sample['aerial_camera'] = observer.aerial['camera']
        sample['aerial_clerk'] = observer.aerial['projected_actors']['clerk']
    return json_value(sample)


def capture_frames(game, output, temporary, trace, ledger):
    scene = game.regent_arrival
    frozen = world_state(game)
    game.handle_events([])
    game.update(0, (0, 0), False)
    require(scene.active and scene.shot == 'mill_close' and scene.phase_time == 0., 'Missing real arrival start')
    require(world_state(game) == frozen, 'Starting arrival changed the acknowledged world')
    trace.begin()
    full_path, short_path = temporary/'full_silent.mp4', temporary/'sequence_silent.mp4'
    full_encoder = encoder(full_path)
    short_encoder = None
    observer = ClerkObserver(scene)
    phases, pages, samples, pan_frames, pan_images = [], [], [], [], []
    stills, still_records = {}, []
    phase_counts = Counter()
    pending_page = None
    due_frame = None
    sequence_start = sequence_end = None
    frames = freeze_checks = 0
    bridge_entry = relief_entry = None
    panorama_identity = None
    panorama_cache_checks = 0
    requests = []
    original_play = game.music.play

    def play(identifier, *args, **kwargs):
        requests.append({'video_frame': frames, 'time': round(frames/FPS, 6),
                         'track': identifier, 'args': list(args), 'kwargs': kwargs})
        return original_play(identifier, *args, **kwargs)

    def still(name, image, target=None):
        if name in stills:
            return
        require(name in OWNED and name != 'capture_report.json', 'Unowned output filename')
        image.save(output/name, optimize=True)
        stills[name] = image.copy()
        still_records.append({'file': name, 'video_frame': frames,
                               'video_second': round(frames/FPS, 6), 'shot': scene.shot,
                               'phase_second': scene.phase_time, 'target_phase_second': target,
                               'camera': list(scene.camera_position),
                               'clerk_actual_draw': list(observer.observed)})

    try:
        with observer.observe(), patch.object(game.music, 'play', play):
            for number in range(18000):
                frames = number
                if number:
                    # The prior frame's PCM interval has already elapsed. Update
                    # once, then deliver a due Space before this boundary's draw.
                    # Thus input-triggered phases are rendered at their real t=0.
                    game.update(STEP, (0, 0), False)
                    if scene.active:
                        require(world_state(game) == frozen, 'World advanced behind arrival')
                        freeze_checks += 1
                    identity = (scene.shot, scene.dialogue_index, scene.page_index)
                    if (scene.active and scene.dialogue is not None and pending_page is not None
                            and identity == pending_page and due_frame is not None and number >= due_frame):
                        key(game, pygame.K_SPACE)
                        pages[-1]['acknowledged_frame'] = number
                        pages[-1]['visible_seconds'] = (number-pages[-1]['first_frame'])/FPS
                        require(pages[-1]['visible_seconds']+1e-9 >= pages[-1]['required_seconds'],
                                'A paragraph was acknowledged too soon')
                        pending_page = None
                    else:
                        game.handle_events([])
                observer.begin_frame(number)
                before_draw = (scene.phase_time, scene.elapsed, scene.shot,
                               scene.dialogue_index, scene.page_index)
                game.draw()
                require(before_draw == (scene.phase_time, scene.elapsed, scene.shot,
                                         scene.dialogue_index, scene.page_index), 'Draw advanced the story')
                image = native_frame(game)
                if scene.active:
                    require(world_state(game) == frozen, 'Draw or dialogue input changed frozen world')
                    observer.collect_card(image)
                    if not phases or phases[-1]['shot'] != scene.shot:
                        phases.append({'shot': scene.shot, 'scene': scene.phase['scene'],
                                       'first_frame': number, 'video_second': round(number/FPS, 6),
                                       'entry_phase_second': scene.phase_time})
                    phase_counts[scene.shot] += 1
                    if number % (3 if scene.shot == PAN_SHOT else 15) == 0 or phase_counts[scene.shot] == 1:
                        samples.append(sample_frame(scene, number, observer))
                    if scene.dialogue is not None:
                        identity = (scene.shot, scene.dialogue_index, scene.page_index)
                        if identity != pending_page:
                            pending_page = identity
                            text = ' '.join(scene.caption_lines)
                            words = len(text.split())
                            hold = 1.5+words*.2
                            due_frame = number+math.ceil(hold*FPS)
                            pages.append({'shot': scene.shot, 'dialogue_index': scene.dialogue_index,
                                          'page_index': scene.page_index, 'speaker': scene.dialogue['speaker'],
                                          'text': text, 'source_paragraph': scene.dialogue['text'],
                                          'words': words, 'required_seconds': hold, 'first_frame': number,
                                          'video_second': round(number/FPS, 6), 'due_frame': due_frame})
                    for target, name in STILLS.get(scene.shot, ()):
                        if scene.phase_time+1e-9 >= target:
                            still(name, image, target)
                    if scene.shot == 'locals' and scene.dialogue is not None:
                        if scene.dialogue_index == 0:
                            still('locals_first.png', image)
                        if scene.dialogue_index == len(scene.phase['dialogue'])-1:
                            still('locals_last_question.png', image)
                            if sequence_start is None:
                                sequence_start = number
                                short_encoder = encoder(short_path)
                    if (scene.shot == 'aerial_descent' and observer.observed
                            and scene.phase_time >= 6. and observer.observed[-1]['reference_clock'] is not None
                            and observer.observed[-1]['reference_clock'] < 0):
                        still('descent_clerk_negative_clock.png', image)
                    if scene.shot == PAN_SHOT:
                        pan_frames.append({'video_frame': number, 'phase_second': scene.phase_time,
                                           'sample': asdict(scene.road_pan_sample)})
                        pan_images.append((f'pan {scene.phase_time:.3f}s | blur {scene.road_pan_sample.blur_px:.1f}px | lines {scene.road_pan_sample.streak_count}',
                                           image.copy()))
                        if len(pan_frames) == 24:
                            still('pan_last_0767ms.png', image)
                    if scene.shot == 'bridge_damage' and bridge_entry is None:
                        bridge_entry = {'video_frame': number, 'phase_second': scene.phase_time,
                                        'camera': list(scene.camera_position)}
                    if scene.shot == 'relief' and relief_entry is None:
                        relief_entry = {'video_frame': number, 'phase_second': scene.phase_time,
                                        'camera': list(scene.camera_position), 'fade_alpha': scene.fade_alpha}
                    panorama = scene.scenery['crossroads']['background']
                    if panorama_identity is None:
                        panorama_identity = id(panorama)
                    require(id(panorama) == panorama_identity, 'Panorama cache was replaced per frame')
                    panorama_cache_checks += 1
                else:
                    still('saved_world.png', image)
                pixels = image.tobytes()
                require(full_encoder.stdin is not None, 'Missing raw-video pipe')
                full_encoder.stdin.write(pixels)
                if sequence_start is not None and sequence_end is None:
                    if scene.active and scene.shot in SEQUENCE_SHOTS:
                        require(short_encoder is not None and short_encoder.stdin is not None,
                                'Missing continuous sequence encoder')
                        short_encoder.stdin.write(pixels)
                    else:
                        sequence_end = number
                        close_encoder(short_encoder)
                        short_encoder = None
                trace.advance(1/FPS)
                frames = number+1
                if not scene.active:
                    break
            else:
                raise AssertionError('Full arrival failed to finish through readable ordinary input')
    finally:
        close_encoder(full_encoder)
        close_encoder(short_encoder)

    require(scene.state == 'seen' and scene.finished_reason == 'finished', 'Arrival was not completed normally')
    require([p['shot'] for p in phases] == [p['id'] for p in scene.data['phases']], 'Full film missed a phase')
    require(all('acknowledged_frame' in page for page in pages), 'A dialogue page was not read')
    require(len(pan_frames) == 24, f'Expected 24 consecutive pan frames, got {len(pan_frames)}')
    require(abs(pan_frames[0]['phase_second']) < 1e-9
            and abs(pan_frames[-1]['phase_second']-23/FPS) < 1e-8, 'Wrong actual pan interval')
    require(bridge_entry is not None and bridge_entry['video_frame'] == pan_frames[-1]['video_frame']+1
            and bridge_entry['phase_second'] == 0.
            and bridge_entry['camera'] == scene.crossroads_data['camera_bridge'],
            'Next bridge frame was not the exact endpoint')
    require(relief_entry is not None and relief_entry['camera'] == scene.crossroads_data['camera_junction']
            and relief_entry['phase_second'] == 0. and relief_entry['fade_alpha'] == 0,
            'Relief hard cut did not return exactly to the crossroads')
    require(sequence_start is not None and sequence_end is not None
            and sequence_end > relief_entry['video_frame']+FPS, 'Truncated crossroads minifilm')
    require(set(stills) == {name for targets in STILLS.values() for _, name in targets} | EXTRA_STILLS,
            'Missing requested still evidence')
    require(observer.negative_frames == set(range(8)), 'Descent did not draw all real clerk gait frames')
    require(game.quests.status(MILL_QUEST) == 'completed' and game.quests.status(REGENT_QUEST) == 'available'
            and game.regent_quest.stage == 'idle', 'Arrival changed quest handoff')
    after = world_state(game)
    for name in ('world', 'player', 'elapsed_ms', 'camera', 'inventory', 'attributes',
                 'quests', 'mill', 'regent', 'flags', 'doors', 'cached_residents', 'cached_wildlife'):
        require(after[name] == frozen[name], f'Handoff changed frozen {name}')
    # finish() intentionally hands the seen receipt to RegentQuest.restore(),
    # which stages Serene/Tomas in the dining room and reveals the visitors.
    # All ACTIVE frames above are strictly frozen. Do not misrepresent this
    # normal post-finish staging as an unchanged resident list or as simulation.
    staging_ids = {'mother_serene', 'tomas'}
    require(all(row in after['residents'] for row in frozen['residents'] if row[1] not in staging_ids),
            'Handoff relocated an unrelated resident')
    resident_changes = []
    for identifier in sorted(staging_ids):
        before_rows = [row for row in frozen['residents'] if row[1] == identifier]
        after_rows = [row for row in after['residents'] if row[1] == identifier]
        require(len(before_rows) == len(after_rows) == 1, 'Handoff lost a family resident')
        require(before_rows[0][3:] == after_rows[0][3:], 'Handoff advanced a family simulation clock')
        if before_rows != after_rows:
            resident_changes.append({'id': identifier, 'before': before_rows[0], 'after': after_rows[0]})
    existing_ids = {row[1] for row in frozen['residents']}
    new_residents = [row for row in after['residents'] if row[1] not in existing_ids]
    require({row[1] for row in new_residents} <= {'aldric', 'regent_clerk', 'regent_driver', 'regent_attendant'},
            'Handoff revealed an unrelated resident')
    completed = (temporary/'journey.json').read_bytes()
    saved = json.loads(completed)
    require(RegentArrival.valid_journey(saved) and saved['regent_arrival'] == {'version': 1, 'state': 'seen'}
            and saved['inventory'] == frozen['inventory'] and saved['quests'] == frozen['quests'],
            'Saved handoff is not seen with identical rewards/quests')

    contact_names = ('gate_approach_0600ms.png', 'gate_greeting_1000ms.png',
                     'gate_admission_1200ms.png', 'gate_admission_2500ms.png', 'gate_admission_4000ms.png',
                     'locals_first.png', 'locals_last_question.png', 'pan_0000ms.png', 'pan_0200ms.png',
                     'pan_0400ms.png', 'pan_0600ms.png', 'pan_last_0767ms.png', 'bridge_cut_0800ms.png',
                     'bridge_damage_1000ms.png', 'relief_hard_cut.png', 'relief_1000ms.png', 'saved_world.png')
    contact_sheet(output/'contact_sheet.jpg', [(name, stills[name]) for name in contact_names])
    contact_sheet(output/'motion_sheet.jpg', [*pan_images,
                  ('next frame: bridge exact endpoint', stills['bridge_cut_0800ms.png']),
                  ('bridge account (1.0s)', stills['bridge_damage_1000ms.png']),
                  ('later hard cut: relief', stills['relief_hard_cut.png'])], columns=6)
    clerk_sheet(output/'gate_clerk.png', stills, observer)
    panorama = scene.scenery['crossroads']['background']
    panorama_name = (scene.crossroads_path.parent/scene.crossroads_data['background']).relative_to(ROOT).as_posix()
    details = {'frames': frames, 'fps': FPS, 'video_size': list(SIZE),
               'duration_seconds': frames/FPS, 'world_freeze_checks': freeze_checks,
               'fixed_update_delta_seconds': STEP,
               'total_update_epsilon_seconds': (frames-1)*(STEP-1/FPS),
               'phases': [{**phase, 'frames': phase_counts[phase['shot']]} for phase in phases],
               'dialogue_pages': pages, 'sampled_trace': samples,
               'trace_sampling': '2Hz plus shot entries; 10Hz during pan; all 24 pan frames separately retained',
               'pan_frames': pan_frames, 'bridge_entry': bridge_entry, 'relief_entry': relief_entry,
               'sequence': {'first_full_frame': sequence_start, 'end_full_frame_exclusive': sequence_end,
                            'frames': sequence_end-sequence_start,
                            'duration_seconds': (sequence_end-sequence_start)/FPS,
                            'scope': 'Entire last locals question, all pan frames, both complete bridge paragraphs, entire relief phase'},
               'stills': still_records, 'clerk_observation': observer.summary(),
               'frozen_after_acknowledged_request': frozen,
               'frozen_state_sha256': json_digest(frozen),
               'handoff_restaging': {
                   'source': 'Production RegentArrival.finish -> RegentQuest.restore -> _setup_stage(force=True)',
                   'only_after_active_cinematic_finishes': True,
                   'existing_resident_changes': resident_changes, 'new_visitors': new_residents,
                   'unrelated_residents_unchanged': True, 'resident_simulation_clocks_unchanged': True},
               'saved_handoff': {'state': saved['regent_arrival'], 'mq03_status': 'available',
                                 'mq03_stage': 'idle', 'reward_inventory_unchanged': True,
                                 'inventory_sha256': json_digest(saved['inventory']),
                                 'save_sha256': hashlib.sha256(completed).hexdigest(),
                                 'world_still': 'saved_world.png', 'normal_world_updates_after_finish': 0},
               'cache': {'crossroads_png_loads_in_full_capture': ledger.image_loads[panorama_name],
                         'same_panorama_surface_checks': panorama_cache_checks,
                         'panorama_size': list(panorama.get_size()),
                         'decoded_surface_bytes': panorama.get_pitch()*panorama.get_height(),
                         'frame_size': list(SIZE), 'per_draw_native_effects_not_retained': True}}
    require(details['cache']['crossroads_png_loads_in_full_capture'] == 1, 'Panorama reloaded during full film')
    return details, requests, completed, full_path, short_path


def capture(output):
    require(shutil.which('ffmpeg') is not None and shutil.which('ffprobe') is not None, 'ffmpeg/ffprobe required')
    output.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc).isoformat()
    guard = ReadOnlyGuard(output)
    ledger = RuntimeInputs(guard)
    capture_sources = {name: guard.python[name] for name in (
        SCRIPT.relative_to(ROOT).as_posix(), 'tools/capture_battle_music_transition.py')}
    fixture_sources = {name: guard.python[name] for name in (
        'tests/test_regent_arrival.py', 'tests/test_mill_battle_gameplay.py')}
    font_sources = {p.relative_to(ROOT).as_posix(): digest(p) for p in (
        ROOT/'assets/ui/fonts/AtkinsonHyperlegible-Regular.ttf',
        ROOT/'assets/ui/fonts/AtkinsonHyperlegible-Bold.ttf', ROOT/'assets/ui/fonts/DejaVuSans.ttf')}
    trace = MixerTrace()
    try:
        with tempfile.TemporaryDirectory(prefix='regent-crossroads-capture-') as name:
            temporary = Path(name)
            trace.install()
            try:
                with ledger.observe(), disposable_game(temporary, music=True) as game:
                    game.overworld_world
                    seed_mill_report(game)
                    acknowledge_report(game)
                    pending = (temporary/'journey.json').read_bytes()
                    require(RegentArrival.valid_journey(json.loads(pending)), 'Fixture pending save is invalid')
                    details, requests, completed, silent, short_silent = capture_frames(
                        game, output, temporary, trace, ledger)
                    # Do not record cleanup stop commands as if they were scene cues.
                    trace.start = None
            finally:
                trace.close()
            audio_path = temporary/'soundtrack.wav'
            pcm = write_pcm(trace, audio_path, details['frames'])
            mux_music(silent, audio_path, output/'full_arrival.mp4')
            short_audio = temporary/'sequence.wav'
            sequence = details['sequence']
            with wave.open(str(audio_path), 'rb') as source, wave.open(str(short_audio), 'wb') as target:
                source.setpos(sequence['first_full_frame']*(RATE//FPS))
                target.setparams(source.getparams())
                short_pcm = source.readframes(sequence['frames']*(RATE//FPS))
                require(len(short_pcm) == sequence['frames']*(RATE//FPS)*4, 'Truncated sequence PCM')
                target.writeframes(short_pcm)
            mux_music(short_silent, short_audio, output/'crossroads_sequence.mp4')
            source_audio = {Path(path).relative_to(ROOT).as_posix(): digest(path) for path in trace.samples}
            require(set(source_audio) == {'assets/music/runtime/eldenmere_theme.ogg',
                                           'assets/music/runtime/royalty_of_the_realm.ogg'},
                    'Reconstruction included music other than Eldenmere/Royalty')
            royalty_plays = [event for event in trace.events if event['event'] == 'play'
                             and event['file'].endswith('/royalty_of_the_realm.ogg')]
            require(len(royalty_plays) == 1 and royalty_plays[0]['loops'] == -1, 'Royalty restarted')
            require(all(event['loops'] == -1 for event in trace.events if event['event'] == 'play'),
                    'Unexpected non-looping music in capture')
            audio = {'method': 'Offline PCM reconstruction using the actual tools.capture_battle_music_transition.MixerTrace installer',
                     'not_hardware_loopback': True, 'effects_volume': 0, 'fake_effects': False,
                     'synchronization': 'Commands observed at native video boundaries; exact 1600-sample PCM blocks per 30fps frame',
                     'initial_state': trace.initial, 'music_requests': requests,
                     'observed_mixer_commands': compressed_mixer_events(trace.events),
                     'raw_mixer_command_count': len(trace.events),
                     'volume_encoding': 'Consecutive equal applied gains run-length encoded, with actual requested ranges',
                     'royalty_loop_play_count': len(royalty_plays), 'pcm': pcm,
                     'sequence_pcm_s16le_sha256': hashlib.sha256(short_pcm).hexdigest(),
                     'source_audio_sha256': source_audio,
                     'decoded_track_sample_frames': {Path(path).relative_to(ROOT).as_posix(): len(samples)
                                                      for path, samples in trace.samples.items()}}
            write_json(output/'audio_events.json', audio)
            # Additional games are disposable and silent. They use actual input
            # and updates from mill_close, not staged cinematic checkpoints.
            with ledger.observe():
                smokes = smoke_checks(temporary, pending, completed)
            inputs = ledger.fingerprints()
            media = {name: probe_video(output/name, frames) for name, frames in (
                ('full_arrival.mp4', details['frames']),
                ('crossroads_sequence.mp4', sequence['frames']))}
            readonly = guard.verify()
            artifact_names = sorted((set(OWNED)-{'capture_report.json'}))
            require(all((output/name).is_file() for name in artifact_names), 'Missing evidence artifact')
            artifacts = {name: {'sha256': digest(output/name), 'bytes': (output/name).stat().st_size}
                         for name in artifact_names}
            report = {'version': 1, 'actual_renderer': True, 'capture_complete': True,
                      'started_at_utc': started, 'finished_at_utc': datetime.now(timezone.utc).isoformat(),
                      'capture_command': '/usr/local/bin/python3 -B tools/capture_regent_crossroads.py',
                      'fixture': {'fresh_game_temporary_journey_and_settings': True,
                                  'earlier_quest_work': 'test_regent_arrival.seed_mill_report',
                                  'report_acknowledgement': 'test_regent_arrival.acknowledge_report: ordinary Space input',
                                  'cached_region_created_before_report': True,
                                  'assigned_cinematic_clocks_or_phase_indices': False,
                                  'assigned_dialogue_indices_or_actor_stations': False,
                                  'full_playthrough_uses_fixed_step_update_and_real_input_draw': True,
                                  'pending_save_sha256': hashlib.sha256(pending).hexdigest()},
                      'encoding': {'size': list(SIZE), 'fps': FPS, 'codec': 'libx264',
                                   'crf': 22, 'preset': 'veryfast', 'audio': 'AAC 128k stereo',
                                   'no_gif': True, 'temporary_raw_video_and_pcm_not_retained': True},
                      **details, 'ordinary_completion': True, 'MQ03_available_unaccepted': True,
                      'audio': {'evidence': 'audio_events.json', 'reconstructed_not_loopback': True,
                                'effects_muted_no_fabricated_effects': True,
                                'royalty_loop_play_count': len(royalty_plays), 'pcm': pcm},
                      'smoke_checks': smokes, 'readonly_guards': readonly,
                      'render_input_scope': 'Only actually executed production Python and actually read runtime asset JSON/PNG; no reviews, authoring inputs or self-report',
                      'render_input_sha256': inputs, 'capture_code_sha256': capture_sources,
                      'fixture_input_sha256': fixture_sources, 'font_input_sha256': font_sources,
                      'source_audio_sha256': source_audio, 'media_probe': media, 'artifacts': artifacts,
                      'environment': {'python': platform.python_version(), 'pygame': pygame.version.ver,
                                      'sdl': list(pygame.get_sdl_version()),
                                      'video_driver': pygame.display.get_driver(),
                                      'audio_driver': os.environ.get('SDL_AUDIODRIVER'),
                                      'numpy': np.__version__, 'pillow': Image.__version__},
                      'known_limitations': ['Headless music is reconstructed from commands, not hardware loopback; effects intentionally absent.',
                                            'One final normal-world draw is recorded; no normal-world simulation update is run after handoff.',
                                            'The normal seen handoff restages Serene/Tomas and reveals the visitors; these changes are reported separately from the strictly frozen active cinematic.',
                                            'Clerk crop panels are nearest-neighbor enlargements of actual in-game frames, not isolated sprite renders.',
                                            'This capture is not the broader test suite. Parent edits to recorded inputs require recapture.']}
            # No source edit may occur after the source hash baseline above.
            require(all(digest(ROOT/path) == value for path, value in capture_sources.items()), 'Capture code changed')
            write_json(output/'capture_report.json', report)
            print(json.dumps({'output': str(output), 'frames': details['frames'],
                              'seconds': details['duration_seconds'], 'pan_frames': len(details['pan_frames']),
                              'sequence_frames': sequence['frames'], 'world_freeze_checks': details['world_freeze_checks'],
                              'dialogue_pages': len(details['dialogue_pages']), 'smokes': len(smokes),
                              'render_inputs': len(inputs), 'cache': details['cache'],
                              'new_evidence_bytes': sum(item['bytes'] for item in artifacts.values()),
                              'report_sha256': digest(output/'capture_report.json')}, indent=2))
    finally:
        trace.close()
        pygame.quit()


def check(output):
    """Read-only staleness/media verification; never refresh stale fingerprints."""
    report_path = output/'capture_report.json'
    before = digest(report_path)
    report = json.loads(report_path.read_text())
    require(report.get('capture_complete') is True, 'Incomplete capture report')
    failures = []
    count = 0
    for section in ('render_input_sha256', 'capture_code_sha256', 'fixture_input_sha256',
                    'font_input_sha256', 'source_audio_sha256'):
        for name, value in report[section].items():
            path = (ROOT/name).resolve()
            require(path.is_relative_to(ROOT), 'Fingerprint leaves workspace')
            count += 1
            if not path.is_file() or digest(path) != value:
                failures.append(f'{section}: {name}')
    for name, record in report['artifacts'].items():
        path = (output/name).resolve()
        require(path.parent == output and name in OWNED, 'Unexpected artifact path')
        if not path.is_file() or digest(path) != record['sha256'] or path.stat().st_size != record['bytes']:
            failures.append(f'artifact: {name}')
    for name, value in report['readonly_guards']['preserved_existing_review_sha256'].items():
        if not (output/name).is_file() or digest(output/name) != value:
            failures.append(f'preserved original: {name}')
    require(not failures, 'Stale capture; recapture instead of rewriting metadata:\n'+'\n'.join(failures))
    probe_video(output/'full_arrival.mp4', report['frames'])
    probe_video(output/'crossroads_sequence.mp4', report['sequence']['frames'])
    require(digest(report_path) == before, '--check changed its report')
    print(json.dumps({'check': 'passed', 'metadata_rewritten': False, 'fingerprints': count,
                      'artifact_hashes': len(report['artifacts']), 'frames': report['frames'],
                      'pan_frames': len(report['pan_frames']), 'sequence_frames': report['sequence']['frames'],
                      'preserved_existing_review_files': len(report['readonly_guards']['preserved_existing_review_sha256']),
                      'report_sha256': before,
                      'media_sha256': {name: record['sha256'] for name, record in report['artifacts'].items()
                                       if name.endswith('.mp4')}}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    parser.add_argument('--check', action='store_true', help='Validate existing hashes/media; write nothing')
    args = parser.parse_args()
    output = args.output.resolve()
    if args.check:
        check(output)
    else:
        capture(output)


if __name__ == '__main__':
    main()