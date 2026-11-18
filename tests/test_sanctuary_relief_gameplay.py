"""Real Sanctuary doors, local recovery and Continue during the MQ03 outing."""
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import pygame

from main import Game
from overworld_travel import HALL_ID, RELIEF_ID, RESERVE_ID, OverworldTravel
from quests import LANTERN_QUEST, REGENT_QUEST
from sanctuary_cave import RESERVE_ENTRY_APPROACH
from tools.capture_mq03_emergency import Driver
from tools.capture_sanctuary_reserve import path as clear_path, walk


class SanctuaryReliefGameplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Earlier quests are a labelled fixture; MQ03, its emergency departure,
        # Mira's return and the Sanctuary journey use actual story input.
        with tempfile.TemporaryDirectory(prefix='relief-story-') as directory:
            driver = Driver(directory)
            driver.meal()
            driver.attack_report()
            driver.departure()
            driver.rejoin_mira()
            driver.arrive()
            assert driver.game.save_progress()
            cls.journey = json.loads(driver.save.read_text())
        pygame.quit()

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='relief-gameplay-')
        self.addCleanup(temporary.cleanup)
        self.addCleanup(pygame.quit)
        self.directory = Path(temporary.name)
        self.path = self.directory/'journey.json'
        self.path.write_text(json.dumps(self.journey))
        self.game = self.load()

    def load(self):
        game = Game(window_size=(960, 640), fullscreen=False, start_on_title=True,
                    save_path=self.path, settings_path=self.directory/'settings.json')
        game.audio.set_music(0)
        game.audio.set_effects(0)
        self.assertTrue(game.has_saved_journey, game.save_error)
        self.assertTrue(game.begin_journey(True), game.save_error)
        game.opening_fade = game.transfer_cooldown = 0
        pygame.event.clear()
        return game

    def key(self, key):
        self.assertTrue(self.game.handle_events([
            pygame.event.Event(pygame.KEYDOWN, key=key, repeat=False),
            pygame.event.Event(pygame.KEYUP, key=key)]))

    def settle(self):
        for _ in range(30):
            if not self.game.opening_fade and not self.game.transfer_cooldown:
                return
            self.game.update(.05, (0, 0), False)
        self.fail('The Sanctuary transfer did not finish')

    def route(self, goal):
        game = self.game
        scene = game.world.data['id']
        points = clear_path(game.world, game.player.position, goal)
        walk(game, points, scene)
        self.assertEqual(game.world.data['id'], scene)
        self.assertTrue(game.world.can_stand(game.player.position))
        self.assertFalse(game.combat.active)

    def doorway(self, identifier, destination):
        """Walk to the authored door and cross it with ordinary movement."""
        game = self.game
        origin = game.world
        door = next(door for door in origin.doors if door.data['id'] == identifier)
        x, y = door.data['anchor']
        north = door.data['entry_side'] == 'north'
        self.route((x, y+24 if north else y-24))
        for _ in range(60):
            if game.world is not origin:
                break
            game.update(.04, (0, -1 if north else 1), False)
        self.assertEqual(game.world.data['id'], destination)
        self.assertTrue(game.world.can_stand(game.player.position))
        landing = tuple(game.player.position)
        self.settle()
        # In particular, returning to the hall next to its north-entry side
        # door must not immediately send a stationary player back inside.
        for _ in range(12):
            game.update(.05, (0, 0), False)
        self.assertEqual(game.world.data['id'], destination)
        self.assertEqual(tuple(game.player.position), landing)

    def enter_room(self):
        self.assertEqual(self.game.world.data['id'], RESERVE_ID)
        self.doorway('sanctuary_hall', HALL_ID)
        self.doorway('relief_room', RELIEF_ID)
        self.assertTrue(self.game.sanctuary_relief.active)
        self.assertIn(self.game.sanctuary_relief.attendant, self.game.world.npcs)

    def story(self):
        game = self.game
        self.assertEqual(game.regent_quest.stage, 'sanctuary_arrival_pending')
        self.assertEqual(game.quests.status(REGENT_QUEST), 'active')
        self.assertEqual(game.quests.status(LANTERN_QUEST), 'locked')
        self.assertEqual(game.party.current_event_id, 'mq03_sanctuary')
        self.assertIn('mira', game.party.active_ids)
        self.assertEqual(game.music.desired_track, 'battle')

    def durable_facts(self):
        game = self.game
        return deepcopy({
            'levels': game.character_progression.to_dict(),
            'inventory': game.inventory.to_dict(),
            'quests': game.quests.to_dict(),
            'flags': sorted(game.social.flags),
            'opening': game.opening.to_dict(),
            'mill': game.mill_quest.to_dict(),
            'regent': game.regent_quest.to_dict(),
            'lantern': game.lantern_quest.to_dict(),
            'members': game.party.members,
            'active': game.party.active_ids,
            'event': game.party.event_id,
            'abilities': game.character_abilities.to_dict(),
            'rig': game.mira_rig.to_dict(),
            'rewards': game.battle_rewards.to_dict(),
            'treasure': game.sanctuary_cave.to_dict(),
            'encounters': game.cave_random_encounters.to_dict(),
            'music': game.music.desired_track,
        })

    def seed_earned_progress(self):
        """Nonempty durable records make accidental resets observable."""
        game = self.game
        active = game.party.active_ids
        hp = {identifier: game.party.characters[identifier].current_hp for identifier in active}
        self.assertTrue(game.character_progression.apply(
            game.character_progression.preview(80, active, hp)))
        self.assertTrue(game.sanctuary_cave.restore(
            {'version': 1, 'opened': ['cave_vein_cache']}))
        self.assertTrue(game.inventory.add('aether_sapphire'))
        game.social.flags.add('relief_gameplay_preserves_seen_dialogue')
        game.cave_random_encounters.reset(73)
        counter = game.cave_random_encounters.to_dict()
        counter['remaining'] = counter['threshold']-80
        counter['was_safe'] = False
        self.assertTrue(game.cave_random_encounters.restore(counter))

    def offer(self, script):
        self.key(pygame.K_e)
        self.assertEqual(self.game.social.script_identifier, script)
        for _ in range(30):
            if self.game.social.choosing:
                self.game.draw()
                return
            self.assertTrue(self.game.social.active)
            self.key(pygame.K_SPACE)
        self.fail('The relief offer did not expose its explicit choices')

    def choose(self, action):
        game = self.game
        index = next(index for index, option in enumerate(game.social.choice_options)
                     if option['action'] == action)
        rect = game.social.choice_rects[index]
        _, size, origin = game._ensure_ui_surface()
        point = (round(origin[0]+rect.centerx*size[0]/480),
                 round(origin[1]+rect.centery*size[1]/320))
        self.assertTrue(game.handle_events([
            pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=point),
            pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=point)]))

    def finish_dialogue(self):
        for _ in range(30):
            if not self.game.social.active:
                self.settle()
                return
            self.assertFalse(self.game.social.choosing)
            self.key(pygame.K_SPACE)
        self.fail('Relief dialogue did not finish')

    def test_real_door_loop_connects_bed_attendant_and_cave_without_story_progress(self):
        before = self.durable_facts()
        self.enter_room()
        metadata = self.game.world.data['relief_room']
        self.route(metadata['bed_approach'])
        self.assertEqual(self.game.bed_rest.interaction_hint(), 'E: rest')
        self.route(metadata['attendant_approach'])
        self.game.player.facing = 'back'
        self.assertEqual(self.game.sanctuary_relief.interaction_hint(),
                         'E: speak to Attendant Nessa')
        self.doorway('hall', HALL_ID)
        self.doorway('reserve_exit', RESERVE_ID)
        self.assertEqual(self.durable_facts(), before)
        self.route(RESERVE_ENTRY_APPROACH)
        self.key(pygame.K_e)
        self.assertEqual(self.game.world.data['id'], 'sanctuary_cave')
        self.settle()
        exit_link = next(link for link in self.game.world.data['cave']['links']
                         if link['id'] == 'reserve')
        self.route(exit_link['approach'])
        self.key(pygame.K_e)
        self.assertEqual(self.game.world.data['id'], RESERVE_ID)
        self.settle()
        self.assertFalse(self.game.combat.active)
        self.story()
        after_cave = self.durable_facts()
        self.assertTrue(self.game.attributes.set_current(hp=9, mp=0))
        self.assertTrue(self.game.party.characters['mira'].set_current(hp=0, mp=0))
        self.enter_room()
        self.route(self.game.world.data['relief_room']['bed_approach'])
        self.offer('sanctuary_relief_bed_offer')
        self.choose('rest')
        self.finish_dialogue()
        for identifier in self.game.party.available_ids:
            attributes = self.game.party.characters[identifier]
            self.assertEqual((attributes.current_hp, attributes.current_mp),
                             (attributes.value('hp'), attributes.value('mp')))
        self.assertEqual(self.durable_facts(), after_cave)
        self.assertEqual(json.loads(self.path.read_text())['player']['scene'], RELIEF_ID)
        self.story()

    def test_attendant_rest_heals_the_travelling_party_and_preserves_the_pending_outing(self):
        self.enter_room()
        self.seed_earned_progress()
        game = self.game
        self.assertTrue(game.party.recruit('rhea'))
        self.assertTrue(game.party.recruit('edran'))
        self.assertTrue(game.party.set_available('edran', False, 'Away on story business.'))
        self.assertTrue(game.party.select(('caelan', 'mira')))
        self.assertIn('rhea', game.party.reserve_ids)
        for identifier in game.party.available_ids:
            self.assertTrue(game.party.characters[identifier].set_current(hp=0, mp=0))
        self.assertTrue(game.party.characters['edran'].set_current(hp=5, mp=1))
        self.route(game.world.data['relief_room']['attendant_approach'])
        game.player.facing = 'back'
        before = self.durable_facts()
        self.offer('sanctuary_relief_attendant_offer')
        self.choose('rest')
        self.assertEqual(game.social.script_identifier, 'sanctuary_relief_attendant_complete')
        for identifier in game.party.available_ids:
            attributes = game.party.characters[identifier]
            self.assertEqual((attributes.current_hp, attributes.current_mp),
                             (attributes.value('hp'), attributes.value('mp')))
        edran = game.party.characters['edran']
        self.assertEqual((edran.current_hp, edran.current_mp), (5, 1))
        self.finish_dialogue()
        self.assertEqual(self.durable_facts(), before)
        self.story()
        self.assertIsNotNone(game._read_saved_journey(), game.save_error)

    def test_continue_in_the_room_keeps_location_resources_progress_and_single_attendant(self):
        self.enter_room()
        self.seed_earned_progress()
        self.route(self.game.world.data['relief_room']['bed_approach'])
        self.game.player.facing = 'left'
        self.assertTrue(self.game.attributes.set_current(hp=7, mp=1))
        self.assertTrue(self.game.party.characters['mira'].set_current(hp=0, mp=0))
        before = self.durable_facts()
        position = tuple(self.game.player.position)
        resources = {identifier: attributes.to_dict()
                     for identifier, attributes in self.game.party.characters.items()}
        self.assertTrue(self.game.save_progress())
        snapshot = json.loads(self.path.read_text())
        self.assertTrue(OverworldTravel.valid_journey(snapshot))
        missing_region = deepcopy(snapshot)
        del missing_region['overworld']
        self.assertFalse(OverworldTravel.valid_journey(missing_region))
        self.game = self.load()
        game = self.game
        self.assertEqual(game.world.data['id'], RELIEF_ID)
        self.assertEqual(tuple(game.player.position), position)
        self.assertEqual(game.player.facing, 'left')
        self.assertTrue(game.world.can_stand(game.player.position))
        self.assertTrue(game.overworld_travel.in_reserve)
        self.assertTrue(game.overworld_travel.remote)
        self.assertEqual(self.durable_facts(), before)
        self.assertEqual({identifier: attributes.to_dict()
                          for identifier, attributes in game.party.characters.items()}, resources)
        for _ in range(5):
            game.sanctuary_relief.ensure_world()
            game.update(.05, (0, 0), False)
        self.assertEqual(sum(npc.data.get('id') == 'relief_attendant'
                             for npc in game.world.npcs), 1)
        self.route(game.world.data['relief_room']['attendant_approach'])
        self.assertIn('mira', [actor.identifier for actor in game.party_travel.actors()])
        self.assertTrue(all(game.world.can_stand(actor.position)
                            for actor in game.party_travel.actors()))
        self.story()

    def test_room_movement_and_map_keep_the_cave_encounter_budget_untouched(self):
        self.enter_room()
        self.seed_earned_progress()
        counter = self.game.cave_random_encounters.to_dict()
        metadata = self.game.world.data['relief_room']
        for _ in range(3):
            self.route(metadata['bed_approach'])
            self.route(metadata['attendant_approach'])
        self.assertEqual(self.game.cave_random_encounters.to_dict(), counter)
        self.assertIsNone(self.game.cave_random_encounters.pending)
        self.key(pygame.K_m)
        self.assertTrue(self.game.map_open)
        self.assertTrue(self.game.map_ui._in_reserve())
        self.assertEqual(self.game.map_ui._reserve().player_position(),
                         tuple(self.game.world.data['exterior_map_position']))
        self.game.draw()
        self.assertFalse(self.game.combat.active)
        self.assertEqual(self.game.cave_random_encounters.to_dict(), counter)
        self.story()


if __name__ == '__main__':
    unittest.main()
