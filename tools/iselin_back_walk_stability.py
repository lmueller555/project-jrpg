"""Register unified body redraws by crown/belt; retain reviewed lower legs."""
import json
from hashlib import sha256
from PIL import Image
from tools.build_mira_combat import _main_component


def stabilize(source, frames):
    root=source/'body_stability_v3'
    authored=json.loads((root/'landmarks.json').read_text())
    records=[];result=[]
    for i,record in enumerate(authored['frames']):
        path=root/record['source'];strip=Image.open(path).convert('RGBA')
        col=record['column'];cell=strip.crop((col*strip.width//4,0,(col+1)*strip.width//4,strip.height))
        cell.putalpha(cell.getchannel('A').point(lambda a:255 if a>=220 else 0))
        cell=_main_component(cell)
        if list(cell.getbbox())!=record['bounds']:
            raise ValueError('Body drawing changed: re-audit landmarks')
        cell=cell.crop(record['bounds'])
        scale=authored['crown_to_belt']/(record['belt'][1]-record['crown'][1])
        size=(round(cell.width*scale),round(cell.height*scale))
        # Body registration is independent of every foot pixel and pose height.
        origin=(21-round(record['crown'][0]*scale),authored['crown_base_y']+authored['bob'][i])
        drawing=Image.new('RGBA',(42,72))
        drawing.alpha_composite(cell.resize(size,Image.Resampling.NEAREST),origin)
        # Restore the reviewed shin/boot movement, without any limb transforms.
        drawing.paste(frames[i].crop((0,48,42,72)),(0,48))
        result.append(drawing)
        records.append({**record,'sha256':sha256(path.read_bytes()).hexdigest(),
                        'scale':scale,'size':list(size),'origin':list(origin),
                        'restored_region_before_coat_cleanup':[0,48,42,72]})
    joins=json.loads((root/'join_landmarks.json').read_text())
    join_records=[]
    for record in joins['frames']:
        i=record['frame']-1;path=root/record['source']
        strip=Image.open(path).convert('RGBA');col=record['column']
        cell=strip.crop((col*strip.width//4,0,(col+1)*strip.width//4,strip.height))
        cell.putalpha(cell.getchannel('A').point(lambda a:255 if a>=220 else 0))
        cell=_main_component(cell)
        if list(cell.getbbox())!=record['bounds']:
            raise ValueError('Join cleanup changed: re-audit landmarks')
        cell=cell.crop(record['bounds']);scale=27/record['belt'][1]
        size=(round(cell.width*scale),round(cell.height*scale))
        origin=(21-round(record['crown'][0]*scale),2+authored['bob'][i])
        drawing=Image.new('RGBA',(42,72))
        drawing.alpha_composite(cell.resize(size,Image.Resampling.NEAREST),origin)
        window=(9,38,34,54)
        result[i].paste(drawing.crop(window),window)
        join_records.append({**record,'scale':scale,'size':list(size),'origin':list(origin),
                             'edit_window':list(window),'sha256':sha256(path.read_bytes()).hexdigest()})
    return result,{'registration':'Uniform complete-drawing scale from crown-to-belt distance; head center x21; explicit 0–2px two-step bob. Reviewed lower legs restored unchanged.',
                   'landmark_sha256':sha256((root/'landmarks.json').read_bytes()).hexdigest(),
                   'frames':records,'bob':authored['bob'],'coat_join_cleanup':join_records,
                   'final_preserved_region':[0,54,42,72],
                   'join_landmark_sha256':sha256((root/'join_landmarks.json').read_bytes()).hexdigest()}
