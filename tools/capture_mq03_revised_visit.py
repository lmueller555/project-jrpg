"""Historical pre-emergency MQ03 capture helpers.

The retained Capture class documents the earlier completed visit. Command-line
use now delegates to the current Sanctuary emergency review, defaulting to
`docs/reviews/mq03_emergency`; it never overwrites the archived visit folder.
"""
from __future__ import annotations
import argparse
import json
import math
import os
from pathlib import Path
import sys

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'tests'), str(ROOT/'tools')]

import pygame
from PIL import Image
from test_opening_dialogue_pass import OpeningDialogueDriver
from capture_mq02_spellblade import Video
from quests import MILL_QUEST, REGENT_QUEST, LANTERN_QUEST

MAIN_SCENES = ('preparations', 'arrival', 'welcome', 'discussion', 'aftermath')


class Capture:
    def __init__(self, output=ROOT/'docs/reviews/mq03_revised_visit'):
        self.output = Path(output);self.output.mkdir(parents=True, exist_ok=True)
        self.driver = OpeningDialogueDriver(on_page=self.page)
        self.game = self.driver.g
        self.video = Video(self.output/'revised_visit.mp4')
        self.recording = False;self.frame_budget = 0.;self.stills = []
        self.visited_stages = [];self.dialogue_rooms = {};self.sources = {}
        self.scene_pages = {};self.route_rooms = [];self.venn_stations = set()
        original_tick = self.driver.tick

        def tick(seconds=.05, direction=(0, 0)):
            original_tick(seconds, direction)
            if not self.recording:return
            game, quest = self.game, self.game.regent_quest
            if not self.visited_stages or self.visited_stages[-1] != quest.stage:
                self.visited_stages.append(quest.stage)
            if not self.route_rooms or self.route_rooms[-1] != game.world.data['id']:
                self.route_rooms.append(game.world.data['id'])
            venn = game.venn_visit.family['father']
            room = next(world.data['id'] for world in game.scenes.values() if venn in world.npcs)
            self.venn_stations.add((room, tuple(venn.position)))
            self.frame_budget += seconds
            if self.frame_budget >= .05-1e-8:
                frame = self.image()
                while self.frame_budget >= .05-1e-8:
                    self.video.frame(frame);self.frame_budget -= .05
            if quest.stage == 'escorting' and game.world is quest.hall:
                self.still('direct_escort_hall.png')
        self.driver.tick = tick
        original_key = self.driver.key

        def paced_key(value=pygame.K_e):
            social = self.game.social
            if (self.recording and value == pygame.K_SPACE and social.active
                    and str(social.script_identifier).startswith('regent_')):
                text = ' '.join(social.page['lines'])
                duration = max(1.5, len(text.split())/3.5)
                for _ in range(math.ceil(duration/.05)):self.driver.tick(.05)
            original_key(value)
        self.driver.key = paced_key

    def image(self):
        self.game.draw()
        return Image.frombytes('RGB', self.game.ui_surface.get_size(),
                               pygame.image.tobytes(self.game.ui_surface, 'RGB'))

    def still(self, name):
        if name in self.stills:return
        self.image().save(self.output/name);self.stills.append(name)

    def page(self, driver, identifier, page):
        if not self.recording or not str(identifier).startswith('regent_'):return
        quest = self.game.regent_quest
        if identifier == 'regent_welcome' and page['source_line'] == 0:
            # Let the actual approach/sit transition settle before its review
            # still; the movie retains the real motion and reading pause.
            for _ in range(14):self.driver.tick(.05)
        self.sources.setdefault(identifier, [dict(line) for line in self.game.social._source_lines])
        self.dialogue_rooms.setdefault(identifier, set()).add(self.game.world.data['id'])
        self.scene_pages[identifier] = self.scene_pages.get(identifier, 0)+1
        text = self.game.social._source_lines[page['source_line']]['text']
        if identifier == 'regent_preparations':self.still('serene_invitation.png')
        if identifier == 'regent_arrival':
            self.still('meet_visitors.png')
            if page['speaker'] == 'lucan':self.still('lucan_introduction.png')
            if 'birthday present' in text:self.still('miras_blade.png')
        if identifier == 'regent_welcome':
            self.still('sanctuary_meal.png')
            if page['speaker'] == 'regent_driver':self.still('tomas_wagon_question.png')
            if page['speaker'] == 'lucan':self.still('lucan_at_meal.png')
        if identifier == 'regent_discussion':
            self.still('ridge_discussion.png')
            if 'monarch' in text:self.still('royal_background.png')
            if 'Aether gathers' in text:self.still('grove_and_confluence.png')
            if 'cannot endorse' in text:self.still('surface_inspection_only.png')
        if identifier == 'regent_aftermath':self.still('personal_aftermath.png')
        assert not self.game.social.choosing
        if identifier in {'regent_'+key for key in MAIN_SCENES}:
            assert self.game.world is (self.game.town if identifier == 'regent_arrival' else quest.dining)

    def walk_station(self, key):
        quest = self.game.regent_quest
        self.driver.travel(quest.world_for_station(key).data['id'])
        point = pygame.Vector2(quest.points[key])
        for radius in (0, 8, 16, 24, 32):
            for offset in ((0, radius), (-radius, 0), (radius, 0), (0, -radius)):
                candidate = point+offset
                if self.game.world.can_stand(candidate):
                    self.driver.walk(candidate);self.game.transfer_cooldown = 0
                    return
        raise AssertionError(('No clear station', key))

    def interact(self, kind):
        quest = self.game.regent_quest
        self.game.social.blocked.clear()
        if not self.game.social.active:assert quest.interact(), (kind, quest.stage)
        assert self.game.social.script_identifier == 'regent_'+kind
        self.driver.read()

    def arrival(self):
        self.driver.run()
        assert self.game.quests.status(MILL_QUEST) == 'completed'
        assert self.game.regent_arrival.state == 'pending'
        origin = tuple(self.game.player.position)
        for _ in range(2400):
            self.driver.tick(.05)
            scene = self.game.regent_arrival
            if scene.shot == 'gate_greeting' and scene.phase_time >= .5:
                self.still('lucan_arrival_continuity.png')
                assert any(actor['id'] == 'lucan' for actor in scene.phase['actors'])
                break
            if scene.dialogue is not None:self.driver.key(pygame.K_SPACE)
        else:raise AssertionError('The arrival never reached its gate greeting')
        self.game.draw();self.driver.click(self.game.regent_arrival.skip_rect.center)
        assert self.game.regent_arrival.state == 'seen'
        assert tuple(self.game.player.position) == origin
        assert self.game.world.data['id'] == 'sanctuary_dining'
        assert self.game.quests.status(REGENT_QUEST) == 'available'

    def run(self):
        try:
            self.arrival()
            self.recording = True
            quest = self.game.regent_quest
            self.game.quest_ui.reset()
            self.driver.actor(quest.serene, 'regent_preparations')
            assert quest.stage == 'assigned'
            self.driver.travel(self.game.town.data['id'])
            self.driver.actor(quest.aldric, 'regent_arrival')
            assert quest.stage == 'escorting'
            self.walk_station('courtyard')
            self.driver.until(lambda: quest.stage == 'welcome' and quest._group_ready)
            self.interact('welcome');assert quest.stage == 'hosted'
            self.driver.until(lambda: quest._group_ready)
            self.interact('discussion');assert quest.stage == 'discussion'
            self.driver.until(lambda: quest._aside_ready)
            self.walk_station('aftermath');self.interact('aftermath')
            assert quest.stage == 'done'
            self.driver.tick(.5)
            self.still('mq03_complete.png')
            self.video.close()
            assert self.game.quests.status(REGENT_QUEST) == 'completed'
            assert self.game.quests.status(LANTERN_QUEST) == 'available'
            assert self.game.inventory.quantity('caelan_gearblade') == 1
            assert quest.lucan in quest.party
            assert not any('AUTHORIZ' in flag.upper() or 'EXCAVATION_STARTED' in flag.upper()
                           for flag in self.game.social.flags)
            expected = {'regent_'+key for key in MAIN_SCENES}
            assert expected <= set(self.sources)
            assert not any('dispute' in key for key in self.sources)
            assert all(quest._world(actor) is quest.dining for actor in quest.party)
            for key in MAIN_SCENES:
                assert self.scene_pages['regent_'+key] == len(self.game.social._make_pages(quest.lines[key]))
            names = ['lucan_introduction.png', 'sanctuary_meal.png', 'grove_and_confluence.png',
                     'royal_background.png', 'personal_aftermath.png', 'mq03_complete.png']
            contact = Image.new('RGB', (1440, 640))
            for index, name in enumerate(names):
                with Image.open(self.output/name) as frame:
                    contact.paste(frame.convert('RGB').resize((480, 320), Image.Resampling.NEAREST),
                                  (index%3*480, index//3*320))
            contact.save(self.output/'scene_contact.png')
            report = {'unseeded_new_game': True, 'normal_player_files_untouched': True,
                'movie': {'file': 'revised_visit.mp4', 'fps': 20, 'frames': self.video.frames,
                          'seconds': self.video.frames/20}, 'quest': quest.to_dict(),
                'objectives': self.game.quests.states[REGENT_QUEST]['completed_objectives'],
                'main_dialogue_pages': {key: count for key, count in self.scene_pages.items() if key in expected},
                'optional_dialogue_pages': {key: count for key, count in self.scene_pages.items() if key not in expected},
                'dialogue': self.sources,
                'dialogue_rooms': {key: sorted(rooms) for key, rooms in self.dialogue_rooms.items()},
                'observed_stages': self.visited_stages, 'route_rooms': self.route_rooms,
                'one_gift': self.game.inventory.quantity('caelan_gearblade'),
                'party': [actor.data['id'] for actor in quest.party],
                'party_rooms': [quest._world(actor).data['id'] for actor in quest.party],
                'one_lucan': sum(quest.lucan in room.npcs for room in self.game.scenes.values()) == 1,
                'one_serene': sum(quest.serene in room.npcs for room in self.game.scenes.values()) == 1,
                'one_tomas': sum(quest.tomas in room.npcs for room in self.game.scenes.values()) == 1,
                'venn_stations_during_visit': sorted(self.venn_stations),
                'no_cart_props': not any(p['id'] == 'venn_cart' for p in quest.surface_props),
                'mq04_available': self.game.quests.status(LANTERN_QUEST) == 'available',
                'saved_journey_valid': self.game._read_saved_journey() is not None,
                'stills': self.stills}
            (self.output/'verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
            (self.output/'README.md').write_text(
                '# MQ03 — The revised Regent’s Road\n\n'
                '[Watch the complete visit](revised_visit.mp4)\n\n'
                '![Actual gameplay contact sheet](scene_contact.png)\n\n'
                'Recorded from a disposable, unseeded New Game through MQ01 and the revised '
                'MQ02 gift, boar encounter, water repair and sanctuary ending. The arrival is '
                'advanced to its gate greeting to verify Lucan is traveling with Aldric; Skip '
                'then returns to the same sanctuary position. The movie records the separate '
                'MQ03 invitation, Lucan’s introduction, normal door navigation directly back '
                'to the sanctuary, the meal, ridge discussion and private aftermath.\n\n'
                f'The silent movie is 960×640 at 20 fps, {self.video.frames/20:.2f} seconds long. '
                'Every main dialogue page is retained with reading time. No quest, equipment, '
                'resource or actor position is seeded, and no player save/settings file is included.\n\n'
                '[Verification metadata](verification.json) records the five scenes, actual '
                'room transfers, Lucan’s presence, completed objectives, absence of cart props, '
                'valid final save and MQ04 availability. Reproduce with '
                '`python tools/capture_mq03_revised_visit.py`.\n')
            print(json.dumps({'output': str(self.output), 'bytes': self.video.path.stat().st_size,
                              'seconds': self.video.frames/20, 'stills': len(self.stills),
                              'valid': report['saved_journey_valid']}))
        finally:
            self.video.close();self.driver.close()


def main(argv=None):
    from tools.capture_mq03_emergency import OUT, main as current_main

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', '--out', dest='output', type=Path, default=OUT)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--no-movie', action='store_true')
    args = parser.parse_args(argv)
    archive = ROOT/'docs/reviews/mq03_revised_visit'
    if args.output.resolve() == archive.resolve():
        parser.error('The revised-visit folder is a historical archive; choose another output folder.')
    forwarded = ['--out', str(args.output)]
    if args.check:forwarded.append('--check')
    if args.no_movie:forwarded.append('--no-movie')
    return current_main(forwarded)


if __name__ == '__main__':main()
