"""Export Serene's three turnaround views without rewriting her approved front."""
import json

from PIL import Image, ImageDraw

from build_serene_idle import BACKGROUND, OUT, SOURCE, font, rgb, write_json


def export_view(direction, recipe, source, palette):
    native = Image.new('RGBA', (24, 36))
    left, _, right, _ = recipe['source_bounds']
    offset, width = recipe['native_x'], recipe['native_width']
    for band in recipe['bands']:
        top, bottom = band['source_y']
        first, last = band['native_y']
        sampled = source.crop((left, top, right, bottom)).resize(
            (width, last - first), Image.Resampling.NEAREST)
        for y in range(sampled.height):
            for x in range(sampled.width):
                pixel = sampled.getpixel((x, y))
                if pixel[3] < 128:
                    continue
                sx = left + int((x + .5) * (right - left) / width)
                sy = top + int((y + .5) * (bottom - top) / sampled.height)
                materials = band['materials']
                for window in recipe['material_windows']:
                    x0, y0, x1, y1 = window['rect']
                    if x0 <= sx < x1 and y0 <= sy < y1:
                        materials = window['materials']
                colors = [rgb(c) for m in materials for c in palette['materials'][m]]
                color = min(colors, key=lambda c: sum((a-b)**2 for a,b in zip(c, pixel[:3])))
                native.putpixel((offset + x, first + y), (*color, 255))
    for x,y in recipe['eyes']:
        native.putpixel((x,y), (*rgb(palette['eyes']['pupil']),255))
        native.putpixel((x,y+1), (*rgb(palette['eyes']['iris']),255))

    assert native.size == (24,36)
    assert native.getbbox()[1::2] == (1,35), 'Height/foot baseline differs'
    assert set(native.getchannel('A').tobytes()) == {0,255}
    allowed = {(*rgb(c),255) for colors in palette['materials'].values() for c in colors}
    allowed.update((*rgb(c),255) for c in palette['eyes'].values())
    assert all(native.getpixel((x,y))[3] == 0 or native.getpixel((x,y)) in allowed
               for y in range(36) for x in range(24))
    if direction == 'back':
        assert not recipe['eyes']
        assert (*rgb(palette['eyes']['iris']),255) not in [native.getpixel((x,y)) for y in range(36) for x in range(24)]
    native.save(OUT / f'idle_{direction}.png')
    layer_dir = SOURCE / f'idle_{direction}_layers'
    layer_dir.mkdir(exist_ok=True)
    combined = Image.new('RGBA', native.size)
    layer_paths = []
    for name, rows in {'head':[0,14], 'bodice_and_arms':[14,22],
                       'skirt_and_hands':[22,29], 'legs_and_boots':[29,36]}.items():
        layer = Image.new('RGBA',native.size)
        layer.paste(native.crop((0,rows[0],24,rows[1])),(0,rows[0]))
        layer.save(layer_dir / f'{name}.png')
        combined.alpha_composite(layer)
        layer_paths.append(f'../../source/characters/serene/{layer_dir.name}/{name}.png')
    assert combined.tobytes() == native.tobytes()
    review = Image.new('RGB',(720,1040),BACKGROUND)
    draw = ImageDraw.Draw(review)
    draw.text((32,16),f'Mother Serene — {direction} idle',font=font(28),fill='#26343e')
    draw.text((32,54),'24×36 pixels · 24× nearest-neighbor · review',font=font(20),fill='#52616c')
    enlarged = native.resize((576,864),Image.Resampling.NEAREST)
    review.paste(enlarged,(72,96),enlarged)
    draw.text((32,984),'Turnaround · approved front design',font=font(23),fill='#26343e')
    review.save(OUT / f'idle_{direction}_review.png')
    path = OUT / f'idle_{direction}.json'
    status = json.loads(path.read_text())['status'] if path.exists() else 'review'
    write_json(path,{
        'character':'serene','display_name':'Mother Serene','animation':f'idle.{direction}',
        'design_status':'approved','status':status,'image':f'idle_{direction}.png',
        'frame_size':[24,36],'rect':[0,0,24,36],'foot_anchor':[12,34],
        'palette':'palette.json','source':'../../source/characters/serene/idle_turnaround_concept.png',
        'export_recipe':'../../source/characters/serene/turnaround_export.json',
        'recipe_view':direction,'layers':layer_paths,
        'eyes':{'top_pixels':recipe['eyes'],'height':2 if recipe['eyes'] else 0,
                'pupil_color':palette['eyes']['pupil'],'iris_color':palette['eyes']['iris']},
        'dress':{'hem_row':28},
        'review':{'image':f'idle_{direction}_review.png','scale':24,'background':BACKGROUND}
    })


def main():
    recipe = json.loads((SOURCE/'turnaround_export.json').read_text())
    palette = json.loads((OUT/'palette.json').read_text())
    source = Image.open(SOURCE/recipe['source']).convert('RGBA')
    for direction, view in recipe['views'].items():
        export_view(direction,view,source,palette)
    sheet = Image.new('RGBA',(96,36))
    board = Image.new('RGB',(1280,656),BACKGROUND)
    draw = ImageDraw.Draw(board)
    draw.text((32,16),'Mother Serene — idle turnaround',font=font(30),fill='#26343e')
    draw.text((32,60),'24×36 frames · 12× nearest-neighbor · shared foot baseline',font=font(22),fill='#52616c')
    frames = []
    for i,direction in enumerate(['front','left','right','back']):
        sprite = Image.open(OUT/f'idle_{direction}.png').convert('RGBA')
        sheet.paste(sprite,(i*24,0))
        # Four columns fit at 12×; the separate new-views board uses 24×.
        enlarged = sprite.resize((288,432),Image.Resampling.NEAREST)
        x = 32+i*312
        board.paste(enlarged,(x,128),enlarged)
        status = json.loads((OUT/f'idle_{direction}.json').read_text())['status']
        draw.text((x+28,590),f'{direction.title()} · {status}',font=font(20),fill='#26343e')
        frames.append({'direction':direction,'rect':[i*24,0,24,36],'status':status})
    board.save(OUT/'idle_all_review.png')
    sheet.save(OUT/'idle_all.png')
    write_json(OUT/'idle_all.json',{'character':'serene','image':'idle_all.png',
        'frame_size':[24,36],'foot_anchor':[12,34],'frames':frames,
        'review':'idle_all_review.png'})
    new_board = Image.new('RGB',(1856,1040),BACKGROUND)
    draw = ImageDraw.Draw(new_board)
    draw.text((32,16),'Mother Serene — left, right and back idles for review',font=font(30),fill='#26343e')
    draw.text((32,60),'Native 24×36 · enlarged 24× · approved front preserved',font=font(22),fill='#52616c')
    for i,direction in enumerate(['left','right','back']):
        sprite=Image.open(OUT/f'idle_{direction}.png').convert('RGBA').resize((576,864),Image.Resampling.NEAREST)
        x=32+i*608
        new_board.paste(sprite,(x,96),sprite)
        draw.text((x+220,986),direction.title(),font=font(26),fill='#26343e')
    new_board.save(OUT/'idle_turnaround_review.png')
    print('Exported three 24×36 idles, 12 source layers, native four-view sheet and opaque review boards.')


if __name__ == '__main__':
    main()
