"""A native woven floor rug and a single resting dog pose; no action loops."""
import hashlib
from pathlib import Path

from PIL import Image,ImageDraw

from build_liam_daisy_run_prototypes import dog_parts,translate,tapered
from build_liam_family_front_walks import ROOT,read,write,blank,rgba

RUG_SOURCE=ROOT/'assets/source/terrain/eldenmere/liam_home'
RUG=ROOT/'assets/terrain/eldenmere/liam_home'
DOG_SOURCE=ROOT/'assets/source/characters/daisy/lying_left'
DOG=ROOT/'assets/characters/daisy/lying_left'


def store_parts(directory,layers):
    directory.mkdir(parents=True,exist_ok=True);paths=[]
    merged=blank(next(iter(layers.values())).size)
    for name,im in layers.items():
        path=directory/f'{name}.png';im.save(path);paths.append(path.relative_to(ROOT).as_posix())
        merged.alpha_composite(im)
    return merged,paths


def rug():
    recipe=read(RUG_SOURCE/'rug_recipe.json');m=recipe['palette'];size=tuple(recipe['frame_size'])
    layers={name:blank(size) for name in ('woven_base','border_and_motifs','fringe')}
    d=ImageDraw.Draw(layers['woven_base'])
    d.polygon(((6,3),(57,3),(59,5),(59,30),(57,32),(6,32),(4,30),(4,5)),fill=m['edge'])
    d.rectangle((5,5,58,30),fill=m['base'])
    for y in range(6,31,2):d.line((6,y,57,y),fill=m['shadow'],width=1)
    d=ImageDraw.Draw(layers['border_and_motifs'])
    d.rectangle((7,6,56,29),outline=m['linen'],width=1)
    d.rectangle((10,9,53,26),outline=m['light'],width=1)
    for x in range(10,54,4):
        for y in (7,28):d.point((x,y),fill=m['accent'])
    for x,y in recipe['motif_centres']:
        d.polygon(((x,y-5),(x+5,y),(x,y+5),(x-5,y)),fill=m['linen'])
        d.polygon(((x,y-3),(x+3,y),(x,y+3),(x-3,y)),fill=m['accent'])
        d.point((x,y),fill=m['linen'])
    d=ImageDraw.Draw(layers['fringe'])
    for y in range(7,30,3):
        d.line((1,y,4,y),fill=m['linen']);d.line((59,y,62,y),fill=m['linen'])
    im,paths=store_parts(RUG_SOURCE/'parts',layers)
    RUG.mkdir(parents=True,exist_ok=True);im.save(RUG/'rug.png')
    write(RUG/'rug.json',{**recipe,'image':'rug.png','layers_from_repo_root':paths,
          'source_recipe':(RUG_SOURCE/'rug_recipe.json').relative_to(ROOT).as_posix()})
    return im


def daisy_rest():
    base=ROOT/'assets/characters/daisy';idle=Image.open(base/'idle_left.png').convert('RGBA')
    m=read(base/'palette.json')['materials'];parts=dog_parts(idle)
    # Lay the approved plume across the floor, preserving every fur color.
    tail=blank((40,36));pivot=(23,24)
    for y in range(36):
        for x in range(32):
            p=parts['tail'].getpixel((x,y))
            if p[3]:tail.putpixel((4+pivot[0]-(y-pivot[1]),3+pivot[1]+x-pivot[0]),p)
    d=ImageDraw.Draw(tail)
    d.polygon(((25,27),(28,27),(30,30),(25,31)),fill=m['gray_fur'][0])
    far=blank((40,36));far.alpha_composite(idle.crop((7,32,12,35)),(9,30))
    fore=blank((40,36));d=ImageDraw.Draw(fore)
    tapered(d,(16,29),(13,32),4,3,m['gray_fur'][1])
    tapered(d,(13,32),(9,33),3,2,m['gray_fur'][2])
    fore.alpha_composite(idle.crop((7,32,12,35)),(6,32))
    hind=blank((40,36));d=ImageDraw.Draw(hind)
    tapered(d,(26,29),(28,31),4,4,m['gray_fur'][1])
    tapered(d,(28,31),(25,32),3,3,m['gray_fur'][0])
    hind.alpha_composite(idle.crop((20,32,25,35)),(23,31))
    layers={'tail':tail,'far_forepaw':far,'body':translate(parts['body'],4,5,(40,36)),
            'folded_hind_leg':hind,'folded_foreleg':fore,
            'head':translate(parts['head'],4,6,(40,36)),
            'ear':translate(parts['ear'],4,6,(40,36))}
    im,paths=store_parts(DOG_SOURCE/'parts',layers)
    allowed={rgba(c) for ramp in m.values() for c in ramp}|{rgba(c) for c in read(base/'palette.json')['eyes'].values()}
    assert set(im.getchannel('A').tobytes())=={0,255}
    assert all(not p[3] or p in allowed for p in getattr(im,'get_flattened_data',im.getdata)())
    assert im.getbbox()[3]==35 and im.getbbox()[0]>0 and im.getbbox()[2]<40,im.getbbox()
    DOG.mkdir(parents=True,exist_ok=True);im.save(DOG/'pose.png')
    status=read(DOG/'pose.json')['status'] if (DOG/'pose.json').exists() else 'review'
    metadata={'character':'daisy','pose':'lying.left','status':status,
          'image':'pose.png','frame_size':[40,36],'draw_anchor':[20,30],'foot_anchor':[20,34],
          'source_idle':'../idle_left.png','approved_idle_sha256':hashlib.sha256((base/'idle_left.png').read_bytes()).hexdigest(),
          'head_offset':[4,6],'body_offset':[4,5],'tail_rotation_clockwise_degrees':90,
          'eyes':{'top_pixels':[[9,23]],'iris_offset_y':1},'layers_from_repo_root':paths,
          'palette':'../palette.json','source_recipe':(DOG_SOURCE/'recipe.json').relative_to(ROOT).as_posix(),
          'notes':'A single awake resting pose with folded legs, lowered chest, original face and floppy ear, large left flank spot and fluffy tail laid beside her. No animation or routine.'}
    write(DOG/'pose.json',metadata)
    write(DOG_SOURCE/'recipe.json',{'source_idle':'assets/characters/daisy/idle_left.png',
          'approved_idle_sha256':metadata['approved_idle_sha256'],'head_offset':[4,6],
          'body_offset':[4,5],'tail_source_pivot':[23,24],'tail_offset':[4,3],
          'tail_rotation_clockwise_degrees':90,'pose_output':'assets/characters/daisy/lying_left/pose.png',
          'folded_foreleg':[[16,29],[13,32],[9,33]],'folded_hind_leg':[[26,29],[28,31],[25,32]],
          'layers_from_repo_root':paths})
    return im


def build():
    rug();daisy_rest()
    print('Built one nonblocking woven rug and one static Daisy lying pose.')


if __name__=='__main__':build()
