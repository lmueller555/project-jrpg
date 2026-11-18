"""Review native Iselin's front walk through production movement/rendering.

This stages a review-only actor in a disposable game session. World.draw and
WorldCanvas.present_detail provide every scene frame; game/HUD input does not
advance. No production actor binding or player save is changed.
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
from PIL import Image, ImageDraw, ImageFont

from main import camera_for
from regent_actors import StoryActor
from tools.capture_sanctuary_rescue import make_game


ART = Path('assets/characters/iselin/native_walk_front')
DEFAULT_OUT = ROOT / 'docs/reviews/iselin_native_front_walk'
START = (384, 432)
GOAL = (384, 598)
SPEED = 74
DT = .035
WALK_SAMPLES = 64
HOLD_SAMPLES = 8
NORMAL_MS = [30, 40] * 8  # GIF stores durations in multiples of 10 ms.
SLOW_MS = [100, 110] * 8


def font(size):
    path = Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
    return ImageFont.truetype(str(path), size) if path.exists() else ImageFont.load_default()


def render(game, camera):
    game.canvas.reset_detail()
    game.world.draw(game.canvas, camera, game.player, 0, include_ui=False)
    target = pygame.transform.scale(game.canvas, (960, 640))
    game.canvas.present_detail(target)
    return Image.frombytes('RGB', target.get_size(), pygame.image.tobytes(target, 'RGB'))


def labelled(image, title, subtitle):
    result = Image.new('RGB', (image.width, image.height + 64), '#e8edf2')
    result.paste(image, (0, 38))
    draw = ImageDraw.Draw(result)
    draw.text((10, 10), title, font=font(15), fill='#263c35')
    draw.text((10, image.height + 44), subtitle, font=font(12), fill='#263c35')
    return result


def gif(path, frames, durations):
    # One palette keeps static scenery from changing color between exposures.
    palette = frames[0].quantize(colors=256, method=Image.Quantize.MEDIANCUT)
    indexed = [frame.quantize(palette=palette, dither=Image.Dither.NONE) for frame in frames]
    indexed[0].save(path, save_all=True, append_images=indexed[1:],
                    duration=durations, loop=0, disposal=2, optimize=False)
    with Image.open(path) as saved:
        total = 0
        for index in range(saved.n_frames):
            saved.seek(index)
            total += saved.info['duration']
    assert total == sum(durations), (str(path), total, sum(durations))


def sample(actor, phase, sample_index, camera):
    return {'phase': phase, 'sample': sample_index,
            'position': [round(value, 6) for value in actor.position],
            'walk_ms': round(actor.walk_ms, 6), 'moving': actor.moving,
            'facing': actor.facing, 'camera': list(camera),
            'native_frame_sha256': sha256(pygame.image.tobytes(actor.sprite(0), 'RGBA')).hexdigest(),
            'detail_override': actor.detailed_sprite(0) is not None}


def capture(output=DEFAULT_OUT):
    output = Path(output)
    required = [ROOT / ART / 'animation.json', ROOT / ART / 'review_actor.json',
                *(ROOT / ART / f'frame_{index:02}.png' for index in range(1, 17))]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
    if missing:
        raise SystemExit('Create the native front-walk exports first: ' + ', '.join(missing))
    manifest = json.loads((ROOT / ART / 'review_actor.json').read_text())
    if 'sheet' not in manifest:
        raise SystemExit('review_actor.json must be the ordinary sheet-based actor animation manifest')
    required.append(ROOT / manifest['sheet'])
    required.extend(ROOT / f'assets/characters/iselin/native_idles/idle_{direction}.png'
                    for direction in ('front', 'left', 'right', 'back'))
    output.mkdir(parents=True, exist_ok=True)
    travel_frames = []
    travel_records = []
    loop_frames = []
    loop_records = []
    with tempfile.TemporaryDirectory(prefix='iselin-native-front-walk-') as directory:
        game = make_game(directory, seed=False, embedded=False)
        try:
            game.world = game.town
            game.on_title = False
            game.opening_fade = 0
            game.player.story_visible = True
            game.player.position.update(432, START[1])
            game.player.moving = game.player.running = False
            game.player.facing = 'front'
            for attribute in ('story_sprite', 'story_position', 'story_draw_anchor',
                              'story_sort_y', 'story_detail'):
                if hasattr(game.player, attribute):
                    delattr(game.player, attribute)
            mira = game.mill_quest.mira
            mira.position.update(336, START[1])
            mira.quest_mode = True
            mira.moving = False
            mira.facing = 'front'
            mira.end_conversation()
            for visitor in game.regent_quest.actors.values():
                visitor.story_visible = False
            actor = StoryActor({
                'id': 'iselin_native_front_walk_review', 'name': 'Regent Iselin',
                'position': START, 'draw_anchor': [12, 30], 'probe_size': [8, 4],
                'facing': 'front', 'art': (ART / 'review_actor.json').as_posix(),
            }, game.world)
            actor.story_visible = True
            assert len(actor.walks['front']) == 16
            assert actor.walk_durations['front'] == (35,) * 16
            assert not actor.detail_idles and not actor.detail_walks
            assert all(frame.get_size() == (24, 36) for frame in actor.walks['front'])
            game.regent_quest._place(actor, game.world, START)
            before = game.quests.to_dict()
            clearance = []
            player_blocker = game.world.probe_rect(game.player.position)
            for y in range(START[1], GOAL[1] + 1):
                clear = game.world.can_stand((START[0], y), actor.probe_size, actor, player_blocker)
                assert clear, ('Route obstructed', START[0], y)
                clearance.append([START[0], y])
            assert game.world.can_stand(game.player.position, game.world.probe_size)
            assert game.world.can_stand(mira.position, mira.probe_size, mira)
            camera = camera_for(((START[0] + GOAL[0]) / 2, (START[1] + GOAL[1]) / 2),
                                game.world.size)
            for phase, count, goal in (('IDLE', HOLD_SAMPLES, START),
                                       ('WALK', WALK_SAMPLES, GOAL),
                                       ('STOP', HOLD_SAMPLES, GOAL)):
                for _ in range(count):
                    game.regent_quest._move(actor, goal, DT, SPEED)
                    assert game.world.can_stand(actor.position, actor.probe_size, actor, player_blocker)
                    assert actor.detailed_sprite(0) is None
                    assert actor.facing == 'front'
                    assert actor.moving == (phase == 'WALK'), (phase, actor.position)
                    image = render(game, camera)
                    index = len(travel_frames)
                    record = sample(actor, phase, index, camera)
                    record['simulation_dt_ms'] = 35
                    record['gif_duration_ms'] = (30, 40)[index % 2]
                    travel_records.append(record)
                    travel_frames.append(labelled(image.crop((240, 0, 720, 560)),
                        f'ISELIN / FRONT / {phase} / t={(index + 1) * DT:.3f}s',
                        'Actual town renderer; fixed camera; ordinary game scale.'))
                    if phase == 'WALK' and index == HOLD_SAMPLES + 31:
                        image.save(output / 'in_game_front_walk.png')
            assert actor.position.distance_to(GOAL) < 1
            assert game.quests.to_dict() == before
            # In-place phase inspection uses the same StoryActor/World renderer.
            # Only this explicitly labelled fixture pins the actor's position.
            game.regent_quest._place(actor, game.world, START)
            actor.moving = True
            loop_camera = camera_for(START, game.world.size)
            for index in range(16):
                actor.walk_ms = index * 35
                image = render(game, loop_camera)
                x, y = actor.position
                crop = (2 * (x - 24 - loop_camera[0]), 2 * (y - 36 - loop_camera[1]),
                        2 * (x + 24 - loop_camera[0]), 2 * (y + 12 - loop_camera[1]))
                closeup = image.crop(crop).resize((288, 288), Image.Resampling.NEAREST)
                loop_frames.append(labelled(closeup, f'ISELIN / FRONT / {index + 1:02}/16',
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
               'in_game_loop_slow.gif', 'in_game_front_walk.png', 'in_game_closeup.png')]
    metadata = {
        'renderer': 'World.draw + WorldCanvas.present_detail, 960x640 presentation; scenery frozen at0.',
        'movement': 'RegentQuest._move at74worldpx/s for travel; explicitly pinned in-place inspection separately.',
        'scope': 'Review actor only; live Iselin art bindings/walks/quest state unchanged.',
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
    print('Captured actual frontward travel, stop transitions and native normal/slow inspection loops.')
    return metadata


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=DEFAULT_OUT)
    capture(parser.parse_args().out)
