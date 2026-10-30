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
from unittest.mock import patch
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
from speech_bubble import MAX_LINES, PANEL_WIDTH, PORTRAIT_SIZE, TEXT_WIDTH
from ui_style import Painter


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
        self.timeline = None
        self.checks = dict(handholding=0, return_barrier=0, glimmer=0,
                           fixed_camera=0, actors_offscreen=0, zoom=0)
        self.semantic_frames = []
        self.clock_samples = []
        self.lamp_samples = {}
        self.clip_records = {}
        self._last_zoom = 1.0
        self.reconstructed_motif_wraps = 0
        self.dialogue_draw_checks = 0
        self.departure = None
        self.paging_review = None

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
            self.clock_samples.append((scene.elapsed, self.seconds))
            if self.timeline is not None:
                self.verify_sequence(scene)
            record = scene.dialogue
            if record is not None:
                index = scene.data['dialogue'].index(record)
                observed = self.observed_dialogue.setdefault(index, dict(
                    index=index, id=record['id'], speaker=record['speaker'], text=record['text'],
                    first_seen=round(scene.elapsed, 4)))
                observed['last_seen'] = round(scene.elapsed, 4)
                layout = scene.caption_layout
                assert layout is not None and layout.portrait is not None
                assert layout.portrait_key == record['speaker'].lower()
                assert layout.portrait.size == (PORTRAIT_SIZE, PORTRAIT_SIZE)
                assert layout.panel.width == PANEL_WIDTH
                assert 0 <= scene.caption_page_index < len(scene.caption_pages)
                assert len(scene.caption_lines) <= MAX_LINES
                pages = observed.setdefault('pages', [dict(index=page_index, lines=list(lines))
                    for page_index, lines in enumerate(scene.caption_pages)])
                assert [page['lines'] for page in pages] == [list(lines) for lines in scene.caption_pages]
                page = pages[scene.caption_page_index]
                page.setdefault('first_seen', round(scene.elapsed, 4))
                page['last_seen'] = round(scene.elapsed, 4)
                assert page['lines'] == list(scene.caption_lines)
                self.dialogue_draw_checks += 1
            if (self.drink_interval is not None and
                    self.drink_interval[0] <= scene.elapsed <= self.drink_interval[1]):
                self.drink_frames.append(pygame.image.tobytes(
                    game.canvas.subsurface(self.drink_crop), 'RGB'))
                self.drink_times.append(scene.elapsed)
        self.encoder.stdin.write(pygame.image.tobytes(game.window, 'RGB'))
        previous_track, previous_position = self.trace.loaded, self.trace.position
        self.trace.advance(1/FPS)
        if (previous_track is not None and previous_track.endswith('dare_to_dream_leitmotif.ogg')
                and self.trace.loaded == previous_track and self.trace.position < previous_position):
            self.reconstructed_motif_wraps += 1
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
                position = scene.actor_position(record['id'])-scene.camera_position
                rect = image.get_bounding_rect().move(round(position.x-anchor[0]),
                                                       round(position.y-anchor[1]))
                assert not scene.caption_rect.colliderect(rect), 'Large caption covers the acting'
                actor_bounds.append(dict(actor=record['id'], bounds=list(rect)))
            self.accessibility = dict(viewport=[480, 320], text_scale=1.5,
                text=scene.dialogue['text'], caption=list(scene.caption_rect),
                lines=list(scene.caption_lines), skip=list(scene.skip_rect),
                portrait=list(scene.caption_layout.portrait),
                portrait_key=scene.caption_layout.portrait_key,
                page_index=scene.caption_page_index,
                pages=[list(lines) for lines in scene.caption_pages],
                actor_bounds=actor_bounds)
        finally:
            game.window = pygame.display.set_mode(original_size, pygame.RESIZABLE)
            game.audio.set_text_scale(original_text)
            game.draw()

    def verify_sequence(self, scene):
        """Observe production state, including the return/repair completion barrier."""
        elapsed, events = scene.elapsed, self.timeline
        if elapsed < events['camera_returned']-1e-7:
            assert scene.lamp_stage < 3, 'Lamp fully restored before the camera returned'
            self.checks['return_barrier'] += 1
        if events['hand_hold'] <= elapsed < events['hand_release']:
            assert scene.cup_visible, 'Cup was not put down before hands were held'
            self.checks['handholding'] += 1
        if events['flare_glimmer']+.05 <= elapsed < events['end']:
            assert scene.glimmer_visible, 'Signal light disappeared after the firework burst'
            self.checks['glimmer'] += 1
        if events['memorial_centered']+.05 <= elapsed < events['helmet_zoom_start']:
            assert scene.memorial_visible
            assert scene.camera_position.distance_to((155, 160)) < 1e-6
            memorial = scene.data['dynamic_props']['memorial']
            assert abs(memorial['position'][0]-scene.camera_position.x-240) < 1e-6
            self.checks['fixed_camera'] += 1
        if events['actors_offscreen']+.05 <= elapsed < events['helmet_zoom_start']:
            for record, anchor, frames, transitions in scene.actors:
                image = scene._actor_frame(record['id'], frames, transitions)
                point = scene.actor_position(record['id'])-scene.camera_position
                bounds = image.get_bounding_rect().move(round(point.x-anchor[0]),
                                                        round(point.y-anchor[1]))
                assert not pygame.Rect(0, 0, 480, 320).colliderect(bounds), record['id']+' did not exit'
            self.checks['actors_offscreen'] += 1
        if elapsed >= events['helmet_zoom_start']:
            assert scene.camera_zoom+1e-9 >= self._last_zoom, 'Helmet zoom reversed'
            self._last_zoom = scene.camera_zoom
            self.checks['zoom'] += 1
        if scene.dialogue is not None and scene.dialogue['id'] == 'so_do_i':
            assert elapsed >= events['camera_returned']
            assert scene.lamp_stage == 3, 'Completion line did not coincide with the restored lamp'

    def capture_semantic_frame(self, scene, name):
        self.snapshot(name)
        self.semantic_frames.append(dict(file=name, elapsed=round(scene.elapsed, 4),
            shot=scene.shot, camera=list(scene.camera_position), zoom=scene.camera_zoom,
            lamp_stage=scene.lamp_stage, flare_phase=scene.flare_phase,
            glimmer_visible=scene.glimmer_visible, cup_visible=scene.cup_visible,
            actors={actor: dict(position=list(scene.actor_position(actor)),
                                pose=scene.pose(actor)) for actor in ('caelan', 'mira')}))
        if name.startswith('lamp_stage_'):
            self.lamp_samples[scene.lamp_stage] = self.game.canvas.copy()

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
                len(painter.wrap(record['text'], TEXT_WIDTH)), len(record['text'])))
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
            point = scene.actor_position(record['id'])-scene.camera_position
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

    def write_large_text_paging_review(self):
        """Render a complete timed line at 480x320 with 150% accessibility text."""
        game, scene = self.game, self.game.opening_cinematic
        record = self.line(scene, 'catch_and_branch')
        original_size, original_text = game.window.get_size(), game.audio.text_scale
        original_elapsed, original_active = scene.elapsed, scene.active
        encoder = None
        pages, page_frames, page_samples = None, {}, {}
        filename = 'large_text_paging.mp4'
        try:
            game.window = pygame.display.set_mode((480, 320), pygame.RESIZABLE)
            game.audio.set_text_scale(1.5)
            scene.active = True
            encoder = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo',
                '-pixel_format', 'rgb24', '-video_size', '480x320', '-framerate', str(FPS),
                '-i', '-', '-an', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20',
                '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(self.output/filename)],
                stdin=subprocess.PIPE)
            frame_count = round((record['end']-record['start'])*FPS)
            for frame in range(frame_count):
                scene.elapsed = record['start']+frame/FPS
                game.draw()
                current = [list(lines) for lines in scene.caption_pages]
                if pages is None:
                    pages = current
                assert current == pages
                page_index = scene.caption_page_index
                page_frames[page_index] = page_frames.get(page_index, 0)+1
                page_samples.setdefault(page_index, game.window.copy())
                assert pygame.Rect(0, 0, 480, 320).contains(scene.caption_rect)
                assert not scene.caption_rect.colliderect(scene.skip_rect)
                encoder.stdin.write(pygame.image.tobytes(game.window, 'RGB'))
            encoder.stdin.close()
            assert encoder.wait() == 0
            encoder = None
            assert set(page_frames) == set(range(len(pages)))
            assert max(map(len, pages))-min(map(len, pages)) <= 1
            assert page_frames[len(pages)-1]/FPS >= 2.7
            sheet = pygame.Surface((480*len(pages), 338))
            sheet.fill('#15232b')
            font = pygame.font.Font(str(ROOT/'assets/ui/fonts/AtkinsonHyperlegible-Regular.ttf'), 11)
            for index in range(len(pages)):
                sheet.blit(page_samples[index], (480*index, 18))
                label = f'Page {index+1} · {page_frames[index]/FPS:.2f}s'
                sheet.blit(font.render(label, True, '#f8f0d9'), (480*index+6, 3))
            pygame.image.save(sheet, str(self.output/'large_text_pages.png'))
            self.paging_review = dict(file=filename, image='large_text_pages.png',
                source='Production Game.draw at the original timed line; separate silent accessibility review',
                dialogue_id=record['id'], scene_interval=[record['start'], record['end']],
                viewport=[480, 320], text_scale=1.5, frames=frame_count, pages=pages,
                page_seconds=[page_frames[index]/FPS for index in range(len(pages))])
        finally:
            if encoder is not None:
                encoder.stdin.close()
                encoder.wait()
            scene.elapsed, scene.active = original_elapsed, original_active
            game.window = pygame.display.set_mode(original_size, pygame.RESIZABLE)
            game.audio.set_text_scale(original_text)
            game.draw()

    def movie_time(self, scene_time):
        return min(self.clock_samples, key=lambda item: abs(item[0]-scene_time))[1]

    def write_action_reviews(self):
        """Extract selected consecutive production frames from the full capture."""
        e = self.timeline
        clips = (
            ('handholding_closeup.mp4', e['hand_reach']-.35, e['hand_release']+.6,
             'crop=400:260:360:200,scale=800:520:flags=neighbor'),
            ('beacon_sequence.mp4', e['flare_launch']-1, e['lamp_restored']+1, None),
            ('helmet_ending.mp4', e['departure_start']-.5, e['end']-.02, None),
        )
        for filename, start, finish, video_filter in clips:
            start_time, finish_time = self.movie_time(start), self.movie_time(finish)
            command = ['ffmpeg', '-y', '-v', 'error', '-ss', str(start_time),
                       '-i', str(self.output/'opening_cinematic.mp4'),
                       '-t', str(finish_time-start_time), '-an']
            if video_filter:
                command += ['-vf', video_filter]
            command += ['-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20',
                        '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
                        str(self.output/filename)]
            subprocess.run(command, check=True)
            self.clip_records[filename] = dict(scene_interval=[start, finish],
                movie_interval=[start_time, finish_time],
                source='Consecutive production-rendered frames; no soundtrack in short clips')

        assert set(self.lamp_samples) == {0, 1, 2, 3}, 'Not all visible repair stages were captured'
        crop = pygame.Rect(169, 166, 66, 68)
        sheet = pygame.Surface((crop.width*4, crop.height+17))
        sheet.fill('#15232b')
        font = pygame.font.Font(str(ROOT/'assets/ui/fonts/AtkinsonHyperlegible-Regular.ttf'), 11)
        for stage in range(4):
            sheet.blit(self.lamp_samples[stage].subsurface(crop), (stage*crop.width, 17))
            sheet.blit(font.render('Stage '+str(stage), True, '#f8f0d9'),
                       (stage*crop.width+3, 2))
        pygame.image.save(pygame.transform.scale(sheet, (sheet.get_width()*3,
                          sheet.get_height()*3)), str(self.output/'lamp_stages.png'))

    def record(self):
        game = self.game
        self.encoder = subprocess.Popen([
            'ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pixel_format', 'rgb24',
            '-video_size', '960x640', '-framerate', str(FPS), '-i', '-', '-an',
            '-c:v', 'libx264', '-preset', 'slow', '-crf', '30', '-pix_fmt',
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
        self.timeline = dict(scene.data['events'])
        self.timeline['end'] = scene.duration
        departure_tracks = {actor: next(track for track in scene.data['position_tracks'][actor]
            if track['start'] == self.timeline['departure_start']) for actor in ('caelan', 'mira')}
        speed = {actor: pygame.Vector2(track['from']).distance_to(track['to']) /
            (track['end']-track['start']) for actor, track in departure_tracks.items()}
        assert all(abs(value-48) < .0001 for value in speed.values())
        loops = {actor: [duration for _, duration in scene._actor_loops[actor]['walk_left']]
                 for actor in ('caelan', 'mira')}
        assert all(all(abs(duration-.18) < 1e-9 for duration in loop) for loop in loops.values())
        follow = next(shot for shot in scene.data['shots'] if shot['id'] == 'departure_follow')
        assert abs(follow['end']-follow['start']-7/1.2) < .00001
        assert follow['to'] == [155, 160]
        self.departure = dict(movement_pixels_per_second=speed,
            walking_frame_seconds=loops, animation_cadence_unchanged=True,
            camera_follow_seconds=follow['end']-follow['start'],
            walking_seconds=self.timeline['actors_offscreen']-self.timeline['departure_start'])
        conversation = next(shot for shot in scene.data['shots'] if shot['id'] == 'conversation')
        # Actor framing is fixed throughout the conversation. Calculate the crop
        # at that authored shot without changing the live scene clock.
        original_elapsed = scene.elapsed
        scene.elapsed = next(cue['start'] for cue in scene.data['acting']['caelan']
                             if cue['pose'] == 'drink')
        self.prepare_drink_capture(scene)
        scene.elapsed = original_elapsed
        longest = self.longest_caption(scene)
        e = self.timeline
        stages = {record['stage']: record['start'] for record in
                  scene.data['dynamic_props']['lamp']['stage_cues']}
        stage_two = stages[2]+.2
        if stage_two >= e['flare_launch']:
            stage_two = max(stages[2], e['camera_returned'])+.1
        assert stage_two < e['lamp_restored'], 'Intermediate repair has no visible ground-shot interval'
        targets = iter(sorted([
            (4, 'valley.png'), (conversation['start']+.1, 'lantern_reveal.png'),
            (conversation['start']+.2, 'lamp_stage_0.png'),
            (self.line(scene, 'valley_houses')['start']+.25, 'conversation.png'),
            (self.line(scene, 'mill_memory')['start']+.25, 'quiet_exchange.png'),
            (e['cup_set_down']+.2, 'cup_on_bench.png'),
            (self.line(scene, 'understood_problem')['start']+.25, 'handholding.png'),
            (e['lamp_work_start']+.2, 'lamp_work.png'),
            (stages[1]+.2, 'lamp_stage_1.png'),
            (stage_two, 'lamp_stage_2.png'),
            (e['flare_launch']+.35, 'flare_ascent.png'),
            (e['flare_burst']+.3, 'flare_burst.png'),
            (e['flare_glimmer']+.5, 'sky_glimmer.png'),
            ((e['camera_return_start']+e['camera_returned'])/2, 'camera_return.png'),
            (e['lamp_restored']+.2, 'lamp_stage_3.png'),
            (e['departure_start']+2, 'departure.png'),
            (e['memorial_centered']-.2, 'foreground_pass.png'),
            (e['memorial_centered']+.2, 'helmet_centered.png'),
            (e['actors_offscreen']+.1, 'actors_offscreen.png'),
            (e['fade_start']-.2, 'helmet_before_fade.png'),
            ((e['helmet_zoom_start']+e['end'])/2, 'last_look.png'),
            (e['fade_start']+.6, 'helmet_fade.png'),
        ]))
        target = next(targets, None)
        pause_at = e['flare_launch']+.7
        paused = enlarged = False
        for _ in range(round((scene.duration+12)*FPS)):
            if not scene.active:
                break
            if target is not None and scene.elapsed >= target[0]:
                self.capture_semantic_frame(scene, target[1])
                target = next(targets, None)
            if scene.elapsed >= longest['start']+.25 and not enlarged:
                self.minimum_text_snapshot()
                enlarged = True
            if scene.elapsed >= pause_at and not paused:
                self.key(pygame.K_ESCAPE)
                self.frame()
                assert scene.paused and game.music.paused
                elapsed = scene.elapsed
                frozen = (scene.camera_position, scene.camera_zoom, scene.flare_phase,
                          scene.lamp_stage, scene.actor_position('caelan'), scene.actor_position('mira'))
                self.event('escape_paused', elapsed=elapsed)
                self.snapshot('paused.png')
                self.hold(2)
                assert scene.elapsed == elapsed
                assert frozen == (scene.camera_position, scene.camera_zoom, scene.flare_phase,
                                   scene.lamp_stage, scene.actor_position('caelan'), scene.actor_position('mira'))
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
        for observed in self.observed_dialogue.values():
            assert all('first_seen' in page for page in observed['pages']), 'Some timed dialogue pages were omitted'
            joined = ' '.join(line for page in observed['pages'] for line in page['lines'])
            assert ' '.join(joined.split()) == ' '.join(observed['text'].split()), 'Timed pages lost dialogue text'
        assert self.accessibility is not None, 'Longest caption was not captured'
        assert all(self.checks.values()), 'Some required cinematic stages were not verified'
        self.event('bedroom_started', first_line=first_line)
        self.hold(1)  # Let the ordinary morning fade reveal the room.
        self.snapshot('bedroom.png')
        self.hold(1)
        self.encoder.stdin.close()
        if self.encoder.wait():
            raise RuntimeError('FFmpeg video encoder failed')
        self.encoder = None
        self.write_drink_review()
        self.write_large_text_paging_review()

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
        self.write_action_reviews()
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
            reconstructed_motif_wraps=self.reconstructed_motif_wraps,
            dialogue_lines=len(self.scene_dialogue),
            dialogue_pages=sum(len(record['pages']) for record in self.observed_dialogue.values()),
            dialogue_draw_checks=self.dialogue_draw_checks,
            standard_dialogue_panel=True, left_speaker_portraits=True,
            no_click_to_continue_prompt=True, departure=self.departure,
            large_text_paging=self.paging_review,
            observed_dialogue=[self.observed_dialogue[index]
                               for index in range(len(self.scene_dialogue))],
            dialogue_gaps_seconds=gaps, accessibility=self.accessibility,
            sequence_events=self.timeline, sequence_checks=self.checks,
            semantic_frames=self.semantic_frames, action_clips=self.clip_records,
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
{len(self.scene_dialogue)} user-authored dialogue lines. The choreography includes
putting the cup down, holding hands, walking to and repairing the lamp, the
blue flare/firework and persistent sky light, the return shot, and the departure
past an anonymous bloodstained helmet. Actor and camera actions receive their
own authored time; ordinary dialogue gaps remain short.

Dialogue uses the same bordered panel, left speaker portraits, gold names,
typography and text spacing as normal gameplay. Longer lines turn through
timed pages inside their existing dialogue holds, with no click-to-continue
prompt. Every page is observed in the full capture. Departure movement is 20%
faster (48 pixels/second); the walking animation keeps its 180 ms frame cadence.
The camera follow is retimed to keep the helmet centered, followed by the
existing slow zoom and fade after both characters leave.

The soundtrack is reconstructed from the exact shipped OGGs and observed
production mixer commands because the headless SDL driver has no audio loopback.
It includes the actual fades and the preserved music position across the pause.
It is not a separate musical arrangement. `verification.json` records the
observed route, all dialogue lines and gaps, single repeating leitmotif request,
frozen-world checks, longest-caption layout and the new sequence barriers. The
two-second Esc demonstration occurs during the flare flight, freezing its
motion, the camera and the same music playback position.

- [Handholding close-up](handholding_closeup.mp4)
- [Flare flight, firework, sky light and completed repair](beacon_sequence.mp4)
- [Departure and helmet ending](helmet_ending.mp4)
- [Four visible lamp repair stages](lamp_stages.png)
- [Automatic paging at 480×320 with 150% text](large_text_paging.mp4)
- [Both large-text pages and their display times](large_text_pages.png)

These short clips are consecutive production-rendered frames with no audio;
the full preview above includes the complete soundtrack.

The accessibility paging clip separately renders the original eight-second
lamp request through production `Game.draw` at 480×320 with 150% text. It shows
both balanced pages using the original timed hold, with no soundtrack or input
required. It does not change the default-size full playthrough above.

[Watch the corrected drinking motion close-up](drinking_closeup.mp4) or inspect its
[rest → lift → sip → lower → rest frames](drinking_keyframes.png). These are
consecutive production world frames, cropped and enlarged at an integer scale;
the short close-up has no audio.

- [Valley establishing shot](valley.png)
- [Lantern-lit sanctuary](lantern_reveal.png)
- [Conversation](conversation.png)
- [Quiet exchange](quiet_exchange.png)
- [Cup placed on the bench](cup_on_bench.png)
- [Mira holding both hands](handholding.png)
- [Mira working on the lamp](lamp_work.png)
- [Flare ascent](flare_ascent.png)
- [Firework burst](flare_burst.png)
- [Persistent sky light](sky_glimmer.png)
- [Camera returning to the pair](camera_return.png)
- [Restored lamp](lamp_stage_3.png)
- [Walking departure](departure.png)
- [Passing behind the foreground sword](foreground_pass.png)
- [Helmet centered; camera held](helmet_centered.png)
- [Both actors offscreen](actors_offscreen.png)
- [Helmet before the fade](helmet_before_fade.png)
- [Helmet close-up](last_look.png)
- [Final helmet fade](helmet_fade.png)
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
                original_text = Painter.text

                def checked_text(painter, text, *args, **kwargs):
                    if self.game.opening_cinematic.active:
                        assert text != 'Click to continue', 'Cinematic showed an interactive dialogue prompt'
                    return original_text(painter, text, *args, **kwargs)

                with patch.object(Painter, 'text', checked_text):
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
