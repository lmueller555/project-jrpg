"""Disposable seeded production dialogue capture, with staged return travel."""
import pygame,tempfile
from pathlib import Path
Path("docs/reviews/mq03_resolution").mkdir(parents=True,exist_ok=True)
from tools.capture_sanctuary_rescue import make_game,seed_victory,press
from regent_resolution import STAGES
if __name__=='__main__':
    with tempfile.TemporaryDirectory() as d:
     g=make_game(d,embedded=False);seed_victory(g);g.sanctuary_rescue.restore({'version':1,'stage':'evacuated'});g.sanctuary_cave.lucan_departed=True;g._sync_story_party();g.world=g._scene_by_id('elden_vale_sanctuary');g.regent_quest.resolution.commit('resolution_report');g.regent_quest._setup_stage()
     c=g.regent_quest
     for stage in STAGES:
      if stage=='resolution_return':
       g.world=c.dining;g.player.position.update((228,252))
       for a in c.sanctuary_escorts:c._place(a,c.dining,c._landing(a,(228,200),c.dining))
       c.resolution.update(0)
      c._setup_stage();actor=c.aldric if stage=='resolution_report' else g.mill_quest.mira if stage=='resolution_companions' else c.serene
      if stage=='resolution_return':continue
      g.player.position.update(g.overworld_travel._landing(g.world,actor.position+pygame.Vector2(0,30)))
      assert c.resolution.interact(),stage
      g.draw();pygame.image.save(g.window,"docs/reviews/mq03_resolution/"+stage+".png")
      for _ in range(300):
       if not g.social.active:break
       press(g);g.social.update((0,0))
      assert c.stage!=stage,stage
      assert g._validate_journey(g.journey_snapshot()) is not None,stage
      g.draw()
     print('Full acknowledged dialogue chain validated',c.stage)
     g.music.stop();pygame.quit()
