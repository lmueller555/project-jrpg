"""Export full-character drawings. No limb assembly or procedural posing."""
from pathlib import Path
import sys,json
from hashlib import sha256
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.build_mira_combat import _main_component
SOURCE=ROOT/'assets/source/characters/iselin/walk_right/redrawn'
OUTPUT=ROOT/'assets/characters/iselin/walk_right'
REVIEW=ROOT/'docs/reviews/iselin_right_walk_redrawn'
SEQUENCE=(('A',0),('D',3),('D',2),('D',1),('B',0),('B',1),('B',2),('B',3),
          ('C',0),('C',1),('C',2),('C',3),('E',0),('E',1),('E',2),('E',3))


def revise_legs():
    """Local imagegen leg edits; preserve every approved upper-body pixel."""
    root=SOURCE/'leg_revision';frames=[None]*16;records=[None]*16
    strips=[(f'legs_{row}.png',list(range(row*4,row*4+4))) for row in range(4)]
    strips.append(('fix_11_12.png',[10,11]))
    for name,indices in strips:
        source=Image.open(root/name).convert('RGBA');cells=[]
        for col in range(len(indices)):
            box=(col*source.width//len(indices),0,(col+1)*source.width//len(indices),source.height)
            cell=source.crop(box);cell.putalpha(cell.getchannel('A').point(lambda a:255 if a>=220 else 0))
            cell=_main_component(cell);bounds=cell.getbbox();cells.append((cell.crop(bounds),box,bounds))
        scale=68/max(im.height for im,_,_ in cells)
        for col,(cell,box,bounds) in enumerate(cells):
            head=cell.crop((0,0,cell.width,cell.height//4)).getbbox()
            size=(round(cell.width*scale),round(cell.height*scale))
            x=22-round((head[0]+head[2])/2*scale);y=70-size[1]
            if x<0 or x+size[0]>42:raise ValueError(('Leg edit clips',name,col,x,size))
            edited=Image.new('RGBA',(42,72));edited.alpha_composite(cell.resize(size,Image.Resampling.NEAREST),(x,y))
            index=indices[col]
            approved=Image.open(root/f'approved_{index+1:02}.png').convert('RGBA')
            edited.paste(approved.crop((0,0,42,46)),(0,0))
            assert edited.crop((0,0,42,46)).tobytes()==approved.crop((0,0,42,46)).tobytes()
            frames[index]=edited
            records[index]={'source':name,'cell':list(box),'bounds':list(bounds),
                            'scale':scale,'size':list(size),'origin':[x,y],'protected_rows':[0,46]}
    return frames,records


def build():
    drawings={};records={}
    for name in ('A','B','C','D','E'):
        source=Image.open(SOURCE/f'{name}.png').convert('RGBA');cells=[]
        for index in range(4):
            rect=(index*source.width//4,0,(index+1)*source.width//4,source.height)
            cell=source.crop(rect);cell.putalpha(cell.getchannel('A').point(lambda a:255 if a>=220 else 0))
            cell=_main_component(cell);bounds=cell.getbbox();cells.append((cell.crop(bounds),rect,bounds))
        scale=68/max(im.height for im,_,_ in cells)
        for index,(cell,rect,bounds) in enumerate(cells):
            head=cell.crop((0,0,cell.width,cell.height//4)).getbbox()
            size=(round(cell.width*scale),round(cell.height*scale))
            x=22-round((head[0]+head[2])/2*scale);y=70-size[1]
            if x<0 or x+size[0]>42:raise ValueError(('Clipping',name,index,x,size))
            drawing=Image.new('RGBA',(42,72))
            drawing.alpha_composite(cell.resize(size,Image.Resampling.NEAREST),(x,y))
            drawings[name,index]=drawing
            records[name,index]={'source':f'{name}.png','column':index,'cell':list(rect),
                                  'bounds':list(bounds),'uniform_scale':scale,'size':list(size),'origin':[x,y]}
    frames=[drawings[key] for key in SEQUENCE]
    frames,leg_records=revise_legs()
    if len({im.tobytes() for im in frames})!=16:raise ValueError('Repeated native drawings')
    OUTPUT.mkdir(parents=True,exist_ok=True);REVIEW.mkdir(parents=True,exist_ok=True)
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',17)
    sheet=Image.new('RGBA',(672,72));board=Image.new('RGB',(752,1300),'#e8edf2');draw=ImageDraw.Draw(board)
    draw.text((16,12),'ISELIN / REDRAWN RIGHT WALK / 16 WHOLE POSES',font=font,fill='#263c35')
    for index,frame in enumerate(frames):
        frame.save(OUTPUT/f'frame_{index+1:02}.png');sheet.alpha_composite(frame,(index*42,0))
        big=frame.resize((168,288),Image.Resampling.NEAREST);pos=(12+index%4*188,46+index//4*310)
        board.paste(big,pos,big);draw.text((pos[0],pos[1]+288),f'{index+1:02}',font=font,fill='#263c35')
    sheet.save(OUTPUT/'spritesheet.png');board.save(REVIEW/'frames.png')
    previews=[]
    for tick in range(32):
        im=Image.new('RGB',(440,380),'#e8edf2');d=ImageDraw.Draw(im)
        for phase,x,label in ((tick%16,22,'Normal speed'),((tick//2)%16,244,'Half speed')):
            frame=frames[phase].resize((168,288),Image.Resampling.NEAREST);im.paste(frame,(x,48),frame)
            d.text((x,12),label,font=font,fill='#263c35');d.text((x,344),f'Frame {phase+1:02}/16',font=font,fill='#263c35')
        previews.append(im)
    previews[0].save(REVIEW/'preview.gif',save_all=True,append_images=previews[1:],duration=[30,40]*16,
                     loop=0,disposal=2,optimize=False)
    (REVIEW/'preview_legs_v2.gif').write_bytes((REVIEW/'preview.gif').read_bytes())
    (REVIEW/'frames_legs_v2.png').write_bytes((REVIEW/'frames.png').read_bytes())
    metadata={'character':'iselin','animation':'walk.right','status':'awaiting_user_review',
              'frame_size':[42,72],'draw_anchor':[21,60],'foot_anchor':[21,68],
              'artwork_pixels_per_world_pixel':2,'cycle_ms':560,'loop':True,
              'recipe':'tools/export_iselin_right_walk_redrawn.py','construction':'complete authored character drawings',
              'frames':[{'file':f'frame_{i+1:02}.png','rect':[i*42,0,42,72],'duration_ms':35} for i in range(16)]}
    (OUTPUT/'animation.json').write_text(json.dumps(metadata,indent=2)+'\n')
    record={'generation_tool':'image_gen.imagegen','references':['idle_right_master.png','redrawn/keys.png'],
            'source_hashes':{p.name:sha256(p.read_bytes()).hexdigest() for p in SOURCE.glob('*.png')},
            'processing':'Local imagegen leg edits to whole-character drawings; crop, alpha220, uniform scale and head registration; approved rows0-45 restored unchanged. No part rig, rotations or procedural limb deformation.',
            'frames':[records[key] for key in SEQUENCE],'review_status':'pending'}
    record['leg_revision']={'generation_tool':'image_gen.imagegen','protected_rows':[0,46],
                            'frames':leg_records,'hashes':{p.name:sha256(p.read_bytes()).hexdigest()
                            for p in (SOURCE/'leg_revision').glob('*.png')}}
    (SOURCE/'registration.json').write_text(json.dumps(record,indent=2)+'\n')


if __name__=='__main__':build()
