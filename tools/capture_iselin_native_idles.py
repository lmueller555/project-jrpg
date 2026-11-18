"""Stage native-density Iselin idles in the production town renderer for review.

No live actor manifest is changed, and all game/save settings are disposable.
The labelled overview contains unscaled crops of the resulting game frames.
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

from regent_actors import StoryActor
from tools.capture_sanctuary_rescue import make_game


DIRECTIONS = ('front', 'left', 'right', 'back')
ART = Path('assets/characters/iselin/native_idles')
DEFAULT_OUT = ROOT / 'docs/reviews/iselin_native_idles'
# Clear, source-authored courtyard paving below the Sanctuary frontage.
POSITIONS = {'caelan': (336, 330), 'mira': (384, 330), 'iselin': (432, 330)}
FOCUS = (384, 330)


def font(size):
    path = ROOT / 'assets/fonts/DejaVuSans.ttf'
    if not path.exists():
        path = Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
    return ImageFont.truetype(str(path), size) if path.exists() else ImageFont.load_default()


def capture(output=DEFAULT_OUT):
    output = Path(output)
    required = [ROOT / ART / 'animation.json',
                *(ROOT / ART / f'idle_{direction}.png' for direction in DIRECTIONS)]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
    if missing:
        raise SystemExit('Create the staged native idle exports first: ' + ', '.join(missing))
    output.mkdir(parents=True, exist_ok=True)
    records = []
    panels = []
    closeups = []
    with tempfile.TemporaryDirectory(prefix='iselin-native-idle-review-') as directory:
        game = make_game(directory, seed=False, embedded=False)
        try:
            game.world = game.town
            game.on_title = False
            game.opening_fade = 0
            game.location_seconds = 0
            game.elapsed_ms = 0
            game.player.story_visible = True
            for attribute in ('story_sprite', 'story_position', 'story_draw_anchor',
                              'story_sort_y', 'story_detail'):
                if hasattr(game.player, attribute):
                    delattr(game.player, attribute)
            # This is an isolated placement fixture, not a quest-state edit.
            for actor in game.regent_quest.actors.values():
                actor.story_visible = False
            game.player.position.update(POSITIONS['caelan'])
            game.player.moving = game.player.running = False
            mira = game.mill_quest.mira
            mira.position.update(POSITIONS['mira'])
            mira.quest_mode = True
            mira.moving = False
            mira.story_visible = True
            mira.end_conversation()
            actor = StoryActor({
                'id': 'iselin_native_idle_review', 'name': 'Regent Iselin',
                'position': POSITIONS['iselin'], 'draw_anchor': [12, 30],
                'probe_size': [8, 4], 'facing': 'front',
                'art': (ART / 'animation.json').as_posix(),
            }, game.world)
            actor.story_visible = True
            assert not actor.detail_idles and not actor.detail_walks
            for name, person, probe in (('caelan', game.player, game.world.probe_size),
                                        ('mira', mira, mira.probe_size),
                                        ('iselin', actor, actor.probe_size)):
                assert game.world.can_stand(person.position, probe, person), name
            game.world.npcs.append(actor)
            game.camera.reset()
            game.camera.focus(FOCUS, duration=0)
            camera = game.camera.position()
            assert game.window.get_size() == (960, 640)
            # Crop the already rendered window; do not rescale/replace its art.
            crop = (2 * (FOCUS[0] - 120 - camera[0]),
                    2 * (FOCUS[1] - 75 - camera[1]),
                    2 * (FOCUS[0] + 120 - camera[0]),
                    2 * (FOCUS[1] + 55 - camera[1]))
            for direction in DIRECTIONS:
                game.player.facing = mira.facing = actor.facing = direction
                assert actor.sprite(0).get_size() == (24, 36)
                assert actor.detailed_sprite(0) is None
                game.draw()
                filename = f'in_game_{direction}.png'
                pygame.image.save(game.window, str(output / filename))
                image = Image.open(output / filename).convert('RGB')
                panels.append((direction, image.crop(crop)))
                closeup = (2 * (FOCUS[0] - 58 - camera[0]),
                           2 * (FOCUS[1] - 36 - camera[1]),
                           2 * (FOCUS[0] + 58 - camera[0]),
                           2 * (FOCUS[1] + 6 - camera[1]))
                closeups.append((direction, image.crop(closeup).resize((464, 168),
                                                                       Image.Resampling.NEAREST)))
                records.append({'direction': direction, 'file': filename,
                                'window_size': list(game.window.get_size()),
                                'camera': list(camera), 'overview_crop': list(crop),
                                'closeup_crop': list(closeup), 'closeup_enlargement': 2,
                                'positions': POSITIONS, 'iselin_draw_anchor': [12, 30],
                                'iselin_probe': [8, 4], 'iselin_detail_override': False})
        finally:
            game.opening_audio.reset()
            game.cave_lesson.release_pose()
            game.elemental_bosses.stop_audio()
            game.music.stop()
            pygame.quit()
    board = Image.new('RGB', (1008, 744), '#e8edf2')
    draw = ImageDraw.Draw(board)
    draw.text((16, 12), 'ISELIN / NATIVE IDLES / IN-GAME REVIEW', font=font(21), fill='#263c35')
    draw.text((16, 42), 'Actual Game.draw() frames; courtyard placement fixture; review only.',
              font=font(14), fill='#263c35')
    for index, (direction, image) in enumerate(panels):
        x = 16 + (index % 2) * 496
        y = 76 + (index // 2) * 326
        draw.text((x, y), direction.upper(), font=font(17), fill='#263c35')
        for name, center in (('Caelan', 144), ('Mira', 240), ('Iselin', 336)):
            draw.text((x + center, y + 25), name, anchor='mt', font=font(14), fill='#263c35')
        board.paste(image, (x, y + 52))
    board.save(output / 'in_game_overview.png')
    enlarged = Image.new('RGB', (976, 548), '#e8edf2')
    draw = ImageDraw.Draw(enlarged)
    draw.text((16, 12), 'ISELIN / IN-GAME COMPARISON CLOSEUPS', font=font(21), fill='#263c35')
    draw.text((16, 42), 'Actual game-frame crops enlarged 2x with nearest-neighbor pixels.',
              font=font(14), fill='#263c35')
    for index, (direction, image) in enumerate(closeups):
        x = 16 + (index % 2) * 480
        y = 76 + (index // 2) * 236
        draw.text((x, y), direction.upper(), font=font(17), fill='#263c35')
        for name, center in (('Caelan', 40), ('Mira', 232), ('Iselin', 424)):
            draw.text((x + center, y + 25), name, anchor='mt', font=font(14), fill='#263c35')
        enlarged.paste(image, (x, y + 52))
    enlarged.save(output / 'in_game_closeups.png')
    exports = [output / record['file'] for record in records]
    exports.extend((output / 'in_game_overview.png', output / 'in_game_closeups.png'))
    metadata = {
        'fixture': 'Four staged facings in Game.draw(), using the actual town and cast idles.',
        'scope': 'Idle art review only; live Iselin manifests, walks and scene poses unchanged.',
        'persistence': 'Temporary save/settings directory; no player saves published.',
        'base_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'source_sha256': {str(path.relative_to(ROOT)): sha256(path.read_bytes()).hexdigest()
                          for path in required},
        'output_sha256': {path.name: sha256(path.read_bytes()).hexdigest() for path in exports},
        'frames': records,
    }
    (output / 'capture.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print('Captured four production game frames and the unscaled in-game comparison overview.')
    return metadata


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=DEFAULT_OUT)
    capture(parser.parse_args().out)
