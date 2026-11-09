"""Preview the two Sanctuary cave enemies without placing world encounters.

The sprite board samples retained native frames directly. The battle reel uses
real Game/BattleScene encounters, ordinary Guard/Attack mouse input and live ATB.
Charging waits and repeated actions are omitted from the reel; included actions
play at their original timing. Disposable character profiles supply review-only
HP endurance so every action and both MP fallbacks can be observed safely.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from functools import lru_cache
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile
from unittest.mock import patch

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUTPUT = ROOT/'docs/reviews/cave_enemy_combat'
ACTORS = ('lithrusk', 'veylume')
PREFERRED_STATES = {
    'lithrusk': ('idle', 'walk', 'claw_clamp', 'shell_bash', 'hurt', 'defeat'),
    'veylume': ('idle', 'fly', 'static_spark', 'gather_charge', 'charged_hold',
                'veinflash', 'hurt', 'defeat'),
}
FPS = 30
VIDEO_SIZE = (960, 704)
SOURCE_FILES = (
    'main.py', 'bestiary.py', 'battle_model.py', 'battle_scene.py',
    'battle_action_fx.py', 'battle_action_audio.py', 'battle_choreography.py',
    'combat_motion_art.py', 'combat_damage.py', 'enemy_growth.py', 'leveling.py',
    'character_attributes.py', 'ui_style.py', 'gearblade_art.py', 'gearblade_fx.py',
    'assets/combat/bestiary.json', 'assets/combat/actions.json',
    'assets/combat/enemy_archetypes.json', 'assets/combat/caelan_choreography.json',
    'assets/characters/level_growth.json', 'assets/characters/attributes.json',
    'assets/ui/fonts/AtkinsonHyperlegible-Regular.ttf',
    'assets/ui/fonts/AtkinsonHyperlegible-Bold.ttf', 'assets/ui/fonts/DejaVuSans.ttf',
    'assets/ui/fonts/DejaVuSerif.ttf',
    'tools/build_lithrusk_combat.py', 'tools/build_veylume_combat.py',
    'tools/capture_cave_enemy_combat.py',
)
ART_FOLDERS = (
    'assets/combat/lithrusk', 'assets/combat/veylume', 'assets/combat/caelan',
    'assets/combat/caelan_motion', 'assets/combat/eldenmere',
)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_hashes():
    names = {name for name in SOURCE_FILES if (ROOT/name).is_file()}
    for folder in ART_FOLDERS:
        names.update(path.relative_to(ROOT).as_posix() for path in (ROOT/folder).rglob('*')
                     if path.is_file())
    for actor in ACTORS:
        for source in (ROOT/'assets/source/combat').glob(actor+'*'):
            if source.is_file():names.add(source.relative_to(ROOT).as_posix())
            else:
                names.update(path.relative_to(ROOT).as_posix() for path in source.rglob('*')
                             if path.is_file())
    # Species choreography/effects can live in small dedicated runtime modules.
    for pattern in ('*enemy*combat*.py', '*cave*enemy*.py'):
        names.update(path.relative_to(ROOT).as_posix() for path in ROOT.glob(pattern)
                     if path.is_file())
    return {name: digest(ROOT/name) for name in sorted(names)}


@lru_cache(maxsize=16)
def font(size, bold=False):
    from PIL import ImageFont
    name = 'AtkinsonHyperlegible-Bold.ttf' if bold else 'AtkinsonHyperlegible-Regular.ttf'
    return ImageFont.truetype(str(ROOT/'assets/ui/fonts'/name), size)


def manifests():
    return {actor: json.loads((ROOT/'assets/combat'/actor/'animation.json').read_text())
            for actor in ACTORS}


def canonical_states(actor, data):
    """Keep all authored states, omitting only duplicate generic aliases."""
    names = [name for name in PREFERRED_STATES[actor] if name in data['animations']]
    signatures = {tuple((frame['file'], frame['duration_ms']) for frame in
                        data['animations'][name]['frames']) for name in names}
    for name, animation in data['animations'].items():
        signature = tuple((frame['file'], frame['duration_ms']) for frame in animation['frames'])
        if name not in names and signature not in signatures:
            names.append(name);signatures.add(signature)
    return names


def sprite_board(output):
    """Display every requested state simultaneously, with unmodified frame art."""
    from PIL import Image, ImageDraw
    banks = manifests()
    frame_images = {}
    rows = {}
    sampled_frames = {}
    states = {actor: canonical_states(actor, banks[actor]) for actor in ACTORS}
    for actor in ACTORS:
        data = banks[actor]
        for state in states[actor]:
            animation = data['animations'][state]
            frames = [(Image.open(ROOT/'assets/combat'/actor/frame['file']).convert('RGBA'),
                       frame['duration_ms']) for frame in animation['frames']]
            assert frames and all(image.size == tuple(data['canvas']) for image, _ in frames)
            frame_images[actor, state] = frames
            sampled_frames[actor, state] = set()
            rows[actor+':'+state] = {
                'frames': len(frames),
                'unique_frames': len({image.tobytes() for image, _ in frames}),
                'duration_ms': sum(duration for _, duration in frames),
                'loop': animation['loop'],
            }
    width = 1024
    tiles, spare = [], []
    row_count = max((len(states[actor])+1)//2 for actor in ACTORS)
    for actor_index, actor in enumerate(ACTORS):
        tiles.extend((actor, state, column+actor_index*2, row)
                     for index, state in enumerate(states[actor])
                     for row, column in (divmod(index, 2),))
        spare.extend((actor, index % 2+actor_index*2, index//2)
                     for index in range(len(states[actor]), row_count*2))
    height = 82+row_count*254+30

    def board(milliseconds=None):
        image = Image.new('RGB', (width, height), '#102722')
        draw = ImageDraw.Draw(image)
        draw.text((24, 13), 'Sanctuary cave — combat animation review',
                  font=font(26, True), fill='#efd38c')
        draw.text((24, 46), 'Native pixel frames at 2× · every state shown · action tiles repeat for review',
                  font=font(17), fill='#b7c9bd')
        for actor, state, column, row in tiles:
            left, top = column*256, 82+row*254
            draw.rounded_rectangle((left+7, top, left+249, top+246), radius=9,
                                   fill='#19382f', outline='#5c7052', width=1)
            title = actor.title()+' · '+state.replace('_', ' ')
            draw.text((left+16, top+7), title, font=font(16, True), fill='#f0d58d')
            frames = frame_images[actor, state]
            elapsed = (sum(duration for _, duration in frames)//2 if milliseconds is None
                       else milliseconds % (sum(duration for _, duration in frames)+280))
            selected = frames[-1][0]
            selected_index = len(frames)-1
            for frame_index, (source, duration) in enumerate(frames):
                if elapsed < duration:
                    selected = source
                    selected_index = frame_index
                    break
                elapsed -= duration
            if milliseconds is not None:sampled_frames[actor, state].add(selected_index)
            sprite = selected.resize((selected.width*2, selected.height*2), Image.Resampling.NEAREST)
            image.paste(sprite, (left+(256-sprite.width)//2, top+29+(204-sprite.height)//2), sprite)
            record = rows[actor+':'+state]
            draw.text((left+16, top+226),
                      str(record['frames'])+' frames · '+str(record['duration_ms'])+' ms',
                      font=font(15), fill='#bacdbd')
        # The unused cells identify the source and make the species split clear.
        for actor, column, row in spare:
            left, top = column*256+16, 82+row*254+65
            if actor == 'lithrusk' and column == 0:
                lines = ('LITHRUSK', 'Ground · Armored', 'Weighty limestone plates', 'Articulated claws and feet')
            elif actor == 'lithrusk':
                lines = ('Original authored poses', 'Fixed native pixel scale', 'Stable ground anchor', 'Real combat timings')
            else:
                lines = ('VEYLUME', 'Electric · Caster', 'Luminous wing veins', 'Sparks, charge and release')
            for index, line in enumerate(lines):
                draw.text((left, top+index*25), line, font=font(16, index == 0),
                          fill='#efd38c' if index == 0 else '#b7c9bd')
        draw.text((24, height-27), 'Sprite showcase only; the battle reel below uses the real ATB controller.',
                  font=font(16), fill='#b7c9bd')
        return image

    board().save(output/'sprite_contact_sheet.png')
    pictures = [board(time).quantize(colors=256, method=Image.Quantize.FASTOCTREE,
                                    dither=Image.Dither.NONE)
                for time in range(0, 3200, 20)]
    pictures[0].save(output/'sprite_animations.gif', save_all=True,
                     append_images=pictures[1:], duration=20, loop=0,
                     disposal=2, optimize=False)
    for (actor, state), indices in sampled_frames.items():
        rows[actor+':'+state]['previewed_frame_count'] = len(indices)
        assert len(indices) == rows[actor+':'+state]['frames'], (actor, state, indices)
    return rows


class Reel:
    def __init__(self, output):
        self.output = output
        self.clips = []
        self.captures = []

    def image(self, surface, title, detail):
        import pygame
        from PIL import Image, ImageDraw
        image = Image.new('RGB', VIDEO_SIZE, '#102722')
        game = Image.frombytes('RGB', surface.get_size(), pygame.image.tobytes(surface, 'RGB'))
        image.paste(game, (0, 40))
        draw = ImageDraw.Draw(image)
        draw.text((18, 6), title, font=font(23, True), fill='#efd38c')
        draw.text((18, 681), detail, font=font(15), fill='#bed0c2')
        return image

    def add(self, frames, reason):
        if not frames:return
        # Keep a long real-ATB observation inexpensive without resampling its
        # pixels: screenshots compress far better than full RGB image objects.
        pictures = []
        for image in frames:
            stream = BytesIO()
            image.save(stream, format='PNG', compress_level=3)
            pictures.append(stream.getvalue())
        self.clips.append({'reason': reason, 'frames': pictures})

    def snapshot(self, actor, state, image, **metadata):
        name = actor+'_'+state+'.png'
        if any(record['file'] == name for record in self.captures):return
        image.save(self.output/name)
        self.captures.append({'file': name, 'actor': actor, 'state': state, **metadata})

    def encode(self):
        from PIL import Image, ImageDraw
        path = self.output/'combat_reel_silent.mp4'
        command = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pixel_format',
                   'rgb24', '-video_size', f'{VIDEO_SIZE[0]}x{VIDEO_SIZE[1]}',
                   '-framerate', str(FPS), '-i', '-', '-an', '-c:v', 'libx264',
                   '-preset', 'fast', '-crf', '18', '-pix_fmt', 'yuv420p',
                   '-movflags', '+faststart', str(path)]
        encoder = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        timeline, offset = [], 0
        for clip in self.clips:
            timeline.append({'start_seconds': round(offset/FPS, 3),
                             'duration_seconds': round(len(clip['frames'])/FPS, 3),
                             'reason': clip['reason']})
            for encoded in clip['frames']:
                with Image.open(BytesIO(encoded)) as image:
                    encoder.stdin.write(image.convert('RGB').tobytes())
            offset += len(clip['frames'])
        encoder.stdin.close()
        error = encoder.stderr.read().decode()
        assert encoder.wait() == 0, error
        # Four representative real BattleScene moments, separate from the sprite atlas.
        selection = []
        for actor, states in (('lithrusk', ('claw_clamp', 'shell_bash')),
                              ('veylume', ('gather_charge', 'veinflash'))):
            for state in states:
                record = next(item for item in self.captures
                              if item['actor'] == actor and item['state'] == state)
                selection.append(record)
        sheet = Image.new('RGB', (960, 744), '#102722')
        draw = ImageDraw.Draw(sheet)
        draw.text((16, 7), 'Real ATB combat — existing Eldenmere review stage',
                  font=font(22, True), fill='#efd38c')
        for index, record in enumerate(selection):
            image = Image.open(self.output/record['file']).convert('RGB')
            image = image.resize((480, 352), Image.Resampling.NEAREST)
            sheet.paste(image, (index % 2*480, 40+index//2*352))
        sheet.save(self.output/'battle_contact_sheet.png')
        return {'fps': FPS, 'frames': offset, 'seconds': round(offset/FPS, 3),
                'size': list(VIDEO_SIZE), 'clips': timeline}


def battle_reel(output):
    import pygame
    from battle_model import BattleModel
    from battle_scene import BattleScene
    from character_attributes import CharacterAttributes
    from leveling import character_stats
    from main import Game

    reel = Reel(output)
    records = []
    with tempfile.TemporaryDirectory(prefix='cave-enemy-review-') as directory:
        work = Path(directory)
        game = Game(window_size=(960, 640), fullscreen=False, start_on_title=False,
                    save_path=None, settings_path=work/'settings.json')
        game.audio.set_music(0);game.audio.set_effects(0)
        game.opening.restore({'version': 1, 'stage': 'disabled'})
        persistent = deepcopy(game.attributes.to_dict())
        pygame.event.clear()

        def render(scene, actor, detail):
            game._ensure_ui_surface()
            scene.draw(game.canvas, game.ui_surface)
            return reel.image(game.ui_surface, actor.title()+' — combat animation review', detail)

        def command(scene, name):
            scene.draw(game.canvas, game.ui_surface)
            point = scene.command_rects[name].center
            for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
                scene.handle_event(pygame.event.Event(kind, button=1, pos=(point[0]*2, point[1]*2)))

        for actor, level, guard_turns in (('lithrusk', 3, 4), ('veylume', 4, 9)):
            catalog = deepcopy(CharacterAttributes().catalog)
            stats = character_stats('caelan', level)
            stats['hp'] = 9999  # Initial disposable endurance fixture, never persistent data.
            catalog['characters']['caelan']['attributes'] = stats
            source = CharacterAttributes('caelan', catalog)
            source_before = deepcopy(source.to_dict())
            model = BattleModel.from_bestiary(source, actor, level, rng=random.Random(17))
            scene = BattleScene(game, model, battlefield='eldenmere')
            events, calls, enemy_actions = [], set(), []
            current = None
            buffer = []
            enemy_seen = set()
            player_attack_seen = False
            mp_fallback_seen = False
            hold_seen = False
            charged_hold = []
            intro, outro = [], []
            original_frame = scene.sprites.frame
            original_drain = model.drain_events

            def frame(sprite, state, elapsed):
                if sprite == actor:calls.add(state)
                return original_frame(sprite, state, elapsed)

            def drain():
                batch = original_drain();events.extend(deepcopy(batch));return batch

            def finish_action(action):
                nonlocal player_attack_seen, mp_fallback_seen
                if action is None or not buffer:return
                if action.actor == 'enemy':
                    is_fallback = (actor == 'veylume' and action.action == 'veylume_static_spark'
                                   and sum(item['action'] == 'veylume_veinflash'
                                           for item in enemy_actions) >= 2)
                    if action.action not in enemy_seen:
                        reel.add(list(buffer), actor+' '+action.action)
                        enemy_seen.add(action.action)
                    elif is_fallback and not mp_fallback_seen:
                        reel.add(list(buffer), actor+' free Spark after MP depletion')
                        mp_fallback_seen = True
                elif action.action == 'attack' and (not player_attack_seen or model.enemy.hp <= 0):
                    reel.add(list(buffer), actor+' receives '+('lethal hit' if model.enemy.hp <= 0 else 'hit'))
                    player_attack_seen = True

            with patch.object(scene.sprites, 'frame', frame), patch.object(model, 'drain_events', drain):
                for tick in range(24000):
                    if model.waiting_for_player:
                        command(scene, 'guard' if len(enemy_actions) < guard_turns else 'attack')
                    scene.update(1/FPS)
                    action = model.current_action
                    if action is not current:
                        finish_action(current)
                        buffer = []
                        current = action
                        if action is not None and action.actor == 'enemy':
                            enemy_actions.append({'action': action.action, 'mp': model.enemy.mp,
                                                  'target': action.target,
                                                  'time': round(scene._elapsed, 4)})
                    detail = ('Existing Eldenmere review stage · real ATB · charging waits omitted')
                    if action is not None:
                        detail = (model.actions[action.action]['name']+' · '+action.actor+
                                  ' · enemy MP '+str(model.enemy.mp)+'/'+str(model.enemy.max_mp))
                    need_hold = (actor == 'veylume' and not hold_seen
                                 and scene._pose('enemy')[0] == 'charged_hold')
                    if action is None and len(intro) >= FPS and model.enemy.hp > 0 and not need_hold:
                        continue  # Only charging waits are omitted; simulation still advances normally.
                    image = render(scene, actor, detail)
                    if need_hold:
                        charged_hold.append(image)
                        if len(charged_hold) == FPS:
                            reel.add(charged_hold, actor+' charged hold between ATB turns')
                            reel.snapshot(actor, 'charged_hold', charged_hold[len(charged_hold)//2],
                                          enemy_mp=model.enemy.mp, target=model.telegraphed_target)
                            hold_seen = True
                    if len(intro) < FPS:
                        intro.append(image)
                        if len(intro) == FPS:reel.add(list(intro), actor+' idle')
                    if action is not None:
                        buffer.append(image)
                        if action.actor == 'enemy' and action.elapsed >= action.impact_at:
                            state = action.action.removeprefix(actor+'_')
                            reel.snapshot(actor, state, image, action=action.action,
                                          elapsed=action.elapsed, enemy_mp=model.enemy.mp,
                                          enemy_hp=model.enemy.hp, target=action.target)
                    if model.enemy.hp <= 0:
                        outro.append(image)
                    if model.ended:
                        finish_action(current)
                        for _ in range(round(1.5*FPS)):
                            scene.update(1/FPS)
                            image = render(scene, actor, 'Defeat · production animation, held on its final frame')
                            outro.append(image)
                        reel.add(outro, actor+' defeat')
                        reel.snapshot(actor, 'defeat', outro[len(outro)//2], enemy_hp=model.enemy.hp)
                        break
                else:raise AssertionError('Real ATB review did not finish for '+actor)
            assert model.phase == 'victory', (actor, model.phase)
            assert source.to_dict() == source_before
            if actor == 'veylume':
                assert sum(item['action'] == 'veylume_veinflash' for item in enemy_actions) == 2
                assert mp_fallback_seen, 'MP depletion fallback was not recorded'
                assert hold_seen, 'Charged hold between ATB turns was not recorded'
            records.append({'actor': actor, 'level': level, 'enemy_actions': enemy_actions,
                            'events': events, 'states_seen': sorted(calls), 'outcome': model.phase,
                            'source_character_unchanged': True, 'simulation_seconds': round(scene._elapsed, 3)})
        assert game.attributes.to_dict() == persistent
        pygame.quit()
    return reel.encode(), records, reel.captures


def check(output):
    output = Path(output)
    report = json.loads((output/'verification.json').read_text())
    assert report['source_sha256'] == source_hashes(), 'Production sources changed; recapture.'
    for name, expected in report['artifact_sha256'].items():
        assert digest(output/name) == expected, name
    assert report['no_user_save_or_settings_files']
    assert report['persistent_attributes_unchanged']
    assert report['video']['seconds'] > 10
    for actor in ACTORS:
        record = next(item for item in report['encounters'] if item['actor'] == actor)
        assert record['outcome'] == 'victory' and record['source_character_unchanged']
        required = set(PREFERRED_STATES[actor])-{'walk', 'fly'}
        assert required <= set(record['states_seen']), (actor, record['states_seen'])
        for state in canonical_states(actor, manifests()[actor]):
            assert report['animations'][actor+':'+state]['unique_frames'] >= 8
            assert report['animations'][actor+':'+state]['previewed_frame_count'] == \
                report['animations'][actor+':'+state]['frames']
    moth = next(item for item in report['encounters'] if item['actor'] == 'veylume')
    names = [item['action'] for item in moth['enemy_actions']]
    cycle = ['veylume_static_spark', 'veylume_gather_charge', 'veylume_veinflash']
    assert names[:6] == cycle*2, names
    assert names.count('veylume_veinflash') == 2
    assert len(names) > 6 and set(names[6:]) == {'veylume_static_spark'}
    assert [item['mp'] for item in moth['enemy_actions']
            if item['action'] == 'veylume_veinflash'] == [7, 3]
    crawler = next(item for item in report['encounters'] if item['actor'] == 'lithrusk')
    assert [item['action'] for item in crawler['enemy_actions'][:4]] == [
        'lithrusk_claw_clamp', 'lithrusk_shell_bash']*2
    print('Cave enemy native sprite boards, real ATB reel and provenance verified.')
    return report


def capture(output):
    output = Path(output);output.mkdir(parents=True, exist_ok=True)
    before = source_hashes()
    animations = sprite_board(output)
    video, encounters, captures = battle_reel(output)
    assert before == source_hashes(), 'Production sources changed during capture.'
    readme = '''# Lithrusk and Veylume combat review

[Animated sprite board](sprite_animations.gif) · [Sprite contact sheet](sprite_contact_sheet.png)
· [Silent in-engine reel](combat_reel_silent.mp4) · [Battle contact sheet](battle_contact_sheet.png)

The sprite board displays every production state at two-times native pixel
size. Each tile repeats its state for inspection; frames come directly from the
retained species animation manifests. The PNG selects a representative pose.

The silent reel uses real Game/BattleScene encounters on the existing Eldenmere
review stage. Caelan uses normal Guard and Attack mouse commands, real ATB and
the approved same-level offensive stats. An initial copied profile grants
9,999 HP solely to sustain the review until both Veinflashes and the free
Static Spark fallback are seen. Included action clips run at their actual
timing; charging waits and repeated actions are omitted. Hurt and defeat result
from ordinary attacks. No battle phase, gauge, MP or animation clock is injected.

Temporary settings and in-memory saves isolate the review from player files.
No world encounters are placed, and no rewards or quest progress are settled.
This is a combat presentation review, not a cave walkthrough or encounter
balance demonstration. Elemental relationships remain authoring metadata.

Reproduce with `python tools/capture_cave_enemy_combat.py`; verify current
sources and retained artifacts with `python tools/capture_cave_enemy_combat.py --check`.
'''
    (output/'README.md').write_text(readme)
    artifacts = {path.name: digest(path) for path in sorted(output.iterdir())
                 if path.is_file() and path.name != 'verification.json'}
    report = {'version': 1, 'source_sha256': before, 'artifact_sha256': artifacts,
              'animations': animations, 'video': video, 'encounters': encounters,
              'captures': captures, 'no_user_save_or_settings_files': True,
              'persistent_attributes_unchanged': True,
              'fixtures': ['Real Game/BattleScene on Eldenmere review stage; no cave world encounters.',
                           'In-memory journey and disposable settings directory.',
                           'Initial same-level offensive stats with review-only 9999 HP endurance.',
                           'Real 30 FPS ATB and mouse Guard/Attack; no resource, gauge or pose injection.',
                           'Included actions remain real-time; repeated actions and charging waits omitted.']}
    (output/'verification.json').write_text(json.dumps(report, indent=2)+'\n')
    check(output)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args(argv)
    return check(args.output) if args.check else capture(args.output)


if __name__ == '__main__':main()
