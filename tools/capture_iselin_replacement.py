"""Capture current Iselin shots and seeded post-rescue dialogue without player saves."""
from pathlib import Path
import json
import os
import sys
import tempfile
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import pygame
from PIL import Image
from tools.capture_sanctuary_rescue import make_game,seed_victory,press
from regent_resolution import STAGES
OUT=ROOT/'docs/reviews/iselin_replacement'


def capture():
    OUT.mkdir(parents=True,exist_ok=True);records=[]
    with tempfile.TemporaryDirectory() as directory:
        parent=make_game(directory,seed=False,embedded=False)
        try:
            parent.on_title=True;parent.open_gallery()
            assert parent.launch_gallery_scene('regent_arrival'),parent.gallery.error
            scene=parent.gallery_session.game.regent_arrival
            for name,time in (('aerial_gate',4),('gate_greeting',1),('locals',1),('relief',1),('town_parking',2)):
                scene.phase_index=next(i for i,p in enumerate(scene.data['phases']) if p['id']==name)
                scene.phase_time=time;scene.dialogue_index=scene.page_index=0
                parent.draw();pygame.image.save(parent.window,str(OUT/(name+'.png')))
                records.append({'file':name+'.png','fixture':'Isolated Gallery; visual shot selection','shot':name,'seconds':time})
            parent.gallery_session.close()
        finally:parent.music.stop();pygame.quit()
    with tempfile.TemporaryDirectory() as directory:
        game=make_game(directory,embedded=False)
        try:
            seed_victory(game)
            game.sanctuary_rescue.restore({'version':1,'stage':'evacuated'})
            game.sanctuary_cave.lucan_departed=True;game._sync_story_party()
            game.world=game._scene_by_id('elden_vale_sanctuary')
            owner=game.regent_quest;owner.resolution.commit('resolution_report');owner._setup_stage()
            for stage in STAGES:
                if stage=='resolution_return':
                    game.world=owner.dining;game.player.position.update((228,252))
                    for actor in owner.sanctuary_escorts:owner._place(actor,owner.dining,owner._landing(actor,(228,200),owner.dining))
                    owner.resolution.update(0);continue
                owner._setup_stage()
                actor=owner.iselin if stage=='resolution_report' else game.mill_quest.mira if stage=='resolution_companions' else owner.serene
                game.player.position.update(game.overworld_travel._landing(game.world,actor.position+pygame.Vector2(0,30)))
                assert owner.resolution.interact(),stage
                game.draw();filename=stage+'.png';pygame.image.save(game.window,str(OUT/filename))
                for _ in range(300):
                    if not game.social.active:break
                    press(game);game.social.update((0,0))
                assert owner.stage!=stage,stage
                assert game._validate_journey(game.journey_snapshot()) is not None,stage
                records.append({'file':filename,'fixture':'Seeded cave victory/evacuation; staged return travel; real acknowledged dialogue',
                                'stage':stage,'valid_checkpoint':True})
        finally:game.music.stop();pygame.quit()
    frames=[]
    for i in range(16):
        im=Image.open(ROOT/f'assets/story/regent_arrival/actors/iselin/walk_left_back_{i:02}.png').convert('RGBA')
        bg=Image.new('RGB',(240,288),'#e8edf2');big=im.resize((240,288),Image.Resampling.NEAREST);bg.paste(big,(0,0),big);frames.append(bg)
    frames[0].save(OUT/'diagonal_walk.gif',save_all=True,append_images=frames[1:],duration=[30,40]*8,loop=0,disposal=2)
    (OUT/'capture.json').write_text(json.dumps({'records':records,'persistence':'All sessions use temporary save/settings paths.'},indent=2)+'\n')
    print('Captured current cinematic shots and acknowledged post-rescue resolution checkpoints.')


if __name__=='__main__':capture()
