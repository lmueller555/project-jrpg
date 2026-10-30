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
        self.observed_dialogue = {}
        self.accessibility = None
        self.drink_frames = []
        self.drink_times = []
        self.drink_crop = None
        self.drink_interval = None
        self.drink_cues = None

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
        scene = game.opening_cinematic
        if scene.active:
            record = scene.dialogue
            if record is not None:
                index = scene.data['dialogue'].index(record)
                observed = self.observed_dialogue.setdefault(index, dict(
                    index=index, id=record['id'], speaker=record['speaker'], text=record['text'],
                    first_seen=round(scene.elapsed, 4)))
                observed['last_seen'] = round(scene.elapsed, 4)
            if (self.drink_interval is not None and
                    self.drink_interval[0] <= scene.elapsed <= self.drink_interval[1]):
                self.drink_frames.append(pygame.image.tobytes(
                    game.canvas.subsurface(self.drink_crop), 'RGB'))
                self.drink_times.append(scene.elapsed)
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
            scene = game.opening_cinematic
            view = pygame.Rect(0, 0, 480, 320)
            assert view.contains(scene.skip_rect)
            assert view.contains(scene.caption_rect)
            assert not scene.caption_rect.colliderect(scene.skip_rect)
            actor_bounds = []
            for record, anchor, frames, transitions in scene.actors:
                image = scene._actor_frame(record['id'], frames, transitions)
                position = pygame.Vector2(record['position'])-scene.camera_position
                rect = image.get_bounding_rect().move(round(position.x-anchor[0]),
                                                       round(position.y-anchor[1]))
                assert not scene.caption_rect.colliderect(rect), 'Large caption covers the acting'
                actor_bounds.append(dict(actor=record['id'], bounds=list(rect)))
            self.accessibility = dict(viewport=[480, 320], text_scale=1.5,
                text=scene.dialogue['text'], caption=list(scene.caption_rect),
                lines=list(scene.caption_lines), skip=list(scene.skip_rect),
                actor_bounds=actor_bounds)
        finally:
            game.window = pygame.display.set_mode(original_size, pygame.RESIZABLE)
            game.audio.set_text_scale(original_text)
            game.draw()

    @staticmethod
    def line(scene, identifier):
        return next(record for record in scene.data['dialogue']
                    if record['id'] == identifier)

    def longest_caption(self, scene):
        """Measure real wrapping at the minimum viewport and largest text size."""
        original = self.game.audio.text_scale
        try:
            self.game.audio.text_scale = 1.5
            painter = self.game.ui.painter(pygame.Surface((480, 320)))
            return max(scene.data['dialogue'], key=lambda record: (
                len(painter.wrap(record['text'], 412)), len(record['text'])))
        finally:
            self.game.audio.text_scale = original

    def prepare_drink_capture(self, scene):
        cues = scene.data['acting']['caelan']
        index = next(index for index, cue in enumerate(cues) if cue['pose'] == 'drink')
        start, finish = cues[index]['start'], cues[index+1]['start']
        actor = next(actor for actor in scene.actors if actor[0]['id'] == 'caelan')
        lower_duration = sum(duration for _, duration in
                             actor[3].get('drink:'+cues[index+1]['pose'], ()))
        self.drink_cues = dict(lift=start, lower=finish, return_settled=finish+lower_duration)
        end = finish+lower_duration+.6
        if index+2 < len(cues):
            assert finish+lower_duration < cues[index+2]['start'], 'Drink overlaps the next acting cue'
            end = min(end, cues[index+2]['start']-.05)
        self.drink_interval = (max(0, start-.6), end)
        rects = []
        for record, anchor, frames, _ in scene.actors:
            point = pygame.Vector2(record['position'])-scene.camera_position
            image = next(iter(frames.values()))
            rects.append(pygame.Rect(round(point.x-anchor[0]), round(point.y-anchor[1]),
                                     image.get_width(), image.get_height()))
        crop = rects[0].unionall(rects[1:]).inflate(12, 12)
        crop.width += crop.width % 2
        crop.height += crop.height % 2
        self.drink_crop = crop.clamp(pygame.Rect(0, 0, 480, 320))

    def write_drink_review(self):
        assert self.drink_frames, 'The production route omitted the drink interval'
        width, height = self.drink_crop.size
        result = subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo',
            '-pixel_format', 'rgb24', '-video_size', f'{width}x{height}',
            '-framerate', str(FPS), '-i', '-', '-an', '-vf',
            f'scale={width*3}:{height*3}:flags=neighbor', '-c:v', 'libx264',
            '-preset', 'veryfast', '-crf', '18', '-pix_fmt', 'yuv420p',
            '-movflags', '+faststart', str(self.output/'drinking_closeup.mp4')],
            input=b''.join(self.drink_frames), check=True)
        assert result.returncode == 0
        lift, lower, settled = (self.drink_cues[key] for key in
                               ('lift', 'lower', 'return_settled'))
        targets = [self.drink_interval[0], lift+.12, (lift+lower)/2,
                   lower+.12, settled+.35]
        selected = [min(range(len(self.drink_times)), key=lambda index:
                        abs(self.drink_times[index]-time)) for time in targets]
        sheet = pygame.Surface((width*5, height+16))
        sheet.fill('#15232b')
        font = pygame.font.Font(str(ROOT/'assets/ui/fonts/AtkinsonHyperlegible-Regular.ttf'), 11)
        labels = ('Rest', 'Lift', 'Sip', 'Lower', 'Rest')
        for column, (index, label) in enumerate(zip(selected, labels)):
            image = pygame.image.frombytes(self.drink_frames[index], (width, height), 'RGB')
            sheet.blit(image, (column*width, 16))
            text = font.render(f'{label} · {self.drink_times[index]:.2f}s', True, '#f8f0d9')
            sheet.blit(text, (column*width+4, 2))
        pygame.image.save(pygame.transform.scale(sheet, (sheet.get_width()*2,
                          sheet.get_height()*2)), str(self.output/'drinking_keyframes.png'))

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
        self.scene_duration = scene.duration
        self.scene_dialogue = list(scene.data['dialogue'])
        conversation = next(shot for shot in scene.data['shots'] if shot['id'] == 'conversation')
        # Actor framing is fixed throughout the conversation. Calculate the crop
        # at that authored shot without changing the live scene clock.
        original_elapsed = scene.elapsed
        scene.elapsed = conversation['start']
        self.prepare_drink_capture(scene)
        scene.elapsed = original_elapsed
        longest = self.longest_caption(scene)
        look = next(cue for cue in reversed(scene.data['acting']['caelan'])
                    if cue['pose'] == 'look_out')
        targets = iter(sorted([
            (4, 'valley.png'), (conversation['start']+.1, 'lantern_reveal.png'),
            (self.line(scene, 'valley_houses')['start']+.25, 'conversation.png'),
            (self.line(scene, 'mill_memory')['start']+.25, 'quiet_exchange.png'),
            (look['start']+.25, 'last_look.png')]))
        target = next(targets, None)
        pause_at = self.line(scene, 'surge')['start']+.4
        paused = enlarged = False
        for _ in range(round((scene.duration+12)*FPS)):
            if not scene.active:
                break
            if target is not None and scene.elapsed >= target[0]:
                self.snapshot(target[1])
                target = next(targets, None)
            if scene.elapsed >= longest['start']+.25 and not enlarged:
                self.minimum_text_snapshot()
                enlarged = True
            if scene.elapsed >= pause_at and not paused:
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
            self.frame()
        assert not scene.active, 'Opening did not finish'
        assert game.world.data['id'] == 'sanctuary_bedroom'
        assert game.opening.stage == 'wake'
        first_line = ' '.join(game.social.page['lines'])
        assert first_line == "Caelan? You're awake, aren't you?"
        assert game.music.desired_track == 'eldenmere'
        assert self.path.is_file()
        assert len(self.observed_dialogue) == len(self.scene_dialogue), 'Some dialogue was not shown'
        assert self.accessibility is not None, 'Longest caption was not captured'
        self.event('bedroom_started', first_line=first_line)
        self.hold(1)  # Let the ordinary morning fade reveal the room.
        self.snapshot('bedroom.png')
        self.hold(1)
        self.encoder.stdin.close()
        if self.encoder.wait():
            raise RuntimeError('FFmpeg video encoder failed')
        self.encoder = None
        self.write_drink_review()

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
        gaps = [round(b['start']-a['end'], 4)
                for a, b in zip(self.scene_dialogue, self.scene_dialogue[1:])]
        data = dict(frames=self.frames, fps=FPS, seconds=self.seconds,
            scene_duration_seconds=self.scene_duration,
            route='Unmodified production title New Game; natural cinematic completion',
            world_freeze_checks=self.freeze_checks, escape_pause_preserves_position=True,
            no_checkpoint_until_bedroom=True, leitmotif_plays=len(motif_plays),
            leitmotif_repeat=True, events=self.events, mixer_commands=commands,
            dialogue_lines=len(self.scene_dialogue),
            observed_dialogue=[self.observed_dialogue[index]
                               for index in range(len(self.scene_dialogue))],
            dialogue_gaps_seconds=gaps, accessibility=self.accessibility,
            drinking=dict(interval=list(self.drink_interval), cues=self.drink_cues,
                          crop=list(self.drink_crop), frames=len(self.drink_frames),
                          clip_seconds=len(self.drink_frames)/FPS,
                          source='Consecutive production world frames; cropped and integer-scaled'),
            screenshots=self.screenshots,
            audio='Exact runtime OGG reconstructed from observed mixer commands; SDL dummy has no loopback',
            music_sha256=hashlib.sha256((ROOT/'assets/music/runtime/dare_to_dream_leitmotif.ogg').read_bytes()).hexdigest())
        (self.output/'verification.json').write_text(json.dumps(data, indent=2)+'\n')
        readme = f'''# Opening cinematic review

[Watch the full cinematic with music](opening_cinematic.mp4).

This capture follows the production title's **New Game** path through the
complete opening, an Esc pause/resume demonstration and the ordinary bedroom
handoff. All images are rendered by the game with the runtime assets. Temporary
journey and settings files leave ordinary saves untouched. Effects are muted.

The expanded scene lasts {self.scene_duration:.1f} seconds and presents all
{len(self.scene_dialogue)} dialogue lines. Its ordinary gaps are one second;
two four-second acting pauses retain room for the drink and final preparation.

The soundtrack is reconstructed from the exact shipped OGGs and observed
production mixer commands because the headless SDL driver has no audio loopback.
It includes the actual fades and the preserved music position across the pause.
It is not a separate musical arrangement. `verification.json` records the
observed route, all dialogue lines and gaps, single repeating leitmotif request,
frozen-world checks and longest-caption layout.

[Watch the corrected drinking motion close-up](drinking_closeup.mp4) or inspect its
[rest → lift → sip → lower → rest frames](drinking_keyframes.png). These are
consecutive production world frames, cropped and enlarged at an integer scale;
the short close-up has no audio.

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
        'scene_duration_seconds', 'dialogue_lines', 'world_freeze_checks',
        'leitmotif_plays', 'leitmotif_repeat')}, indent=2))


if __name__ == '__main__':
    main()
