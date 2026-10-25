"""Actual school renders, full-room review and walk-through of the new doorway."""
import os
os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1')
from pathlib import Path
import sys

import pygame
from PIL import Image,ImageDraw,ImageSequence
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import main
from capture_liam_house import card
from capture_liam_blocks import save_gif
from build_liam_family_front_walks import font,write

OUT=ROOT/'docs/reviews/eldenmere_school'


def setup():
    game=main.Game(fullscreen=False,start_on_title=False)
    for routine in game.play_routines+game.block_routines+game.bone_routines:routine.cooldown_ms=999999
    return game


def image_of(surface):return Image.frombytes('RGB',surface.get_size(),pygame.image.tobytes(surface,'RGB'))


def exterior_frame(game):
    box=(512,520,792,800)
    target=pygame.Surface((box[2]-box[0],box[3]-box[1]))
    game.town.draw(target,box[:2],game.player,game.elapsed_ms)
    return card(image_of(target),'Eldenmere / village school','Book sign, bell, shaded yard and path to the well square',3)


def full_room(game,room):
    # Use the normal renderer in two native viewports so its normal culling is
    # respected, then join the final 64 world rows without moving any objects.
    target=pygame.Surface(main.VIEW_SIZE)
    room.draw(target,(0,0),game.player,game.elapsed_ms)
    image=Image.new('RGB',room.size)
    image.paste(image_of(target).crop((0,0,room.size[0],main.VIEW_SIZE[1])),(0,0))
    offset=room.size[1]-main.VIEW_SIZE[1]
    room.draw(target,(0,offset),game.player,game.elapsed_ms)
    bottom=room.size[1]-main.VIEW_SIZE[1]
    image.paste(image_of(target).crop((0,main.VIEW_SIZE[1]-bottom,room.size[0],main.VIEW_SIZE[1])),(0,main.VIEW_SIZE[1]))
    return card(image,'Eldenmere school / furnished classroom','16x12 floor | six pupil seats, writing board, books and festival corner',2)


def scene_frame(game):
    camera=main.camera_for(game.player.position,game.world.size)
    game.world.draw(game.canvas,camera,game.player,game.elapsed_ms)
    name='Schoolyard' if game.world is game.town else 'Classroom'
    return card(image_of(game.canvas),'School entrance / actual game walk-through',name+' | normal walking speed and proximity door animation',2)


def save_loop(name,frames,duration):
    path=OUT/(name+'.gif');save_gif(path,frames,duration)
    with Image.open(path) as im:
        assert im.info['loop']==0
        durations=[f.info['duration'] for f in ImageSequence.Iterator(im)]
    return {'file':path.name,'frames':len(durations),'duration_ms':sum(durations),'bytes':path.stat().st_size}


def capture():
    OUT.mkdir(parents=True,exist_ok=True);report={'status':'review','actual_renderer':True,'captures':{}}
    game=setup();game.player.position.update(672,752)
    assert game.town.can_stand(game.player.position)
    game.update(.6,(0,0),False)  # Hold the nearby door open throughout the charm loop.
    frames=[]
    for _ in range(18):
        frames.append(exterior_frame(game));game.update(.3,(0,0),False)
    frames[0].save(OUT/'exterior.png')
    report['captures']['exterior']=save_loop('exterior',frames,300)
    room=game._scene_by_id('school');game.world=room;game.player.position.update(216,252)
    assert room.can_stand(game.player.position)
    frames=[];game.elapsed_ms=0
    for _ in range(36):
        frames.append(full_room(game,room));game.update(.3,(0,0),False)
    frames[0].save(OUT/'interior.png')
    report['captures']['interior']=save_loop('interior',frames,300)
    pygame.quit()
    game=setup();game.player.position.update(672,770)
    frames=[];scenes=[];doors=[]
    def tick(direction=(0,0)):
        frames.append(scene_frame(game));game.update(.1,direction,False)
        scene=game.world.data['id']
        if not scenes or scenes[-1]!=scene:scenes.append(scene)
        doors.append(next(d for d in game.town.doors if d.data['id']=='school').state)
    for _ in range(4):tick()
    for _ in range(50):
        tick((0,-1))
        if game.world is not game.town:break
    else:raise RuntimeError('Could not enter school by walking')
    for _ in range(8):tick()
    for _ in range(22):tick((0,-1))
    for _ in range(8):tick()
    for _ in range(55):
        tick((0,1))
        if game.world is game.town:break
    else:raise RuntimeError('Could not leave school by walking')
    for _ in range(9):tick((0,1))
    for _ in range(8):tick()
    report['captures']['door_walkthrough']=save_loop('door_walkthrough',frames,100)
    report['door_scenes_seen']=scenes;report['door_states_seen']=sorted(set(doors))
    report['teacher']='liam_mother';report['classroom_npcs']=len(room.npcs)
    pygame.quit()
    overview=Image.open(ROOT/'assets/maps/eldenmere/playable/overview.png').convert('RGB')
    draw=ImageDraw.Draw(overview);draw.fontmode='1'
    draw.rectangle((566,520,778,784),outline='#ffdc71',width=3)
    draw.line((777,560,1082,446),fill='#ffdc71',width=3)
    draw.rectangle((1068,418,1468,452),fill='#24302d')
    draw.text((1080,424),'Village school — northeast of the well',font=font(17),fill='#ffdc71')
    card(overview,'Eldenmere / new school location','Lower ground south of the workshop and west of the stream',1).save(OUT/'town_layout.png')
    report['scope']='Playable exterior and furnished interior; teaching and pupil routines are a later stage.'
    write(OUT/'captures.json',report)
    print('Captured exterior, whole classroom, real entrance round trip and marked town layout.',flush=True)


if __name__=='__main__':capture()
