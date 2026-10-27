"""Capture MQ04's village section using actual game movement and callbacks.

Only the already-shipped frame_ready checkpoint is seeded. Every new village
scene, companion transfer and objective completion follows the production game.
"""
import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
from pathlib import Path
import json
import sys
import tempfile
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pygame
from PIL import Image, ImageDraw, ImageFont
from main import Game
from halden_visit import town_path
from npc_routines import find_path
from tools.capture_lantern_quest import Capture as OpeningCapture, seed_previous_quests
from tools.capture_mill_quest import save_gif

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'docs/reviews/lantern_village'
LANTERN = 'CH01_MQ04'
MAIN_SCENES = ('departure', 'mill_arrival', 'mill_flour', 'venn_arrival',
               'venn_preparations', 'elira_welcome', 'elira_lantern',
               'elira_memory', 'elira_company', 'elira_goodbye', 'reflection')
FIRST_FOUR = ['join_preparations', 'build_frame', 'visit_neighbours', 'visit_elira']


def seed_frame_checkpoint(game):
    """Seed the shipped PR1 result, never any of this section's new progress."""
    seed_previous_quests(game)
    assert game.accept_quest(LANTERN)
    for key in FIRST_FOUR[:2]:assert game.quests.complete_objective(LANTERN, key)
    game.world = game.town
    game.player.position.update(game.lantern_quest.points['workshop'])
    assert game.lantern_quest.restore({'version': 1, 'stage': 'frame_ready'})
    game.opening_fade = 0;game.transfer_cooldown = 0
    game.social.blocked.clear();game.quests.drain_events();game.quest_ui.reset()
    game.camera.reset()
    assert game.quests.states[LANTERN]['completed_objectives'] == FIRST_FOUR[:2]
    assert game.lantern_quest.stage == 'frame_ready'


class Capture:
    wait = OpeningCapture.wait
    frame = OpeningCapture.frame

    def __init__(self):
        OUT.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory()
        self.g = Game(fullscreen=False, start_on_title=False,
                      save_path=Path(self.temp.name)/'journey.json',
                      settings_path=Path(self.temp.name)/'settings.json')
        self.g.audio.set_music(0);self.g.audio.set_effects(0)
        self.c = self.g.lantern_quest
        self.frames = [];self.durations = [];self.saved_stills = set()
        self.seen_pages = [];self.seen_contexts = [];self.transitions = [];self.companion_transfers = []
        self.tick_index = 0;self.label = 'What the Village Carries'
        self.font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 13)
        seed_frame_checkpoint(self.g)

    def save_still(self, name):
        self.g.draw();pygame.image.save(self.g.ui_surface, OUT/name)
        self.saved_stills.add(name)

    def tick(self, seconds=1/30, direction=(0, 0), record=True):
        before = self.g.world.data['id']
        companions = {a: self.c._world(a).data['id'] for a in (self.c.liam, self.c.tomas)}
        self.g.update(seconds, direction, False);self.tick_index += 1
        if self.g.world.data['id'] != before:
            self.transitions.append([before, self.g.world.data['id']])
        for actor, origin in companions.items():
            destination = self.c._world(actor).data['id']
            if destination != origin:self.companion_transfers.append([actor.data['id'], origin, destination])
        if record and self.tick_index % 30 == 0:self.frame(120)

    def at(self, key):
        point = pygame.Vector2(self.c.village_points[key])
        for radius in (0, 8, 16, 24):
            for offset in ((0, radius), (-radius, 0), (radius, 0), (0, -radius)):
                candidate = point+offset
                if self.g.world.can_stand(candidate):
                    self.walk(candidate);self.g.transfer_cooldown = 0;return
        raise AssertionError(('No interaction station', key, tuple(point)))

    def walk(self, goal, next_scene=None, seconds=150):
        """Choose a navigable route, then use the ordinary player mover."""
        origin = self.g.world
        goal = pygame.Vector2(*(round(value/2)*2 for value in goal))
        route = [];stalled = 0
        probe = SimpleNamespace(probe_size=origin.probe_size)
        for _ in range(round(seconds*30)):
            if self.g.world is not origin:
                assert self.g.world.data['id'] == next_scene;return
            if self.g.social.active:self.read()
            if self.g.player.position.distance_to(goal) < 1.2:
                if next_scene is None:return
                door = next(d for d in origin.doors
                            if pygame.Vector2(d.data['anchor']).distance_to(goal) < 3)
                self.tick(direction=(0, -1 if door.data['entry_side'] == 'north' else 1))
                continue
            if not route or stalled >= 15:
                found = find_path(origin, self.g.player.position, goal, origin.probe_size, None)
                if found is None and origin is self.g.town:
                    found = town_path(origin, self.g.player.position, goal, probe, None)
                assert found is not None, ('No route', origin.data['id'],
                                           tuple(self.g.player.position), tuple(goal))
                route = list(found);stalled = 0
            if not route:continue
            delta = pygame.Vector2(route[0])-self.g.player.position
            if delta.length() < 1.2:route.pop(0);continue
            previous = self.g.player.position.copy()
            self.tick(min(1/30, delta.length()/72), delta)
            stalled = stalled+1 if self.g.player.position == previous else 0
        raise AssertionError(('Walking stalled', origin.data['id'], self.c.stage,
                              tuple(self.g.player.position), tuple(goal)))

    def read(self):
        identifier = self.g.social.script_identifier;count = 0
        while self.g.social.active and self.g.social.script_identifier == identifier:
            count += 1;assert count < 300, ('Unfinished dialogue', identifier)
            for _ in range(4):self.tick(record=False)
            self.frame(650)
            page = self.g.social.page
            self.seen_pages.append((identifier, self.g.social.page_index, page['speaker']))
            self.seen_contexts.append((identifier, self.c.stage))
            kind = identifier.removeprefix('lantern_') if identifier else ''
            name = kind+'.png'
            if kind in MAIN_SCENES and name not in self.saved_stills:self.save_still(name)
            if kind == 'elira_memory' and page['speaker'] == 'elira' and 'elira_memory_detail.png' not in self.saved_stills:
                self.save_still('elira_memory_detail.png')
            text = ' '.join(page.get('lines', []))
            if kind == 'elira_memory' and "with me interrupting" in text:
                self.save_still('elira_laughter.png')
            if kind == 'elira_company' and "hear him get it wrong" in text:
                self.save_still('elira_quiet.png')
            self.g.social.advance()

    def interact(self, kind):
        self.wait(lambda: self.c._target() == kind)
        for actor in (self.c.liam, self.c.tomas):
            assert actor in self.g.world.npcs, ('Missing companion', kind, actor.data['id'])
            assert actor.position.distance_to(self.g.player.position) < 160, ('Distant companion', kind, actor.data['id'])
        assert self.c.interact(), (kind, self.c.stage)
        assert self.g.social.script_identifier == 'lantern_'+kind
        self.read()

    def exit_room(self):
        door = next(d for d in self.g.world.doors if d.data['id'] == 'courtyard')
        self.walk(door.data['anchor'], self.g.town.data['id'])

    def enter_room(self, identifier):
        door = next(d for d in self.g.town.doors if d.data['id'] == identifier)
        self.walk(door.data['anchor'], identifier)

    def run(self):
        self.frame(1000)
        self.label = 'Leave Liam’s frame and drawing safely with Mira'
        self.walk(self.c.points['workshop']);self.interact('departure')
        assert self.c.stage == 'outing'
        self.label = 'Halden is preparing the festival flour at the working mill'
        self.at('mill');self.interact('mill_arrival');self.interact('mill_flour')
        assert self.c.stage == 'mill_visited'
        self.save_still('mill_world.png')
        self.label = 'The Venn family prepares within the child’s limits'
        self.enter_room('venn');self.at('venn')
        self.interact('venn_arrival');self.interact('venn_preparations')
        assert self.c.stage == 'neighbours_visited'
        self.save_still('venn_world.png');self.exit_room()
        self.label = 'Elira welcomes Liam, Caelan and Tomas'
        self.enter_room('elira');self.at('elira')
        for kind in ('elira_welcome', 'elira_lantern', 'elira_memory', 'elira_company', 'elira_goodbye'):
            self.interact(kind)
        assert self.c.stage == 'elira_farewell'
        self.save_still('elira_world.png')
        self.label = 'Leave together with a question for another conversation'
        self.exit_room();self.at('reflection');self.interact('reflection')
        assert self.c.stage == 'elira_visited'
        assert self.g.quests.status(LANTERN) == 'active'
        assert self.g.quests.states[LANTERN]['completed_objectives'] == FIRST_FOUR
        assert self.g.mill_quest.mill_restored and not self.g.opening_conclusion.mill_stopped
        assert self.g.elira_visit.lantern == 'table'
        assert 'CH01_MQ05' not in self.g.quests.definitions
        self.save_still('endpoint_world.png');self.frame(1600)
        self.g.save_progress()
        saved = json.loads((Path(self.temp.name)/'journey.json').read_text())
        assert saved['lantern_quest'] == {'version': 1, 'stage': 'elira_visited'}
        main_ids = {'lantern_'+kind for kind in MAIN_SCENES}
        actual = {identifier for identifier, _, _ in self.seen_pages}
        assert main_ids <= actual, ('Missing scenes', main_ids-actual)
        for kind in MAIN_SCENES:
            expected = len(self.g.social._make_pages(self.c.lines[kind]))
            observed = sum(identifier == 'lantern_'+kind for identifier, _, _ in self.seen_pages)
            assert observed == expected, ('Missing or repeated pages', kind, observed, expected)
        assert self.transitions.count(['eldenmere.playable', 'venn']) == 1
        assert self.transitions.count(['venn', 'eldenmere.playable']) == 1
        assert self.transitions.count(['eldenmere.playable', 'elira']) == 1
        assert self.transitions.count(['elira', 'eldenmere.playable']) == 1
        for identifier in ('liam', 'tomas'):
            for origin, destination in (('eldenmere.playable', 'venn'), ('venn', 'eldenmere.playable'),
                                         ('eldenmere.playable', 'elira'), ('elira', 'eldenmere.playable')):
                assert self.companion_transfers.count([identifier, origin, destination]) == 1
        self.write_artifacts(saved, actual-main_ids)
        self.temp.cleanup();pygame.quit()

    def write_artifacts(self, saved, optional):
        frames = [];durations = [];travel = 0
        for frame, duration in zip(self.frames, self.durations):
            if duration < 300:
                travel += 1
                if travel % 4 != 1:continue
            frames.append(frame);durations.append(duration)
        size = None
        for width, colors in ((320, 64), (300, 48), (280, 40), (256, 32)):
            size = (width, round(width*344/480))
            compact = [frame.resize(size, Image.Resampling.NEAREST) for frame in frames]
            save_gif(OUT/'quest.gif', compact, durations, colors)
            if (OUT/'quest.gif').stat().st_size < 1_000_000:break
        transcript = ['# What the Village Carries — dialogue', '',
                      'Captured through the actual game from the shipped PR1 frame checkpoint.', '']
        for kind in MAIN_SCENES:
            transcript += ['## '+kind.replace('_', ' ').title(), '']
            for line in self.c.lines[kind]:
                name = self.g.social.data['speakers'][line['speaker']]['name']
                transcript += ['**'+name+':** '+line['text'], '']
        (OUT/'dialogue.md').write_text('\n'.join(transcript), encoding='utf-8')
        (OUT/'capture.json').write_text(json.dumps({
            'quest_id': LANTERN, 'stage': self.c.stage, 'quest_completed': False,
            'completed_objectives': saved['quests']['quests'][LANTERN]['completed_objectives'],
            'dialogue_pages': len(self.seen_pages), 'main_scenes': list(MAIN_SCENES),
            'optional_dialogue': sorted(optional), 'overview_frames': len(frames),
            'overview_size': list(size), 'actual_door_transitions': self.transitions,
            'companion_door_transitions': self.companion_transfers,
            'seeded': 'completed MQ01–MQ03 and shipped MQ04 PR1 frame_ready checkpoint only',
            'mill_running': True, 'festival_started': False, 'elira_lantern': 'table',
            'stills': sorted(self.saved_stills)}, indent=2)+'\n')
        (OUT/'README.md').write_text(
            '# What the Village Carries — review\n\n'
            'The capture uses the production Game, normal walking, actual Venn and Elira '
            'cottage doors, companion staging and all eleven new dialogue callbacks. '
            'Only the already-shipped MQ04 PR1 frame checkpoint and earlier quests are seeded.\n\n'
            '`quest.gif` contains every main dialogue page in a time-compressed overview. '
            'Use the native PNG stills and `dialogue.md` for readable scene review.\n\n'
            'The endpoint is `elira_visited`: MQ04 remains active with its first four '
            'objectives complete. Liam’s frame and drawing remain at Mira’s workshop, '
            'Elira keeps her existing memorial lantern, and the mill remains running.\n\n'
            'Reproduce with `python tools/capture_lantern_village.py`.\n', encoding='utf-8')
        print('Captured MQ04 village:', len(frames), 'overview frames;', len(self.seen_pages), 'dialogue pages')
        print('quest.gif', (OUT/'quest.gif').stat().st_size, 'bytes')


def capture():Capture().run()
if __name__ == '__main__':capture()
