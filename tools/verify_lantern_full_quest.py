"""Verify one continuous, normally played MQ04 journey through all four parts.

Only the completed MQ01--MQ03 prerequisite fixture is seeded. MQ04 starts
available, with no completed objectives, and advances solely through the real
Game's dialogue callbacks, action updates, movement and door transfers. This
driver writes evidence to work/ only; it never regenerates review images.
"""
import os

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

from collections import Counter
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pygame

from main import Game
from tools.capture_lantern_quest import seed_previous_quests
from tools.capture_lantern_village import Capture as VillageCapture


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'work/lantern-full-quest-verification.json'
LANTERN = 'CH01_MQ04'
OBJECTIVES = ('join_preparations', 'build_frame', 'visit_neighbours', 'visit_elira',
              'take_break', 'speak_serene', 'finish_lantern', 'show_mother')
PARTS = (
    ('invitation', 'classroom', 'design', 'permission', 'workshop', 'test_shape',
     'assemble', 'lift', 'frame_ready'),
    ('departure', 'mill_arrival', 'mill_flour', 'venn_arrival', 'venn_preparations',
     'elira_welcome', 'elira_lantern', 'elira_memory', 'elira_company',
     'elira_goodbye', 'reflection'),
    ('break_invitation', 'collect_frame', 'home_welcome', 'snack', 'paper_practice',
     'brothers', 'liam_questions', 'sanctuary_welcome', 'returning_life',
     'remembering', 'sanctuary_close'),
    ('finish_invitation', 'home_return', 'purpose', 'final_panel', 'dry_fit',
     'fasten_covering', 'finished_lantern', 'school_welcome', 'show_mother',
     'homeward', 'put_away', 'farewell'),
)
MAIN_SCENES = tuple(kind for part in PARTS for kind in part)
EXPECTED_DOORS = (
    ('eldenmere.playable', 'school'), ('school', 'eldenmere.playable'),
    ('eldenmere.playable', 'venn'), ('venn', 'eldenmere.playable'),
    ('eldenmere.playable', 'elira'), ('elira', 'eldenmere.playable'),
    ('eldenmere.playable', 'liam_house'), ('liam_house', 'eldenmere.playable'),
    ('eldenmere.playable', 'sanctuary_hall'), ('sanctuary_hall', 'eldenmere.playable'),
    ('eldenmere.playable', 'liam_house'), ('liam_house', 'eldenmere.playable'),
    ('eldenmere.playable', 'school'), ('school', 'eldenmere.playable'),
    ('eldenmere.playable', 'liam_house'),
)


class FullQuestDriver:
    # This helper uses A* only to choose player input directions. It calls
    # Game.update for every step, preserving collisions and actual doors.
    walk = VillageCapture.walk

    def __init__(self):
        self.temp = tempfile.TemporaryDirectory(prefix='lantern-full-quest-')
        self.save_path = Path(self.temp.name)/'journey.json'
        self.settings_path = Path(self.temp.name)/'settings.json'
        self.g = Game(fullscreen=False, start_on_title=False,
                      save_path=self.save_path, settings_path=self.settings_path)
        self.g.audio.set_music(0);self.g.audio.set_effects(0)
        self.c = self.g.lantern_quest
        seed_previous_quests(self.g)
        assert self.g.quests.status(LANTERN) == 'available'
        assert self.c.stage == 'idle'
        assert not self.g.quests.states[LANTERN]['completed_objectives']
        self.tick_index = 0
        self.seen_pages = []
        self.main_order = []
        self.dialogues = []
        self.transitions = []
        self.actor_transfers = []
        self.object_changes = []
        self.progress_changes = []
        self.checkpoints = []
        self.identity_checks = 0
        self.carry_directions = set()
        self.actors = self._actors(self.g)
        self._last_objects = None
        self._last_progress = None
        self.assert_identities()
        self._observe()

    @staticmethod
    def _actors(game):
        c = game.lantern_quest
        actors = (c.liam, c.tomas, c.serene, c.mira, c.mother, c.father,
                  c.halden, c.elira, *c.children.values(), *c.venn_family.values())
        return {a.data['id']: a for a in actors}

    def actor_world(self, actor):
        worlds = [w.data['id'] for w in self.g.scenes.values() if actor in w.npcs]
        assert len(worlds) == 1, ('Actor membership', actor.data['id'], worlds)
        return worlds[0]

    def assert_identities(self):
        for identifier, actor in self.actors.items():
            matches = [a for w in self.g.scenes.values() for a in w.npcs
                       if a.data['id'] == identifier]
            assert len(matches) == 1 and matches[0] is actor, (
                'Replaced or duplicated actor', identifier, len(matches))
            assert self.c._world(actor).data['id'] == self.actor_world(actor)
        self.identity_checks += 1

    def objects(self):
        result = {'frame_location': self.c.rest.frame_location,
                  'paper_location': self.c.rest.paper_location,
                  'elira_lantern': self.g.elira_visit.lantern,
                  'mill_restored': self.g.mill_quest.mill_restored,
                  'mill_stopped': self.g.opening_conclusion.mill_stopped}
        finish = getattr(self.c, 'finish_part', None)
        if finish is not None:
            result['finish'] = {'active': finish.active}
            if finish.active:
                result['finish'].update({name: getattr(finish, name) for name in (
                    'frame_location', 'frame_form', 'lantern_location',
                    'lantern_form', 'finished', 'lit') if hasattr(finish, name)})
                result['finish']['frame_is_lit'] = finish.art['frame_is_lit']
        return result

    def progress(self):
        return {'stage': self.c.stage, 'status': self.g.quests.status(LANTERN),
                'objectives': list(self.g.quests.states[LANTERN]['completed_objectives'])}

    def _observe(self):
        objects = self.objects()
        if objects != self._last_objects:
            self.object_changes.append({'tick': self.tick_index, 'stage': self.c.stage,
                                        'objects': objects})
            self._last_objects = objects
        progress = self.progress()
        count = len(progress['objectives'])
        assert progress['objectives'] == list(OBJECTIVES[:count]), progress
        if self._last_progress is not None:
            assert count >= len(self._last_progress['objectives']), progress
        if progress != self._last_progress:
            self.progress_changes.append({'tick': self.tick_index, **progress})
            self._last_progress = progress

    def tick(self, seconds=1/30, direction=(0, 0), record=True):
        origin = self.g.world.data['id']
        before = {identifier: self.actor_world(actor)
                  for identifier, actor in self.actors.items()}
        self.g.update(seconds, direction, False)
        self.tick_index += 1
        destination = self.g.world.data['id']
        if destination != origin:
            self.transitions.append({'tick': self.tick_index, 'from': origin,
                                     'to': destination, 'stage': self.c.stage})
        for identifier, room in before.items():
            after = self.actor_world(self.actors[identifier])
            if after != room:
                self.actor_transfers.append({'tick': self.tick_index, 'actor': identifier,
                                             'from': room, 'to': after,
                                             'stage': self.c.stage})
        if self.c.rest.frame_location == 'held' and self.c.liam.moving:
            self.carry_directions.add(self.c.liam.facing)
        self._observe()

    def wait(self, predicate, seconds=150):
        for _ in range(round(seconds*30)):
            if predicate():return
            if self.g.social.active:self.read()
            else:self.tick()
        raise AssertionError(('Timeout', self.progress(), self.c.action,
                              self.g.world.data['id'], tuple(self.g.player.position),
                              getattr(self.c, '_ready', None), self.c._target()))

    def at(self, points, key):
        point = pygame.Vector2(points[key])
        for radius in (0, 8, 16, 24, 32):
            for offset in ((0, radius), (-radius, 0), (radius, 0), (0, -radius)):
                candidate = point+offset
                if self.g.world.can_stand(candidate):
                    self.walk(candidate)
                    return
        raise AssertionError(('No interaction station', key, tuple(point)))

    def enter_room(self, door_id, scene_id=None):
        assert self.g.world is self.g.town, ('Enter from town', door_id)
        door = next(d for d in self.g.town.doors if d.data['id'] == door_id)
        self.walk(door.data['anchor'], scene_id or door_id)

    def exit_room(self):
        assert self.g.world is not self.g.town
        door = next(d for d in self.g.world.doors if d.data['id'] == 'courtyard')
        self.walk(door.data['anchor'], self.g.town.data['id'])

    def read(self):
        identifier = self.g.social.script_identifier
        kind = identifier.removeprefix('lantern_') if identifier else ''
        if kind in MAIN_SCENES:
            assert kind not in self.main_order, ('Repeated main scene', kind)
            assert kind == MAIN_SCENES[len(self.main_order)], (
                'Unexpected main scene order', kind, self.main_order)
            self.main_order.append(kind)
        record = {'identifier': identifier, 'world': self.g.world.data['id'],
                  'stage_before': self.c.stage, 'pages': []}
        for _ in range(350):
            if not self.g.social.active or self.g.social.script_identifier != identifier:break
            for _ in range(4):self.tick(record=False)
            page = self.g.social.page
            entry = {'index': self.g.social.page_index, 'speaker': page['speaker'],
                     'lines': list(page.get('lines', [])), 'stage': self.c.stage,
                     'world': self.g.world.data['id']}
            record['pages'].append(entry)
            self.seen_pages.append((identifier, self.g.social.page_index, page['speaker']))
            self.g.social.advance()
            self._observe()
        else:raise AssertionError(('Unfinished dialogue', identifier, self.c.stage))
        record['stage_after'] = self.c.stage
        record['action_after'] = self.c.action
        record['actors'] = {key: {'world': self.actor_world(actor),
                                 'position': list(actor.position)}
                            for key, actor in self.actors.items()}
        self.dialogues.append(record)
        self.assert_identities()

    def interact(self, kind):
        identifier = 'lantern_'+kind
        expected = len(self.g.social._make_pages(self.c.lines[kind]))
        observed = lambda: sum(name == identifier for name, _, _ in self.seen_pages)
        # Main proximity speech can begin while the player walks to a station.
        self.wait(lambda: observed() == expected or self.c._target() == kind)
        if observed() == expected:return
        assert observed() == 0, ('Partially read scene', kind, observed(), expected)
        assert self.c.interact(), (kind, self.c.stage)
        assert self.g.social.script_identifier == identifier
        self.read()
        assert observed() == expected, ('Missing pages', kind, observed(), expected)

    def stage(self, expected):
        self.wait(lambda: self.c.action is None and self.c.stage == expected)

    def checkpoint(self, part, stage, completed):
        self.stage(stage)
        assert self.g.quests.states[LANTERN]['completed_objectives'] == list(OBJECTIVES[:completed])
        assert self.g.mill_quest.mill_restored and not self.g.opening_conclusion.mill_stopped
        assert self.g.elira_visit.lantern == 'table'
        assert 'CH01_MQ05' not in self.g.quests.definitions
        self.assert_identities()
        record = {'part': part, 'tick': self.tick_index, **self.progress(),
                  'world': self.g.world.data['id'], 'objects': self.objects()}
        self.checkpoints.append(record)
        print('Part', part, stage, ':', completed, 'objectives;', len(self.main_order),
              'main scenes', flush=True)

    def opening(self):
        self.at(self.c.points, 'invitation');self.interact('invitation');self.stage('invited')
        self.enter_room('school');self.at(self.c.points, 'classroom')
        for kind, stage in (('classroom', 'classroom'), ('design', 'designed'),
                            ('permission', 'permitted')):
            self.interact(kind);self.stage(stage)
        self.exit_room();self.at(self.c.points, 'workshop')
        for kind, stage in (('workshop', 'workshop'), ('test_shape', 'tested'),
                            ('assemble', 'assembled'), ('lift', 'lifted'),
                            ('frame_ready', 'frame_ready')):
            self.interact(kind);self.stage(stage)
        self.checkpoint(1, 'frame_ready', 2)

    def village(self):
        self.at(self.c.points, 'workshop');self.interact('departure');self.stage('outing')
        self.at(self.c.village_points, 'mill')
        self.interact('mill_arrival');self.interact('mill_flour');self.stage('mill_visited')
        self.enter_room('venn');self.at(self.c.village_points, 'venn')
        self.interact('venn_arrival');self.interact('venn_preparations')
        self.stage('neighbours_visited');self.exit_room()
        self.enter_room('elira');self.at(self.c.village_points, 'elira')
        for kind in PARTS[1][5:10]:self.interact(kind)
        self.stage('elira_farewell');self.exit_room()
        self.at(self.c.village_points, 'reflection');self.interact('reflection')
        self.checkpoint(2, 'elira_visited', 4)

    def rest(self):
        self.at(self.c.village_points, 'reflection');self.interact('break_invitation')
        self.stage('collecting_route');self.at(self.c.rest_points, 'collection')
        self.interact('collect_frame');self.stage('materials_collected')
        assert self.c.rest.frame_location == 'held'
        self.enter_room('liam_house');self.at(self.c.rest_points, 'home')
        self.interact('home_welcome');self.stage('materials_home')
        assert self.c.rest.frame_location == 'home'
        for kind, stage in (('snack', 'rested'), ('paper_practice', 'paper_tried'),
                            ('brothers', 'brothers_spoken'), ('liam_questions', 'home_break_done')):
            self.interact(kind);self.stage(stage)
        self.exit_room();self.enter_room('sanctuary', 'sanctuary_hall')
        self.at(self.c.rest_points, 'sanctuary')
        for kind in PARTS[2][7:]:self.interact(kind)
        self.checkpoint(3, 'serene_heard', 6)

    def finish(self):
        """The final section uses the same public interaction/action route."""
        def perform(kind, stage):
            world, station = self.c.finish_part._where()
            assert world is self.g.world, (kind, world.data['id'], self.g.world.data['id'])
            self.at(self.c.finish_points, station)
            self.interact(kind);self.stage(stage)

        perform('finish_invitation', 'finish_invited')
        self.exit_room();self.enter_room('liam_house')
        for kind, stage in (('home_return', 'home_rejoined'), ('purpose', 'purpose_chosen'),
                            ('final_panel', 'panel_ready'), ('dry_fit', 'fit_ready'),
                            ('fasten_covering', 'covered'), ('finished_lantern', 'lantern_finished')):
            perform(kind, stage)
        assert self.g.quests.states[LANTERN]['completed_objectives'] == list(OBJECTIVES[:7])
        assert self.c.finish_part.frame_location == 'held'
        assert self.c.finish_part.frame_form == 'finished'
        assert self.c.finish_part.art['frame_is_lit'] is False
        assert self.c.finish_part.art['final_covering_attached'] is True
        self.exit_room();self.enter_room('school')
        perform('school_welcome', 'school_met')
        perform('show_mother', 'mother_shown')
        assert self.c.mother in self.c.school.npcs
        assert self.c.mother not in self.c.liam_home.npcs
        assert all(child in self.c.school.npcs for child in self.c.children.values())
        perform('homeward', 'homeward')
        assert self.g.quests.states[LANTERN]['completed_objectives'] == list(OBJECTIVES[:7])
        self.exit_room();self.enter_room('liam_house')
        perform('put_away', 'put_away')
        assert self.c.finish_part.frame_location == 'home'
        assert self.c.finish_part.frame_form == 'finished'
        assert self.g.quests.status(LANTERN) == 'active'
        perform('farewell', 'done')
        self.wait(lambda: self.g.play_routines[0].liam_owner is None)
        self.checkpoint(4, 'done', 8)

    def terminal_reload(self):
        assert self.g.quests.status(LANTERN) == 'completed'
        assert self.g.world is self.c.liam_home
        assert not self.g.social.active and self.c.action is None
        assert self.c.rest.frame_location == 'home'
        assert self.c.finish_part.frame_location == 'home'
        assert self.c.finish_part.frame_form == 'finished'
        assert self.c.finish_part.art['frame_is_lit'] is False
        assert self.actor_world(self.c.liam) == 'liam_house'
        assert self.c.serene.story_following is False
        selected_before = self.selected_village_props()
        visible = self.finished_home_object()
        assert self.g.save_progress()
        saved = json.loads(self.save_path.read_text())
        assert saved['lantern_quest'] == {'version': 1, 'stage': 'done'}
        other = Game(fullscreen=False, start_on_title=True,
                     save_path=self.save_path, settings_path=self.settings_path)
        other.audio.set_music(0);other.audio.set_effects(0)
        assert other.saved_journey is not None, other.save_error
        assert other.begin_journey(True), other.save_error
        self.g = other;self.c = other.lantern_quest;self.actors = self._actors(other)
        selected_immediately_after = self.selected_village_props()
        assert self.c.serene.story_following is False
        assert not other.quests.drain_events(), 'Replay notices during terminal restore'
        for _ in range(300):
            other.update(1/30, (0, 0), False)
            assert not other.social.active, 'Replay dialogue during terminal restore'
            assert not other.quest_ui.notices and other.quest_ui.current_notice is None
        self.assert_identities()
        assert other.quests.status(LANTERN) == 'completed'
        assert self.c.stage == 'done' and self.c.action is None
        assert self.c.rest.frame_location == 'home'
        assert self.c.finish_part.frame_location == 'home'
        assert self.c.finish_part.frame_form == 'finished'
        assert self.c.finish_part.art['frame_is_lit'] is False
        assert self.c._world(self.c.liam) is self.c.liam_home
        assert other.elira_visit.lantern == 'table'
        assert other.mill_quest.mill_restored and not other.opening_conclusion.mill_stopped
        assert other.venn_visit.repaired
        assert 'CH01_MQ05' not in other.quests.definitions
        restored_visible = self.finished_home_object()
        return {'saved_controller': saved['lantern_quest'], 'status': other.quests.status(LANTERN),
                'objectives': list(other.quests.states[LANTERN]['completed_objectives']),
                'world': other.world.data['id'], 'objects': self.objects(),
                'idle_seconds': 10, 'replayed_dialogue': False, 'replayed_notices': False,
                'liam_world': self.c._world(self.c.liam).data['id'],
                'serene_following_before_reload': False,
                'serene_following_after_reload': self.c.serene.story_following,
                'selected_village_props_before_reload': selected_before,
                'selected_village_props_immediately_after_reload': selected_immediately_after,
                'visible_lanterns_before_reload': visible,
                'visible_lanterns_after_reload': restored_visible}

    def selected_village_props(self):
        selected = []
        for prop in self.c.village.surface_props:
            assert self.c.village.surface_prop_visible(prop), prop['id']
            if 'selected' in prop['states']:
                assert prop['surface'] is prop['states']['selected'], (
                    'Village decoration lost its selected state', prop['id'], self.c.stage)
                selected.append(prop['id'])
        assert selected, 'No selected village decorations checked'
        return selected

    def finished_home_object(self):
        # Inspect the same visibility hooks used by World.draw, ensuring the
        # finished object replaces the previous bare home frame.
        visible = []
        for world in self.g.scenes.values():
            for owner, prop in world.routine_props:
                if prop['id'] not in ('home_frame', 'home_lantern'):continue
                if owner.surface_prop_visible(prop):
                    visible.append({'id': prop['id'], 'world': world.data['id'],
                                    'position': list(prop['position'])})
        assert visible == [{'id': 'home_lantern', 'world': 'liam_house',
                            'position': list(next(p['position'] for p in self.c.finish_part.surface_props
                                                  if p['id'] == 'home_lantern'))}], visible
        return visible

    def run(self):
        self.opening();self.village();self.rest();self.finish()
        assert self.main_order == list(MAIN_SCENES)
        assert [(d['from'], d['to']) for d in self.transitions] == list(EXPECTED_DOORS)
        counts = Counter(identifier for identifier, _, _ in self.seen_pages)
        page_counts = {}
        for kind in MAIN_SCENES:
            expected = len(self.g.social._make_pages(self.c.lines[kind]))
            observed = counts['lantern_'+kind]
            assert observed == expected, ('Missing/repeated pages', kind, observed, expected)
            page_counts[kind] = observed
        terminal = self.terminal_reload()
        evidence = {
            'verified': True,
            'fixture': 'Only completed MQ01–MQ03 prerequisites and initial player station; MQ04 available with zero objectives.',
            'mq04_seeded_or_restored_during_playthrough': False,
            'one_continuous_game_until_completed': True,
            'normal_player_movement_and_doors': True,
            'main_scene_count': len(self.main_order), 'main_scene_order': self.main_order,
            'main_dialogue_page_count': sum(page_counts.values()), 'page_counts': page_counts,
            'checkpoints': self.checkpoints, 'progress_changes': self.progress_changes,
            'door_transfers': self.transitions, 'actor_transfers': self.actor_transfers,
            'identity_checks': self.identity_checks, 'object_changes': self.object_changes,
            'carry_directions': sorted(self.carry_directions), 'dialogues': self.dialogues,
            'terminal_reload': terminal,
        }
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(evidence, indent=2)+'\n', encoding='utf-8')
        print('Verified', len(self.main_order), 'main scenes and', sum(page_counts.values()),
              'pages; all 8 objectives completed; terminal reload quiet.', flush=True)
        print(OUT.relative_to(ROOT), flush=True)
        return evidence

    def close(self):
        self.temp.cleanup();pygame.quit()


if __name__ == '__main__':
    driver = FullQuestDriver()
    try:driver.run()
    finally:driver.close()
