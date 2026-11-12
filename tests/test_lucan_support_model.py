"""Lucan's guest skills use battle-local stats and per-recipient turns."""
from copy import deepcopy
import unittest

from battle_model import BattleModel, LUCAN_SKILLS, load_actions
from character_attributes import CharacterAttributes
from combat_damage import physical_damage
from leveling import character_stats


class FixedVariance:
    def randint(self, low, high):return 100


class LucanSupportModelTests(unittest.TestCase):
    def model(self, enemy='cave_bat', level=2):
        members=[]
        for key in ('player','mira','lucan'):
            values=character_stats('caelan' if key=='player' else key,5)
            values['hp']=9999
            members.append({'identifier':key,'name':key.title(),'attributes':values,
                'hp':9999,'mp':values['mp'],'attack':'bolt_shot' if key=='mira' else 'attack'})
        model=BattleModel.from_bestiary(CharacterAttributes(),enemy,level,
            party_members=members, guest_abilities={'lucan':LUCAN_SKILLS},
            learned_abilities=('aether_edge',),weapon_equipped=True,rng=FixedVariance())
        model.enemy.hp=model.enemy.attributes['hp']=999999
        return model

    def ready(self, model, actor='lucan'):
        self.assertEqual(model.phase,'charging')
        for member in (*model.party,*model.enemies):member.atb=0
        model.combatant(actor).atb=1
        model.update(0)
        self.assertEqual(model.ready_actor,actor)

    def finish(self, model):
        action=model.current_action
        model.update(action.duration-action.elapsed)
        return action

    def cast(self, model, skill, actor='lucan'):
        self.ready(model,actor)
        self.assertTrue(model.choose_action(skill),model.action_reason(skill))
        return self.finish(model)

    def enemy_turn(self, model):
        for member in (*model.party,*model.enemies):member.atb=0
        model.enemy.atb=1
        model.update(0)
        return self.finish(model)

    def test_support_skills_are_lucan_commands_with_exact_resource_costs(self):
        model=self.model()
        self.assertEqual(model.skill_actions('lucan'),list(LUCAN_SKILLS))
        self.assertNotIn('inspire',model.available_actions('player'))
        self.assertEqual(model.command_actions('lucan'),['attack','skills','guard','flee'])
        for skill,cost in (('inspire',5),('bolster',5),('provoke',8)):
            before=model.combatant('lucan').mp
            self.cast(model,skill)
            self.assertEqual(model.combatant('lucan').mp,before-cost)
        model.combatant('lucan').mp=4
        self.ready(model)
        before=(model.combatant('lucan').mp,deepcopy(model.combatant('lucan').buffs))
        self.assertFalse(model.choose_action('inspire'))
        self.assertEqual((model.combatant('lucan').mp,model.combatant('lucan').buffs),before)

    def test_buffs_use_recipient_turns_and_cast_does_not_consume_casters_new_turn(self):
        model=self.model()
        originals=[deepcopy(member.attributes) for member in model.party]
        self.cast(model,'inspire')
        self.assertTrue(all(member.buffs=={'inspire':5} for member in model.party))
        for i in range(4):
            self.cast(model,'guard','player')
            self.assertEqual(model.player.buffs['inspire'],4-i)
        self.assertEqual(model.combatant('mira').buffs['inspire'],5)
        self.assertEqual(model.combatant('lucan').buffs['inspire'],5)
        expected=physical_damage(model.player,model.enemy,1,variance_percent=100)
        strike=self.cast(model,'attack','player')
        self.assertEqual(strike.damage,expected)
        self.assertFalse(model.player.buffs)
        self.assertEqual([member.attributes for member in model.party],originals)

    def test_refresh_does_not_stack_and_both_buffs_coexist_with_caps(self):
        model=self.model()
        model.player.attributes['str']=11
        model.player.attributes['def']=900
        self.cast(model,'inspire')
        self.assertEqual(model.player.value('str'),16)
        self.cast(model,'guard','player')
        self.cast(model,'inspire')
        self.assertEqual(model.player.buffs['inspire'],5)
        self.assertEqual(model.player.value('str'),16)
        self.cast(model,'bolster')
        self.assertEqual(model.player.value('def'),999)
        self.assertEqual(model.player.attributes['def'],900)
        self.assertEqual(model.combatant('lucan').buffs,{'inspire':4,'bolster':5})

    def test_bolster_reduces_physical_hits_and_all_buffs_clear_on_ko_and_result(self):
        model=self.model()
        self.cast(model,'bolster')
        expected=physical_damage(model.enemy,model.player,.6,variance_percent=100)
        hit=self.enemy_turn(model)
        self.assertEqual(hit.target,'player')
        self.assertEqual(hit.damage,expected)
        model.player.hp=0
        model.update(0)
        self.assertFalse(model.player.buffs)
        model.player.hp=100
        model._result('fled')
        self.assertTrue(all(not member.buffs for member in model.party))

    def test_provoke_redirects_five_enemy_actions_then_expires(self):
        model=self.model()
        self.cast(model,'provoke')
        for remaining in range(4,-1,-1):
            action=self.enemy_turn(model)
            self.assertEqual(action.target,'lucan')
            self.assertEqual(model._enemy_states['enemy'].provoke_turns,remaining)
        self.assertFalse(model.enemy_provocations)
        self.assertEqual(self.enemy_turn(model).target,'player')

    def test_boss_and_miniboss_provoke_is_rejected_without_spending_resources(self):
        for enemy,level in (('vespermaw',7),('embravyr',4),('nivareth',4),('ridgeback_tusker',1)):
            with self.subTest(enemy=enemy):
                model=self.model(enemy,level)
                self.ready(model)
                lucan=model.combatant('lucan');before=(lucan.mp,lucan.atb)
                self.assertIn('immune',model.action_reason('provoke'))
                self.assertFalse(model.choose_action('provoke'))
                self.assertEqual((lucan.mp,lucan.atb),before)
                self.assertFalse(model.enemy_provocations)

    def test_provoke_ko_and_battle_result_clear_forced_targeting(self):
        model=self.model()
        self.cast(model,'provoke')
        model.combatant('lucan').hp=0
        model.update(0)
        self.assertFalse(model.enemy_provocations)
        self.assertEqual(self.enemy_turn(model).target,'player')
        model.combatant('lucan').hp=100
        self.cast(model,'provoke')
        model._result('victory')
        self.assertFalse(model.enemy_provocations)

    def test_prepared_single_target_spell_gets_new_warning_for_lucan(self):
        model=self.model('veylume',3)
        # Advance to a preparation naturally, retaining the actual action bank.
        for _ in range(6):
            action=self.enemy_turn(model)
            if action.kind=='prepare':break
        else:self.fail('Veylume never prepared a spell')
        model.drain_events()
        self.cast(model,'provoke')
        self.assertEqual(model.telegraphed_target,'lucan')
        warnings=[event for event in model.drain_events() if event['type']=='telegraph']
        self.assertEqual(len(warnings),1)
        self.assertEqual(warnings[0]['target'],'lucan')
        spell=self.enemy_turn(model)
        self.assertEqual(spell.target,'lucan')
        self.assertEqual(model._enemy_states['enemy'].provoke_turns,4)

    def group(self):
        sample=self.model()
        members=[{'identifier':member.identifier,'name':member.name,
                  'attributes':deepcopy(member.attributes),'hp':member.hp,'mp':member.mp,
                  'attack':'bolt_shot' if member.identifier=='mira' else 'attack'}
                 for member in sample.party]
        return BattleModel.from_bestiary_group(CharacterAttributes(),
            [{'enemy_id':'cave_bat','level':2},{'enemy_id':'lithrusk','level':2}],
            party_members=members,guest_abilities={'lucan':LUCAN_SKILLS},
            initial_atb=False,rng=FixedVariance())

    def test_each_enemy_counts_its_own_turns_and_party_wide_attacks_stay_party_wide(self):
        model=self.group()
        self.cast(model,'provoke')
        model.actions['cave_bat_bite']['target']='all_opponents'
        action=self.enemy_turn(model)
        self.assertEqual(action.targets,('player','mira','lucan'))
        self.assertEqual(action.target,'all_opponents')
        self.assertEqual(model.enemy_provocations['enemy']['turns'],4)
        self.assertEqual(model.enemy_provocations['enemy_2']['turns'],5)
        self.cast(model,'provoke')
        self.assertTrue(all(record['turns']==5 for record in model.enemy_provocations.values()))

    def test_mixed_eligible_and_immune_enemies_receive_truthful_status_events(self):
        model=self.group()
        # A future mixed formation can contain an immune tier. The actual
        # solo story bosses are independently checked through the Bestiary.
        model.enemy_records['enemy_2']['metadata']['tier']='boss'
        model.drain_events()
        action=self.cast(model,'provoke')
        self.assertEqual(action.targets,('enemy',))
        self.assertEqual(set(model.enemy_provocations),{'enemy'})
        events=model.drain_events()
        self.assertTrue(any(event['type']=='provoke_immune'
                            and event['target']=='enemy_2' for event in events))

    def test_changed_marked_target_gets_its_own_response_opportunity(self):
        model=self.model('vespermaw',7)
        # Exercise a future susceptible normal enemy with the existing held
        # strike/response mechanism; actual Vespermaw remains immune above.
        model.enemy_records['enemy']['metadata']['tier']='normal'
        state=model._enemy_states['enemy']
        state.action_index=2
        self.enemy_turn(model)
        self.assertNotEqual(state.telegraphed_target,'lucan')
        self.cast(model,'provoke')
        self.assertEqual(state.telegraphed_target,'lucan')
        self.assertEqual(state.response_actions,0)
        self.assertTrue(model._enemy_response_pending('enemy'))
        self.cast(model,'guard')
        self.assertFalse(model._enemy_response_pending('enemy'))
        self.assertEqual(self.enemy_turn(model).target,'lucan')

    def test_provoker_ko_reissues_prepared_normal_spell_warning(self):
        model=self.model('veylume',3)
        self.cast(model,'provoke')
        for _ in range(6):
            if self.enemy_turn(model).kind=='prepare':break
        self.assertEqual(model.telegraphed_target,'lucan')
        model.drain_events()
        model.combatant('lucan').hp=0
        model.update(0)
        warnings=[event for event in model.drain_events() if event['type']=='telegraph']
        self.assertEqual(len(warnings),1)
        self.assertNotEqual(warnings[0]['target'],'lucan')
        self.assertFalse(model.enemy_provocations)


if __name__=='__main__':unittest.main()
