import bpy, math
from mathutils import Vector
from pathlib import Path
out=Path('/workspace/project-jrpg/assets/source/cinematics/fire_veinhold/bridge_ascent/characters/iselin/keys')
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
def mat(name,col):
 m=bpy.data.materials.new(name);m.diffuse_color=(*col,1);return m
white=mat('White hair camera guide',(0.8,.82,.88));blue=mat('Blue coat camera guide',(.055,.11,.32));gray=mat('Gray limbs camera guide',(.21,.23,.27));skin=mat('Hands camera guide',(.65,.51,.4))
def ell(name,loc,scale,m):
 bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=12,location=loc);o=bpy.context.object;o.name=name;o.scale=scale;o.data.materials.append(m);return o
def bone(name,a,b,r,m):
 a,b=Vector(a),Vector(b);mid=(a+b)/2;bpy.ops.mesh.primitive_cylinder_add(vertices=18,radius=r,depth=(b-a).length,location=mid);o=bpy.context.object;o.name=name;o.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler();o.data.materials.append(m);return o
hips=[(.11,0,1.0),(-.11,0,1.0)];rk=(.12,-.24,.52);rf=(.13,-.56,.07);lk=(-.12,.40,.78);lf=(-.12,.18,.42)
for name,a,b in [('Rthigh',hips[0],rk),('Rcalf',rk,rf),('Lthigh',hips[1],lk),('Lcalf',lk,lf)]:bone(name,a,b,.075,gray)
ell('Rboot',rf,(.09,.16,.06),gray);ell('Lboot',lf,(.09,.14,.07),gray)
ell('hips',(0,0,1.0),(.22,.15,.12),blue);o=ell('torso',(0,.065,1.28),(.23,.14,.3),blue);o.rotation_euler[0]=-.16
for name,shoulder,elbow,hand in [('R',(.23,.1,1.43),(.36,-.12,1.23),(.34,-.28,1.15)),('L',(-.23,.1,1.43),(-.36,.27,1.28),(-.33,.43,1.28))]:
 bone(name+'upperarm',shoulder,elbow,.075,blue);bone(name+'forearm',elbow,hand,.065,blue);ell(name+'hand',hand,(.065,.075,.06),skin)
ell('head crown',(0,.22,1.76),(.14,.17,.18),white)
ell('right mantle',(.3,-.35,1.24),(.37,.58,.085),blue)
# Loose hair and mantle stream behind/right in world space; this is pose geometry only.
for i in range(7):
 a=(.03+i*.015,.2-i*.025,1.81);b=(.25+i*.05,-.7+i*.035,1.42)
 bone('Hair camera volume'+str(i),a,b,.042,white)
for i in range(4):bone('Forward left braid'+str(i),(-.14,.23+i*.025,1.61-i*.10),(-.16,.26+i*.025,1.51-i*.10),.045,white)
cam=bpy.data.cameras.new('Exact vertical orthographic');o=bpy.data.objects.new('Exact vertical orthographic',cam);bpy.context.collection.objects.link(o);o.location=(0,-.05,8);o.rotation_euler=(0,0,math.pi);cam.type='ORTHO';cam.ortho_scale=2.2;bpy.context.scene.camera=o
world=bpy.context.scene.world;world.color=(.5,.5,.5);world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.5,.5,.5,1)
for loc,power in [((1,2,6),300),((-2,-2,5),200)]:
 l=bpy.data.lights.new('Guide lighting','AREA');l.energy=power;l.shape='DISK';l.size=5;ob=bpy.data.objects.new('Guide lighting',l);bpy.context.collection.objects.link(ob);ob.location=loc
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=12;scene.cycles.use_denoising=False;scene.render.resolution_x=1024;scene.render.resolution_y=1024;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.filepath=str(out/'overhead_3d_camera_pose_guide.png');scene.render.film_transparent=False;scene.view_settings.view_transform='Standard'
bpy.ops.wm.save_as_mainfile(filepath=str(out/'overhead_camera_guide.blend'));bpy.ops.render.render(write_still=True)
