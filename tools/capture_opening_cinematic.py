"""Capture the real title-to-cinematic-to-bedroom route with its soundtrack.

Images come from Game.draw. SDL dummy has no audio loopback, so audio is
reconstructed from the exact runtime OGG and observed production mixer calls.
Temporary journey/settings files keep ordinary saves untouched.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import wave

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'tools')]

import numpy as np
import pygame
from main import Game
from capture_battle_music_transition import MixerTrace, FPS, RATE


class Capture:
    def __init__(self, output):
        self.output = output
        output.mkdir(parents=True, exist_ok=True)
        self.trace = MixerTrace()
        self.frames = 0
        self.events = []
        self.screenshots = []
        self.freeze_checks = 0
        self.encoder = None

    @property
    def seconds(self):
        return self.frames/FPS

    def event(self, name, **values):
        self.events.append(dict(time=round(self.seconds, 4), event=name, **values))

    def key(self, code):
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=code, repeat=False))
        pygame.event.post(pygame.event.Event(pygame.KEYUP, key=code))

    def snapshot(self, name):
        self.game.draw()
        pygame.image.save(self.game.window, str(self.output/name))
        self.screenshots.append(name)

    def frame(self):
        game = self.game
        active = game.opening_cinematic.active
        before = (game.elapsed_ms, tuple(game.player.position), game.quests.to_dict())
        if not game.handle_events():
            raise AssertionError('Capture closed unexpectedly')
        game.update(1/FPS, (0, 0), False)
        if active and game.opening_cinematic.active:
            after = (game.elapsed_ms, tuple(game.player.position), game.quests.to_dict())
            assert before == after, 'The flashforward advanced the ordinary world'
            self.freeze_checks += 1
            assert game.music.desired_track == 'opening_leitmotif'
            assert not self.path.exists(), 'Future scene wrote a journey checkpoint'
        game.draw()
        self.encoder.stdin.write(pygame.image.tobytes(game.window, 'RGB'))
        self.trace.advance(1/FPS)
        self.frames += 1

    def hold(self, seconds):
        for _ in range(round(seconds*FPS)):
            self.frame()

    def minimum_text_snapshot(self):
        game = self.game
        original_size = game.window.get_size()
        original_text = game.audio.text_scale
        try:
            game.window = pygame.display.set_mode((480, 320), pygame.RESIZABLE)
            game.audio.set_text_scale(1.5)
            self.snapshot('minimum_large_text.png')
            assert pygame.Rect(0, 0, 480, 320).contains(game.opening_cinematic.skip_rect)
        finally:
            game.window = pygame.display.set_mode(original_size, pygame.RESIZABLE)
            game.audio.set_text_scale(original_text)
            game.draw()

    def record(self):
        game = self.game
        self.encoder = subprocess.Popen([
            'ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pixel_format', 'rgb24',
            '-video_size', '960x640', '-framerate', str(FPS), '-i', '-', '-an',
            '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23', '-pix_fmt',
            'yuv420p', str(self.output/'silent.mp4')], stdin=subprocess.PIPE)
        self.trace.begin()
        self.snapshot('title.png')
        self.hold(.75)
        self.key(pygame.K_RETURN)
        for _ in range(100):
            if game.opening_cinematic.active:
                break
            self.frame()
        scene = game.opening_cinematic
        assert scene.active and not game.on_title
        self.event('cinematic_started', duration=scene.duration)
        targets = iter([(4, 'valley.png'), (22, 'lantern_reveal.png'),
                        (37, 'conversation.png'), (62, 'quiet_exchange.png'),
                        (scene.duration-9.5, 'last_look.png')])
        target = next(targets, None)
        paused = enlarged = False
        for _ in range(round((scene.duration+12)*FPS)):
            if not scene.active:
                break
            if target is not None and scene.elapsed >= target[0]:
                self.snapshot(target[1])
                target = next(targets, None)
            if scene.elapsed >= 45 and not paused:
                self.key(pygame.K_ESCAPE)
                self.frame()
                assert scene.paused and game.music.paused
                elapsed = scene.elapsed
                self.event('escape_paused', elapsed=elapsed)
                self.snapshot('paused.png')
                self.hold(2)
                assert scene.elapsed == elapsed
                self.key(pygame.K_ESCAPE)
                self.frame()
                assert not scene.paused and not game.music.paused
                self.event('escape_resumed', elapsed=scene.elapsed)
                paused = True
            if scene.elapsed >= 60 and not enlarged:
                self.minimum_text_snapshot()
                enlarged = True
            self.frame()
        assert not scene.active, 'Opening did not finish'
        assert game.world.data['id'] == 'sanctuary_bedroom'
        assert game.opening.stage == 'wake'
        first_line = ' '.join(game.social.page['lines'])
        assert first_line == "Caelan? You're awake, aren't you?"
        assert game.music.desired_track == 'eldenmere'
        assert self.path.is_file()
        self.event('bedroom_started', first_line=first_line)
        self.hold(1)  # Let the ordinary morning fade reveal the room.
        self.snapshot('bedroom.png')
        self.hold(1)
        self.encoder.stdin.close()
        if self.encoder.wait():
            raise RuntimeError('FFmpeg video encoder failed')
        self.encoder = None

    def write_audio_and_metadata(self):
        audio = np.concatenate(self.trace.blocks)
        with wave.open(str(self.output/'soundtrack.wav'), 'wb') as writer:
            writer.setnchannels(2)
            writer.setsampwidth(2)
            writer.setframerate(RATE)
            writer.writeframes((np.clip(audio, -1, 1)*32767).astype('<i2').tobytes())
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', str(self.output/'silent.mp4'),
            '-i', str(self.output/'soundtrack.wav'), '-map', '0:v', '-map', '1:a',
            '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest',
            '-movflags', '+faststart', str(self.output/'opening_cinematic.mp4')], check=True)
        for name in ('silent.mp4', 'soundtrack.wav'):
            (self.output/name).unlink()
        commands = [event for event in self.trace.events if event['event'] != 'volume']
        motif_plays = [event for event in commands if event['event'] == 'play'
                       and event.get('file', '').endswith('dare_to_dream_leitmotif.ogg')]
        assert len(motif_plays) == 1 and motif_plays[0]['loops'] == -1
        data = dict(frames=self.frames, fps=FPS, seconds=self.seconds,
            route='Unmodified production title New Game; natural cinematic completion',
            world_freeze_checks=self.freeze_checks, escape_pause_preserves_position=True,
            no_checkpoint_until_bedroom=True, leitmotif_plays=len(motif_plays),
            leitmotif_repeat=True, events=self.events, mixer_commands=commands,
            screenshots=self.screenshots,
            audio='Exact runtime OGG reconstructed from observed mixer commands; SDL dummy has no loopback',
            music_sha256=hashlib.sha256((ROOT/'assets/music/runtime/dare_to_dream_leitmotif.ogg').read_bytes()).hexdigest())
        (self.output/'verification.json').write_text(json.dumps(data, indent=2)+'\n')
        readme = '''# Opening cinematic review

[Watch the full cinematic with music](opening_cinematic.mp4).

This capture follows the production title's **New Game** path through the
complete opening, an Esc pause/resume demonstration and the ordinary bedroom
handoff. All images are rendered by the game with the runtime assets. Temporary
journey and settings files leave ordinary saves untouched. Effects are muted.

The soundtrack is reconstructed from the exact shipped OGGs and observed
production mixer commands because the headless SDL driver has no audio loopback.
It includes the actual fades and the preserved music position across the pause.
It is not a separate musical arrangement. `verification.json` records the
observed route, single repeating leitmotif request and frozen-world checks.

- [Valley establishing shot](valley.png)
- [Lantern-lit sanctuary](lantern_reveal.png)
- [Conversation](conversation.png)
- [Quiet exchange](quiet_exchange.png)
- [Final look](last_look.png)
- [Esc pause](paused.png)
- [480×320 with 150% text](minimum_large_text.png)
- [Bedroom handoff](bedroom.png)

Rebuild from the repository root with:

```sh
python tools/capture_opening_cinematic.py
```
'''
        (self.output/'README.md').write_text(readme)
        return data

    def run(self):
        with tempfile.TemporaryDirectory(prefix='opening-cinematic-capture-') as temporary:
            self.path = Path(temporary)/'journey.json'
            self.trace.install()
            try:
                self.game = Game(window_size=(960, 640), fullscreen=False,
                    save_path=self.path, settings_path=Path(temporary)/'settings.json')
                self.game.audio.set_music(1)
                self.game.audio.set_effects(0)
                pygame.event.clear()
                self.record()
                return self.write_audio_and_metadata()
            finally:
                if self.encoder is not None:
                    self.encoder.stdin.close()
                    self.encoder.wait()
                self.trace.close()
                pygame.quit()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path,
                        default=ROOT/'docs/reviews/opening_cinematic')
    args = parser.parse_args()
    data = Capture(args.output).run()
    print(json.dumps({key: data[key] for key in ('frames', 'seconds',
        'world_freeze_checks', 'leitmotif_plays', 'leitmotif_repeat')}, indent=2))


if __name__ == '__main__':
    main()
