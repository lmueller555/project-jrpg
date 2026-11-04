"""Review exported companion frames using the production CombatSprites loader.

The montage repeats non-looping actions for inspection; runtime metadata keeps
their ordinary one-shot behavior. This does not create encounters or abilities.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pygame
from PIL import Image, ImageDraw, ImageFont
from battle_scene import CombatSprites


BG = '#e8edf2'
INK = '#243741'


def font(size):
    try:return ImageFont.truetype('DejaVuSans.ttf', size)
    except OSError:return ImageFont.load_default(size=size)


def enlarge(image, scale):
    return image.resize((image.width*scale, image.height*scale), Image.Resampling.NEAREST)


def draw_frame(image, path, x, y, scale):
    with Image.open(path) as source:frame = enlarge(source.convert('RGBA'), scale)
    image.paste(frame, (x, y), frame)


def preview(actor, output):
    folder = ROOT/'assets/combat'/actor
    data = json.loads((folder/'animation.json').read_text())
    special = 'cast' if actor == 'rhea' else 'technique'
    states = ['idle', 'attack', special, 'guard', 'hurt', 'victory', 'defeat', 'walk']
    labels = {'idle': 'Ready / idle', 'attack': 'Staff strike' if actor == 'rhea' else 'Sword attack',
              'cast': 'Cast: prepare / channel / release', 'technique': 'Technique: shield bash',
              'guard': 'Guard', 'hurt': 'Hurt / recover', 'victory': 'Victory',
              'defeat': 'Defeat', 'walk': 'Movement / flee cycle'}
    output.mkdir(parents=True, exist_ok=True)
    loader = CombatSprites()
    frames = []
    for sample in range(160):
        board = Image.new('RGB', (1024, 630), BG)
        draw = ImageDraw.Draw(board)
        draw.text((18, 12), data['display_name']+' — combat animations for review', font=font(23), fill=INK)
        draw.text((18, 43), 'Actual runtime frames · one-shot actions repeat here for review · 4× pixels', font=font(15), fill=INK)
        for index, state in enumerate(states):
            x, y = (index%4)*256, 78+(index//4)*270
            animation = data['animations'][state]
            duration = sum(f['duration_ms'] for f in animation['frames'])
            clock = sample*50 if animation['loop'] else (sample*50)%(duration+650)
            surface, anchor = loader.frame(actor, state, clock)
            frame = Image.frombytes('RGBA', surface.get_size(), pygame.image.tobytes(surface, 'RGBA'))
            frame = enlarge(frame, 4)
            board.paste(frame, (x, y), frame)
            draw.line((x+10, y+54*4+1, x+246, y+54*4+1), fill='#c5ced1')
            draw.text((x+10, y+241), labels[state], font=font(13), fill=INK)
        frames.append(board)
    # A single palette prevents colors changing as other review tiles animate.
    palette_board = Image.new('RGB', (256, 400), BG)
    with Image.open(folder/'spritesheet.png') as sheet:
        palette_board.paste(sheet, (0, 0), sheet)
    ImageDraw.Draw(palette_board).rectangle((0, 384, 255, 399), fill=INK)
    palette = palette_board.quantize(colors=256)
    indexed = [frame.quantize(palette=palette, dither=Image.Dither.NONE) for frame in frames]
    indexed[0].save(output/f'{actor}_animations.gif', save_all=True, append_images=indexed[1:],
                   duration=50, loop=0, disposal=2, optimize=False)
    frames[0].save(output/f'{actor}_overview.png')
    # All native poses, with the original approved ready design beside the new one.
    contact = Image.new('RGB', (1024, 1780), BG)
    draw = ImageDraw.Draw(contact)
    draw.text((18, 10), data['display_name']+' — all 24 authored poses', font=font(25), fill=INK)
    draw.text((18, 47), 'Approved ready reference', font=font(18), fill=INK)
    draw.text((530, 47), 'New ready pose — pending review', font=font(18), fill=INK)
    draw_frame(contact, ROOT/f'assets/source/combat/companion_animations/{actor}/approved_ready_reference.png', 140, 76, 3)
    draw_frame(contact, folder/'idle_01.png', 650, 76, 3)
    cells = {}
    for state in states:
        for index, frame in enumerate(data['animations'][state]['frames']):
            cells[frame['source_cell']] = (state, index+1, frame['file'])
    for cell, (state, number, filename) in sorted(cells.items()):
        x, y = (cell%4)*256, 320+(cell//4)*240
        draw_frame(contact, folder/filename, x+32, y, 3)
        draw.text((x+14, y+198), f'{labels[state]} · {number}', font=font(13), fill=INK)
    contact.save(output/f'{actor}_poses.png')
    return {'actor': actor, 'states': states, 'authored_poses': 24,
            'canvas': data['canvas'], 'anchor': data['anchor'], 'renderer': 'CombatSprites.frame',
            'source_sha256': data['source_sha256'], 'status': 'pending_user_review'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'docs/reviews/companion_combat_animations')
    args = parser.parse_args()
    pygame.display.init();pygame.display.set_mode((480, 320))
    try:
        report = {'actors': [preview(actor, args.output) for actor in ('lucan', 'rhea')]}
        report['media_sha256'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                 for p in sorted(args.output.iterdir()) if p.suffix in ('.png', '.gif')}
        (args.output/'preview.json').write_text(json.dumps(report, indent=2)+'\n')
    finally:pygame.quit()


if __name__ == '__main__':main()
