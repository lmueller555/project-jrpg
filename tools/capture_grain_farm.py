"""Record production Game.update/draw at normal zoom; no painted scene overlays."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
from pathlib import Path
import sys
import tempfile
import json
import subprocess
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import pygame
from PIL import Image
from main import Game
from grain_farm import MILL_FLAG, SCENE_ID
from tools.capture_lantern_quest import seed_previous_quests

OUT=ROOT/'docs/reviews/grain_farm'


class Recorder:
    def __init__(self, game, name):
        self.game=game;self.count=0
        self.process=subprocess.Popen(['ffmpeg','-y','-loglevel','error','-f','rawvideo','-pixel_format','rgb24',
            '-video_size','960x640','-framerate','15','-i','-','-an','-c:v','libx264','-preset','fast',
            '-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(OUT/(name+'.mp4'))],stdin=subprocess.PIPE)

    def frame(self):
        self.game.draw()
        self.process.stdin.write(pygame.image.tobytes(self.game.window,'RGB'))
        self.count+=1

    def run(self,seconds,direction=(0,0)):
        for i in range(round(seconds*30)):
            self.game.update(1/30,direction,False)
            if i%2==0:self.frame()

    def until(self,predicate,limit=30):
        for _ in range(limit*15):
            if predicate():return
            self.run(2/30)
        raise AssertionError(('Timed out',self.game.world.grain_farm.stage))

    def close(self):
        self.process.stdin.close()
        assert self.process.wait()==0
        return {'frames':self.count,'fps':15,'seconds':self.count/15}


def game_at_farm(root, repaired=False):
    game=Game(window_size=(960,640),fullscreen=False,start_on_title=False,
        save_path=root/'journey.json',settings_path=root/'settings.json')
    game.audio.set_music(0);game.audio.set_effects(0)
    if repaired:
        seed_previous_quests(game)
        # Fixture includes the physical intake-repair fact emitted by gameplay.
        game.social.flags.add(MILL_FLAG)
    game.world=game.overworld_world
    game.player.position.update(-876,232)
    game.opening_fade=game.transfer_cooldown=0;game.location_seconds=0
    game.camera.reset();game.camera.focus((-861,200),duration=0)
    return game


def still(game,name):
    game.draw()
    Image.frombytes('RGB',game.window.get_size(),pygame.image.tobytes(game.window,'RGB')).save(OUT/(name+'.png'))


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    report={}
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp)
        g=game_at_farm(root)
        r=Recorder(g,'before_repair');r.run(12)
        g.player.position.update(-853,192)
        assert g.overworld_travel.interact()
        while g.social.active:r.run(3);g.social.advance()
        r.run(2);report['before_repair']=r.close();still(g,'before_repair')
        assert g.world.grain_farm.state['loaded']==0
        g=game_at_farm(root,True);f=g.world.grain_farm
        r=Recorder(g,'loading_and_vignette')
        r.until(lambda:f.stage=='ready' and f.coworker_stop==6)
        still(g,'loaded_cart')
        # Walk closer using real movement, clear of the workers' foot probes.
        r.run(.4,(0,-1))
        assert g.overworld_travel.interact()
        assert g.social.script_identifier==SCENE_ID
        while g.social.active:
            r.run(3.5)
            still(g,'dialogue_'+str(g.social.page_index))
            g.social.advance()
        r.until(lambda:f.stage=='help_place');r.run(.3);still(g,'shared_grip')
        r.until(lambda:f.state['scene_done']);r.run(6)
        still(g,'finished');report['loading_and_vignette']=r.close()
        assert g.save_progress()
        g=game_at_farm(root,True);f=g.world.grain_farm
        r=Recorder(g,'blocked_path_and_continue')
        r.until(lambda:f.stage=='carry')
        # Place the leader in the lane to establish the blocked-path fixture;
        # all subsequent motion and recovery use normal Game.update movement.
        g.player.position.update(-824,210)
        r.run(3);still(g,'yielding')
        stopped=tuple(f.loader.position);r.run(2);assert tuple(f.loader.position)==stopped
        r.run(.7,(-1,0));r.run(.55,(0,1))
        r.until(lambda:f.state['loaded']==1 and f.stage=='carry')
        assert g.save_progress()
        r.run(.4);still(g,'before_continue')
        g.on_title=True
        assert g.begin_journey(True)
        g.camera.focus((-861,200),duration=0);g.location_seconds=0
        assert g.world.grain_farm.state['loaded']==1
        r.run(1);still(g,'after_continue')
        r.until(lambda:f.stage=='ready' and f.coworker_stop==6)
        r.run(2);report['blocked_path_and_continue']=r.close()
        report['final_state']=f.to_dict()
        report['cache_stats']=g.world.cache_stats
    (OUT/'capture_report.json').write_text(json.dumps(report,indent=2)+'\n')
    pygame.quit()

if __name__=='__main__':main()
