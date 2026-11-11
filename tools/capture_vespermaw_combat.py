"""Review Vespermaw's retained sprite poses in an isolated cave visual fixture.

The sprite board samples the actual manifest clocks. BattleScene captures use
ordinary Bat rules with only the enemy name/art replaced and an explicitly
injected visual pose clock. They demonstrate rendering and layout, never the
pending boss mechanics, encounter balance, rewards or quest progression.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from functools import lru_cache
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUTPUT = ROOT/'docs/reviews/vespermaw_combat'
ART = ROOT/'assets/combat/vespermaw'
STATES = ('idle', 'prowl', 'raking_claw', 'confluence_roar', 'gather_resonance',
          'charged_hold', 'ruinous_pounce', 'exhausted', 'hurt', 'defeat')
SOURCE_FILES = ('tools/capture_vespermaw_combat.py', 'tools/build_vespermaw_combat.py',
                'battle_scene.py', 'battle_model.py', 'bestiary.py', 'enemy_combat_design.py',
                'battle_choreography.py', 'battle_action_fx.py', 'combat_motion_art.py',
                'mira_combat_art.py', 'battle_announcements.py', 'enemy_charge_aura.py',
                'cave_battlefield.py', 'ui_style.py', 'leveling.py', 'character_attributes.py',
                'assets/combat/bestiary.json', 'assets/combat/actions.json',
                'assets/combat/guests.json', 'assets/characters/level_growth.json',
                'assets/characters/attributes.json')
SOURCE_FOLDERS = ('assets/combat/vespermaw', 'assets/source/combat/vespermaw',
                  'assets/combat/cave_depths', 'assets/combat/caelan',
                  'assets/combat/lucan', 'assets/combat/mira', 'assets/ui/fonts')
FPS = 30


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_hashes():
    names = set(SOURCE_FILES)
    for folder in SOURCE_FOLDERS:
        names.update(path.relative_to(ROOT).as_posix() for path in (ROOT/folder).rglob('*')
                     if path.is_file())
    return {name: digest(ROOT/name) for name in sorted(names)}


@lru_cache(maxsize=16)
def font(size, bold=False):
    from PIL import ImageFont
    name = 'AtkinsonHyperlegible-Bold.ttf' if bold else 'AtkinsonHyperlegible-Regular.ttf'
    return ImageFont.truetype(str(ROOT/'assets/ui/fonts'/name), size)


def selected_frame(animation, milliseconds, *, review_repeat=False):
    durations = [frame['duration_ms'] for frame in animation['frames']]
    total = sum(durations)
    time = max(0, milliseconds)
    if animation['loop']:time %= total
    elif review_repeat:time %= total+250
    time = min(time, total-1)
    for index, duration in enumerate(durations):
        if time < duration:return index
        time -= duration
    return len(durations)-1


def sprite_board(output, manifest):
    """Show every state simultaneously; source frames are never redrawn."""
    from PIL import Image, ImageDraw
    animations = manifest['animations']
    assert set(STATES) <= set(animations)
    images = {state: [Image.open(ART/record['file']).convert('RGBA')
                      for record in animations[state]['frames']] for state in STATES}
    records = {state: {'frames': len(images[state]),
                      'unique_frames': len({image.tobytes() for image in images[state]}),
                      'duration_ms': sum(frame['duration_ms'] for frame in animations[state]['frames']),
                      'loop': animations[state]['loop']}
               for state in STATES}
    seen = {state: set() for state in STATES}
    columns, tile_width, tile_height = 5, 350, 345
    native_width, native_height = manifest['canvas']
    size = (columns*tile_width, 92+2*tile_height+34)

    def board(milliseconds=None):
        image = Image.new('RGB', size, '#102722')
        draw = ImageDraw.Draw(image)
        draw.text((24, 12), 'Vespermaw — combat sprite animation review',
                  font=font(28, True), fill='#efd38c')
        draw.text((24, 49), 'Retained native frames at 2× · actual manifest clocks · all ten states',
                  font=font(19), fill='#bed0c2')
        for index, state in enumerate(STATES):
            left, top = index % columns*tile_width, 92+index//columns*tile_height
            draw.rounded_rectangle((left+6, top, left+tile_width-6, top+tile_height-8),
                                   radius=8, fill='#19382f', outline='#5c7052')
            draw.text((left+17, top+8), state.replace('_', ' ').title(),
                      font=font(19, True), fill='#f0d58d')
            animation = animations[state]
            selected = (animation.get('contact_ms', records[state]['duration_ms']//2)
                        if milliseconds is None else milliseconds)
            frame_index = selected_frame(animation, selected, review_repeat=milliseconds is not None)
            if milliseconds is not None:seen[state].add(frame_index)
            frame = images[state][frame_index]
            sprite = frame.resize((native_width*2, native_height*2), Image.Resampling.NEAREST)
            x = left+(tile_width-sprite.width)//2
            y = top+34
            floor = y+manifest['anchor'][1]*2
            draw.line((left+15, floor, left+tile_width-15, floor), fill='#294b3e')
            image.paste(sprite, (x, y), sprite)
            detail = records[state]
            label = f"{detail['frames']} frames · {detail['duration_ms']} ms"
            draw.text((left+17, top+tile_height-29), label, font=font(16), fill='#bed0c2')
        draw.text((24, size[1]-28),
                  'Non-looping actions repeat for inspection; boss behavior remains pending.',
                  font=font(17), fill='#bed0c2')
        return image

    board().save(output/'sprite_contact_sheet.png')
    duration = max(record['duration_ms'] for record in records.values())+500
    # One review palette avoids false color flicker between independently
    # quantized GIF frames; production sprite pixels already share a palette.
    palette = board(0).quantize(colors=256, method=Image.Quantize.MEDIANCUT,
                               dither=Image.Dither.NONE)
    pictures = [board(time).quantize(palette=palette, dither=Image.Dither.NONE)
                for time in range(0, duration, 20)]
    pictures[0].save(output/'sprite_animations.gif', save_all=True,
                     append_images=pictures[1:], duration=20, loop=0, disposal=1, optimize=True)
    for state in STATES:
        records[state]['previewed_frames'] = len(seen[state])
        assert len(seen[state]) == records[state]['frames'], (state, seen[state])
    assert sum(record['frames'] for record in records.values()) == manifest['authored_frames']
    return records


def visual_fixture(size=(960, 640), text_scale=1):
    """Use production renderer/UI, isolated rule model and no persistent Game."""
    import pygame
    from audio_settings import AudioSettings
    from battle_model import BattleModel
    from battle_scene import BattleScene
    from character_attributes import CharacterAttributes
    from inventory import Inventory
    from leveling import character_stats
    from ui_style import UIStyle

    pygame.display.init();pygame.font.init()
    game = SimpleNamespace(window=pygame.display.set_mode(size), ui_surface=pygame.Surface(size),
                           audio=AudioSettings(), inventory=Inventory(), attributes=CharacterAttributes())
    game.audio.set_music(0);game.audio.set_effects(0);game.audio.set_text_scale(text_scale)
    game.ui = UIStyle(game)
    game.to_canvas = lambda point: (point[0]*480/size[0], point[1]*320/size[1])
    members = []
    for identifier, name in (('player', 'Caelan'), ('mira', 'Mira'), ('lucan', 'Lucan')):
        stats = character_stats('caelan' if identifier == 'player' else identifier, 7)
        members.append({'identifier': identifier, 'name': name, 'attributes': stats,
                        'hp': stats['hp'], 'mp': stats['mp'],
                        'attack': 'bolt_shot' if identifier == 'mira' else 'attack'})
    # Never instantiate the pending canonical boss: ordinary Bat mechanics are
    # used only as the production renderer's model-shaped visual fixture.
    model = BattleModel(game.attributes, party_members=members)
    model.enemy.name = 'Vespermaw'
    model.enemy_sprite_id = 'vespermaw'
    scene = BattleScene(game, model, battlefield='cave_depths')
    return game, model, scene, pygame.Surface((480, 320))


def bordered(surface, state, *, minimum=False):
    import pygame
    from PIL import Image, ImageDraw
    image = Image.new('RGB', (surface.get_width(), surface.get_height()+76), '#102722')
    image.paste(Image.frombytes('RGB', surface.get_size(), pygame.image.tobytes(surface, 'RGB')), (0, 40))
    draw = ImageDraw.Draw(image)
    draw.text((12, 8), 'Vespermaw · '+state.replace('_', ' '),
              font=font(18 if minimum else 23, True), fill='#efd38c')
    draw.text((12, image.height-27),
              'Art-only pose fixture · boss mechanics pending' if minimum else
              'Production cave BattleScene · injected visual pose clock · ordinary Bat rule fixture',
              font=font(13 if minimum else 16), fill='#bed0c2')
    return image


def battle_previews(output, manifest):
    import pygame
    from PIL import Image, ImageDraw

    game, model, scene, canvas = visual_fixture()
    before = (deepcopy(model.enemy.attributes), (model.enemy.hp, model.enemy.mp),
              [(actor.hp, actor.mp) for actor in model.party])
    pose = ['idle', 0]
    original_pose = scene._pose
    captures, timeline, offset = [], [], 0
    size = (960, 716)
    command = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pixel_format', 'rgb24',
               '-video_size', f'{size[0]}x{size[1]}', '-framerate', str(FPS), '-i', '-',
               '-an', '-c:v', 'libx264', '-preset', 'fast', '-crf', '18', '-pix_fmt', 'yuv420p',
               '-movflags', '+faststart', str(output/'cave_art_reel_silent.mp4')]
    encoder = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

    def sample(actor):
        return tuple(pose) if actor == 'enemy' else original_pose(actor)

    try:
        with patch.object(scene, '_pose', sample):
            for state in STATES:
                animation = manifest['animations'][state]
                duration = sum(frame['duration_ms'] for frame in animation['frames'])
                count = math.ceil(duration/1000*FPS)
                timeline.append({'state': state, 'start_seconds': offset/FPS,
                                 'duration_seconds': count/FPS, 'manifest_duration_ms': duration})
                saved = False
                representative = animation.get('contact_ms', duration//2)
                for index in range(count):
                    pose[:] = state, min(duration-1, index*1000/FPS)
                    scene._elapsed = (offset+index)/FPS
                    scene.draw(canvas, game.ui_surface)
                    image = bordered(game.ui_surface, state)
                    encoder.stdin.write(image.tobytes())
                    if not saved and pose[1] >= representative:
                        name = 'battle_'+state+'.png';image.save(output/name)
                        captures.append({'state': state, 'file': name, 'pose_ms': pose[1],
                                         'actor_scale': scene._actor_scale('enemy')})
                        saved = True
                offset += count
        encoder.stdin.close()
        error = encoder.stderr.read().decode()
        assert encoder.wait() == 0, error
    except BaseException:
        encoder.kill();encoder.wait();raise
    assert before == (deepcopy(model.enemy.attributes), (model.enemy.hp, model.enemy.mp),
                      [(actor.hp, actor.mp) for actor in model.party])
    assert model.phase == 'charging', 'The visual review must not simulate or settle a boss fight'

    # Inspect native-resolution accessibility layout using the production UI.
    game, model, scene, canvas = visual_fixture((480, 320), 1.5)
    original_pose = scene._pose
    for state in ('idle', 'confluence_roar', 'ruinous_pounce', 'defeat'):
        animation = manifest['animations'][state]
        milliseconds = animation.get('contact_ms', sum(frame['duration_ms'] for frame in animation['frames'])//2)
        with patch.object(scene, '_pose', lambda actor, s=state, t=milliseconds:
                          (s, t) if actor == 'enemy' else original_pose(actor)):
            scene.draw(canvas, game.ui_surface)
            bordered(game.ui_surface, state, minimum=True).save(output/('native_large_text_'+state+'.png'))
    sheet = Image.new('RGB', (960, 764), '#102722')
    draw = ImageDraw.Draw(sheet)
    draw.text((16, 8), 'Vespermaw — production cave renderer, art-only fixtures',
              font=font(22, True), fill='#efd38c')
    for index, state in enumerate(('idle', 'confluence_roar', 'ruinous_pounce', 'defeat')):
        image = Image.open(output/('battle_'+state+'.png')).convert('RGB')
        image = image.resize((480, 358), Image.Resampling.NEAREST)
        sheet.paste(image, (index % 2*480, 40+index//2*358))
    sheet.save(output/'battle_contact_sheet.png')
    pygame.quit()
    return {'fps': FPS, 'frames': offset, 'seconds': offset/FPS, 'size': list(size),
            'clips': timeline, 'captures': captures, 'resources_unchanged': True,
            'boss_mechanics_simulated': False, 'minimum_viewport': [480, 320], 'large_text': 1.5}


def check(output):
    output = Path(output)
    report = json.loads((output/'verification.json').read_text())
    assert report['source_sha256'] == source_hashes(), 'Production sources changed; recapture.'
    for filename, expected in report['artifact_sha256'].items():
        assert digest(output/filename) == expected, filename
    for state in STATES:
        row = report['animations'][state]
        assert row['previewed_frames'] == row['frames'] == row['unique_frames'], state
    assert report['no_user_save_or_settings_files']
    assert report['video']['resources_unchanged'] and not report['video']['boss_mechanics_simulated']
    print('Vespermaw sprites, cave art-only fixtures and retained provenance verified.')
    return report


def capture(output):
    output = Path(output);output.mkdir(parents=True, exist_ok=True)
    before = source_hashes()
    manifest = json.loads((ART/'animation.json').read_text())
    animations = sprite_board(output, manifest)
    video = battle_previews(output, manifest)
    assert before == source_hashes(), 'Sources changed during capture; rerun after the art is frozen.'
    readme = '''# Vespermaw combat art review

[Animated sprite board](sprite_animations.gif) · [Sprite contact sheet](sprite_contact_sheet.png)
· [Silent cave art reel](cave_art_reel_silent.mp4) · [Cave contact sheet](battle_contact_sheet.png)

The sprite board displays every retained state at twice its native pixel size.
It samples the actual animation manifest clock at 50 FPS; non-looping actions
repeat for inspection after a short final-pose hold. Each individual exported
pose appears in the board, and verification records frame counts and durations.

The cave reel renders the same poses through the production BattleScene at
their manifest clocks. This is an explicitly visual-only fixture: it uses
ordinary Bat rules with Vespermaw's name and art, a copied level-seven party,
and a directly sampled enemy pose clock. It does not run Vespermaw's pending
party-wide damage, marked-target response rules or recovery vulnerability.
Its HP/ATB bars are fixture UI, not a boss balance demonstration.

Separate native 480×320 captures use 150% text. No Game instance or user save,
settings, inventory, quest or reward settlement is involved. The boss remains
excluded from random encounters and its canonical combat implementation gate
remains in place.

Reproduce with `python tools/capture_vespermaw_combat.py`; verify with
`python tools/capture_vespermaw_combat.py --check`. Use `--output /tmp/vespermaw-review`
for disposable alternative captures.
'''
    (output/'README.md').write_text(readme)
    artifacts = {path.name: digest(path) for path in sorted(output.iterdir())
                 if path.is_file() and path.name != 'verification.json'}
    report = {'version': 1, 'source_sha256': before, 'artifact_sha256': artifacts,
              'animations': animations, 'video': video,
              'authored_frames': manifest['authored_frames'],
              'no_user_save_or_settings_files': True,
              'fixture': 'Ordinary Bat model, Vespermaw art/name, directly sampled visual poses; no boss mechanics.'}
    (output/'verification.json').write_text(json.dumps(report, indent=2)+'\n')
    return check(output)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    parser.add_argument('--check', action='store_true')
    arguments = parser.parse_args(argv)
    return check(arguments.output) if arguments.check else capture(arguments.output)


if __name__ == '__main__':main()
