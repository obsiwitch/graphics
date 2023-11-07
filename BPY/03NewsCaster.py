#!/usr/bin/env -S blender --factory-startup --python

# blender: 3.0
# ref: Mega Man Legends News Caster

import sys, importlib, dataclasses
from math import radians
from pathlib import Path

import bpy, bmesh
C = bpy.context
D = bpy.data

from mathutils import Matrix, Vector
def Mat(*args): return Matrix(args)
def Vec(*args): return Vector(args)
Diagonal = Matrix.Diagonal
Rotation = Matrix.Rotation
Translation = Matrix.Translation

import PIL.Image, PIL.ImageDraw # https://pypi.org/project/Pillow/

if '.' not in sys.path:
    sys.path.append('.')
import shared
importlib.reload(shared)

@dataclasses.dataclass
class UVIsland:
    faces: list[bmesh.types.BMFace] = dataclasses.field(default_factory=list)
    bbox: dict[str, float] = dataclasses.field(default_factory=dict)

    def calc_bbox(self, uv_layer) -> dict[str, float]:
        if not self.faces: return {}
        init_uv = self.faces[0].loops[0][uv_layer].uv
        left = right = init_uv.x
        top = bottom = init_uv.y
        for face in self.faces:
            for loop in face.loops:
                uv = loop[uv_layer].uv
                top = max(top, uv.y)
                left = min(left, uv.x)
                right = max(right, uv.x)
                bottom = min(bottom, uv.y)
        self.bbox = { 't': top, 'l': left, 'r': right, 'b': bottom,
                      'h': top - bottom, 'w': right - left }
        return self.bbox

# Unwrap UVs using cube projection.
def bm_uv_cube_project(faces, uv_layer):
    islands = { 'top':   UVIsland(), 'bottom': UVIsland(),
                'front': UVIsland(), 'back':   UVIsland(),
                'right': UVIsland(), 'left':   UVIsland() }

    # unwrap UVs using cube projection
    # note: faces loops produce split UVs, verts link_loops produce stitched UVs
    # ref: blender source uvedit_unwrap_cube_project() & axis_dominant_v3()
    for face in faces:
        n = face.normal
        # pick the 2 non-dominant axes for the projection
        if abs(n.z) >= abs(n.x) and abs(n.z) >= abs(n.y):
            i, j = 0, 1
            islands['top' if n.z >= 0 else 'bottom'].faces.append(face)
        elif abs(n.y) >= abs(n.x) and abs(n.y) >= abs(n.z):
            i, j = 0, 2
            islands['back' if n.y >= 0 else 'front'].faces.append(face)
        else:
            i, j = 1, 2
            islands['right' if n.x >= 0 else 'left'].faces.append(face)

        for loop in face.loops:
            loop[uv_layer].uv.x = loop.vert.co[i]
            loop[uv_layer].uv.y = loop.vert.co[j]

    # islands' bounding boxes
    for island in islands.values():
        island.calc_bbox(uv_layer)

    return islands

# Position islands resulting from a cube projection.
def bm_uv_cube_position(islands, uv_layer, init_offset=Vector((0.5, 0.0)), margin=0.01):
    # position islands at (0, 0), offset them and update the bbox
    def do_position(key, offset):
        for face in islands[key].faces:
            for loop in face.loops:
                loop[uv_layer].uv.x += offset.x - islands[key].bbox['l']
                loop[uv_layer].uv.y += offset.y - islands[key].bbox['b']
        islands[key].calc_bbox(uv_layer)

    # select which axis of the specified island will contribute to the offset
    def do_offset(key, offset, axis):
        if islands[key].faces:
            offset.x += axis[0] * (islands[key].bbox['w'] + margin)
            offset.y += axis[1] * (islands[key].bbox['h'] + margin)

    # place front, top and bottom islands on the same row
    offset = init_offset.copy()
    do_position('front', offset)
    do_offset('front', offset, axis=(0, 1))
    do_position('top', offset)
    do_offset('top', offset, axis=(0, 1))
    do_position('bottom', offset)

    # place right, back and left islands on the same column as the front island
    offset = init_offset.copy()
    do_offset('front', offset, axis=(1, 0))
    do_position('right', offset)
    do_offset('right', offset, axis=(1, 0))
    do_position('back', offset)
    do_offset('back', offset, axis=(1, 0))
    do_position('left', offset)

def bm_create_plane(bm, fill):
    result = bmesh.ops.create_grid(bm, x_segments=0, y_segments=0, size=0.5)
    if not fill:
        bmesh.ops.delete(bm, geom=result['verts'][0].link_faces,
                         context='FACES_ONLY')
    return result

class Character:
    @classmethod
    def object(cls):
        # mesh & object
        bm = bmesh.new()
        uv_layer = bm.loops.layers.uv.new()
        shared.bm_absorb_obj(bm, cls.head())
        shared.bm_absorb_obj(bm, cls.arm())
        shared.bm_absorb_obj(bm, cls.pelvis())
        bmesh.ops.mirror(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:],
                         merge_dist=0.001, axis='X', mirror_u=True)
        shared.bm_absorb_obj(bm, cls.nose())
        shared.bm_absorb_obj(bm, cls.neck())

        mesh = D.meshes.new('character')
        bm.to_mesh(mesh)
        bm.free()
        object = D.objects.new(mesh.name, mesh)

        # texture & material
        texture = cls.texture()
        material = cls.material(texture)
        object.data.materials.append(material)

        return object

    @classmethod
    def scale_uvs(cls, faces, uv_layer, islands={}):
        for face in faces:
            for loop in face.loops:
                loop[uv_layer].uv.x -= 0.5
                loop[uv_layer].uv *= 0.27
                loop[uv_layer].uv.x += 0.5
        for island in islands.values():
            island.calc_bbox(uv_layer)

    @classmethod
    def head(cls) -> bpy.types.Object:
        bm = bmesh.new()

        uv_layer = bm.loops.layers.uv.new()
        sphv = bmesh.ops.create_uvsphere(bm, u_segments=6, v_segments=5,
                                         radius=0.5)['verts']
        bmesh.ops.scale(bm, verts=sphv, vec=(0.36, 0.37, 0.35))
        bmesh.ops.translate(bm, verts=sphv, vec=(0.0, 0.03, 1.53))
        bmesh.ops.bisect_plane(bm, geom=sphv, dist=0.0000001, plane_co=(0, 0, 0),
                               plane_no=(1, 0, 0), clear_inner=True)
        sphv = bm.verts[:]

        # tweak right
        sphv[16].co.z -= 0.01
        sphv[11].co.y -= 0.02
        bmesh.ops.translate(bm, verts=sphv[1:14:4], vec=(0.0, 0.0, -0.03))
        sphv[13].co.y += 0.015
        sphv[1].co.y -= 0.04
        sphv[14].co.y -= 0.01
        sphv[15].co.z = sphv[14].co.z
        bmesh.ops.rotate(bm, cent=sphv[15].co, verts=sphv[2:15:4] + sphv[15:16],
                         matrix=Rotation(radians(10), 4, 'X'))
        bmesh.ops.scale(bm, verts=sphv[7:11], vec=(1.0, 0.0, 1.0))
        bmesh.ops.translate(bm, verts=sphv[7:11], vec=(0.0, -0.08, 0.0))
        sphv[10].co.z += 0.015

        # tweak front
        sphv[9].co.x -= 0.045
        sphv[5].co.x = sphv[9].co.x
        sphv[10].co.x -= 0.035

        # hair back spike
        pokev = bmesh.ops.poke(bm, faces=sphv[2].link_faces[0:1])['verts']
        pokev[0].co += Vec(-pokev[0].co.x, 0.06, -0.09)
        bmesh.ops.pointmerge(bm, verts=(pokev[0], sphv[2]), merge_co=pokev[0].co)

        # UVs
        islands = bm_uv_cube_project(bm.faces, uv_layer)
        offset = Vec(0.5, islands['front'].bbox['b'] + 1.5)
        bm_uv_cube_position(islands, uv_layer, init_offset=offset)
        cls.scale_uvs(bm.faces, uv_layer, islands)

        # mesh & object
        mesh = D.meshes.new('head')
        bm.to_mesh(mesh)
        bm.free()
        object = D.objects.new(mesh.name, mesh)

        # texture & material
        texture = cls.head_texture()
        material = cls.material(texture)
        object.data.materials.append(material)

        return object

    @classmethod
    def head_texture(cls) -> bpy.types.Image:
        size = (512, 512)
        image = PIL.Image.new(mode='RGBA', size=size)
        draw = PIL.ImageDraw.Draw(image)

        # hair & face
        draw.rectangle(xy=((256, 0), (336, 116)), fill=(28, 22, 19))
        draw.rectangle(xy=((256, 94), (276, 116)), fill=(248, 208, 168))
        draw.rectangle(xy=((256, 23), (276, 38)), fill=(248, 208, 168))
        draw.polygon(xy=((261, 94), (262, 88), (263, 94)), fill=(248, 208, 168))
        draw.polygon(xy=((271, 94), (272, 90), (272, 94)), fill=(248, 208, 168))

        # eyes
        x, y = 260, 97
        draw.ellipse(xy=((x+0, y+0), (x+7, y+4)), fill=(220, 220, 220))
        draw.rectangle(xy=((x+2, y+0), (x+3, y+4)), fill=(48, 64, 112))
        draw.line(xy=((x+0, y-1), (x+3, y-3), (x+7, y-1)), fill=(56, 40, 32))

        # lips
        draw.line(xy=((256, 110), (257, 110)), fill=(240, 176, 128))

        # mirror
        image.alpha_composite(image.transpose(PIL.Image.FLIP_LEFT_RIGHT))

        filepath = '03TmpHead.png'
        image.save(filepath)
        return D.images.load(filepath, check_existing=True)

    @classmethod
    def nose(cls) -> bpy.types.Object:
        # bmesh
        bm = bmesh.new()
        uv_layer = bm.loops.layers.uv.new()
        conev = bmesh.ops.create_cone(bm, segments=3, radius1=1.0, radius2=0.0,
                                      depth=1.0)['verts']
        bmesh.ops.rotate(bm, verts=conev, matrix=Rotation(radians(90), 3, 'X'))
        bmesh.ops.scale(bm, verts=conev, vec=(0.02, 0.04, 0.04))
        bmesh.ops.translate(bm, verts=conev, vec=(0.0, -0.122, 1.443))
        conev[0].co.y -= 0.01

        # UVs
        bm.verts.ensure_lookup_table()
        for vert in bm.verts:
            for loop in vert.link_loops:
                loop[uv_layer].uv = bm.verts[3].co.xz
                loop[uv_layer].uv += Vec(0.5, 1.5)
        cls.scale_uvs(bm.faces, uv_layer)

        # mesh & object
        mesh = D.meshes.new('nose')
        bm.to_mesh(mesh)
        bm.free()
        return D.objects.new(mesh.name, mesh)

    @classmethod
    def neck(cls) -> bpy.types.Object:
        # bmesh
        bm = bmesh.new()
        uv_layer = bm.loops.layers.uv.new()
        l1 = bm_create_plane(bm, fill=False)['verts']
        bmesh.ops.scale(bm, verts=l1, vec=(0.07, 0.06, 1.0))
        bmesh.ops.scale(bm, verts=l1[2:], vec=(0.0, 1.07, 1.0))
        bmesh.ops.translate(bm, verts=l1, vec=(0.0, 0.02, 1.35))
        bmesh.ops.extrude_edge_only(bm, edges=bm.edges)
        bmesh.ops.translate(bm, verts=bm.verts[-4:], vec=(0.0, 0.0, 0.07))
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0001)

        # UVs
        bm.verts.ensure_lookup_table()
        for vert in bm.verts:
            for loop in vert.link_loops:
                loop[uv_layer].uv = bm.verts[5].co.xz
                loop[uv_layer].uv += Vec(0.5, 1.5)
        cls.scale_uvs(bm.faces, uv_layer)

        # mesh & object
        mesh = D.meshes.new('neck')
        bm.to_mesh(mesh)
        bm.free()
        return D.objects.new(mesh.name, mesh)

    @classmethod
    def torso(cls) -> bpy.types.Object:
        bm = bmesh.new()
        uv_layer = bm.loops.layers.uv.new()

        luppertop = bm_create_plane(bm, fill=True)['verts']
        bmesh.ops.scale(bm, verts=luppertop, vec=(0.14, 0.1, 1.0))
        bmesh.ops.translate(bm, verts=luppertop, vec=(0.0, 0.015, 1.352))

        luppermid = bm_create_plane(bm, fill=False)['verts']
        bmesh.ops.scale(bm, verts=luppermid, vec=(0.24, 0.18, 1.0))
        bmesh.ops.translate(bm, verts=luppermid, vec=(0.0, -0.017, 1.21))

        lwaist = bm_create_plane(bm, fill=False)['verts']
        bmesh.ops.scale(bm, verts=lwaist, vec=(0.14, 0.11, 1.0))
        bmesh.ops.translate(bm, verts=lwaist, vec=(0.0, -0.02, 1.076))

        lbot = bm_create_plane(bm, fill=False)['verts']
        bmesh.ops.scale(bm, verts=lbot, vec=(0.23, 0.16, 1.0))
        bmesh.ops.translate(bm, verts=lbot, vec=(0.0, -0.004, 0.999))

        bmesh.ops.bridge_loops(bm, edges=bm.edges)
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:],
                               dist=0.0000001, plane_co=(0, 0, 0),
                               plane_no=(1, 0, 0), clear_inner=True)

        islands = bm_uv_cube_project(bm.faces, uv_layer)
        offset = Vec(0.5, islands['front'].bbox['b'] + 0.6)
        bm_uv_cube_position(islands, uv_layer, init_offset=offset)
        cls.scale_uvs(bm.faces, uv_layer, islands)

        # mesh & object
        mesh = D.meshes.new('torso')
        bm.to_mesh(mesh)
        bm.free()
        object = D.objects.new(mesh.name, mesh)

        # texture & material
        texture = cls.torso_texture()
        material = cls.material(texture)
        object.data.materials.append(material)

        return object

    @classmethod
    def torso_texture(cls) -> bpy.types.Image:
        size = (512, 512)
        image = PIL.Image.new(mode='RGBA', size=size)
        draw = PIL.ImageDraw.Draw(image)

        # jeans
        draw.rectangle(xy=((256, 280), (317, 291)), fill=(48, 64, 112))
        draw.line(xy=((256, 283), (317, 283)), fill=(24, 40, 88))

        # shirt
        draw.rectangle(xy=((256, 242), (317, 279)), fill=(224, 232, 232))
        draw.rectangle(xy=((262, 227), (265, 242)), fill=(224, 232, 232))
        draw.polygon(xy=((256, 242), (261, 242), (256, 250)), fill=(248, 208, 168))
        draw.line(xy=((256, 251), (260, 253), (265, 242), (317, 242)),
                  fill=(200, 200, 200))

        # mirror
        image.alpha_composite(image.transpose(PIL.Image.FLIP_LEFT_RIGHT))

        # buttons
        draw.line(xy=((256, 251), (256, 279)), fill=(200, 200, 200))
        for y in range(4):
            y *= 7
            draw.rectangle(xy=((253, 255 + y), (254, 256 + y)),
                           fill=(190, 190, 190))

        filepath = '03TmpTorso.png'
        image.save(filepath)
        return D.images.load(filepath, check_existing=True)

    @classmethod
    def arm(cls) -> bpy.types.Object:
        bm = bmesh.new()
        uv_layer = bm.loops.layers.uv.new()

        l1 = bm_create_plane(bm, fill=True)['verts']
        bmesh.ops.scale(bm, verts=l1, vec=(0.11, 0.07, 1.0))
        bmesh.ops.rotate(bm, verts=l1, cent=l1[0].co,
                         matrix=Rotation(radians(10), 4, 'Y'))
        bmesh.ops.translate(bm, verts=l1, vec=(0.12627, 0.019375, 1.3378))

        l4 = bm_create_plane(bm, fill=False)['verts']
        bmesh.ops.scale(bm, verts=l4, vec=(0.06, 0.06, 1.0))
        bmesh.ops.rotate(bm, verts=l4, matrix=Rotation(radians(-10), 4, 'Y'))
        bmesh.ops.translate(bm, verts=l4, vec=(0.19385, 0.02, 1.0928))

        l5 = bm_create_plane(bm, fill=False)['verts']
        bmesh.ops.scale(bm, verts=l5, vec=(0.08, 0.06, 1.0))
        bmesh.ops.rotate(bm, verts=l5, matrix=Rotation(radians(-12), 4, 'Y'))
        bmesh.ops.translate(bm, verts=l5, vec=(0.23261, 0.02, 0.94141))

        l6 = bm_create_plane(bm, fill=False)['verts']
        bmesh.ops.scale(bm, verts=l6, vec=(0.12, 0.15, 1.0))
        bmesh.ops.translate(bm, verts=l6, vec=(0.24, 0.0, 0.81))
        bmesh.ops.translate(bm, verts=l6[1::1], vec=(0.0, 0.0, -0.01))
        bmesh.ops.translate(bm, verts=l6[2:3], vec=(0.03, 0.0, 0.0))

        l7 = bm_create_plane(bm, fill=False)['verts']
        bmesh.ops.scale(bm, verts=l7, vec=(0.0, 0.12, 1.0))
        bmesh.ops.translate(bm, verts=l7, vec=(0.22202, 0.01375, 0.76588))

        bmesh.ops.bridge_loops(bm, edges=bm.edges)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0001)

        islands = bm_uv_cube_project(bm.faces, uv_layer)
        offset = Vec(0.5, islands['front'].bbox['b'] + 1.25)
        bm_uv_cube_position(islands, uv_layer, init_offset=offset)
        cls.scale_uvs(bm.faces, uv_layer, islands)

        mesh = D.meshes.new('arm')
        bm.to_mesh(mesh)
        bm.free()
        return D.objects.new(mesh.name, mesh)

    @classmethod
    def leg(cls) -> bpy.types.Object:
        # bmesh
        bm = bmesh.new()
        uv_layer = bm.loops.layers.uv.new()

        ltop = bm_create_plane(bm, fill=False)['verts']
        bmesh.ops.scale(bm, verts=ltop, vec=(0.16, 0.16, 1.0))
        bmesh.ops.scale(bm, verts=ltop[1::2], vec=(1.0, 1.15, 1.0))
        bmesh.ops.translate(bm, verts=ltop, vec=(0.08, 0.016, 0.83))
        bmesh.ops.translate(bm, verts=ltop[1::2], vec=(0.0, 0.0, 0.084))

        lmid = bm_create_plane(bm, fill=False)['verts']
        bmesh.ops.scale(bm, verts=lmid, vec=(0.1, 0.1, 1.0))
        bmesh.ops.translate(bm, verts=lmid, vec=(0.065, 0.025, 0.55))

        lbot = bm_create_plane(bm, fill=False)['verts']
        bmesh.ops.scale(bm, verts=lbot, vec=(0.1, 0.1, 1.0))
        bmesh.ops.translate(bm, verts=lbot, vec=(0.06566, 0.033125, 0.0))
        bmesh.ops.translate(bm, verts=lbot[0:2], vec=(0.0, 0.0, 0.15))

        lfeet = bm_create_plane(bm, fill=True)['verts']
        bmesh.ops.scale(bm, verts=lfeet, vec=(0.1, 0.06, 1.0))
        bmesh.ops.translate(bm, verts=lfeet, vec=(0.06625, -0.178 + 0.03, 0.0))
        bmesh.ops.rotate(bm, verts=lfeet, cent=lfeet[0].co,
                         matrix=Rotation(radians(80), 4, 'X'))

        bmesh.ops.bridge_loops(bm, edges=bm.edges)

        # UVs
        islands = bm_uv_cube_project(bm.faces, uv_layer)
        offset = Vec(0.5, islands['front'].bbox['b'])
        bm_uv_cube_position(islands, uv_layer, init_offset=offset)
        cls.scale_uvs(bm.faces, uv_layer, islands)

        # mesh & object
        mesh = D.meshes.new('leg')
        bm.to_mesh(mesh)
        bm.free()
        object = D.objects.new(mesh.name, mesh)

        # texture & material
        texture = cls.leg_texture()
        material = cls.material(texture)
        object.data.materials.append(material)

        return object

    @classmethod
    def leg_texture(cls) -> bpy.types.Image:
        size = (512, 512)
        image = PIL.Image.new(mode='RGBA', size=size)
        draw = PIL.ImageDraw.Draw(image)

        # jeans
        draw.rectangle(xy=((256, 385), (390, 480)), fill=(48, 64, 112))
        draw.rectangle(xy=((256, 478), (390, 480)), fill=(24, 40, 88))

        # shoe
        draw.rectangle(xy=((256, 489), (390, 512)), fill=(224, 232, 232))
        draw.rectangle(xy=((256, 378), (269, 384)), fill=(224, 232, 232))
        draw.rectangle(xy=((256, 325), (269, 361)), fill=(224, 232, 232))

        # mirror
        image.alpha_composite(image.transpose(PIL.Image.FLIP_LEFT_RIGHT))

        filepath = '03TmpLeg.png'
        image.save(filepath)
        return D.images.load(filepath, check_existing=True)

    @classmethod
    def pelvis(cls) -> bpy.types.Object:
        bm = bmesh.new()
        uv_layer = bm.loops.layers.uv.new()

        # create pelvis from torso and leg
        shared.bm_absorb_obj(bm, cls.torso())
        shared.bm_absorb_obj(bm, cls.leg())
        bmesh.ops.bridge_loops(bm, edges=bm.edges[6:8] + bm.edges[17:18]
                               + bm.edges[25:29])
        bmesh.ops.subdivide_edges(bm, edges=bm.edges[55:57], cuts=1)
        bm.verts.ensure_lookup_table()
        bm.verts[32].co = bm.verts[19].co
        bm.verts[33].co.y = bm.verts[19].co.y
        bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=0.0001)

        # uvs
        islands = bm_uv_cube_project(bm.faces[23:27], uv_layer)
        offset = Vec(0.5, islands['front'].bbox['b'] + 0.55)
        bm_uv_cube_position(islands, uv_layer, init_offset=offset)
        cls.scale_uvs(bm.faces[23:27], uv_layer, islands)

        # mesh & object
        mesh = D.meshes.new('torso_pelvis_leg')
        bm.to_mesh(mesh)
        bm.free()
        object = D.objects.new(mesh.name, mesh)

        # texture & material
        texture = cls.pelvis_texture()
        material = cls.material(texture)
        object.data.materials.append(material)

        return object

    @classmethod
    def pelvis_texture(cls) -> bpy.types.Image:
        size = (512, 512)
        image = PIL.Image.new(mode='RGBA', size=size)
        draw = PIL.ImageDraw.Draw(image)

        draw.rectangle(xy=((256, 297), (330, 321)), fill=(48, 64, 112))
        image.alpha_composite(image.transpose(PIL.Image.FLIP_LEFT_RIGHT))

        filepath = '03TmpPelvis.png'
        image.save(filepath)
        return D.images.load(filepath, check_existing=True)

    @classmethod
    def material(cls, texture) -> bpy.types.Material:
        material = D.materials.new(name='material')
        material.use_nodes = True

        # nodes
        nodes = material.node_tree.nodes
        nodes.new('ShaderNodeTexImage')
        nodes['Image Texture'].image = texture
        nodes['Image Texture'].interpolation = 'Closest'
        nodes['Principled BSDF'].inputs['Specular'].default_value = 0.0

        # links
        links = material.node_tree.links
        links.new(nodes['Image Texture'].outputs['Color'],
                  nodes['Principled BSDF'].inputs['Base Color'])

        return material

    @classmethod
    def texture(cls) -> bpy.types.Image:
        img_out = PIL.Image.new(mode='RGBA', size=(512, 512), color=(248, 208, 168))
        for p in Path().glob('03Tmp*.png'):
            if str(p) in D.images:
                D.images.remove(D.images[str(p)])
            img_in = PIL.Image.open(p)
            img_out.alpha_composite(img_in)

        filepath = '03Texture.png'
        img_out.save(filepath)
        return D.images.load(filepath, check_existing=True)

if __name__ == '__main__':
    shared.delete_data()
    D.scenes[0].collection.objects.link(Character.object())
