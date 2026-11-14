"""Export complete Iselin scene drawings; reuse approved walks unchanged in pose."""
from pathlib import Path
from hashlib import sha256
import argparse
import io
import json
import sys
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.build_mira_combat import _main_component
SOURCE=ROOT/'assets/source/characters/iselin/scene_work'
GROUND=ROOT/'assets/story/regent_arrival/actors/iselin'
AERIAL=ROOT/'assets/story/regent_aerial/actors/iselin'


def png(image):
    out=io.BytesIO();image.save(out,format='PNG',optimize=True);return out.getvalue()


def json_bytes(value):return (json.dumps(value,indent=2)+'\n').encode()


def cells(path,columns,rows,records=None):
    image=Image.open(path).convert('RGBA');result=[]
    for row in range(rows):
        for col in range(columns):
            cell=image.crop((col*image.width//columns,row*image.height//rows,
                             (col+1)*image.width//columns,(row+1)*image.height//rows))
            cell.putalpha(cell.getchannel('A').point(lambda a:255 if a>=220 else 0))
            cell=_main_component(cell);bounds=cell.getbbox();result.append(cell.crop(bounds))
            if records is not None:records.append({'column':col,'row':row,'cell_bounds':[col*image.width//columns,row*image.height//rows,(col+1)*image.width//columns,(row+1)*image.height//rows],'silhouette_bounds_in_cell':list(bounds)})
    return result


def head_x(image):
    bounds=image.crop((0,0,image.width,image.height//4)).getbbox()
    return (bounds[0]+bounds[2])/2


def register(image,scale,canvas,origin):
    size=(round(image.width*scale),round(image.height*scale))
    x,y=origin;result=Image.new('RGBA',canvas)
    scaled=image.resize(size,Image.Resampling.NEAREST)
    bounds=scaled.getbbox()
    if x+bounds[0]<0 or y+bounds[1]<0 or x+bounds[2]>canvas[0] or y+bounds[3]>canvas[1]:
        raise ValueError(('Clipped complete pose',size,origin,canvas))
    result.alpha_composite(scaled,origin)
    return result


def products():
    outputs={};extractions={'poses':[],'diagonal':[],'aerial':[]}
    source=cells(SOURCE/'poses.png',3,2,extractions['poses'])
    scale=80/source[0].height
    poses={}
    for name,index in (('listen_left',0),('gesture_left',1),('turn_left_back',2)):
        image=source[index]
        poses[name]=register(image,scale,(80,96),(40-round(head_x(image)*scale),12))
    # Cinematic ordinary views use the approved complete idle/walk drawings.
    scale=80/68
    for direction in ('left','right','back'):
        image=Image.open(ROOT/f'assets/characters/iselin/idle_{direction}_42x72.png').convert('RGBA')
        poses['stand_'+direction]=register(image,scale,(80,96),(40-round(21*scale),92-round(68*scale)))
    loops={}
    for direction in ('left','back'):
        seq=[]
        for i in range(16):
            name=f'walk_{direction}_{i:02}.png'
            image=Image.open(ROOT/f'assets/characters/iselin/walk_{direction}/frame_{i+1:02}.png').convert('RGBA')
            outputs[GROUND/name]=png(register(image,scale,(80,96),(40-round(21*scale),92-round(68*scale))))
            seq.append({'file':name,'duration_ms':35})
        loops['walk_'+direction]=seq
    diagonal=cells(SOURCE/'diagonal.png',4,4,extractions['diagonal'])
    # One source density for the whole diagonal cycle; fixed crown grid, never boot-normalized.
    scale=80/max(image.height for image in diagonal)
    seq=[]
    for i,image in enumerate(diagonal):
        name=f'walk_left_back_{i:02}.png'
        sprite=register(image,scale,(80,96),(40-round(head_x(image)*scale),12+((1,1,0,0,1,2,2,1)*2)[i]))
        outputs[GROUND/name]=png(sprite);seq.append({'file':name,'duration_ms':35})
    loops['walk_left_back']=seq
    for name,image in poses.items():outputs[GROUND/(name+'.png')]=png(image)
    outputs[GROUND/'animation.json']=json_bytes({'version':1,'canvas':[80,96],'anchor':[40,92],
        'poses':{name:name+'.png' for name in poses},'loops':loops,
        'gaits':{'walk_left':{'stride_pixels':32}},
        'source':'Complete Iselin drawings and approved 16-frame walks; no limb assembly.'})
    aerial=cells(SOURCE/'aerial.png',2,1,extractions['aerial']);scale=28/max(image.height for image in aerial)
    for name,image in zip(('overhead','oblique'),aerial):
        outputs[AERIAL/(name+'.png')]=png(register(image,scale,(48,64),
            (24-round(head_x(image)*scale),56-round(image.height*scale))))
    outputs[AERIAL/'animation.json']=json_bytes({'version':1,'canvas':[48,64],'anchor':[24,56],
        'poses':{'overhead':'overhead.png','oblique':'oblique.png'},'loops':{},
        'overhead_facing':'north','oblique_facing':'northwest','source':'Complete authored Iselin aerial views.'})
    seated=source[3];scale=68/source[0].height
    sprite=register(seated,scale,(42,72),(21-round(head_x(seated)*scale),70-round(seated.height*scale)))
    outputs[ROOT/'assets/story/regent/poses/iselin_seated_42x72.png']=png(sprite)
    outputs[ROOT/'assets/story/regent/poses/iselin_seated.png']=png(sprite.resize((21,36),Image.Resampling.NEAREST))
    # Pillow versions can encode identical PNG pixels differently. Keep the
    # verified existing encoding so exporters remain stable across environments.
    for path,data in list(outputs.items()):
        if path.suffix=='.png' and path.exists():
            current=Image.open(path).convert('RGBA');expected=Image.open(io.BytesIO(data)).convert('RGBA')
            if current.size==expected.size and current.tobytes()==expected.tobytes():outputs[path]=path.read_bytes()
    outputs[SOURCE/'registration.json']=json_bytes({'generation_tool':'image_gen.imagegen',
        'references':['idle_front_master.png','idle_left_master.png','idle_back_master.png'],
        'source_sha256':{p.name:sha256(p.read_bytes()).hexdigest() for p in sorted(SOURCE.glob('*.png'))},
        'extractions':extractions,
        'registration':{'cinematic_pose_scale':80/source[0].height,'standing_crown_y':12,
            'approved_walk_scale':80/68,'approved_walk_source_anchor':[21,68],'cinematic_anchor':[40,92],
            'diagonal_scale':80/max(image.height for image in diagonal),
            'diagonal_origins':[[40-round(head_x(image)*80/max(c.height for c in diagonal)),12+((1,1,0,0,1,2,2,1)*2)[i]] for i,image in enumerate(diagonal)],
            'seated_scale':68/source[0].height,'seated_origin':[21-round(head_x(seated)*68/source[0].height),70-round(seated.height*68/source[0].height)],
            'aerial_scale':28/max(image.height for image in aerial),
            'aerial_origins':[[24-round(head_x(image)*28/max(c.height for c in aerial)),56-round(image.height*28/max(c.height for c in aerial))] for image in aerial]},
        'construction':'Complete generated pose cells; uniform whole-drawing sampling, alpha220 extraction and fixed body grid. No detached limbs or nonuniform scaling.',
        'exports':{str(p.relative_to(ROOT)):sha256(data).hexdigest() for p,data in outputs.items()}})
    return outputs


def build(check=False):
    output=products();changed=[]
    for path,data in output.items():
        if not path.exists() or path.read_bytes()!=data:changed.append(str(path.relative_to(ROOT)))
        if not check:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    if check and changed:raise SystemExit('Stale Iselin scene exports: '+', '.join(changed))
    return output


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true')
    build(parser.parse_args().check)
