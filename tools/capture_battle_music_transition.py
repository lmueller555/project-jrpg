"""Capture real MQ02 music cues and battle entry using a disposable journey.

Video frames come from the production game. SDL's dummy device cannot record
audio, so the MP4 soundtrack is reconstructed from the supplied runtime tracks
and the actual mixer load/play/volume/pause commands emitted during capture.
This is documented in the review metadata rather than presented as loopback.
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
from unittest.mock import patch
import wave

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'tests')]

import numpy as np
import pygame
from main import Game
from npc_routines import find_path
from test_mill_battle_gameplay import MillBattleGameplayTests, key, click

FPS = 30
RATE = 48000


class MixerTrace:
    """Observe production calls; reconstruct only the requested soundtrack."""

    def __init__(self):
        self.clock = 0.0
        self.start = None
        self.loaded = None
        self.samples = {}
        self.position = 0
        self.playing = False
        self.paused = False
        self.volume = 0.0
        self.events = []
        self.blocks = []
        self.patchers = []
        self.initial = None

    def event(self, kind, **values):
        if self.start is not None:
            self.events.append(dict(time=round(self.clock-self.start, 6), event=kind, **values))

    def install(self):
        handlers = dict(load=self.load, play=self.play, stop=self.stop,
                        set_volume=self.set_volume, pause=self.pause, unpause=self.unpause)
        for name, handler in handlers.items():
            original = getattr(pygame.mixer.music, name)
            def wrapped(*args, _original=original, _handler=handler, **kwargs):
                result = _original(*args, **kwargs)
                _handler(*args, **kwargs)
                return result
            patcher = patch.object(pygame.mixer.music, name, wrapped)
            patcher.start();self.patchers.append(patcher)

    def close(self):
        for patcher in reversed(self.patchers):patcher.stop()

    def load(self, path, *args, **kwargs):
        self.loaded = str(Path(path).resolve())
        self.position = 0;self.playing = False;self.paused = False
        if self.loaded not in self.samples:
            result = subprocess.run(['ffmpeg', '-v', 'error', '-i', self.loaded,
                '-f', 'f32le', '-acodec', 'pcm_f32le', '-ar', str(RATE), '-ac', '2', '-'],
                stdout=subprocess.PIPE, check=True)
            self.samples[self.loaded] = np.frombuffer(result.stdout, '<f4').reshape(-1, 2)
        self.event('load', file=str(Path(self.loaded).relative_to(ROOT)))

    def play(self, loops=0, start=0.0, fade_ms=0):
        assert fade_ms == 0, 'This capture expects controller-clocked fades, not SDL wall-clock fades'
        assert loops == -1, 'Review soundtrack expects the production looping music stream'
        self.position = round(start*RATE)
        self.playing = True;self.paused = False
        self.event('play', file=str(Path(self.loaded).relative_to(ROOT)), loops=loops, start=start)

    def stop(self):
        self.playing = False;self.paused = False
        self.event('stop')

    def set_volume(self, volume):
        self.volume = pygame.mixer.music.get_volume()
        self.event('volume', requested=float(volume), applied=self.volume)

    def pause(self):
        self.paused = True;self.event('pause')

    def unpause(self):
        self.paused = False;self.event('unpause')

    def begin(self):
        self.start = self.clock
        self.initial = dict(file=str(Path(self.loaded).relative_to(ROOT)) if self.loaded else None,
            position_frames=self.position, playing=self.playing, paused=self.paused, volume=self.volume)

    def advance(self, seconds):
        count = round(seconds*RATE)
        block = np.zeros((count, 2), 'float32')
        if self.playing and not self.paused and self.loaded is not None:
            source = self.samples[self.loaded]
            indices = (np.arange(count)+self.position) % len(source)
            block[:] = source[indices]*self.volume
            self.position = (self.position+count) % len(source)
        if self.start is not None and count:self.blocks.append(block)
        self.clock += seconds


class Capture:
    def __init__(self, output):
        self.output = output
        output.mkdir(parents=True, exist_ok=True)
        self.trace = MixerTrace()
        self.frame_count = 0
        self.screenshots = []
        self.phases = []
        self.request_log = []
        self.freeze_checks = 0
        self.encoder = None
        self.case = None

    @property
    def seconds(self):return self.frame_count/FPS

    def mark(self, phase, **values):
        self.phases.append(dict(time=round(self.seconds, 6), phase=phase, **values))

    def snapshot(self, name):
        self.game.draw()
        pygame.image.save(self.game.window, str(self.output/name))
        self.screenshots.append(name)

    def frame(self):
        game = self.game
        transition = game.combat.transitioning
        if transition:
            model = game.combat.model
            before = (tuple(member.atb for member in (*model.party, model.enemy)),
                      model.phase, game.elapsed_ms, tuple(game.player.position))
        game.update(1/FPS, (0, 0), False)
        if transition:
            after = (tuple(member.atb for member in (*model.party, model.enemy)),
                     model.phase, game.elapsed_ms, tuple(game.player.position))
            assert before == after, 'Entry transition advanced battle or world clocks'
            self.freeze_checks += 1
        game.draw()
        self.encoder.stdin.write(pygame.image.tobytes(game.window, 'RGB'))
        self.frame_count += 1

    def hold(self, seconds):
        for _ in range(round(seconds*FPS)):self.frame()

    def advance(self):
        key(self.game, pygame.K_SPACE)
        self.game.update(0, (0, 0), False)

    def walk_to_encounter(self):
        game = self.game
        route = find_path(game.world, game.player.position, (180, 374), game.world.probe_size, None)
        assert route is not None
        for corner in route:
            for _ in range(1000):
                if game.social.script_identifier == 'mill_encounter_intro':return
                delta = pygame.Vector2(corner)-game.player.position
                if delta.length() < .04:break
                game.update(min(.05, delta.length()/72), delta, False)
        for _ in range(300):
            if game.social.script_identifier == 'mill_encounter_intro':return
            game.update(.05, (0, 0), False)
        raise AssertionError('Real upstream approach did not start the encounter dialogue')

    def record(self):
        game = self.game
        # Skip earlier tree observations using normal acknowledgement. Recording
        # starts before Mira's warning cue, with the village theme still selected.
        while game.social.page['source_line'] < 4:self.advance()
        assert game.music.desired_track == 'eldenmere'
        game.audio.set_music(1)
        game.audio.set_effects(0)
        self.trace.begin()
        self.encoder = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo',
            '-pixel_format', 'rgb24', '-video_size', '960x640', '-framerate', str(FPS), '-i', '-',
            '-an', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '24', '-pix_fmt', 'yuv420p',
            str(self.output/'silent.mp4')], stdin=subprocess.PIPE)
        cue_seen = False
        while game.social.script_identifier == 'mill_encounter_intro':
            page = game.social.page
            cue = page.get('cue') == 'mill_battle_music'
            if cue:
                assert not cue_seen
                assert game.music.desired_track == 'battle'
                cue_seen = True;self.cue_seconds = self.seconds
                self.mark('mira_back_away_music_cue', text=' '.join(page['lines']))
                self.snapshot('mira_music_cue.png')
            elif not cue_seen:
                assert game.music.desired_track == 'eldenmere'
                if not self.screenshots:self.snapshot('before_music_cue.png')
            self.hold(3.1 if cue else 2.2 if page['source_line'] == 5 else 1.7)
            self.advance()
        assert cue_seen and game.combat.active and game.combat.transitioning
        self.mark('transition_started')
        game.combat.model.rng = random.Random(7)
        transition_phases = set()
        while game.combat.transitioning:
            phase = game.combat.transition.phase
            if phase == 'closing' and game.combat.transition.elapsed > .12 and phase not in transition_phases:
                transition_phases.add(phase);self.snapshot('transition_closing.png')
            if phase == 'revealing' and phase not in transition_phases:
                transition_phases.add(phase);self.snapshot('transition_reveal.png')
            self.frame()
        self.mark('battle_revealed')
        assert not any(member.atb for member in (*game.combat.model.party, game.combat.model.enemy))
        assert game.music.desired_track == 'battle'
        scene = game.combat.scene
        used_attack = False
        seen_tutorial = set()
        for _ in range(2000):
            if scene.tutorial_active:
                text = scene.tutorial_text
                if text not in seen_tutorial:
                    seen_tutorial.add(text);self.mark('tutorial', text=text)
                    self.snapshot('battle_guidance.png') if 'battle_guidance.png' not in self.screenshots else None
                    self.hold(1.8)
                self.advance()
            elif scene.model.ended:
                assert scene.model.phase == 'fled'
                self.mark('withdrawal_result')
                self.hold(.8)
                click(game, scene.continue_rect.center)
                game.update(0, (0, 0), False)
                assert not game.combat.active and not game.mill_quest.encounter_cleared
                assert game.music.desired_track == 'eldenmere'
                self.mark('returned_to_safe_approach')
                self.hold(2.2);self.snapshot('returned_world.png')
                return
            elif scene.model.waiting_for_player:
                game.draw()
                if not used_attack:
                    used_attack = True;self.mark('mira_spear_thrust')
                    click(game, scene.command_rects['attack'].center)
                else:
                    self.mark('caelan_flee')
                    click(game, scene.command_rects['flee'].center)
                self.frame()
            else:self.frame()
        raise AssertionError('Review battle did not reach a safe withdrawal')

    def run(self):
        self.trace.install()
        original_update = Game.update
        def update(game, seconds, *args, **kwargs):
            result = original_update(game, seconds, *args, **kwargs)
            self.trace.advance(seconds)
            return result
        try:
            with patch.object(Game, 'update', update):
                self.case = MillBattleGameplayTests('runTest')
                self.case.setUp()
                self.game = self.case.game
                original_play = self.game.music.play
                def play(identifier, *args, **kwargs):
                    if self.trace.start is not None:
                        self.request_log.append(dict(time=round(self.seconds, 6), track=identifier))
                    return original_play(identifier, *args, **kwargs)
                self.game.music.play = play
                self.case.diagnose();self.case.enter_path();self.walk_to_encounter()
                self.record()
            self.encoder.stdin.close()
            if self.encoder.wait() != 0:raise RuntimeError('Video encoding failed')
            audio = np.concatenate(self.trace.blocks)
            assert len(audio) == self.frame_count*(RATE//FPS)
            assert np.max(np.abs(audio)) < 1
            with wave.open(str(self.output/'soundtrack.wav'), 'wb') as target:
                target.setparams((2, 2, RATE, 0, 'NONE', 'not compressed'))
                target.writeframes(np.round(audio*32767).astype('<i2').tobytes())
            subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', str(self.output/'silent.mp4'),
                '-i', str(self.output/'soundtrack.wav'), '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k',
                '-movflags', '+faststart', '-shortest', str(self.output/'battle_music_transition.mp4')], check=True)
            self.output.joinpath('silent.mp4').unlink()
            self.output.joinpath('soundtrack.wav').unlink()
            battle_plays = [e for e in self.trace.events if e['event'] == 'play' and e['file'].endswith('kindled_courage.ogg')]
            assert len(battle_plays) == 1, 'The early battle theme restarted on battle entry'
            assert battle_plays[0]['time'] >= self.cue_seconds
            metadata = dict(temporary_journey_and_settings=True, normal_player_files_untouched=True,
                prior_quest_fixture='MQ01 completed through public quest APIs; MQ02 reunion/diagnosis and north-road entry played with existing test fixture station placement; encounter approach uses production walking',
                video_frames=self.frame_count, video_fps=FPS, duration_seconds=self.seconds,
                screenshots=self.screenshots, phases=self.phases, mixer_initial_state=self.trace.initial,
                music_requests=self.request_log, mixer_events=self.trace.events,
                battle_track_play_count=len(battle_plays), transition_frozen_clock_checks=self.freeze_checks,
                music_selected_at_mira_page=True, music_not_restarted_on_battle_entry=True,
                soundtrack='Offline reconstruction from exact supplied OGG streams and production mixer commands; not hardware loopback. Effects muted for music review.',
                source_audio={str(Path(p).relative_to(ROOT)):hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in self.trace.samples},
                outcome='Flee: safe approach, no quest completion or rewards', game_integration=True)
            self.output.joinpath('verification.json').write_text(json.dumps(metadata, indent=2)+'\n')
            self.output.joinpath('README.md').write_text('''# User music and battle-entry review

[Watch the recorded scene with music](battle_music_transition.mp4).

The production game shows Mira's warning, starts the supplied **Kindled Courage**
track on “Easy, Caelan. Back slowly. Keep your feet under you,” then closes a
brief curtain over the actual world before revealing the riverbank battle.
The same music stream continues through entry, ATB decisions and guidance.
Mira demonstrates a spear thrust; Caelan withdraws through the real Flee command,
returning to the safe approach and the supplied **Eldenmere Theme**.

![Mira's music cue](mira_music_cue.png)
![World curtain](transition_closing.png)
![Battle guidance](battle_guidance.png)

Video frames are captured directly from the game at 960×640 and 30 FPS. Because
SDL's headless audio device cannot provide loopback recording, the MP4 soundtrack
is reconstructed offline from the exact runtime OGGs and observed production
mixer load/play/volume/pause commands. It includes the real controller's fade and
duck levels; effects are muted so the music can be reviewed clearly.

The disposable journey seeds completed MQ01 through public quest APIs. Existing
test helpers place actors at the prelude interaction stations, play MQ02's
reunion, diagnosis and departure, and then walk the actual upstream approach.
Captured dialogue, commands, transition, battle clocks and return are production
behavior. No ordinary journey or settings file is used.

The [verification record](verification.json) includes the cue time, music and
mixer events, per-frame frozen-clock checks, source hashes and safe withdrawal.
It verifies that the battle track starts once on Mira's page and does not
restart when the battle opens.

Reproduce with:

```sh
python tools/capture_battle_music_transition.py --output work/battle-music-transition
```
''')
            print(json.dumps(dict(output=str(self.output), seconds=self.seconds, frames=self.frame_count,
                bytes=self.output.joinpath('battle_music_transition.mp4').stat().st_size,
                battle_track_play_count=len(battle_plays), transition_frozen_clock_checks=self.freeze_checks)))
        finally:
            if self.encoder is not None and self.encoder.poll() is None:
                if self.encoder.stdin and not self.encoder.stdin.closed:self.encoder.stdin.close()
                self.encoder.wait()
            self.trace.close()
            if self.case is not None:
                self.case.tearDown();self.case.doCleanups()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'docs/reviews/battle_music_transition')
    Capture(parser.parse_args().output).run()
