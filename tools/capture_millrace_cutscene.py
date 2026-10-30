"""Capture the production millrace arrival, scripted camera and battle handoff.

Frames are rendered by the game. The soundtrack is reconstructed from the exact
runtime OGGs and observed mixer commands because SDL dummy has no loopback.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch
import wave

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'tests'), str(ROOT/'tools')]

import numpy as np
import pygame
from main import Game
from capture_battle_music_transition import MixerTrace, FPS, RATE
from test_mill_battle_gameplay import MillBattleGameplayTests, key


class Capture:
    def __init__(self, output):
        self.output = output
        self.output.mkdir(parents=True, exist_ok=True)
        self.trace = MixerTrace()
        self.case = None
        self.encoder = None
        self.frames = 0
        self.screenshots = []
        self.events = []
        self.requests = []
        self.positions = []
        self.actor_checks = 0
        self.hold_checks = 0
        self.entry_checks = 0
        self._fixed_actors = None
        self._boar_origin = None
        self._last_phase = None

    @property
    def seconds(self):return self.frames/FPS

    def mark(self, event, **values):
        self.events.append(dict(time=round(self.seconds, 6), event=event, **values))

    def snapshot(self, name):
        self.game.draw()
        pygame.image.save(self.game.window, str(self.output/name))
        if name not in self.screenshots:self.screenshots.append(name)

    def actor_positions(self):
        return tuple(self.game.player.position), tuple(self.game.mill_quest.mira.position)

    def frame(self):
        game, quest = self.game, self.game.mill_quest
        transition = game.combat.transitioning
        before = None
        if transition:
            model = game.combat.model
            before = (game.elapsed_ms, self.actor_positions(), model.phase,
                      tuple(member.atb for member in (*model.party, model.enemy)))
        if not game.handle_events():raise RuntimeError('Capture closed unexpectedly')
        game.update(1/FPS, (0, 0), False)
        phase = quest.encounter_cutscene_phase
        if phase != self._last_phase:
            self.mark('cutscene_phase', phase=phase, camera=game.camera.position())
            self._last_phase = phase
            if phase == 'noticing':self.snapshot('party_stopped.png')
        if phase in ('noticing', 'pan_to_boar', 'conversation', 'pan_back'):
            if self._fixed_actors is None:self._fixed_actors = self.actor_positions()
            assert self.actor_positions() == self._fixed_actors, 'Stopped actors moved during the camera scene'
            self.actor_checks += 1
            assert not game.player.moving and not quest.mira.moving
        if phase == 'conversation' and game.camera.settled:
            if self._boar_origin is None:self._boar_origin = game.camera.position()
            assert game.camera.position() == self._boar_origin, 'Boar shot did not hold'
            self.hold_checks += 1
        if before is not None:
            model = game.combat.model
            after = (game.elapsed_ms, self.actor_positions(), model.phase,
                     tuple(member.atb for member in (*model.party, model.enemy)))
            assert before == after, 'Battle entry advanced world or battle clocks'
            self.entry_checks += 1
        self.positions.append(dict(time=round(self.seconds, 6), phase=phase,
                                   camera=game.camera.position()))
        game.draw()
        self.encoder.stdin.write(pygame.image.tobytes(game.window, 'RGB'))
        self.frames += 1

    def hold(self, seconds):
        for _ in range(round(seconds*FPS)):self.frame()

    def until(self, predicate, label, limit=600):
        for _ in range(limit):
            if predicate():return
            self.frame()
        raise AssertionError('Timed out: '+label)

    def advance(self):
        key(self.game, pygame.K_SPACE)
        self.game.update(0, (0, 0), False)

    def boar_rect(self):
        camera = pygame.Vector2(self.game.camera.position())
        position = pygame.Vector2(self.game.mill_quest.points['combat_position'])
        # The retained native Tusker canvas and anchor include every idle pose.
        return pygame.Rect(round(position.x-48-camera.x), round(position.y-62-camera.y), 96, 72)

    def check_dialogue_framing(self):
        layout = self.game.social.bubble.layout()
        assert layout is not None
        assert pygame.Rect(0, 0, 480, 320).contains(layout.panel)
        boar = self.boar_rect()
        assert pygame.Rect(0, 0, 480, 320).contains(boar), 'The boar was clipped in its focus shot'
        assert not layout.panel.colliderect(boar), 'Dialogue covered the boar'
        return dict(camera=self.game.camera.position(), boar=list(boar), panel=list(layout.panel))

    def large_text_snapshot(self, filename, *, boar=False):
        game = self.game
        old_size, old_text = game.window.get_size(), game.audio.text_scale
        try:
            game.window = pygame.display.set_mode((480, 320), pygame.RESIZABLE)
            game.audio.set_text_scale(1.5)
            game.draw()
            if boar:
                framing = self.check_dialogue_framing()
            else:
                panel = game.social.bubble.layout().panel
                camera = pygame.Vector2(game.camera.position())
                actors = [pygame.Rect(round(actor.position.x-12-camera.x),
                                     round(actor.position.y-34-camera.y), 24, 36)
                          for actor in (game.player, game.mill_quest.mira)]
                assert all(not panel.colliderect(actor) for actor in actors), 'Return dialogue covered the party'
                framing = dict(panel=list(panel), actors=[list(actor) for actor in actors])
            self.snapshot(filename)
            return framing
        finally:
            game.window = pygame.display.set_mode(old_size, pygame.RESIZABLE)
            game.audio.set_text_scale(old_text)
            game.draw()

    def record(self):
        game, quest = self.game, self.game.mill_quest
        game.audio.set_music(1);game.audio.set_effects(0)
        self.trace.begin()
        self.encoder = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo',
            '-pixel_format', 'rgb24', '-video_size', '960x640', '-framerate', str(FPS), '-i', '-',
            '-an', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '24', '-pix_fmt', 'yuv420p',
            str(self.output/'silent.mp4')], stdin=subprocess.PIPE)
        self.mark('town_north_exit')
        self.snapshot('town_departure.png');self.hold(1.2)
        key(game, pygame.K_e)
        game.update(0, (0, 0), False)
        assert game.world is quest.upstream
        self.arrival = list(game.player.position)
        self.mark('entered_millrace', player=self.arrival)
        self.snapshot('arrival_party.png')
        self.until(lambda: quest.encounter_cutscene_phase == 'conversation' and game.social.active,
                   'boar conversation')
        assert game.music.desired_track == 'eldenmere' and not game.combat.active
        self.boar_framing = self.check_dialogue_framing()
        self.snapshot('boar_conversation.png')
        self.minimum_boar = self.large_text_snapshot('boar_minimum_large_text.png', boar=True)
        seen = set()
        cue_seen = False
        while game.social.script_identifier == 'mill_encounter_intro':
            page = game.social.page
            assert page is not None
            identity = page['source_line'], page['offset']
            assert identity not in seen, 'Prose stopped advancing'
            seen.add(identity)
            text = ' '.join(page['lines'])
            cue = page.get('cue') == 'mill_return_to_party'
            self.mark('dialogue_page', speaker=page['speaker'], text=text,
                      source_line=page['source_line'], cue=page.get('cue'))
            assert game.music.desired_track == 'eldenmere'
            if cue:
                cue_seen = True
                self.warning_time = self.seconds
                assert quest.encounter_cutscene_phase == 'pan_back'
                self.mark('return_pan_requested', camera=game.camera.position())
                self.snapshot('return_pan_started.png')
                self.until(lambda: game.camera.settled, 'return to party')
                assert not game.combat.active and game.music.desired_track == 'eldenmere'
                self.return_time = self.seconds
                self.mark('party_camera_arrived', camera=game.camera.position())
                self.snapshot('party_returned.png')
                self.minimum_party = self.large_text_snapshot('party_minimum_large_text.png')
                self.hold(2.0)
                assert not game.combat.active and game.music.desired_track == 'eldenmere'
            else:
                assert quest.encounter_cutscene_phase == 'conversation'
                self.check_dialogue_framing()
                self.hold(2.4 if len(text) < 70 else 3.1)
            self.advance()
        assert cue_seen
        self.until(lambda: game.combat.active, 'battle handoff', limit=120)
        assert game.camera.settled and game.music.desired_track == 'battle'
        assert self.actor_positions() == self._fixed_actors
        self.battle_time = self.seconds
        self.mark('battle_started_after_camera_and_ack', camera=game.camera.position())
        while game.combat.transitioning:
            transition = game.combat.transition
            if transition.phase == 'closing' and transition.elapsed >= .14 and 'battle_transition.png' not in self.screenshots:
                self.snapshot('battle_transition.png')
            self.frame()
        assert not any(member.atb for member in (*game.combat.model.party, game.combat.model.enemy))
        self.mark('battlefield_revealed')
        self.snapshot('battlefield.png');self.hold(2.2)

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
                self.case.setUp();self.game = self.case.game
                self.case.diagnose()
                # Station placement occurs before recording. Actual entry uses
                # the north-road interaction and its ordinary follower route.
                self.case.place((720, 12), self.game.town)
                original_play = self.game.music.play
                def play(identifier, *args, **kwargs):
                    if self.trace.start is not None:
                        self.requests.append(dict(time=round(self.seconds, 6), track=identifier))
                    return original_play(identifier, *args, **kwargs)
                self.game.music.play = play
                self.record()
            self.encoder.stdin.close()
            if self.encoder.wait() != 0:raise RuntimeError('Cutscene video encoding failed')
            audio = np.concatenate(self.trace.blocks)
            assert len(audio) == self.frames*(RATE//FPS)
            assert np.max(np.abs(audio)) < 1
            with wave.open(str(self.output/'soundtrack.wav'), 'wb') as target:
                target.setparams((2, 2, RATE, 0, 'NONE', 'not compressed'))
                target.writeframes(np.round(audio*32767).astype('<i2').tobytes())
            subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', str(self.output/'silent.mp4'),
                '-i', str(self.output/'soundtrack.wav'), '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k',
                '-movflags', '+faststart', '-shortest', str(self.output/'millrace_cutscene.mp4')], check=True)
            self.output.joinpath('silent.mp4').unlink();self.output.joinpath('soundtrack.wav').unlink()
            plays = [event for event in self.trace.events if event['event'] == 'play'
                     and event['file'].endswith('kindled_courage.ogg')]
            assert len(plays) == 1
            battle_requests = [event for event in self.requests if event['track'] == 'battle']
            assert battle_requests and battle_requests[0]['time'] >= self.return_time
            assert plays[0]['time'] >= self.return_time
            metadata = dict(temporary_journey_and_settings=True, normal_player_files_untouched=True,
                prior_fixture='MQ01 public completion and MQ02 reunion/diagnosis/warning use existing station fixtures; the recording uses actual town exit, follower transfer, camera, dialogue and battle transition without actor teleports after arrival',
                duration_seconds=self.seconds, video_frames=self.frames, video_fps=FPS,
                screenshots=self.screenshots, phases=self.events, actor_stationary_checks=self.actor_checks,
                stopped_actor_positions=self._fixed_actors, boar_camera_hold_checks=self.hold_checks,
                battle_transition_frozen_checks=self.entry_checks, camera_frames=self.positions,
                boar_framing=self.boar_framing, minimum_boar_framing=self.minimum_boar,
                minimum_party_framing=self.minimum_party, music_requests=self.requests,
                mixer_initial_state=self.trace.initial, mixer_events=self.trace.events,
                return_warning_seconds=self.warning_time, party_camera_arrived_seconds=self.return_time,
                battle_started_seconds=self.battle_time, battle_music_play_count=len(plays),
                battle_music_started_after_party_camera=True, fight_waited_for_warning_ack=True,
                source_audio={str(Path(p).relative_to(ROOT)):hashlib.sha256(Path(p).read_bytes()).hexdigest()
                              for p in self.trace.samples},
                soundtrack='Offline reconstruction from exact runtime OGGs and observed production mixer commands, not hardware loopback; effects muted.',
                game_integration=True)
            self.output.joinpath('verification.json').write_text(json.dumps(metadata, indent=2)+'\n')
            self.output.joinpath('README.md').write_text('''# Millrace arrival cutscene review

[Watch the arrival, boar camera shot and battle handoff](millrace_cutscene.mp4).

The recording starts at Eldenmere's northern exit. Entering the millrace uses
the real world link and companion transfer. Caelan stops, Mira joins and notices
the threat, and the camera pans to the boar. The camera holds there while the
player-paced conversation plays in a readable portrait panel.

Mira's final “Caelan, come back to me” warning starts the return pan. The party
shot settles before the warning is acknowledged. Only then do Kindled Courage
and the existing world-to-battle transition begin. The actors retain their
standing positions and normal proportions throughout the camera movement.

![Boar conversation](boar_conversation.png)
![Camera returned to the party](party_returned.png)
![Minimum window with enlarged text](party_minimum_large_text.png)

The disposable journey uses legitimate completed MQ01 progress and existing
station fixtures for the earlier MQ02 interactions. No ordinary save/settings
files are used. After entry, all actor movement, camera work, prose advancement
and battle entry are production behavior.

Video frames are captured from the actual 960×640 game at 30 FPS. The soundtrack
is reconstructed offline from the exact runtime OGGs and observed mixer commands
because SDL's dummy device has no audio loopback; effects are muted for review.
The [verification record](verification.json) includes camera/actor checks,
dialogue timing, one battle-track playback and its delayed start after the pan.

Reproduce:

```sh
python tools/capture_millrace_cutscene.py --output work/millrace-cutscene
```
''')
            paths = ['tools/capture_millrace_cutscene.py'] + [str(p.relative_to(ROOT))
                    for p in sorted(self.output.iterdir()) if p.suffix in ('.mp4', '.png', '.json', '.md')]
            if self.output.resolve() == (ROOT/'docs/reviews/millrace_cutscene').resolve():
                (ROOT/'work/millrace-camera-preview-paths.json').write_text(json.dumps(paths, indent=2)+'\n')
            print(json.dumps(dict(output=str(self.output), seconds=self.seconds, frames=self.frames,
                video_bytes=self.output.joinpath('millrace_cutscene.mp4').stat().st_size,
                stopped_actor_checks=self.actor_checks, boar_hold_checks=self.hold_checks,
                battle_track_play_count=len(plays))))
        finally:
            if self.encoder is not None and self.encoder.poll() is None:
                if self.encoder.stdin and not self.encoder.stdin.closed:self.encoder.stdin.close()
                self.encoder.wait()
            self.trace.close()
            if self.case is not None:
                self.case.tearDown();self.case.doCleanups()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'docs/reviews/millrace_cutscene')
    Capture(parser.parse_args().output).run()
