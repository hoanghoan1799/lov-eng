"""
Game-ready export of the rigged characters: merged meshes and one shared palette texture.

Run headless:
    /Applications/Blender.app/Contents/MacOS/Blender --background \
        --python tools/blender/build_game.py -- boy assets/characters --preview
    ... -- girl assets/characters --preview

Output (in the folder you pass)
    <variant>_game.glb            skinned, animated, 7 meshes, ONE material, ONE 256x8 texture
    <variant>_game.palette.json   colour cell of every recolourable part (see below)
    game_<variant>_*.png          preview renders (with --preview)

Why this layout
- Draw calls: the rigged characters had 85-87 separate meshes. Here every part is merged into
  one of 7 slot meshes (Body, Face, Hair, Top, Bottom, Shoes, Backpack). All slots share one
  material, so a character costs 7 draw calls, and the game can batch identical materials.
- Customisation: slots stay separate so the game can hide or swap them (a new hairstyle is a
  new Hair mesh; a skirt is a new Bottom mesh).
- Recolouring: instead of one material per colour, every vertex is UV-mapped onto one cell of
  a small palette texture. To recolour a part, repaint that cell (see the .palette.json):
  the texture is 32 cells of 8x8 px; cell i spans x = i*8 .. i*8+7. Keep NEAREST filtering and no
  mipmaps (the exported sampler already requests nearest).
- Skinning is rigid and written straight into vertex groups, one bone per source part, so the
  16-bone rig and the 9 animations behave exactly as before.
"""

import json
import os
import sys

import bmesh
import bpy

try:
    HERE = os.path.dirname(os.path.abspath(__file__))
except NameError:  # pasted into Blender: set this to the folder with the other scripts
    HERE = os.path.abspath("tools/blender")
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import build_blockout as bo  # noqa: E402
import build_rigged as rg  # noqa: E402

CELLS = 32  # palette cells
CELL_PX = 8  # pixels per cell side

# ------------------------------------------------------------------ slots
FACE = {"Eye", "EyeShine", "EyeShine2", "Brow", "Blush", "Nose", "Mouth"}
TOP = {"Torso", "ShoulderYoke", "HoodiePocket", "HoodieHem", "StarFront", "HoodCollar", "HoodBack", "HoodDroop",
       "Cord", "CordTip", "ShirtTorso", "ShirtPanel", "JacketBack", "JacketFlap", "JacketTrim", "JacketHem",
       "JacketCollar", "SleeveUpper", "SleeveBulge", "SleeveRing", "SleeveLower", "Cuff", "WristCuff"}
BOTTOM = {"PantsHip", "PantsThigh", "PantsPocket", "PantsShin", "PantsHem", "Skirt", "SkirtBelt", "Sock", "SockRing"}
BODY = {"Head", "Neck", "Ear", "Hand", "Thumb", "LegThigh", "LegShin"}
SLOT_ORDER = ["Body", "Face", "Hair", "Top", "Bottom", "Shoes", "Backpack"]


def slot_for(part_name):
    base = part_name.partition(".")[0]
    if base.startswith("Hair"):
        return "Hair"
    if base.startswith("Backpack"):
        return "Backpack"
    if base.startswith("Shoe"):
        return "Shoes"
    for slot, names in (("Face", FACE), ("Top", TOP), ("Bottom", BOTTOM), ("Body", BODY)):
        if base in names:
            return slot
    raise KeyError(f"part {part_name!r} has no slot")


# ------------------------------------------------------------------ palette
def make_palette(variant, used):
    """Builds the palette image and the single shared material. Returns (material, {name: cell})."""
    colors = {**bo.PALETTE["common"], **bo.PALETTE[variant]}
    order = [name for name in colors if name in used]
    assert len(order) <= CELLS, "palette is full"
    width, height = CELLS * CELL_PX, CELL_PX
    image = bpy.data.images.new(f"Palette_{variant}", width, height, alpha=False)
    pixels = []
    for _ in range(height):
        for x in range(width):
            cell = x // CELL_PX
            if cell < len(order):
                h = colors[order[cell]].lstrip("#")
                r, g, b = (int(h[i : i + 2], 16) / 255 for i in (0, 2, 4))
            else:
                r, g, b = 1.0, 0.0, 1.0  # unused cells are magenta, so a stray UV is obvious
            pixels += [r, g, b, 1.0]
    image.pixels = pixels
    image.file_format = "PNG"
    image.pack()

    mat = bpy.data.materials.new("M_Palette")
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = image
    tex.interpolation = "Closest"  # exported as a NEAREST sampler: no colour bleeding between cells
    links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = bo.ROUGHNESS
    if "Metallic" in bsdf.inputs:
        bsdf.inputs["Metallic"].default_value = 0.0
    mat.roughness = bo.ROUGHNESS
    cells = {name: i for i, name in enumerate(order)}
    mat["palette_cells"] = json.dumps(cells)  # exported as glTF extras
    mat["palette_cell_px"] = CELL_PX
    return mat, cells


# ------------------------------------------------------------------ merge
def merge_into_slots(collection, rig, variant, material, cells):
    """Merges every part into its slot mesh, writes palette UVs and rigid bone weights."""
    deps = bpy.context.evaluated_depsgraph_get()
    parts = [o for o in collection.objects if o.type == "MESH"]
    bone_names = [b.name for b in rig.pose.bones]
    groups = {slot: [] for slot in SLOT_ORDER}
    for obj in parts:
        groups[slot_for(obj.name)].append(obj)

    merged = {}
    for slot in SLOT_ORDER:
        objs = groups[slot]
        if not objs:
            continue
        bm = bmesh.new()
        ranges = []
        for obj in objs:
            # evaluated mesh = Bevel + Subdivision already applied
            mesh = bpy.data.meshes.new_from_object(obj.evaluated_get(deps), depsgraph=deps)
            v0, f0 = len(bm.verts), len(bm.faces)
            bm.from_mesh(mesh)
            bm.verts.ensure_lookup_table()
            bm.faces.ensure_lookup_table()
            assert len(bm.verts) == v0 + len(mesh.vertices), "from_mesh must append"
            ranges.append((obj, v0, len(bm.verts), f0, len(bm.faces)))
            bpy.data.meshes.remove(mesh)
        uv_layer = bm.loops.layers.uv.verify()
        weights = bm.verts.layers.deform.verify()
        for obj, v0, v1, f0, f1 in ranges:
            bone = rg.bone_for(obj.name)
            assert bone, f"{obj.name} has no bone"
            group_index = bone_names.index(bone)
            u = (cells[obj.data.materials[0].name] + 0.5) / CELLS
            for v in bm.verts[v0:v1]:
                v[weights][group_index] = 1.0
            for face in bm.faces[f0:f1]:
                for loop in face.loops:
                    loop[uv_layer].uv = (u, 0.5)
        mesh = bpy.data.meshes.new(slot)
        bm.to_mesh(mesh)
        bm.free()
        mesh.materials.append(material)
        out = bpy.data.objects.new(slot, mesh)
        collection.objects.link(out)
        for name in bone_names:  # same order as the deform indices above
            out.vertex_groups.new(name=name)
        modifier = out.modifiers.new("Armature", "ARMATURE")
        modifier.object = rig
        out.parent = rig
        merged[slot] = out

    originals = {o.data for o in parts}
    old_materials = [m for m in bpy.data.materials if m is not material]
    for obj in parts:
        bpy.data.objects.remove(obj, do_unlink=True)
    for mesh in originals:
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)
    for mat in old_materials:
        if mat.users == 0:
            bpy.data.materials.remove(mat)
    for slot, obj in merged.items():  # the originals are gone, so the clean names are free again
        obj.name = slot
        obj.data.name = slot
    return merged


def build(variant="boy", out_dir="assets/characters", preview=False):
    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    collection, root = bo.create_character(variant)
    used = {o.data.materials[0].name for o in collection.objects if o.type == "MESH"}
    rig = rg.build_armature(collection, root, variant)
    material, cells = make_palette(variant, used)
    merged = merge_into_slots(collection, rig, variant, material, cells)
    rg.build_animations(rig)
    bpy.context.scene.render.fps = rg.FPS

    glb = os.path.join(out_dir, f"{variant}_game.glb")
    bpy.ops.object.select_all(action="DESELECT")
    bpy.ops.export_scene.gltf(
        filepath=glb, export_format="GLB", export_apply=False, export_yup=True, export_animations=True,
        export_animation_mode="NLA_TRACKS", export_materials="EXPORT", export_extras=True,
    )

    colors = {**bo.PALETTE["common"], **bo.PALETTE[variant]}
    sidecar = os.path.join(out_dir, f"{variant}_game.palette.json")
    with open(sidecar, "w") as f:
        json.dump({
            "texture": {"cells": CELLS, "cellPx": CELL_PX, "width": CELLS * CELL_PX, "height": CELL_PX, "filter": "nearest, no mipmaps"},
            "slots": [s for s in SLOT_ORDER if s in merged],
            "materials": {name: {"cell": cell, "hex": colors[name]} for name, cell in cells.items()},
        }, f, indent=2)

    report = {
        "variant": variant,
        "meshes": {slot: len(obj.data.vertices) for slot, obj in merged.items()},
        "triangles": sum(len(obj.data.polygons) for obj in merged.values()),
        "materials": [m.name for m in bpy.data.materials if m.users],
        "palette_cells_used": len(cells),
        "actions": [a.name for a in bpy.data.actions],
        "glb": glb,
        "palette_json": sidecar,
    }
    if preview:
        report["preview"] = render_game_previews(rig, out_dir, variant)
    return report


def render_game_previews(rig, out_dir, variant):
    """Same poses as build_rigged, written as game_<variant>_<pose>.png."""
    scene = bpy.context.scene
    cam = bo.setup_preview(scene)
    cam.data.lens = 70
    from mathutils import Vector

    def shot(name, loc):
        cam.location = loc
        cam.rotation_euler = (Vector((0, 0, 0.78)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = os.path.join(out_dir, f"game_{variant}_{name}.png")
        bpy.ops.render.render(write_still=True)

    for track in rig.animation_data.nla_tracks:
        track.mute = True
    rg.reset_pose(rig)
    shot("rest", (0, -5.2, 0.85))
    for action, frame, where in (("Walk", 7, (4.6, -3.2, 1.0)), ("Wave", 8, (0, -5.2, 0.85)), ("Dance", 12, (0, -5.2, 0.85))):
        rg.reset_pose(rig)
        rig.animation_data.action = bpy.data.actions[action]
        scene.frame_set(frame)
        shot(action.lower(), where)
    rig.animation_data.action = None
    for track in rig.animation_data.nla_tracks:
        track.mute = False
    return scene.render.engine


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    variant = args[0] if args else "boy"
    out = args[1] if len(args) > 1 and not args[1].startswith("--") else "assets/characters"
    print(json.dumps(build(variant, out, preview="--preview" in args), indent=2))
