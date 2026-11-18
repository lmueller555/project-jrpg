"""Actual production-Game evidence for a scoped regional idle/walk migration.

Normal movement remains controller-owned. Only prerequisite flags, player review
station and initial scene are fixtures. Directional stills are explicitly staged
pose fixtures in the production renderer, separate from the actual movement trace.
Temporary journeys/settings only; this never publishes or changes existing art.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import pygame
from PIL import Image
from main import Game
from regional_npc_art import ROLES,actor_binding
STATIONS={'grain':(-776,250),'bridge':(-2340,644),'regional_gardener':(-508,1206),'regional_picker':(-135,-230)}

def capture(actor_id,output):
    binding=actor_binding(actor_id)
    if binding is None:raise ValueError('Explicit migration not active: '+actor_id)
    output.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='regional-native-') as temp:
        p=Path(temp);game=Game(fullscreen=False,window_size=(960,640),start_on_title=True,save_path=p/'journey.json',settings_path=p/'settings.json')
        try:
            game.on_title=False;game.opening.restore({'version':1,'stage':'disabled'});game.opening_fade=game.transfer_cooldown=0
            game.social.flags.add('CH01_MQ02_MILL_RESTORED')
            game.world=game.overworld_world
            controllers=(game.world.grain_farm,game.world.bridge_crew,game.world.garden_orchard)
            actor=next(a for c in controllers for a in c.actors if a.data['id']==actor_id)
            station=STATIONS.get(actor_id,STATIONS[actor_id.split('_')[0]]) if actor_id.startswith(('grain_','bridge_')) else STATIONS[actor_id]
            game.player.position.update(station);game.camera.reset();trace=[];frames=[];selected=[]
            for tick in range(5400):
                game.update(1/30,(0,0),False)
                if actor.pose=='idle' and actor.moving:
                    trace.append({'tick':tick,'position':list(actor.position),'facing':actor.facing,'pose':actor.pose,'clock':actor.clock,'safe_feet':game.world.can_stand(actor.position,actor.probe_size,actor)})
                    game.draw()
                    if not selected:
                        pygame.image.save(game.canvas.native,str(output/'actual_walk_native.png'));selected.append(tick)
                    if len(frames)<24:frames.append(Image.frombytes('RGB',game.canvas.native.get_size(),pygame.image.tobytes(game.canvas.native,'RGB')))
                    if len(trace)>=24:break
            if not trace:raise AssertionError('No controller-owned unladen walking observed')
            durations=[30 if i%3 else 40 for i in range(len(frames))]
            frames[0].save(output/'actual_walk.gif',save_all=True,append_images=frames[1:],duration=durations,loop=0)
            # Disclosed pose fixtures show all directions at the same real station.
            old=(actor.pose,actor.facing,actor.moving,actor.clock)
            for facing in ('front','back','left','right'):
                actor.pose='idle';actor.facing=facing;actor.moving=False;actor.clock=0
                game.draw();pygame.image.save(game.canvas.native,str(output/f'fixture_idle_{facing}.png'))
            actor.pose,actor.facing,actor.moving,actor.clock=old
            report={'actor_id':actor_id,'binding':binding,'scene':game.world.data['id'],'player_review_station':station,'method':'initialized Game.update and Game.draw; native WorldCanvas960x640','fixtures':'Earlier mill-restored fact and player station; directional idle stills explicitly staged. Actual walk feet/facing/clock are controller-owned.','actual_movement_trace':trace,'activity_status':'Original activity bodies retained, not claimed HD','guardrails':{'sanctuary_gardener_not_in_scope':True,'maps_and_save_schema_unchanged':True}}
            (output/'observations.json').write_text(json.dumps(report,indent=2)+'\n')
        finally:game.music.stop();pygame.quit()

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('actor',choices=ROLES);p.add_argument('output',type=Path);a=p.parse_args();capture(a.actor,a.output)
