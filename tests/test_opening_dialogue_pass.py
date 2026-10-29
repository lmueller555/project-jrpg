"""Read the new opening as a player: real scenes, literal emotes and directions."""
import json
import os
from pathlib import Path
import re
import tempfile
import unittest
from types import SimpleNamespace
from collections import deque
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import pygame
import main
from elira_visit import STOOL_APPROACH, TABLE_APPROACH
from halden_visit import SOURCES, STORAGE, town_path
from npc_routines import find_path
from quests import OPENING_QUEST, MILL_QUEST
from speech_bubble import MAX_LINES, TEXT_WIDTH
from venn_visit import PIN_APPROACH, CHANNEL_APPROACH
from test_mill_battle_gameplay import finish_mill_battle

ROOT = Path(__file__).resolve().parents[1]
FILES = ('assets/story/opening.json', 'assets/story/halden/scene.json',
         'assets/story/elira/scene.json', 'assets/story/venn/scene.json',
         'assets/story/opening_conclusion.json', 'assets/story/mill/scene.json')


def dialogue_sets():
    """Only spoken passages touched by this pass, not world metadata."""
    result = {}
    for name in FILES:
        data = json.loads((ROOT/name).read_text())
        for key, lines in data.items():
            if isinstance(lines, list) and lines and isinstance(lines[0], dict) and 'speaker' in lines[0]:
                result[name+':'+key] = lines
    data = json.loads((ROOT/'assets/dialogue/eldenmere.json').read_text())
    for conversation in data['characters']['mother_serene']['conversations']:
        if conversation['id'].startswith('serene_quest_'):
            result[conversation['id']] = conversation['lines']
    return result


def plain(text):return re.sub(r'\*[^*]+\*', '', text).strip()


class OpeningDialogueDriver:
    """The verifier and tests share inputs, never seeded main-quest progress."""
    def __init__(self, method='magicks', order=('elira', 'venn'), on_page=None):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name)/'journey.json'
        self.g = main.Game(fullscreen=False, start_on_title=True, save_path=self.path,
                           settings_path=Path(self.temp.name)/'settings.json')
        self.g.audio.set_music(0);self.g.audio.set_effects(0);pygame.event.clear()
        self.method = method;self.order = order;self.on_page = on_page
        self.pages = [];self.sources = {};self.scenes = [];self.transitions = []
        self.actions = [];self.identity_checks = 0;self._last_action = None

    def close(self):self.temp.cleanup();pygame.quit()

    def key(self, key=pygame.K_e):
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=key, repeat=False))
        pygame.event.post(pygame.event.Event(pygame.KEYUP, key=key, repeat=False))
        assert self.g.handle_events()

    def click(self, point):
        w, h = self.g.window.get_size();scale = max(1, min(w//480, h//320))
        position = (round((w-480*scale)/2+point[0]*scale), round((h-320*scale)/2+point[1]*scale))
        for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            pygame.event.post(pygame.event.Event(kind, button=1, pos=position))
        assert self.g.handle_events()

    def tick(self, seconds=.05, direction=(0, 0)):
        before = self.g.world.data['id'];self.g.update(seconds, direction, False)
        after = self.g.world.data['id']
        if before != after:self.transitions.append([before, after])
        action = (self.g.opening.action_name, self.g.halden_visit.action,
                  self.g.elira_visit.action, self.g.venn_visit.action, self.g.mill_quest.action)
        if action != self._last_action:
            self.actions.append([after, list(action)]);self._last_action = action

    def until(self, predicate, seconds=100, read=True):
        for _ in range(round(seconds/.05)):
            if predicate():return
            if getattr(getattr(self.g, 'combat', None), 'active', False):
                finish_mill_battle(self.g, read_aftermath=False)
            if read and self.g.social.locked:self.read()
            self.tick()
        raise AssertionError(('Timeout', self.g.world.data['id'], tuple(self.g.player.position),
                              self.g.opening.stage, self.g.social.script_identifier))

    def identifier(self):
        return self.g.social.script_identifier or (self.g.social.conversation or {}).get('id')

    def record_page(self):
        social = self.g.social;identifier = self.identifier();page = social.page
        if identifier not in self.sources:
            self.sources[identifier] = [dict(line) for line in social._source_lines]
        if not self.scenes or self.scenes[-1] != identifier:self.scenes.append(identifier)
        actor = social.resolve_speaker();speaker = page['speaker']
        # The wake-up voice is deliberately on the other side of the bedroom door.
        remote = identifier == 'opening_wake' and speaker == 'tomas'
        assert actor is not None or remote, ('Missing speaker', identifier, speaker, self.g.world.data['id'])
        if actor is not None and actor is not self.g.player:
            assert actor in self.g.world.npcs
            assert sum(a is actor for world in self.g.scenes.values() for a in world.npcs) == 1
            self.identity_checks += 1
        self.g.draw();layout = social.bubble.layout()
        assert pygame.Rect(0, 0, 480, 320).contains(layout.panel), (identifier, layout.panel)
        assert len(page['lines']) <= MAX_LINES
        assert all(social.font.size(line)[0] <= TEXT_WIDTH for line in page['lines'])
        self.pages.append({'scene': identifier, 'page': social.page_index,
                           'source_line': page['source_line'], 'speaker': speaker,
                           'room': self.g.world.data['id'], 'text': ' '.join(page['lines'])})
        if self.on_page:self.on_page(self, identifier, page)

    def read(self):
        for _ in range(1000):
            if not self.g.social.locked:return
            if not self.g.social.active:self.tick(.02);continue
            if self.g.social.choosing:return
            self.record_page();self.key(pygame.K_SPACE)
        raise AssertionError(('Unread conversation', self.identifier()))

    def walk(self, goal, destination=None, read=True, *, return_if_blocked=False):
        world = self.g.world;goal = pygame.Vector2(*(round(value/2)*2 for value in goal))
        # Replan only when an independently moving resident crosses the path.
        for attempt in range(8):
            route = find_path(world, self.g.player.position, goal, world.probe_size, None)
            if route is None and world is self.g.town:
                route = town_path(world, self.g.player.position, goal, SimpleNamespace(probe_size=world.probe_size), None)
            if route is None:
                # A resident may occupy the next approach during a replan.
                # Actor callers choose another live offset; fixed destinations
                # wait briefly, still failing if the route remains blocked.
                if return_if_blocked:return False
                if read and self.g.social.locked:self.read()
                self.tick(.2)
                continue
            stalled = False
            for corner in route:
                for _ in range(900):
                    if getattr(getattr(self.g, 'combat', None), 'active', False):
                        finish_mill_battle(self.g, read_aftermath=False)
                    if self.g.world is not world:
                        assert self.g.world.data['id'] == destination
                        return
                    if self.g.social.locked:
                        if not read:return
                        self.read()
                        if self.g.social.choosing:return
                    delta = pygame.Vector2(corner)-self.g.player.position
                    if delta.length()<.03:break
                    before = self.g.player.position.copy()
                    self.tick(min(.05, delta.length()/72), delta)
                    assert self.g.world is not world or world.can_stand(self.g.player.position)
                    if before == self.g.player.position and not self.g.household_action:
                        stalled = True;break
                else:raise AssertionError(('Walking stalled', world.data['id'], corner))
                if stalled:break
            if not stalled:break
            self.tick(.2)
        else:raise AssertionError(('Residents blocked route', world.data['id'], tuple(goal)))
        if destination and self.g.world is world:
            door = next(d for d in world.doors if pygame.Vector2(d.data['anchor']).distance_to(goal)<2)
            direction = (0, -1) if door.data['entry_side'] == 'north' else (0, 1)
            for _ in range(160):
                if self.g.world is not world:return
                if read and self.g.social.locked:self.read()
                self.tick(1/30, direction)
            raise AssertionError(('Door did not transfer', world.data['id'], destination))
        if read and self.g.social.locked:self.read()
        return True

    def travel(self, identifier):
        destination = self.g._scene_by_id(identifier)
        for _ in range(12):
            if self.g.world is destination:return
            start = self.g.world;queue = [(start, None)];seen = {start.path};edge = None
            for world, first in queue:
                if world is destination:edge = first;break
                for door in world.doors:
                    other = self.g._load_scene(ROOT/door.data['destination'])
                    if other.path not in seen:
                        seen.add(other.path);queue.append((other, first or (door, other)))
            assert edge, ('No door connection', start.data['id'], identifier)
            door, other = edge;self.walk(door.data['anchor'], other.data['id'])
        raise AssertionError(('Too many doors', identifier))

    def actor(self, actor, expected):
        if expected in self.sources:return True
        assert actor in self.g.world.npcs
        for _ in range(8):
            for offset in ((0, 24), (0, 28), (24, 0), (-24, 0), (0, -24)):
                if actor not in self.g.world.npcs:return False
                goal = pygame.Vector2(*(round(value/2)*2 for value in actor.position+offset))
                if not self.g.world.can_stand(goal):continue
                if self.g.world is not self.g.town and find_path(self.g.world, self.g.player.position, goal, self.g.world.probe_size, None) is None:continue
                approached = self.walk(goal, return_if_blocked=True)
                if expected in self.sources:return True
                if approached is False:continue
                if self.g.social.locked:self.read()
                if expected in self.sources:return True
                if actor not in self.g.world.npcs:return False
                # Residents can move while incidental dialogue is read. Replan
                # against their live position instead of starting out of range.
                if self.g.player.position.distance_to(actor.position)>self.g.social.data['release_radius']:continue
                if self.g.social.start(actor):
                    self.read()
                    # A pending request can be cancelled while the resident
                    # finishes a delivery. Only recorded prose counts as read.
                    if expected in self.sources:return True
            self.tick(.2)
        raise AssertionError(('Could not approach actor', actor.data['id'], expected))

    def breakfast(self):
        self.key(pygame.K_RETURN);self.tick(.7)
        assert self.g.opening.stage == 'wake';self.read()
        self.until(lambda: self.g.opening.stage == 'explore')
        self.travel('sanctuary_dining')
        self.until(lambda: self.g.opening.stage == 'assignment')
        self.offer()

    def offer(self, accept=True):
        serene = next(a for a in self.g.persistent_npcs if a.data['id'] == 'mother_serene')
        self.actor(serene, 'serene_quest_offer')
        assert self.g.social.choosing
        if accept:
            self.click(self.g.social.choice_rects[0].center)
            self.read();self.until(lambda: self.g.opening.stage == 'done')
            assert self.g.quests.status(OPENING_QUEST) == 'active'

    def halden(self):
        self.travel('halden');h = self.g.halden_visit
        self.walk((176, 210))  # Clear the shared arrival threshold for Tomas.
        self.until(lambda: h.tomas.scene_id == 'halden' and h.owns_tomas)
        self.actor(h.halden, 'halden_arrival');self.until(lambda: h.medicine and h.action is None)
        for i in (0, 1, 2):
            self.walk((SOURCES[i][0], SOURCES[i][1]+18));self.key()
            if i == 1:
                self.walk((170, 210));self.until(lambda: h.tomas_job is None)
                assert 1 in h.stored
            else:
                self.until(lambda: h.action is None);assert h.carried == i
                self.walk((STORAGE[i][0], STORAGE[i][1]+22));self.key()
                self.until(lambda: h.action is None);assert i in h.stored
        self.actor(h.halden, 'halden_conclusion')
        if 'halden_goodbye' not in self.sources:
            goal = h.tomas.position+(24, 0)
            if not self.g.world.can_stand(goal):goal = h.tomas.position+(0, 24)
            self.walk(goal)
            self.until(lambda: 'halden_goodbye' in self.sources)
        self.walk((176, 210));self.until(lambda: self.g.quests.objective_status(OPENING_QUEST, 'halden') == 'completed')

    def elira(self):
        self.travel('elira');c = self.g.elira_visit
        self.actor(c.elira, 'elira_arrival');self.until(lambda: c.delivered and c.action is None)
        self.walk(STOOL_APPROACH);self.key();self.until(lambda: c.action is None and c.lantern == 'carried')
        self.walk(TABLE_APPROACH);self.key();self.until(lambda: c.action is None and c.lantern == 'table')
        self.actor(c.elira, 'elira_resolution');assert c.completed

    def venn(self):
        self.travel('venn');c = self.g.venn_visit
        self.actor(c.family['father'], 'venn_arrival');self.until(lambda: c.delivered and c.action is None)
        self.travel(self.g.town.data['id'])
        for key, goal in (('pin', PIN_APPROACH), ('channel', CHANNEL_APPROACH)):
            self.walk(goal);self.key();self.read();assert key in c.inspected
        self.walk(PIN_APPROACH);self.key();self.read();assert self.g.social.choosing
        self.click(self.g.social.choice_rects[0 if self.method == 'tools' else 1].center)
        self.until(lambda: c.repaired and c.action is None)
        assert c.magicks_failed == (self.method == 'magicks')
        self.travel('venn');self.actor(c.family['father'], 'venn_resolution');assert c.completed

    def report(self):
        serene = self.g.opening_conclusion.serene
        for _ in range(8):
            self.travel(self.g._routine_worlds[serene].data['id'])
            if serene in self.g.world.npcs:
                if self.actor(serene, 'serene_quest_report'):break
        else:raise AssertionError('Could not meet Serene on her sanctuary rounds')
        self.travel('sanctuary_hall');self.walk((184, 258))
        self.until(lambda: self.g.opening_conclusion.stage == 'done')
        assert self.g.quests.status(OPENING_QUEST) == 'completed'
        assert self.g.quests.status(MILL_QUEST) == 'available'

    def mill_event(self, kind):
        c = self.g.mill_quest
        assert c._target() and c._target()[0] == kind, (kind, c._target())
        self.key();self.read();assert 'mill_'+kind in self.sources

    def mill_at(self, key):
        self.walk(self.g.mill_quest.points[key]);c = self.g.mill_quest
        self.until(lambda: c.mira in self.g.world.npcs and c.mira.position.distance_to(self.g.player.position)<=76)
        if self.g.social.locked:self.read()

    def mill_link(self, upstream):
        self.walk((720, 32) if upstream else (180, 546));c = self.g.mill_quest
        self.until(lambda: c.mira in self.g.world.npcs and c.mira.position.distance_to(self.g.player.position)<=76)
        if self.g.social.locked:self.read()
        assert self.g.nearby_world_link()
        before = self.g.world.data['id'];self.key()
        after = self.g.world.data['id'];self.transitions.append([before, after])
        assert before != after
        self.until(lambda: c.mira in self.g.world.npcs)

    def mill(self):
        self.travel(self.g.town.data['id']);c = self.g.mill_quest
        self.actor(c.mira, 'mill_reunion');assert c.active
        self.mill_at('mechanism');self.mill_event('mechanism')
        self.mill_at('race');self.mill_event('race')
        self.mill_link(True)
        self.mill_at('intake');self.mill_event('intake')
        self.mill_at('bypass');self.mill_event('prepare');self.until(lambda: c.prepared and c.action is None)
        if self.g.social.locked:self.read()
        self.mill_at('spell');self.mill_event('spell_intro');self.until(lambda: c.spell_done)
        self.read();assert c.encouraged
        self.mill_at('lever');self.mill_event('repair');self.until(lambda: c.restored and c.action is None)
        if self.g.social.locked:self.read()
        self.mill_link(False);self.mill_at('mill_station');self.mill_event('verify')
        self.mill_event('resolution');assert c.resolved

    def run(self):
        self.breakfast();self.halden()
        for household in self.order:getattr(self, household)()
        self.report();self.mill();self.g.save_progress()
        assert self.g.quests.status(OPENING_QUEST) == self.g.quests.status(MILL_QUEST) == 'completed'
        return self


class OpeningDialogueDriverTimingTests(unittest.TestCase):
    def test_approach_replans_moving_target_and_retries_cancelled_pending_request(self):
        for interruption in ('moving_target', 'pending_cancelled', 'blocked_approach'):
            with self.subTest(interruption=interruption):
                expected = 'serene_quest_report'
                actor = SimpleNamespace(data={'id': 'mother_serene'}, position=pygame.Vector2(100, 100))
                world = SimpleNamespace(npcs=[actor], can_stand=lambda point: True)
                social = SimpleNamespace(locked=False, data={'release_radius': 36})
                driver = object.__new__(OpeningDialogueDriver)
                driver.g = SimpleNamespace(world=world, town=world, social=social,
                                           player=SimpleNamespace(position=pygame.Vector2(0, 0)))
                driver.sources = {};driver.scenes = ['tomas_repeat']
                walks = [];starts = [];reads = []

                def walk(goal, *, return_if_blocked=False):
                    walks.append(tuple(goal));driver.g.player.position.update(goal)
                    if interruption == 'blocked_approach' and len(walks) == 1:
                        self.assertTrue(return_if_blocked)
                        return False
                    if interruption == 'moving_target' and len(walks) == 1:
                        actor.position.x += 100

                def start(target):
                    self.assertIs(target, actor)
                    self.assertLessEqual(driver.g.player.position.distance_to(actor.position), 36)
                    starts.append(target)
                    return True

                def read():
                    reads.append(True)
                    if interruption == 'pending_cancelled' and len(reads) == 1:return
                    driver.sources[expected] = [{'speaker': 'serene', 'text': 'There you are.'}]

                driver.walk = walk;driver.read = read;social.start = start
                self.assertTrue(driver.actor(actor, expected))
                self.assertIn(expected, driver.sources)
                self.assertGreaterEqual(len(walks), 2)
                self.assertEqual(len(starts), 2 if interruption == 'pending_cancelled' else 1)

    def test_walk_waits_for_transient_resident_and_fails_if_route_stays_blocked(self):
        driver = object.__new__(OpeningDialogueDriver)
        world = SimpleNamespace(data={'id': 'hall'}, probe_size=(8, 4), can_stand=lambda point: True)
        driver.g = SimpleNamespace(world=world, town=object(), household_action=False,
                                   player=SimpleNamespace(position=pygame.Vector2(0, 0)),
                                   social=SimpleNamespace(locked=False))
        waits = []

        def tick(seconds=.05, direction=(0, 0)):
            vector = pygame.Vector2(direction)
            if vector.length_squared():driver.g.player.position += vector.normalize()*72*seconds
            else:waits.append(seconds)

        driver.tick = tick
        with patch(__name__+'.find_path', side_effect=(None, deque([(4, 0)]))):
            self.assertTrue(driver.walk((4, 0)))
        self.assertEqual(driver.g.player.position, (4, 0))
        self.assertEqual(waits, [.2])
        with patch(__name__+'.find_path', return_value=None):
            self.assertFalse(driver.walk((8, 0), return_if_blocked=True))
            with self.assertRaisesRegex(AssertionError, 'Residents blocked route'):
                driver.walk((8, 0))
        self.assertEqual(driver.g.player.position, (4, 0))


class OpeningDialoguePassTests(unittest.TestCase):
    def setUp(self):
        self.driver = OpeningDialogueDriver();self.addCleanup(self.driver.close)

    def test_briefing_introduces_households_needs_landmarks_and_festival(self):
        data = json.loads((ROOT/'assets/dialogue/eldenmere.json').read_text())
        conversations = data['characters']['mother_serene']['conversations']
        offer = next(c for c in conversations if c['id'] == 'serene_quest_offer')
        text = ' '.join(plain(line['text']) for line in offer['lines'])
        for fragment in ('Halden', 'medicine', 'flour', 'Festival of Light', 'Elira',
                         'bread and lamp oil', 'southern bridge', 'Venn', 'eastern terrace'):
            with self.subTest(fragment=fragment):self.assertIn(fragment, text)
        self.assertGreaterEqual(len(offer['lines']), 12)
        self.assertTrue(any(line['text'] == 'There’s bread and lamp oil for Elira, too. She’ll be getting her lantern ready for the Festival of Light.' for line in offer['lines']))

    def test_literal_emotes_are_balanced_selective_and_replace_parentheticals(self):
        passages = dialogue_sets();total = cues = 0
        for identifier, lines in passages.items():
            for line in lines:
                total += 1;text = line['text'];cues += bool('*' in text)
                with self.subTest(passage=identifier, text=text):
                    self.assertEqual(text.count('*') % 2, 0)
                    self.assertNotIn('**', text)
                    self.assertNotRegex(text, r'\((?:laugh|grin|smil|soft|quiet|pause|concern|hesitat)')
                    for cue in re.findall(r'\*([^*]+)\*', text):
                        self.assertTrue(cue.strip());self.assertLess(len(cue), 100)
        self.assertGreaterEqual(cues, 15)
        self.assertLess(cues, total*.5)

    def test_all_spoken_pages_keep_literal_asterisks_and_fit_normal_and_large_text(self):
        g = self.driver.g
        for scale in (1.0, 1.5):
            g.audio.set_text_scale(scale)
            for identifier, lines in dialogue_sets().items():
                pages = g.social._make_pages(lines)
                for source_index, line in enumerate(lines):
                    rendered = ' '.join(' '.join(page['lines']) for page in pages if page['source_line'] == source_index)
                    self.assertEqual(rendered, ' '.join(line['text'].split()), (scale, identifier, source_index))
                for page in pages:
                    self.assertLessEqual(len(page['lines']), MAX_LINES)
                    self.assertTrue(all(g.social.font.size(text)[0] <= TEXT_WIDTH for text in page['lines']))

    def test_new_game_reaches_full_briefing_before_explicit_acceptance(self):
        d = self.driver;d.key(pygame.K_RETURN);d.tick(.7);d.read()
        d.until(lambda: d.g.opening.stage == 'explore');d.travel('sanctuary_dining')
        d.until(lambda: d.g.opening.stage == 'assignment')
        d.offer(accept=False)
        self.assertEqual(d.g.quests.status(OPENING_QUEST), 'available')
        self.assertFalse(d.g.halden_visit.owns_tomas)
        self.assertIn('Venn', ' '.join(line['text'] for line in d.sources['serene_quest_offer']))
        d.g.social.cancel()
        self.assertEqual(d.g.quests.status(OPENING_QUEST), 'available')
        self.assertFalse(d.g.inventory.was_granted(OPENING_QUEST))

    def test_legacy_assignment_without_tomas_keeps_same_offer_and_all_directions(self):
        d = self.driver;d.key(pygame.K_RETURN);d.tick(.7);d.read()
        d.until(lambda: d.g.opening.stage == 'explore');d.travel('sanctuary_dining')
        d.until(lambda: d.g.opening.stage == 'assignment')
        tomas = d.g.halden_visit.tomas;hall = d.g._scene_by_id('sanctuary_hall')
        # A legacy assignment can have Tomas in the hall. This narrow fixture
        # checks the fallback; full-route checks never alter actor stations.
        for world in d.g.scenes.values():
            if tomas in world.npcs:world.npcs.remove(tomas)
        hall.npcs.append(tomas);tomas.position.update(208, 282);tomas.scene_id = 'sanctuary_hall'
        d.g._routine_worlds[tomas] = hall
        d.offer(accept=False)
        lines = d.sources['serene_quest_offer'];self.assertFalse(any(line['speaker'] == 'tomas' for line in lines))
        text = ' '.join(line['text'] for line in lines)
        for word in ('Halden', 'Elira', 'Venn', 'upper bridge', 'southern bridge', 'eastern terrace'):
            self.assertIn(word, text)
        self.assertTrue(d.g.social.choosing)
        self.assertEqual(d.g.quests.status(OPENING_QUEST), 'available')

    def test_repair_aftermath_releases_grip_on_acknowledgment_or_cancel_and_never_replays_on_load(self):
        from test_mill_quest import MillQuestTests
        for acknowledge in (False, True):
            with self.subTest(acknowledge=acknowledge):
                h = MillQuestTests();h.setUp()
                try:
                    h.cast();h.at('lever', True)
                    self.assertTrue(h.c.interact());h.read_all()
                    h.until(lambda: h.c.restored and h.c.action is None)
                    self.assertEqual(h.g.social.script_identifier, 'mill_repair_done')
                    self.assertTrue(h.c._holding_repair_pose())
                    self.assertIsNotNone(getattr(h.g.player, 'story_sprite', None))
                    snapshot = h.c.to_dict()
                    if acknowledge:
                        h.g.social.advance();h.tick()
                        self.assertFalse(h.c._holding_repair_pose())
                        self.assertIsNone(getattr(h.g.player, 'story_sprite', None))
                    h.g.social.cancel()
                    self.assertFalse(h.c._holding_repair_pose())
                    self.assertIsNone(getattr(h.g.player, 'story_sprite', None))
                    self.assertEqual(h.c.to_dict(), snapshot)
                    h.reload()
                    self.assertEqual(h.c.to_dict(), snapshot)
                    self.assertFalse(h.c._holding_repair_pose())
                    self.assertFalse(h.g.social.active)
                    self.assertIsNone(getattr(h.g.player, 'story_sprite', None))
                finally:h.tearDown();h.doCleanups()

    def test_unseeded_route_failed_magick_and_all_main_scenes_complete(self):
        d = self.driver.run()
        self.assertTrue(d.g.venn_visit.magicks_failed)
        self.assertIn('mill_encouragement_failed', d.sources)
        self.assertNotIn('mill_encouragement', d.sources)
        for identifier in ('opening_greeting', 'opening_breakfast', 'opening_kindness',
                           'serene_quest_offer', 'opening_acceptance', 'halden_arrival',
                           'halden_conclusion', 'halden_goodbye', 'elira_arrival',
                           'elira_resolution', 'venn_arrival', 'venn_resolution',
                           'serene_quest_report', 'opening_mill_arrival', 'mill_reunion',
                           'mill_mechanism', 'mill_race', 'mill_diagnosis', 'mill_intake',
                           'mill_prepare', 'mill_prepare_done', 'mill_spell_intro', 'mill_repair', 'mill_repair_done', 'mill_verify',
                           'mill_resolution'):
            with self.subTest(scene=identifier):self.assertIn(identifier, d.sources)
        self.assertGreater(d.identity_checks, 100)
        self.assertEqual(sum(d.g.mill_quest.mira in world.npcs for world in d.g.scenes.values()), 1)

    def test_unseeded_tools_route_keeps_other_household_order_and_no_invented_failure(self):
        self.driver.close();self.driver = OpeningDialogueDriver(method='tools', order=('venn', 'elira'))
        self.addCleanup(self.driver.close)
        d = self.driver.run()
        self.assertFalse(d.g.venn_visit.magicks_failed)
        self.assertIn('mill_encouragement', d.sources)
        self.assertNotIn('mill_encouragement_failed', d.sources)
        self.assertLess(d.scenes.index('venn_resolution'), d.scenes.index('elira_resolution'))
        self.assertFalse(any('Venn' in line['text'] for line in d.sources['mill_encouragement']))


if __name__ == '__main__':unittest.main()
