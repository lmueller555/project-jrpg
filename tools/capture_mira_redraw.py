"""Review Mira's authored drawings through the production battle renderer.

This isolated reel declares its fixtures: Mira's ready gauge, durable passive
Tusker, selected incoming tusk strikes, and one-HP lethal cases. Actions, damage,
impact clocks, UI, sprites and reactions are production code. No player files
are read or written. A sprite sheet and animated board assemble exported PNGs.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import io
import json
import os
from pathlib import Path
import random
import subprocess
import sys
from types import SimpleNamespace

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'tools')]

import pygame
from PIL import Image, ImageDraw, ImageFont

from audio_settings import AudioSettings
from battle_model import BattleModel, ENEMY_PATH
from battle_scene import BattleScene
from character_attributes import CharacterAttributes
from ui_style import UIStyle

FPS = 60
SIZE = (960, 640)
STATES = ('idle', 'attack', 'guard_enter', 'guard', 'guard_impact', 'hurt',
          'overclock', 'victory', 'defeat', 'walk')


def fingerprints():
    names = ['battle_scene.py', 'battle_model.py', 'mira_combat_art.py',
             'assets/combat/actions.json', 'tools/capture_mira_redraw.py']
    for folder in ('assets/combat/mira', 'assets/source/combat/mira_redraw'):
        names.extend(str(p.relative_to(ROOT)) for p in (ROOT/folder).rglob('*') if p.is_file())
    return {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
            for name in sorted(names)}


def font(size):
    return ImageFont.truetype(str(ROOT/'assets/ui/fonts/DejaVuSans.ttf'), size)


def select_frame(animation, time):
    duration = sum(frame['duration_ms'] for frame in animation['frames'])
    time = time % duration if animation['loop'] else min(time, duration - 1)
    for frame in animation['frames']:
        if time < frame['duration_ms']:
            return frame['file']
        time -= frame['duration_ms']
    return animation['frames'][-1]['file']


def sprite_boards(output):
    folder = ROOT/'assets/combat/mira'
    data = json.loads((folder/'animation.json').read_text())
    images = {frame['file']: Image.open(folder/frame['file']).convert('RGBA')
              for state in STATES for frame in data['animations'][state]['frames']}
    sheet = Image.new('RGB', (1400, len(STATES)*150+55), '#17262d')
    draw = ImageDraw.Draw(sheet)
    draw.text((18, 12), 'MIRA / authored combat drawings / 2x native pixels', font=font(20), fill='#f1cd77')
    for row, state in enumerate(STATES):
        y = 50 + row*150
        draw.text((16, y+35), state.replace('_', ' ').title(), font=font(17), fill='#f8f0d9')
        for index, record in enumerate(data['animations'][state]['frames']):
            x = 200 + index*148
            image = images[record['file']].resize((128, 128), Image.Resampling.NEAREST)
            sheet.paste(image, (x, y), image)
            draw.line((x, y+108, x+128, y+108), fill='#3b514e')
            draw.text((x+3, y+128), f"{record['duration_ms']} ms", font=font(13), fill='#b7c3af')
    sheet.save(output/'sprite_sheet.png')
    # Compare exported production pixels with the verified pre-redraw commit.
    before_after = Image.new('RGB', (1200, 900), '#17262d')
    comparison = ImageDraw.Draw(before_after)
    comparison.text((18, 12), 'MIRA / before and updated / same native scale and floor',
                    font=font(20), fill='#f1cd77')
    source_version = '45bd4ce6e55843862b2b3804ea4f155d5ca33e5d'
    for column, label in enumerate(('Before', 'Updated', 'Caelan / scale reference')):
        comparison.text((column*400+24, 52), label, font=font(19), fill='#f8f0d9')
    for row, (old_file, new_file, label) in enumerate((
            ('idle_01.png','idle_01.png','Ready'),
            ('attack_02.png','attack_04.png','Aimed / release pose'))):
        old = Image.open(io.BytesIO(subprocess.check_output([
            'git','show',source_version+':assets/combat/mira/'+old_file], cwd=ROOT))).convert('RGBA')
        new = images[new_file]
        caelan = Image.open(ROOT/'assets/combat/caelan/idle_01.png').convert('RGBA')
        registered = Image.new('RGBA', (64,64))
        registered.alpha_composite(caelan, (8,12))
        y = 95+row*390
        for column, image in enumerate((old,new,registered)):
            image = image.resize((384,384), Image.Resampling.NEAREST)
            before_after.paste(image,(column*400+8,y),image)
            comparison.line((column*400+8,y+324,column*400+392,y+324),fill='#52675d')
        comparison.text((20,y+355),label,font=font(17),fill='#b7c3af')
    before_after.save(output/'before_after.png')
    frames = []
    for elapsed in range(0, 2400, 80):
        board = Image.new('RGB', (864, 920), '#17262d')
        draw = ImageDraw.Draw(board)
        draw.text((18, 12), 'MIRA / production sprite animations / 3x', font=font(20), fill='#f1cd77')
        for index, state in enumerate(STATES):
            x, y = (index % 4)*216, 55+(index//4)*285
            anim = data['animations'][state]
            # One-shot states have a readable hold, then restart in this review.
            clock = elapsed % (sum(f['duration_ms'] for f in anim['frames'])+450)
            image = images[select_frame(anim, clock)].resize((192, 192), Image.Resampling.NEAREST)
            board.paste(image, (x+12, y+20), image)
            draw.line((x+12, y+182, x+204, y+182), fill='#3b514e')
            draw.text((x+12, y+225), state.replace('_', ' ').title(), font=font(17), fill='#f8f0d9')
        frames.append(board)
    frames[0].save(output/'sprite_animations.gif', save_all=True,
                   append_images=frames[1:], duration=80, loop=0, disposal=2)


class Capture:
    def __init__(self, output):
        self.output = output
        output.mkdir(parents=True, exist_ok=True)
        pygame.init()
        self.game = SimpleNamespace(window=pygame.display.set_mode(SIZE),
                                    ui_surface=pygame.Surface(SIZE),
                                    attributes=CharacterAttributes(), audio=AudioSettings())
        self.game.audio.set_effects(0)
        self.game.audio.set_music(0)
        self.game.ui = UIStyle(self.game)
        self.game.to_canvas = lambda point: (point[0]*480/self.game.window.get_width(),
                                            point[1]*320/self.game.window.get_height())
        self.canvas = pygame.Surface((480,320))
        self.frames = 0
        self.cases = []
        self.encoder = None
        self.current_case = None
        self.saved = set()

    def make_scene(self, *, reduced=False, enemy_hp=1000000, mira_hp=None):
        self.game.audio.reduced_motion = reduced
        enemies = json.loads(ENEMY_PATH.read_text())
        enemies['enemies']['ridgeback_tusker']['attributes'].update(hp=enemy_hp, speed=0)
        model = BattleModel(self.game.attributes, ['aether_edge'], weapon_equipped=True,
                            guest_id='mira', enemy_id='ridgeback_tusker', enemy_data=enemies,
                            rng=random.Random(7))
        if mira_hp is not None:
            model.combatant('mira').hp = mira_hp
        self.scene = BattleScene(self.game, model, battlefield='millrace')
        self.model = model
        self.events = []
        drain = model.drain_events
        def observe_events():
            events = drain()
            self.events.extend(deepcopy(events))
            return events
        model.drain_events = observe_events
        self.draw()
        return model

    def draw(self):
        self.scene.draw(self.canvas, self.game.ui_surface)
        self.game.window.blit(self.game.ui_surface, (0, 0))

    def snapshot(self, name):
        if name in self.saved:
            return
        self.draw()
        pygame.image.save(self.game.ui_surface, str(self.output/name))
        self.saved.add(name)

    def frame(self):
        self.scene.update(1/FPS)
        self.draw()
        self.encoder.stdin.write(pygame.image.tobytes(self.game.ui_surface, 'RGB'))
        self.frames += 1

    def hold(self, seconds):
        for _ in range(round(seconds*FPS)):
            self.frame()

    def click(self, logical):
        for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            self.scene.handle_event(pygame.event.Event(kind, button=1,
                                   pos=tuple(round(v*2) for v in logical)))
        self.draw()

    def choose(self, action):
        self.model.combatant('mira').atb = 1
        self.scene.update(0)
        self.draw()
        assert self.model.ready_actor == 'mira'
        if action == 'overclock':
            self.click(self.scene.command_rects['skills'].center)
        self.click(self.scene.command_rects[action].center)
        assert self.model.current_action is not None
        return self.model.current_action

    def case(self, name, *, action='attack', reduced=False, enemy_hp=1000000):
        self.make_scene(reduced=reduced, enemy_hp=enemy_hp)
        self.current_case = name
        start = self.frames/FPS
        self.hold(.65)
        self.snapshot(name+'_ready.png')
        current = self.choose(action)
        captured = set()
        while self.model.current_action is current:
            age = current.elapsed
            for label, threshold in (('prepare', .15), ('release', .28),
                                     ('impact', current.impact_at), ('recover', current.duration-.12)):
                if age >= threshold and label not in captured:
                    self.snapshot(name+'_'+label+'.png')
                    captured.add(label)
            self.frame()
        self.hold(1.0)
        if current.action == 'bolt_shot':
            assert len([e for e in self.events if e['type']=='impact' and e['action']=='bolt_shot']) == 1
        if current.action == 'overclock':
            assert len([e for e in self.events if e['type']=='haste_applied']) == 1
        self.snapshot(name+'_settled.png')
        self.cases.append({'case': name, 'start': start, 'end': self.frames/FPS,
                           'action': current.action, 'duration': current.duration,
                           'impact_at': current.impact_at, 'damage': current.damage,
                           'reduced_motion': reduced, 'outcome': self.model.phase,
                           'mp_after': self.model.combatant('mira').mp,
                           'haste_turns': self.model.bot_for('mira').haste_turns if self.model.bots else None,
                           'events': self.events})

    def incoming(self, name, *, guarded=False, lethal=False):
        self.make_scene(mira_hp=1 if lethal else None)
        start = self.frames/FPS
        self.hold(.5)
        if guarded:
            action = self.choose('guard')
            while self.model.current_action is action:
                self.frame()
            self.hold(.3)
        self.model._start_action('enemy', 'tusk_strike')
        action = self.model.current_action
        assert action.target == 'mira'
        captured = False
        for _ in range(round((action.duration+1.2)*FPS)):
            self.frame()
            if action.resolved and not captured:
                self.snapshot(name+'_impact.png')
                captured = True
        self.snapshot(name+'_settled.png')
        self.cases.append({'case': name, 'start': start, 'end': self.frames/FPS,
                           'guarded': guarded, 'lethal': lethal, 'incoming': action.action,
                           'damage': action.damage, 'mira_hp': self.model.combatant('mira').hp,
                           'pose': self.scene._pose('mira')[0], 'events': self.events})

    def layout_stills(self):
        self.make_scene()
        self.hold(.8)
        for size, scale, reduced, name in (((480,320),1.5,False,'minimum_large_text.png'),
                                         ((960,640),1.0,False,'normal_battle.png'),
                                         ((960,640),1.0,True,'reduced_motion.png')):
            self.game.window = pygame.display.set_mode(size)
            self.game.ui_surface = pygame.Surface(size)
            self.game.audio.set_text_scale(scale)
            self.game.audio.reduced_motion = reduced
            self.snapshot(name)
        self.game.audio.reduced_motion = False
        self.game.audio.set_text_scale(1.)

    def run(self):
        before = fingerprints()
        self.encoder = subprocess.Popen(['ffmpeg','-y','-v','error','-f','rawvideo',
            '-pixel_format','rgb24','-video_size','960x640','-framerate',str(FPS),'-i','-',
            '-an','-c:v','libx264','-preset','veryfast','-crf','20','-pix_fmt','yuv420p',
            str(self.output/'mira_combat_reel_silent.mp4')], stdin=subprocess.PIPE)
        try:
            self.case('bolt_shot')
            self.case('overclock', action='overclock')
            self.incoming('guarded_hit', guarded=True)
            self.incoming('unguarded_hit')
            self.case('reduced_motion_shot', reduced=True)
            self.case('victory', enemy_hp=1)
            self.incoming('incapacitated', lethal=True)
            self.layout_stills()
        finally:
            self.encoder.stdin.close()
            assert self.encoder.wait() == 0
            pygame.quit()
        sprite_boards(self.output)
        # Decode the actual encoded video for a compact motion review board.
        contact = Image.new('RGB', (960, 1044), '#17262d')
        labels = (('Bolt Shot', .94), ('Overclock', 3.62),
                  ('Guarded impact', 6.72), ('Unguarded impact', 9.25),
                  ('Victory settled', 15.52), ('Incapacitated', 17.60))
        for index, (label, seconds) in enumerate(labels):
            pixels = subprocess.check_output(['ffmpeg','-v','error','-ss',str(seconds),
                '-i',str(self.output/'mira_combat_reel_silent.mp4'),'-frames:v','1',
                '-f','image2pipe','-vcodec','png','-'])
            image = Image.open(io.BytesIO(pixels)).convert('RGB')
            image = image.resize((480,320), Image.Resampling.NEAREST)
            x,y = (index % 2)*480, (index//2)*348
            contact.paste(image,(x,y))
            ImageDraw.Draw(contact).text((x+8,y+324),label+f' / {seconds:.2f}s',
                                        font=font(15),fill='#f8f0d9')
        contact.save(self.output/'decoded_video_frames.png')
        after = fingerprints()
        assert before == after, 'Capture changed source or runtime art'
        (self.output/'verification.json').write_text(json.dumps({
            'silent': True, 'fps': FPS, 'size': list(SIZE), 'seconds': self.frames/FPS,
            'fixtures': ['Isolated production BattleModel and BattleScene with Mira guest and Rivet.',
                         'Durable passive Tusker (HP=1000000, Speed=0), deterministic RNG seed 7.',
                         'Mira ATB=1 before player-command clicks; incoming tusk strikes explicitly selected.',
                         'Victory sets enemy HP=1 at scene creation; incapacity sets Mira HP=1.',
                         'No action definitions, damage clocks, animation clocks, poses or frames replaced.'],
            'cases': self.cases, 'files_unchanged_during_capture': before == after,
            'screenshots': sorted(self.saved)}, indent=2)+'\n')
        (self.output/'fingerprints.json').write_text(json.dumps(after, indent=2)+'\n')
        print(json.dumps({'output':str(self.output),'seconds':self.frames/FPS,'cases':len(self.cases)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'docs/reviews/mira_redraw')
    Capture(parser.parse_args().output).run()
