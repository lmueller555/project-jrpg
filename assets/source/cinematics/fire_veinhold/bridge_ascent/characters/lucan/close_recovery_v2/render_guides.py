"""Reference-only canonical adult model and continuous35→contact48 recovery.

Original guide/script/reference bytes remain unchanged. This version starts from
source35's independently inverted3D feet and measured sword glove, then authors a
natural recovery toward right contact48 rather than copying frontal boot heights.
The guide is never rendered as final character art.
"""
from pathlib import Path
import importlib.util,json,math,sys
import bpy
from mathutils import Vector
HERE=Path(__file__).resolve().parent
BASE=HERE.parent
spec=importlib.util.spec_from_file_location('lucan_guide_v1',BASE/'render_pose_guides.py')
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
g.HERE=HERE

R_KEYS=[(35/60,(.14654406,.10810553,.83612708),(0,2,-1)),
        (39/60,(.14,.30,.72),(-.1,2.5,-3)),
        (43/60,(.13,.43,.34),(0,0,-5)),
        (45/60,(.13,.40,.18),(0,-1.8,-4)),
        (48/60,(.13,.30,.065),(0,-4,0))]
L_KEYS=[(35/60,(-.05180482,.41889645,.5397023),(-.2,-4,-1.5)),
        (39/60,(-.09,.1522,.42),(-.3,-4,-1.5)),
        (43/60,(-.12,-.1145,.30),(-.15,-4,0)),
        (45/60,(-.13,-.2478,.32),(0,-3,2)),
        (48/60,(-.13,-.35,.40),(0,3,.7))]
SOURCE35_KNEES={1:(.09693494,.4310709,1.21458752),-1:(-.04711827,.49064174,1.03450594)}

def fitted_forward(side):
    from mathutils import Matrix
    hip=Vector((side*.11,0,.95-.012*math.cos(4*math.pi*35/48)))
    foot=Vector((R_KEYS if side==1 else L_KEYS)[0][1]);knee=Vector(SOURCE35_KNEES[side]);axis=(foot-hip).normalized()
    bend=(knee-(foot+hip)/2).normalized()
    matrix=Matrix(((bend.x,axis.x,-1),(bend.y,axis.y,0),(bend.z,axis.z,0)))
    result=matrix.inverted()@Vector((0,1,0))
    return Vector((result.z,1,0))
SIDE_FORWARD={side:fitted_forward(side) for side in(1,-1)}


def motion_at(frame,keys):
    t=max(keys[0][0],min(keys[-1][0],frame/60))
    return tuple(g.curve(t,[(time,point[axis],velocity[axis]) for time,point,velocity in keys]) for axis in range(3))


def knee_at(hip,foot,side):
    hip,foot=Vector(hip),Vector(foot);delta=foot-hip;distance=delta.length
    if distance>=1:raise ValueError('Fixed .50+.50m leg cannot reach authored foot')
    axis=delta.normalized();forward=SIDE_FORWARD[side];bend=(forward-axis*forward.dot(axis)).normalized()
    return tuple((hip+foot)/2+bend*math.sqrt(.25-(distance/2)**2))


def hair_cap(center,mat):
    vertices=[];rings,segments=7,24
    for row in range(rings+1):
        phi=math.pi/2*row/rings
        for col in range(segments):
            theta=math.tau*col/segments
            vertices.append((center[0]+.11*math.sin(phi)*math.cos(theta),center[1]+.12*math.sin(phi)*math.sin(theta),center[2]+.113*math.cos(phi)))
    faces=[]
    for row in range(rings):
        for col in range(segments):faces.append((row*segments+col,row*segments+(col+1)%segments,(row+1)*segments+(col+1)%segments,(row+1)*segments+col))
    mesh=bpy.data.meshes.new('Bare hair upper hemisphere reference');mesh.from_pydata(vertices,[],faces);mesh.update();obj=bpy.data.objects.new('Dark hair cap reference',mesh);bpy.context.collection.objects.link(obj);obj.data.materials.append(mat)


def build_actor(frame,mats):
    if frame<35:frame+=48
    steel,gold,red,hair,leather=mats
    theta=math.tau*frame/48;recoil=-.012*math.cos(2*theta);hip_z=.95+recoil
    joint=g.material('Joint identity reference',(.75,.58,.18));skin=g.material('Face/neck identity reference',(.46,.28,.19))
    landmarks={}
    for side,keys in((1,R_KEYS),(-1,L_KEYS)):
        name='Right' if side==1 else 'Left';foot=motion_at(frame,keys);hip=(side*.11,0,hip_z);knee=knee_at(hip,foot,side)
        g.bone(name+' thigh',hip,knee,.075,steel);g.bone(name+' calf',knee,foot,.065,steel)
        g.ellipsoid(name+' visible knee marker',knee,(.085,.085,.085),joint)
        g.ellipsoid(name+' boot',foot,(.085,.15,.065),leather)
        landmarks[name.lower()+'_knee']=list(knee);landmarks[name.lower()+'_foot']=list(foot)
    g.ellipsoid('hips',(0,0,hip_z),(.17,.14,.11),red)
    torso=g.ellipsoid('torso',(0,0,1.30+recoil),(.18,.12,.30),red);torso.rotation_euler[0]=-.13
    for side in(1,-1):g.ellipsoid(('Right' if side==1 else 'Left')+' pauldron',(side*.17,.08,1.55+recoil),(.08,.10,.08),steel)
    # Canonical cranium was fitted from approvedsource35; genericmannequin1.69
    # was too low. Preserve its top near1.85m with anatomically sized axes.
    crest=-.012*math.cos(4*math.pi*35/48)
    head_z=1.7369+(recoil-crest)*.5
    g.ellipsoid('head skin reference',(0,.16,head_z),(.107,.115,.11),skin)
    g.ellipsoid('neck/collar reference',(0,.13,head_z-.145),(.07,.065,.075),steel)
    hair_cap((0,.16,head_z),hair)
    u=max(0,min(1,(frame-35)/13))
    right=(.1414556840+(.30-.1414556840)*u,.1058670036+(-.28-.1058670036)*u,1.30+(1.10-1.30)*u)
    left=(-.17-.08*u,.12+.12*u,1.25-.165*u)
    hands={1:right,-1:left}
    for side in(1,-1):
        name='Right' if side==1 else 'Left';shoulder=(side*.17,.08,1.49+recoil);hand=hands[side];elbow=g.elbow_at(shoulder,hand,side)
        if (Vector(hand)-Vector(shoulder)).length>.57:raise ValueError('Arm exceeds fixed human guide length')
        g.bone(name+' upperarm',shoulder,elbow,.068,steel);g.bone(name+' forearm',elbow,hand,.06,steel);g.ellipsoid(name+' glove',hand,(.065,.075,.06),leather)
    grip=Vector(right);guard=grip+Vector((.02,.10,-.12));angle=math.radians(17+28*(1-math.cos(theta))/2);horizontal=math.sqrt(.94**2-.65**2)
    point=guard+Vector((horizontal*math.sin(angle),horizontal*math.cos(angle),-.65))
    g.bone('Sword grip',tuple(grip+Vector((0,-.07,.07))),tuple(guard),.022,leather);g.bone('Sword blade',tuple(guard),tuple(point),.019,steel);g.bone('Sword guard',tuple(guard+Vector((-.10,0,0))),tuple(guard+Vector((.10,0,0))),.018,gold)
    cx,cy,cz=left[0]-.07,left[1]+.06,left[2]+.02
    vertices=[(cx-.15,cy-.04,cz+.32),(cx+.15,cy-.04,cz+.32),(cx+.145,cy-.01,cz-.02),(cx,cy-.06,cz-.38),(cx-.14,cy-.01,cz-.02),(cx,cy+.06,cz)]
    pitch=math.radians(20*(1-u))
    vertices=[(x,cy+(y-cy)*math.cos(pitch)+(z-cz)*math.sin(pitch),cz-(y-cy)*math.sin(pitch)+(z-cz)*math.cos(pitch)) for x,y,z in vertices]
    mesh=bpy.data.meshes.new('Upright shield');mesh.from_pydata(vertices,[],[(i,(i+1)%5,5) for i in range(5)]);mesh.update();obj=bpy.data.objects.new('Left upright shield reference',mesh);bpy.context.collection.objects.link(obj);obj.data.materials.append(red)
    for a,b in zip(vertices[:5],vertices[1:5]+vertices[:1]):g.bone('Shield rim',a,b,.014,gold)
    g.ellipsoid('Trailing tabard',(0,-.14-.035*math.sin(theta-.4),.99+recoil),(.23,.25,.065),red)
    return {'head_centre':[0,.16,head_z],'head_radius_x':.11,'hip':[0,0,hip_z],
            'right_hand':list(right),'left_hand':list(left),**landmarks}


g.build_actor=build_actor
if __name__=='__main__':
    (HERE/'canonical_model.json').write_text(json.dumps({'purpose':'authoring_reference_only; not finalart or acceptance','canonical_head_base_z':1.7369,'head_axes':[.11,.12,.113],'pauldron_pair_outer_width_m':.50,'source35_inverted_feet':{'right':R_KEYS[0][1],'left':L_KEYS[0][1]},'source35_measured_knee_and_boot_pixels':{'right_knee':[454,620],'right_boot_center':[437,684],'left_knee':[540,730],'left_boot_center':[540,920]},'source35_fitted_knees':SOURCE35_KNEES,'right_keyframes':R_KEYS,'left_keyframes':L_KEYS,'source35_measured_right_glove_pixels':[435,477],'source35_inverted_right_glove':R_KEYS[0][1] if False else [.1414556840,.1058670036,1.30],'contact_frames':[0,24],'cycle_seconds':.8,'body_speed_metres_per_second':4},indent=2)+'\n')
    g.main()
