"""
Builds the Park English hero character (v2): a cartoon, low-poly, rigged avatar
modelled on the "English Adventure World" character sheet.

Run headless:
    /Applications/Blender.app/Contents/MacOS/Blender --background \
        --python tools/blender/build_character.py -- assets/characters

Or paste into Blender's Python console / the Blender MCP `execute_blender_code`
tool and call `build(out_dir)`.

Conventions (the game relies on these):
- The character faces -Y in Blender, which is +Z (forward) in glTF / Three.js.
- Every part is its own object so the game can toggle or recolor it. Names:
    Hair_*      hair variants, show one          Outfit parts: Hood*, Torso, Sleeve*, Pants*, Skirt
    Hat_*, Glasses_*, Headphones_*, Backpack*    accessories, optional
    Eyes*, Mouth_*, Brow*                        face sets, show one eye set and one mouth
- Materials are named M_* and are the recolor hooks (M_Hair, M_Shirt, M_Pants, ...).
- One shared skeleton with elbows and knees, rigid skinning (one bone per part).
- NLA tracks / glTF animations: Idle, Walk, Run, Wave, Clap, Laugh, Think, Dance, Heart.
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector

OUT_DIR_DEFAULT = "assets/characters"
COLLECTION = "Character_Hero"
FPS = 24


# ---------------------------------------------------------------- materials
def srgb_to_linear(value):
    return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4


def hex_to_linear(hex_color):
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) / 255 for i in (0, 2, 4))
    return (srgb_to_linear(r), srgb_to_linear(g), srgb_to_linear(b), 1.0)


PALETTE = {
    "M_Skin": "#ffd0ad",
    "M_SkinShade": "#f0a98a",
    "M_Hair": "#6b3f27",
    "M_Shirt": "#2f5fd0",
    "M_Sleeve": "#5f8be8",
    "M_Rib": "#2447a3",
    "M_Emblem": "#bcd3ff",
    "M_Pants": "#34363c",
    "M_Skirt": "#4b6fb3",
    "M_Shoes": "#2f5fd0",
    "M_Sole": "#f6f4ee",
    "M_EyeWhite": "#ffffff",
    "M_Iris": "#6b3b25",
    "M_Pupil": "#1c1210",
    "M_EyeShine": "#ffffff",
    "M_Brow": "#4a2c1b",
    "M_Cheek": "#ff9a8f",
    "M_Mouth": "#8f2f3a",
    "M_Tongue": "#ff8a96",
    "M_Backpack": "#5b3d2b",
    "M_Strap": "#47301f",
    "M_Headphones": "#b9bec6",
    "M_Cap": "#2f7d5b",
    "M_Frame": "#2a2a33",
}


def make_materials():
    materials = {}
    for name, hex_color in PALETTE.items():
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = hex_to_linear(hex_color)
            bsdf.inputs["Roughness"].default_value = 0.85
            if "Metallic" in bsdf.inputs:
                bsdf.inputs["Metallic"].default_value = 0.0
        mat.diffuse_color = hex_to_linear(hex_color)
        materials[name] = mat
    return materials


# ---------------------------------------------------------------- geometry
def new_part(name, bm, collection, material):
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    mesh.polygons.foreach_set("use_smooth", [True] * len(mesh.polygons))
    mesh.update()
    mesh.materials.append(material)
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    return obj


HEAD_CENTER = Vector((0, 0, 1.12))


def ellipsoid(name, center, scale, material, collection, rot=(0, 0, 0), cut=None, sink=None, segments=(18, 12)):
    """A smooth blob. `cut(co)` returns True for vertices to delete (hair caps, hats)."""
    bm = bmesh.new()
    matrix = (
        Matrix.Translation(Vector(center))
        @ Euler(rot, "XYZ").to_matrix().to_4x4()
        @ Matrix.Diagonal(Vector((*scale, 1.0)))
    )
    bmesh.ops.create_uvsphere(bm, u_segments=segments[0], v_segments=segments[1], radius=1.0, matrix=matrix)
    if cut:
        doomed = [v for v in bm.verts if cut(v.co)]
        bmesh.ops.delete(bm, geom=doomed, context="VERTS")
    if sink:
        for v in bm.verts:
            if sink(v.co):
                v.co = HEAD_CENTER + (v.co - HEAD_CENTER) * 0.7
    return new_part(name, bm, collection, material)


def frustum(name, center, r_bottom, r_top, height, material, collection, squash=0.82):
    """A smooth flared cone, used for the skirt."""
    bm = bmesh.new()
    matrix = Matrix.Translation(Vector(center)) @ Matrix.Diagonal(Vector((1.0, squash, 1.0, 1.0)))
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=28, radius1=r_bottom, radius2=r_top, depth=height, matrix=matrix)
    return new_part(name, bm, collection, material)


def torus(name, center, major, minor, material, collection, segs=28, rings=8):
    """A ring in the XZ plane (faces -Y), used for glasses."""
    bm = bmesh.new()
    cx, cy, cz = center
    grid = []
    for i in range(segs):
        theta = math.tau * i / segs
        row = []
        for j in range(rings):
            phi = math.tau * j / rings
            r = major + minor * math.cos(phi)
            row.append(bm.verts.new((cx + r * math.cos(theta), cy + minor * math.sin(phi), cz + r * math.sin(theta))))
        grid.append(row)
    for i in range(segs):
        for j in range(rings):
            a, b = grid[i][j], grid[(i + 1) % segs][j]
            c, d = grid[(i + 1) % segs][(j + 1) % rings], grid[i][(j + 1) % rings]
            bm.faces.new((a, b, c, d))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return new_part(name, bm, collection, material)


def star(name, center, outer, inner, depth, material, collection):
    """A 5-point star plate facing -Y, used for the hoodie emblem."""
    bm = bmesh.new()
    cx, cy, cz = center
    pts = []
    for k in range(10):
        r = outer if k % 2 == 0 else inner
        a = math.pi / 2 + k * math.pi / 5
        pts.append((cx + r * math.cos(a), cz + r * math.sin(a)))
    front = [bm.verts.new((x, cy - depth, z)) for x, z in pts]
    back = [bm.verts.new((x, cy, z)) for x, z in pts]
    bm.faces.new(front[::-1])
    bm.faces.new(back)
    for k in range(10):
        n = (k + 1) % 10
        bm.faces.new((front[k], front[n], back[n], back[k]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh_obj = new_part(name, bm, collection, material)
    mesh_obj.data.polygons.foreach_set("use_smooth", [False] * len(mesh_obj.data.polygons))
    return mesh_obj


# ---------------------------------------------------------------- character
def build_parts(collection, mats):
    """Returns {bone_name: [objects]} describing which bone drives which part."""
    bones = ("Spine", "Head", "Hips", "UpperArm.L", "LowerArm.L", "UpperArm.R", "LowerArm.R",
             "UpperLeg.L", "LowerLeg.L", "UpperLeg.R", "LowerLeg.R")
    parts = {b: [] for b in bones}

    def add(bone, obj):
        parts[bone].append(obj)
        return obj

    E = lambda *a, **k: ellipsoid(*a, collection=collection, **k)

    # ---- head, neck
    add("Head", E("Head", (0, 0, 1.12), (0.345, 0.315, 0.31), mats["M_Skin"], segments=(32, 18)))
    add("Spine", E("Neck", (0, 0, 0.9), (0.085, 0.08, 0.07), mats["M_Skin"], segments=(14, 8)))
    for side, sx in (("L", 1), ("R", -1)):
        add("Head", E(f"Ear.{side}", (0.335 * sx, 0.01, 1.1), (0.05, 0.045, 0.065), mats["M_Skin"], segments=(12, 8)))
        # eyes: white, iris, pupil, two highlights
        add("Head", E(f"Eye.{side}", (0.12 * sx, -0.272, 1.135), (0.078, 0.03, 0.092), mats["M_EyeWhite"], segments=(16, 12)))
        add("Head", E(f"Iris.{side}", (0.12 * sx, -0.294, 1.132), (0.062, 0.024, 0.078), mats["M_Iris"], segments=(16, 12)))
        add("Head", E(f"Pupil.{side}", (0.12 * sx, -0.307, 1.132), (0.036, 0.014, 0.046), mats["M_Pupil"], segments=(12, 8)))
        add("Head", E(f"EyeShine.{side}", (0.106 * sx, -0.318, 1.16), (0.022, 0.012, 0.025), mats["M_EyeShine"], segments=(10, 8)))
        add("Head", E(f"EyeShine2.{side}", (0.138 * sx, -0.317, 1.1), (0.011, 0.01, 0.012), mats["M_EyeShine"], segments=(8, 6)))
        add("Head", E(f"Brow.{side}", (0.125 * sx, -0.262, 1.245), (0.06, 0.012, 0.014), mats["M_Brow"], rot=(0, 0.12 * sx, 0), segments=(12, 8)))
        add("Head", E(f"Cheek.{side}", (0.205 * sx, -0.222, 1.03), (0.055, 0.014, 0.034), mats["M_Cheek"], rot=(0, 0, 0.5 * sx), segments=(12, 8)))
        # happy closed eyes (alternate set)
        add("Head", E(f"EyesHappy.{side}", (0.12 * sx, -0.295, 1.14), (0.07, 0.012, 0.022), mats["M_Pupil"], rot=(0, 0.0, 0), segments=(14, 8),
                      cut=lambda v: v.z < 1.14))
    add("Head", E("Nose", (0, -0.298, 1.06), (0.022, 0.016, 0.016), mats["M_SkinShade"], segments=(10, 8)))
    # mouths: open smile (default), closed smile, surprised
    add("Head", E("Mouth_Open", (0, -0.282, 0.985), (0.075, 0.022, 0.046), mats["M_Mouth"], cut=lambda v: v.z > 0.985, segments=(16, 10)))
    add("Head", E("Tongue", (0, -0.292, 0.968), (0.036, 0.012, 0.02), mats["M_Tongue"], segments=(10, 8)))
    add("Head", E("Mouth_Smile", (0, -0.292, 1.0), (0.06, 0.012, 0.022), mats["M_Mouth"], cut=lambda v: v.z > 1.0, segments=(14, 8)))
    add("Head", E("Mouth_O", (0, -0.292, 0.985), (0.03, 0.02, 0.04), mats["M_Mouth"], segments=(12, 10)))

    # ---- hair variants (one object each; the game shows one)
    # oval hairline: removes the face area, keeps hair over the forehead, temples and sides
    fringe_cut = lambda v: v.y < -0.05 and (v.x / 0.3) ** 2 + ((v.z - 1.1) / 0.28) ** 2 < 1

    CAP_C, CAP_S = (0, 0.045, 1.185), (0.375, 0.35, 0.335)

    def on_cap(x, z, lift=1.02):
        """A point just outside the hair cap surface above (x, z), so locks lie flat on it."""
        inside = 1 - (x / CAP_S[0]) ** 2 - ((z - CAP_C[2]) / CAP_S[2]) ** 2
        return (x, CAP_C[1] - CAP_S[1] * math.sqrt(max(inside, 0.02)) * lift, z)

    def hair_cap(name, back_z, scale=CAP_S):
        # the lower rim slopes: low at the nape, high at the temples, so it never reads as a bowl edge
        def cut(v):
            rim = back_z + (1.17 - back_z) * min(1.0, max(0.0, -v.y / 0.3))
            return v.z < rim or fringe_cut(v)
        return add("Head", E(name, CAP_C, scale, mats["M_Hair"], sink=cut, segments=(44, 28)))

    # messy boy hair: cap plus swept locks lying on the surface
    hair_cap("Hair_Messy", 1.02)
    for k, (x, z, sc, rz) in enumerate([
        (-0.2, 1.4, (0.1, 0.05, 0.04), 0.7), (-0.08, 1.44, (0.1, 0.05, 0.04), 0.45),
        (0.05, 1.45, (0.1, 0.05, 0.04), 0.2), (0.17, 1.42, (0.09, 0.05, 0.04), -0.25),
        (0.0, 1.5, (0.14, 0.07, 0.035), 0.3), (-0.13, 1.49, (0.1, 0.07, 0.035), 0.6),
    ]):
        add("Head", E(f"Hair_MessyLock{k}", on_cap(x, z), sc, mats["M_Hair"], rot=(0, 0, rz), segments=(14, 8)))
    # bob with straight fringe
    hair_cap("Hair_Bob", 0.96, scale=(0.39, 0.365, 0.345))
    add("Head", E("Hair_BobBack", (0, 0.12, 1.03), (0.37, 0.2, 0.3), mats["M_Hair"], segments=(18, 12)))
    add("Head", E("Hair_BobFringe", (0, -0.2, 1.37), (0.27, 0.06, 0.06), mats["M_Hair"], segments=(16, 10)))
    for side, sx in (("L", 1), ("R", -1)):
        add("Head", E(f"Hair_BobSide.{side}", (0.335 * sx, -0.02, 1.02), (0.06, 0.13, 0.22), mats["M_Hair"], segments=(12, 10)))
    # double buns
    hair_cap("Hair_Buns", 1.02)
    for side, sx in (("L", 1), ("R", -1)):
        add("Head", E(f"Hair_Bun.{side}", (0.23 * sx, 0.05, 1.5), (0.11, 0.11, 0.11), mats["M_Hair"], segments=(14, 10)))
    add("Head", E("Hair_BunFringe", (0, -0.2, 1.37), (0.26, 0.06, 0.06), mats["M_Hair"], segments=(16, 10)))
    # long hair
    hair_cap("Hair_Long", 0.9)
    add("Head", E("Hair_LongBack", (0, 0.14, 0.88), (0.34, 0.14, 0.42), mats["M_Hair"], segments=(18, 12)))
    add("Head", E("Hair_LongFringe", (0, -0.2, 1.37), (0.27, 0.06, 0.06), mats["M_Hair"], rot=(0, 0, 0.05), segments=(16, 10)))

    # ---- accessories
    add("Head", E("Hat_CapTop", (0, 0.015, 1.36), (0.385, 0.36, 0.22), mats["M_Cap"], cut=lambda v: v.z < 1.33, segments=(24, 12)))
    add("Head", E("Hat_CapBrim", (0, -0.33, 1.33), (0.24, 0.2, 0.025), mats["M_Cap"], rot=(0.1, 0, 0), segments=(16, 8)))
    for side, sx in (("L", 1), ("R", -1)):
        add("Head", torus(f"Glasses_Lens.{side}", (0.125 * sx, -0.312, 1.135), 0.085, 0.009, mats["M_Frame"], collection))
        add("Head", E(f"Glasses_Temple.{side}", (0.31 * sx, -0.16, 1.14), (0.012, 0.17, 0.012), mats["M_Frame"], segments=(8, 6)))
    add("Head", E("Glasses_Bridge", (0, -0.318, 1.145), (0.04, 0.01, 0.01), mats["M_Frame"], segments=(8, 6)))

    # headphones worn around the neck (as in the reference)
    for side, sx in (("L", 1), ("R", -1)):
        add("Spine", E(f"Headphones_Cup.{side}", (0.205 * sx, -0.06, 0.86), (0.075, 0.05, 0.095), mats["M_Headphones"], rot=(0, 0, 0.25 * sx), segments=(16, 10)))
        add("Spine", E(f"Headphones_Rim.{side}", (0.2 * sx, -0.095, 0.86), (0.058, 0.018, 0.078), mats["M_Frame"], rot=(0, 0, 0.25 * sx), segments=(14, 8)))
    for k in range(9):
        a = math.pi * k / 8
        add("Spine", E(f"Headphones_Band{k}", (math.cos(a) * 0.205, 0.04 + math.sin(a) * 0.08, 0.9), (0.024, 0.024, 0.024), mats["M_Headphones"], segments=(8, 6)))

    # backpack with straps
    add("Spine", E("Backpack", (0, 0.2, 0.72), (0.2, 0.09, 0.25), mats["M_Backpack"], segments=(18, 12)))
    add("Spine", E("BackpackPocket", (0, 0.285, 0.64), (0.14, 0.04, 0.12), mats["M_Strap"], segments=(14, 10)))
    for side, sx in (("L", 1), ("R", -1)):
        add("Spine", E(f"BackpackStrap.{side}", (0.13 * sx, -0.1, 0.82), (0.05, 0.09, 0.15), mats["M_Strap"], rot=(0.15, 0, 0), segments=(10, 8)))

    # ---- hoodie torso
    add("Spine", E("Torso", (0, 0, 0.77), (0.235, 0.18, 0.2), mats["M_Shirt"], segments=(26, 16)))
    add("Spine", E("TorsoLower", (0, 0, 0.6), (0.22, 0.17, 0.15), mats["M_Shirt"], segments=(24, 14)))
    add("Spine", E("HoodHem", (0, 0, 0.49), (0.222, 0.172, 0.035), mats["M_Rib"], segments=(24, 10)))
    add("Spine", E("HoodCollar", (0, 0.0, 0.94), (0.14, 0.12, 0.045), mats["M_Shirt"], segments=(18, 8)))
    add("Spine", E("HoodBack", (0, 0.1, 0.9), (0.17, 0.09, 0.1), mats["M_Shirt"], segments=(16, 10)))
    add("Spine", star("Emblem", (0, -0.19, 0.78), 0.07, 0.03, 0.012, mats["M_Emblem"], collection))
    add("Spine", E("HoodPocket", (0, -0.158, 0.56), (0.12, 0.035, 0.05), mats["M_Shirt"], segments=(16, 8)))

    # ---- arms: upper sleeve, forearm + cuff + hand with thumb
    for side, sx in (("L", 1), ("R", -1)):
        add(f"UpperArm.{side}", E(f"SleeveUpper.{side}", (0.3 * sx, 0, 0.8), (0.08, 0.08, 0.13), mats["M_Sleeve"], segments=(14, 10)))
        add(f"LowerArm.{side}", E(f"SleeveLower.{side}", (0.325 * sx, 0, 0.62), (0.075, 0.075, 0.12), mats["M_Shirt"], segments=(14, 10)))
        add(f"LowerArm.{side}", E(f"Cuff.{side}", (0.33 * sx, 0, 0.51), (0.08, 0.08, 0.03), mats["M_Rib"], segments=(14, 8)))
        add(f"LowerArm.{side}", E(f"Hand.{side}", (0.335 * sx, 0, 0.45), (0.068, 0.055, 0.075), mats["M_Skin"], segments=(14, 10)))
        add(f"LowerArm.{side}", E(f"Thumb.{side}", (0.385 * sx, -0.03, 0.455), (0.026, 0.026, 0.045), mats["M_Skin"], rot=(0, 0.5 * sx, 0), segments=(10, 8)))

    # ---- hips, cargo pants, skirt
    add("Hips", E("PantsHip", (0, 0, 0.45), (0.225, 0.17, 0.09), mats["M_Pants"], segments=(22, 12)))
    add("Hips", frustum("Skirt", (0, 0, 0.4), 0.3, 0.2, 0.2, mats["M_Skirt"], collection))
    for side, sx in (("L", 1), ("R", -1)):
        add(f"UpperLeg.{side}", E(f"PantsThigh.{side}", (0.1 * sx, 0, 0.37), (0.115, 0.115, 0.155), mats["M_Pants"], segments=(14, 10)))
        add(f"UpperLeg.{side}", E(f"PantsPocket.{side}", (0.205 * sx, -0.01, 0.35), (0.04, 0.075, 0.07), mats["M_Pants"], segments=(10, 8)))
        add(f"LowerLeg.{side}", E(f"PantsShin.{side}", (0.1 * sx, 0, 0.19), (0.105, 0.105, 0.125), mats["M_Pants"], segments=(14, 10)))
        add(f"LowerLeg.{side}", E(f"PantsCuff.{side}", (0.1 * sx, 0, 0.1), (0.11, 0.11, 0.03), mats["M_Pants"], segments=(14, 8)))
        # sneakers: blue upper, white sole, toe cap, laces
        add(f"LowerLeg.{side}", E(f"Shoe.{side}", (0.1 * sx, -0.045, 0.075), (0.1, 0.18, 0.075), mats["M_Shoes"], segments=(16, 10)))
        add(f"LowerLeg.{side}", E(f"ShoeSole.{side}", (0.1 * sx, -0.045, 0.03), (0.105, 0.195, 0.035), mats["M_Sole"], segments=(16, 8)))
        add(f"LowerLeg.{side}", E(f"ShoeToe.{side}", (0.1 * sx, -0.14, 0.06), (0.075, 0.075, 0.05), mats["M_Sole"], segments=(12, 8)))
        add(f"LowerLeg.{side}", E(f"ShoeLaces.{side}", (0.1 * sx, -0.075, 0.125), (0.05, 0.06, 0.022), mats["M_Sole"], segments=(10, 8)))
    for side, sx in (("L", 1), ("R", -1)):
        add(f"UpperLeg.{side}", E(f"BareThigh.{side}", (0.1 * sx, 0, 0.36), (0.095, 0.095, 0.15), mats["M_Skin"], segments=(12, 8)))
        add(f"LowerLeg.{side}", E(f"BareShin.{side}", (0.1 * sx, 0, 0.19), (0.085, 0.085, 0.125), mats["M_Skin"], segments=(12, 8)))
    return parts


LEG_BONES = ("UpperLeg.L", "LowerLeg.L", "UpperLeg.R", "LowerLeg.R")
LEG_STRETCH = 1.16  # longer legs, closer to the reference sheet
BODY_LIFT = 0.08


def stretch_z(z, bone):
    return z * LEG_STRETCH if bone in LEG_BONES else z + BODY_LIFT


def restyle(parts):
    """Lengthens the legs and lifts everything above the hips by the same amount."""
    for bone, objs in parts.items():
        for obj in objs:
            for v in obj.data.vertices:
                v.co.z = stretch_z(v.co.z, bone)
            obj.data.update()


BONES = [
    # name, head, tail, parent
    ("Root", (0, 0, 0), (0, 0, 0.2), None),
    ("Hips", (0, 0, 0.5), (0, 0, 0.58), "Root"),
    ("Spine", (0, 0, 0.58), (0, 0, 0.9), "Hips"),
    ("Head", (0, 0, 0.9), (0, 0, 1.5), "Spine"),
    ("UpperArm.L", (0.27, 0, 0.9), (0.32, 0, 0.7), "Spine"),
    ("LowerArm.L", (0.32, 0, 0.7), (0.335, 0, 0.45), "UpperArm.L"),
    ("UpperArm.R", (-0.27, 0, 0.9), (-0.32, 0, 0.7), "Spine"),
    ("LowerArm.R", (-0.32, 0, 0.7), (-0.335, 0, 0.45), "UpperArm.R"),
    ("UpperLeg.L", (0.1, 0, 0.5), (0.1, 0, 0.3), "Hips"),
    ("LowerLeg.L", (0.1, 0, 0.3), (0.1, 0, 0.06), "UpperLeg.L"),
    ("UpperLeg.R", (-0.1, 0, 0.5), (-0.1, 0, 0.3), "Hips"),
    ("LowerLeg.R", (-0.1, 0, 0.3), (-0.1, 0, 0.06), "UpperLeg.R"),
]


def build_rig(collection):
    data = bpy.data.armatures.new("CharacterRig")
    rig = bpy.data.objects.new("CharacterRig", data)
    collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    for name, head, tail, parent in BONES:
        bone = data.edit_bones.new(name)
        if name != "Root":
            head = (head[0], head[1], stretch_z(head[2], name))
            tail = (tail[0], tail[1], stretch_z(tail[2], name))
        bone.head, bone.tail = head, tail
        if parent:
            bone.parent = data.edit_bones[parent]
    bpy.ops.object.mode_set(mode="OBJECT")
    return rig


def skin(parts, rig):
    for bone, objs in parts.items():
        for obj in objs:
            group = obj.vertex_groups.new(name=bone)
            group.add(list(range(len(obj.data.vertices))), 1.0, "REPLACE")
            modifier = obj.modifiers.new("Armature", "ARMATURE")
            modifier.object = rig
            obj.parent = rig


# ---------------------------------------------------------------- animation
# Sign conventions (the rig is mirrored): rotating a hanging bone about +X by a positive
# angle swings its tip backwards (+Y); negative swings forwards. Rotating about Z lifts
# Arm.R outwards with a positive angle and Arm.L outwards with a negative angle.
def pose(rig, bone, frame, rot=None, loc=None):
    pb = rig.pose.bones[bone]
    pb.rotation_mode = "XYZ"
    if rot is not None:
        pb.rotation_euler = rot
        pb.keyframe_insert("rotation_euler", frame=frame)
    if loc is not None:
        pb.location = loc
        pb.keyframe_insert("location", frame=frame)


def new_action(rig, name):
    if rig.animation_data is None:
        rig.animation_data_create()
    action = bpy.data.actions.new(name)
    action.use_fake_user = True
    rig.animation_data.action = action
    return action


def finish_action(rig, action, name):
    track = rig.animation_data.nla_tracks.new()
    track.name = name
    strip = track.strips.new(name, 1, action)
    strip.name = name
    rig.animation_data.action = None


def cycle(rig, name, length, fn):
    """Records a looping animation by sampling fn(frame, t) for t in [0, 1)."""
    action = new_action(rig, name)
    for frame in range(length + 1):
        fn(frame + 1, (frame % length) / length)
    finish_action(rig, action, name)


def build_animations(rig):
    tau = math.tau
    s = lambda t, k=1, phase=0: math.sin(tau * (t * k + phase))
    c = lambda t, k=1, phase=0: math.cos(tau * (t * k + phase))
    zero = (0, 0, 0)

    def reset(f, skip=()):
        for bone in ("Spine", "Head", "UpperArm.L", "LowerArm.L", "UpperArm.R", "LowerArm.R",
                     "UpperLeg.L", "LowerLeg.L", "UpperLeg.R", "LowerLeg.R"):
            if bone not in skip:
                pose(rig, bone, f, rot=zero)
        if "Hips" not in skip:
            pose(rig, "Hips", f, rot=zero, loc=zero)

    def idle(f, t):
        reset(f, skip=("Hips", "Spine", "Head", "UpperArm.L", "UpperArm.R", "LowerArm.L", "LowerArm.R"))
        pose(rig, "Hips", f, rot=zero, loc=(0, 0, 0.01 * s(t)))
        pose(rig, "Spine", f, rot=(0.02 * s(t), 0, 0))
        pose(rig, "Head", f, rot=(0.03 * s(t, 1, 0.15), 0, 0.05 * s(t, 1, 0.5)))
        pose(rig, "UpperArm.L", f, rot=(0, 0, -0.06 + 0.02 * s(t, 1, 0.2)))
        pose(rig, "UpperArm.R", f, rot=(0, 0, 0.06 - 0.02 * s(t, 1, 0.2)))
        pose(rig, "LowerArm.L", f, rot=(-0.18, 0, 0))
        pose(rig, "LowerArm.R", f, rot=(-0.18, 0, 0))

    def locomotion(swing, bob, lean, knee):
        def fn(f, t):
            pose(rig, "Hips", f, rot=(0, 0, 0.05 * s(t)), loc=(0, 0, bob * abs(c(t))))
            pose(rig, "Spine", f, rot=(-lean, 0, -0.07 * s(t)))
            pose(rig, "Head", f, rot=(lean * 0.6, 0, 0.04 * s(t)))
            for side, ph in (("L", 0.0), ("R", 0.5)):
                leg = swing * s(t, 1, ph)
                pose(rig, f"UpperLeg.{side}", f, rot=(-leg, 0, 0))
                pose(rig, f"LowerLeg.{side}", f, rot=(knee * (0.55 + 0.45 * c(t, 1, ph)), 0, 0))
                pose(rig, f"UpperArm.{side}", f, rot=(leg * 0.9, 0, -0.1 if side == "L" else 0.1))
                pose(rig, f"LowerArm.{side}", f, rot=(-0.3 - 0.35 * max(0.0, -s(t, 1, ph)) - lean, 0, 0))
        return fn

    def wave(f, t):
        reset(f)
        pose(rig, "UpperArm.R", f, rot=(0, 0, 2.35))
        pose(rig, "LowerArm.R", f, rot=(0, 0, 0.55 * s(t, 3)))
        pose(rig, "UpperArm.L", f, rot=(0, 0, -0.06))
        pose(rig, "Head", f, rot=(0, 0, -0.12))
        pose(rig, "Hips", f, rot=zero, loc=(0, 0, 0.01 * s(t, 2)))

    def clap(f, t):
        reset(f, skip=("Hips",))
        k = 0.5 + 0.5 * s(t, 4)
        pose(rig, "UpperArm.L", f, rot=(-0.95, 0, 0.5 - 0.35 * k))
        pose(rig, "UpperArm.R", f, rot=(-0.95, 0, -0.5 + 0.35 * k))
        pose(rig, "LowerArm.L", f, rot=(-0.9, 0, 0.5 - 0.35 * k))
        pose(rig, "LowerArm.R", f, rot=(-0.9, 0, -0.5 + 0.35 * k))
        pose(rig, "Head", f, rot=(0.05 * s(t, 4), 0, 0))
        pose(rig, "Hips", f, rot=zero, loc=(0, 0, 0.015 * abs(s(t, 4))))

    def laugh(f, t):
        reset(f, skip=("Hips",))
        pose(rig, "Spine", f, rot=(0.14 + 0.05 * s(t, 4), 0, 0))
        pose(rig, "Head", f, rot=(0.3 + 0.08 * s(t, 4), 0, 0))
        pose(rig, "Hips", f, rot=zero, loc=(0, 0, 0.03 * abs(s(t, 4))))
        pose(rig, "UpperArm.L", f, rot=(-0.3, 0, -0.2 - 0.1 * s(t, 4)))
        pose(rig, "UpperArm.R", f, rot=(-0.3, 0, 0.2 + 0.1 * s(t, 4)))
        pose(rig, "LowerArm.L", f, rot=(-1.0, 0, 0))
        pose(rig, "LowerArm.R", f, rot=(-1.0, 0, 0))

    def think(f, t):
        reset(f, skip=("Hips",))
        pose(rig, "UpperArm.R", f, rot=(-0.55, 0, 0.35))
        pose(rig, "LowerArm.R", f, rot=(-2.25, 0, 0))
        pose(rig, "UpperArm.L", f, rot=(-0.2, 0, -0.1))
        pose(rig, "LowerArm.L", f, rot=(-1.1, 0, 0))
        pose(rig, "Head", f, rot=(0.1, 0, 0.2 + 0.03 * s(t)))
        pose(rig, "Hips", f, rot=zero, loc=(0, 0, 0.008 * s(t)))

    def dance(f, t):
        reset(f, skip=("Hips",))
        pose(rig, "Hips", f, rot=(0, 0, 0.12 * s(t)), loc=(0.05 * s(t), 0, 0.04 * abs(s(t, 2))))
        pose(rig, "Spine", f, rot=(0, 0, 0.1 * s(t)))
        pose(rig, "Head", f, rot=(0, 0, -0.18 * s(t)))
        pose(rig, "UpperArm.L", f, rot=(0, 0, -(1.55 + 0.55 * s(t, 2))))
        pose(rig, "UpperArm.R", f, rot=(0, 0, 1.55 + 0.55 * s(t, 2, 0.5)))
        pose(rig, "LowerArm.L", f, rot=(-0.4, 0, 0))
        pose(rig, "LowerArm.R", f, rot=(-0.4, 0, 0))
        pose(rig, "UpperLeg.L", f, rot=(-0.3 * s(t, 2), 0, 0))
        pose(rig, "UpperLeg.R", f, rot=(0.3 * s(t, 2), 0, 0))
        pose(rig, "LowerLeg.L", f, rot=(0.35 * max(0.0, s(t, 2)), 0, 0))
        pose(rig, "LowerLeg.R", f, rot=(0.35 * max(0.0, -s(t, 2)), 0, 0))

    def heart(f, t):
        reset(f, skip=("Hips",))
        pulse = 0.08 * s(t, 2)
        pose(rig, "UpperArm.L", f, rot=(0, 0, -(2.75 + pulse)))
        pose(rig, "UpperArm.R", f, rot=(0, 0, 2.75 + pulse))
        pose(rig, "LowerArm.L", f, rot=(0, 0, 1.35))
        pose(rig, "LowerArm.R", f, rot=(0, 0, -1.35))
        pose(rig, "Head", f, rot=(0, 0, 0.08 * s(t)))
        pose(rig, "Hips", f, rot=zero, loc=(0, 0, 0.012 * s(t, 2)))

    cycle(rig, "Idle", 48, idle)
    cycle(rig, "Walk", 24, locomotion(0.6, 0.025, 0.04, 0.95))
    cycle(rig, "Run", 16, locomotion(0.95, 0.055, 0.2, 1.5))
    cycle(rig, "Wave", 48, wave)
    cycle(rig, "Clap", 24, clap)
    cycle(rig, "Laugh", 24, laugh)
    cycle(rig, "Think", 48, think)
    cycle(rig, "Dance", 48, dance)
    cycle(rig, "Heart", 48, heart)


# ---------------------------------------------------------------- export / preview
def export_glb(path):
    bpy.ops.object.select_all(action="DESELECT")
    bpy.ops.export_scene.gltf(
        filepath=path,
        export_format="GLB",
        export_animations=True,
        export_animation_mode="NLA_TRACKS",
        export_materials="EXPORT",
        export_yup=True,
        export_apply=False,
    )


def setup_preview():
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x, scene.render.resolution_y = 640, 800
    shading = scene.display.shading
    shading.light = "STUDIO"
    shading.color_type = "MATERIAL"
    shading.show_object_outline = True
    scene.display.render_aa = "8"
    world = bpy.data.worlds.new("PreviewWorld")
    world.color = (0.82, 0.8, 0.96)
    scene.world = world
    cam = bpy.data.objects.new("PreviewCam", bpy.data.cameras.new("PreviewCam"))
    bpy.context.collection.objects.link(cam)
    scene.camera = cam
    return scene, cam


def render_view(scene, cam, path, location, target=(0, 0, 0.84), lens=70):
    cam.location = location
    cam.data.lens = lens
    direction = Vector(target) - Vector(location)
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


# Optional parts and the default set shown in the game's first outfit.
GROUPS = {
    "hair": ["Hair_Messy", "Hair_Bob", "Hair_Buns", "Hair_Long"],
    "mouth": ["Mouth_Open", "Tongue", "Mouth_Smile", "Mouth_O"],
    "eyes": ["Eye.", "Iris.", "Pupil.", "EyeShine.", "EyeShine2.", "EyesHappy."],
    "hat": ["Hat_"],
    "glasses": ["Glasses_"],
    "phones": ["Headphones_"],
    "pack": ["Backpack"],
    "skirt": ["Skirt"],
    "pants": ["PantsHip", "PantsThigh", "PantsPocket", "PantsShin", "PantsCuff"],
}


def show(collection, hair="Hair_Messy", mouth="open", eyes="open", hat=False, glasses=False,
         phones=True, pack=True, skirt=False):
    """Preview-only visibility; the exported GLB keeps every part visible."""
    for obj in collection.objects:
        if obj.type != "MESH":
            continue
        n = obj.name
        visible = True
        if n.startswith("Hair_"):
            visible = n.startswith(hair)
        elif n in ("Mouth_Open", "Tongue"):
            visible = mouth == "open"
        elif n == "Mouth_Smile":
            visible = mouth == "smile"
        elif n == "Mouth_O":
            visible = mouth == "o"
        elif n.startswith("EyesHappy."):
            visible = eyes == "happy"
        elif n.startswith(("Eye.", "Iris.", "Pupil.", "EyeShine")):
            visible = eyes == "open"
        elif n.startswith("Hat_"):
            visible = hat
        elif n.startswith("Glasses_"):
            visible = glasses
        elif n.startswith("Headphones_"):
            visible = phones
        elif n.startswith("Backpack"):
            visible = pack
        elif n == "Skirt":
            visible = skirt
        elif n.startswith(("PantsHip", "PantsThigh", "PantsPocket", "PantsShin", "PantsCuff")):
            visible = not skirt
        elif n.startswith(("BareThigh", "BareShin")):
            visible = skirt
        obj.hide_render = not visible


def reset_pose(rig):
    for pb in rig.pose.bones:
        pb.rotation_mode = "XYZ"
        pb.rotation_euler = (0, 0, 0)
        pb.location = (0, 0, 0)
    bpy.context.view_layer.update()


def build(out_dir=OUT_DIR_DEFAULT):
    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    collection = bpy.data.collections.new(COLLECTION)
    bpy.context.scene.collection.children.link(collection)
    bpy.context.scene.render.fps = FPS

    mats = make_materials()
    parts = build_parts(collection, mats)
    restyle(parts)
    rig = build_rig(collection)
    skin(parts, rig)
    build_animations(rig)

    export_glb(os.path.join(out_dir, "hero.glb"))

    scene, cam = setup_preview()
    for track in rig.animation_data.nla_tracks:  # tracks start together and would blend
        track.mute = True
    reset_pose(rig)
    p = lambda name: os.path.join(out_dir, name)
    show(collection)
    render_view(scene, cam, p("preview_front.png"), (0, -5.0, 0.8))
    render_view(scene, cam, p("preview_three_quarter.png"), (3.2, -3.8, 1.1))
    render_view(scene, cam, p("preview_side.png"), (5.0, 0, 0.8))
    render_view(scene, cam, p("preview_back.png"), (-2.6, 4.2, 1.1))
    # customization variants
    show(collection, hair="Hair_Bob", mouth="smile", eyes="happy", pack=False, phones=False, skirt=True)
    render_view(scene, cam, p("preview_variant_girl.png"), (0, -5.0, 0.8))
    show(collection, hair="Hair_Buns", glasses=True, phones=False)
    render_view(scene, cam, p("preview_variant_buns_glasses.png"), (0, -5.0, 0.8))
    show(collection, hair="Hair_Long", hat=True, mouth="o")
    render_view(scene, cam, p("preview_variant_cap.png"), (0, -5.0, 0.8))
    # animation stills
    show(collection)
    for action, frame, name, where in (
        ("Walk", 7, "preview_walk.png", (4.6, -3.2, 1.0)),
        ("Wave", 8, "preview_wave.png", (0, -5.0, 0.8)),
        ("Dance", 12, "preview_dance.png", (0, -5.0, 0.8)),
        ("Heart", 6, "preview_heart.png", (0, -5.0, 0.8)),
        ("Think", 10, "preview_think.png", (0, -5.0, 0.8)),
        ("Run", 5, "preview_run.png", (4.6, -3.2, 1.0)),
    ):
        reset_pose(rig)
        rig.animation_data.action = bpy.data.actions[action]
        scene.frame_set(frame)
        render_view(scene, cam, p(name), where)
    rig.animation_data.action = None
    for track in rig.animation_data.nla_tracks:
        track.mute = False
    for obj in collection.objects:
        obj.hide_render = False

    bpy.ops.wm.save_as_mainfile(filepath=p("hero.blend"))
    return {"out_dir": out_dir, "objects": len(collection.objects), "actions": [a.name for a in bpy.data.actions]}


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    print(build(argv[0] if argv else OUT_DIR_DEFAULT))
