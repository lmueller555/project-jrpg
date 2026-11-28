"""Render camera/pose references only; guide pixels never ship as character art."""
import argparse
import json
import math
from pathlib import Path
import sys

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[6]
sys.path.insert(0, str(ROOT))
from cinematic_bridge_ascent import actor_states_at, camera_at


def material(name, rgb):
    item = bpy.data.materials.new(name)
    item.diffuse_color = (*rgb, 1)
    return item


def ellipsoid(name, point, scale, mat):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, location=point)
    item = bpy.context.object
    item.name = name
    item.scale = scale
    item.data.materials.append(mat)
    return item


def bone(name, first, second, radius, mat):
    first, second = Vector(first), Vector(second)
    bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=radius,
        depth=(second-first).length, location=(first+second)/2)
    item = bpy.context.object
    item.name = name
    item.rotation_euler = (second-first).to_track_quat('Z', 'Y').to_euler()
    item.data.materials.append(mat)


def hermite(t, a, b):
    t0, p0, v0 = a
    t1, p1, v1 = b
    u = (t-t0)/(t1-t0)
    return ((2*u**3-3*u**2+1)*p0 + (u**3-2*u**2+u)*(t1-t0)*v0
            + (-2*u**3+3*u**2)*p1 + (u**3-u**2)*(t1-t0)*v1)


def curve(t, keys):
    for first, second in zip(keys, keys[1:]):
        if t <= second[0]:
            return hermite(t, first, second)
    return keys[-1][1]


def foot_at(seconds):
    u = seconds % .8
    if u <= .18:
        return .30-4*u, .065
    y = curve(u, [(.18,-.42,-4),(.28,-.60,0),(.4,-.35,3),(.52,.12,4),
                  (.64,.48,1),(.72,.50,-1),(.8,.30,-4)])
    z = curve(u, [(.18,.065,0),(.20,.14,3),(.28,.32,1),(.4,.40,.7),(.52,.53,0),
                  (.64,.38,-2),(.72,.20,-2),(.8,.065,0)])
    return y, z


def knee_at(hip, foot):
    # Fixed .50m thigh/calf lengths; choose the anatomically forward knee.
    y, z = foot[1]-hip[1], foot[2]-hip[2]
    distance = math.hypot(y,z)
    if distance >= 1:
        raise ValueError('Guide foot target exceeds the unchanging leg length')
    midpoint_y, midpoint_z = (hip[1]+foot[1])/2, (hip[2]+foot[2])/2
    height = math.sqrt(.25-(distance/2)**2)
    return (hip[0], midpoint_y-z/distance*height, midpoint_z+y/distance*height)


def elbow_at(shoulder, hand, side):
    first, second = Vector(shoulder), Vector(hand)
    delta = second-first
    distance = delta.length
    upper, lower = .29, .28
    along = (upper**2-lower**2+distance**2)/(2*distance)
    height = math.sqrt(max(0,upper**2-along**2))
    direction = delta.normalized()
    outward = Vector((side,0,0))
    outward = (outward-direction*outward.dot(direction)).normalized()
    return tuple(first+direction*along+outward*height)


def build_actor(frame, mats):
    phase = frame/60
    theta = 2*math.pi*phase/.8
    steel, gold, red, hair, leather = mats
    recoil = -.012*math.cos(2*theta)
    hip_z = .95+recoil
    for side, offset in ((1,0),(-1,.4)):
        name = 'Right' if side==1 else 'Left'
        y,z = foot_at(phase+offset)
        hip = (side*.11,0,hip_z)
        foot = (side*.13,y,z)
        knee = knee_at(hip,foot)
        bone(name+' thigh',hip,knee,.075,steel)
        bone(name+' calf',knee,foot,.068,steel)
        ellipsoid(name+' boot',foot,(.085,.15,.065),leather)
    ellipsoid('hips',(0,0,hip_z),(.22,.14,.11),red)
    torso = ellipsoid('torso',(0,.06,1.22+recoil),(.235,.14,.29),red)
    torso.rotation_euler[0] = -.13
    for side in (1,-1):
        ellipsoid(('Right' if side==1 else 'Left')+' pauldron',
            (side*.24,.08,1.43+recoil),(.15,.15,.10),steel)
    hands = {}
    for side in (1,-1):
        name = 'Right' if side==1 else 'Left'
        y = .05-.33*math.cos(theta) if side==1 else .06+.18*math.cos(theta)
        z = 1.10+.15*(1-math.cos(theta))/2 if side==1 else 1.12-.035*math.cos(theta)
        shoulder = (side*.24,.08,1.43+recoil)
        hand = (side*.34,y,z+recoil)
        elbow = elbow_at(shoulder,hand,side)
        bone(name+' upper arm',shoulder,elbow,.073,steel)
        bone(name+' forearm',elbow,hand,.065,steel)
        ellipsoid(name+' glove',hand,(.065,.075,.06),leather)
        hands[side] = hand
    ellipsoid('Dark hair crown',(0,.16,1.69+recoil),(.18,.19,.16),hair)
    ellipsoid('Trailing tabard',(0,-.14-.035*math.sin(theta-.4),.99+recoil),(.23,.25,.065),red)
    # Constant blade length with a safe phase-dependent carry direction.
    grip = Vector(hands[1])
    guard = grip+Vector((.02,.10,-.12))
    angle = math.radians(17+28*(1-math.cos(theta))/2)
    horizontal = math.sqrt(.94**2-.65**2)
    point = guard+Vector((horizontal*math.sin(angle),horizontal*math.cos(angle),-.65))
    bone('Sword grip',tuple(grip+Vector((0,-.07,.07))),tuple(guard),.022,leather)
    bone('Sword blade',tuple(guard),tuple(point),.019,steel)
    bone('Sword guard',tuple(guard+Vector((-.10,0,0))),tuple(guard+Vector((.10,0,0))),.018,gold)
    left = hands[-1]
    center_x, center_y, center_z = left[0]-.10,left[1]+.06,left[2]+.02
    vertices = [(center_x-.22,center_y-.04,center_z+.32),
                (center_x+.22,center_y-.04,center_z+.32),
                (center_x+.21,center_y-.01,center_z-.02),
                (center_x,center_y-.06,center_z-.38),
                (center_x-.20,center_y-.01,center_z-.02),
                (center_x,center_y+.06,center_z)]
    mesh = bpy.data.meshes.new('Upright shield guide')
    mesh.from_pydata(vertices,[],[(i,(i+1)%5,5) for i in range(5)])
    mesh.update()
    shield = bpy.data.objects.new('Left shield guide',mesh)
    bpy.context.collection.objects.link(shield)
    shield.data.materials.append(red)
    for first,second in zip(vertices[:5],vertices[1:5]+vertices[:1]):
        bone('Shield rim',first,second,.014,gold)
    return {'head_centre':[0,.16,1.69+recoil], 'head_radius_x':.18,
            'hip':[0,0,hip_z], 'right_hand':list(hands[1]),'left_hand':list(hands[-1])}


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--kind',choices=('overhead','transition'),default='overhead')
    parser.add_argument('--indices',default='0,12,24,36')
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    folder = HERE/'guide_frames'
    folder.mkdir(exist_ok=True)
    results = []
    for index in map(int,args.indices.split(',')):
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)
        mats = [material('Steel',(.38,.44,.52)),material('Gold',(.65,.47,.20)),
                material('Oxblood',(.31,.055,.075)),material('Dark hair',(.11,.075,.055)),
                material('Leather',(.20,.11,.065))]
        frame = index if args.kind=='overhead' else actor_states_at(index/60)['runners'][0]['frame_index']
        landmarks = build_actor(frame,mats)
        data = bpy.data.cameras.new('Pose reference camera')
        data.sensor_fit = 'HORIZONTAL'
        owner = bpy.data.objects.new('Pose reference camera',data)
        bpy.context.collection.objects.link(owner)
        if args.kind=='overhead':
            owner.location = (0,0,8)
            owner.rotation_euler = (0,0,math.pi)
            data.type = 'ORTHO'
            data.ortho_scale = 2.048
        else:
            state = actor_states_at(index/60)
            actor = state['runners'][0]
            camera = state['camera']
            owner.location = (0,camera['position'][1]-actor['world_position_metres'][1],camera['position'][2])
            right,up,back = camera['right'],camera['up'],[-x for x in camera['forward']]
            owner.rotation_euler = Matrix(((right[0],up[0],back[0]),
                (right[1],up[1],back[1]),(right[2],up[2],back[2]))).to_euler()
            data.type = 'PERSP'
            data.sensor_fit = 'HORIZONTAL'
            data.sensor_width = 36
            data.lens = 500*actor['depth_metres']*36/1024
        scene = bpy.context.scene
        scene.camera = owner
        scene.render.engine = 'CYCLES'
        scene.cycles.samples = 3
        scene.cycles.use_denoising = False
        scene.cycles.seed = 0
        scene.render.resolution_x,scene.render.resolution_y = 1024,1536
        scene.render.resolution_percentage = 50
        scene.render.image_settings.file_format = 'PNG'
        data.shift_y = 0
        bpy.context.view_layer.update()
        initial = world_to_camera_view(scene,owner,Vector((0,0,0))).y
        data.shift_y = .1
        bpy.context.view_layer.update()
        slope = (world_to_camera_view(scene,owner,Vector((0,0,0))).y-initial)/.1
        data.shift_y = (.375-initial)/slope
        world = scene.world
        world.use_nodes = True
        world.node_tree.nodes['Background'].inputs[0].default_value = (.45,.45,.45,1)
        for loc,energy in (((1,2,6),300),((-2,-2,5),200)):
            light = bpy.data.lights.new('Guide light','AREA')
            light.energy,light.size = energy,5
            item = bpy.data.objects.new('Guide light',light)
            bpy.context.collection.objects.link(item)
            item.location = loc
        scene.view_settings.view_transform = 'Standard'
        scene.render.film_transparent = False
        output = folder/f'{args.kind}_{index:03d}_guide.png'
        scene.render.filepath = str(output)
        bpy.ops.render.render(write_still=True)
        bpy.context.view_layer.update()
        projected = {name:[512*world_to_camera_view(scene,owner,Vector(point)).x,
                          768*(1-world_to_camera_view(scene,owner,Vector(point)).y)]
                     for name,point in landmarks.items() if isinstance(point,list)}
        results.append({'index':index,'gait_frame':frame,'kind':args.kind,
            'file':output.name,'source_density':250,'anchor':[256,480],
            'purpose':'authoring_reference_only; not measurements of final artwork',
            'guide_landmark_targets':projected})
    (folder/(args.kind+'_guide_targets.json')).write_text(json.dumps(results,indent=2)+'\n')


if __name__=='__main__':
    main()
