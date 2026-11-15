"""Export approved, not-yet-integrated Caelan idles without changing runtime banks."""
from pathlib import Path
import hashlib
import json
import sys
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.build_mira_combat import _main_component
from tools.caelan_outline import apply_outline

SOURCE=ROOT/'assets/source/characters/caelan/idles_hd_review/idles_authored.png'
OUT=ROOT/'assets/characters/caelan/review_hd/idles'
REVIEW=ROOT/'docs/reviews/caelan_hd_idles'
DIRECTIONS=('front','left','right','back')


def build():
    atlas=Image.open(SOURCE).convert('RGBA');cells=[]
    for i in range(4):
        x,y=i%2,i//2
        rect=(round(x*atlas.width/2),round(y*atlas.height/2),
              round((x+1)*atlas.width/2),round((y+1)*atlas.height/2))
        body=_main_component(atlas.crop(rect));bounds=body.getbbox()
        cells.append((body,bounds,rect))
    # One source scale for the entire direction set, never stretch individual
    # limbs or normalize each body's height independently.
    scale=68/(cells[0][1][3]-cells[0][1][1]);drawings=[];records=[]
    for direction,(body,bounds,rect) in zip(DIRECTIONS,cells):
        crop=body.crop(bounds)
        resized=crop.resize((round(crop.width*scale),round(crop.height*scale)),Image.Resampling.NEAREST)
        low=max(bounds[1],bounds[3]-round(crop.height*.12))
        contacts=[x for y in range(low,bounds[3]) for x in range(bounds[0],bounds[2]) if body.getpixel((x,y))[3]]
        center=(min(contacts)+max(contacts)+1)/2
        x=round(24-(center-bounds[0])*scale);y=70-resized.height
        if min(x,y)<1 or x+resized.width>47 or y+resized.height>71:
            raise ValueError((direction,'Clipped silhouette',resized.size,(x,y)))
        image=Image.new('RGBA',(48,72));image.alpha_composite(resized,(x,y))
        drawings.append(image)
        records.append({'direction':direction,'file':'idle_'+direction+'.png',
                        'source_rect':list(rect),'source_bounds':list(bounds),
                        'destination':[x,y],'visible_size':list(resized.size)})
    # Shared palette preserves materials across all four drawings. Ignore
    # invisible source RGB so alpha matte cannot displace skin/teal highlights.
    colors=[p[:3] for im in drawings for p in im.get_flattened_data() if p[3]]
    ramp=Image.new('RGB',(len(colors),1));ramp.putdata(colors)
    palette=ramp.quantize(colors=64,dither=Image.Dither.NONE)
    OUT.mkdir(parents=True,exist_ok=True);REVIEW.mkdir(parents=True,exist_ok=True)
    final=[]
    for record,image in zip(records,drawings):
        alpha=image.getchannel('A')
        image=image.convert('RGB').quantize(palette=palette,dither=Image.Dither.NONE).convert('RGBA')
        image.putalpha(alpha);image=apply_outline(image)
        image.save(OUT/record['file']);final.append(image)
    manifest={'version':1,'status':'approved','design_status':'approved','artwork_status':'approved',
        'runtime_integration':True,
        'source':str(SOURCE.relative_to(ROOT)),'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        'frame_size':[48,72],'logical_size':[24,36],'artwork_pixels_per_world_pixel':2,
        'draw_anchor':[24,60],'foot_anchor':[24,68],'source_scale':scale,
        'palette_colors':64,'anatomical_left_hip_pouch':True,'drawings':records}
    (OUT/'idles.json').write_text(json.dumps(manifest,indent=2)+'\n')
    sheet=Image.new('RGBA',(192,72))
    for i,image in enumerate(final):sheet.alpha_composite(image,(48*i,0))
    sheet.save(OUT/'spritesheet.png')
    font_path='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    font=ImageFont.truetype(font_path,19);small=ImageFont.truetype(font_path,15)
    preview=Image.new('RGB',(896,520),'#252e35');d=ImageDraw.Draw(preview)
    d.text((24,14),'Caelan | directional idle review | 48 x 72 artwork',font=font,fill='#edf0e9')
    for i,(direction,image) in enumerate(zip(DIRECTIONS,final)):
        x=16+224*i
        d.text((x+75,60),direction.title(),font=font,fill='#e4cd94')
        d.line((x+12,370,x+192,370),fill='#48555b')
        preview.paste(image.resize((192,288),Image.Resampling.NEAREST),(x,90),image.resize((192,288),Image.Resampling.NEAREST))
        preview.paste(image,(x+72,414),image)
    d.text((24,389),'Bottom row: normal size at a 960 x 640 game viewport',font=small,fill='#bdc8cd')
    preview.save(REVIEW/'directions.png')
    print('Exported four approved 48x72 idles; runtime registration retained.')


if __name__=='__main__':build()
