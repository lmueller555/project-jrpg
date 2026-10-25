"""Native-canvas placement and hit areas for in-world portrait dialogue."""
import os
from types import SimpleNamespace
import unittest

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame

from speech_bubble import MAX_LINES, TEXT_WIDTH, SpeechBubble
from ui_style import FOREST


class SpeechBubbleTests(unittest.TestCase):
    def setUp(self):
        pygame.font.init()
        self.npc = SimpleNamespace(position=(250, 220), data={'name': 'Mother Serene'})
        self.player = SimpleNamespace(position=(270, 246))
        self.anchor = (250, 190)
        portraits = {}
        for key, color in (('serene', '#549b68'), ('caelan', '#886fb2')):
            portraits[key] = pygame.Surface((72, 72))
            portraits[key].fill(color)
        self.social = SimpleNamespace(
            active=True, pending=False, choosing=False, actor=self.npc,
            page={'speaker': 'serene', 'lines': ['Come sit and eat.', 'There is bread enough.']},
            data={'speakers': {'serene': {'name': 'Mother Serene', 'portrait': 'serene'},
                               'caelan': {'name': 'Caelan', 'portrait': 'caelan'}}},
            portraits=portraits,
            font=pygame.font.Font(None, 18), name_font=pygame.font.Font(None, 20),
            hint_font=pygame.font.Font(None, 14),
            choice_options=[{'text': "I'll help"}, {'text': 'Not just yet'}],
            game=SimpleNamespace(player=self.player,
                                 world=SimpleNamespace(data={'player_draw_anchor': (12, 30)}),
                                 camera=SimpleNamespace(position=lambda: (0, 0))),
            anchor_position=lambda: self.anchor,
            resolve_speaker=lambda: self.npc)
        self.bubble = SpeechBubble(self.social)
        self.canvas = pygame.Surface((480, 320))

    def tearDown(self):pygame.quit()

    def test_above_speaker_uses_compact_portrait_panel(self):
        layout = self.bubble.layout()
        self.assertLessEqual(layout.panel.bottom, self.anchor[1]-8)
        self.assertLess(layout.panel.width, 320)
        self.assertEqual(layout.portrait.size, (48, 48))
        self.assertTrue(layout.panel.contains(layout.portrait))
        self.assertEqual(layout.tail_side, 'bottom')
        self.assertEqual((TEXT_WIDTH, MAX_LINES), (224, 3))

    def test_top_edge_repositions_bubble_without_covering_either_head(self):
        self.anchor = (240, 28)
        self.player.position = (256, 70)
        layout = self.bubble.layout()
        self.assertGreaterEqual(layout.panel.top, 76)
        for head in (pygame.Rect(226, 26, 28, 38), pygame.Rect(242, 38, 28, 38)):
            self.assertFalse(layout.panel.colliderect(head))
        self.assertEqual(layout.tail_side, 'top')

    def test_all_viewport_edges_keep_portrait_text_and_buttons_inside(self):
        self.social.choosing = True
        for anchor in ((1, 1), (478, 1), (1, 318), (478, 318)):
            with self.subTest(anchor=anchor):
                self.anchor = anchor
                layout = self.bubble.draw(self.canvas)
                self.assertTrue(self.canvas.get_rect().contains(layout.panel))
                self.assertTrue(layout.panel.contains(layout.portrait))
                for rect in layout.choice_rects:self.assertTrue(layout.panel.contains(rect))

    def test_camera_motion_moves_anchor_and_valid_answer_hit_areas_together(self):
        self.social.choosing = True
        before = self.bubble.layout(camera=(0, 0))
        after = self.bubble.layout(camera=(10, 10))
        self.assertEqual(after.anchor, (before.anchor[0]-10, before.anchor[1]-10))
        self.assertEqual(after.panel.topleft, (before.panel.x-10, before.panel.y-10))
        for first, second in zip(before.choice_rects, after.choice_rects):
            self.assertEqual(second.center, (first.centerx-10, first.centery-10))
            self.assertFalse(second.collidepoint((second.right, second.bottom)))

    def test_player_reply_switches_anchor_and_approved_portrait(self):
        serene = self.bubble.draw(self.canvas)
        self.assertEqual(self.canvas.get_at(serene.portrait.center)[:3], (84, 155, 104))
        self.social.page = {'speaker': 'caelan', 'lines': ['I am coming.']}
        self.social.resolve_speaker = lambda: self.player
        self.anchor = (270, 216)
        reply = self.bubble.draw(self.canvas)
        self.assertEqual(reply.anchor, self.anchor)
        self.assertEqual(reply.portrait_key, 'caelan')
        self.assertEqual(self.canvas.get_at(reply.portrait.center)[:3], (136, 111, 178))

    def test_player_reply_keeps_initiating_npc_face_visible(self):
        self.social.page = {'speaker': 'caelan', 'lines': ['Who needs us?']}
        self.social.resolve_speaker = lambda: self.player
        self.anchor = (270, 216)
        layout = self.bubble.draw(self.canvas)
        npc_head = pygame.Rect(236, 188, 28, 38)
        player_head = pygame.Rect(256, 214, 28, 38)
        self.assertFalse(layout.panel.colliderect(npc_head))
        self.assertFalse(layout.panel.colliderect(player_head))
        self.assertEqual(layout.anchor, self.anchor)
        self.assertEqual(layout.tail_side, 'bottom')
        self.assertLessEqual(layout.panel.bottom, npc_head.top-8)

    def test_scripted_reply_keeps_other_in_room_speakers_visible(self):
        self.social.actor = None
        self.npc.data['id'] = 'mother_serene'
        self.social.data['speakers']['serene']['actor_id'] = 'mother_serene'
        self.social.game.world.npcs = [self.npc]
        self.social.pages = [{'speaker': 'serene'}, {'speaker': 'caelan'}]
        self.social.page = {'speaker': 'caelan', 'lines': ['Thank you.']}
        self.social.resolve_speaker = lambda: self.player
        self.anchor = (270, 216)
        layout = self.bubble.draw(self.canvas)
        self.assertFalse(layout.panel.colliderect(pygame.Rect(236, 188, 28, 38)))
        self.assertEqual(layout.anchor, self.anchor)

    def test_off_room_speaker_has_identified_portrait_without_false_tail(self):
        self.social.resolve_speaker = lambda: None
        layout = self.bubble.draw(self.canvas)
        self.assertTrue(layout.offscreen)
        self.assertIsNone(layout.tail_side)
        self.assertEqual(layout.portrait_key, 'serene')

    def test_visible_sleeping_player_head_is_not_labeled_as_a_nearby_voice(self):
        self.social.game.opening = SimpleNamespace(_sleeping=True)
        self.player.story_visible = False
        self.social.page = {'speaker': 'caelan', 'lines': ['I am awake.']}
        self.social.resolve_speaker = lambda: self.player
        layout = self.bubble.draw(self.canvas)
        self.assertFalse(layout.offscreen)
        self.assertIsNotNone(layout.tail_side)

    def test_two_quest_answers_are_separate_visible_buttons(self):
        self.social.choosing = True
        layout = self.bubble.draw(self.canvas)
        self.assertEqual(len(layout.choice_rects), 2)
        left, right = layout.choice_rects
        self.assertFalse(left.colliderect(right))
        self.assertEqual(left.top, right.top)
        for rect in layout.choice_rects:
            self.assertEqual(self.canvas.get_at((rect.x+3, rect.y+3))[:3], pygame.Color(FOREST)[:3])
        self.assertLessEqual(right.right, layout.panel.right-8)

    def test_three_answers_expand_vertically_within_bubble(self):
        self.social.choosing = True
        self.social.choice_options.append({'text': 'Tell me more'})
        layout = self.bubble.draw(self.canvas)
        self.assertEqual(len(layout.choice_rects), 3)
        for previous, following in zip(layout.choice_rects, layout.choice_rects[1:]):
            self.assertLess(previous.bottom, following.top)
        self.assertTrue(layout.panel.contains(layout.choice_rects[-1]))

    def test_long_answers_use_wrapped_full_width_buttons(self):
        self.social.choosing = True
        self.social.choice_prompt = 'Which household shall we visit first?'
        self.social.choice_options = [
            {'text': 'We should take the medicine to Halden first.'},
            {'text': 'Tell me where Elira lives before we leave.'}]
        layout = self.bubble.draw(self.canvas)
        self.assertEqual(layout.choice_rects[0].width, TEXT_WIDTH)
        self.assertGreaterEqual(len(layout.option_lines[0]), 2)
        self.assertFalse(layout.choice_rects[0].colliderect(layout.choice_rects[1]))
        self.assertTrue(layout.panel.contains(layout.choice_rects[1]))
        for lines, rect in zip(layout.option_lines, layout.choice_rects):
            for line in lines:
                self.assertLessEqual(self.social.font.size(line)[0], rect.width-12)

    def test_pending_prop_handoff_hint_is_attached_to_npc(self):
        self.social.active = False
        self.social.pending = True
        layout = self.bubble.draw(self.canvas)
        self.assertTrue(layout.pending)
        self.assertIsNone(layout.portrait)
        self.assertEqual(layout.anchor, self.anchor)
        self.assertLess(layout.panel.height, 40)
        self.assertFalse(layout.choice_rects)

    def test_no_active_conversation_does_not_draw_or_supply_stale_buttons(self):
        self.social.active = self.social.pending = False
        self.canvas.fill('#112233')
        self.assertIsNone(self.bubble.draw(self.canvas))
        self.assertEqual(self.canvas.get_at((240, 160))[:3], (17, 34, 51))

    def test_original_portrait_pixels_and_dimensions_are_preserved(self):
        source = self.social.portraits['serene']
        before = pygame.image.tobytes(source, 'RGB')
        self.bubble.draw(self.canvas)
        self.assertEqual(source.get_size(), (72, 72))
        self.assertEqual(pygame.image.tobytes(source, 'RGB'), before)

    def test_short_reply_has_less_empty_space_than_three_line_reply(self):
        self.social.page['lines'] = ['Thank you.']
        short = self.bubble.layout()
        self.social.page['lines'] = ['There is still much to do.',
                                     'Halden needs his medicine.',
                                     'Take Tomas along with you.']
        longer = self.bubble.layout()
        self.assertLess(short.panel.height, longer.panel.height)
        self.assertTrue(short.panel.contains(short.portrait))

    def test_high_resolution_portrait_and_choices_keep_world_coordinate_hitboxes(self):
        self.social.choosing = True
        canvas = pygame.Surface((1440, 960))
        layout = self.bubble.draw(canvas)
        self.assertEqual(layout.anchor, self.anchor)
        self.assertTrue(pygame.Rect(0, 0, 480, 320).contains(layout.panel))
        self.assertEqual(canvas.get_at((layout.portrait.centerx*3, layout.portrait.centery*3))[:3],
                         (84, 155, 104))
        for rect in layout.choice_rects:
            self.assertTrue(layout.panel.contains(rect))

    def test_choice_hover_and_press_have_distinct_visible_states(self):
        self.social.choosing = True
        layout = self.bubble.draw(self.canvas)
        rect = layout.choice_rects[0]
        sample = (rect.right-4, rect.top+4)
        normal = self.canvas.get_at(sample)
        self.social.pointer_position = rect.center
        self.bubble.draw(self.canvas)
        hover = self.canvas.get_at(sample)
        self.social.pointer_pressed = True
        self.bubble.draw(self.canvas)
        pressed = self.canvas.get_at(sample)
        self.assertNotEqual(normal, hover)
        self.assertNotEqual(hover, pressed)


if __name__ == '__main__':unittest.main()
