"""Blender camera/volume AUTHORING REFERENCES ONLY, never runtime figures.

Adapted from Iselin's accepted overhead planning scene. Final image-authored
soldier anatomy is independent whole-figure artwork, not rendered by this tool.
"""
import bpy, math, json, sys
from pathlib import Path
from mathutils import Vector, Matrix
from bpy_extras.object_utils import world_to_camera_view
REPO=Path('/workspace/project-jrpg');sys.path.insert(0,str(REPO))
from cinematic_bridge_ascent import actor_states_at
HERE=Path(__file__).resolve().parent.parent
OUT=HERE/'authoring/blender_calibrated_guides';OUT.mkdir(exist_ok=True)
W,H=1024,1536;PPM=500;ANCHOR=(512,960)

def material(name,col):
 m=bpy.data.materials.new(name);m.diffuse_color=(*col,1);return m

def ell(name,loc,scale,mat):
 bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=12,location=loc);o=bpy.context.object;o.name=name;o.scale=scale;o.data.materials.append(mat);return o

def bone(name,a,b,r,mat):
 a,b=Vector(a),Vector(b);bpy.ops.mesh.primitive_cylinder_add(vertices=18,radius=r,depth=(b-a).length,location=(a+b)/2);o=bpy.context.object;o.name=name;o.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler();o.data.materials.append(mat);return o

def two_bone(a,b,l1,l2,bend):
 a,b=Vector(a),Vector(b);v=b-a;dist=min(l1+l2-.001,max(.01,v.length));direction=v.normalized();along=(l1*l1-l2*l2+dist*dist)/(2*dist);normal=Vector(bend);normal=(normal-direction*normal.dot(direction)).normalized();return a+direction*along+normal*math.sqrt(max(0,l1*l1-along*along))

def foot(q):
 # Continuous authoring plan informed by the reviewed Crown phase chart.
 # Support ends near9/48;18/48 is flight with the opposite foot approaching.
 keys=[(0,.45,.02),(.125,-.05,.07),(.20,-.42,.08),(.25,-.50,.25),(.375,-.45,.43),(.5,-.42,.39),(.625,-.15,.46),(.75,.20,.55),(.875,.50,.19),(1,.45,.02)]
 q%=1
 for i in range(len(keys)-1):
  if keys[i][0]<=q<=keys[i+1][0]:break
 t0,*a=keys[i];t1,*b=keys[i+1];u=(q-t0)/(t1-t0);out=[]
 for component in (1,2):
  left=keys[i-1] if i else (keys[-2][0]-1,*keys[-2][1:]);right=keys[i+2] if i+2<len(keys) else (keys[1][0]+1,*keys[1][1:]);m0=(keys[i+1][component]-left[component])/(keys[i+1][0]-left[0]);m1=(right[component]-keys[i][component])/(right[0]-keys[i][0]);h00=2*u**3-3*u**2+1;h10=u**3-2*u**2+u;h01=-2*u**3+3*u**2;h11=u**3-u**2;out.append(h00*a[component-1]+h10*(t1-t0)*m0+h01*b[component-1]+h11*(t1-t0)*m1)
 return out[0],max(.02,out[1])

def build(sample):
 bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
 silver=material('Steel volume guide',(.50,.57,.65));navy=material('Navy costume guide',(.035,.07,.18));trousers=material('Charcoal leg guide',(.13,.14,.17));leather=material('Leather glove and boot guide',(.27,.14,.07));skin=material('Face under helmet guide',(.50,.35,.23))
 frame=sample['phase'];phi=2*math.pi*frame/48;bob=-.025*math.cos(2*phi);hips_z=.92+bob;points={}
 for side,x,offset in [('R',.12,0),('L',-.12,.5)]:
  q=(frame/48+offset)%1;f,z=foot(q);hip=(x,0,hips_z);ankle=(x,f,z+.13);knee=two_bone(hip,ankle,.44,.46,(0,1,0));points.update({side+'_hip':list(hip),side+'_knee':list(knee),side+'_ankle':list(ankle)})
  bone(side+' thigh',hip,knee,.085,trousers);bone(side+' calf',knee,ankle,.075,trousers);ell(side+' knee plate',knee+Vector((0,.035,.015)),(.105,.08,.09),silver);boot=ell(side+' boot',(x,f+.07,z+.085),(.085,.16,.085),leather);boot.rotation_euler.x=.1*math.sin(2*math.pi*q)
 ell('pelvis',(0,0,hips_z),(.21,.16,.12),navy);torso=ell('forward leaning steel torso',(0,.08,1.26+bob),(.23,.15,.29),silver);torso.rotation_euler.x=-.16
 # Two short tabard tails stream behind the pelvis, not a frontal torso below
 # the head in an overhead picture. These are source-only simple volumes.
 for side,x in [('R',.12),('L',-.12)]:
  tail=ell(side+' navy trailing tabard',(x,-.18,hips_z-.08),(.12,.25,.025),navy);tail.rotation_euler.z=(.08 if side=='R' else -.08)*math.sin(phi)
 for side,sign in [('R',1),('L',-1)]:
  shoulder=(sign*.23,.15,1.43+bob);A=-math.cos(phi)
  hand=(.29,.10+.30*A,1.13+.10*A+bob) if side=='R' else (-.40,.13-.12*A,1.18-.04*A+bob)
  elbow=two_bone(shoulder,hand,.30,.28,(sign*.35,-.2,-1));points.update({side+'_shoulder':list(shoulder),side+'_elbow':list(elbow),side+'_glove':list(hand)})
  ell(side+' steel shoulder',shoulder,(.14,.14,.11),silver);bone(side+' upper arm',shoulder,elbow,.075,silver);bone(side+' forearm',elbow,hand,.065,silver);ell(side+' leather glove',hand,(.065,.075,.065),leather)
  if side=='R':
   h=Vector(hand);tip=h+Vector((.30,.18,-.75));bone('one sword projected blade',h,tip,.018,silver);bone('one sword guard',h+Vector((-.07,0,0)),h+Vector((.07,0,0)),.018,silver);points['sword_tip']=list(tip)
  else:
   normal=Vector((-.65,.76,.02)).normalized();bpy.ops.mesh.primitive_cylinder_add(vertices=48,radius=.27,depth=.045,location=Vector(hand)+Vector((-.065,0,.02)));o=bpy.context.object;o.name='upright round shield, true angle';o.rotation_euler=normal.to_track_quat('Z','Y').to_euler();o.data.materials.append(silver)
 ell('head',(0,.23,1.62+bob),(.13,.145,.14),skin);ell('helmet crown ahead of hips',(0,.22,1.65+bob),(.14,.16,.14),silver);ell('helmet brim',(0,.23,1.575+bob),(.17,.18,.018),silver);points['helmet_crown']=[0,.22,1.65+bob];points['pelvis']=[0,0,hips_z]
 elevation=math.radians(sample['elevation']);azimuth=math.radians(sample['azimuth']);ray=Vector((math.sin(azimuth)*math.cos(elevation),math.cos(azimuth)*math.cos(elevation),math.sin(elevation)));target=Vector((0,0,.9));view=-ray;right=Vector((-1,0,0));right=(right-view*right.dot(view)).normalized();up=right.cross(view).normalized()
 data=bpy.data.cameras.new('Actual Crown camera ray');cam=bpy.data.objects.new('Actual Crown camera ray',data);bpy.context.collection.objects.link(cam);cam.location=target+ray*8;cam.rotation_euler=Matrix((right,up,-view)).transposed().to_quaternion().to_euler();data.type='ORTHO';data.ortho_scale=H/PPM;scene=bpy.context.scene;scene.camera=cam;scene.render.resolution_x=W;scene.render.resolution_y=H;scene.render.resolution_percentage=100
 bpy.context.view_layer.update();p0=world_to_camera_view(scene,cam,Vector((0,0,0)));p1=world_to_camera_view(scene,cam,right);actualppm=(p1.x-p0.x)*W;data.ortho_scale*=actualppm/PPM;bpy.context.view_layer.update();p0=world_to_camera_view(scene,cam,Vector((0,0,0)));px=p0.x*W;py=(1-p0.y)*H;cam.location+=right*(-(ANCHOR[0]-px)/PPM)+up*((ANCHOR[1]-py)/PPM);bpy.context.view_layer.update()
 scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.30,.30,.30,1)
 for loc,power in [((1,2,6),400),((-2,-2,5),250)]:
  l=bpy.data.lights.new('Source guide light','AREA');l.energy=power;l.size=5;o=bpy.data.objects.new('Source guide light',l);bpy.context.collection.objects.link(o);o.location=loc
 scene.render.engine='CYCLES';scene.cycles.samples=8;scene.cycles.use_denoising=False;scene.render.film_transparent=False;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='Standard';scene.render.filepath=str(OUT/(sample['id']+'.png'))
 projected={}
 for key,p in points.items():
  q=world_to_camera_view(scene,cam,Vector(p));projected[key]=[round(q.x*W,4),round((1-q.y)*H,4)]
 record={**sample,'canvas':[W,H],'anchor':list(ANCHOR),'pixels_per_metre':PPM,'world_points_authoring_plan':points,'projected_points_authoring_plan':projected,'guide_only':True,'construction':'True Blender3D camera/pose planning reference, never a final/runtime sprite'};(OUT/(sample['id']+'.json')).write_text(json.dumps(record,indent=2)+'\n');bpy.ops.render.render(write_still=True)

samples=[]
for t in [0,.4,.8,1.2,1.6,2.2]:
 a=next(a for a in actor_states_at(t)['runners'] if a['id']=='crown_soldier');samples.append({'id':f'time_{round(t*60):03d}','time':t,'phase':a['frame_index'],'elevation':a['view_elevation_degrees'],'azimuth':a['view_azimuth_degrees'],'native_pixels_per_metre':a['pixels_per_metre']})
samples.append({'id':'model90_phase18','phase':18,'elevation':90,'azimuth':0})
for sample in samples:build(sample)
(OUT/'samples.json').write_text(json.dumps(samples,indent=2)+'\n')
