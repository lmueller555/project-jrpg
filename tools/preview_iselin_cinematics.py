"""Inspect retained Iselin artwork and optional clips without a retired scene.

No production art or scene file is written. The optional probe reuses existing
still drawings to inspect the neutral action player; it is not new animation art.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import sys
import tempfile
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
GROUND=ROOT/'assets/characters/iselin/cinematic/ground/animation.json'
OUT=Path(tempfile.gettempdir())/'iselin-character-library-preview'
PROBE='synthetic_mechanic_probe'
CUE='review:iselin'


def digest(path):return sha256(Path(path).read_bytes()).hexdigest()

def font(size):
    from PIL import ImageFont
    return ImageFont.truetype(str(ROOT/'assets/ui/fonts/AtkinsonHyperlegible-Regular.ttf'),size)

def reference_board(output):
    from PIL import Image,ImageDraw
    board=Image.new('RGB',(1280,690),'#e8edf2');draw=ImageDraw.Draw(board)
    draw.text((16,10),'EXISTING ISELIN REFERENCES / NO NEW ARTWORK',font=font(23),fill='#263c35')
    draw.text((16,43),'Each group labels its own canvas and inspection enlargement; these are different camera slots.',
              font=font(16),fill='#263c35')
    refs=[]
    def paste(path,x,y,scale,label):
        image=Image.open(ROOT/path).convert('RGBA')
        large=image.resize((image.width*scale,image.height*scale),Image.Resampling.NEAREST)
        board.paste(large,(x,y),large)
        draw.text((x,y+large.height+7),label,font=font(14),fill='#263c35')
        refs.append({'path':path,'sha256':digest(ROOT/path),'canvas':list(image.size),'enlargement':scale})
    for index,direction in enumerate(('front','left','right','back')):
        paste(f'assets/characters/iselin/native_idles/idle_{direction}.png',16+index*150,104,4,
              f'{direction}:24x36 /4x')
    paste('assets/characters/iselin/cinematic/seated.png',646,104,4,'seated:24x36 /4x')
    for index,name in enumerate(('overhead','oblique')):
        paste(f'assets/characters/iselin/cinematic/aerial/{name}.png',834+index*210,84,3,
              f'{name}:48x64 /3x')
    data=json.loads(GROUND.read_text())
    for index,(name,filename) in enumerate(data['poses'].items()):
        paste('assets/characters/iselin/cinematic/ground/'+filename,16+index*208,370,2,
              name+' /80x96 /2x')
    draw.text((16,651),'Native idles/seat:world scale. Ground/aerial:existing cinematic camera presentation. No limb edits or interpolation.',
              font=font(15),fill='#263c35')
    board.save(output/'reference_board.png')
    return refs

def probe_record():
    return {'classification':'Synthetic mechanic probe using existing still poses; not authored performance animation.',
            'actions':{PROBE:{'entry':[{'pose':'stand_left','duration_ms':100}],
                 'hold':{'pose':'gesture_left','duration_ms':None},
                 'recovery':[{'pose':'listen_left','duration_ms':120}],
                 'rest_pose':'stand_left'}}}

def write_gif(path,frames,durations):
    from PIL import Image
    palette=frames[0].quantize(colors=256)
    indexed=[frame.quantize(palette=palette,dither=Image.Dither.NONE) for frame in frames]
    indexed[0].save(path,save_all=True,append_images=indexed[1:],duration=durations,
                    loop=0,disposal=1,optimize=False)
    total=0
    with Image.open(path) as image:
        count=image.n_frames
        if count!=len(indexed):raise ValueError('GIF sampled frame count changed')
        for index in range(count):
            image.seek(index);total+=image.info['duration']
            if image.info['duration']!=durations[index]:
                raise ValueError('GIF sampled exposure changed')
            if image.convert('RGB').tobytes()!=indexed[index].convert('RGB').tobytes():
                raise ValueError('GIF decoded frame differs from its quantized source')
    if total!=sum(durations):raise ValueError('GIF playback duration was not preserved')
    return {'frames':count,'total_ms':total,'decoded_frames_match_quantized_sources':True,
            'sample_exposures_preserved':True,'disposal':1}

class Review:
    def __init__(self,args):
        import pygame
        from cinematic_actor_actions import ActionPlayer,load_actions
        self.pygame=pygame;self.args=args
        pygame.display.init();pygame.display.set_mode((640,360))
        self.record=json.loads(GROUND.read_text())
        if args.action_file:
            self.record['actions']=json.loads(args.action_file.read_text())['actions']
        if args.probe:self.record.update(probe_record())
        self.poses={name:pygame.image.load(str(GROUND.parent/file)).convert_alpha()
                    for name,file in self.record['poses'].items()}
        self.loops={name:[(pygame.image.load(str(GROUND.parent/f['file'])).convert_alpha(),f['duration_ms'])
                          for f in frames] for name,frames in self.record.get('loops',{}).items()}
        self.player=ActionPlayer(load_actions(self.record,self.poses,GROUND))
        self.action=PROBE if args.probe else args.action
        if args.pose and args.pose not in self.poses:raise ValueError('Unknown pose: '+args.pose)
        if args.loop and args.loop not in self.loops:raise ValueError('Unknown loop: '+args.loop)
        self.restart()

    def restart(self):
        self.elapsed=0.;self.released=False;self.player.clear()
        if self.action:self.player.play(self.action,CUE)

    def release(self):
        self.released=True
        return self.player.release(CUE)

    def advance(self,seconds):
        target=self.elapsed+seconds
        if (self.action and not self.released and self.args.release_at is not None
                and self.elapsed <= self.args.release_at <= target):
            self.player.update(self.args.release_at-self.elapsed)
            self.release();self.player.update(target-self.args.release_at)
        elif self.action:self.player.update(seconds)
        self.elapsed=target

    def frame(self):
        if self.action:return self.player.frame
        if self.args.loop:
            frames=self.loops[self.args.loop];clock=(self.elapsed*1000)%sum(d for _,d in frames)
            for image,duration in frames:
                if clock<duration:return image
                clock-=duration
            return frames[-1][0]
        return self.poses[self.args.pose or 'stand_left']

    def draw(self):
        from PIL import Image,ImageDraw
        image=self.frame()
        sprite=Image.frombytes('RGBA',image.get_size(),self.pygame.image.tobytes(image,'RGBA'))
        board=Image.new('RGB',(640,360),'#e8edf2');draw=ImageDraw.Draw(board)
        board.paste(sprite.resize((160,192),Image.Resampling.NEAREST),(240,100),
                    sprite.resize((160,192),Image.Resampling.NEAREST))
        label=self.action or self.args.loop or self.args.pose or 'stand_left'
        draw.text((12,10),'RETAINED ISELIN ART / NEUTRAL PREVIEW',font=font(20),fill='#263c35')
        draw.text((12,44),f'{label} / t={self.elapsed:.3f}s / {self.player.stage}',font=font(16),fill='#263c35')
        draw.text((12,319),'Space: pause / E: release / R: restart / Esc: close',font=font(15),fill='#263c35')
        return board


def preservation():
    baseline=json.loads((ROOT/'docs/reviews/iselin_native_integration/approved_assets.json').read_text())
    for path,value in baseline['sha256'].items():
        if digest(ROOT/path)!=value:raise ValueError('Approved native asset changed: '+path)
    return {'png_count':baseline['png_count'],'native_approved_assets_unchanged':True}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--headless',action='store_true')
    parser.add_argument('--board-only',action='store_true')
    parser.add_argument('--list',action='store_true')
    group=parser.add_mutually_exclusive_group()
    group.add_argument('--pose');group.add_argument('--loop');group.add_argument('--action')
    parser.add_argument('--probe',action='store_true')
    parser.add_argument('--action-file',type=Path)
    parser.add_argument('--release-at',type=float)
    parser.add_argument('--seconds',type=float,default=1)
    parser.add_argument('--speed',type=float,choices=(1,.25),default=1)
    parser.add_argument('--fps',type=int,choices=(25,50),default=50)
    parser.add_argument('--samples',default='0,.05,.1,.3,.42,.7')
    parser.add_argument('--out',type=Path,default=OUT)
    parser.add_argument('--check-preservation',action='store_true')
    args=parser.parse_args()
    if not math.isfinite(args.seconds) or args.seconds<=0:parser.error('--seconds must be positive finite')
    if args.release_at is not None and (not math.isfinite(args.release_at) or args.release_at<0):
        parser.error('--release-at must be nonnegative finite')
    record=json.loads(GROUND.read_text())
    if args.list:
        print(json.dumps({key:list(record.get(key,{})) for key in ('poses','loops','actions')},indent=2));return
    args.out.mkdir(parents=True,exist_ok=True)
    refs=reference_board(args.out)
    metadata={'classification':'Existing character-library references; synthetic probe is not authored performance.',
              'references':refs,'persistence':'No Game, quest, save or production asset writes.'}
    if args.check_preservation:metadata['preservation']=preservation()
    if args.board_only:
        (args.out/'preview.json').write_text(json.dumps(metadata,indent=2)+'\n');return
    if args.headless:
        os.environ.setdefault('SDL_VIDEODRIVER','dummy');os.environ.setdefault('SDL_AUDIODRIVER','dummy')
    review=Review(args)
    try:
        if args.headless:
            count=max(1,math.ceil(args.seconds*args.fps));frames=[];states=[]
            for index in range(count):
                frames.append(review.draw());states.append({'seconds':review.elapsed,**review.player.state})
                review.advance(1/args.fps)
            durations=[round(1000/args.fps/args.speed)]*count
            metadata['gif']=write_gif(args.out/'preview.gif',frames,durations)
            metadata['timeline']=states
            for index,sample in enumerate(float(value) for value in args.samples.split(',')):
                if not math.isfinite(sample) or sample<0:raise ValueError('Samples must be nonnegative finite')
                review.restart();review.advance(sample);review.draw().save(args.out/f'sample_{index:02}.png')
            (args.out/'preview.json').write_text(json.dumps(metadata,indent=2)+'\n')
        else:
            pygame=review.pygame;clock=pygame.time.Clock();playing=True;running=True
            while running:
                seconds=clock.tick(args.fps)/1000
                for event in pygame.event.get():
                    if event.type==pygame.QUIT:running=False
                    elif event.type==pygame.KEYDOWN:
                        if event.key==pygame.K_ESCAPE:running=False
                        elif event.key==pygame.K_SPACE:playing=not playing
                        elif event.key==pygame.K_r:review.restart()
                        elif event.key==pygame.K_e:review.release()
                if playing:review.advance(seconds*args.speed)
                card=review.draw();pygame.display.get_surface().blit(pygame.image.frombytes(card.tobytes(),card.size,'RGB'),(0,0))
                pygame.display.flip()
    finally:review.pygame.quit()


if __name__=='__main__':main()
