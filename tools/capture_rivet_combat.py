"""Record a silent production MQ02 Rivet journey in disposable player files.

Earlier MQ01 work is seeded with the existing public-API fixture. MQ02 dialogue,
commands, combat clocks, damage, results, and the walk to the intake use the real
Game paths. No battle phase, resource, gauge, or animation timer is overridden.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import hashlib
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
sys.path[:0] = [str(ROOT), str(ROOT/'tests')]

import pygame
from PIL import Image, ImageDraw, ImageFont

from main import Game, WALK_SPEED
from npc_routines import find_path
from test_mill_battle_gameplay import click, key, read_social, seed_mill_handoff
from ui_style import Painter


FPS = 30
VIDEO_SIZE = (960, 640)
TRANSIENT_FIELDS = {'atb', 'haste_turns', 'haste_rate_multiplier', 'current_action', 'bots'}


def fingerprints():
    groups = {
        'renderers': ['main.py', 'battle_scene.py', 'world_encounters.py',
                      'ui_style.py', 'battle_transition.py', 'spoils_scene.py'],
        'rules_and_story': ['battle_model.py', 'combat_damage.py', 'bot_loadouts.py',
                            'character_abilities.py', 'mill_quest.py', 'post_battle.py',
                            'assets/combat/actions.json', 'assets/combat/bots.json',
                            'assets/combat/guests.json', 'assets/combat/enemies.json',
                            'assets/abilities/catalog.json', 'assets/abilities/characters.json',
                            'assets/story/mill/scene.json', 'assets/story/mill/layout.json'],
        'runtime_art': [str(path.relative_to(ROOT)) for actor in ('mira', 'rivet')
                        for path in sorted((ROOT/'assets/combat'/actor).glob('*'))
                        if path.is_file()],
        'art_sources_and_capture': ['tools/build_machinist_assets.py',
                                    'tools/capture_rivet_combat.py',
                                    'tests/test_mill_battle_gameplay.py',
                                    'assets/source/combat/machinist/generation.json',
                                    'assets/source/combat/machinist/mira_bolt_launcher_generated_sheet.png',
                                    'assets/source/combat/machinist/rivet_generated_sheet.png'],
    }
    result = {}
    for group, names in groups.items():
        files = {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
                 for name in sorted(names)}
        result[group] = {
            'sha256': hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest(),
            'files': files,
        }
    return result


class Capture:
    def __init__(self, output):
        self.output = output
        self.output.mkdir(parents=True, exist_ok=True)
        self.frames = 0
        self.simulation_seconds = 0.0
        self.encoder = None
        self.events = []
        self.inputs = []
        self.observations = []
        self.screenshots = []
        self.labels = {}
        self.actions_seen = set()
        self.screens_seen = set()
        self.transition_freeze_checks = 0
        self.omitted_notice_wait_seconds = 0.0

    @property
    def seconds(self):
        return self.frames/FPS

    def mark(self, kind, **values):
        self.observations.append({'video_seconds': round(self.seconds, 3),
                                  'observation': kind, **values})

    def press(self, value, reason):
        self.inputs.append({'video_seconds': round(self.seconds, 3),
                            'input': pygame.key.name(value), 'reason': reason})
        key(self.game, value)

    def click(self, logical, reason):
        self.inputs.append({'video_seconds': round(self.seconds, 3),
                            'input': 'click', 'logical_position': list(logical), 'reason': reason})
        click(self.game, logical)

    def snapshot(self, name, label, *, text_scale=1.0):
        """Draw at native output size; no resampling or state/time changes."""
        if name in self.screens_seen:
            return
        game = self.game
        old_scale = game.audio.text_scale
        game.handle_events([pygame.event.Event(pygame.VIDEORESIZE, w=480, h=320)])
        game.audio.set_text_scale(text_scale)
        texts = []
        text = Painter.text

        def observe(painter, value, *args, **kwargs):
            texts.append(str(value))
            return text(painter, value, *args, **kwargs)

        try:
            with patch.object(Painter, 'text', observe):
                game.draw()
            assert game.window.get_size() == (480, 320)
            assert game.ui_surface.get_clip() == game.ui_surface.get_rect()
            pygame.image.save(game.window, str(self.output/name))
        finally:
            game.audio.set_text_scale(old_scale)
            game.handle_events([pygame.event.Event(pygame.VIDEORESIZE,
                                                    w=VIDEO_SIZE[0], h=VIDEO_SIZE[1])])
            game.draw()
        self.screens_seen.add(name)
        self.labels[name] = label
        record = {'file': name, 'label': label, 'size': [480, 320],
                  'text_scale': text_scale, 'video_seconds': round(self.seconds, 3),
                  'observed_text': list(dict.fromkeys(texts))}
        if not game.combat.active:
            record['world_camera'] = list(game.camera.position())
            record['mira_position'] = list(game.mill_quest.mira.position)
        self.screenshots.append(record)

    def wait_for_world_notices(self):
        """Let real announcement timers finish; omit the idle wait from video."""
        for _ in range(2400):
            self.game.update(1/FPS, (0, 0), False)
            self.game.draw()
            self.omitted_notice_wait_seconds += 1/FPS
            ui = self.game.quest_ui
            if ui.current_notice is None and not ui.notices:
                return
        raise AssertionError('World quest announcements did not finish normally.')

    def frame(self, direction=(0, 0), seconds=1/FPS):
        game = self.game
        transition = game.combat.transitioning
        if transition:
            model = game.combat.model
            before = (model.phase, tuple(actor.atb for actor in
                      (*model.party, model.enemy, *model.bots)), game.elapsed_ms)
        assert game.handle_events()
        game.update(seconds, direction, False)
        self.simulation_seconds += seconds
        if transition:
            after = (model.phase, tuple(actor.atb for actor in
                     (*model.party, model.enemy, *model.bots)), game.elapsed_ms)
            assert before == after, 'Entry transition advanced battle or world clocks.'
            self.transition_freeze_checks += 1
        game.draw()
        self.observe_frame()
        assert game.window.get_size() == VIDEO_SIZE
        self.encoder.stdin.write(pygame.image.tobytes(game.window, 'RGB'))
        self.frames += 1

    def hold(self, seconds):
        for _ in range(round(seconds*FPS)):
            self.frame()

    def observe_frame(self):
        if not self.game.combat.active:
            return
        model = self.game.combat.model
        action = model.current_action
        if action is None:
            return
        if action.action == 'overclock' and action.elapsed >= .23:
            self.snapshot('05_overclock_cast.png', 'Overclock: Mira works the control; Rivet responds')
        if action.action == 'piston_jab' and action.resolved:
            self.snapshot('07_piston_jab.png', 'Autonomous Piston Jab at impact')
        if action.action == 'tusker_charge' and action.resolved:
            impacts = [event for event in self.events
                       if event['type'] == 'impact' and event.get('action') == 'tusker_charge']
            if impacts and impacts[-1]['guarded'] and not self.game.combat.scene.tutorial_active:
                self.snapshot('08_guarded_charge.png', 'Charge meets the selected target\'s Guard')
        if action.action == 'overclock' and action.resolved:
            self.snapshot('06_haste_150.png', 'Haste 8, with 150% text at the minimum window',
                          text_scale=1.5)

    def place_prior_station(self, point, world=None):
        """Use the existing MQ02 prelude station fixture, before combat only."""
        game = self.game
        world = world or game.world
        game.world = world
        for radius in (0, 8, 16, 24):
            for offset in ((0, radius), (radius, 0), (-radius, 0), (0, -radius)):
                position = pygame.Vector2(point)+offset
                if not world.can_stand(position):
                    continue
                game.player.position.update(position)
                for delta in ((-24, 0), (24, 0), (0, 24), (0, -24)):
                    if world.can_stand(position+delta):
                        game.mill_quest._place_mira(world, position+delta)
                        break
                game.camera.reset()
                game.transfer_cooldown = 0
                return
        raise AssertionError('No clear prelude station fixture position.')

    def prepare(self):
        game = self.game
        seed_mill_handoff(game)
        controller = game.mill_quest
        self.place_prior_station(controller.mira.position+(0, 28), game.town)
        key(game, pygame.K_e)
        assert game.social.script_identifier == 'mill_reunion'
        read_social(game)
        assert controller.mira_armed and not controller.mira_weapon_stowed
        game.update(.3, (0, 0), False)
        self.wait_for_world_notices()
        self.snapshot('01_launcher_carried.png', 'Launcher carried after the authored reunion')
        self.mark('launcher_carried', mira_armed=controller.mira_armed)
        self.hold(1.2)
        for station in ('mechanism', 'race'):
            self.place_prior_station(controller.points[station])
            key(game, pygame.K_e)
            read_social(game)
        assert controller.warned
        self.place_prior_station(controller.points['town_trail'], game.town)
        self.press(pygame.K_e, 'Take the authored north-road link')
        assert game.world is controller.upstream
        for _ in range(1000):
            if game.combat.active:
                return
            if game.social.active:
                # Prelude prose is condensed in this combat-focused video.
                key(game, pygame.K_SPACE)
            self.frame()
        raise AssertionError('Authored MQ02 entry did not start the battle.')

    def record_battle(self):
        game = self.game
        scene = game.combat.scene
        model = scene.model
        model.rng = random.Random(7)
        bot = model.bot_for('mira')
        assert bot is not None and (bot.atb, bot.haste_turns) == (0, 0)
        drain = model.drain_events

        def observe_events():
            batch = drain()
            self.events.extend({'video_seconds': round(self.seconds, 3), **deepcopy(event)}
                               for event in batch)
            return batch

        overclocked = caelan_skills = False
        with patch.object(model, 'drain_events', side_effect=observe_events):
            while game.combat.transitioning:
                self.frame()
            assert all(actor.atb == 0 for actor in (*model.party, model.enemy, *model.bots))
            self.mark('free_empty_atb_deployment', owner='mira', bot='rivet',
                      mira_mp=model.combatant('mira').mp, bot_atb=bot.atb,
                      bot_haste_turns=bot.haste_turns, bot_has_hp=hasattr(bot, 'hp'),
                      bot_has_mp=hasattr(bot, 'mp'))
            self.snapshot('02_empty_bot_atb.png', 'Automatic Rivet deployment: empty independent ATB')
            for _ in range(6000):
                if model.ended:
                    break
                if scene.tutorial_active:
                    self.hold(.8)
                    self.press(pygame.K_SPACE, 'Acknowledge authored battle guidance')
                    continue
                if model.waiting_for_player:
                    game.draw()
                    actor = model.ready_actor
                    if actor == 'mira' and not overclocked:
                        before = (model.combatant('mira').mp, bot.atb)
                        self.click(scene.command_rects['skills'].center, 'Open Mira Skills')
                        assert scene.command_menu == 'skills'
                        self.snapshot('04_overclock_skills.png', 'Mira Skills: Overclock costs 5 MP')
                        self.hold(1.5)
                        self.click(scene.command_rects['overclock'].center, 'Cast Overclock')
                        action = model.current_action
                        assert (action.actor, action.action, action.target) == ('mira', 'overclock', 'rivet')
                        assert (model.combatant('mira').mp, bot.atb, bot.haste_turns) == (before[0]-5, before[1], 0)
                        self.mark('overclock_accepted', mira_mp_before=before[0],
                                  mira_mp_after=model.combatant('mira').mp,
                                  bot_fraction_before=before[1], bot_fraction_after=bot.atb,
                                  haste_before_impact=bot.haste_turns)
                        overclocked = True
                    else:
                        if actor == 'player' and not caelan_skills:
                            before = (model.player.mp, model.player.atb, bot.atb)
                            self.click(scene.command_rects['skills'].center, 'Try unarmed Caelan Skills')
                            assert scene.command_menu == 'root'
                            assert scene._notice == 'Requires a weapon.'
                            assert (model.player.mp, model.player.atb, bot.atb) == before
                            self.mark('unarmed_skills_rejected_without_cost', player_mp=model.player.mp,
                                      player_atb=model.player.atb, bot_atb=bot.atb)
                            self.snapshot('03_caelan_unarmed_skills.png', 'Caelan Skills disabled: requires a weapon')
                            self.hold(1.2)
                            caelan_skills = True
                        command = 'guard' if model.telegraphed_target == actor else 'attack'
                        self.click(scene.command_rects[command].center, actor+' chooses '+command)
                    self.frame()
                else:
                    self.frame()
            else:
                raise AssertionError('Production battle did not finish.')
        assert overclocked and caelan_skills
        assert model.phase == 'victory'
        assert model.bots == () and (bot.atb, bot.haste_turns) == (0, 0)
        assert any(event['type'] == 'haste_applied' and event['remaining_turns'] == 8
                   and event['rate_multiplier'] == 1.5 for event in self.events)
        assert any(event['type'] == 'impact' and event.get('action') == 'tusker_charge'
                   and event['guarded'] for event in self.events)
        self.mark('victory_cleanup', bots_remaining=len(model.bots),
                  detached_bot_atb=bot.atb, detached_bot_haste_turns=bot.haste_turns)
        self.snapshot('09_victory.png', 'Victory: attachment combat state cleared')
        for _ in range(300):
            if game.combat.post_phase == 'spoils' and game.combat.spoils.awarded:
                break
            self.frame()
        else:
            raise AssertionError('Victory did not reach awarded Spoils.')
        assert model.bots == ()
        self.mark('spoils_cleanup', bots_remaining=len(model.bots),
                  receipt=game.combat.receipt_id,
                  rewards=deepcopy(game.combat.spoils.rewards))
        self.snapshot('10_spoils.png', 'Spoils of Battle: no bot party row or combat state')
        self.hold(1.5)
        self.click(game.combat.spoils.continue_rect.center, 'Continue from awarded Spoils')
        for _ in range(300):
            if not game.combat.active:
                break
            self.frame()
        assert not game.combat.active
        read_social(game)
        assert game.mill_quest.aftermath_done

    def walk_to_intake(self):
        game = self.game
        controller = game.mill_quest
        goal = controller.points['intake']
        route = find_path(game.world, game.player.position, goal,
                          game.world.probe_size, None)
        assert route is not None, 'No production walking path to the intake.'
        self.mark('walk_to_intake', start=list(game.player.position), goal=list(goal))
        for point in route:
            for _ in range(1000):
                delta = pygame.Vector2(point)-game.player.position
                if delta.length() < .05:
                    break
                before = game.player.position.copy()
                self.frame(delta, min(1/FPS, delta.length()/WALK_SPEED))
                assert game.player.position.distance_to(before) > 1e-6, 'Production player walking was blocked.'
            else:
                raise AssertionError('Player did not finish a walking segment.')
        self.hold(.6)
        self.press(pygame.K_e, 'Inspect the intake after victory and aftermath')
        assert game.social.script_identifier == 'mill_intake'
        read_social(game)
        assert 'intake' in controller.inspected
        assert controller.mira_weapon_stowed and not controller.mira_armed
        self.hold(1.0)
        self.wait_for_world_notices()
        self.snapshot('11_launcher_stowed.png', 'Launcher stowed after real intake inspection')
        self.mark('launcher_stowed', intake_inspected=True, mira_weapon_stowed=True)
        self.hold(1.0)

    def contact_sheet(self):
        columns, cell_height = 3, 350
        rows = (len(self.screenshots)+columns-1)//columns
        sheet = Image.new('RGB', (480*columns, cell_height*rows), '#142b26')
        draw = ImageDraw.Draw(sheet)
        font = ImageFont.truetype(str(ROOT/'assets/ui/fonts/AtkinsonHyperlegible-Regular.ttf'), 14)
        for index, item in enumerate(self.screenshots):
            x, y = index % columns*480, index//columns*cell_height
            with Image.open(self.output/item['file']) as screenshot:
                sheet.paste(screenshot.convert('RGB'), (x, y))
            draw.text((x+8, y+325), item['file'], fill='#f8f0d9', font=font)
        sheet.save(self.output/'contact_sheet.png')

        # Detail crops preserve native game pixels, enlarged by a whole factor.
        detail = Image.new('RGB', (768, 316), '#142b26')
        detail_draw = ImageDraw.Draw(detail)
        for index, name in enumerate(('01_launcher_carried.png', '11_launcher_stowed.png')):
            item = next(record for record in self.screenshots if record['file'] == name)
            anchor = (pygame.Vector2(item['mira_position'])+(0, -15) if index == 0
                      else (pygame.Vector2(430, 252)+pygame.Vector2(item['mira_position']))/2)
            center = anchor-pygame.Vector2(item['world_camera'])
            box = (round(center.x)-64, round(center.y)-48,
                   round(center.x)+64, round(center.y)+48)
            with Image.open(self.output/name) as screenshot:
                crop = screenshot.crop(box).resize((384, 288), Image.Resampling.NEAREST)
                detail.paste(crop, (index*384, 0))
            detail_draw.text((index*384+8, 294), 'Carried' if index == 0 else 'Stowed',
                             fill='#f8f0d9', font=font)
        detail.save(self.output/'launcher_world_detail.png')

        # These tiles come from the encoded video itself, not the still exports.
        video_sheet = Image.new('RGB', (480*columns, cell_height*rows), '#142b26')
        video_draw = ImageDraw.Draw(video_sheet)
        for index, item in enumerate(self.screenshots):
            frame = subprocess.run([
                'ffmpeg', '-v', 'error', '-ss', str(item['video_seconds']),
                '-i', str(self.output/'rivet_combat_silent.mp4'), '-frames:v', '1',
                '-vf', 'scale=480:320:flags=neighbor', '-f', 'rawvideo',
                '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE, check=True)
            rendered = Image.frombytes('RGB', (480, 320), frame.stdout)
            x, y = index % columns*480, index//columns*cell_height
            video_sheet.paste(rendered, (x, y))
            video_draw.text((x+8, y+325), str(item['video_seconds'])+'s · '+item['file'],
                            fill='#f8f0d9', font=font)
        video_sheet.save(self.output/'video_contact_sheet.png')

    def report(self, before):
        after = fingerprints()
        assert before == after, 'Captured runtime/source files changed during recording; rerun capture.'
        (self.output/'fingerprints.json').write_text(json.dumps(after, indent=2)+'\n')
        counts = Counter(event['action'] for event in self.events if event['type'] == 'action_started')
        impacts = [event for event in self.events if event['type'] == 'impact']
        metadata = {
            'preview': 'Silent; production game frames with no audio track.',
            'video': 'rivet_combat_silent.mp4', 'video_size': list(VIDEO_SIZE),
            'fps': FPS, 'frames': self.frames, 'duration_seconds': round(self.seconds, 3),
            'recorded_update_seconds': round(self.simulation_seconds, 3),
            'omitted_world_notice_wait_seconds': round(self.omitted_notice_wait_seconds, 3),
            'temporary_journey_and_settings': True,
            'fixture': 'MQ01 complete through public APIs; MQ02 prelude station placement only. Prelude prose is condensed. Battle and post-battle walk are production updates and input.',
            'rng': 'random.Random(7); no battle HP/MP/ATB/phase/action timer overrides.',
            'source_fingerprints_unchanged_during_capture': True,
            'fingerprint_groups': {group: record['sha256'] for group, record in after.items()},
            'transition_frozen_clock_checks': self.transition_freeze_checks,
            'action_counts': dict(counts), 'observations': self.observations,
            'inputs': self.inputs, 'battle_events': self.events,
            'screenshots': self.screenshots,
            'piston_jab_damage': [event['damage'] for event in impacts if event['action'] == 'piston_jab'],
            'guarded_charge_damage': [event['damage'] for event in impacts
                                      if event['action'] == 'tusker_charge' and event['guarded']],
        }
        (self.output/'verification.json').write_text(json.dumps(metadata, indent=2)+'\n')
        hashes = '\n'.join('- '+group+': `'+record['sha256']+'`'
                           for group, record in after.items())
        (self.output/'README.md').write_text(f'''# Mira, Rivet, and Overclock production review

[Watch the silent production capture](rivet_combat_silent.mp4) · [Native stills](contact_sheet.png) · [Video frames](video_contact_sheet.png) · [Launcher details](launcher_world_detail.png)

The video shows the carried bolt launcher, authored MQ02 entry, Rivet deployed
with empty ATB, Mira's real Skills → Overclock input, and the five-MP deduction.
Haste applies at impact with eight bot turns and a 1.5× charge rate. Caelan's
unarmed Skills command stays disabled. Rivet attacks autonomously; the charge
target chooses Guard before the Tusker hits. Victory clears bot combat state,
Spoils awards once, and the real walk and intake inspection stow the launcher.

This is a **silent preview**: {self.frames} direct production frames at {FPS} FPS,
960×640, lasting {self.seconds:.2f} seconds. Native screenshots are 480×320;
`06_haste_150.png` uses the production 150% text setting at that minimum window.
The game supplies all sprites, effects, status, captions, command bounds, and UI.
The contact sheet only assembles those rendered frames.

Only MQ01 completion and prelude interaction-station placement are fixtures.
MQ02 conversations are acknowledged normally; prelude and aftermath prose is
condensed in the combat-focused edit. Combat and the post-battle walk advance
through ordinary timed `Game.update`, input, and draw calls. The seeded RNG is
7; HP, MP, ATB, phases, and action/animation timers are never overridden.
Journey and settings files live in a temporary directory.
World announcement timers also finish normally; {self.omitted_notice_wait_seconds:.2f}
seconds of idle waiting is omitted from the video for the two clear world stills.

Observed action starts: {dict(counts)}. Piston Jab damage:
{metadata['piston_jab_damage']}; guarded charge damage:
{metadata['guarded_charge_damage']}. Exact command inputs, start/impact events,
Haste application/ticks, zero-state cleanup, and screenshot text observations
are in [verification.json](verification.json). No per-frame state dump is used.

Runtime and source files were fingerprinted before and after capture and matched.
Full file SHA-256 values are in [fingerprints.json](fingerprints.json).

{hashes}

Reproduce from the repository root:

```sh
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy \\
  /workspace/.venvs/project-jrpg/bin/python tools/capture_rivet_combat.py \\
  --output docs/reviews/mira_rivet
```
''')
        return metadata

    def run(self):
        before = fingerprints()
        with tempfile.TemporaryDirectory(prefix='rivet-production-capture-') as directory:
            path = Path(directory)
            self.game = Game(window_size=VIDEO_SIZE, fullscreen=False, start_on_title=False,
                             save_path=path/'journey.json', settings_path=path/'settings.json')
            self.game.audio.set_music(0)
            self.game.audio.set_effects(0)
            pygame.event.clear()
            self.encoder = subprocess.Popen([
                'ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pixel_format', 'rgb24',
                '-video_size', '960x640', '-framerate', str(FPS), '-i', '-', '-an',
                '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '22', '-pix_fmt', 'yuv420p',
                str(self.output/'rivet_combat_silent.mp4')], stdin=subprocess.PIPE)
            try:
                self.prepare()
                self.record_battle()
                self.walk_to_intake()
                assert self.game.save_progress()
                saved = json.loads((path/'journey.json').read_text())
                assert saved['bot_loadouts']['loadouts'] == {'mira': {'bot_id': 'rivet', 'ability_id': 'piston_jab'}}
                assert not any('"'+field+'"' in json.dumps(saved) for field in TRANSIENT_FIELDS)
            finally:
                self.encoder.stdin.close()
                code = self.encoder.wait()
                self.game.opening_audio.reset()
                self.game.regional_audio.reset()
                self.game.music.stop()
                pygame.quit()
            assert code == 0, 'Video encoding failed.'
        self.contact_sheet()
        metadata = self.report(before)
        print(json.dumps({'output': str(self.output), 'frames': self.frames,
                          'seconds': metadata['duration_seconds'],
                          'actions': metadata['action_counts'], 'screenshots': len(self.screenshots)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'docs/reviews/mira_rivet')
    Capture(parser.parse_args().output).run()
