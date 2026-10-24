"""Export Tomas's shorter left/right/back idles and opaque review boards."""
import json

from PIL import Image, ImageDraw

from build_tomas_idle import BACKGROUND, OUT, SOURCE, font, rgb, sample_source, write_json


def build():
    recipe=json.loads((SOURCE/'turnaround_export.json').read_text())
    palette=json.loads((OUT/'palette.json').read_text())
    source=Image.open(SOURCE/recipe['source']).convert('RGBA')
    allowed={(*rgb(c),255) for ramp in palette['materials'].values() for c in ramp}
    allowed.update((*rgb(c),255) for c in palette['eyes'].values())
    patch=(*rgb(palette['materials']['patch'][0]),255)
    iris=(*rgb(palette['eyes']['iris']),255)
    for direction,view in recipe['views'].items():
        native=sample_source(source,view,palette)
        assert native.size==(24,36)
        assert native.getbbox()[1::2]==(3,35), 'Expected 32 visible rows, foot baseline 34'
        assert set(native.getchannel('A').tobytes())=={0,255}
        pixels=[native.getpixel((x,y)) for y in range(36) for x in range(24)]
        assert all(not p[3] or p in allowed for p in pixels)
        assert pixels.count(iris)==(0 if direction=='back' else 1)
        assert (patch in pixels)==(direction=='left'), 'Patch belongs on near left knee only'
        assert all(26<=y<31 for y in range(36) for x in range(24)
                   if native.getpixel((x,y))==patch), 'Patch must remain at the knee'
        native.save(OUT/f'idle_{direction}.png')
        directory=SOURCE/f'idle_{direction}_layers'
        directory.mkdir(exist_ok=True)
        combined=Image.new('RGBA',native.size)
        layers=[]
        for name,(first,last) in recipe['layers'].items():
            layer=Image.new('RGBA',native.size)
            layer.paste(native.crop((0,first,24,last)),(0,first))
            layer.save(directory/f'{name}.png')
            combined.alpha_composite(layer)
            layers.append(f'../../source/characters/tomas/{directory.name}/{name}.png')
        assert combined.tobytes()==native.tobytes()
        review=Image.new('RGB',(720,1040),BACKGROUND)
        draw=ImageDraw.Draw(review)
        draw.text((32,16),f'Tomas — {direction} idle',font=font(28),fill='#26343e')
        draw.text((32,54),'24×36 frame · 32 px visible height · 24× review',font=font(20),fill='#52616c')
        enlarged=native.resize((576,864),Image.Resampling.NEAREST)
        review.paste(enlarged,(72,96),enlarged)
        draw.text((32,984),'Turnaround · approved front preserved',font=font(23),fill='#26343e')
        review.save(OUT/f'idle_{direction}_review.png')
        path=OUT/f'idle_{direction}.json'
        status=json.loads(path.read_text())['status'] if path.exists() else 'review'
        box=native.getbbox()
        write_json(path,{
            'character':'tomas','animation':f'idle.{direction}','design_status':'approved','status':status,
            'image':f'idle_{direction}.png','frame_size':[24,36],'rect':[0,0,24,36],
            'occupied_rect':[box[0],box[1],box[2]-box[0],box[3]-box[1]],
            'visible_height_px':32,'foot_anchor':[12,34],
            'palette':'palette.json','source':'../../source/characters/tomas/idle_turnaround_concept.png',
            'export_recipe':'../../source/characters/tomas/turnaround_export.json','recipe_view':direction,
            'layers':layers,'eyes':view['eyes'],
            'knee_patch':{'anatomical_side':'left','placement':'front_of_knee','visible':direction=='left',
                          'visibility_reason':{'left':'near left leg','right':'occluded by near right leg',
                                               'back':'front of knee faces away'}[direction]},
            'review':{'image':f'idle_{direction}_review.png','scale':24,'background':BACKGROUND}
        })
    sheet=Image.new('RGBA',(96,36))
    board=Image.new('RGB',(1280,656),BACKGROUND)
    draw=ImageDraw.Draw(board)
    draw.text((32,16),'Tomas — idle turnaround',font=font(30),fill='#26343e')
    draw.text((32,60),'24×36 frames · 32 px visible height · 12× nearest-neighbor',font=font(22),fill='#52616c')
    records=[]
    for i,direction in enumerate(['front','left','right','back']):
        native=Image.open(OUT/f'idle_{direction}.png').convert('RGBA')
        sheet.paste(native,(i*24,0))
        enlarged=native.resize((288,432),Image.Resampling.NEAREST)
        x=32+i*312
        board.paste(enlarged,(x,128),enlarged)
        status=json.loads((OUT/f'idle_{direction}.json').read_text())['status']
        draw.text((x+28,590),f'{direction.title()} · {status}',font=font(20),fill='#26343e')
        records.append({'direction':direction,'rect':[i*24,0,24,36],'status':status})
    sheet.save(OUT/'idle_all.png')
    board.save(OUT/'idle_all_review.png')
    write_json(OUT/'idle_all.json',{'character':'tomas','image':'idle_all.png',
        'frame_size':[24,36],'foot_anchor':[12,34],'visible_height_px':32,
        'frames':records,'review':'idle_all_review.png'})
    board=Image.new('RGB',(1856,1040),BACKGROUND)
    draw=ImageDraw.Draw(board)
    draw.text((32,16),'Tomas — left, right and back idles for review',font=font(30),fill='#26343e')
    draw.text((32,60),'24×36 frame · 32 px visible height · 24× nearest-neighbor',font=font(22),fill='#52616c')
    for i,direction in enumerate(['left','right','back']):
        native=Image.open(OUT/f'idle_{direction}.png').convert('RGBA')
        enlarged=native.resize((576,864),Image.Resampling.NEAREST)
        x=32+i*608
        board.paste(enlarged,(x,96),enlarged)
        draw.text((x+220,986),direction.title(),font=font(26),fill='#26343e')
    board.save(OUT/'idle_turnaround_review.png')
    print('Exported Tomas left/right/back: 24×36 frames, 32 visible rows, 12 layers and opaque review boards.')


if __name__=='__main__':
    build()
