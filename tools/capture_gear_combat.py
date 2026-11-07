"""Record real MQ02 gear input and an isolated four-focus Aether Edge reel.

The full journey seeds only prior MQ01 work and prelude station placement, then
uses production dialogue, selector events, combat clocks, damage and settlement.
The isolated reel supplies a durable harmless Bat fixture so all four identical
non-elemental strikes can be compared without changing any action definition.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
import math
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
sys.path[:0] = [str(ROOT), str(ROOT/'tests'), str(ROOT/'tools')]

import pygame
from PIL import Image, ImageDraw, ImageFont

from battle_model import BattleModel, ENEMY_PATH
from battle_scene import BattleScene
from character_attributes import CharacterAttributes
from gear_state import GEM_ORDER, REQUIRED_GEMS
from main import Game
from test_mill_battle_gameplay import click, key, read_social, seed_mill_handoff
from test_aether_edge_battle_model import FixedVariance
from capture_rivet_combat import Capture as RivetCapture


FPS = 30
SIZE = (960, 640)
NATIVE = (480, 320)


def fingerprints():
    names = ['battle_model.py', 'battle_scene.py', 'gear_state.py', 'gear_widget.py',
             'gearblade_fx.py', 'gearblade_art.py', 'ui_style.py', 'main.py',
             'character_abilities.py', 'world_encounters.py', 'tools/capture_gear_combat.py',
             'assets/combat/actions.json', 'assets/combat/bestiary.json',
             'assets/abilities/catalog.json', 'assets/abilities/characters.json']
    # Every authored pose and source input stays byte-identical during capture.
    for directory in ('assets/story/gearblade_focus', 'assets/source/combat',
                      'assets/source/cinematics/mill_gift'):
        names.extend(str(path.relative_to(ROOT)) for path in (ROOT/directory).rglob('*')
                     if path.is_file())
    return {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
            for name in sorted(set(names))}


def encoder(path):
    return subprocess.Popen([
        'ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pixel_format', 'rgb24',
        '-video_size', '960x640', '-framerate', str(FPS), '-i', '-', '-an',
        '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '22', '-pix_fmt', 'yuv420p',
        str(path)], stdin=subprocess.PIPE)


class Capture(RivetCapture):
    def __init__(self, output):
        super().__init__(output)
        self.guidance_seen = set()
        self.full_frames = 0
        self.reel_frames = 0
        self.reel_observations = []

    def snapshot(self, name, label, *, text_scale=1.):
        if name in self.screens_seen:return
        self.game.draw()
        pygame.image.save(self.game.window, str(self.output/name))
        self.screens_seen.add(name)
        self.screenshots.append({'file': name, 'label': label, 'size': list(SIZE),
                                 'video_seconds': round(self.seconds, 3)})

    def observe_frame(self):
        if not self.game.combat.active:return
        model, scene = self.game.combat.model, self.game.combat.scene
        action = model.current_action
        if scene.gear.dragging:
            self.snapshot('gear_drag.png', 'Captured gear gesture, with no command accepted')
        if action is None:return
        if action.actor == 'player' and .23 <= action.elapsed <= .28:
            if action.action == 'aether_edge':
                self.snapshot('aether_'+action.active_gem+'.png', 'Non-elemental Aether Edge · '+action.active_gem)
            elif action.kind == 'failed_edge':
                self.snapshot('first_attempt.png', 'First elemental attempt, before failure')
        if action.kind == 'failed_edge' and action.resolved:
            self.snapshot('failed_attempt.png', 'Failed first focus: no damage and no MP cost')
        if action.action == 'tusker_charge' and action.resolved:
            self.snapshot('guarded_charge.png', 'The required opening Guard meets the charge')

    def move(self, logical, *, buttons=(0, 0, 0), reason='Move pointer'):
        point = tuple(round(value*2) for value in logical)
        self.game.handle_events([pygame.event.Event(pygame.MOUSEMOTION,
                                                    pos=point, rel=(0, 0), buttons=buttons)])
        self.inputs.append({'video_seconds': round(self.seconds, 3), 'input': 'motion',
                            'logical_position': list(logical), 'reason': reason})

    def seat(self, scene, gem, *, standalone=False):
        """Send a captured quarter-turn gesture, including release outside."""
        old = scene.model.active_gem
        if old == gem:return
        current, target = GEM_ORDER.index(old), GEM_ORDER.index(gem)
        steps = (current-target) % 4
        if steps > 2:steps -= 4
        bounds = scene.gear.rect
        center = pygame.Vector2(bounds.centerx, bounds.top+bounds.height*25/48)
        radius = min(bounds.width, bounds.height)*.32
        points = [center+pygame.Vector2(math.cos(angle)*radius, math.sin(angle)*radius)
                  for angle in (index*steps*math.pi/2/12 for index in range(13))]
        if standalone:
            send = lambda event:scene.handle_event(event)
            make_point = lambda point:tuple(round(value*2) for value in point)
            frame = self.reel_frame
        else:
            send = lambda event:self.game.handle_events([event])
            make_point = lambda point:tuple(round(value*2) for value in point)
            frame = self.frame
        self.inputs.append({'video_seconds': round(self.seconds, 3), 'input': 'drag',
                            'from': old, 'to': gem, 'reason': 'Seat the matching elemental focus'})
        send(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=make_point(points[0])))
        for point in points[1:]:
            send(pygame.event.Event(pygame.MOUSEMOTION, pos=make_point(point),
                                    rel=(0, 0), buttons=(1, 0, 0)))
            frame()
        send(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=make_point(points[-1])))
        for _ in range(5):frame()
        assert scene.model.active_gem == gem, (old, gem, scene.model.active_gem)
        assert scene.gear.active_gem == gem and not scene.model.gear_settling

    def choose(self, action):
        scene, model = self.game.combat.scene, self.game.combat.model
        self.game.draw()
        if action in ('aether_edge', *REQUIRED_GEMS, 'overclock'):
            if scene.command_menu != 'skills':
                self.click(scene.command_rects['skills'].center, 'Open '+model.ready_actor+' Skills')
                self.game.draw()
        assert not model.action_reason(action), model.action_reason(action)
        self.click(scene.command_rects[action].center, 'Choose '+action)

    def record_battle(self):
        game, scene = self.game, self.game.combat.scene
        model = scene.model
        model.rng = random.Random(7)
        assert model.spellblade_guided and model.weapon_equipped
        drain = model.drain_events

        def events():
            batch = drain()
            self.events.extend({'video_seconds': round(self.seconds, 3), **deepcopy(event)}
                               for event in batch)
            return batch

        normal_gems = iter(('ice', 'water', 'nature', 'fire'))
        overclocked = hovered = False
        with patch.object(model, 'drain_events', side_effect=events):
            for _ in range(12000):
                if model.ended:break
                if game.combat.transitioning:self.frame();continue
                if scene.tutorial_active:
                    text = scene.tutorial_text
                    if text not in self.guidance_seen:
                        self.guidance_seen.add(text)
                        self.snapshot('guidance_'+str(len(self.guidance_seen)).zfill(2)+'.png', text)
                    self.hold(.65)
                    self.press(pygame.K_SPACE, 'Acknowledge authored MQ02 guidance')
                    continue
                if model.waiting_for_player:
                    stage, actor = model.spellblade_stage, model.ready_actor
                    if stage == 'guard':
                        self.snapshot('opening_guard.png', 'Opening lesson: Guard first')
                        self.hold(.4);self.choose('guard')
                    elif stage in ('first_edge', 'second_edge'):
                        chosen = 'nature_edge' if stage == 'first_edge' else 'flame_edge'
                        self.seat(scene, REQUIRED_GEMS[chosen])
                        self.game.draw()
                        self.click(scene.command_rects['skills'].center, 'Open elemental lesson Skills')
                        self.game.draw()
                        self.snapshot(stage+'_skills.png', 'Matching focus gates the temporary lesson choices')
                        self.hold(.4);self.choose(chosen)
                    elif actor == 'mira' and not overclocked:
                        self.choose('overclock');overclocked = True
                    elif model.telegraphed_target == actor:self.choose('guard')
                    elif actor == 'player' and model.player.mp >= 4:
                        gem = next(normal_gems, model.active_gem)
                        self.seat(scene, gem)
                        self.choose('aether_edge')
                    else:self.choose('attack')
                    self.move((470, 180), reason='Leave the selector after committing a command')
                    self.frame()
                elif model.spellblade_stage == 'complete' and model.phase == 'charging' and not hovered:
                    before = {unit.identifier: unit.atb for unit in (*model.party, *model.bots, model.enemy)}
                    self.move(scene.gear.rect.center, reason='Hover over gear: all charging gauges use 25% speed')
                    assert scene.atb_multiplier == .25
                    self.snapshot('hover_slow.png', 'Gear hover: global charging falls to 25%')
                    self.hold(.6)
                    self.mark('hover_global_slow', multiplier=scene.atb_multiplier,
                              before=before, after={unit.identifier: unit.atb for unit in
                                                    (*model.party, *model.bots, model.enemy)})
                    self.move((470, 180), reason='Resume ordinary ATB charging')
                    hovered = True
                else:self.frame()
            else:raise AssertionError('Production MQ02 battle did not finish')
        assert model.phase == 'victory'
        assert model.aether_edge_discovered and 'aether_edge' in model.learned_abilities
        assert not set(REQUIRED_GEMS).intersection(model.learned_abilities)
        assert overclocked and hovered
        assert sum(event['type'] == 'spellblade_failed' for event in self.events) == 1
        assert sum(event['type'] == 'spellblade_discovered' for event in self.events) == 1
        self.snapshot('victory.png', 'Victory after real selector input and normal battle clocks')
        for _ in range(300):
            if game.combat.post_phase == 'spoils' and game.combat.spoils.awarded:break
            self.frame()
        else:raise AssertionError('Victory did not reach awarded Spoils')
        self.snapshot('spoils.png', 'One settled victory receipt, with no transient gear state')
        self.hold(.8)
        self.click(game.combat.spoils.continue_rect.center, 'Continue from awarded Spoils')
        for _ in range(300):
            if not game.combat.active:break
            self.frame()
        assert not game.combat.active
        read_social(game)
        assert game.character_abilities.active_gem() == model.active_gem
        assert game.character_abilities.known_abilities() >= {'aether_edge'}

    def reel_frame(self):
        self.reel_scene.update(1/FPS)
        self.reel_scene.draw(self.game.canvas, self.game.ui_surface)
        self.game.window.blit(self.game.ui_surface, (0, 0))
        self.reel_encoder.stdin.write(pygame.image.tobytes(self.game.window, 'RGB'))
        self.reel_frames += 1

    def reel_click(self, point):
        actual = tuple(round(value*2) for value in point)
        for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            self.reel_scene.handle_event(pygame.event.Event(kind, button=1, pos=actual))

    def record_reel(self):
        enemies = json.loads(ENEMY_PATH.read_text())
        enemies['enemies']['bat']['attributes'].update(hp=1000000, str=0, mag=0, speed=0)
        model = BattleModel(CharacterAttributes(), ['aether_edge'], weapon_equipped=True,
                            enemy_data=enemies, rng=FixedVariance())
        self.reel_scene = BattleScene(self.game, model)
        self.reel_encoder = encoder(self.output/'four_gem_fx_silent.mp4')
        try:
            for gem in GEM_ORDER:
                for _ in range(2000):
                    if model.waiting_for_player:break
                    self.reel_frame()
                assert model.waiting_for_player
                self.seat(self.reel_scene, gem, standalone=True)
                for _ in range(18):self.reel_frame()
                pygame.image.save(self.game.window, str(self.output/('idle_'+gem+'.png')))
                self.reel_click(self.reel_scene.command_rects['skills'].center)
                self.reel_frame()
                self.reel_click(self.reel_scene.command_rects['aether_edge'].center)
                action = model.current_action
                assert action.active_gem == gem
                for _ in range(8):self.reel_frame()
                name = 'fx_'+gem+'.png'
                pygame.image.save(self.game.window, str(self.output/name))
                self.reel_observations.append({'gem': gem, 'snapshot': name,
                                                'video_seconds': self.reel_frames/FPS,
                                                'action': action.action, 'kind': action.kind,
                                                'snapshot_at': action.elapsed})
                for _ in range(24):self.reel_frame()
                self.reel_observations[-1].update(damage=action.damage,
                                                 mp_after=model.player.mp)
            assert len({item['damage'] for item in self.reel_observations}) == 1
        finally:
            self.reel_encoder.stdin.close()
            assert self.reel_encoder.wait() == 0

    def contact_sheet(self):
        names = ['opening_guard.png', 'gear_drag.png', 'first_edge_skills.png',
                 'failed_attempt.png', 'second_edge_skills.png', 'hover_slow.png',
                 'fx_nature.png', 'fx_water.png', 'fx_fire.png', 'fx_ice.png',
                 'victory.png', 'spoils.png']
        sheet = Image.new('RGB', (1440, 350*math.ceil(len(names)/3)), '#142b26')
        draw = ImageDraw.Draw(sheet)
        font = ImageFont.truetype(str(ROOT/'assets/ui/fonts/AtkinsonHyperlegible-Regular.ttf'), 14)
        for index, name in enumerate(names):
            x, y = index % 3*480, index//3*350
            with Image.open(self.output/name) as screenshot:
                sheet.paste(screenshot.convert('RGB').resize(NATIVE, Image.Resampling.NEAREST), (x, y))
            draw.text((x+8, y+325), name, fill='#f8f0d9', font=font)
        sheet.save(self.output/'contact_sheet.png')

        samples = [(item['file'], 'mq02_gear_combat_silent.mp4', item['video_seconds'])
                   for item in self.screenshots if item['file'] in
                   ('first_edge_skills.png', 'failed_attempt.png', 'second_edge_skills.png',
                    'hover_slow.png', 'victory.png', 'spoils.png')]
        samples.extend((item['snapshot'], 'four_gem_fx_silent.mp4', item['video_seconds'])
                       for item in self.reel_observations)
        if samples:
            sheet = Image.new('RGB', (1440, 350*math.ceil(len(samples)/3)), '#142b26')
            draw = ImageDraw.Draw(sheet)
            for index, (name, video, seconds) in enumerate(samples):
                decoded = subprocess.run([
                    'ffmpeg', '-v', 'error', '-ss', str(seconds), '-i', str(self.output/video),
                    '-frames:v', '1', '-vf', 'scale=480:320:flags=neighbor',
                    '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                    stdout=subprocess.PIPE, check=True)
                frame = Image.frombytes('RGB', NATIVE, decoded.stdout)
                x, y = index % 3*480, index//3*350
                sheet.paste(frame, (x, y))
                draw.text((x+8, y+325), f'{seconds:.2f}s · '+name, fill='#f8f0d9', font=font)
            sheet.save(self.output/'video_contact_sheet.png')

    def run(self):
        before = fingerprints()
        with tempfile.TemporaryDirectory(prefix='caelan-gear-capture-') as directory:
            path = Path(directory)
            self.game = Game(window_size=SIZE, fullscreen=False, start_on_title=False,
                             save_path=path/'journey.json', settings_path=path/'settings.json')
            self.game.audio.set_music(0);self.game.audio.set_effects(0)
            pygame.event.clear()
            self.encoder = encoder(self.output/'mq02_gear_combat_silent.mp4')
            try:
                self.prepare()
                self.record_battle()
                assert self.game.save_progress()
                saved = json.loads((path/'journey.json').read_text())
                self.mark('saved_settled_gem', gem=self.game.character_abilities.active_gem(),
                          ability_state=saved['character_abilities'])
            finally:
                self.encoder.stdin.close()
                assert self.encoder.wait() == 0
            self.full_frames = self.frames
            self.record_reel()
            self.game.opening_audio.reset();self.game.regional_audio.reset();self.game.music.stop()
            pygame.quit()
        after = fingerprints()
        assert before == after, 'Runtime/source files changed during capture; rerun capture'
        self.contact_sheet()
        report = {'silent': True, 'size': list(SIZE), 'fps': FPS,
                  'production_video': 'mq02_gear_combat_silent.mp4',
                  'production_seconds': self.full_frames/FPS,
                  'reel_video': 'four_gem_fx_silent.mp4', 'reel_seconds': self.reel_frames/FPS,
                  'production_fixture': 'Prior MQ01 public-API handoff + prelude station placement only; MQ02 gift and combat run through production input/update/draw.',
                  'production_overrides': 'RNG seed 7 only; no HP/MP/ATB/phase/action/animation timer overrides.',
                  'reel_fixture': 'Explicit 1000000-HP harmless slow Bat and fixed 100% damage variance; learned Aether Edge; production action definitions and real selector/menu input.',
                  'source_and_art_fingerprints_unchanged': before == after,
                  'observations': self.observations, 'reel': self.reel_observations,
                  'inputs': self.inputs, 'events': self.events, 'screenshots': self.screenshots,
                  'actions': dict(Counter(event['action'] for event in self.events
                                          if event['type'] == 'action_started'))}
        (self.output/'verification.json').write_text(json.dumps(report, indent=2)+'\n')
        (self.output/'fingerprints.json').write_text(json.dumps(after, indent=2)+'\n')
        (self.output/'README.md').write_text('''# Caelan gear combat review

[Production MQ02 combat](mq02_gear_combat_silent.mp4) · [Four-focus FX reel](four_gem_fx_silent.mp4) · [Contact sheet](contact_sheet.png) · [Decoded video frames](video_contact_sheet.png)

Both silent previews render the production battle scene at 960×640, 30 FPS.
The MQ02 capture begins from the public prior-quest handoff fixture, receives
Mira’s gift through the real scene, then shows the required Guard, matching-gem
first failure, next-turn Aether Edge discovery, global 25% hover charging,
ordinary party combat, victory and Spoils settlement. Selector changes use real
captured pointer gestures. No combat resources, gauges, phases or action timers
are overwritten. Only prior work, prelude station placement and RNG 7 are fixtures.

The separate four-focus reel uses an explicitly durable harmless Bat fixture,
and compares learned non-elemental Aether Edge with Nature, Water, Fire and Ice
selected. It creates no elemental unlocks and changes no damage definition.
The screenshot names `fx_*.png` mark the same action age in every focus.

[Verification](verification.json) records inputs, lesson events, normal action
counts, settlement and reel observations. [Fingerprints](fingerprints.json)
confirm production rules, rendered art and art source files stayed byte-identical
during capture. The contact sheet only assembles rendered frames.

Reproduce with:

```sh
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy \\
  /workspace/.venvs/project-jrpg/bin/python tools/capture_gear_combat.py
```
''')
        print(json.dumps({'output': str(self.output), 'production_seconds': report['production_seconds'],
                          'reel_seconds': report['reel_seconds'], 'actions': report['actions']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'docs/reviews/caelan_gear')
    Capture(parser.parse_args().output).run()
