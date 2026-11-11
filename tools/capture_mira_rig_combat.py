#!/usr/bin/env python3
"""Capture actual phase-two rig commands and effects in disposable Game runs.

Travel and initial ATB readiness are shortened. Character injuries and the
optional third-party member are explicit fixture setup. No enemy HP or battle
outcome is edited, and no successful skill is represented by an art override.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'tests')]

import pygame
from PIL import Image

from test_mira_rig_gameplay import RigGameFixture
from test_mill_battle_gameplay import key, click

OUT = ROOT/'docs/reviews/mira_rig_combat'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    evidence = {'scope': 'Phase two: actual live battle rules, controls and skill effects',
        'fixture': ['Each run uses a disposable completed-Mill Game and temporary save/settings files.',
                    'Caelan starts injured at40HP/0MP, Mira has30MP; readiness is explicitly shortened.',
                    'Two or three active members use a real authored cave encounter.',
                    'Lucan is recruited only in the three-character layout fixture.',
                    'All routing/skill/target commands use production mouse or keyboard input.',
                    'No enemy HP, battle outcome, pose or effect is replaced; no complete-victory claim.'],
        'captures': {}, 'actions': []}
    encoder = None
    gif_frames = []
    video_frames = 0
    fixture = None

    def setup(count=2):
        nonlocal fixture
        fixture = RigGameFixture();fixture.setUp()
        game = fixture.game
        game.window = pygame.display.set_mode((960, 640));game._ensure_ui_surface()
        if count == 3:
            assert game.party.recruit('lucan')
            assert game.party.select(('caelan', 'mira', 'lucan'))
        fixture.cave();fixture.ready('mira')
        acknowledge()
        return game

    def cleanup():
        nonlocal fixture
        if fixture is None:return
        game = fixture.game
        game.elemental_bosses.stop_audio();game.combat.stop_audio();game.music.stop()
        fixture.doCleanups();fixture = None

    def acknowledge():
        game = fixture.game
        for _ in range(20):
            if not game.combat.scene.tutorial_active:return
            key(game, pygame.K_SPACE);game.update(0, (0, 0), False)
        raise AssertionError('Combat instruction did not finish')

    def state():
        game = fixture.game;model = game.combat.model
        return {'text_scale': game.audio.text_scale, 'allocation': model.rig_allocation,
                'party': {member.identifier: {'hp': member.hp, 'mp': member.mp,
                    'barrier': member.barrier, 'barrier_turns': member.barrier_turns} for member in model.party},
                'enemies': {enemy.identifier: {'hp': enemy.hp, 'mp': enemy.mp} for enemy in model.enemies},
                'skill_uses': dict(model.rig_skill_uses), 'item_spent': dict(model.item_spent),
                'current_action': model.current_action.action if model.current_action else None,
                'phase': model.phase}

    def capture(name):
        game = fixture.game;game.draw()
        pygame.image.save(game.window, str(OUT/(name+'.png')))
        evidence['captures'][name] = state()

    def allocate(allocation):
        fixture.ready('mira');acknowledge()
        game = fixture.game;scene = game.combat.scene
        game.draw()
        for channel, target in allocation.items():
            while scene.rig.draft[channel] > target:
                click(game, scene.rig.buttons[(channel, '-')].center);game.draw()
        for channel, target in allocation.items():
            while scene.rig.draft[channel] < target:
                click(game, scene.rig.buttons[(channel, '+')].center);game.draw()
        click(game, scene.rig.buttons['apply'].center);game.draw()
        assert game.combat.model.rig_allocation == allocation

    def record_frame():
        nonlocal video_frames
        game = fixture.game;game.draw()
        raw = pygame.image.tobytes(game.window, 'RGB')
        encoder.stdin.write(raw);video_frames += 1
        if video_frames % 2 == 0:
            gif_frames.append(Image.frombytes('RGB', (960, 640), raw).resize((720, 480), Image.Resampling.NEAREST))

    def perform(identifier, target=None):
        game = fixture.game;model = game.combat.model;scene = game.combat.scene
        fixture.ready('mira');acknowledge()
        before = state()
        fixture.click_command('skills');fixture.click_command(identifier)
        if scene.command_menu == 'skill_targets':
            fixture.click_command('ally:'+target)
        elif scene._target_command is not None:
            game.draw()
            click(game, scene.enemy_rects[target or model.enemies[0].identifier].center)
        assert model.current_action is not None and model.current_action.action == identifier
        action = model.current_action
        elapsed = 0.
        captured = False
        while model.current_action is action:
            game.update(.05, (0, 0), False);elapsed += .05
            record_frame()
            if not captured and elapsed >= action.impact_at:
                capture(identifier+'_impact');captured = True
            if elapsed > action.duration+.2:raise AssertionError('Action did not complete')
        after = state()
        evidence['actions'].append({'skill': identifier, 'before': before, 'after': after})
        capture(identifier+'_after')
        for _ in range(5):record_frame()

    try:
        for count in (2, 3):
            game = setup(count)
            for scale in (1., 1.5):
                game.audio.set_text_scale(scale)
                capture('combat_'+str(count)+'_party_text_'+str(round(scale*100)))
            cleanup()
        game = setup()
        encoder = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo',
            '-pix_fmt', 'rgb24', '-s', '960x640', '-r', '20', '-i', '-', '-an',
            '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '21', '-movflags', '+faststart',
            str(OUT/'mira_rig_combat.mp4')], stdin=subprocess.PIPE)
        allocate({'weapons': 0, 'protection': 3, 'support': 3})
        capture('support_allocation')
        perform('bulwark')
        perform('repair_pulse', 'player')
        allocate({'weapons': 3, 'protection': 1, 'support': 2})
        capture('offense_allocation')
        perform('charged_bolt', game.combat.model.enemies[0].identifier)
        perform('arc_discharge', game.combat.model.enemies[-1].identifier)
        allocate({'weapons': 2, 'protection': 2, 'support': 2})
        perform('impact_bolt', game.combat.model.living_enemies[0].identifier)
        encoder.stdin.close()
        if encoder.wait() != 0:raise RuntimeError('Combat video encoding failed')
        encoder = None
        gif_frames[0].save(OUT/'mira_rig_combat.gif', save_all=True,
            append_images=gif_frames[1:], duration=100, loop=0, optimize=False)
        assert not game.combat.model.bots
        evidence['video'] = {'file': 'mira_rig_combat.mp4', 'frames': video_frames, 'fps': 20, 'audio': False}
        evidence['fingerprints'] = {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
            for name in ('battle_model.py', 'battle_scene.py', 'mira_rig_ui.py', 'mira_rig_rules.py')}
        (OUT/'evidence.json').write_text(json.dumps(evidence, indent=2)+'\n')
    finally:
        if encoder is not None:
            encoder.stdin.close();encoder.wait()
        cleanup()
    print('Captured '+str(len(evidence['captures']))+' live Mira rig views and '+str(video_frames)+' video frames')


if __name__ == '__main__':main()
