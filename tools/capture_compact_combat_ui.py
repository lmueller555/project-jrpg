"""Reproduce compact combat UI review pixels with production rendering and inputs.

The before renderer is loaded from BASELINE with its real repository asset root.
Both stills use independently constructed, identical PartyState/BattleModel
fixtures. No saved journey or settings are read or written. The silent reel uses
real ATB, action clocks, mouse/keyboard handling, damage and bot haste durations.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import io
import json
import math
import os
from pathlib import Path
import random
import re
import subprocess
import sys
from types import ModuleType, SimpleNamespace

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pygame
from PIL import Image, ImageDraw, ImageFont

from audio_settings import AudioSettings
from battle_model import BattleModel, ENEMY_PATH
from battle_scene import BattleScene
from character_attributes import CharacterAttributes
from party_state import PartyState
from ui_style import UIStyle

BASELINE = 'f5c2203010fbfd7a4c17c475a654ef8004edd8ed'
FPS = 20
SIZE = (960, 640)
OUTPUT = ROOT/'docs/reviews/compact_combat_ui'
RESOURCES = {'caelan': (103, 11), 'mira': (177, 13), 'lucan': (97, 4)}
BOT_HUD = re.compile(r'^Rivet ATB$|^Haste\s*[·•:]\s*\d+$')
UNCHANGED_CONTRACT = ('battle_model.py', 'party_state.py', 'character_attributes.py',
                      'gear_state.py', 'gear_widget.py', 'assets/combat/actions.json',
                      'assets/combat/bots.json', 'assets/combat/guests.json',
                      'assets/combat/enemies.json')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fingerprints():
    sources = ('audio_settings.py', 'battle_action_audio.py', 'battle_action_fx.py',
               'battle_choreography.py', 'battle_model.py', 'battle_scene.py',
               'character_attributes.py', 'combat_damage.py', 'combat_motion_art.py',
               'gear_state.py', 'gear_widget.py', 'gearblade_art.py', 'gearblade_fx.py',
               'mira_combat_art.py', 'party_state.py', 'ui_style.py',
               'tools/capture_compact_combat_ui.py', 'assets/characters/attributes.json',
               'assets/characters/party.json')
    paths = [ROOT/name for name in sources]
    for directory in ('assets/combat', 'assets/story/gearblade_focus', 'assets/ui/fonts'):
        paths.extend(path for path in (ROOT/directory).rglob('*') if path.is_file())
    return {str(path.relative_to(ROOT)): digest(path) for path in sorted(set(paths))}


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2)+'\n')


def baseline_scene():
    source = subprocess.check_output(['git', 'show', BASELINE+':battle_scene.py'], cwd=ROOT)
    module = ModuleType('_compact_review_baseline_battle_scene')
    module.__file__ = str(ROOT/'battle_scene.py')
    sys.modules[module.__name__] = module
    exec(compile(source, module.__file__, 'exec'), module.__dict__)
    return module.BattleScene, hashlib.sha256(source).hexdigest()


def unchanged_model_state():
    """Before/after differences must come from the renderer, not battle rules."""
    hashes = {}
    for name in UNCHANGED_CONTRACT:
        source = subprocess.check_output(['git', 'show', BASELINE+':'+name], cwd=ROOT)
        hashes[name] = hashlib.sha256(source).hexdigest()
        assert digest(ROOT/name) == hashes[name], f'Baseline model/state changed: {name}'
    return hashes


class RecordingPainter:
    """Observe actual text sent to the renderer without changing any pixels."""
    def __init__(self, painter, texts):
        self.painter, self.texts = painter, texts

    def __getattr__(self, name):
        return getattr(self.painter, name)

    def text(self, value, *args, **kwargs):
        self.texts.append(str(value))
        return self.painter.text(value, *args, **kwargs)


class Capture:
    def __init__(self, output):
        self.output = output
        output.mkdir(parents=True, exist_ok=True)
        pygame.init()
        self.game = SimpleNamespace(window=pygame.display.set_mode(SIZE),
                                    ui_surface=pygame.Surface(SIZE),
                                    attributes=CharacterAttributes(), audio=AudioSettings())
        self.game.audio.set_music(0)
        self.game.audio.set_effects(0)
        self.game.ui = UIStyle(self.game)
        painter = self.game.ui.painter
        self.game.ui.painter = lambda surface: RecordingPainter(painter(surface), self.texts)
        self.game.to_canvas = lambda point: (point[0]*480/self.game.window.get_width(),
                                            point[1]*320/self.game.window.get_height())
        self.canvas = pygame.Surface((480, 320))
        self.texts = []
        self.shots, self.inputs, self.events, self.stages = [], [], [], []
        self.frames = 0
        self.simulated = 0.
        self.encoder = None
        self.recording = False
        self.no_bot_hud_draws = 0

    def viewport(self, size=SIZE, text_scale=1.):
        self.game.window = pygame.display.set_mode(size)
        self.game.ui_surface = pygame.Surface(size)
        self.game.audio.set_text_scale(text_scale)

    def make_scene(self, scene_type=BattleScene, *, count=3, maximum=False, reel=False):
        attributes = CharacterAttributes()
        party = PartyState(attributes)
        for identifier in ('mira', 'lucan')[:count-1]:
            assert party.recruit(identifier)
        for identifier in party.active_ids:
            member = party.attributes(identifier)
            if maximum:
                assert member.set_modifiers('review_resource_extremes',
                    {'hp': 9999-member.value('hp'), 'mp': 999-member.value('mp')})
                assert member.set_current(hp=9999, mp=999)
            else:
                hp, mp = RESOURCES[identifier]
                assert member.set_current(hp=hp, mp=mp)
        enemies = json.loads(ENEMY_PATH.read_text())
        if reel:
            enemies['enemies']['bat']['attributes']['hp'] = 9999
        model = BattleModel(attributes, ['aether_edge'], weapon_equipped=True,
                            party_members=party.battle_members(), enemy_data=enemies,
                            rng=random.Random(7))
        if reel:
            # The only ready-gauge fixture in the reel. Subsequent gauges run normally.
            model.combatant('mira').atb = 1.
        else:
            # Frozen, comparable opening state; do not advance gauges between stills.
            model.enemy.hp = 16
            for member, atb in zip(model.party, (.95, 0., .98)):
                member.atb = atb
            if model.bots:
                model.bot_for('mira').atb = .9
        self.game.attributes, self.game.party = attributes, party
        self.model = model
        self.scene = scene_type(self.game, model, battlefield='eldenmere')
        self.scene._elapsed = .8  # Show deployed actors, not the initial deployment fade.
        drain = model.drain_events
        def observed_events():
            events = drain()
            self.events.extend(deepcopy(events))
            return events
        model.drain_events = observed_events
        self.draw()
        return model

    def draw(self):
        self.texts.clear()
        self.scene.draw(self.canvas, self.game.ui_surface)
        self.game.window.blit(self.game.ui_surface, (0, 0))
        assert self.game.ui_surface.get_clip() == self.game.ui_surface.get_rect()

    def geometry(self):
        scene = self.scene
        height = scene.panel_rect.height
        return {'panel': list(scene.panel_rect), 'panel_height': height,
                'status_height': scene._status_height,
                'interactive_height': height-scene._status_height,
                'status_fraction': scene._status_height/height,
                'interactive_fraction': (height-scene._status_height)/height,
                'gear': list(scene.gear.rect),
                'columns': {identifier: {key: list(value) for key, value in row.items()
                                        if isinstance(value, pygame.Rect)}
                            for identifier, row in scene.party_rows.items()},
                'commands': {key: list(value) for key, value in scene.command_rects.items()},
                'rendered_bot_hud': [text for text in self.texts if BOT_HUD.match(text)]}

    def shot(self, name):
        self.draw()
        pygame.image.save(self.game.ui_surface, str(self.output/name))
        self.shots.append({'file': name, 'window': list(self.game.window.get_size()),
                           'text_scale': self.game.audio.text_scale,
                           'party': [member.identifier for member in self.model.party],
                           'resources': {member.identifier: {'hp': member.hp, 'max_hp': member.max_hp,
                               'mp': member.mp, 'max_mp': member.max_mp} for member in self.model.party},
                           'geometry': self.geometry()})

    def key(self, key):
        self.inputs.append({'simulation_seconds': round(self.simulated, 3),
                            'kind': 'key', 'key': pygame.key.name(key)})
        self.scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key, repeat=False))
        self.scene.handle_event(pygame.event.Event(pygame.KEYUP, key=key))

    def pointer(self, kind, point):
        physical = (round(point[0]*self.game.window.get_width()/480),
                    round(point[1]*self.game.window.get_height()/320))
        self.inputs.append({'simulation_seconds': round(self.simulated, 3),
                            'kind': pygame.event.event_name(kind), 'logical': list(point)})
        values = {'pos': physical}
        if kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            values['button'] = 1
        elif kind == pygame.MOUSEMOTION:
            values.update(rel=(0, 0), buttons=(1, 0, 0))
        self.scene.handle_event(pygame.event.Event(kind, **values))

    def click(self, point):
        for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            self.pointer(kind, point)

    def choose(self, action):
        self.draw()
        if action == 'overclock':
            self.click(self.scene.command_rects['skills'].center)
            self.draw()
        self.click(self.scene.command_rects[action].center)
        assert self.model.current_action is not None
        return self.model.current_action

    def frame(self):
        self.scene.update(1/FPS)
        self.simulated += 1/FPS
        self.draw()
        assert not any(BOT_HUD.match(text) for text in self.texts), self.texts
        self.no_bot_hud_draws += 1
        if self.recording:
            self.encoder.stdin.write(pygame.image.tobytes(self.game.ui_surface, 'RGB'))
            self.frames += 1

    def hold(self, seconds):
        for _ in range(round(seconds*FPS)):
            self.frame()

    def stills(self):
        old, old_hash = baseline_scene()
        self.baseline_source_hash = old_hash
        for size, stem in (((1440, 960), '1440'), (SIZE, '960')):
            self.viewport(size)
            for scene_type, version in ((old, 'before'), (BattleScene, 'after')):
                self.make_scene(scene_type)
                self.shot(f'{version}_{stem}.png')
        self.viewport((480, 320), 1.5)
        self.make_scene(old)
        self.shot('before_minimum_480_text_150.png')
        self.make_scene()
        self.shot('minimum_480_text_150.png')
        self.make_scene(maximum=True)
        self.shot('maximum_resources_480_text_150.png')
        self.viewport()
        for count in (1, 2):
            self.make_scene(count=count)
            self.shot(f'{count}_member_960.png')
        # Side-by-side captured pixels, no reconstructed UI. The 1440 stills
        # remain available separately at the user's screenshot scale.
        images = [Image.open(self.output/f'{version}_960.png').convert('RGB')
                  for version in ('before', 'after')]
        board = Image.new('RGB', (1920, 680), '#17262d')
        font = ImageFont.truetype(str(ROOT/'assets/ui/fonts/DejaVuSans.ttf'), 22)
        for index, (label, image) in enumerate(zip(('Before', 'Updated'), images)):
            board.paste(image, (index*960, 40))
            ImageDraw.Draw(board).text((index*960+16, 9), label, font=font, fill='#f1cd77')
        board.save(self.output/'before_after.png', optimize=True)

    def reel(self):
        self.viewport()
        self.events.clear()
        model = self.make_scene(reel=True)
        self.scene.update(0)
        assert model.ready_actor == 'mira'
        self.encoder = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo',
            '-pixel_format', 'rgb24', '-video_size', '960x640', '-framerate', str(FPS), '-i', '-',
            '-an', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23', '-pix_fmt', 'yuv420p',
            str(self.output/'compact_combat_ui_silent.mp4')], stdin=subprocess.PIPE)
        try:
            self.recording = True
            self.stages.append({'video_seconds': 0, 'stage': 'Mira ready; compact three-member HUD'})
            self.hold(.6)
            initial_gem = model.active_gem
            self.key(pygame.K_g)
            self.key(pygame.K_RIGHT)
            self.hold(.3)
            self.key(pygame.K_RETURN)
            self.hold(.4)
            keyboard_gem = model.active_gem
            assert keyboard_gem != initial_gem
            self.key(pygame.K_TAB)
            self.stages.append({'video_seconds': self.frames/FPS, 'stage': 'Gear mouse drag and release'})
            wheel = self.scene.gear.rect
            center = (wheel.centerx, wheel.top+round(wheel.height*25/48))
            radius = wheel.width*.25
            self.pointer(pygame.MOUSEBUTTONDOWN, (center[0], center[1]-radius))
            for angle in (-math.pi/2, -math.pi/3, -math.pi/6, 0.):
                self.pointer(pygame.MOUSEMOTION,
                             (center[0]+radius*math.cos(angle), center[1]+radius*math.sin(angle)))
                self.hold(.1)
            self.pointer(pygame.MOUSEBUTTONUP, (center[0]+radius, center[1]))
            self.hold(.5)
            dragged_gem = model.active_gem
            assert dragged_gem != keyboard_gem
            # Pointer leaves the wheel so its deliberate ATB slowdown does not
            # affect the bot action or the remainder of this review.
            self.pointer(pygame.MOUSEMOTION, (470, 5))
            self.stages.append({'video_seconds': self.frames/FPS, 'stage': 'Mira selects Overclock'})
            action = self.choose('overclock')
            while model.current_action is action:
                self.frame()
            bot = model.bot_for('mira')
            assert bot.haste_turns == 8
            overclock_mp = model.combatant('mira').mp
            self.shot('overclock_active_960.png')
            self.stages.append({'video_seconds': self.frames/FPS, 'stage': 'Rivet charges and acts autonomously'})
            first_completed = False
            for _ in range(600):
                if model.waiting_for_player:
                    self.choose('guard')
                self.frame()
                if any(event['type'] == 'haste_tick' for event in self.events):
                    first_completed = True
                    self.shot('rivet_after_action_960.png')
                    self.hold(.7)
                    break
            assert first_completed, 'Rivet never completed its autonomous action'
            self.recording = False
            # Continue the same actual combat silently until all eight hasted
            # bot actions finish; the review video remains a short contiguous reel.
            for _ in range(6000):
                if not bot.haste_turns:
                    break
                if model.waiting_for_player:
                    self.choose('guard')
                self.frame()
                assert not model.ended, 'Review must not end before haste expires'
            assert bot.haste_turns == 0
            ticks = [event['remaining_turns'] for event in self.events if event['type'] == 'haste_tick']
            assert ticks == list(range(7, -1, -1)), ticks
            impacts = [event for event in self.events
                       if event['type'] == 'impact' and event['actor'] == bot.identifier]
            assert len(impacts) >= 8
            self.bot_verification = {'overclock_mp_after': overclock_mp, 'haste_applied': 8,
                'haste_tick_remaining': ticks, 'autonomous_bot_impacts': len(impacts),
                'haste_expired_events': len([event for event in self.events if event['type'] == 'haste_expired']),
                'simulation_seconds': round(self.simulated, 3), 'rendered_frames_without_bot_hud': self.no_bot_hud_draws,
                'gear_keyboard': [initial_gem, keyboard_gem], 'gear_mouse_drag': [keyboard_gem, dragged_gem]}
        finally:
            self.recording = False
            self.encoder.stdin.close()
            assert self.encoder.wait() == 0

    def decoded_video_board(self):
        """Inspect the encoded result rather than assembling raw render buffers."""
        board = Image.new('RGB', (960, 740), '#17262d')
        font = ImageFont.truetype(str(ROOT/'assets/ui/fonts/DejaVuSans.ttf'), 17)
        draw = ImageDraw.Draw(board)
        draw.text((12, 8), 'Decoded silent reel / actual production frames',
                  font=font, fill='#f1cd77')
        cases = ((.8, 'Keyboard gear preview'), (1.6, 'Captured mouse drag'),
                 (2.7, 'Mira Overclock'), (7.8, 'Autonomous Rivet action'))
        for index, (seconds, label) in enumerate(cases):
            pixels = subprocess.check_output(['ffmpeg', '-v', 'error', '-ss', str(seconds),
                '-i', str(self.output/'compact_combat_ui_silent.mp4'), '-frames:v', '1',
                '-f', 'image2pipe', '-vcodec', 'png', '-'])
            image = Image.open(io.BytesIO(pixels)).convert('RGB').resize((480, 320), Image.Resampling.NEAREST)
            x, y = (index % 2)*480, 40+(index//2)*350
            board.paste(image, (x, y))
            draw.text((x+8, y+324), f'{label} / {seconds:.1f}s', font=font, fill='#f8f0d9')
        board.save(self.output/'decoded_reel_frames.png', optimize=True)

    def run(self):
        before = fingerprints()
        model_state = unchanged_model_state()
        try:
            self.stills()
            self.reel()
        finally:
            pygame.quit()
        after = fingerprints()
        assert before == after, 'Production sources changed during capture; rerun.'
        self.decoded_video_board()
        artifacts = {path.name: digest(path) for path in sorted(self.output.iterdir())
                     if path.suffix in ('.png', '.mp4')}
        write_json(self.output/'fingerprints.json', after)
        write_json(self.output/'verification.json', {
            'baseline_commit': BASELINE, 'baseline_scene_sha256': self.baseline_source_hash,
            'model_state_unchanged_from_baseline': model_state,
            'fixtures': [
                'Production PartyState recruits Mira and Lucan for an isolated review only. Lucan recruitment is not added to the story.',
                'Identical before/after: Caelan HP103/140 MP11/30; Mira HP177/300 MP13/30; Lucan HP97/140 MP4/30; Bat HP16/72; RNG seed7.',
                'Stills freeze party gauges at .95,0,.98 and Rivet at .9; scene presentation elapsed=.8s shows completed deployment.',
                'Resource-extreme still uses supported max HP9999/MP999 through a named review modifier.',
                'Reel starts Mira ATB=1 and all other gauges=0, with durable Bat HP9999. All later ATB/action/damage/haste clocks are production simulation.',
                'Real G/Right/Enter and mouse drag change gems, real UI clicks select Overclock, subsequent ready actors choose Guard through the UI.',
                'Video is one contiguous sequence through the first completed hasted bot action. Simulation then continues until all eight haste turns expire.',
                'No action definitions, sprites, poses, camera, staging, draw calls, personal save files, or settings files are replaced.'
            ], 'silent': True, 'video_fps': FPS, 'video_size': list(SIZE),
            'video_seconds': self.frames/FPS, 'shots': self.shots,
            'stages': self.stages, 'inputs': self.inputs, 'bot_verification': self.bot_verification,
            'events': self.events, 'files_unchanged_during_capture': before == after, 'artifacts': artifacts})
        print(json.dumps({'output': str(self.output), 'video_seconds': self.frames/FPS,
                          'bot_verification': self.bot_verification}))


def check(output):
    report = json.loads((output/'verification.json').read_text())
    assert json.loads((output/'fingerprints.json').read_text()) == fingerprints(), 'Source changed; recapture review.'
    for name, expected in report['artifacts'].items():
        assert digest(output/name) == expected, f'Artifact changed: {name}'
    baseline = subprocess.check_output(['git', 'show', BASELINE+':battle_scene.py'], cwd=ROOT)
    assert hashlib.sha256(baseline).hexdigest() == report['baseline_scene_sha256']
    assert unchanged_model_state() == report['model_state_unchanged_from_baseline']
    probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams',
        '-of', 'json', str(output/'compact_combat_ui_silent.mp4')]))
    assert [stream['codec_type'] for stream in probe['streams']] == ['video']
    stream = probe['streams'][0]
    assert (stream['width'], stream['height']) == SIZE
    assert stream['r_frame_rate'] == f'{FPS}/1'
    bot = report['bot_verification']
    assert bot['haste_tick_remaining'] == list(range(7, -1, -1))
    assert bot['autonomous_bot_impacts'] >= 8 and bot['haste_expired_events'] == 1
    assert all(not shot['geometry']['rendered_bot_hud'] for shot in report['shots']
               if not shot['file'].startswith('before_'))
    shots = {shot['file']: shot for shot in report['shots']}
    for size in ('1440', '960'):
        old = shots[f'before_{size}.png']['geometry']
        new = shots[f'after_{size}.png']['geometry']
        assert new['panel_height'] < old['panel_height']
        assert new['interactive_height'] == 2*new['status_height']
        assert new['gear'][2:] == old['gear'][2:] == [48, 48]
    print('Compact combat UI sources, artifact hashes, silent video and eight autonomous bot actions verified.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.check:
        check(args.output)
    else:
        Capture(args.output).run()
