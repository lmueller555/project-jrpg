import os,sys,tempfile,json
from pathlib import Path
os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy';os.environ['PYGAME_HIDE_SUPPORT_PROMPT']='1'
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import pygame
from PIL import Image,ImageDraw
from main import Game
from rendering import WorldCanvas
with tempfile.TemporaryDirectory() as tmp:
 g=Game(fullscreen=False,start_on_title=False,save_path=Path(tmp)/'save.json',settings_path=Path(tmp)/'settings.json')
 for name in ['elira']:
  out=ROOT/'docs/reviews'/f'{name}_native';out.mkdir(exist_ok=True)
  visit=getattr(g,name+'_visit');actor=getattr(visit,name);world=visit.home;g.world=world;g.player.position.update(192,250)
  canvas=WorldCanvas((480,320));world.draw(canvas,(0,0),g.player,0,include_ui=False);pygame.image.save(canvas.native,str(out/'live_home.png'))
  board=Image.new('RGB',(940,620),'#62705f');d=ImageDraw.Draw(board)
  for j,f in enumerate(['front','back','left','right']):
   bank=ROOT/'assets/characters/named_hd'/name;idle=Image.open(bank/f'idle_{f}.png').convert('RGBA');big=idle.resize((96,144),Image.Resampling.NEAREST);board.paste(big,(0,j*154+12),big);d.text((0,j*154),f,fill='white')
   for i in range(8):
    im=Image.open(bank/f'walk_{f}/frame_{i+1:02}.png').convert('RGBA');big=im.resize((96,144),Image.Resampling.NEAREST);board.paste(big,(110+i*103,j*154+12),big);d.text((110+i*103,j*154),str(i+1),fill='white')
  board.save(out/'numbered.png')
  if name=='halden':
   travel=[];poses=[]
   for i in range(9):
    if i:g.opening_conclusion._move(actor,(240,176),.07)
    travel.append({'frame':i,'position':list(actor.position),'walk_ms':actor.walk_ms,'facing':actor.facing,'moving':actor.moving})
    c=WorldCanvas((480,320));world.draw(c,(0,0),g.player,i*70,include_ui=False);poses.append(Image.frombytes('RGB',(960,640),pygame.image.tobytes(c.native,'RGB')))
   poses[0].save(out/'actual_travel.gif',save_all=True,append_images=poses[1:],duration=70,loop=0)
   (out/'travel_observation.json').write_text(json.dumps({'type':'Actual OpeningConclusion._move in unchanged Halden home geometry','frames':travel,'foot_lock':'Stylized 560ms gait at unchanged 56-world-unit travel speed; native stance excursion is shorter than world displacement. Residual sliding remains; no perfect ground-lock claim and no speed/collision alteration.'},indent=2)+'\n')
 pygame.quit()
