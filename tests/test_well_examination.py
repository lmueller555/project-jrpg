"""Reachable, repeatable well inspection without any simulation side effects."""
from copy import deepcopy
from dataclasses import dataclass
from types import SimpleNamespace
import unittest

import pygame

from well_examination import WellExamination


@dataclass(frozen=True)
class Snapshot:
    phase_id: str = 'idle'
    pail_owner: str = 'actor'
    water_units: int = 0


class Dialogue:
    def __init__(self):
        self.locked = False
        self.script_identifier = None
        self.lines = None
        self.accept = True
        self.pointer_cleared = False

    def start_script(self, lines, on_complete=None, identifier=None):
        if self.locked or not self.accept:return False
        self.locked = True
        self.script_identifier = identifier
        self.lines = lines
        if on_complete is not None:raise AssertionError('Inspection supplied a progress callback')
        return True

    def clear_pointer(self):self.pointer_cleared = True

    def close(self):
        self.locked = False
        self.script_identifier = None


class World:
    def __init__(self):
        self.size = (1000, 1200)
        self.blocked = pygame.Mask(self.size)
        self.blocked.draw(pygame.Mask((48, 48), fill=True), (504, 840))
        self.other_feet = []
        self.observation = Snapshot()
        self.well = SimpleNamespace(
            presentation=SimpleNamespace(base={'geometry': {
                'ground_rect_world_logical': [504, 840, 48, 48]}}),
            model=SimpleNamespace(contract={'pail': {'capacity_units': 6}}),
            owner=None, snapshot=lambda:self.observation)

    def can_stand(self, point):
        rect = pygame.Rect(round(point[0])-12, round(point[1])-6, 24, 12)
        return (self.blocked.overlap(pygame.Mask(rect.size, fill=True), rect.topleft) is None
                and not any(rect.colliderect(other) for other in self.other_feet))


class WellExaminationTests(unittest.TestCase):
    def setUp(self):
        self.world = World()
        self.game = SimpleNamespace(
            town=self.world, world=self.world,
            player=SimpleNamespace(position=pygame.Vector2(528, 900),
                                   facing='back', moving=True, running=True),
            social=Dialogue(), on_title=False, game_over=False,
            _music_focused=True, map_open=False,
            quest_ui=SimpleNamespace(journal_open=False), household_action=None,
            transfer_cooldown=0, opening_fade=0,
            opening=SimpleNamespace(stage='done', locks_player=False),
            _mouse_held=True)
        for owner in ('pause', 'inventory_ui', 'services', 'party_ui',
                      'world_map_viewer', 'save_menu', 'status_ui'):
            setattr(self.game, owner, SimpleNamespace(is_open=False))
        for owner in ('combat', 'opening_cinematic', 'mill_gift', 'regent_arrival',
                      'sanctuary_arrival', 'sanctuary_rescue'):
            setattr(self.game, owner, SimpleNamespace(active=False))
        self.inspection = WellExamination(self.game)

    def stand(self, position, facing):
        self.game.player.position.update(position)
        self.game.player.facing = facing

    def test_each_reachable_side_uses_its_actual_facing_and_ground_support(self):
        for point, facing in (((528, 900), 'back'), ((492, 864), 'right'),
                              ((528, 834), 'front'), ((564, 864), 'left')):
            with self.subTest(point=point):
                self.stand(point, facing)
                self.assertTrue(self.world.can_stand(point))
                self.assertEqual(self.inspection.interaction_hint(), 'E: Examine well')
                self.game.player.facing = 'front' if facing != 'front' else 'back'
                self.assertFalse(self.inspection.available())
                self.assertFalse(self.inspection.interact())

    def test_range_is_measured_to_physical_edge_not_canvas_or_center(self):
        self.stand((486, 864), 'right')
        self.assertTrue(self.inspection.available())
        self.stand((485.5, 864), 'right')
        self.assertFalse(self.inspection.available())
        self.stand((492, 834), 'right')
        self.assertTrue(self.inspection.available())
        self.stand((486, 834), 'right')
        self.assertFalse(self.inspection.available())

    def test_solid_or_occupied_feet_and_blocked_approach_reject_inspection(self):
        self.stand((528, 864), 'back')
        self.assertFalse(self.inspection.available())
        self.stand((528, 900), 'back')
        self.world.other_feet.append(pygame.Rect(516, 894, 24, 12))
        self.assertFalse(self.inspection.available())
        self.world.other_feet.clear()
        self.stand((486, 864), 'right')
        self.world.blocked.set_at((500, 864), 1)
        self.assertTrue(self.world.can_stand(self.game.player.position))
        self.assertFalse(self.inspection.available())

    def test_idle_working_and_full_pail_descriptions_follow_authoritative_snapshot(self):
        self.assertEqual(self.inspection.description_key(), 'idle')
        self.world.well.owner = object()
        self.world.observation = Snapshot('lower', 'well', 0)
        self.assertEqual(self.inspection.description_key(), 'working')
        self.world.observation = Snapshot('fill', 'well', 3)
        self.assertEqual(self.inspection.description_key(), 'working')
        self.world.observation = Snapshot('raise', 'well', 6)
        self.assertEqual(self.inspection.description_key(), 'filled')
        self.world.well.owner = None
        self.world.observation = Snapshot('complete', 'actor', 6)
        self.assertEqual(self.inspection.description_key(), 'idle')

    def test_starting_and_repeating_prose_never_changes_the_operation(self):
        self.world.well.owner = object()
        owner = self.world.well.owner
        self.world.observation = Snapshot('raise', 'well', 6)
        before = self.world.observation
        for _ in range(2):
            self.assertTrue(self.inspection.interact())
            self.assertEqual(self.game.social.script_identifier, 'well_examine_filled')
            self.assertIs(self.world.observation, before)
            self.assertIs(self.world.well.owner, owner)
            self.assertFalse(self.game.player.moving)
            self.assertFalse(self.game.player.running)
            self.assertFalse(self.game._mouse_held)
            self.assertTrue(self.game.social.pointer_cleared)
            self.game.social.close()
        self.assertTrue(self.inspection.available())

    def test_existing_dialogue_wins_and_failed_start_does_not_change_input(self):
        self.game.social.locked = True
        self.assertFalse(self.inspection.interact())
        self.assertEqual(self.inspection.interaction_hint(), '')
        self.game.social.locked = False
        self.game.social.accept = False
        self.assertFalse(self.inspection.interact())
        self.assertTrue(self.game.player.moving)
        self.assertTrue(self.game.player.running)
        self.assertTrue(self.game._mouse_held)

    def test_dialogue_cannot_mutate_retained_source_lines(self):
        before = deepcopy(self.inspection.data)
        self.assertTrue(self.inspection.interact())
        self.game.social.lines[0]['text'] = 'Caller mutation'
        self.game.social.close()
        self.assertEqual(self.inspection.data, before)
        self.assertTrue(self.inspection.interact())
        self.assertNotEqual(self.game.social.lines[0]['text'], 'Caller mutation')

    def test_scene_focus_modal_and_story_gates_share_hint_and_action_availability(self):
        for owner in ('pause', 'inventory_ui', 'services', 'party_ui',
                      'world_map_viewer', 'save_menu', 'status_ui'):
            with self.subTest(modal=owner):
                getattr(self.game, owner).is_open = True
                self.assertFalse(self.inspection.available())
                self.assertEqual(self.inspection.interaction_hint(), '')
                self.assertFalse(self.inspection.interact())
                getattr(self.game, owner).is_open = False
        for owner in ('combat', 'opening_cinematic', 'mill_gift', 'regent_arrival',
                      'sanctuary_arrival', 'sanctuary_rescue'):
            with self.subTest(scene=owner):
                getattr(self.game, owner).active = True
                self.assertFalse(self.inspection.available())
                getattr(self.game, owner).active = False
        for name in ('on_title', 'game_over', 'map_open', 'household_action'):
            with self.subTest(flag=name):
                old = getattr(self.game, name)
                setattr(self.game, name, True)
                self.assertFalse(self.inspection.available())
                setattr(self.game, name, old)
        self.game._music_focused = False
        self.assertFalse(self.inspection.available())
        self.game._music_focused = True
        self.game.quest_ui.journal_open = True
        self.assertFalse(self.inspection.available())
        self.game.quest_ui.journal_open = False
        self.game.world = SimpleNamespace()
        self.assertFalse(self.inspection.available())

    def test_menu_gallery_and_playtest_container_are_suppressed_but_playtest_game_is_allowed(self):
        for name, blocked in (('_is_gallery_preview', True), ('on_gallery', True),
                              ('on_quest_playtest', True), ('gallery_session', object()),
                              ('quest_playtest_session', object())):
            with self.subTest(flag=name):
                setattr(self.game, name, blocked)
                self.assertFalse(self.inspection.available())
                setattr(self.game, name, False if isinstance(blocked, bool) else None)
        self.game._is_quest_playtest = True
        self.assertTrue(self.inspection.available())

    def test_transition_and_held_story_arrival_suppress_inspection(self):
        for name in ('transfer_cooldown', 'opening_fade'):
            setattr(self.game, name, .2)
            self.assertFalse(self.inspection.available())
            setattr(self.game, name, 0)
        self.game.regent_arrival.state = 'pending'
        self.assertFalse(self.inspection.available())
        self.game.regent_arrival.state = 'idle'
        self.game.opening.locks_player = True
        self.assertFalse(self.inspection.available())
        self.game.opening.locks_player = False
        self.game.regent_quest = SimpleNamespace(locks_player=True)
        self.assertFalse(self.inspection.available())


if __name__ == '__main__':unittest.main()
