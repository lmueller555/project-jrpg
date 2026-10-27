"""Capture MQ04's first section through the actual Game and quest callbacks.

Only completed MQ01--MQ03 prerequisites and the starting player station are
seeded. All new quest dialogue, doors, companion movement and construction use
the same paths as a normal playthrough. The overview is time-compressed; full
resolution stills and a complete transcript accompany it for dialogue review.
"""
import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
from pathlib import Path
import json
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pygame
from PIL import Image, ImageDraw, ImageFont
from main import Game
from npc_routines import find_path
from quests import OPENING_QUEST, MILL_QUEST, REGENT_QUEST
from tools.capture_mill_quest import save_gif

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'docs/reviews/lantern_quest'
LANTERN = 'CH01_MQ04'
MAIN_SCENES = ('invitation', 'classroom', 'design', 'permission', 'workshop',
               'test_shape', 'assemble', 'lift', 'frame_ready')


def seed_previous_quests(game):
    """Set only previously shipped quest facts, never MQ04 progress."""
    assert game.accept_quest(OPENING_QUEST)
    for key in ('halden', 'elira', 'venn'):
        assert game.quests.complete_objective(OPENING_QUEST, key)
    game._sync_inventory()
    game.halden_visit.restore();game.elira_visit.restore();game.venn_visit.restore()
    assert game.quests.turn_in(OPENING_QUEST, 'mother_serene')
    assert game.quests.unlock(MILL_QUEST)
    game.opening_conclusion.restore({'version': 1, 'stage': 'done'})
    assert game.accept_quest(MILL_QUEST)
    for objective in game.quests.definitions[MILL_QUEST]['objectives']:
        assert game.quests.complete_objective(MILL_QUEST, objective['id'])
    assert game.quests.turn_in(MILL_QUEST, 'mira_worker')
    assert game.mill_quest.restore({
        'version': 1, 'inspected': ['mechanism', 'race', 'intake'],
        'prepared': True, 'spell_done': True, 'encouraged': True,
        'restored': True, 'verified': True, 'resolved': True})
    game.opening.restore({'version': 1, 'stage': 'disabled'})
    if game.quests.status(REGENT_QUEST) == 'locked':
        assert game.quests.unlock(REGENT_QUEST)
    assert game.accept_quest(REGENT_QUEST)
    for objective in game.quests.definitions[REGENT_QUEST]['objectives']:
        assert game.quests.complete_objective(REGENT_QUEST, objective['id'])
    assert game.quests.turn_in(REGENT_QUEST, 'mother_serene')
    assert game.regent_quest.restore({'version': 1, 'stage': 'done'})
    if game.quests.status(LANTERN) == 'locked':assert game.quests.unlock(LANTERN)
    assert game.lantern_quest.restore(None)
    game.world = game.town
    game.player.position.update(game.lantern_quest.points['invitation'])
    game.player.facing = 'back'
    game.opening_fade = 0;game.transfer_cooldown = 0
    game.social.blocked.clear();game.quests.drain_events();game.quest_ui.reset()
    game.camera.reset()
    assert game.quests.status(LANTERN) == 'available'
    assert game.lantern_quest.stage == 'idle'


class Capture:
    def __init__(self):
        OUT.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory()
        self.g = Game(fullscreen=False, start_on_title=False,
                      save_path=Path(self.temp.name)/'journey.json',
                      settings_path=Path(self.temp.name)/'settings.json')
        self.g.audio.set_music(0);self.g.audio.set_effects(0)
        self.c = self.g.lantern_quest
        self.frames = [];self.durations = [];self.craft = [];self.craft_durations = []
        self.seen_pages = [];self.seen_contexts = [];self.saved_stills = set()
        self.tick_index = 0;self.label = 'A Light of His Own / festival preparations'
        self.font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 13)
        seed_previous_quests(self.g)

    def frame(self, duration=120):
        self.g.draw()
        source = Image.frombytes('RGB', self.g.ui_surface.get_size(),
                                 pygame.image.tobytes(self.g.ui_surface, 'RGB'))
        out = Image.new('RGB', (480, 344), '#e8edf2')
        out.paste(source.resize((480, 320), Image.Resampling.NEAREST), (0, 24))
        ImageDraw.Draw(out).text((8, 4), self.label, font=self.font, fill='#243529')
        self.frames.append(out);self.durations.append(duration)

    def save_still(self, name):
        self.g.draw();pygame.image.save(self.g.ui_surface, OUT/name)
        self.saved_stills.add(name)

    def tick(self, seconds=1/30, direction=(0, 0), record=True):
        was_action = bool(self.c.action)
        self.g.update(seconds, direction, False);self.tick_index += 1
        if self.c.action == 'assemble' and self.c.action_time >= 1.0 and 'assembly_contact.png' not in self.saved_stills:
            self.save_still('assembly_contact.png')
        if self.c.action == 'lift' and .7 <= self.c.action_time < 1.2 and 'lifting_support.png' not in self.saved_stills:
            self.save_still('lifting_support.png')
        if record and self.tick_index % 30 == 0:self.frame(120)
        if (was_action or self.c.action) and self.tick_index % 3 == 0:
            self.g.draw()
            image = Image.frombytes('RGB', self.g.ui_surface.get_size(),
                                    pygame.image.tobytes(self.g.ui_surface, 'RGB'))
            self.craft.append(image.resize((480, 320), Image.Resampling.NEAREST))
            self.craft_durations.append(100)

    def wait(self, predicate, seconds=150):
        for _ in range(round(seconds*30)):
            if predicate():return
            self.tick()
        raise AssertionError(('Timeout', self.c.stage, self.c.action,
                              self.g.world.data['id'], tuple(self.g.player.position),
                              getattr(self.c, '_ready', None)))

    def walk(self, goal, next_scene=None, seconds=150):
        """Walk with live collisions and replan around moving residents."""
        origin = self.g.world
        # The game's local A* grid advances by two pixels. Interaction anchors
        # may be odd-valued; approach their nearest grid point, still well
        # within the controller's interaction radius.
        goal = pygame.Vector2(*(round(value/2)*2 for value in goal))
        route = [];stalled = 0
        for _ in range(round(seconds*30)):
            if self.g.world is not origin:
                assert self.g.world.data['id'] == next_scene
                return
            if self.g.social.active:self.read()
            if self.g.player.position.distance_to(goal) < 1.2:
                if next_scene is None:return
                door = next(d for d in origin.doors
                            if pygame.Vector2(d.data['anchor']).distance_to(goal) < 3)
                direction = (0, -1 if door.data['entry_side'] == 'north' else 1)
                self.tick(direction=direction)
                continue
            if not route or stalled >= 15:
                found = find_path(origin, self.g.player.position, goal,
                                  origin.probe_size, None)
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

    def at(self, key):
        point = pygame.Vector2(self.c.points[key])
        for radius in (0, 8, 16, 24):
            for offset in ((0, radius), (-radius, 0), (radius, 0), (0, -radius)):
                candidate = point+offset
                if self.g.world.can_stand(candidate):
                    self.walk(candidate);self.g.transfer_cooldown = 0
                    return
        raise AssertionError(('No interaction station', key, tuple(point)))

    def read(self):
        identifier = self.g.social.script_identifier;count = 0
        while self.g.social.active and self.g.social.script_identifier == identifier:
            count += 1;assert count < 250, ('Unfinished dialogue', identifier)
            for _ in range(4):self.tick(record=False)
            self.frame(650)
            page = self.g.social.page
            self.seen_pages.append((identifier, self.g.social.page_index, page['speaker']))
            self.seen_contexts.append((identifier, self.c.stage))
            kind = identifier.removeprefix('lantern_') if identifier else ''
            name = kind+'.png'
            if kind in MAIN_SCENES and name not in self.saved_stills:self.save_still(name)
            self.g.social.advance()

    def interact(self, kind):
        self.wait(lambda: self.c._target() == kind)
        assert self.c.interact(), (kind, self.c.stage)
        assert self.g.social.script_identifier == 'lantern_'+kind
        self.read()

    def run(self):
        self.frame(1000)
        self.label = 'Tomas asks Caelan to help at the school'
        self.at('invitation');self.interact('invitation')
        assert self.c.stage == 'invited'
        self.label = 'A special preparation afternoon at the village school'
        door = next(d for d in self.g.town.doors if d.data['id'] == 'school')
        self.walk(door.data['anchor'], 'school')
        self.at('classroom')
        self.interact('classroom');assert self.c.stage == 'classroom'
        self.label = 'Liam has plans for a tower-shaped lantern'
        self.interact('design');assert self.c.stage == 'designed'
        self.interact('permission');assert self.c.stage == 'permitted'
        self.label = 'An agreed outing to Mira with Caelan and Tomas'
        exit_door = next(d for d in self.g.world.doors if d.data['id'] == 'courtyard')
        self.walk(exit_door.data['anchor'], self.g.town.data['id'])
        self.at('workshop')
        self.label = 'Mira takes Liam\u2019s design seriously'
        self.interact('workshop');assert self.c.stage == 'workshop'
        self.interact('test_shape');assert self.c.stage == 'tested'
        self.label = 'Build, try, and adjust the tower frame together'
        self.interact('assemble')
        self.wait(lambda: self.c.action is None and self.c.stage == 'assembled')
        self.save_still('assembled_frame.png')
        self.interact('lift')
        self.wait(lambda: self.c.action is None and self.c.stage == 'lifted')
        self.label = 'Liam has a frame of his own; its purpose is still to come'
        self.interact('frame_ready')
        assert self.c.stage == 'frame_ready'
        assert self.g.quests.status(LANTERN) == 'active'
        assert self.g.quests.states[LANTERN]['completed_objectives'] == ['join_preparations', 'build_frame']
        assert self.g.mill_quest.mill_restored and not self.g.opening_conclusion.mill_stopped
        assert 'CH01_MQ05' not in self.g.quests.definitions
        self.save_still('frame_ready_world.png');self.frame(1600)
        self.g.save_progress()
        saved = json.loads((Path(self.temp.name)/'journey.json').read_text())
        assert saved['lantern_quest']['stage'] == 'frame_ready'
        main_ids = {'lantern_'+kind for kind in MAIN_SCENES}
        actual = {identifier for identifier, _, _ in self.seen_pages}
        assert main_ids <= actual, ('Missing scenes', main_ids-actual)
        for kind in MAIN_SCENES:
            expected = len(self.g.social._make_pages(self.c.lines[kind]))
            observed = sum(identifier == 'lantern_'+kind for identifier, _, _ in self.seen_pages)
            assert observed == expected, ('Missing/repeated pages', kind, observed, expected)
        frames = [];durations = [];travel = 0
        for frame, duration in zip(self.frames, self.durations):
            if duration < 300:
                travel += 1
                if travel % 4 != 1:continue
            frames.append(frame);durations.append(duration)
        # Keep every prose page while making the inline overview small enough
        # for attachment previews. Native UI stills and the transcript preserve
        # reading detail; this animated overview demonstrates the whole route.
        preview_size = None
        for width, colors in ((320, 64), (300, 48), (280, 40), (256, 32)):
            preview_size = (width, round(width*344/480))
            compact = [frame.resize(preview_size, Image.Resampling.NEAREST) for frame in frames]
            save_gif(OUT/'quest.gif', compact, durations, colors)
            if (OUT/'quest.gif').stat().st_size < 1_000_000:break
        if self.craft:save_gif(OUT/'construction.gif', self.craft, self.craft_durations, 96)
        transcript = ['# A Light of His Own \u2014 PR1 dialogue', '',
                      'Captured through the actual game. Only MQ01\u2013MQ03 prerequisites were seeded.', '']
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
            'optional_dialogue': sorted(actual-main_ids), 'overview_frames': len(frames),
            'construction_frames': len(self.craft), 'overview_size': list(preview_size),
            'seeded': 'completed MQ01/MQ02/MQ03 prerequisites and starting player station only',
            'mill_running': True, 'festival_started': False,
            'stills': sorted(self.saved_stills)}, indent=2)+'\n')
        (OUT/'README.md').write_text(
            '# A Light of His Own — PR1 review\n\n'
            'The capture uses the production Game, normal walking and door transitions, '
            'quest dialogue callbacks, companion staging and construction actions. '
            'Only completed MQ01–MQ03 prerequisites and the initial player station are seeded.\n\n'
            '`quest.gif` is a time-compressed overview containing every main dialogue page. '
            'Use the native-resolution PNG stills and `dialogue.md` to read the script. '
            '`construction.gif` shows the real assembly and lifting actions.\n\n'
            'The section ends at `frame_ready`: MQ04 remains active, its first two objectives '
            'are complete, and the lantern is unlit. The repaired mill remains running.\n\n'
            'Reproduce with `python tools/capture_lantern_quest.py`.\n', encoding='utf-8')
        print('Captured MQ04 PR1:', len(frames), 'overview frames;',
              len(self.craft), 'construction frames;', len(self.seen_pages), 'dialogue pages')
        for name in ('quest.gif', 'construction.gif'):
            if (OUT/name).exists():print(name, (OUT/name).stat().st_size, 'bytes')
        self.temp.cleanup();pygame.quit()


def capture():Capture().run()
if __name__ == '__main__':capture()
