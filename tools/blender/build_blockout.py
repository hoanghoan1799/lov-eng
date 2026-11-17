"""
Stylized base mesh for the Park English chibi characters, boy or girl, in A-pose (v2).

Matches the "Boy / Girl Character: A-pose" turnaround sheet.

Run headless (writes preview PNGs and a GLB next to the output folder):
    /Applications/Blender.app/Contents/MacOS/Blender --background \
        --python tools/blender/build_blockout.py -- boy assets/characters --preview --export
    ... -- girl assets/characters --preview --export

Or paste into Blender (Scripting tab, or the Blender MCP `execute_blender_code` tool) and call:
    build("boy")          # or build("girl"); add preview_dir= / export_path= if wanted

What changed in v2 (fixes for the review notes)
- No z-fighting: every layered part is bigger than the one under it by a clear margin
  (hair 8-10% over the scalp, cuffs and sleeve rings wider than the sleeve, hems wider than the
  leg), and the hair shell blends into the skin through a smooth falloff instead of a cut edge.
- Hair is built from flat, tapered strands (hand-built tubes along Catmull-Rom curves with an
  elliptical cross-section), not stacked spheres.
- Faces: big eyes with two highlights, curved brown brows, blush, a small smile.
- Outfits: soft shoulders, curved kangaroo pocket, drawstrings, a hood behind the nape;
  open pink jacket over a light shirt with white trim; pleated skirt; rounded sneakers with a
  toe cap, laces and a layered sole.
- Materials: roughness 0.7 (matte clay), Shade Smooth on every mesh, and a 3-point studio rig
  (Key, Fill, Rim) used for the preview renders (lights are not exported).

Conventions
- Total height 1.5 m, head 0.5 m (1:3), arms 45 degrees from vertical, legs mirrored across X.
- Every part is its own object; materials are named M_* and are the recolour hooks.
- An Empty named Character_Boy / Character_Girl sits at (0, 0, 0), directly under the feet, and
  every part is parented to it. The character faces -Y (Blender), which is +Z in glTF.
"""

import json
import math
import os
import sys

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector, geometry

# ------------------------------------------------------------------ proportions
HEAD_CENTER = Vector((0, 0, 1.25))
HEAD_SCALE = (0.275, 0.25, 0.25)  # head height 0.5 = 1/3 of the 1.5 m body
SHOULDER_Z = 0.93
SHOULDER_X = 0.22
A_POSE = math.radians(45)  # angle of the arms from vertical
ROUGHNESS = 0.7  # matte, clay-like

# ------------------------------------------------------------------ colours (from the sheet)
PALETTE = {
    "common": {
        "M_Skin": "#FFD0AD",
        "M_SkinShade": "#F0A98A",
        "M_Eye": "#2A1B14",
        "M_EyeShine": "#FFFFFF",
        "M_Cheek": "#FF9AA0",
        "M_Mouth": "#9A3A44",
        "M_Backpack": "#2B2B30",
        "M_Strap": "#1F1F24",
        "M_Sole": "#F6F4EE",
        "M_Outsole": "#CFCBC2",
        "M_Trim": "#FFFFFF",
    },
    "boy": {
        "M_Hair": "#4A3525",
        "M_Brow": "#3A261A",
        "M_Hoodie": "#2E86DE",
        "M_HoodieRib": "#1F5FA8",
        "M_Cord": "#EAF2FF",
        "M_Emblem": "#FFFFFF",
        "M_Pants": "#2C3A47",
        "M_Shoes": "#2E86DE",
    },
    "girl": {
        "M_Hair": "#5A3A28",
        "M_Brow": "#4A2E1F",
        "M_Jacket": "#F78FB3",
        "M_Sleeve": "#F5F6FA",
        "M_Shirt": "#CBD0DC",
        "M_Skirt": "#3C4A6B",
        "M_Sock": "#F5F6FA",
        "M_Shoes": "#F8A5C2",
    },
}


def srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hex_to_linear(hex_color):
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) / 255 for i in (0, 2, 4))
    return (srgb_to_linear(r), srgb_to_linear(g), srgb_to_linear(b), 1.0)


def make_materials(variant):
    mats = {}
    for name, hex_color in {**PALETTE["common"], **PALETTE[variant]}.items():
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = hex_to_linear(hex_color)
            bsdf.inputs["Roughness"].default_value = ROUGHNESS
            if "Metallic" in bsdf.inputs:
                bsdf.inputs["Metallic"].default_value = 0.0
        mat.diffuse_color = hex_to_linear(hex_color)
        mat.roughness = ROUGHNESS
        mats[name] = mat
    return mats


# ------------------------------------------------------------------ maths helpers
def sstep(a, b, x):
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def head_point(az_deg, el_deg, k=1.0):
    """A point on the head ellipsoid scaled by k. az 0 = front (-Y), +az towards +X; el 90 = crown."""
    az, el = math.radians(az_deg), math.radians(el_deg)
    return Vector((
        HEAD_SCALE[0] * k * math.cos(el) * math.sin(az),
        -HEAD_SCALE[1] * k * math.cos(el) * math.cos(az),
        HEAD_CENTER.z + HEAD_SCALE[2] * k * math.sin(el),
    ))


def surf_y(x, z, k=1.0):
    """Y of the front surface of the head at (x, z)."""
    inside = 1 - (x / (HEAD_SCALE[0] * k)) ** 2 - ((z - HEAD_CENTER.z) / (HEAD_SCALE[2] * k)) ** 2
    return -HEAD_SCALE[1] * k * math.sqrt(max(inside, 0.0))


# ------------------------------------------------------------------ builder
class Builder:
    def __init__(self, collection, root, mats):
        self.collection, self.root, self.mats = collection, root, mats

    def _finish(self, name, bm, mat, subsurf=0, bevel=0.0, smooth=True):
        mesh = bpy.data.meshes.new(name)
        bm.to_mesh(mesh)
        bm.free()
        mesh.polygons.foreach_set("use_smooth", [smooth] * len(mesh.polygons))
        mesh.update()
        mesh.materials.append(self.mats[mat])
        obj = bpy.data.objects.new(name, mesh)
        self.collection.objects.link(obj)
        obj.parent = self.root  # object origin stays at (0, 0, 0), under the feet
        if bevel:
            mod = obj.modifiers.new("Bevel", "BEVEL")
            mod.width, mod.segments, mod.limit_method = bevel, 3, "ANGLE"
        if subsurf:
            mod = obj.modifiers.new("Subdivision", "SUBSURF")
            mod.levels = mod.render_levels = subsurf
        return obj

    def blob(self, name, center, scale, mat, rot=(0, 0, 0), segments=(20, 12), warp=None):
        """UV sphere stretched to an ellipsoid. `warp(co)` may move each vertex (hair shell)."""
        bm = bmesh.new()
        m = Matrix.Translation(Vector(center)) @ Euler(rot, "XYZ").to_matrix().to_4x4() @ Matrix.Diagonal(Vector((*scale, 1.0)))
        bmesh.ops.create_uvsphere(bm, u_segments=segments[0], v_segments=segments[1], radius=1.0, matrix=m)
        if warp:
            for v in bm.verts:
                v.co = warp(v.co)
        return self._finish(name, bm, mat)

    def box(self, name, center, size, mat, rot=(0, 0, 0), bevel=0.03, subsurf=1):
        """A cube rounded with Bevel + Subdivision Surface."""
        bm = bmesh.new()
        m = Matrix.Translation(Vector(center)) @ Euler(rot, "XYZ").to_matrix().to_4x4() @ Matrix.Diagonal(Vector((*size, 1.0)))
        bmesh.ops.create_cube(bm, size=1.0, matrix=m)
        return self._finish(name, bm, mat, subsurf=subsurf, bevel=bevel)

    def limb(self, name, p0, p1, r0, r1, mat, segments=16, round_ends=True):
        """A tapered cylinder p0 -> p1. With round_ends a sphere caps each end so joints stay continuous."""
        a, b = Vector(p0), Vector(p1)
        axis = b - a
        quat = Vector((0, 0, 1)).rotation_difference(axis.normalized())
        m = Matrix.Translation((a + b) / 2) @ quat.to_matrix().to_4x4()
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=not round_ends, cap_tris=False, segments=segments, radius1=r0, radius2=r1, depth=axis.length, matrix=m)
        if round_ends:
            for point, radius in ((a, r0), (b, r1)):
                bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=max(6, segments // 2), radius=radius, matrix=Matrix.Translation(point))
        return self._finish(name, bm, mat)

    def torus_h(self, name, center, major_x, major_y, minor, mat, segs=36, rings=8):
        """A horizontal elliptical ring (collars, hems, waistbands)."""
        bm = bmesh.new()
        cx, cy, cz = center
        grid = []
        for i in range(segs):
            th = math.tau * i / segs
            row = []
            for j in range(rings):
                ph = math.tau * j / rings
                rx, ry = major_x + minor * math.cos(ph), major_y + minor * math.cos(ph)
                row.append(bm.verts.new((cx + rx * math.cos(th), cy + ry * math.sin(th), cz + minor * math.sin(ph))))
            grid.append(row)
        for i in range(segs):
            for j in range(rings):
                bm.faces.new((grid[i][j], grid[(i + 1) % segs][j], grid[(i + 1) % segs][(j + 1) % rings], grid[i][(j + 1) % rings]))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        return self._finish(name, bm, mat)

    def strand(self, name, pts, rw, rt, mat, taper=0.9, profile=None, res=8, sides=10):
        """A flat, tapered tube along a smooth curve through `pts`.

        rw is the half width and rt the half thickness of the cross-section. `taper` shrinks it
        towards the tip (a pointed tail); `profile(t)` overrides that with any 0..1 scale curve
        (used for brows and the mouth, which are thin at both ends).
        """
        P = [Vector(p) for p in pts]
        n = len(P)
        samples = []
        for i in range(n - 1):
            p0 = P[i - 1] if i > 0 else P[i]
            p1, p2 = P[i], P[i + 1]
            p3 = P[i + 2] if i + 2 < n else P[i + 1]
            h1, h2 = p1 + (p2 - p0) / 6, p2 - (p3 - p1) / 6
            seg = geometry.interpolate_bezier(p1, h1, h2, p2, res + 1)
            samples += seg if i == 0 else seg[1:]
        count = len(samples)
        bm = bmesh.new()
        rings = []
        for idx, p in enumerate(samples):
            t = idx / (count - 1)
            tangent = (samples[min(idx + 1, count - 1)] - samples[max(idx - 1, 0)]).normalized()
            ref = Vector((0, -1, 0)) if abs(tangent.dot(Vector((0, -1, 0)))) < 0.9 else Vector((1, 0, 0))
            n1 = tangent.cross(ref).normalized()
            n2 = tangent.cross(n1).normalized()
            scale = profile(t) if profile else 1 - taper * t ** 1.6
            scale = max(scale, 0.02)
            ring = []
            for k in range(sides):
                a = math.tau * k / sides
                ring.append(bm.verts.new(p + n1 * (rw * scale * math.cos(a)) + n2 * (rt * scale * math.sin(a))))
            rings.append(ring)
        for i in range(count - 1):
            for k in range(sides):
                bm.faces.new((rings[i][k], rings[i][(k + 1) % sides], rings[i + 1][(k + 1) % sides], rings[i + 1][k]))
        bm.faces.new(rings[0][::-1])
        if taper >= 0.5 and not profile:  # pointed tip
            tip = bm.verts.new(samples[-1] + (samples[-1] - samples[-2]).normalized() * rw * 0.6)
            for k in range(sides):
                bm.faces.new((rings[-1][k], rings[-1][(k + 1) % sides], tip))
        else:
            bm.faces.new(rings[-1])
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        return self._finish(name, bm, mat)

    def hair_shell(self, name, back_z, scale=1.1, mat="M_Hair"):
        """A hair cap that sits clearly outside the scalp and sinks into it along a smooth hairline.

        No vertex is deleted and nothing is coplanar with the skin: a smooth falloff pulls the
        shell inside the head over the face and below the rim, so the skin/hair intersection is
        one clean curve instead of a stair-stepped edge.
        """
        def warp(co):
            gate = sstep(-0.01, -0.07, co.y)  # 1 in front of the head
            q = (co.x / 0.2) ** 2 + ((co.z - 1.2) / 0.2) ** 2
            face = 1 - gate * (1 - sstep(0.55, 1.25, q))
            rim = back_z + (1.28 - back_z) * min(1.0, max(0.0, -co.y / 0.25))
            low = sstep(rim - 0.03, rim + 0.05, co.z)
            k = 0.74 + 0.26 * min(face, low)
            return HEAD_CENTER + (co - HEAD_CENTER) * k
        S = tuple(s * scale for s in HEAD_SCALE)
        return self.blob(name, HEAD_CENTER + Vector((0, 0.012, 0.012)), S, mat, segments=(64, 40), warp=warp)

    def pleated_skirt(self, name, z_top, z_bottom, r_top, r_bottom, mat, pleats=18, per_pleat=4, squash=0.88):
        """A flared skirt lofted from rings whose radius follows a triangle wave: sharp vertical pleats."""
        bm = bmesh.new()
        n = pleats * per_pleat
        rings = []
        for level in range(9):
            u = level / 8
            z = z_top + (z_bottom - z_top) * u
            base = r_top + (r_bottom - r_top) * u
            amp = 0.006 + 0.03 * u
            ring = []
            for i in range(n):
                phase = (i / per_pleat) % 1.0
                tri = abs(phase * 2 - 1) * 2 - 1  # -1..1 triangle wave
                r = base + amp * tri
                a = math.tau * i / n
                ring.append(bm.verts.new((r * math.cos(a), r * math.sin(a) * squash, z)))
            rings.append(ring)
        for lv in range(8):
            for i in range(n):
                bm.faces.new((rings[lv][i], rings[lv][(i + 1) % n], rings[lv + 1][(i + 1) % n], rings[lv + 1][i]))
        bm.faces.new(rings[0][::-1])
        bm.faces.new(rings[-1])
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        return self._finish(name, bm, mat)

    def star(self, name, center, outer, inner, depth, mat):
        """A flat 5-point star plate on the chest (faces -Y)."""
        bm = bmesh.new()
        cx, cy, cz = center
        pts = []
        for k in range(10):
            r = outer if k % 2 == 0 else inner
            a = math.pi / 2 + k * math.pi / 5
            pts.append((cx + r * math.cos(a), cz + r * math.sin(a)))
        near = [bm.verts.new((x, cy, z)) for x, z in pts]
        far = [bm.verts.new((x, cy + depth, z)) for x, z in pts]
        bm.faces.new(near[::-1])
        bm.faces.new(far)
        for k in range(10):
            n = (k + 1) % 10
            bm.faces.new((near[k], near[n], far[n], far[k]))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        return self._finish(name, bm, mat, smooth=False)  # a crisp emblem, not a rounded blob


# ------------------------------------------------------------------ shared parts
def build_face(b, brow_w, brow_t):
    b.blob("Head", HEAD_CENTER, HEAD_SCALE, "M_Skin", segments=(40, 24))
    b.limb("Neck", (0, 0, 0.95), (0, 0, 1.04), 0.065, 0.06, "M_Skin", segments=12, round_ends=False)
    for side, sx in (("L", 1), ("R", -1)):
        b.blob(f"Ear.{side}", (0.27 * sx, 0.01, 1.24), (0.04, 0.035, 0.055), "M_Skin", segments=(12, 8))
        # big round eye with a large and a small highlight
        b.blob(f"Eye.{side}", (0.095 * sx, -0.232, 1.25), (0.047, 0.025, 0.064), "M_Eye", segments=(16, 12))
        b.blob(f"EyeShine.{side}", (0.081 * sx, -0.251, 1.275), (0.016, 0.01, 0.019), "M_EyeShine", segments=(10, 8))
        b.blob(f"EyeShine2.{side}", (0.112 * sx, -0.25, 1.228), (0.008, 0.007, 0.009), "M_EyeShine", segments=(8, 6))
        # curved brow, thin at both ends
        brow = []
        for u in (0.0, 0.33, 0.66, 1.0):
            x = (0.052 + 0.092 * u) * sx
            z = 1.322 + 0.017 * math.sin(math.pi * u) - 0.006 * u
            brow.append((x, surf_y(x, z) - 0.005, z))
        b.strand(f"Brow.{side}", brow, brow_w, brow_t, "M_Brow", profile=lambda t: 0.45 + 0.55 * math.sin(math.pi * t) ** 0.6, res=6, sides=8)
        # soft blush
        b.blob(f"Blush.{side}", (0.165 * sx, surf_y(0.165, 1.185), 1.185), (0.05, 0.011, 0.032), "M_Cheek", rot=(0, 0, 0.3 * sx), segments=(14, 8))
    b.blob("Nose", (0, surf_y(0, 1.2) - 0.008, 1.2), (0.017, 0.013, 0.013), "M_SkinShade", segments=(10, 8))
    # small closed smile: low in the middle, corners lifted
    smile = []
    for u in (0.0, 0.25, 0.5, 0.75, 1.0):
        x = (u - 0.5) * 0.09
        z = 1.172 - 0.013 * (1 - (x / 0.045) ** 2)
        smile.append((x, surf_y(x, z) - 0.004, z))
    b.strand("Mouth", smile, 0.0065, 0.0042, "M_Mouth", profile=lambda t: 0.3 + 0.7 * math.sin(math.pi * t) ** 0.5, res=6, sides=8)


def build_shoes(b, lx, upper, shoe_toe="M_Sole", wscale=1.0):
    """Rounded sneakers: upper, toe cap, heel, tongue, white laces, midsole and outsole as separate layers.

    wscale narrows the shoe across X so that closely spaced feet (the girl) do not fuse into one plate.
    """
    w = wscale
    for side, sx in (("L", 1), ("R", -1)):
        x = lx * sx
        b.blob(f"Shoe.{side}", (x, -0.035, 0.092), (0.082 * w, 0.16, 0.074), upper, segments=(20, 14))
        b.blob(f"ShoeToe.{side}", (x, -0.135, 0.07), (0.075 * w, 0.075, 0.052), shoe_toe, segments=(16, 10))
        b.blob(f"ShoeHeel.{side}", (x, 0.06, 0.092), (0.07 * w, 0.055, 0.06), upper, segments=(14, 10))
        b.blob(f"ShoeTongue.{side}", (x, -0.07, 0.15), (0.04 * w, 0.05, 0.035), shoe_toe, rot=(0.5, 0, 0), segments=(12, 8))
        for i, y in enumerate((-0.085, -0.055, -0.025)):  # three white laces across the instep
            b.limb(f"ShoeLace{i}.{side}", (x - 0.042 * w, y, 0.152 - i * 0.003), (x + 0.042 * w, y, 0.152 - i * 0.003), 0.0075, 0.0075, "M_Trim", segments=8)
        b.box(f"ShoeSole.{side}", (x, -0.04, 0.032), (0.165 * w, 0.325, 0.024), "M_Sole", bevel=0.01)
        b.box(f"ShoeOutsole.{side}", (x, -0.04, 0.01), (0.17 * w, 0.33, 0.02), "M_Outsole", bevel=0.008)


def build_backpack(b):
    b.box("Backpack", (0, 0.19, 0.8), (0.3, 0.14, 0.38), "M_Backpack", bevel=0.035)
    b.box("BackpackPocket", (0, 0.27, 0.7), (0.2, 0.04, 0.14), "M_Strap", bevel=0.015)
    for side, sx in (("L", 1), ("R", -1)):
        b.box(f"BackpackStrap.{side}", (0.1 * sx, -0.1, 0.84), (0.05, 0.05, 0.26), "M_Strap", bevel=0.012, subsurf=1)


def arm_points(sx):
    """Shoulder, elbow, wrist, hand centre and direction for the 45 degree A-pose, mirrored by sx."""
    d = Vector((math.sin(A_POSE) * sx, 0, -math.cos(A_POSE)))
    shoulder = Vector((SHOULDER_X * sx, 0, SHOULDER_Z))
    elbow = shoulder + d * 0.2
    wrist = elbow + d * 0.19
    hand = wrist + d * 0.06
    return shoulder, elbow, wrist, hand, d


def build_hands(b, side, sx, hand, d, scale=1.0):
    b.blob(f"Hand.{side}", hand, (0.05 * scale, 0.04 * scale, 0.06 * scale), "M_Skin", rot=(0, -A_POSE * sx, 0), segments=(14, 10))
    b.blob(f"Thumb.{side}", hand + Vector((0.0, -0.04, 0.01)) + d * 0.01, (0.02 * scale, 0.02 * scale, 0.035 * scale), "M_Skin", segments=(10, 8))


# ------------------------------------------------------------------ boy
def build_boy(b):
    build_face(b, brow_w=0.016, brow_t=0.007)

    # ---- messy spiky hair: a shell plus flat tapered locks (no stacked spheres)
    b.hair_shell("Hair_Shell", back_z=1.08, scale=1.1)
    K = 1.085
    bangs = [  # sweep across the forehead to the character's right
        ([(30, 70), (12, 58), (-8, 46), (-30, 31)], 0.03),
        ([(16, 74), (0, 62), (-20, 50), (-42, 34)], 0.032),
        ([(44, 62), (26, 52), (6, 42), (-14, 32)], 0.028),
        ([(-4, 78), (-22, 66), (-44, 52), (-64, 36)], 0.03),
    ]
    for i, (pts, rw) in enumerate(bangs):
        b.strand(f"Hair_Bang{i}", [head_point(az, el, K) for az, el in pts], rw, 0.012, "M_Hair", taper=0.92)
    for side, sx in (("L", 1), ("R", -1)):  # side locks in front of the ears
        b.strand(f"Hair_Side.{side}", [head_point(sx * az, el, K) for az, el in [(70, 42), (79, 26), (85, 10)]], 0.026, 0.012, "M_Hair", taper=0.9)
        b.strand(f"Hair_Nape.{side}", [head_point(sx * az, el, K) for az, el in [(120, 40), (135, 18), (146, -2)]], 0.03, 0.012, "M_Hair", taper=0.9)
    for i, (az, el, length, tx, ty) in enumerate([  # spiky tufts around the crown
        (-35, 78, 0.12, -0.3, 0.0), (-10, 84, 0.14, 0.0, -0.15), (15, 82, 0.13, 0.25, -0.1), (40, 74, 0.11, 0.35, 0.0),
        (-55, 66, 0.10, -0.4, 0.0), (70, 60, 0.09, 0.3, 0.1), (180, 70, 0.12, 0.0, 0.3), (150, 62, 0.10, 0.2, 0.2), (-150, 62, 0.10, -0.2, 0.2),
    ]):
        start = head_point(az, el, 1.05)
        direction = Vector((math.sin(math.radians(az)) * 0.4 + tx, -math.cos(math.radians(az)) * 0.3 + ty, 1.0)).normalized()
        mid = start + direction * length * 0.5 + Vector((tx * 0.03, ty * 0.03, 0))
        end = start + direction * length + Vector((tx * 0.06, ty * 0.06, -0.01))
        b.strand(f"Hair_Spike{i}", [start, mid, end], 0.034, 0.016, "M_Hair", taper=0.95, res=6)

    # ---- hoodie: soft shoulder yoke, barrel torso, curved kangaroo pocket
    b.box("Torso", (0, 0, 0.8), (0.42, 0.27, 0.36), "M_Hoodie", bevel=0.09)
    b.blob("ShoulderYoke", (0, 0, 0.9), (0.295, 0.16, 0.105), "M_Hoodie", segments=(28, 16))
    b.blob("HoodiePocket", (0, -0.112, 0.69), (0.165, 0.052, 0.072), "M_Hoodie", segments=(24, 12))
    b.box("HoodieHem", (0, 0, 0.62), (0.43, 0.28, 0.05), "M_HoodieRib", bevel=0.02)
    b.star("StarFront", (0, -0.1415, 0.82), 0.07, 0.03, 0.012, "M_Emblem")
    # collar ring, hood hanging behind the nape, drawstrings with small tips
    b.torus_h("HoodCollar", (0, 0.015, 0.985), 0.13, 0.105, 0.03, "M_Hoodie")
    b.blob("HoodBack", (0, 0.125, 0.93), (0.19, 0.1, 0.11), "M_Hoodie", segments=(22, 14))
    b.blob("HoodDroop", (0, 0.15, 0.85), (0.15, 0.07, 0.1), "M_Hoodie", segments=(20, 12))
    for side, sx in (("L", 1), ("R", -1)):
        cord = [(0.055 * sx, -0.118, 0.975), (0.088 * sx, -0.148, 0.9), (0.104 * sx, -0.152, 0.8), (0.1 * sx, -0.148, 0.71)]
        b.strand(f"Cord.{side}", cord, 0.008, 0.008, "M_Cord", taper=0.0, profile=lambda t: 1.0, res=6, sides=8)
        b.blob(f"CordTip.{side}", (0.1 * sx, -0.148, 0.695), (0.011, 0.011, 0.022), "M_Cord", segments=(8, 6))
    build_backpack(b)

    # ---- arms: puffy sleeves, dark-blue rolled cuffs that fully cover the wrist, hands
    for side, sx in (("L", 1), ("R", -1)):
        shoulder, elbow, wrist, hand, d = arm_points(sx)
        b.limb(f"SleeveUpper.{side}", shoulder, elbow, 0.085, 0.078, "M_Hoodie")
        b.limb(f"SleeveLower.{side}", elbow, wrist - d * 0.02, 0.078, 0.07, "M_Hoodie")
        b.limb(f"Cuff.{side}", wrist - d * 0.05, wrist + d * 0.02, 0.083, 0.081, "M_HoodieRib", segments=18, round_ends=False)
        build_hands(b, side, sx, hand, d)

    # ---- cargo pants: two separate straight legs with a gap, wide hems over the shoes
    lx = 0.115
    b.box("PantsHip", (0, 0, 0.64), (0.4, 0.24, 0.12), "M_Pants", bevel=0.045)
    for side, sx in (("L", 1), ("R", -1)):
        x = lx * sx
        b.limb(f"PantsThigh.{side}", (x, 0, 0.62), (x, 0, 0.36), 0.096, 0.094, "M_Pants")
        b.limb(f"PantsShin.{side}", (x, 0, 0.36), (x, 0, 0.115), 0.094, 0.1, "M_Pants")
        b.limb(f"PantsHem.{side}", (x, 0, 0.145), (x, 0, 0.1), 0.108, 0.112, "M_Pants", segments=18, round_ends=False)
        b.blob(f"PantsPocket.{side}", (x + 0.088 * sx, -0.004, 0.45), (0.034, 0.072, 0.088), "M_Pants", segments=(14, 10))
    build_shoes(b, lx, "M_Shoes")


# ------------------------------------------------------------------ girl
def build_girl(b):
    build_face(b, brow_w=0.012, brow_t=0.005)

    # ---- long hair: shell, curved bangs, side locks, tapered back locks
    b.hair_shell("Hair_Shell", back_z=0.98, scale=1.1)
    K = 1.085
    for sx_name, sx in (("L", 1), ("R", -1)):
        for i, (pts, rw) in enumerate([
            ([(4, 66), (22, 52), (44, 34), (60, 16)], 0.026),
            ([(2, 60), (16, 46), (34, 30), (48, 14)], 0.024),
            ([(8, 70), (30, 56), (54, 40), (72, 22)], 0.03),
        ]):
            b.strand(f"Hair_Bang{i}.{sx_name}", [head_point(sx * az, el, K) for az, el in pts], rw, 0.012, "M_Hair", taper=0.88)
        b.strand(f"Hair_Side.{sx_name}", [head_point(sx * az, el, K) for az, el in [(70, 38), (80, 22), (86, 4), (88, -16)]], 0.03, 0.013, "M_Hair", taper=0.92)
    back = [  # (points, half width): wavy locks that taper to a point
        ([(0, 0.2, 1.42), (0.004, 0.27, 1.2), (0.012, 0.3, 0.95), (-0.01, 0.31, 0.72), (0.014, 0.29, 0.5)], 0.2),
        ([(0.13, 0.2, 1.38), (0.17, 0.25, 1.15), (0.2, 0.27, 0.92), (0.19, 0.27, 0.7), (0.17, 0.26, 0.52)], 0.11),
        ([(-0.13, 0.2, 1.38), (-0.17, 0.25, 1.15), (-0.2, 0.27, 0.92), (-0.19, 0.27, 0.7), (-0.17, 0.26, 0.55)], 0.11),
        ([(0.2, 0.14, 1.32), (0.25, 0.2, 1.12), (0.265, 0.24, 0.98)], 0.075),
        ([(-0.2, 0.14, 1.32), (-0.25, 0.2, 1.12), (-0.265, 0.24, 0.98)], 0.075),
    ]
    for i, (pts, rw) in enumerate(back):
        b.strand(f"Hair_Back{i}", pts, rw, 0.05, "M_Hair", taper=0.95, res=8)

    # ---- inner shirt, pink jacket that opens at the front, white trim
    b.box("ShirtTorso", (0, 0, 0.8), (0.34, 0.22, 0.32), "M_Shirt", bevel=0.07)
    b.blob("ShirtPanel", (0, -0.112, 0.8), (0.095, 0.062, 0.165), "M_Shirt", segments=(20, 14))
    b.box("JacketBack", (0, 0.015, 0.8), (0.4, 0.24, 0.33), "M_Jacket", bevel=0.08)
    for side, sx in (("L", 1), ("R", -1)):
        b.blob(f"JacketFlap.{side}", (0.118 * sx, -0.108, 0.8), (0.105, 0.05, 0.172), "M_Jacket", rot=(0, 0, 0.1 * sx), segments=(20, 14))
        b.blob(f"JacketTrim.{side}", (0.034 * sx, -0.145, 0.8), (0.011, 0.018, 0.165), "M_Trim", segments=(8, 10))
    b.torus_h("JacketHem", (0, 0.005, 0.642), 0.205, 0.135, 0.02, "M_Trim")
    b.torus_h("JacketCollar", (0, 0.01, 0.985), 0.12, 0.1, 0.032, "M_Jacket")

    # ---- arms: pink sleeve -> wide pink cuff -> wider white trim ring -> white puffy forearm
    for side, sx in (("L", 1), ("R", -1)):
        shoulder, elbow, wrist, hand, d = arm_points(sx)
        b.limb(f"SleeveUpper.{side}", shoulder, elbow + d * 0.02, 0.078, 0.072, "M_Jacket")
        b.limb(f"SleeveBulge.{side}", elbow - d * 0.01, elbow + d * 0.05, 0.088, 0.085, "M_Jacket")
        b.limb(f"SleeveRing.{side}", elbow + d * 0.04, elbow + d * 0.065, 0.094, 0.094, "M_Trim", segments=20, round_ends=False)
        b.limb(f"SleeveLower.{side}", elbow + d * 0.045, wrist - d * 0.02, 0.06, 0.055, "M_Sleeve")
        b.limb(f"WristCuff.{side}", wrist - d * 0.035, wrist + d * 0.015, 0.066, 0.064, "M_Trim", segments=18, round_ends=False)
        build_hands(b, side, sx, hand, d, scale=0.92)
    build_backpack(b)

    # ---- pleated skirt, belt, bare legs, socks with a fold
    b.pleated_skirt("Skirt", 0.655, 0.43, 0.165, 0.275, "M_Skirt")
    b.torus_h("SkirtBelt", (0, 0, 0.66), 0.165, 0.145, 0.013, "M_Skirt")
    lx = 0.075
    for side, sx in (("L", 1), ("R", -1)):
        x = lx * sx
        b.limb(f"LegThigh.{side}", (x, 0, 0.55), (x, 0, 0.32), 0.07, 0.058, "M_Skin")
        b.limb(f"LegShin.{side}", (x, 0, 0.32), (x, 0, 0.17), 0.058, 0.052, "M_Skin")
        b.limb(f"Sock.{side}", (x, 0, 0.215), (x, 0, 0.1), 0.063, 0.06, "M_Sock", segments=18, round_ends=False)
        b.limb(f"SockRing.{side}", (x, 0, 0.222), (x, 0, 0.2), 0.07, 0.07, "M_Sock", segments=18, round_ends=False)
    build_shoes(b, lx, "M_Shoes", wscale=0.78)


# ------------------------------------------------------------------ checks, lighting, preview, export
def world_bounds(collection):
    deps = bpy.context.evaluated_depsgraph_get()
    lo, hi = Vector((1e9, 1e9, 1e9)), Vector((-1e9, -1e9, -1e9))
    for obj in collection.objects:
        if obj.type != "MESH":
            continue
        ev = obj.evaluated_get(deps)
        for corner in ev.bound_box:
            p = ev.matrix_world @ Vector(corner)
            lo = Vector((min(lo[i], p[i]) for i in range(3)))
            hi = Vector((max(hi[i], p[i]) for i in range(3)))
    return lo, hi


def setup_studio_lights(scene, target=(0, 0, 0.78)):
    """Classic 3-point studio rig. Preview only: lights are not exported to the GLB."""
    world = bpy.data.worlds.new("StudioWorld")
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    if background:
        background.inputs["Color"].default_value = (0.84, 0.82, 0.97, 1.0)
        background.inputs["Strength"].default_value = 0.9
    scene.world = world
    scene.view_settings.view_transform = "Standard"  # keeps the palette colours true
    rig = {
        "Key": ((2.6, -3.4, 3.2), 260, 2.6, (1.0, 0.96, 0.9)),
        "Fill": ((-3.2, -2.6, 1.4), 90, 3.2, (0.85, 0.9, 1.0)),
        "Rim": ((-1.6, 3.4, 2.6), 220, 1.8, (1.0, 1.0, 1.0)),
    }
    for name, (loc, energy, size, color) in rig.items():
        data = bpy.data.lights.new(name, "AREA")
        data.energy, data.size, data.color = energy, size, color
        light = bpy.data.objects.new(name, data)
        light.location = loc
        light.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        bpy.context.collection.objects.link(light)


def use_eevee(scene):
    for engine in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            scene.render.engine = engine
            return True
        except TypeError:
            continue
    return False


def setup_preview(scene):
    scene.render.resolution_x, scene.render.resolution_y = 700, 860
    setup_studio_lights(scene)
    if not use_eevee(scene):
        scene.render.engine = "BLENDER_WORKBENCH"
        sh = scene.display.shading
        sh.light, sh.color_type, sh.show_object_outline = "STUDIO", "MATERIAL", True
        scene.display.render_aa = "8"
    cam = bpy.data.objects.new("PreviewCam", bpy.data.cameras.new("PreviewCam"))
    bpy.context.collection.objects.link(cam)
    scene.camera = cam
    return cam


def render_previews(out_dir, variant):
    scene = bpy.context.scene
    cam = setup_preview(scene)
    for name, loc, ortho in (
        ("front", (0, -6, 0.78), True), ("side", (6, 0, 0.78), True), ("back", (0, 6, 0.78), True),
        ("three_quarter", (3.6, -4.6, 1.2), False),
    ):
        cam.location = loc
        cam.data.type = "ORTHO" if ortho else "PERSP"
        cam.data.ortho_scale = 2.0
        cam.data.lens = 65
        cam.rotation_euler = (Vector((0, 0, 0.78)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = os.path.join(out_dir, f"blockout_{variant}_{name}.png")
        bpy.ops.render.render(write_still=True)
    return scene.render.engine


def create_character(variant="boy", reset_scene=True):
    """Builds the character in the current Blender session. Returns (collection, root)."""
    assert variant in ("boy", "girl")
    if reset_scene:
        bpy.ops.wm.read_factory_settings(use_empty=True)
    name = f"Character_{variant.capitalize()}"
    collection = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(collection)
    root = bpy.data.objects.new(name, None)  # Empty at (0, 0, 0): under the soles, character pivot
    root.empty_display_type = "PLAIN_AXES"
    collection.objects.link(root)

    mats = make_materials(variant)
    builder = Builder(collection, root, mats)
    (build_boy if variant == "boy" else build_girl)(builder)
    return collection, root


def build(variant="boy", preview_dir=None, export_path=None):
    collection, root = create_character(variant)
    lo, hi = world_bounds(collection)
    meshes = [o for o in collection.objects if o.type == "MESH"]
    report = {
        "variant": variant,
        "parts": len(meshes),
        "materials": len(bpy.data.materials),
        "roughness": sorted({round(m.roughness, 2) for m in bpy.data.materials}),
        "all_smooth": all(all(p.use_smooth for p in m.data.polygons) for m in meshes if m.name != "StarFront"),
        "root_location": tuple(round(v, 4) for v in root.location),
        "feet_z": round(lo.z, 4),
        "height_crown": round(HEAD_CENTER.z + HEAD_SCALE[2], 3),
        "head_to_body": round((2 * HEAD_SCALE[2]) / (HEAD_CENTER.z + HEAD_SCALE[2]), 3),
        "x_symmetry_error": round(abs(lo.x + hi.x), 4),
        "arm_angle_deg": round(math.degrees(A_POSE)),
    }
    if preview_dir:
        os.makedirs(preview_dir, exist_ok=True)
        report["render_engine"] = render_previews(preview_dir, variant)
    if export_path:
        os.makedirs(os.path.dirname(os.path.abspath(export_path)), exist_ok=True)
        bpy.ops.object.select_all(action="DESELECT")
        bpy.ops.export_scene.gltf(filepath=export_path, export_format="GLB", export_apply=True, export_yup=True, export_materials="EXPORT")
        report["exported"] = export_path
    return report


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    variant = args[0] if args else "boy"
    out_dir = os.path.abspath(args[1]) if len(args) > 1 and not args[1].startswith("--") else os.path.abspath("assets/characters")
    print(json.dumps(build(
        variant,
        preview_dir=out_dir if "--preview" in args else None,
        export_path=os.path.join(out_dir, f"blockout_{variant}.glb") if "--export" in args else None,
    ), indent=2))
