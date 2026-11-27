"""Shared, fully spatial Fire Veinhold architecture for the offline prologue.

This module does not create Blender objects or depend on bpy.  The caller owns
materials, mesh batching, lighting and rendering.  Dimensions are metres; the
south gate's open bridge centreline is (-40, -115, 12).
"""
from __future__ import annotations

import math
import random


def _arch(m, x, y, z, width, height, depth, material="bronze", rotation=0):
    """A physically open, segmented round arch, with separately modelled posts."""
    r = width / 2
    shoulder = z + height - r
    c, s = math.cos(rotation), math.sin(rotation)
    def p(u, v, zz):
        return (x + u*c-v*s, y + u*s+v*c, zz)
    for side in (-1, 1):
        m.cube(p(side*(r+.38), 0, (z+shoulder)/2),
               (.76, depth, shoulder-z), material, rotation_z=rotation)
    for i in range(14):
        a, b = math.pi*i/14, math.pi*(i+1)/14
        m.beam(p(r*math.cos(a), 0, shoulder+r*math.sin(a)),
               p(r*math.cos(b), 0, shoulder+r*math.sin(b)), .76, material)


def _banner(m, x, y, z, width=3.0, height=10, rotation=0):
    c, s = math.cos(rotation), math.sin(rotation)
    def p(u, v, zz):
        return (x+u*c-v*s, y+u*s+v*c, zz)
    m.cube(p(0, 0, z), (width, .10, height), "crimson", rotation_z=rotation)
    # Long inset golden lance/chevron is the same insignia on every facade.
    m.beam(p(-width*.36, -.075, z+height*.31),
           p(0, -.075, z-height*.32), .12, "bronze_light")
    m.beam(p(width*.36, -.075, z+height*.31),
           p(0, -.075, z-height*.32), .12, "bronze_light")
    m.beam(p(0, -.08, z+height*.42), p(0, -.08, z-height*.16),
           .1, "bronze_light")
    m.beam(p(-width*.62, 0, z+height*.52),
           p(width*.62, 0, z+height*.52), .18, "bronze")


def _window(m, x, y, z, width=1.2, height=2.2, rotation=0, lit=True):
    c, s = math.cos(rotation), math.sin(rotation)
    def p(u, v, zz):
        return (x+u*c-v*s, y+u*s+v*c, zz)
    m.cube(p(0, 0, z), (width+.42, .14, height+.40),
           "black", rotation_z=rotation)
    m.cube(p(0, -.09, z), (width, .09, height),
           "window" if lit else "steel", rotation_z=rotation)
    # Broad sill, fine lintel and mullion preserve the window silhouette at range.
    for zz in (z-height/2-.12, z+height/2+.12):
        m.cube(p(0, -.12, zz), (width+.62, .32, .18),
               "bronze", rotation_z=rotation)
    m.cube(p(0, -.15, z), (.09, .10, height),
           "bronze", rotation_z=rotation)


def _roof(m, x, y, z, w, d, rise):
    """Pitched slate roof: real sloping faces, ribs, rooflights and eave trim."""
    xl, xr, yf, yb = x-w/2, x+w/2, y-d/2, y+d/2
    ridge_l, ridge_r = (xl+1.1,y,z+rise), (xr-1.1,y,z+rise)
    m.face([(xl,yf,z),(xr,yf,z),ridge_r,ridge_l], "roof")
    m.face([(xr,yb,z),(xl,yb,z),ridge_l,ridge_r], "roof_light")
    m.face([(xl,yb,z),(xl,yf,z),ridge_l], "roof")
    m.face([(xr,yf,z),(xr,yb,z),ridge_r], "roof")
    m.beam(ridge_l, ridge_r, .36, "bronze")
    m.beam((xl,yf,z),(xr,yf,z),.44,"bronze")
    m.beam((xl,yb,z),(xr,yb,z),.44,"bronze")
    for i in range(1, max(2, int(w/3))):
        xx=xl+w*i/max(2,int(w/3))
        for yy in (yf,yb):
            m.beam((xx,yy,z+.08),(xx,y,z+rise+.08),.13,"steel_light")
    # Staggered slate courses are actual thin, slightly raised strips.
    for k in range(1,5):
        u=k/5
        for sign in (-1,1):
            yy=y+sign*d*.5*(1-u)
            m.beam((xl+.2,yy,z+rise*u+.04),
                   (xr-.2,yy,z+rise*u+.04),.08,"roof_light")


def _barracks(m, x, y, w, d, h=13, z=12):
    m.cube((x,y,z+h/2),(w,d,h),"basalt")
    m.cube((x,y,z+1.0),(w+.7,d+.7,1.6),"basalt_light")
    m.cube((x,y,z+h-.25),(w+.65,d+.65,.7),"bronze")
    rise=7.2 if h>=19 else 5.8
    _roof(m,x,y,z+h,w+1.8,d+1.8,rise)
    cols=max(2,int(w/4.1))
    for side in (-1,1):
        yy=y+side*(d/2+.06)
        rot=0 if side<0 else math.pi
        for i in range(cols):
            xx=x-w/2+w*(i+.5)/cols
            for level in range(4,max(9,int(h)-1),5):
                _window(m,xx,yy,z+level,1.15,2.25,rot,
                        lit=((i+int(level)+int(x))%6!=0))
        # Pilaster/buttress cadence prevents long plain box walls.
        for i in range(cols+1):
            xx=x-w/2+w*i/cols
            m.cube((xx,y+side*(d/2+.45),z+h*.45),(.65,.9,h*.9),"basalt_light")
    # Narrow gable windows remain visible from the reverse view.
    for side in (-1,1):
        xx=x+side*(w/2+.07)
        rot=-math.pi/2 if side<0 else math.pi/2
        for yy in (y-d*.23,y+d*.23):
            _window(m,xx,yy,z+6.8,1.0,2.8,rot)
    # Chimneys and roof maintenance vents break the skyline.
    for xx in (x-w*.28,x+w*.28):
        m.cube((xx,y+1.0,z+h+rise-.3),(1.5,1.5,4.5),"basalt_light")
        m.cube((xx,y+1.0,z+h+rise+2),(2.1,2.1,.45),"bronze")
        for side in (-1,1):
            yy=y+side*d*.29
            # Dormers are small occupied rooms, with their own pitched roofs.
            m.cube((xx,yy,z+h+rise*.42),(3.3,2.5,3.0),"basalt_light")
            _roof(m,xx,yy,z+h+rise*.42+1.5,3.8,3.0,1.8)
            _window(m,xx,yy+side*1.3,z+h+rise*.42,.85,1.3,
                    0 if side<0 else math.pi)


def _terrace(m,x,y,w,d,z):
    """Clipped-corner retaining foundation and an occupied upper guardwalk."""
    cut=min(w,d)*.14
    outline=[(x-w/2+cut,y-d/2),(x+w/2-cut,y-d/2),
             (x+w/2,y-d/2+cut),(x+w/2,y+d/2-cut),
             (x+w/2-cut,y+d/2),(x-w/2+cut,y+d/2),
             (x-w/2,y+d/2-cut),(x-w/2,y-d/2+cut)]
    m.face([(xx,yy,z) for xx,yy in outline],"basalt_light")
    for i,a in enumerate(outline):
        b=outline[(i+1)%len(outline)]
        m.face([(a[0],a[1],0),(b[0],b[1],0),(b[0],b[1],z),(a[0],a[1],z)],"basalt")
        m.beam((a[0],a[1],z-.4),(b[0],b[1],z-.4),.65,"bronze")
        length=math.hypot(b[0]-a[0],b[1]-a[1])
        nx,ny=(b[1]-a[1])/length,-(b[0]-a[0])/length
        sections=max(1,int(length/7))
        for k in range(sections+1):
            t=k/sections; xx=a[0]+(b[0]-a[0])*t; yy=a[1]+(b[1]-a[1])*t
            m.beam((xx+nx*1.3,yy+ny*1.3,1),
                   (xx,yy,z-.5),1.0,"basalt_light")
            m.cube((xx,yy,z+1.1),(1.45,1.45,2.2),"basalt")
        m.beam((a[0],a[1],z+.6),(b[0],b[1],z+.6),.27,"steel_light")
    # Fine paving joints preserve scale on the wide upper service platform.
    for xx in range(int(x-w*.38),int(x+w*.38),5):
        m.beam((xx,y-d*.38,z+.035),(xx,y+d*.38,z+.035),.07,"steel")
    for yy in range(int(y-d*.38),int(y+d*.38),5):
        m.beam((x-w*.38,yy,z+.035),(x+w*.38,yy,z+.035),.07,"steel")


def _flank_works(m,beacons):
    """Occupied side terraces remain readable when the volcano masks the keep.

    The central mountain is deliberately untouched: new foundations wrap its
    eastern/western foot instead of putting architecture through the crater.
    """
    _terrace(m,-138,9,65,166,18)
    _terrace(m,143,28,64,145,20)
    for args in [(-139,-30,41,23,23,18),(-137,14,29,22,28,18),
                 (-137,80,42,19,24,18),(139,24,33,22,27,20),
                 (140,70,36,20,23,20),(111,24,20,18,19,20)]:
        _barracks(m,*args)
    # Tall peripheral watchtowers give the reverse silhouette identifiable
    # architecture rather than isolated amber dots behind the dormant cone.
    _tower(m,-160,14,18,w=13,d=15,h=47,beacons=beacons)
    _tower(m,-126,91,18,w=14,d=14,h=44,beacons=beacons)
    _tower(m,164,47,20,w=13,d=15,h=49,beacons=beacons)
    _tower(m,125,91,20,w=13,d=13,h=41,beacons=beacons)
    # Two stepped rear curtain sections stop at the mountain's natural wall.
    for x in (-142,144):
        m.cube((x,96,9),(47,5,18),"basalt")
        m.cube((x,96,27),(47,3.5,18),"basalt")
        m.cube((x,94.1,34.8),(47,.45,.7),"bronze")
        m.cube((x,97.9,34.8),(47,.45,.7),"bronze")
        for k in range(9):
            xx=x-22+k*5.5
            m.cube((xx,96,37),(2,4.2,3),"basalt_light")
            m.beam((xx,99.2,18),(xx,97.3,34),.8,"steel_light")
        for xx in (x-15,x,x+15):
            _window(m,xx,97.9,29,1.0,2.6,math.pi)
    # Broad solid stairs connect the lower road to each higher platform.
    for sx,top in ((-1,18),(1,20)):
        xx=sx*137
        for i in range(13):
            height=(top-12)*(i+1)/13
            m.cube((xx,-64+i*.8,12+height/2),(10,.85,height),"basalt_light")
        for side in (-1,1):
            m.beam((xx+side*5,-65,13.8),(xx+side*5,-54,top+1.8),.24,"bronze")
    # Repeated buttressed arcades along the east/west lower retaining walls
    # provide a useful architectural rhythm from the broadside checkpoints.
    for side in (-1,1):
        xx=side*172
        for yy in range(-28,77,13):
            rot=-math.pi/2 if side<0 else math.pi/2
            _window(m,xx,yy,10,4.1,7.4,rot,lit=False)
            _arch(m,xx,yy,5.5,4.5,8,.3,"bronze",rot)


def _tower(m, x,y,z,w=12,d=12,h=35,beacons=None,banner=True):
    m.cube((x,y,z+h/2),(w,d,h),"basalt")
    m.cube((x,y,z+1.5),(w+2.0,d+2.0,3),"basalt_light")
    for level in (h*.25,h*.59,h-.5):
        m.cube((x,y,z+level),(w+.75,d+.75,.55),"bronze")
    # Four tapering external buttresses and gold corner capitals.
    for sx in (-1,1):
        for sy in (-1,1):
            xx,yy=x+sx*w/2,y+sy*d/2
            m.cube((xx,yy,z+h*.40),(1.6,1.6,h*.8),"basalt_light")
            m.cube((xx,yy,z+h*.80),(1.1,1.1,h*.18),"steel_light")
            m.cube((xx,yy,z+h+.4),(1.8,1.8,2.2),"bronze")
            m.cone((xx,yy,z+h+2.7),1.2,.13,3.2,"roof",segments=4)
    # Fine crenels rather than a solid roof slab.
    m.cube((x,y,z+h),(w+1,d+1,.8),"steel_light")
    for i in range(5):
        t=-.5+i/4
        for side in (-1,1):
            m.cube((x+t*w,y+side*d/2,z+h+1.0),(1.25,1.25,2.0),"basalt")
            m.cube((x+side*w/2,y+t*d,z+h+1.0),(1.25,1.25,2.0),"basalt")
    for side in (-1,1):
        for level in (h*.28,h*.54,h*.80):
            _window(m,x,y+side*(d/2+.08),z+level,1.4,2.8,
                    0 if side<0 else math.pi)
            _window(m,x+side*(w/2+.08),y,z+level,1.2,2.8,
                    -math.pi/2 if side<0 else math.pi/2)
        if banner:
            _banner(m,x+side*w*.26,y-d/2-.21,z+h*.58,2.4,h*.41)
            _banner(m,x+side*w*.26,y+d/2+.21,z+h*.58,2.4,h*.41,math.pi)
    if beacons is not None:
        zz=z+h+2.6
        m.cylinder((x,y,zz),1.15,2.1,"steel",segments=12)
        m.cylinder((x,y,zz+1.5),.72,1.4,"beacon",segments=12)
        m.cone((x,y,zz+2.4),1.1,.1,.8,"bronze",segments=12)
        beacons.append((x,y,zz+1.5))


def _gate(m, x,y,z,beacons,rotation=0):
    """Twin towers flank a genuinely empty passage, never a black painted door."""
    c,s=math.cos(rotation),math.sin(rotation)
    def p(u,v,zz):
        return x+u*c-v*s,y+u*s+v*c,zz
    for side in (-1,1):
        xx,yy,_=p(side*11,0,z)
        _tower(m,xx,yy,z,10,12,32,beacons)
    # The high bridge between towers leaves the lower central lane open.
    m.cube(p(0,0,z+26),(13,12,7),"basalt",rotation_z=rotation)
    for side in (-1,1):
        ax,ay,_=p(0,side*6.1,z)
        _arch(m,ax,ay,z,12,24,.8,"bronze",rotation)
    for side in (-1,1):
        for k in range(4):
            m.cube(p(side*6.2,0,z+3+k*4),(1,12,1),"bronze",rotation_z=rotation)
    m.cube(p(0,0,z+.05),(14,17,.15),"steel",rotation_z=rotation)


def _reservoir(m,x=110,y=-43,z=12,r=33,beacons=None):
    # An open reinforced ember basin: centre is visible from every orbit angle.
    m.cylinder((x,y,z+3),r+3,6,"basalt",segments=64)
    m.cylinder((x,y,z+8),r,10,"steel",segments=64)
    m.cylinder((x,y,z+13.1),r-2,.18,"ember",segments=64)
    for zz,rr,minor in ((z+3,r+3,.8),(z+11.9,r+1.1,1.0),(z+14,r+.4,.7)):
        m.torus((x,y,zz),rr,minor,"bronze",segments=64,sides=6)
    # Segmented rim panels, massive radial external braces and narrow guardwalk.
    for i in range(24):
        a=math.tau*i/24
        ca,sa=math.cos(a),math.sin(a)
        xx,yy=x+(r+1)*ca,y+(r+1)*sa
        m.cube((xx,yy,z+7),(1.3,3.1,13),"basalt_light",rotation_z=a)
        m.beam((x+(r+5)*ca,y+(r+5)*sa,z),
               (x+(r+.5)*ca,y+(r+.5)*sa,z+12),.9,"steel_light")
        m.cylinder((x+(r+1.6)*ca,y+(r+1.6)*sa,z+15),.3,3,"steel",segments=6)
        m.beam((x+(r+1.6)*ca,y+(r+1.6)*sa,z+16.4),
               (x+(r+1.6)*math.cos(a+math.tau/24),
                y+(r+1.6)*math.sin(a+math.tau/24),z+16.4),.16,"bronze")
        if i%4==0:
            _banner(m,xx,yy,z+7,2.2,8,a+math.pi/2)
    # Bright veins/ripples across the aether surface read as suspended energy.
    for k in range(7):
        rr=4+k*3.6
        m.torus((x+math.sin(k)*1.6,y+math.cos(k)*1.6,z+13.22),
                rr,.16,"ember_hot",segments=36,sides=4)
    for i in range(28):
        a=i*2.39996
        rr=5+(i%8)*3
        zz=z+13.6+(i%5)*.45
        m.cone((x+rr*math.cos(a),y+rr*math.sin(a),zz),.34,.05,1.1,
               "ember_hot",segments=5)
    for i in range(4):
        a=i*math.pi/2+.3
        xx,yy=x+(r+2)*math.cos(a),y+(r+2)*math.sin(a)
        m.cylinder((xx,yy,z+17.5),.55,1.9,"beacon",segments=8)
        if beacons is not None:
            beacons.append((xx,yy,z+17.7))


def _extraction(m):
    # Four braced legs form a visibly hollow extraction gantry on the flank.
    centre=(40,52)
    for sx in (-1,1):
        for sy in (-1,1):
            xx,yy=centre[0]+sx*12,centre[1]+sy*10
            m.beam((xx,yy,36),(centre[0]+sx*7,centre[1]+sy*6,91),1.6,"steel")
            m.cube((xx,yy,36),(5,5,2),"basalt_light")
    for zz in (47,60,74,88):
        for sy in (-1,1):
            yy=centre[1]+sy*9
            m.beam((centre[0]-11,yy,zz),(centre[0]+11,yy,zz),.7,"bronze")
            m.beam((centre[0]-11,yy,zz-10),(centre[0]+11,yy,zz),.55,"steel_light")
            m.beam((centre[0]+11,yy,zz-10),(centre[0]-11,yy,zz),.55,"steel_light")
        for sx in (-1,1):
            xx=centre[0]+sx*10
            m.beam((xx,centre[1]-9,zz),(xx,centre[1]+9,zz),.7,"bronze")
    m.cylinder((centre[0],centre[1],69),7,32,"steel",segments=16)
    for zz in (53,59,70,81,86):
        m.torus((centre[0],centre[1],zz),7.6,.75,"bronze",segments=24,sides=5)
    for i in range(8):
        a=math.tau*i/8
        xx,yy=centre[0]+7.12*math.cos(a),centre[1]+7.12*math.sin(a)
        m.beam((xx,yy,55),(xx,yy,83),.33,"ember")
    # Two massive, flange-jointed conduits arc down into the circular basin.
    for side in (-1,1):
        points=[(40+side*5,48,78),(57+side*5,39,75),(75+side*5,22,63),
                (88+side*5,3,48),(99+side*5,-15,36),(108+side*5,-29,28)]
        for a,b in zip(points,points[1:]):
            m.beam(a,b,4.2,"steel")
            # Three fine orange external aether channels follow each pipe.
            for dx in (-1.0,0,1.0):
                m.beam((a[0]+dx,a[1]-.35,a[2]+2.15),
                       (b[0]+dx,b[1]-.35,b[2]+2.15),.25,"ember")
        for xx,yy,zz in points:
            m.cube((xx,yy,zz),(5.2,5.2,1.2),"bronze")
        for xx,yy,zz in points[1:-1]:
            m.beam((xx,yy,14),(xx,yy,zz-2),1.0,"steel_light")
            m.beam((xx-3,yy-3,14),(xx,yy,zz-2),.5,"steel")


def build_fortress(m, beacons):
    """Add the approved fortress, its two gatehouses and harvesting machinery."""
    rng=random.Random(16243)
    # An irregular military terrace, not one rectangular building footprint.
    m.cube((-5,-33,10),(220,124,3),"basalt")
    m.cube((100,-40,10),(96,98,3),"basalt")
    # South curtain wall is divided by gate opening at x=-40.
    for lo,hi in ((-129,-56),(-24,142)):
        mid=(lo+hi)/2
        m.cube((mid,-102,17), (hi-lo,4,14), "basalt")
        m.cube((mid,-104.1,23.7),(hi-lo,.6,.65),"bronze")
        for xx in range(int(lo)+3,int(hi),7):
            m.cube((xx,-102,25),(2.4,4.6,3.4),"basalt_light")
            m.beam((xx,-106,11),(xx,-104,22),.8,"steel_light")
    # Elevated inner road and stairs to barracks level, with black steel drains.
    m.cube((-38,-86,12),(21,39,.4),"steel")
    for xx in (-49,-27):
        m.beam((xx,-107,13),(xx,-66,13),.25,"bronze")
    for i in range(16):
        m.cube((-38,-105+i*2.4,12.25),(19,.14,.1),"steel_light")
    # Main keep retains the tall centre-front silhouette of the approved image.
    # Elevated command terrace matches the approved keep's higher eastern
    # silhouette.  The full plinth and entrance stair support the raised body.
    m.cube((8,-53,19),(28,28,14),"basalt")
    m.cube((8,-53,12.75),(31,31,1.5),"basalt_light")
    m.cube((8,-53,25.5),(30,30,1),"bronze")
    for sx in (-1,1):
        for sy in (-1,1):
            m.beam((8+sx*15,-53+sy*15,12),
                   (8+sx*12,-53+sy*12,35),1.3,"basalt_light")
    for i in range(14):
        height=i+1
        m.cube((8,-81+i,12+height/2),(9,1.05,height),"basalt_light")
    for side in (-1,1):
        m.beam((8+side*4.8,-81,13.8),(8+side*4.8,-67,27.8),
               .24,"bronze")
    _tower(m,8,-53,26,w=24,d=24,h=57,beacons=beacons)
    m.cube((8,-53,84.5),(20,20,2.3),"bronze")
    _tower(m,8,-53,85,w=10,d=10,h=15,beacons=None,banner=False)
    m.cone((8,-53,103),5.6,.3,6,"roof",segments=4)
    # Companion watchtower and rear command bastion are visible after orbit.
    _tower(m,-72,-35,12,w=13,d=15,h=36,beacons=beacons)
    _tower(m,58,-4,12,w=17,d=17,h=42,beacons=beacons)
    _gate(m,-40,-115,12,beacons)
    _gate(m,-140,50,12,beacons,rotation=math.pi/2)
    # Long, pitched-roof buildings make the settlement feel occupied and large.
    for args in [(-80,-63,42,18,19),(-91,-8,40,19,22),
                 (-53,13,35,16,20),(29,-72,31,18,18),
                 (50,-43,27,17,21),(84,-1,27,15,18),
                 (-115,26,27,17,18),(10,9,27,17,19),
                 (21,-17,25,16,17)]:
        _barracks(m,*args)
    _flank_works(m,beacons)
    _reservoir(m,beacons=beacons)
    _extraction(m)
    # Dockside arches stand in actual depth under the south terrace.
    for xx in range(-122,145,13):
        if -59<xx<-20:
            continue
        m.cube((xx,-108,7),(2.2,8,12),"basalt_light")
        _arch(m,xx+5.5,-108,1,8.8,10,1,"steel_light")
    # Small service cranes, crate stacks, vents, and taut pipe racks keep yards
    # inhabited without introducing any protagonist before the later shots.
    for xx,yy in ((-60,-88),(15,-87),(58,-72),(-114,7)):
        m.beam((xx,yy,12),(xx,yy,25),.55,"steel")
        m.beam((xx,yy,25),(xx+7,yy,25),.5,"steel_light")
        m.beam((xx,yy,19),(xx+7,yy,25),.3,"bronze")
        m.beam((xx+6,yy,25),(xx+6,yy,16),.1,"black")
        for j in range(3):
            m.cube((xx+4+j*1.9,yy+2,13),(1.7,1.7,2),"basalt_light")
            m.cube((xx+4+j*1.9,yy+2,13),(1.9,.18,2.1),"bronze")
    # Pipe racks on the terrace are restrained, weathered and spatially fixed.
    for yy in (-88,-83):
        m.beam((39,yy,13.1),(80,yy,13.1),.7,"steel_light")
        for xx in range(40,80,5):
            m.cube((xx,yy,12.4),(1,1,1.4),"basalt")
    # Bolted panels and warm recessed vents around the reservoir service hall.
    for xx in range(73,144,7):
        for zz in (16,20):
            m.cube((xx,-90,zz),(3,.16,1.4),"black")
            for k in range(3):
                m.cube((xx-1+k,-90.13,zz),(.12,.12,1.2),"bronze")
    # Fine roadway markings and settled loading pallets contribute close-shot
    # scale; do not block either centreline or put a crown actor in this shot.
    for i in range(24):
        xx=rng.uniform(-118,75)
        yy=rng.uniform(-88,22)
        if abs(xx+38)<15:
            continue
        m.cube((xx,yy,12.55),(rng.uniform(1,2),rng.uniform(1,2),.5),"steel")
