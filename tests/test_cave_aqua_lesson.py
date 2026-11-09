"""Persisted tutorial formation facts, checkpoints and unobstructed preparation."""
from copy import deepcopy
from types import SimpleNamespace
import unittest

import pygame

from cave_lesson import CaveLesson
from cave_random_encounters import CaveRandomEncounters


class FakeAbilities:
    def __init__(self, known=(), weapon=True):self.known=set(known);self.weapon=weapon
    def known_abilities(self):return frozenset(self.known)
    def has_weapon(self):return self.weapon
    def owned_gems(self):return ('water',)
    def to_dict(self):
        return {'characters':{'caelan':{'equipped_weapon':'caelan_gearblade' if self.weapon else None}}}
    def learn_ability(self, character, skill):
        self.known.add(skill)
        return True


class CaveAquaLessonTests(unittest.TestCase):
    def game(self, known=(), weapon=True):
        abilities=FakeAbilities(known,weapon)
        return SimpleNamespace(character_abilities=abilities,
                               party=SimpleNamespace(active_ids=('caelan','mira'),
                                   characters={'caelan':SimpleNamespace(current_hp=10)},
                                   battle_reason=lambda:None))

    def test_fixed_pair_uses_countdown_actual_local_scene_and_saved_seed(self):
        for position in ([456,1280],[1100,1200],[1680,970]):
            with self.subTest(position=position):
                counter=CaveRandomEncounters(seed=82)
                before=counter.to_dict()
                self.assertIsNone(counter.advance(before['remaining']-1,position,introductory=True))
                ticket=counter.advance(1,position,introductory=True)
                self.assertEqual(ticket['formation'],'bat_pair')
                self.assertEqual(ticket['members'],[{'enemy_id':'cave_bat','level':2}]*2)
                self.assertEqual(ticket['lesson'],'aqua_edge')
                self.assertEqual(ticket['battlefield'],counter.region_at(position)['battlefield'])
                self.assertTrue(counter.valid_ticket(ticket))
                clone=CaveRandomEncounters(seed=1)
                self.assertTrue(clone.restore(counter.to_dict()))
                self.assertEqual(clone.advance(1000,position),ticket)
                self.assertEqual(clone.to_dict(),counter.to_dict())
                malformed=deepcopy(ticket);malformed['members'][0]['level']=3
                self.assertFalse(counter.valid_ticket(malformed))
                malformed=deepcopy(ticket);malformed['formation']='bat'
                self.assertFalse(counter.valid_ticket(malformed))
                malformed=deepcopy(ticket);malformed['lesson']='unknown'
                self.assertFalse(counter.valid_ticket(malformed))

    def test_only_explicit_intro_flag_changes_normal_weighted_roster(self):
        counter=CaveRandomEncounters(seed=82)
        ticket=counter.advance(1000,[1680,970])
        self.assertNotIn('lesson',ticket)
        self.assertTrue(counter.finish(ticket['receipt']))
        intro=counter.advance(1000,[1680,970],introductory=True)
        self.assertTrue(counter.finish(intro['receipt']))
        following=counter.advance(1000,[1680,970])
        self.assertNotIn('lesson',following)
        self.assertTrue(counter.valid_snapshot(counter.to_dict()))

    def test_resource_preflight_does_not_require_mp_and_state_is_independent(self):
        game=self.game();game.party.characters['caelan'].current_mp=0
        lesson=CaveLesson(game)
        self.assertIsNone(lesson.ready_reason())
        game.party.characters['caelan'].current_hp=0
        self.assertIn('recover',lesson.ready_reason())
        game.party.characters['caelan'].current_hp=10;game.character_abilities.weapon=False
        self.assertIn('Equip',lesson.ready_reason())
        game.character_abilities.weapon=True
        game.party.active_ids=('mira',)
        self.assertIn('combat party',lesson.ready_reason())
        self.assertTrue(lesson.needs_intro)
        self.assertEqual(lesson.to_dict(),{'version':1,'resonance_seen':False,
                                         'battle_cleared':False,'deferred':False})
        self.assertFalse(lesson.mark_cleared({'receipt':'normal'}))
        lesson.resonance_seen=True
        self.assertTrue(lesson.defer({'lesson':'aqua_edge'}))
        self.assertTrue(lesson.needs_intro)
        self.assertTrue(lesson.mark_cleared({'lesson':'aqua_edge'}))
        self.assertFalse(lesson.needs_intro);self.assertFalse(lesson.deferred)

    def test_state_restore_is_atomic_and_rejects_invalid_combinations(self):
        lesson=CaveLesson(self.game())
        lesson.resonance_seen=True
        before=lesson.to_dict()
        for mutation in ({'version':True},{'deferred':1},{'battle_cleared':True,'deferred':True},
                         {'extra':False},{'battle_cleared':True,'resonance_seen':False}):
            record=before|mutation
            self.assertFalse(lesson.restore(record),record)
            self.assertEqual(lesson.to_dict(),before)
        self.assertTrue(lesson.restore())
        self.assertFalse(lesson.resonance_seen)

    def test_legacy_visitors_preserve_learned_aether_and_gain_aqua_without_replay(self):
        for legacy in ({'cave_random_encounters':{'sequence':3}},
                       {'sanctuary_boss':{'defeated':True}},
                       {'sanctuary_boss':{'pending':{'receipt':'boss:vespermaw'}}}):
            game=self.game(('aether_edge',))
            lesson=CaveLesson(game)
            self.assertTrue(lesson.restore(legacy_journey=legacy))
            self.assertEqual(game.character_abilities.known,{'aether_edge','aqua_edge'})
            self.assertTrue(lesson.resonance_seen);self.assertTrue(lesson.battle_cleared)
        game=self.game(('aether_edge',));lesson=CaveLesson(game)
        self.assertTrue(lesson.restore(legacy_journey={'cave_random_encounters':{'sequence':0}}))
        self.assertEqual(game.character_abilities.known,{'aether_edge'})
        self.assertTrue(lesson.needs_intro)

    def test_deferred_ticket_can_travel_to_bed_without_reroll_or_false_clear(self):
        counter=CaveRandomEncounters(seed=82)
        ticket=counter.advance(1000,[456,1280],introductory=True)
        journey={'cave_random_encounters':counter.to_dict(),
                 'player':{'scene':'elden_vale_sanctuary_relief','position':[100,100]},
                 'cave_lesson':{'version':1,'resonance_seen':True,'battle_cleared':False,'deferred':True}}
        self.assertTrue(CaveRandomEncounters.valid_journey(journey))
        self.assertTrue(CaveLesson.valid_journey(journey))
        for malformed in (None, [], 'deferred'):
            bad = deepcopy(journey);bad['cave_lesson'] = malformed
            self.assertFalse(CaveRandomEncounters.valid_journey(bad))
        journey['cave_lesson']['deferred']=False
        self.assertFalse(CaveRandomEncounters.valid_journey(journey))
        journey['player']={'scene':'sanctuary_cave','position':ticket['position']}
        self.assertTrue(CaveRandomEncounters.valid_journey(journey))
        self.assertTrue(CaveLesson.valid_journey(journey))
        journey['cave_lesson']['battle_cleared']=True
        self.assertFalse(CaveLesson.valid_journey(journey))
        journey['post_battle']={'stage':'awarded','encounter':ticket}
        self.assertFalse(CaveLesson.valid_journey(journey))
        journey['character_abilities']={'learned_abilities':{'caelan':['aqua_edge']}}
        self.assertTrue(CaveLesson.valid_journey(journey))
        for malformed in (None,[],{'cave_lesson':[]},{'cave_lesson':journey['cave_lesson'],
                                                  'cave_random_encounters':[]}):
            self.assertFalse(CaveLesson.valid_journey(malformed))

    def test_completed_legacy_gift_migration_is_targeted_and_idempotent(self):
        from character_abilities import CharacterAbilities
        from inventory import Inventory
        from main import Game
        inventory=Inventory()
        abilities=CharacterAbilities(inventory)
        status=['active']
        game=SimpleNamespace(character_abilities=abilities,inventory=inventory,
                             mill_quest=SimpleNamespace(legacy_bypass=True),
                             quests=SimpleNamespace(status=lambda identifier:status[0]))
        self.assertFalse(Game._migrate_legacy_blade(game))
        self.assertEqual(inventory.quantity('caelan_gearblade'),0)
        status[0]='completed'
        self.assertTrue(Game._migrate_legacy_blade(game))
        self.assertEqual(inventory.quantity('caelan_gearblade'),1)
        self.assertEqual(abilities.owned_gems(),('water',))
        self.assertIn('aether_edge',abilities.known_abilities())
        before=abilities.to_dict()
        self.assertFalse(Game._migrate_legacy_blade(game))
        self.assertEqual(abilities.to_dict(),before)
        self.assertEqual(inventory.quantity('caelan_gearblade'),1)
        other=Inventory();game.inventory=other;game.character_abilities=CharacterAbilities(other)
        self.assertFalse(Game._migrate_legacy_blade(game,False))
        self.assertEqual(other.quantity('caelan_gearblade'),0)

    def test_pose_release_restores_prior_owner_and_reset_clears_only_our_pose(self):
        game=self.game()
        original=pygame.Surface((3,3))
        game.player=SimpleNamespace(story_sprite=pygame.Surface((4,4)),story_draw_anchor=(20,38))
        lesson=CaveLesson(game)
        lesson._pose_prior={'story_sprite':original,'story_draw_anchor':(1,2)}
        self.assertTrue(lesson.restore())
        self.assertIs(game.player.story_sprite,original)
        self.assertEqual(game.player.story_draw_anchor,(1,2))
        lesson._pose_prior={}
        lesson.release_pose()
        self.assertFalse(hasattr(game.player,'story_sprite'))
        self.assertFalse(hasattr(game.player,'story_draw_anchor'))

    def test_resonance_draw_is_bounded_and_reduced_motion_is_static(self):
        game=self.game()
        game.world=SimpleNamespace(data={'id':'sanctuary_cave'})
        game.social=SimpleNamespace(script_identifier='cave_blue_resonance')
        game.player=SimpleNamespace(position=pygame.Vector2(100,100))
        game.audio=SimpleNamespace(reduced_motion=True)
        lesson=CaveLesson(game);lesson._glowing=True
        first=pygame.Surface((480,320),pygame.SRCALPHA)
        second=first.copy()
        lesson.draw_world(first,(0,0));lesson._elapsed=1000
        lesson.draw_world(second,(0,0))
        self.assertEqual(pygame.image.tobytes(first,'RGBA'),pygame.image.tobytes(second,'RGBA'))
        self.assertLess(first.get_bounding_rect().width,40)
        self.assertLess(first.get_bounding_rect().height,50)


if __name__ == '__main__':unittest.main()
