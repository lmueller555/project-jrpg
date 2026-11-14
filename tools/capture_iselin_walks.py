"""Review registered Iselin walks through town navigation and production depth rendering."""
from pathlib import Path
from hashlib import sha256
import json
import os
import sys
import tempfile

os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import pygame
from PIL import Image,ImageDraw,ImageFont
from main import camera_for
from regent_actors import StoryActor
from tools.capture_sanctuary_rescue import make_game

OUT=ROOT/'docs/reviews/iselin_walk_integration'
SPEED=74
DT=.035


def render(game,camera):
    game.canvas.reset_detail()
    # Freeze scenery while reviewing the actor's actual walk clock.
    game.world.draw(game.canvas,camera,game.player,0,include_ui=False)
    target=pygame.transform.scale(game.canvas,(960,640))
    game.canvas.present_detail(target)
    return Image.frombytes('RGB',target.get_size(),pygame.image.tobytes(target,'RGB'))


def square(world,actor):
    distance=SPEED*DT*32
    for y in range(480,680,12):
        for x in range(330,720,12):
            corners=[pygame.Vector2(x,y),pygame.Vector2(x+distance,y),
                     pygame.Vector2(x+distance,y-distance),pygame.Vector2(x,y-distance)]
            if all(world.can_stand(start.lerp(end,i/64),actor.probe_size)
                   for start,end in zip(corners,corners[1:]+corners[:1]) for i in range(65)):
                return corners
    raise ValueError('No collision-free review square')


def capture():
    OUT.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as directory:
        game=make_game(directory,seed=False,embedded=False)
        try:
            game.world=game.town;game.on_title=False
            before=game.quests.to_dict()
            record=json.loads((ROOT/'assets/characters/iselin/actor.json').read_text())
            actor=StoryActor(record,game.world);actor.story_visible=True
            corners=square(game.world,actor);actor.position.update(corners[0])
            game.world.npcs.append(actor);game.regent_quest._worlds[actor]=game.world
            game.player.position.update(corners[0]+pygame.Vector2(40,40))
            assert game.world.can_stand(game.player.position,game.world.probe_size)
            game.player.moving=False;game.player.story_visible=True
            # The review stages ordinary standing Caelan, not the opening's bed pose.
            for attribute in ('story_sprite','story_position','story_draw_anchor','story_sort_y'):
                if hasattr(game.player,attribute):delattr(game.player,attribute)
            camera=camera_for((corners[0]+corners[2])/2,game.world.size)
            font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',15)
            frames=[];samples=[];events=[]
            for direction,end in zip(('right','back','left','front'),corners[1:]+corners[:1]):
                for tick in range(40):
                    if tick<32:
                        game.regent_quest._move(actor,end,DT,SPEED)
                        mode='WALK'
                    else:
                        game.regent_quest._move(actor,end,DT,SPEED)
                        assert not actor.moving
                        mode='IDLE'
                    assert game.world.can_stand(actor.position,actor.probe_size,actor)
                    image=render(game,camera)
                    if tick==15:
                        image.save(OUT/f'{direction}.png');samples.append(image)
                    card=Image.new('RGB',(480,436),'#e8edf2')
                    card.paste(image.crop((240,120,720,520)),(0,36))
                    ImageDraw.Draw(card).text((12,9),f'Iselin / {direction.upper()} / {mode} / actual town renderer',font=font,fill='#263c35')
                    frames.append(card)
                    events.append({'direction':actor.facing,'moving':actor.moving,'walk_ms':round(actor.walk_ms,4),
                                   'position':list(actor.position),'detail':actor.detailed_sprite(0) is not None})
            assert game.quests.to_dict()==before
            # A real foreground tree, rendered after the actor in normal depth order.
            tree=next(entity for entity in game.world.entities if entity['id']=='sanctuary.shade_tree')
            occlusion=None
            for y in range(250,324,2):
                for x in range(200,286,2):
                    position=pygame.Vector2(x,y)
                    if not game.world.can_stand(position,actor.probe_size,actor):continue
                    # Require actual opaque tree pixels over the actor's crown.
                    pixel=(round(x-tree['rect'].x),round(y-27-tree['rect'].y))
                    if not tree['surfaces'][0].get_rect().collidepoint(pixel):continue
                    if tree['surfaces'][0].get_at(pixel).a<128:continue
                    actor.position.update(position);actor.facing='right';actor.moving=True;actor.walk_ms=245
                    render(game,camera_for(position,game.world.size)).save(OUT/'tree_occlusion.png')
                    occlusion={'entity':tree['id'],'position':list(position),'tree_sort_y':tree['sort_y']}
                    break
                if occlusion:break
            assert occlusion is not None
            sheet=Image.new('RGB',(960,640))
            for i,image in enumerate(samples):sheet.paste(image.resize((480,320),Image.Resampling.NEAREST),((i%2)*480,(i//2)*320))
            sheet.save(OUT/'directions.png')
            frames[0].save(OUT/'travel.gif',save_all=True,append_images=frames[1:],duration=[30,40]*80,loop=0,disposal=2)
            (OUT/'evidence.json').write_text(json.dumps({
                'renderer':'World.draw + WorldCanvas.present_detail','movement':'RegentQuest._move',
                'fixture':'Temporary save/settings; review actor only; no regent replacement',
                'walking_speed_world_px_s':SPEED,'step_ms':35,'scenery_elapsed_ms':0,
                'camera':list(camera),'corners':[list(c) for c in corners],
                'quests_unchanged':True,'tree_occlusion':occlusion,'frames':events,
                'approved_frame_sha256':{str(path.relative_to(ROOT)):sha256(path.read_bytes()).hexdigest()
                    for path in sorted((ROOT/'assets/characters/iselin').glob('walk_*/frame_*.png'))}},indent=2)+'\n')
            print(f'Captured {len(frames)} frames, four directions, stop/turn transitions and tree occlusion.')
        finally:game.music.stop();pygame.quit()


if __name__=='__main__':capture()
