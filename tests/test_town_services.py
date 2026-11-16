"""Atomic prices, real keeper input, shared rest and resumable service results."""
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
import pygame
from economy import Wallet, purchase, MAX_GOLD
from inventory import Inventory, MAX_QUANTITY


class Transactions(unittest.TestCase):
    def test_free_and_paid_purchases_update_both_resources(self):
        inventory=Inventory();wallet=Wallet()
        self.assertTrue(purchase(inventory,wallet,{'potion':0},'potion',3)[0])
        self.assertEqual((inventory.quantity('potion'),wallet.gold),(3,0))
        wallet.gold=10
        self.assertTrue(purchase(inventory,wallet,{'ether':3},'ether',2)[0])
        self.assertEqual((inventory.quantity('ether'),wallet.gold),(2,4))

    def test_invalid_purchases_never_mutate_either_resource(self):
        inventory=Inventory.new_journey();wallet=Wallet(10)
        cases=[({'potion':11},'potion',1),({'potion':0},'potion',0),
               ({'potion':0},'potion',-1),({'potion':0},'potion',True),
               ({'potion':0},'potion',1.5),({'potion':-1},'potion',1),
               ({'potion':True},'potion',1),({'potion':0},'unknown',1),
               ({'halden_medicine':0},'halden_medicine',1),
               ({'caelan_gearblade':0},'caelan_gearblade',1)]
        before=inventory.to_dict()
        for stock,key,qty in cases:
            with self.subTest(stock=stock,key=key,qty=qty):
                self.assertFalse(purchase(inventory,wallet,stock,key,qty)[0])
                self.assertEqual(inventory.to_dict(),before);self.assertEqual(wallet.gold,10)

    def test_capacity_is_shared_with_every_inventory_grant(self):
        inventory=Inventory();wallet=Wallet(8);inventory.add('potion',MAX_QUANTITY-1)
        self.assertFalse(purchase(inventory,wallet,{'potion':2},'potion',2)[0])
        self.assertEqual(wallet.gold,8)
        self.assertTrue(purchase(inventory,wallet,{'potion':2},'potion',1)[0])
        self.assertFalse(inventory.add('potion'))
        self.assertEqual((inventory.quantity('potion'),wallet.gold),(MAX_QUANTITY,6))

    def test_wallet_rejects_bad_balances_and_charges_atomically(self):
        for value in (True,-1,MAX_GOLD+1,1.0,None):
            with self.assertRaises(ValueError):Wallet(value)
        wallet=Wallet(7)
        for amount in (-1,True,8):self.assertFalse(wallet.spend(amount));self.assertEqual(wallet.gold,7)
        self.assertTrue(wallet.spend(0));self.assertTrue(wallet.spend(7));self.assertEqual(wallet.gold,0)


class TownServicesGameplay(unittest.TestCase):
    def setUp(self):
        from main import Game
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        p=Path(self.temp.name)
        self.g=Game(fullscreen=False,window_size=(960,640),start_on_title=True,
                    save_path=p/'save.json',settings_path=p/'settings.json')
        self.addCleanup(self.g.music.stop);self.addCleanup(pygame.quit)
        g=self.g;g.on_title=False;g.opening.stage='disabled';g.opening_fade=g.transfer_cooldown=0
        g.audio.set_music(0);g.audio.set_effects(0)
        self.station('item_shop',(216,188));pygame.event.clear()

    def station(self,scene,position):
        g=self.g;g.world=g._scene_by_id(scene);g.player.position.update(position)
        g.player.facing='back';g.opening_fade=g.transfer_cooldown=0
        g.saves.scene=scene;g.saves.pending_scene=None

    def key(self,key):
        self.g.handle_events([pygame.event.Event(pygame.KEYDOWN,key=key,repeat=False),
                              pygame.event.Event(pygame.KEYUP,key=key)])

    def choose(self,action):
        g=self.g
        for _ in range(24):
            if g.social.choosing:break
            self.key(pygame.K_SPACE)
        self.assertTrue(g.social.choosing);g.draw()
        index=next(i for i,r in enumerate(g.social.choice_options) if r['action']==action)
        rect=g.social.choice_rects[index];pos=(round(rect.centerx*2),round(rect.centery*2))
        g.handle_events([pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=pos),
                         pygame.event.Event(pygame.MOUSEBUTTONUP,button=1,pos=pos)])

    def open_shop(self):
        self.assertIn('shopkeeper',self.g.services.interaction_hint())
        self.key(pygame.K_e);self.assertEqual(self.g.social.script_identifier,'item_shop_offer')
        self.choose('buy');self.assertTrue(self.g.services.is_open)

    def finish_dialogue(self):
        for _ in range(24):
            if not self.g.social.active:return
            self.key(pygame.K_SPACE)
        self.fail('Dialogue did not finish')

    def test_every_service_is_free_and_gold_is_zero_without_a_grant(self):
        g=self.g
        self.assertEqual(g.wallet.gold,0)
        self.assertEqual(set(g.services.data['shop']['stock']),{'potion','ether','revival_salts','smoke_bomb','rest_kit'})
        self.assertEqual(set(g.services.data['shop']['stock'].values()),{0})
        self.assertEqual(g.services.data['inn']['price'],0)

    def test_real_keyboard_quantity_confirmation_and_session_autosave(self):
        g=self.g;self.open_shop();before=g.inventory.quantity('potion')
        self.key(pygame.K_RIGHT);self.key(pygame.K_RETURN)
        self.assertEqual(g.inventory.quantity('potion'),before)
        self.key(pygame.K_RETURN)
        self.assertEqual(g.inventory.quantity('potion'),before+2);self.assertEqual(g.wallet.gold,0)
        self.assertEqual(g.saves.pending_services,[])
        g.saves.update(.1);self.assertEqual(g.saves.library.autos(g.saves.campaign),[])
        self.key(pygame.K_ESCAPE);self.assertFalse(g.services.is_open)
        g.saves.scene_deadline=60;g.update(.1,(0,0),False)
        autos=g.saves.library.autos(g.saves.campaign)
        self.assertEqual(len(autos),1);self.assertEqual(autos[0]['metadata']['reason'],'shop')
        self.assertEqual(autos[0]['payload']['inventory']['items']['potion'],before+2)
        self.assertEqual(autos[0]['payload']['gold'],0)
        g.update(.1,(0,0),False);self.assertEqual(len(g.saves.library.autos(g.saves.campaign)),1)

    def test_cancel_buy_and_leave_browsing_do_not_change_resources_or_request_saves(self):
        g=self.g;before=g.inventory.to_dict();self.open_shop()
        self.key(pygame.K_RETURN);self.key(pygame.K_ESCAPE)
        self.assertTrue(g.services.is_open);self.assertFalse(g.services.shop.confirming)
        self.key(pygame.K_ESCAPE)
        self.assertFalse(g.pause.is_open);self.assertEqual(g.inventory.to_dict(),before)
        self.assertEqual(g.saves.pending_services,[])

    def test_shop_freezes_movement_and_conflicting_menus_and_focus_blocks_buy(self):
        g=self.g;self.open_shop();before=tuple(g.player.position);clock=g.elapsed_ms
        g.update(.5,(1,0),True)
        self.assertEqual(tuple(g.player.position),before);self.assertEqual(g.elapsed_ms,clock)
        self.key(pygame.K_i);self.key(pygame.K_j);self.key(pygame.K_m)
        self.assertFalse(g.inventory_ui.is_open or g.map_open or g.quest_ui.journal_open)
        self.assertFalse(g.enter(g.world.doors[0]))
        g._music_focused=False;self.key(pygame.K_RETURN)
        self.assertFalse(g.services.shop.confirming)

    def test_mouse_purchase_confirmation_and_cancel_use_actual_button_bounds(self):
        g=self.g;self.open_shop();shop=g.services.shop
        def click(rect):
            point=(rect.centerx*2,rect.centery*2)
            g.handle_events([pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=point),
                             pygame.event.Event(pygame.MOUSEBUTTONUP,button=1,pos=point)])
        before=g.inventory.quantity('potion')
        click(shop.plus_rect);self.assertEqual(shop.quantity,2)
        click(shop.buy_rect);click(shop.no_rect)
        self.assertEqual(g.inventory.quantity('potion'),before)
        click(shop.buy_rect);click(shop.yes_rect)
        self.assertEqual(g.inventory.quantity('potion'),before+2)
        click(shop.leave_rect);self.assertEqual(len(g.saves.pending_services),1)

    def test_failed_full_stack_purchase_changes_nothing_and_requests_no_service_save(self):
        g=self.g;g.inventory.add('potion',MAX_QUANTITY-g.inventory.quantity('potion'))
        self.open_shop();self.key(pygame.K_RETURN);self.key(pygame.K_RETURN)
        self.assertIn('cannot hold',g.services.shop.notice)
        self.assertEqual(g.inventory.quantity('potion'),MAX_QUANTITY)
        self.key(pygame.K_ESCAPE);self.assertEqual(g.saves.pending_services,[])

    def test_multiple_purchases_refresh_owned_counts_and_publish_one_session(self):
        g=self.g;self.open_shop();shop=g.services.shop
        before=g.inventory.quantity('ether');self.key(pygame.K_DOWN)
        for _ in range(3):self.key(pygame.K_RETURN);self.key(pygame.K_RETURN)
        self.assertEqual(g.inventory.quantity('ether'),before+3)
        self.key(pygame.K_ESCAPE);self.assertEqual(len(g.saves.pending_services),1)

    def test_gold_round_trip_legacy_default_and_bad_save_rejection(self):
        g=self.g;g.wallet.gold=47;snapshot=g.journey_snapshot()
        self.assertEqual(snapshot['gold'],47);self.assertTrue(g.save_progress())
        for value in (True,-1,MAX_GOLD+1,None,'0',0.0):
            bad=deepcopy(snapshot);bad['gold']=value
            self.assertIsNone(g._validate_journey(bad))
        self.assertIsNotNone(g._validate_journey(deepcopy(snapshot)))
        g.saved_journey=snapshot;self.assertTrue(g.begin_journey(True));self.assertEqual(g.wallet.gold,47)
        legacy=deepcopy(snapshot);legacy.pop('gold');self.assertIsNotNone(g._validate_journey(legacy))
        g.saved_journey=legacy;self.assertTrue(g.begin_journey(True));self.assertEqual(g.wallet.gold,0)

    def test_autosave_load_restores_purchase_and_closes_service_ui(self):
        g=self.g;self.open_shop();self.key(pygame.K_RETURN);self.key(pygame.K_RETURN)
        bought=g.inventory.quantity('potion');self.key(pygame.K_ESCAPE);g.update(.1,(0,0),False)
        row=g.saves.latest('auto');self.assertIsNotNone(row)
        g.inventory.remove('potion');self.open_shop()
        self.assertTrue(g.saves.load(row));self.assertFalse(g.services.is_open)
        self.assertEqual(g.inventory.quantity('potion'),bought);self.assertEqual(g.world.data['id'],'item_shop')

    def test_service_autosave_failure_retries_without_repeating_purchase(self):
        g=self.g;self.open_shop();self.key(pygame.K_RETURN);self.key(pygame.K_RETURN)
        bought=g.inventory.quantity('potion');self.key(pygame.K_ESCAPE)
        with patch.object(g.saves.library,'write_auto',return_value=False):g.saves.update(.1)
        self.assertEqual(len(g.saves.pending_services),1);self.assertEqual(g.inventory.quantity('potion'),bought)
        g.saves.update(11);self.assertEqual(g.saves.pending_services,[])
        self.assertEqual(g.inventory.quantity('potion'),bought)
        self.assertEqual(len(g.saves.library.autos(g.saves.campaign)),1)

    def test_innkeeper_and_guest_bed_share_confirmed_zero_cost_rest(self):
        g=self.g
        for via_keeper,pos in ((True,(168,160)),(False,(96,150))):
            self.station('inn',pos);g.attributes.set_current(hp=7,mp=1)
            self.key(pygame.K_e);self.assertEqual(g.social.script_identifier,'inn_rest_offer')
            self.assertIn('0 gold',g.social.conversation['choice_prompt'])
            self.choose('rest');self.assertEqual(g.attributes.current_hp,g.attributes.value('hp'))
            self.assertEqual(g.attributes.current_mp,g.attributes.value('mp'));self.assertEqual(g.wallet.gold,0)
            self.assertEqual(len(g.saves.pending_services),1)
            self.finish_dialogue();g.update(.8,(0,0),False)
            self.assertEqual(g.saves.pending_services,[])
            self.assertEqual(g.saves.library.autos(g.saves.campaign)[0]['metadata']['reason'],'inn')

    def test_inn_decline_and_walk_away_do_not_heal_or_charge(self):
        g=self.g;self.station('inn',(168,160));g.attributes.set_current(hp=7,mp=1)
        self.key(pygame.K_e);self.choose('leave')
        self.assertEqual(g.attributes.current_hp,7);self.assertEqual(g.saves.pending_services,[])
        self.key(pygame.K_e);g.player.position.update(216,294)
        self.assertFalse(g.services.nearby('inn'))
        g.bed_rest._choose('rest',g.services.rest_profile(),lambda:g.services.nearby('inn'))
        self.assertEqual(g.attributes.current_hp,7)

    def test_paid_inn_rejects_insufficient_gold_and_failed_save_rolls_back_charge_and_heal(self):
        g=self.g;self.station('inn',(168,160));g.attributes.set_current(hp=7,mp=1)
        g.services.data['inn']['price']=5
        self.key(pygame.K_e);self.choose('rest')
        self.assertEqual(g.attributes.current_hp,7);self.assertEqual(g.wallet.gold,0)
        self.finish_dialogue();g.wallet.gold=8
        self.key(pygame.K_e)
        with patch.object(g,'save_progress',return_value=False):self.choose('rest')
        self.assertEqual(g.attributes.current_hp,7);self.assertEqual(g.attributes.current_mp,1)
        self.assertEqual(g.wallet.gold,8);self.assertEqual(g.saves.pending_services,[])
        self.assertEqual(g.social.script_identifier,'inn_rest_retry')
        self.choose('rest');self.assertEqual(g.wallet.gold,3)
        self.assertEqual(g.attributes.current_hp,g.attributes.value('hp'))

    def test_keeper_requires_front_counter_approach_and_available_exploration(self):
        g=self.g
        for scene,position in [('item_shop',(216,294)),('item_shop',(216,110)),('inn',(168,90))]:
            self.station(scene,position);self.assertFalse(g.services.interact())
        self.station('item_shop',(216,188));g.opening_fade=.2
        self.assertFalse(g.services.interact())

    def test_menu_renders_at_all_text_sizes_including_long_owned_counts(self):
        g=self.g;self.open_shop();g.inventory.add('potion',MAX_QUANTITY-g.inventory.quantity('potion'))
        for scale in (1.,1.25,1.5):
            g.audio.set_text_scale(scale);g.draw()
            self.assertEqual(g.ui_surface.get_size(),(960,640))
            g.services.shop.confirming=True;g.draw();g.services.shop.confirming=False

if __name__=='__main__':unittest.main()
