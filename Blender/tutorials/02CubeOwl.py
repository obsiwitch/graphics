#!/usr/bin/env -S blender --factory-startup --python

# name: Cube Owl
# blender: 2.93.0
# ref: https://cloud.blender.org/training/primitive-animals/

import sys, math
import bpy, bmesh
from mathutils import Matrix, Vector
import numpy as np

if '.' not in sys.path:
    sys.path.append('.')
if 'shared' in sys.modules:
    del sys.modules['shared']
import shared

class Owl:
    @classmethod
    def new(cls):
        collection = bpy.data.collections.new('Owl')

        torso = cls.new_torso()
        collection.objects.link(torso)

        face_parts = cls.new_face()
        face_parts[0].parent = torso
        for part in face_parts:
            collection.objects.link(part)

        wings = cls.new_wings(anchor=torso)
        wings.parent = torso
        collection.objects.link(wings)

        feathers = cls.new_feathers(location=(0.0, 0.9, -0.6))
        for feather in feathers:
            feather.parent = torso
            collection.objects.link(feather)

        legs = cls.new_legs(mirror_object=torso)
        legs.parent = torso
        collection.objects.link(legs)

        return collection

    @classmethod
    def new_torso(cls):
        # mesh & object
        obj = shared.new_obj(bmesh.ops.create_cube, name='Torso', size=2)
        shared.use_smooth(obj.data, True)

        # modifiers
        bevel_mod = obj.modifiers.new(name='Bevel', type='BEVEL')
        bevel_mod.width = 0.02
        bevel_mod.segments = 2

        return obj

    @classmethod
    def new_face(cls):
        base = cls.new_face_base()
        beak = cls.new_face_beak()
        beak.parent = base
        eyes = cls.new_face_eyes(mirror_object=beak)
        eyes.parent = base
        return [base, beak, eyes]

    @classmethod
    def new_face_base(cls):
        # mesh: half-heart face
        mesh = bpy.data.meshes.new('Face')
        mesh.from_pydata(
            # The vertices 1 and 5 control/guide the subdivision modifier.
            vertices=((0.0, 0.0, -0.72), (-0.045, 0, -0.702),
                      (-0.9, 0.0, -0.36), (-0.9, 0.0, 0.45),
                      (-0.45, 0.0, 0.9), (-0.040725, 0.0, 0.490725),
                      (0.0, 0.0, 0.45), (0.0, 0.0, -0.36)),
            edges=(),
            faces=((0, 1, 2, 7), (7, 2, 3, 6), (6, 3, 4, 5)),
        )
        shared.use_smooth(mesh, True)

        # bmesh
        bm = bmesh.new()
        bm.from_mesh(mesh)

        # extrude
        bm.edges.ensure_lookup_table()
        _geom = bmesh.ops.extrude_face_region(bm,
            geom = bm.faces,
            # exclude these edges from the extrusion to avoid having inner
            # geometry creating a crease after the mirror modifier
            edges_exclude = set((bm.edges[3], bm.edges[8]))
        )
        bmesh.ops.translate(bm, vec=(0.0, -0.1, 0.0), verts=bm.verts[8:])

        bm.to_mesh(mesh)
        bm.free()

        # object
        obj = bpy.data.objects.new('Face', mesh)
        obj.location.y = -0.95
        mirror_mod = obj.modifiers.new(name='Mirror', type='MIRROR')
        subdiv_mod = obj.modifiers.new(name='Subdivision', type='SUBSURF')
        subdiv_mod.levels = subdiv_mod.render_levels = 2

        return obj

    @classmethod
    def new_face_beak(cls):
        height = 0.5
        obj = shared.new_obj(bmesh.ops.create_cone, name='Beak',
            segments=4, diameter1=0.35, diameter2=1e-3, depth=height)
        shared.use_smooth(obj.data, True)
        shared.set_origin(obj, (0, 0, -height / 2))
        obj.location.z = 0
        obj.rotation_euler.x = math.pi / 2

        subdiv_mod = obj.modifiers.new(name='Subdivision', type='SUBSURF')
        subdiv_mod.levels = subdiv_mod.render_levels = 2
        deform_mod = obj.modifiers.new(name='SimpleDeform', type='SIMPLE_DEFORM')
        deform_mod.deform_method = 'BEND'
        deform_mod.deform_axis = 'X'
        deform_mod.angle = -math.pi / 2

        return obj

    @classmethod
    def new_face_eyes(cls, mirror_object):
        obj = shared.new_obj(bmesh.ops.create_uvsphere, name='Eyes',
            u_segments=16, v_segments=8, diameter=0.25)
        shared.use_smooth(obj.data, True)
        obj.scale.y = 0.25
        obj.location = (0.45, -0.1, 0.2)
        mirror_mod = obj.modifiers.new(name='Mirror', type='MIRROR')
        mirror_mod.mirror_object = mirror_object
        return obj

    @classmethod
    def new_wings(cls, anchor):
        # mesh
        # 1. manually place points to create rough wing outline
        # 2. select all vertices & create face
        # 3. poke faces
        # 4. offset central vertex
        mesh = bpy.data.meshes.new('Wing')
        mesh.from_pydata(
            vertices = ((0.00,  0.98, -0.63), (0.00, -0.18,  0.99),
                        (0.00, -0.91, -0.40), (0.00,  0.88, -0.63),
                        (0.00, -0.91,  0.64), (0.25, -0.09,  0.04),),
            edges = (),
            faces = ((1, 4, 5), (4, 2, 5), (2, 3, 5), (3, 0, 5), (0, 1, 5)),
        )
        shared.use_smooth(mesh, True)

        # object
        obj = bpy.data.objects.new('Wings', mesh)
        obj.location.x = (obj.dimensions.x / 4) + anchor.location.x \
                       + (anchor.dimensions.x / 2)
        obj.location.z = -0.5
        obj.scale = (1.1, 1.1, 1.1)

        # modifiers
        subdiv_mod = obj.modifiers.new(name='Subdivision', type='SUBSURF')
        subdiv_mod.levels = subdiv_mod.render_levels = 2
        mirror1_mod = obj.modifiers.new(name='MirrorOrigin', type='MIRROR')
        mirror2_mod = obj.modifiers.new(name='MirrorObject', type='MIRROR')
        mirror2_mod.mirror_object = anchor
        bevel_mod = obj.modifiers.new(name='Bevel', type='BEVEL')

        return obj

    @classmethod
    def new_feathers(cls, location):
        feathers = [ cls.new_feather() ]
        feathers[0].location = location
        feathers += [feathers[0].copy() for _ in range(4)]

        for feather, angle, scale in zip(
            feathers, range(-50, 75, 25), [0.6, 0.8, 1.0, 0.8, 0.6]
        ):
            feather.scale = (scale, scale, scale)
            feather.rotation_euler.z = math.radians(angle)
            # ref: https://blender.stackexchange.com/q/44760
            feather.rotation_euler = (
                Matrix.Rotation(math.radians(25), 3, 'X')
                @ feather.rotation_euler.to_matrix()
            ).to_euler()
        return feathers

    @classmethod
    def new_feather(cls):
        # mesh
        vertices = ((-0.27, 0.31, 0.0), (0.0, -0.88, 0.0),
                    (-0.27, 0.51, 0.0), (0.0, 0.90, 0.0),
                    (0.0, 0.40, 0.10), (-0.10, 0.90, 0.0),
                    (-0.05, -0.88, 0.0))
        faces = ((3, 5, 4), (5, 2, 4), (0, 4, 2), (1, 4, 0, 6))
        mesh = bpy.data.meshes.new('Feather')
        mesh.from_pydata(vertices=vertices, edges=(), faces=faces)
        shared.use_smooth(mesh, True)

        # object
        obj = bpy.data.objects.new('Feather', mesh)

        # modifiers
        mirrorx_mod = obj.modifiers.new(name='MirrorX', type='MIRROR')
        mirrorx_mod.use_clip = True
        subdiv_mod = obj.modifiers.new(name='Subdivision', type='SUBSURF')
        subdiv_mod.levels = subdiv_mod.render_levels = 2
        mirrorz_mod = obj.modifiers.new(name='MirrorZ', type='MIRROR')
        mirrorz_mod.use_axis = (False, False, True)

        # origin
        shared.set_origin(obj, vertices[1])

        return obj

    @classmethod
    def new_legs(cls, mirror_object):
        bm = bmesh.new()

        # tibia
        _c1 = bmesh.ops.create_circle(bm, radius=0.2, segments=8)
        c2 = bmesh.ops.extrude_edge_only(bm, edges=bm.edges)
        c2 = shared.bm_geom_split(c2['geom'])
        bmesh.ops.translate(bm, verts=c2['verts'], vec=(-0.25, 0.25, -0.25))
        bmesh.ops.scale(bm, verts=c2['verts'], vec=(0.5, 0.5, 1.0))

        # tarsometatarsus
        c3 = bmesh.ops.extrude_edge_only(bm, edges=c2['edges'])
        c3 = shared.bm_geom_split(c3['geom'])
        bmesh.ops.translate(bm, verts=c3['verts'], vec=(0.125, -0.125, -0.20))
        bmesh.ops.scale(bm, verts=c3['verts'], vec=(0.5, 0.5, 1.0))

        mesh = bpy.data.meshes.new('Legs')
        bm.to_mesh(mesh)
        shared.use_smooth(mesh, True)
        bm.free()

        obj = bpy.data.objects.new('Legs', mesh)
        obj.location = (0.5, 0.0, -1.0)
        mirror_mod = obj.modifiers.new(name='Mirror', type='MIRROR')
        mirror_mod.mirror_object = mirror_object

        return obj

if __name__ == '__main__':
    # reset data
    shared.delete_data()

    # create character
    owl_collection = Owl.new()

    # setup scene
    scene = bpy.data.scenes[0]
    scene.collection.children.link(owl_collection)
