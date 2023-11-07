from typing import Any, Callable
import bpy, bmesh
C = bpy.context
D = bpy.data

# Delete most data from the blend-file.
def delete_data() -> None:
    for prop_collection in (
        D.actions, D.armatures, D.cameras, D.lights, D.materials, D.meshes,
        D.objects, D.collections, D.images
    ):
        for item in prop_collection:
            prop_collection.remove(item)

# Create a new object from a bpy.ops.create_ function.
def new_obj(bmesh_op: Callable, name: str, *args: Any, **kwargs: Any) -> bpy.types.Object:
    bm = bmesh.new()
    bmesh_op(bm, *args, **kwargs)
    mesh = D.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    return D.objects.new(name, mesh)

# Append an object's data to a bmesh object.
def bm_absorb_obj(bm: bmesh.types.BMesh, obj: bpy.types.Object) -> None:
    bm.from_mesh(obj.data)
    for m in obj.data.materials:
        D.materials.remove(m)
    D.meshes.remove(obj.data) # removes both the mesh and object from D

# Split a mixed list of BMvert, BMEdge and BMFace into a dict.
def bm_geom_split(geom: list) -> dict[str, list]:
    result = {
        'geom': geom,
        'verts': list(e for e in geom if isinstance(e, bmesh.types.BMVert)),
        'edges': list(e for e in geom if isinstance(e, bmesh.types.BMEdge)),
        'faces': list(e for e in geom if isinstance(e, bmesh.types.BMFace)),
    }
    result['v'] = result['verts']
    result['e'] = result['edges']
    result['f'] = result['faces']
    return result

