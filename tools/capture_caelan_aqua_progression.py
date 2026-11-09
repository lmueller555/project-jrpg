"""Photograph the production Blue-gem, Aether and Aqua progression in disposable games.

Earlier quest fixtures and the shortened encounter countdown are explicitly
recorded. All photographed poses, menus, dialogue and strikes come from Game.
Pillow only places the rendered screenshots beside review captions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'tests')]

import pygame
from PIL import Image, ImageDraw, ImageFont
from test_aqua_progression_gameplay import AquaProgressionGameplayTests
from test_mq02_spellblade_gameplay import MQ02SpellbladeGameplayTests, drive_spellblade_battle
from test_mill_battle_gameplay import click, key

OUTPUT = ROOT/'docs/reviews/caelan_aqua_progression'


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


class Review:
    def __init__(self, output):
        self.output = output
        output.mkdir(parents=True, exist_ok=True)
        self.captures = []

    def photograph(self, game, name, label):
        if any(item['file'] == name for item in self.captures):return
        game.draw()
        pygame.image.save(game.ui_surface, str(self.output/name))
        model = game.combat.model if game.combat.active else None
        action = model.current_action if model else None
        self.captures.append({'file':name, 'label':label,
            'scene':game.world.data['id'],
            'learned':sorted(game.character_abilities.known_abilities()),
            'owned_gems':list(game.character_abilities.owned_gems()),
            'action':action.action if action else None,
            'action_seconds':round(action.elapsed, 3) if action else None,
            'caelan_mp':model.player.mp if model else game.attributes.current_mp})

    def gift_and_boar(self):
        case = MQ02SpellbladeGameplayTests()
        try:
            driver = case.driver()  # Completed MQ01 fixture; MQ02 plays through real inputs.
            game = driver.g
            case.begin_gift(driver)
            for _ in range(1000):
                if game.mill_gift.shot == 'gear':break
                key(game, pygame.K_SPACE);driver.tick(.05)
            else:raise AssertionError('Gift never reached the gear close-up')
            while game.mill_gift.phase_time < 3.3:driver.tick(.05)
            for _ in range(2):key(game, pygame.K_SPACE)
            self.photograph(game, 'gift_blue.png', 'Gift: one Blue gem, three empty sockets')
            driver.read()
            assert game.character_abilities.owned_gems() == ('water',)
            case.start_battle(driver)

            def frame(current, tag, action=None):
                names = {
                    'skills_first_edge':('boar_aqua_menu.png', 'Boar: only Aqua Edge can be attempted'),
                    'resolved_aqua_edge_attempt':('boar_failed_aqua.png', 'Boar: Aqua Edge fails'),
                    'resolved_aether_edge':('boar_aether.png', 'Boar: accidental Aether Edge strikes'),
                }
                if tag in names:self.photograph(current, *names[tag])

            scene = drive_spellblade_battle(game, stop_after_discovery=True, on_frame=frame)
            actions = [item for item in scene.review_trace if item['actor'] == 'player']
            assert [item['action'] for item in actions[:3]] == ['guard', 'aqua_edge_attempt', 'aether_edge']
            assert actions[1]['damage'] == 0 and actions[2]['damage'] > 0
            assert 'aether_edge' in game.character_abilities.known_abilities()
            assert 'aqua_edge' not in game.character_abilities.known_abilities()
            return actions
        finally:case.doCleanups()

    def cave(self):
        AquaProgressionGameplayTests.setUpClass()
        case = AquaProgressionGameplayTests()
        try:
            case.setUp()
            game = case.game
            game.attributes.set_current(mp=0)  # Explicit zero-MP review fixture.
            case.enter_cave(read=False)
            key(game, pygame.K_SPACE)
            game.update(.1, (0, 0), False)
            self.photograph(game, 'cave_resonance.png', 'Cave: authored Blue-gem resonance')
            case.read()
            ticket = case.trigger()  # Saved real ticket; countdown shortened only for capture.
            model = case.load_battle()
            scene = game.combat.scene
            assert model.player.mp == 0
            assert ticket['members'] == [{'enemy_id':'cave_bat', 'level':2}]*2
            assert len(model.enemies) == 2
            for _ in range(2000):
                if scene.tutorial_active:key(game, pygame.K_SPACE)
                elif model.waiting_for_player:break
                else:game.update(.05, (0, 0), False)
            else:raise AssertionError('Cave lesson never offered its first action')
            game.draw();click(game, scene.command_rects['skills'].center)
            self.photograph(game, 'cave_aqua_0mp.png', 'First cave battle: Aqua Edge costs 0 MP')
            game.draw();click(game, scene.command_rects['aqua_edge'].center)
            key(game, pygame.K_RETURN)
            for _ in range(2000):
                action = model.current_action
                if action and action.action == 'aqua_edge' and action.elapsed >= .9:
                    self.photograph(game, 'cave_water_strike.png', 'Aqua Edge: actual blue Water strike')
                if model.aqua_edge_discovered:break
                if scene.tutorial_active:key(game, pygame.K_SPACE)
                game.update(.025, (0, 0), False)
            else:raise AssertionError('The actual Aqua Edge strike never resolved')
            assert model.player.mp == 0
            assert 'aqua_edge' in game.character_abilities.known_abilities()
            while scene.tutorial_active:
                if 'Learned Aqua Edge' in scene._tutorial_queue[0]['help']:
                    self.photograph(game, 'cave_aqua_learned.png', 'Aqua Edge learned; later battles cost 4 MP')
                    break
                key(game, pygame.K_SPACE)
            assert any(item['file'] == 'cave_aqua_learned.png' for item in self.captures)
            saved = json.loads(case.path.read_text())
            assert 'aqua_edge' in saved['character_abilities']['learned_abilities']['caelan']
            assert saved['character_attributes']['current_mp'] == 0
            assert game.cave_random_encounters.pending == ticket
            return {'ticket':ticket, 'mp_after_learning':model.player.mp,
                    'learned':sorted(game.character_abilities.known_abilities()),
                    'discovery_saved':True, 'battle_cleared':game.cave_lesson.battle_cleared}
        finally:case.doCleanups()

    def contact_sheet(self):
        sheet = Image.new('RGB', (960, ((len(self.captures)+1)//2)*350), '#132c25')
        draw = ImageDraw.Draw(sheet)
        font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 14)
        for index, capture in enumerate(self.captures):
            x, y = index%2*480, index//2*350
            draw.text((x+6, y+5), capture['label'], fill='#efd38c', font=font)
            frame = Image.open(self.output/capture['file']).convert('RGB')
            frame.thumbnail((480, 320), Image.Resampling.NEAREST)
            sheet.paste(frame, (x, y+28))
        sheet.save(self.output/'contact_sheet.png', optimize=True)

    def run(self):
        actions = self.gift_and_boar()
        cave = self.cave()
        self.contact_sheet()
        sources = ['battle_model.py', 'battle_scene.py', 'character_abilities.py',
                   'cave_lesson.py', 'world_encounters.py', 'gearblade_fx.py',
                   'assets/story/mill/scene.json', 'assets/story/mill_gift/animation.json',
                   'assets/story/gearblade_focus/world/provenance.json',
                   'tools/capture_caelan_aqua_progression.py']
        record = {
            'fixtures':['Gift/Boar run: MQ01 completed with the supported test fixture; MQ02 gift, departure and tutorial use real inputs.',
                'Cave run: earlier completed-Mill fixture, followed by actual MQ03 dialogue/travel; public weapon acquisition represents its already-earned blade.',
                'Cave Caelan MP explicitly set to 0; encounter approach positioned and countdown reduced to 1 pixel for capture. Formation and seed are selected and saved by production code.'],
            'disposable_saves_and_settings':True,
            'synthetic_attack_poses':False,
            'captures':self.captures, 'boar_player_actions':actions, 'cave':cave,
            'source_sha256':{name:digest(ROOT/name) for name in sources},
            'artifact_sha256':{item['file']:digest(self.output/item['file']) for item in self.captures},
        }
        record['artifact_sha256']['contact_sheet.png'] = digest(self.output/'contact_sheet.png')
        (self.output/'verification.json').write_text(json.dumps(record, indent=2)+'\n')
        pygame.quit()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args(argv)
    Review(args.output).run()
    print('Captured Caelan progression in '+str(args.output))


if __name__ == '__main__':main()
