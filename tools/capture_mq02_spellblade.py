"""Capture the actual MQ02 gift, Spellblade lesson and blue-focus repair.

Starts a disposable New Game, uses the real opening quest driver, and never
seeds equipment, abilities, quest completion or battle attributes. Pillow only
assembles rendered frames into review GIFs; it does not alter game artwork.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import sys
import subprocess
import tempfile
from unittest.mock import patch

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'tests')]

import pygame
from PIL import Image
import test_opening_dialogue_pass as opening
from test_mq02_spellblade_gameplay import ATTEMPTS, WEAPON, drive_spellblade_battle
from quests import MILL_QUEST


class Video:
    """Stream real display-resolution frames without retaining a raw movie."""
    def __init__(self, path):
        self.path = path;self.frames = 0;self.closed = False
        self.log = tempfile.TemporaryFile()
        self.process = subprocess.Popen([
            'ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
            '-s', '960x640', '-r', '20', '-i', 'pipe:0', '-an', '-c:v', 'libx264',
            '-preset', 'fast', '-crf', '23', '-maxrate', '1M', '-bufsize', '2M',
            '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(path)],
            stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=self.log)

    def frame(self, image):
        if image.size != (960, 640):image = image.resize((960, 640), Image.Resampling.NEAREST)
        self.process.stdin.write(image.tobytes());self.frames += 1

    def close(self):
        if self.closed:return
        if self.process.stdin is not None and not self.process.stdin.closed:
            self.process.stdin.close()
        code = self.process.wait(timeout=60)
        self.log.seek(0);error = self.log.read().decode('utf-8', errors='replace')
        self.log.close();self.closed = True
        if code:raise RuntimeError('Video export failed: '+str(self.path)+'\n'+error)


def save_animation(path, frames, duration):
    if not frames:raise AssertionError('No rendered frames for '+str(path))
    sample = Image.new('RGB', (120*len(frames), 80))
    for index, frame in enumerate(frames):
        sample.paste(frame.resize((120, 80), Image.Resampling.NEAREST), (120*index, 0))
    palette = sample.quantize(colors=256, dither=Image.Dither.NONE)
    indexed = [frame.quantize(palette=palette, dither=Image.Dither.NONE) for frame in frames]
    indexed[0].save(path, save_all=True, append_images=indexed[1:], duration=duration,
                    loop=0, disposal=1, optimize=False)
    with Image.open(path) as result:return result.n_frames


class Capture:
    def __init__(self, output):
        self.output = output;output.mkdir(parents=True, exist_ok=True)
        self.driver = opening.OpeningDialogueDriver(on_page=self.page)
        self.game = self.driver.g
        self.game.audio.set_effects(1)
        self.stills, self.gift_shots, self.guidance = [], [], []
        self.frames = {'gift': [], 'water': []}
        self.actions = []
        self.water_focus = []
        self.gift_ticks = self.water_ticks = 0
        self.before_battle_receipts = None
        self.gear_click_time = None
        self.videos = {name: Video(output/(name+'.mp4'))
                       for name in ('gift', 'combat_lesson', 'water_focus')}
        original = self.driver.tick

        def tick(seconds=.05, direction=(0, 0)):
            clicked = self.game.mill_gift._gear_clicked
            original(seconds, direction)
            game, quest = self.game, self.game.mill_quest
            gift = game.mill_gift
            if gift.active:
                self.gift_ticks += 1
                shot = str(gift.shot)
                if shot not in self.gift_shots:self.gift_shots.append(shot)
                if self.gift_ticks % 3 == 0:
                    self.frame('gift')
                if gift._gear_clicked and not clicked:
                    self.gear_click_time = self.videos['gift'].frames/20
                self.videos['gift'].frame(self.image())
                threshold = {'gear': 3.2, 'handoff': 2.4}.get(shot, .7)
                if gift.phase_time >= threshold:
                    self.still('gift_'+shot+'.png')
            if quest.action == 'spell' and getattr(game.player, 'story_sprite', None) is not None:
                self.water_focus.append(quest.spell_focus)
                self.water_ticks += 1
                closeup = self.water_image()
                if self.water_ticks % 3 == 0:
                    self.frames['water'].append(closeup.resize((480, 320), Image.Resampling.NEAREST))
                self.videos['water_focus'].frame(closeup)
                if quest.action_time >= .8:self.still('water_focus_cast.png')
                if quest.action_time >= 1.2 and 'water_focus_closeup.png' not in self.stills:
                    closeup.save(self.output/'water_focus_closeup.png')
                    self.stills.append('water_focus_closeup.png')
        self.driver.tick = tick
        original_key = self.driver.key

        def paced_key(value=pygame.K_e):
            gift = self.game.mill_gift
            if gift.active and value in (pygame.K_SPACE, pygame.K_e, pygame.K_RETURN):
                line = gift.dialogue
                if line is not None:
                    # A person can read every page before acknowledging it.
                    seconds = max(1.5, len(line['text'].split())/3.5)
                    for _ in range(math.ceil(seconds/.05)):self.driver.tick(.05)
            original_key(value)
        self.driver.key = paced_key
        original_event = self.driver.mill_event

        def clear_notices_before_cast(kind):
            if kind == 'spell_intro':
                # Let real transient notices expire before reviewing the cast.
                # No UI owner or quest state is disabled for the capture.
                for _ in range(400):
                    ui = self.game.quest_ui
                    if ui.current_notice is None and not ui.notices:break
                    self.driver.tick(.05)
            original_event(kind)
        self.driver.mill_event = clear_notices_before_cast

    def image(self):
        self.game.draw()
        return Image.frombytes('RGB', self.game.ui_surface.get_size(),
                               pygame.image.tobytes(self.game.ui_surface, 'RGB'))

    def frame(self, group):
        self.frames[group].append(self.image().resize((480, 320), Image.Resampling.NEAREST))

    def water_image(self):
        image = self.image()
        point = self.game.player.position-pygame.Vector2(self.game.camera.position())
        rect = pygame.Rect(round(point.x-54), round(point.y-58), 192, 128)
        rect.clamp_ip(pygame.Rect(0, 0, 480, 320))
        width, height = image.size
        crop = image.crop((round(rect.left*width/480), round(rect.top*height/320),
                           round(rect.right*width/480), round(rect.bottom*height/320)))
        return crop.resize((960, 640), Image.Resampling.NEAREST)

    def add_gift_audio(self):
        assert self.gear_click_time is not None, 'The observed runtime gear click did not occur'
        source = ROOT/'assets/story/mill_gift/gear_click.ogg'
        target = self.output/'gift_with_audio.mp4'
        delay = round(self.gear_click_time*1000)
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', str(self.output/'gift.mp4'),
                        '-i', str(source), '-filter_complex',
                        f'[1:a]volume=0.14,adelay=delays={delay}:all=1,apad[a]',
                        '-map', '0:v:0', '-map', '[a]', '-c:v', 'copy', '-c:a', 'aac',
                        '-b:a', '96k', '-shortest', '-movflags', '+faststart', str(target)],
                       check=True)
        target.replace(self.output/'gift.mp4')

    def still(self, filename):
        if filename in self.stills:return
        self.game.draw()
        pygame.image.save(self.game.window, str(self.output/filename))
        self.stills.append(filename)

    def page(self, driver, identifier, page):
        names = {'mill_warning': 'armed_departure.png',
                 'mill_encounter_intro': 'monster_reveal.png',
                 'mill_aftermath': 'spellblade_aftermath.png',
                 'mill_encouragement_failed': 'small_magic_success.png',
                 'mill_repair_done': 'intake_restored.png',
                 'mill_verify': 'mill_running.png',
                 'mill_sanctuary_return': 'sanctuary_homecoming.png',
                 'mill_resolution': 'report_to_halden.png'}
        if identifier in names:self.still(names[identifier])

    def battle_frame(self, game, tag, action=None):
        names = {'ready': 'guard_lesson.png',
                 'skills_first_edge': 'first_focus_choices.png',
                 'skills_second_edge': 'second_focus_choices.png',
                 'resolved_guard': 'guard_action.png',
                 'resolved_nature_edge': 'failed_focus.png',
                 'resolved_aether_edge': 'aether_edge_strike.png',
                 'normal_controls': 'normal_party_controls.png',
                 'victory': 'victory.png',
                 'spoils': 'spoils_of_battle.png'}
        if tag in names:self.still(names[tag])
        if tag == 'guidance':
            text = str(action)
            if text not in self.guidance:self.guidance.append(text)
            for _ in range(math.ceil(max(1.5, len(text.split())/3.5)*20)):
                self.videos['combat_lesson'].frame(self.image())
                game.update(.05, (0, 0), False)
        elif tag in ('ready', 'skills_first_edge', 'skills_second_edge', 'normal_controls'):
            for _ in range(20):
                self.videos['combat_lesson'].frame(self.image())
                game.update(.05, (0, 0), False)

    def battle(self, game, *args, **kwargs):
        self.before_battle_receipts = len(game.battle_rewards.to_dict()['receipts'])
        original_step = kwargs.pop('on_step', None)

        def action_frame(scene):
            if original_step:original_step(scene)
            if (not game.combat.transitioning and not scene.tutorial_active
                    and scene.model.current_action is not None):
                self.videos['combat_lesson'].frame(self.image())

        scene = drive_spellblade_battle(game, *args, **kwargs, on_frame=self.battle_frame,
                                        on_step=action_frame,
                                        first='nature_edge', second='aqua_edge')
        self.actions = scene.review_trace
        self.reward = scene.model.enemy_definition['rewards']
        assert scene.model.phase == 'victory' and scene.model.aether_edge_discovered
        return scene

    def run(self):
        try:
            with patch.object(opening, 'finish_mill_battle', self.battle):self.driver.run()
            game, quest = self.game, self.game.mill_quest
            assert game.quests.status(MILL_QUEST) == 'completed'
            assert quest.spell_done and quest.restored and quest.aftermath_done
            assert game.inventory.quantity(WEAPON) == 1
            assert 'aether_edge' in game.character_abilities.known_abilities()
            assert set(ATTEMPTS).isdisjoint(game.character_abilities.known_abilities())
            assert set(self.water_focus) == {'water'}
            assert game._read_saved_journey() is not None
            assert game.quests.status('CH01_MQ03') == 'available'
            assert game.regent_arrival.state in ('pending', 'seen')
            assert quest.reported_to_halden and quest.cups_placed
            assert game.world.data['id'] == 'sanctuary_dining'
            game.update(.1, (0, 0), False)
            if game.regent_arrival.active:self.still('aldric_arrival.png')
            gift_frames = save_animation(self.output/'gift_preview.gif', self.frames['gift'], 150)
            water_frames = save_animation(self.output/'water_focus.gif', self.frames['water'], 150)
            sheet = Image.new('RGB', (1440, 640))
            for index, name in enumerate(('gift_handoff.png', 'gift_gear.png', 'failed_focus.png',
                                           'aether_edge_strike.png', 'water_focus_closeup.png',
                                           'spoils_of_battle.png')):
                with Image.open(self.output/name) as image:
                    sheet.paste(image.convert('RGB').resize((480, 320), Image.Resampling.NEAREST),
                                (index%3*480, index//3*320))
            sheet.save(self.output/'scene_contact.png')
            for video in self.videos.values():video.close()
            self.add_gift_audio()
            player = [action for action in self.actions if action['actor'] == 'player']
            assert [action['action'] for action in player[:3]] == ['guard', 'nature_edge', 'aether_edge']
            assert player[1]['damage'] == 0 and player[2]['damage'] > 0
            metadata = {'unseeded_new_game': True, 'disposable_journey_and_settings': True,
                        'normal_player_files_untouched': True, 'stills': self.stills,
                        'gift_shots': self.gift_shots, 'gift_frames': gift_frames,
                        'weapon_item': WEAPON, 'weapon_quantity': game.inventory.quantity(WEAPON),
                        'guidance': self.guidance, 'actions': self.actions,
                        'first_focus_failed': True, 'next_caelan_focus_produced_aether_edge': True,
                        'normal_party_controls_resumed': True, 'permanent_elemental_attempts': False,
                        'water_focus': sorted(set(self.water_focus)), 'water_frames': water_frames,
                        'prior_venn_failure_played': game.venn_visit.magicks_failed,
                        'quest_completed': True, 'mill_restored': True,
                        'reported_to_halden': quest.reported_to_halden,
                        'cups_placed': quest.cups_placed,
                        'completion_scene': game.world.data['id'],
                        'aldric_handoff': game.regent_arrival.state,
                        'battle_rewards': self.reward,
                        'receipts_before_battle': self.before_battle_receipts,
                        'receipts_after_quest': len(game.battle_rewards.to_dict()['receipts']),
                        'saved_journey_valid': True,
                        'dialogue_pages': len(self.driver.pages),
                        'gift_audio': {'source': 'assets/story/mill_gift/gear_click.ogg',
                                       'cue_seconds': self.gear_click_time, 'gain': .14,
                                       'method': 'Authored sound mixed at observed runtime cue'},
                        'videos': {name: {'file': name+'.mp4', 'fps': 20,
                                          'frames': video.frames,
                                          'seconds': video.frames/20}
                                   for name, video in self.videos.items()}}
            (self.output/'verification.json').write_text(json.dumps(metadata, indent=2)+'\n')
            print(json.dumps({'output': str(self.output), 'stills': len(self.stills),
                              'gift_frames': gift_frames, 'water_frames': water_frames,
                              'quest_completed': True, 'aldric_handoff': metadata['aldric_handoff']}))
        finally:
            for video in self.videos.values():video.close()
            self.driver.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'docs/reviews/mq02_spellblade')
    Capture(parser.parse_args(argv).output).run()


if __name__ == '__main__':main()
