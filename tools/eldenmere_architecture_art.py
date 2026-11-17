"""Native 2x architecture drawings for the Eldenmere projection audit.

This authoring module draws roofs, structural framing and facade geometry around
explicit ground rectangles. It never fits a facade by slicing around a portal.
Retained native-HD *details* (bell, signs and fixed shop goods) are isolated props,
not resized building masters. Gameplay registration remains owned by map recipes.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import random

from PIL import Image, ImageChops, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'assets/source/terrain/eldenmere/exteriors_hd/architecture_audit'
BUSINESS_SOURCE = ROOT / 'assets/source/terrain/eldenmere/business_exteriors_hd/architecture_audit'
DENSITY = 2
INK = '#171e1a'
WOOD = ('#654e3c', '#836347', '#a08158', '#b79a6c')
STONE = ('#736e60', '#827d6e', '#969284', '#aaa492', '#b5ae9c', '#c3bcaa')
PLASTER = ('#aa9d80', '#d3c6a4', '#e1d6bc')
GLASS = ('#34464b', '#53696e', '#8ab3b0')
LEAVES = ('#173f31', '#205b3b', '#2c7c50', '#42975f', '#67b982')
ROOFS = {
    'slate': ('#4e5e64', '#657579', '#87948f', '#a2aaa0'),
    'terracotta': ('#704e47', '#946555', '#b3856a', '#c6a187'),
    'moss': ('#4e5a46', '#6c7b58', '#8f9a75', '#adb693'),
    'heather': ('#57515f', '#787083', '#99909f', '#b7adb9'),
}
# These are live consumers, not new occupations inferred from source names.
DESIGN_IDS = {
    'standard_gardener': 'halden', 'compact_gardener': 'elira',
    'wide_weathered': 'venn', 'standard_craft': 'home_a',
    'standard_heather': 'home_b', 'standard_weathered': 'home_c',
    'wide_craft': 'liam_house', 'inn_maintained': 'inn',
    'item_shop_maintained': 'item_shop',
}
IDENTITIES = {
    'halden': 'Maintained cottage; broad stone sill, paired shutters and a small dry grain-storage hatch. No new work identity.',
    'elira': 'Compact cared-for household; single mulberry curtain, sheltered wall lantern and a modest remembrance flower pot. No new biography.',
    'venn': 'Wide family cottage; repaired lower render, louvred storage bay and restrained damp-side roof wear. Quest gate and child remain unchanged.',
    'home_a': 'Domestic house with a narrow left lean-to storage locker and long ridge repair flashing; no Liam roof patch/firewood duplicate.',
    'home_b': 'Heather roof household; small over-door cross gable, paired narrow windows, scalloped lintel and low linen chest.',
    'home_c': 'Moss-roof household; broad shutter pair, sheltered rain jar and clustered low planting, without Venn facade weathering.',
    'liam_house': 'Family home; offset timber roof repair, open log cradle and three unequal window bays. Toys and Daisy remain owned indoors.',
    'mira': 'Working workshop; broad double doorway, exposed bracing, tool rack, cog sign and retained right-rear hearth flue.',
    'mill': 'Working grain mill; tall open processing bay with loading doors and pulley beam, low left receiving annex, stone axle seat and right-rear hearth flue.',
    'school': 'Wide maintained classroom; paired glazed classroom bays, central book gable and bell, walls terminate within the declared footprint; right-rear hearth flue.',
    'sanctuary': 'Serene, Caelan and Tomas household; long cared-for domestic roof, retained bell mount, arched household panes, herb frontage and right-side dining flue. Not the regional Sanctuary.',
    'inn': 'Two occupied storeys: common/reception downstairs and four front guest window bays upstairs, with east-side internal stair circulation reserved separately.',
    'item_shop': 'Fixed potion, sword/shield and helmet/breastplate merchandise; sheltered blue-green awning and a distinct delivery hatch. No flue and no stock animation.',
}


@lru_cache(maxsize=1)
def records():
    result = {}
    for family in ('exteriors_hd', 'business_exteriors_hd'):
        recipe = json.loads((ROOT / f'assets/source/terrain/eldenmere/{family}/recipe.json').read_text())
        for r in recipe['designs']:
            name = DESIGN_IDS.get(r['id'], r['id'])
            if name in IDENTITIES:
                result[name] = r
    return result


@lru_cache(maxsize=4)
def _shingle_details(palette):
    """Uniformly sampled isolated material, never a house/facade transformation."""
    source=ROOT/'assets/source/terrain/eldenmere/exteriors_hd/cottages_authored.png'
    with Image.open(source) as image:master=image.convert('RGBA')
    boxes=((127,433,151,449),(154,434,178,450),(183,434,207,450),
           (211,434,235,450),(113,452,137,468),(142,452,166,468),
           (173,452,197,468),(202,452,226,468),(233,452,257,468))
    ramp=ROOFS[palette]
    colors=[tuple(int(c[i:i+2],16) for i in (1,3,5))+(255,) for c in ramp]
    result=[]
    for box in boxes:
        tile=master.crop(box).resize((21,14),Image.Resampling.NEAREST)
        out=Image.new('RGBA',tile.size)
        for yy in range(tile.height):
            for xx in range(tile.width):
                r,g,b,a=tile.getpixel((xx,yy));value=(r*2+g*3+b)/6
                # Preserve deliberate cuts, chips and broad planes; map only
                # the material's value ramp into the region's existing colors.
                idx=0 if value<65 else 1 if value<99 else 2 if value<146 else 3
                out.putpixel((xx,yy),colors[idx])
        result.append(out)
    return tuple(result)


@dataclass
class Architecture:
    """Separated immutable-by-convention authored layers and logical contracts."""
    structure: Image.Image
    pane_mask: Image.Image
    material_masks: dict[str, Image.Image]
    metadata: dict

    def ambient(self, phase=0, reduced_motion=False):
        """Window light/smoke never mutate the underlying architecture."""
        result = self.structure.copy()
        if reduced_motion:
            return result
        light = Image.new('RGBA', result.size, '#e4b66b')
        light.putalpha(self.pane_mask)
        result.alpha_composite(light)
        emitter = self.metadata.get('smoke_emitter_logical')
        if emitter:
            smoke = Image.new('RGBA', result.size)
            draw = ImageDraw.Draw(smoke)
            ex, ey = [round(v * 2) for v in emitter]
            for offset in (0, 6, 12):
                age = (phase + offset) % 18
                if age < 16:
                    x, y = ex + age // 4, ey - age * 2
                    draw.ellipse((x - 3, y - 8, x + 3, y), fill=('#c5ccc1' if age < 9 else '#dce0d2'))
            result.alpha_composite(smoke)
        return result


class Drawing:
    def __init__(self, name, size):
        self.name = name
        self.image = Image.new('RGBA', tuple(v * 2 for v in size))
        self.draw = ImageDraw.Draw(self.image)
        self.masks = {n: Image.new('L', self.image.size) for n in ('roof', 'masonry', 'timber', 'plaster', 'glass', 'merchandise')}
        self.panes = []
        self.roof_bounds = []
        self.rng = random.Random(name)

    @staticmethod
    def coords(rect):
        x, y, w, h = rect
        return round(x*2), round(y*2), round((x+w)*2)-1, round((y+h)*2)-1

    def ownership(self, mask, material):
        for name,existing in self.masks.items():
            if name==material:self.masks[name]=ImageChops.lighter(existing,mask)
            else:existing.paste(0,(0,0),mask)

    def rect(self, rect, fill, material=None, outline=None, width=1):
        box = self.coords(rect)
        if fill is not None or outline is not None:
            self.draw.rectangle(box, fill=fill, outline=outline, width=width)
        if material:
            ownership=Image.new('L',self.image.size);ImageDraw.Draw(ownership).rectangle(box,fill=255)
            self.ownership(ownership,material)

    def line(self, points, fill, width=1, material=None):
        pts = [(round(x*2), round(y*2)) for x, y in points]
        self.draw.line(pts, fill=fill, width=width)
        if material:
            ownership=Image.new('L',self.image.size);ImageDraw.Draw(ownership).line(pts,fill=255,width=width)
            self.ownership(ownership,material)

    def polygon(self, points, fill, material=None, outline=INK):
        pts = [(round(x*2), round(y*2)) for x, y in points]
        self.draw.polygon(pts, fill=fill, outline=outline)
        if material:
            ownership=Image.new('L',self.image.size);ImageDraw.Draw(ownership).polygon(pts,fill=255)
            self.ownership(ownership,material)

    def plaster(self, rect, weather=0):
        self.rect(rect, PLASTER[1], 'plaster', INK)
        x, y, w, h = rect
        # Small joined clusters, not per-pixel noise or checkerboards.
        for _ in range(round(w*h/23)):
            xx = x+1+self.rng.random()*(w-3); yy=y+1+self.rng.random()*(h-3)
            self.line(((xx,yy),(xx+1.5,yy),(xx+2,yy+.5)), self.rng.choice(PLASTER), 1)
            if self.rng.random()<.3:self.line(((xx+.5,yy+.5),(xx+2,yy+.5)),PLASTER[2],1)
        # Eave shadow and small exposed edges model thickness around framing.
        self.rect((x+.5,y+.5,w-1,2),PLASTER[0],'plaster')
        for xx in (x+4,x+w-12):
            if w>20:
                self.polygon(((xx,y+h-6),(xx+3,y+h-9),(xx+6,y+h-7),(xx+8,y+h-5)),STONE[2],'masonry',outline=PLASTER[0])
                self.line(((xx+1,y+h-6),(xx+6,y+h-6)),STONE[4])
        for k in range(weather):
            xx=x+3+(k*19) % max(4, int(w-7)); yy=y+h-5-(k*3)%10
            self.polygon(((xx,yy),(xx+5,yy-1),(xx+7,yy+2),(xx+5,yy+4),(xx,yy+3)),PLASTER[0],outline=PLASTER[0])

    def beam(self, rect, brace=False):
        self.rect(rect, WOOD[0], 'timber', INK)
        x,y,w,h=rect
        if h > w:
            self.line(((x+1,y+1),(x+1,y+h-1)),WOOD[2])
            self.line(((x+w-.5,y+1),(x+w-.5,y+h-1)),WOOD[0])
            for yy in range(round(y+4),round(y+h-2),9):
                self.line(((x+2,yy),(x+2,yy+4)),WOOD[1])
        else:
            self.line(((x+1,y+.5),(x+w-1,y+.5)),WOOD[2])
            self.line(((x+1,y+h-.5),(x+w-1,y+h-.5)),WOOD[0])
            for xx in range(round(x+4),round(x+w-2),12):
                self.line(((xx,y+1.5),(xx+5,y+1.5)),WOOD[1])

    def brace(self,x,y,dx,dy):
        self.line(((x,y),(x+dx,y+dy)),INK,6,'timber')
        self.line(((x,y),(x+dx,y+dy)),WOOD[1],4,'timber')
        self.line(((x-.5,y),(x+dx-.5,y+dy)),WOOD[2],1)

    def stonework(self, rect):
        self.rect(rect,STONE[0],'masonry',INK)
        x,y,w,h=rect
        for row,yy in enumerate(range(round(y*2)+1,round((y+h)*2)-1,9)):
            xx=round(x*2)+1-(7 if row%2 else 0)
            while xx<round((x+w)*2)-1:
                ww=self.rng.choice((13,16,19))
                left=max(round(x*2)+1,xx);right=min(round((x+w)*2)-2,xx+ww-2)
                if right>left:
                    top=yy;bottom=min(round((y+h)*2)-2,yy+7)
                    self.draw.rectangle((left,top,right,bottom),fill=self.rng.choice(STONE[1:4]))
                    self.draw.line((left+1,top,right-1,top),fill=STONE[4])
                    self.draw.point((right,bottom),fill=STONE[1])
                    if self.rng.random()<.3:self.draw.line((right-3,top+2,right-2,bottom-1),fill=STONE[1])
                    self.draw.line((left+1,bottom,right-1,bottom),fill=STONE[1])
                xx+=ww

    def roof(self, rect, palette='slate', hip=5, wear=False, ridge=True):
        """Parallel eaves and ridge; diagonal hips are roof construction, not convergence."""
        x,y,w,h=rect; ramp=ROOFS[palette]
        points=((x,y),(x+w,y),(x+w,y+h),(x,y+h))
        mask=Image.new('L',self.image.size); md=ImageDraw.Draw(mask)
        pts=[(round(a*2),round(b*2)) for a,b in points];md.polygon(pts,fill=255)
        layer=Image.new('RGBA',self.image.size);ld=ImageDraw.Draw(layer)
        ld.polygon(pts,fill=ramp[0],outline=INK)
        # A short far slope and long near slope explain roof depth. Tile
        # dimensions stay fixed, with per-course joints and native chipping.
        ridge_y=round((y+h*.24)*2)
        roof_seed=random.Random(self.name+str(rect))
        tiles=_shingle_details(palette)
        for row,yy in enumerate(range(round(y*2)+1,round((y+h)*2),13)):
            xx=round(x*2)-((row%2)*7)
            while xx<round((x+w)*2):
                tile=tiles[roof_seed.randrange(len(tiles))].copy()
                if yy<ridge_y:
                    # Far slope is a separate physical surface, kept quiet.
                    colors=[tuple(int(c[i:i+2],16) for i in (1,3,5))+(255,) for c in ramp]
                    dim={color:colors[max(0,index-1)] for index,color in enumerate(colors)}
                    tile.putdata([dim.get(pixel,pixel) for pixel in tile.get_flattened_data()])
                layer.alpha_composite(tile,(xx,yy))
                xx+=20
        layer.putalpha(mask);self.image.alpha_composite(layer)
        self.ownership(mask,'roof')
        self.draw=ImageDraw.Draw(self.image)
        if hip:
            ry=y+h*.24
            # True hipped end planes have diagonal construction edges inside
            # rectangular orthographic eaves, not converging distant walls.
            self.line(((x,y),(x+hip,ry),(x,y+h)),ramp[0],2,'roof')
            self.line(((x+w,y),(x+w-hip,ry),(x+w,y+h)),ramp[0],2,'roof')
            self.line(((x+.5,y),(x+hip+.5,ry),(x+.5,y+h)),ramp[2],1)
        self.line(points+(points[0],),INK,1)
        self.line(((x,y+h),(x+w,y+h)),INK,3,'roof')
        self.line(((x+1,y+h-1),(x+w-1,y+h-1)),ramp[3],1)
        # Thin eave fascia and rafter ends have native grain, rather than a flat
        # black ruler under a featureless rectangle.
        self.rect((x+.5,y+h+.5,w-1,1.5),WOOD[0],'timber',INK)
        self.line(((x+1,y+h+.5),(x+w-1,y+h+.5)),WOOD[2])
        for xx in range(round(x+4),round(x+w-2),9):
            self.rect((xx,y+h+1,1.5,2),WOOD[2],'timber',INK)
        if ridge:
            ry=y+h*.24
            self.rect((x+hip+1,ry-1.5,w-(hip+1)*2,3),ramp[0],'roof',INK)
            for xx in range(round(x+hip+1),round(x+w-hip-1),7):
                self.rect((xx+.5,ry-1,5.5,2),ramp[2],'roof')
                self.line(((xx+1,ry-.5),(xx+5,ry-.5)),ramp[3])
        if wear:
            for k in range(7):
                xx=x+6+(k*13)%max(8,int(w-14));yy=y+3+(k*7)%max(5,int(h-8))
                self.line(((xx,yy),(xx+2,yy),(xx+3,yy+1)),LEAVES[1],2)
        self.roof_bounds.append(list(rect))

    def window(self, rect, shutters='both', arch=False, curtains=None, lit=False):
        x,y,w,h=rect
        self.rect((x-1,y-1,w+2,h+3),WOOD[0],'timber',INK)
        self.rect(rect,WOOD[2],'timber',INK)
        self.line(((x+.5,y+.5),(x+w-1,y+.5)),WOOD[3])
        # Four individually declared glass panes exclude frames and mullions.
        border=2; gx=x+border; gy=y+border; gw=w-border*2; gh=h-border*2
        for row in range(2):
            for col in range(2):
                pane=(gx+col*(gw/2+.25), gy+row*(gh/2+.25),gw/2-.75,gh/2-.75)
                if pane[2]<=0 or pane[3]<=0:continue
                self.rect(pane,GLASS[0],'glass')
                px,py,pw,ph=pane
                self.line(((px+.5,py+ph-1),(px+pw-1,py+1)),GLASS[1])
                self.line(((px+1,py+ph-1),(px+pw-1,py+1)),GLASS[2])
                self.panes.append({'rect_logical':list(pane),'role':'front glass','lighting':True})
        if curtains:
            self.polygon(((gx,gy),(gx+2.5,gy),(gx+1,gy+gh-2),(gx,gy+gh)),curtains,outline=curtains)
            self.polygon(((gx+gw-2,gy),(gx+gw,gy),(gx+gw,gy+gh),(gx+gw-1,gy+gh-2)),curtains,outline=curtains)
        self.rect((x-1,y+h,w+2,2),WOOD[2],'timber',INK)
        self.line(((x,y+h+.5),(x+w,y+h+.5)),WOOD[3])
        for nx in (x+.5,x+w-1):
            for ny in (y+1,y+h-1):self.draw.point((round(nx*2),round(ny*2)),fill=STONE[4])
        for side in ('left','right'):
            if shutters not in ('both',side):continue
            sx=x-5 if side=='left' else x+w+1
            self.rect((sx,y+1,4,h-1),WOOD[1],'timber',INK)
            for sy in range(round(y+3),round(y+h-1),3):self.line(((sx+.5,sy),(sx+3.5,sy)),WOOD[0])
            self.line(((sx+1,y+2),(sx+1,y+h-2)),WOOD[2])
        if arch:
            self.polygon(((x-1,y),(x+w/2,y-6),(x+w+1,y),(x+w-1,y),(x+w/2,y-3),(x+1,y)),STONE[3],'masonry')

    def planter(self,x,y,w=17,flowers='#bd7898'):
        self.rect((x,y+5,w,5),WOOD[1],'timber',INK)
        self.line(((x,y+5),(x+w,y+5)),WOOD[3])
        for k in range(round(w/2)):
            xx=x+1+k*2;yy=y+2-(k%3)
            self.line(((xx,y+5),(xx,yy)),LEAVES[1],2)
            self.rect((xx-.5,yy,1.5,1),LEAVES[3])
            self.rect((xx+.5,yy-1,1,1),flowers)

    def chimney(self,x,y,height=21):
        self.stonework((x-4,y,8,height))
        # Alternating quoins wrap the shaft; top-facing cap has visible depth.
        for yy in range(round(y+3),round(y+height-2),7):
            self.rect((x-4,yy,8,2),STONE[1],'masonry',INK)
            self.line(((x-3.5,yy+.5),(x+3.5,yy+.5)),STONE[4])
        self.rect((x-5,y-2,10,4),STONE[3],'masonry',INK)
        self.rect((x-3.5,y-1,7,2),INK)
        self.line(((x-4.5,y+1.5),(x+4.5,y+1.5)),STONE[5])
        self.line(((x-4,y+height),(x+4,y+height)),WOOD[0],2)
        return [x,y-.5]

    def canopy(self,rect,palette='slate'):
        x,y,w,h=rect; ramp=ROOFS[palette]
        points=((x,y+h),(x+w/2-1,y),(x+w/2+1,y),(x+w,y+h))
        shape=Image.new('L',self.image.size)
        ImageDraw.Draw(shape).polygon([(round(xx*2),round(yy*2)) for xx,yy in points],fill=255)
        layer=Image.new('RGBA',self.image.size,ramp[0]);ld=ImageDraw.Draw(layer)
        tiles=_shingle_details(palette)
        for row,yy in enumerate(range(round(y*2),round((y+h)*2),10)):
            for col,xx in enumerate(range(round(x*2)-(row%2)*7,round((x+w)*2),20)):
                layer.alpha_composite(tiles[(row+col)%len(tiles)],(xx,yy))
        layer.putalpha(shape);self.image.alpha_composite(layer);self.draw=ImageDraw.Draw(self.image)
        self.ownership(shape,'roof')
        self.line(points+(points[0],),INK,1)
        self.line(((x,y+h),(x+w,y+h)),WOOD[2],2,'timber')
        self.roof_bounds.append(list(rect))

    def portal(self,rect):
        x,y,w,h=rect
        self.beam((x-2,y-3,w+4,3))
        self.beam((x-2,y,2,h))
        self.beam((x+w,y,2,h))
        # This hole is independent of facade construction and never used to fit it.
        bx,by,br,bb=self.coords(rect)
        self.image.paste((0,0,0,0),(bx,by,br+1,bb+1))
        for mask in self.masks.values():ImageDraw.Draw(mask).rectangle(self.coords(rect),fill=0)

    def detail(self,path,position,limit=None):
        with Image.open(ROOT/path) as image:im=image.convert('RGBA')
        if limit:im.thumbnail(tuple(round(v*2) for v in limit),Image.Resampling.NEAREST)
        self.image.alpha_composite(im,tuple(round(v*2) for v in position))
        self.draw=ImageDraw.Draw(self.image)

    def finish(self):
        # Pane ownership is explicit at creation; structural/cloth pixels drawn
        # later erase panes rather than accidentally receiving emissive light.
        mask=Image.new('L',self.image.size)
        md=ImageDraw.Draw(mask)
        for p in self.panes:md.rectangle(self.coords(p['rect_logical']),fill=255)
        glass_colors={tuple(int(c[i:i+2],16) for i in (1,3,5)) for c in GLASS}
        pixels=self.image.load();mp=mask.load()
        for yy in range(self.image.height):
            for xx in range(self.image.width):
                if mp[xx,yy] and (pixels[xx,yy][:3] not in glass_colors or not pixels[xx,yy][3]):mp[xx,yy]=0
        # Material masks describe visible ownership, not hidden layers.
        for name,material in self.masks.items():
            if name!='glass':
                material.paste(0,(0,0),mask)
        self.masks['glass']=mask.copy()
        alpha=self.image.getchannel('A')
        self.masks={name:ImageChops.multiply(material,alpha) for name,material in self.masks.items()}
        return mask


def _facade(d,ground,top,weather=0,posts=()):
    x,y,w,h=ground;foot=y+h
    d.plaster((x,top,w,foot-top),weather)
    d.stonework((x,foot-8,w,8))
    d.beam((x,top,3,foot-top-7));d.beam((x+w-3,top,3,foot-top-7))
    d.beam((x,top,w,3));d.beam((x,foot-10,w,2))
    for xx in posts:d.beam((xx,top,2.5,foot-top-9))
    return foot


def _threshold(d,door,foot):
    x,y,w,h=door;bottom=y+h
    d.stonework((x-3,bottom,w+6,max(2,foot-bottom)))
    d.line(((x-3,bottom+.5),(x+w+3,bottom+.5)),STONE[5])


def _cottage(d,name,r):
    x,y,w,h=r['ground_rect_logical'];foot=y+h;door=r['door_rect_logical'];dx,dy,dw,dh=door
    _facade(d,(x,y,w,h),103,weather=3 if name=='venn' else 1 if name=='home_c' else 0)
    # Each facade has individually designed bay rhythm and dressing, not a color
    # change on Halden's facade. Their roof courses share physical tile dimensions.
    if name=='elira':
        d.window((51,111,17,20),shutters='right',curtains='#9685b0')
        d.detail('assets/terrain/eldenmere/exteriors_hd/props/windowbox_white/idle.png',(49,127),(20,14))
        d.beam((17,110,6,21));d.line(((19,112),(19,127)),WOOD[2])
    elif name=='halden':
        d.window((22,112,18,19));d.window((81,112,17,19),shutters='right')
        d.stonework((15,132,28,7));d.rect((17,120,9,11),WOOD[0],'timber',INK)
        for yy in range(122,130,2):d.line(((18,yy),(25,yy)),WOOD[2])
        d.detail('assets/terrain/eldenmere/exteriors_hd/props/windowbox_violet/idle.png',(78,126),(23,16))
    elif name=='home_a':
        d.window((25,111,15,17),shutters='right');d.window((82,113,15,18),shutters='left')
        d.beam((16,115,18,21));d.rect((17,116,16,19),WOOD[1],'timber',INK)
        for xx in (21,26,31):d.line(((xx,117),(xx,134)),WOOD[0])
        d.line(((18,132),(32,119)),WOOD[2],2)
    elif name=='home_b':
        d.window((24,113,12,18),shutters='left',curtains='#ded7bc')
        d.window((82,113,12,18),shutters='right',curtains='#ded7bc')
        d.rect((78,134,24,6),WOOD[0],'timber',INK)
        d.rect((79,133,22,2),WOOD[2],'timber',INK)
        d.line(((89,135),(89,139)),STONE[4])
    elif name=='home_c':
        d.window((24,112,20,19),shutters='both');d.window((81,114,14,17),shutters='right')
        d.detail('assets/terrain/eldenmere/exteriors_hd/props/windowbox_yellow/idle.png',(18,126),(27,16))
        d.rect((88,132,9,9),STONE[2],'masonry',INK)
        d.rect((87,131,11,2),STONE[4],'masonry',INK)
    elif name=='venn':
        d.window((23,111,17,20),shutters='left',curtains='#ded7bc')
        d.window((51,114,14,17),shutters='both')
        d.window((103,112,17,19),shutters='right',curtains='#ded7bc')
        d.rect((17,132,22,7),WOOD[0],'timber',INK)
        for xx in range(19,38,3):d.line(((xx,133),(xx,138)),WOOD[2])
        d.detail('assets/terrain/eldenmere/exteriors_hd/props/windowbox_white/idle.png',(101,126),(23,16))
    else: # Liam household: retain repaired roof + open firewood identity.
        d.window((23,112,17,19),shutters='left')
        d.window((51,114,13,17),shutters='right',curtains='#ded7bc')
        d.window((105,111,17,20),shutters='right')
        d.detail('assets/terrain/eldenmere/exteriors_hd/props/firewood/idle.png',(104,127),(24,16))
    # Long roof footprint is visible behind the front wall; no distant horizon.
    d.roof((x-5,32,w+10,73),r['roof'],hip={'elira':13,'halden':6,'venn':9,'home_a':0,'home_b':0,'home_c':17,'liam_house':0}[name],wear=name in ('venn','home_c'))
    d.beam((x-2,105,w+4,3))
    for xx in (x+3,x+w-7):d.brace(xx,108,4,6)
    if name=='halden':
        # Small roof ventilation louvre over the dry storage side.
        d.polygon(((26,82),(34,71),(42,82)),PLASTER[0],'plaster')
        d.rect((29,81,10,9),WOOD[0],'timber',INK)
        for yy in (83,86,89):d.line(((30,yy),(38,yy)),WOOD[2])
        d.brace(26,82,8,-11);d.brace(34,71,8,11)
    if name=='venn':
        # Low cross-gable marks this broad family entrance bay.
        d.polygon(((68,105),(83,86),(99,105)),PLASTER[1],'plaster')
        d.brace(69,105,14,-18);d.brace(83,87,15,18)
        d.rect((80,97,6,4),WOOD[1],'timber',INK)
    if name=='home_a':
        # Long sheet-metal ridge repair, not Liam's broken shingle patch.
        d.rect((28,42,27,6),'#737e7a','roof',INK)
        for xx in range(31,53,5):d.line(((xx,43),(xx,47)), '#a4aaa0')
        d.roof((14,94,23,16),r['roof'],hip=0,ridge=False)
    if name=='home_b':
        d.polygon(((47,105),(59,87),(72,105)),PLASTER[1],'plaster')
        d.brace(48,105,11,-16);d.brace(59,89,12,16)
        d.canopy((48,85,22,7),r['roof'])
        d.rect((56,96,6,5),WOOD[1],'timber',INK)
    if name=='liam_house':
        d.polygon(((97,62),(115,65),(112,80),(94,77)),WOOD[1],'roof')
        for yy in (66,71,76):d.line(((97,yy),(112,yy+2)),WOOD[2])
        d.line(((98,64),(109,78)),WOOD[0],2)
    chimney_x={'elira':73,'halden':91,'home_a':90,'home_b':88,'home_c':90,'venn':116,'liam_house':116}[name]
    emitter=d.chimney(chimney_x,22,24)
    _threshold(d,door,foot);d.portal(door)
    return emitter


def _mira(d,r):
    ground=r['ground_rect_logical'];x,y,w,h=ground
    _facade(d,ground,125,posts=(49,92))
    d.window((22,133,22,22),shutters='left')
    d.rect((98,135,27,22),WOOD[0],'timber',INK)
    d.line(((100,138),(122,138)),WOOD[3],2)
    for xx in (103,110,117):
        d.line(((xx,140),(xx,150)),'#a4aaa0',2)
        d.line(((xx-2,142),(xx+2,142)),'#737e7a',2)
    d.rect((100,154,23,3),WOOD[2],'timber',INK)
    d.roof((7,52,130,75),'terracotta',hip=3)
    d.beam((10,127,124,3))
    for xx in (16,49,93,125):d.brace(xx,130,4,7)
    # Native lower lean-to remains inside occupied walls, not a new blocker.
    d.roof((14,117,30,15),'terracotta',hip=0,ridge=False)
    d.line(((132,130),(144,130)),WOOD[1],5,'timber')
    d.detail('assets/terrain/eldenmere/exteriors_hd/props/sign_cog/idle.png',(135,127),(24,28))
    emitter=d.chimney(116,34,30)
    _threshold(d,r['door_rect_logical'],168);d.portal(r['door_rect_logical'])
    return emitter


def _mill(d,r):
    # Two joined orthographic volumes cover the SAME retained 96x72 ground:
    # a tall processing bay at x57..120 and lower receiving annex at x24..60.
    # Their roof depth covers that ground depth; height changes eave elevation,
    # never wall width or the occupied blocker.
    d.plaster((57,77,63,55),1);d.stonework((57,120,63,12))
    for xx in (57,86,117):d.beam((xx,77,3,44))
    d.beam((57,79,63,3));d.beam((57,117,63,3))
    d.brace(61,104,11,13);d.brace(115,83,-8,6)
    d.rect((75,84,26,31),WOOD[0],'timber',INK)
    d.rect((77,86,22,27),WOOD[1],'timber',INK)
    for xx in (81,86,91,96):d.line(((xx,87),(xx,112)),WOOD[0])
    d.line(((77,109),(98,89)),WOOD[2],3)
    d.window((63,85,10,12),shutters='none')
    d.rect((105,90,10,11),WOOD[0],'timber',INK)
    for yy in (92,95,98):d.line(((106,yy),(114,yy)),WOOD[2])
    # The lower annex and both foundations start at occupied x=24, not x≈2.
    d.plaster((24,99,36,33));d.stonework((24,121,36,11))
    d.beam((24,99,3,23));d.beam((57,99,3,23));d.beam((24,101,36,3))
    d.roof((21,25,43,76),'slate',hip=2)
    d.roof((52,5,72,74),'slate',hip=4)
    # Hoist projects from the front eave. It explains the tall processing volume
    # without inventing extra residential floors or a decorative upstairs room.
    d.beam((73,79,33,3));d.beam((88,72,3,16))
    d.draw.ellipse((174,163,184,173),fill=STONE[2],outline=INK)
    d.line(((89,86),(89,94)),WOOD[3])
    d.stonework((105,117,15,15))
    d.rect((110,116,9,4),'#535c5d','timber',INK)
    emitter=d.chimney(102,8,24)
    _threshold(d,r['door_rect_logical'],140);d.portal(r['door_rect_logical'])
    return emitter


def _school(d,r):
    ground=r['ground_rect_logical'];_facade(d,ground,143,posts=(72,117))
    for xx in (36,60,123,147):
        d.window((xx,152,13,22),shutters='none')
        d.detail('assets/terrain/eldenmere/exteriors_hd/props/windowbox_'+('white' if xx<100 else 'yellow')+'/idle.png',(xx-3,171),(19,14))
    d.roof((19,43,154,102),'slate',hip=4)
    d.beam((22,145,148,3))
    # Central entry gable is a shallow architectural projection, not a huge side wall.
    d.polygon(((78,149),(96,124),(114,149)),PLASTER[1],'plaster')
    d.brace(79,149,17,-23);d.brace(96,126,17,23)
    d.detail('assets/terrain/eldenmere/exteriors_hd/props/sign_book/idle.png',(86,130),(20,19))
    # School bell with its own roof, backed by roof rather than a horizon scene.
    d.beam((90,24,3,29));d.beam((101,24,3,29))
    d.rect((93,27,8,20),WOOD[0],'timber',INK)
    d.detail('assets/maps/eldenmere/courtyard_hd/props/bell.png',(92,29),(10,19))
    d.canopy((87,14,20,13),'slate')
    emitter=d.chimney(146,38,25)
    _threshold(d,r['door_rect_logical'],192);d.portal(r['door_rect_logical'])
    return emitter


def _sanctuary(d,r):
    _facade(d,r['ground_rect_logical'],151,posts=(99,156))
    # Long household facade and existing entrance bays, not a chapel replacement.
    for xx in (25,48,72,165,188):
        d.window((xx,165,12,23),shutters='none',arch=True,curtains='#ded7bc')
    d.roof((7,31,202,122),'slate',hip=5)
    d.beam((10,153,196,3))
    for xx in (18,91,159,197):d.brace(xx,156,6,7)
    # Retain the exact local bell mount [42,54] used by the courtyard helper.
    d.rect((38,34,21,46),WOOD[0],'timber',INK)
    d.rect((41,43,15,34),INK)
    d.beam((38,34,3,45));d.beam((56,34,3,45))
    d.canopy((34,22,29,15),'slate')
    emitter=d.chimney(177,28,30)
    _threshold(d,r['door_rect_logical'],204);d.portal(r['door_rect_logical'])
    # Porch arch/jambs frame the retained wide double doorway.
    x,y,w,h=r['door_rect_logical']
    d.stonework((x-4,y+3,3,h-3));d.stonework((x+w+1,y+3,3,h-3))
    return emitter


def _inn(d,r):
    # Floor heights share a single vertical projection, separate from ground depth.
    _facade(d,r['ground_rect_logical'],122,posts=(64,125))
    d.beam((12,177,168,5))
    # Exactly four front guest bays correspond to the PR4 real upper scene.
    for n,xx in enumerate((28,66,105,144)):
        d.window((xx,137,20,29),shutters='none',curtains=('#ded7bc','#b37d64','#ded7bc','#688b9b')[n])
        d.detail('assets/terrain/eldenmere/exteriors_hd/props/windowbox_white/idle.png',(xx-2,160),(24,16))
    d.window((28,195,29,24),shutters='left')
    d.window((136,195,27,24),shutters='right')
    d.roof((7,24,178,100),'terracotta',hip=5)
    d.beam((10,124,172,4))
    for xx in (17,65,126,171):d.brace(xx,128,5,7)
    # Shallow porch with visible upper surface, jambs and fixed posts.
    d.roof((75,182,42,13),'terracotta',hip=2,ridge=False)
    d.beam((76,195,3,37));d.beam((114,195,3,37))
    emitter=d.chimney(153,27,29)
    d.detail('assets/terrain/eldenmere/business_exteriors_hd/props/porch_bench/idle.png',(23,220),(38,20))
    d.detail('assets/terrain/eldenmere/business_exteriors_hd/props/sheltered_firewood/idle.png',(139,215),(31,25))
    _threshold(d,r['door_rect_logical'],240);d.portal(r['door_rect_logical'])
    return emitter


def _shop(d,r):
    _facade(d,r['ground_rect_logical'],133,posts=(63,152))
    d.roof((7,35,154,100),'slate',hip=4)
    d.beam((10,135,148,3))
    d.rect((18,157,12,16),WOOD[1],'timber',INK)
    for xx in (21,25,28):d.line(((xx,158),(xx,171)),WOOD[0])
    d.rect((20,161,7,2),STONE[1],'timber',INK)
    # Canvas coordinates of merchandise are preserved exactly for old consumers.
    # Authored awning top surface has parallel edges; only cloth is cloth.
    d.polygon(((66,111),(152,111),(155,135),(64,135)),'#435d6b',outline=INK)
    for xx in range(67,152,11):
        d.polygon(((xx,112),(xx+4,112),(xx+3,133),(xx-1,133)),'#688b9b',outline='#688b9b')
    d.line(((64,135),(155,135)),WOOD[2],2)
    for xx in range(65,151,8):d.line(((xx,135),(xx+3,137),(xx+6,135)),'#ded7bc',1)
    d.detail('assets/terrain/eldenmere/business_exteriors_hd/displays/maintained.png',(70,136))
    d.rect((70,136,78,48),None,'merchandise')
    _threshold(d,r['door_rect_logical'],192);d.portal(r['door_rect_logical'])
    return None


def generate_architecture(building_id, record=None):
    """Return an independent drawing; no map mutation, writes, or facade resizes.

    ``building_id`` accepts live entity IDs or their one-to-one existing design
    IDs. ``record`` may supply the existing recipe record so integrations can
    assert registration without duplicating its geometry.
    """
    name=DESIGN_IDS.get(building_id,building_id)
    if name=='liam':name='liam_house'
    if name not in IDENTITIES:raise KeyError(f'No reviewed audit drawing for {building_id}')
    r=records()[name] if record is None else record
    expected=records()[name]
    for key in ('logical_size','ground_rect_logical','door_rect_logical'):
        if r[key]!=expected[key]:raise ValueError(f'Review changed {name} {key} before drawing')
    d=Drawing(name,r['logical_size'])
    if name in ('halden','elira','venn','home_a','home_b','home_c','liam_house'):emitter=_cottage(d,name,r)
    else:emitter={'mira':_mira,'mill':_mill,'school':_school,'sanctuary':_sanctuary,'inn':_inn,'item_shop':_shop}[name](d,r)
    panes=d.finish()
    x,y,w,h=r['ground_rect_logical']
    meta={
        'id':name,'identity':IDENTITIES[name],'artwork_pixels_per_world_pixel':2,
        'logical_size':r['logical_size'],'ground_rect_logical':r['ground_rect_logical'],
        'depth_baseline_logical':y+h,'door_rect_logical':r['door_rect_logical'],
        'roof_planes_logical':d.roof_bounds,'roof_overhang_is_not_occupied_wall':True,
        'roof_volumes':[{'role':'processing bay','ground_rect_logical':[57,60,63,72],'roof_rect_logical':[52,5,72,74]},{'role':'receiving annex','ground_rect_logical':[24,60,36,72],'roof_rect_logical':[21,25,43,76]}] if name=='mill' else [{'role':'main occupied volume','ground_rect_logical':r['ground_rect_logical'],'roof_rect_logical':d.roof_bounds[0]}],
        'wall_ground_bounds_logical':r['ground_rect_logical'],
        'smoke_emitter_logical':emitter,'chimney_cap_rect_logical':[emitter[0]-5,emitter[1]-1.5,10,4] if emitter else None,'pane_regions':d.panes,
        'pane_review':'Explicit per-pane geometry, intersected with actual glass pixels after all framing. No color-selected roof regions.',
        'export_transform':'native authoring at 2x; no source facade registration or portal-first strip scaling',
        'occupied_floors':2 if name=='inn' else 1,
        'fixed_shop_display_rect_logical':[70,136,78,48] if name=='item_shop' else None,
        'business_sign':{'owner':'existing separate business sign layer only; not baked into architecture','prop':r['sign'],'position_logical':r['sign_position_logical']} if name in ('inn','item_shop') else None,
        'mill_wheel_position_logical':[88,94] if name=='mill' else None,
        'mill_axle_center_logical':[112,118] if name=='mill' else None,
        'mill_service_fence':'not present; crossing assembly owns service landing' if name=='mill' else None,
        'bell_mount_logical':[42,54] if name=='sanctuary' else None,
    }
    return Architecture(d.image,panes,d.masks,meta)


def building_structure(record, sources=None, recipe=None):
    """Drop-in builder adapter for the thirteen explicitly reviewed live designs."""
    result=generate_architecture(record['id'],record)
    return result.structure,result.pane_mask


def _png(image):
    stream=BytesIO();image.save(stream,format='PNG');return stream.getvalue()


def preview_closed(architecture):
    """Review-only closed door/bell/wheel composition from retained native parts."""
    result=architecture.structure.copy();name=architecture.metadata['id'];r=records()[name]
    family='business_exteriors_hd' if name in ('inn','item_shop') else 'exteriors_hd'
    design=r['id'];door=ROOT/f'assets/terrain/eldenmere/{family}/buildings/{design}/doors/frame_00.png'
    if door.exists():
        with Image.open(door) as im:result.alpha_composite(im.convert('RGBA'),tuple(v*2 for v in r['door_rect_logical'][:2]))
    if name in ('inn','item_shop'):
        with Image.open(ROOT/f"assets/terrain/eldenmere/business_exteriors_hd/props/{r['sign']}/idle.png") as im:result.alpha_composite(im.convert('RGBA'),tuple(v*2 for v in r['sign_position_logical']))
    if name=='mill':
        with Image.open(ROOT/'assets/terrain/eldenmere/exteriors_hd/mill/wheel_idle.png') as im:result.alpha_composite(im.convert('RGBA'),(176,188))
    if name=='sanctuary':
        with Image.open(ROOT/'assets/maps/eldenmere/courtyard_hd/props/bell.png') as im:result.alpha_composite(im.convert('RGBA'),(84,108))
    return result


def products():
    result={};schedule=[];images={}
    for name in IDENTITIES:
        art=generate_architecture(name);images[name]=preview_closed(art)
        folder=BUSINESS_SOURCE if name in ('inn','item_shop') else SOURCE
        target=folder/name
        for label,im in [('structure',art.structure),('pane_mask',art.pane_mask),*[(k+'_mask',v) for k,v in art.material_masks.items()]]:
            result[str((target/(label+'.png')).relative_to(ROOT))]=_png(im)
        result[str((target/'geometry.json').relative_to(ROOT))]=(json.dumps(art.metadata,indent=2)+'\n').encode()
        schedule.append(art.metadata)
    # All rows remain native 2x. Scale witnesses and footprint overlays are not
    # production assets or substitutes for actual in-game movement captures.
    board=Image.new('RGB',(4*480,4*560),'#e8e9df');bd=ImageDraw.Draw(board)
    actor=Image.open(ROOT/'assets/characters/caelan/review_hd/idles/idle_front.png').convert('RGBA')
    overlay=board.copy();od=ImageDraw.Draw(overlay)
    pane_board=board.copy();pd=ImageDraw.Draw(pane_board)
    for i,(name,im) in enumerate(images.items()):
        xx=(i%4)*480+(480-im.width)//2;yy=(i//4)*560+24
        board.paste(im,(xx,yy),im);overlay.paste(im,(xx,yy),im)
        art=generate_architecture(name);x,y,w,h=art.metadata['ground_rect_logical'];dx,dy,dw,dh=art.metadata['door_rect_logical']
        pane_image=im.copy();tint=Image.new('RGBA',im.size,'#f6c653');tint.putalpha(art.pane_mask);pane_image.alpha_composite(tint);pane_board.paste(pane_image,(xx,yy),pane_image)
        pd.text((i%4*480+12,i//4*560+526),name+' / gold = reviewed panes only',fill='#243529')
        ax=xx+round((dx+dw/2)*2)-actor.width//2;ay=yy+round((y+h)*2)+20-68
        for target in (board,overlay):target.paste(actor,(ax,ay),actor)
        for tx in range(0,480,48):od.line(((i%4*480+tx,yy),(i%4*480+tx,yy+490)),fill='#d0d7c8')
        od.rectangle((xx+x*2,yy+y*2,xx+(x+w)*2-1,yy+(y+h)*2-1),outline='#06a9b4',width=2)
        od.rectangle((xx+dx*2,yy+dy*2,xx+(dx+dw)*2-1,yy+(dy+dh)*2-1),outline='#d78936',width=2)
        od.line(((xx+x*2,yy+(y+h)*2),(xx+(x+w)*2,yy+(y+h)*2)),fill='#bd5377',width=3)
        for dd in (bd,od):dd.text((i%4*480+12,i//4*560+526),name+' / native 2x / Caelan scale',fill='#243529')
    bd.text((12,8),'AUTHORING CONTACT BOARD, NOT GAMEPLAY',fill='#243529')
    od.text((12,8),'AUTHORING FOOTPRINTS, NOT GAMEPLAY / cyan occupied ground, orange portal, pink depth baseline',fill='#243529')
    pd.text((12,8),'AUTHORING PANE OWNERSHIP, NOT GAMEPLAY / roof, masonry, timber and stock excluded',fill='#243529')
    result[str((SOURCE/'pane_ownership_board.png').relative_to(ROOT))]=_png(pane_board)
    compare=Image.new('RGB',(1000,500),'#e8e9df');cd=ImageDraw.Draw(compare)
    for i,name in enumerate(('mill','school','item_shop')):
        sample=generate_architecture(name)
        # Exact native crops keep both material states at 1:1 density.
        left=sample.ambient(7);right=sample.ambient(7,True)
        for j,pic in enumerate((left,right)):
            px=i*330+j*165;py=30
            if name=='mill':crop=(140,90,280,285)
            elif name=='school':crop=(235,220,375,380)
            else:crop=(140,270,296,368)
            patch=pic.crop(crop);compare.paste(patch,(px,py),patch)
            cd.text((px,250),name+(' normal' if j==0 else ' reduced'),fill='#243529')
    cd.text((8,8),'NATIVE AUTHORING MATERIAL CHECK, NOT GAMEPLAY: fixed mill slate, school panes and shop stock',fill='#243529')
    result[str((SOURCE/'normal_reduced_material_board.png').relative_to(ROOT))]=_png(compare)
    result[str((SOURCE/'native_contact_board.png').relative_to(ROOT))]=_png(board)
    result[str((SOURCE/'footprint_contact_board.png').relative_to(ROOT))]=_png(overlay)
    result[str((SOURCE/'recipe.json').relative_to(ROOT))]=(json.dumps({
        'version':1,'builder':'tools/eldenmere_architecture_art.py','density':2,
        'projection':'orthogonal axes; vertical walls rise from declared ground rectangles; parallel eaves and roof ridges; height does not enlarge blockers',
        'status':'authored shell revision; live integration and gameplay captures owned by town builder',
        'palette_reference':'assets/source/terrain/eldenmere/exteriors_hd/recipe.json',
        'designs':schedule,
        'retained_native_details':['existing five door states','native mill wheel','courtyard bell at retained mount','cog/book signs','business signs','fixed shop display','inn bench/firewood'],
        'new_native_construction':['deep roof planes with fixed-size shingle courses','registered foundations and occupied walls','per-household window rhythms, joinery and storage','mill receiving annex/hoist/processing structure','school footprint correction and flue','right-hearth workshop flue','two-storey inn structural framing'],
        'not_reused':['legacy RGB buildings','portal-first facade strips','mill baked service fence'],
        'native_material_source':{'file':'assets/source/terrain/eldenmere/exteriors_hd/cottages_authored.png','sha256':sha256((ROOT/'assets/source/terrain/eldenmere/exteriors_hd/cottages_authored.png').read_bytes()).hexdigest(),'isolated_shingle_rectangles':[[127,433,151,449],[154,434,178,450],[183,434,207,450],[211,434,235,450],[113,452,137,468],[142,452,166,468],[173,452,197,468],[202,452,226,468],[233,452,257,468]],'sample':'uniform 24x16 to 21x14; material values mapped to existing roof ramp'},
        'source_module_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),
    },indent=2)+'\n').encode()
    return result


def build(check=False):
    result=products();stale=[]
    for path,data in result.items():
        target=ROOT/path
        if not target.exists() or target.read_bytes()!=data:
            stale.append(path)
            if not check:target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    if check and stale:raise SystemExit('Stale architecture authoring exports: '+', '.join(stale))
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');args=parser.parse_args()
    print(f'{len(build(args.check))} architecture authoring exports '+('verified' if args.check else 'built'))
