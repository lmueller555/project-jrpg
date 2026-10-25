"""A native schoolhouse assembled with Eldenmere's approved material palette."""
from pathlib import Path
import hashlib
import random
from PIL import Image,ImageDraw
from build_eldenmere_stream import read_json,write_json
from build_building_interiors import poses

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'assets/terrain/eldenmere/school/exterior'
SOURCE=ROOT/'assets/source/terrain/eldenmere/school/exterior'
SIZE=(192,192)
DOOR=(86,150,20,34)


def blank():return Image.new('RGBA',SIZE)
def opened(path):return Image.open(path).convert('RGBA')
def save(path,image):
    path.parent.mkdir(parents=True,exist_ok=True);image.save(path)
    return path.relative_to(ROOT).as_posix()
def bbox(rect):x,y,w,h=rect;return x,y,x+w,y+h


def structure():
    p=read_json(ROOT/'assets/terrain/eldenmere/cottage/palette.json')['materials']
    p['roof']={'shadow':'#465c60','base':'#5d7476','light':'#809590','edge':'#a0afa1'}
    p['outline']={'base':'#45382d'}
    p['bronze']={'shadow':'#6f5a35','base':'#977c43','light':'#cfb878'}
    layers={name:blank() for name in ('ground_shadow','chimney','walls','foundation','timber','windows','roof','porch','bell','door')}
    d=ImageDraw.Draw(layers['ground_shadow']);d.ellipse((14,176,179,191),fill='#827d6e');d.ellipse((22,179,174,191),fill='#736e60')
    # Chimney behind the eaves, with irregular masonry matching village stone.
    d=ImageDraw.Draw(layers['chimney']);d.rectangle((144,49,156,100),fill='#45382d')
    d.rectangle((146,50,154,98),fill=p['stone']['base']);d.rectangle((142,48,158,52),fill=p['stone']['shadow'])
    d.line((143,48,157,48),fill=p['stone']['cap']);d.line((143,50,157,50),fill=p['stone']['light'])
    for y in range(55,99,5):
        d.line((146,y,154,y),fill=p['stone']['joint']);d.line((147,y+1,153,y+1),fill=p['stone']['light'])
        x=149 if (y//5)%2 else 152;d.line((x,y-4,x,y-1),fill=p['stone']['joint'])
    # Cream plaster is varied with fixed small flecks, never noise that animates.
    d=ImageDraw.Draw(layers['walls']);d.polygon(((25,116),(165,116),(169,123),(169,182),(25,182)),fill='#45382d')
    d.rectangle((27,119,165,180),fill=p['plaster']['base']);d.rectangle((160,123,166,181),fill=p['plaster']['shadow'])
    d.line((29,123,158,123),fill=p['plaster']['light'],width=2)
    rng=random.Random(81)
    for _ in range(110):
        x=rng.randrange(29,160);y=rng.randrange(126,180)
        d.point((x,y),fill=p['plaster']['light'] if (x+y)%3 else p['plaster']['shadow'])
    # A low rubble foundation makes the public building sit on the same ground.
    d=ImageDraw.Draw(layers['foundation']);d.rectangle((24,178,168,190),fill='#45382d')
    for row,y in enumerate((179,185)):
        for x in range(25-(row%2)*7,168,14):
            left=max(25,x);right=min(167,x+12)
            d.rectangle((left,y,right,y+4),fill=p['stone']['base'] if x%3 else p['stone']['shadow'])
            d.line((left,y,right,y),fill=p['stone']['cap']);d.line((left,y+1,min(right,left+6),y+1),fill=p['stone']['light'])
    d.line((26,190,168,190),fill=p['stone']['joint'])
    # Posts and small diagonal braces support the roof and divide the bays.
    d=ImageDraw.Draw(layers['timber'])
    for x in (27,77,113,161):
        d.rectangle((x,123,x+3,180),fill=p['wood']['shadow']);d.line((x+1,124,x+1,178),fill=p['wood']['light'])
        d.point((x+2,151),fill=p['wood']['worn'])
    for y in (126,176):
        d.rectangle((27,y,164,y+3),fill=p['wood']['shadow']);d.line((29,y,162,y),fill=p['wood']['light'])
    for a,b in (((31,132),(42,139)),((75,132),(67,139)),((117,132),(127,139)),((159,132),(150,139))):
        d.line((*a,*b),fill=p['wood']['shadow'],width=3);d.line((*a,*b),fill=p['wood']['light'],width=1)
    # Tall paired panes, with reflections and worn sills at child-friendly scale.
    d=ImageDraw.Draw(layers['windows'])
    for x in (37,128):
        d.rectangle((x-2,139,x+29,175),fill='#45382d');d.rectangle((x-1,140,x+28,172),fill=p['wood']['light'])
        d.rectangle((x,141,x+27,170),fill=p['wood']['shadow'])
        for xx in (x+2,x+15):
            d.rectangle((xx,143,xx+10,168),fill=p['glass']['dark'])
            d.rectangle((xx+1,144,xx+9,166),fill=p['glass']['base'])
            d.line((xx+2,145,xx+7,145),fill=p['glass']['reflection']);d.line((xx+2,146,xx+2,155),fill=p['glass']['reflection'])
            d.line((xx+1,154,xx+9,154),fill=p['wood']['shadow'])
            d.line((xx+7,158,xx+7,164),fill=p['glass']['dark'])
        d.rectangle((x-3,172,x+30,175),fill=p['wood']['shadow']);d.line((x-2,172,x+29,172),fill=p['wood']['worn'])
    # Hip roof courses: each native tile is individually shaded and staggered.
    roof=layers['roof'];mask=Image.new('L',SIZE);ImageDraw.Draw(mask).polygon(((31,65),(159,65),(186,123),(184,128),(8,128),(6,124)),fill=255)
    texture=blank();d=ImageDraw.Draw(texture);d.rectangle((0,60,191,131),fill=p['roof']['shadow'])
    rng=random.Random(23)
    for row,y in enumerate(range(66,126,6)):
        for x in range(-5-(row%2)*5,192,10):
            shade=p['roof']['base'] if rng.randrange(4) else p['roof']['light']
            d.rectangle((x,y,x+8,y+4),fill=shade)
            d.line((x+1,y,x+7,y),fill=p['roof']['light']);d.point((x+1,y+1),fill=p['roof']['edge'])
            if rng.randrange(3)==0:d.line((x+5,y+3,x+7,y+3),fill=p['roof']['shadow'])
    roof.paste(texture,(0,0),mask);d=ImageDraw.Draw(roof)
    d.line(((31,65),(159,65),(186,123),(184,128),(8,128),(6,124),(31,65)),fill='#45382d',width=2)
    d.line((31,66,159,66),fill=p['roof']['edge']);d.line((11,126,181,126),fill=p['wood']['light'])
    # Ridge cap tiles are chunkier than the roof slates, like the cottage pack.
    for x in range(33,158,11):
        d.rectangle((x,63,x+9,67),fill=p['roof']['shadow']);d.line((x+1,63,x+8,63),fill=p['roof']['edge']);d.line((x+1,64,x+8,64),fill=p['roof']['light'])
    # Small sheltered porch; posts leave a clear 20px doorway.
    d=ImageDraw.Draw(layers['porch']);d.rectangle((81,145,84,185),fill=p['wood']['shadow']);d.line((82,147,82,182),fill=p['wood']['worn'])
    d.rectangle((108,145,111,185),fill=p['wood']['shadow']);d.line((109,147,109,182),fill=p['wood']['light'])
    d.polygon(((96,127),(117,143),(116,148),(76,148),(75,143)),fill='#45382d')
    d.polygon(((96,129),(113,142),(79,142)),fill=p['roof']['base'])
    for yy,left,right in ((134,91,101),(138,85,107),(142,80,112)):
        d.line((left,yy,right,yy),fill=p['roof']['light']);d.line((left,yy+1,right,yy+1),fill=p['roof']['shadow'])
    d.line((78,146,115,146),fill=p['wood']['worn'])
    d.rectangle((83,184,109,188),fill=p['stone']['shadow']);d.line((84,184,108,184),fill=p['stone']['cap'])
    d.rectangle((80,188,112,191),fill=p['stone']['base']);d.line((81,188,111,188),fill=p['stone']['highlight'])
    # A modest roof bell, distinct from the sanctuary's taller belfry.
    d=ImageDraw.Draw(layers['bell']);d.rectangle((88,42,103,64),fill=p['wood']['shadow'])
    d.rectangle((91,46,100,62),fill=p['roof']['shadow']);d.line((89,45,89,62),fill=p['wood']['light']);d.line((102,45,102,62),fill=p['wood']['light'])
    d.polygon(((96,34),(106,41),(105,45),(86,45),(85,41)),fill='#45382d')
    d.polygon(((96,36),(103,41),(88,41)),fill=p['roof']['base']);d.line((88,42,103,42),fill=p['roof']['light'])
    d.line((96,47,96,49),fill=p['bronze']['shadow'])
    d.polygon(((94,49),(98,49),(99,56),(101,58),(91,58),(93,56)),fill=p['bronze']['base'])
    d.line((94,50,94,55),fill=p['bronze']['light']);d.line((92,58,100,58),fill=p['bronze']['shadow']);d.point((96,59),fill=p['bronze']['light'])
    d.line((97,60,97,64),fill=p['wood']['light'])
    # The door crop is also the exact base of every hinge animation patch.
    d=ImageDraw.Draw(layers['door']);x,y,w,h=DOOR
    d.rectangle((x,y,x+w-1,y+h-1),fill='#45382d');d.rectangle((x+1,y+1,x+w-2,y+h-2),fill=p['wood']['light'])
    d.rectangle((x+2,y+2,x+w-3,y+h-2),fill=p['wood']['base'])
    for xx in (x+6,x+11,x+16):d.line((xx,y+3,xx,y+h-3),fill=p['wood']['shadow'])
    for yy in (y+7,y+23):d.line((x+3,yy,x+w-4,yy),fill=p['wood']['worn'])
    d.rectangle((x+14,y+17,x+15,y+18),fill=p['iron']['shadow']);d.point((x+14,y+17),fill=p['bronze']['light'])
    result=blank();paths=[]
    for name,layer in layers.items():result.alpha_composite(layer);paths.append(save(SOURCE/'layers'/f'{name}.png',layer))
    save(OUT/'structure.png',result)
    return p,result,paths


def book_sign(phase,palette):
    sign=Image.new('RGBA',(13,17));d=ImageDraw.Draw(sign)
    d.line((6,0,6,3),fill=palette['iron']['shadow']);d.point((6,1),fill=palette['iron']['light'])
    d.rectangle((0,4,12,16),fill='#45382d');d.rectangle((1,5,11,15),fill=palette['wood']['base']);d.line((2,5,10,5),fill=palette['wood']['worn'])
    d.polygon(((2,8),(5,7),(6,8),(7,7),(10,8),(10,12),(7,11),(6,12),(5,11),(2,12)),fill=palette['plaster']['light'])
    d.line((6,8,6,12),fill=palette['wood']['shadow']);d.line((3,9,4,9),fill=palette['plaster']['shadow']);d.line((8,9,9,9),fill=palette['plaster']['shadow'])
    tilt=(0,0,0,1,1,1,0,0,0,-1,-1,-1,0,0,0,0,0,0)[phase]
    out=blank()
    for yy in range(sign.height):
        offset=round(tilt*max(0,yy-3)/13)
        out.alpha_composite(sign.crop((0,yy,13,yy+1)),(69+offset,140+yy))
    return out


def build():
    palette,base,paths=structure();frames=[];source_records=[]
    for tick in range(18):
        smoke=blank();smoke.alpha_composite(opened(ROOT/f'assets/terrain/eldenmere/cottage/smoke/frame_{tick+1:02}.png'),(57,0))
        lantern=blank();lantern.alpha_composite(opened(ROOT/f'assets/terrain/eldenmere/cottage/lantern/frame_{tick+1:02}.png'),(46,40))
        sign=book_sign(tick,palette)
        im=base.copy();im.alpha_composite(smoke);im.alpha_composite(lantern);im.alpha_composite(sign)
        frame=save(OUT/f'frames/frame_{tick+1:02}.png',im);frames.append(frame)
        for name,layer in [('smoke',smoke),('lantern',lantern),('book_sign',sign)]:save(SOURCE/name/f'frame_{tick+1:02}.png',layer)
        source_records.append({'file':frame,'layers_from_repo_root':paths+[
            (SOURCE/name/f'frame_{tick+1:02}.png').relative_to(ROOT).as_posix() for name in ('smoke','lantern','book_sign')]})
        assert set(im.getchannel('A').tobytes())=={0,255}
    x,y,w,h=DOOR;closed=base.crop((x,y,x+w,y+h));door_frames=[]
    for i,patch in enumerate(poses(closed),1):door_frames.append(save(OUT/f'doors/frame_{i:02}.png',patch))
    assert opened(ROOT/frames[0]).crop((x,y,x+w,y+h)).tobytes()==opened(ROOT/door_frames[0]).tobytes()
    save(OUT/'closed.png',opened(ROOT/frames[0]))
    status=read_json(OUT/'school.json')['status'] if (OUT/'school.json').exists() else 'review'
    write_json(OUT/'school.json',{'id':'eldenmere.school.exterior','status':status,'tile_size':[24,24],
        'frame_size':list(SIZE),'ground_rect':[24,96,144,96],'structure':(OUT/'structure.png').relative_to(ROOT).as_posix(),
        'frames':frames,'frame_duration_ms':300,'cycle_duration_ms':5400,
        'door':{'position':[x,y],'size':[w,h],'frames':door_frames,'frame_duration_ms':100},
        'animated_layers':['smoke','lantern','book_sign'],'static_bell':True,
        'source_frames':source_records,'palette':palette})
    write_json(SOURCE/'recipe.json',{'frame_size':list(SIZE),'ground_rect':[24,96,144,96],
        'door_rect':list(DOOR),'smoke_source':'assets/terrain/eldenmere/cottage/smoke',
        'lantern_source':'assets/terrain/eldenmere/cottage/lantern',
        'material_palette_source':'assets/terrain/eldenmere/cottage/palette.json',
        'roof_palette':palette['roof'],'courses':'staggered native10x6 slates with fixed seed23',
        'layers_from_repo_root':paths,'frames':source_records})
    print('Built schoolhouse: 192x192, 6x4 ground, five door patches and eighteen charm phases.')


if __name__=='__main__':build()
