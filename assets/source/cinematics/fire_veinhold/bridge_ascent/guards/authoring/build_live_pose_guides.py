"""Render motion/camera guides only; no guide pixels enter production art."""
from pathlib import Path
import math
import bpy
from mathutils import Matrix, Vector

OUT = Path(__file__).resolve().parent


def material(name, rgb):
    result = bpy.data.materials.new(name)
    result.diffuse_color = (*rgb, 1)
    return result


def ellipsoid(name, position, scale, mat):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, location=position)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    obj.data.materials.append(mat)
    return obj


def link(name, a, b, radius, mat):
    a, b = Vector(a), Vector(b)
    bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=radius,
                                      depth=(b-a).length, location=(a+b)/2)
    obj = bpy.context.object
    obj.name = name
    obj.rotation_euler = (b-a).to_track_quat('Z', 'Y').to_euler()
    obj.data.materials.append(mat)


def foot(phase):
    keys = [(0,-.55,.055),(.2,0,.055),(.38,.42,.055),(.5,.55,.30),
            (.68,.1,.70),(.84,-.34,.48),(1,-.55,.055)]
    for first, second in zip(keys, keys[1:]):
        if phase <= second[0]:
            t = (phase-first[0])/(second[0]-first[0])
            t = t*t*(3-2*t)
            return tuple(first[i]+(second[i]-first[i])*t for i in (1,2))
    raise ValueError(phase)


def knee(hip, ankle):
    # Two equal links, with the knee bending toward the direction of travel.
    dy, dz = ankle[1]-hip[1], ankle[2]-hip[2]
    distance = math.hypot(dy,dz)
    middle = ((hip[1]+ankle[1])/2,(hip[2]+ankle[2])/2)
    height = math.sqrt(max(0,.51**2-(distance/2)**2))
    perpendicular = (dz/distance,-dy/distance)
    if perpendicular[0] > 0:
        perpendicular = tuple(-value for value in perpendicular)
    return (hip[0],middle[0]+height*perpendicular[0],middle[1]+height*perpendicular[1])


def render(index):
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    plate = material('Neutral armor guide',(.29,.34,.39))
    joints = material('Joint guide',(.12,.16,.20))
    leather = material('Hands and boots guide',(.28,.20,.15))
    copper = material('Copper identity guide',(.40,.22,.12))
    visor = material('Front of closed visor guide',(.025,.035,.045))
    phase = index/16
    hips_z = .86-.035*math.cos(4*math.pi*phase)
    ellipsoid('Pelvis',(0,0,hips_z),(.22,.14,.13),joints)
    ellipsoid('Torso',(0,-.07,hips_z+.32),(.29,.17,.31),plate)
    head=ellipsoid('Closed helmet crown',(0,-.16,hips_z+.84),(.125,.155,.16),plate)
    head.rotation_euler[0]=math.radians(20)
    face=ellipsoid('Front visor bowed toward travel minusY',(0,-.286,hips_z+.762),(.10,.028,.07),visor)
    face.rotation_euler[0]=math.radians(20)
    for side, offset in [('R',0),('L',.5)]:
        sign = -1 if side=='R' else 1
        f = (phase+offset)%1
        y,z = foot(f)
        hip = (sign*.13,0,hips_z)
        ankle = (sign*.13,y,z)
        joint = knee(hip,ankle)
        link(side+' thigh',hip,joint,.087,plate)
        link(side+' shin',joint,ankle,.070,plate)
        ellipsoid(side+' knee',joint,(.10,.095,.10),plate)
        ellipsoid(side+' foot',ankle,(.085,.145,.065),leather)
        shoulder=(sign*.26,-.07,hips_z+.57)
        excursion = .28 if side=='R' else .16
        hand=(sign*.40,excursion*math.cos(2*math.pi*f),hips_z+.22+.06*math.sin(2*math.pi*f))
        elbow=(sign*.38,hand[1]*.45,hips_z+.37)
        link(side+' upper arm',shoulder,elbow,.085,plate)
        link(side+' forearm',elbow,hand,.075,plate)
        ellipsoid(side+' glove',hand,(.065,.070,.060),leather)
        if side=='R':
            blade_end=(hand[0],hand[1]-.62,hand[2]-.52)
            link('Sword guide',hand,blade_end,.025,plate)
            link('Crossguard',(hand[0]-.10,hand[1],hand[2]),
                 (hand[0]+.10,hand[1],hand[2]),.025,copper)
        else:
            ellipsoid('Forearm shield',(hand[0],hand[1]-.04,hand[2]),(.27,.045,.35),plate)
    theta=math.radians(70)
    right=(-1,0,0)
    forward=(0,math.cos(theta),-math.sin(theta))
    up=(0,-math.sin(theta),-math.cos(theta))
    eye=(0,-4,.9+4*math.tan(theta))
    data=bpy.data.cameras.new('World minusY / screenUP authoring camera')
    obj=bpy.data.objects.new(data.name,data)
    bpy.context.collection.objects.link(obj)
    obj.matrix_world=Matrix(((right[0],up[0],-forward[0],eye[0]),
                             (right[1],up[1],-forward[1],eye[1]),
                             (right[2],up[2],-forward[2],eye[2]),(0,0,0,1)))
    data.type='ORTHO'
    data.ortho_scale=2.75
    scene=bpy.context.scene
    scene.camera=obj
    scene.world.use_nodes=True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.22,.28,.34,1)
    for loc,power in [((2,1,6),450),((-3,-2,5),250)]:
        data=bpy.data.lights.new('Pose-guide area','AREA');data.energy=power;data.size=5
        light=bpy.data.objects.new(data.name,data);bpy.context.collection.objects.link(light);light.location=loc
    scene.render.engine='CYCLES'
    scene.cycles.samples=6
    scene.cycles.use_denoising=False
    scene.render.resolution_x=512
    scene.render.resolution_y=512
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'
    scene.render.film_transparent=False
    scene.view_settings.view_transform='Standard'
    scene.render.filepath=str(OUT/f'live_guide_{index:02d}.png')
    bpy.ops.render.render(write_still=True)


if __name__=='__main__':
    for i in range(16):
        render(i)
