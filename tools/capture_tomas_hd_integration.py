"""Staged-pose native Game.draw reviews; state-machine behavior lives in tests.

Uses actual rooms, actor assets, prop ownership, sorting and native renderer.
Only positions/action clocks are fixtures; no composed mockup or rescaled shot.
"""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy');os.environ.setdefault('SDL_AUDIODRIVER','dummy')
from pathlib import Path
import sys,tempfile,json
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import pygame
from main import Game
OUT=ROOT/'docs/reviews/tomas_hd_integration'
def run():
 OUT.mkdir(parents=True,exist_ok=True)
 with tempfile.TemporaryDirectory() as tmp:
  folder=Path(tmp);g=Game(window_size=(960,640),fullscreen=False,start_on_title=False,save_path=folder/'save.json',settings_path=folder/'settings.json')
  g.opening.restore({'version':1,'stage':'disabled'});g.opening_fade=g.transfer_cooldown=g.location_seconds=0
  t=next(a for a in g.persistent_npcs if a.data['id']=='tomas');dining=g._scene_by_id('sanctuary_dining');g.world=dining;g.player.position.update(280,286)
  def capture(name):
   g.camera.reset();g.draw();pygame.image.save(g.canvas.native,str(OUT/(name+'.png')))
  for name,step,pos,clock in [('routine_surface','prepare',(160,262),800),('routine_held','prepare',(160,262),1100),('tinker','tinker',(104,262),1100)]:
   t.select_step(step,pos,'sanctuary_dining');t.state_ms=clock;capture(name)
  t.state_ms=0;t.story_paused=True
  o=g.opening;o.stage='breakfast';o._phase='meal';o._body(t,o._image('tomas_eat/frame_03.png'),o.data['tomas_seated_position']);capture('opening_eat')
  o._clear_pose(t);o.restore({'version':1,'stage':'disabled'})
  owner=g.regent_quest;owner.stage='hosted';owner._meal_ready=True;owner.scene_actions._meal_clock=1;owner.scene_actions._apply_seating();capture('regent_right_seat');owner.scene_actions.release()
  owner.stage='idle';owner._meal_ready=False
  (OUT/'capture.json').write_text(json.dumps({'kind':'production Game.draw: routine/opening/regent staged pose review; Halden real accepted-quest interaction/update lift','native_size':[960,640],'scenes':['sanctuary_dining','halden'],'files':['routine_surface.png','routine_held.png','tinker.png','opening_eat.png','regent_right_seat.png','halden_lift.png'],'behavior_tests':['test_tomas_routines','test_halden_visit','test_opening_sequence','test_regent_actions','test_tomas_hd_integration']},indent=2)+'\n')
 pygame.quit()
 # Drive the accepted Halden quest through its real interaction/update path.
 sys.path.insert(0,str(ROOT/'tests'))
 from test_halden_visit import HaldenGameplayTests
 fixture=HaldenGameplayTests();fixture.setUp()
 try:
  fixture.medicine();fixture.game.player.position.update(128,292)
  fixture.key(pygame.K_e);fixture.game.player.position.update(176,210)
  for _ in range(1400):
   fixture.game.update(1/60,(0,0),False)
   if fixture.visit.tomas_job=='lift' and fixture.visit.tomas_time>=.4:
    fixture.game.opening_fade=fixture.game.location_seconds=0
    fixture.game.camera.reset();fixture.game.draw()
    pygame.image.save(fixture.game.canvas.native,str(OUT/'halden_lift.png'))
    break
  else:raise AssertionError('Live sack lift was not reached')
 finally:fixture.tearDown();fixture.doCleanups()
if __name__=='__main__':run()
