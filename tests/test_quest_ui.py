"""Player-facing quest feedback: modal input, timing and room projection."""
import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
from collections import deque
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import pygame
from quest_ui import QuestUI


class Log:
    def __init__(self):
        self.definitions = {'q': {'title': 'A Day Like Any Other', 'giver': 'serene',
                                 'summary': 'Help the households of Eldenmere.',
                                 'objectives': [{'id': 'halden', 'text': 'Help Halden with three grain sacks.'},
                                                {'id': 'elira', 'text': 'Retrieve Elira\'s memorial lantern.', 'requires': ['halden']} ]}}
        self.states = {'q': {'status': 'active', 'completed_objectives': []}}
        self.events = []
    def drain_events(self):
        events, self.events = self.events, []
        return events
    def objective_status(self, identifier, objective):
        return 'active' if objective == 'halden' else 'queued'
    def marker_for(self, actor):
        return '?' if self.states['q']['status'] == 'ready' and actor == 'serene' else '!' if actor == 'serene' else None
    def tracker_text(self):
        return 'Visit Halden with Tomas.'


class Actor:
    def __init__(self):
        self.data = {'id': 'serene'}
        self.position = pygame.Vector2(80, 80)
        self.draw_anchor = [12, 30]
        self.image = pygame.Surface((24, 36), pygame.SRCALPHA)
        self.image.fill('white')
    def sprite(self, elapsed):
        return self.image


def door(destination, anchor=(100, 80)):
    return SimpleNamespace(data={'destination': destination, 'anchor': anchor})


class QuestUITests(unittest.TestCase):
    def setUp(self):
        pygame.display.init()
        pygame.font.init()
        pygame.display.set_mode((480, 320))
        self.actor = Actor()
        town = SimpleNamespace(npcs=[], doors=[door('assets/maps/eldenmere/building_interiors/rooms/sanctuary_hall/map.json')],
                               data={'id': 'eldenmere.playable'}, size=(1536, 1344))
        hall = SimpleNamespace(npcs=[], data={'id': 'sanctuary_hall'}, doors=[door('assets/maps/eldenmere/building_interiors/rooms/sanctuary_dining/map.json')])
        dining = SimpleNamespace(npcs=[self.actor], data={'id': 'sanctuary_dining'}, doors=[])
        self.game = SimpleNamespace(quests=Log(), town=town, world=dining, social=SimpleNamespace(locked=False),
                                    map_open=False, elapsed_ms=1000, title=SimpleNamespace(music_enabled=False),
                                    scenes={'town': town, 'hall': hall, 'dining': dining},
                                    persistent_npcs=[self.actor], _routine_worlds={self.actor: dining})
        self.ui = QuestUI(self.game)
        self.canvas = pygame.Surface((480, 320))

    def tearDown(self):
        pygame.quit()

    def test_notice_queue_is_ordered_and_hidden_time_does_not_consume_it(self):
        self.game.quests.events = [{'kind': k, 'quest_id': 'q', 'title': 'Quest', 'text': k}
                                   for k in ('accepted', 'objective', 'ready', 'completed')]
        self.ui.journal_open = True
        self.ui.update(30)
        self.assertIsNone(self.ui.current_notice)
        self.assertEqual(len(self.ui.notices), 4)
        self.ui.close_journal()
        with patch.object(self.ui, '_chime') as sound:
            self.ui.update(0)
            self.assertEqual(self.ui.current_notice['kind'], 'accepted')
            initial = self.ui.notice_seconds
            self.game.map_open = True
            self.ui.update(30)
            self.assertEqual(self.ui.notice_seconds, initial)
            self.game.map_open = False
            self.ui.update(initial+.1)
            self.assertEqual(self.ui.current_notice['kind'], 'objective')
            self.assertEqual(sound.call_count, 2)
        self.ui.reset()
        self.assertIsNone(self.ui.current_notice)
        self.assertFalse(self.ui.notices)

    def test_journal_lists_distinct_queued_and_completed_states_and_scrolls(self):
        self.game.quests.definitions['q']['objectives'] *= 20
        self.ui.toggle_journal()
        self.ui.draw_journal(self.canvas)
        self.assertGreater(self.ui.max_scroll, 0)
        text = ' '.join(row[0] for row in self.ui._journal_rows())
        self.assertIn('IN PROGRESS', text)
        self.assertIn('[ ]', text)
        self.assertIn('[-]', text)
        self.assertIn('after Halden', text)
        self.assertTrue(self.ui.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, y=-2)))
        self.assertEqual(self.ui.scroll, 64)
        self.ui.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_END))
        self.assertEqual(self.ui.scroll, self.ui.max_scroll)
        self.ui.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        self.assertFalse(self.ui.journal_open)
        self.assertFalse(self.ui.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN)))

    def test_nested_sanctuary_giver_projects_to_entrance_without_loading_scenes(self):
        before = dict(self.game.scenes)
        self.assertEqual(self.ui._map_position(self.actor), (100, 80))
        self.assertEqual(self.game.scenes, before)
        with patch.object(self.ui, '_symbol') as symbol:
            self.ui.draw_map_markers(self.canvas, (28, 66), (220, 192))
            symbol.assert_called_once()
            self.assertEqual(symbol.call_args.args[1], '!')
            self.assertEqual(symbol.call_args.args[2], (42, 77))
        self.game.quests.states['q']['status'] = 'ready'
        with patch.object(self.ui, '_symbol') as symbol:
            self.ui.draw_map_markers(self.canvas, (28, 66), (220, 192))
            self.assertEqual(symbol.call_args.args[1], '?')
        self.game.town.npcs.append(self.actor)
        self.assertEqual(self.ui._map_position(self.actor), (80, 80))

    def test_rendering_contains_text_and_hides_hud_behind_modal_views(self):
        self.canvas.fill('black')
        self.ui.draw_markers(self.canvas, (0, 0))
        self.ui.draw_tracker(self.canvas)
        self.assertNotEqual(pygame.image.tobytes(self.canvas, 'RGB'), bytes(480*320*3))
        for modal in ('map', 'dialogue', 'journal'):
            self.game.map_open = modal == 'map'
            self.game.social.locked = modal == 'dialogue'
            self.ui.journal_open = modal == 'journal'
            self.canvas.fill('black')
            self.ui.draw_markers(self.canvas, (0, 0))
            self.ui.draw_tracker(self.canvas)
            self.assertEqual(pygame.image.tobytes(self.canvas, 'RGB'), bytes(480*320*3))
        lines = self.ui.wrap('W'*200, self.ui.font, 112)
        self.assertTrue(all(self.ui.font.size(line)[0] <= 112 for line in lines))

    def test_acceptance_and_completion_announcements_name_the_quest(self):
        for kind, label in (('accepted', 'Quest accepted'), ('completed', 'Quest completed')):
            event = {'kind': kind, 'title': 'A Day Like Any Other', 'text': 'Your objectives are in the journal.'}
            headings, body = self.ui._notification_content(event)
            self.assertEqual(' '.join(headings), label+': A Day Like Any Other')
            self.assertTrue(all(self.ui.small_font.size(line)[0] <= 338 for line in headings))
            self.assertEqual(' '.join(body), event['text'])
        event = {'kind': 'objective', 'title': 'Quest', 'text': 'Medicine delivered to Halden.'}
        headings, body = self.ui._notification_content(event)
        self.assertEqual(headings, ['Objective completed'])
        self.assertEqual(body, ['Medicine delivered to Halden.'])

    def test_no_audio_device_is_nonfatal_and_disabled_music_mutes_chimes(self):
        with patch('pygame.mixer.get_init', return_value=None), patch('pygame.mixer.init', side_effect=pygame.error('No audio')):
            self.game.title.music_enabled = True
            self.ui._chime('accepted')
        self.game.title.music_enabled = False
        with patch('pygame.mixer.init') as init:
            self.ui._chime('completed')
            init.assert_not_called()


if __name__ == '__main__':
    unittest.main()
