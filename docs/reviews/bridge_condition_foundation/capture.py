"""Render production bridge states in temporary journeys, without changing saves.

Run from the repository root with dummy SDL drivers. Intact/restored are explicit
fixtures using the existing procedural deck, not final bridge-art approvals.
"""
from pathlib import Path
import json
import os
import tempfile

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import pygame
from bridge_condition import BridgeCondition
from main import Game


def capture():
    output = Path(__file__).resolve().parent
    records = []
    with tempfile.TemporaryDirectory(prefix='bridge-condition-review-') as folder:
        game = Game(fullscreen=False, save_path=Path(folder)/'journey.json',
                    settings_path=Path(folder)/'settings.json')
        game.audio.set_music(0);game.audio.set_effects(0)
        facts = game.quests.to_dict(), set(game.social.flags)
        for label, phase in (('current_start', None), ('destroyed_fixture', 'destroyed'),
                             ('intact_fixture', 'intact'), ('restored_fixture', 'restored')):
            snapshot = {'bridge_condition': BridgeCondition(phase).to_dict()} if phase else None
            game.overworld_travel.restore_bridge_condition(snapshot)
            world = game.overworld_world
            game.world = world
            point = world._tile_rect(world.region['bridge']['deck_rect_tiles']).center
            game.player.position.update(point if phase in ('intact', 'restored') else (-2376, 644))
            game.player.facing='front';game.player.moving=False
            surface = pygame.Surface((480,320))
            world.draw(surface, (-2820, 520), game.player, 0, include_ui=False)
            pygame.image.save(surface, output/(label+'.png'))
            records.append({'image':label+'.png', 'condition':world.bridge_condition.to_dict(),
                            'deck_center_passable':world.can_stand(point),
                            'crew_active':world.bridge_crew.active})
        assert facts == (game.quests.to_dict(), set(game.social.flags))
        game.music.stop();game.regional_audio.reset()
    pygame.quit()
    (output/'captures.json').write_text(json.dumps({'records':records,
        'quest_and_dialogue_facts_unchanged':True,
        'intact_and_restored_are_interim_fixtures':True}, indent=2)+'\n')


if __name__ == '__main__':capture()
