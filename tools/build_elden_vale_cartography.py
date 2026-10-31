"""Bake a georeferenced illustrated atlas from original cartographic art.

Only this offline exporter assembles a regional canvas. The game loads visible
fixed-size tiles at a suitable mip level, shared between the map and minimap.
Generated art supplies the illustration; authored geography supplies its masks.
"""
from __future__ import annotations

import argparse
import hashlib
from io import BytesIO
import json
import math
import os
from pathlib import Path
import sys

os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from regional_cartography import geometry_fingerprint

REGION = ROOT/'assets/maps/overworld/elden_vale/region.json'
ART = ROOT/'assets/cartography/elden_vale/art/art.json'
OUTPUT = ROOT/'assets/cartography/elden_vale'
SOURCE = ROOT/'assets/source/cartography/elden_vale'
DENSITY = 6
TILE_SIZE = 512
LEVELS = (1,2,4)
FOCUS = [-140,-110,280,220]


def encoded(image):
    buffer = BytesIO();image.save(buffer,format='PNG',optimize=True)
    return buffer.getvalue()


def stable(x,y,salt=0):
    return ((x*73856093)^(y*19349663)^(salt*83492791))&0xffffffff


def thick_path(draw,points,width,fill):
    if len(points)<2:return
    draw.line(points,fill=fill,width=max(1,round(width)),joint='curve')
    radius = width/2
    for x,y in points:draw.ellipse((x-radius,y-radius,x+radius,y+radius),fill=fill)


def survey(data):
    bx,by,bw,bh = data['bounds_tiles'];scale = 3
    canvas = Image.new('RGB',(bw*scale,bh*scale),'#d8dfc2')
    draw = ImageDraw.Draw(canvas)
    point = lambda p:((p[0]-bx)*scale,(p[1]-by)*scale)
    colors = {'fields':'#d1b46e','forests':'#729469','hills':'#b2aa84','scorched':'#806e60'}
    for group in ('fields','forests','hills','scorched'):
        for feature in data.get('terrain',{}).get(group,[]):
            draw.polygon([point(p) for p in feature['polygon']],fill=colors[group])
    for river in data.get('terrain',{}).get('rivers',[]):
        thick_path(draw,[point(p) for p in river['points']],river['width']*scale,'#639cab')
    for road in data.get('roads',[]):
        thick_path(draw,[point(p) for p in road['points']],max(1,road['width']*scale*.6),'#eadbb8')
    for wall in data.get('walls',[]):
        draw.line((point((wall['x0'],wall['y'])),point((wall['x1'],wall['y']))),fill='#58645b',width=3)
    anchors = {'Eldenmere':data['town']['tile_position'],
               'Western crossing':data['bridge']['tile_position']}
    anchors.update({g['label']:g['tile_position'] for g in data.get('gates',[])})
    for name,p in anchors.items():
        x,y = point(p);draw.ellipse((x-5,y-5,x+5,y+5),fill='#773f39')
        draw.text((x+8,y-6),name,fill='#26372f',stroke_width=1,stroke_fill='#eee6cf')
    metadata = {'version':1,'source':REGION.relative_to(ROOT).as_posix(),
                'geometry_sha256':geometry_fingerprint(data),'bounds_tiles':data['bounds_tiles'],
                'survey_pixels_per_tile':scale,'atlas_pixels_per_tile':DENSITY,
                'focus_bounds_tiles':FOCUS,'anchors':anchors,
                'notes':'Geographic survey only; artwork adds no roads, watercourses or labels.'}
    return encoded(canvas),(json.dumps(metadata,indent=2)+'\n').encode()


class Illustrator:
    def __init__(self,data):
        self.data = data;self.bounds = data['bounds_tiles'];self.assets = json.loads(ART.read_text())
        self._images = {}
        self.size = self.bounds[2]*DENSITY,self.bounds[3]*DENSITY

    def image(self,key,kind='tiles'):
        cache = kind,key
        if cache not in self._images:
            record = self.assets[kind][key]
            self._images[cache] = Image.open(ROOT/record['image']).convert('RGBA')
        return self._images[cache]

    def point(self,p):return ((p[0]-self.bounds[0])*DENSITY,(p[1]-self.bounds[1])*DENSITY)

    def pattern(self,size,key,origin=(0,0)):
        image = self.image(key);target = Image.new('RGBA',size)
        for x in range(-(origin[0]%image.width),size[0],image.width):
            for y in range(-(origin[1]%image.height),size[1],image.height):target.alpha_composite(image,(x,y))
        return target

    def polygon_layer(self,canvas,feature,key,feather=2,angle=0):
        points = [self.point(p) for p in feature['polygon']]
        left,top = max(0,math.floor(min(p[0] for p in points))-8),max(0,math.floor(min(p[1] for p in points))-8)
        right,bottom = min(self.size[0],math.ceil(max(p[0] for p in points))+8),min(self.size[1],math.ceil(max(p[1] for p in points))+8)
        if right<=left or bottom<=top:return
        size = right-left,bottom-top
        mask = Image.new('L',size);draw = ImageDraw.Draw(mask)
        draw.polygon([(x-left,y-top) for x,y in points],fill=255)
        if feather:mask = mask.filter(ImageFilter.GaussianBlur(feather))
        if angle:
            span = math.ceil(math.hypot(*size))+4
            raw = self.pattern((span,span),key,(left,top)).rotate(-angle,Image.Resampling.NEAREST)
            x,y = (raw.width-size[0])//2,(raw.height-size[1])//2
            layer = raw.crop((x,y,x+size[0],y+size[1]))
        else:layer = self.pattern(size,key,(left,top))
        layer.putalpha(mask)
        canvas.alpha_composite(layer,(left,top))

    def masses(self,canvas,feature,keys,*,spacing=108,size=176,seed=0):
        """Compose generated canopy/ridge silhouettes within the survey mask."""
        points = [self.point(p) for p in feature['polygon']]
        left,top = max(0,math.floor(min(p[0] for p in points))),max(0,math.floor(min(p[1] for p in points)))
        right,bottom = min(self.size[0],math.ceil(max(p[0] for p in points))),min(self.size[1],math.ceil(max(p[1] for p in points)))
        if right<=left or bottom<=top:return
        box = right-left,bottom-top
        layer = Image.new('RGBA',box);mask = Image.new('L',box)
        ImageDraw.Draw(mask).polygon([(x-left,y-top) for x,y in points],fill=255)
        mask = mask.filter(ImageFilter.GaussianBlur(3))
        for row,y in enumerate(range(top-size//2,bottom+size//2,spacing)):
            for col,x in enumerate(range(left-size//2,right+size//2,spacing)):
                value = stable(col,row,seed)
                width = round(size*(.85+(value%31)/100))
                raw = self.image(keys[(value>>6)%len(keys)],'props')
                sprite = raw.resize((width,width),Image.Resampling.NEAREST)
                # Jitter of whole illustrated masses avoids a symbol lattice.
                px = x-left+(value%35)-17;py = y-top+((value>>9)%35)-17
                layer.alpha_composite(sprite,(px,py))
        alpha = layer.getchannel('A')
        from PIL import ImageChops
        layer.putalpha(ImageChops.multiply(alpha,mask))
        canvas.alpha_composite(layer,(left,top))

    def render(self):
        canvas = self.pattern(self.size,'land')
        terrain = self.data.get('terrain',{})
        for feature in terrain.get('fields',[]):
            crop = feature.get('crop','grain')
            self.polygon_layer(canvas,feature,crop if crop in self.assets['tiles'] else 'grain',1,
                               feature.get('row_angle',0))
        for index,feature in enumerate(terrain.get('forests',[])):
            key = 'forest_floor' if 'forest_floor' in self.assets['tiles'] else 'land'
            self.polygon_layer(canvas,feature,key,5)
            style = feature.get('style','broadleaf')
            keys = ['forest_conifer_a','forest_conifer_b'] if style=='conifer' else ['forest_broadleaf_a','forest_broadleaf_b']
            if style=='mixed':keys += ['forest_conifer_a']
            self.masses(canvas,feature,keys,spacing=92,size=170,seed=index+17)
        for index,feature in enumerate(terrain.get('hills',[])):
            if feature.get('style')=='wooded_rise':continue
            key = 'rock_base' if 'rock_base' in self.assets['tiles'] else 'pasture'
            self.polygon_layer(canvas,feature,key,6)
            self.masses(canvas,feature,['foothills_a','foothills_b'],spacing=115,size=200,seed=index+61)
        # Geography wins over illustration: these exact masks keep channels
        # aligned and never fabricate blue rivers, fords, or hidden crossings.
        water = self.pattern(self.size,'water')
        bank_mask = Image.new('L',self.size);water_mask = Image.new('L',self.size)
        for river in terrain.get('rivers',[]):
            points = [self.point(p) for p in river['points']]
            width = river.get('width',10)*DENSITY
            thick_path(ImageDraw.Draw(bank_mask),points,width+12,255)
            thick_path(ImageDraw.Draw(water_mask),points,width,255)
        bank = self.pattern(self.size,'fallow');bank.putalpha(bank_mask)
        canvas.alpha_composite(bank)
        water.putalpha(water_mask);canvas.alpha_composite(water)
        return canvas.convert('RGB')


def build(check=False,survey_only=False):
    data = json.loads(REGION.read_text())
    png,metadata = survey(data)
    products = {SOURCE/'survey.png':png,SOURCE/'survey.json':metadata}
    if not survey_only:
        if not ART.is_file():raise ValueError('Cartographic artwork must be exported first')
        art = json.loads(ART.read_text())
        inputs = [REGION,ART,Path(__file__).resolve(),ROOT/'regional_cartography.py']
        inputs += [ROOT/item['image'] for group in ('tiles','props') for item in art.get(group,{}).values()]
        hashes = {path.relative_to(ROOT).as_posix():hashlib.sha256(path.read_bytes()).hexdigest() for path in inputs}
        illustrator = Illustrator(data);canvas = illustrator.render();records = []
        for level in LEVELS:
            image = canvas if level==1 else canvas.resize((canvas.width//level,canvas.height//level),Image.Resampling.LANCZOS)
            for y in range(math.ceil(image.height/TILE_SIZE)):
                for x in range(math.ceil(image.width/TILE_SIZE)):
                    right,bottom = min((x+1)*TILE_SIZE,image.width),min((y+1)*TILE_SIZE,image.height)
                    tile = image.crop((x*TILE_SIZE,y*TILE_SIZE,right,bottom))
                    path = OUTPUT/f'tiles/lod_{level}/{x}_{y}.png'
                    products[path] = encoded(tile)
                    records.append({'level':level,'x':x,'y':y,'image':path.relative_to(ROOT).as_posix(),
                                    'size':list(tile.size)})
        manifest = {'version':1,'region_id':data['region_id'],'geometry_sha256':geometry_fingerprint(data),
                    'bounds_tiles':data['bounds_tiles'],'focus_bounds_tiles':FOCUS,
                    'pixels_per_tile':DENSITY,'tile_size':TILE_SIZE,'levels':list(LEVELS),
                    'art_manifest':ART.relative_to(ROOT).as_posix(),
                    'art_sha256':hashlib.sha256(ART.read_bytes()).hexdigest(),
                    'source':REGION.relative_to(ROOT).as_posix(),
                    'source_sha256':hashlib.sha256(REGION.read_bytes()).hexdigest(),
                    'input_sha256':hashes,
                    'tiles':records}
        products[OUTPUT/'manifest.json'] = (json.dumps(manifest,indent=2)+'\n').encode()
        for path,digest in hashes.items():
            if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=digest:
                raise ValueError(f'Cartography input changed during export: {path}')
    for path,content in products.items():
        if check:
            if not path.is_file() or path.read_bytes()!=content:raise ValueError(f'Stale map asset: {path.relative_to(ROOT)}')
        else:
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(content)
    print(f'{"Verified" if check else "Exported"} survey'+('' if survey_only else f' and {len(records)} illustrated atlas tiles'))


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true');parser.add_argument('--survey-only',action='store_true')
    args = parser.parse_args();build(check=args.check,survey_only=args.survey_only)
