"""Register complete left-view drawings against the approved walk cadence."""
from pathlib import Path
from hashlib import sha256
import sys,json
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.build_mira_combat import _main_component
SOURCE=ROOT/'assets/source/characters/iselin/walk_left/redrawn'
OUTPUT=ROOT/'assets/characters/iselin/walk_left'
REVIEW=ROOT/'docs/reviews/iselin_left_walk_redrawn'


def build():
    frames=[];records=[]
    for row in range(4):
        source=Image.open(SOURCE/f'authored_{row}.png').convert('RGBA');cells=[]
        for col in range(4):
            rect=(col*source.width//4,0,(col+1)*source.width//4,source.height)
            cell=source.crop(rect);cell.putalpha(cell.getchannel('A').point(lambda a:255 if a>=220 else 0))
            cell=_main_component(cell);bounds=cell.getbbox();cells.append((cell.crop(bounds),rect,bounds))
        scale=68/max(c.height for c,_,_ in cells)
        for col,(cell,rect,bounds) in enumerate(cells):
            head=cell.crop((0,0,cell.width,cell.height//4)).getbbox()
            size=(round(cell.width*scale),round(cell.height*scale))
            origin=(20-round((head[0]+head[2])/2*scale),70-size[1])
            if origin[0]<0 or origin[0]+size[0]>42:raise ValueError('Clipped walk drawing')
            image=Image.new('RGBA',(42,72));image.alpha_composite(cell.resize(size,Image.Resampling.NEAREST),origin)
            # Preserve the approved continuous foot path as a whole lower-image
            # region. Upper left-view costume, hair and arm drawing stays new.
            motion=Image.open(SOURCE/f'motion_{row*4+col+1:02}.png').convert('RGBA')
            image.paste(motion.crop((0,46,42,72)),(0,46))
            frames.append(image)
            records.append({'source':f'authored_{row}.png','column':col,'cell':list(rect),'bounds':list(bounds),
                            'scale':scale,'size':list(size),'origin':list(origin),'protected_motion_rows':[46,72]})
    if len({im.tobytes() for im in frames})!=16:raise ValueError('Repeated exported pose')
    OUTPUT.mkdir(parents=True,exist_ok=True);REVIEW.mkdir(parents=True,exist_ok=True)
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',17)
    sheet=Image.new('RGBA',(672,72));board=Image.new('RGB',(752,1300),'#e8edf2');draw=ImageDraw.Draw(board)
    draw.text((16,12),'ISELIN / LEFT WALK / 16 WHOLE DRAWINGS',font=font,fill='#263c35')
    for index,frame in enumerate(frames):
        frame.save(OUTPUT/f'frame_{index+1:02}.png');sheet.alpha_composite(frame,(index*42,0))
        pos=(12+index%4*188,46+index//4*310);big=frame.resize((168,288),Image.Resampling.NEAREST)
        board.paste(big,pos,big);draw.text((pos[0],pos[1]+288),f'{index+1:02}',font=font,fill='#263c35')
    sheet.save(OUTPUT/'spritesheet.png');board.save(REVIEW/'frames.png')
    previews=[]
    for tick in range(32):
        im=Image.new('RGB',(440,380),'#e8edf2');d=ImageDraw.Draw(im)
        for index,x,label in ((tick%16,22,'Normal speed'),((tick//2)%16,244,'Half speed')):
            frame=frames[index].resize((168,288),Image.Resampling.NEAREST);im.paste(frame,(x,48),frame)
            d.text((x,12),label,font=font,fill='#263c35');d.text((x,344),f'Frame {index+1:02}/16',font=font,fill='#263c35')
        previews.append(im)
    previews[0].save(REVIEW/'preview.gif',save_all=True,append_images=previews[1:],
                     duration=[30,40]*16,loop=0,disposal=2,optimize=False)
    (OUTPUT/'animation.json').write_text(json.dumps({'character':'iselin','animation':'walk.left',
        'status':'approved','frame_size':[42,72],'draw_anchor':[21,60],'foot_anchor':[21,68],
        'artwork_pixels_per_world_pixel':2,'cycle_ms':560,'loop':True,'recipe':'tools/export_iselin_left_walk.py',
        'construction':'complete authored drawings; asymmetric left-view costume and drawn hair sway',
        'frames':[{'file':f'frame_{i+1:02}.png','rect':[i*42,0,42,72],'duration_ms':35} for i in range(16)]},indent=2)+'\n')
    (SOURCE/'registration.json').write_text(json.dumps({'generation_tool':'image_gen.imagegen',
        'motion_reference':'approved walk_right reflected as a pose guide only',
        'appearance_reference':'assets/source/characters/iselin/idle_left_master.png',
        'sources':{p.name:sha256(p.read_bytes()).hexdigest() for p in SOURCE.glob('*.png')},
        'processing':'Whole-drawing alpha220 extraction, uniform scale per strip and head/ground registration; approved reflected lower rows46-71 retained to protect foot motion. No limb assembly or procedural hair movement.',
        'frames':records,'status':'approved'},indent=2)+'\n')


if __name__=='__main__':build()
