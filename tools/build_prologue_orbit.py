#!/usr/bin/env python3
"""Rebuild the spatial Fire Veinhold continuation with Blender 4.3+.

Run ``python tools/build_prologue_orbit.py --preview`` for composition proofs,
then ``python tools/build_prologue_orbit.py --render`` for the complete bank.
Every viewpoint is rendered from the saved shared scene; no image interpolation
or independently generated perspective paintings are used.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import random
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/cinematics/fire_veinhold/continuation'
DEST = ROOT/'assets/story/fire_veinhold_opening/continuation'
WIDTH, HEIGHT = 960, 640


def prepare_projection_plate():
    from PIL import Image
    folder=SOURCE/'materials'; folder.mkdir(parents=True,exist_ok=True)
    source=ROOT/'assets/story/fire_veinhold_opening/shot01/environment/panorama.png'
    factor=960/1024*1.035
    for source,dest in ((source,folder/'approved_projection.png'),(ROOT/'assets/source/cinematics/fire_veinhold/shot01/environment/cinder_bridges_generated.png',folder/'orbit_000_terrain.png')):
        if dest.exists(): continue
        image=Image.open(source).convert('RGB'); resized=image.resize((round(image.width*factor),round(image.height*factor)),Image.Resampling.BICUBIC)
        left=(resized.width-960)//2; top=round(50*factor)
        resized.crop((left,top,left+960,top+640)).save(dest)


def finish_exports(args):
    from PIL import Image, ImageDraw
    if args.preview:
        prefix='base' if args.base_only else 'preview'
        paths=[SOURCE/f'{prefix}_orbit_{int(i):04d}.png' for i in args.proof_frames.split(',') if i]
        paths.extend(SOURCE/f'{prefix}_rush_{int(i):04d}.png' for i in args.rush_proof_frames.split(',') if i)
        paths=[p for p in paths if p.exists()]
        sheet=Image.new('RGB',(960,math.ceil(len(paths)/2)*350),(8,14,29)); draw=ImageDraw.Draw(sheet)
        for i,path in enumerate(sorted(paths)):
            image=Image.open(path); image.thumbnail((480,320)); x=(i%2)*480; y=(i//2)*350
            sheet.paste(image,(x,y)); draw.text((x+8,y+323),path.stem,fill=(210,225,242))
        sheet.save(SOURCE/'camera_contact_sheet.png')
        return
    if not args.render: return
    manifest=json.loads((DEST/'manifest.json').read_text())
    for segment,record in manifest['segments'].items():
        if args.segment not in ('all',segment): continue
        rows=json.loads((DEST/record['metadata_path']).read_text())
        for i,row in enumerate(rows):
            if not args.start<=i<args.stop: continue
            path=DEST/record['frames'][i]
            if not path.exists(): continue
            # Beauty exports stay sharp. Runtime owns optional movement lines
            # and blur so reduced-motion playback can use the same bank.
            alarm=Image.new('RGBA',(WIDTH,HEIGHT)); drawing=ImageDraw.Draw(alarm)
            for x,y,r in row['alarm_points']:
                for j in range(7,0,-1):
                    radius=r*j/2.2; alpha=int(100*(1-j/8)**2)
                    drawing.ellipse((x-radius,y-radius,x+radius,y+radius),fill=(255,18,11,alpha))
                drawing.ellipse((x-r*.3,y-r*.3,x+r*.3,y+r*.3),fill=(255,78,42,245))
            alarm.save(DEST/record['alarm_frames'][i],compress_level=6)
    # .blend backups are build byproducts, not another scene authority.
    backup=SOURCE/'fire_veinhold_continuation.blend1'
    if backup.exists(): backup.unlink()


def check_exports():
    from PIL import Image
    manifest=json.loads((DEST/'manifest.json').read_text())
    expected={'orbit':301,'rush':61,'alarm_hold':16,'reveal':16}
    count=0
    for key,n in expected.items():
        record=manifest['segments'][key]; assert len(record['frames'])==len(record['alarm_frames'])==n,key
        rows=json.loads((DEST/record['metadata_path']).read_text()); assert len(rows)==n
        for filename in record['frames']+record['alarm_frames']:
            path=DEST/filename
            with Image.open(path) as image:
                assert image.size==(WIDTH,HEIGHT),(filename,image.size)
                if '/alarm_' in filename: assert image.mode=='RGBA',filename
                image.verify()
            count+=1
        assert all(math.isfinite(x) for r in rows for x in r['camera']['position'])
        if key=='orbit':
            angles=[r['camera']['orbit_degrees'] for r in rows]
            assert abs(angles[0])<1e-8 and abs(angles[-1]-180)<1e-8
            assert all(a<b for a,b in zip(angles,angles[1:]))
            assert len({tuple(r['camera']['position']) for r in rows})==301
        if key in ('orbit','rush'):
            assert all(abs(r['time_seconds']-i/60)<1e-8 for i,r in enumerate(rows))
    config=json.loads((SOURCE/'scene_config.json').read_text())
    assert config['mainland_landing_to_final_camera_metres']==6.096
    assert len(config['guards'])==4
    assert len({guard['pose'] for guard in config['guards']})==4
    assert config['bridges'][0]['start'][1]<0
    assert config['bridges'][1]['start'][0]<0 and config['bridges'][1]['start'][1]>0
    reveal=json.loads((DEST/manifest['segments']['reveal']['metadata_path']).read_text())
    start,end=config['bridges'][0]['start'],config['bridges'][0]['end']; camera=reveal[0]['camera']['position']
    dx,dy=end[0]-start[0],end[1]-start[1]; length=math.hypot(dx,dy)
    along=((camera[0]-start[0])*dx+(camera[1]-start[1])*dy)/length
    lateral=abs((camera[0]-start[0])*dy-(camera[1]-start[1])*dx)/length
    assert abs(along-6.096)<.001 and lateral<.001,(along,lateral)
    print(f'Validated {count} native images, 301 orbit / 61 rush geometry perspectives, four guards and both bridge identities.')
    return 0


def write_recipe():
    def entry(path):
        return {'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size}
    manifest=json.loads((DEST/'manifest.json').read_text())
    runtime={}
    for segment,record in manifest['segments'].items():
        for filename in record['frames']+record['alarm_frames']+[record['metadata_path']]:
            path=DEST/filename; runtime[filename]=entry(path)
    inputs=[Path(__file__),ROOT/'tools/prologue_orbit_architecture.py',ROOT/'tools/prologue_orbit_projection.py',ROOT/'assets/story/fire_veinhold_opening/shot01/environment/panorama.png']
    inputs.extend(sorted((SOURCE/'materials').glob('*.png')))
    inputs.extend(sorted((SOURCE/'materials').glob('*.json')))
    inputs.extend(sorted((SOURCE/'materials').glob('*.txt')))
    guard_exporter=ROOT/'tools/export_frozen_guard_layers.py'
    if guard_exporter.exists(): inputs.append(guard_exporter)
    inputs.extend(ROOT/f'assets/story/fire_veinhold_opening/shot01/environment/plume_{i:02d}.png' for i in range(1,17))
    record={'version':1,'command':'python tools/build_prologue_orbit.py --render --samples 16','renderer':'Blender 4.3 Cycles CPU, deterministic painted surface pass','render_size':[WIDTH,HEIGHT],'segments':{name:len(data['frames']) for name,data in manifest['segments'].items()},'source_inputs':{str(path.relative_to(ROOT)):entry(path) for path in inputs},'packed_blend':entry(SOURCE/'fire_veinhold_continuation.blend'),'scene_config':entry(SOURCE/'scene_config.json'),'runtime_assets':runtime}
    (SOURCE/'export_recipe.json').write_text(json.dumps(record,indent=2)+'\n')
    print(f'Wrote reproducible export recipe with {len(runtime)} image/camera hashes.')


def parse_args():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--preview', action='store_true')
    parser.add_argument('--render', action='store_true')
    parser.add_argument('--start', type=int, default=0)
    parser.add_argument('--stop', type=int, default=301)
    parser.add_argument('--segment', choices=('orbit', 'rush', 'alarm_hold', 'reveal', 'all'), default='all')
    parser.add_argument('--samples', type=int, default=16)
    parser.add_argument('--scale', type=float, default=1.)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--base-only', action='store_true')
    parser.add_argument('--proof-frames', default='0,23,53,98,150,202,300')
    parser.add_argument('--rush-proof-frames', default='30,60')
    parser.add_argument('--write-recipe', action='store_true')
    parser.add_argument('--patch-continuation', action='store_true')
    parser.add_argument('--blender', default='/usr/bin/blender')
    args = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]
    return parser.parse_args(args)


def main():
    args = parse_args()
    try:
        import bpy
    except ImportError:
        if args.check:
            return check_exports()
        if args.write_recipe:
            write_recipe()
            return 0
        prepare_projection_plate()
        command = [args.blender, '--background', '--factory-startup', '--threads', '8', '--python', __file__, '--', *sys.argv[1:]]
        environment=dict(os.environ, MESA_SHADER_CACHE_DIR='/tmp/veinhold-mesa-shader-cache', LP_NUM_THREADS='5')
        result=subprocess.call(command, cwd=ROOT, env=environment)
        if result==0: finish_exports(args)
        return result
    build(bpy, args)
    return 0


class MeshBatch:
    def __init__(self, materials):
        self.verts, self.faces, self.indices = [], [], []
        self.materials = materials
        self.names = list(materials)

    def face(self, points, material):
        offset = len(self.verts)
        self.verts.extend(tuple(p) for p in points)
        self.faces.append(tuple(range(offset, len(self.verts))))
        self.indices.append(self.names.index(material))

    def cube(self, center, scale, material, rotation_z=0):
        x, y, z = center; w, d, h = (s/2 for s in scale)
        c, s = math.cos(rotation_z), math.sin(rotation_z)
        offset = len(self.verts)
        for a, b, k in ((-w,-d,-h),(w,-d,-h),(w,d,-h),(-w,d,-h),(-w,-d,h),(w,-d,h),(w,d,h),(-w,d,h)):
            self.verts.append((x+a*c-b*s,y+a*s+b*c,z+k))
        for face in ((0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)):
            self.faces.append(tuple(offset+i for i in face)); self.indices.append(self.names.index(material))

    def cylinder(self, center, radius, depth, material, segments=12):
        self.cone(center, radius, radius, depth, material, segments)

    def cone(self, center, radius1, radius2, depth, material, segments=12):
        x,y,z = center; offset = len(self.verts)
        for r,h in ((radius1,-depth/2),(radius2,depth/2)):
            self.verts.extend((x+r*math.cos(i*math.tau/segments),y+r*math.sin(i*math.tau/segments),z+h) for i in range(segments))
        self.faces.extend((tuple(offset+i for i in reversed(range(segments))),tuple(offset+segments+i for i in range(segments))))
        self.indices.extend([self.names.index(material)]*2)
        for i in range(segments):
            j=(i+1)%segments
            self.faces.append((offset+i,offset+j,offset+segments+j,offset+segments+i)); self.indices.append(self.names.index(material))

    def beam(self, a, b, width, material):
        from mathutils import Vector
        av,bv = Vector(a),Vector(b); direction=(bv-av).normalized()
        other=Vector((0,0,1)) if abs(direction.z)<.95 else Vector((1,0,0))
        u=direction.cross(other).normalized()*width/2; v=direction.cross(u).normalized()*width/2
        offset=len(self.verts)
        self.verts.extend(tuple(p+i*u+j*v) for p in (av,bv) for i,j in ((-1,-1),(1,-1),(1,1),(-1,1)))
        for face in ((0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)):
            self.faces.append(tuple(offset+i for i in face)); self.indices.append(self.names.index(material))

    def torus(self, center, major_radius, minor_radius, material, segments=32, sides=6):
        x,y,z=center; offset=len(self.verts)
        for i in range(segments):
            a=i*math.tau/segments
            for j in range(sides):
                b=j*math.tau/sides; r=major_radius+minor_radius*math.cos(b)
                self.verts.append((x+r*math.cos(a),y+r*math.sin(a),z+minor_radius*math.sin(b)))
        for i in range(segments):
            for j in range(sides):
                self.faces.append((offset+i*sides+j,offset+((i+1)%segments)*sides+j,offset+((i+1)%segments)*sides+(j+1)%sides,offset+i*sides+(j+1)%sides)); self.indices.append(self.names.index(material))

    def finish(self, bpy, name):
        mesh=bpy.data.meshes.new(name); mesh.from_pydata(self.verts,[],self.faces); mesh.update()
        obj=bpy.data.objects.new(name,mesh); bpy.context.collection.objects.link(obj)
        for material in self.materials.values(): mesh.materials.append(material)
        for polygon,index in zip(mesh.polygons,self.indices): polygon.material_index=index
        return obj


def build(bpy, args):
    from mathutils import Vector
    from bpy_extras.object_utils import world_to_camera_view
    sys.path.insert(0,str(ROOT/'tools'))
    SOURCE.mkdir(parents=True,exist_ok=True); DEST.mkdir(parents=True,exist_ok=True)
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
    random.seed(307)
    scene=bpy.context.scene
    base_collection=bpy.context.collection
    common_collection=bpy.data.collections.new('Shared vent-anchored drawn smoke')
    scene.collection.children.link(common_collection)
    scene.render.engine='CYCLES'
    scene.cycles.device='CPU'; scene.cycles.samples=args.samples
    scene.cycles.seed=0; scene.cycles.use_animated_seed=False
    scene.cycles.use_denoising=False
    scene.cycles.max_bounces=4; scene.cycles.transparent_max_bounces=6
    scene.render.resolution_x=WIDTH; scene.render.resolution_y=HEIGHT
    scene.render.resolution_percentage=round(args.scale*100)
    scene.render.image_settings.file_format='PNG'; scene.render.image_settings.color_mode='RGB'; scene.render.image_settings.compression=25
    scene.render.fps=60
    scene.render.film_transparent=True
    scene.world.color=(.009,.018,.055)
    scene.world.use_nodes=True
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.014,.032,.085,1)
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.40
    scene.view_settings.view_transform='Standard'; scene.view_settings.look='Medium High Contrast'
    scene.view_settings.exposure=0; scene.view_settings.gamma=1

    def mat(name, color, metallic=.0, roughness=.7, emission=0, texture=True, alpha=1):
        m=bpy.data.materials.new(name); m.diffuse_color=(*color,alpha); m.use_nodes=True
        nodes=m.node_tree.nodes; links=m.node_tree.links; p=nodes.get('Principled BSDF')
        p.inputs['Base Color'].default_value=(*color,alpha); p.inputs['Metallic'].default_value=metallic; p.inputs['Roughness'].default_value=roughness
        p.inputs['Alpha'].default_value=alpha
        if emission:
            p.inputs['Emission Color'].default_value=(*color,1); p.inputs['Emission Strength'].default_value=emission
        if texture:
            tex=nodes.new('ShaderNodeTexNoise'); tex.inputs['Scale'].default_value=3.8; tex.inputs['Detail'].default_value=3; tex.inputs['Roughness'].default_value=.8
            ramp=nodes.new('ShaderNodeValToRGB'); ramp.color_ramp.interpolation='CONSTANT'
            ramp.color_ramp.elements.remove(ramp.color_ramp.elements[1])
            for n,(position,mult) in enumerate(((.0,.48),(.32,.74),(.52,1),(.7,1.34),(.85,1.7))):
                element=ramp.color_ramp.elements[0] if n==0 else ramp.color_ramp.elements.new(position)
                element.position=position; element.color=(*(min(.95,c*mult) for c in color),1)
            links.new(tex.outputs['Fac'],ramp.inputs['Fac']); links.new(ramp.outputs['Color'],p.inputs['Base Color'])
            bump=nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value=.17; bump.inputs['Distance'].default_value=.12
            links.new(tex.outputs['Fac'],bump.inputs['Height']); links.new(bump.outputs['Normal'],p.inputs['Normal'])
        return m

    materials={
        'basalt':mat('Midnight dressed basalt',(.075,.113,.175)),
        'basalt_light':mat('Moon-facing stone',(.18,.25,.34)),
        'steel':mat('Blue black forged iron',(.065,.115,.18),.58,.45),
        'steel_light':mat('Brushed blue steel',(.22,.32,.43),.58,.37),
        'bronze':mat('Weathered bronze',(.31,.20,.083),.55,.48),
        'bronze_light':mat('Gilt edge bronze',(.59,.41,.19),.63,.40),
        'roof':mat('Slate roof',(.065,.12,.19),.14),
        'roof_light':mat('Slate silver edging',(.24,.35,.47),.20),
        'window':mat('Steady warm windows',(.95,.48,.13),.12,emission=2.2,texture=False),
        'ember':mat('Contained fire aether',(.95,.24,.018),.1,emission=2.0),
        'ember_hot':mat('White gold aether',(.99,.65,.13),.05,emission=3.3,texture=False),
        'crimson':mat('Carcovian crimson',(.25,.025,.045)),
        'black':mat('Deep shadow',(.012,.021,.04),texture=False),
        'beacon':mat('Inactive red beacon glass',(.14,.013,.022),.25,.18,texture=False),
        'rock':mat('Blue mountain schist',(.16,.25,.37),.05),
        'rock_dark':mat('Shadow volcanic rock',(.065,.105,.17)),
        'rock_rust':mat('Dormant red volcanic terraces',(.29,.16,.15)),
        'snow':mat('Moonlit mineral seams',(.37,.48,.59)),
        'foam':mat('Breaking blue surf',(.22,.44,.63),emission=.25),
        'ice':mat('Translucent blue stasis',(.14,.47,.70),.16,.24,texture=False,alpha=.30),
        'ice_edge':mat('Ice silver crystalline edges',(.48,.80,.96),.23,.26,emission=.30),
        'skin':mat('Guard skin',(.41,.29,.24)),
        'leather':mat('Guard black leather',(.035,.040,.055)),
    }
    materials['stone']=materials['basalt']
    # Authored seamless paint textures preserve the approved navy/silver finish.
    texture_for={'rock':'schist','rock_dark':'schist','rock_rust':'schist','snow':'schist','basalt':'masonry','basalt_light':'masonry','steel':'steel','steel_light':'steel','roof':'masonry','roof_light':'masonry'}
    for key,filename in texture_for.items():
        path=SOURCE/'materials'/f'{filename}.png'
        if not path.exists(): continue
        material=materials[key]; nodes=material.node_tree.nodes; links=material.node_tree.links
        p=nodes.get('Principled BSDF'); image=nodes.new('ShaderNodeTexImage'); image.image=bpy.data.images.load(str(path),check_existing=True); image.interpolation='Linear'; image.projection='BOX'; image.projection_blend=.18
        coord=nodes.new('ShaderNodeTexCoord'); scale=nodes.new('ShaderNodeVectorMath'); scale.operation='SCALE'; scale.inputs['Scale'].default_value=.006 if filename=='schist' else .065
        links.new(coord.outputs['Object'],scale.inputs[0]); links.new(scale.outputs[0],image.inputs['Vector']); links.new(image.outputs['Color'],p.inputs['Base Color'])
        if key=='rock_rust':
            grey=nodes.new('ShaderNodeRGBToBW'); colors=nodes.new('ShaderNodeValToRGB')
            colors.color_ramp.elements[0].position=.025; colors.color_ramp.elements[0].color=(.045,.039,.055,1)
            colors.color_ramp.elements[1].position=.38; colors.color_ramp.elements[1].color=(.49,.28,.16,1)
            links.new(image.outputs['Color'],grey.inputs[0]); links.new(grey.outputs[0],colors.inputs[0]); links.new(colors.outputs[0],p.inputs['Base Color'])
        p.inputs['Roughness'].default_value=.84 if filename!='steel' else .47
    # The far Damar headland relief always uses this dedicated hand-painted
    # rock material. It never inherits a view plate's sky or distant water.
    materials['rock_damar']=materials['rock_rust'].copy()
    materials['rock_damar'].name='Damar headland dedicated rust schist'
    terrain=MeshBatch(materials); architecture=MeshBatch(materials); waterdetails=MeshBatch(materials)

    # A single rocky island with radial terraces and a recessed dormant crater.
    def island(cx,cy,rx,ry,height,volcanic=False,seed=5,material_override=None):
        rng=random.Random(seed); sectors=144; rings=40
        v=[]; f=[]; mi=[]
        jitter=[1+.042*math.sin(i*math.tau/sectors*7+seed)+.028*math.sin(i*math.tau/sectors*13+seed*.2) for i in range(sectors)]
        for r in range(rings+1):
            u=r/rings
            for i in range(sectors):
                a=i*math.tau/sectors; wobble=jitter[i]*(1+.04*math.sin(a*7))
                x=cx+math.cos(a)*rx*u*wobble; y=cy+math.sin(a)*ry*u*wobble
                if volcanic:
                    if cx==0 and cy==65:
                        # A broad 50 m shoulder supports a shorter upper cone,
                        # preserving the approved low caldera silhouette.
                        if u<.14: z=height*(.86+.04*math.sin(a*3))
                        elif u<.23: z=height*(1-.025*math.cos(a*4))
                        elif u<.70: z=height*(.40+.60*max(0,1-(u-.23)/.47)**1.2)
                        else: z=height*.40*max(0,(1-u)/.30)**.8
                        # The occupied military terrace cuts into its apron;
                        # houses and the road remain above their support plane.
                        if y<45 and -150<x<170: z=min(z,12+max(0,y-15)*1.4)
                    elif u<.20: z=height*(.86+.07*math.sin(a*3))
                    elif u<.29: z=height*(1-.05*math.cos(a*4))
                    else: z=height*max(0,(1-u)/.71)**1.65
                    z+=(math.sin(a*17+u*7)+.38*math.sin(a*33-u*13))*height*.035*math.sin(u*math.pi)
                else:
                    z=height*(max(0,1-u)**.65)+5*math.sin(a*4+u*11)*(1-u)
                if u>.92: z-=12*((u-.92)/.08)
                v.append((x,y,z))
        for r in range(rings):
            for i in range(sectors):
                j=(i+1)%sectors
                f.extend(((r*sectors+i,(r+1)*sectors+i,(r+1)*sectors+j),(r*sectors+i,(r+1)*sectors+j,r*sectors+j)))
                # Geological color follows coherent landforms. Periodic
                # sector/ring alternation creates conspicuous radial stripes.
                rock=material_override or ('rock_dark' if r<5 and volcanic else 'rock')
                mi.extend([terrain.names.index(rock)]*2)
        offset=len(terrain.verts); terrain.verts.extend(v); terrain.faces.extend(tuple(offset+p for p in face) for face in f); terrain.indices.extend(mi)
        # Cliff spurs and pale mineral strips give the shoreline an irregular outline.
        for i in range(75):
            a=rng.random()*math.tau; rr=rng.uniform(.82,1.04)
            x=cx+math.cos(a)*rx*rr; y=cy+math.sin(a)*ry*rr
            terrain.cone((x,y,1),rng.uniform(3,8),rng.uniform(0,2),rng.uniform(6,18),'rock',5)
        return (cx,cy,height)

    island(0,0,205,163,17,seed=17)
    island(0,65,145,125,127,True,29)
    island(720,4200,350,285,155,True,31)
    # Active island crater/fire contrasts with the depleted near volcano.
    architecture.cylinder((720,4200,145),65,1.4,'ember',40)
    architecture.torus((720,4200,149),67,2,'rock_rust',40,6)
    for k in range(8):
        a=k*.62
        architecture.beam((720+65*math.cos(a),4200+65*math.sin(a),146),(720+250*math.cos(a),4200+175*math.sin(a),15),1.8,'ember')
    for cx,cy,rx,ry,h,seed in ((-320,-325,170,130,9,41),(-480,-500,260,240,160,42)):
        island(cx,cy,rx,ry,h,seed=seed)
    island(-500,-1800,2200,1500,26,seed=46)
    island(-1000,2200,900,600,70,seed=47,material_override='rock_rust')
    for cx,cy,rx,ry,height,seed in ((-1450,2450,350,250,160,51),(-1120,2400,300,220,130,52),(-800,2400,250,200,180,53),(-500,2350,250,180,120,54)):
        island(cx,cy,rx,ry,height,seed=seed,material_override='rock_damar')
    # Continuous Merovaran mountain barrier visible after the reverse orbit.
    for i in range(12):
        island(-700+i*130,-1100+(i%3)*45,125,95,105+(i*37)%120,False,100+i)
    for i in range(9):
        island(120+i*75,200+i*21,18+i%3*4,13,8+i%4*3,False,180+i)

    # Water: bands of silver-blue wavelets, fine roughness and a single surface.
    water=mat('Night sea',(.015,.09,.18),.34,.25,texture=False)
    p=water.node_tree.nodes.get('Principled BSDF'); nodes=water.node_tree.nodes; links=water.node_tree.links
    tex=nodes.new('ShaderNodeTexNoise'); tex.inputs['Scale'].default_value=1.7; tex.inputs['Detail'].default_value=3.5; tex.inputs['Roughness'].default_value=.8
    coord=nodes.new('ShaderNodeTexCoord'); mapping=nodes.new('ShaderNodeVectorMath'); mapping.operation='MULTIPLY'; mapping.inputs[1].default_value=(.45,1.5,1)
    links.new(coord.outputs['Object'],mapping.inputs[0]); links.new(mapping.outputs[0],tex.inputs['Vector'])
    ramp=nodes.new('ShaderNodeValToRGB'); ramp.color_ramp.elements[0].position=.35; ramp.color_ramp.elements[0].color=(.008,.035,.085,1); ramp.color_ramp.elements[1].position=.72; ramp.color_ramp.elements[1].color=(.055,.20,.34,1)
    links.new(tex.outputs['Fac'],ramp.inputs[0]); links.new(ramp.outputs[0],p.inputs['Base Color'])
    bump=nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value=.26; bump.inputs['Distance'].default_value=.15; links.new(tex.outputs['Fac'],bump.inputs['Height']); links.new(bump.outputs['Normal'],p.inputs['Normal'])
    ocean_path=SOURCE/'materials/ocean.png'
    if ocean_path.exists():
        image=nodes.new('ShaderNodeTexImage'); image.image=bpy.data.images.load(str(ocean_path)); image.interpolation='Linear'; scaling=nodes.new('ShaderNodeVectorMath'); scaling.operation='SCALE'; scaling.inputs['Scale'].default_value=.0019
        links.new(coord.outputs['Object'],scaling.inputs[0]); links.new(scaling.outputs[0],image.inputs['Vector']); links.new(image.outputs['Color'],p.inputs['Base Color']); p.inputs['Roughness'].default_value=.7; bump.inputs['Strength'].default_value=.08
    bpy.ops.mesh.primitive_plane_add(size=15000,location=(0,0,-1)); bpy.context.object.name='Continuous night ocean'; bpy.context.object.data.materials.append(water)
    rng=random.Random(44)
    for i in range(950):
        x=rng.uniform(-900,900); y=rng.uniform(-800,900)
        if (x/216)**2+(y/175)**2<1: continue
        waterdetails.cube((x,y,-.35),(rng.uniform(.8,4),rng.uniform(.12,.38),.05),'foam')
    for i in range(170):
        a=i*math.tau/170
        r=205+(i%4)*1.3
        waterdetails.cube((math.cos(a)*r,math.sin(a)*165,-.15),(2.5,.40,.06),'foam',a+math.pi/2)

    beacons=[]
    from prologue_orbit_architecture import build_fortress
    build_fortress(architecture,beacons)

    def bridge(start,end,width,name):
        av,bv=Vector(start),Vector(end); delta=bv-av; direction=delta.normalized(); normal=Vector((-direction.y,direction.x,0)); length=delta.length
        angle=math.atan2(direction.y,direction.x)
        architecture.cube(tuple((av+bv)/2),(length,width,1),'steel',angle)
        architecture.cube(tuple((av+bv)/2+Vector((0,0,.55))),(length,width-.8,.14),'basalt_light',angle)
        sections=math.ceil(length/13)
        for i in range(sections+1):
            c=av+delta*i/sections
            for side in (-1,1):
                p=c+normal*side*(width/2-.25)
                architecture.cube(tuple(p+Vector((0,0,1.05))),(.28,.28,2.1),'steel_light')
                architecture.cube(tuple(p+Vector((0,0,2.15))),(.55,.55,.20),'bronze')
                if i<sections:
                    q=av+delta*(i+1)/sections+normal*side*(width/2-.25)
                    architecture.beam(tuple(p+Vector((0,0,1.2))),tuple(q+Vector((0,0,1.2))),.19,'steel')
                    architecture.beam(tuple(p+Vector((0,0,2.1))),tuple(q+Vector((0,0,2.1))),.23,'steel_light')
                    architecture.beam(tuple(p+Vector((0,0,.3))),tuple(q+Vector((0,0,1.8))),.13,'bronze')
                    architecture.beam(tuple(p+Vector((0,0,1.8))),tuple(q+Vector((0,0,.3))),.13,'steel')
            architecture.cube(tuple(c+Vector((0,0,.66))),(.15,width-.7,.025),'bronze',angle)
            if i%4==0 and i>0 and i<sections:
                architecture.cube(tuple(c+Vector((0,0,-9))),(5,width*.60,18),'basalt')
                architecture.cube(tuple(c+Vector((0,0,-17))),(8,width*.80,2),'basalt_light')
            # Riveted under-deck double trusses are real geometry from both sides.
            if i<sections:
                q=av+delta*(i+1)/sections
                for side in (-1,1):
                    p=c+normal*side*width/2; q1=q+normal*side*width/2
                    architecture.beam(tuple(p-Vector((0,0,1))),tuple(q1-Vector((0,0,4))),.7,'steel')
                    architecture.beam(tuple(p-Vector((0,0,4))),tuple(q1-Vector((0,0,1))),.6,'steel_light')
        return {'start':list(start),'end':list(end),'width':width,'length':length,'name':name}

    merovar=bridge((-275,-300,12),(-40,-115,12),14,'Merovar bridge')
    damar=bridge((-550,1700,12),(-140,50,12),10,'Damar bridge')

    # Ice aftermath: four separately posed guards, static anatomy inside stasis.
    a=Vector(merovar['start']); b=Vector(merovar['end']); d=(b-a).normalized(); side=Vector((-d.y,d.x,0))
    guards=[]
    def guard(i,along,lateral,pose):
        base=a+d*along+side*lateral; base.z=12.75
        # anatomical coordinates rotate toward the facility they were defending.
        f=d; r=side
        def P(x,y,z): return tuple(base+r*x+f*y+Vector((0,0,z)))
        architecture.cube(P(0,0,1.10),(.47,.28,.62),'steel_light',angle)
        architecture.cube(P(0,.02,.84),(.50,.31,.11),'bronze',angle)
        architecture.cube(P(0,-.05,.70),(.46,.33,.28),'crimson',angle)
        architecture.cone(P(0,0,1.66),.21,.15,.34,'steel',10)
        architecture.cube(P(0,.16,1.62),(.27,.08,.085),'black',angle)
        architecture.beam(P(-.20,.13,1.43),P(.20,.13,1.43),.10,'bronze')
        armposes=[((-.42,.03,1.12),(-.48,.39,1.39),(.42,-.06,1.15),(.43,-.12,.91)),((-.39,.07,1.51),(-.15,.47,1.67),(.40,.06,1.50),(.18,.49,1.69)),((-.45,.02,1.07),(-.44,.28,.88),(.50,.10,1.35),(.63,.35,1.46)),((-.42,-.08,1.27),(-.57,.14,1.44),(.36,.02,1.10),(.43,.27,.93))]
        le,re,rr,rh=armposes[pose]
        for sx,elbow,hand in ((-.26,le,re),(.26,rr,rh)):
            architecture.beam(P(sx,0,1.30),P(*elbow),.16,'steel')
            architecture.beam(P(*elbow),P(*hand),.12,'steel_light')
            architecture.cube(P(*hand),(.12,.12,.15),'leather')
        for sx,advance in ((-.14,.09 if pose%2 else -.17),(.14,-.13 if pose%2 else .18)):
            architecture.beam(P(sx,0,.72),P(sx,advance,.39),.17,'steel')
            architecture.beam(P(sx,advance,.39),P(sx,advance+.04,.09),.14,'steel_light')
            architecture.cube(P(sx,advance+.10,.065),(.20,.31,.13),'leather',angle)
        # Faceted ice is a complete, closed enclosure, with sparse contour seams.
        for z,rad in ((.05,.61),(1.88,.38)):
            architecture.torus(P(0,0,z),rad,.010,'ice_edge',10,4)
        architecture.cone(P(0,0,1.02),.65,.35,2.05,'ice',7)
        for k in range(7):
            aa=k*math.tau/7
            architecture.beam(P(.65*math.cos(aa),.65*math.sin(aa),0),P(.35*math.cos(aa),.35*math.sin(aa),2.04),.012,'ice_edge')
        guards.append({'id':f'carcovian_guard_{i+1}','position':list(base),'pose':pose})
    angle=math.atan2(d.y,d.x)
    for i,(along,lateral,pose) in enumerate(((.7,-3.2,0),(1.6,2.5,1),(3.,-1.2,2),(.6,4.6,3))): guard(i,along,lateral,pose)
    for i in range(40):
        along=random.uniform(0,23); lateral=random.uniform(-6.5,6.5); center=a+d*along+side*lateral; center.z=12.67
        architecture.cylinder(tuple(center),random.uniform(.25,1.1),.035,'ice',7)
        if i%3==0:
            architecture.beam(tuple(center-side*.22),tuple(center+side*.22),.022,'ice_edge')
    for k in range(12):
        p=a+d*(k*1.9)+side*6.65; p.z=13.15
        architecture.cone(tuple(p),.11,0,random.uniform(.25,.65),'ice_edge',5)

    geology=terrain.finish(bpy,'Shared geology / both mainland approaches / islands')
    for polygon in geology.data.polygons: polygon.use_smooth=True
    fortress=architecture.finish(bpy,'Detailed basalt steel bronze fortress / riveted bridges / frozen guards')
    waterdetails.finish(bpy,'World anchored surf and moonlit wavelets')

    # Reuse the approved sixteen COMPLETE plume drawings. These are two
    # vent-anchored, camera-facing surfaces with depth occlusion, never a field
    # of duplicated square smoke-puff births. Both passes use the same objects.
    plume_frames=[bpy.data.images.load(str(ROOT/f'assets/story/fire_veinhold_opening/shot01/environment/plume_{i:02d}.png'),check_existing=True) for i in range(1,17)]
    smoke_objects=[]
    for name,origin,size,tint,opacity,offset in (('Depleted main crater steam',(12,65,125),75,(210/255,224/255,239/255,1),155/255,0),('Distant active ash',(720,4200,155),466,(154/255,164/255,185/255,1),225/255,1.35)):
        material=bpy.data.materials.new(name+' complete drawn plume'); material.use_nodes=True; nodes=material.node_tree.nodes; nodes.clear(); links=material.node_tree.links
        output=nodes.new('ShaderNodeOutputMaterial'); transparent=nodes.new('ShaderNodeBsdfTransparent'); emission=nodes.new('ShaderNodeEmission')
        a=nodes.new('ShaderNodeTexImage'); a.image=plume_frames[0]; a.interpolation='Linear'; b=nodes.new('ShaderNodeTexImage'); b.image=plume_frames[1]; b.interpolation='Linear'
        mix=nodes.new('ShaderNodeMixRGB'); links.new(a.outputs['Color'],mix.inputs[1]); links.new(b.outputs['Color'],mix.inputs[2])
        multiply=nodes.new('ShaderNodeMixRGB'); multiply.blend_type='MULTIPLY'; multiply.inputs[0].default_value=1; multiply.inputs[2].default_value=tint; links.new(mix.outputs[0],multiply.inputs[1]); links.new(multiply.outputs[0],emission.inputs['Color'])
        aa=nodes.new('ShaderNodeMath'); aa.operation='MULTIPLY'; links.new(a.outputs['Alpha'],aa.inputs[0])
        ab=nodes.new('ShaderNodeMath'); ab.operation='MULTIPLY'; links.new(b.outputs['Alpha'],ab.inputs[0])
        add=nodes.new('ShaderNodeMath'); add.operation='ADD'; links.new(aa.outputs[0],add.inputs[0]); links.new(ab.outputs[0],add.inputs[1])
        strength=nodes.new('ShaderNodeMath'); strength.operation='MULTIPLY'; strength.inputs[1].default_value=opacity; links.new(add.outputs[0],strength.inputs[0])
        shader=nodes.new('ShaderNodeMixShader'); links.new(strength.outputs[0],shader.inputs[0]); links.new(transparent.outputs[0],shader.inputs[1]); links.new(emission.outputs[0],shader.inputs[2]); links.new(shader.outputs[0],output.inputs[0])
        mesh=bpy.data.meshes.new(name+' world-anchored billboard'); mesh.from_pydata([(0,0,0)]*4,[],[(0,1,2,3)]); mesh.materials.append(material); uv=mesh.uv_layers.new()
        for loop,coord in zip(uv.data,((0,0),(1,0),(1,1),(0,1))): loop.uv=coord
        obj=bpy.data.objects.new(name,mesh); common_collection.objects.link(obj); obj.location=origin
        smoke_objects.append({'obj':obj,'size':size,'a':a,'b':b,'mix':mix,'aa':aa,'ab':ab,'phase_offset':offset})

    # World-relative lighting and a real moon remain fixed through the orbit.
    def area(name,location,color,power,size,target):
        light=bpy.data.lights.new(name,'AREA'); light.energy=power; light.color=color; light.shape='DISK'; light.size=size
        obj=bpy.data.objects.new(name,light); bpy.context.collection.objects.link(obj); obj.location=location
        obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()
    sun=bpy.data.lights.new('Silver moon key','SUN'); sun.energy=2.5; sun.color=(.53,.69,1); sun.angle=.09
    sun_obj=bpy.data.objects.new('Silver moon key',sun); bpy.context.collection.objects.link(sun_obj); sun_obj.rotation_euler=(.44,-.48,-.48)
    area('Broad atmospheric fill',(0,-300,430),(.25,.43,.85),1800000,600,(0,0,20))
    area('Fire reservoir bounce',(110,-45,50),(1,.21,.025),95000,55,(110,-45,5))
    star_mat=mat('Star and moon silver',(.60,.78,1),emission=2.0,texture=False)
    stars=MeshBatch({'star':star_mat})
    for i in range(4000):
        az=random.uniform(0,math.tau); el=random.uniform(.03,1.35); rr=3800
        pos=(rr*math.cos(el)*math.cos(az),rr*math.cos(el)*math.sin(az),rr*math.sin(el))
        stars.cube(pos,(random.uniform(3,6),)*3,'star')
    stars.finish(bpy,'Fixed celestial stars')
    # A true enclosing sky surface makes the base pass opaque while the
    # separate relief pass can retain film transparency around its geometry.
    sky_material=bpy.data.materials.new('Painted midnight sky'); sky_material.use_nodes=True
    nodes=sky_material.node_tree.nodes; nodes.clear(); links=sky_material.node_tree.links
    sky_output=nodes.new('ShaderNodeOutputMaterial'); sky_emission=nodes.new('ShaderNodeEmission'); coordinate=nodes.new('ShaderNodeTexCoord'); separate=nodes.new('ShaderNodeSeparateXYZ'); ramp=nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position=.48; ramp.color_ramp.elements[0].color=(.012,.040,.115,1); ramp.color_ramp.elements[1].position=.95; ramp.color_ramp.elements[1].color=(.002,.006,.022,1)
    links.new(coordinate.outputs['Generated'],separate.inputs[0]); links.new(separate.outputs['Z'],ramp.inputs[0]); links.new(ramp.outputs[0],sky_emission.inputs[0]); links.new(sky_emission.outputs[0],sky_output.inputs[0])
    bpy.ops.mesh.primitive_uv_sphere_add(segments=64,ring_count=32,radius=9700); sky=bpy.context.object; sky.name='Continuous world-relative midnight sky'; sky.data.materials.append(sky_material)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=40,ring_count=24,radius=45,location=(-680,2500,450)); moon=bpy.context.object; moon.name='Fixed moon'; moon.data.materials.append(star_mat)
    camera_data=bpy.data.cameras.new('Cinematic perspective camera'); camera=bpy.data.objects.new('Cinematic perspective camera',camera_data); bpy.context.collection.objects.link(camera); scene.camera=camera
    camera.data.lens=70; camera.data.sensor_width=36; camera.data.clip_start=.08; camera.data.clip_end=30000
    scene.use_nodes=True; tree=scene.node_tree; tree.nodes.clear(); rl=tree.nodes.new('CompositorNodeRLayers'); glare=tree.nodes.new('CompositorNodeGlare'); glare.glare_type='FOG_GLOW'; glare.quality='LOW'; glare.threshold=1.7; glare.size=6; glare.mix=-.95; out=tree.nodes.new('CompositorNodeComposite'); tree.links.new(rl.outputs['Image'],glare.inputs['Image']); tree.links.new(glare.outputs['Image'],out.inputs['Image'])
    final=Vector(merovar['start'])+d*6.096+Vector((0,0,2.65))
    final_target=final-d*18+Vector((0,0,-1.4))

    def smooth(t): return t*t*(3-2*t)
    def camera_at(segment,t):
        if segment=='orbit':
            u=max(0,min(1,t/5)); e=smooth(u); theta=-math.pi/2+math.pi*e
            position=Vector((math.cos(theta)*(800-345*e),math.sin(theta)*(800-345*e),125+230*e))
            target=Vector((-40*e,-80*e,80+70*e))
            degrees=180*e
        elif segment=='alarm_hold': return camera_at('orbit',5)
        elif segment=='rush':
            u=max(0,min(1,t)); e=smooth(u)
            p0,_target,_=camera_at('orbit',5)
            p1=Vector((115,140,330)); p2=final+Vector((135,120,70)); p3=final
            position=p0*(1-e)**3+p1*3*(1-e)**2*e+p2*3*(1-e)*e*e+p3*e**3
            target=_target.lerp(final_target,smooth(u))
            # Clear the fortress before descending, then travel the final
            # bridge stretch at eye height rather than looking down onto a
            # stretched projection of a ground-level theatrical matte.
            eye_lock=smooth(max(0,min(1,(u-.55)/.25)))
            position.z=final.z+(position.z-final.z)*(1-eye_lock)
            target.z=final_target.z+(target.z-final_target.z)*(1-eye_lock)
            degrees=180
        else:
            position=final; target=final_target; degrees=180
        return position,target,degrees

    def smoke_at(seconds):
        right=camera.rotation_euler.to_quaternion()@Vector((1,0,0)); up=camera.rotation_euler.to_quaternion()@Vector((0,1,0))
        for record in smoke_objects:
            phase=((seconds+record['phase_offset'])%4)*4; index=int(phase); fraction=phase-index
            record['a'].image=plume_frames[index%16]; record['b'].image=plume_frames[(index+1)%16]
            record['mix'].inputs[0].default_value=fraction; record['aa'].inputs[1].default_value=1-fraction; record['ab'].inputs[1].default_value=fraction
            for vertex,(x,y) in zip(record['obj'].data.vertices,((0,256),(256,256),(256,0),(0,0))):
                vertex.co=right*(x-70)/256*record['size']+up*(230-y)/256*record['size']
            record['obj'].data.update()

    landmarks={'dormant_crater':[12,65,125],'active_crater':[720,4200,155],'reservoir':[110,-45,22],'merovar_landing':merovar['start'],'island_merovar_gate':merovar['end'],'damar_landing':damar['start'],'island_damar_gate':damar['end'],**{x['id']:x['position'] for x in guards}}
    def metadata(segment,index,t):
        position,target,degrees=camera_at(segment,t); camera.location=position; camera.rotation_euler=(target-position).to_track_quat('-Z','Y').to_euler()
        camera.data.lens=(70-45*smooth(min(1,t/5))) if segment=='orbit' else 25 if segment=='alarm_hold' else (25-7*smooth(min(1,t))) if segment=='rush' else 18
        bpy.context.view_layer.update()
        visible={}
        for key,p in landmarks.items():
            point=world_to_camera_view(scene,camera,Vector(p)); visible[key]=[round(point.x*WIDTH,3),round((1-point.y)*HEIGHT,3),round(point.z,4)]
        lamps=[]; depsgraph=bpy.context.evaluated_depsgraph_get()
        for beacon in beacons:
            point=Vector(beacon); projected=world_to_camera_view(scene,camera,point)
            if not (0<projected.x<1 and 0<projected.y<1 and projected.z>0): continue
            direction=(point-camera.location); distance=direction.length
            start=camera.location.copy(); remaining=max(0,distance-1.2)
            for _ in range(4):
                hit,point,_,_,hit_obj,_=scene.ray_cast(depsgraph,start,direction.normalized(),distance=remaining)
                if not hit or hit_obj not in [item['obj'] for item in smoke_objects]: break
                travelled=(point-start).length+.02; start=point+direction.normalized()*.02; remaining-=travelled
                if remaining<=0: hit=False; break
            if not hit: lamps.append([round(projected.x*WIDTH,3),round((1-projected.y)*HEIGHT,3),round(max(2,min(24,1450/distance)),3)])
        return {'index':index,'time_seconds':t,'camera':{'position':list(position),'target':list(target),'up':[0,0,1],'fov_degrees':math.degrees(camera.data.angle),'orbit_degrees':degrees},'landmarks':visible,'alarm_points':lamps}

    # Project the approved painting onto surfaces visible in the initial view.
    # Unseen faces retain the independently authored, continuous tiled materials.
    metadata('orbit',0,0)
    plate_path=SOURCE/'materials/approved_projection.png'
    project_weights=[]
    if plate_path.exists():
        plate=bpy.data.images.load(str(plate_path),check_existing=True)
        moon_uv=moon.data.uv_layers.new(name='Original moon registration')
        for polygon in moon.data.polygons:
            for loop_i in polygon.loop_indices:
                p=world_to_camera_view(scene,camera,moon.matrix_world@moon.data.vertices[moon.data.loops[loop_i].vertex_index].co)
                moon_uv.data[loop_i].uv=(p.x,p.y)
        moon_material=bpy.data.materials.new('Original cratered moon'); moon_material.use_nodes=True; nodes=moon_material.node_tree.nodes; nodes.clear(); links=moon_material.node_tree.links
        output=nodes.new('ShaderNodeOutputMaterial'); em=nodes.new('ShaderNodeEmission'); tex=nodes.new('ShaderNodeTexImage'); tex.image=plate; uv=nodes.new('ShaderNodeUVMap'); uv.uv_map=moon_uv.name
        links.new(uv.outputs[0],tex.inputs[0]); links.new(tex.outputs['Color'],em.inputs[0]); links.new(em.outputs[0],output.inputs[0]); moon.data.materials.clear(); moon.data.materials.append(moon_material)
        for obj in (geology,fortress):
            uv=obj.data.uv_layers.new(name='Approved initial perspective')
            for polygon in obj.data.polygons:
                for loop_i in polygon.loop_indices:
                    p=world_to_camera_view(scene,camera,obj.matrix_world@obj.data.vertices[obj.data.loops[loop_i].vertex_index].co)
                    uv.data[loop_i].uv=(p.x,p.y)
        excluded={'ice','ice_edge','skin','leather','ember','ember_hot','window','beacon','foam'}
        for key,m in materials.items():
            if key in excluded or m.name.endswith(' projected'): continue
            nodes=m.node_tree.nodes; links=m.node_tree.links; output=nodes.get('Material Output'); original=output.inputs['Surface'].links[0].from_socket
            texture=nodes.new('ShaderNodeTexImage'); texture.image=plate; texture.extension='EXTEND'; texture.interpolation='Linear'
            uv=nodes.new('ShaderNodeUVMap'); uv.uv_map='Approved initial perspective'; links.new(uv.outputs[0],texture.inputs['Vector'])
            emission=nodes.new('ShaderNodeEmission'); links.new(texture.outputs['Color'],emission.inputs['Color'])
            geo=nodes.new('ShaderNodeNewGeometry'); dot=nodes.new('ShaderNodeVectorMath'); dot.operation='DOT_PRODUCT'; dot.inputs[1].default_value=(0,-1,.12); links.new(geo.outputs['Normal'],dot.inputs[0])
            facing=nodes.new('ShaderNodeMapRange'); facing.inputs['From Min'].default_value=.01; facing.inputs['From Max'].default_value=.06; links.new(dot.outputs['Value'],facing.inputs['Value'])
            weight=nodes.new('ShaderNodeValue'); weight.outputs[0].default_value=1; project_weights.append(weight)
            multiply=nodes.new('ShaderNodeMath'); multiply.operation='MULTIPLY'; links.new(facing.outputs[0],multiply.inputs[0]); links.new(weight.outputs[0],multiply.inputs[1])
            mix=nodes.new('ShaderNodeMixShader'); links.new(multiply.outputs[0],mix.inputs[0]); links.new(original,mix.inputs[1]); links.new(emission.outputs[0],mix.inputs[2]); links.new(mix.outputs[0],output.inputs['Surface'])
            m.name+=' projected'
    # A painted surface pass is deterministic and inexpensive on CPU. Fixed
    # world-normal illumination preserves form without noisy indirect sampling.
    for m in bpy.data.materials:
        if not m.use_nodes: continue
        nodes=m.node_tree.nodes; links=m.node_tree.links; p=next((n for n in nodes if n.type=='BSDF_PRINCIPLED'),None)
        if p is None: continue
        if m==materials['ice']:
            glass=nodes.new('ShaderNodeBsdfGlass'); glass.inputs['Color'].default_value=(.63,.86,1,1); glass.inputs['Roughness'].default_value=.012; glass.inputs['IOR'].default_value=1.015
            for link in list(p.outputs[0].links): links.new(glass.outputs[0],link.to_socket)
            continue
        emission=nodes.new('ShaderNodeEmission')
        if p.inputs['Base Color'].is_linked:
            source_color=p.inputs['Base Color'].links[0].from_socket
        else:
            solid=nodes.new('ShaderNodeRGB'); solid.outputs[0].default_value=p.inputs['Base Color'].default_value; source_color=solid.outputs[0]
        distance=nodes.new('ShaderNodeCameraData'); haze=nodes.new('ShaderNodeMapRange'); haze.inputs['From Min'].default_value=700; haze.inputs['From Max'].default_value=5500; haze.inputs['To Max'].default_value=.84
        links.new(distance.outputs['View Distance'],haze.inputs[0]); atmosphere=nodes.new('ShaderNodeMixRGB'); atmosphere.inputs[2].default_value=(.024,.073,.15,1); links.new(source_color,atmosphere.inputs[1]); links.new(haze.outputs[0],atmosphere.inputs[0])
        links.new(atmosphere.outputs[0],emission.inputs['Color'])
        strength=p.inputs['Emission Strength'].default_value
        if strength>0: emission.inputs['Strength'].default_value=max(1,strength*.65)
        else:
            geo=nodes.new('ShaderNodeNewGeometry'); dot=nodes.new('ShaderNodeVectorMath'); dot.operation='DOT_PRODUCT'; dot.inputs[1].default_value=(-.45,-.25,.85); links.new(geo.outputs['Normal'],dot.inputs[0])
            lighting=nodes.new('ShaderNodeMapRange'); lighting.inputs['From Min'].default_value=-1; lighting.inputs['From Max'].default_value=1; lighting.inputs['To Min'].default_value=.43; lighting.inputs['To Max'].default_value=1.05; links.new(dot.outputs['Value'],lighting.inputs[0]); links.new(lighting.outputs[0],emission.inputs['Strength'])
        for link in list(p.outputs[0].links): links.new(emission.outputs[0],link.to_socket)
    # Additional artist-finished reference views are baked onto the actual
    # visible faces. Occluded faces retain their tiled materials; projected
    # keep windows cannot accidentally be painted onto the ocean or far wall.
    from mathutils.bvhtree import BVHTree
    reference_specs=[('000',0.0),('090',2.5),('180',5.0)]
    for label,reference_time in reference_specs:
        reference_path=SOURCE/'materials'/f'orbit_{label}_final.png'
        if not reference_path.exists(): continue
        metadata('orbit',round(reference_time*60),reference_time)
        vertices=[]; polygons=[]
        for obj in (geology,fortress):
            offset=len(vertices); vertices.extend(tuple(obj.matrix_world@v.co) for v in obj.data.vertices)
            polygons.extend(tuple(offset+i for i in p.vertices) for p in obj.data.polygons)
        bvh=BVHTree.FromPolygons(vertices,polygons,all_triangles=False,epsilon=.002)
        uv_name=f'Painted reference {label}'; visibility_name=f'Visible painted reference {label}'
        for obj in (geology,fortress):
            obj.data.uv_layers.new(name=uv_name)
            visibility=obj.data.attributes.new(name=visibility_name,type='FLOAT',domain='CORNER')
            # Adding a corner attribute can reallocate Blender's CustomData
            # layer array. A previously retained UV-layer handle then aliases
            # another layer. Always reacquire by name after that allocation.
            uv=obj.data.uv_layers[uv_name]
            for polygon in obj.data.polygons:
                centre=obj.matrix_world@polygon.center; ray=centre-camera.location; distance=ray.length
                direction=ray.normalized(); n=obj.matrix_world.to_3x3()@polygon.normal
                facing=max(0,n.dot(-direction)); p=world_to_camera_view(scene,camera,centre)
                minimum_facing=.001 if obj==geology else .08
                eligible=0<=p.x<=1 and 0<=p.y<=1 and p.z>0 and facing>minimum_facing
                if (label=='000' and obj==geology and centre.z>40
                        and (centre.x/165)**2+((centre.y-65)/145)**2<1.25):
                    # The initial painting's low apron is broader than this
                    # surface: use dedicated schist here, never project its
                    # horizontal grass terraces onto steep volcanic walls.
                    eligible=False
                if eligible:
                    hit=bvh.ray_cast(camera.location,direction,max(0,distance-.08))
                    eligible=hit[0] is None
                weight=(1 if obj==geology else min(1,max(0,(facing-.08)/.18))) if eligible else 0
                for loop_i in polygon.loop_indices:
                    point=world_to_camera_view(scene,camera,obj.matrix_world@obj.data.vertices[obj.data.loops[loop_i].vertex_index].co)
                    uv.data[loop_i].uv=(point.x,point.y); visibility.data[loop_i].value=weight
            # Verify the stored named layer, rather than trusting a Python
            # handle, before a misregistered texture can enter a frame bank.
            for loop_i in (0,len(obj.data.loops)//3,len(obj.data.loops)-1):
                point=world_to_camera_view(scene,camera,obj.matrix_world@obj.data.vertices[obj.data.loops[loop_i].vertex_index].co)
                actual=obj.data.uv_layers[uv_name].data[loop_i].uv
                assert (actual-Vector((point.x,point.y))).length<1e-5,(label,obj.name,'UV registration')
        image=bpy.data.images.load(str(reference_path),check_existing=True)
        terrain_path=SOURCE/'materials'/f'orbit_{label}_terrain.png'
        terrain_image=bpy.data.images.load(str(terrain_path),check_existing=True) if terrain_path.exists() else None
        for key,m in materials.items():
            if key in {'window','ember','ember_hot','ice','ice_edge','skin','leather','beacon','foam','rock_damar'}: continue
            is_geology=key in {'rock','rock_dark','rock_rust','snow'}
            if is_geology and terrain_image is None: continue
            nodes=m.node_tree.nodes; links=m.node_tree.links; output=next(n for n in nodes if n.type=='OUTPUT_MATERIAL'); original=output.inputs[0].links[0].from_socket
            tex=nodes.new('ShaderNodeTexImage'); tex.image=terrain_image if is_geology else image; tex.extension='EXTEND'; tex.interpolation='Linear'
            uv=nodes.new('ShaderNodeUVMap'); uv.uv_map=uv_name; links.new(uv.outputs[0],tex.inputs[0])
            emission=nodes.new('ShaderNodeEmission'); links.new(tex.outputs['Color'],emission.inputs['Color'])
            visibility=nodes.new('ShaderNodeAttribute'); visibility.attribute_name=visibility_name
            mix=nodes.new('ShaderNodeMixShader'); links.new(visibility.outputs['Fac'],mix.inputs[0]); links.new(original,mix.inputs[1]); links.new(emission.outputs[0],mix.inputs[2]); links.new(mix.outputs[0],output.inputs[0])
    # The approved front and final paintings are mapped to dense nonplanar
    # geometry, rendered from the SAME moving perspective camera. The separate
    # pass supplies original-view detail while the shared scene supplies unseen
    # sides. It is not an image rotated/zoomed between perspective endpoints.
    from prologue_orbit_projection import create_depth_stage, create_frozen_stage
    projection_collection=bpy.data.collections.new('Painted spatial reliefs'); scene.collection.children.link(projection_collection)
    metadata('orbit',0,0)
    opening_stage=create_depth_stage(bpy,camera,plate_path,'Approved first vista spatial relief','opening')
    metadata('reveal',0,0)
    final_stage=create_frozen_stage(bpy,camera,SOURCE/'materials/frozen_bridge_background.png',[SOURCE/'materials'/name for name in ('frozen_guard_left_back.png','frozen_guard_left_front.png','frozen_guard_right_mid.png','frozen_guard_right_back.png')])
    for obj in (opening_stage,final_stage):
        for collection in list(obj.users_collection): collection.objects.unlink(obj)
        projection_collection.objects.link(obj)
    main_layer=scene.view_layers[0]; main_layer.layer_collection.children[projection_collection.name].exclude=True
    projection_layer=scene.view_layers.new('Approved painted spatial relief')
    projection_layer.layer_collection.children[base_collection.name].exclude=True
    rl.layer=main_layer.name
    projected=tree.nodes.new('CompositorNodeRLayers'); projected.layer=projection_layer.name
    alpha_over=tree.nodes.new('CompositorNodeAlphaOver'); alpha_over.inputs[0].default_value=1
    tree.links.new(rl.outputs['Image'],alpha_over.inputs[1]); tree.links.new(projected.outputs['Image'],alpha_over.inputs[2]); tree.links.new(alpha_over.outputs['Image'],glare.inputs['Image'])
    metadata('orbit',0,0); smoke_at(25)
    config={'version':1,'renderer':'Blender 4.3 Cycles CPU painted surface pass','render_size':[WIDTH,HEIGHT],'fps':60,'orbit_samples':301,'orbit_degrees':180,'orbit_seconds':5,'rush_samples':61,'rush_seconds':1,'metres_per_unit':1,'mainland_landing_to_final_camera_metres':6.096,'initial_world_heading':'east-southeast','reverse_world_heading':'west-northwest','geometry_axes':'local+x screen-right at initial camera; local+y points east-southeast in canon geography','bridges':[merovar,damar],'guards':guards,'landmarks':landmarks,'projection_meshes':{'opening':{'vertices':len(opening_stage.data.vertices),'faces':len(opening_stage.data.polygons)},'final':{'vertices':len(final_stage.data.vertices),'faces':len(final_stage.data.polygons)}},'notes':['Shared geometry and world-anchored moonlight; no image-plane orbit.','Approved initial/final plates are reconstructed as nonplanar spatial reliefs, not flat quads.','Opening relief applies only over the first three degrees; all remaining orbit views use the shared fully spatial scene.','Painted 0/90/180 views bake onto actual visible faces; terrain-only versions prevent architecture pixels on geology.','The relief and shared scene are rendered with the same moving camera.','Main volcano depleted and dormant; distant crater active.','301 inclusive orbit samples define 300 1/60-second intervals.','Beauty lamps inactive; projected alarm masks respect scene ray occlusion.','Two approved COMPLETE drawn plumes are vent anchored in world space with true depth occlusion, not duplicated puff tiles.','Smoke uses original four-second phase and global time25+continuation time.']}
    config['opening_handoff']={'last_orbit_degree':3,'moon_relief_front_depth_metres':3340,'matte_edge_feather_uv':.045,'full_edge_softness_at_degree':.25}
    config['render_samples']=args.samples; config['sampling_seed']=scene.cycles.seed; config['animated_seed']=False
    config['notes']=[note for note in config['notes'] if not note.startswith('Approved initial/final plates')]
    config['notes'].append('The final stage uses a rigid far backdrop, four separate RGBA guard planes and an actual horizontal deck; no final depth-field mesh is used.')
    config['frozen_stage']={'backdrop_depth_metres':700,'backdrop_overscan':3,'deck_elevation_metres':12.65,'deck_width_metres':17,'guard_depths_metres':[5.5,3.4,4.5,5.5],'ground_photo_polygon_native':[[0,640],[960,640],[960,425],[634,316],[396,316],[0,425]],'takeover_seconds':[.60,.82]}
    config['rush_eye_height_lock']={'start_seconds':.55,'complete_seconds':.80,'eye_elevation_metres':final.z,'focus_elevation_metres':final_target.z}
    (SOURCE/'scene_config.json').write_text(json.dumps(config,indent=2)+'\n')
    for node in project_weights: node.outputs[0].default_value=0
    opening_stage.hide_render=False; final_stage.hide_render=True; alpha_over.inputs[0].default_value=1
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.file.make_paths_relative()
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE/'fire_veinhold_continuation.blend'),compress=True)
    segments={'orbit':(301,5000,None),'alarm_hold':(16,4000,4000),'rush':(61,1000,None),'reveal':(16,4000,4000)}
    manifest={'version':1,'width':WIDTH,'height':HEIGHT,'fps':60,'segments':{}}
    for segment,(count,duration,loop) in segments.items():
        folder=DEST/segment; folder.mkdir(exist_ok=True)
        frames=[f'{segment}/frame_{i:04d}.png' for i in range(count)]; alarms=[f'{segment}/alarm_{i:04d}.png' for i in range(count)]
        record={'frames':frames,'alarm_frames':alarms,'duration_ms':duration,'metadata_path':f'{segment}/cameras.json','inclusive_end':not bool(loop)}
        if loop: record['loop_ms']=loop
        manifest['segments'][segment]=record
        rows=[]
        for i in range(count):
            t=i/60 if not loop else i*loop/count/1000
            rows.append(metadata(segment,i,t))
        (folder/'cameras.json').write_text(json.dumps(rows,indent=2)+'\n')
    (DEST/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')

    jobs=[]
    if args.preview:
        for segment,i in [('orbit',int(x)) for x in args.proof_frames.split(',') if x]+[('rush',int(x)) for x in args.rush_proof_frames.split(',') if x]: jobs.append((segment,i,SOURCE/f'{"base" if args.base_only else "preview"}_{segment}_{i:04d}.png'))
    elif args.render:
        for segment,(count,_,loop) in segments.items():
            if args.segment not in ('all',segment): continue
            for i in range(max(0,args.start),min(count,args.stop)):
                if args.patch_continuation and not ((segment=='orbit' and i<23) or (segment=='rush' and i>=33) or segment=='reveal'): continue
                jobs.append((segment,i,DEST/manifest['segments'][segment]['frames'][i]))
    start=time.monotonic()
    for segment,i,path in jobs:
        loop=segments[segment][2]; t=i/60 if not loop else i*loop/segments[segment][0]/1000
        row=metadata(segment,i,t); smoke_at(25+t+(5 if segment=='alarm_hold' else 9 if segment=='rush' else 10 if segment=='reveal' else 0))
        angle=row['camera']['orbit_degrees']
        # The front-view painting is a source texture, rather than a billboard.
        # As its grazing surfaces turn away, tile-authored rear surfaces take
        # over; this avoids stretching projected roofs across unseen terrain.
        for node in project_weights: node.outputs[0].default_value=0
        opening_stage.hide_render=segment!='orbit' or angle>=3 or args.base_only
        opening_stage.data.materials[0].node_tree.nodes['Opening boundary softness'].outputs[0].default_value=min(1,angle/.25)
        final_stage.hide_render=segment not in ('rush','reveal')
        if segment=='orbit': alpha_over.inputs[0].default_value=1-smooth(max(0,min(1,angle/3)))
        elif segment=='rush': alpha_over.inputs[0].default_value=smooth(max(0,min(1,(t-.60)/.22)))
        elif segment=='reveal': alpha_over.inputs[0].default_value=1
        else: alpha_over.inputs[0].default_value=0
        if args.base_only: alpha_over.inputs[0].default_value=0
        # Most of the film uses only the shared spatial scene. Avoid tracing
        # an unused matte pass when the compositor's relief weight is zero.
        projection_layer.use=alpha_over.inputs[0].default_value>0
        main_layer.use=not (segment in ('rush','reveal') and alpha_over.inputs[0].default_value>=1)
        scene.render.filepath=str(path); bpy.ops.render.render(write_still=True)
        print(f'FRAME {segment} {i} {path} elapsed={time.monotonic()-start:.2f}',flush=True)
    print('Spatial source and camera manifest complete.',flush=True)


if __name__=='__main__':
    raise SystemExit(main())
