#!/usr/bin/env -S blender --factory-startup --python

# blender: 3.6.4

import sys, importlib
from math import radians
from pathlib import Path

import bpy, bmesh
C = bpy.context
D = bpy.data

from mathutils import Matrix, Vector
def Mat(*args): return Matrix(args)
def Vec(*args): return Vector(args)

if '.' not in sys.path:
    sys.path.append('.')
import shared
importlib.reload(shared)

def bm_to_obj(bm: bmesh.types.BMesh, name: str, free: bool) -> bpy.types.Object:
    mesh = D.meshes.new(name)
    bm.to_mesh(mesh)
    if free: bm.free()
    return D.objects.new(mesh.name, mesh)

class Character:
    @classmethod
    def head(cls) -> bpy.types.Object:
        bm = bmesh.new()

        v = bmesh.ops.create_uvsphere(bm, u_segments=6, v_segments=6, radius=0.5)['verts']
        v[11].co.x += 0.05 # temples
        v[22].co.x -= 0.05 # temples

        v[15].co.y -= 0.05 # top/forehead
        v[17].co.y = v[16].co.y # eye/nose
        v[18].co.y -= 0.1 # nose tip
        v[19].co.y -= 0.1 # mouth
        v[31].co.y -= 0.3 # chin

        v[18].co.z += 0.05 # nose tip

        return bm_to_obj(bm, 'head', free=True)

    @classmethod
    def torso(cls) -> bpy.types.Object:
        bm = bmesh.new()
        v = bmesh.ops.create_uvsphere(bm, u_segments=4, v_segments=4, radius=0.5)['verts']

        # waist
        bmesh.ops.scale(bm, verts=tuple(v[i] for i in (0, 3, 6, 11)), vec=(0.5, 0.5, 1.0))

        # chest
        v[5].co.z -= 0.1
        v[5].co.y -= 0.05

        # squish front and back
        bmesh.ops.scale(bm, vec=(1.0, 0.75, 1.0), verts=v)

        return bm_to_obj(bm, 'torso', free=True)

if __name__ == '__main__':
    shared.delete_data()
    D.scenes[0].collection.objects.link(Character.torso())
