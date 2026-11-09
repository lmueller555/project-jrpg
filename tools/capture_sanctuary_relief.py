"""Review the visitor relief room with production movement, dialogue and rest.

Only the initial hall location, recruited party and injuries are disposable
review fixtures. Door entry, room walking, offers, recovery and rendering use
the game. No player journey or settings outside a temporary folder is touched.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pygame
from PIL import Image, ImageDraw, ImageFont

from main import Game
from tools.capture_sanctuary_reserve import path as clear_path, walk


HALL = 'elden_vale_sanctuary_hall'
ROOM = 'elden_vale_sanctuary_relief'
DEFAULT_OUTPUT = ROOT/'docs/reviews/sanctuary_relief'


def resources(game):
    return {identifier: {'hp': attributes.current_hp, 'mp': attributes.current_mp,
                         'max_hp': attributes.value('hp'), 'max_mp': attributes.value('mp')}
            for identifier, attributes in game.party.characters.items()}


def preserved(game):
    return {'levels': game.character_progression.to_dict(),
            'inventory': game.inventory.to_dict(), 'quests': game.quests.to_dict(),
            'flags': sorted(game.social.flags), 'abilities': game.character_abilities.to_dict(),
            'cave_encounters': game.cave_random_encounters.to_dict(),
            'music': game.music.desired_track}


class Review:
    def __init__(self, output):
        self.output = output
        output.mkdir(parents=True, exist_ok=True)
        self.captures = []
        self.checks = {}

    def key(self, key):
        assert self.game.handle_events([
            pygame.event.Event(pygame.KEYDOWN, key=key, repeat=False),
            pygame.event.Event(pygame.KEYUP, key=key)])

    def tick(self, seconds=.05):
        self.game.update(seconds, (0, 0), False)

    def size(self, size=(960, 640), text_scale=1.):
        game = self.game
        game.window = pygame.display.set_mode(size, pygame.RESIZABLE)
        game.windowed_size = size
        game.audio.set_text_scale(text_scale)
        game._ensure_ui_surface()

    def photograph(self, name, label):
        game = self.game
        game.location_seconds = 0
        game.quest_ui.current_notice = None
        game.quest_ui.notices.clear()
        game.draw()
        pygame.image.save(game.window, self.output/name)
        self.captures.append({'file': name, 'label': label,
                              'scene': game.world.data['id'],
                              'position': list(game.player.position),
                              'window': list(game.window.get_size()),
                              'text_scale': game.audio.text_scale,
                              'script': game.social.script_identifier,
                              'party_resources': resources(game)})

    def route(self, goal):
        game = self.game
        scene = game.world.data['id']
        points = clear_path(game.world, game.player.position, goal)
        walk(game, points, scene)
        self.tick()
        assert game.world.data['id'] == scene
        assert game.world.can_stand(game.player.position)

    def offer(self):
        self.key(pygame.K_e)
        for _ in range(30):
            if self.game.social.choosing:
                self.game.draw()
                return
            assert self.game.social.active, 'Offer ended before showing its choices'
            self.key(pygame.K_SPACE)
        raise AssertionError('Rest choices did not appear')

    def choose(self, action):
        game = self.game
        index = next(index for index, option in enumerate(game.social.choice_options)
                     if option['action'] == action)
        rect = game.social.choice_rects[index]
        _, size, origin = game._ensure_ui_surface()
        point = (round(origin[0]+rect.centerx*size[0]/480),
                 round(origin[1]+rect.centery*size[1]/320))
        assert game.handle_events([
            pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=point),
            pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=point)])

    def finish_dialogue(self):
        for _ in range(30):
            if not self.game.social.active:
                self.tick(.7)
                return
            assert not self.game.social.choosing
            self.key(pygame.K_SPACE)
        raise AssertionError('Rest dialogue did not finish')

    def run(self):
        with tempfile.TemporaryDirectory(prefix='sanctuary-relief-review-') as directory:
            game = self.game = Game(window_size=(960, 640), fullscreen=False,
                start_on_title=False, save_path=Path(directory)/'journey.json',
                settings_path=Path(directory)/'settings.json')
            game.audio.set_music(0)
            game.audio.set_effects(0)
            game.opening.restore({'version': 1, 'stage': 'disabled'})
            game.social.cancel()
            game.social.blocked.clear()
            game.quests.drain_events()
            game.quest_ui.reset()
            for identifier in ('mira', 'lucan', 'rhea'):
                assert game.party.recruit(identifier)
            assert game.party.select(('caelan', 'mira', 'lucan'))
            for identifier, hp, mp in (('caelan', 17, 3), ('mira', 0, 0),
                                       ('lucan', 25, 2), ('rhea', 5, 1)):
                assert game.party.characters[identifier].set_current(hp=hp, mp=mp)
            # An unrecruited character's resources must not be recovered remotely.
            assert game.party.characters['edran'].set_current(hp=14, mp=2)
            game.world = game._scene_by_id(HALL)
            game.player.position.update(game.world.data['spawn'])
            game.player.facing = 'back'
            game.opening_fade = game.transfer_cooldown = 0
            game.party_travel.reset()
            game.camera.reset()
            pygame.event.clear()

            door = next(door for door in game.world.doors
                        if ROOM in door.data['destination'])
            approach = tuple(game.world.data.get('relief_room_approach',
                             (door.data['anchor'][0], door.data['anchor'][1]+24)))
            self.route(approach)
            self.photograph('hall_relief_door.png', 'Sanctuary hall · visitor-room entrance')
            # Use the production doorway contact after walking its clear approach.
            for _ in range(35):
                if game.world.data['id'] == ROOM:break
                game.update(.04, (0, -1), False)
            assert game.world.data['id'] == ROOM, 'Hall doorway did not enter the relief room'
            self.tick(.4)
            game.camera.reset()
            self.photograph('relief_room.png', 'Visitor relief room · bed, water and attendant')
            metadata = game.world.data['relief_room']
            assert game.sanctuary_relief.attendant in game.world.npcs
            assert len([npc for npc in game.world.npcs
                        if npc.data.get('id') == 'relief_attendant']) == 1

            self.route(metadata['bed_approach'])
            game.player.facing = 'back'
            assert game.bed_rest.nearby()
            before_resources = resources(game)
            before_state = preserved(game)
            self.offer()
            assert game.social.script_identifier == 'sanctuary_relief_bed_offer'
            self.photograph('bed_offer.png', 'Bedside offer · free, explicitly confirmed rest')
            self.size((480, 320), 1.5)
            self.photograph('bed_offer_large_text.png', 'Bedside offer · native 150% text')
            self.choose('rest')
            self.finish_dialogue()
            after_resources = resources(game)
            assert preserved(game) == before_state
            assert all(after_resources[identifier]['hp'] == after_resources[identifier]['max_hp']
                       and after_resources[identifier]['mp'] == after_resources[identifier]['max_mp']
                       for identifier in game.party.available_ids)
            assert after_resources['edran'] == before_resources['edran']
            self.checks.update(before_resources=before_resources, after_resources=after_resources,
                available_reserves_restored=True, active_ko_revived=True,
                unrecruited_elsewhere_preserved=True, progression_items_story_counter_music_preserved=True)

            self.size()
            game.party_ui.open()
            self.photograph('restored_party.png', 'After resting · active party restored')
            game.party_ui.close()
            self.route(metadata['attendant_approach'])
            game.player.facing = 'back'
            assert game.sanctuary_relief.interaction_hint()
            self.offer()
            assert game.social.script_identifier == 'sanctuary_relief_attendant_offer'
            self.photograph('attendant_offer.png', 'Attendant Nessa · visitor care and a free rest')
            self.choose('leave')
            self.tick()
            self.checks['declined_attendant_rest_kept_resources'] = resources(game) == after_resources
            assert self.checks['declined_attendant_rest_kept_resources']
            self.checks['walked_hall_door_bed_attendant'] = True
            self.checks['room_source'] = game.world.data.get('source_recipe')
            self.checks['attendant_count'] = len([npc for npc in game.world.npcs
                if npc.data.get('id') == 'relief_attendant'])
            game.music.stop()
            pygame.quit()
        self.write_review()

    def write_review(self):
        width, height = 480, 320
        sheet = Image.new('RGB', (2*(width+12), 3*(height+30)), '#10271f')
        draw = ImageDraw.Draw(sheet)
        font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 11)
        for index, record in enumerate(self.captures):
            x, y = index % 2*(width+12), index // 2*(height+30)
            draw.text((x+6, y+4), record['label'], fill='#f1cd77', font=font)
            with Image.open(self.output/record['file']) as picture:
                sheet.paste(picture.convert('RGB').resize((width, height), Image.Resampling.NEAREST), (x+6, y+23))
        sheet.save(self.output/'contact_sheet.png')
        (self.output/'verification.json').write_text(json.dumps({
            'fixture': 'Disposable hall location, recruited party and injuries; production movement, doors, dialogue and recovery.',
            'captures': self.captures, 'checks': self.checks}, indent=2)+'\n')
        (self.output/'README.md').write_text('''# Sanctuary visitor relief room

![Production relief-room and rest captures](contact_sheet.png)

These captures use the production `Game`, its hall doorway, visitor-room map,
attendant, bed choices, recovery, and Party menu. The initial hall location,
recruited party and injuries are disposable review fixtures. No player save or
settings outside a temporary directory is read or changed.

The tool walks from the hall entrance to the new wing, enters by normal door
contact, then walks to the bed and Nessa. Rest is accepted through the real
choice UI. All available companions recover HP/MP, including a fallen active
member and an available reserve. An unrecruited character remains unchanged;
EXP, inventory, quest facts, cave encounter state and the score remain intact.

Six screenshots cover the hall door, room, bed offer, minimum-size 150% text,
restored party and attendant's offer. `verification.json` records the exact
fixture resources and checks. The map uses the existing native pixel packs.

Reproduce from the repository root:

```sh
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python tools/capture_sanctuary_relief.py
```

Use `--output /tmp/sanctuary-relief-review` for disposable alternative captures.
''')
        print(f'Captured {len(self.captures)} Sanctuary relief-room views in {self.output}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    Review(arguments.output.resolve()).run()
