"""Review MQ04's finish through real movement, doors and scene callbacks.

Only the shipped serene_heard checkpoint is seeded. No PR4 completion, object
ownership, cast movement or dialogue state is manufactured for this capture.
"""
import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
from pathlib import Path
import json
import shutil
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pygame
from PIL import Image, ImageFont
from main import Game
from tools.capture_lantern_rest import Capture as RestCapture, seed_elira_checkpoint, FIRST_SIX
from tools.capture_mill_quest import save_gif

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'docs/reviews/lantern_finish'
LANTERN = 'CH01_MQ04'
OBJECTIVES = FIRST_SIX + ['finish_lantern', 'show_mother']
MAIN_SCENES = ('finish_invitation', 'home_return', 'purpose', 'final_panel',
               'dry_fit', 'fasten_covering', 'finished_lantern', 'school_welcome',
               'show_mother', 'homeward', 'put_away', 'farewell')


def seed_serene_checkpoint(game):
    """Build only the existing PR3 save contract, not this release's progress."""
    seed_elira_checkpoint(game)
    for objective in FIRST_SIX[4:]:
        assert game.quests.complete_objective(LANTERN, objective)
    game.world = game._scene_by_id('sanctuary_hall')
    game.player.position.update(game.lantern_quest.rest_points['sanctuary'])
    assert game.lantern_quest.restore({'version': 1, 'stage': 'serene_heard'})
    game.opening_fade = 0;game.transfer_cooldown = 0
    game.social.blocked.clear();game.quests.drain_events();game.quest_ui.reset()
    game.camera.reset()
    assert game.quests.states[LANTERN]['completed_objectives'] == FIRST_SIX
    assert game.lantern_quest.stage == 'serene_heard'


class Capture(RestCapture):
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
        self.label = 'A Lantern of His Own'
        self.font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 13)
        seed_serene_checkpoint(self.g)

    def save_still(self, name):
        self.g.draw();pygame.image.save(self.g.ui_surface, OUT/name)
        self.saved_stills.add(name)

    def tick(self, seconds=1/30, direction=(0, 0), record=True):
        origin = self.g.world.data['id']
        actors = (self.c.liam, self.c.tomas, self.c.serene, self.c.mother)
        before = {a: self.c._world(a).data['id'] for a in actors}
        location = self.c.finish_part.frame_location
        action = bool(self.c.action)
        self.g.update(seconds, direction, False);self.tick_index += 1
        destination = self.g.world.data['id']
        if destination != origin:self.transitions.append([origin, destination])
        for actor, room in before.items():
            after = self.c._world(actor).data['id']
            if after != room:self.companion_transfers.append([actor.data['id'], room, after])
        if self.c.finish_part.frame_location != location:
            self.ownership_changes.append([location, self.c.finish_part.frame_location])
        carrying = self.c.finish_part.frame_location == 'held'
        if carrying and self.c.liam.moving:self.carry_directions.add(self.c.liam.facing)
        if record and self.tick_index % 30 == 0:self.frame(120)
        if (action or self.c.action or carrying) and self.tick_index % 4 == 0:
            self.g.draw()
            image = Image.frombytes('RGB', self.g.ui_surface.get_size(),
                                    pygame.image.tobytes(self.g.ui_surface, 'RGB'))
            self.motion.append(image.resize((480, 320), Image.Resampling.NEAREST))
            self.motion_durations.append(130)
        if carrying and self.c.liam.moving:
            name = 'carry_'+self.c.liam.facing+'.png'
            if name not in self.saved_stills:self.save_still(name)

    def at_current(self):
        world, station = self.c.finish_part._where()
        assert world is self.g.world, (self.c.stage, world.data['id'], self.g.world.data['id'])
        point = pygame.Vector2(self.c.finish_points[station])
        for radius in (0, 8, 16, 24, 32):
            for offset in ((0, radius), (-radius, 0), (radius, 0), (0, -radius)):
                candidate = point+offset
                if world.can_stand(candidate):
                    self.walk(candidate);self.g.transfer_cooldown = 0;return
        raise AssertionError(('No interaction station', station, tuple(point)))

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
            if kind == 'show_mother' and page['speaker'] == 'liam_mother':
                if 'mother_detail.png' not in self.saved_stills:self.save_still('mother_detail.png')
            if kind == 'farewell' and page['speaker'] == 'liam_father':
                if 'father_detail.png' not in self.saved_stills:self.save_still('father_detail.png')
            self.g.social.advance()

    def perform(self, kind, stage):
        self.at_current();self.interact(kind)
        self.wait(lambda: self.c.action is None and self.c.stage == stage)

    def run(self):
        self.frame(1000)
        self.label = 'Return from Serene with a personal idea'
        self.perform('finish_invitation', 'finish_invited')
        self.exit_room();self.enter_room('liam_house', 'liam_house')
        self.perform('home_return', 'home_rejoined')
        self.label = 'Liam chooses who his lantern is for'
        self.perform('purpose', 'purpose_chosen')
        self.label = 'Draw the final window and broader stairs'
        self.perform('final_panel', 'panel_ready')
        self.perform('dry_fit', 'fit_ready');self.save_still('dry_fit_world.png')
        self.label = 'Wrap, fasten and inspect one unlit lantern'
        self.perform('fasten_covering', 'covered');self.save_still('covered_world.png')
        self.perform('finished_lantern', 'lantern_finished')
        assert self.c.finish_part.frame_location == 'held'
        assert self.g.quests.states[LANTERN]['completed_objectives'] == OBJECTIVES[:7]
        self.label = 'Carry the finished lantern to the actual school'
        self.exit_room();self.enter_room('school', 'school')
        self.perform('school_welcome', 'school_met')
        self.perform('show_mother', 'mother_shown');self.save_still('school_world.png')
        assert self.c.mother in self.c.school.npcs and self.c.mother not in self.c.liam_home.npcs
        assert self.g.quests.status(LANTERN) == 'active'
        self.label = 'Mother stays with the class; the lantern goes home'
        self.perform('homeward', 'homeward')
        self.exit_room();self.enter_room('liam_house', 'liam_house')
        self.perform('put_away', 'put_away');self.save_still('stored_world.png')
        assert self.g.quests.status(LANTERN) == 'active'
        self.label = 'A quiet farewell completes the afternoon'
        self.perform('farewell', 'done')
        self.wait(lambda: self.g.play_routines[0].liam_owner is None)
        self.save_still('endpoint_world.png');self.frame(1800)
        assert self.g.quests.status(LANTERN) == 'completed'
        assert self.g.quests.states[LANTERN]['completed_objectives'] == OBJECTIVES
        assert self.c.finish_part.frame_location == 'home'
        assert self.carry_directions == {'front', 'back', 'left', 'right'}
        assert self.g.mill_quest.mill_restored and not self.g.opening_conclusion.mill_stopped
        assert self.g.venn_visit.repaired and self.g.elira_visit.lantern == 'table'
        for prop in self.c.village.surface_props:
            assert self.c.village.surface_prop_visible(prop)
            if 'selected' in prop['states']:assert prop['surface'] is prop['states']['selected']
        assert not self.c.finish_part.art['frame_is_lit']
        assert self.c.finish_part.frame_form == 'finished'
        assert 'CH01_MQ05' not in self.g.quests.definitions
        self.g.save_progress()
        saved = json.loads((Path(self.temp.name)/'journey.json').read_text())
        assert saved['lantern_quest'] == {'version': 1, 'stage': 'done'}
        main_ids = {'lantern_'+kind for kind in MAIN_SCENES}
        actual = {identifier for identifier, _, _ in self.seen_pages}
        assert main_ids <= actual
        for kind in MAIN_SCENES:
            expected = len(self.g.social._make_pages(self.c.lines[kind]))
            observed = sum(identifier == 'lantern_'+kind for identifier, _, _ in self.seen_pages)
            assert observed == expected, ('Missing/repeated pages', kind, observed, expected)
        expected_doors = [('sanctuary_hall', 'eldenmere.playable'),
                          ('eldenmere.playable', 'liam_house'),
                          ('liam_house', 'eldenmere.playable'),
                          ('eldenmere.playable', 'school'),
                          ('school', 'eldenmere.playable'),
                          ('eldenmere.playable', 'liam_house')]
        assert self.transitions == [list(pair) for pair in expected_doors], self.transitions
        for origin, destination in set(expected_doors):
            count = expected_doors.count((origin, destination))
            for identifier in ('liam', 'tomas'):
                assert self.companion_transfers.count([identifier, origin, destination]) == count
        assert self.ownership_changes == [['home', 'held'], ['held', 'home']]
        self.write_artifacts(saved, actual-main_ids)
        self.temp.cleanup();pygame.quit()

    def write_artifacts(self, saved, optional):
        frames = [];durations = [];travel = 0
        for frame, duration in zip(self.frames, self.durations):
            if duration < 300:
                travel += 1
                if travel % 4 != 1:continue
            frames.append(frame);durations.append(duration)
        for width, colors in ((320, 64), (300, 48), (280, 40), (256, 32), (240, 24)):
            size = (width, round(width*344/480))
            compact = [frame.resize(size, Image.Resampling.NEAREST) for frame in frames]
            save_gif(OUT/'quest.gif', compact, durations, colors)
            if (OUT/'quest.gif').stat().st_size < 1_000_000:break
        assert (OUT/'quest.gif').stat().st_size < 1_000_000
        if self.motion:
            count = max(1, len(self.motion)//100)
            motion = self.motion[::count];times = self.motion_durations[::count]
            for width, colors in ((320, 64), (280, 48), (240, 40)):
                motion_size = (width, round(width*320/480))
                images = [f.resize(motion_size, Image.Resampling.NEAREST) for f in motion]
                save_gif(OUT/'motion.gif', images, times, colors)
                if (OUT/'motion.gif').stat().st_size < 1_000_000:break
            assert (OUT/'motion.gif').stat().st_size < 1_000_000
        board = ROOT/'work/lantern-finish-art/pose_board.png'
        if board.exists():shutil.copyfile(board, OUT/'pose_board.png')
        transcript = ['# A Lantern of His Own — dialogue', '',
                      'Captured through the production game from the shipped PR3 endpoint.', '']
        for kind in MAIN_SCENES:
            transcript += ['## '+kind.replace('_', ' ').title(), '']
            for line in self.c.lines[kind]:
                name = self.g.social.data['speakers'][line['speaker']]['name']
                transcript += ['**'+name+':** '+line['text'], '']
        (OUT/'dialogue.md').write_text('\n'.join(transcript), encoding='utf-8')
        (OUT/'capture.json').write_text(json.dumps({
            'quest_id': LANTERN, 'stage': self.c.stage, 'quest_completed': True,
            'completed_objectives': saved['quests']['quests'][LANTERN]['completed_objectives'],
            'dialogue_pages': len(self.seen_pages), 'main_scenes': list(MAIN_SCENES),
            'optional_dialogue': sorted(optional), 'overview_frames': len(frames),
            'overview_size': list(size), 'actual_door_transitions': self.transitions,
            'companion_door_transitions': self.companion_transfers,
            'frame_ownership_changes': self.ownership_changes,
            'observed_carry_directions': sorted(self.carry_directions),
            'seeded': 'completed MQ01–MQ03 and shipped MQ04 PR3 serene_heard checkpoint only',
            'mill_running': True, 'festival_started': False, 'frame_location': 'home',
            'frame_form': self.c.finish_part.frame_form, 'frame_is_lit': False,
            'mother_location': self.c._world(self.c.mother).data['id'],
            'other_children_at_school': len(self.c.children),
            'elira_lantern': 'table', 'stills': sorted(self.saved_stills)}, indent=2)+'\n')
        (OUT/'README.md').write_text(
            '# A Lantern of His Own — review\n\n'
            'The capture uses the production Game, normal walking, real sanctuary, home '
            'and school doors, all twelve final dialogue callbacks, and all material '
            'actions. Only the shipped PR3 endpoint and earlier quests are seeded.\n\n'
            '`quest.gif` includes every main dialogue page in a time-compressed overview '
            'under 1 MB. `motion.gif` shows real material work and covered-lantern carrying. '
            'Native PNG stills and `dialogue.md` provide readable dialogue; `pose_board.png` '
            'shows the sprite poses at pixel scale.\n\n'
            'At `done`, all eight MQ04 objectives are complete. The single finished lantern '
            'is stored unlit at home, Mother is still teaching at school, and the afternoon '
            'and prior village repairs persist. The festival has not started.\n\n'
            'Reproduce with `python tools/capture_lantern_finish.py`.\n', encoding='utf-8')
        print('Captured MQ04 finish:', len(frames), 'overview frames;', len(self.seen_pages), 'dialogue pages')
        for name in ('quest.gif', 'motion.gif'):
            if (OUT/name).exists():print(name, (OUT/name).stat().st_size, 'bytes')


def capture():Capture().run()
if __name__ == '__main__':capture()
