"""Matching native wooden food/water bowls with three static fill states."""
from PIL import Image,ImageChops,ImageDraw

from build_liam_family_front_walks import ROOT,read,write,blank,rgba

SOURCE=ROOT/'assets/source/terrain/eldenmere/liam_home'
OUT=ROOT/'assets/terrain/eldenmere/liam_home/bowls'


def store(path,im):
    path.parent.mkdir(parents=True,exist_ok=True);im.save(path)
    return path.relative_to(ROOT).as_posix()


def build():
    recipe=read(SOURCE/'bowls_recipe.json');size=tuple(recipe['frame_size'])
    wood=read(ROOT/recipe['wood_palette_source'])['palette']
    water=read(ROOT/recipe['water_palette_source'])['palette']
    outer=blank(size);d=ImageDraw.Draw(outer)
    # Carved sides sit below a wide lip; the bowl is shallow at character scale.
    d.ellipse((5,16,18,19),fill=wood['outline'])
    d.polygon(((4,12),(19,12),(18,16),(16,18),(7,18),(5,16)),fill=wood['outline'])
    d.polygon(((5,13),(18,13),(17,16),(15,17),(8,17),(6,16)),fill=wood['wood_base'])
    d.line((7,16,16,16),fill=wood['wood_shadow'])
    d.line((8,17,14,17),fill=wood['wood_light'])
    # The same recessed wooden interior is visible in both empty variants.
    d.ellipse((4,8,19,16),fill=wood['wood_light'],outline=wood['outline'])
    d.ellipse((6,9,17,14),fill=wood['wood_shadow'])
    d.line((8,12,15,12),fill=wood['wood_base'])
    d.line((9,13,14,13),fill=wood['wood_light'])
    rim=blank(size);d=ImageDraw.Draw(rim)
    d.line((8,9,15,9),fill=wood['wood_worn'])
    d.line((5,13,6,15,9,16,14,16,18,14),fill=wood['wood_worn'],width=1)
    d.point((17,10),fill=wood['wood_base'])
    mask=Image.new('L',size);ImageDraw.Draw(mask).ellipse((7,10,16,13),fill=255)
    # Keep the half fill lower in the carved well and visibly smaller.
    half=Image.new('L',size);ImageDraw.Draw(half).ellipse((8,12,15,13),fill=255)
    half=ImageChops.multiply(half,mask)
    common=blank(size);common.alpha_composite(outer);common.alpha_composite(rim)
    front=blank(size)
    for y in range(13,24):
        for x in range(24):
            if not mask.getpixel((x,y)):front.putpixel((x,y),common.getpixel((x,y)))
    store(OUT/'front_overlay.png',front)
    store(SOURCE/'bowls_parts/wooden_body.png',outer)
    store(SOURCE/'bowls_parts/front_rim.png',rim)
    store(OUT/'content_mask.png',mask)
    store(OUT/'half_content_mask.png',half)
    records={};sheet=blank((72,48))
    for row,kind in enumerate(('food','water')):
        states={}
        for column,(state,fraction) in enumerate(recipe['states'].items()):
            contents=blank(size);active=mask if state=='full' else half if state=='half_full' else Image.new('L',size)
            d=ImageDraw.Draw(contents)
            if kind=='water':
                d.rectangle((0,0,23,23),fill=water['water_base'])
                d.line((7,13,16,13),fill=water['water_dark'])
                d.line((10 if state=='full' else 11,11 if state=='full' else 12,13,11 if state=='full' else 12),fill=water['water_light'])
            else:
                m=recipe['food_palette'];d.rectangle((0,0,23,23),fill=m['base'])
                for x,y in ((8,10),(11,11),(14,10),(9,12),(14,12)):
                    d.rectangle((x,y,x+1,y+1),fill=m['light'])
                    d.point((x+1,y+1),fill=m['shadow'])
                for p in ((10,10),(13,12),(15,11)):d.point(p,fill=m['crumb'])
            contents.putalpha(active)
            image=outer.copy();image.alpha_composite(contents);image.alpha_composite(rim)
            # Wood, shadow, registration and collision never change with fill.
            for y in range(24):
                for x in range(24):
                    if not mask.getpixel((x,y)):assert image.getpixel((x,y))==common.getpixel((x,y))
            file=store(OUT/f'{kind}_{state}.png',image)
            content_file=store(SOURCE/f'bowls_parts/{kind}_{state}_contents.png',contents)
            states[state]={'image_from_repo_root':file,'fill_fraction':fraction,
                           'content_pixels':sum(bool(v) for v in active.tobytes()),
                           'layers_from_repo_root':[(SOURCE/'bowls_parts/wooden_body.png').relative_to(ROOT).as_posix(),
                                                    content_file,(SOURCE/'bowls_parts/front_rim.png').relative_to(ROOT).as_posix()]}
            sheet.alpha_composite(image,(column*24,row*24))
        records[kind]={'states':states,'default_state':'full'}
    store(OUT/'spritesheet.png',sheet)
    metadata={**recipe,'bowls':records,'sheet':'spritesheet.png','sheet_rows':['food','water'],
              'front_overlay':'front_overlay.png',
              'sheet_columns':list(recipe['states']),'animated':False,
              'content_mask':'content_mask.png','half_content_mask':'half_content_mask.png',
              'source_recipe':(SOURCE/'bowls_recipe.json').relative_to(ROOT).as_posix()}
    write(OUT/'bowls.json',metadata)
    print('Built wooden food and water bowls: full, half-full and empty; fixed native registration.')
    return metadata


if __name__=='__main__':build()
