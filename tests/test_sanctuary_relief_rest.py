"""Confirmed visitor care shares the bed transaction and preserves progression."""
from copy import deepcopy
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, PropertyMock, patch

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import pygame

from main import Game
from sanctuary_relief import SCENE_ID, SanctuaryRelief


ROOT = Path(__file__).resolve().parents[1]


class ReliefWorld:
    """Small physical fixture; the map suite checks real doors and wall paths."""
    def __init__(self):
        self.data = {'id': SCENE_ID, 'relief_room': {
            'attendant': {'position': [252, 174], 'facing': 'front', 'variant': 'female_01'}}}
        self.size = (336, 288)
        self.blocked = pygame.Mask(self.size)
        self.npcs = []
        self.entities = [{'id': 'visitor_bed', 'rect': pygame.Rect(48, 110, 48, 72)}]
        self.images = {}

    def probe_rect(self, point, size=(24, 12)):
        result = pygame.Rect(0, 0, *size)
        result.center = tuple(round(value) for value in point)
        return result

    def can_stand(self, point, size=(24, 12), ignore_npc=None):
        probe = self.probe_rect(point, size)
        return (pygame.Rect(0, 0, *self.size).contains(probe)
                and not probe.colliderect(pygame.Rect(56, 128, 32, 48))
                and not any(actor is not ignore_npc and probe.colliderect(actor.blocker)
                            for actor in self.npcs))

    def image(self, path):
        if path not in self.images:
            self.images[path] = pygame.image.load(str(ROOT / path)).convert_alpha()
        return self.images[path]


class SanctuaryReliefRestTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='sanctuary-relief-rest-')
        self.addCleanup(temporary.cleanup)
        self.addCleanup(pygame.quit)
        directory = Path(temporary.name)
        self.game = Game(window_size=(960, 640), fullscreen=False, start_on_title=False,
                         save_path=directory/'journey.json', settings_path=directory/'settings.json')
        self.game.audio.set_music(0)
        self.game.audio.set_effects(0)
        self.game.opening.stage = 'disabled'
        self.game.opening_fade = self.game.transfer_cooldown = 0
        self.game.world = ReliefWorld()
        self.game.save_progress = Mock(return_value=True)
        self.controller = SanctuaryRelief(self.game)
        self.controller.ensure_world()
        self.bedside()

    def bedside(self):
        self.game.player.position.update(104, 150)
        self.game.player.facing = 'left'

    def attendant(self):
        self.game.player.position.update(240, 202)
        self.game.player.facing = 'back'

    def choices(self):
        for _ in range(20):
            if self.game.social.choosing:
                self.game.social.refresh_layout()
                return
            self.assertTrue(self.game.social.active)
            self.game.social.advance()
        self.fail('The rest offer did not reach explicit choices')

    def choose(self, action):
        self.choices()
        index = next(index for index, choice in enumerate(self.game.social.choice_options)
                     if choice['action'] == action)
        self.assertTrue(self.game.social.click(self.game.social.choice_rects[index].center))

    def resources(self):
        return {identifier: (attributes.current_hp, attributes.current_mp)
                for identifier, attributes in self.game.party.characters.items()}

    def durable_facts(self):
        game = self.game
        return deepcopy((game.character_progression.to_dict(), game.quests.to_dict(),
                         game.mill_quest.to_dict(), game.regent_quest.to_dict(),
                         game.inventory.to_dict(), game.character_abilities.to_dict(),
                         game.bot_loadouts.to_dict(), game.party.members, game.party.active_ids,
                         game.party.event_id, game.battle_rewards.to_dict(),
                         game.cave_random_encounters.to_dict(), sorted(game.social.flags)))

    def wound_party(self):
        party = self.game.party
        for identifier in ('mira', 'lucan', 'rhea', 'edran'):
            self.assertTrue(party.recruit(identifier))
        self.assertTrue(party.set_available('edran', False, 'Elsewhere in the story.'))
        for index, attributes in enumerate(party.characters.values()):
            self.assertTrue(attributes.set_current(hp=0 if index % 2 else 7, mp=0))
        self.assertIn('rhea', party.reserve_ids)

    def test_bed_confirmation_recovers_available_party_and_reserves_without_other_rewards(self):
        self.wound_party()
        before = self.durable_facts()
        unavailable = self.resources()['edran']
        self.assertEqual(self.game.bed_rest.interaction_hint(), 'E: rest')
        self.assertTrue(self.game.bed_rest.interact())
        self.assertEqual(self.game.social.script_identifier, 'sanctuary_relief_bed_offer')
        self.choose('rest')
        for identifier in self.game.party.available_ids:
            attributes = self.game.party.characters[identifier]
            self.assertEqual(self.resources()[identifier], (attributes.value('hp'), attributes.value('mp')))
        self.assertEqual(self.resources()['edran'], unavailable)
        self.assertEqual(self.durable_facts(), before)
        self.assertEqual(self.game.social.script_identifier, 'sanctuary_relief_bed_complete')
        self.assertGreater(self.game.opening_fade, 0)
        self.game.save_progress.assert_called_once()

    def test_attendant_has_registered_portrait_and_uses_same_confirmed_recovery(self):
        self.wound_party()
        self.attendant()
        self.assertEqual(self.controller.interaction_hint(), 'E: speak to Attendant Nessa')
        self.assertTrue(self.controller.interact())
        self.assertEqual(self.game.social.script_identifier, 'sanctuary_relief_attendant_offer')
        speaker = self.game.social.data['speakers']['relief_attendant']
        self.assertEqual(speaker['name'], 'Attendant Nessa')
        self.assertIn(speaker['portrait'], self.game.social.portraits)
        self.choose('rest')
        self.assertEqual(self.game.social.script_identifier, 'sanctuary_relief_attendant_complete')
        self.assertGreater(self.game.party.characters['mira'].current_hp, 0)
        self.assertEqual(self.game.attributes.current_mp, self.game.attributes.value('mp'))

    def test_prose_decline_and_cancel_never_heal(self):
        for source in ('bed', 'attendant'):
            with self.subTest(source=source):
                self.game.social.cancel_script()
                self.game.attributes.set_current(hp=7, mp=0)
                if source == 'bed':self.bedside();start = self.game.bed_rest.interact
                else:self.attendant();start = self.controller.interact
                self.assertTrue(start())
                self.choices()
                for _ in range(3):self.game.social.advance()
                self.assertEqual((self.game.attributes.current_hp, self.game.attributes.current_mp), (7, 0))
                self.choose('leave')
                self.assertEqual((self.game.attributes.current_hp, self.game.attributes.current_mp), (7, 0))
                self.assertTrue(start())
                self.assertTrue(self.game.social.cancel())
                self.assertIsNone(self.game.social._choice_callback)
                self.assertEqual((self.game.attributes.current_hp, self.game.attributes.current_mp), (7, 0))
        self.game.save_progress.assert_not_called()

    def test_stale_bed_and_attendant_choices_recheck_range_and_scene(self):
        for source in ('bed', 'attendant'):
            for leave_room in (False, True):
                with self.subTest(source=source, leave_room=leave_room):
                    self.game.social.cancel_script()
                    self.game.world.data['id'] = SCENE_ID
                    self.game.attributes.set_current(hp=9, mp=1)
                    if source == 'bed':self.bedside();self.assertTrue(self.game.bed_rest.interact())
                    else:self.attendant();self.assertTrue(self.controller.interact())
                    self.choices()
                    callback = self.game.social._choice_callback
                    self.game.social.cancel_script()
                    if leave_room:self.game.world.data['id'] = 'elden_vale_sanctuary_hall'
                    else:self.game.player.position.update(168, 248)
                    callback('rest')
                    self.assertEqual((self.game.attributes.current_hp, self.game.attributes.current_mp), (9, 1))
        self.game.save_progress.assert_not_called()

    def test_save_failure_rolls_back_and_explicit_retry_recovers_once(self):
        self.wound_party()
        before, facts = self.resources(), self.durable_facts()
        self.game.save_progress.side_effect = (False, True)
        self.assertTrue(self.game.bed_rest.interact())
        self.choose('rest')
        self.assertEqual(self.resources(), before)
        self.assertEqual(self.durable_facts(), facts)
        self.assertEqual(self.game.social.script_identifier, 'sanctuary_relief_bed_retry')
        self.assertTrue(self.game.bed_rest.last_error)
        self.assertEqual(self.game.opening_fade, 0)
        self.choose('rest')
        self.assertEqual(self.game.save_progress.call_count, 2)
        self.assertFalse(self.game.bed_rest.last_error)
        self.assertEqual(self.game.attributes.current_hp, self.game.attributes.value('hp'))
        self.assertEqual(self.durable_facts(), facts)

    def test_menus_transfers_story_actions_and_combat_block_rest(self):
        blockers = (('pause', 'is_open'), ('inventory_ui', 'is_open'),
                    ('party_ui', 'is_open'), ('world_map_viewer', 'is_open'),
                    ('quest_ui', 'journal_open'), ('combat', 'scene'))
        for owner, field in blockers:
            with self.subTest(owner=owner):
                instance = getattr(self.game, owner)
                previous = getattr(instance, field)
                setattr(instance, field, object() if owner == 'combat' else True)
                self.assertFalse(self.game.bed_rest.interact())
                setattr(instance, field, previous)
        for field in ('transfer_cooldown', 'opening_fade', 'map_open'):
            with self.subTest(field=field):
                setattr(self.game, field, 1)
                self.assertFalse(self.game.bed_rest.interact())
                setattr(self.game, field, 0)
        with patch.object(Game, 'household_action', new_callable=PropertyMock, return_value=True):
            self.assertFalse(self.game.bed_rest.interact())
        self.game.opening.stage = 'wake'
        self.assertFalse(self.game.bed_rest.interact())
        self.game.save_progress.assert_not_called()

    def test_attendant_lifecycle_keeps_one_actor_and_releases_conversation_pose(self):
        actor = self.controller.attendant
        self.controller.ensure_world()
        self.assertIs(self.controller.attendant, actor)
        self.assertEqual(self.game.world.npcs, [actor])
        self.assertEqual(actor.scene_id, SCENE_ID)
        self.attendant()
        self.assertTrue(self.controller.interact())
        self.assertTrue(actor.conversation_ready)
        self.game.social.cancel()
        self.controller.update(0)
        self.assertFalse(actor.conversation_ready)
        self.controller.reset()
        self.assertEqual(self.game.world.npcs, [])
        self.controller.ensure_world()
        self.assertEqual(len(self.game.world.npcs), 1)


if __name__ == '__main__':unittest.main()
