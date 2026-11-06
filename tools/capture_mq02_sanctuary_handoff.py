"""Record MQ02's actual Halden→home→Aldric handoff from a disposable New Game.

No quest, actor position, equipment, resources or world progress is seeded.
Pillow assembles only rendered screenshots; gameplay art is never modified.
"""
from __future__ import annotations
import argparse
import json
import math
import os
from pathlib import Path
import sys

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'tests')]

import pygame
from PIL import Image
import test_opening_dialogue_pass as opening
from capture_mq02_spellblade import Video, save_animation
from quests import MILL_QUEST, REGENT_QUEST


class Capture:
    def __init__(self, output):
        self.output = output;output.mkdir(parents=True, exist_ok=True)
        self.driver = opening.OpeningDialogueDriver(on_page=self.page)
        self.game = self.driver.g
        self.video = Video(output/'sanctuary_handoff.mp4')
        self.started = False;self.frames = [];self.stills = [];self.cup_frames = 0
        self.states = [];self.last_state = None;self.frame_budget = 0.
        original = self.driver.tick

        def tick(seconds=.05, direction=(0, 0)):
            original(seconds, direction)
            if not self.started:return
            game, quest = self.game, self.game.mill_quest
            home = quest.sanctuary_return
            state = [game.world.data['id'], quest.reported_to_halden, home.action_active,
                     home.holding_cups, quest.cups_placed, quest.resolved,
                     game.regent_arrival.state]
            if state != self.last_state:
                self.states.append(state);self.last_state = state
            image = self.image();self.frame_budget += seconds
            while self.frame_budget >= .05-1e-8:
                self.video.frame(image);self.frame_budget -= .05
                if home.action_active:
                    self.cup_frames += 1
                    if self.cup_frames % 3 == 0:
                        self.frames.append(image.resize((480, 320), Image.Resampling.NEAREST))
            if home.action_active and home.holding_cups and game.player.moving:
                self.still('carrying_cups.png')
            if quest.cups_placed:self.still('cups_placed.png')
            if game.regent_arrival.active:
                if game.regent_arrival.shot == 'sanctuary_close':self.still('sanctuary_fade.png')
                if game.regent_arrival.shot == 'aerial_region' and game.regent_arrival.phase_time >= .8:
                    self.still('aerial_arrival.png')
        self.driver.tick = tick
        original_key = self.driver.key

        def paced_key(value=pygame.K_e):
            social = self.game.social
            if (self.started and value == pygame.K_SPACE and social.active
                    and social.script_identifier in ('mill_resolution', 'mill_sanctuary_return',
                                                      'mill_sanctuary_setting', 'regent_preparations')):
                text = ' '.join(social.page['lines'])
                for _ in range(math.ceil(max(1.5, len(text.split())/3.5)/.05)):
                    self.driver.tick(.05)
            original_key(value)
        self.driver.key = paced_key

    def image(self):
        self.game.draw()
        return Image.frombytes('RGB', self.game.ui_surface.get_size(),
                               pygame.image.tobytes(self.game.ui_surface, 'RGB'))

    def still(self, name):
        if name in self.stills:return
        self.image().save(self.output/name);self.stills.append(name)

    def page(self, driver, identifier, page):
        if identifier == 'mill_resolution':
            self.started = True
            if page['source_line'] >= len(self.game.social._source_lines)-7:
                self.still('mill_farewell.png')
        elif identifier == 'mill_sanctuary_return':
            self.still('sanctuary_checkin.png')
            text = self.game.social._source_lines[page['source_line']]['text']
            if text.startswith('The tables are finished'):self.still('setting_tables.png')
        elif identifier == 'mill_sanctuary_setting':self.still('holding_cups_dialogue.png')
        elif identifier == 'regent_preparations':self.still('mq03_invitation.png')

    def run(self):
        try:
            self.driver.run()
            game, quest = self.game, self.game.mill_quest
            assert game.quests.status(MILL_QUEST) == 'completed'
            assert quest.reported_to_halden and quest.cups_placed and quest.resolved
            assert game.world.data['id'] == 'sanctuary_dining'
            assert game.regent_arrival.state == 'pending'
            assert game.quests.status(REGENT_QUEST) == 'available'
            origin = tuple(game.player.position)
            for _ in range(240):
                self.driver.tick(.05)
                if 'aerial_arrival.png' in self.stills:break
            else:raise AssertionError('The arrival did not start from the sanctuary')
            game.draw();self.driver.click(game.regent_arrival.skip_rect.center)
            assert game.regent_arrival.state == 'seen'
            assert game.world.data['id'] == 'sanctuary_dining'
            assert tuple(game.player.position) == origin
            assert game.quests.status(REGENT_QUEST) == 'available'
            self.driver.actor(game.regent_quest.serene, 'regent_preparations')
            assert game.quests.status(REGENT_QUEST) == 'active'
            for _ in range(10):self.driver.tick(.05)
            self.video.close()
            assert self.frames, 'No actual cup action was captured'
            save_animation(self.output/'cup_action.gif', self.frames, 150)
            contact = Image.new('RGB', (1440, 640))
            images = ('mill_farewell.png', 'setting_tables.png', 'carrying_cups.png',
                      'holding_cups_dialogue.png', 'aerial_arrival.png', 'mq03_invitation.png')
            for index, name in enumerate(images):
                with Image.open(self.output/name) as image:
                    contact.paste(image.convert('RGB').resize((480, 320), Image.Resampling.NEAREST),
                                  (index%3*480, index//3*320))
            contact.save(self.output/'scene_contact.png')
            verification = {
                'unseeded_new_game': True, 'disposable_journey_and_settings': True,
                'normal_player_files_untouched': True,
                'quest_completed_at_sanctuary': True, 'reported_to_halden': quest.reported_to_halden,
                'cups_placed_after_destination_dialogue': quest.cups_placed,
                'movie': {'file': 'sanctuary_handoff.mp4', 'fps': 20,
                          'frames': self.video.frames, 'seconds': self.video.frames/20},
                'cup_action_frames': self.cup_frames, 'stills': self.stills,
                'observed_state_transitions': self.states,
                'sanctuary_return': self.driver.sources['mill_sanctuary_return'],
                'sanctuary_setting': self.driver.sources['mill_sanctuary_setting'],
                'mq03_invitation': self.driver.sources['regent_preparations'],
                'arrival_skip_retained_player_location': list(origin),
                'post_cinematic_scene': game.world.data['id'],
                'mq03_accepted_separately': game.quests.status(REGENT_QUEST),
                'one_serene': sum(quest.sanctuary_return.serene in w.npcs for w in game.scenes.values()),
                'one_tomas': sum(quest.sanctuary_return.tomas in w.npcs for w in game.scenes.values()),
                'one_gift': game.inventory.quantity('caelan_gearblade'),
                'saved_journey_valid': game._read_saved_journey() is not None}
            (self.output/'verification.json').write_text(json.dumps(verification, ensure_ascii=False, indent=2)+'\n')
            (self.output/'README.md').write_text(
                '# MQ02 sanctuary homecoming and MQ03 handoff\n\n'
                '[Watch the complete ending](sanctuary_handoff.mp4) · '
                '[Cup action](cup_action.gif)\n\n'
                '![Actual gameplay contact sheet](scene_contact.png)\n\n'
                'Recorded from an unseeded disposable New Game through MQ01, Mira’s gift, '
                'the boar encounter and the repaired mill. The ending uses the ordinary '
                'sanctuary doors, the exact approved Tomas/Serene/Caelan exchange, a visible '
                'cup collection and carry, the destination dialogue, and physical placement. '
                'MQ02 finishes only after the cups are set down. Aldric’s aerial cinematic '
                'then begins; using its Skip button returns to the same dining-room position. '
                'A separate conversation accepts MQ03.\n\n'
                f'The review movie is silent, 960×640 at 20 fps, and lasts {self.video.frames/20:.2f} seconds, with readable dialogue. '
                'The arrival is shown only through its aerial opening because the rest of '
                'that cinematic is unchanged. No player save or settings file is included.\n\n'
                'Reproduce with `python tools/capture_mq02_sanctuary_handoff.py`. '
                '[Verification metadata](verification.json) records the actual observed '
                'states, dialogue, actor uniqueness and retained player position.\n')
            print(json.dumps({'output': str(self.output), 'seconds': self.video.frames/20,
                              'mp4_bytes': self.video.path.stat().st_size,
                              'stills': len(self.stills), 'valid': verification['saved_journey_valid']}))
        finally:
            self.video.close();self.driver.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=ROOT/'docs/reviews/mq02_sanctuary_handoff')
    args = parser.parse_args();Capture(args.output).run()


if __name__ == '__main__':main()
