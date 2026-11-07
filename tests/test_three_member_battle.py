"""Persistent lineup snapshots, three independent turns and accessible field UI."""
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame

from audio_settings import AudioSettings
from battle_model import BattleModel, load_guests, load_actions
from battle_scene import BattleScene, CombatSprites
from character_attributes import CharacterAttributes, ATTRIBUTE_IDS
from inventory import Inventory
from ui_style import Painter, UIStyle


NAMES = {'player': 'Caelan', 'mira': 'Mira', 'lucan': 'Lucan Rooke',
         'rhea': 'Rhea Sorel', 'edran': 'Edran Hale'}


def profiles(*identifiers, maximum=False):
    source = CharacterAttributes()
    defaults = {key: source.value(key) for key in ATTRIBUTE_IDS}
    mira = load_guests(load_actions())['mira']['attributes']
    members = []
    for identifier in identifiers:
        attributes = dict(mira if identifier == 'mira' else defaults)
        if maximum:attributes.update(hp=9999, mp=999)
        members.append({'identifier': identifier, 'name': NAMES[identifier],
                        'attributes': attributes, 'hp': attributes['hp'],
                        'mp': attributes['mp'],
                        'attack': 'bolt_shot' if identifier == 'mira' else 'attack'})
    return members


class ThreeMemberBattleTests(unittest.TestCase):
    def model(self, members=None, **options):
        return BattleModel(CharacterAttributes(), party_members=(
            profiles('player', 'mira', 'rhea') if members is None else members), **options)

    def test_lineup_copies_current_resources_and_ratings_without_refilling(self):
        supplied = profiles('player', 'mira', 'edran')
        supplied[0].update(hp=19, mp=7)
        supplied[1].update(hp=0, mp=3)
        supplied[2].update(hp=41, mp=0)
        model = self.model(supplied)
        self.assertEqual([(member.identifier, member.hp, member.mp) for member in model.party],
                         [('player', 19, 7), ('mira', 0, 3), ('edran', 41, 0)])
        supplied[2]['attributes']['str'] = 255
        supplied[2]['hp'] = 1
        self.assertEqual(model.combatant('edran').hp, 41)
        self.assertEqual(model.combatant('edran').value('str'), CharacterAttributes().value('str'))
        model.player.hp = 1
        self.assertEqual(supplied[0]['hp'], 19)
        self.assertNotIn('mira', model.ready_members)

    def test_three_ready_members_select_independent_turns_before_enemy(self):
        model = self.model(bot_loadouts={})
        for actor in (*model.party, model.enemy):actor.atb = 1
        model.update(0)
        self.assertEqual(model.ready_members, ('player', 'mira', 'rhea'))
        self.assertTrue(model.select_ready('rhea'))
        self.assertTrue(model.choose_action('guard'))
        self.assertEqual([actor.atb for actor in model.party], [1, 1, 0])
        model.update(model.current_action.duration)
        self.assertTrue(model.combatant('rhea').guarded)
        self.assertEqual(model.ready_members, ('player', 'mira'))
        self.assertTrue(model.select_ready('mira'))
        self.assertTrue(model.choose_action('attack'))
        self.assertEqual(model.current_action.action, 'bolt_shot')
        self.assertIsNone(model.current_action.choreography)
        model.update(model.current_action.duration)
        self.assertEqual(model.ready_actor, 'player')
        self.assertFalse(any(event['type'] == 'action_started' and event['actor'] == 'enemy'
                             for event in model.events))
        self.assertFalse(model.select_ready('rhea'))

    def test_existing_skills_and_mp_belong_only_to_their_owner(self):
        model = self.model(learned_abilities=['aether_dart'])
        for member in model.party:member.atb = 1
        model.update(0)
        original_mp = [member.mp for member in model.party]
        self.assertTrue(model.choose_action('aether_dart', actor_id='player'))
        self.assertEqual([member.mp for member in model.party],
                         [original_mp[0]-4, *original_mp[1:]])
        model.update(model.current_action.duration)
        self.assertTrue(model.select_ready('rhea'))
        self.assertEqual(model.available_actions(), ['attack', 'guard', 'flee'])
        self.assertEqual(model.skill_actions(), [])
        self.assertFalse(model.choose_action('aether_dart'))
        self.assertTrue(model.choose_action('attack'))
        self.assertEqual(model.current_action.actor, 'rhea')
        self.assertIsNone(model.current_action.choreography)
        self.assertFalse(model.current_action.weapon_equipped)

    def test_enemy_targets_third_living_actor_and_defeat_waits_for_every_member(self):
        supplied = profiles('player', 'mira', 'rhea')
        supplied[0]['hp'] = supplied[1]['hp'] = 0
        model = self.model(supplied, enemy_id='ridgeback_tusker')
        self.assertEqual(model.phase, 'charging')
        self.assertEqual(model._enemy_target('tusk_strike'), 'rhea')
        model.telegraphed_target = 'mira'
        self.assertEqual(model._enemy_target('tusker_charge'), 'rhea')
        model.enemy.atb = 1
        model.update(0)
        self.assertEqual(model.current_action.target, 'rhea')
        model.combatant('rhea').hp = 1
        model.update(model.current_action.duration)
        self.assertEqual(model.phase, 'defeat')
        self.assertEqual(model.bots, ())

    def test_bot_attachment_uses_no_party_slot_and_reserve_mira_deploys_nothing(self):
        model = self.model()
        self.assertEqual(len(model.party), 3)
        self.assertEqual([bot.identifier for bot in model.bots], ['rivet'])
        self.assertIsNone(model._party_actor('rivet'))
        self.assertFalse(model.select_ready('rivet'))
        model = self.model(profiles('player', 'lucan', 'edran'))
        self.assertEqual(model.bots, ())
        for identifier in ('lucan', 'edran'):
            self.assertEqual(model.available_actions(identifier), ['attack', 'guard', 'flee'])

    def test_guided_lesson_accepts_snapshot_and_third_member_covers_automatically(self):
        model = self.model(enemy_id='ridgeback_tusker', weapon_equipped=True,
                           spellblade_tutorial=True)
        model.enemy.atb = 0
        model.combatant('rhea').atb = 1
        model.update(0)
        self.assertEqual((model.current_action.actor, model.current_action.action),
                         ('rhea', 'guard'))
        self.assertEqual(model.ready_members, ())
        model.update(model.current_action.duration)
        self.assertTrue(model.combatant('rhea').guarded)

    def test_rejects_oversize_duplicate_unknown_or_invalid_party_snapshots(self):
        invalid = [[], profiles('player', 'mira', 'lucan', 'rhea'),
                   profiles('mira'), profiles('player', 'player')]
        for field, value in (('identifier', 'enemy'), ('name', ''), ('hp', -1),
                             ('hp', True), ('mp', 9999), ('attack', 'aether_dart'),
                             ('attributes', {})):
            members = profiles('player', 'mira')
            members[1][field] = value
            invalid.append(members)
        for supplied in invalid:
            with self.subTest(supplied=supplied), self.assertRaises(ValueError):
                self.model(supplied)
        with self.assertRaises(ValueError):
            self.model(guest_id='mira')


class ThreeMemberBattleUITests(unittest.TestCase):
    def setUp(self):
        pygame.display.init()
        pygame.font.init()
        self.game = SimpleNamespace(window=pygame.display.set_mode((480, 320)),
                                    ui_surface=pygame.Surface((480, 320)),
                                    audio=AudioSettings(), attributes=CharacterAttributes(),
                                    inventory=Inventory(), to_canvas=lambda point: point)
        self.game.audio.set_effects(0)
        self.game.ui = UIStyle(self.game)
        self.canvas = pygame.Surface((480, 320))

    def tearDown(self):pygame.quit()

    def test_three_columns_max_resources_and_bot_fit_at_minimum_and_default_size(self):
        for identifiers in (('player', 'mira', 'edran'), ('player', 'lucan', 'rhea')):
            model = BattleModel(self.game.attributes,
                                party_members=profiles(*identifiers, maximum=True),
                                weapon_equipped=True)
            scene = BattleScene(self.game, model)
            for size in ((480, 320), (960, 640)):
                self.game.window = pygame.display.set_mode(size)
                self.game.ui_surface = pygame.Surface(size)
                for text_scale in (1, 1.5):
                    with self.subTest(identifiers=identifiers, size=size, text_scale=text_scale):
                        self.game.audio.set_text_scale(text_scale)
                        records = []
                        original = Painter.text

                        def capture(painter, text, *args, **kwargs):
                            bounds = original(painter, text, *args, **kwargs)
                            records.append((str(text), bounds))
                            return bounds

                        with patch.object(Painter, 'text', capture):
                            scene.draw(self.canvas, self.game.ui_surface)
                        self.assertTrue(self.canvas.get_rect().contains(scene.panel_rect))
                        for identifier, row in scene.party_rows.items():
                            member = model.combatant(identifier)
                            matching = [(text, bounds) for text, bounds in records
                                        if text in (member.name, 'HP 9999/9999', 'MP 999/999')
                                        and bounds.colliderect(row['column'])]
                            self.assertEqual(len(matching), 3)
                            for text, bounds in matching:
                                self.assertTrue(row['row'].contains(bounds), (text, bounds, row))
                            for index, (_, bounds) in enumerate(matching):
                                for _, other in matching[index+1:]:
                                    self.assertFalse(bounds.colliderect(other))
                            self.assertLessEqual(row['column'].right, scene.commands_panel.left)
                            self.assertTrue(row['row'].contains(row['hp']))
                            self.assertTrue(row['row'].contains(row['mp']))
                            self.assertLessEqual(row['name'].right, row['atb'].left)
                            self.assertLessEqual(abs(row['name'].centery-row['atb'].centery), 1)
                            for bar, label in (('hp', 'hp_text'), ('mp', 'mp_text')):
                                self.assertLessEqual(row[bar].right, row[label].left)
                                self.assertLessEqual(abs(row[bar].centery-row[label].centery), 1)
                            actor = 'caelan' if identifier == 'player' else identifier
                            image, anchor = scene.sprites.frame(actor, 'idle', 0)
                            ink = image.get_bounding_rect()
                            point = scene._home_positions()[identifier]
                            visible = pygame.Rect(round(point.x+(ink.left-anchor[0])*2),
                                                  round(point.y+(ink.top-anchor[1])*2),
                                                  ink.width*2, ink.height*2)
                            self.assertTrue(self.canvas.get_rect().contains(visible))
                            self.assertLessEqual(visible.bottom, scene.panel_rect.top)
                        self.assertTrue(scene.party_rows['player']['interactable'].contains(scene.gear.rect))
                        for _, bounds in records:
                            if bounds.colliderect(scene.commands_panel):
                                self.assertTrue(scene.commands_panel.contains(bounds))
                        self.assertEqual(scene.bot_status, {})
                        self.assertFalse(any(text == 'Rivet ATB' or text.startswith('Haste ·')
                                             for text, _ in records))

    def test_native_edran_art_falls_back_to_idle_without_mirroring(self):
        sprites = CombatSprites()
        idle, anchor = sprites.frame('edran', 'idle', 0)
        attack, attack_anchor = sprites.frame('edran', 'attack', 0)
        self.assertIs(idle, attack)
        self.assertEqual(anchor, attack_anchor)
        self.assertEqual(anchor, (32, 54))

    def test_keyboard_and_pointer_can_select_the_third_ready_member(self):
        model = BattleModel(self.game.attributes,
                            party_members=profiles('player', 'lucan', 'rhea'))
        for member in model.party:member.atb = 1
        model.update(0)
        scene = BattleScene(self.game, model)
        scene.draw(self.canvas, self.game.ui_surface)
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_TAB)
        scene.handle_event(event)
        self.assertEqual(model.ready_actor, 'lucan')
        scene.handle_event(event)
        self.assertEqual(model.ready_actor, 'rhea')
        model.select_ready('player')
        scene.handle_event(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=1, pos=scene.party_rows['rhea']['row'].center))
        self.assertEqual(model.ready_actor, 'rhea')


if __name__ == '__main__':unittest.main()
