"""Compare retained pre-cleanup female profiles with current native exports."""
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/'docs/reviews/female_profile_chin'
NPCS=ROOT/'assets/characters/npcs'
LABELS=('01 / Blue dress / blue eyes','02 / Sage dress / green eyes','03 / Plum dress / hazel eyes')


def font(size):return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',size)
def opened(path):return Image.open(path).convert('RGBA')


def paste_native(board,sprite,xy,scale,crop=None):
    if crop:sprite=sprite.crop(crop)
    background=Image.new('RGBA',sprite.size,'#e8edf2');background.alpha_composite(sprite)
    board.paste(background.convert('RGB').resize((sprite.width*scale,sprite.height*scale),Image.Resampling.NEAREST),xy)


def save_loop(path,frames,durations):
    # RGB boards use the exact small sprite palette with opaque backgrounds.
    frames[0].save(path,save_all=True,append_images=frames[1:],duration=durations,
                   loop=0,disposal=2,optimize=False)


def build():
    face=Image.new('RGB',(1280,810),'#e8edf2');d=ImageDraw.Draw(face);d.fontmode='1'
    d.text((16,10),'Female NPC profiles / closed-mouth chin comparison',font=font(23),fill='#24382f')
    for col,label in enumerate(('Left / before','Left / after','Right / before','Right / after')):
        d.text((160+col*280+12,50),label,font=font(19),fill='#24382f')
    for row,label in enumerate(LABELS):
        y=90+row*235
        for index,line in enumerate(label.split(' / ')):
            d.text((12,y+35+index*26),line,font=font(17),fill='#24382f')
        for col,direction in enumerate(('left','left','right','right')):
            folder=OUTPUT/'before'/f'female_{row+1:02}' if col%2==0 else NPCS/f'female_{row+1:02}'
            paste_native(face,opened(folder/f'idle_{direction}.png'),(160+col*280+12,y),20,(6,5,18,16))
    face.save(OUTPUT/'faces_before_after.png')
    for direction in ('left','right'):
        frames=[]
        for phase in range(1,5):
            board=Image.new('RGB',(1152,432),'#e8edf2');d=ImageDraw.Draw(board);d.fontmode='1'
            d.text((16,8),f'Female NPC {direction} walk / before and after',font=font(23),fill='#24382f')
            for variant,label in enumerate(LABELS,1):
                x=(variant-1)*384
                d.text((x+12,42),label,font=font(17),fill='#24382f')
                for col,state in enumerate(('before','after')):
                    d.text((x+col*192+12,70),state.title(),font=font(18),fill='#526761')
                    path=OUTPUT/'before'/f'female_{variant:02}'/f'walk_{direction}_{phase:02}.png' if col==0 else NPCS/f'female_{variant:02}/walk_{direction}/frame_{phase:02}.png'
                    paste_native(board,opened(path),(x+col*192,100),8)
            d.text((16,400),f'Frame {phase}/4 | 140 ms per frame | existing stride and head bob',font=font(18),fill='#526761')
            frames.append(board)
        save_loop(OUTPUT/f'walk_{direction}_before_after.gif',frames,[140]*4)
        frames[0].save(OUTPUT/f'walk_{direction}_before_after.png')
    # A compact check of the actual gardener attachment/pose exports.
    pack=NPCS/'female_02/gardener';meta=json.loads((pack/'animations.json').read_text())
    frames=[]
    for phase in range(1,5):
        board=Image.new('RGB',(960,340),'#e8edf2');d=ImageDraw.Draw(board);d.fontmode='1'
        d.text((16,8),'Gardener / corrected carrying profiles',font=font(23),fill='#24382f')
        for col,(mode,direction) in enumerate((('empty','left'),('empty','right'),('full','left'),('full','right'))):
            key=f'carry_{mode}.{direction}_{phase:02}';pose=meta['poses'][key]
            body=opened(pack/pose['body']);level=0 if mode=='empty' else meta['water_capacity']
            bucket=opened(pack/f'bucket_0_{level}.png');xy=(pose['grip'][0],pose['grip'][1])
            image=Image.new('RGBA',(48,48))
            if pose['order']=='before':image.alpha_composite(bucket,xy)
            image.alpha_composite(body)
            if pose['order']=='after':image.alpha_composite(bucket,xy)
            paste_native(board,image,(col*240,65),5)
            d.text((col*240+12,310),f'{mode.title()} / {direction}',font=font(18),fill='#526761')
        frames.append(board)
    save_loop(OUTPUT/'gardener_carry_profiles.gif',frames,[140]*4)
    (OUTPUT/'comparison.json').write_text(json.dumps({
        'status':'approved' if all(json.loads((NPCS/f'female_{n:02}/walk_{d}/animation.json').read_text())['status']=='approved'
                                  for n in (1,2,3) for d in ('left','right')) else 'review',
        'before_commit':'8c8daed83dc959e171c6c8d59af89fb6429d163f',
        'native_frame_size':[24,36],'walk_frame_duration_ms':140,
        'change':'Three dark chin pixels per profile replaced with existing skin shades',
        'variants':[1,2,3],'directions':['left','right']
    },indent=2)+'\n')
    print('Built enlarged face and synchronized walk comparisons for all three female palettes.')


if __name__=='__main__':build()
