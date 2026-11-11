#!/usr/bin/env python3
"""Render the isolated phase-one art study with production battle composition.

No battle actions execute. Poses/attachment FX are explicitly sought for visual
review; resources, EXP, inventory, unlocks and saves remain unchanged.
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
sys.path.insert(0, str(ROOT))

import pygame
from PIL import Image, ImageDraw, ImageFont

from main import Game
from mira_rig_preview import MiraRigPreview, POSES


OUT = ROOT/'docs/reviews/mira_arm_rig'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    pygame.init();pygame.display.set_mode((960, 640))
    game = Game(window_size=(960, 640), fullscreen=False, start_on_title=False,
                _preview_window=pygame.Surface((960, 640)))
    study = MiraRigPreview(game)
    before = game._progress_signature()
    evidence = dict(scope='Phase one: worn arm-rig artwork and local routing study only',
        fixture=['Isolated non-persistent Game; fixed level-one Caelan/Mira composition.',
                 'Two level-two Cave Bats, no bot loadouts, frozen command-ready ATB.',
                 'No model actions, battle outcomes, damage, healing, MP costs or unlocks execute.',
                 'Poses and illustrative attachment effects are sought for art review.',
                 'Three-member variant adds Lucan only to the disposable composition.'], captures=[])

    def capture(name, state='idle', progress=.5):
        study.select_pose(next(index for index, pair in enumerate(POSES) if pair[0] == state))
        study.pose_ms = study.pose_duration_ms*progress
        study.draw()
        pygame.image.save(game.window, str(OUT/name))
        evidence['captures'].append(dict(file=name, party_count=study.party_count,
            text_scale=game.audio.text_scale, pose=state, pose_ms=study.pose_ms,
            allocation=study.rig.allocation,
            resources={member.identifier: dict(hp=member.hp, mp=member.mp)
                       for member in study.model.party}))

    try:
        for count in (2, 3):
            study.party_count = count;study._make_scene()
            for scale in (1., 1.5):
                game.audio.set_text_scale(scale)
                capture(f'combat_{count}_party_text_{round(scale*100)}.png')
        study.party_count = 2;study._make_scene();game.audio.set_text_scale(1.)
        for state in ('attack', 'charged_bolt', 'bulwark', 'repair_pulse', 'impact_bolt', 'arc_discharge'):
            capture(state+'.png', state, .57)
        # A deliberate redistribution demonstrates the local control affordance.
        study.rig.adjust('support', -1);study.rig.adjust('weapons', 1);study.rig.commit()
        capture('weapons_configuration.png', 'charged_bolt', .38)
        (ROOT/'assets/ui/gallery/mira_arm_rig.png').write_bytes((OUT/'combat_2_party_text_100.png').read_bytes())

        encoder = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error',
            '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '960x640', '-r', '20', '-i', '-',
            '-an', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '21',
            '-movflags', '+faststart', str(OUT/'mira_arm_rig_study.mp4')], stdin=subprocess.PIPE)
        gif_frames = []
        frames = 0
        for index, (state, label) in enumerate(POSES):
            study.select_pose(index)
            milliseconds = study.pose_duration_ms+350
            for frame in range(max(1, round(milliseconds/50))):
                study.pose_ms = min(study.pose_duration_ms-1, frame*50)
                study.elapsed += .05;study.scene._elapsed = study.elapsed
                study.draw()
                raw = pygame.image.tostring(game.window, 'RGB')
                encoder.stdin.write(raw);frames += 1
                if state in ('idle', 'charged_bolt', 'bulwark', 'repair_pulse', 'impact_bolt', 'arc_discharge') and frame % 2 == 0:
                    gif_frames.append(Image.frombytes('RGB', (960, 640), raw).resize((720, 480), Image.Resampling.NEAREST))
        encoder.stdin.close()
        if encoder.wait() != 0:raise RuntimeError('Video export failed')
        gif_frames[0].save(OUT/'mira_arm_rig_study.gif', save_all=True,
                          append_images=gif_frames[1:], duration=100, loop=0, optimize=False)
        evidence['video'] = dict(file='mira_arm_rig_study.mp4', frames=frames, fps=20,
                                states=[state for state, _ in POSES], audio=False)

        manifest = json.loads((ROOT/'assets/combat/mira/animation.json').read_text())
        font = ImageFont.truetype(str(ROOT/'assets/ui/fonts/AtkinsonHyperlegible-Regular.ttf'), 16)
        contact = Image.new('RGB', (640, len(POSES)*144), '#10271f')
        draw = ImageDraw.Draw(contact)
        for row, (state, label) in enumerate(POSES):
            animation = manifest['animations'].get(state, manifest['animations']['idle'])
            for sample, fraction in enumerate((0., .35, .65, .99)):
                cell = animation['frames'][min(len(animation['frames'])-1, int(len(animation['frames'])*fraction))]
                with Image.open(ROOT/'assets/combat/mira'/cell['file']) as frame:
                    sprite = frame.convert('RGBA').resize((128, 128), Image.Resampling.NEAREST)
                    contact.paste(sprite, (128+sample*128, row*144+12), sprite)
            draw.text((8, row*144+55), label, font=font, fill='#f1cd77')
        contact.save(OUT/'pose_contact_sheet.png')
        assert before == game._progress_signature(), 'Art study changed persistent progress'
        assert not game.save_store.enabled and not game.combat.active
        evidence['progress_unchanged'] = True
        evidence['fingerprints'] = {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
            for name in ('mira_rig_preview.py', 'mira_rig_ui.py', 'assets/combat/mira/animation.json')}
        (OUT/'evidence.json').write_text(json.dumps(evidence, indent=2)+'\n')
    finally:
        game.music.stop();game.opening_audio.reset();pygame.quit()
    print('Captured phase-one Mira arm-rig stills, animation study and contact sheet')


if __name__ == '__main__':main()
