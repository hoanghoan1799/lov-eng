"""
English Adventure World - Phase 2: Central Park detail, Reusable_Props (instancing), collision names.

What this adds on top of Phase 1
1. 11_Reusable_Props: master meshes (3 tree variants split into trunk and leaves, 4 flower bushes,
   park bench, classic street lamp, wooden fence, signboard, rock, grass tuft). Every placed copy is
   a LINKED DUPLICATE: a new object that shares the master's mesh data (Alt+D). In glTF each
   master becomes one mesh referenced by many nodes, which gltfjsx --instance turns into one
   InstancedMesh per master.
2. Central Park (10-20 players): round tiled plaza, two-tier fountain, giant old tree north of the
   plaza, outdoor stage, quest board at the main entrance, NPC guide area, playground (slide,
   swings, seesaw, sandbox), benches, flower rings, lamps and trees.
3. Props scattered along roads and around the buildings on the whole island.
4. Naming for physics: COL_ for solid things (walls, fountain, tree trunks, benches, lamps...),
   DEC_ for small decoration (flowers, leaves, tufts, awnings, windows...). Ground, roads and water
   keep their plain names so the game can treat them as walkable surfaces.

Called from build_world.py.
"""

import math
import random
import re

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector

import build_island as bi
import build_island_phase3 as p3

PI = math.pi
PROPS_COLLECTION = "11_Reusable_Props"
LITE = False  # set True before build_masters() for the low-poly mobile variant


def _lite_seg(seg):
    return (max(6, seg[0] - 4), max(4, seg[1] - 3)) if LITE else seg


# ------------------------------------------------------------------ master meshes
class Prop:
    """Builds one mesh with several material slots from primitives (origin on the ground)."""

    def __init__(self, name):
        self.name, self.bm, self.slots = name, bmesh.new(), []

    def _tag(self, f0, mat, smooth):
        if mat not in self.slots:
            self.slots.append(mat)
        idx = self.slots.index(mat)
        self.bm.faces.ensure_lookup_table()
        for f in self.bm.faces[f0:]:
            f.material_index, f.smooth = idx, smooth

    def sphere(self, c, scale, mat, seg=(10, 7), smooth=True):
        seg = _lite_seg(seg)
        f0 = len(self.bm.faces)
        m = Matrix.Translation(Vector(c)) @ Matrix.Diagonal(Vector((*scale, 1.0)))
        bmesh.ops.create_uvsphere(self.bm, u_segments=seg[0], v_segments=seg[1], radius=1.0, matrix=m)
        self._tag(f0, mat, smooth)

    def cyl(self, c, r0, r1, h, mat, seg=12, rot=(0, 0, 0), smooth=True):
        seg = max(6, seg - 4) if LITE else seg
        f0 = len(self.bm.faces)
        m = Matrix.Translation(Vector(c)) @ Euler(rot, "XYZ").to_matrix().to_4x4()
        bmesh.ops.create_cone(self.bm, cap_ends=True, cap_tris=False, segments=seg, radius1=r0, radius2=r1, depth=h, matrix=m)
        self._tag(f0, mat, smooth)

    def box(self, c, size, mat, rot=(0, 0, 0)):
        f0 = len(self.bm.faces)
        m = Matrix.Translation(Vector(c)) @ Euler(rot, "XYZ").to_matrix().to_4x4() @ Matrix.Diagonal(Vector((*size, 1.0)))
        bmesh.ops.create_cube(self.bm, size=1.0, matrix=m)
        self._tag(f0, mat, False)

    def make(self, collection, location):
        mesh = bpy.data.meshes.new(self.name)
        self.bm.to_mesh(mesh)
        self.bm.free()
        for slot in self.slots:
            mesh.materials.append(bi.MATS[slot])
        obj = bpy.data.objects.new(self.name, mesh)
        obj.location = Vector(location)
        collection.objects.link(obj)
        return obj


def build_masters(collection):
    """Creates every reusable master once. Returns {name: object}."""
    masters = {}
    x = [-60.0]

    def add(name, builder):
        prop = Prop(name)
        builder(prop)
        masters[name] = prop.make(collection, (x[0], -100.0, 0.0))
        x[0] += 7.0

    rng = random.Random(5)
    # trees: trunk (collider) and leaves (decoration) are separate masters, three variants
    add("COL_Tree_A_Trunk", lambda p: (p.cyl((0, 0, 1.3), 0.34, 0.24, 2.6, "Mat_Trunk", seg=10), p.sphere((0, 0, 0.1), (0.5, 0.5, 0.3), "Mat_Trunk")))
    add("DEC_Tree_A_Leaves", lambda p: [p.sphere(c, (r, r, r * 0.9), "Mat_Leaf", seg=(12, 8)) for c, r in (((0, 0, 3.9), 1.9), ((1.1, 0.4, 3.2), 1.3), ((-1.0, -0.5, 3.3), 1.3), ((0.2, -0.9, 4.6), 1.1))])
    add("COL_Tree_B_Trunk", lambda p: (p.cyl((0, 0, 1.7), 0.3, 0.2, 3.4, "Mat_Trunk", seg=10), p.sphere((0, 0, 0.1), (0.45, 0.45, 0.3), "Mat_Trunk")))
    add("DEC_Tree_B_Leaves", lambda p: [p.sphere(c, (r, r, r * 0.95), "Mat_Leaf_Dark", seg=(12, 8)) for c, r in (((0, 0, 3.9), 1.9), ((0, 0, 5.3), 1.5), ((0.7, 0.4, 6.4), 0.95))])
    add("COL_Tree_C_Trunk", lambda p: (p.cyl((0, 0, 1.0), 0.36, 0.26, 2.0, "Mat_Trunk", seg=10), p.sphere((0, 0, 0.1), (0.55, 0.55, 0.3), "Mat_Trunk")))
    add("DEC_Tree_C_Leaves", lambda p: ([p.sphere((1.3 * math.cos(a), 1.3 * math.sin(a), 3.0 + 0.25 * (k % 2)), (1.35, 1.35, 1.1), "Mat_Leaf_Light", seg=(12, 8)) for k, a in enumerate([PI * 2 * i / 5 for i in range(5)])], p.sphere((0, 0, 3.6), (1.5, 1.5, 1.2), "Mat_Leaf_Light", seg=(12, 8)), p.sphere((0.9, -0.6, 4.1), (0.45, 0.45, 0.45), "Mat_Blossom", seg=(8, 6)), p.sphere((-0.9, 0.6, 4.2), (0.45, 0.45, 0.45), "Mat_Blossom", seg=(8, 6))))

    def bush(flower):
        def build(p):
            p.sphere((0, 0, 0.45), (0.75, 0.75, 0.55), "Mat_Leaf", seg=(12, 8))
            for _ in range(11):
                a, el = rng.uniform(0, PI * 2), rng.uniform(0.2, 1.2)
                p.sphere((0.78 * math.cos(a) * math.cos(el), 0.78 * math.sin(a) * math.cos(el), 0.45 + 0.6 * math.sin(el)), (0.13, 0.13, 0.13), flower, seg=(6, 4))
        return build

    for name, mat in (("Pink", "Mat_Flower_Pink"), ("Yellow", "Mat_Flower_Yellow"), ("Purple", "Mat_Flower_Purple"), ("Red", "Mat_Flower_Red")):
        add(f"DEC_Bush_{name}", bush(mat))

    def bench(p):
        p.box((0, 0, 0.5), (1.8, 0.5, 0.08), "Mat_Wood")
        p.box((0, -0.24, 0.9), (1.8, 0.08, 0.55), "Mat_Wood")
        for sx in (-0.8, 0.8):
            p.box((sx, 0, 0.25), (0.1, 0.5, 0.5), "Mat_Dark")
            p.box((sx, -0.22, 0.72), (0.1, 0.1, 0.9), "Mat_Dark")
            p.box((sx, 0, 0.72), (0.1, 0.5, 0.06), "Mat_Dark")

    add("COL_Bench", bench)

    def lamp(p):
        p.cyl((0, 0, 0.18), 0.26, 0.2, 0.36, "Mat_Dark", seg=10)
        p.cyl((0, 0, 1.9), 0.07, 0.09, 3.2, "Mat_Dark", seg=8)
        p.cyl((0, 0, 3.55), 0.22, 0.12, 0.2, "Mat_Dark", seg=8)
        p.cyl((0, 0, 3.95), 0.2, 0.2, 0.6, "Mat_Lamp_Glow", seg=8)
        p.cyl((0, 0, 4.4), 0.38, 0.05, 0.3, "Mat_Dark", seg=8)
        p.sphere((0, 0, 4.62), (0.08, 0.08, 0.08), "Mat_Dark", seg=(6, 4))

    add("COL_Lamp", lamp)

    def fence(p):
        for px in (-1.2, 0.0, 1.2):
            p.box((px, 0, 0.5), (0.14, 0.14, 1.0), "Mat_Wood_Dark")
        for pz in (0.35, 0.8):
            p.box((0, 0, pz), (2.4, 0.07, 0.1), "Mat_Wood")
        for k in range(5):
            p.box((-0.96 + k * 0.48, 0.05, 0.55), (0.14, 0.05, 0.9), "Mat_Wood")

    add("COL_Fence", fence)

    def signboard(p):
        p.cyl((-1.0, 0, 1.2), 0.07, 0.07, 2.4, "Mat_Wood_Dark", seg=8)
        p.cyl((1.0, 0, 1.2), 0.07, 0.07, 2.4, "Mat_Wood_Dark", seg=8)
        p.box((0, 0, 2.3), (2.8, 0.1, 0.9), "Mat_Wood")
        p.box((1.65, 0, 2.3), (0.6, 0.1, 0.6), "Mat_Wood", rot=(0, PI / 4, 0))

    add("COL_Signboard", signboard)

    def rock(p):
        f0 = len(p.bm.faces)
        bmesh.ops.create_uvsphere(p.bm, u_segments=8, v_segments=6, radius=1.0, matrix=Matrix.Diagonal(Vector((1.0, 0.9, 0.7, 1.0))))
        for v in p.bm.verts:
            v.co *= 1 + rng.uniform(-0.18, 0.18)
            v.co.z = max(v.co.z, -0.05)
        p._tag(f0, "Mat_Rock", False)

    add("COL_Rock", rock)

    def tuft(p):
        for k in range(6):
            a = PI * 2 * k / 6
            p.cyl((0.12 * math.cos(a), 0.12 * math.sin(a), 0.22), 0.07, 0.0, 0.45, "Mat_Grass_Light", seg=5, rot=(0.25 * math.sin(a), -0.25 * math.cos(a), 0), smooth=False)

    add("DEC_GrassTuft", tuft)
    return masters


def link(master, name, coll, loc, yaw=0.0, scale=1.0):
    """A linked duplicate: a new object that shares the master's mesh data."""
    inst = bpy.data.objects.new(name, master.data)
    inst.location = Vector(loc)
    inst.rotation_euler = (0, 0, yaw)
    inst.scale = (scale, scale, scale)
    coll.objects.link(inst)
    return inst


def facing_center_yaw(x, y):
    f = Vector((-x, -y)).normalized()
    return math.atan2(-f.x, f.y)


# ------------------------------------------------------------------ park detail
def torus_h(f, name, c, major, minor, mat, segs=40, rings=8):
    bm = bmesh.new()
    cx, cy, cz = c
    grid = []
    for i in range(segs):
        th = PI * 2 * i / segs
        row = []
        for j in range(rings):
            ph = PI * 2 * j / rings
            r = major + minor * math.cos(ph)
            row.append(bm.verts.new((cx + r * math.cos(th), cy + r * math.sin(th), cz + minor * math.sin(ph))))
        grid.append(row)
    for i in range(segs):
        for j in range(rings):
            bm.faces.new((grid[i][j], grid[(i + 1) % segs][j], grid[(i + 1) % segs][(j + 1) % rings], grid[i][(j + 1) % rings]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return f._emit(name, bm, mat)


def plaza(f):
    """Light round tiles with grout lines: two alternating colours, each one mesh."""
    a, b = bmesh.new(), bmesh.new()
    for ri, (r0, r1) in enumerate(((3.8, 4.8), (4.8, 5.8), (5.8, 6.8), (6.8, 7.8), (7.8, 8.8), (8.8, 9.5))):
        rm = (r0 + r1) / 2
        n = int(PI * 2 * rm / 1.4)
        for k in range(n):
            t0, t1 = PI * 2 * k / n, PI * 2 * (k + 1) / n
            gap = 0.05 / rm
            bm = a if (ri + k) % 2 == 0 else b
            pts = [(r0 + 0.05, t0 + gap), (r1 - 0.05, t0 + gap), (r1 - 0.05, t1 - gap), (r0 + 0.05, t1 - gap)]
            bm.faces.new([bm.verts.new((r * math.cos(t), r * math.sin(t), 0.1)) for r, t in pts])
    for bm in (a, b):
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    f._emit("PlazaTilesLight", a, "Mat_Plaza", smooth=False)
    f._emit("PlazaTilesWarm", b, "Mat_Plaza_Accent", smooth=False)


def fountain(f):
    f.cyl("Fountain_Basin", (0, 0, 0.4), 3.75, 3.55, 0.8, "Mat_Plaza", seg=40)
    torus_h(f, "Fountain_Rim", (0, 0, 0.82), 3.58, 0.22, "Mat_Plaza_Accent")
    f.cyl("Fountain_Water1", (0, 0, 0.78), 3.4, 3.4, 0.06, "Mat_Pool", seg=40)
    f.cyl("Fountain_Column", (0, 0, 1.75), 0.5, 0.66, 1.9, "Mat_Plaza", seg=20)
    f.cyl("Fountain_Bowl", (0, 0, 2.75), 1.2, 1.9, 0.5, "Mat_Plaza", seg=32)
    torus_h(f, "Fountain_BowlRim", (0, 0, 3.0), 1.82, 0.15, "Mat_Plaza_Accent", segs=32)
    f.cyl("Fountain_Water2", (0, 0, 2.96), 1.65, 1.65, 0.05, "Mat_Pool", seg=32)
    f.cyl("Fountain_Spire", (0, 0, 3.55), 0.18, 0.3, 1.1, "Mat_Plaza", seg=12)
    f.sphere("Fountain_Finial", (0, 0, 4.2), (0.42, 0.42, 0.5), "Mat_Plaza_Accent")
    jets = p3.Batch(f, "Fountain_Jets", "Mat_Pool", smooth=True)
    for k in range(6):
        a = PI * 2 * k / 6
        jets.cyl((2.2 * math.cos(a), 2.2 * math.sin(a), 1.15), 0.07, 0.18, 0.7, seg=8)
        jets.sphere((2.2 * math.cos(a), 2.2 * math.sin(a), 1.55), (0.2, 0.2, 0.2), seg=(6, 4))
        jets.sphere((1.9 * math.cos(a), 1.9 * math.sin(a), 1.3), (0.12, 0.12, 0.12), seg=(6, 4))
    jets.cyl((0, 0, 3.4), 0.05, 0.12, 0.5, seg=8)
    jets.emit()


def giant_tree(f):
    f.cyl("GiantTree_TrunkA", (0, 0, 1.7), 1.6, 1.2, 3.4, "Mat_Trunk", seg=14)
    f.cyl("GiantTree_TrunkB", (0, 0, 4.9), 1.2, 0.85, 3.2, "Mat_Trunk", seg=14)
    roots = p3.Batch(f, "GiantTree_Roots", "Mat_Trunk", smooth=True)
    for k in range(6):
        a = PI * 2 * k / 6 + 0.3
        roots.sphere((1.5 * math.cos(a), 1.5 * math.sin(a), 0.3), (0.9, 0.55, 0.4), seg=(8, 6))
    roots.emit()
    br = p3.Batch(f, "GiantTree_Branches", "Mat_Trunk", smooth=True)
    for k in range(5):
        a = PI * 2 * k / 5 + 0.6
        br.cyl((1.1 * math.cos(a), 1.1 * math.sin(a), 7.0), 0.28, 0.18, 2.4, seg=8, rot=(-0.7 * math.sin(a) + 0.0, 0.7 * math.cos(a), 0))
    br.emit()
    a_, b_, c_ = p3.Batch(f, "GiantTree_LeavesA", "Mat_Leaf", smooth=True), p3.Batch(f, "GiantTree_LeavesB", "Mat_Leaf_Dark", smooth=True), p3.Batch(f, "GiantTree_LeavesC", "Mat_Leaf_Light", smooth=True)
    spots = [((0, 0, 9.6), 3.8, a_), ((2.8, 1.2, 8.2), 3.0, b_), ((-2.9, -0.8, 8.4), 3.1, c_), ((0.8, -2.8, 8.0), 2.7, a_), ((-1.2, 2.9, 8.6), 2.9, b_),
             ((0, 0, 11.6), 2.6, c_), ((3.6, -1.8, 9.8), 2.2, a_), ((-3.4, 2.0, 10.0), 2.3, b_)]
    for c, r, b in spots:
        b.sphere(c, (r, r, r * 0.85), seg=(14, 9))
    for b in (a_, b_, c_):
        b.emit()
    # swing rope hanging from a branch and a little wooden signpost
    rope = p3.Batch(f, "GiantTree_Swing", "Mat_Wood_Dark")
    rope.box((2.4, 0.0, 5.0), (0.05, 0.05, 3.0)).box((3.2, 0.0, 5.0), (0.05, 0.05, 3.0)).box((2.8, 0.0, 3.5), (1.0, 0.4, 0.08))
    rope.emit()


def stage(f):
    f.box("Stage_Platform", (0, 0, 0.55), (10, 6, 1.1), "Mat_Wood")
    f.box("Stage_Floor", (0, 0, 1.12), (9.6, 5.6, 0.06), "Mat_Wood_Dark", bevel=0.01)
    st = p3.Batch(f, "Stage_Steps", "Mat_Wood")
    for i in range(3):
        st.box((0, 3.4 + i * 0.45, 0.2 + (2 - i) * 0.0 + 0.18 * (2 - i) * 0.0 + 0.1), (3.2, 0.6, 0.25 + (2 - i) * 0.3))
    st.emit()
    f.box("Stage_BackWall", (0, -2.8, 3.4), (10, 0.4, 4.6), "Mat_Roof_Coral")
    f.box("Stage_CurtainL", (-3.9, -2.4, 3.2), (1.8, 0.35, 4.2), "Mat_Curtain")
    f.box("Stage_CurtainR", (3.9, -2.4, 3.2), (1.8, 0.35, 4.2), "Mat_Curtain")
    f.box("Stage_Roof", (0, 0, 5.8), (10.8, 6.8, 0.4), "Mat_Roof_Blue")
    f.box("Stage_Fascia", (0, 3.45, 5.4), (10.8, 0.2, 0.8), "Mat_Sign_Yellow")
    f.text("Stage_Banner", "EVENT STAGE", (0, 3.58, 5.4), 0.5, "Mat_Dark")
    posts = p3.Batch(f, "Stage_Posts", "Mat_Wood_Dark")
    for x in (-5.0, 5.0):
        posts.cyl((x, 3.0, 3.0), 0.16, 0.16, 5.6, seg=8)
    posts.emit()
    spots = p3.Batch(f, "Stage_Spotlights", "Mat_Dark")
    glow = p3.Batch(f, "Stage_SpotGlow", "Mat_Lamp_Glow", smooth=True)
    for x in (-3.0, 0.0, 3.0):
        spots.cyl((x, 2.6, 5.4), 0.3, 0.2, 0.6, seg=10, rot=(0.7, 0, 0))
        glow.sphere((x, 2.85, 5.2), (0.17, 0.12, 0.17), seg=(6, 4))
    spots.emit()
    glow.emit()
    spk = p3.Batch(f, "Stage_Speakers", "Mat_Dark")
    for x in (-4.4, 4.4):
        spk.box((x, 1.6, 2.0), (0.9, 0.8, 1.6))
    spk.emit()
    f.cyl("Stage_MicStand", (0, 2.0, 1.75), 0.03, 0.03, 1.4, "Mat_Metal", seg=6)


def quest_area(f_board, f_npc):
    f = f_board
    for sx in (-2.1, 2.1):
        f.cyl(f"QuestBoard_Post{int(sx)}", (sx, 0, 1.5), 0.14, 0.14, 3.0, "Mat_Wood_Dark", seg=10)
    f.box("QuestBoard_Board", (0, 0.1, 1.9), (4.2, 0.3, 2.6), "Mat_Wood")
    f.box("QuestBoard_Panel", (0, 0.28, 1.9), (3.8, 0.06, 2.2), "Mat_Chalk")
    f.gable("QuestBoard_Roof", (0, 0, 3.2), 4.6, 1.4, 1.0, "Mat_Roof_Red", ridge="x", overhang=0.3)
    f.box("QuestBoard_Header", (0, 0.32, 3.0), (3.6, 0.08, 0.5), "Mat_Sign_Yellow")
    f.text("QuestBoard_Title", "QUESTS", (0, 0.4, 3.0), 0.4, "Mat_Dark")
    notes = {m: p3.Batch(f, f"QuestBoard_Notes_{m[4:]}", m) for m in ("Mat_White", "Mat_Wall_Yellow", "Mat_Wall_Pink", "Mat_Glass")}
    rng = random.Random(2)
    mats = list(notes)
    for r in range(3):
        for c in range(4):
            notes[mats[(r + c) % 4]].box((-1.4 + c * 0.95, 0.34, 1.0 + r * 0.7), (0.62, 0.02, 0.5), rot=(0, rng.uniform(-0.1, 0.1), 0))
    for b in notes.values():
        b.emit()
    lamp = p3.Batch(f, "QuestBoard_Lantern", "Mat_Lamp_Glow", smooth=True)
    lamp.sphere((0, 0.3, 3.85), (0.16, 0.16, 0.2), seg=(8, 6))
    lamp.emit()
    # NPC guide area: round carpet, ring, two banners and a signpost
    g = f_npc
    g.cyl("NPCArea_Carpet", (0, 0, 0.1), 2.3, 2.3, 0.1, "Mat_Plaza_Accent", seg=32)
    torus_h(g, "NPCArea_Ring", (0, 0, 0.16), 2.3, 0.07, "Mat_Sign_Yellow", segs=40, rings=6)
    for sx in (-2.6, 2.6):
        g.cyl(f"NPCArea_Pole{int(sx)}", (sx, 0, 1.4), 0.06, 0.06, 2.8, "Mat_Wood_Dark", seg=6)
        g.box(f"NPCArea_Flag{int(sx)}", (sx + 0.45, 0, 2.4), (0.9, 0.04, 0.7), "Mat_Roof_Blue")
    g.box("NPCArea_Sign", (0, -2.8, 0.9), (1.8, 0.1, 0.5), "Mat_Wood")
    g.text("NPCArea_SignText", "NPC GUIDE", (0, -2.74, 0.9), 0.22, "Mat_White")


def playground(f):
    f.box("Playground_Floor", (0, 0, 0.07), (12, 10, 0.14), "Mat_Plaza_Accent")
    edge = p3.Batch(f, "Playground_Edge", "Mat_Wood")
    edge.box((0, 5.0, 0.22), (12.4, 0.25, 0.3)).box((0, -5.0, 0.22), (12.4, 0.25, 0.3)).box((6.0, 0, 0.22), (0.25, 10, 0.3)).box((-6.0, 0, 0.22), (0.25, 10, 0.3))
    edge.emit()
    # slide: tower with roof, ladder, curved ramp
    f.box("Playground_SlideTower", (-3.6, -2.2, 1.4), (1.8, 1.8, 2.8), "Mat_Roof_Blue")
    f.cyl("Playground_SlideRoof", (-3.6, -2.2, 3.4), 1.7, 0.1, 1.2, "Mat_Roof_Red", seg=4, rot=(0, 0, PI / 4))
    f.box("Playground_SlideRamp", (-3.6, 0.6, 1.4), (1.1, 4.6, 0.16), "Mat_Roof_Red", rot=(0.6, 0, 0))
    for s in (-0.6, 0.6):
        f.box(f"Playground_SlideRail{int(s * 10)}", (-3.6 + s, 0.6, 1.8), (0.08, 4.6, 0.1), "Mat_Roof_Red", rot=(0.6, 0, 0))
    lad = p3.Batch(f, "Playground_Ladder", "Mat_Wall_Yellow")
    for z in (0.5, 1.1, 1.7, 2.3):
        lad.box((-3.6, -3.18, z), (1.0, 0.08, 0.08))
    lad.box((-4.1, -3.18, 1.4), (0.08, 0.08, 2.8)).box((-3.1, -3.18, 1.4), (0.08, 0.08, 2.8))
    lad.emit()
    # swings: frame, chains, seats
    f.box("Playground_SwingBar", (2.5, 2.2, 2.7), (4.4, 0.14, 0.14), "Mat_Dark")
    legs = p3.Batch(f, "Playground_SwingLegs", "Mat_Dark")
    for x in (0.4, 4.6):
        legs.box((x, 1.85, 1.35), (0.12, 0.12, 2.8), rot=(-0.26, 0, 0)).box((x, 2.55, 1.35), (0.12, 0.12, 2.8), rot=(0.26, 0, 0))
    legs.emit()
    ch = p3.Batch(f, "Playground_SwingChains", "Mat_Rail")
    sw = p3.Batch(f, "Playground_SwingSeats", "Mat_Sign_Yellow")
    sw2 = p3.Batch(f, "Playground_SwingSeatsB", "Mat_Roof_Coral")
    for i, x in enumerate((1.6, 3.4)):
        ch.box((x - 0.3, 2.2, 1.7), (0.03, 0.03, 2.0)).box((x + 0.3, 2.2, 1.7), (0.03, 0.03, 2.0))
        (sw if i == 0 else sw2).box((x, 2.2, 0.75), (0.7, 0.35, 0.1))
    ch.emit()
    sw.emit()
    sw2.emit()
    # seesaw with rounded seats, sandbox with walls
    f.cyl("Playground_SeesawBase", (2.5, -2.6, 0.35), 0.45, 0.25, 0.7, "Mat_Roof_Blue", seg=3)
    f.box("Playground_SeesawPlank", (2.5, -2.6, 0.78), (4.4, 0.5, 0.14), "Mat_Wall_Orange", rot=(0, 0.2, 0))
    seats = p3.Batch(f, "Playground_SeesawSeats", "Mat_Roof_Coral", smooth=True)
    seats.sphere((0.4, -2.6, 0.45), (0.3, 0.3, 0.2), seg=(8, 6)).sphere((4.6, -2.6, 1.15), (0.3, 0.3, 0.2), seg=(8, 6))
    seats.emit()
    f.box("Playground_SandboxWalls", (-3.4, 3.2, 0.3), (3.4, 3.0, 0.5), "Mat_Wood")
    f.box("Playground_Sand", (-3.4, 3.2, 0.5), (3.0, 2.6, 0.12), "Mat_Path")
    toys = p3.Batch(f, "Playground_SandToys", "Mat_Roof_Red", smooth=True)
    toys.cyl((-3.0, 3.2, 0.7), 0.25, 0.2, 0.3, seg=10)
    toys.emit()


def build_park_detail(colls, masters, rng):
    park = colls["01_Central_Park"]
    stale = ("CentralPark_Fountain", "CentralPark_GiantTree", "CentralPark_Stage", "CentralPark_QuestBoard", "CentralPark_NPC_Spot",
             "CentralPark_PlaygroundArea", "CentralPark_Plaza", "CentralPark_PlazaRing")
    for obj in list(park.objects):
        if obj.name.startswith(stale):
            mesh = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            if mesh and mesh.users == 0:
                bpy.data.meshes.remove(mesh)
    base = bi.Frame(park, "CentralPark", (0, 0, 0), 0.0)
    base.cyl("PlazaBase", (0, 0, 0.04), 9.6, 9.6, 0.08, "Mat_Sidewalk", seg=64)
    plaza(base)
    fountain(base)
    giant_tree(bi.Frame(park, "CentralPark", (6.5, 14.5, 0), 0.0))
    stage(bi.Frame(park, "CentralPark", (15.5, -4.0, 0), bi.yaw_for((15.5, -4.0))))
    quest_area(bi.Frame(park, "CentralPark", (4.2, -20.2, 0), PI), bi.Frame(park, "CentralPark", (0, -15.4, 0), 0.0))
    playground(bi.Frame(park, "CentralPark", (-13.0, -9.0, 0), bi.yaw_for((-13.0, -9.0))))

    counts = {}

    def put(master_name, name, loc, yaw=0.0, scale=1.0, coll=park):
        counts[master_name] = counts.get(master_name, 0) + 1
        return link(masters[master_name], f"{name}_{counts[master_name]:03d}", coll, loc, yaw, scale)

    avoid = [((15.5, -4.0), 9.0), ((-13.0, -9.0), 9.5), ((4.2, -20.2), 5.0), ((0.0, -15.4), 4.0), ((6.5, 14.5), 7.0)]

    def clear(x, y, extra=0.0):
        return all(math.hypot(x - ax, y - ay) > r + extra for (ax, ay), r in avoid)

    # benches around the plaza, facing the fountain
    for k in range(8):
        a = math.radians(22.5 + 45 * k)
        x, y = 12.2 * math.cos(a), 12.2 * math.sin(a)
        put("COL_Bench", "COL_Bench", (x, y, 0.04), facing_center_yaw(x, y))
    # benches along the lawn edge and near the stage
    for a in (35, 145, 215, 325):
        x, y = 19.4 * math.cos(math.radians(a)), 19.4 * math.sin(math.radians(a))
        if clear(x, y, 1.5):
            put("COL_Bench", "COL_Bench", (x, y, 0.04), facing_center_yaw(x, y))
    # flower ring around the plaza and along the lawn edge
    flowers = ["DEC_Bush_Pink", "DEC_Bush_Yellow", "DEC_Bush_Purple", "DEC_Bush_Red"]
    for k in range(24):
        a = math.radians(7.5 + 15 * k)
        if min(abs((math.degrees(a) % 90) - 0), abs((math.degrees(a) % 90) - 90)) < 9:
            continue
        x, y = 10.9 * math.cos(a), 10.9 * math.sin(a)
        put(flowers[k % 4], "DEC_Bush", (x, y, 0.05), rng.uniform(0, PI * 2), rng.uniform(0.9, 1.15))
    for k in range(30):
        a = math.radians(6 + 12 * k)
        x, y = 21.2 * math.cos(a), 21.2 * math.sin(a)
        if clear(x, y, 1.0) and min(abs((math.degrees(a) % 90)), abs((math.degrees(a) % 90) - 90)) > 7:
            put(flowers[(k + 1) % 4], "DEC_Bush", (x, y, 0.05), rng.uniform(0, PI * 2), rng.uniform(0.9, 1.2))
    # classic lamps on the lawn, trees inside the park
    for k in range(8):
        a = math.radians(22.5 + 45 * k)
        put("COL_Lamp", "COL_Lamp", (16.9 * math.cos(a), 16.9 * math.sin(a), 0.05), 0.0)
    kinds = [("COL_Tree_A_Trunk", "DEC_Tree_A_Leaves"), ("COL_Tree_B_Trunk", "DEC_Tree_B_Leaves"), ("COL_Tree_C_Trunk", "DEC_Tree_C_Leaves")]
    for k in range(16):
        a = math.radians(11 + 22.5 * k)
        x, y = 19.2 * math.cos(a), 19.2 * math.sin(a)
        if min(abs((math.degrees(a) % 90)), abs((math.degrees(a) % 90) - 90)) < 9 or not clear(x, y, 1.5):
            continue
        trunk, leaves = kinds[k % 3]
        yaw, s = rng.uniform(0, PI * 2), rng.uniform(0.85, 1.15)
        put(trunk, trunk, (x, y, 0.03), yaw, s)
        put(leaves, leaves, (x, y, 0.03), yaw, s)
    # fence around the playground with a gate gap at the front
    pf = bi.Frame(park, "tmp", (-13.0, -9.0, 0), bi.yaw_for((-13.0, -9.0)))
    for side, (cx, cy, rot) in {"N": (0, -5.9, 0), "S": (0, 5.9, 0), "E": (6.9, 0, PI / 2), "W": (-6.9, 0, PI / 2)}.items():
        n, step = (5, 2.4) if rot == 0 else (4, 2.4)
        for i in range(n):
            off = (i - (n - 1) / 2) * step
            lx, ly = (cx + off, cy) if rot == 0 else (cx, cy + off)
            if side == "S" and abs(off) < 1.3:
                continue  # gate
            w = pf.world((lx, ly, 0))
            put("COL_Fence", "COL_Fence", (w.x, w.y, 0.04), bi.yaw_for((-13.0, -9.0)) + rot)
    return counts


# ------------------------------------------------------------------ scatter over the island
class Space:
    """Free-space test for scattering: bounding boxes of everything already built, roads, stream."""

    def __init__(self, layout, colls):
        self.layout = layout
        self.boxes = []
        for pid, cname, prefix, center, depth, _b, rad in bi.PLACES:
            for o in colls[cname].objects:
                if o.type != "MESH" or o.data.users > 1:
                    continue
                xs = [o.location.x + v.co.x for v in o.data.vertices]
                ys = [o.location.y + v.co.y for v in o.data.vertices]
                self.boxes.append((min(xs), min(ys), max(xs), max(ys)))
        self.spokes = [(bi.unit(bi.door_point(p[3], p[4])) * (bi.RING_OUT + 1.0), bi.door_point(p[3], p[4])) for p in bi.PLACES]
        self.spokes = [(Vector(a), Vector(b)) for a, b in self.spokes]
        self.taken = []

    def free(self, x, y, clear=1.0, min_r=33.0, max_r=56.0):
        p = Vector((x, y))
        if not (min_r <= p.length <= max_r):
            return False
        for x0, y0, x1, y1 in self.boxes:
            if x0 - clear <= x <= x1 + clear and y0 - clear <= y <= y1 + clear:
                return False
        if any(bi.seg_dist(p, a, b) < 3.6 + clear for a, b in self.spokes):
            return False
        if self.layout.stream_distance(p) < 4.3 + clear:
            return False
        if any(math.hypot(x - tx, y - ty) < tr + clear for tx, ty, tr in self.taken):
            return False
        return True


def scatter(colls, layout, masters, rng, counts):
    env = colls["00_Environment_Terrain"]
    space = Space(layout, colls)

    def put(master_name, name, loc, yaw=0.0, scale=1.0, coll=env):
        counts[master_name] = counts.get(master_name, 0) + 1
        return link(masters[master_name], f"{name}_{counts[master_name]:03d}", coll, loc, yaw, scale)

    # lamps: both sides of the ring road, then along each road
    for k in range(36):
        a = math.radians(5 + 10 * k)
        x, y = 30.9 * math.cos(a), 30.9 * math.sin(a)
        if any(bi.seg_dist(Vector((x, y)), s, e) < 4.2 for s, e in space.spokes):
            continue
        put("COL_Lamp", "COL_Lamp", (x, y, 0.05), 0.0)
    for k in range(12):
        a = math.radians(15 + 30 * k)
        if min(abs((math.degrees(a) % 90)), abs((math.degrees(a) % 90) - 90)) < 8:
            continue
        put("COL_Lamp", "COL_Lamp", (22.0 * math.cos(a), 22.0 * math.sin(a), 0.05), 0.0)
    for idx, (s, e) in enumerate(space.spokes):
        d = bi.unit(e - s)
        n = Vector((-d.y, d.x))
        length = (e - s).length
        for j in range(int(length // 9)):
            p = s + d * (5.0 + j * 9.0) + n * (3.4 if j % 2 == 0 else -3.4)
            if layout.stream_distance(p) < 5.0:
                continue
            put("COL_Lamp", "COL_Lamp", (p.x, p.y, 0.05), 0.0)
    # signboards at the start of every road, readable from the park
    sign_names = ["COFFEE SHOP", "RESTAURANT", "SUPERMARKET", "SHOPPING MALL", "LIBRARY", "SCHOOL", "HOTEL", "TRAIN STATION", "AIRPORT"]
    for (pid, cname, prefix, center, depth, _b, rad), (s, e), text in zip(bi.PLACES, space.spokes, sign_names):
        d = bi.unit(e - s)
        p = s + d * 2.5 + Vector((-d.y, d.x)) * 3.6
        yaw = facing_center_yaw(p.x, p.y)
        put("COL_Signboard", "COL_Signboard", (p.x, p.y, 0.05), yaw, coll=colls[cname])
        f = bi.Frame(colls[cname], f"Sign_{prefix}", (p.x, p.y, 0), yaw)
        f.text("Text", text, (0, 0.12, 2.3), 0.2 if len(text) > 10 else 0.26, "Mat_Dark")
    # trees (three variants), flower bushes, rocks, grass tufts
    kinds = [("COL_Tree_A_Trunk", "DEC_Tree_A_Leaves"), ("COL_Tree_B_Trunk", "DEC_Tree_B_Leaves"), ("COL_Tree_C_Trunk", "DEC_Tree_C_Leaves")]
    placed = 0
    for _ in range(6000):
        if placed >= 110:
            break
        a, r = rng.uniform(0, PI * 2), math.sqrt(rng.uniform(33.0 ** 2, 56.0 ** 2))
        x, y = r * math.cos(a), r * math.sin(a)
        if not space.free(x, y, clear=1.2):
            continue
        space.taken.append((x, y, 2.6))
        trunk, leaves = kinds[rng.choice((0, 0, 1, 1, 2))]
        z, yaw, s = layout.height(x, y), rng.uniform(0, PI * 2), rng.uniform(0.85, 1.3)
        put(trunk, trunk, (x, y, z), yaw, s)
        put(leaves, leaves, (x, y, z), yaw, s)
        placed += 1
    flowers = ["DEC_Bush_Pink", "DEC_Bush_Yellow", "DEC_Bush_Purple", "DEC_Bush_Red"]
    placed = 0
    for _ in range(6000):
        if placed >= 90:
            break
        a, r = rng.uniform(0, PI * 2), math.sqrt(rng.uniform(32.0 ** 2, 56.0 ** 2))
        x, y = r * math.cos(a), r * math.sin(a)
        if not space.free(x, y, clear=0.5, min_r=32.0):
            continue
        space.taken.append((x, y, 0.9))
        put(flowers[placed % 4], "DEC_Bush", (x, y, layout.height(x, y)), rng.uniform(0, PI * 2), rng.uniform(0.8, 1.25))
        placed += 1
    placed = 0
    for _ in range(4000):
        if placed >= 16:
            break
        p = rng.choice(layout.stream)
        a = rng.uniform(0, PI * 2)
        off = rng.uniform(3.2, 5.0)
        x, y = p.x + off * math.cos(a), p.y + off * math.sin(a)
        if not space.free(x, y, clear=-2.0, min_r=31.5, max_r=56.5):
            continue
        space.taken.append((x, y, 0.8))
        put("COL_Rock", "COL_Rock", (x, y, layout.height(x, y) - 0.05), rng.uniform(0, PI * 2), rng.uniform(0.7, 1.6))
        placed += 1
    placed = 0
    for _ in range(4000):
        if placed >= 90:
            break
        a, r = rng.uniform(0, PI * 2), math.sqrt(rng.uniform(31.5 ** 2, 57.0 ** 2))
        x, y = r * math.cos(a), r * math.sin(a)
        if not space.free(x, y, clear=0.2, min_r=31.5, max_r=57.0):
            continue
        space.taken.append((x, y, 0.5))
        put("DEC_GrassTuft", "DEC_GrassTuft", (x, y, layout.height(x, y)), rng.uniform(0, PI * 2), rng.uniform(0.8, 1.4))
        placed += 1


# ------------------------------------------------------------------ collision naming
COL_PREFIXES = ("Wall", "Tower", "Column", "CanopyColumn", "Abutment", "Plane_Body", "Plane_Wings", "Plane_TailFin", "Plane_TailWing", "Pier", "Trunk", "Basin", "Bowl")
COL_NAMES = {
    "Walls", "WallsLower", "WallsUpper", "WingL", "WingR", "Terminal", "Glass", "Podium", "Plinth", "Platform", "Counter", "ServeCounter", "CheckoutA", "CheckoutB",
    "TrainEngine", "TrainBoiler", "TrainChimney", "Ballast", "AnnexBackWall", "AnnexSideWall", "SlideTower", "SlideRamp", "SwingBar", "JetBridge",
    "JetBridgeBase", "FuelTruckTank", "FuelTruckCab", "ReceptionDesk", "LobbySofa", "Pool", "PoolRim", "Rim", "Column", "Bowl", "Board", "PlazaBase",
    "Floor", "Sleepers", "Rails", "Posts", "Planters", "Pots", "CartCorralPosts", "ProduceStandA", "Chimney", "Columns", "Steps", "Dome", "DomeDrum",
}
GROUND_PREFIXES = ("Island_", "Water_Plane", "Stream", "Waterfall_", "Road_", "Sidewalk_", "CentralPark_Lawn", "CentralPark_Path")
GROUND_NAMES = {"Deck", "Plank", "PatioFloor", "PoolDeck", "Apron", "Runway", "FloorSlab", "AnnexFloor", "PlazaTilesLight", "PlazaTilesWarm", "Playground_Floor",
                "Playground_Sand", "Carpet", "Ring"}


def classify(name):
    """COL_ for solid things, DEC_ for decoration, None for ground that characters walk on."""
    if name.startswith(("COL_", "DEC_")):
        return None
    if name.startswith(GROUND_PREFIXES):
        return None
    tokens = re.split(r"[_.]", name)
    tail = tokens[1:] if len(tokens) > 1 else tokens
    if any(t in GROUND_NAMES or t.startswith("Plank") for t in tail) and not any(t.startswith("Rail") for t in tail):
        return None
    if any(t in COL_NAMES or t.startswith(COL_PREFIXES) for t in tail):
        return "COL_"
    return "DEC_"


def apply_collision_names():
    stats = {"COL_": 0, "DEC_": 0, "ground": 0}
    for obj in bpy.data.objects:
        if obj.type != "MESH" or any(c.name == PROPS_COLLECTION for c in obj.users_collection):
            continue
        prefix = classify(obj.name)
        if prefix:
            obj.name = prefix + obj.name
            stats[prefix] += 1
        elif obj.name.startswith("COL_"):
            stats["COL_"] += 1
        elif obj.name.startswith("DEC_"):
            stats["DEC_"] += 1
        else:
            stats["ground"] += 1
    return stats
