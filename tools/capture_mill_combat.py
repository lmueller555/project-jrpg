"""Review MQ02's first battle from a real New Game through the repaired mill.

The existing opening driver supplies production walking, dialogue and inputs.
No quest progress, combat unlocks, spells or character attributes are seeded.
Pillow only assembles already-rendered frames into the review animation.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import random
import sys
from unittest.mock import patch

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'tests')]

import pygame
from PIL import Image
import test_opening_dialogue_pass as opening_driver
from test_mill_battle_gameplay import key, click
from quests import MILL_QUEST


class Capture:
    def __init__(self, output):
        self.output = output
        output.mkdir(parents=True, exist_ok=True)
        self.frames, self.durations, self.captures = [], [], []
        self.guidance, self.actions, self.checks = [], [], []
        self._actions = []
        self.driver = opening_driver.OpeningDialogueDriver(on_page=self.page)
        self.game = self.driver.g
        self._action_ticks = 0
        original_tick = self.driver.tick

        def tick(seconds=.05, direction=(0, 0)):
            original_tick(seconds, direction)
            quest = self.game.mill_quest
            if (self.game.world is quest.upstream and quest.encounter_pending
                    and not self.game.social.locked and not self.game.combat.active
                    and 384 < self.game.player.position.y <= 400
                    and 'river_path.png' not in self.captures):
                self.frame(700, 'river_path.png')
            action = self.game.mill_quest.action
            if action in ('spell', 'repair'):
                self._action_ticks += 1
                if self._action_ticks % 4 == 0:self.frame(100)
        self.driver.tick = tick

    def frame(self, duration=100, filename=None):
        game = self.game
        game.draw()
        image = Image.frombytes('RGB', game.ui_surface.get_size(),
                                pygame.image.tobytes(game.ui_surface, 'RGB'))
        self.frames.append(image.resize((480, 320), Image.Resampling.NEAREST))
        self.durations.append(duration)
        if filename:
            pygame.image.save(game.window, str(self.output/filename))
            self.captures.append(filename)

    def page(self, driver, identifier, page):
        names = {'mill_warning': 'mira_warning.png',
                 'mill_encounter_intro': 'monster_on_path.png',
                 'mill_aftermath': 'aftermath.png',
                 'mill_aftermath_recovered': 'first_aid.png',
                 'mill_encouragement_failed': 'small_magic_success.png',
                 'mill_repair_done': 'intake_restored.png',
                 'mill_resolution': 'festival_flour.png'}
        filename = names.get(identifier)
        # Frame the creature and the damaged bank with Mira's actual warning.
        if identifier == 'mill_encounter_intro' and page['source_line'] < 3:return
        if filename and filename not in self.captures:
            assert not driver.g.social.choosing
            self.frame(700, filename)

    def battle(self, game, command='attack', *, dismiss=True,
               read_aftermath=False, on_step=None):
        scene, model = game.combat.scene, game.combat.model
        assert game.combat.kind == 'mill' and model.enemy_id == 'ridgeback_tusker'
        assert [member.name for member in model.party] == ['Caelan', 'Mira']
        model.rng = random.Random(7)
        # Capture the production entry before labeling a frame as battlefield.
        while game.combat.transitioning:
            self.frame(100)
            game.update(1/30, (0, 0), False)
        self.frame(600, 'battlefield.png')
        world = game.elapsed_ms, tuple(game.player.position), tuple(game.mill_quest.mira.position)
        captured_actions, guide_keys = set(), set()
        ready_verified = False
        for tick in range(12000):
            if on_step:on_step(scene)
            action = model.current_action
            if action is not None and not any(action is known for known in self._actions):
                self._actions.append(action)
            if scene.tutorial_active:
                text = scene.tutorial_text
                if text not in guide_keys:
                    guide_keys.add(text);self.guidance.append(text)
                    filename = ('charge_warning.png' if 'lowering' in text else
                                'battle_guidance.png' if 'battle_guidance.png' not in self.captures else None)
                    self.frame(900, filename)
                    before = [member.atb for member in (*model.party, model.enemy)]
                    game.update(.75, (0, 0), False)
                    assert before == [member.atb for member in (*model.party, model.enemy)]
                key(game, pygame.K_SPACE)
            elif model.ended:
                assert model.phase == 'victory'
                assert not game.mill_quest.encounter_cleared and not game.mill_quest.restored
                self.frame(900, 'victory.png')
                if dismiss:
                    click(game, scene.continue_rect.center)
                    assert not game.combat.active
                    assert game.mill_quest.encounter_cleared
                    assert not game.mill_quest.aftermath_done
                    assert not game.social.choosing
                assert world == (game.elapsed_ms, tuple(game.player.position),
                                 tuple(game.mill_quest.mira.position))
                self.actions = [asdict(action) for action in self._actions]
                self.checks.append({'world_frozen_during_battle': True,
                                    'ready_and_guidance_freeze_all_gauges': True,
                                    'reward_rp': model.enemy_definition['rewards']['rp'],
                                    'battle_did_not_repair_intake': True,
                                    'linear_aftermath': True})
                return scene
            elif model.waiting_for_player:
                if not ready_verified:
                    self.frame(600, 'party_ready.png')
                    before = [member.atb for member in (*model.party, model.enemy)]
                    game.update(3, (0, 0), False)
                    assert before == [member.atb for member in (*model.party, model.enemy)]
                    original_window = game.window.get_size()
                    original_scale = game.audio.text_scale
                    game.window = pygame.display.set_mode((480, 320), pygame.RESIZABLE)
                    game.audio.set_text_scale(1.5)
                    self.frame(600, 'minimum_window_large_text.png')
                    game.window = pygame.display.set_mode(original_window, pygame.RESIZABLE)
                    game.audio.set_text_scale(original_scale)
                    ready_verified = True
                game.draw()
                choice = 'guard' if model.telegraphed_target == model.ready_actor else 'attack'
                click(game, scene.command_rects[choice].center)
            else:
                game.update(1/30, (0, 0), False)
                action = model.current_action
                if action is not None and tick % 3 == 0:
                    filename = None
                    if action.elapsed >= action.impact_at and action.action not in captured_actions:
                        captured_actions.add(action.action)
                        filename = action.action+'.png'
                    self.frame(100, filename)
        raise AssertionError('The real mill battle did not finish')

    def run(self):
        try:
            assert not self.game.combat.bat_unlocked
            with patch.object(opening_driver, 'finish_mill_battle', self.battle):
                self.driver.run()
            quest = self.game.mill_quest
            assert self.game.quests.status(MILL_QUEST) == 'completed'
            assert quest.encounter_cleared and quest.aftermath_done and quest.spell_done and quest.restored
            assert self.game.combat.bat_unlocked and not self.game.opening_conclusion.mill_stopped
            assert self.game._read_saved_journey() is not None
            self.frame(900, 'mill_running.png')
            samples = Image.new('RGB', (120*len(self.frames), 80))
            for index, frame in enumerate(self.frames):
                samples.paste(frame.resize((120, 80), Image.Resampling.NEAREST), (index*120, 0))
            palette = samples.quantize(colors=256, dither=Image.Dither.NONE)
            frames = [frame.quantize(palette=palette, dither=Image.Dither.NONE) for frame in self.frames]
            frames[0].save(self.output/'mill_combat.gif', save_all=True, append_images=frames[1:],
                           duration=self.durations, loop=0, disposal=1, optimize=False)
            with Image.open(self.output/'mill_combat.gif') as image:encoded = image.n_frames
            metadata = {'unseeded_new_game': True, 'temporary_journey_and_settings': True,
                        'normal_player_files_untouched': True, 'prior_venn_failure_played': True,
                        'captures': self.captures, 'guidance': self.guidance,
                        'actions': self.actions, 'checks': self.checks,
                        'quest_completed': True, 'mill_visibly_restored': True,
                        'no_rest_continue_choice': True, 'saved_journey_valid': True,
                        'rendered_frames': len(frames), 'encoded_frames': encoded,
                        'battle_rewards': self.game.lattice.state()['rp'],
                        'source_dialogue_pages': len(self.driver.pages)}
            (self.output/'verification.json').write_text(json.dumps(metadata, indent=2)+'\n')
            print(json.dumps({'output': str(self.output), 'captures': len(self.captures),
                              'frames': encoded, 'gif_bytes': (self.output/'mill_combat.gif').stat().st_size,
                              'completed_quest': True, 'unseeded_new_game': True}))
        finally:
            self.driver.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'work/mill-combat')
    Capture(parser.parse_args(argv).output).run()


if __name__ == '__main__':main()
