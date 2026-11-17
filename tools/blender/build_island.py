"""
English Adventure World - Phase 1: floating island master layout (styled blockout).

Run headless:
    /Applications/Blender.app/Contents/MacOS/Blender --background \
        --python tools/blender/build_island.py -- assets/world --preview --export

Or paste into Blender and call build("assets/world", preview=True, export=True).

Phase 1 delivers
- 11 Collections: 00_Environment_Terrain, 01_Central_Park, 02_Coffee_Shop ... 10_Airport.
- A floating island about 120 m across: rolling green hills on top, a low-poly rock underside,
  a turquoise Water_Plane far below, a stream across the island with 3 wooden bridges, a ring
  road around the park, a road from the park to each of the 9 destinations, sidewalks and
  park pathways.
- Central_Park (radius 22 m) in the middle and the 9 other places around it:
    west / south-west  : Coffee Shop, Restaurant, Supermarket, Shopping Mall (the tallest of them)
    north / north-east : Library, School (sports court), Hotel (pool)
    east / south-east  : Train Station (tracks along the rim), Airport (runway on the flat rim)
- Shared materials only (Mat_*), Roughness 0.75, so the .glb needs very few draw calls.
- Every mesh has Scale 1 and Rotation 0 (transforms are baked); its origin sits on the ground
  at the centre of the building it belongs to.
- Scale: doors are 2.6 m, floors 3.2 m, matching a 1.6 m chibi character. A 1.6 m reference
  figure (REF_Scale_Chibi_1.6m) stands in the park; delete it before export if you do not want it.
- An isometric elevated 3/4 camera and a warm Sun with soft shadows frame the whole island.

World axes: +X east, +Y north, +Z up. After the glTF export (Y up) north becomes -Z.
"""

import json
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector

ROUGHNESS = 0.75
ISLAND_R = 60.0  # 120 m across
PARK_R = 22.0
RING_IN, RING_OUT = 24.0, 29.0  # ring road around the park

COLLECTIONS = [
    "00_Environment_Terrain", "01_Central_Park", "02_Coffee_Shop", "03_Restaurant", "04_Supermarket",
    "05_Shopping_Mall", "06_Library", "07_School", "08_Hotel", "09_Train_Station", "10_Airport",
]

# ------------------------------------------------------------------ shared materials
PALETTE = {
    "Mat_Grass": "#7ED06B", "Mat_Grass_Light": "#98DE7C", "Mat_Road": "#59606B", "Mat_Sidewalk": "#D9D4C7",
    "Mat_Path": "#EBCB9A", "Mat_Plaza": "#F4DFC4", "Mat_Plaza_Accent": "#E8A87C",
    "Mat_Wall_Cream": "#FFF1D6", "Mat_Wall_Orange": "#F6A55B", "Mat_Wall_Yellow": "#FFD36B",
    "Mat_Wall_Teal": "#7FD6C8", "Mat_Wall_Pink": "#F7B7C8", "Mat_Wall_Brick": "#D98C6E",
    "Mat_Roof_Coral": "#F2776B", "Mat_Roof_Red": "#D9544F", "Mat_Roof_Green": "#5FB38A",
    "Mat_Roof_Blue": "#5A86C6", "Mat_Roof_Gray": "#8C97A6", "Mat_Glass": "#9FD8F5",
    "Mat_Wood": "#B9824F", "Mat_Wood_Dark": "#7E5436", "Mat_White": "#FFFFFF", "Mat_Dark": "#3A3F4B",
    "Mat_Stripe_Brown": "#8B5A3C", "Mat_Water": "#2BB3C0", "Mat_Pool": "#47C2E8", "Mat_Rock": "#8C8A94",
    "Mat_Soil": "#8B6A4A", "Mat_Rail": "#9AA1AD", "Mat_Court": "#5B9BD5", "Mat_Runway": "#454B57",
    "Mat_Marking": "#F5F5F5", "Mat_Sign_Yellow": "#FFC83D", "Mat_Leaf": "#4CAF50", "Mat_Trunk": "#8B6B4A",
}
MATS = {}


def srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def make_materials():
    for name, hex_color in PALETTE.items():
        h = hex_color.lstrip("#")
        rgb = tuple(srgb_to_linear(int(h[i : i + 2], 16) / 255) for i in (0, 2, 4)) + (1.0,)
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = rgb
            bsdf.inputs["Roughness"].default_value = ROUGHNESS
            if "Metallic" in bsdf.inputs:
                bsdf.inputs["Metallic"].default_value = 0.0
        mat.diffuse_color = rgb
        mat.roughness = ROUGHNESS
        MATS[name] = mat


# ------------------------------------------------------------------ small helpers
def sstep(a, b, x):
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def seg_dist(p, a, b):
    """Distance from 2D point p to segment a-b."""
    ab, ap = b - a, p - a
    t = max(0.0, min(1.0, ap.dot(ab) / ab.length_squared)) if ab.length_squared else 0.0
    return (p - (a + ab * t)).length


def catmull(points, per_segment=24):
    """Dense polyline through points (Catmull-Rom)."""
    P = [Vector(p) for p in points]
    out = []
    for i in range(len(P) - 1):
        p0, p1, p2, p3 = P[max(i - 1, 0)], P[i], P[i + 1], P[min(i + 2, len(P) - 1)]
        for k in range(per_segment):
            t = k / per_segment
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(P[-1])
    return out


def add_object(coll, name, bm, mat, origin=(0, 0, 0), smooth=True, bevel=0.0):
    """Turns a bmesh into an object. `bm` holds coordinates relative to `origin`; transforms stay baked."""
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    mesh.polygons.foreach_set("use_smooth", [smooth] * len(mesh.polygons))
    mesh.update()
    mesh.materials.append(MATS[mat])
    obj = bpy.data.objects.new(name, mesh)
    obj.location = Vector(origin)
    coll.objects.link(obj)
    if bevel:
        mod = obj.modifiers.new("Bevel", "BEVEL")
        mod.width, mod.segments, mod.limit_method = bevel, 2, "ANGLE"
    return obj


# ------------------------------------------------------------------ building frame
class Frame:
    """Local building coordinates: +X right, +Y towards the front door, +Z up. Origin on the ground."""

    def __init__(self, coll, prefix, origin, yaw):
        self.coll, self.prefix, self.origin, self.yaw = coll, prefix, Vector(origin), yaw
        self.R = Matrix.Rotation(yaw, 4, "Z")

    def world(self, local):
        return self.origin + self.R @ Vector(local)

    def _emit(self, name, bm, mat, smooth=True, bevel=0.0):
        bmesh.ops.transform(bm, matrix=self.R, verts=bm.verts)  # rotation baked in, origin stays put
        return add_object(self.coll, f"{self.prefix}_{name}", bm, mat, self.origin, smooth, bevel)

    def box(self, name, c, size, mat, rot=(0, 0, 0), bevel=0.06):
        bm = bmesh.new()
        m = Matrix.Translation(Vector(c)) @ Euler(rot, "XYZ").to_matrix().to_4x4() @ Matrix.Diagonal(Vector((*size, 1.0)))
        bmesh.ops.create_cube(bm, size=1.0, matrix=m)
        return self._emit(name, bm, mat, smooth=False, bevel=bevel)

    def cyl(self, name, c, r_bottom, r_top, h, mat, seg=24, rot=(0, 0, 0), cap=True):
        bm = bmesh.new()
        m = Matrix.Translation(Vector(c)) @ Euler(rot, "XYZ").to_matrix().to_4x4()
        bmesh.ops.create_cone(bm, cap_ends=cap, cap_tris=False, segments=seg, radius1=r_bottom, radius2=r_top, depth=h, matrix=m)
        return self._emit(name, bm, mat, smooth=seg >= 16)

    def sphere(self, name, c, scale, mat, seg=(16, 10)):
        bm = bmesh.new()
        m = Matrix.Translation(Vector(c)) @ Matrix.Diagonal(Vector((*scale, 1.0)))
        bmesh.ops.create_uvsphere(bm, u_segments=seg[0], v_segments=seg[1], radius=1.0, matrix=m)
        return self._emit(name, bm, mat)

    def gable(self, name, c, w, d, h, mat, ridge="x", overhang=0.5):
        """A pitched roof. The ridge runs along local X (default) or Y; c is the centre of its base."""
        bm = bmesh.new()
        hw, hd = w / 2 + overhang, d / 2 + overhang
        cx, cy, cz = c
        if ridge == "x":
            a = [bm.verts.new((cx - hw, cy - hd, cz)), bm.verts.new((cx + hw, cy - hd, cz)), bm.verts.new((cx + hw, cy + hd, cz)), bm.verts.new((cx - hw, cy + hd, cz))]
            r = [bm.verts.new((cx - hw, cy, cz + h)), bm.verts.new((cx + hw, cy, cz + h))]
            bm.faces.new((a[0], a[1], r[1], r[0]))
            bm.faces.new((a[2], a[3], r[0], r[1]))
            bm.faces.new((a[1], a[2], r[1]))
            bm.faces.new((a[3], a[0], r[0]))
        else:
            a = [bm.verts.new((cx - hw, cy - hd, cz)), bm.verts.new((cx + hw, cy - hd, cz)), bm.verts.new((cx + hw, cy + hd, cz)), bm.verts.new((cx - hw, cy + hd, cz))]
            r = [bm.verts.new((cx, cy - hd, cz + h)), bm.verts.new((cx, cy + hd, cz + h))]
            bm.faces.new((a[1], a[2], r[1], r[0]))
            bm.faces.new((a[3], a[0], r[0], r[1]))
            bm.faces.new((a[0], a[1], r[0]))
            bm.faces.new((a[2], a[3], r[1]))
        bm.faces.new(a[::-1])
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        return self._emit(name, bm, mat, smooth=False)

    def text(self, name, body, c, size, mat, extrude=0.06):
        """Extruded lettering standing on the facade, readable from the front (+Y)."""
        curve = bpy.data.curves.new(f"tmp_{name}", "FONT")
        curve.body, curve.size, curve.extrude = body, size, extrude
        curve.align_x, curve.align_y = "CENTER", "CENTER"
        tmp = bpy.data.objects.new(f"tmp_{name}", curve)
        bpy.context.scene.collection.objects.link(tmp)
        bpy.context.view_layer.update()
        mesh = bpy.data.meshes.new_from_object(tmp.evaluated_get(bpy.context.evaluated_depsgraph_get()))
        bpy.data.objects.remove(tmp, do_unlink=True)
        bpy.data.curves.remove(curve)
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bpy.data.meshes.remove(mesh)
        stand = Matrix.Translation(Vector(c)) @ Matrix.Rotation(math.pi, 4, "Z") @ Matrix.Rotation(math.pi / 2, 4, "X")
        bmesh.ops.transform(bm, matrix=stand, verts=bm.verts)
        return self._emit(name, bm, mat, smooth=False)

    def star(self, name, c, outer, inner, depth, mat):
        """A flat 5-point star plate facing the front."""
        bm = bmesh.new()
        cx, cy, cz = c
        pts = [((outer if k % 2 == 0 else inner) * math.cos(math.pi / 2 + k * math.pi / 5), (outer if k % 2 == 0 else inner) * math.sin(math.pi / 2 + k * math.pi / 5)) for k in range(10)]
        near = [bm.verts.new((cx + x, cy, cz + z)) for x, z in pts]
        far = [bm.verts.new((cx + x, cy - depth, cz + z)) for x, z in pts]
        bm.faces.new(near)
        bm.faces.new(far[::-1])
        for k in range(10):
            n = (k + 1) % 10
            bm.faces.new((near[n], near[k], far[k], far[n]))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        return self._emit(name, bm, mat, smooth=False)

    def round_table(self, name, c, mat_top="Mat_Wood", umbrella="Mat_Roof_Coral"):
        x, y, z = c
        self.cyl(f"{name}_Pole", (x, y, z + 0.4), 0.08, 0.08, 0.8, "Mat_Wood_Dark", seg=8)
        self.cyl(f"{name}_Top", (x, y, z + 0.82), 0.6, 0.6, 0.08, mat_top, seg=20)
        for i, (dx, dy) in enumerate(((0.9, 0), (-0.9, 0), (0, 0.9), (0, -0.9))):
            self.box(f"{name}_Stool{i}", (x + dx, y + dy, z + 0.25), (0.4, 0.4, 0.5), "Mat_Wood", bevel=0.05)
        if umbrella:
            self.cyl(f"{name}_UmbrellaPole", (x, y, z + 1.4), 0.04, 0.04, 2.8, "Mat_Wood_Dark", seg=6)
            self.cyl(f"{name}_Umbrella", (x, y, z + 2.9), 1.5, 0.05, 0.6, umbrella, seg=12)


# ------------------------------------------------------------------ the 10 places (styled blockouts)
def build_coffee(f):
    f.box("Walls", (0, 0, 2.0), (9, 7, 4), "Mat_Wall_Cream")
    f.gable("Roof", (0, 0, 4.0), 9, 7, 1.8, "Mat_Roof_Coral")
    f.box("Door", (-2.4, 3.52, 1.1), (1.3, 0.1, 2.2), "Mat_Wood_Dark", bevel=0.03)
    for i, x in enumerate((0.6, 3.2)):
        f.box(f"Window{i}", (x, 3.52, 1.7), (2.0, 0.1, 1.4), "Mat_Glass", bevel=0.03)
    for i in range(6):  # striped awning
        f.box(f"Awning{i}", (-3.75 + i * 1.5, 4.4, 3.0), (1.5, 2.2, 0.12), "Mat_White" if i % 2 else "Mat_Stripe_Brown", rot=(-0.3, 0, 0), bevel=0.02)
    f.box("Counter", (-6.0, 4.6, 0.55), (3.2, 1.2, 1.1), "Mat_Wood")
    f.cyl("CupSign_Body", (0, 0, 6.15), 0.95, 0.75, 1.3, "Mat_White", seg=20)
    f.cyl("CupSign_Saucer", (0, 0, 5.46), 1.3, 1.3, 0.1, "Mat_Wood", seg=20)
    f.cyl("CupSign_Handle", (1.0, 0, 6.2), 0.3, 0.3, 0.2, "Mat_White", seg=12, rot=(math.pi / 2, 0, 0))
    f.text("Sign", "COFFEE SHOP", (0, 3.6, 3.4), 0.7, "Mat_Wood_Dark")
    f.round_table("Table0", (3.0, 7.2, 0))
    f.round_table("Table1", (6.4, 6.2, 0), umbrella="Mat_White")


def build_restaurant(f):
    f.box("WallsLower", (0, 0, 1.7), (12, 9, 3.4), "Mat_Wall_Orange")
    f.box("WallsUpper", (0, 0, 4.9), (11, 8, 3.0), "Mat_Wall_Brick")
    f.gable("Roof", (0, 0, 6.4), 11, 8, 1.8, "Mat_Roof_Red")
    f.box("Chimney", (3.5, -1.5, 8.2), (0.9, 0.9, 2.2), "Mat_Wall_Brick")
    f.box("Door", (0, 4.52, 1.2), (1.6, 0.1, 2.4), "Mat_Wood_Dark", bevel=0.03)
    for i, x in enumerate((-3.8, 3.8)):
        f.box(f"WindowLow{i}", (x, 4.52, 1.8), (2.4, 0.1, 1.5), "Mat_Glass", bevel=0.03)
    for i, x in enumerate((-3.5, 0, 3.5)):
        f.box(f"WindowUp{i}", (x, 4.02, 5.0), (2.0, 0.1, 1.4), "Mat_Glass", bevel=0.03)
    for i in range(8):
        f.box(f"Awning{i}", (-5.25 + i * 1.5, 5.3, 3.1), (1.5, 2.0, 0.12), "Mat_White" if i % 2 else "Mat_Roof_Red", rot=(-0.3, 0, 0), bevel=0.02)
    f.cyl("ChefHat_Band", (0, 0, 7.3 + 1.0), 0.95, 0.95, 0.9, "Mat_White", seg=20)
    for i, (x, y) in enumerate(((0, 0), (0.55, 0.2), (-0.55, 0.2), (0, -0.5))):
        f.sphere(f"ChefHat_Puff{i}", (x, y, 9.1), (0.65, 0.65, 0.6), "Mat_White")
    f.text("Sign", "RESTAURANT", (0, 4.12, 6.3), 0.65, "Mat_White")
    for i, (x, y) in enumerate(((-4, 9), (0, 9), (4, 9))):
        f.round_table(f"Table{i}", (x, y, 0), umbrella=None)
    for i, x in enumerate((-6.5, 6.5)):  # fence around the outdoor dining area
        for j in range(5):
            f.box(f"FencePost{i}{j}", (x, 6.8 + j * 1.2, 0.5), (0.12, 0.12, 1.0), "Mat_Wood_Dark", bevel=0.02)
        f.box(f"FenceRail{i}", (x, 9.2, 0.7), (0.08, 4.8, 0.1), "Mat_Wood", bevel=0.02)
    f.box("FenceFront", (0, 11.6, 0.7), (13.0, 0.08, 0.1), "Mat_Wood", bevel=0.02)
    f.box("ServeCounter", (6.2, 4.4, 0.6), (2.6, 1.0, 1.2), "Mat_Wood")


def build_supermarket(f):
    f.box("Walls", (0, 0, 2.5), (16, 11, 5), "Mat_Wall_Teal")
    f.box("RoofSlab", (0, 0, 5.15), (16.8, 11.8, 0.3), "Mat_Roof_Green")
    f.box("GlassFront", (0, 5.52, 1.8), (8, 0.1, 3.0), "Mat_Glass", bevel=0.03)
    f.box("DoorFrame", (0, 5.58, 1.8), (0.3, 0.1, 3.0), "Mat_White", bevel=0.02)
    f.box("SignBand", (0, 5.7, 4.2), (11, 0.4, 1.1), "Mat_Sign_Yellow")
    f.text("Sign", "SUPERMARKET", (0, 5.95, 4.2), 0.75, "Mat_Dark")
    f.sphere("AppleSign", (0, 0, 6.5), (1.1, 1.1, 1.0), "Mat_Roof_Red")
    f.cyl("AppleStem", (0, 0, 7.5), 0.07, 0.07, 0.5, "Mat_Wood_Dark", seg=6)
    f.sphere("AppleLeaf", (0.45, 0, 7.55), (0.4, 0.15, 0.2), "Mat_Leaf", seg=(8, 6))
    for i in range(4):  # shopping carts
        f.box(f"Cart{i}", (-6 + i * 1.4, 7.3, 0.6), (1.1, 0.7, 0.9), "Mat_Rail", bevel=0.04)
        f.box(f"CartBase{i}", (-6 + i * 1.4, 7.3, 0.15), (1.1, 0.7, 0.1), "Mat_Dark", bevel=0.02)
    for i, mat in enumerate(("Mat_Roof_Red", "Mat_Wall_Orange", "Mat_Leaf")):  # produce crates
        f.box(f"Crate{i}", (4.2 + i * 1.6, 6.6, 0.4), (1.3, 1.0, 0.8), mat, bevel=0.04)


def build_mall(f):
    f.box("Glass", (0, 0, 7.0), (16, 14, 14), "Mat_Glass")
    for i, z in enumerate((3.5, 7.0, 10.5, 14.1)):
        f.box(f"Floor{i}", (0, 0, z), (16.5, 14.5, 0.4), "Mat_White" if i % 2 else "Mat_Wall_Pink", bevel=0.05)
    for i, x in enumerate((-8, -4, 0, 4, 8)):
        f.box(f"Mullion{i}", (x, 7.05, 7.0), (0.25, 0.25, 14), "Mat_White", bevel=0.03)
    for i, (z, mat) in enumerate(((2.2, "Mat_Roof_Coral"), (5.7, "Mat_Roof_Blue"), (9.2, "Mat_Wall_Yellow"))):
        f.box(f"StoreAwning{i}", (-3.8, 7.9, z), (5.5, 1.4, 0.15), mat, rot=(-0.25, 0, 0), bevel=0.03)
    f.cyl("Canopy", (3.5, 8.2, 3.3), 3.0, 3.0, 0.3, "Mat_Roof_Coral", seg=24)
    f.box("SignBand", (0, 7.2, 15.2), (13, 0.5, 1.6), "Mat_Sign_Yellow")
    f.text("Sign", "SHOPPING MALL", (0, 7.5, 15.2), 0.95, "Mat_Dark")
    f.box("BagSign", (0, 0, 17.4), (1.8, 0.9, 1.6), "Mat_Roof_Coral")
    f.box("BagHandle", (0, 0, 18.6), (1.0, 0.15, 0.8), "Mat_Wood", bevel=0.03)


def build_library(f):
    f.box("Walls", (0, 0, 3.5), (14, 10, 7), "Mat_Wall_Cream")
    f.box("RoofSlab", (0, 0, 7.15), (14.8, 10.8, 0.3), "Mat_Roof_Gray")
    f.gable("Pediment", (0, 5.6, 7.3), 9.6, 1.6, 2.6, "Mat_Wall_Cream", ridge="y", overhang=0.0)
    for i in range(6):
        f.cyl(f"Column{i}", (-5 + i * 2, 5.6, 3.3), 0.42, 0.42, 6.4, "Mat_White", seg=16)
    for i in range(3):
        f.box(f"Step{i}", (0, 6.9 + i * 0.5, 0.15 + (2 - i) * 0.0 + 0.15 * (3 - i)), (11 - i * 0.6, 1.0, 0.3 * (3 - i)), "Mat_Sidewalk", bevel=0.04)
    f.box("Door", (0, 5.06, 1.4), (1.8, 0.1, 2.8), "Mat_Wood_Dark", bevel=0.03)
    f.text("Sign", "LIBRARY", (0, 5.9, 7.9), 0.7, "Mat_Dark")
    f.box("BookLeft", (-0.7, 0, 8.4), (1.3, 0.2, 1.7), "Mat_Roof_Coral", rot=(0, 0.35, 0))
    f.box("BookRight", (0.7, 0, 8.4), (1.3, 0.2, 1.7), "Mat_Wall_Yellow", rot=(0, -0.35, 0))
    for i, x in enumerate((-9.5, -11.0)):  # small garden: hedges and a tree
        f.sphere(f"Hedge{i}", (x, 2, 0.6), (0.9, 0.9, 0.7), "Mat_Leaf")
    f.cyl("TreeTrunk", (-10.5, -3, 1.0), 0.25, 0.3, 2.0, "Mat_Trunk", seg=8)
    f.sphere("TreeLeaves", (-10.5, -3, 3.2), (1.7, 1.7, 1.5), "Mat_Leaf")


def build_school(f):
    f.box("Walls", (0, 0, 3.5), (20, 9, 7), "Mat_Wall_Yellow")
    f.box("RoofSlab", (0, 0, 7.15), (20.8, 9.8, 0.3), "Mat_Roof_Red")
    f.box("Tower", (0, 0, 10.0), (4.2, 4.2, 6.0), "Mat_Wall_Cream")
    f.cyl("TowerRoof", (0, 0, 14.0), 3.2, 0.1, 2.0, "Mat_Roof_Red", seg=4, rot=(0, 0, math.pi / 4))
    f.cyl("ClockFace", (0, 2.2, 10.4), 1.3, 1.3, 0.16, "Mat_White", seg=24, rot=(math.pi / 2, 0, 0))
    f.box("ClockHandH", (0, 2.32, 10.7), (0.12, 0.06, 0.8), "Mat_Dark", bevel=0.01)
    f.box("ClockHandM", (0.35, 2.32, 10.4), (0.7, 0.06, 0.1), "Mat_Dark", bevel=0.01)
    f.box("Door", (0, 4.52, 1.4), (2.4, 0.1, 2.8), "Mat_Wood_Dark", bevel=0.03)
    for i, x in enumerate((-8, -5, 5, 8)):
        f.box(f"Window{i}", (x, 4.52, 3.6), (1.8, 0.1, 1.5), "Mat_Glass", bevel=0.03)
    f.text("Sign", "SCHOOL", (0, 4.6, 6.2), 0.7, "Mat_Dark")
    f.cyl("FlagPole", (-8.5, 0, 9.0), 0.06, 0.06, 4.0, "Mat_Rail", seg=6)
    f.box("Flag", (-7.8, 0, 10.4), (1.4, 0.05, 0.9), "Mat_Roof_Blue", bevel=0.01)
    # sports court beside the school
    f.box("Court", (17.5, 1.0, 0.05), (16, 9.5, 0.1), "Mat_Court", bevel=0.01)
    f.box("CourtLineCenter", (17.5, 1.0, 0.12), (0.15, 9.5, 0.02), "Mat_Marking", bevel=0.0)
    f.box("CourtLineSide0", (9.6, 1.0, 0.12), (0.15, 9.5, 0.02), "Mat_Marking", bevel=0.0)
    f.box("CourtLineSide1", (25.4, 1.0, 0.12), (0.15, 9.5, 0.02), "Mat_Marking", bevel=0.0)
    for i, x in enumerate((10.2, 24.8)):
        f.cyl(f"HoopPole{i}", (x, 1.0, 1.6), 0.07, 0.07, 3.2, "Mat_Dark", seg=8)
        f.cyl(f"HoopRing{i}", (x + (0.5 if i == 0 else -0.5), 1.0, 3.0), 0.35, 0.35, 0.05, "Mat_Roof_Coral", seg=16)


def build_hotel(f):
    f.box("Tower", (0, 0, 10.0), (12, 12, 20), "Mat_Wall_Cream")
    for i in range(6):
        f.box(f"Balcony{i}", (0, 6.5, 3.6 + i * 3.2), (12.6, 1.3, 0.25), "Mat_Wall_Teal", bevel=0.04)
    for r in range(5):
        for c in range(3):
            f.box(f"Window{r}{c}", (-3.6 + c * 3.6, 6.06, 5.0 + r * 3.2), (1.8, 0.1, 1.4), "Mat_Glass", bevel=0.03)
    f.box("Door", (0, 6.06, 1.4), (2.6, 0.1, 2.8), "Mat_Wood_Dark", bevel=0.03)
    f.box("Canopy", (0, 7.4, 3.1), (5.0, 2.8, 0.2), "Mat_Roof_Coral", bevel=0.03)
    f.box("RoofTop", (0, 0, 20.3), (12.6, 12.6, 0.6), "Mat_Wall_Teal")
    f.box("SignBand", (0, 6.2, 18.4), (8, 0.4, 1.4), "Mat_Sign_Yellow")
    f.text("Sign", "HOTEL", (0, 6.45, 18.4), 0.9, "Mat_Dark")
    for i, x in enumerate((-2.2, 0, 2.2)):
        f.star(f"Star{i}", (x, 6.3, 21.6), 0.7, 0.3, 0.1, "Mat_Sign_Yellow")
    # swimming pool in front and to the side
    f.box("PoolDeck", (-10.0, 7.5, 0.05), (12, 8, 0.1), "Mat_Plaza")
    f.box("Pool", (-10.0, 7.5, 0.1), (9, 5, 0.12), "Mat_Pool", bevel=0.03)
    for i in range(3):
        f.box(f"Lounger{i}", (-13.0 + i * 1.8, 11.6, 0.3), (0.8, 1.8, 0.35), "Mat_White", bevel=0.04)
    f.round_table("PoolTable", (-5.4, 10.8, 0), umbrella="Mat_Roof_Coral")


def build_station(f):
    f.box("Walls", (0, 0, 3.0), (16, 8, 6), "Mat_Wall_Brick")
    f.gable("Roof", (0, 0, 6.0), 16, 8, 2.2, "Mat_Roof_Blue")
    f.cyl("ClockFace", (0, 4.1, 5.6), 1.0, 1.0, 0.16, "Mat_White", seg=24, rot=(math.pi / 2, 0, 0))
    f.box("Door", (0, 4.06, 1.3), (2.2, 0.1, 2.6), "Mat_Wood_Dark", bevel=0.03)
    for i, x in enumerate((-5, -2.5, 2.5, 5)):
        f.box(f"Window{i}", (x, 4.06, 2.4), (1.4, 0.1, 1.6), "Mat_Glass", bevel=0.03)
    f.text("Sign", "TRAIN STATION", (0, 4.15, 4.3), 0.55, "Mat_White")
    f.box("Platform", (0, -6.0, 0.4), (30, 3.0, 0.8), "Mat_Sidewalk", bevel=0.05)
    f.box("PlatformRoof", (0, -6.0, 3.6), (14, 3.6, 0.2), "Mat_Roof_Blue", bevel=0.03)
    for i, x in enumerate((-6, 6)):
        f.box(f"PlatformPost{i}", (x, -6.0, 2.1), (0.2, 0.2, 3.0), "Mat_Dark", bevel=0.02)
    for tr, y in enumerate((-9.6, -12.4)):  # two tracks along the island rim
        for rail in (-0.55, 0.55):
            f.box(f"Rail{tr}{'L' if rail < 0 else 'R'}", (0, y + rail, 0.25), (36, 0.12, 0.14), "Mat_Rail", bevel=0.02)
        for k in range(30):
            f.box(f"Sleeper{tr}_{k}", (-17.4 + k * 1.2, y, 0.1), (0.35, 1.7, 0.1), "Mat_Wood_Dark", bevel=0.01)
    # a cartoon train waiting on the first track
    f.box("TrainEngine", (-4, -9.6, 1.6), (4.5, 2.4, 2.6), "Mat_Roof_Coral", bevel=0.2)
    f.cyl("TrainChimney", (-5.6, -9.6, 3.4), 0.35, 0.45, 0.9, "Mat_Dark", seg=12)
    for i in range(2):
        f.box(f"TrainCar{i}", (1.2 + i * 5.2, -9.6, 1.6), (4.8, 2.4, 2.6), "Mat_Wall_Yellow" if i else "Mat_Wall_Teal", bevel=0.2)


def build_airport(f):
    f.box("Terminal", (0, 0, 3.5), (22, 8, 7), "Mat_Wall_Cream")
    f.box("TerminalBand", (0, 0, 6.6), (22.6, 8.6, 0.8), "Mat_Roof_Blue")
    f.box("TerminalRoof", (0, 0, 7.4), (21, 7.2, 0.9), "Mat_Roof_Gray", bevel=0.25)
    f.box("GlassFront", (0, 4.02, 3.0), (16, 0.1, 4.0), "Mat_Glass", bevel=0.03)
    f.box("Canopy", (0, 5.6, 4.4), (12, 3.0, 0.25), "Mat_Roof_Gray", bevel=0.04)
    f.text("Sign", "AIRPORT", (0, 4.2, 6.5), 0.85, "Mat_White")
    f.cyl("TowerShaft", (13.5, -1, 8.0), 1.5, 1.2, 16, "Mat_White", seg=16)
    f.cyl("TowerCab", (13.5, -1, 17.0), 2.4, 2.9, 2.4, "Mat_Glass", seg=16)
    f.cyl("TowerRoof", (13.5, -1, 18.7), 3.2, 0.2, 1.1, "Mat_Roof_Coral", seg=16)
    f.box("Apron", (0, -7.0, 0.05), (26, 6, 0.1), "Mat_Sidewalk", bevel=0.01)
    f.box("Runway", (0, -13.0, 0.06), (32, 6.5, 0.12), "Mat_Runway", bevel=0.01)
    for k in range(8):
        f.box(f"Marking{k}", (-14 + k * 4, -13.0, 0.14), (2.2, 0.3, 0.02), "Mat_Marking", bevel=0.0)
    # parked airplane on the apron
    f.cyl("Plane_Body", (-2, -8.0, 1.5), 0.9, 0.9, 8.0, "Mat_White", seg=16, rot=(0, math.pi / 2, 0))
    f.sphere("Plane_Nose", (2.0, -8.0, 1.5), (1.0, 0.9, 0.9), "Mat_White")
    f.box("Plane_Wings", (-1.2, -8.0, 1.4), (2.0, 9.0, 0.2), "Mat_Roof_Blue", bevel=0.05)
    f.box("Plane_TailFin", (-5.6, -8.0, 2.7), (1.5, 0.2, 1.9), "Mat_Roof_Blue", bevel=0.05)
    f.box("Plane_TailWing", (-5.6, -8.0, 1.8), (1.1, 3.4, 0.15), "Mat_Roof_Blue", bevel=0.04)
    f.cyl("Windsock", (-12, -15.8, 1.8), 0.06, 0.06, 3.6, "Mat_Rail", seg=6)
    f.cyl("WindsockCone", (-11.4, -15.8, 3.4), 0.4, 0.15, 1.2, "Mat_Roof_Coral", seg=10, rot=(0, math.pi / 2, 0))


# ------------------------------------------------------------------ layout
def unit(v):
    return v / v.length


PLACES = [
    # id, collection, prefix, centre, ground depth (for the door), builder, flat radius, door offset
    ("coffee", "02_Coffee_Shop", "CoffeeShop", (-40, 8), 7, build_coffee, 10),
    ("restaurant", "03_Restaurant", "Restaurant", (-42, -12.5), 9, build_restaurant, 11),
    ("supermarket", "04_Supermarket", "Supermarket", (-33, -31), 11, build_supermarket, 11),
    ("mall", "05_Shopping_Mall", "ShoppingMall", (-18, -44), 14, build_mall, 11),
    ("library", "06_Library", "Library", (-33, 38), 10, build_library, 11),
    ("school", "07_School", "School", (-6, 45), 9, build_school, 18),
    ("hotel", "08_Hotel", "Hotel", (27, 36), 12, build_hotel, 14),
    ("station", "09_Train_Station", "TrainStation", (40, -8), 8, build_station, 14),
    ("airport", "10_Airport", "Airport", (17.6, -34.2), 8, build_airport, 15),
]

STREAM_POINTS = [(-62, 24), (-44, 29), (-26, 27), (-8, 31), (10, 31), (30, 28), (46, 25), (62, 20)]


def front_dir(center):
    return unit(-Vector(center))


def yaw_for(center):
    f = front_dir(center)
    return math.atan2(-f.x, f.y)


def door_point(center, depth):
    c = Vector(center)
    return c + front_dir(center) * (depth / 2 + 2.5)


# ------------------------------------------------------------------ terrain
class Layout:
    def __init__(self):
        self.stream = [Vector(p[:2]) for p in catmull(STREAM_POINTS, 20) if Vector(p[:2]).length <= ISLAND_R - 0.5]
        self.rng = random.Random(7)
        self.flat = []  # (kind, a, b, radius): circles (a only) or capsules (a-b)
        self.flat.append(("c", Vector((0, 0)), None, 30.0))
        for pid, _, _, center, depth, _, rad in PLACES:
            self.flat.append(("c", Vector(center), None, rad))
            self.flat.append(("s", Vector(center), self.ring_point(center), 4.6))
        # train tracks and runway run along the rim
        c = Vector((40, -8))
        yaw = yaw_for((40, -8))
        R = Matrix.Rotation(yaw, 3, "Z")
        for off in (-19, 19):
            pass
        a = Vector(c) + (R @ Vector((-19, -11.0, 0))).to_2d()
        b = Vector(c) + (R @ Vector((19, -11.0, 0))).to_2d()
        self.flat.append(("s", a, b, 6.5))
        c = Vector((17.6, -34.2))
        R = Matrix.Rotation(yaw_for((17.6, -34.2)), 3, "Z")
        a = c + (R @ Vector((-18, -13.0, 0))).to_2d()
        b = c + (R @ Vector((18, -13.0, 0))).to_2d()
        self.flat.append(("s", a, b, 8.0))
        # hills in the free ground
        self.hills = []
        tries = 0
        while len(self.hills) < 12 and tries < 3000:
            tries += 1
            ang = self.rng.uniform(0, math.tau)
            rr = self.rng.uniform(31, 55)
            p = Vector((rr * math.cos(ang), rr * math.sin(ang)))
            if self.flat_mask(p.x, p.y) > 0.8 or self.stream_distance(p) < 6:
                continue
            if any((p - h[0]).length < 11 for h in self.hills):
                continue
            self.hills.append((p, self.rng.uniform(6.0, 9.0), self.rng.uniform(3.0, 5.0)))

    def ring_point(self, center):
        return unit(Vector(center)) * RING_OUT

    def flat_mask(self, x, y):
        p = Vector((x, y))
        m = 0.0
        for kind, a, b, rad in self.flat:
            d = (p - a).length if kind == "c" else seg_dist(p, a, b)
            m = max(m, 1 - sstep(rad, rad + 5.0, d))
        return m

    def stream_distance(self, p):
        return min((p - s).length for s in self.stream)

    def height(self, x, y):
        p = Vector((x, y))
        r = p.length
        h = sum(amp * math.exp(-((p - c).length_squared) / (2 * sig * sig)) for c, sig, amp in self.hills)
        h += 0.55 * math.sin(x / 9.0) * math.cos(y / 11.0) + 0.25 * math.sin(x / 4.7 + y / 6.1)
        h *= 1 - self.flat_mask(x, y)
        d = self.stream_distance(p) if r < ISLAND_R + 2 else 99
        carve = 1 - sstep(2.1, 4.6, d)
        h = h * (1 - carve) + (-0.85) * carve
        if r > 54:
            h -= 3.8 * ((r - 54) / (ISLAND_R - 54)) ** 1.7
        return h


def build_terrain(coll, layout):
    # top surface: polar grid
    rings, segs = 56, 160
    bm = bmesh.new()
    centre = bm.verts.new((0, 0, layout.height(0, 0)))
    grid = []
    for i in range(1, rings + 1):
        r = ISLAND_R * i / rings
        row = []
        for j in range(segs):
            a = math.tau * j / segs
            x, y = r * math.cos(a), r * math.sin(a)
            row.append(bm.verts.new((x, y, layout.height(x, y))))
        grid.append(row)
    for j in range(segs):
        bm.faces.new((centre, grid[0][(j + 1) % segs], grid[0][j]))
    for i in range(rings - 1):
        for j in range(segs):
            bm.faces.new((grid[i][j], grid[i][(j + 1) % segs], grid[i + 1][(j + 1) % segs], grid[i + 1][j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    add_object(coll, "Island_Top", bm, "Mat_Grass")
    rim_z = layout.height(ISLAND_R, 0)

    # low-poly rock underside with a soil band at the top
    rng = random.Random(3)
    levels = [(ISLAND_R, rim_z), (ISLAND_R - 1.5, rim_z - 4.0), (53, -14), (44, -21), (33, -28), (20, -34), (8, -38.5)]
    n = 20
    bm = bmesh.new()
    verts = []
    for r, z in levels:
        row = []
        for j in range(n):
            a = math.tau * j / n + (0.15 if len(verts) % 2 else 0.0)
            jitter = 1.0 if r == ISLAND_R else 1 + rng.uniform(-0.07, 0.07)
            row.append(bm.verts.new((r * jitter * math.cos(a), r * jitter * math.sin(a), z + (0 if r == ISLAND_R else rng.uniform(-0.8, 0.8)))))
        verts.append(row)
    tip = bm.verts.new((0, 0, -42))
    soil_faces = []
    for i in range(len(levels) - 1):
        for j in range(n):
            f = bm.faces.new((verts[i][j], verts[i + 1][j], verts[i + 1][(j + 1) % n], verts[i][(j + 1) % n]))
            if i == 0:
                soil_faces.append(f)
    for j in range(n):
        bm.faces.new((verts[-1][j], tip, verts[-1][(j + 1) % n]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new("Island_Rock")
    for f in soil_faces:
        f.material_index = 1
    bm.to_mesh(mesh)
    bm.free()
    mesh.materials.append(MATS["Mat_Rock"])
    mesh.materials.append(MATS["Mat_Soil"])
    mesh.polygons.foreach_set("use_smooth", [False] * len(mesh.polygons))
    obj = bpy.data.objects.new("Island_Rock", mesh)
    coll.objects.link(obj)

    # water far below the floating island
    bm = bmesh.new()
    s = 260
    vs = [bm.verts.new(p) for p in ((-s, -s, -48), (s, -s, -48), (s, s, -48), (-s, s, -48))]
    bm.faces.new(vs)
    add_object(coll, "Water_Plane", bm, "Mat_Water", smooth=False)


def strip(coll, name, pts, width, z, mat):
    """A flat ribbon along a polyline (roads, sidewalks, stream)."""
    bm = bmesh.new()
    left, right = [], []
    for i, p in enumerate(pts):
        prev, nxt = pts[max(i - 1, 0)], pts[min(i + 1, len(pts) - 1)]
        delta = Vector(nxt) - Vector(prev)
        t = unit(delta) if delta.length > 1e-6 else Vector((1, 0))
        n = Vector((-t.y, t.x))
        left.append(bm.verts.new((p.x + n.x * width / 2, p.y + n.y * width / 2, z)))
        right.append(bm.verts.new((p.x - n.x * width / 2, p.y - n.y * width / 2, z)))
    for i in range(len(pts) - 1):
        bm.faces.new((left[i], left[i + 1], right[i + 1], right[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return add_object(coll, name, bm, mat, smooth=False)


def annulus(coll, name, r0, r1, z, mat, segs=96):
    bm = bmesh.new()
    inner = [bm.verts.new((r0 * math.cos(math.tau * i / segs), r0 * math.sin(math.tau * i / segs), z)) for i in range(segs)]
    outer = [bm.verts.new((r1 * math.cos(math.tau * i / segs), r1 * math.sin(math.tau * i / segs), z)) for i in range(segs)]
    for i in range(segs):
        bm.faces.new((inner[i], outer[i], outer[(i + 1) % segs], inner[(i + 1) % segs]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return add_object(coll, name, bm, mat, smooth=False)


def disc(coll, name, c, r, z, mat, segs=64):
    bm = bmesh.new()
    ring = [bm.verts.new((c[0] + r * math.cos(math.tau * i / segs), c[1] + r * math.sin(math.tau * i / segs), z)) for i in range(segs)]
    bm.faces.new(ring)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return add_object(coll, name, bm, mat, smooth=False)


def build_stream_and_bridges(coll, layout, spokes):
    """Stream, two waterfalls at the rim, and a wooden bridge wherever a road crosses the stream."""
    strip(coll, "Stream", layout.stream, 4.2, -0.42, "Mat_Water")
    for i, end in enumerate((layout.stream[0], layout.stream[-1])):
        d = unit(end)
        n = Vector((-d.y, d.x))
        a = Vector(end)
        # a curved falling ribbon: it leaves the stream bed, arcs outwards and narrows as it drops
        bm = bmesh.new()
        steps = 8
        rows = []
        for k in range(steps + 1):
            t = k / steps
            p = a + d * (0.2 + 2.4 * t)
            z = -0.42 - 7.2 * t ** 1.7
            w = 2.1 - 0.4 * t
            rows.append((bm.verts.new((p.x + n.x * w, p.y + n.y * w, z)), bm.verts.new((p.x - n.x * w, p.y - n.y * w, z))))
        for k in range(steps):
            bm.faces.new((rows[k][0], rows[k][1], rows[k + 1][1], rows[k + 1][0]))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        add_object(coll, f"Waterfall_{i}", bm, "Mat_Water", smooth=False)
        # foam where the water hits the surface far below
        foam = bmesh.new()
        base = a + d * 2.8
        for j in range(9):
            off = (j - 4) * 0.5
            bmesh.ops.create_uvsphere(foam, u_segments=8, v_segments=6, radius=0.42 + 0.12 * (j % 3), matrix=Matrix.Translation((base.x + n.x * off, base.y + n.y * off, -7.5 + 0.1 * (j % 2))))
        add_object(coll, f"Waterfall_{i}_Foam", foam, "Mat_White")

    bridges = []
    for name, a, b in spokes:
        a2, b2 = Vector(a), Vector(b)
        inside = []
        for k in range(401):
            p = a2.lerp(b2, k / 400)
            inside.append(layout.stream_distance(p) < 3.0)
        if any(inside):
            first, last = inside.index(True), len(inside) - 1 - inside[::-1].index(True)
            pa, pb = a2.lerp(b2, first / 400), a2.lerp(b2, last / 400)
            bridges.append((name, pa, pb))
    return bridges


def build_bridge(coll, idx, pa, pb):
    mid = (pa + pb) / 2
    axis = unit(pb - pa)
    length = (pb - pa).length + 3.0
    yaw = math.atan2(axis.y, axis.x) - math.pi / 2  # local +Y along the bridge
    f = Frame(coll, f"Bridge{idx}", (mid.x, mid.y, 0), yaw)
    f.box("Deck", (0, 0, 0.35), (5.4, length, 0.3), "Mat_Wood", bevel=0.04)
    for k in range(int(length / 0.9)):
        f.box(f"Plank{k}", (0, -length / 2 + 0.5 + k * 0.9, 0.52), (5.0, 0.7, 0.06), "Mat_Wood_Dark", bevel=0.01)
    for side, x in (("L", -2.6), ("R", 2.6)):
        f.box(f"Rail{side}", (x, 0, 1.15), (0.14, length, 0.14), "Mat_Wood_Dark", bevel=0.02)
        for k in range(int(length / 1.6) + 1):
            f.box(f"Post{side}{k}", (x, -length / 2 + 0.4 + k * 1.6, 0.8), (0.18, 0.18, 1.0), "Mat_Wood_Dark", bevel=0.02)
    for side, y in (("A", -length / 2), ("B", length / 2)):
        f.box(f"Abutment{side}", (0, y, -0.1), (5.8, 0.9, 0.9), "Mat_Rock", bevel=0.05)


# ------------------------------------------------------------------ central park (blockout)
def build_park(coll):
    f = Frame(coll, "CentralPark", (0, 0, 0), 0.0)
    disc(coll, "CentralPark_Lawn", (0, 0), PARK_R, 0.03, "Mat_Grass_Light")
    disc(coll, "CentralPark_Plaza", (0, 0), 9.5, 0.07, "Mat_Plaza")
    annulus(coll, "CentralPark_PlazaRing", 7.2, 7.9, 0.08, "Mat_Plaza_Accent")
    annulus(coll, "CentralPark_PathRing", 14.0, 15.6, 0.06, "Mat_Path")
    for k, ang in enumerate((0, 90, 180, 270)):
        a = math.radians(ang)
        strip(coll, f"CentralPark_Path{k}", [Vector((9.0 * math.cos(a), 9.0 * math.sin(a))), Vector((PARK_R * math.cos(a), PARK_R * math.sin(a)))], 3.0, 0.06, "Mat_Path")
    f.cyl("Fountain_Base", (0, 0, 0.45), 3.2, 3.2, 0.9, "Mat_Plaza", seg=32)
    f.cyl("Fountain_Water", (0, 0, 0.92), 2.7, 2.7, 0.06, "Mat_Pool", seg=32)
    f.cyl("Fountain_Column", (0, 0, 1.9), 0.45, 0.6, 2.0, "Mat_Plaza", seg=16)
    f.cyl("Fountain_Bowl", (0, 0, 2.8), 1.5, 0.9, 0.35, "Mat_Plaza", seg=24)
    f.sphere("Fountain_Top", (0, 0, 3.3), (0.45, 0.45, 0.55), "Mat_Pool")
    # iconic giant tree, slightly north of the plaza
    f.cyl("GiantTree_Trunk", (4, 13, 3.0), 1.1, 1.6, 6.0, "Mat_Trunk", seg=12)
    for i, (x, y, z, s) in enumerate(((4, 13, 8.5, 4.2), (1.6, 12, 7.3, 3.1), (6.5, 14.2, 7.4, 3.2), (4, 11.5, 10.8, 2.8))):
        f.sphere(f"GiantTree_Leaves{i}", (x, y, z), (s, s, s * 0.85), "Mat_Leaf", seg=(20, 12))
    # event stage, quest board and NPC spot
    f.box("Stage_Platform", (13.5, -4, 0.55), (9, 6, 1.1), "Mat_Wood", bevel=0.08)
    f.box("Stage_Backdrop", (17.2, -4, 3.2), (1.0, 6, 4.6), "Mat_Roof_Coral", bevel=0.08)
    f.box("Stage_Roof", (14.2, -4, 5.6), (10, 7, 0.4), "Mat_Roof_Blue", bevel=0.08)
    for i, y in enumerate((-6.6, -1.4)):
        f.cyl(f"Stage_Pole{i}", (9.4, y, 3.3), 0.15, 0.15, 5.0, "Mat_Wood_Dark", seg=8)
    f.box("QuestBoard_Board", (0, -17.2, 2.0), (3.6, 0.3, 2.4), "Mat_Wood", bevel=0.05)
    for i, x in enumerate((-1.5, 1.5)):
        f.cyl(f"QuestBoard_Post{i}", (x, -17.2, 1.0), 0.12, 0.12, 2.0, "Mat_Wood_Dark", seg=8)
    f.cyl("NPC_Spot", (0, -14.2, 0.1), 1.6, 1.6, 0.1, "Mat_Plaza_Accent", seg=24)
    f.box("PlaygroundArea", (-12.5, -9, 0.06), (10, 8, 0.1), "Mat_Path", bevel=0.01)
    f.cyl("REF_Scale_Chibi_1.6m_Body", (0, -13.2, 0.55), 0.3, 0.3, 1.1, "Mat_Roof_Blue", seg=12)
    f.sphere("REF_Scale_Chibi_1.6m_Head", (0, -13.2, 1.32), (0.3, 0.28, 0.28), "Mat_Wall_Cream")


# ------------------------------------------------------------------ scene
def setup_scene():
    scene = bpy.context.scene
    world = bpy.data.worlds.new("SkyWorld")
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (0.7, 0.84, 1.0, 1.0)
        bg.inputs["Strength"].default_value = 1.0
    scene.world = world
    scene.view_settings.view_transform = "Standard"
    sun_data = bpy.data.lights.new("Sun_Warm", "SUN")
    sun_data.energy, sun_data.color, sun_data.angle = 2.8, (1.0, 0.93, 0.8), math.radians(5)  # soft shadows
    sun = bpy.data.objects.new("Sun_Warm", sun_data)
    sun.location = (-60, -40, 90)
    sun.rotation_euler = (Vector((0, 0, 0)) - sun.location).to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(sun)
    cam_data = bpy.data.cameras.new("Camera_Isometric")
    cam_data.type, cam_data.ortho_scale, cam_data.clip_end = "ORTHO", 150, 600
    cam = bpy.data.objects.new("Camera_Isometric", cam_data)
    cam.location = (115, -115, 105)
    cam.rotation_euler = (Vector((0, 0, -3)) - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(cam)
    scene.camera = cam
    return scene, cam


def use_eevee(scene):
    for engine in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            scene.render.engine = engine
            return True
        except TypeError:
            continue
    scene.render.engine = "BLENDER_WORKBENCH"
    return False


def render_views(scene, cam, out_dir):
    use_eevee(scene)
    scene.render.resolution_x, scene.render.resolution_y = 1800, 1150
    views = {
        "island_iso": ((115, -115, 105), (0, 0, -3), 150),
        "island_iso_back": ((-115, 115, 105), (0, 0, -3), 150),
        "island_top": ((0, 0, 200), (0, 0, 0), 135),
    }
    for name, (loc, target, scale) in views.items():
        cam.location = loc
        cam.data.ortho_scale = scale
        direction = Vector(target) - Vector(loc)
        cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = os.path.join(out_dir, f"{name}.png")
        bpy.ops.render.render(write_still=True)
    cam.location = (115, -115, 105)
    cam.rotation_euler = (Vector((0, 0, -3)) - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam.data.ortho_scale = 150
    return scene.render.engine


# ------------------------------------------------------------------ main build
def create_island():
    """Builds Phase 1 in the open Blender session and returns what later phases need."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    make_materials()
    colls = {}
    for name in COLLECTIONS:
        c = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(c)
        colls[name] = c

    layout = Layout()
    build_terrain(colls["00_Environment_Terrain"], layout)
    env = colls["00_Environment_Terrain"]

    # roads: ring around the park, then a spoke from the ring to each destination's front door
    annulus(env, "Road_Ring", RING_IN, RING_OUT, 0.05, "Mat_Road")
    annulus(env, "Sidewalk_RingInner", RING_IN - 1.4, RING_IN, 0.06, "Mat_Sidewalk")
    annulus(env, "Sidewalk_RingOuter", RING_OUT, RING_OUT + 1.4, 0.06, "Mat_Sidewalk")
    spokes = []
    for pid, cname, prefix, center, depth, builder, rad in PLACES:
        door = door_point(center, depth)
        start = unit(door) * (RING_OUT + 1.0)
        spokes.append((prefix, start, door))
    bridges = build_stream_and_bridges(env, layout, spokes)
    crossings = {name: (pa, pb) for name, pa, pb in bridges}
    for prefix, start, door in spokes:
        a, b = Vector(start), Vector(door)
        if prefix in crossings:
            pa, pb = crossings[prefix]
            parts = [(a, pa - unit(pb - pa) * 0.0), (pb + unit(pb - pa) * 0.0, b)]
        else:
            parts = [(a, b)]
        for k, (p, q) in enumerate(parts):
            if (q - p).length < 1.0:  # the crossing starts or ends at the road end: no road piece needed
                continue
            pts = [p.lerp(q, t / 8) for t in range(9)]
            strip(env, f"Road_{prefix}_{k}", pts, 4.6, 0.05, "Mat_Road")
            for side, off in (("A", 2.8), ("B", -2.8)):
                d = unit(q - p)
                n = Vector((-d.y, d.x)) * off
                strip(env, f"Sidewalk_{prefix}_{k}{side}", [pt + n for pt in pts], 1.2, 0.06, "Mat_Sidewalk")
    for i, (name, pa, pb) in enumerate(bridges):
        build_bridge(env, i, pa, pb)

    build_park(colls["01_Central_Park"])
    for pid, cname, prefix, center, depth, builder, rad in PLACES:
        f = Frame(colls[cname], prefix, (center[0], center[1], 0), yaw_for(center))
        builder(f)

    scene, cam = setup_scene()
    return colls, layout, bridges, scene, cam


def build(out_dir="assets/world", preview=False, export=False):
    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    colls, layout, bridges, scene, cam = create_island()
    report = scene_report(colls, layout, bridges)
    if preview:
        report["render_engine"] = render_views(scene, cam, out_dir)
    if export:
        glb = os.path.join(out_dir, "island_phase1.glb")
        bpy.ops.object.select_all(action="DESELECT")
        bpy.ops.export_scene.gltf(filepath=glb, export_format="GLB", export_apply=True, export_yup=True, export_materials="EXPORT")
        report["exported"] = glb
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out_dir, "island_phase1.blend"))
    if export:
        merged = os.path.join(out_dir, "island_phase1_merged.glb")
        report["merged"] = export_merged(merged)
        report["merged_glb"] = merged
    return report


def export_merged(path):
    """Draw-call budget check: one mesh per shared material (world space, modifiers applied).

    The organised glb keeps one object per part (good for editing and for collision naming);
    this variant shows what the island costs when everything with the same material is one draw.
    Run after the .blend is saved: it adds throw-away objects to the open scene.
    """
    deps = bpy.context.evaluated_depsgraph_get()
    by_material = {}
    for obj in [o for o in bpy.data.objects if o.type == "MESH"]:
        mat = obj.data.materials[0].name if obj.data.materials else None
        if mat is None:
            continue
        by_material.setdefault(mat, []).append(obj)
    created = []
    for mat, objs in by_material.items():
        bm = bmesh.new()
        for obj in objs:
            tmp = bpy.data.meshes.new_from_object(obj.evaluated_get(deps), depsgraph=deps)
            tmp.transform(obj.matrix_world)
            bm.from_mesh(tmp)
            bpy.data.meshes.remove(tmp)
        mesh = bpy.data.meshes.new(f"Merged_{mat}")
        bm.to_mesh(mesh)
        bm.free()
        mesh.polygons.foreach_set("use_smooth", [False] * len(mesh.polygons))
        mesh.materials.append(MATS[mat] if mat in MATS else bpy.data.materials[mat])
        out = bpy.data.objects.new(f"Merged_{mat}", mesh)
        bpy.context.scene.collection.objects.link(out)
        created.append(out)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in created:
        obj.select_set(True)
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True, export_apply=False, export_yup=True, export_materials="EXPORT")
    return {"meshes": len(created), "triangles": sum(len(o.data.polygons) for o in created)}


def scene_report(colls, layout, bridges):
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    not_applied = [o.name for o in meshes if any(abs(s - 1) > 1e-6 for s in o.scale) or any(abs(r) > 1e-6 for r in o.rotation_euler)]
    xs = [v.co.x for o in meshes if o.name == "Island_Top" for v in o.data.vertices]
    ys = [v.co.y for o in meshes if o.name == "Island_Top" for v in o.data.vertices]
    place_centres = {p[2]: Vector(p[3]) for p in PLACES}
    min_gap = min((a - b).length for i, a in enumerate(place_centres.values()) for b in list(place_centres.values())[i + 1 :])
    stream_clear = {k: round(layout.stream_distance(v), 1) for k, v in place_centres.items()}
    reach = {}
    for c in bpy.context.scene.collection.children:
        if c.name[:2] in ("00", "01"):
            continue
        radii = [(o.location.xy + v.co.xy).length for o in c.objects if o.type == "MESH" for v in o.data.vertices]
        reach[c.name] = (round(min(radii), 1), round(max(radii), 1))
    return {
        "collections": [c.name for c in bpy.context.scene.collection.children],
        "objects_per_collection": {c.name: len(c.objects) for c in bpy.context.scene.collection.children},
        "mesh_objects": len(meshes),
        "materials": len(bpy.data.materials),
        "roughness": sorted({round(m.roughness, 2) for m in bpy.data.materials}),
        "transforms_not_applied": not_applied,
        "island_diameter_m": round(max(max(xs) - min(xs), max(ys) - min(ys)), 1),
        "hills": len(layout.hills),
        "bridges": [b[0] for b in bridges],
        "min_distance_between_places_m": round(min_gap, 1),
        "place_to_stream_m": stream_clear,
        "reach_min_max_from_centre_m": reach,
    }


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    out = args[0] if args and not args[0].startswith("--") else "assets/world"
    print(json.dumps(build(out, preview="--preview" in args, export="--export" in args), indent=2))
