"""Native named child bedrest; complete native head reused at documented pillow registration, eyelids separately drawn. No legacy upscaling."""
from PIL import Image,ImageDraw
from pathlib import Path
import json
ROLE='child';O='#281f24';SK='#e8c49d';SS='#c58e69';SL='#fae2bd';HAIR='#785132';HS='#3d2118';HL='#a47848'
def poly(d,q,c):d.polygon(q,fill=c,outline=O)
def head(im, dr):
    d = ImageDraw.Draw(im)
    child = ROLE == 'child'
    top = 18 if child else 2

    def p(q, c):
        poly(d, [(x, y + top) for x, y in q], c)

    def ln(q, c, w=1):
        d.line([(x, y + top) for x, y in q], fill=c, width=w)
    if dr in ['front', 'back']:
        if ROLE == 'mother':
            p([(19, 0), (27, 0), (31, 3), (33, 8), (32, 16), (29, 21), (18, 21), (15, 17), (14, 10), (16, 4)], HAIR)
        else:
            p([(18, 2), (20, 0), (24, 1), (27, 0), (30, 3), (32, 4), (31, 7), (33, 9), (31, 13), (30, 17), (27, 21), (21, 21), (17, 17), (15, 12), (14, 8), (16, 4)], HAIR)
        ln([(18, 5), (21, 3), (26, 2), (29, 4)], HL)
        if dr == 'front':
            p([(19, 9), (23, 7), (28, 9), (30, 12), (29, 17), (26, 21), (22, 21), (18, 17), (17, 13)], SK)
            ln([(28, 12), (29, 16), (27, 19)], SS)
            ln([(19, 13), (20, 13)], O)
            ln([(27, 13), (28, 13)], O)
            ln([(20, 14), (20, 14)], '#805736' if ROLE == 'mother' else '#4e7950')
            ln([(27, 14), (27, 14)], '#805736' if ROLE == 'mother' else '#4e7950')
            ln([(23, 18), (25, 18)], SS)
            p([(16, 6), (21, 3), (28, 4), (31, 8), (30, 11), (27, 9), (24, 10), (22, 8), (19, 11), (16, 13)], HAIR)
            ln([(19, 7), (23, 5), (27, 6)], HL)
            if ROLE == 'father':
                ln([(20, 18), (21, 20), (25, 22), (28, 19)], '#8d6951')
                ln([(23, 19), (25, 19)], SS)
        else:
            ln([(19, 7), (18, 13), (21, 17)], HS)
            ln([(24, 4), (25, 9), (28, 13)], HL)
            ln([(22, 19), (27, 19)], HS)
    else:
        p([(19, 1), (23, 0), (28, 1), (31, 4), (32, 8), (31, 13), (33, 15), (30, 18), (27, 21), (22, 21), (18, 17), (15, 12), (15, 7), (17, 3)], HAIR)
        ln([(18, 6), (22, 3), (27, 3)], HL)
        p([(25, 9), (29, 9), (30, 12), (34, 14), (33, 16), (30, 16), (29, 19), (26, 21), (23, 18), (22, 13)], SK)
        ln([(23, 12), (23, 17), (26, 19)], SS)
        ln([(28, 13), (29, 13)], O)
        ln([(28, 14), (28, 14)], '#805736' if ROLE == 'mother' else '#4e7950')
        ln([(28, 18), (29, 18)], SS)
        p([(22, 4), (27, 3), (31, 6), (31, 9), (28, 8), (25, 10), (22, 10), (21, 13)], HAIR)
        ln([(23, 6), (27, 5)], HL)
        if ROLE == 'mother':
            p([(16, 10), (20, 12), (21, 19), (19, 22), (16, 20), (15, 16)], HAIR)
            ln([(17, 13), (18, 18)], HL)
        if ROLE == 'father':
            ln([(25, 20), (28, 20), (30, 17)], '#8d6951')
P=Path(__file__).parent;ROOT=P.parents[5];OUT=ROOT/'assets/characters/named_hd/venn_child/bedrest';OUT.mkdir(parents=True,exist_ok=True)
standing=Image.new('RGBA',(48,72));head(standing,'front')
rest=Image.new('RGBA',(48,72));rest.alpha_composite(standing.crop((0,18,48,42)),(0,8));d=ImageDraw.Draw(rest);d.rectangle((22,29,26,33),fill=SK);d.line([(22,30),(22,32)],fill=SS)
rest.save(OUT/'rest_head.png');blink=rest.copy();d=ImageDraw.Draw(blink)
for x in [19,27]:
 d.rectangle((x,21,x+1,22),fill=SK);d.line([(x,22),(x+1,22)],fill='#71452c')
blink.save(OUT/'rest_blink.png')
meta={'version':1,'character':'venn_child','animation':'bedrest','status':'candidate','artwork_pixels_per_world_pixel':2,'frame_size':[48,72],'logical_size':[24,36],'draw_anchor':[24,24],'story_position_world':[60,112],'story_sort_y':167,'collision':'nonblocking; existing social foot point unchanged','cycle_ms':4800,'frames':[{'file':'rest_head.png','duration_ms':4640},{'file':'rest_blink.png','duration_ms':160}]}
(OUT/'animation.json').write_text(json.dumps(meta,indent=2))
E=ROOT/'docs/reviews/named_hd/venn_child/bedrest';E.mkdir(parents=True,exist_ok=True);sheet=Image.new('RGBA',(96,72),'#777b76');sheet.alpha_composite(rest,(0,0));sheet.alpha_composite(blink,(48,0));sheet.resize((576,432),Image.Resampling.NEAREST).save(E/'rest-6x.png')
frames=[]
for im in [rest,blink]:
 bg=Image.new('RGBA',(48,72),'#777b76');bg.alpha_composite(im);frames.append(bg.convert('RGB').resize((192,288),Image.Resampling.NEAREST))
frames[0].save(E/'rest-4x.gif',save_all=True,append_images=frames[1:],duration=[4640,160],loop=0)
changed=[(x,y) for y in range(72) for x in range(48) if rest.getpixel((x,y))!=blink.getpixel((x,y))];assert all(19<=x<=28 and 21<=y<=22 for x,y in changed);assert len(changed)>0;assert rest.getchannel('A').tobytes()==blink.getchannel('A').tobytes()
(E/'checks.json').write_text(json.dumps({'hard_alpha':set(rest.getchannel('A').getdata())<={0,255},'identical_registration_and_silhouette':True,'changed_eyelid_pixels':changed,'preserved_cadence_ms':[4640,160]},indent=2))
