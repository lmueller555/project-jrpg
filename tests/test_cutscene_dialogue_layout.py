"""Off-speaker mill cutscene dialogue stays readable without covering its shot."""
import os
from types import SimpleNamespace
import unittest

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame

from speech_bubble import MAX_LINES, PANEL_WIDTH, TEXT_WIDTH, SpeechBubble
from ui_style import UIStyle


class CutsceneDialogueLayoutTests(unittest.TestCase):
    def setUp(self):
        pygame.font.init()
        self.player = SimpleNamespace(position=(180, 510))
        self.mira = SimpleNamespace(position=(160, 534), data={'id': 'mira_worker'})
        self.quest = SimpleNamespace(encounter_cutscene_active=True,
                                     encounter_cutscene_phase='conversation')
        self.game = SimpleNamespace(player=self.player,
                                    world=SimpleNamespace(data={'player_draw_anchor': (12, 30)}),
                                    mill_quest=self.quest,
                                    audio=SimpleNamespace(text_scale=1, reduced_motion=True))
        self.game.ui = UIStyle(self.game)
        portraits = {}
        for key, color in (('mira', '#d48b91'), ('caelan', '#886fb2')):
            portraits[key] = pygame.Surface((72, 72))
            portraits[key].fill(color)
        self.anchor = (180, 480)
        self.social = SimpleNamespace(
            game=self.game, active=True, pending=False, choosing=False, actor=None,
            script_identifier='mill_encounter_intro',
            page={'speaker': 'mira', 'lines': ['Look at its tusks.', 'It must have brought the tree down.']},
            data={'speakers': {'mira': {'name': 'Mira', 'portrait': 'mira'},
                               'caelan': {'name': 'Caelan', 'portrait': 'caelan'}}},
            portraits=portraits, choice_options=[],
            anchor_position=lambda: self.anchor, resolve_speaker=lambda: self.mira)
        self.bubble = SpeechBubble(self.social)
        self.canvas = pygame.Surface((480, 320))

    def tearDown(self):pygame.quit()

    def assert_readable(self, layout):
        self.assertTrue(self.canvas.get_rect().contains(layout.panel))
        self.assertTrue(layout.panel.contains(layout.portrait))
        painter = self.game.ui.painter(self.canvas)
        for index, line in enumerate(self.social.page['lines']):
            rect = pygame.Rect((0, 0), painter.font().size(line))
            rect.topleft = (layout.text_origin[0], layout.text_origin[1]+index*layout.line_height)
            self.assertTrue(layout.panel.contains(rect), (line, rect, layout.panel))
            self.assertLess(rect.bottom, layout.panel.bottom-painter.font('small').get_height()-7)

    def test_creature_shot_uses_a_fixed_lower_panel_without_false_speech_tail(self):
        first = self.bubble.draw(self.canvas, camera=(120, 203))
        self.assertEqual(first.panel.bottom, 310)
        self.assertEqual(first.panel.centerx, 240)
        self.assertEqual(first.panel.width, PANEL_WIDTH)
        self.assertIsNone(first.tail_side)
        self.assertEqual(first.name_lines, ('Mira',))
        self.assertFalse(first.panel.colliderect(pygame.Rect(192, 46, 96, 72)))
        self.assert_readable(first)
        # Panning or swapping the speaking observer cannot drag the panel.
        self.social.page = {'speaker': 'caelan', 'lines': self.social.page['lines']}
        self.social.resolve_speaker = lambda: self.player
        self.anchor = (20, 640)
        after = self.bubble.draw(self.canvas, camera=(96, 210))
        self.assertEqual(after.panel, first.panel)
        self.assertEqual(after.name_lines, ('Caelan',))
        self.assertIsNone(after.tail_side)

    def test_return_shot_places_warning_above_the_stopped_party(self):
        self.quest.encounter_cutscene_phase = 'pan_back'
        self.social.page['lines'] = ['Caelan, come back to me.', 'Slowly. Keep your feet under you.']
        layout = self.bubble.draw(self.canvas, camera=(0, 232))
        self.assertEqual(layout.panel.top, 6)
        for head in (pygame.Rect(166, 246, 28, 38), pygame.Rect(146, 270, 28, 38)):
            self.assertFalse(layout.panel.colliderect(head))
        self.assert_readable(layout)
        self.assertIsNone(layout.tail_side)

    def test_large_text_preserves_all_three_lines_and_the_creature_clearance(self):
        self.game.audio.text_scale = 1.5
        # Same source-page contract as SocialSystem: 224px wrapping, three lines.
        painter = self.game.ui.painter(self.canvas)
        text = 'Those fresh gouges in the bark match its tusks.'
        self.social.page['lines'] = painter.wrap(text, TEXT_WIDTH)[:MAX_LINES]
        layout = self.bubble.draw(self.canvas, camera=(120, 203))
        self.assertEqual(layout.panel.bottom, 310)
        self.assertGreater(layout.panel.top, 118)
        self.assertFalse(layout.panel.colliderect(pygame.Rect(192, 46, 96, 72)))
        self.assert_readable(layout)
        self.quest.encounter_cutscene_phase = 'pan_back'
        layout = self.bubble.draw(self.canvas, camera=(0, 232))
        self.assertLess(layout.panel.bottom, 246)
        self.assert_readable(layout)

    def test_ordinary_and_unrelated_dialogue_keep_actor_anchored_bubbles(self):
        self.quest.encounter_cutscene_active = False
        self.social.actor = self.mira
        self.anchor = (250, 190)
        self.mira.position = (250, 220)
        self.player.position = (270, 246)
        normal = self.bubble.layout(camera=(0, 0))
        self.assertEqual(normal.tail_side, 'bottom')
        self.assertLessEqual(normal.panel.bottom, self.anchor[1]-8)
        self.quest.encounter_cutscene_active = True
        self.social.script_identifier = 'mill_warning'
        unrelated = self.bubble.layout(camera=(0, 0))
        self.assertEqual(unrelated.panel, normal.panel)
        self.assertEqual(unrelated.tail_side, normal.tail_side)

    def test_display_scaling_does_not_change_cinematic_layout_or_source_portraits(self):
        source = self.social.portraits['mira']
        before = pygame.image.tobytes(source, 'RGB')
        native = self.bubble.draw(self.canvas, camera=(120, 203))
        large = pygame.Surface((1440, 960))
        scaled = self.bubble.draw(large, camera=(120, 203))
        self.assertEqual(scaled.panel.bottom, native.panel.bottom)
        self.assertEqual(scaled.panel.centerx, native.panel.centerx)
        self.assertEqual(scaled.panel.width, native.panel.width)
        self.assertEqual(large.get_at((scaled.portrait.centerx*3, scaled.portrait.centery*3))[:3],
                         (212, 139, 145))
        self.assertEqual(pygame.image.tobytes(source, 'RGB'), before)


if __name__ == '__main__':unittest.main()
