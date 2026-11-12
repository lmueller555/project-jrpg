"""Guest support commands use production menus, gestures and status feedback."""
import os
from types import SimpleNamespace
import unittest

os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
import pygame

from audio_settings import AudioSettings
from battle_model import BattleModel, LUCAN_SKILLS
from battle_scene import BattleScene
from character_attributes import CharacterAttributes
from inventory import Inventory
from leveling import character_stats
from ui_style import UIStyle


class LucanSkillSceneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):pygame.init()

    @classmethod
    def tearDownClass(cls):pygame.quit()

    def scene(self, size=(960,640), text=1, enemy='cave_bat'):
        game=SimpleNamespace(window=pygame.display.set_mode(size),
            ui_surface=pygame.Surface(size),audio=AudioSettings(),inventory=Inventory())
        game.audio.set_effects(0);game.audio.set_text_scale(text)
        game.ui=UIStyle(game)
        game.to_canvas=lambda point:(point[0]*480/size[0],point[1]*320/size[1])
        members=[]
        for key in ('player','mira','lucan'):
            stats=character_stats('caelan' if key=='player' else key,5)
            members.append({'identifier':key,'name':'Caelan' if key=='player' else key.title(),
                'attributes':stats,'hp':stats['hp'],'mp':stats['mp'],
                'attack':'bolt_shot' if key=='mira' else 'attack'})
        model=BattleModel.from_bestiary(CharacterAttributes(),enemy,7 if enemy=='vespermaw' else 2,
            party_members=members,guest_abilities={'lucan':LUCAN_SKILLS},weapon_equipped=True)
        scene=BattleScene(game,model,battlefield='cave_echo_chamber' if enemy=='vespermaw' else 'cave_outer')
        canvas=pygame.Surface((480,320))
        scene.draw(canvas,game.ui_surface)
        return scene,canvas,game

    def ready(self,scene):
        for actor in (*scene.model.party,*scene.model.enemies):actor.atb=0
        scene.model.combatant('lucan').atb=1
        scene.update(0)

    def choose(self,scene,command):
        scene.selected=scene._command_actions().index(command)
        scene._confirm()

    def test_guest_has_skills_items_guard_and_flee_and_costed_skill_labels(self):
        scene,canvas,game=self.scene()
        self.ready(scene)
        self.assertTrue(set(('attack','skills','items','guard','flee'))<=set(scene._command_actions()))
        self.choose(scene,'skills')
        self.assertTrue(set(LUCAN_SKILLS)<=set(scene._command_actions()))
        for key,cost in (('inspire',5),('bolster',5),('provoke',8)):
            self.assertIn(str(cost)+' MP',scene._command_label(key))
        scene.draw(canvas,game.ui_surface)
        self.assertFalse(scene.gear_enabled)
        self.assertFalse(scene.rig_enabled)

    def test_support_uses_registered_gesture_and_shows_recipient_turn_badges(self):
        for size,text in (((960,640),1),((480,320),1.5)):
            for skill,pose in (('inspire','technique'),('bolster','guard')):
                with self.subTest(size=size,skill=skill):
                    scene,canvas,game=self.scene(size,text)
                    self.ready(scene);self.choose(scene,'skills');self.choose(scene,skill)
                    action=scene.model.current_action
                    self.assertEqual(scene._pose('lucan')[0],pose)
                    scene.update(action.impact_at-.01)
                    self.assertTrue(all(not member.buffs for member in scene.model.party))
                    scene.update(.01)
                    scene.draw(canvas,game.ui_surface)
                    self.assertEqual(set(scene.support_badges),{'player','mira','lucan'})
                    for member in scene.model.party:self.assertEqual(member.buffs[skill],5)
                    for badge in scene.support_badges.values():
                        self.assertLessEqual(badge.bottom,scene.panel_rect.top)
                        self.assertGreaterEqual(badge.left,0)
                        self.assertLessEqual(badge.right,480)
                    self.assertIn(skill.title(),scene.announcements.current['text'])

    def test_provoke_feedback_and_boss_rejection_are_truthful(self):
        scene,canvas,game=self.scene()
        self.ready(scene);self.choose(scene,'skills');self.choose(scene,'provoke')
        action=scene.model.current_action;scene.update(action.impact_at)
        scene.draw(canvas,game.ui_surface)
        self.assertEqual(scene.model.enemy_provocations['enemy']['target'],'lucan')
        self.assertIn('enemy',scene.support_badges)
        scene,canvas,game=self.scene(enemy='vespermaw')
        self.ready(scene);self.choose(scene,'skills')
        mp=scene.model.combatant('lucan').mp
        self.assertTrue(scene._command_reason('provoke'))
        self.choose(scene,'provoke')
        self.assertIsNone(scene.model.current_action)
        self.assertEqual(scene.model.combatant('lucan').mp,mp)
        self.assertFalse(scene.model.enemy_provocations)

    def test_combined_buffs_do_not_overprint_barrier_counts_at_large_text(self):
        scene,canvas,game=self.scene((480,320),1.5)
        for member in scene.model.party:member.buffs={'inspire':5,'bolster':4}
        scene.model.combatant('mira').barrier=20
        scene.model.combatant('mira').barrier_turns=2
        scene.draw(canvas,game.ui_surface)
        badges=list(scene.support_badges.values())
        for index,badge in enumerate(badges):
            self.assertFalse(any(badge.colliderect(other) for other in badges[index+1:]))
            self.assertFalse(any(badge.colliderect(other) for other in scene.barrier_badges.values()))


if __name__=='__main__':unittest.main()
