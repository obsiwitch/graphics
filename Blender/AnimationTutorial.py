#!/usr/bin/env -S blender --factory-startup --python

# ref: [CG Cookie - Animating With Python](https://www.youtube.com/watch?v=QnvN1dieIAU)
# ref: [BPY Documentation](https://docs.blender.org/api/current/)
# ref: [Python Performance with Blender operators](https://blender.stackexchange.com/a/7360)
# blender version: 2.92.0

import bpy, bmesh, itertools, math, mathutils

def template_cube():


    return obj

# reset
bpy.context.preferences.view.show_splash = False
for data_type in (bpy.data.actions, bpy.data.cameras, bpy.data.lights,
                  bpy.data.materials, bpy.data.meshes, bpy.data.objects,
                  bpy.data.collections):
    for item in data_type:
        data_type.remove(item)

# template cube (equivalent: bpy.ops.mesh.primitive_cube_add())
bm = bmesh.new()
bmesh.ops.create_cube(bm, size=2.0)
mesh = bpy.data.meshes.new('Cube')
bm.to_mesh(mesh)
bm.free()
tplcube = bpy.data.objects.new('Cube', mesh)

## modifiers
tplcube.modifiers.new(name='Wireframe', type='WIREFRAME')
tplcube.modifiers['Wireframe'].thickness = 0.05

## materials
material = bpy.data.materials.new(name='Material')
material.use_nodes = True
tplcube.data.materials.append(material)

### shader nodes (tip: organize nodes in GUI w/ 'Node Arrange' addon)
nodes = material.node_tree.nodes
nodes.remove(nodes['Principled BSDF'])
nodes.new('ShaderNodeTexCoord')
nodes.new('ShaderNodeEmission')
nodes['Emission'].inputs['Strength'].default_value = 2.5

### links between nodes
links = material.node_tree.links
links.new(nodes['Texture Coordinate'].outputs['Camera'],
          nodes['Emission'].inputs['Color'])
links.new(nodes['Emission'].outputs['Emission'],
          nodes['Material Output'].inputs['Surface'])

# 10*10 cubes grid
scene = bpy.data.scenes['Scene']
for x, y in itertools.product(range(10), repeat=2):
    if x == 0 and y == 0: continue
    c = tplcube.copy()
    c.location[0] = x * 2
    c.location[1] = y * 2
    scene.collection.objects.link(c)

# animation
scene.frame_end = 80 + len(bpy.data.objects)
for i, obj in enumerate(bpy.data.objects):
    obj.scale = (0, 0, 0)
    obj.keyframe_insert(data_path='scale', frame=1 + i)
    obj.scale = (1, 1, 5)
    obj.keyframe_insert(data_path='scale', frame=50 + i)
    obj.scale = (1, 1, 0.5)
    obj.keyframe_insert(data_path='scale', frame=70 + i)
    obj.scale = (1, 1, 1)
    obj.keyframe_insert(data_path='scale', frame=80 + i)

# camera
bpy.ops.object.camera_add()
camera = bpy.data.objects['Camera']
camera.location = mathutils.Vector((-10, -10, 30))
camera.rotation_euler[0] = math.radians(45)
camera.rotation_euler[2] = math.radians(-45)

# world & render
bpy.data.worlds['World'] \
   .node_tree.nodes["Background"] \
   .inputs['Color'].default_value = (0, 0, 0, 1)
scene.eevee.use_bloom = True
