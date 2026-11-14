"""Capture the real arrival's side walks using normal input/update/draw only.

Earlier MQ02 work is a test fixture. The unread report, every cinematic phase,
and the final quest handoff progress normally; no scene clock or actor station
is assigned. Only the side-walking shots are recorded in the review clip.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'tests')]

import pygame
from PIL import Image, ImageDraw

from main import Game
from quests import MILL_QUEST, REGENT_QUEST
from test_regent_arrival import acknowledge_report, seed_mill_report

OUT = ROOT/'docs/reviews/aldric_side_walk'
FPS = 30
SHOTS = ('gate_approach', 'town_approach', 'town_parking')


def signature(game):
    return (game.world.data['id'], tuple(game.player.position), game.elapsed_ms,
            tuple((world.data['id'], actor.data['id'], tuple(actor.position))
                  for world in game.scenes.values() for actor in world.npcs))


def inputs():
    paths = [ROOT/name for name in ('regent_arrival.py', 'main.py',
             'tools/build_aldric_side_walk.py', 'tools/build_regent_arrival_actors.py',
             'tools/capture_aldric_side_walk.py', 'assets/story/regent_arrival/scene.json')]
    paths.extend((ROOT/'assets/story/regent_arrival/actors').rglob('*.png'))
    paths.extend((ROOT/'assets/story/regent_arrival/actors').rglob('*.json'))
    paths.extend(path for path in
                 (ROOT/'assets/source/cinematics/regent_arrival/actors/aldric_side_walk').glob('*')
                 if path.suffix in ('.png','.json'))
    return {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
            for p in paths if p.is_file()}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    original = inputs()
    with tempfile.TemporaryDirectory(prefix='aldric-walk-capture-') as temporary:
        directory = Path(temporary)
        game = Game(fullscreen=False, start_on_title=False, window_size=(960, 640),
                    save_path=directory/'journey.json', settings_path=directory/'settings.json')
        game.audio.set_music(0)
        game.audio.set_effects(0)
        seed_mill_report(game)
        acknowledge_report(game)
        game.update(1/FPS, (0, 0), False)
        scene = game.regent_arrival
        frozen = signature(game)
        trace, phases, cards = [], [], {}
        video = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo',
            '-pixel_format', 'rgb24', '-video_size', '480x320', '-framerate', str(FPS),
            '-i', '-', '-an', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '16',
            '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(OUT/'in_scene.mp4')],
            stdin=subprocess.PIPE)
        frame_count = 0
        try:
            for tick in range(12000):
                if not scene.active:
                    break
                shot = scene.shot
                if not phases or phases[-1] != shot:
                    phases.append(shot)
                if shot in SHOTS:
                    game.draw()
                    image = Image.frombytes('RGB', game.ui_surface.get_size(),
                                            pygame.image.tobytes(game.ui_surface, 'RGB'))
                    image = image.resize((480, 320), Image.Resampling.NEAREST)
                    video.stdin.write(image.tobytes())
                    frame_count += 1
                    actor = next(a for a in scene.phase['actors'] if a['id'] == 'aldric')
                    pose = scene.actor_pose(actor)
                    selected = scene._frame(actor)
                    loop = scene.actor_art['aldric']['loops'].get(pose, [])
                    index = next((i for i, (frame, _) in enumerate(loop) if frame is selected), None)
                    position = scene.actor_position(actor)
                    trace.append(dict(shot=shot, seconds=scene.phase_time, position=list(position),
                                      pose=pose, frame=index))
                    if pose == 'walk_left':
                        if (shot, index) not in cards:
                            camera = scene.camera_position
                            center = position-camera
                            crop = image.crop((round(center.x)-48, round(center.y)-96,
                                               round(center.x)+48, round(center.y)+8))
                            cards[shot, index] = crop.resize((192, 208), Image.Resampling.NEAREST)
                if scene.dialogue is not None:
                    game.handle_events([pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE, repeat=False),
                                        pygame.event.Event(pygame.KEYUP, key=pygame.K_SPACE)])
                game.update(1/FPS, (0, 0), False)
                if scene.active:
                    assert signature(game) == frozen
            else:
                raise AssertionError('Arrival did not finish through ordinary input')
        finally:
            video.stdin.close()
            assert video.wait() == 0
            game.music.stop()
            game.opening_audio.reset()
            game.regional_audio.reset()
        assert scene.finished_reason == 'finished' and scene.state == 'seen'
        assert game.quests.status(MILL_QUEST) == 'completed'
        assert game.quests.status(REGENT_QUEST) == 'available'
        assert game.regent_quest.stage == 'idle'
        assert original == inputs(), 'Capture modified production inputs'
        sheet = Image.new('RGB', (8*200, 3*240), '#26352e')
        draw = ImageDraw.Draw(sheet)
        for row, name in enumerate(SHOTS):
            observed = {sample['frame'] for sample in trace
                        if sample['shot']==name and sample['pose']=='walk_left'}
            assert observed == set(range(8)), (name, observed)
            for index in range(8):
                sheet.paste(cards[name, index], (index*200, row*240))
                draw.text((index*200+5, row*240+216), name+' / '+str(index), fill='#f1e7c8')
        sheet.save(OUT/'in_scene_frames.png', optimize=True)
        report = dict(actual_renderer=True, fps=FPS, recorded_frames=frame_count,
                      capture='normal Game input/update/draw; side-walk clips only',
                      assigned_cinematic_clocks=False, relocated_actors=False,
                      audio='silent SDL dummy review; production score unchanged',
                      all_eight_frames_visible_in_each_side_shot=True,
                      world_frozen=True, ordinary_completion=True,
                      mq03_available_not_accepted=True, phases=phases,
                      render_input_sha256=original, sampled_actor_trace=trace)
        (OUT/'capture_report.json').write_text(json.dumps(report, indent=2)+'\n')
        print(json.dumps({key:value for key,value in report.items()
                          if key not in ('render_input_sha256','sampled_actor_trace')}, indent=2))
    pygame.quit()


if __name__ == '__main__':
    main()