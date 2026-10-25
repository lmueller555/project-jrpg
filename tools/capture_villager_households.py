"""Approved parent pairings and actual furnished home renders."""
import os
os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1')
from pathlib import Path
import sys
import pygame
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import main
from capture_liam_house import card
from capture_liam_blocks import save_gif
from build_liam_family_front_walks import font,write
OUT=ROOT/'docs/reviews/villager_households'


def room_image(game,room):
    surface=pygame.Surface(main.VIEW_SIZE);room.draw(surface,(0,0),game.player,game.elapsed_ms)
    image=Image.new('RGB',room.size);image.paste(Image.frombytes('RGB',main.VIEW_SIZE,pygame.image.tobytes(surface,'RGB')).crop((0,0,room.size[0],320)),(0,0))
    offset=max(0,room.size[1]-320)
    if offset:
        room.draw(surface,(0,offset),game.player,game.elapsed_ms)
        image.paste(Image.frombytes('RGB',main.VIEW_SIZE,pygame.image.tobytes(surface,'RGB')).crop((0,320-offset,room.size[0],320)),(0,320))
    return image


def run():
    OUT.mkdir(parents=True,exist_ok=True)
    registry=main.read_json(ROOT/'assets/maps/eldenmere/households/households.json')
    board=Image.new('RGB',(1152,416),'#e8edf2');draw=ImageDraw.Draw(board);draw.fontmode='1'
    draw.text((24,14),'Eldenmere / three parent pairs',font=font(26),fill='#26343e')
    draw.text((24,52),'Approved sprites | names and children remain unassigned',font=font(18),fill='#52616c')
    game=main.Game(fullscreen=False,start_on_title=False)
    for r in game.play_routines+game.block_routines+game.bone_routines:r.cooldown_ms=999999
    reports={}
    for index,family in enumerate(registry['households']):
        x=index*384
        draw.text((x+24,92),family['home'],font=font(22),fill='#26343e')
        for j,role in enumerate(('mother','father')):
            m=family[role];sprite=Image.open(ROOT/m['sprite_root']/'idle_front.png').convert('RGBA')
            enlarged=sprite.resize((144,216),Image.Resampling.NEAREST);board.paste(enlarged,(x+24+j*168,128),enlarged)
            draw.text((x+24+j*168,356),role.title(),font=font(20),fill='#26343e')
        draw.text((x+24,389),'Mother works at sanctuary' if index==0 else family['label'],font=font(17),fill='#52616c')
        room=game._scene_by_id(family['home']);game.world=room;game.player.position.update(178,292)
        frames=[]
        subtitle='Father at home | mother is the existing sanctuary gardener' if index==0 else 'Both parents at home | actual game placement'
        for tick in range(36):
            game.elapsed_ms=tick*300
            frames.append(card(room_image(game,room),family['label']+' / '+family['home'],subtitle,2))
        frames[0].save(OUT/(family['home']+'.png'));save_gif(OUT/(family['home']+'.gif'),frames,300)
        reports[family['home']]={'household':room.data['household'],'present':[a.data['id'] for a in room.npcs]}
    board.save(OUT/'parent_pairs.png')
    overview=Image.open(ROOT/game.town.data['overview']).convert('RGB');d=ImageDraw.Draw(overview);d.fontmode='1'
    for family,color in zip(registry['households'],('#ffda72','#e4b7f0','#b3e3a2')):
        e=next(e for e in game.town.entities if e['id']==family['home']);x,y=e['position']
        d.rectangle((x-6,y-4,x+126,y+148),outline=color,width=3)
        d.rectangle((x-8,y+149,x+172,y+175),fill='#24302d')
        d.text((x-2,y+153),family['home']+' / parents',font=font(15),fill=color)
    overview.save(OUT/'assigned_homes.png')
    write(OUT/'captures.json',{'status':'review','reports':reports,'gardener_stays_in_town':True,'pair_board_uses_approved_reference_sprites':True})
    pygame.quit();print('Captured three actual homes, parent-pair reference and marked town map.')


if __name__=='__main__':run()
