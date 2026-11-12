"""Production-rendered nonpersistent Echo Chamber scenery and boss art study."""
from pathlib import Path
import os,sys,json,hashlib
os.environ.setdefault('SDL_VIDEODRIVER','dummy');os.environ.setdefault('SDL_AUDIODRIVER','dummy');os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import pygame
from PIL import Image
from main import Game
from sanctuary_cave import SCENE_ID
from battle_model import BattleModel
from battle_scene import BattleScene
from sanctuary_boss_entry import SanctuaryBossEntry
OUT=ROOT/'docs/reviews/echo_chasm'

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    pygame.init();pygame.display.set_mode((960,640))
    game=Game(fullscreen=False,start_on_title=False,_preview_window=pygame.Surface((960,640)))
    game.audio.set_music(0);game.audio.set_effects(0)
    game.world=game._scene_by_id(SCENE_ID);game.player.position.update(2060,390)
    camera=(1844,110);frames=[]
    def save(surface,name):
        scaled=pygame.transform.scale(surface,(960,640));pygame.image.save(scaled,str(OUT/name))
        return Image.frombytes('RGB',scaled.get_size(),pygame.image.tobytes(scaled,'RGB'))
    try:
        for time in range(0,12000,500):
            game.world.chasm_elapsed_ms=time
            game.world.draw(game.canvas,camera,game.player,time,include_ui=False)
            frames.append(save(game.canvas,'exploration.png') if time==4000 else Image.frombytes('RGB',(960,640),pygame.image.tobytes(pygame.transform.scale(game.canvas,(960,640)),'RGB')))
        frames[0].save(OUT/'exploration.gif',save_all=True,append_images=frames[1:],duration=500,loop=0)
        game.world.reduced_motion=True
        game.world.draw(game.canvas,camera,game.player,4000,include_ui=False)
        save(game.canvas,'reduced_motion.png');game.world.reduced_motion=False
        # Two-member display fixture only; no quests or persistent recruitment.
        game.party.recruit('mira')
        model=BattleModel.from_bestiary(game.attributes,'vespermaw',7,party_members=game.party.battle_members(),weapon_equipped=True)
        scene=BattleScene(game,model,battlefield='cave_echo_chamber')
        scene._elapsed=4.
        scene.draw(game.canvas,game.ui_surface)
        pygame.image.save(game.ui_surface,str(OUT/'combat.png'))
        entry=SanctuaryBossEntry(game.canvas,(240,160),intro_seen=False,reduced_motion=True,audio_settings=game.audio)
        entry.elapsed=.3;entry.draw(game,game.canvas,game.ui_surface)
        pygame.image.save(game.ui_surface,str(OUT/'intro_reduced.png'));entry.stop_audio()
        Image.open(ROOT/'assets/terrain/limestone_cave/chasm/modules.png').resize((768,384),Image.Resampling.NEAREST).save(OUT/'modules.png')
        assert not game.save_store.enabled
        data={'scope':'Disposable visual fixtures using production world and BattleScene renderers. No played encounter or quest completion is claimed.','exploration_times_ms':list(range(0,12000,500)),'camera':list(camera),'persistent_save_enabled':False,'battle_fixture':'Level-seven Vespermaw, two member display fixture','fingerprints':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ('assets/maps/sanctuary_cave/map.json','assets/combat/cave_echo_chamber/battlefield.json','cave_chasm_fx.py','sanctuary_boss_entry.py','tools/capture_echo_chasm.py')}}
        (OUT/'evidence.json').write_text(json.dumps(data,indent=2)+'\n')
        print('Captured Echo Chamber world, Reduced Motion intro and boss battlefield')
    finally:game.regional_audio.stop();game.music.stop();pygame.quit()
if __name__=='__main__':main()
