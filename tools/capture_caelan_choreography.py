"""Record Caelan's production choreography and an unmodified-clock MQ02 run.

The production journey reuses the existing gear capture driver without editing
its provenance. Only the separate reel uses durable enemies, scripted incoming
attacks and a fixed damage roll, each declared in verification.json.
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
import subprocess
import sys
import tempfile

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
from gear_state import GEM_ORDER
from main import Game
from test_aether_edge_battle_model import FixedVariance
from capture_gear_combat import Capture as GearCapture, encoder, FPS, SIZE, NATIVE


def fingerprints():
    names = ['battle_model.py', 'battle_scene.py', 'battle_choreography.py',
             'battle_action_fx.py', 'battle_action_audio.py', 'combat_motion_art.py',
             'gearblade_art.py', 'gearblade_fx.py', 'gear_widget.py', 'gear_state.py',
             'character_abilities.py', 'world_encounters.py', 'main.py',
             'tools/capture_gear_combat.py', 'tools/capture_caelan_choreography.py']
    for directory in ('assets/combat', 'assets/story/gearblade_focus',
                      'assets/source/combat', 'assets/source/cinematics/mill_gift'):
        names.extend(str(path.relative_to(ROOT)) for path in (ROOT/directory).rglob('*')
                     if path.is_file())
    return {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
            for name in sorted(set(names))}


class Capture(GearCapture):
    def __init__(self, output):
        super().__init__(output)
        self.reel_cases = []
        self.phase_screens = []
        self._seen_phases = set()
        self.reel_omitted_charging_seconds = 0.

    def observe_frame(self):
        super().observe_frame()
        if not self.game.combat.active:
            return
        scene, model = self.game.combat.scene, self.game.combat.model
        sample = scene._choreography()
        if sample is not None:
            action = model.current_action
            key = (action.action, sample.phase)
            if key not in self._seen_phases:
                self._seen_phases.add(key)
                self.snapshot('mq02_'+action.action+'_'+sample.phase+'.png',
                              action.name+' · '+sample.phase)
            if action.resolved:
                self.snapshot('mq02_'+action.action+'_impact.png', action.name+' · impact')

    def reel_frame(self):
        self.reel_scene.update(1/FPS)
        self.reel_scene.draw(self.game.canvas, self.game.ui_surface)
        self.game.window.blit(self.game.ui_surface, (0, 0))
        self.reel_encoder.stdin.write(pygame.image.tobytes(self.game.window, 'RGB'))
        self.reel_frames += 1

    def reel_snapshot(self, case, phase):
        name = case+'_'+phase+'.png'
        if name in self.screens_seen:
            return
        self.screens_seen.add(name)
        pygame.image.save(self.game.window, str(self.output/name))
        self.phase_screens.append({'file': name, 'case': case, 'phase': phase,
                                   'video_seconds': round(max(0, self.reel_frames-1)/FPS, 3)})

    def make_reel_scene(self, *, armed=True, enemy='bat', gem='water', learned=()):
        enemies = json.loads(ENEMY_PATH.read_text())
        enemies['enemies'][enemy]['attributes'].update(hp=1000000, speed=0)
        model = BattleModel(CharacterAttributes(), learned, weapon_equipped=armed,
                            enemy_id=enemy, enemy_data=enemies, active_gem=gem,
                            rng=FixedVariance())
        self.reel_scene = BattleScene(self.game, model,
                                     battlefield='millrace' if enemy != 'bat' else 'eldenmere')
        return model

    def await_player(self):
        for _ in range(1200):
            if self.reel_scene.model.waiting_for_player:
                self.reel_scene.draw(self.game.canvas, self.game.ui_surface)
                return
            # Keep the review reel compact while still charging through the
            # real model clock. The complete journey records ordinary charging.
            self.reel_scene.update(1/FPS)
            self.reel_omitted_charging_seconds += 1/FPS
        raise AssertionError('Isolated fixture did not become ready')

    def choose_reel(self, command):
        scene = self.reel_scene
        if command == 'aether_edge':
            self.reel_click(scene.command_rects['skills'].center)
            scene.draw(self.game.canvas, self.game.ui_surface)
        self.reel_click(scene.command_rects[command].center)
        assert scene.model.current_action is not None

    def action_reel(self, case, command, *, armed=True, enemy='bat', gem='water'):
        model = self.make_reel_scene(armed=armed, enemy=enemy, gem=gem,
                                     learned=('aether_edge', 'aether_dart'))
        self.await_player()
        self.choose_reel(command)
        action = model.current_action
        start = self.reel_frames/FPS
        phases = []
        for _ in range(math.ceil(action.duration*FPS)+1):
            self.reel_frame()
            sample = self.reel_scene._choreography()
            if sample is not None and sample.phase not in phases:
                phases.append(sample.phase)
            # Capture the middle of each phase, where the authored pose reads.
            if sample is not None and .35 <= sample.phase_progress <= .75:
                self.reel_snapshot(case, sample.phase)
            if action.resolved:
                self.reel_snapshot(case, 'impact')
            if model.current_action is not action:
                break
        assert action.resolved and model.current_action is not action
        self.reel_snapshot(case, 'returned')
        self.reel_cases.append({'case': case, 'action': command, 'armed': armed,
                                'enemy': enemy, 'gem': gem, 'start_seconds': start,
                                'end_seconds': self.reel_frames/FPS, 'phases': phases,
                                'damage': action.damage, 'duration': action.duration,
                                'impact_at': action.impact_at, 'mp_after': model.player.mp})
        for _ in range(9):
            self.reel_frame()

    def incoming_reel(self, enemy, *, guarded):
        model = self.make_reel_scene(enemy=enemy)
        self.await_player()
        if guarded:
            self.choose_reel('guard')
            guard = model.current_action
            while model.current_action is guard:
                self.reel_frame()
        # This explicitly isolated fixture selects an incoming ability. It then
        # uses the same elapsed time, impact, damage and reaction path as play.
        identifier = 'bite' if enemy == 'bat' else 'tusker_charge'
        model._start_action('enemy', identifier)
        action = model.current_action
        case = enemy+('_guarded' if guarded else '_hurt')
        start = self.reel_frames/FPS
        hp = model.player.hp
        phases = set()
        for _ in range(math.ceil((action.duration+.55)*FPS)):
            self.reel_frame()
            state = self.reel_scene._pose('player')[0]
            if state not in phases and (state.startswith('hurt') or state.startswith('guard')):
                phases.add(state)
                self.reel_snapshot(case, state)
        self.reel_cases.append({'case': case, 'enemy': enemy, 'incoming': identifier,
                                'guarded': guarded, 'start_seconds': start,
                                'end_seconds': self.reel_frames/FPS,
                                'damage': hp-model.player.hp,
                                'reaction_poses': sorted(phases)})

    def record_reel(self):
        self.reel_encoder = encoder(self.output/'caelan_choreography_reel_silent.mp4')
        try:
            self.action_reel('unarmed_attack_bat', 'attack', armed=False)
            self.action_reel('armed_attack_bat', 'attack')
            for gem in GEM_ORDER:
                self.action_reel('edge_'+gem+'_bat', 'aether_edge', gem=gem)
            self.action_reel('aether_dart_bat', 'aether_dart')
            self.action_reel('guard_bat', 'guard')
            self.action_reel('armed_attack_boar', 'attack', enemy='ridgeback_tusker')
            for enemy in ('bat', 'ridgeback_tusker'):
                for guarded in (False, True):
                    self.incoming_reel(enemy, guarded=guarded)
            edges = [case for case in self.reel_cases if case.get('action') == 'aether_edge']
            assert len({case['damage'] for case in edges}) == 1
        finally:
            self.reel_encoder.stdin.close()
            assert self.reel_encoder.wait() == 0

    def contact_sheet(self):
        # Assemble only existing rendered images; no pose or sprite synthesis.
        cases = ('unarmed_attack_bat', 'armed_attack_bat', 'edge_water_bat',
                 'aether_dart_bat', 'guard_bat', 'ridgeback_tusker_hurt',
                 'ridgeback_tusker_guarded')
        selected = [item for case in cases for item in self.phase_screens
                    if item['case'] == case]
        columns = 4
        sheet = Image.new('RGB', (480*columns, 350*math.ceil(len(selected)/columns)), '#142b26')
        draw = ImageDraw.Draw(sheet)
        font = ImageFont.truetype(str(ROOT/'assets/ui/fonts/AtkinsonHyperlegible-Regular.ttf'), 14)
        for index, item in enumerate(selected):
            x, y = index % columns*480, index//columns*350
            with Image.open(self.output/item['file']) as source:
                sheet.paste(source.convert('RGB').resize(NATIVE, Image.Resampling.NEAREST), (x, y))
            draw.text((x+6, y+324), item['case']+' · '+item['phase'], font=font, fill='#f8f0d9')
        sheet.save(self.output/'contact_sheet.png')
        proof = {('unarmed_attack_bat', 'impact'), ('armed_attack_bat', 'impact'),
                 ('edge_water_bat', 'impact'), ('aether_dart_bat', 'release'),
                 ('guard_bat', 'brace'), ('armed_attack_boar', 'impact'),
                 ('ridgeback_tusker_hurt', 'hurt_recover'),
                 ('ridgeback_tusker_guarded', 'guard_impact')}
        decoded_samples = [item for item in self.phase_screens
                           if (item['case'], item['phase']) in proof]
        decoded_sheet = Image.new('RGB', (1920, 350*math.ceil(len(decoded_samples)/4)), '#142b26')
        decoded_draw = ImageDraw.Draw(decoded_sheet)
        for index, item in enumerate(decoded_samples):
            decoded = subprocess.run([
                'ffmpeg', '-v', 'error', '-ss', str(item['video_seconds']),
                '-i', str(self.output/'caelan_choreography_reel_silent.mp4'),
                '-frames:v', '1', '-vf', 'scale=480:320:flags=neighbor',
                '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                stdout=subprocess.PIPE, check=True)
            frame = Image.frombytes('RGB', NATIVE, decoded.stdout)
            x, y = index % 4*480, index//4*350
            decoded_sheet.paste(frame, (x, y))
            decoded_draw.text((x+6, y+324), item['case']+' · '+item['phase'],
                              font=font, fill='#f8f0d9')
        decoded_sheet.save(self.output/'decoded_video_contact_sheet.png')

    def run(self, *, reel_only=False):
        before = fingerprints()
        (self.output/'fingerprints_start.json').write_text(json.dumps(before, indent=2)+'\n')
        with tempfile.TemporaryDirectory(prefix='caelan-choreography-') as directory:
            path = Path(directory)
            self.game = Game(window_size=SIZE, fullscreen=False, start_on_title=False,
                             save_path=path/'journey.json', settings_path=path/'settings.json')
            self.game.audio.set_music(0)
            self.game.audio.set_effects(0)
            pygame.event.clear()
            if not reel_only:
                self.encoder = encoder(self.output/'mq02_choreography_silent.mp4')
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
            self.game.opening_audio.reset()
            self.game.regional_audio.reset()
            self.game.music.stop()
            pygame.quit()
        after = fingerprints()
        changed = [name for name in sorted(set(before)|set(after)) if before.get(name) != after.get(name)]
        assert not changed, 'Source or art changed during capture; rerun after edits settle: '+', '.join(changed)
        self.contact_sheet()
        report = {'silent': True, 'size': list(SIZE), 'fps': FPS,
                  'production_video': None if reel_only else 'mq02_choreography_silent.mp4',
                  'production_seconds': self.full_frames/FPS,
                  'reel_video': 'caelan_choreography_reel_silent.mp4',
                  'reel_seconds': self.reel_frames/FPS,
                  'reel_omitted_charging_seconds': self.reel_omitted_charging_seconds,
                  'production_fixture': 'Prior MQ01 public-API handoff and MQ02 prelude station placement; RNG 7. No combat HP, MP, ATB, phase or timer overrides.',
                  'reel_fixture': 'Isolated 1000000-HP enemy definitions, enemy Speed 0, fixed 100% damage variance, learned Edge/Dart. Incoming reel explicitly starts Bite or Bankbreaker Charge. No animation timer overrides.',
                  'source_and_art_fingerprints_unchanged': before == after,
                  'reel': self.reel_cases, 'phase_screens': self.phase_screens,
                  'observations': self.observations, 'inputs': self.inputs,
                  'events': self.events, 'screenshots': self.screenshots,
                  'actions': dict(Counter(event.get('action') for event in self.events
                                          if event['type'] == 'action_started'))}
        (self.output/'verification.json').write_text(json.dumps(report, indent=2)+'\n')
        (self.output/'fingerprints.json').write_text(json.dumps(after, indent=2)+'\n')
        (self.output/'README.md').write_text('''# Caelan choreography review

[Choreography reel](caelan_choreography_reel_silent.mp4) · [Real MQ02 journey](mq02_choreography_silent.mp4) · [Phase contact sheet](contact_sheet.png) · [Decoded video frames](decoded_video_contact_sheet.png)

Silent production rendering at 960×640 and 30 FPS. The reel shows unarmed and
armed Attack, all four non-elemental Aether Edge focus colors, Aether Dart,
Guard, and guarded versus unguarded reactions to the Bat and Boar. Each action
uses production choreography, authored sprites, damage and impact timing.
Isolated reel fixtures are declared in [verification.json](verification.json).
Initial gauge charging is simulated normally and omitted from this short reel.

The full MQ02 video reuses the earlier capture driver, receives the weapon
through real dialogue, selects opening Guard, fails the first matching focus,
discovers Aether Edge on the next attempt, uses Mira's Overclock and Rivet,
then reaches victory and settled Spoils. Combat resources, gauges and animation
clocks are never overridden. Earlier quest progress, prelude placement and
RNG 7 are the only full-journey fixtures. The earlier capture script is unedited.

[Verification](verification.json) includes inputs, events, action counts and
phase timestamps. [Fingerprints](fingerprints.json) prove source and art stayed
unchanged throughout capture. Contact sheets only assemble rendered frames.

Reproduce: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy /workspace/.venvs/project-jrpg/bin/python tools/capture_caelan_choreography.py`.
''')
        print(json.dumps({'output': str(self.output), 'production_seconds': self.full_frames/FPS,
                          'reel_seconds': self.reel_frames/FPS, 'actions': report['actions']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'docs/reviews/caelan_choreography')
    parser.add_argument('--reel-only', action='store_true', help='Render only the isolated review reel')
    arguments = parser.parse_args()
    Capture(arguments.output).run(reel_only=arguments.reel_only)
