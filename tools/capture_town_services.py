"""Capture real town-service input flows with disposable saves and settings."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import argparse
import json
from pathlib import Path
import sys
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pygame
from main import Game


def capture(folder):
    folder.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='town-services-review-') as directory:
        root=Path(directory)
        g=Game(fullscreen=False,window_size=(960,640),start_on_title=True,
               save_path=root/'save.json',settings_path=root/'settings.json')
        try:
            g.on_title=False;g.opening.stage='disabled';g.opening_fade=g.transfer_cooldown=0
            def station(scene,position):
                g.world=g._scene_by_id(scene);g.player.position.update(position)
                g.player.facing='back';g.camera.reset()
            def key(value):
                g.handle_events([pygame.event.Event(pygame.KEYDOWN,key=value,repeat=False),
                                 pygame.event.Event(pygame.KEYUP,key=value)])
            def shot(name):
                g.draw();pygame.image.save(g.window,str(folder/(name+'.png')))
            def choose(action):
                for _ in range(30):
                    if g.social.choosing:break
                    key(pygame.K_SPACE)
                if not g.social.choosing:raise RuntimeError('No service choices')
                g.draw();index=next(i for i,r in enumerate(g.social.choice_options) if r['action']==action)
                rect=g.social.choice_rects[index];point=(round(rect.centerx*2),round(rect.centery*2))
                g.handle_events([pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=point),
                                 pygame.event.Event(pygame.MOUSEBUTTONUP,button=1,pos=point)])
            station('item_shop',(216,188));key(pygame.K_e);choose('buy')
            shot('shop');key(pygame.K_RIGHT);key(pygame.K_RETURN);shot('purchase_confirmation')
            key(pygame.K_RETURN);shot('purchase_complete')
            g.audio.set_text_scale(1.5);shot('shop_large_text')
            key(pygame.K_DOWN);key(pygame.K_DOWN);key(pygame.K_DOWN);key(pygame.K_DOWN)
            shot('rest_kit_large_text');key(pygame.K_ESCAPE)
            g.update(.1,(0,0),False)
            g.audio.set_text_scale(1.0);station('inn',(168,160));g.attributes.set_current(hp=7,mp=1)
            key(pygame.K_e)
            for _ in range(30):
                if g.social.choosing:break
                key(pygame.K_SPACE)
            shot('inn_confirmation');g.audio.set_text_scale(1.5);shot('inn_large_text')
            choose('rest');g.audio.set_text_scale(1.0);shot('inn_recovered')
            for _ in range(30):
                if not g.social.active:break
                key(pygame.K_SPACE)
            g.update(.8,(0,0),False)
            key(pygame.K_i);shot('satchel_gold')
            observations={'gold':g.wallet.gold,'potion_count':g.inventory.quantity('potion'),
                          'hp':g.attributes.current_hp,'max_hp':g.attributes.value('hp'),
                          'autosave_reasons':[e['metadata']['reason'] for e in g.saves.library.autos(g.saves.campaign)],
                          'save_scope':'Disposable temporary journey and settings; no player saves touched.'}
            (folder/'observations.json').write_text(json.dumps(observations,indent=2)+'\n')
        finally:g.music.stop();pygame.quit()

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('folder',type=Path)
    capture(parser.parse_args().folder)
