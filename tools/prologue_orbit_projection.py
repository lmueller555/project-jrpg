"""Project approved artwork onto a dense, world-space cinematic relief mesh.

The approved first/final views are production plates, not independently
generated orbit frames. The opening reconstructs dense 2.5D surfaces with
separated semantic silhouettes at actual depth discontinuities. The final
bridge uses rigid, independent stasis cutouts, a distant backdrop and an
actual horizontal ground plane; it has no reconstructed depth field.
Camera movement reveals parallax and geometric occlusion. The shared
fortress/terrain scene supplies surfaces unseen in the approved plates.
"""
from __future__ import annotations

import math
from pathlib import Path


def _smooth(a, b, value):
    if a == b:
        return float(value >= b)
    t = max(0.0, min(1.0, (value-a)/(b-a)))
    return t*t*(3.0-2.0*t)


def _mix(a, b, weight):
    return a+(b-a)*max(0.0, min(1.0, weight))


def _rounded_region(u, v, left, top, right, bottom, soft=.04):
    """Smooth superellipse with rounded corners, never a rectangular cutout."""
    cx, cy = (left+right)*.5, (top+bottom)*.5
    rx, ry = (right-left)*.5, (bottom-top)*.5
    distance = (abs((u-cx)/rx)**6 + abs((v-cy)/ry)**6)**(1/6)
    return 1.0-_smooth(1.0-soft*4.0, 1.0+soft*4.0, distance)


def _plane_depth(origin, direction, height, minimum=.3, maximum=4000.0):
    if direction.z >= -1e-6:
        return maximum
    distance=(height-origin.z)/direction.z
    return max(minimum, min(maximum, distance)) if distance > 0 else maximum


def _inside_polygon(u,v,points):
    inside=False
    a=points[-1]
    for b in points:
        if (a[1]>v)!=(b[1]>v):
            crossing=(b[0]-a[0])*(v-a[1])/(b[1]-a[1])+a[0]
            if u<crossing:
                inside=not inside
        a=b
    return inside


_ISLAND_OUTLINE=((.12,.57),(.18,.49),(.19,.42),(.23,.37),
                 (.28,.39),(.35,.36),(.39,.33),(.43,.30),
                 (.52,.30),(.58,.33),(.64,.30),(.68,.38),
                 (.77,.40),(.88,.45),(.94,.52),(.99,.54),
                 (1.02,.73),(.94,.78),(.87,.80),(.76,.80),
                 (.68,.81),(.61,.79),(.54,.79),(.48,.81),
                 (.43,.77),(.35,.75),(.27,.72),(.20,.68),(.17,.63))
_CONE_OUTLINE=((.28,.45),(.34,.39),(.43,.335),(.48,.305),
               (.53,.31),(.56,.34),(.59,.39),(.64,.46),
               (.68,.50),(.59,.51),(.48,.52),(.35,.50))


def _opening_surface(u,v,origin,direction):
    """Return a semantic surface ID and physical depth, with real boundaries.

    These IDs are intentionally discontinuous.  Connecting the near keep to
    distant water produces a stretched roof-shaped curtain at oblique angles;
    the mesh builder instead leaves that silhouette open for the shared scene.
    """
    if v<.315:
        label,depth=0,9000.0
    else:
        label,depth=1,_plane_depth(origin,direction,0,maximum=9000)
    # The physical moon is much nearer than the theatrical sky enclosure.
    # Match its front surface so the brief handoff cannot create two discs.
    moon_radius=math.sqrt(((u-.098)/.060)**2+((v-.0484)/.090)**2)
    if moon_radius<1:
        # Keep the sky's connected semantic ID: cutting another silhouette
        # here would expose an annular gap around the painted blue corona.
        depth=_mix(3340.0,9000.0,_smooth(.50,1.0,moon_radius))
    if u<.245 and .285<v<.445 and _rounded_region(u,v,-.14,.285,.255,.42,.045)>.5:
        label,depth=2,2500.0
    if _inside_polygon(u,v,_ISLAND_OUTLINE):
        label,depth=3,805.0+95.0*(.55-v)
    if _inside_polygon(u,v,_CONE_OUTLINE):
        label,depth=4,900.0
    if .72<u<.90 and .30<v<.385 and _rounded_region(u,v,.72,.30,.90,.385,.035)>.5:
        label,depth=5,5100.0
    if _rounded_region(u,v,.285,.455,.468,.615,.018)>.5:
        label,depth=6,795.0
    if _rounded_region(u,v,.585,.475,.785,.675,.018)>.5:
        label,depth=7,790.0
    if _rounded_region(u,v,.575,.315,.742,.570,.018)>.5:
        label,depth=8,850.0
    if _rounded_region(u,v,.475,.397,.605,.654,.018)>.5:
        label,depth=9,755.0
    if _rounded_region(u,v,.410,.644,.585,.802,.018)>.5:
        label,depth=10,690.0
    if _rounded_region(u,v,.757,.535,1.025,.760,.025)>.5:
        label,depth=11,740.0
    # Deck, under-deck trusses and their piers share one separated near object.
    line=.977-.54*u
    if u<.46 and v>.705 and abs(v-line)<(.035+.018*(1-u)):
        label,depth=12,450.0+240.0*max(0.0,min(1.0,u/.52))
    return label,max(50.0,min(9000.0,depth))


def _opening_depth(u,v,origin,direction):
    return _opening_surface(u,v,origin,direction)[1]


def _semantic_interior(labels,nx,ny,radius=6):
    """Distance from each separated surface edge, capped at six grid steps."""
    from collections import deque
    distances=[radius]*len(labels); queue=deque()
    for j in range(ny):
        for i in range(nx):
            index=j*nx+i; label=labels[index]
            edge=False
            for yy in range(max(0,j-1),min(ny,j+2)):
                for xx in range(max(0,i-1),min(nx,i+2)):
                    if labels[yy*nx+xx]!=label:
                        edge=True; break
                if edge:
                    break
            if edge:
                distances[index]=0; queue.append(index)
    # Multi-source breadth-first propagation is bounded to the narrow rim;
    # deep interiors need no traversal and retain a value of one.
    while queue:
        index=queue.popleft(); distance=distances[index]+1
        if distance>=radius:
            continue
        i=index%nx; j=index//nx
        for neighbour in ((index-1 if i else -1),
                          (index+1 if i+1<nx else -1),
                          (index-nx if j else -1),
                          (index+nx if j+1<ny else -1)):
            if neighbour>=0 and distance<distances[neighbour]:
                distances[neighbour]=distance; queue.append(neighbour)
    return [min(1.0,distance/radius) for distance in distances]


def create_frozen_stage(bpy,camera,background_path,guard_paths,
                        name="Frozen bridge separated stasis"):
    """Return one all-rigid mesh with scenery, a deck and four ice actors.

    ``guard_paths`` contains four full-canvas RGBA images in this order:
    left back, left front, right middle, far right.  Their complete silhouettes
    are fixed on separate world-space planes at 5.5, 3.4, 4.5 and 5.5 metres.
    Transparent image pixels expose the empty bridge. The background is a
    distant overscanned quad and the deck is one real horizontal plane; no
    depth-field triangles connect scenery, deck or character silhouettes.
    """
    from mathutils import Vector
    paths=[Path(background_path),*[Path(path) for path in guard_paths]]
    if len(paths)!=5:
        raise ValueError("Frozen bridge requires four complete guard cutouts")
    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(path)
    images=[bpy.data.images.load(str(path.resolve()),check_existing=True) for path in paths]
    if any(tuple(image.size)!=tuple(images[0].size) for image in images[1:]):
        raise ValueError("Guard cutouts must retain the background's full canvas")
    bpy.context.view_layer.update()
    frame=camera.data.view_frame(scene=bpy.context.scene)
    left=min(p.x for p in frame); right=max(p.x for p in frame)
    bottom=min(p.y for p in frame); top=max(p.y for p in frame)
    z=sum(p.z for p in frame)/len(frame)
    origin=camera.matrix_world.translation.copy()
    rotation=camera.matrix_world.to_quaternion()
    def local_ray(u,v):
        return Vector((left+(right-left)*u,top+(bottom-top)*v,z))
    vertices=[]; coordinates=[]; faces=[]; slots=[]
    # Three-times overscan has UVs outside 0..1. EXTEND holds the far sky's
    # edge colours rather than exposing a rectangular black card boundary.
    for u,v in ((-1,-1),(-1,2),(2,2),(2,-1)):
        point=local_ray(u,v)*(700.0/-z)
        vertices.append(tuple(origin+rotation@point)); coordinates.append((u,1-v))
    faces.append((0,1,2,3)); slots.append(0)
    depths=(5.5,3.4,4.5,5.5)
    for slot,distance in enumerate(depths,1):
        start=len(vertices)
        for u,v in ((0,0),(0,1),(1,1),(1,0)):
            # Constant optical depth makes each complete silhouette a rigid
            # plane. A normalized-ray distance would bend its four corners.
            point=local_ray(u,v)*(distance/-z)
            vertices.append(tuple(origin+rotation@point))
            coordinates.append((u,1-v))
        faces.append(tuple(start+k for k in range(4))); slots.append(slot)
    start=len(vertices)
    ground_forward=rotation@Vector((0,0,-1)); ground_forward.z=0
    ground_forward.normalize()
    ground_right=ground_forward.cross(Vector((0,0,1))).normalized()
    for lateral,along in ((-8.5,-1000),(8.5,-1000),(8.5,1000),(-8.5,1000)):
        point=origin+ground_right*lateral+ground_forward*along
        vertices.append((point.x,point.y,12.65)); coordinates.append((0,0))
    faces.extend(((start,start+1,start+2),(start,start+2,start+3)))
    slots.extend((5,5))
    mesh=bpy.data.meshes.new(name+" rigid background deck and actor mesh")
    mesh.from_pydata(vertices,[],faces); mesh.update()
    uv=mesh.uv_layers.new(name="Approved frozen bridge full canvas")
    for polygon,slot in zip(mesh.polygons,slots):
        polygon.material_index=slot
        for loop_index in polygon.loop_indices:
            uv.data[loop_index].uv=coordinates[mesh.loops[loop_index].vertex_index]
    for index,image in enumerate(images):
        material=bpy.data.materials.new(name+(" empty bridge" if index==0 else f" complete ice guard {index}"))
        material.use_nodes=True; nodes=material.node_tree.nodes; nodes.clear(); links=material.node_tree.links
        output=nodes.new("ShaderNodeOutputMaterial")
        emission=nodes.new("ShaderNodeEmission"); emission.inputs["Strength"].default_value=1
        texture=nodes.new("ShaderNodeTexImage"); texture.image=image
        texture.interpolation="Linear"; texture.extension="CLIP" if index else "EXTEND"
        texcoord=nodes.new("ShaderNodeUVMap"); texcoord.uv_map=uv.name
        links.new(texcoord.outputs["UV"],texture.inputs["Vector"])
        links.new(texture.outputs["Color"],emission.inputs["Color"])
        if index:
            transparent=nodes.new("ShaderNodeBsdfTransparent")
            mix=nodes.new("ShaderNodeMixShader")
            links.new(texture.outputs["Alpha"],mix.inputs[0])
            links.new(transparent.outputs[0],mix.inputs[1])
            links.new(emission.outputs[0],mix.inputs[2])
            links.new(mix.outputs[0],output.inputs["Surface"])
        else:
            # Overscan must stay opaque without repeating entire edge rows
            # into long streaks. Fade only the outer eight native pixels to
            # a calm night-haze colour; preserve the original interior photo.
            separate=nodes.new("ShaderNodeSeparateXYZ")
            links.new(texcoord.outputs["UV"],separate.inputs[0])
            margins=[]
            for axis,pixels in (("X",960),("Y",640)):
                opposite=nodes.new("ShaderNodeMath"); opposite.operation="SUBTRACT"; opposite.inputs[0].default_value=1
                links.new(separate.outputs[axis],opposite.inputs[1])
                margin=nodes.new("ShaderNodeMath"); margin.operation="MINIMUM"
                links.new(separate.outputs[axis],margin.inputs[0]); links.new(opposite.outputs[0],margin.inputs[1])
                width=nodes.new("ShaderNodeMath"); width.operation="MULTIPLY"; width.inputs[1].default_value=pixels/8
                links.new(margin.outputs[0],width.inputs[0]); margins.append(width.outputs[0])
            feather=nodes.new("ShaderNodeMath"); feather.operation="MINIMUM"; feather.use_clamp=True
            links.new(margins[0],feather.inputs[0]); links.new(margins[1],feather.inputs[1])
            haze=nodes.new("ShaderNodeMixRGB"); haze.inputs[1].default_value=(.008,.020,.050,1)
            links.new(feather.outputs[0],haze.inputs[0]); links.new(texture.outputs["Color"],haze.inputs[2]); links.new(haze.outputs[0],emission.inputs["Color"])
            links.new(emission.outputs[0],output.inputs["Surface"])
        mesh.materials.append(material)
    # This fixed transform is deliberately linked at the scene root: the
    # projection view layer excludes the ordinary base collection, but still
    # needs this calibration object for its projective ground coordinates.
    calibration=bpy.data.objects.new(name+" fixed terminal photo calibration",None)
    calibration.matrix_world=camera.matrix_world.copy()
    calibration.empty_display_type="PLAIN_AXES"
    bpy.context.scene.collection.objects.link(calibration)
    ground=bpy.data.materials.new(name+" rigid projected navy steel deck")
    ground.use_nodes=True; nodes=ground.node_tree.nodes; nodes.clear(); links=ground.node_tree.links
    output=nodes.new("ShaderNodeOutputMaterial"); emission=nodes.new("ShaderNodeEmission")
    emission.inputs["Strength"].default_value=1
    calibrated=nodes.new("ShaderNodeTexCoord"); calibrated.object=calibration
    xyz=nodes.new("ShaderNodeSeparateXYZ"); links.new(calibrated.outputs["Object"],xyz.inputs[0])
    def operation(kind,a,b=None):
        node=nodes.new("ShaderNodeMath"); node.operation=kind
        if hasattr(a,"node"):
            links.new(a,node.inputs[0])
        else:
            node.inputs[0].default_value=a
        if b is not None:
            if hasattr(b,"node"):
                links.new(b,node.inputs[1])
            else:
                node.inputs[1].default_value=b
        return node.outputs[0]
    depth=operation("MULTIPLY",xyz.outputs["Z"],-1)
    factor=camera.data.lens/camera.data.sensor_width
    pu=operation("ADD",operation("MULTIPLY",operation("DIVIDE",xyz.outputs["X"],depth),factor),.5)
    pv=operation("ADD",operation("MULTIPLY",operation("DIVIDE",xyz.outputs["Y"],depth),factor*images[0].size[0]/images[0].size[1]),.5)
    combine=nodes.new("ShaderNodeCombineXYZ"); links.new(pu,combine.inputs["X"]); links.new(pv,combine.inputs["Y"])
    photo=nodes.new("ShaderNodeTexImage"); photo.image=images[0]
    photo.interpolation="Linear"; photo.extension="EXTEND"; links.new(combine.outputs[0],photo.inputs["Vector"])
    conditions=[operation("GREATER_THAN",depth,.01),
                operation("GREATER_THAN",pu,0),operation("LESS_THAN",pu,1),
                operation("GREATER_THAN",pv,0),operation("LESS_THAN",pv,1)]
    valid=conditions[0]
    for condition in conditions[1:]:
        valid=operation("MULTIPLY",valid,condition)
    world=nodes.new("ShaderNodeTexCoord")
    scale=nodes.new("ShaderNodeVectorMath"); scale.operation="SCALE"; scale.inputs["Scale"].default_value=.065
    links.new(world.outputs["Object"],scale.inputs[0])
    steel_path=Path(background_path).parent/"steel.png"
    steel=nodes.new("ShaderNodeTexImage"); steel.image=bpy.data.images.load(str(steel_path.resolve()),check_existing=True)
    steel.projection="BOX"; steel.projection_blend=.15; steel.interpolation="Linear"; steel.extension="REPEAT"
    links.new(scale.outputs[0],steel.inputs["Vector"])
    navy=nodes.new("ShaderNodeMixRGB"); navy.blend_type="MULTIPLY"; navy.inputs[0].default_value=.70
    navy.inputs[2].default_value=(.09,.18,.30,1); links.new(steel.outputs["Color"],navy.inputs[1])
    choose=nodes.new("ShaderNodeMixRGB"); links.new(valid,choose.inputs[0]); links.new(navy.outputs[0],choose.inputs[1]); links.new(photo.outputs["Color"],choose.inputs[2])
    links.new(choose.outputs[0],emission.inputs["Color"])
    # Only genuine deck pixels may project onto the flat strip. Railings,
    # torchposts and scenery in the valid image region remain visible on the
    # opaque far photograph instead of becoming flattened floor decorations.
    top_v=operation("SUBTRACT",1,pv)
    taper=operation("MAXIMUM",operation("DIVIDE",operation("SUBTRACT",425/640,top_v),(425-316)/640),0)
    floor_left=operation("MULTIPLY",taper,396/960)
    floor_right=operation("SUBTRACT",1,operation("MULTIPLY",taper,(960-634)/960))
    floor=operation("MULTIPLY",operation("GREATER_THAN",top_v,316/640),
                    operation("GREATER_THAN",pu,floor_left))
    floor=operation("MULTIPLY",floor,operation("LESS_THAN",pu,floor_right))
    opacity=operation("SUBTRACT",1,operation("MULTIPLY",valid,operation("SUBTRACT",1,floor)))
    transparent=nodes.new("ShaderNodeBsdfTransparent")
    surface=nodes.new("ShaderNodeMixShader")
    links.new(opacity,surface.inputs[0]); links.new(transparent.outputs[0],surface.inputs[1]); links.new(emission.outputs[0],surface.inputs[2]); links.new(surface.outputs[0],output.inputs["Surface"])
    mesh.materials.append(ground)
    obj=bpy.data.objects.new(name,mesh); bpy.context.collection.objects.link(obj)
    obj["production_role"]="rigid far backdrop, actual horizontal deck, four disconnected stasis silhouettes"
    obj["source_images"]=[str(path) for path in paths]
    obj["guard_optical_depths_metres"]=list(depths)
    obj["reference_camera_position"]=list(origin)
    obj["reference_camera_lens_mm"]=camera.data.lens
    obj["ground_height_metres"]=12.65
    obj["ground_width_metres"]=17.0
    obj["ground_length_metres"]=2000.0
    obj["backdrop_optical_depth_metres"]=700.0
    obj["calibration_object"]=calibration.name
    return obj


def create_depth_stage(bpy,camera,image_path,name,mode="opening"):
    """Return the opening's dense semantic mesh matching ``camera`` exactly.

    The caller owns collection/view-layer membership and lifecycle.  The
    camera must already have its shot pose and lens.  All image coordinates
    used for the depth authoring below are normalized from the upper left.
    """
    if mode=="final":
        raise ValueError("Final bridge depth fields are unsupported; use create_frozen_stage")
    if mode!="opening":
        raise ValueError("Unknown cinematic relief mode: "+str(mode))
    path=Path(image_path)
    if not path.is_file():
        raise FileNotFoundError(path)
    from mathutils import Vector
    image=bpy.data.images.load(str(path.resolve()),check_existing=True)
    if not image.size[0] or not image.size[1]:
        raise ValueError("Empty approved cinematic plate")
    bpy.context.view_layer.update()
    frame=camera.data.view_frame(scene=bpy.context.scene)
    left=min(p.x for p in frame); right=max(p.x for p in frame)
    bottom=min(p.y for p in frame); top=max(p.y for p in frame)
    z=sum(p.z for p in frame)/len(frame)
    origin=camera.matrix_world.translation.copy()
    rotation=camera.matrix_world.to_quaternion()
    nx,ny=641,427
    vertices=[]; faces=[]; coordinates=[]; labels=[]
    for j in range(ny):
        v=j/(ny-1)
        for i in range(nx):
            u=i/(nx-1)
            ray=(rotation@Vector((left+(right-left)*u,
                                  top+(bottom-top)*v,z))).normalized()
            label,distance=_opening_surface(u,v,origin,ray)
            vertices.append(tuple(origin+ray*distance))
            coordinates.append((u,1.0-v))
            labels.append(label)
    for j in range(ny-1):
        for i in range(nx-1):
            a=j*nx+i; b=a+1; c=a+nx; d=c+1
            # Omit only the thin triangles that cross a silhouette.  Never
            # stretch a foreground building texture onto a far ocean surface.
            if labels[a]==labels[c]==labels[d]:
                faces.append((a,c,d))
            if labels[a]==labels[d]==labels[b]:
                faces.append((a,d,b))
    mesh=bpy.data.meshes.new(name+" spatial relief mesh")
    mesh.from_pydata(vertices,[],faces); mesh.update()
    uv_name="Approved plate coordinates"
    mesh.uv_layers.new(name=uv_name)
    interior_name="Opening semantic interior"
    if mode=="opening":
        mesh.attributes.new(name=interior_name,type="FLOAT",domain="CORNER")
        interiors=_semantic_interior(labels,nx,ny)
    # CORNER allocation can move CustomData storage. Reacquire both handles
    # only after all layer allocations, before writing either registered UVs
    # or feather values.
    uv=mesh.uv_layers[uv_name]
    interior=mesh.attributes[interior_name] if mode=="opening" else None
    for polygon in mesh.polygons:
        for loop_index in polygon.loop_indices:
            vertex_index=mesh.loops[loop_index].vertex_index
            uv.data[loop_index].uv=coordinates[vertex_index]
            if interior is not None:
                interior.data[loop_index].value=interiors[vertex_index]
    material=bpy.data.materials.new(name+" approved painted surface")
    material.use_nodes=True
    nodes=material.node_tree.nodes; nodes.clear()
    output=nodes.new("ShaderNodeOutputMaterial")
    emission=nodes.new("ShaderNodeEmission"); emission.inputs["Strength"].default_value=1
    texture=nodes.new("ShaderNodeTexImage"); texture.image=image
    texture.interpolation="Linear"; texture.extension="EXTEND"
    texcoord=nodes.new("ShaderNodeUVMap"); texcoord.uv_map=uv.name
    links=material.node_tree.links
    links.new(texcoord.outputs["UV"],texture.inputs["Vector"])
    links.new(texture.outputs["Color"],emission.inputs["Color"])
    if mode=="opening":
        softness=nodes.new('ShaderNodeValue'); softness.name='Opening boundary softness'; softness.outputs[0].default_value=0
        separate=nodes.new('ShaderNodeSeparateXYZ'); links.new(texcoord.outputs['UV'],separate.inputs[0])
        ux=nodes.new('ShaderNodeMath'); ux.operation='SUBTRACT'; ux.inputs[0].default_value=1; links.new(separate.outputs['X'],ux.inputs[1])
        vy=nodes.new('ShaderNodeMath'); vy.operation='SUBTRACT'; vy.inputs[0].default_value=1; links.new(separate.outputs['Y'],vy.inputs[1])
        mins=[]
        for first,second in ((separate.outputs['X'],ux.outputs[0]),(separate.outputs['Y'],vy.outputs[0])):
            minimum=nodes.new('ShaderNodeMath'); minimum.operation='MINIMUM'; links.new(first,minimum.inputs[0]); links.new(second,minimum.inputs[1]); mins.append(minimum)
        minimum=nodes.new('ShaderNodeMath'); minimum.operation='MINIMUM'; links.new(mins[0].outputs[0],minimum.inputs[0]); links.new(mins[1].outputs[0],minimum.inputs[1])
        feather=nodes.new('ShaderNodeMapRange'); feather.inputs['From Min'].default_value=0; feather.inputs['From Max'].default_value=.045; links.new(minimum.outputs[0],feather.inputs[0])
        semantic=nodes.new('ShaderNodeAttribute'); semantic.attribute_name=interior_name
        combined=nodes.new('ShaderNodeMath'); combined.operation='MINIMUM'; links.new(feather.outputs[0],combined.inputs[0]); links.new(semantic.outputs['Fac'],combined.inputs[1])
        invert=nodes.new('ShaderNodeMath'); invert.operation='SUBTRACT'; invert.inputs[0].default_value=1; links.new(combined.outputs[0],invert.inputs[1])
        multiply=nodes.new('ShaderNodeMath'); multiply.operation='MULTIPLY'; links.new(invert.outputs[0],multiply.inputs[0]); links.new(softness.outputs[0],multiply.inputs[1])
        alpha=nodes.new('ShaderNodeMath'); alpha.operation='SUBTRACT'; alpha.inputs[0].default_value=1; links.new(multiply.outputs[0],alpha.inputs[1])
        transparent=nodes.new('ShaderNodeBsdfTransparent'); mix=nodes.new('ShaderNodeMixShader'); links.new(alpha.outputs[0],mix.inputs[0]); links.new(transparent.outputs[0],mix.inputs[1]); links.new(emission.outputs[0],mix.inputs[2]); links.new(mix.outputs[0],output.inputs['Surface'])
    else:
        links.new(emission.outputs[0],output.inputs["Surface"])
    mesh.materials.append(material)
    obj=bpy.data.objects.new(name,mesh)
    bpy.context.collection.objects.link(obj)
    obj["production_role"]="approved opening image reconstructed as separated semantic spatial relief"
    obj["source_image"]=str(path)
    obj["depth_mode"]=mode
    obj["grid_size"]=[nx,ny]
    obj["reference_camera_position"]=list(origin)
    obj["reference_camera_lens_mm"]=camera.data.lens
    return obj
