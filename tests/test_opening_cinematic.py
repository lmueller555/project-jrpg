"""Cinematic shot, acting, text and input contracts independent of quest state."""
import json
import math
import os
from pathlib import Path
import re
import tempfile
from types import SimpleNamespace
import unittest

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame

from audio_settings import AudioSettings
from opening_cinematic import OpeningCinematic, SCENE
from ui_style import UIStyle


class OpeningCinematicTests(unittest.TestCase):
    def setUp(self):
        pygame.display.init()
        pygame.font.init()
        temporary = tempfile.TemporaryDirectory(prefix='cinematic-unit-')
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.game = SimpleNamespace(window=pygame.display.set_mode((960, 640)),
                                    audio=AudioSettings(), _music_focused=True)
        self.game.ui = UIStyle(self.game)
        self.game.to_canvas = self.to_canvas
        self.canvas = pygame.Surface((480, 320))
        self.ui = pygame.Surface((960, 640))
        data = json.loads(SCENE.read_text())
        self.path = self.directory/'scene.json'
        self.path.write_text(json.dumps(data))

        def fixture_image(filename, size, color=None):
            target = self.directory/filename
            target.parent.mkdir(parents=True, exist_ok=True)
            image = pygame.Surface(size, pygame.SRCALPHA)
            if color is not None:
                image.fill(color)
            pygame.image.save(image, target)

        for index, record in enumerate(data['layers']):
            fixture_image(record['file'], data['canvas'], '#192a40' if index == 0 else None)
        if 'upper_sky' in data:
            sky = data['upper_sky']
            fixture_image(sky['file'], sky['size'], '#192a40')
        props = data.get('dynamic_props', {})
        for filename in props.get('lamp', {}).get('states', []):
            fixture_image(filename, (18, 30), '#b89b5d')
        if 'cup' in props:
            fixture_image(props['cup']['file'], (8, 8), '#b89b5d')
        if 'memorial' in props:
            fixture_image(props['memorial']['file'], (100, 160), '#736b64')
        for actor in data['actors']:
            path = self.directory/actor['manifest']
            path.parent.mkdir(parents=True)
            poses = {cue['pose']: cue['pose']+'.png' for cue in data['acting'][actor['id']]}
            image = pygame.Surface((96, 112), pygame.SRCALPHA)
            pygame.draw.rect(image, '#d8c49b', (24, 24, 48, 80))
            for filename in poses.values():
                pygame.image.save(image, path.parent/filename)
            manifest = {'canvas': [96, 112], 'anchor': [48, 104], 'poses': poses}
            if actor['id'] == 'mira':
                transition = pygame.Surface((96, 112), pygame.SRCALPHA)
                transition.fill('#875755')
                pygame.image.save(transition, path.parent/'kneel_sit.png')
                cues = data['acting']['mira']
                sit_index = next(i for i, cue in enumerate(cues) if cue['pose'] == 'sit')
                transition_id = cues[sit_index-1]['pose']+':sit'
                manifest['transitions'] = {transition_id: [
                    {'file': 'kneel_sit.png', 'duration_ms': 300}]}
            path.write_text(json.dumps(manifest))
        self.scene = OpeningCinematic(self.game, scene_path=self.path)

    def tearDown(self):
        pygame.quit()

    def to_canvas(self, point):
        width, height = self.game.window.get_size()
        scale = max(1, min(width//480, height//320))
        x, y = ((point[0]-(width-480*scale)//2)/scale,
                (point[1]-(height-320*scale)//2)/scale)
        return (x, y) if 0 <= x < 480 and 0 <= y < 320 else None

    def draw(self):
        self.scene.draw(self.canvas, self.ui)

    def shot_record(self, identifier):
        return next(record for record in self.scene.data['shots'] if record['id'] == identifier)

    def acting_cue(self, actor, pose):
        return next(cue for cue in self.scene.data['acting'][actor] if cue['pose'] == pose)

    def dialogue_record(self, identifier):
        return next(record for record in self.scene.data['dialogue']
                    if record['id'] == identifier)

    def key(self, *, repeat=False):
        self.scene.handle_event(pygame.event.Event(pygame.KEYDOWN,
                                                  key=pygame.K_ESCAPE,
                                                  repeat=repeat))

    def click(self, logical):
        width, height = self.game.window.get_size()
        scale = max(1, min(width//480, height//320))
        pos = (round((width-480*scale)//2+logical[0]*scale),
               round((height-320*scale)//2+logical[1]*scale))
        self.scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))

    def test_natural_completion_releases_before_one_callback(self):
        calls = []
        self.scene.start(lambda: calls.append((self.scene.active, self.scene.paused,
                                               self.scene.finished_reason)))
        self.scene.update(self.scene.duration-1)
        self.assertTrue(self.scene.active)
        self.scene.update(1)
        self.scene.update(200)
        self.scene.skip()
        self.assertEqual(calls, [(False, False, 'completed')])

    def test_reset_discards_callback_and_start_replays_from_first_shot(self):
        calls = []
        self.scene.start(lambda: calls.append('discarded'))
        self.scene.update(50)
        self.scene.reset()
        self.scene.update(200)
        self.assertEqual(calls, [])
        self.scene.start(lambda: calls.append('replayed'))
        self.assertEqual((self.scene.elapsed, self.scene.shot, self.scene.paused),
                         (0, 'valley', False))
        self.scene.skip()
        self.assertEqual(calls, ['replayed'])

    def test_escape_freezes_the_camera_caption_and_rendered_layers(self):
        self.scene.start()
        self.scene.update(14)
        self.key()
        self.draw()
        image = pygame.image.tobytes(self.canvas, 'RGB')
        state = self.scene.elapsed, self.scene.camera_position, self.scene.dialogue
        self.scene.update(40)
        self.draw()
        self.assertEqual((self.scene.elapsed, self.scene.camera_position, self.scene.dialogue), state)
        self.assertEqual(pygame.image.tobytes(self.canvas, 'RGB'), image)
        self.key(repeat=True)
        self.assertTrue(self.scene.paused)
        self.key()
        self.scene.update(.5)
        self.assertGreater(self.scene.elapsed, state[0])

    def test_focus_gain_does_not_override_manual_pause(self):
        self.scene.start()
        self.scene.update(1)
        self.scene.handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        self.scene.update(3)
        self.assertEqual(self.scene.elapsed, 1)
        self.key()
        self.scene.handle_event(pygame.event.Event(pygame.WINDOWFOCUSGAINED))
        self.scene.update(3)
        self.assertEqual(self.scene.elapsed, 1)
        self.assertTrue(self.scene.paused)
        self.key()
        self.scene.update(.5)
        self.assertEqual(self.scene.elapsed, 1.5)

    def test_skip_button_works_while_paused_and_other_clicks_do_nothing(self):
        calls = []
        self.scene.start(lambda: calls.append(self.scene.finished_reason))
        self.key()
        self.draw()
        self.click((20, 20))
        self.assertTrue(self.scene.active)
        self.scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1))
        self.click(self.scene.skip_rect.center)
        self.assertEqual(calls, ['skipped'])
        self.assertFalse(self.scene.paused)

    def test_letterbox_click_cannot_skip_but_scaled_button_can(self):
        self.game.window = pygame.display.set_mode((1100, 640))
        self.scene.start()
        self.draw()
        self.scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,
                                                  button=1, pos=(20, 620)))
        self.assertTrue(self.scene.active)
        self.scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1))
        self.click(self.scene.skip_rect.center)
        self.assertFalse(self.scene.active)

    def test_camera_pan_is_smooth_bounded_and_holds_for_conversation(self):
        self.scene.start()
        reveal = self.shot_record('reveal')
        conversation = self.shot_record('conversation')
        half_pan = (reveal['end']-reveal['start'])/2
        self.scene.update(reveal['start'])
        self.assertEqual(self.scene.camera_position, reveal['from'])
        self.scene.update(half_pan)
        midpoint = pygame.Vector2(reveal['from']).lerp(reveal['to'], .5)
        self.assertAlmostEqual(self.scene.camera_position.x, midpoint.x)
        self.assertAlmostEqual(self.scene.camera_position.y, midpoint.y)
        self.scene.update(half_pan)
        point = self.scene.camera_position.copy()
        self.scene.update((conversation['end']-conversation['start'])/2)
        self.assertEqual(self.scene.camera_position, point)
        self.assertEqual(self.scene.shot, 'conversation')
        for elapsed in range(math.ceil(self.scene.duration)+1):
            self.scene.elapsed = min(elapsed, self.scene.duration)
            x, y = self.scene.camera_position
            # Vector2.lerp can drift a few ulps even when both endpoints
            # are identical. Allow only numerical noise, not pixel overshoot.
            left, top, right, bottom = self.scene.data.get('camera_bounds', [0, 0, 480, 160])
            self.assertTrue(left-1e-9 <= x <= right+1e-9 and top-1e-9 <= y <= bottom+1e-9,
                            (elapsed, x, y))

    def test_temporal_caption_identifies_flashforward_before_the_reveal(self):
        self.scene.start()
        self.assertIsNone(self.scene.framing_caption)
        caption = self.scene.data['framing_caption']
        self.scene.update((caption['start']+caption['end'])/2)
        self.assertEqual(self.scene.framing_caption['text'], 'Later in the journey…')
        self.assertEqual(self.scene.shot, 'valley')
        self.assertIsNone(self.scene.dialogue)
        self.scene.update(caption['end']-self.scene.elapsed+1)
        self.assertIsNone(self.scene.framing_caption)

    def test_reduced_motion_changes_shots_without_continuous_pan(self):
        self.scene.start()
        self.game.audio.set_reduced_motion(True)
        reveal = self.shot_record('reveal')
        self.scene.update(reveal['start']+1)
        point = self.scene.camera_position.copy()
        self.scene.update(4)
        self.assertEqual(self.scene.camera_position, point)
        self.assertEqual(point, reveal['to'])
        self.draw()
        rendered = pygame.image.tobytes(self.canvas, 'RGB')
        self.scene.update(2)
        self.draw()
        self.assertEqual(pygame.image.tobytes(self.canvas, 'RGB'), rendered)

    def test_captions_fit_all_display_and_text_sizes_and_preserve_hand_area(self):
        self.scene.start()
        for size in ((480, 320), (960, 640)):
            self.game.window = pygame.display.set_mode(size)
            self.ui = pygame.Surface(size)
            for scale in (1, 1.25, 1.5):
                self.game.audio.text_scale = scale
                for record in self.scene.data['dialogue']:
                    self.scene.elapsed = record['start']+.1
                    self.draw()
                    rect = self.scene.caption_rect
                    self.assertTrue(pygame.Rect(0, 0, 480, 320).contains(rect))
                    self.assertFalse(rect.colliderect(self.scene.skip_rect))
                    # Faces/hands live approximately screen130..205 at the
                    # authored conversation shot. Text stays above or below.
                    self.assertTrue(rect.bottom <= 130 or rect.top >= 210,
                                    (size, scale, record['text'], rect))
                    painter = self.game.ui.painter(self.ui)
                    self.assertTrue(all(painter.font().size(line)[0] <= 412
                                        for line in self.scene.caption_lines))

    def test_expanded_exchange_matches_the_approved_speaker_transcript(self):
        guide = (SCENE.parents[3]/'docs/OPENING_CINEMATIC.md').read_text(encoding='utf-8')
        documented = re.findall(r'^- \*\*(Mira|Caelan):\*\* “(.*)”$', guide, re.MULTILINE)
        dialogue = self.scene.data['dialogue']
        self.assertEqual(len(dialogue), 30)
        self.assertEqual(len({record['id'] for record in dialogue}), 30)
        self.assertEqual([(record['speaker'], record['text']) for record in dialogue],
                         documented)
        order = [record['id'] for record in dialogue]
        beats = ('entrance', 'evacuation', 'surge', 'mill_memory',
                 'small_spell', 'two_of_us', 'one_moment')
        self.assertEqual([order.index(beat) for beat in beats],
                         sorted(order.index(beat) for beat in beats))

    def test_dialogue_gaps_are_brisk_and_short_replies_do_not_linger(self):
        dialogue = self.scene.data['dialogue']
        gaps = [following['start']-current['end']
                for current, following in zip(dialogue, dialogue[1:])]
        self.assertTrue(all(gap >= 1-1e-9 for gap in gaps))
        self.assertGreaterEqual(sum(abs(gap-1) < 1e-9 for gap in gaps), 20)
        for identifier in ('thanks', 'halden', 'told_me'):
            record = self.dialogue_record(identifier)
            self.assertGreaterEqual(record['end']-record['start'], 2)
            self.assertLessEqual(record['end']-record['start'], 4)
        short = self.dialogue_record('thanks')
        long = self.dialogue_record('small_spell')
        self.assertGreater(long['end']-long['start'],
                           2*(short['end']-short['start']))

    def test_the_complete_sip_finishes_before_the_cup_is_set_down(self):
        drink = self.acting_cue('caelan', 'drink')
        returning = next(cue for cue in self.scene.data['acting']['caelan']
                         if cue['start'] > drink['start'] and cue['pose'] == 'seated_cup')

        def transition_seconds(actor, identifier):
            record = next(record for record in self.scene.data['actors']
                          if record['id'] == actor)
            manifest = json.loads((SCENE.parent/record['manifest']).read_text())
            return sum(frame['duration_ms'] for frame in manifest['transitions'][identifier])/1000

        self.assertLess(drink['start']+transition_seconds('caelan', 'seated_cup:drink'),
                        returning['start'])
        self.assertLessEqual(returning['start']+transition_seconds('caelan', 'drink:seated_cup'),
                             self.scene.data['events']['cup_set_down'])
        self.assertFalse(any(record['speaker'] == 'Caelan'
                             and record['start'] < returning['start']
                             and record['end'] > drink['start']
                             for record in self.scene.data['dialogue']))

    def test_authored_transition_runs_once_then_holds_destination_pose(self):
        self.scene.start()
        actor = next(actor for actor in self.scene.actors if actor[0]['id'] == 'mira')
        _, _, frames, transitions = actor
        start = self.acting_cue('mira', 'sit')['start']
        self.scene.elapsed = start+.1
        image = self.scene._actor_frame('mira', frames, transitions)
        self.assertEqual(image.get_at((0, 0)), pygame.Color('#875755'))
        self.scene.elapsed = start+.4
        self.assertIs(self.scene._actor_frame('mira', frames, transitions), frames['sit'])
        self.game.audio.set_reduced_motion(True)
        self.scene.elapsed = start+.1
        self.assertIs(self.scene._actor_frame('mira', frames, transitions), frames['sit'])

    def test_invalid_delta_cannot_corrupt_visual_clock(self):
        self.scene.start()
        for delta in (-1, float('nan'), float('inf'), None, '4'):
            self.scene.update(delta)
        self.assertEqual(self.scene.elapsed, 0)

    def test_missing_or_escaping_art_does_not_activate_partial_scene(self):
        self.scene.data['layers'][0]['file'] = '../outside.png'
        with self.assertRaises(ValueError):
            self.scene.start()
        self.assertFalse(self.scene.active)
        self.assertIsNone(self.scene.layers)


if __name__ == '__main__':
    unittest.main()
