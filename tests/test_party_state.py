"""Party selection preserves ownership, story constraints and resources."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
import unittest

from character_attributes import CharacterAttributes
from party_state import MAX_PARTY, PartyState


ROOT = Path(__file__).resolve().parents[1]


class PartyStateTests(unittest.TestCase):
    def setUp(self):
        self.caelan = CharacterAttributes()
        self.party = PartyState(self.caelan)

    def recruit_all(self):
        for identifier in ('mira','lucan','rhea','edran'):
            self.assertTrue(self.party.recruit(identifier))

    def test_new_game_only_reveals_caelan_and_keeps_his_resource_alias(self):
        self.assertIs(self.party.characters['caelan'], self.caelan)
        self.assertEqual(tuple(self.party.members), ('caelan',))
        self.assertEqual(self.party.active_ids, ('caelan',))
        self.assertEqual(self.party.required_ids, ('caelan',))
        self.assertEqual(self.party.known_ids, ('caelan','mira','lucan','rhea','edran'))
        self.caelan.set_current(hp=12,mp=1)
        self.assertEqual(self.party.battle_members()[0]['hp'],12)
        for definition in self.party.definitions.values():
            self.assertTrue((ROOT/definition['portrait']).is_file())

    def test_mira_uses_existing_combat_ratings_without_global_catalog_changes(self):
        guest=json.loads((ROOT/'assets/combat/guests.json').read_text())['guests']['mira']
        mira=self.party.characters['mira']
        self.assertEqual(mira.to_dict()['attributes'],guest['attributes'])
        self.assertEqual((mira.current_hp,mira.current_mp),(150,30))
        self.assertEqual(set(CharacterAttributes().catalog['characters']), {'caelan'})

    def test_recruitment_autofills_only_empty_slots_then_keeps_reserves(self):
        self.recruit_all()
        self.assertEqual(MAX_PARTY,3)
        self.assertEqual(self.party.active_ids,('caelan','mira','lucan'))
        self.assertEqual(self.party.reserve_ids,('rhea','edran'))
        self.assertFalse(self.party.recruit('mira',temporary=True))
        self.assertFalse(self.party.members['mira']['temporary'])
        visible=self.party.members
        visible['caelan']['available']=False
        self.assertTrue(self.party.members['caelan']['available'])

    def test_reserving_and_reselecting_never_heals_or_revives(self):
        self.recruit_all()
        self.party.characters['mira'].set_current(hp=0,mp=2)
        self.party.characters['lucan'].set_current(hp=8,mp=0)
        self.assertTrue(self.party.select(('caelan','rhea','edran')))
        self.assertTrue(self.party.select(('caelan','mira','lucan')))
        self.assertEqual((self.party.attributes('mira').current_hp,self.party.attributes('mira').current_mp),(0,2))
        self.assertEqual((self.party.attributes('lucan').current_hp,self.party.attributes('lucan').current_mp),(8,0))

    def test_selection_limits_and_availability_rejections_are_atomic(self):
        self.recruit_all()
        self.assertTrue(self.party.set_available('rhea',False,'Away on a story errand.'))
        before=self.party.to_dict()
        for selection in ((),('mira',),('caelan','caelan'),('caelan','unknown'),
                          ('caelan','mira','lucan','edran'),('mira','caelan'),
                          ('caelan','rhea'),['caelan',[]],None,'caelan'):
            with self.subTest(selection=selection):
                self.assertFalse(self.party.select(selection))
                self.assertEqual(self.party.to_dict(),before)
        self.assertIn('story errand', self.party.selection_reason(('caelan','rhea')))
        self.assertTrue(self.party.select(('caelan',)))

    def test_unrecruited_character_is_not_selectable(self):
        before=self.party.to_dict()
        self.assertFalse(self.party.select(('caelan','lucan')))
        self.assertFalse(self.party.set_available('mira',True))
        self.assertEqual(self.party.to_dict(),before)

    def test_departure_removes_active_member_without_erasing_resources(self):
        self.party.recruit('mira',temporary=True)
        self.party.characters['mira'].set_current(hp=77,mp=9)
        self.assertTrue(self.party.set_available('mira',False,'Working in Eldenmere.'))
        self.assertEqual(self.party.active_ids,('caelan',))
        self.assertTrue(self.party.members['mira']['temporary'])
        self.assertTrue(self.party.set_available('mira',True))
        self.assertEqual(self.party.active_ids,('caelan',))
        self.assertTrue(self.party.select(('caelan','mira')))
        self.assertEqual((self.party.attributes('mira').current_hp,self.party.attributes('mira').current_mp),(77,9))

    def test_story_requirements_take_slots_and_locked_recruits_stay_reserve(self):
        self.recruit_all()
        self.party.select(('caelan','lucan','rhea'))
        self.assertTrue(self.party.begin_event('mill',required=('mira',),reason='Mira is needed for the repair.',locked=True))
        self.assertEqual(self.party.required_ids,('caelan','mira'))
        self.assertEqual(self.party.active_ids,('caelan','mira','lucan'))
        self.assertIn('repair',self.party.selection_change_reason())
        self.assertFalse(self.party.select(('caelan','mira','edran')))
        self.assertFalse(self.party.set_available('mira',False,'Elsewhere.'))
        self.assertEqual(self.party.previous_formation(),('caelan','lucan','rhea'))
        self.assertTrue(self.party.end_event('mill',restore=True))
        self.assertEqual(self.party.active_ids,('caelan','lucan','rhea'))

    def test_event_unavailability_is_overlay_and_does_not_undo_story_changes(self):
        self.recruit_all()
        self.assertTrue(self.party.begin_event('cave',unavailable=('mira',),reason='Waiting outside.'))
        self.assertFalse(self.party.members['mira']['available'])
        self.assertTrue(self.party.to_dict()['members']['mira']['available'])
        self.assertTrue(self.party.set_available('mira',False,'Returned to the workshop.'))
        self.assertTrue(self.party.select(('caelan','lucan','edran')))
        self.assertTrue(self.party.end_event('cave'))
        self.assertEqual(self.party.active_ids,('caelan','lucan','edran'))
        self.assertFalse(self.party.members['mira']['available'])
        self.assertEqual(self.party.members['mira']['reason'],'Returned to the workshop.')

    def test_event_return_does_not_silently_displace_a_new_selection(self):
        self.recruit_all()
        self.assertTrue(self.party.begin_event('cave',unavailable=('mira',)))
        self.assertTrue(self.party.select(('caelan','lucan','rhea')))
        self.assertTrue(self.party.end_event('cave'))
        self.assertTrue(self.party.members['mira']['available'])
        self.assertEqual(self.party.active_ids,('caelan','lucan','rhea'))

    def test_event_constraints_reject_invalid_or_overlapping_events_without_mutation(self):
        self.recruit_all()
        before=self.party.to_dict()
        for kwargs in ({'required':('mira','lucan','rhea')},
                       {'required':('mira',),'unavailable':('mira',)},
                       {'unavailable':('caelan',)}, {'required':('unknown',)},
                       {'required':('mira','mira')}, {'locked':True,'selection_pending':True}):
            with self.subTest(kwargs=kwargs):
                self.assertFalse(self.party.begin_event('bad',**kwargs))
                self.assertEqual(self.party.to_dict(),before)
        self.assertTrue(self.party.begin_event('cave'))
        current=self.party.to_dict()
        self.assertFalse(self.party.begin_event('boss'))
        self.assertFalse(self.party.end_event('boss'))
        self.assertEqual(self.party.to_dict(),current)

    def test_pending_event_selection_survives_load_and_confirms_its_lock(self):
        self.recruit_all()
        self.assertTrue(self.party.begin_event('boss',required=('mira',),
            selection_pending=True,selection_title='Prepare for the crossing',lock_after=True))
        data=self.party.to_dict()
        loaded=PartyState(CharacterAttributes())
        self.assertTrue(loaded.restore(data))
        self.assertEqual(loaded.current_event_id,'boss')
        self.assertEqual(loaded.pending_selection,{'event_id':'boss','title':'Prepare for the crossing','lock_after':True})
        self.assertFalse(loaded.locked)
        self.assertTrue(loaded.select(('caelan','mira','rhea')))
        self.assertTrue(loaded.confirm_event('boss'))
        self.assertTrue(loaded.locked)
        self.assertIsNone(loaded.pending_selection)
        again=PartyState(CharacterAttributes())
        self.assertTrue(again.restore(loaded.to_dict()))
        self.assertTrue(again.locked)
        self.assertEqual(again.active_ids,('caelan','mira','rhea'))

    def test_all_ko_party_can_be_inspected_but_cannot_begin_a_fight(self):
        self.party.recruit('mira')
        self.caelan.set_current(hp=0)
        self.party.characters['mira'].set_current(hp=0)
        self.assertEqual(self.party.selection_reason(self.party.active_ids),'')
        self.assertIn('able to fight',self.party.battle_reason())

    def test_battle_specs_are_copies_and_settlement_is_atomic_for_all_active_members(self):
        self.recruit_all()
        self.party.attributes('rhea').set_current(hp=28,mp=7)
        specs=self.party.battle_members()
        self.assertEqual(tuple(s['identifier'] for s in specs),('player','mira','lucan'))
        specs[0]['attributes']['str']=99
        self.assertEqual(self.caelan.value('str'),10)
        combatants=[SimpleNamespace(identifier='player',hp=91,mp=12),
                    SimpleNamespace(identifier='mira',hp=0,mp=4),
                    SimpleNamespace(identifier='lucan',hp=38,mp=1)]
        self.assertTrue(self.party.apply_battle(SimpleNamespace(party=combatants)))
        self.assertEqual((self.caelan.current_hp,self.caelan.current_mp),(91,12))
        self.assertEqual(self.party.attributes('mira').current_hp,0)
        self.assertEqual((self.party.attributes('rhea').current_hp,self.party.attributes('rhea').current_mp),(28,7))
        before=self.party.to_dict()
        combatants[0].hp=42
        combatants[2].hp=999999
        self.assertFalse(self.party.apply_battle(SimpleNamespace(party=combatants)))
        self.assertEqual(self.party.to_dict(),before)

    def test_roundtrip_preserves_roster_resources_attributes_and_all_object_aliases(self):
        self.recruit_all()
        self.party.set_available('mira',False,'At the workshop.')
        self.party.select(('caelan','lucan','edran'))
        self.caelan.set_current(hp=83,mp=4)
        self.party.attributes('edran').set_current(hp=0,mp=1)
        data=self.party.to_dict()
        aliases=dict(self.party.characters)
        self.assertTrue(self.party.restore(data))
        self.assertEqual(self.party.to_dict(),data)
        for identifier,attributes in aliases.items():self.assertIs(self.party.characters[identifier],attributes)
        other=PartyState(CharacterAttributes())
        self.assertTrue(other.restore(data))
        self.assertEqual(other.to_dict(),data)
        data['members']['lucan']['available']=False
        self.assertTrue(other.members['lucan']['available'])

    def test_restore_preserves_existing_external_attribute_modifiers(self):
        self.assertTrue(self.caelan.set_modifiers('equipment',{'hp':40,'str':7}))
        self.assertTrue(self.caelan.set_current(hp=175,mp=2))
        snapshot=self.party.to_dict()
        self.caelan.set_current(hp=4)
        self.assertTrue(self.party.restore(snapshot))
        self.assertEqual((self.caelan.current_hp,self.caelan.value('hp'),self.caelan.value('str')),(175,180,17))
        self.assertEqual(self.caelan._modifiers,{'equipment':{'hp':40,'str':7}})

    def test_malformed_save_is_rejected_atomically(self):
        self.recruit_all()
        self.caelan.set_current(hp=64,mp=3)
        before=self.party.to_dict()
        variants=[]
        for key in before:
            missing=deepcopy(before);missing.pop(key);variants.append(missing)
        for active in ([],['mira'],['caelan','caelan'],['caelan','unknown'],['caelan','mira','lucan','rhea']):
            changed=deepcopy(before);changed['active']=active;variants.append(changed)
        for field,value in (('available',1),('available',False),('temporary','yes'),('reason',None)):
            changed=deepcopy(before);changed['members']['caelan'][field]=value;variants.append(changed)
        changed=deepcopy(before);changed['characters']['mira']['current_hp']=301;variants.append(changed)
        changed=deepcopy(before);changed['characters']['mira']['attributes']['str']=True;variants.append(changed)
        changed=deepcopy(before);changed['members']['lucan']['available']=False;changed['members']['lucan']['reason']='Away';variants.append(changed)
        changed=deepcopy(before);changed['members'].pop('lucan');variants.append(changed)
        for value in (None,True,[],{},*variants):
            with self.subTest(value=value):
                self.assertFalse(self.party.restore(value))
                self.assertEqual(self.party.to_dict(),before)

    def test_invalid_mutators_do_not_throw_or_change_state(self):
        before=self.party.to_dict()
        for identifier in (None,[],{},True,'unknown'):
            with self.subTest(identifier=identifier):
                self.assertFalse(self.party.recruit(identifier))
                self.assertFalse(self.party.set_available(identifier,False,'Unavailable.'))
        self.assertFalse(self.party.set_available('caelan',False,'Elsewhere.'))
        self.assertFalse(self.party.set_event_locked('missing'))
        self.assertFalse(self.party.confirm_event('missing'))
        self.assertEqual(self.party.to_dict(),before)


if __name__ == '__main__':unittest.main()
