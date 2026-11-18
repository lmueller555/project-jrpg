"""Review Caelan's contour revision beside Mira and in production scenes.

Before frames come from the pre-outline commit. Current travel uses Player's
actual selector; world/interaction fixtures use existing production renderers.
All fixtures disable disk persistence and label seeded rescue victory facts.
"""
from __future__ import annotations
import argparse
import gc
from hashlib import sha256
from io import BytesIO
import json
import os
from pathlib import Path
import subprocess
import sys

os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
import pygame
from PIL import Image,ImageDraw
from tools import capture_caelan_overworld as travel_review

BASELINE='6e1a61bc8bfe80caeafd8d868331c3fe43eaf056'
OUT=ROOT/'docs/reviews/caelan_outline'
DIRECTIONS=('front','back','left','right')


def baseline_image(path):
    raw=subprocess.check_output(['git','show',f'{BASELINE}:{path}'],cwd=ROOT)
    return Image.open(BytesIO(raw)).convert('RGBA')


def comparison(game):
    card=Image.new('RGB',(1040,1040),travel_review.BG);draw=ImageDraw.Draw(card)
    draw.text((20,16),'CAELAN / SHARED OVERWORLD OUTLINE STYLE',font=travel_review.font(24),fill=travel_review.INK)
    draw.text((20,53),'Original Caelan, revised Caelan, and current Mira — native canvases, nearest enlargement',font=travel_review.font(15),fill=travel_review.MUTED)
    for row,label in enumerate(('Caelan before','Caelan outlined','Mira reference')):
        draw.text((16,125+row*280),label,font=travel_review.font(17),fill=travel_review.INK)
        for col,direction in enumerate(DIRECTIONS):
            center=250+col*220
            if row==0:
                image=baseline_image(f'assets/characters/caelan/idle_{direction}.png')
                anchor=(12,30)
                draw.text((center,91),direction.capitalize(),font=travel_review.font(17),fill=travel_review.INK,anchor='mt')
            elif row==1:
                image=travel_review.runtime_frame(game,direction,'idle');anchor=(12,30)
            else:
                image=Image.open(ROOT/f'assets/characters/mira/idle_{direction}.png').convert('RGBA');anchor=(16,30)
            base=300+row*280
            draw.line((center-72,base+24,center+72,base+24),fill='#b7c2ca')
            enlarged=image.resize((image.width*6,image.height*6),Image.Resampling.NEAREST)
            card.paste(enlarged,(center-anchor[0]*6,base-anchor[1]*6),enlarged)
            card.paste(image,(center-anchor[0],base+35),image)
    draw.text((18,1005),'Each enlarged row includes a native-size sample below. Sprite and ground registration are unchanged.',font=travel_review.font(15),fill=travel_review.MUTED)
    card.save(OUT/'comparison.png')


def rescue_studies():
    from tools.capture_sanctuary_rescue import make_game,seed_victory,press
    game=make_game();game.saves.enabled=False
    owner=game.sanctuary_rescue
    seed_victory(game);owner.maybe_start()
    captured=[]
    desired={'free_worker','treatment','assisted_stand'}
    for _ in range(4000):
        game.update(.05,(0,0),False)
        if owner.active:
            key=owner.shot
            if key in desired and owner._action_elapsed>=owner.phase.get('cue_seconds',1.)+.1:
                game.draw();file='rescue_'+key+'.png'
                pygame.image.save(game.window,str(OUT/file))
                captured.append(dict(file=file,phase=key,action_seconds=owner._action_elapsed,
                                     camera=list(owner._camera_center),zoom=owner._camera_zoom,
                                     player=list(game.player.position)))
                desired.remove(key)
            if owner.dialogue is not None:press(game)
        if owner.stage=='greenwell' and not owner.active:break
    else:raise AssertionError('Rescue pose capture did not reach Greenwell')
    assert not desired,desired
    game.player.update((-1,0),.02,game.world,False);game.draw()
    pygame.image.save(game.window,str(OUT/'rescue_greenwell_walk.png'))
    captured.append(dict(file='rescue_greenwell_walk.png',stage=owner.stage,
                         player=list(game.player.position),camera=list(game.camera.position())))
    assert not game.save_store.enabled and game.saves.library.root is None
    owner.reset();game.combat.reset();game.music.stop()
    return captured


def capture(output=OUT):
    global OUT
    OUT=Path(output);OUT.mkdir(parents=True,exist_ok=True)
    travel_review.OUT=OUT
    pygame.init();pygame.display.set_mode((960,640))
    game=travel_review.Game(window_size=(960,640),fullscreen=False,start_on_title=False,
                            _preview_window=pygame.Surface((960,640)))
    game.audio.set_music(0);game.audio.set_effects(0)
    before=game._progress_signature()
    comparison(game);clock=travel_review.travel(game)
    worlds=[]
    for filename,world,label,direction,point in (
        ('town.png',game.town,'Eldenmere','front',(384,344)),
        ('cave.png',game._scene_by_id('sanctuary_cave'),'Sanctuary cave','right',(456,1280))):
        card,record=travel_review.world_still(game,world,label,direction,point)
        card.save(OUT/filename);worlds.append(dict(file=filename,**record))
    travel_review.action_sheet()
    assert before==game._progress_signature()
    assert not game.save_store.enabled and not game.saves.enabled
    game.combat.reset();game.music.stop()
    interactions=travel_review.interaction_studies()
    gc.collect()
    rescue=rescue_studies()
    files=[p for p in (ROOT/'assets/characters/caelan').rglob('*.png')]
    files += [p for p in (ROOT/'assets/story/sanctuary_rescue/actions').glob('*.png')]
    files += [ROOT/f'assets/characters/mira/idle_{d}.png' for d in DIRECTIONS]
    files += [ROOT/name for name in ('tools/build_caelan_overworld.py','tools/build_caelan_overworld_dependents.py',
                                    'tools/build_sanctuary_rescue_art.py','tools/capture_caelan_outline.py',
                                    'sanctuary_rescue.py','sanctuary_arrival.py',
                                    'assets/story/sanctuary_rescue/art.json',
                                    'assets/source/story/sanctuary_rescue/registration.json',
                                    'assets/source/characters/caelan/overworld_refresh/travel_authored.png',
                                    'assets/source/characters/caelan/overworld_refresh/actions_authored.png')]
    files += [ROOT/'assets/source/characters/caelan/overworld_refresh/registration.json']
    for path in (ROOT/'tools').glob('*contour*.py'):files.append(path)
    for path in (ROOT/'tools').glob('*outline*.py'):files.append(path)
    outputs=sorted(p for p in OUT.iterdir() if p.suffix in ('.png','.gif'))
    evidence=dict(baseline_commit=BASELINE,
        scope='Isolated actual Player selector, production world and interaction owners. Rescue prerequisites/victory are explicitly seeded; no played fight or full quest walkthrough is claimed.',
        travel_loop_ms=clock,disk_persistence_disabled=True,travel_progress_unchanged=True,
        worlds=worlds,interactions=interactions,rescue=rescue,
        input_sha256={p.relative_to(ROOT).as_posix():sha256(p.read_bytes()).hexdigest() for p in sorted(set(files))},
        output_sha256={p.name:sha256(p.read_bytes()).hexdigest() for p in outputs})
    (OUT/'evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
    pygame.quit()
    print(f'Captured {len(outputs)} outline review artifacts; travel loop {clock} ms.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=OUT)
    capture(parser.parse_args().output)
