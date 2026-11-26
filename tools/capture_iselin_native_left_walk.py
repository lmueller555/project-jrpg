"""Render native Iselin's left walk through production movement for review.

Only a temporary review actor is staged. World.draw/present_detail render the
town; campaign bindings and player saves are never changed.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
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
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pygame
from PIL import Image

from main import camera_for
from story_actor import StoryActor
from tools.capture_iselin_native_front_walk import gif, labelled, render, sample
from tools.scenario_fixtures import make_game, place_review_actor, move_review_actor


ART = Path('assets/characters/iselin/native_walk_left')
DEFAULT_OUT = ROOT / 'docs/reviews/iselin_native_left_walk'
START = (550, 480)
GOAL = (384, 480)
SPEED = 74
DT = .035
WALK_SAMPLES = 64
HOLD_SAMPLES = 8
NORMAL_MS = [30, 40] * 8
SLOW_MS = [100, 110] * 8


def capture(output=DEFAULT_OUT):
    output = Path(output)
    required = [ROOT / ART / 'animation.json', ROOT / ART / 'review_actor.json',
                *(ROOT / ART / f'frame_{index:02}.png' for index in range(1, 17))]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
    if missing:
        raise SystemExit('Create the native left-walk exports first: ' + ', '.join(missing))
    manifest = json.loads((ROOT / ART / 'review_actor.json').read_text())
    if 'sheet' not in manifest:
        raise SystemExit('review_actor.json must be the ordinary sheet-based actor animation manifest')
    required.append(ROOT / manifest['sheet'])
    required.extend(ROOT / f'assets/characters/iselin/native_idles/idle_{direction}.png'
                    for direction in ('front', 'left', 'right', 'back'))
    required.append(ROOT / 'tools/capture_iselin_native_front_walk.py')
    output.mkdir(parents=True, exist_ok=True)
    travel_frames = []
    travel_records = []
    loop_frames = []
    loop_records = []
    with tempfile.TemporaryDirectory(prefix='iselin-native-left-walk-') as directory:
        game = make_game(directory, seed=False, embedded=False)
        try:
            game.world = game.town
            game.on_title = False
            game.opening_fade = 0
            game.player.story_visible = True
            game.player.position.update(550, 432)
            game.player.moving = game.player.running = False
            game.player.facing = 'left'
            for attribute in ('story_sprite', 'story_position', 'story_draw_anchor',
                              'story_sort_y'):
                if hasattr(game.player, attribute):
                    delattr(game.player, attribute)
            mira = game.mill_quest.mira
            mira.position.update(550, 528)
            mira.quest_mode = True
            mira.moving = False
            mira.facing = 'left'
            mira.end_conversation()
            actor = StoryActor({
                'id': 'iselin_native_left_walk_review', 'name': 'Regent Iselin',
                'position': START, 'draw_anchor': [12, 30], 'probe_size': [8, 4],
                'facing': 'left', 'art': (ART / 'review_actor.json').as_posix(),
            }, game.world)
            actor.story_visible = True
            assert len(actor.walks['left']) == 16
            assert actor.walk_durations['left'] == (35,) * 16
            assert not getattr(actor, 'detail_idles', {}) and not getattr(actor, 'detail_walks', {})
            assert all(frame.get_size() == (24, 36) for frame in actor.walks['left'])
            place_review_actor(actor, game.world, START)
            before = game.quests.to_dict()
            clearance = []
            player_blocker = game.world.probe_rect(game.player.position)
            for x in range(GOAL[0], START[0] + 1):
                clear = game.world.can_stand((x, START[1]), actor.probe_size, actor, player_blocker)
                assert clear, ('Route obstructed', x, START[1])
                clearance.append([x, START[1]])
            assert game.world.can_stand(game.player.position, game.world.probe_size)
            assert game.world.can_stand(mira.position, mira.probe_size, mira)
            camera = camera_for(((START[0] + GOAL[0]) / 2, START[1]), game.world.size)
            for phase, count, goal in (('IDLE', HOLD_SAMPLES, START),
                                       ('WALK', WALK_SAMPLES, GOAL),
                                       ('STOP', HOLD_SAMPLES, GOAL)):
                for _ in range(count):
                    move_review_actor(actor, game.world, goal, DT, SPEED)
                    assert game.world.can_stand(actor.position, actor.probe_size, actor, player_blocker)
                    assert getattr(actor, 'detailed_sprite', lambda _: None)(0) is None
                    assert actor.facing == 'left'
                    assert actor.moving == (phase == 'WALK'), (phase, actor.position)
                    image = render(game, camera)
                    index = len(travel_frames)
                    record = sample(actor, phase, index, camera)
                    record.update(simulation_dt_ms=35, gif_duration_ms=(30, 40)[index % 2])
                    travel_records.append(record)
                    travel_frames.append(labelled(image.crop((240, 120, 720, 500)),
                        f'ISELIN / LEFT / {phase} / t={(index + 1) * DT:.3f}s',
                        'Actual town renderer; fixed camera; ordinary game scale.'))
                    if phase == 'WALK' and index == HOLD_SAMPLES + 31:
                        image.save(output / 'in_game_left_walk.png')
            assert actor.position.distance_to(GOAL) < 1
            assert game.quests.to_dict() == before
            # Explicitly pinned phase inspection, separate from actual travel.
            place_review_actor(actor, game.world, START)
            actor.moving = True
            loop_camera = camera_for(START, game.world.size)
            for index in range(16):
                actor.walk_ms = index * 35
                image = render(game, loop_camera)
                x, y = actor.position
                crop = (2 * (x - 24 - loop_camera[0]), 2 * (y - 36 - loop_camera[1]),
                        2 * (x + 24 - loop_camera[0]), 2 * (y + 12 - loop_camera[1]))
                closeup = image.crop(crop).resize((288, 288), Image.Resampling.NEAREST)
                loop_frames.append(labelled(closeup, f'ISELIN / LEFT / {index + 1:02}/16',
                                            'In-place; game-window crop enlarged 3x.'))
                loop_records.append(sample(actor, 'IN_PLACE', index, loop_camera))
        finally:
            game.opening_audio.reset()
            game.cave_lesson.release_pose()
            game.elemental_bosses.stop_audio()
            game.music.stop()
            pygame.quit()
    gif(output / 'in_game_travel.gif', travel_frames, [30, 40] * (len(travel_frames) // 2))
    gif(output / 'in_game_loop.gif', loop_frames, NORMAL_MS)
    gif(output / 'in_game_loop_slow.gif', loop_frames, SLOW_MS)
    loop_frames[4].save(output / 'in_game_closeup.png')
    exports = [output / filename for filename in ('in_game_travel.gif', 'in_game_loop.gif',
               'in_game_loop_slow.gif', 'in_game_left_walk.png', 'in_game_closeup.png')]
    metadata = {
        'renderer': 'World.draw + WorldCanvas.present_detail, 960x640 presentation; scenery frozen at0.',
        'movement': 'RegentQuest._move at74worldpx/s for left travel; pinned in-place inspection separately.',
        'scope': 'Isolated direction inspection fixture; canonical native Iselin is integrated separately.',
        'persistence': 'Disposable save/settings directory; no player saves published.',
        'base_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'walking_speed_world_px_s': SPEED, 'simulation_step_ms': 35,
        'fixed_camera': list(camera), 'route_start': START, 'route_goal': GOAL,
        'route_clearance_positions': clearance, 'quests_unchanged': True,
        'normal_loop_ms': sum(NORMAL_MS), 'normal_gif_exposures_ms': NORMAL_MS,
        'slow_loop_ms': sum(SLOW_MS), 'slow_gif_exposures_ms': SLOW_MS,
        'travel_frames': travel_records, 'in_place_frames': loop_records,
        'source_sha256': {str(path.relative_to(ROOT)): sha256(path.read_bytes()).hexdigest()
                          for path in required},
        'output_sha256': {path.name: sha256(path.read_bytes()).hexdigest() for path in exports},
    }
    (output / 'capture.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print('Captured actual leftward travel, stop transitions and native normal/slow inspection loops.')
    return metadata


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=DEFAULT_OUT)
    capture(parser.parse_args().out)
