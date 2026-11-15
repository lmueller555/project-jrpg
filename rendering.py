"""Logical-coordinate drawing onto a complete 2x scene buffer.

Pygame surfaces passed by asset tools retain ordinary semantics. Runtime draw
calls opt into these adapters explicitly; pygame itself is never monkeypatched.
"""
from collections import OrderedDict
import math
import weakref
import pygame

LOGICAL_SIZE = (480, 320)
RENDER_SCALE = 2
RENDER_SIZE = (960, 640)
CACHE_BYTES = 32 * 1024 * 1024
_CACHE = OrderedDict()
_CACHE_WEIGHT = 0
_IMMUTABLE = weakref.WeakSet()


def immutable(image):
    _IMMUTABLE.add(image)
    return image


def cache_info():
    return {'bytes': _CACHE_WEIGHT, 'entries': len(_CACHE), 'budget': CACHE_BYTES}


def clear_cache():
    global _CACHE_WEIGHT
    _CACHE.clear(); _CACHE_WEIGHT = 0


def _scaled(image, size):
    global _CACHE_WEIGHT
    size = tuple(max(1, round(v)) for v in size)
    if image.get_size() == size:return image
    if image not in _IMMUTABLE:return pygame.transform.scale(image, size)
    key = (image, size, image.get_alpha(), image.get_colorkey())
    found = _CACHE.pop(key, None)
    if found is not None:
        _CACHE[key] = found
        return found
    result = pygame.transform.scale(image, size)
    weight = result.get_pitch() * result.get_height()
    if weight <= CACHE_BYTES:
        while _CACHE and _CACHE_WEIGHT + weight > CACHE_BYTES:
            _, old = _CACHE.popitem(last=False)
            _CACHE_WEIGHT -= surface_bytes(old)
        _CACHE[key] = result; _CACHE_WEIGHT += weight
    return result


def _rect(rect, factor=2):
    values=tuple(rect)
    if len(values)==2:
        x,y=values[0];width,height=values[1]
    else:x,y,width,height=values
    left,top=round(x*factor),round(y*factor)
    right,bottom=round((x+width)*factor),round((y+height)*factor)
    return pygame.Rect(left,top,right-left,bottom-top)


class WorldCanvas(pygame.Surface):
    """A logical compatibility surface plus an authoritative full-scene buffer.

    Geometry-facing Surface methods remain in logical units. ``native`` is the
    complete render-pixel surface. The logical mirror supports existing sampling
    and geometry code; presentation never reconstructs the scene from that mirror.
    """
    def __init__(self, size, flags=0, depth=32):
        super().__init__(size, flags, depth)
        self.native = pygame.Surface((size[0]*2, size[1]*2), flags, depth)

    @property
    def dense(self):return self.native

    def reset_detail(self):
        # Kept for callers that begin a frame here. No detail patches or pixel
        # repair scans exist: every pass writes the full composition directly.
        pass

    def present_detail(self, target):present(self, target)

    def fill(self, color, rect=None, special_flags=0):
        result = super().fill(color, rect, special_flags)
        self.native.fill(color, None if rect is None else _rect(rect), special_flags)
        return result

    def blit(self, source, dest, area=None, special_flags=0):
        result = super().blit(source, dest, area, special_flags)
        origin = dest.topleft if isinstance(dest, pygame.Rect) else dest[:2]
        # Clip in render pixels so a half-unit anchor at the viewport edge
        # keeps its last visible texel. Geometry-facing bounds stay logical.
        area_rect=source.get_rect() if area is None else pygame.Rect(area)
        origin_px=(round(origin[0]*2),round(origin[1]*2))
        bounds=pygame.Rect(origin_px,(area_rect.w*2,area_rect.h*2))
        visible=bounds.clip(self.native.get_clip()).clip(self.native.get_rect())
        if not visible:return result
        crop=pygame.Rect(area_rect.x*2+visible.x-origin_px[0],
                         area_rect.y*2+visible.y-origin_px[1],*visible.size)
        crop=crop.clip(pygame.Rect(0,0,source.get_width()*2,source.get_height()*2))
        if not crop:return result
        position=(origin_px[0]+crop.x-area_rect.x*2,
                  origin_px[1]+crop.y-area_rect.y*2)
        if isinstance(source,WorldCanvas):image=source.native.subsurface(crop)
        elif source.get_width()*source.get_height()<=256*256 and source in _IMMUTABLE:
            image=_scaled(source,(source.get_width()*2,source.get_height()*2)).subsurface(crop)
        else:
            left,top=crop.x//2,crop.y//2
            right,bottom=math.ceil(crop.right/2),math.ceil(crop.bottom/2)
            logical_crop=pygame.Rect(left,top,right-left,bottom-top)
            image=_scaled(source.subsurface(logical_crop),(logical_crop.w*2,logical_crop.h*2))
            image=image.subsurface((crop.x-left*2,crop.y-top*2,crop.w,crop.h))
        self.native.blit(image,position,special_flags=special_flags)
        return result

    def blits(self, blit_sequence, doreturn=1):
        result = [self.blit(*args) for args in blit_sequence]
        return result if doreturn else None

    def blit_art(self, image, position):
        asset = artwork(image, 2)
        return self.blit(asset, position)

    def set_clip(self, rect=None):
        result = super().set_clip(rect)
        self.native.set_clip(None if rect is None else _rect(rect))
        return result

    def set_alpha(self, value, flags=0):
        super().set_alpha(value, flags);self.native.set_alpha(value, flags)

    def set_colorkey(self, color, flags=0):
        super().set_colorkey(color, flags);self.native.set_colorkey(color, flags)

    def set_at(self, pos, color):
        super().set_at(pos,color);self.native.fill(color,(pos[0]*2,pos[1]*2,2,2))

    def scroll(self, dx=0, dy=0):
        super().scroll(dx,dy);self.native.scroll(dx*2,dy*2)

    def get_bounding_rect(self,min_alpha=1):
        bounds=self.native.get_bounding_rect(min_alpha)
        left,top=bounds.left//2,bounds.top//2
        return pygame.Rect(left,top,math.ceil(bounds.right/2)-left,
                           math.ceil(bounds.bottom/2)-top)

    def copy(self):
        out=pygame.Surface.copy(self)
        out.native=self.native.copy()
        return out

    def subsurface(self, *args):
        rect=pygame.Rect(*args)
        out=pygame.Surface.subsurface(self,rect)
        out.native=self.native.subsurface(_rect(rect))
        return out

    def convert(self, *args):
        out=pygame.Surface.convert(self,*args)
        out.native=self.native.convert(*args)
        return out

    def convert_alpha(self, *args):
        out=pygame.Surface.convert_alpha(self,*args)
        out.native=self.native.convert_alpha(*args)
        return out


def layer(size, flags=pygame.SRCALPHA, depth=32):
    return WorldCanvas(size,flags,depth)


def artwork(image, density=1, logical_size=None):
    """Normalize explicit artwork density; raw image loading is unchanged."""
    if type(density) not in (int,float) or density not in (1,2):
        raise ValueError('Artwork density must be 1 or 2 pixels per world unit')
    expected=tuple(value/density for value in image.get_size())
    if any(value != int(value) for value in expected):
        raise ValueError('Artwork dimensions must be divisible by density')
    if logical_size is not None and tuple(logical_size)!=expected:
        raise ValueError('Artwork dimensions do not match the logical size')
    if density==1:return image
    if isinstance(image,WorldCanvas):return image
    key=('artwork',image,density,image.get_alpha(),image.get_colorkey())
    cached=_CACHE.pop(key,None)
    if cached is not None:
        _CACHE[key]=cached
        return cached
    size=tuple(int(v) for v in expected)
    out=WorldCanvas(size,pygame.SRCALPHA)
    pygame.Surface.blit(out,pygame.transform.scale(image,size),(0,0))
    out.native=image.copy()
    if image in _IMMUTABLE:
        global _CACHE_WEIGHT
        weight=out.native.get_pitch()*out.native.get_height()+out.get_pitch()*out.get_height()
        if weight<=CACHE_BYTES:
            while _CACHE and _CACHE_WEIGHT+weight>CACHE_BYTES:
                _,old=_CACHE.popitem(last=False)
                _CACHE_WEIGHT-=surface_bytes(old)
            _CACHE[key]=out;_CACHE_WEIGHT+=weight
    return out


def present(source, target):
    image=source.native if isinstance(source,WorldCanvas) else source
    pygame.transform.scale(image,target.get_size(),target)


def snapshot(source):
    """An ordinary, complete render-pixel frame, independent of live state."""
    return (source.native if isinstance(source,WorldCanvas) else source).copy()


def scale(source, size, dest_surface=None):
    size=tuple(round(v) for v in size)
    if isinstance(dest_surface,WorldCanvas):
        pygame.transform.scale(source,size,dest_surface)
        raw=source.native if isinstance(source,WorldCanvas) else source
        pygame.transform.scale(raw,(size[0]*2,size[1]*2),dest_surface.native)
        return dest_surface
    if isinstance(source,WorldCanvas):
        if dest_surface is not None:
            pygame.transform.scale(source.native,size,dest_surface)
            return dest_surface
        result=WorldCanvas(size,source.get_flags() & pygame.SRCALPHA)
        pygame.transform.scale(source,size,result)
        pygame.transform.scale(source.native,(size[0]*2,size[1]*2),result.native)
        return result
    return (pygame.transform.scale(source,size) if dest_surface is None else
            pygame.transform.scale(source,size,dest_surface))


def flip(source, xbool, ybool):
    if not isinstance(source,WorldCanvas):return pygame.transform.flip(source,xbool,ybool)
    out=source.copy()
    pygame.Surface.blit(out,pygame.transform.flip(source,xbool,ybool),(0,0))
    out.native=pygame.transform.flip(source.native,xbool,ybool)
    return out


def rotate(source, angle):
    if not isinstance(source,WorldCanvas):return pygame.transform.rotate(source,angle)
    low=pygame.transform.rotate(source,angle)
    out=WorldCanvas(low.get_size(),pygame.SRCALPHA);pygame.Surface.blit(out,low,(0,0))
    high=pygame.transform.rotate(source.native,angle)
    out.native=pygame.transform.scale(high,(low.get_width()*2,low.get_height()*2))
    return out


class _Draw:
    """Explicit logical-coordinate adapters for pygame drawing primitives."""
    def __getattr__(self,name):
        original=getattr(pygame.draw,name)
        def call(surface,color,*args,**kwargs):
            original=getattr(pygame.draw,name)
            result=original(surface,color,*args,**kwargs)
            if not isinstance(surface,WorldCanvas):return result
            a=list(args);k=dict(kwargs)
            point=lambda p:tuple(round(v*2) for v in p)
            if name in ('rect','ellipse','arc'):
                if a:a[0]=_rect(a[0])
                if 'rect' in k:k['rect']=_rect(k['rect'])
            elif name=='circle':
                if a:a[0]=point(a[0])
                if len(a)>1:a[1]=round(a[1]*2)
                if 'center' in k:k['center']=point(k['center'])
                if 'radius' in k:k['radius']=round(k['radius']*2)
            elif name in ('line','aaline'):
                for i in range(min(2,len(a))):a[i]=point(a[i])
                for key in ('start_pos','end_pos'):
                    if key in k:k[key]=point(k[key])
            elif name in ('lines','aalines'):
                if len(a)>1:a[1]=[point(p) for p in a[1]]
                if 'points' in k:k['points']=[point(p) for p in k['points']]
            elif name=='polygon':
                if a:a[0]=[point(p) for p in a[0]]
                if 'points' in k:k['points']=[point(p) for p in k['points']]
            width_index={'rect':1,'ellipse':1,'arc':3,'circle':2,'line':2,'lines':2,'polygon':1}.get(name)
            if width_index is not None and len(a)>width_index:a[width_index]*=2
            elif name in ('line','lines','arc') and 'width' not in k:k['width']=2
            for key in ('width','border_radius','border_top_left_radius','border_top_right_radius','border_bottom_left_radius','border_bottom_right_radius'):
                if key in k and k[key]>=0:k[key]*=2
            # Positional rounded-rectangle radius follows the width argument.
            if name=='rect':
                for i in range(2,len(a)):
                    if a[i]>=0:a[i]*=2
            original(surface.native,color,*a,**k)
            return result
        setattr(self,name,call)
        return call


draw=_Draw()


def record_art(image, record=None, default_density=1):
    record=record or {}
    return artwork(image,record.get('artwork_pixels_per_world_pixel',default_density),
                   record.get('logical_size'))


def load_art(world,path,record=None):
    loader=getattr(world,'art_image',None)
    return loader(path,record) if loader is not None else record_art(world.image(path),record)


def surface_bytes(image):
    return image.get_pitch()*image.get_height()+(image.native.get_pitch()*image.native.get_height()
                                               if isinstance(image,WorldCanvas) else 0)


class SurfaceCache(OrderedDict):
    """Byte-bounded LRU for projected image banks; oversized results stay transient."""
    def __init__(self,budget=64*1024*1024):
        super().__init__();self.budget=budget;self.bytes=0
    def get(self,key,default=None):
        value=super().get(key,default)
        if key in self:self.move_to_end(key)
        return value
    def __setitem__(self,key,value):
        if key in self:self.bytes-=surface_bytes(super().pop(key))
        weight=surface_bytes(value)
        if weight>self.budget:return
        while self and self.bytes+weight>self.budget:
            _,old=super().popitem(last=False);self.bytes-=surface_bytes(old)
        super().__setitem__(key,value);self.bytes+=weight
    def clear(self):super().clear();self.bytes=0


def project_art(source,size):
    """Sample authored artwork directly into both scene densities at load/cache time."""
    if isinstance(source,WorldCanvas):return scale(source,size)
    size=tuple(max(1,round(v)) for v in size)
    out=WorldCanvas(size,source.get_flags() & pygame.SRCALPHA)
    pygame.transform.scale(source,size,out)
    pygame.transform.scale(source,(size[0]*2,size[1]*2),out.native)
    return out


def display_image(source,size):
    """A plain display-space bitmap; no logical intermediate escapes to UI blit."""
    return pygame.transform.scale(source.native if isinstance(source,WorldCanvas) else source,
                                  tuple(round(v) for v in size))
