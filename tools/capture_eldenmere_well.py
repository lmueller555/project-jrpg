"""Review the implemented well square with the actual town renderer."""
import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT']='1'

import json
from pathlib import Path
import subprocess
import sys

from PIL import Image, ImageDraw
import pygame

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import main
from capture_gardener import font, gif, panel, render

OUTPUT=ROOT/'docs/reviews/eldenmere_well'
BEFORE_COMMIT='1ae774a5c8901b7f15cc4af8163fde8c1377e869'


def town_layout(game):
    overview=Image.open(ROOT/game.world.data['overview']).convert('RGB')
    board=Image.new('RGB',(1840,1440),'#e8edf2');board.paste(overview,(24,72))
    d=ImageDraw.Draw(board);d.fontmode='1'
    d.text((24,14),'Eldenmere / implemented well square',font=font(28),fill='#24382f')
    d.text((24,48),'64 x 56 tiles | 24px terrain | new square and southern connection',font=font(16),fill='#526761')
    labels={'sanctuary':'Sanctuary','mira':"Mira's workshop",'mill':'Watermill',
            'halden':"Halden's cottage",'elira':"Elira's cottage",'venn':'Venn family cottage',
            'home_a':'Village home A','home_b':'Village home B','home_c':'Village home C'}
    for i,door in enumerate(game.world.doors,1):
        x,y=door.data['anchor'];x+=24;y+=72
        d.ellipse((x-10,y-10,x+10,y+10),fill='#24382f',outline='#e8edf2',width=1)
        d.text((x-5,y-8),str(i),font=font(13),fill='#e8edf2')
        d.text((1584,120+(i-1)*34),f'{i}. {labels[door.data["id"]]}',font=font(17),fill='#24382f')
    d.rectangle((24+384,72+768,24+624,72+960),outline='#e3c46e',width=2)
    d.rectangle((24+504,72+960,24+552,72+1008),outline='#e3c46e',width=2)
    d.text((1584,466),'NEW WELL SQUARE',font=font(20),fill='#24382f')
    for i,text in enumerate(('10 x 8 tile commons','2 x 2 tile well base','Rounded dirt edges','Worn stone apron','Southern path link','Open gathering side')):
        d.text((1584,510+i*30),text,font=font(17),fill='#526761')
    d.text((1584,740),'Gold outline:',font=font(18),fill='#24382f')
    d.text((1584,770),'new square and path',font=font(16),fill='#526761')
    board.save(OUTPUT/'town_layout.png')
    before_path=OUTPUT/'before_overview.png'
    if not before_path.exists():
        before_path.write_bytes(subprocess.check_output(['git','show',f'{BEFORE_COMMIT}:assets/maps/eldenmere/playable/overview.png'],cwd=ROOT))
    before=Image.open(before_path).convert('RGB').crop((288,672,936,1104))
    after=overview.crop((288,672,936,1104))
    comparison=Image.new('RGB',(1296,512),'#e8edf2');draw=ImageDraw.Draw(comparison);draw.fontmode='1'
    draw.text((16,12),'Before / existing commons',font=font(24),fill='#24382f')
    draw.text((664,12),'After / well square',font=font(24),fill='#24382f')
    comparison.paste(before,(0,60));comparison.paste(after,(648,60))
    comparison.save(OUTPUT/'commons_before_after.png')


def capture():
    OUTPUT.mkdir(parents=True,exist_ok=True)
    game=main.Game();game.player.position.update(480,924);game.player.facing='left'
    town_layout(game)
    # Drive the real player around all four sides. Remaining footage rests at
    # the starting point so the 10.8s environment clock closes cleanly.
    targets=[(480,816),(576,816),(576,924),(480,924)];target_index=0
    frames=[]
    for index in range(108):
        scene=render(game,(336,720)).crop((0,0,432,320))
        frames.append(panel(scene,2,'Eldenmere / well square in-game',
                            'Actual renderer | Caelan explores the square | 2x enlargement',
                            'Stone well / water glints / clear paths around all four sides'))
        remaining=.1
        while remaining>1e-8:
            if target_index>=len(targets):game.update(remaining,(0,0),False);break
            delta=pygame.Vector2(targets[target_index])-game.player.position
            if delta.length()<1e-6:target_index+=1;continue
            dt=min(remaining,delta.length()/main.WALK_SPEED)
            before=game.player.position.copy();game.update(dt,delta,False);remaining-=dt
            if before==game.player.position:raise RuntimeError('Square review route is blocked')
    if target_index<len(targets):raise RuntimeError('Square walk did not complete')
    frames[0].save(OUTPUT/'well_square.png')
    gif(OUTPUT/'well_square.gif',frames)
    closeups=[];game.player.position.update(528,900);game.player.facing='back'
    for index in range(12):
        # Capture one exact 1.2s water cycle, with Caelan beside the well.
        game.world.draw(game.canvas,(444,768),game.player,index*100)
        image=Image.frombytes('RGB',main.VIEW_SIZE,pygame.image.tobytes(game.canvas,'RGB')).crop((0,0,168,144))
        closeups.append(panel(image,4,'Eldenmere / village well',
                              'Native 24px world | Caelan for scale | 4x enlargement',
                              'Fixed stone, timber and windlass / gentle shaft-water movement'))
    closeups[0].save(OUTPUT/'well_closeup.png')
    gif(OUTPUT/'well_closeup.gif',closeups)
    (OUTPUT/'capture.json').write_text(json.dumps({
        'status':main.read_json(ROOT/'assets/terrain/eldenmere/well/well.json')['status'],
        'before_commit':BEFORE_COMMIT,'source_map':game.world.path.relative_to(ROOT).as_posix(),
        'well_position':[486,792],'ground_rect':[504,840,48,48],
        'square_rect_tiles':[16,32,10,8],'scene_duration_ms':10800,
        'closeup_duration_ms':1200,'walk_completed':True
    },indent=2)+'\n')
    pygame.quit()


if __name__=='__main__':capture()
