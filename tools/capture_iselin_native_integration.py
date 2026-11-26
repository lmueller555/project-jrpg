"""Review retained native Iselin art without a retired quest or arrival scene.

Actor stations and clocks are explicit art-review fixtures. World rendering is
production Game.draw; these captures do not imply new narrative integration.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
import pygame
from PIL import Image,ImageDraw,ImageFont
from story_actor import StoryActor
from tools.capture_iselin_native_front_walk import gif,labelled
from tools.scenario_fixtures import make_game
REVIEW=ROOT/'docs/reviews/iselin_native_integration'
OUT=ROOT/'docs/reviews/opening_runtime_retirement/iselin_art_library'
DIRECTIONS=('front','left','right','back')


def approved_assets():
    baseline=json.loads((REVIEW/'approved_assets.json').read_text())
    for path,digest in baseline['sha256'].items():
        assert sha256((ROOT/path).read_bytes()).hexdigest()==digest,path
    return baseline

def native(actor):
    assert actor.draw_anchor==(12,30)
    assert set(actor.idles)==set(DIRECTIONS)
    assert set(actor.walks)==set(DIRECTIONS)
    assert not callable(getattr(actor,'detailed_sprite',None))
    for direction in DIRECTIONS:
        assert actor.idles[direction].get_size()==(24,36)
        assert actor.walk_durations[direction]==(35,)*16
        assert all(frame.get_size()==(24,36) for frame in actor.walks[direction])

def image(game):
    game.draw()
    return Image.frombytes('RGB',game.window.get_size(),pygame.image.tobytes(game.window,'RGB'))

def save_frame(game,output,name,records,fixture,**facts):
    filename=name+'.png'
    image(game).save(output/filename)
    records.append({'file':filename,'fixture':fixture,**facts})

def stop(game):
    game.opening_audio.reset();game.regional_audio.reset()
    game.music.stop();pygame.quit()

def diagonal_board(output):
    folder=ROOT/'assets/characters/iselin/cinematic/ground'
    manifest=json.loads((folder/'animation.json').read_text())
    frames=manifest['loops']['walk_left_back']
    board=Image.new('RGB',(704,932),'#e8edf2');draw=ImageDraw.Draw(board)
    font=ImageFont.truetype(str(ROOT/'assets/ui/fonts/AtkinsonHyperlegible-Regular.ttf'),15)
    draw.text((12,10),'EXPORTED CINEMATIC DIAGONAL / ANATOMY INSPECTION',font=font,fill='#263c35')
    hashes={}
    for index,record in enumerate(frames):
        path=folder/record['file'];sprite=Image.open(path).convert('RGBA')
        x=12+(index%4)*174;y=42+(index//4)*220
        draw.text((x,y),f'{index+1:02}',font=font,fill='#263c35')
        enlarged=sprite.resize((160,192),Image.Resampling.NEAREST)
        board.paste(enlarged,(x,y+20),enlarged)
        hashes[str(path.relative_to(ROOT))]=sha256(path.read_bytes()).hexdigest()
    board.save(output/'scene_diagonal_frames.png')
    return {'file':'scene_diagonal_frames.png',
            'fixture':'Numbered exported cinematic drawings, enlarged2x; anatomy inspection independent of horse occlusion. Not a gameplay screenshot.',
            'source_sha256':hashes}

def travel(output,directory,records):
    game=make_game(directory,embedded=False)
    observations={}
    try:
        record=json.loads((ROOT/'assets/characters/iselin/actor.json').read_text())
        actor=StoryActor(record,game.town);actor.story_visible=True
        game.town.npcs.append(actor);game.world=game.town
        game.player.position.update(550,432);game.camera.focus((400,480),duration=0)
        native(actor)
        for direction in DIRECTIONS:
            actor.position.update(384,480);actor.facing=direction;actor.moving=True
            frames=[]
            for index in range(16):
                actor.walk_ms=index*35
                frames.append(image(game))
            gif(output/f'walk_{direction}.gif',frames,[30,40]*8)
            observations[direction]={'frames':16,'frame_ms':35,'duration_ms':560,
                'position':list(actor.position),'fixture':'Stationary authored cycle; no quest owner.'}
            actor.moving=False
            save_frame(game,output,'idle_'+direction,records,'Neutral StoryActor in actual Game.draw.',
                       direction=direction,anchor=list(actor.draw_anchor))
        actor.request_conversation('left')
        assert actor.sprite(0) is actor.idles['left']
        save_frame(game,output,'conversation_idle',records,'Generic conversation-facing selection; no scripted story.')
        actor.end_conversation()
    finally:stop(game)
    return observations


def capture(output=OUT):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    baseline=approved_assets();records=[]
    with tempfile.TemporaryDirectory(prefix='iselin-art-library-') as directory:
        observations=travel(output,directory,records)
    records.append(diagonal_board(output));approved_assets()
    metadata={'base_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
              'renderer':'Production Game.draw with neutral StoryActor art fixtures.',
              'persistence':'Temporary save/settings only; no retired quest or scene replay.',
              'approved_pngs_preserved':len(baseline['sha256']),'frames':records,'cycles':observations}
    (output/'capture.json').write_text(json.dumps(metadata,indent=2)+'\n')
    return metadata


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=OUT)
    capture(parser.parse_args().out)
