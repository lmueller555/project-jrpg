"""Pose/camera authoring guide only. No guide pixel enters final artwork."""
import math
from pathlib import Path

import bpy
from mathutils import Vector

OUT = Path(__file__).resolve().parent
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)


def material(name, color):
    item = bpy.data.materials.new(name)
    item.diffuse_color = (*color, 1)
    return item


hair = material('Dark hair crown guide', (.11, .075, .055))
steel = material('Polished steel guide', (.38, .44, .52))
gold = material('Gold edges guide', (.65, .47, .20))
red = material('Oxblood tabard and shield guide', (.31, .055, .075))
leather = material('Brown glove and boot guide', (.20, .11, .065))


def ellipsoid(name, location, scale, mat):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, location=location)
    item = bpy.context.object
    item.name = name
    item.scale = scale
    item.data.materials.append(mat)
    return item


def bone(name, first, second, radius, mat):
    first, second = Vector(first), Vector(second)
    bpy.ops.mesh.primitive_cylinder_add(vertices=18, radius=radius,
        depth=(second-first).length, location=(first+second)/2)
    item = bpy.context.object
    item.name = name
    item.rotation_euler = (second-first).to_track_quat('Z', 'Y').to_euler()
    item.data.materials.append(mat)
    return item


# The two named anatomical chains are explicit. Right foot is the contact;
# left foot recovers behind. +Y is forward and maps to image bottom.
right_hip, left_hip = (.11, 0, 1.0), (-.11, 0, 1.0)
right_knee, right_foot = (.13, .31, .54), (.14, .65, .065)
left_knee, left_foot = (-.12, -.22, .66), (-.13, -.43, .40)
for name, first, second in (
    ('Right thigh', right_hip, right_knee), ('Right calf', right_knee, right_foot),
    ('Left thigh', left_hip, left_knee), ('Left calf', left_knee, left_foot)):
    bone(name, first, second, .075, steel)
ellipsoid('Right contact boot', right_foot, (.09, .17, .065), leather)
ellipsoid('Left recovering boot', left_foot, (.09, .145, .07), leather)
ellipsoid('Hips', (0, 0, 1.0), (.23, .15, .12), red)
body = ellipsoid('Torso', (0, .07, 1.29), (.24, .14, .30), red)
body.rotation_euler[0] = -.16
ellipsoid('Right pauldron', (.24, .10, 1.47), (.15, .17, .105), steel)
ellipsoid('Left pauldron', (-.24, .10, 1.47), (.15, .17, .105), steel)
for side, shoulder, elbow, hand in (
    ('Right', (.24, .10, 1.43), (.37, -.12, 1.23), (.34, -.28, 1.12)),
    ('Left', (-.24, .10, 1.43), (-.38, .27, 1.27), (-.35, .38, 1.15))):
    bone(side+' upper arm', shoulder, elbow, .075, steel)
    bone(side+' forearm', elbow, hand, .065, steel)
    ellipsoid(side+' glove', hand, (.065, .075, .06), leather)
ellipsoid('Bare head and dark hair crown', (0, .22, 1.80), (.145, .17, .17), hair)

# Sword ownership stays on the anatomical right. Its point aims low/forward.
grip, guard, point = (.34, -.28, 1.12), (.37, -.13, .96), (.54, .70, .12)
bone('Sword grip', (.33, -.35, 1.20), guard, .025, leather)
bone('Sword blade', guard, point, .022, steel)
bone('Sword guard', (.27, -.13, .96), (.47, -.13, .96), .022, gold)

# The shield remains upright in X/Z, strapped to the left forearm. Its curved
# surface has only .11 m of plan depth, rather than a broad face laid flat.
vertices = [(-.67, .40, 1.43), (-.23, .40, 1.43), (-.24, .43, 1.05),
            (-.45, .38, .70), (-.65, .43, 1.05), (-.45, .49, 1.12)]
faces = [(index, (index+1) % 5, 5) for index in range(5)]
mesh = bpy.data.meshes.new('Upright left shield camera guide')
mesh.from_pydata(vertices, [], faces)
mesh.update()
shield = bpy.data.objects.new('Upright left shield camera guide', mesh)
bpy.context.collection.objects.link(shield)
shield.data.materials.append(red)
for first, second in zip(vertices[:5], vertices[1:5]+vertices[:1]):
    bone('Shield rim guide', first, second, .017, gold)

camera = bpy.data.cameras.new('Exact vertical camera')
owner = bpy.data.objects.new('Exact vertical camera', camera)
bpy.context.collection.objects.link(owner)
owner.location = (0, .05, 8)
owner.rotation_euler = (0, 0, math.pi)
camera.type = 'ORTHO'
camera.ortho_scale = 2.1
bpy.context.scene.camera = owner
world = bpy.context.scene.world
world.use_nodes = True
world.node_tree.nodes['Background'].inputs[0].default_value = (.45, .45, .45, 1)
for location, energy in (((1, 2, 6), 300), ((-2, -2, 5), 200)):
    light = bpy.data.lights.new('Guide lighting', 'AREA')
    light.energy = energy
    light.size = 5
    item = bpy.data.objects.new('Guide lighting', light)
    bpy.context.collection.objects.link(item)
    item.location = location
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 12
scene.cycles.use_denoising = False
scene.render.resolution_x = scene.render.resolution_y = 1024
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.filepath = str(OUT/'true_overhead_3d_pose_guide.png')
scene.render.film_transparent = False
scene.view_settings.view_transform = 'Standard'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'overhead_camera_guide.blend'))
bpy.ops.render.render(write_still=True)
