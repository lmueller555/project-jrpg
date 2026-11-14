"""Register complete rear-view drawings for motion review; no limb rig."""
from pathlib import Path
from hashlib import sha256
import sys,json
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.build_mira_combat import _main_component
SOURCE=ROOT/'assets/source/characters/iselin/walk_back/redrawn'
OUTPUT=ROOT/'assets/characters/iselin/walk_back'
REVIEW=ROOT/'docs/reviews/iselin_back_walk'
SEQUENCE=(('F',0),('F',1),('F',2),('F',3),('A',1),('B',0),('B',1),('B',2),
          ('C',0),('C',1),('keys',2),('keys',1),('L',0),('L',1),('L',2),('L',3))


def build():
    drawings={};records={}
    for name in {name for name,_ in SEQUENCE}:
        source=Image.open(SOURCE/f'{name}.png').convert('RGBA');cells=[]
        for col in range(4):
            box=(col*source.width//4,0,(col+1)*source.width//4,source.height)
            cell=source.crop(box);cell.putalpha(cell.getchannel('A').point(lambda a:255 if a>=220 else 0))
            cell=_main_component(cell);bounds=cell.getbbox();cells.append((cell.crop(bounds),box,bounds))
        scale=68/max(c.height for c,_,_ in cells)
        for col,(cell,box,bounds) in enumerate(cells):
            head=cell.crop((0,0,cell.width,cell.height//4)).getbbox()
            size=(round(cell.width*scale),round(cell.height*scale))
            origin=(21-round((head[0]+head[2])/2*scale),70-size[1])
            if origin[0]<0 or origin[0]+size[0]>42:raise ValueError('Clipped authored pose')
            frame=Image.new('RGBA',(42,72));frame.alpha_composite(cell.resize(size,Image.Resampling.NEAREST),origin)
            drawings[name,col]=frame;records[name,col]={'source':f'{name}.png','column':col,'box':list(box),
                'bounds':list(bounds),'scale':scale,'size':list(size),'origin':list(origin)}
    frames=[drawings[key] for key in SEQUENCE]
    # Imagegen redraws complete poses. Protect every pixel outside the right
    # lower-leg edit window, including all approved arms and the entire left leg.
    revision=SOURCE/'right_foot_revision'
    originals=[f.copy() for f in frames]
    corrections=[]
    for group in range(4):
        path=revision/f'edited_{group}.png'
        source=Image.open(path).convert('RGBA');cells=[]
        for col in range(4):
            cell=source.crop((col*source.width//4,0,(col+1)*source.width//4,source.height))
            cell.putalpha(cell.getchannel('A').point(lambda a:255 if a>=220 else 0))
            cell=_main_component(cell);bounds=cell.getbbox();cells.append((cell.crop(bounds),bounds))
        scale=68/max(cell.height for cell,_ in cells)
        for col,(cell,bounds) in enumerate(cells):
            head=cell.crop((0,0,cell.width,cell.height//4)).getbbox()
            size=(round(cell.width*scale),round(cell.height*scale))
            origin=(21-round((head[0]+head[2])/2*scale),70-size[1])
            drawing=Image.new('RGBA',(42,72))
            drawing.alpha_composite(cell.resize(size,Image.Resampling.NEAREST),origin)
            index=group*4+col;window=(22,48,32,72)
            frames[index]=originals[index].copy()
            frames[index].paste(drawing.crop(window),window)
            corrections.append({'frame':index+1,'source':str(path.relative_to(SOURCE)),
                'sha256':sha256(path.read_bytes()).hexdigest(),'column':col,
                'bounds':list(bounds),'scale':scale,'size':list(size),
                'origin':list(origin),'edit_window':list(window)})
    from tools.iselin_back_walk_stability import stabilize
    frames,stability=stabilize(SOURCE,frames)
    if len({f.tobytes() for f in frames})!=16:raise ValueError('Repeated exported poses')
    OUTPUT.mkdir(parents=True,exist_ok=True);REVIEW.mkdir(parents=True,exist_ok=True)
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',17)
    sheet=Image.new('RGBA',(672,72));board=Image.new('RGB',(752,1300),'#e8edf2');draw=ImageDraw.Draw(board)
    draw.text((16,12),'ISELIN / REAR WALK / 16 WHOLE DRAWINGS',font=font,fill='#263c35')
    for i,frame in enumerate(frames):
        frame.save(OUTPUT/f'frame_{i+1:02}.png');sheet.alpha_composite(frame,(i*42,0))
        pos=(12+i%4*188,46+i//4*310);big=frame.resize((168,288),Image.Resampling.NEAREST)
        board.paste(big,pos,big);draw.text((pos[0],pos[1]+288),f'{i+1:02}',font=font,fill='#263c35')
    sheet.save(OUTPUT/'spritesheet.png');board.save(REVIEW/'frames.png');board.save(REVIEW/'frames_stable_body_v3.png')
    previews=[]
    for tick in range(32):
        im=Image.new('RGB',(440,380),'#e8edf2');d=ImageDraw.Draw(im)
        for i,x,label in ((tick%16,22,'Normal speed'),((tick//2)%16,244,'Half speed')):
            frame=frames[i].resize((168,288),Image.Resampling.NEAREST);im.paste(frame,(x,48),frame)
            d.text((x,12),label,font=font,fill='#263c35');d.text((x,344),f'Frame {i+1:02}/16',font=font,fill='#263c35')
        previews.append(im)
    previews[0].save(REVIEW/'preview.gif',save_all=True,append_images=previews[1:],duration=[30,40]*16,
                     loop=0,disposal=2,optimize=False)
    import shutil
    shutil.copyfile(REVIEW/'preview.gif',REVIEW/'preview_stable_body_v3.gif')
    (OUTPUT/'animation.json').write_text(json.dumps({'character':'iselin','animation':'walk.back',
        'status':'awaiting_user_review','frame_size':[42,72],'draw_anchor':[21,60],'foot_anchor':[21,68],
        'artwork_pixels_per_world_pixel':2,'cycle_ms':560,'loop':True,'recipe':'tools/export_iselin_back_walk.py',
        'construction':'complete authored rear-view drawings; no limb assembly',
        'frames':[{'file':f'frame_{i+1:02}.png','rect':[i*42,0,42,72],'duration_ms':35} for i in range(16)]},indent=2)+'\n')
    (SOURCE/'registration.json').write_text(json.dumps({'generation_tool':'image_gen.imagegen',
        'reference':'assets/source/characters/iselin/idle_back_master.png',
        'sources':{p.name:sha256(p.read_bytes()).hexdigest() for p in sorted(SOURCE.glob('*.png'))},
        'processing':'Whole drawing alpha220 extraction, common scale per strip and head/ground registration. Right lower-leg regional redraw from complete imagegen poses; all other original pixels restored. No limb transforms, mirrors or interpolation.',
        'body_stability':stability,'right_foot_corrections':corrections,'frames':[records[key] for key in SEQUENCE],'status':'awaiting_user_review'},indent=2)+'\n')


if __name__=='__main__':build()
