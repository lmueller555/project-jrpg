"""Capture a real victory, one-shot fanfare and Spoils of Battle screen.

Game frames and mixer commands are production behavior. SDL's dummy audio device
cannot record loopback, so the MP4 soundtrack is rebuilt offline from those
commands and the exact runtime OGGs, including the fanfare's natural one-shot end.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import time
import wave
from unittest.mock import patch

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'tools'), str(ROOT/'tests')]

import numpy as np
import pygame
from main import Game
from ui_style import Painter
from capture_combat import fixture
from capture_battle_music_transition import MixerTrace, FPS, RATE
from test_mill_battle_gameplay import key, click


class OneShotTrace(MixerTrace):
    """Observe ordinary SDL calls and reconstruct finite or looping playback."""

    def __init__(self):
        super().__init__()
        self.loops = -1
        self.fanfare_eof = None

    def event(self, kind, **values):
        if (kind == 'volume' and self.events and self.events[-1]['event'] == 'volume'
                and self.events[-1].get('applied') == values.get('applied')):
            return
        super().event(kind, **values)

    def play(self, loops=0, start=0.0, fade_ms=0):
        assert fade_ms == 0, 'Preview expects the production clock-driven fade envelope'
        assert loops in (-1, 0), 'Unexpected repeat count'
        self.loops = loops
        self.position = round(start*RATE)
        self.playing = True
        self.paused = False
        self.event('play', file=str(Path(self.loaded).relative_to(ROOT)), loops=loops, start=start)

    def advance(self, seconds):
        count = round(seconds*RATE)
        block = np.zeros((count, 2), 'float32')
        if self.playing and not self.paused and self.loaded is not None:
            source = self.samples[self.loaded]
            if self.loops == -1:
                indices = (np.arange(count)+self.position) % len(source)
                block[:] = source[indices]*self.volume
                self.position = (self.position+count) % len(source)
            else:
                used = min(count, max(0, len(source)-self.position))
                block[:used] = source[self.position:self.position+used]*self.volume
                self.position += used
                if self.position >= len(source):
                    self.playing = False
                    if self.start is not None:
                        ended = self.clock + used/RATE - self.start
                        self.events.append(dict(time=round(ended, 6), event='decoded_source_end',
                            file=str(Path(self.loaded).relative_to(ROOT))))
                        if self.loaded.endswith('triumphal_fanfare.ogg'):
                            self.fanfare_eof = ended
        if self.start is not None and count:self.blocks.append(block)
        self.clock += seconds


class Capture:
    def __init__(self, output):
        self.output = output
        output.mkdir(parents=True, exist_ok=True)
        self.trace = OneShotTrace()
        self.encoder = None
        self.frame_count = 0
        self.screenshots = []
        self.phases = []
        self.requests = []
        self.wall_start = None
        self.last_post_phase = None
        self.reward_before = None
        self.reward_after = None
        self.banner_text = []
        self.spoils_text = []
        self.controller_completed_at = None

    @property
    def seconds(self):return self.frame_count/FPS

    def mark(self, phase, **values):
        self.phases.append(dict(time=round(self.seconds, 6), phase=phase, **values))

    def snapshot(self, name):
        self.game.draw()
        pygame.image.save(self.game.window, str(self.output/name))
        self.screenshots.append(name)

    def drawn_text(self):
        text = []
        original = Painter.text
        def record(painter, content, *args, **kwargs):
            text.append(str(content))
            return original(painter, content, *args, **kwargs)
        with patch.object(Painter, 'text', record):self.game.draw()
        return text

    def frame(self):
        self.game.update(1/FPS, (0, 0), False)
        post_phase = self.game.combat.post_phase if self.game.combat.active else None
        if post_phase != self.last_post_phase:
            if post_phase:self.mark(post_phase)
            self.last_post_phase = post_phase
        if self.game.music.completed and self.controller_completed_at is None:
            self.controller_completed_at = self.seconds
            self.mark('fanfare_completed_no_following_music')
        self.game.draw()
        self.encoder.stdin.write(pygame.image.tobytes(self.game.window, 'RGB'))
        self.frame_count += 1
        # Let the real SDL one-shot reach EOF. Headless frame generation alone
        # advances game clocks faster than the actual music device.
        target = self.wall_start+self.seconds
        delay = target-time.monotonic()
        if delay > 0:time.sleep(delay)

    def hold(self, seconds):
        for _ in range(round(seconds*FPS)):self.frame()

    def preroll(self):
        game = self.game
        game.world = game.town
        game.player.position.update(game.combat.position+(0, 24))
        game.player.facing = 'back'
        game.camera.reset()
        game.opening_fade = game.transfer_cooldown = 0
        assert game.combat.interaction_hint() == 'E: Engage Bat'
        key(game, pygame.K_e)
        assert game.combat.active
        game.combat.model.rng = random.Random(7)
        scene, model = game.combat.scene, game.combat.model
        # Play the battle itself, retaining normal starting attributes and HP.
        # Recording begins near its end; no enemy/player values are injected.
        for _ in range(6000):
            if model.waiting_for_player and model.enemy.hp <= 20:
                return
            if model.waiting_for_player:
                game.draw();click(game, scene.command_rects['attack'].center)
            else:game.update(.1, (0, 0), False)
            assert not model.ended, 'The preparatory battle ended before recording'
        raise AssertionError('Bat encounter did not reach its final attack')

    def record(self):
        game = self.game
        scene, model = game.combat.scene, game.combat.model
        self.reward_before = dict(rp=game.lattice.state()['rp'],
                                  emerald=game.inventory.quantity('aether_emerald'))
        game.audio.set_effects(0)
        game.audio.set_music(1)
        self.trace.begin()
        self.encoder = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo',
            '-pixel_format', 'rgb24', '-video_size', '960x640', '-framerate', str(FPS), '-i', '-',
            '-an', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '24', '-pix_fmt', 'yuv420p',
            str(self.output/'silent.mp4')], stdin=subprocess.PIPE)
        self.wall_start = time.monotonic()
        self.mark('final_attack_ready', enemy_hp=model.enemy.hp)
        self.snapshot('final_attack_ready.png')
        self.hold(1.0)
        for _ in range(600):
            if game.combat.post_phase is not None:break
            if model.waiting_for_player:
                game.draw();click(game, scene.command_rects['attack'].center)
            self.frame()
        else:raise AssertionError('Final attacks did not produce victory')
        assert model.phase == 'victory'
        assert game.music.desired_track == 'victory'
        assert game.lattice.state()['rp'] == self.reward_before['rp']
        self.hold(.35)
        self.snapshot('victory_banner.png')
        self.banner_text = self.drawn_text()
        assert 'VICTORY' in self.banner_text
        assert not any('RP' in text or 'Emerald' in text for text in self.banner_text)
        for _ in range(150):
            if game.combat.post_phase == 'spoils' and game.combat.spoils.awarded:break
            self.frame()
        else:raise AssertionError('Victory did not reach awarded Spoils')
        spoils = game.combat.spoils
        self.snapshot('spoils_of_battle.png')
        self.spoils_text = self.drawn_text()
        assert 'Spoils of Battle' in self.spoils_text
        assert 'Resonance Points (RP)' in self.spoils_text
        self.reward_after = dict(rp=game.lattice.state()['rp'],
                                 emerald=game.inventory.quantity('aether_emerald'))
        assert self.reward_after == dict(rp=self.reward_before['rp']+20,
                                         emerald=self.reward_before['emerald']+1)
        assert game.combat.active and game.music.desired_track == 'victory'
        self.mark('rewards_received_in_spoils', rewards=self.reward_after)
        for _ in range(300):
            if game.music.completed and self.trace.fanfare_eof is not None:break
            self.frame()
        else:raise AssertionError('The real one-shot fanfare did not finish')
        self.mark('silence_review_started')
        before = len([e for e in self.trace.events if e['event'] == 'play'])
        silence_start = self.frame_count
        self.hold(2.6)
        silence = np.concatenate(self.trace.blocks[silence_start:])
        assert len(silence) and np.max(np.abs(silence)) == 0
        assert before == len([e for e in self.trace.events if e['event'] == 'play'])
        assert game.music.completed and not game.music.playing
        assert game.combat.spoils is spoils and spoils.awarded
        self.snapshot('spoils_after_fanfare_silence.png')
        self.silence_seconds = (self.frame_count-silence_start)/FPS

        normal_size = game.window.get_size()
        normal_scale = game.audio.text_scale
        game.window = pygame.display.set_mode((480, 320), pygame.RESIZABLE)
        game.audio.set_text_scale(1.5)
        self.snapshot('spoils_minimum_large_text.png')
        game.window = pygame.display.set_mode(normal_size, pygame.RESIZABLE)
        game.audio.set_text_scale(normal_scale)
        game.draw()
        click(game, spoils.continue_rect.center)
        game.update(0, (0, 0), False)
        assert not game.combat.active
        assert game.music.desired_track == 'eldenmere'
        assert self.reward_after == dict(rp=game.lattice.state()['rp'],
                                         emerald=game.inventory.quantity('aether_emerald'))
        self.mark('continue_returns_to_world_music')
        self.hold(1.8)
        self.snapshot('returned_world.png')
        assert game._read_saved_journey() is not None

    def run(self):
        self.trace.install()
        original_update = Game.update
        def update(game, seconds, *args, **kwargs):
            result = original_update(game, seconds, *args, **kwargs)
            self.trace.advance(seconds)
            return result
        try:
            with patch.object(Game, 'update', update), fixture() as game:
                self.game = game
                original_play = game.music.play
                def play(identifier, *args, **kwargs):
                    if self.trace.start is not None:
                        self.requests.append(dict(time=round(self.seconds, 6), track=identifier))
                    return original_play(identifier, *args, **kwargs)
                game.music.play = play
                self.preroll()
                self.record()
            self.encoder.stdin.close()
            if self.encoder.wait() != 0:raise RuntimeError('Video encoding failed')
            audio = np.concatenate(self.trace.blocks)
            assert len(audio) == self.frame_count*(RATE//FPS)
            assert np.max(np.abs(audio)) < 1
            wav = self.output/'soundtrack.wav'
            with wave.open(str(wav), 'wb') as target:
                target.setparams((2, 2, RATE, 0, 'NONE', 'not compressed'))
                target.writeframes(np.round(audio*32767).astype('<i2').tobytes())
            video = self.output/'victory_spoils.mp4'
            subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', str(self.output/'silent.mp4'),
                '-i', str(wav), '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k',
                '-movflags', '+faststart', '-shortest', str(video)], check=True)
            self.output.joinpath('silent.mp4').unlink()
            wav.unlink()
            victory_plays = [e for e in self.trace.events if e['event'] == 'play'
                             and e['file'].endswith('triumphal_fanfare.ogg')]
            assert len(victory_plays) == 1 and victory_plays[0]['loops'] == 0
            metadata = dict(temporary_journey_and_settings=True,
                normal_player_files_untouched=True,
                prior_quest_fixture='Legitimate completed legacy MQ02 unlocks optional Bat; combat is played with normal starting stats and real commands, recording starts before the final attack',
                video_frames=self.frame_count, video_fps=FPS, duration_seconds=self.seconds,
                screenshots=self.screenshots, phases=self.phases, music_requests=self.requests,
                mixer_initial_state=self.trace.initial, mixer_events=self.trace.events,
                fanfare_plays=len(victory_plays), fanfare_loop_count=0,
                controller_observed_natural_eof=self.controller_completed_at is not None,
                controller_completed_at=self.controller_completed_at,
                decoded_fanfare_end_seconds=self.trace.fanfare_eof,
                silent_spoils_seconds=self.silence_seconds,
                no_music_during_silent_spoils=True,
                reward_before=self.reward_before, reward_after=self.reward_after,
                rewards_awarded_before_continue=True, continue_did_not_award_again=True,
                no_in_battle_reward_text=True,
                banner_text=self.banner_text, spoils_text=self.spoils_text,
                source_audio={str(Path(p).relative_to(ROOT)):hashlib.sha256(Path(p).read_bytes()).hexdigest()
                              for p in self.trace.samples},
                soundtrack='Offline reconstruction from exact runtime OGGs and observed production mixer commands; not hardware loopback. One-shot source stops at its natural end. Effects muted.',
                game_integration=True)
            self.output.joinpath('verification.json').write_text(json.dumps(metadata, indent=2)+'\n')
            self.output.joinpath('README.md').write_text('''# Victory and Spoils of Battle review

[Watch victory, the fanfare and Spoils of Battle](victory_spoils.mp4).

The production Bat fight is played with Caelan's normal starting attributes and
real commands. Recording begins before the final attack. Enemy/player HP and
damage are never edited for the preview. The temporary fixture unlocks the Bat
through a legitimate completed legacy mill journey.

The last enemy's defeat starts **Triumphal Fanfare** once and shows the victory
banner. The scene then fades to a separate **Spoils of Battle** screen, where
Caelan receives 20 Resonance Points and one Aether Emerald. The fanfare reaches
its natural end, followed by 2.6 seconds of verified silence while Spoils stays
open. Continue returns to the world and its Eldenmere Theme without re-awarding.

![Victory banner](victory_banner.png)
![Spoils of Battle](spoils_of_battle.png)
![Minimum window at 150% text](spoils_minimum_large_text.png)

Video frames are captured directly from the game at 960×640 and 30 FPS. SDL's
dummy audio device cannot record loopback; the MP4 soundtrack is reconstructed
offline from the exact runtime OGGs and observed production mixer commands,
including one-shot playback, fades and the natural source ending. The capture
also runs at real time during recording so the production controller observes
the actual SDL one-shot completion. Effects are muted for music review.

The [verification record](verification.json) includes reward timing, once-only
fanfare playback, natural EOF, the silent interval, mixer events and source
hashes. Temporary journey/settings files keep normal player files untouched.

Reproduce with:

```sh
python tools/capture_victory_spoils.py --output work/victory-spoils
```
''')
            paths = ['tools/capture_victory_spoils.py']
            paths += [str(path.relative_to(ROOT)) for path in sorted(self.output.iterdir()) if path.is_file()]
            (ROOT/'work/victory-spoils-preview-paths.json').write_text(json.dumps(paths, indent=2)+'\n')
            print(json.dumps(dict(output=str(self.output), seconds=self.seconds,
                frames=self.frame_count, video_bytes=video.stat().st_size,
                silence_seconds=self.silence_seconds, one_shot_plays=len(victory_plays))))
        finally:
            if self.encoder is not None and self.encoder.poll() is None:
                if self.encoder.stdin and not self.encoder.stdin.closed:self.encoder.stdin.close()
                self.encoder.wait()
            self.trace.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'docs/reviews/victory_spoils')
    Capture(parser.parse_args().output).run()
