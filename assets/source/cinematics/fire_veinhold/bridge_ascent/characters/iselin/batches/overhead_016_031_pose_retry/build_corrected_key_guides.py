"""Render camera/pose authoring guides only; no guide pixels become character art.

Use Blender4.3+ with --background --python this-file -- --startN --stopN.
The generated anatomy is reference scaffolding, not a sprite/animation exporter.
"""
from pathlib import Path
import argparse,json,math,sys
ROOT=Path('/workspace/project-jrpg')
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from cinematic_bridge_ascent import actor_states_at,camera_at
BASE=Path(__file__).resolve().parent

def main():
 import bpy
 from mathutils import Vector,Matrix
 from bpy_extras.object_utils import world_to_camera_view
 parser=argparse.ArgumentParser();parser.add_argument('--kind',choices=['transition','overhead'],default='transition');parser.add_argument('--parity',choices=['even','odd','all'],default='even');parser.add_argument('--start',type=int,default=0);parser.add_argument('--stop',type=int,default=50);args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
 bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
 def material(name,col):
  m=bpy.data.materials.new(name);m.diffuse_color=(*col,1);return m
 white=material('White head/hair guide',(.8,.82,.86));blue=material('Blue clothing guide',(.055,.11,.30));gray=material('Gray leg guide',(.2,.22,.26));skin=material('Hand guide',(.64,.50,.39))
 objects={}
 def ell(name,loc,scale,mat):
  bpy.ops.mesh.primitive_uv_sphere_add(segments=16,ring_count=8,location=loc);o=bpy.context.object;o.name=name;o.scale=scale;o.data.materials.append(mat);objects[name]=o;return o
 def bone(name,a,b,r,mat):
  a,b=Vector(a),Vector(b);bpy.ops.mesh.primitive_cylinder_add(vertices=14,radius=r,depth=(b-a).length,location=(a+b)/2);o=bpy.context.object;o.name=name;o.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler();o['guide_rest_radius']=r;o['guide_rest_length']=(b-a).length;o.data.materials.append(mat);o['guide_base_radius']=r;o['guide_base_depth']=(b-a).length;objects[name]=o;return o
 def change_bone(name,a,b,r):
  a,b=Vector(a),Vector(b);o=objects[name];o.location=(a+b)/2;o.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler();o.scale=(r/o['guide_rest_radius'],r/o['guide_rest_radius'],(b-a).length/o['guide_rest_length'])
 def gait(phase):
  hipz=.82-.025*math.cos(4*math.pi*phase);p={};hips={'R':(.105,0,hipz),'L':(-.105,0,hipz)}
  for side,offset in [('R',0),('L',.5)]:
   u=(phase-offset)%1
   if u<=.25:y=.4-.8*u/.25;z=.05
   else:
    s=(u-.25)/.75;y=-.4+.8*(3*s*s-2*s*s*s);z=.05+.55*math.sin(math.pi*s)**1.2
   foot=(.12 if side=='R' else -.12,y,z);h=hips[side];dy,dz=foot[1]-h[1],foot[2]-h[2];dist=math.hypot(dy,dz);height=math.sqrt(max(0,.44**2-(dist/2)**2));knee=(h[0],(h[1]+foot[1])/2-dz/dist*height,(h[2]+foot[2])/2+dy/dist*height)
   p[side+'hip']=h;p[side+'knee']=knee;p[side+'foot']=foot
   swing=(-1 if side=='R' else 1)*math.cos(2*math.pi*phase)
   sh=(.22 if side=='R' else -.22,.10,hipz+.50);el=(.34 if side=='R' else -.34,.12*swing,hipz+.28);hand=(.30 if side=='R' else -.30,.29*swing,hipz+.29+.13*swing)
   p[side+'shoulder']=sh;p[side+'elbow']=el;p[side+'hand']=hand
  p['hips']=(0,0,hipz);p['torso']=(0,.06,hipz+.25);p['head']=(0,.22,hipz+.73);return p
 first=gait(10/48)
 for side in ('R','L'):
  bone(side+'thigh',first[side+'hip'],first[side+'knee'],.075,gray);bone(side+'calf',first[side+'knee'],first[side+'foot'],.065,gray);ell(side+'boot',first[side+'foot'],(.082,.13,.06),gray)
  bone(side+'upperarm',first[side+'shoulder'],first[side+'elbow'],.065,blue);bone(side+'forearm',first[side+'elbow'],first[side+'hand'],.06,blue);ell(side+'fist',first[side+'hand'],(.065,.07,.055),skin)
 ell('hips',first['hips'],(.2,.13,.13),blue);ell('torso',first['torso'],(.22,.14,.27),blue);objects['torso'].rotation_euler[0]=-.18
 ell('crown',first['head'],(.135,.16,.17),white)
 # Small attachment hints keep anatomical costume sides clear without hiding the gait.
 ell('right-mantle-attachment',(.25,.02,1.30),(.11,.13,.055),blue)
 for i in range(5):bone('hair'+str(i),(.035*i,.18-i*.018,1.64),(.30+i*.055,-.50+i*.03,1.35),.028,white)
 for i in range(3):bone('left-forward-braid'+str(i),(-.16,.22+i*.02,1.46-i*.09),(-.17,.24+i*.02,1.37-i*.09),.034,white)
 camdata=bpy.data.cameras.new('Pose camera');cam=bpy.data.objects.new('Pose camera',camdata);bpy.context.collection.objects.link(cam);bpy.context.scene.camera=cam
 scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=8;scene.cycles.use_denoising=False;scene.render.resolution_x=1024;scene.render.resolution_y=1536;scene.render.resolution_percentage=50;scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False;scene.view_settings.view_transform='Standard';scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.4,.4,.4,1)
 for loc,power in [((1,2,6),250),((-2,-2,5),160)]:
  ld=bpy.data.lights.new('Guide light','AREA');ld.energy=power;ld.shape='DISK';ld.size=5;ob=bpy.data.objects.new('Guide light',ld);bpy.context.collection.objects.link(ob);ob.location=loc
 out=BASE/'guides_corrected'/args.kind;out.mkdir(parents=True,exist_ok=True);records=[]
 selected=list(range(8 if args.parity!='odd' else 9,120,1 if args.parity=='all' else 2)) if args.kind=='transition' else [0,8,16,24,32,40]
 for index in selected[args.start:args.stop]:
  t=index/60 if args.kind=='transition' else 0;state=next(a for a in actor_states_at(t)['runners'] if a['id']=='iselin');phase=state['cycle_phase']/.8 if args.kind=='transition' else index/48;p=gait(phase)
  for side in ('R','L'):
   change_bone(side+'thigh',p[side+'hip'],p[side+'knee'],.075);change_bone(side+'calf',p[side+'knee'],p[side+'foot'],.065);objects[side+'boot'].location=p[side+'foot'];change_bone(side+'upperarm',p[side+'shoulder'],p[side+'elbow'],.065);change_bone(side+'forearm',p[side+'elbow'],p[side+'hand'],.06);objects[side+'fist'].location=p[side+'hand']
  for label in ('hips','torso'):objects[label].location=p[label]
  objects['crown'].location=p['head']
  if args.kind=='transition':
   c=camera_at(t);cam.location=(c['position'][0]-state['world_position_metres'][0],c['position'][1]-state['world_position_metres'][1],c['position'][2]);f=Vector(c['forward']);up=Vector(c['up']);right=Vector(c['right']);cam.rotation_euler=Matrix((right,up,-f)).transposed().to_quaternion().to_euler();camdata.type='PERSP';camdata.sensor_fit='VERTICAL';camdata.sensor_height=32;depth=state['depth_metres'];camdata.lens=500*depth*32/1536
  else:
   cam.location=(0,0,8);cam.rotation_euler=(0,0,math.pi);camdata.type='ORTHO';camdata.ortho_scale=3.072
  camdata.shift_x=camdata.shift_y=0;bpy.context.view_layer.update()
  root=Vector((0,0,0));v=world_to_camera_view(scene,cam,root);base=(v.x,v.y)
  camdata.shift_x=.01;bpy.context.view_layer.update();v=world_to_camera_view(scene,cam,root);sx=(v.x-base[0])/.01;camdata.shift_x=0
  camdata.shift_y=.01;bpy.context.view_layer.update();v=world_to_camera_view(scene,cam,root);sy=(v.y-base[1])/.01;camdata.shift_y=0
  camdata.shift_x=(.5-base[0])/sx;camdata.shift_y=(.375-base[1])/sy;bpy.context.view_layer.update()
  filename=f'guide_{index:03d}.png';scene.render.filepath=str(out/filename);bpy.ops.render.render(write_still=True)
  landmarks={name:[world_to_camera_view(scene,cam,Vector(value)).x*512,(1-world_to_camera_view(scene,cam,Vector(value)).y)*768] for name,value in p.items()}
  records.append({'index':index,'phase_frame':state['frame_index'] if args.kind=='transition' else index,'view_elevation':state['view_elevation_degrees'] if args.kind=='transition' else 90,'guide_file':filename,'ground_anchor':[256,480],'landmarks_guide':landmarks,'guide_only':True})
 (out/f'metadata_{args.parity}_{args.start:03d}_{args.stop:03d}.json').write_text(json.dumps(records,indent=2)+'\n')
 print('GUIDEONLY',args.kind,len(records))
if __name__=='__main__':main()
