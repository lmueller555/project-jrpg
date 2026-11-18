"""Source-authored interior architecture extension for the live Eldenmere builder.

Wiring (the caller owns products and disk writes)::

    from tools.eldenmere_interior_architecture import apply_interior_architecture
    interior_review = apply_interior_architecture(maps, paths, ex, furnishing)

Call after the established room furnishing loop, before overview/map JSON export.
The extension only mutates the supplied in-memory maps/paths/Export collector.
It also loads the three Serene household rooms through their existing registry;
those curated fixtures, cues and scene identities are deliberately not rebuilt.
All placements and additions are declared in the source recipe. No runtime file
writes, prices, inventory, actor creation, quest state or recovery logic live here.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json
import math

from PIL import Image, ImageChops, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'assets/source/maps/eldenmere/town_hd/interior_architecture'
PREFIX = 'rooms/interior_architecture'
RECIPE_PATH = SOURCE / 'recipe.json'


def recipe():
    return json.loads(RECIPE_PATH.read_text())


def _rgba(value):
    if isinstance(value, str):
        value = value.lstrip('#')
        return tuple(int(value[i:i+2], 16) for i in (0, 2, 4)) + (255,)
    return tuple(value) if len(value) == 4 else tuple(value)+(255,)


def _shade(color, amount):
    color = _rgba(color)
    return tuple(max(0, min(255, c+amount)) for c in color[:3])+(color[3],)


class Draft:
    """Small native pixel-art draft with logical design coordinates.

    Fine joints, grain, rivets, weave and external contours are one *artwork*
    pixel. Geometry remains on the logical grid; no supersampling/soft alpha.
    """
    def __init__(self, size, palette):
        self.image = Image.new('RGBA', tuple(v*2 for v in size))
        self.draw = ImageDraw.Draw(self.image)
        self.palette = palette

    def color(self, value):
        return _rgba(self.palette.get(value, value))

    def rect(self, box, fill, outline=None, width=1):
        self.draw.rectangle(tuple(round(v*2) for v in box),
                            fill=self.color(fill),
                            outline=self.color(outline) if outline else None,
                            width=width)

    def poly(self, points, fill, outline='contour'):
        self.draw.polygon([(round(x*2), round(y*2)) for x, y in points],
                          fill=self.color(fill), outline=self.color(outline) if outline else None)

    def line(self, points, color, width=1):
        self.draw.line([(round(x*2), round(y*2)) for x, y in points],
                       fill=self.color(color), width=width)

    def ellipse(self, box, fill, outline='contour', width=1):
        self.draw.ellipse(tuple(round(v*2) for v in box),
                          fill=self.color(fill),
                          outline=self.color(outline) if outline else None, width=width)

    def timber(self, box, dark=False, vertical=False):
        x0, y0, x1, y1 = box
        self.rect(box, 'oak_shadow' if dark else 'oak', 'contour')
        self.line([(x0+.5, y1-.5), (x0+.5, y0+.5), (x1-.5, y0+.5)], 'oak_light')
        self.line([(x0+1, y1-1), (x1-1, y1-1), (x1-1, y0+1)], 'oak_dark')
        if vertical:
            for x in range(round(x0+2), round(x1), 3):
                self.line([(x, y0+2), (x+.5, y1-2)], 'oak_shadow')
        else:
            for y in range(round(y0+2), round(y1), 3):
                self.line([(x0+2, y), (x1-2, y+.5)], 'oak_shadow')
        for x, y in ((x0+1.5, y0+1.5), (x1-1.5, y1-1.5)):
            self.rect((x, y, x+.5, y+.5), 'iron_shadow')

    def sack(self, box, tied=False):
        x, y, w, h = box
        # A short gathered neck above a broad, weight-bearing bag, not the
        # repeated hourglass silhouette of a long tie and narrow body.
        if tied:
            self.poly([(x+w*.5-2,y),(x+w*.5+2,y),(x+w*.5+1,y+3),
                       (x+w-2,y+5),(x+w,y+h-3),(x+w-2,y+h),
                       (x+2,y+h),(x,y+h-3),(x+2,y+5),(x+w*.5-1,y+3)],'canvas')
            self.line([(x+w*.5-2,y+3),(x+w*.5+2,y+3)],'oak_shadow',2)
        else:
            self.poly([(x+2,y+2),(x+w-2,y+2),(x+w-1,y+5),
                       (x+w,y+h-3),(x+w-2,y+h),(x+2,y+h),
                       (x,y+h-3),(x+1,y+5)],'canvas')
        self.line([(x+2,y+6),(x+1,y+h-4),(x+3,y+h-1)],'canvas_light')
        self.line([(x+w-2,y+6),(x+w-1,y+h-4),(x+w-3,y+h-1)],'canvas_shadow')
        for i in range(4, int(w)-2, 3):
            self.line([(x+i,y+7),(x+i-.5,y+h-3)],'canvas_shadow')
        for j in range(8, int(h)-2, 3):
            self.line([(x+2,y+j),(x+w-2,y+j)],'canvas_light')
        if not tied:
            self.ellipse((x+1,y,x+w-1,y+4),'canvas_light')
            self.ellipse((x+2,y+1,x+w-2,y+3),'grain','oak_shadow')
            for i in range(3,int(w)-2,2):
                self.line([(x+i,y+1),(x+i+.5,y+2)],'canvas_light')

    def cloth(self, box, color, folded=True):
        x, y, w, h = box
        self.rect((x,y,x+w,y+h), color, 'contour')
        self.line([(x+1,y+1),(x+w-1,y+1)], _shade(color,24))
        for row in range(2, int(h), 3):
            self.line([(x+1,y+row),(x+w-1,y+row)], _shade(color,-16))
        for col in range(2,int(w),4):
            self.line([(x+col,y+1),(x+col,y+h-1)], _shade(color,12))
        if folded:self.line([(x+w-3,y+1),(x+w-3,y+h-1)], _shade(color,-30))

    def jar(self, box, color='glass'):
        x, y, w, h = box
        neck=max(2,w*.38)
        self.rect((x+(w-neck)/2,y,x+(w+neck)/2,y+2), 'oak_shadow', 'contour')
        self.poly([(x+(w-neck)/2,y+2),(x+(w+neck)/2,y+2),
                   (x+w-1,y+4),(x+w,y+h-2),(x+w-1,y+h),
                   (x+1,y+h),(x,y+h-2),(x+1,y+4)], color)
        self.line([(x+1.5,y+4),(x+1,y+h-2)], _shade(self.color(color),38))
        self.line([(x+w-1,y+5),(x+w-1,y+h-2),(x+2,y+h-1)], _shade(self.color(color),-30))
        self.rect((x+1,y+h*.56,x+w-1,y+h*.56+2), 'canvas_light')
        self.line([(x+2,y+4),(x+2.5,y+5)], '#e0e3c5')


def _storage(size, style, palette, linen):
    """Open, purpose-specific supplies replace misleading cottage imagery."""
    d = Draft(size, palette)
    w,h = size
    if h <= 26:
        d.timber((2,h-7,w-2,h-4))
        d.poly([(4,h-4),(7,h-4),(7,h-1)], 'oak_dark')
        d.poly([(w-7,h-4),(w-4,h-4),(w-7,h-1)], 'oak_dark')
        base = h-8
        if style == 'workshop':
            for x in (7,17,28):
                d.rect((x,base-9,x+2,base), 'iron', 'contour')
                d.rect((x-2,base-10,x+5,base-7), 'iron_shadow', 'contour')
            d.jar((36,base-10,6,10),'#929d87')
        elif style == 'grain':
            d.jar((5,base-12,8,12), '#bd9c60')
            d.jar((18,base-10,7,10), '#aaa480')
            # Grain measure and wooden scoop, not books/domestic crockery.
            d.timber((29,base-7,42,base))
            d.line([(32,base-5),(42,base-11)], 'oak_light', 3)
        else:
            d.cloth((5,base-7,15,7), linen)
            d.jar((27,base-11,8,11), '#b9ad8c')
        return d.image
    # Retain the established supporting silhouette/canvas, draw open storage.
    d.timber((3,5,w-4,11))
    d.rect((5,11,w-6,h-6), 'oak_dark', 'contour')
    d.timber((3,10,7,h-3),vertical=True)
    d.timber((w-8,10,w-4,h-3),vertical=True)
    shelves = [h*.47,h-7]
    if h >= 60:shelves.insert(0,h*.30)
    for y in shelves:d.timber((5,y,w-6,y+3))
    if style == 'grain':
        if w >= 40:
            d.sack((9,13,13,max(14,h*.47-14)))
            d.sack((25,15,12,max(12,h*.47-16)),tied=True)
        else:d.sack((7,13,w-13,max(14,h*.47-14)))
        y=h*.47+5
        d.sack((9,y,min(14,w-18),h-y-9),tied=True)
        if w>=40:
            d.timber((27,y+5,39,h-8))
            for xx in range(29,39,3):d.line([(xx,y+6),(xx,h-9)], 'oak_dark')
    elif style == 'workshop':
        y=h*.47
        for x in range(9,w-9,7):
            d.rect((x,y-13,x+2,y-1),'iron','contour')
            d.rect((x-1,y-13,x+4,y-10),'iron_shadow','contour')
        for x in range(9,w-10,10):
            d.jar((x,y+6,7,max(8,h-y-15)), '#8b977f')
        d.line([(10,8),(w-12,8)], 'iron_shadow', 2)
    elif style in ('household_linen','inn_linen'):
        for i,y in enumerate((h*.47-11,h-18)):
            d.cloth((9,y,w-21,8),linen if i==0 else '#c9bea1')
            d.cloth((11,y-3,w-25,4),_shade(linen,14))
    elif style == 'household_crockery':
        y=h*.47
        for x in range(9,w-12,10):d.jar((x,y-13,8,12),'#ab9b80')
        d.cloth((9,h-16,w-21,7),linen)
    else:
        # General household baskets and repair materials establish no trade.
        for x in range(9,w-12,15):
            d.rect((x,h*.47-12,x+12,h*.47-1),'#b58f59','contour')
            for yy in range(round(h*.47-10),round(h*.47),2):
                d.line([(x+1,yy),(x+11,yy)],'oak_shadow')
            for xx in range(x+2,x+12,3):
                d.line([(xx,h*.47-10),(xx,h*.47-2)],'oak_light')
        d.cloth((9,h-17,w-21,9),linen)
        if style=='household_repair':
            d.line([(10,h-12),(w-13,h-12)],'iron',3)
            d.rect((13,h-15,18,h-10),'oak_light','contour')
    return d.image


def _bed_linen(im, color, variant=0):
    """Explicit blanket-only material mask; headboard, pillow and feet persist."""
    out=im.copy().convert('RGBA')
    w,h=out.size
    mask=Image.new('L',out.size)
    md=ImageDraw.Draw(mask)
    # Reviewed blanket body normalized to the shared existing bed drawing.
    md.polygon([(w*.24,h*.42),(w*.76,h*.42),(w*.78,h*.78),(w*.22,h*.78)],fill=255)
    mask=ImageChops.multiply(mask,out.getchannel('A'))
    colored=Image.new('RGBA',out.size)
    cd=ImageDraw.Draw(colored)
    for y in range(h):
        for x in range(w):
            # Preserve value detail of the underlying illustrated folds/weave.
            r,g,b,a=out.getpixel((x,y))
            shade=round((r+g+b)/3-117)
            c=_shade(color,max(-40,min(34,shade)))
            if variant%3==0 and (x//7+y//8)%2:c=_shade(c,-9)
            elif variant%3==1 and y%10<2:c=_shade(c,18)
            elif variant%3==2 and (x%10<2 or y%10<2):c=_shade(c,15)
            cd.point((x,y),fill=c)
    out.paste(colored,(0,0),mask)
    return out


def _stair_art(palette, upstairs=False):
    """An ascending flight or recessed descending well, never a route arrow.

    Both sensors are approached northwards. Direction is communicated by built
    form, not a chevron that can be mistaken for a destination-floor label.
    Existing canvas, support rails, landing and trigger remain exact.
    """
    d=Draft((60,84),palette)
    if upstairs:
        # Open well cut into the upper floor: deep end shadow, visible inner
        # return faces, and treads that lose light as they descend away.
        d.rect((5,0,54,79),'#24221d','contour')
        d.rect((6,2,10,78),'#514331')
        d.rect((49,2,53,78),'#352e24')
        d.line([(10,3),(10,77)],'#766046')
        d.line([(48.5,3),(48.5,77)],'#171a17')
        for index,y in enumerate(range(19,76,9)):
            amount=index*7
            d.rect((11,y,48,y+7),_shade('#4d402f',amount))
            d.line([(11,y+6.5),(48,y+6.5)],_shade('#6e5940',amount))
            d.line([(11,y+7),(48,y+7)],'#24221d')
            d.line([(15,y+3),(28,y+3)],_shade('#574630',amount))
        # Thick far rim establishes a hole instead of a free-standing ladder.
        d.timber((5,0,54,5),dark=True)
    else:
        # Broad tread tops and narrow shadowed risers rise to a bright landing.
        d.rect((5,0,54,81),'oak_dark','contour')
        for index,y in enumerate(range(7,78,9)):
            d.rect((6,y,53,y+5),'oak')
            d.line([(7,y+.5),(52,y+.5)],'oak_light')
            d.line([(10,y+2),(24,y+2)],'oak_shadow')
            d.line([(34,y+3),(47,y+3)],'oak_shadow')
            d.rect((6,y+5.5,53,y+8),'oak_dark')
            d.line([(6,y+5.5),(53,y+5.5)],'oak_edge')
            d.line([(6,y+8),(53,y+8)],'contour')
        d.timber((5,0,54,6))
    # Uprights share the existing exactly named narrow support footprints.
    for x in (0,55):
        d.timber((x+.5,0,x+4,79),dark=True,vertical=True)
        for y in (1,25,49,73):
            d.timber((x,y,x+4.5,y+8),vertical=True)
            d.rect((x+1,y+1,x+3.5,y+2),'oak_edge','contour')
    d.timber((5,79,54,83))
    return d.image


def _gear(d, center, radius, phase, teeth=16):
    cx,cy=center
    points=[]
    for i in range(teeth*4):
        r=radius if i%4 in (1,2) else radius-2
        a=i*math.tau/(teeth*4)+phase
        points.append((cx+math.cos(a)*r,cy+math.sin(a)*r*.72))
    d.poly(points,'oak_shadow')
    d.ellipse((cx-radius+3,cy-(radius-3)*.72,cx+radius-3,cy+(radius-3)*.72),'oak_light')
    spokes=4 if teeth==16 else 6
    for i in range(spokes):
        a=phase+i*math.tau/spokes
        d.line([(cx+math.cos(a)*4,cy+math.sin(a)*3),
                (cx+math.cos(a)*(radius-4),cy+math.sin(a)*(radius-4)*.72)],'oak_dark',3)
    d.ellipse((cx-4,cy-3,cx+4,cy+3),'iron')
    d.ellipse((cx-1,cy-1,cx+1,cy+1),'iron_light')


def _drivetrain(palette, frame):
    d=Draft((126,72),palette)
    # Wheel axle visibly enters a bearing in the east wall, right to left.
    d.rect((113,15,125,37),'stone_shadow','contour')
    d.rect((115,16,125,19),'stone_light','contour')
    d.ellipse((116,21,125,33),'iron_shadow')
    d.rect((57,22,123,27),'oak_dark','contour')
    d.line([(59,23),(122,23)],'oak_light',2)
    for x in (80,112):
        d.rect((x,21,x+5,28),'iron','contour')
        d.rect((x+1,22,x+2,23),'iron_light')
    # Fixed trestles support the shaft; rotating gear teeth never move them.
    for x in (57,104):
        d.poly([(x-5,30),(x-9,49),(x-3,49),(x,34),(x+4,49),(x+10,49),(x+5,30)],'oak_shadow')
        d.timber((x-7,29,x+8,33))
    _gear(d,(56,26),17,frame*math.pi/24)
    _gear(d,(43,39),10,-frame*math.pi/18,12)
    # Vertical spindle and runner stone share a mechanically joined support.
    d.rect((39,39,44,51),'iron_shadow','contour')
    d.line([(40,40),(40,51)],'iron_light',2)
    d.ellipse((8,46,67,69),'stone_shadow')
    d.rect((9,51,66,61),'stone_shadow')
    d.ellipse((8,39,67,62),'stone','contour')
    d.ellipse((12,41,63,59),'stone_light','contour')
    # Fixed bedstone's dressing marks remain fixed, only runner channels turn.
    for i in range(12):
        a=i*math.tau/12
        d.line([(37+math.cos(a)*23,50+math.sin(a)*8),
                (37+math.cos(a)*27,50+math.sin(a)*10)],'stone_shadow')
    d.ellipse((16,39,59,55),'stone','contour')
    for i in range(6):
        a=i*math.tau/6-frame*math.pi/18
        d.line([(37+math.cos(a)*5,47+math.sin(a)*2),
                (37+math.cos(a)*18,47+math.sin(a)*6)],'stone_shadow')
    # Hopper and shoe are supported over the millstone, not a domestic table.
    d.timber((19,10,23,43),vertical=True)
    d.timber((55,10,59,43),vertical=True)
    d.timber((18,9,60,13))
    d.poly([(25,17),(52,17),(46,35),(34,35)],'oak')
    d.poly([(25,17),(30,13),(55,13),(52,17)],'oak_light')
    d.poly([(30,14),(51,14),(49,16),(29,16)],'grain')
    d.line([(35,35),(36,40),(43,40)],'oak_shadow',3)
    d.ellipse((37,44,43,48),'iron_shadow')
    # Meal chute, canvas catch bag and restrained flour remnants.
    d.poly([(9,51),(15,52),(12,61),(6,61)],'oak_shadow')
    d.sack((1,57,15,14),tied=False)
    for x,y in ((22,65),(25,67),(30,66),(20,67)):
        d.rect((x,y,x+1,y+.5),'canvas_light')
    return d.image


def _shop_display(base, palette, armor=False):
    # Retain the illustrated carved frame and its occupied bounds. Reviewed
    # interior content rectangles replace only food/books, never the timber.
    size=(base.width//2,base.height//2)
    d=Draft(size,palette);d.image=base.copy();d.draw=ImageDraw.Draw(d.image)
    if armor:
        d.rect((6,30,43,66),'oak_dark')
        for y in range(32,66,5):
            d.line([(7,y),(42,y)],'#51412e')
        # A sword, cuirass and helmet are decorative stock, with dark outlines,
        # bright edges, leather straps and shaded steel. No equipment grant.
        d.rect((10,33,12,58),'iron_shadow','contour')
        d.poly([(11,30),(12.5,34),(12,52),(10,54),(10,34)],'iron_light')
        d.line([(11,34),(11,51)],'iron')
        d.rect((7,52,15,54),'oak_light','contour')
        d.rect((10,54,12,61),'oak_shadow','contour')
        d.rect((9,60,13,62),'iron','contour')
        d.poly([(25,33),(32,33),(34,36),(39,38),(37,43),(34,41),
                   (35,54),(33,57),(24,57),(22,54),(23,41),(20,43),(18,38),(23,36)],'iron')
        d.poly([(25,34),(28,36),(28,51),(25,53),(24,43)],'iron_light')
        d.poly([(30,36),(32,35),(34,41),(33,53),(30,51)],'#7c8982')
        d.line([(28,36),(30,36),(30,51),(34,54)],'iron_shadow')
        d.line([(22,38),(25,39),(25,48)],'#b7b7a0')
        d.rect((23,53,34,55),'oak_shadow','contour')
        d.rect((27,53,30,55),'oak_light','contour')
        for x in (24,27,31,34):d.rect((x,56,x+.5,56.5),'iron_light')
        # Helm sits on a real lower shelf with a raised dome and dark visor.
        d.ellipse((25,58,36,66),'iron_shadow')
        d.ellipse((26,57,35,63),'iron')
        d.line([(28,58),(27,60),(27,62)],'iron_light')
        d.line([(27,62),(34,62)],'contour',2)
        d.line([(31,59),(31,65)],'iron_light')
    else:
        for row,y in enumerate((22,34,46,58)):
            d.rect((5,y-1,43,y+9),'oak_dark')
            for i,x in enumerate((8,20,32)):
                d.jar((x,y,7,9),('#5d9791','#a66456','#829a61')[(row+i)%3])
    return d.image


def _south_exit(shell, door, palette, room_id):
    """Draw a timber wall cutaway around the unchanged southward trigger."""
    out=shell.copy().convert('RGBA')
    x=round(door['anchor'][0]);y=round(door['entry_y'])
    d=Draft((44,42),palette)
    # Remove the template's small legacy threshold/mat above the actual
    # sensor. Lift that narrow strip from adjacent planks on the same rows
    # so existing floor joints and lighting continue through the approach.
    donor=((x-61)*2,(y-16)*2,(x-35)*2,y*2)
    d.image.alpha_composite(out.crop(donor),(18,0))
    # The sill's inner edge is right on the transfer line (local y=16).
    # Match the 24-unit walkable cut through the wall. The material beyond it
    # is a glimpse of the destination, not a floating plank or a new corridor.
    d.rect((9,19,34.5,41.5),'#24302d')
    if door['id']=='hall':
        # A short view of the hall's transverse oak planks, distinct from
        # the brighter exterior yard materials without rotating the floor.
        d.rect((10,19,33.5,31.5),'#8c7257','contour')
        for yy,xx in ((23,24),(28,17)):
            d.line([(10,yy),(33.5,yy)],'oak_dark')
            d.line([(11,yy+.5),(32,yy+.5)],'oak')
            d.line([(xx,yy+.5),(xx,yy+4.5)],'oak_shadow')
    else:
        from tools.eldenmere_hd_materials import Materials
        if room_id in {'school','inn','item_shop','sanctuary_hall'}:
            landing=Materials().paving((48,25),tuple(map(round,door['spawn'])))
        else:
            # The local yard ribbon is a small section of the town dirt bank.
            mat=Materials()
            landing=mat.dirt[255].crop((0,11,48,36))
        d.image.alpha_composite(landing,(20,39))
        d.line([(10,31.5),(33.5,31.5)],'contour')
    # Return faces attach into the rail at local y=22. Tall uprights or a
    # header would obstruct the cutaway; broad end-grain caps signal the wall.
    for left in (3,34):
        d.timber((left,7,left+6.5,26),dark=True,vertical=True)
        d.rect((left,7,left+6.5,11.5),'oak_light','contour')
        d.line([(left+1,8),(left+5.5,8)],'oak_edge')
        d.line([(left+1.5,9.5),(left+5,9.5)],'oak_shadow')
    d.rect((9.5,16,34,20.5),'stone','contour')
    d.line([(10,16.5),(33.5,16.5)],'stone_light')
    d.line([(10,19.5),(33.5,19.5)],'stone_shadow')
    d.line([(16,17),(16,19)],'stone_shadow')
    d.line([(28,17),(28,19)],'stone_shadow')
    out.alpha_composite(d.image,((x-22)*2,(y-16)*2))
    return out


def _room_architecture(shell, data, policy, palette):
    out=shell.copy().convert('RGBA')
    # Differentiation is authored at the material/work-area level, not broad RGB
    # selection that can repaint panes, roof-like masonry, or quest objects.
    if policy['floor']=='industrial':
        d=Draft(tuple(data['size_pixels']),palette)
        # Native village stone is a dry fire-/vibration-resistant machine pad.
        # The explicit material rectangle owns this color adjustment, never a
        # broad RGB test that could accidentally select architecture or panes.
        from tools.eldenmere_hd_materials import Materials
        paving=Materials().paving((252,146),(280,105)).convert('RGB')
        paving=paving.point(lambda value:round(value*.82)).convert('RGBA')
        d.image.alpha_composite(paving,(560,210))
        d.draw=ImageDraw.Draw(d.image)
        d.line([(280,178),(406,178),(406,105)],'stone_shadow')
        # A substantial upper crossbeam explains the tall processing volume.
        d.timber((24,72,408,78),dark=True)
        for x in (84,252,402):d.timber((x,73,x+5,96),dark=True,vertical=True)
        out.alpha_composite(d.image)
    elif policy['floor'].startswith('woven_'):
        # Flat household runner, never an unblocked tall furniture silhouette.
        color={'woven_blue':'#667f81','woven_ochre':'#9c8454','woven_plum':'#817284'}[policy['floor']]
        d=Draft((62,58),palette)
        d.cloth((3,3,55,50),color,False)
        for y in range(6,53,4):d.line([(5,y),(56,y)],_shade(color,18))
        for x in range(6,56,4):
            d.line([(x,1),(x,3)],'canvas_shadow')
            d.line([(x,53),(x,55)],'canvas_shadow')
        out.alpha_composite(d.image,(58,330))
    # Exit architecture is shared, existing animated northern Serene room doors
    # remain their separately registered controller-driven leaves.
    for door in data['doors']:
        if door['entry_side']=='south' and not door['frames']:
            out=_south_exit(out,door,palette,data['id'])
    return out


def _new_entity(identifier, position, size, frames, **extra):
    return {'id':identifier,'position':list(position),'logical_size':list(size),
            'sort_y':position[1]+size[1],'sort_priority':0,'frames':frames,
            'frame_duration_ms':600,'phase_offset':0,
            'artwork_pixels_per_world_pixel':2,'reduced_motion_frame':0,**extra}


def _replace_fixture(data, entity, im, export):
    previous=list(entity['frames'])
    path=export.png(f"{PREFIX}/{data['id']}/{entity['id']}",im)
    size=entity.get('logical_size') or [im.width//2,im.height//2]
    entity.update(frames=[path],logical_size=list(size),
                  artwork_pixels_per_world_pixel=2,reduced_motion_frame=0)
    # Update existing alias targets, not their keys/ownership. Stateful fixtures
    # (lantern shelf, toys, bowls and deposited quest props) never call this.
    replacements=data.setdefault('art_replacements',{})
    for old in previous:replacements[old]=export.art(path,size)
    for key,record in list(replacements.items()):
        if isinstance(record,dict) and record.get('file') in previous:
            replacements[key]=export.art(path,size)


def _add_collision(data, export, additions, base_path=None):
    if not additions:return
    collision=export.load(base_path or data['collision']).convert('L')
    before=collision.copy();d=ImageDraw.Draw(collision)
    for item in additions:
        x,y,w,h=item['rect']
        d.rectangle((x,y,x+w-1,y+h-1),fill=255)
    data['collision']=export.png(f"{PREFIX}/{data['id']}/collision",collision)
    data['architecture_occupancy']=deepcopy(additions)
    # Explicit delta for review and exact geometry regression, never broad masks.
    delta=ImageChops.difference(before,collision)
    data['architecture_collision_delta']=export.png(f"{PREFIX}/{data['id']}/collision_delta",delta)
    if hasattr(export,'records'):
        export.records[data['architecture_collision_delta']]['pixel_space']='logical_geometry'


def _guest_floor(inn, spec, palette, export, furnishing):
    """Exactly one new ordinary interior, registered through the town registry."""
    from tools.build_sanctuary_home_hd import architecture
    data=deepcopy(inn)
    data.update(id='inn_guest_floor',name='Eldenmere Inn · Guest Floor',
                spawn=[366,300],npcs=[],quests=[],destinations={},entities=[],
                doors=[],interaction_cues=[],ground_overlays=[],foreground=[],
                art_replacements={},size_pixels=list(spec['size']),size_tiles=[18,14])
    for field in ('rest_profile','architecture_occupancy','architecture_collision_delta'):
        data.pop(field,None)
    shell=architecture(data,{'windows':spec['windows'],'entry_rect':[-64,-64,20,12]},'hall')
    # There is no exterior exit upstairs. Repair the empty template entry and
    # author only the east stairwell/corridor; no mysterious threshold downstairs.
    for i,(x,y) in enumerate(spec['beds']):
        bed=_bed_linen(furnishing('bed',(48,72)),('#82998f','#8d92a1','#a18d6e','#90829c')[i],i)
        path=export.png(f'{PREFIX}/inn_guest_floor/guest_bed_{i+1}',bed)
        data['entities'].append(_new_entity(f'guest_bed_{i+1}',(x,y),(48,72),[path]))
        chest=furnishing('chest',(24,24))
        path=export.png(f'{PREFIX}/inn_guest_floor/guest_chest_{i+1}',chest)
        data['entities'].append(_new_entity(f'guest_chest_{i+1}',(x+53,142),(24,24),[path]))
        side=furnishing('bedside_table',(20,24))
        path=export.png(f'{PREFIX}/inn_guest_floor/bedside_{i+1}',side)
        data['entities'].append(_new_entity(f'bedside_{i+1}',(x+52,94),(20,24),[path]))
    for i,x in enumerate(spec['screens_x']):
        d=Draft((6,136),palette)
        d.timber((.5,0,5,132),dark=True,vertical=True)
        for y in (0,28,60,94,126):d.rect((0,y,5,y+3),'oak_light','contour')
        path=export.png(f'{PREFIX}/inn_guest_floor/screen_{i+1}',d.image)
        data['entities'].append(_new_entity(f'guest_screen_{i+1}',(x,66),(6,136),[path]))
    # Shared flue continues through the east wall without another upstairs fire.
    d=Draft((12,52),palette)
    d.rect((2,0,11,51),'stone','contour')
    for y in range(0,50,7):
        d.line([(2,y),(11,y)],'stone_shadow')
        d.line([(6 if y%2 else 8,y),(6 if y%2 else 8,y+7)],'stone_shadow')
    path=export.png(f'{PREFIX}/inn_guest_floor/flue',d.image)
    data['entities'].append(_new_entity('inn_flue',(396,24),(12,52),[path]))
    collision=Image.new('L',tuple(spec['size']),255);cd=ImageDraw.Draw(collision)
    cd.rectangle((24,72,407,311),fill=0)
    for e in data['entities']:
        if e['id'].startswith(('guest_bed_','guest_chest_','bedside_')):
            x,y=e['position'];w,h=e['logical_size']
            cd.rectangle((x+3,y+h//2,x+w-4,y+h-1),fill=255)
    data['collision']=export.png(f'{PREFIX}/inn_guest_floor/collision_base',collision)
    if hasattr(export,'records'):
        export.records[data['collision']]['pixel_space']='logical_geometry'
    data['ground_frames']=[export.png(f'{PREFIX}/inn_guest_floor/ground',shell.convert('RGB'))]
    data['interior_architecture']={'recipe':RECIPE_PATH.relative_to(ROOT).as_posix(),
        'purpose':'Four ordinary guest sleeping bays and a shared corridor/stair landing',
        'geometry':'New upper floor only; no exterior exit, service, recovery or quest owner'}
    return data



def _lantern_workshop_surfaces(town, export, palette):
    """Retain canonical phase drawings and the one workshop/frame owner.

    The old town composer incorrectly assigned generic paper stock to *every*
    craft_surface phase. These explicit aliases win over that generic mapping.
    Canonical small quest drawings are retained compatibility art at declared
    density, not passed off as newly redrawn HD character/prop animation.
    """
    art=json.loads((ROOT/'assets/story/lantern/art.json').read_text())
    rest=json.loads((ROOT/'assets/story/lantern/rest_art.json').read_text())
    surface=next(p for p in art['props'] if p['id']=='craft_surface')
    aliases=town.setdefault('art_replacements',{})
    # Source-authored full-width trestle agrees with the existing 60x6 footprint.
    # The prior generated donor had shrunk the physical table to 29 world units.
    d=Draft((64,28),palette)
    for x in (7,53):
        d.timber((x,14,x+4,27),dark=True,vertical=True)
    d.timber((10,22,55,25),dark=True)
    d.timber((0,6,63,13))
    d.timber((0,13,63,16),dark=True)
    for x,y in ((14,8),(38,10),(51,7)):
        d.line([(x,y),(x+5,y),(x+6,y+.5)],'oak_light')
        d.line([(x+1,y+.5),(x+3,y+.5)],'oak_dark')
    table_path=export.png(f'{PREFIX}/lantern_workshop/table',d.image)
    table=next(p for p in art['props'] if p['id']=='craft_table')
    for legacy in table['states'].values():aliases[legacy]=export.art(table_path,(64,28))
    # Upstream #250 intentionally clears only the transferred contents. The
    # real, separately owned craft_table remains visible at its original station.
    # Do not duplicate that table in the empty content layer or override its
    # canonical zero-alpha surface/identity used during checkpoint restoration.
    aliases.pop(rest['workshop_collected'],None)
    for state,legacy in surface['states'].items():
        with Image.open(ROOT/legacy) as old:
            phase=old.convert('RGBA').resize((128,112),Image.Resampling.NEAREST)
        path=export.png(f'{PREFIX}/lantern_workshop/{state}',phase)
        aliases[legacy]=export.art(path,(64,56))
    return {'table_position':table['position'],'surface_position':surface['position'],
            'states':list(surface['states']),'collected':rest['workshop_collected'],
            'source_density':1,'export_density':2,
            'phase_art':'Retained canonical frame/material/action drawings, uniform compatibility sampling; no generic papers substitution.',
            'ownership':'Existing table and craft_surface only; canonical zero-alpha contents after pickup, real table/support stays visible, carrier/home objects retain their sources.'}

def apply_interior_architecture(maps, paths, export, furnishing):
    """Apply the PR4 recipe to builder-owned dictionaries and export collector.

    ``export`` supplies png(name, PIL image), load(path), art(path, logical_size)
    and json(path, object). ``furnishing(name, size)`` returns retained native 2×
    furniture. Return a machine-readable review record, also exported to JSON.
    Re-running produces identical bytes; input quest/actor/service state is not
    consulted or modified. Existing generated records are replaced by ID.
    """
    rec=recipe();palette=rec['palette'];town=maps['town']
    for name,policy in rec['rooms'].items():
        if name not in maps:
            paths[name]=town['interior_scenes'][name]
            maps[name]=json.loads((ROOT/paths[name]).read_text())
        data=maps[name]
        if policy.get('base_ground'):
            # Curated household shell is independently source-built, not our own
            # previous generated output. This keeps repeated town builds stable.
            shell=Image.open(ROOT/policy['base_ground']).convert('RGBA')
        else:shell=export.load(data['ground_frames'][0]).convert('RGBA')
        shell=_room_architecture(shell,data,policy,palette)
        data['ground_frames']=[export.png(f'{PREFIX}/{name}/ground',shell.convert('RGB'))]
        data['artwork_pixels_per_world_pixel']=2
        data['pause_on_focus_loss']=True
        for index,e in enumerate(data['entities']):
            identifier=e['id']
            if policy['storage']=='retained':continue
            im=export.load(e['frames'][0]).convert('RGBA')
            size=e.get('logical_size') or [im.width//2,im.height//2]
            if identifier in ('bed','parents_bed','liam_bed','guest_bed','guest_bed_east') or identifier.endswith('_bed'):
                _replace_fixture(data,e,_bed_linen(im,policy['linen'],index),export)
            elif identifier in ('cupboard','pantry','shelf','storage','storage_b'):
                _replace_fixture(data,e,_storage(size,policy['storage'],palette,policy['linen']),export)
            elif name=='item_shop' and identifier in ('stock_shelf','bookcase'):
                _replace_fixture(data,e,_shop_display(im,palette,identifier=='bookcase'),export)
        # Existing school work, map, chair and lesson artwork is already specific.
        # Review its faces; do not paint another front window over the board.
        data['interior_architecture']={'recipe':RECIPE_PATH.relative_to(ROOT).as_posix(),
            'purpose':policy['purpose'],'geometry':'retained except named architecture_occupancy',
            'south_exits':'open cutaway with jambs and real threshold, no unsynchronized leaf'}
        _add_collision(data,export,rec['collision_additions'].get(name,[]),
                       rec.get('collision_base_paths',{}).get(name))
    mill=maps['mill'];spec=rec['mill_processing']
    frames=[export.png(f'{PREFIX}/mill/drivetrain_{i:02}',_drivetrain(palette,i)) for i in range(spec['frames'])]
    mill['entities']=[e for e in mill['entities'] if e['id']!=spec['entity']]
    mill['entities'].append(_new_entity(spec['entity'],spec['position'],spec['logical_size'],frames,
        sort_y=spec['depth_baseline'],frame_duration_ms=spec['frame_duration_ms'],
        animation_driver=spec['animation_driver']))
    inn=maps['inn'];upper=rec['guest_floor'];stairs=rec['stairs']
    # Retained right/rear exterior flue is explained by a real common-room fire.
    if not any(e['id']=='inn.hearth' for e in inn['entities']):
        hearth=furnishing('hearth',(48,72))
        path=export.png(f'{PREFIX}/inn/hearth',hearth)
        inn['entities'].append(_new_entity('inn.hearth',(350,24),(48,72),[path],sort_y=96))
    paths[upper['id']]=upper['map'];town['interior_scenes'][upper['id']]=upper['map']
    maps[upper['id']]=_guest_floor(inn,upper,palette,export,furnishing)
    _add_collision(maps[upper['id']],export,rec['collision_additions'][upper['id']])
    for name,opposite,identifier,arrival in (
            ('inn','inn_guest_floor','guest_stairs','common_stairs'),
            ('inn_guest_floor','inn','common_stairs','guest_stairs')):
        data=maps[name]
        data['doors']=[d for d in data['doors'] if d['id']!=identifier]
        data['doors'].append({'id':identifier,'host':None,'anchor':stairs['trigger_anchor'],
            'entry_y':stairs['trigger_anchor'][1],'entry_side':stairs['entry_side'],
            'entry_half_width':stairs['entry_half_width'],'open_radius':30,'close_radius':38,
            'frame_duration_ms':100,'frames':[],'position':stairs['footprint'][:2],
            'requires_open':False,'destination':paths[opposite],'spawn':stairs['spawn'],
            'arrival_facing':stairs['arrival_facing'],'arrival_door':arrival,
            'rearm_after_exit':stairs['rearm_after_exit']})
        art=_stair_art(palette,name=='inn_guest_floor')
        path=export.png(f'{PREFIX}/{name}/stairs',art)
        data['entities']=[e for e in data['entities'] if e['id']!='inn.stairs']
        data['entities'].append(_new_entity('inn.stairs',stairs['footprint'][:2],stairs['footprint'][2:],[path]))
    lantern_review=_lantern_workshop_surfaces(town,export,palette)
    review={'id':rec['id'],'version':rec['version'],
        'recipe':RECIPE_PATH.relative_to(ROOT).as_posix(),
        'recipe_sha256':sha256(RECIPE_PATH.read_bytes()).hexdigest(),
        'rooms':{n:paths[n] for n in (*rec['rooms'],upper['id'])},
        'existing_room_count':len(rec['rooms']),'new_scenes':[upper['id']],
        'mill_processing':spec,'stairs':stairs,'guest_floor':upper,
        'collision_additions':rec['collision_additions'],'lantern_workshop_continuity':lantern_review,
        'protected':'Original fixture IDs/positions, existing portals, actors, state images, story ownership, services and inventory are unchanged.'}
    export.json('assets/maps/eldenmere/town_hd/interior_architecture.json',review)
    return review
