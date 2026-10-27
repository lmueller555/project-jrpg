"""Capture the home break and Serene visit through the production Game.

Only the already-shipped elira_visited checkpoint and prior quests are seeded.
Every new scene, material handoff and objective uses normal game callbacks.
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
from tools.capture_lantern_village import Capture as VillageCapture, seed_frame_checkpoint
from tools.capture_mill_quest import save_gif

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'docs/reviews/lantern_rest'
LANTERN = 'CH01_MQ04'
FIRST_SIX = ['join_preparations', 'build_frame', 'visit_neighbours', 'visit_elira',
             'take_break', 'speak_serene']
MAIN_SCENES = ('break_invitation', 'collect_frame', 'home_welcome', 'snack',
               'paper_practice', 'brothers', 'liam_questions', 'sanctuary_welcome',
               'returning_life', 'remembering', 'sanctuary_close')


def seed_elira_checkpoint(game):
    """Seed only the shipped PR2 result, never this section's new progress."""
    seed_frame_checkpoint(game)
    for objective in FIRST_SIX[2:4]:
        assert game.quests.complete_objective(LANTERN, objective)
    game.world = game.town
    game.player.position.update(game.lantern_quest.village_points['reflection'])
    assert game.lantern_quest.restore({'version': 1, 'stage': 'elira_visited'})
    game.opening_fade = 0;game.transfer_cooldown = 0
    game.social.blocked.clear();game.quests.drain_events();game.quest_ui.reset()
    game.camera.reset()
    assert game.quests.states[LANTERN]['completed_objectives'] == FIRST_SIX[:4]


class Capture:
    wait = VillageCapture.wait
    frame = VillageCapture.frame
    walk = VillageCapture.walk

    def __init__(self):
        OUT.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory()
        self.g = Game(fullscreen=False, start_on_title=False,
                      save_path=Path(self.temp.name)/'journey.json',
                      settings_path=Path(self.temp.name)/'settings.json')
        self.g.audio.set_music(0);self.g.audio.set_effects(0)
        self.c = self.g.lantern_quest
        self.frames = [];self.durations = [];self.motion = [];self.motion_durations = []
        self.saved_stills = set();self.seen_pages = [];self.seen_contexts = []
        self.transitions = [];self.companion_transfers = [];self.ownership_changes = []
        self.carry_directions = set();self.tick_index = 0
        self.label = 'Questions After the Noise'
        self.font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 13)
        seed_elira_checkpoint(self.g)

    def save_still(self, name):
        self.g.draw();pygame.image.save(self.g.ui_surface, OUT/name)
        self.saved_stills.add(name)

    def tick(self, seconds=1/30, direction=(0, 0), record=True):
        origin = self.g.world.data['id']
        actors = (self.c.liam, self.c.tomas, self.c.serene)
        before = {a: self.c._world(a).data['id'] for a in actors}
        location = self.c.rest.frame_location
        action = bool(self.c.action)
        self.g.update(seconds, direction, False);self.tick_index += 1
        destination = self.g.world.data['id']
        if destination != origin:self.transitions.append([origin, destination])
        for actor, room in before.items():
            after = self.c._world(actor).data['id']
            if after != room:self.companion_transfers.append([actor.data['id'], room, after])
        if self.c.rest.frame_location != location:
            self.ownership_changes.append([location, self.c.rest.frame_location])
        carrying = self.c.rest.frame_location == 'held'
        if carrying and self.c.liam.moving:self.carry_directions.add(self.c.liam.facing)
        if record and self.tick_index % 30 == 0:self.frame(120)
        if (action or self.c.action or carrying) and self.tick_index % 4 == 0:
            self.g.draw()
            image = Image.frombytes('RGB', self.g.ui_surface.get_size(),
                                    pygame.image.tobytes(self.g.ui_surface, 'RGB'))
            self.motion.append(image.resize((480, 320), Image.Resampling.NEAREST))
            self.motion_durations.append(130)
        if carrying and self.c.liam.moving and 'carrying.png' not in self.saved_stills:
            self.save_still('carrying.png')
        if self.c.stage == 'paper_tried' and 'practice_world.png' not in self.saved_stills:
            self.save_still('practice_world.png')

    def at(self, key):
        desired = self.c.village_points['reflection'] if key == 'break_invitation' else self.c.rest_points[key]
        point = pygame.Vector2(desired)
        for radius in (0, 8, 16, 24, 32):
            for offset in ((0, radius), (-radius, 0), (radius, 0), (0, -radius)):
                candidate = point+offset
                if self.g.world.can_stand(candidate):
                    self.walk(candidate);self.g.transfer_cooldown = 0;return
        raise AssertionError(('No interaction station', key, tuple(point)))

    def enter_room(self, door_id, scene_id):
        door = next(d for d in self.g.town.doors if d.data['id'] == door_id)
        self.walk(door.data['anchor'], scene_id)

    def exit_room(self):
        door = next(d for d in self.g.world.doors if d.data['id'] == 'courtyard')
        self.walk(door.data['anchor'], self.g.town.data['id'])

    def read(self):
        identifier = self.g.social.script_identifier;count = 0
        while self.g.social.active and self.g.social.script_identifier == identifier:
            count += 1;assert count < 350, ('Unfinished dialogue', identifier)
            for _ in range(4):self.tick(record=False)
            self.frame(650)
            page = self.g.social.page
            self.seen_pages.append((identifier, self.g.social.page_index, page['speaker']))
            self.seen_contexts.append((identifier, self.c.stage))
            kind = identifier.removeprefix('lantern_') if identifier else ''
            name = kind+'.png'
            if kind in MAIN_SCENES and name not in self.saved_stills:self.save_still(name)
            text = ' '.join(page.get('lines', []))
            if kind == 'brothers' and 'brothers_background.png' not in self.saved_stills:
                self.save_still('brothers_background.png')
            if kind == 'returning_life' and ('believe' in text or 'returns' in text):
                self.save_still('serene_belief.png')
            if kind == 'remembering' and ('miss' in text or 'bread' in text):
                self.save_still('serene_remembrance.png')
            self.g.social.advance()

    def interact(self, kind):
        identifier = 'lantern_'+kind
        expected = len(self.g.social._make_pages(self.c.lines[kind]))
        if sum(name == identifier for name, _, _ in self.seen_pages) == expected:
            # Ordinary proximity speech can start while Caelan approaches.
            # The walk reader already followed its real completion callback.
            return
        self.wait(lambda: self.c._target() == kind)
        for actor in (self.c.liam, self.c.tomas):
            assert actor in self.g.world.npcs, ('Missing companion', kind, actor.data['id'])
            assert actor.position.distance_to(self.g.player.position) < 160
        assert self.c.interact(), (kind, self.c.stage)
        assert self.g.social.script_identifier == identifier
        self.read()

    def run(self):
        self.frame(1000)
        self.label = 'A pause after visiting Elira'
        self.at('break_invitation');self.interact('break_invitation')
        assert self.c.stage == 'collecting_route'
        self.label = 'Collect the frame and drawing from Mira'
        self.at('collection');self.interact('collect_frame')
        self.wait(lambda: self.c.action is None and self.c.stage == 'materials_collected')
        assert self.c.rest.frame_location == 'held'
        self.save_still('materials_collected.png')
        self.label = 'Liam carries his frame home'
        self.enter_room('liam_house', 'liam_house');self.at('home')
        self.interact('home_welcome')
        self.wait(lambda: self.c.action is None and self.c.stage == 'materials_home')
        assert self.c.rest.frame_location == 'home'
        self.save_still('materials_home.png')
        self.label = 'An ordinary family break'
        self.interact('snack');assert self.c.stage == 'rested'
        self.label = 'Try the stairs on a loose paper panel'
        self.interact('paper_practice')
        self.wait(lambda: self.c.action is None and self.c.stage == 'paper_tried')
        self.interact('brothers');assert self.c.stage == 'brothers_spoken'
        self.interact('liam_questions');assert self.c.stage == 'home_break_done'
        self.save_still('home_world.png')
        assert self.g.quests.states[LANTERN]['completed_objectives'] == FIRST_SIX[:5]
        self.label = 'Bring Liam’s questions to Serene'
        self.exit_room();self.enter_room('sanctuary', 'sanctuary_hall');self.at('sanctuary')
        for kind in ('sanctuary_welcome', 'returning_life', 'remembering', 'sanctuary_close'):
            self.interact(kind)
        assert self.c.stage == 'serene_heard'
        assert self.g.quests.status(LANTERN) == 'active'
        assert self.g.quests.states[LANTERN]['completed_objectives'] == FIRST_SIX
        assert self.c.rest.frame_location == 'home'
        assert self.g.mill_quest.mill_restored and not self.g.opening_conclusion.mill_stopped
        assert self.g.elira_visit.lantern == 'table'
        assert 'CH01_MQ05' not in self.g.quests.definitions
        self.save_still('endpoint_world.png');self.frame(1600)
        self.g.save_progress()
        saved = json.loads((Path(self.temp.name)/'journey.json').read_text())
        assert saved['lantern_quest'] == {'version': 1, 'stage': 'serene_heard'}
        main_ids = {'lantern_'+kind for kind in MAIN_SCENES}
        actual = {identifier for identifier, _, _ in self.seen_pages}
        assert main_ids <= actual
        for kind in MAIN_SCENES:
            expected = len(self.g.social._make_pages(self.c.lines[kind]))
            observed = sum(identifier == 'lantern_'+kind for identifier, _, _ in self.seen_pages)
            assert observed == expected, ('Missing/repeated pages', kind, observed, expected)
        for origin, destination in (('eldenmere.playable', 'liam_house'),
                                    ('liam_house', 'eldenmere.playable'),
                                    ('eldenmere.playable', 'sanctuary_hall')):
            assert self.transitions.count([origin, destination]) == 1
            for identifier in ('liam', 'tomas'):
                assert self.companion_transfers.count([identifier, origin, destination]) == 1
        assert ['workshop', 'held'] in self.ownership_changes
        assert ['held', 'home'] in self.ownership_changes
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
        if self.motion:
            count = max(1, len(self.motion)//100)
            motion = self.motion[::count];times = self.motion_durations[::count]
            for width, colors in ((320, 64), (280, 48), (240, 40)):
                motion_size = (width, round(width*320/480))
                images = [f.resize(motion_size, Image.Resampling.NEAREST) for f in motion]
                save_gif(OUT/'motion.gif', images, times, colors)
                if (OUT/'motion.gif').stat().st_size < 1_000_000:break
        transcript = ['# Questions After the Noise — dialogue', '',
                      'Captured through the production game from the shipped PR2 endpoint.', '']
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
            'frame_ownership_changes': self.ownership_changes,
            'observed_carry_directions': sorted(self.carry_directions),
            'seeded': 'completed MQ01–MQ03 and shipped MQ04 PR2 elira_visited checkpoint only',
            'mill_running': True, 'festival_started': False, 'frame_location': 'home',
            'elira_lantern': 'table', 'stills': sorted(self.saved_stills)}, indent=2)+'\n')
        (OUT/'README.md').write_text(
            '# Questions After the Noise — review\n\n'
            'The capture uses the production Game, normal walking, real home and sanctuary '
            'doors, material handoffs and all eleven new dialogue callbacks. Only the shipped '
            'PR2 endpoint and earlier quests are seeded.\n\n'
            '`quest.gif` contains every main dialogue page in a time-compressed overview. '
            '`motion.gif` shows actual carrying and material actions. Use the native PNG '
            'stills and `dialogue.md` for readable review.\n\n'
            'The endpoint is `serene_heard`: MQ04 remains active with its first six '
            'objectives complete. The single frame, drawing and practice paper stay at home; '
            'the final covering and purpose remain for PR4.\n\n'
            'Reproduce with `python tools/capture_lantern_rest.py`.\n', encoding='utf-8')
        print('Captured MQ04 rest:', len(frames), 'overview frames;', len(self.seen_pages), 'dialogue pages')
        for name in ('quest.gif', 'motion.gif'):
            if (OUT/name).exists():print(name, (OUT/name).stat().st_size, 'bytes')


def capture():Capture().run()
if __name__ == '__main__':capture()
