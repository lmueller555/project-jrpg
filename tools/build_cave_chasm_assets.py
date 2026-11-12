"""Register authored limestone rupture modules and compose reusable pit scenery."""
from pathlib import Path
import hashlib,json
from PIL import Image,ImageDraw,ImageChops
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'assets/source/terrain/limestone_cave/chasm/authored_modules.png'
OUT=ROOT/'assets/terrain/limestone_cave/chasm'
NAMES=('rim.north','rim.south','rim.west','rim.east','face.deep','debris.fresh','crack.fresh','scratches.climbing')
SIZES=((96,48),(96,40),(48,96),(48,96),(96,96),(48,32),(48,48),(40,32))
POLYGON=((24,42),(64,24),(112,16),(166,23),(224,32),(263,57),(270,92),(242,122),(189,143),(125,150),(62,138),(25,111),(14,76))

def build():
    OUT.mkdir(parents=True,exist_ok=True)
    atlas=Image.open(SOURCE).convert('RGBA');modules={};images={}
    for i,(name,size) in enumerate(zip(NAMES,SIZES)):
        box=(round(i%4*atlas.width/4),round(i//4*atlas.height/2),round((i%4+1)*atlas.width/4),round((i//4+1)*atlas.height/2))
        image=atlas.crop(box);image.putalpha(image.getchannel('A').point(lambda x:255 if x>=128 else 0));bounds=image.getbbox()
        cut=image.crop(bounds);scale=min((size[0]-2)/cut.width,(size[1]-2)/cut.height)
        cut=cut.resize((round(cut.width*scale),round(cut.height*scale)),Image.Resampling.NEAREST)
        image=Image.new('RGBA',size);image.alpha_composite(cut,((size[0]-cut.width)//2,(size[1]-cut.height)//2))
        path=OUT/(name.replace('.','_')+'.png');image.save(path,optimize=True);images[name]=image
        modules[name]={'frames':[path.relative_to(ROOT).as_posix()],'size':list(size),'source_cell':i,'source_rect':list(box),'source_bounds':list(bounds),'scale':scale}
    # Geometry is dark depth, with authored rock strata clipped inside it.
    pit=Image.new('RGBA',(288,174));mask=Image.new('L',pit.size);ImageDraw.Draw(mask).polygon(POLYGON,fill=255)
    interior=Image.new('RGBA',pit.size,(7,12,18,255))
    for x in range(16,280,80):interior.alpha_composite(images['face.deep'],(x,20))
    pixels=interior.load()
    for y in range(interior.height):
        gain=max(.08,.48-y/270)
        for x in range(interior.width):
            r,g,b,a=pixels[x,y];pixels[x,y]=(round(r*gain),round(g*gain),round(b*gain),a)
    pit.paste(interior,(0,0),mask)
    solid=mask.copy()
    for name,point in [('rim.north',(20,0)),('rim.north',(100,0)),('rim.north',(184,16)),('rim.west',(0,32)),('rim.east',(240,38)),('rim.south',(16,112)),('rim.south',(98,134)),('rim.south',(182,119)),('debris.fresh',(238,132)),('crack.fresh',(4,125)),('scratches.climbing',(64,99))]:
        pit.alpha_composite(images[name],point)
        if name.startswith('rim.'):
            rim=Image.new('L',pit.size);rim.paste(images[name].getchannel('A'),point)
            solid=ImageChops.lighter(solid,rim)
    pit.save(OUT/'rupture.png',optimize=True)
    solid.save(OUT/'collision.png',optimize=True)
    data={'version':1,'id':'limestone.chasm','source':SOURCE.relative_to(ROOT).as_posix(),'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'modules':modules,'composition':{'file':(OUT/'rupture.png').relative_to(ROOT).as_posix(),'size':[288,174],'collision':(OUT/'collision.png').relative_to(ROOT).as_posix(),'collision_polygon':[list(p) for p in POLYGON]},'operation':'Equal-cell extraction, alpha threshold, fixed nearest-neighbor registration; authored modules composed around a dark depth mask.'}
    (OUT/'assets.json').write_text(json.dumps(data,indent=2)+'\n')
    board=Image.new('RGBA',(384,192))
    for i,name in enumerate(NAMES):board.alpha_composite(images[name],((i%4)*96,(i//4)*96))
    board.save(OUT/'modules.png',optimize=True)
    return data
if __name__=='__main__':build()
