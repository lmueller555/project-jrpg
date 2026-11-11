"""The mill lesson resolves Guard, failure, and the inadvertent discovery in order."""
import unittest
from battle_model import BattleModel, ELEMENTAL_EDGE_ATTEMPTS
from character_attributes import CharacterAttributes
from gear_state import REQUIRED_GEMS
from test_aether_edge_battle_model import FixedVariance


class SpellbladeLessonTests(unittest.TestCase):
    def model(self):
        return BattleModel(CharacterAttributes(),enemy_id='ridgeback_tusker',guest_id='mira',
                           weapon_equipped=True,spellblade_tutorial=True,rng=FixedVariance())

    def ready(self,model):
        model.update(1000)
        self.assertTrue(model.waiting_for_player)
        self.assertEqual(model.ready_actor,'player')

    def test_blue_attempt_fails_then_accidentally_discovers_aether_without_second_choice(self):
        m=self.model();self.ready(m)
        self.assertEqual(m.spellblade_stage,'guard')
        self.assertFalse(m.choose_action('attack'));self.assertFalse(m.choose_action('flee'))
        self.assertFalse(m.select_ready('mira'))
        self.assertNotEqual(m.command_reason('skills'),'')
        self.assertTrue(m.choose_action('guard'));self.ready(m)
        charge=next(e for e in m.events if e['type']=='impact' and e['action']=='tusker_charge')
        self.assertTrue(charge['guarded']);self.assertGreater(m.player.hp,0)
        self.assertEqual(m.spellblade_stage,'first_edge')
        self.assertEqual(m.skill_actions(),['aqua_edge'])
        self.assertNotIn('aether_edge',m.available_actions())
        hp,mp=m.enemy.hp,m.player.mp
        self.assertTrue(m.choose_action('aqua_edge'));failed=m.current_action
        self.assertEqual(failed.action,'aqua_edge_attempt')
        m.update(failed.impact_at)
        self.assertEqual(m.enemy.hp,hp);self.assertEqual(m.player.mp,mp)
        self.assertFalse(m.aether_edge_discovered)
        self.assertEqual(m.spellblade_stage,'second_edge')
        m.update(failed.duration-failed.elapsed)
        self.assertEqual(m.current_action.action,'aether_edge')
        self.assertEqual(m.player.mp,mp-4)
        self.assertFalse(m.waiting_for_player)
        m.update(m.current_action.impact_at)
        self.assertTrue(m.aether_edge_discovered)
        self.assertEqual(m.spellblade_stage,'complete')
        self.assertEqual(m.skill_actions('player'),['aether_edge'])
        self.assertGreater(m.current_action.damage,0)
        self.assertGreater(m.enemy.hp,0)
        self.assertNotIn('aqua_edge',m.learned_abilities)
        self.assertEqual(sum(e['type']=='spellblade_discovered' for e in m.events),1)

    def test_ready_choices_pause_all_party_enemy_and_bot_gauges(self):
        m=self.model();self.ready(m)
        before=[a.atb for a in (*m.party,m.enemy)]
        m.update(10000)
        self.assertEqual([a.atb for a in (*m.party,m.enemy)],before)

    def test_known_skill_skips_the_temporary_training_menu(self):
        m=BattleModel(CharacterAttributes(),enemy_id='ridgeback_tusker',guest_id='mira',
                      weapon_equipped=True,spellblade_tutorial=True,learned_abilities=['aether_edge'])
        self.assertFalse(m.spellblade_guided)
        self.assertEqual(m.skill_actions('player'),['aether_edge'])
        self.assertFalse(m.aether_edge_discovered)

    def test_caelan_incapacitation_releases_companions_without_an_unearned_skill(self):
        model=self.model();model.player.hp=0
        for _ in range(100):
            model.update(1000)
            if model.ended:break
            self.assertTrue(model.waiting_for_player)
            self.assertEqual(model.ready_actor,'mira')
            self.assertTrue(model.choose_action('attack'))
        self.assertTrue(model.ended)
        self.assertFalse(model.spellblade_guided)
        self.assertFalse(model.aether_edge_discovered)
        self.assertNotIn('aether_edge',model.learned_abilities)
        self.assertEqual(model.skill_actions('player'),[])
        self.assertEqual(sum(e['type']=='spellblade_interrupted' for e in model.events),1)

    def test_incapacitation_while_waiting_cannot_leave_a_dead_actor_ready(self):
        model=self.model();self.ready(model)
        model.player.hp=0;model.update(1000)
        self.assertEqual(model.ready_actor,'mira')
        self.assertFalse(model.spellblade_guided)
        self.assertFalse(model.aether_edge_discovered)


if __name__=='__main__':unittest.main()
