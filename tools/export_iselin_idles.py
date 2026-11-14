"""Register generated directional drawings without painting or mirroring art."""
from hashlib import sha256
import json
from PIL import Image, ImageDraw
from tools.export_iselin_first_assets import ROOT, BASE, REVIEW, SPRITE, encoded, json_bytes, matte, font


def products():
    outputs={};records={};directions=('front','left','right','back')
    animation={'idles':{},'walks':{},'high_resolution_idles':{}}
    board=Image.new('RGB',(840,560),'#e8edf2');draw=ImageDraw.Draw(board)
    draw.text((20,16),'ISELIN / FOUR DIRECTIONAL IDLES / 42 x 72',font=font(23),fill='#263c35')
    draw.text((20,52),'Actual exports enlarged 4x; normal party scale at 2x artwork density.',font=font(16),fill='#263c35')
    for index,direction in enumerate(directions):
        source=f'assets/source/characters/iselin/idle_{direction}_master.png'
        master=Image.open(ROOT/source).convert('RGBA')
        master.putalpha(master.getchannel('A').point(lambda v:255 if v>=128 else 0))
        bounds=master.getbbox();crop=master.crop(bounds)
        scale=68/crop.height;size=(round(crop.width*scale),68)
        if size[0]>40:raise ValueError('Directional art would clip: '+direction)
        image=Image.new('RGBA',(42,72));origin=((42-size[0])//2,2)
        image.alpha_composite(crop.resize(size,Image.Resampling.NEAREST),origin)
        if direction=='front':
            # Preserve the approved export byte-for-byte.
            image=Image.open(ROOT/BASE/'idle_front_42x72.png').convert('RGBA')
        else:
            outputs[f'{BASE}/idle_{direction}_42x72.png']=encoded(image)
            outputs[f'{BASE}/idle_{direction}_logical.png']=encoded(image.resize((21,36),Image.Resampling.NEAREST))
        animation['idles'][direction]=f'{BASE}/idle_{direction}_logical.png'
        animation['high_resolution_idles'][direction]={'image':f'{BASE}/idle_{direction}_42x72.png','draw_anchor':[21,60]}
        records[direction]={'source':source,'sha256':sha256((ROOT/source).read_bytes()).hexdigest(),
                            'bounds':list(bounds),'nominal_uniform_scale':scale,'rounded_size':list(size),'origin':list(origin)}
        x=index*210+21
        board.paste(matte(image,4),(x,100))
        draw.text((x+84,405),direction.upper(),anchor='mt',font=font(19),fill='#263c35')
        board.paste(matte(image),(x+63,448))
    outputs[f'{BASE}/animation.json']=json_bytes(animation)
    outputs[f'{REVIEW}/directional_idles.png']=encoded(board)
    outputs['assets/source/characters/iselin/directional_registration.json']=json_bytes({
        'generation_tool':'image_gen.imagegen','reference':SPRITE,
        'method':'Separate authored directional views; hard-alpha extraction and uniform nearest-neighbor registration only.',
        'anatomy':'Braid anatomical left, mantle/brooch anatomical right; braid falls over chest.',
        'frame_size':[42,72],'logical_frame_size':[21,36],'draw_anchor':[21,60],
        'foot_anchor':[21,68],'records':records})
    actor=json.loads((ROOT/BASE/'actor.json').read_text())
    actor['scope']='Four directional idles; walking and cinematic poses remain future work.'
    outputs[f'{BASE}/actor.json']=json_bytes(actor)
    return outputs
