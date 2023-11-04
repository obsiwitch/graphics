#!/usr/bin/env -S blender --factory-startup --python

# blender: 3.6.4

import sys, importlib
from math import radians
from pathlib import Path

import bpy, bmesh
C = bpy.context
D = bpy.data

if '.' not in sys.path:
    sys.path.append('.')
import shared
importlib.reload(shared)

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

        # mesh & object
        mesh = D.meshes.new('head')
        bm.to_mesh(mesh)
        bm.free()
        object = D.objects.new(mesh.name, mesh)

        return object

if __name__ == '__main__':
    shared.delete_data()
    D.scenes[0].collection.objects.link(Character.head())
