"""
English Adventure World - Phase 3: detailed exteriors for the 9 destinations.

Replaces the Phase 1 blockouts inside the 02_Coffee_Shop ... 10_Airport collections with
detailed buildings. Same positions, same facing, same shared Mat_* materials (Roughness 0.75).

Rules every building follows
- Built in a local frame: +X right, +Y towards the front door, +Z up, origin on the ground at
  the building's centre. Rotation is baked into the mesh, so every object has Scale 1 and
  Rotation 0 and its origin sits on the ground.
- Main masses (walls, towers, platforms) are their own named objects so they can become colliders.
  Repeated small parts (chairs, windows, products, wheels) are batched into one mesh per
  material, which keeps the object count and the draw calls low.

Called from build_world.py; it can also be run through build_world.py --only phase3.
"""

import math

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector

import build_island as bi

PI = math.pi

NEW_MATERIALS = {
    "Mat_Curtain": "#C9344F", "Mat_Metal": "#B8C0CC", "Mat_Lamp_Glow": "#FFE9A8",
    "Mat_Leaf_Dark": "#3E9B4F", "Mat_Leaf_Light": "#8BD968", "Mat_Blossom": "#F7A8C4",
    "Mat_Flower_Pink": "#F78FB3", "Mat_Flower_Yellow": "#FFD84D", "Mat_Flower_Purple": "#9B7BE0",
    "Mat_Flower_Red": "#E85D5D", "Mat_Hazard": "#FFC83D", "Mat_Chalk": "#2F3B35",
}


def register_materials():
    for name, hex_color in NEW_MATERIALS.items():
        bi.PALETTE.setdefault(name, hex_color)


GLASS_ALPHA = 0.38


def make_glass_transparent():
    """Mat_Glass becomes see-through, so interiors (supermarket shelves, hotel lobby) show."""
    mat = bpy.data.materials["Mat_Glass"]
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Alpha"].default_value = GLASS_ALPHA
    for attr, value in (("surface_render_method", "BLENDED"), ("blend_method", "BLEND")):
        try:
            setattr(mat, attr, value)
        except (AttributeError, TypeError):
            pass
    mat.diffuse_color = (*mat.diffuse_color[:3], GLASS_ALPHA)


# ------------------------------------------------------------------ batching of small parts
class Batch:
    """Many small primitives merged into one mesh with one material (local building coordinates)."""

    def __init__(self, frame, name, mat, smooth=False):
        self.f, self.name, self.mat, self.smooth = frame, name, mat, smooth
        self.bm = bmesh.new()
        self.count = 0

    def box(self, c, size, rot=(0, 0, 0)):
        m = Matrix.Translation(Vector(c)) @ Euler(rot, "XYZ").to_matrix().to_4x4() @ Matrix.Diagonal(Vector((*size, 1.0)))
        bmesh.ops.create_cube(self.bm, size=1.0, matrix=m)
        self.count += 1
        return self

    def cyl(self, c, r0, r1, h, seg=12, rot=(0, 0, 0), cap=True):
        m = Matrix.Translation(Vector(c)) @ Euler(rot, "XYZ").to_matrix().to_4x4()
        bmesh.ops.create_cone(self.bm, cap_ends=cap, cap_tris=False, segments=seg, radius1=r0, radius2=r1, depth=h, matrix=m)
        self.count += 1
        return self

    def sphere(self, c, scale, seg=(10, 7)):
        m = Matrix.Translation(Vector(c)) @ Matrix.Diagonal(Vector((*scale, 1.0)))
        bmesh.ops.create_uvsphere(self.bm, u_segments=seg[0], v_segments=seg[1], radius=1.0, matrix=m)
        self.count += 1
        return self

    def emit(self):
        if not self.count:
            self.bm.free()
            return None
        return self.f._emit(self.name, self.bm, self.mat, smooth=self.smooth)


def ring_x(b, c, major, minor, segs=14, rot_axis="y"):
    """A ring of small spheres in the XZ plane (handles, wreaths, hoops)."""
    for i in range(segs):
        a = PI * 2 * i / segs
        b.sphere((c[0] + major * math.cos(a), c[1], c[2] + major * math.sin(a)), (minor, minor, minor), seg=(6, 4))


def windows(f, name, xs, y, z, w, h, mat="Mat_Glass"):
    b = Batch(f, name, mat)
    for x in xs:
        b.box((x, y, z), (w, 0.1, h))
    return b.emit()


def frames(f, name, xs, y, z, w, h, t=0.12, mat="Mat_White"):
    """White window frames: four thin bars around each window."""
    b = Batch(f, name, mat)
    for x in xs:
        b.box((x, y, z + h / 2), (w + t * 2, 0.14, t)).box((x, y, z - h / 2), (w + t * 2, 0.14, t))
        b.box((x - w / 2, y, z), (t, 0.14, h)).box((x + w / 2, y, z), (t, 0.14, h))
    return b.emit()


def stripes(f, prefix, c, n, step, depth, tilt, mat_a, mat_b, thick=0.12):
    """A striped awning: alternating boxes in two materials, plus a scalloped front edge."""
    a, b = Batch(f, f"{prefix}A", mat_a), Batch(f, f"{prefix}B", mat_b)
    x0 = c[0] - step * (n - 1) / 2
    for i in range(n):
        tgt = a if i % 2 == 0 else b
        tgt.box((x0 + i * step, c[1], c[2]), (step, depth, thick), rot=(tilt, 0, 0))
        tgt.sphere((x0 + i * step, c[1] + depth / 2 * math.cos(tilt), c[2] - depth / 2 * abs(math.sin(tilt)) - 0.05), (step * 0.5, 0.12, 0.16), seg=(8, 5))
    a.emit()
    b.emit()


def chair_set(f, name, positions, mat="Mat_Wood", yaws=None):
    b = Batch(f, name, mat)
    legs = Batch(f, name + "Legs", "Mat_Wood_Dark")
    for i, (x, y) in enumerate(positions):
        yaw = yaws[i] if yaws else 0.0
        c, s = math.cos(yaw), math.sin(yaw)
        b.box((x, y, 0.5), (0.5, 0.5, 0.08), rot=(0, 0, yaw))
        b.box((x - 0.24 * s, y + 0.24 * c, 0.85), (0.5, 0.06, 0.6), rot=(0, 0, yaw))
        for dx, dy in ((0.2, 0.2), (-0.2, 0.2), (0.2, -0.2), (-0.2, -0.2)):
            legs.box((x + dx * c - dy * s, y + dx * s + dy * c, 0.24), (0.06, 0.06, 0.48))
    b.emit()
    legs.emit()


def table_with_umbrella(f, name, c, umbrella_mat, chairs=4, umbrella=True):
    x, y = c
    wood, dark, cloth = Batch(f, f"{name}Wood", "Mat_Wood"), Batch(f, f"{name}Pole", "Mat_Wood_Dark"), Batch(f, f"{name}Cloth", umbrella_mat)
    wood.cyl((x, y, 0.8), 0.65, 0.65, 0.08, seg=20)
    dark.cyl((x, y, 0.4), 0.08, 0.08, 0.8, seg=8)
    dark.cyl((x, y, 0.04), 0.35, 0.35, 0.08, seg=12)
    if umbrella:
        dark.cyl((x, y, 1.5), 0.04, 0.04, 3.0, seg=6)
        cloth.cyl((x, y, 2.95), 1.6, 0.06, 0.65, seg=12)
    wood.emit()
    dark.emit()
    cloth.emit()
    seats = [(x + 1.0 * math.cos(a), y + 1.0 * math.sin(a)) for a in [PI * 2 * k / chairs + PI / 4 for k in range(chairs)]]
    chair_set(f, f"{name}Chairs", seats, yaws=[math.atan2(y - sy, x - sx) - PI / 2 + PI for sx, sy in seats])


def potted_plants(f, name, positions, size=0.5):
    pot, leaf = Batch(f, f"{name}Pots", "Mat_Roof_Coral"), Batch(f, f"{name}Leaves", "Mat_Leaf")
    for x, y in positions:
        pot.cyl((x, y, 0.3), size * 0.8, size * 0.6, 0.6, seg=10)
        leaf.sphere((x, y, 0.9), (size, size, size * 0.9), seg=(8, 6))
    pot.emit()
    leaf.emit()


def wheels(b, centres, r, width, axis="x"):
    rot = (0, PI / 2, 0) if axis == "x" else (PI / 2, 0, 0)
    for c in centres:
        b.cyl(c, r, r, width, seg=12, rot=rot)


def fence_line(f, name, a, b, h=0.9, step=1.3, mat_post="Mat_Wood_Dark", mat_rail="Mat_Wood"):
    A, B = Vector(a), Vector(b)
    n = max(2, int((B - A).length / step))
    posts, rails = Batch(f, f"{name}Posts", mat_post), Batch(f, f"{name}Rails", mat_rail)
    yaw = math.atan2((B - A).y, (B - A).x)
    for i in range(n + 1):
        p = A.lerp(B, i / n)
        posts.box((p.x, p.y, h / 2), (0.14, 0.14, h))
    mid = (A + B) / 2
    for z in (h * 0.35, h * 0.8):
        rails.box((mid.x, mid.y, z), ((B - A).length, 0.07, 0.1), rot=(0, 0, yaw))
    posts.emit()
    rails.emit()


# ------------------------------------------------------------------ 02 Coffee Shop
def coffee(f):
    f.box("Walls", (0, 0, 2.0), (9, 7, 4), "Mat_Wall_Cream")
    f.box("Base", (0, 0, 0.5), (9.3, 7.3, 1.0), "Mat_Stripe_Brown")
    f.gable("Roof", (0, 0, 4.0), 9, 7, 2.0, "Mat_Roof_Coral")
    f.box("RoofRidge", (0, 0, 6.05), (9.9, 0.4, 0.22), "Mat_Roof_Red")
    f.box("Chimney", (2.6, -1.5, 6.2), (0.9, 0.9, 2.2), "Mat_Wall_Brick")
    f.box("DoorFrame", (-2.5, 3.52, 1.25), (1.5, 0.16, 2.5), "Mat_White")
    f.box("Door", (-2.5, 3.58, 1.15), (1.2, 0.1, 2.3), "Mat_Wood_Dark")
    windows(f, "Windows", (0.3, 2.6), 3.52, 1.9, 1.9, 1.5)
    frames(f, "WindowFrames", (0.3, 2.6), 3.58, 1.9, 1.9, 1.5)
    stripes(f, "Awning", (0.2, 4.45, 3.1), 8, 0.85, 2.2, -0.32, "Mat_White", "Mat_Stripe_Brown")
    f.box("SignBoard", (0, 3.6, 3.65), (6.4, 0.18, 0.7), "Mat_Wood_Dark")
    f.text("Sign", "COFFEE", (0, 3.72, 3.65), 0.5, "Mat_White")
    # giant coffee cup on the roof, steam above it
    cup = Batch(f, "CupSign", "Mat_White", smooth=True)
    cup.cyl((0, 0, 6.85), 1.0, 0.8, 1.4, seg=24)
    cup.cyl((0, 0, 6.15), 1.25, 1.25, 0.12, seg=24)
    ring_x(cup, (1.1, 0, 6.9), 0.5, 0.11)
    cup.emit()
    steam = Batch(f, "CupSteam", "Mat_White", smooth=True)
    for i, (x, z) in enumerate(((0, 8.0), (0.25, 8.5), (-0.2, 9.0))):
        steam.sphere((x, 0, z), (0.28, 0.28, 0.35))
    steam.emit()
    f.cyl("CupCoffee", (0, 0, 7.5), 0.85, 0.85, 0.05, "Mat_Stripe_Brown", seg=24)
    # open-air coffee bar annex on the right: counter and machine are visible from outside
    f.box("AnnexFloor", (7.2, 0.2, 0.08), (4.4, 5.4, 0.16), "Mat_Sidewalk")
    f.box("AnnexBackWall", (9.3, 0.2, 1.6), (0.25, 5.4, 3.2), "Mat_Wall_Cream")
    f.box("AnnexSideWall", (7.2, -2.4, 1.6), (4.4, 0.25, 3.2), "Mat_Wall_Cream")
    f.box("AnnexRoof", (7.2, 0.4, 3.35), (5.0, 6.2, 0.25), "Mat_Roof_Coral")
    f.box("Counter", (7.2, 2.3, 0.6), (3.8, 0.9, 1.2), "Mat_Wood")
    f.box("CounterTop", (7.2, 2.3, 1.25), (4.0, 1.1, 0.1), "Mat_Wood_Dark")
    mach = Batch(f, "EspressoMachine", "Mat_Metal")
    mach.box((6.6, 2.2, 1.65), (1.2, 0.6, 0.7)).cyl((6.3, 2.2, 2.1), 0.09, 0.09, 0.2, seg=8).cyl((6.9, 2.2, 2.1), 0.09, 0.09, 0.2, seg=8)
    mach.emit()
    cups = Batch(f, "CounterCups", "Mat_White")
    for i in range(4):
        cups.cyl((7.7 + i * 0.3, 2.4, 1.38), 0.1, 0.08, 0.18, seg=8)
    cups.emit()
    jars = Batch(f, "ShelfJars", "Mat_Roof_Coral")
    jars_b = Batch(f, "ShelfJarsB", "Mat_Wall_Yellow")
    for i in range(5):
        (jars if i % 2 else jars_b).cyl((6.0 + i * 0.7, -2.1, 2.0), 0.18, 0.18, 0.4, seg=8)
    f.box("Shelf", (7.2, -2.2, 1.78), (4.0, 0.3, 0.08), "Mat_Wood")
    jars.emit()
    jars_b.emit()
    f.box("MenuBoard", (9.1, 0.2, 2.0), (0.1, 1.8, 1.2), "Mat_Chalk")
    f.text("MenuText", "MENU", (9.0, 0.2, 2.4), 0.4, "Mat_White")
    # outdoor tables with umbrellas, planters, A-frame sign
    table_with_umbrella(f, "TableA", (-2.2, 7.4), "Mat_Roof_Coral")
    table_with_umbrella(f, "TableB", (1.8, 8.2), "Mat_White")
    table_with_umbrella(f, "TableC", (5.2, 7.0), "Mat_Stripe_Brown")
    potted_plants(f, "Planters", ((-4.6, 3.9), (4.7, 3.9), (-4.6, 9.0)))
    f.box("AFrameSign", (-5.2, 5.4, 0.55), (0.9, 0.12, 1.1), "Mat_Chalk", rot=(-0.12, 0, 0))
    lamps = Batch(f, "StringLights", "Mat_Lamp_Glow", smooth=True)
    for i in range(9):
        lamps.sphere((-3.6 + i * 0.9, 4.0, 3.0 - 0.18 * math.sin(i / 8 * PI)), (0.1, 0.1, 0.1), seg=(6, 4))
    lamps.emit()


# ------------------------------------------------------------------ 03 Restaurant
def restaurant(f):
    f.box("WallsLower", (0, 0, 1.7), (12, 9, 3.4), "Mat_Wall_Orange")
    f.box("WallsUpper", (0, 0, 4.9), (11, 8, 3.0), "Mat_Wall_Brick")
    f.box("Cornice", (0, 0, 3.45), (12.4, 9.4, 0.25), "Mat_White")
    f.gable("Roof", (0, 0, 6.4), 11, 8, 2.0, "Mat_Roof_Red")
    f.box("RoofRidge", (0, 0, 8.45), (11.9, 0.4, 0.22), "Mat_Roof_Gray")
    f.box("Chimney", (3.6, -1.5, 8.4), (0.9, 0.9, 2.4), "Mat_Wall_Brick")
    smoke = Batch(f, "Smoke", "Mat_White", smooth=True)
    for i, (x, z) in enumerate(((3.6, 10.0), (3.9, 10.6), (3.5, 11.2))):
        smoke.sphere((x, -1.5, z), (0.32 + i * 0.08,) * 3)
    smoke.emit()
    f.box("DoorFrame", (0, 4.52, 1.3), (2.2, 0.2, 2.6), "Mat_White")
    f.box("DoorLeft", (-0.5, 4.6, 1.15), (0.9, 0.1, 2.3), "Mat_Wood_Dark")
    f.box("DoorRight", (0.5, 4.6, 1.15), (0.9, 0.1, 2.3), "Mat_Wood_Dark")
    f.cyl("DoorArch", (0, 4.6, 2.6), 1.1, 1.1, 0.12, "Mat_Wood_Dark", seg=16, rot=(PI / 2, 0, 0))
    windows(f, "WindowsLow", (-3.9, 3.9), 4.52, 1.9, 2.3, 1.6)
    frames(f, "WindowFramesLow", (-3.9, 3.9), 4.6, 1.9, 2.3, 1.6)
    windows(f, "WindowsUp", (-3.6, 0, 3.6), 4.02, 5.0, 1.8, 1.5)
    frames(f, "WindowFramesUp", (-3.6, 0, 3.6), 4.1, 5.0, 1.8, 1.5)
    shut = Batch(f, "Shutters", "Mat_Roof_Red")
    for x in (-3.6, 0, 3.6):
        shut.box((x - 1.15, 4.12, 5.0), (0.4, 0.08, 1.5)).box((x + 1.15, 4.12, 5.0), (0.4, 0.08, 1.5))
    shut.emit()
    stripes(f, "Awning", (0, 5.4, 3.15), 10, 1.2, 2.0, -0.3, "Mat_White", "Mat_Roof_Red")
    # chef hat and crossed fork and knife signs on the roof
    hat = Batch(f, "ChefHat", "Mat_White", smooth=True)
    hat.cyl((0, 0, 9.15), 0.95, 0.95, 0.9, seg=20)
    for x, y in ((0, 0), (0.55, 0.2), (-0.55, 0.2), (0, -0.5), (0, 0.35)):
        hat.sphere((x, y, 10.0), (0.62, 0.62, 0.58))
    hat.emit()
    cut = Batch(f, "ForkKnife", "Mat_Metal")
    cut.box((-3.0, 0, 9.6), (0.14, 0.14, 2.4), rot=(0, 0.25, 0)).box((3.0, 0, 9.6), (0.14, 0.14, 2.4), rot=(0, -0.25, 0))
    cut.box((-3.2, 0, 10.6), (0.7, 0.14, 0.4)).sphere((3.25, 0, 10.7), (0.28, 0.1, 0.6), seg=(8, 6))
    cut.emit()
    f.box("SignBoard", (0, 4.15, 6.5), (7.5, 0.2, 0.9), "Mat_Wood_Dark")
    f.text("Sign", "RESTAURANT", (0, 4.28, 6.5), 0.6, "Mat_White")
    # fenced outdoor dining patio with tables, string lights and planters
    fence_line(f, "PatioFenceL", (-7.2, 6.0), (-7.2, 12.4))
    fence_line(f, "PatioFenceR", (7.2, 6.0), (7.2, 12.4))
    fence_line(f, "PatioFenceFrontA", (-7.2, 12.4), (-1.6, 12.4))
    fence_line(f, "PatioFenceFrontB", (1.6, 12.4), (7.2, 12.4))
    f.box("PatioFloor", (0, 9.2, 0.04), (14.4, 6.8, 0.08), "Mat_Plaza")
    for i, (x, y) in enumerate(((-4.4, 8.0), (0.0, 8.0), (4.4, 8.0), (-2.2, 11.0), (2.2, 11.0))):
        table_with_umbrella(f, f"Table{i}", (x, y), "Mat_Roof_Red" if i % 2 else "Mat_White", umbrella=(i % 2 == 0))
    lamps = Batch(f, "StringLights", "Mat_Lamp_Glow", smooth=True)
    for i in range(13):
        lamps.sphere((-6.6 + i * 1.1, 6.2, 3.3 - 0.25 * math.sin(i / 12 * PI)), (0.1, 0.1, 0.1), seg=(6, 4))
    lamps.emit()
    potted_plants(f, "Planters", ((-6.4, 5.4), (6.4, 5.4), (-6.4, 12.4), (6.4, 12.4)))
    # food service counter with serving hatch and menu
    f.box("ServeCounter", (6.9, 2.8, 0.6), (3.0, 1.0, 1.2), "Mat_Wood")
    f.box("ServeCounterTop", (6.9, 2.8, 1.25), (3.2, 1.2, 0.1), "Mat_Wood_Dark")
    f.box("ServeRoof", (6.9, 3.3, 2.9), (3.6, 2.2, 0.15), "Mat_Roof_Red")
    for sx in (5.3, 8.5):
        f.box(f"ServePost{int(sx)}", (sx, 3.6, 1.6), (0.12, 0.12, 3.0), "Mat_Wood_Dark")
    food = Batch(f, "ServeDishes", "Mat_White")
    for i in range(3):
        food.cyl((6.0 + i * 0.9, 2.8, 1.36), 0.28, 0.28, 0.06, seg=12)
    food.emit()
    f.box("MenuBoard", (6.9, 4.4, 2.0), (1.6, 0.12, 1.0), "Mat_Chalk")


# ------------------------------------------------------------------ 04 Supermarket
def shelf_unit(f, name, c, length, rows=4, colors=("Mat_Roof_Red", "Mat_Wall_Yellow", "Mat_Leaf", "Mat_Roof_Blue", "Mat_Wall_Pink", "Mat_Wall_Orange")):
    x, y, z = c
    frame = Batch(f, f"{name}Frame", "Mat_Metal")
    frame.box((x, y, 1.0), (length, 0.7, 0.08))
    for r in range(rows):
        frame.box((x, y, 0.4 + r * 0.55), (length, 0.7, 0.05))
    frame.box((x - length / 2, y, 1.0), (0.08, 0.7, 2.0)).box((x + length / 2, y, 1.0), (0.08, 0.7, 2.0))
    frame.emit()
    prod = {m: Batch(f, f"{name}Products_{m[4:]}", m) for m in colors}
    for r in range(rows):
        for i in range(int(length / 0.45)):
            m = colors[(i + r * 2) % len(colors)]
            prod[m].box((x - length / 2 + 0.3 + i * 0.45, y, 0.55 + r * 0.55), (0.32, 0.5, 0.3))
    for b in prod.values():
        b.emit()


def supermarket(f):
    # hollow building: the glass front lets you see the shelves inside
    f.box("WallBack", (0, -5.1, 2.5), (16, 0.4, 5), "Mat_Wall_Teal")
    f.box("WallLeft", (-7.8, 0, 2.5), (0.4, 10.4, 5), "Mat_Wall_Teal")
    f.box("WallRight", (7.8, 0, 2.5), (0.4, 10.4, 5), "Mat_Wall_Teal")
    f.box("FloorSlab", (0, 0, 0.1), (16, 11, 0.2), "Mat_Sidewalk")
    f.box("RoofSlab", (0, 0, 5.15), (16.8, 11.8, 0.3), "Mat_Roof_Green")
    f.box("RoofParapet", (0, 0, 5.5), (16.8, 11.8, 0.4), "Mat_Wall_Teal")
    f.box("PillarL", (-7.6, 5.2, 2.5), (0.7, 0.7, 5), "Mat_White")
    f.box("PillarR", (7.6, 5.2, 2.5), (0.7, 0.7, 5), "Mat_White")
    f.box("PillarMid", (-3.0, 5.2, 2.5), (0.4, 0.4, 5), "Mat_White")
    f.box("PillarMid2", (3.0, 5.2, 2.5), (0.4, 0.4, 5), "Mat_White")
    f.box("GlassFrontL", (-5.3, 5.25, 2.0), (4.2, 0.1, 3.4), "Mat_Glass")
    f.box("GlassFrontR", (5.3, 5.25, 2.0), (4.2, 0.1, 3.4), "Mat_Glass")
    f.box("GlassTransom", (0, 5.25, 4.1), (14.8, 0.1, 1.3), "Mat_Glass")
    # large sliding glass doors with aluminium frames and a visible gap
    f.box("DoorGlassL", (-1.0, 5.3, 1.45), (1.7, 0.08, 2.8), "Mat_Glass")
    f.box("DoorGlassR", (1.0, 5.3, 1.45), (1.7, 0.08, 2.8), "Mat_Glass")
    rails = Batch(f, "DoorFrames", "Mat_White")
    for x in (-1.9, -0.1, 0.1, 1.9):
        rails.box((x, 5.34, 1.45), (0.1, 0.1, 2.9))
    rails.box((0, 5.34, 2.95), (4.0, 0.12, 0.12))
    rails.emit()
    f.box("SignBand", (0, 5.7, 4.75), (11, 0.4, 1.1), "Mat_Sign_Yellow")
    f.text("Sign", "SUPERMARKET", (0, 5.95, 4.75), 0.75, "Mat_Dark")
    apple = Batch(f, "AppleSign", "Mat_Roof_Red", smooth=True)
    apple.sphere((0, 0, 7.0), (1.1, 1.1, 1.0))
    apple.emit()
    stem = Batch(f, "AppleStem", "Mat_Wood_Dark")
    stem.cyl((0, 0, 8.05), 0.07, 0.07, 0.5, seg=6)
    stem.emit()
    leaf = Batch(f, "AppleLeaf", "Mat_Leaf", smooth=True)
    leaf.sphere((0.45, 0, 8.1), (0.4, 0.15, 0.2), seg=(8, 6))
    leaf.emit()
    # colourful interior shelves, checkout counters, and a few carts inside
    for i, x in enumerate((-5.6, -2.4, 0.8, 4.0)):
        shelf_unit(f, f"Shelf{i}", (x, -1.8, 0), 2.6)
    shelf_unit(f, "ShelfBack", (0, -4.4, 0), 12.0)
    f.box("CheckoutA", (5.6, 3.6, 0.55), (2.0, 0.9, 1.1), "Mat_Wood")
    f.box("CheckoutB", (-5.6, 3.6, 0.55), (2.0, 0.9, 1.1), "Mat_Wood")
    # outdoor cart corral with a row of shopping carts
    f.box("CartCorralRoof", (-4.8, 8.4, 2.1), (6.0, 1.8, 0.12), "Mat_Roof_Green")
    posts = Batch(f, "CartCorralPosts", "Mat_Metal")
    for x in (-7.6, -2.0):
        for y in (7.6, 9.2):
            posts.box((x, y, 1.05), (0.1, 0.1, 2.1))
    posts.emit()
    basket, base, handles, wl = Batch(f, "CartBaskets", "Mat_Rail"), Batch(f, "CartBases", "Mat_Metal"), Batch(f, "CartHandles", "Mat_Roof_Red"), Batch(f, "CartWheels", "Mat_Dark")
    for i in range(6):
        x = -7.0 + i * 0.85
        basket.box((x, 8.4, 0.85), (0.7, 1.0, 0.5))
        base.box((x, 8.4, 0.4), (0.7, 1.0, 0.06))
        handles.box((x, 7.8, 1.15), (0.7, 0.06, 0.06))
        wheels(wl, [(x - 0.28, 8.1, 0.1), (x + 0.28, 8.1, 0.1), (x - 0.28, 8.7, 0.1), (x + 0.28, 8.7, 0.1)], 0.1, 0.06)
    for b in (basket, base, handles, wl):
        b.emit()
    # produce stands with fruit
    f.box("ProduceStandA", (4.2, 7.4, 0.5), (3.2, 1.4, 1.0), "Mat_Wood")
    fruit_r, fruit_o, fruit_g = Batch(f, "FruitRed", "Mat_Roof_Red", smooth=True), Batch(f, "FruitOrange", "Mat_Wall_Orange", smooth=True), Batch(f, "FruitGreen", "Mat_Leaf_Light", smooth=True)
    for i in range(6):
        for j, b in enumerate((fruit_r, fruit_o, fruit_g)):
            b.sphere((3.0 + i * 0.5, 7.0 + j * 0.45, 1.12), (0.18, 0.18, 0.18), seg=(6, 5))
    for b in (fruit_r, fruit_o, fruit_g):
        b.emit()
    f.box("Awning", (4.2, 7.8, 2.4), (3.8, 2.4, 0.12), "Mat_Roof_Coral", rot=(-0.2, 0, 0))


# ------------------------------------------------------------------ 05 Shopping Mall
def mannequin(b_body, b_head, x, y, z):
    b_body.cyl((x, y, z + 0.9), 0.22, 0.3, 1.3, seg=10).cyl((x, y, z + 0.1), 0.25, 0.3, 0.2, seg=10)
    b_head.sphere((x, y, z + 1.7), (0.16, 0.16, 0.2), seg=(8, 6))


def mall(f):
    f.box("Glass", (0, 0, 7.0), (16, 14, 14), "Mat_Glass")
    slabs = Batch(f, "FloorSlabs", "Mat_White")
    pink = Batch(f, "FloorSlabsPink", "Mat_Wall_Pink")
    for i, z in enumerate((3.5, 7.0, 10.5, 14.1)):
        (slabs if i % 2 else pink).box((0, 0, z), (16.6, 14.6, 0.4))
    slabs.emit()
    pink.emit()
    mull = Batch(f, "Mullions", "Mat_White")
    for x in (-8, -6, -4, -2, 0, 2, 4, 6, 8):
        mull.box((x, 7.1, 7.0), (0.18, 0.2, 14))
    mull.emit()
    for x in (-8.1, 8.1):
        f.box(f"Pier{int(x)}", (x, 7.0, 7.0), (0.8, 0.8, 14.2), "Mat_Wall_Pink")
    # fashion storefronts on each floor: awnings, shop signs, mannequins behind the glass
    cols = ("Mat_Roof_Coral", "Mat_Roof_Blue", "Mat_Wall_Yellow")
    for fl, z in enumerate((1.9, 5.4, 8.9)):
        stripes(f, f"Awning{fl}", (-3.6, 7.9, z + 1.0), 5, 1.2, 1.3, -0.25, cols[fl], "Mat_White")
        f.box(f"ShopSign{fl}", (3.6, 7.2, z + 1.2), (4.2, 0.16, 0.6), cols[(fl + 1) % 3])
        body, head = Batch(f, f"Mannequins{fl}", "Mat_Wall_Pink", smooth=True), Batch(f, f"MannequinHeads{fl}", "Mat_Wall_Cream", smooth=True)
        for k in range(4):
            mannequin(body, head, -5.5 + k * 2.2, 5.4, z - 0.9)
        body.emit()
        head.emit()
    # entrance: big round canopy, revolving door, escalator ramp
    f.cyl("Canopy", (3.5, 8.8, 3.4), 3.2, 3.2, 0.3, "Mat_Roof_Coral", seg=28)
    for k, (x, y) in enumerate(((1.2, 10.4), (5.8, 10.4), (1.2, 7.2), (5.8, 7.2))):
        f.cyl(f"CanopyColumn{k}", (x, y, 1.65), 0.16, 0.16, 3.3, "Mat_White", seg=10)
    f.cyl("RevolvingDoor", (3.5, 7.4, 1.4), 1.4, 1.4, 2.7, "Mat_Glass", seg=20)
    f.box("EscalatorRamp", (-3.6, 7.8, 0.9), (1.6, 3.4, 0.3), "Mat_Metal", rot=(0.38, 0, 0))
    f.box("EscalatorRail", (-2.8, 7.8, 1.3), (0.1, 3.4, 0.1), "Mat_Dark", rot=(0.38, 0, 0))
    # rooftop sign, shopping bag sculpture, hanging banners, planters
    f.box("SignBand", (0, 7.4, 15.4), (13.6, 0.6, 1.7), "Mat_Sign_Yellow")
    f.text("Sign", "SHOPPING MALL", (0, 7.75, 15.4), 1.0, "Mat_Dark")
    f.box("BagSign", (0, 0, 17.6), (2.0, 1.0, 1.8), "Mat_Roof_Coral")
    handles = Batch(f, "BagHandles", "Mat_Wood")
    ring_x(handles, (0, 0, 18.6), 0.55, 0.07, segs=10)
    handles.emit()
    ban_a, ban_b = Batch(f, "BannersA", "Mat_Roof_Coral"), Batch(f, "BannersB", "Mat_Roof_Blue")
    for i, x in enumerate((-6.4, -3.2, 3.2, 6.4)):
        (ban_a if i % 2 else ban_b).box((x, 7.3, 12.2), (1.1, 0.06, 3.0))
    ban_a.emit()
    ban_b.emit()
    potted_plants(f, "Planters", ((-7.4, 8.4), (7.4, 8.4), (-7.4, 11.0), (7.4, 11.0)), 0.55)
    roofrail = Batch(f, "RoofRail", "Mat_White")
    for x in range(-8, 9, 2):
        roofrail.box((x, 7.0, 14.7), (0.08, 0.08, 0.8))
    roofrail.box((0, 7.0, 15.05), (16.2, 0.1, 0.1))
    roofrail.emit()


# ------------------------------------------------------------------ 06 Library
def library(f):
    f.box("Walls", (0, 0, 3.6), (14, 10, 7.2), "Mat_Wall_Cream")
    f.box("Plinth", (0, 0, 0.3), (14.6, 10.6, 0.6), "Mat_Sidewalk")
    f.box("Cornice", (0, 0, 7.3), (14.8, 10.8, 0.4), "Mat_White")
    f.box("RoofSlab", (0, 0, 7.7), (13.4, 9.6, 0.4), "Mat_Roof_Gray")
    dome = Batch(f, "Dome", "Mat_Roof_Green", smooth=True)
    dome.sphere((0, -1.0, 8.0), (3.6, 3.6, 2.4), seg=(20, 12))
    dome.emit()
    f.cyl("DomeDrum", (0, -1.0, 8.2), 3.6, 3.6, 0.6, "Mat_Wall_Cream", seg=20)
    f.box("DomeFinial", (0, -1.0, 10.7), (0.25, 0.25, 1.0), "Mat_Sign_Yellow")
    f.gable("Pediment", (0, 5.6, 7.7), 9.8, 1.6, 2.6, "Mat_Wall_Cream", ridge="y", overhang=0.0)
    f.cyl("PedimentRelief", (0, 6.5, 8.6), 0.8, 0.8, 0.12, "Mat_Sign_Yellow", seg=20, rot=(PI / 2, 0, 0))
    cols = Batch(f, "Columns", "Mat_White", smooth=True)
    for i in range(6):
        cols.cyl((-5 + i * 2, 5.6, 3.9), 0.42, 0.42, 6.6, seg=16)
        cols.cyl((-5 + i * 2, 5.6, 0.75), 0.55, 0.55, 0.3, seg=16)
        cols.cyl((-5 + i * 2, 5.6, 7.1), 0.55, 0.55, 0.3, seg=16)
    cols.emit()
    steps = Batch(f, "Steps", "Mat_Sidewalk")
    for i in range(4):
        steps.box((0, 6.5 + i * 0.55, 0.15 + (3 - i) * 0.0 + 0.15 * (4 - i) * 0.0 + 0.1 + i * 0.0), (12.0 - i * 0.8, 1.2, 0.3 + (3 - i) * 0.2))
    steps.emit()
    f.box("DoorFrame", (0, 5.06, 1.75), (2.4, 0.2, 3.1), "Mat_White")
    f.box("DoorLeft", (-0.5, 5.12, 1.6), (0.95, 0.1, 2.8), "Mat_Wood_Dark")
    f.box("DoorRight", (0.5, 5.12, 1.6), (0.95, 0.1, 2.8), "Mat_Wood_Dark")
    # tall arched windows along the facade and sides
    win, arch = Batch(f, "ArchWindows", "Mat_Glass"), Batch(f, "ArchWindowTops", "Mat_Glass", smooth=True)
    for x in (-5.4, -3.2, 3.2, 5.4):
        win.box((x, 5.04, 3.2), (1.1, 0.1, 2.6))
        arch.cyl((x, 5.04, 4.5), 0.55, 0.55, 0.1, seg=14, rot=(PI / 2, 0, 0))
    win.emit()
    arch.emit()
    frames(f, "WindowFrames", (-5.4, -3.2, 3.2, 5.4), 5.1, 3.2, 1.1, 2.6)
    f.box("SignBoard", (0, 6.4, 7.9), (4.6, 0.2, 0.8), "Mat_Wall_Cream")
    f.text("Sign", "LIBRARY", (0, 6.55, 7.9), 0.6, "Mat_Dark")
    # giant open book sculpture and book-shaped banners
    books = Batch(f, "BookSculpture", "Mat_Roof_Coral")
    books.box((-0.75, -1.0, 11.6), (1.4, 0.2, 1.8), rot=(0, 0.4, 0))
    books2 = Batch(f, "BookSculptureB", "Mat_Wall_Yellow")
    books2.box((0.75, -1.0, 11.6), (1.4, 0.2, 1.8), rot=(0, -0.4, 0))
    books.emit()
    books2.emit()
    # garden: hedges, topiary, a small fountain, benches and reading umbrella
    hedge = Batch(f, "Hedges", "Mat_Leaf_Dark")
    for x in (-10.4, 10.4):
        for y in (-2.0, 1.0, 4.0):
            hedge.box((x, y, 0.5), (1.4, 2.4, 1.0))
    hedge.emit()
    top = Batch(f, "Topiary", "Mat_Leaf", smooth=True)
    for x, y in ((-9.0, 7.5), (9.0, 7.5), (-9.0, -4.5), (9.0, -4.5)):
        top.sphere((x, y, 1.6), (0.8, 0.8, 0.8), seg=(10, 7))
    top.emit()
    pots = Batch(f, "TopiaryPots", "Mat_Roof_Coral")
    for x, y in ((-9.0, 7.5), (9.0, 7.5), (-9.0, -4.5), (9.0, -4.5)):
        pots.cyl((x, y, 0.5), 0.5, 0.4, 1.0, seg=10)
    pots.emit()
    f.cyl("GardenFountainBase", (-11.5, 8.5, 0.35), 1.6, 1.6, 0.7, "Mat_Plaza", seg=20)
    f.cyl("GardenFountainWater", (-11.5, 8.5, 0.72), 1.35, 1.35, 0.05, "Mat_Pool", seg=20)
    table_with_umbrella(f, "ReadingTable", (11.0, 9.0), "Mat_Roof_Blue", chairs=2)


# ------------------------------------------------------------------ 07 School
def school(f):
    f.box("Walls", (0, 0, 3.5), (20, 9, 7), "Mat_Wall_Yellow")
    f.box("WingL", (-12.5, 0.5, 2.6), (5, 7, 5.2), "Mat_Wall_Orange")
    f.box("WingR", (12.5, 0.5, 2.6), (5, 7, 5.2), "Mat_Wall_Orange")
    f.box("Plinth", (0, 0, 0.3), (20.6, 9.6, 0.6), "Mat_Sidewalk")
    f.box("RoofSlab", (0, 0, 7.2), (21, 9.8, 0.4), "Mat_Roof_Red")
    f.box("RoofWingL", (-12.5, 0.5, 5.3), (5.6, 7.6, 0.4), "Mat_Roof_Red")
    f.box("RoofWingR", (12.5, 0.5, 5.3), (5.6, 7.6, 0.4), "Mat_Roof_Red")
    f.box("Tower", (0, 0, 10.2), (4.4, 4.4, 6.0), "Mat_Wall_Cream")
    f.cyl("TowerRoof", (0, 0, 14.3), 3.3, 0.1, 2.2, "Mat_Roof_Red", seg=4, rot=(0, 0, PI / 4))
    f.cyl("ClockFace", (0, 2.3, 10.6), 1.35, 1.35, 0.16, "Mat_White", seg=24, rot=(PI / 2, 0, 0))
    hands = Batch(f, "ClockHands", "Mat_Dark")
    hands.box((0, 2.42, 10.95), (0.12, 0.06, 0.85)).box((0.38, 2.42, 10.6), (0.75, 0.06, 0.1))
    for k in range(12):
        a = PI * 2 * k / 12
        hands.box((1.1 * math.sin(a), 2.4, 10.6 + 1.1 * math.cos(a)), (0.08, 0.04, 0.12))
    hands.emit()
    bell = Batch(f, "Bell", "Mat_Sign_Yellow", smooth=True)
    bell.cyl((0, 0, 12.2), 0.7, 0.4, 0.8, seg=12)
    bell.emit()
    f.box("DoorFrame", (0, 4.52, 1.6), (3.2, 0.2, 3.0), "Mat_White")
    f.box("DoorLeft", (-0.7, 4.6, 1.45), (1.2, 0.1, 2.7), "Mat_Wood_Dark")
    f.box("DoorRight", (0.7, 4.6, 1.45), (1.2, 0.1, 2.7), "Mat_Wood_Dark")
    xs = (-8.5, -5.5, 5.5, 8.5)
    windows(f, "WindowsMain", xs, 4.52, 3.7, 1.8, 1.7)
    frames(f, "WindowFramesMain", xs, 4.58, 3.7, 1.8, 1.7)
    windows(f, "WindowsMainLow", xs, 4.52, 1.5, 1.8, 1.3)
    windows(f, "WindowsWings", (-13.5, -11.0, 11.0, 13.5), 4.02, 2.8, 1.6, 1.6)
    f.box("SignBoard", (0, 4.6, 6.3), (6.0, 0.2, 0.9), "Mat_Wall_Cream")
    f.text("Sign", "SCHOOL", (0, 4.72, 6.3), 0.65, "Mat_Dark")
    f.cyl("FlagPole", (-8.5, 0.5, 9.4), 0.06, 0.06, 4.4, "Mat_Rail", seg=6)
    f.box("Flag", (-7.8, 0.5, 10.9), (1.4, 0.05, 0.9), "Mat_Roof_Blue")
    mural = Batch(f, "WingMurals", "Mat_Roof_Coral")
    mural_b = Batch(f, "WingMuralsB", "Mat_Roof_Blue")
    for i, x in enumerate((-14.6, -10.4, 10.4, 14.6)):
        (mural if i % 2 else mural_b).box((x, 4.02, 1.2), (1.3, 0.08, 1.0))
    mural.emit()
    mural_b.emit()
    # entrance gate and a bike rack
    gate = Batch(f, "GatePosts", "Mat_Wall_Brick")
    gate.box((-3.0, 9.6, 1.1), (0.7, 0.7, 2.2)).box((3.0, 9.6, 1.1), (0.7, 0.7, 2.2))
    gate.emit()
    f.box("GateBar", (0, 9.6, 2.35), (6.7, 0.35, 0.4), "Mat_Roof_Blue")
    f.text("GateText", "WELCOME", (0, 9.8, 2.35), 0.28, "Mat_White")
    fence_line(f, "SchoolFenceL", (-3.4, 9.6), (-9.5, 9.6))
    fence_line(f, "SchoolFenceR", (3.4, 9.6), (9.5, 9.6))
    bikes = Batch(f, "BikeRack", "Mat_Rail")
    for i in range(5):
        bikes.box((-9.5 + i * 0.7, 7.0, 0.45), (0.06, 1.2, 0.9))
    bikes.emit()
    # sports court with line markings and two hoops
    f.box("Court", (17.5, 1.0, 0.05), (16, 9.5, 0.1), "Mat_Court")
    lines = Batch(f, "CourtLines", "Mat_Marking")
    lines.box((17.5, 1.0, 0.12), (0.15, 9.5, 0.02)).box((9.6, 1.0, 0.12), (0.15, 9.5, 0.02)).box((25.4, 1.0, 0.12), (0.15, 9.5, 0.02))
    lines.box((17.5, -3.7, 0.12), (16, 0.15, 0.02)).box((17.5, 5.7, 0.12), (16, 0.15, 0.02))
    lines.cyl((17.5, 1.0, 0.12), 1.6, 1.6, 0.02, seg=24)
    lines.emit()
    hoops = Batch(f, "HoopPoles", "Mat_Dark")
    ring = Batch(f, "HoopRings", "Mat_Roof_Coral", smooth=True)
    board = Batch(f, "HoopBoards", "Mat_White")
    for sx, dx in ((10.2, 0.55), (24.8, -0.55)):
        hoops.cyl((sx, 1.0, 1.6), 0.07, 0.07, 3.2, seg=8)
        board.box((sx + dx * 0.4, 1.0, 3.0), (0.06, 1.2, 0.8))
        ring_x(ring, (sx + dx, 1.0, 2.9), 0.32, 0.03, segs=10)
    hoops.emit()
    ring.emit()
    board.emit()
    # small playground by the court: slide and swings
    f.box("SlideTower", (13.0, 7.8, 1.3), (1.4, 1.4, 2.6), "Mat_Roof_Blue")
    f.box("SlideRamp", (13.0, 9.6, 1.1), (1.0, 3.2, 0.14), "Mat_Roof_Red", rot=(0.55, 0, 0))
    f.box("SwingBar", (20.0, 8.0, 2.4), (4.0, 0.12, 0.12), "Mat_Dark")
    sw = Batch(f, "SwingLegs", "Mat_Dark")
    for x in (18.1, 21.9):
        sw.box((x, 7.5, 1.2), (0.1, 0.1, 2.5), rot=(0.25, 0, 0)).box((x, 8.5, 1.2), (0.1, 0.1, 2.5), rot=(-0.25, 0, 0))
    sw.emit()
    seats = Batch(f, "SwingSeats", "Mat_Sign_Yellow")
    for x in (19.2, 20.8):
        seats.box((x, 8.0, 0.7), (0.6, 0.35, 0.08))
    seats.emit()


# ------------------------------------------------------------------ 08 Hotel
def hotel(f):
    f.box("Tower", (0, 0, 10.0), (12, 12, 20), "Mat_Wall_Cream")
    f.box("Podium", (0, 1.0, 2.0), (14, 11.5, 4.0), "Mat_Wall_Teal")
    f.box("PodiumRoof", (0, 1.0, 4.1), (14.6, 12.1, 0.3), "Mat_White")
    bal = Batch(f, "Balconies", "Mat_Wall_Teal")
    rails = Batch(f, "BalconyRails", "Mat_White")
    for i in range(5):
        z = 4.6 + i * 3.1
        bal.box((0, 6.5, z), (12.6, 1.3, 0.25))
        for x in range(-6, 7, 1):
            rails.box((x, 7.1, z + 0.55), (0.06, 0.06, 0.8))
        rails.box((0, 7.1, z + 0.95), (12.6, 0.06, 0.08))
    bal.emit()
    rails.emit()
    for r in range(5):
        windows(f, f"Windows{r}", (-3.6, 0, 3.6), 6.06, 5.6 + r * 3.1, 1.8, 1.5)
    # lobby: glass front with a visible reception desk, plant and sofa
    f.box("LobbyGlass", (0, 7.0, 2.0), (9.0, 0.12, 3.4), "Mat_Glass")
    f.box("RevolvingDoor", (0, 7.4, 1.4), (2.4, 2.4, 2.7), "Mat_Glass")
    f.cyl("RevolvingCore", (0, 7.4, 1.4), 1.2, 1.2, 2.7, "Mat_Glass", seg=16)
    f.box("ReceptionDesk", (-2.4, 4.8, 0.6), (3.0, 1.0, 1.2), "Mat_Wood")
    f.box("ReceptionTop", (-2.4, 4.8, 1.25), (3.2, 1.1, 0.1), "Mat_Wood_Dark")
    f.box("LobbySofa", (3.0, 4.6, 0.45), (2.8, 1.0, 0.9), "Mat_Roof_Coral")
    # canopy on columns, luggage cart
    f.box("Canopy", (0, 9.4, 3.4), (7.0, 3.6, 0.25), "Mat_Roof_Coral")
    for k, (x, y) in enumerate(((-3.2, 10.9), (3.2, 10.9))):
        f.cyl(f"CanopyColumn{k}", (x, y, 1.7), 0.18, 0.18, 3.4, "Mat_White", seg=10)
    cart = Batch(f, "LuggageCart", "Mat_Sign_Yellow")
    cart.box((4.8, 9.2, 0.8), (1.2, 0.7, 0.08)).box((4.8, 8.9, 1.2), (1.2, 0.06, 1.0)).box((4.8, 9.2, 1.6), (1.2, 0.06, 0.06))
    cart.emit()
    bags = Batch(f, "Luggage", "Mat_Roof_Blue")
    bags.box((4.6, 9.2, 1.1), (0.55, 0.4, 0.55)).box((5.2, 9.2, 1.0), (0.45, 0.35, 0.4))
    bags.emit()
    # roof: sign, three stars, antenna
    f.box("RoofTop", (0, 0, 20.3), (12.6, 12.6, 0.6), "Mat_Wall_Teal")
    f.box("SignBand", (0, 6.25, 18.6), (8.4, 0.45, 1.5), "Mat_Sign_Yellow")
    f.text("Sign", "HOTEL", (0, 6.55, 18.6), 0.95, "Mat_Dark")
    for i, x in enumerate((-2.4, 0, 2.4)):
        f.star(f"Star{i}", (x, 6.4, 22.0), 0.8, 0.34, 0.12, "Mat_Sign_Yellow")
    f.cyl("Antenna", (-4.5, -3.0, 22.0), 0.08, 0.08, 3.4, "Mat_Rail", seg=6)
    # swimming pool with deck, ladder, loungers, umbrellas
    f.box("PoolDeck", (-10.0, 7.5, 0.05), (12.4, 8.4, 0.1), "Mat_Plaza")
    f.box("PoolRim", (-10.0, 7.5, 0.18), (10.2, 6.0, 0.16), "Mat_White")
    f.box("Pool", (-10.0, 7.5, 0.2), (9.6, 5.4, 0.12), "Mat_Pool")
    lad = Batch(f, "PoolLadder", "Mat_Metal")
    lad.cyl((-5.5, 6.2, 0.7), 0.04, 0.04, 1.0, seg=6).cyl((-5.5, 6.8, 0.7), 0.04, 0.04, 1.0, seg=6)
    lad.emit()
    lounge, pad = Batch(f, "Loungers", "Mat_White"), Batch(f, "LoungerPads", "Mat_Wall_Pink")
    for i in range(4):
        x = -13.4 + i * 2.0
        lounge.box((x, 11.9, 0.3), (0.8, 1.9, 0.3))
        pad.box((x, 11.9, 0.5), (0.7, 1.7, 0.08))
    lounge.emit()
    pad.emit()
    table_with_umbrella(f, "PoolTable", (-5.6, 11.2), "Mat_Roof_Coral", chairs=2)
    ring = Batch(f, "PoolFloat", "Mat_Roof_Red", smooth=True)
    ring_x(ring, (-9.0, 7.5, 0.42), 0.4, 0.09, segs=10)
    ring.emit()
    potted_plants(f, "Planters", ((-6.4, 4.2), (6.4, 4.2), (-14.6, 4.0), (-14.6, 12.0)))


# ------------------------------------------------------------------ 09 Train station
def station(f):
    f.box("Walls", (0, 0, 3.0), (16, 8, 6), "Mat_Wall_Brick")
    f.box("Plinth", (0, 0, 0.3), (16.6, 8.6, 0.6), "Mat_Sidewalk")
    f.gable("Roof", (0, 0, 6.0), 16, 8, 2.2, "Mat_Roof_Blue")
    f.box("ClockTower", (0, 0.5, 8.0), (3.0, 3.0, 4.0), "Mat_Wall_Brick")
    f.cyl("ClockTowerRoof", (0, 0.5, 10.7), 2.3, 0.1, 1.8, "Mat_Roof_Blue", seg=4, rot=(0, 0, PI / 4))
    f.cyl("ClockFace", (0, 2.1, 8.4), 1.0, 1.0, 0.16, "Mat_White", seg=24, rot=(PI / 2, 0, 0))
    hands = Batch(f, "ClockHands", "Mat_Dark")
    hands.box((0, 2.2, 8.7), (0.1, 0.05, 0.6)).box((0.25, 2.2, 8.4), (0.5, 0.05, 0.08))
    hands.emit()
    f.box("DoorFrame", (0, 4.06, 1.5), (3.0, 0.2, 3.0), "Mat_White")
    f.box("DoorGlass", (0, 4.14, 1.4), (2.6, 0.1, 2.7), "Mat_Glass")
    f.cyl("DoorArch", (0, 4.14, 2.8), 1.3, 1.3, 0.12, "Mat_Glass", seg=16, rot=(PI / 2, 0, 0))
    xs = (-6.0, -3.8, 3.8, 6.0)
    windows(f, "Windows", xs, 4.06, 2.6, 1.4, 1.8)
    frames(f, "WindowFrames", xs, 4.12, 2.6, 1.4, 1.8)
    f.box("SignBoard", (0, 4.2, 4.9), (6.4, 0.2, 0.8), "Mat_Wall_Cream")
    f.text("Sign", "TRAIN STATION", (0, 4.32, 4.9), 0.5, "Mat_Dark")
    # platform with canopy, posts, benches, ticket kiosk, yellow safety edge
    f.box("Platform", (0, -6.0, 0.4), (32, 3.2, 0.8), "Mat_Sidewalk")
    edge = Batch(f, "PlatformEdge", "Mat_Hazard")
    edge.box((0, -7.5, 0.82), (32, 0.25, 0.04))
    edge.emit()
    f.box("PlatformRoof", (0, -6.0, 3.8), (16, 4.0, 0.22), "Mat_Roof_Blue")
    posts = Batch(f, "PlatformPosts", "Mat_Dark")
    for x in (-7, -2.5, 2.5, 7):
        posts.box((x, -5.0, 2.3), (0.22, 0.22, 3.0))
    posts.emit()
    benches = Batch(f, "PlatformBenches", "Mat_Wood")
    for x in (-5, 0, 5):
        benches.box((x, -5.2, 1.3), (1.6, 0.45, 0.1)).box((x, -4.95, 1.7), (1.6, 0.08, 0.5))
    benches.emit()
    f.box("TicketKiosk", (10.5, -5.4, 1.6), (2.0, 1.6, 1.6), "Mat_Wall_Cream")
    f.box("KioskRoof", (10.5, -5.4, 2.55), (2.4, 2.0, 0.2), "Mat_Roof_Coral")
    f.box("PlatformClock", (-10.5, -5.4, 3.0), (0.2, 1.2, 1.2), "Mat_White")
    # two tracks with ballast, rails and sleepers, a signal light
    f.box("Ballast", (0, -11.0, 0.08), (36, 5.6, 0.16), "Mat_Rock")
    sleep = Batch(f, "Sleepers", "Mat_Wood_Dark")
    rail = Batch(f, "Rails", "Mat_Rail")
    for tr, y in enumerate((-9.6, -12.4)):
        for dy in (-0.55, 0.55):
            rail.box((0, y + dy, 0.28), (36, 0.12, 0.14))
        for k in range(30):
            sleep.box((-17.4 + k * 1.2, y, 0.2), (0.35, 1.8, 0.1))
    sleep.emit()
    rail.emit()
    f.cyl("SignalPole", (15.5, -8.0, 2.0), 0.1, 0.1, 4.0, "Mat_Dark", seg=8)
    lights = Batch(f, "SignalLights", "Mat_Roof_Red", smooth=True)
    lights.sphere((15.5, -7.8, 3.9), (0.2, 0.15, 0.2), seg=(8, 6))
    lights.emit()
    # cartoon train: engine with cabin, chimney, headlight, windows and wheels, plus two cars
    f.box("TrainEngine", (-4.0, -9.6, 1.6), (4.6, 2.4, 2.6), "Mat_Roof_Coral")
    f.cyl("TrainBoiler", (-5.2, -9.6, 1.9), 1.1, 1.1, 2.6, "Mat_Roof_Red", seg=16, rot=(0, PI / 2, 0))
    f.cyl("TrainChimney", (-6.0, -9.6, 3.5), 0.35, 0.5, 1.0, "Mat_Dark", seg=12)
    f.box("TrainCabinRoof", (-2.8, -9.6, 3.1), (2.4, 2.8, 0.2), "Mat_Roof_Blue")
    tw = Batch(f, "TrainWindows", "Mat_Glass")
    tw.box((-2.8, -8.38, 2.0), (1.2, 0.08, 0.9))
    tr_lamp = Batch(f, "TrainHeadlight", "Mat_Lamp_Glow", smooth=True)
    tr_lamp.sphere((-7.15, -9.6, 1.5), (0.28, 0.28, 0.28), seg=(8, 6))
    tw.emit()
    tr_lamp.emit()
    car_a, car_b, win_c, wheel_b = Batch(f, "TrainCarTeal", "Mat_Wall_Teal"), Batch(f, "TrainCarYellow", "Mat_Wall_Yellow"), Batch(f, "TrainCarWindows", "Mat_Glass"), Batch(f, "TrainWheels", "Mat_Dark")
    for i in range(2):
        x = 1.4 + i * 5.2
        (car_b if i else car_a).box((x, -9.6, 1.6), (4.8, 2.4, 2.6))
        for k in range(3):
            win_c.box((x - 1.5 + k * 1.5, -8.38, 2.0), (0.9, 0.08, 0.9))
    wheels(wheel_b, [(x, -8.4, 0.45) for x in (-6.0, -4.0, -2.0, 0.0, 2.0, 5.0, 7.0, 10.0, 12.0)], 0.4, 0.12, axis="y")
    for b in (car_a, car_b, win_c, wheel_b):
        b.emit()


# ------------------------------------------------------------------ 10 Airport
def airport(f):
    f.box("Terminal", (0, 0, 3.5), (22, 8, 7), "Mat_Wall_Cream")
    f.box("TerminalBand", (0, 0, 6.6), (22.6, 8.6, 0.8), "Mat_Roof_Blue")
    f.gable("TerminalRoof", (0, 0, 7.0), 22, 8, 1.7, "Mat_Roof_Blue", ridge="x", overhang=0.6)
    f.box("TerminalClerestory", (0, 0, 8.0), (14, 3.2, 0.9), "Mat_Glass")
    f.box("GlassFront", (0, 4.02, 3.0), (17, 0.12, 4.2), "Mat_Glass")
    mull = Batch(f, "GlassMullions", "Mat_White")
    for x in range(-8, 9, 2):
        mull.box((x, 4.1, 3.0), (0.12, 0.14, 4.3))
    mull.emit()
    f.box("Canopy", (0, 5.6, 4.4), (13, 3.2, 0.25), "Mat_Roof_Gray")
    for k, x in enumerate((-5.5, 5.5)):
        f.cyl(f"CanopyColumn{k}", (x, 6.9, 2.2), 0.2, 0.2, 4.4, "Mat_White", seg=10)
    f.box("SignBoard", (0, 4.3, 6.5), (8.4, 0.3, 1.0), "Mat_Roof_Blue")
    f.text("Sign", "AIRPORT", (0, 4.5, 6.5), 0.8, "Mat_White")
    f.cyl("TowerShaft", (13.5, -1, 8.0), 1.5, 1.2, 16, "Mat_White", seg=16)
    f.cyl("TowerCab", (13.5, -1, 17.0), 2.4, 2.9, 2.4, "Mat_Glass", seg=16)
    f.cyl("TowerRoof", (13.5, -1, 18.7), 3.2, 0.2, 1.1, "Mat_Roof_Coral", seg=16)
    f.cyl("TowerMast", (13.5, -1, 20.4), 0.06, 0.06, 2.2, "Mat_Rail", seg=6)
    # apron, taxi lines, runway with edge lights and threshold markings
    f.box("Apron", (0, -7.0, 0.05), (26, 6, 0.1), "Mat_Sidewalk")
    f.box("Runway", (0, -13.0, 0.06), (32, 6.5, 0.12), "Mat_Runway")
    mk = Batch(f, "RunwayMarkings", "Mat_Marking")
    for k in range(8):
        mk.box((-14 + k * 4, -13.0, 0.14), (2.2, 0.3, 0.02))
    for k in range(4):
        mk.box((-15.2, -14.6 + k * 1.1, 0.14), (1.6, 0.3, 0.02)).box((15.2, -14.6 + k * 1.1, 0.14), (1.6, 0.3, 0.02))
    mk.emit()
    taxi = Batch(f, "TaxiLine", "Mat_Hazard")
    taxi.box((0, -9.8, 0.12), (24, 0.18, 0.02))
    taxi.emit()
    rl = Batch(f, "RunwayLights", "Mat_Lamp_Glow", smooth=True)
    for k in range(17):
        rl.sphere((-16 + k * 2.0, -9.6, 0.2), (0.12, 0.12, 0.12), seg=(6, 4)).sphere((-16 + k * 2.0, -16.4, 0.2), (0.12, 0.12, 0.12), seg=(6, 4))
    rl.emit()
    # jet bridge from the terminal to the aircraft
    f.box("JetBridge", (-2.5, -2.6, 3.0), (2.0, 6.0, 2.0), "Mat_Metal")
    f.box("JetBridgeBase", (-2.5, -5.6, 1.0), (1.0, 1.0, 2.0), "Mat_Dark")
    # detailed airplane parked on the apron
    f.cyl("Plane_Body", (-2, -8.0, 1.9), 1.0, 1.0, 8.4, "Mat_White", seg=18, rot=(0, PI / 2, 0))
    nose = Batch(f, "Plane_Nose", "Mat_White", smooth=True)
    nose.sphere((2.2, -8.0, 1.9), (1.2, 1.0, 1.0))
    nose.sphere((-6.3, -8.0, 2.1), (1.4, 0.8, 0.8))
    nose.emit()
    cock = Batch(f, "Plane_Cockpit", "Mat_Glass")
    cock.box((2.6, -8.0, 2.3), (0.7, 1.3, 0.35)).box((-0.6, -6.98, 2.1), (0.9, 0.06, 0.35)).box((1.0, -6.98, 2.1), (0.9, 0.06, 0.35))
    cock.emit()
    f.box("Plane_Stripe", (-2, -8.0, 1.6), (8.4, 2.05, 0.18), "Mat_Roof_Blue")
    f.box("Plane_Wings", (-1.2, -8.0, 1.6), (2.4, 9.4, 0.22), "Mat_Roof_Blue")
    eng = Batch(f, "Plane_Engines", "Mat_Metal", smooth=True)
    eng.cyl((-0.4, -10.6, 1.2), 0.45, 0.45, 1.4, seg=12, rot=(0, PI / 2, 0)).cyl((-0.4, -5.4, 1.2), 0.45, 0.45, 1.4, seg=12, rot=(0, PI / 2, 0))
    eng.emit()
    f.box("Plane_TailFin", (-6.2, -8.0, 3.4), (1.7, 0.2, 2.2), "Mat_Roof_Blue")
    f.box("Plane_TailWing", (-6.2, -8.0, 2.2), (1.2, 3.6, 0.15), "Mat_Roof_Blue")
    gear = Batch(f, "Plane_Gear", "Mat_Dark")
    gear.cyl((1.2, -8.0, 0.55), 0.06, 0.06, 1.0, seg=6)
    wheels(gear, [(1.2, -8.2, 0.3), (1.2, -7.8, 0.3), (-1.8, -8.7, 0.3), (-1.8, -7.3, 0.3)], 0.3, 0.14, axis="y")
    gear.emit()
    # baggage carts, fuel truck, windsock, helipad
    cart_b, cart_w = Batch(f, "BaggageCarts", "Mat_Wall_Orange"), Batch(f, "BaggageWheels", "Mat_Dark")
    for i in range(3):
        cart_b.box((4.0 + i * 1.7, -5.2, 0.7), (1.4, 1.0, 0.6))
        wheels(cart_w, [(3.5 + i * 1.7, -5.7, 0.15), (4.5 + i * 1.7, -5.7, 0.15)], 0.15, 0.08)
    cart_b.emit()
    cart_w.emit()
    f.box("FuelTruckTank", (9.0, -8.0, 1.5), (3.6, 1.6, 1.6), "Mat_White")
    f.box("FuelTruckCab", (11.2, -8.0, 1.2), (1.2, 1.6, 1.4), "Mat_Roof_Red")
    f.cyl("Windsock", (-12, -15.8, 1.8), 0.06, 0.06, 3.6, "Mat_Rail", seg=6)
    f.cyl("WindsockCone", (-11.4, -15.8, 3.4), 0.4, 0.15, 1.2, "Mat_Roof_Coral", seg=10, rot=(0, PI / 2, 0))
    f.cyl("Helipad", (12.0, -2.5, 0.08), 2.4, 2.4, 0.08, "Mat_Roof_Blue", seg=28)
    hmark = Batch(f, "HelipadMark", "Mat_Marking")
    hmark.box((11.2, -2.5, 0.14), (0.3, 1.8, 0.02)).box((12.8, -2.5, 0.14), (0.3, 1.8, 0.02)).box((12.0, -2.5, 0.14), (1.6, 0.3, 0.02))
    hmark.emit()


BUILDERS = {
    "coffee": coffee, "restaurant": restaurant, "supermarket": supermarket, "mall": mall, "library": library,
    "school": school, "hotel": hotel, "station": station, "airport": airport,
}


def rebuild_buildings(colls):
    """Removes the Phase 1 blockouts and builds the detailed versions in the same collections."""
    for pid, cname, prefix, center, depth, _old, rad in bi.PLACES:
        coll = colls[cname]
        for obj in list(coll.objects):
            mesh = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            if mesh and mesh.users == 0:
                bpy.data.meshes.remove(mesh)
        frame = bi.Frame(coll, prefix, (center[0], center[1], 0), bi.yaw_for(center))
        BUILDERS[pid](frame)
