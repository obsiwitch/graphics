#!/usr/bin/env -S blender --factory-startup --python

# name: Animated grid of cubes
# blender: 2.92.0
# ref: [CG Cookie - Animating With Python](https://www.youtube.com/watch?v=QnvN1dieIAU)
# ref: [BPY Documentation](https://docs.blender.org/api/current/)
# ref: [Python Performance with Blender operators](https://blender.stackexchange.com/a/7360)

import sys, itertools, math, importlib
import bpy, bmesh, mathutils

# ref: https://docs.blender.org/api/current/info_tips_and_tricks.html#executing-modules
if '.' not in sys.path:
    sys.path.append('.')
import shared
importlib.reload(shared)

# Create a template cube.
def new_cube() -> bpy.types.Object:
    # mesh & object (alt: bpy.ops.mesh.primitive_cube_add())
    obj = shared.new_obj(bmesh.ops.create_cube, name='Cube')

    # modifiers
    obj.modifiers.new(name='Wireframe', type='WIREFRAME')
    obj.modifiers['Wireframe'].thickness = 0.05

    # materials
    material = bpy.data.materials.new(name='Material')
    material.use_nodes = True
    obj.data.materials.append(material)

    ## shader nodes (tip: organize nodes in GUI w/ 'Node Arrange' addon)
    nodes = material.node_tree.nodes
    nodes.remove(nodes['Principled BSDF'])
    nodes.new('ShaderNodeTexCoord')
    nodes.new('ShaderNodeEmission')
    nodes['Emission'].inputs['Strength'].default_value = 2.5

    ## links between nodes
    links = material.node_tree.links
    links.new(nodes['Texture Coordinate'].outputs['Camera'],
              nodes['Emission'].inputs['Color'])
    links.new(nodes['Emission'].outputs['Emission'],
              nodes['Material Output'].inputs['Surface'])

    return obj

# Create a 10*10 animated grid of `obj` objects.
def new_grid(obj: bpy.types.Object) -> bpy.types.Collection:
    # grid
    collection = bpy.data.collections.new('Grid')
    for x, y in itertools.product(range(10), repeat=2):
        c = obj.copy()
        c.location[0] = x * 2
        c.location[1] = y * 2
        collection.objects.link(c)

    # animation
    for i, obj in enumerate(collection.objects):
        obj.scale = (0, 0, 0)
        obj.keyframe_insert(data_path='scale', frame=1 + i)
        obj.scale = (1, 1, 5)
        obj.keyframe_insert(data_path='scale', frame=50 + i)
        obj.scale = (1, 1, 0.5)
        obj.keyframe_insert(data_path='scale', frame=70 + i)
        obj.scale = (1, 1, 1)
        obj.keyframe_insert(data_path='scale', frame=80 + i)

    return collection

def setup_scene(collection: bpy.types.Collection) -> None:
    # add collection to Scene Collection
    scene = bpy.data.scenes['Scene']
    scene.collection.children.link(collection)

    # camera (alt: bpy.ops.object.camera_add())
    camera = bpy.data.objects.new('Camera', bpy.data.cameras.new('Camera'))
    camera.location = mathutils.Vector((-10, -10, 30))
    camera.rotation_euler[0] = math.radians(45)
    camera.rotation_euler[2] = math.radians(-45)
    scene.collection.objects.link(camera)

    # world & render properties
    bpy.data.worlds['World'] \
       .node_tree.nodes["Background"] \
       .inputs['Color'].default_value = (0, 0, 0, 1)
    scene.frame_end = 80 + len(collection.objects)
    scene.eevee.use_bloom = True

if __name__ == '__main__':
    shared.delete_data()
    cube = new_cube()
    grid = new_grid(obj=cube)
    setup_scene(collection=grid)
