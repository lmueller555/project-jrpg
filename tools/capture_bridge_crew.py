"""Actual Game.update/draw review; fixture positions and input are documented."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
from pathlib import Path
import sys, tempfile, json
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import pygame
from PIL import Image
from main import Game
from tools.capture_lantern_quest import seed_previous_quests
import tools.capture_grain_farm as capture
OUT=ROOT/'docs/reviews/bridge_crew'
capture.OUT=OUT

class Recorder(capture.Recorder):
    def until(self,predicate,limit=60):
        for _ in range(limit*15):
            if predicate():return
            self.run(2/30)
        raise AssertionError((self.game.world.bridge_crew.stage,self.game.world.bridge_crew.state))

def setup(root):
    g=Game(window_size=(960,640),fullscreen=False,start_on_title=False,save_path=root/'journey.json',settings_path=root/'settings.json')
    g.audio.set_music(0);g.audio.set_effects(0);seed_previous_quests(g)
    g.world=g.overworld_world;g.player.position.update(-2376,642)
    g.opening_fade=g.transfer_cooldown=0;g.location_seconds=0
    g.camera.focus((-2376,616),duration=0)
    return g

def still(g,name):
    g.draw();Image.frombytes('RGB',g.window.get_size(),pygame.image.tobytes(g.window,'RGB')).save(OUT/(name+'.png'))

def main():
    OUT.mkdir(parents=True,exist_ok=True);report={}
    with tempfile.TemporaryDirectory() as tmp:
        g=setup(Path(tmp));c=g.world.bridge_crew;r=Recorder(g,'work_and_tea')
        r.until(lambda:c.stage=='carry');r.run(.5);still(g,'carry')
        r.until(lambda:c.stage=='ready');r.run(.5)
        assert g.overworld_travel.interact()
        r.until(lambda:c.stage=='request');still(g,'tea_arrives')
        assert g.overworld_travel.interact()
        while g.social.active:r.run(3);g.social.advance()
        r.until(lambda:c.stage=='wobble');r.run(1);still(g,'steady_surface')
        r.until(lambda:c.stage=='exchange');still(g,'handoff')
        assert g.overworld_travel.interact()
        while g.social.active:r.run(3);g.social.advance()
        r.until(lambda:c.stage=='sit');r.run(3);still(g,'tea_break')
        r.until(lambda:c.state['tea_beat']==5);r.run(5)
        report['work_and_tea']=r.close()
        g=setup(Path(tmp));c=g.world.bridge_crew;r=Recorder(g,'blocked_and_continue')
        r.until(lambda:c.stage=='carry');g.player.position.update(-2352,616)
        r.run(3);p=tuple(c.mason.position);r.run(2);assert p==tuple(c.mason.position);still(g,'yield')
        r.run(.5,(0,1));r.run(.4,(-1,0))
        r.until(lambda:c.state['sorted']==1 and c.stage=='carry')
        assert g.save_progress();still(g,'before_continue');r.run(1)
        g.on_title=True;assert g.begin_journey(True);g.opening_fade=g.transfer_cooldown=0
        g.camera.focus((-2376,616),duration=0);g.location_seconds=0
        c=g.world.bridge_crew;assert c.state['sorted']==1;r.run(1);still(g,'after_continue')
        r.until(lambda:c.stage=='ready');r.run(2);report['blocked_and_continue']=r.close()
        g=setup(Path(tmp));c=g.world.bridge_crew
        # Start from a legitimate completed sorting checkpoint to isolate tea recovery.
        c.restore({'sorted':3,'tea_beat':0,'greeted':[]})
        r=Recorder(g,'tea_continue')
        assert g.overworld_travel.interact()
        r.until(lambda:c.stage=='request');assert g.overworld_travel.interact()
        while g.social.active:r.run(2.5);g.social.advance()
        r.until(lambda:c.stage=='reach');r.run(.8);assert g.save_progress();still(g,'cup_before_continue')
        g.on_title=True;assert g.begin_journey(True);g.opening_fade=g.transfer_cooldown=0
        g.camera.focus((-2376,616),duration=0);g.location_seconds=0;c=g.world.bridge_crew
        r.until(lambda:c.stage=='exchange');assert g.overworld_travel.interact()
        while g.social.active:r.run(2.5);g.social.advance()
        r.until(lambda:c.stage=='sit');r.run(1);assert g.save_progress();still(g,'sit_before_continue')
        g.on_title=True;assert g.begin_journey(True);g.opening_fade=g.transfer_cooldown=0
        g.camera.focus((-2376,616),duration=0);g.location_seconds=0;c=g.world.bridge_crew
        assert c.state['tea_beat']==4
        r.until(lambda:c.state['tea_beat']==5);r.run(2);report['tea_continue']=r.close()
        report['cache_stats']=g.world.cache_stats
    (OUT/'capture_report.json').write_text(json.dumps(report,indent=2)+'\n')
    pygame.quit()

if __name__=='__main__':main()
