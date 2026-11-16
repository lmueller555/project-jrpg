"""Capture the expanded town through actual gameplay using temporary saves only."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import argparse
import gc
import json
from pathlib import Path
import sys
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pygame
from PIL import Image
from main import Game
from rendering import WorldCanvas

def capture(folder):
    folder.mkdir(parents=True,exist_ok=True);observations={}
    with tempfile.TemporaryDirectory(prefix='eldenmere-hd-review-') as directory:
        p=Path(directory);g=Game(fullscreen=False,window_size=(960,640),start_on_title=True,save_path=p/'journey.json',settings_path=p/'settings.json')
        try:
            g.on_title=False;g.opening.restore({'version':1,'stage':'disabled'});g.opening_fade=0
            def shot(name=None):
                g.camera.reset();g.draw()
                if name:pygame.image.save(g.canvas.native,str(folder/(name+'.png')))
                return Image.frombytes('RGB',g.canvas.native.get_size(),pygame.image.tobytes(g.canvas.native,'RGB'))
            for name,scene,position in [('courtyard','eldenmere.playable',(384,320)),('workshop','eldenmere.playable',(670,470)),('school_exterior','eldenmere.playable',(672,756)),('well_square','eldenmere.playable',(576,914)),('mill','eldenmere.playable',(984,372)),('residential','eldenmere.playable',(1020,648)),('elira_exterior','eldenmere.playable',(684,984)),('venn_exterior','eldenmere.playable',(1260,744)),('south_lane','eldenmere.playable',(528,1450)),('upstream','upstream',(480,288))]:
                g.world=g._scene_by_id(scene);g.player.position.update(position);shot(name)
            for room in ('halden','elira','venn','home_a','home_b','home_c','mira','mill','liam_house','school','inn','item_shop'):
                g.world=g._scene_by_id(room);g.player.position.update(g.world.data['spawn']);shot('interior_'+room)
            g.world=g.town;g.player.position.update(528,1488)
            view=WorldCanvas((768,416));g.world.draw(view,(72,1216),g.player,g.elapsed_ms,False,party_actors=g.party_travel.actors());pygame.image.save(view.native,str(folder/'business_lane_wide_native.png'))
            for running in (False,True):
                g.world=g.town;g.player.position.update(752,480);g.transfer_cooldown=0;frames=[];trace=[]
                for _ in range(72 if not running else 42):
                    g.update(1/30,(1,0),running);trace.append(list(g.player.position));g.draw()
                    view=WorldCanvas((480,320));g.town.draw(view,(600,320),g.player,g.elapsed_ms,False,party_actors=g.party_travel.actors())
                    frames.append(Image.frombytes('RGB',view.native.get_size(),pygame.image.tobytes(view.native,'RGB')))
                name='bridge_run' if running else 'bridge_walk'
                palette=frames[0].quantize(colors=256);sequence=[f.quantize(palette=palette,dither=Image.Dither.NONE) for f in frames]
                sequence[0].save(folder/(name+'.gif'),save_all=True,append_images=sequence[1:],duration=33,loop=0,optimize=False,disposal=1);observations[name]=trace
            for name in ('inn','item_shop'):
                door=next(d for d in g.town.doors if d.data['id']==name);g.world=g.town;g.transfer_cooldown=0;g.player.position.update(pygame.Vector2(door.data['anchor'])+(0,12));g.update(.5,(0,0),False);shot(name+'_door_open')
            g.world=g._scene_by_id('inn');g.player.position.update(96,150);g.transfer_cooldown=0;g.opening_fade=0
            g._update_object_cues(.12);shot('inn_rest_available')
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_e,repeat=False));g.handle_events();g.draw()
            pygame.image.save(g.window,str(folder/'inn_rest_prompt.png'));observations['inn_rest_dialogue']=g.social.script_identifier;g.social.cancel_script()
            g.world=g.town;g.player.position.update(528,1488);g.map_open=True;g.draw();pygame.image.save(g.window,str(folder/'town_map.png'));g.map_open=False
            g.world=g.town;g.player.position.update(576,914);gardener=next(n for n in g.world.npcs if n.data['id']=='sanctuary_gardener')
            g.update(gardener.rest_remaining_ms/1000+1/60,(0,0),False)
            for _ in range(3600):
                if gardener.state=='well_lower':break
                g.update(1/30,(0,0),False)
            observations['gardener_state']=gardener.state
            for i in range(4):shot('well_work_'+str(i));g.update(.65,(0,0),False)
            g.audio.set_reduced_motion(True);g.update(.1,(0,0),False);shot('reduced_motion')
            (folder/'observations.json').write_text(json.dumps(observations,indent=2)+'\n')
        finally:g.music.stop();pygame.quit();gc.collect()

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('output',type=Path);capture(parser.parse_args().output)
