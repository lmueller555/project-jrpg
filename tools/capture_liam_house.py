"""Capture actual gameplay at the new home plus a marked town overview."""
import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT']='1'
import sys
from pathlib import Path

import pygame
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import main
from build_liam_family_front_walks import font,save_gif

REVIEW=ROOT/'docs/reviews/liam_family_home'


def card(image,title,subtitle,scale=2):
    enlarged=image.resize((image.width*scale,image.height*scale),Image.Resampling.NEAREST)
    out=Image.new('RGB',(enlarged.width,enlarged.height+88),'#e8edf2')
    d=ImageDraw.Draw(out);d.fontmode='1'
    d.text((20,12),title,font=font(24),fill='#26343e')
    d.text((20,48),subtitle,font=font(17),fill='#52616c')
    out.paste(enlarged,(0,88));return out


def capture():
    REVIEW.mkdir(parents=True,exist_ok=True)
    game=main.Game(fullscreen=False,start_on_title=False)
    recipe=main.read_json(ROOT/'assets/maps/eldenmere/liam_house/house.json')
    game.player.position.update(288,558)
    game.update(.6,(0,0),False)  # Let proximity open the door normally.
    frames=[]
    for i in range(18):
        game.update(.2,(0,0),False)
        game.draw()
        im=Image.frombytes('RGB',main.VIEW_SIZE,pygame.image.tobytes(game.canvas,'RGB'))
        frames.append(card(im,"Liam's family cottage / in-game exterior",'Wide cottage south of the sanctuary | chimney smoke and lantern',2))
    frames[0].save(REVIEW/'exterior.png')
    save_gif(REVIEW/'exterior.gif',frames,200)
    game.world=game._load_scene(ROOT/game.town.data['interior_scenes']['liam_house'])
    game.player.position.update(214,270);game.elapsed_ms=0
    assert game.world.can_stand(game.player.position)
    game.draw()
    im=Image.frombytes('RGB',main.VIEW_SIZE,pygame.image.tobytes(game.canvas,'RGB'))
    card(im,"Liam's family cottage / furnished interior",'16x10 floor | two beds, four dining seats, kitchen and hearth',2).save(REVIEW/'interior.png')
    pygame.quit()
    with Image.open(ROOT/'assets/maps/eldenmere/playable/overview.png') as native:
        overview=native.convert('RGB')
    marked=overview.copy();d=ImageDraw.Draw(marked);d.fontmode='1'
    d.rectangle((196,426,354,536),outline='#ffdc71',width=3)
    d.line((353,436,440,406),fill='#ffdc71',width=3)
    d.rectangle((435,384,622,412),fill='#24302d')
    d.text((442,390),"Liam's family cottage",font=font(15),fill='#ffdc71')
    card(marked,'Eldenmere / new family home','Highlighted cottage immediately south of the sanctuary, west of the lane',1).save(REVIEW/'town_layout.png')
    card(overview.crop((120,96,552,672)),"Sanctuary and Liam's family home",'Same lower-ground level as the village lane | separate from the eastern Venn home',2).save(REVIEW/'neighborhood.png')
    print('Captured actual gameplay exterior GIF, interior and marked town layout.')


if __name__=='__main__':capture()
