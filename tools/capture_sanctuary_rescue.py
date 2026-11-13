"""Isolated production rescue review; fixtures never publish a player save."""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import sys

os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
import pygame

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))


def seed_cave(game):
    """Seed acknowledged prerequisites, leaving rescue/boss/rewards untouched."""
    from quest_playtest import _completed_mill
    from quests import REGENT_QUEST
    from regent_quest import OBJECTIVES
    from sanctuary_boss import APPROACH
    _completed_mill(game)
    assert game.regent_arrival.restore({'version':1,'state':'seen'})
    assert game.accept_quest(REGENT_QUEST)
    for identifier in OBJECTIVES[:3]:assert game.quests.complete_objective(REGENT_QUEST,identifier)
    assert game.regent_quest.restore({'version':3,'stage':'sanctuary_arrival_pending'})
    assert game.sanctuary_arrival.restore({'version':1,'beat':7,'completed':True,'cave_entered':True})
    assert game._sync_story_party()
    assert game.character_abilities.learn_ability('caelan','aqua_edge')
    assert game.cave_lesson.restore({'version':1,'resonance_seen':True,'battle_cleared':True,'deferred':False})
    game.world=game._scene_by_id('sanctuary_cave')
    game.player.position.update(APPROACH);game.player.facing='back'
    game.player.moving=game.player.running=False
    game.opening_fade=game.transfer_cooldown=0.
    game.social.cancel_script();game.social.blocked.clear()
    game.quests.drain_events();game.quest_ui.reset()
    game.party_travel.reset();game.camera.reset()
    game._sync_world_music(restoring=True)
    return game


def make_game(directory=None,*,title=False,seed=True,embedded=True):
    from main import Game
    pygame.display.init();pygame.display.set_mode((960,640))
    kwargs={}
    if embedded:kwargs.update(_preview_window=pygame.Surface((960,640)),_quest_playtest=True)
    elif directory is not None:
        kwargs.update(save_path=Path(directory)/'journey.json',settings_path=Path(directory)/'settings.json')
    game=Game(window_size=(960,640),fullscreen=False,start_on_title=title,**kwargs)
    game.audio.set_music(0);game.audio.set_effects(0)
    if seed:seed_cave(game)
    return game


def press(game,key=pygame.K_SPACE):
    return game.handle_events([pygame.event.Event(pygame.KEYDOWN,key=key,repeat=False),
                               pygame.event.Event(pygame.KEYUP,key=key)])


def advance_until(game,predicate,*,limit=6000,dt=.05):
    for _ in range(limit):
        if predicate():return
        game.update(dt,(0,0),False)
        owner=game.sanctuary_rescue
        if owner.active and owner.dialogue is not None:press(game)
    raise AssertionError(('Rescue did not settle',game.sanctuary_rescue.to_dict(),
                          getattr(game.sanctuary_rescue,'phase_index',None),
                          getattr(game.sanctuary_rescue,'error',None)))


def seed_victory(game):
    """Labelled fixture: durable victory facts, no simulated fight or EXP grant."""
    from post_battle import battle_reward_definition
    from sanctuary_boss import RECEIPT
    reward=battle_reward_definition('cave_boss')
    assert game.sanctuary_rescue.restore({'version':1,'stage':'confrontation'})
    assert game.award_battle_rewards(RECEIPT,reward['drops'])
    assert game.sanctuary_boss.restore({'version':1,'defeated':True,'intro_seen':True,'pending':None})
    return game


def capture(output):
    from PIL import Image, ImageDraw
    import gc
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    game=make_game()
    owner=game.sanctuary_rescue
    records=[];frames=[];seen=set();image_files=[]
    def render(label):
        game.draw()
        name=label+'.png'
        pygame.image.save(game.window,str(output/name))
        image_files.append(name)
        return Image.open(output/name).convert('RGB')
    def drive(end):
        for tick in range(6000):
            if end():return
            game.update(.1,(0,0),False)
            if not owner.active:continue
            record={'mode':owner.mode,'shot':owner.shot,'phase_time':round(owner.phase_time,3),
                    'action_time':round(owner._action_elapsed,3),'stage':owner.stage,
                    'camera':list(owner._camera_center),'zoom':owner._camera_zoom,
                    'actors':{key:{'position':list(actor.position),'pose':actor.pose,
                                   'moving':actor.moving,'facing':actor.facing}
                              for key,actor in owner.actors.items()}}
            records.append(record)
            key=owner.shot
            if key not in seen and owner._action_elapsed>=min(1.5,owner.phase['min_seconds']*.7):
                seen.add(key);render(key)
            cue=owner.phase.get('cue_seconds')
            cue_key=key+'_after_cue'
            if cue is not None and cue_key not in seen and owner._action_elapsed>=cue+.1:
                seen.add(cue_key);render(cue_key)
            if tick%5==0:
                game.draw()
                raw=pygame.image.tobytes(game.window,'RGB')
                frames.append(Image.frombytes('RGB',game.window.get_size(),raw).resize((480,320),Image.Resampling.NEAREST))
            if owner.dialogue is not None:press(game)
        raise AssertionError(('Capture did not settle',owner.to_dict(),owner.shot,owner.error))
    completed=[]
    def before_finished():
        completed.append(True)
        return True
    assert owner.start_before(before_finished)
    drive(lambda:bool(completed))
    pre_resources={key:member.to_dict() for key,member in game.party.characters.items()}
    seed_victory(game)
    assert owner.maybe_start()
    drive(lambda:owner.stage=='greenwell' and not owner.active)
    render('greenwell_waiting')
    game.player.position.update(1950,852)
    assert owner.interact()
    render('departure_choice')
    game.social.cancel_script();owner._choose_departure('return')
    drive(lambda:owner.stage=='evacuated' and not owner.active)
    game.update(.1,(0,0),False);render('caretaker_handoff_finished')
    after_resources={key:member.to_dict() for key,member in game.party.characters.items()}
    assert pre_resources==after_resources
    assert not game.save_store.enabled and not game.audio.store.enabled
    assert game.sanctuary_cave.lucan_departed and 'lucan' not in game.party.active_ids
    if frames:
        palette=frames[len(frames)//2].quantize(colors=256)
        quantized=[frame.quantize(palette=palette,dither=Image.Dither.NONE) for frame in frames]
        quantized[0].save(output/'rescue.gif',save_all=True,append_images=quantized[1:],
                          duration=500,loop=0,optimize=True)
    thumbs=[]
    for name in image_files:
        frame=Image.open(output/name).convert('RGB').resize((480,320),Image.Resampling.NEAREST)
        tile=Image.new('RGB',(480,350),'#e8edf2');tile.paste(frame,(0,30))
        ImageDraw.Draw(tile).text((8,8),name.removesuffix('.png'),fill='#20303a')
        thumbs.append(tile)
    board=Image.new('RGB',(480*3,350*((len(thumbs)+2)//3)),'#e8edf2')
    for index,tile in enumerate(thumbs):board.paste(tile,((index%3)*480,(index//3)*350))
    board.save(output/'contact_sheet.png')
    files=['sanctuary_rescue.py','main.py','sanctuary_boss.py','sanctuary_cave.py',
           'party_travel.py','regent_emergency.py','assets/story/sanctuary_rescue/scene.json',
           'assets/story/sanctuary_rescue/art.json','tools/capture_sanctuary_rescue.py']
    def asset_paths(value):
        if isinstance(value,dict):
            for item in value.values():yield from asset_paths(item)
        elif isinstance(value,list):
            for item in value:yield from asset_paths(item)
        elif isinstance(value,str) and value.startswith('assets/') and (ROOT/value).is_file():
            yield value
    files=sorted(set(files)|set(asset_paths(owner.art))|{
        'assets/maps/sanctuary_cave/map.json','assets/maps/elden_vale_sanctuary/map.json',
        'tools/build_sanctuary_rescue_art.py'})
    evidence={'scope':'Disposable seeded cave prerequisites and labelled durable victory facts. No played fight, EXP grant or end-to-end quest walkthrough is claimed.',
              'persistence_enabled':False,'resources_unchanged':pre_resources==after_resources,
              'screenshots':image_files,'camera_samples':records,
              'output_sha256':{name:sha256((output/name).read_bytes()).hexdigest()
                               for name in image_files+['rescue.gif','contact_sheet.png']},
              'final_rescue':owner.to_dict(),'lucan_departed':game.sanctuary_cave.lucan_departed,
              'fingerprints':{name:sha256((ROOT/name).read_bytes()).hexdigest() for name in files}}
    (output/'evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
    owner.reset();game.music.stop();pygame.quit();del game;gc.collect()
    print('Captured '+str(len(image_files))+' rescue frames and '+str(len(records))+' camera samples.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'docs/reviews/sanctuary_rescue')
    capture(parser.parse_args().output)
