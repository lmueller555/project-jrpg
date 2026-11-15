"""Actual Player movement and production composition, using temporary saves only."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
from pathlib import Path
import sys
import tempfile
import json
import hashlib
import math
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import pygame
from main import Game,Player,WALK_SPEED,camera_for
from rendering import WorldCanvas,snapshot,surface_bytes

OUT=ROOT/'docs/reviews/caelan_walk_integration'
DT=.035
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'

def square(world,seed):
    distance=WALK_SPEED*DT*32
    # Search ordinary traversable floor; do not remove furniture or collision.
    candidates=[pygame.Vector2(x,y) for y in range(max(36,int(seed[1])-160),min(world.size[1]-12,int(seed[1])+161),8)
                for x in range(max(12,int(seed[0])-160),min(world.size[0]-110,int(seed[0])+161),8)]
    candidates.sort(key=lambda p:p.distance_squared_to(seed))
    for point in candidates:
        corners=[point,point+pygame.Vector2(distance,0),point+pygame.Vector2(distance,-distance),point+pygame.Vector2(0,-distance)]
        if all(world.can_stand(a.lerp(b,k/81)) for a,b in zip(corners,corners[1:]+corners[:1]) for k in range(82)):
            return corners
    raise ValueError('No clear 80-unit review square in '+world.data['id'])

def render(world,player,camera,overlay=None):
    canvas=WorldCanvas((480,320))
    world.draw(canvas,camera,player,0,False)
    if overlay is not None:overlay(canvas,camera)
    raw=snapshot(canvas)
    return Image.frombytes('RGB',raw.get_size(),pygame.image.tobytes(raw,'RGB'))

def card(image,label):
    out=Image.new('RGB',(560,440),'#252e35')
    out.paste(image.crop((200,120,760,520)),(0,40))
    ImageDraw.Draw(out).text((12,10),label,font=ImageFont.truetype(FONT,15),fill='#edf0e9')
    return out

def gif(path,frames):
    packed=Image.new('RGB',(frames[0].width*8,frames[0].height*math.ceil(len(frames)/8)))
    for i,im in enumerate(frames):packed.paste(im,(i%8*im.width,i//8*im.height))
    palette=packed.quantize(colors=256,dither=Image.Dither.NONE)
    indexed=[im.quantize(palette=palette,dither=Image.Dither.NONE) for im in frames]
    indexed[0].save(path,save_all=True,append_images=indexed[1:],duration=([30,40]*math.ceil(len(frames)/2))[:len(frames)],loop=0,disposal=2,optimize=False)

def capture():
    OUT.mkdir(parents=True,exist_ok=True)
    evidence={'movement':'Player.update with real collision; World.draw at native density',
              'fixture':'Temporary saves/settings, frozen scenery; ordinary travel is isolated, staged cup review advances SanctuaryReturn only',
              'step_ms':35,'walking_speed_world_units_s':WALK_SPEED,'scenes':{},'legacy_transitions':[]}
    with tempfile.TemporaryDirectory(prefix='caelan-hd-integration-') as directory:
        p=Path(directory);game=Game(fullscreen=False,start_on_title=True,window_size=(960,640),save_path=p/'journey.json',settings_path=p/'settings.json')
        try:
            player=game.player
            for attribute in ('story_sprite','story_position','story_draw_anchor','story_sort_y'):
                if hasattr(player,attribute):delattr(player,attribute)
            quests=game.quests.to_dict()
            for name,scene,seed in [('town','eldenmere.playable',(456,936)),('hall','sanctuary_hall',(140,276)),('cave','sanctuary_cave',(1460,1520))]:
                world=game._scene_by_id(scene);corners=square(world,seed)
                player.position.update(corners[0]);player.walk_ms=0;player.running=player.moving=False
                center=(corners[0]+corners[2])/2;camera=camera_for(center,world.size)
                frames=[];events=[];samples=[]
                for direction,vector in [('right',(1,0)),('back',(0,-1)),('left',(-1,0)),('front',(0,1))]:
                    for tick in range(38):
                        before=player.position.copy()
                        player.update(vector if tick<32 else (0,0),DT,world)
                        if tick<32:
                            assert player.moving
                            assert abs(player.position.distance_to(before)-WALK_SPEED*DT)<1e-6
                        image=render(world,player,camera)
                        frames.append(card(image,f'Caelan / {name} / {direction} / '+('WALK' if player.moving else 'IDLE')))
                        events.append({'facing':player.facing,'moving':player.moving,'walk_ms':round(player.walk_ms,3),'position':list(player.position)})
                        if tick==15:
                            image.save(OUT/f'{name}_{direction}.png');samples.append(image)
                assert player.position.distance_to(corners[0])<1e-6
                gif(OUT/f'{name}_travel.gif',frames)
                sheet=Image.new('RGB',(960,640))
                for i,image in enumerate(samples):sheet.paste(image.resize((480,320),Image.Resampling.NEAREST),(i%2*480,i//2*320))
                sheet.save(OUT/f'{name}_directions.png')
                evidence['scenes'][name]={'scene':scene,'corners':[list(c) for c in corners],'camera':list(camera),'frames':events}
                if name=='hall':
                    player.position.update(corners[0]);transitions=[]
                    for mode,vector,count,running in [('WALK HD',(1,0),32,False),('IDLE HD',(0,0),8,False),('RUN legacy',(-1,0),20,True),('IDLE HD',(0,0),8,False)]:
                        for tick in range(count):
                            player.update(vector,DT,world,running)
                            transitions.append(card(render(world,player,camera),'Caelan / '+mode))
                    gif(OUT/'walk_run_transitions.gif',transitions)
                    evidence['legacy_transitions'].append('Running uses original 24x36 four-frame drawings; idle/walk remain HD.')
            # Real town foreground at its normal painter depth.
            world=game.town;tree=next(e for e in world.entities if e['id']=='sanctuary.shade_tree')
            covered=None
            for y in range(250,324,2):
                for x in range(200,286,2):
                    position=pygame.Vector2(x,y)
                    if not world.can_stand(position):continue
                    pixel=(round(x-tree['rect'].x),round(y-27-tree['rect'].y))
                    if not tree['surfaces'][0].get_rect().collidepoint(pixel):continue
                    if tree['surfaces'][0].get_at(pixel).a<128:continue
                    player.position.update(position);player.facing='right';player.moving=True;player.running=False;player.walk_ms=245
                    render(world,player,camera_for(position,world.size)).save(OUT/'tree_occlusion.png')
                    covered={'entity':tree['id'],'position':list(position),'sort_y':tree['sort_y']};break
                if covered:break
            assert covered is not None
            evidence['foreground']=covered
            # The cup scene owns its legacy body/grip while carrying. Stage
            # only transient holding state; no pickup/completion callback runs.
            from sanctuary_return import SOURCE
            cups=game.mill_quest.sanctuary_return;game.world=cups.dining
            assert cups.prepare()
            player.position.update(SOURCE);player.moving=player.running=False
            cups._holding=True;cups.action='carry';cups.action_time=0.;cups._route=None
            camera=camera_for((200,150),cups.dining.size);carrying=[]
            for tick in range(120):
                cups.update(DT)
                image=render(cups.dining,player,camera,cups.draw_world)
                carrying.append(card(image,'Caelan / cup delivery / scene-owned legacy grip'))
                if tick==30:image.save(OUT/'cup_carry.png')
            gif(OUT/'cup_carry.gif',carrying)
            cups.release()
            assert getattr(player,'story_sprite',None) is None
            evidence['legacy_transitions'].append('Cup carrying retains the four-phase legacy body/grip; release restores HD travel.')
            assert game.quests.to_dict()==quests
            evidence['quests_unchanged']=True
            surfaces=list(player.idles.values())+[f for bank in (player.walks,player.runs) for frames in bank.values() for f,_ in frames]
            evidence['loaded_player_surface_bytes']=sum(surface_bytes(f) for f in surfaces)
            # Sole-span endpoints are visible rolling contact observations, not
            # ankle positions: retain this as a sliding diagnostic, not a rig.
            evidence['side_stance_diagnostics']={}
            for direction,sign in [('right',1),('left',-1)]:
                meta=json.loads((ROOT/f'assets/characters/caelan/review_hd/walk_{direction}/animation.json').read_text())
                spans=[meta['frames'][i]['support_ground_interval'] for i in (0,7)]
                relative=((spans[1][0]+spans[1][2])-(spans[0][0]+spans[0][2]))/2
                travel=sign*WALK_SPEED*DT*7*2
                evidence['side_stance_diagnostics'][direction]={'native_actor_travel':round(travel,2),
                    'observed_sole_span_midpoint_delta':relative,'estimated_world_span_drift_native_px':round(travel+relative,2),
                    'limit':'Rolling sole midpoint is an approximate indicator; it is not an ankle/heel lock measurement.'}
            evidence['approved_png_sha256']={str(file.relative_to(ROOT)):hashlib.sha256(file.read_bytes()).hexdigest()
                for file in sorted((ROOT/'assets/characters/caelan/review_hd').rglob('*.png'))}
            (OUT/'evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
            print('Captured native Player travel in town/hall/cave, gait transitions and real foreground occlusion.')
        finally:game.music.stop();pygame.quit()

if __name__=='__main__':capture()
