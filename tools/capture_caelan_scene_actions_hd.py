"""Production scene staging/crops for HD action review; temporary saves only."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy');os.environ.setdefault('SDL_AUDIODRIVER','dummy')
from pathlib import Path
import sys,tempfile,json
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import pygame
from PIL import Image,ImageDraw
from main import Game,camera_for
from rendering import WorldCanvas,snapshot
from caelan_scene_art import image as scene_image
OUT=ROOT/'docs/reviews/caelan_scene_actions_hd'
def capture():
    OUT.mkdir(parents=True,exist_ok=True);cards=[];report=[]
    with tempfile.TemporaryDirectory(prefix='caelan-scene-review-') as directory:
        p=Path(directory);game=Game(fullscreen=False,start_on_title=True,window_size=(960,640),save_path=p/'journey.json',settings_path=p/'settings.json')
        try:
            player=game.player
            def clear():
                for key in ('story_sprite','story_position','story_draw_anchor','story_sort_y'):
                    if hasattr(player,key):delattr(player,key)
                player.story_visible=True;player.moving=player.running=False
            def take(label,world,position,overlay=None):
                player.position.update(position);camera=camera_for(position,world.size)
                canvas=WorldCanvas((480,320));world.draw(canvas,camera,player,0,False)
                if overlay:overlay(canvas,camera)
                raw=snapshot(canvas);im=Image.frombytes('RGB',raw.get_size(),pygame.image.tobytes(raw,'RGB'));im.save(OUT/(label+'.png'))
                x=round((position[0]-camera[0])*2);y=round((position[1]-camera[1])*2)
                crop=Image.new('RGB',(320,240),'#26322f');crop.paste(im.crop((x-160,y-160,x+160,y+80)),(0,0));ImageDraw.Draw(crop).text((8,8),label,fill='white');cards.append(crop)
                report.append({'label':label,'scene':world.data['id'],'position':list(position),'camera':list(camera),'logical_sprite_size':list(player.story_sprite.get_size()),'native_sprite_size':list(player.story_sprite.native.get_size())})
            clear();world=game._scene_by_id('sanctuary_dining');game.world=world
            for name in ['caelan_sit','caelan_eat','caelan_seated_cup']:
                if name=='caelan_seated_cup':
                    game.opening.stage='breakfast';game.opening._start_cup()
                for i in range(4):
                    frames=game.opening._animation(name);t=sum(r['duration_ms'] for r in frames[:i])/1000+.001
                    if name=='caelan_seated_cup':game.opening._actions[0]['update'](t)
                    else:game.opening._pose(player,name,t,game.opening.data['caelan_seated_position'])
                    take(name+'_'+str(i),world,game.opening.data['caelan_seated_position'],game.opening.draw_world if name=='caelan_seated_cup' else None)
            clear();visit=game.halden_visit;game.world=visit.home
            from halden_visit import SOURCES
            position=(SOURCES[0][0],SOURCES[0][1]+18)
            for i in range(4):
                visit._pose(player,'caelan','lift','back',i);take('sack_lift_'+str(i),visit.home,position)
            clear();visit=game.venn_visit;game.world=game.town
            from venn_visit import PIN_APPROACH
            for i in range(4):
                visit._pose('tools_'+str(i));take('gate_work_'+str(i),game.town,PIN_APPROACH)
            clear();world=game._scene_by_id('sanctuary_cave');game.world=world
            for i in range(4):
                player.story_sprite=scene_image(world,f'assets/story/sanctuary_rescue/actions/row_5_{i}.png');player.story_draw_anchor=(20,34)
                take('cave_assist_'+str(i),world,(1460,1520))
        finally:pygame.quit()
    sheet=Image.new('RGB',(320*4,240*((len(cards)+3)//4)))
    for i,im in enumerate(cards):sheet.paste(im,(i%4*320,i//4*240))
    timings=[[f['duration_ms'] for f in game.opening._animation(n)] for n in ('caelan_sit','caelan_eat','caelan_seated_cup')]+[[180]*4,[200]*4,[320]*4]
    for i,name in enumerate(('sit','eat','cup_pass','sack_lift','gate_work','cave_assist')):
        frames=cards[i*4:i*4+4]
        frames[0].save(OUT/(name+'.gif'),save_all=True,append_images=frames[1:],duration=timings[i],loop=0,disposal=2)
    sheet.save(OUT/'scene_contact_sheet.png');(OUT/'scene_review.json').write_text(json.dumps({'method':'Staged registered production scene poses with World.draw, collision/furniture unchanged. This is visual evidence, not a complete gameplay replay. Lifecycle and transfer checks live in focused tests.','frames':report},indent=2)+'\n')
if __name__=='__main__':capture()
