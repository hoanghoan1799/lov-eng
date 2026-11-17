"""
English Adventure World - full island build: Phase 1 + Phase 3 + Phase 2 in one run.

    /Applications/Blender.app/Contents/MacOS/Blender --background \
        --python tools/blender/build_world.py -- assets/world --preview --export

Order (Phase 3 runs before the scatter so props avoid the final building footprints):
  1. Phase 1  build_island.create_island()       terrain, water, stream, bridges, roads, blockouts
  2. materials / masters                          shared Mat_* palette + 11_Reusable_Props
  3. Phase 3  build_island_phase3                 detailed exteriors for the 9 destinations
  4. Phase 2  build_island_phase2                 Central Park detail, props scattered with linked duplicates
  5. naming   COL_ / DEC_
  6. checks, previews, island_world.blend, island_world.glb (organised, instanced props) and
     island_world_game.glb (static parts merged per material + instanced props: the draw-call budget)
"""

import json
import math
import os
import random
import struct
import sys

import bmesh
import bpy
from mathutils import Vector

try:
    HERE = os.path.dirname(os.path.abspath(__file__))
except NameError:
    HERE = os.path.abspath("tools/blender")
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import build_island as bi  # noqa: E402
import build_island_phase2 as p2  # noqa: E402
import build_island_phase3 as p3  # noqa: E402

BUILDING_SHOTS = {
    # id: (distance in front, sideways, height, target height, lens)
    "coffee": (21, 8, 9, 3.0, 45), "restaurant": (24, 10, 11, 3.5, 45), "supermarket": (26, 10, 11, 2.5, 45),
    "mall": (30, 14, 16, 7.0, 45), "library": (26, 10, 11, 4.0, 45), "school": (36, 16, 14, 4.0, 40),
    "hotel": (32, 14, 18, 9.0, 45), "station": (34, 18, 13, 2.5, 40), "airport": (36, 18, 15, 3.0, 40),
}


def make_scene():
    p3.register_materials()
    colls, layout, bridges, scene, cam = bi.create_island()
    props = bpy.data.collections.new(p2.PROPS_COLLECTION)
    bpy.context.scene.collection.children.link(props)
    colls[p2.PROPS_COLLECTION] = props
    masters = p2.build_masters(props)
    for obj in masters.values():
        obj.hide_render = True  # masters live off the island and are never rendered or exported
    p3.make_glass_transparent()
    return colls, layout, bridges, scene, cam, masters


def render_all(scene, cam, colls, out_dir):
    bi.use_eevee(scene)
    shots = {}

    def shoot(name, loc, target, ortho_scale=None, lens=45, res=(1800, 1150)):
        scene.render.resolution_x, scene.render.resolution_y = res
        cam.location = Vector(loc)
        if ortho_scale:
            cam.data.type, cam.data.ortho_scale = "ORTHO", ortho_scale
        else:
            cam.data.type, cam.data.lens = "PERSP", lens
        cam.data.clip_end = 800
        cam.rotation_euler = (Vector(target) - cam.location).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = os.path.join(out_dir, f"{name}.png")
        bpy.ops.render.render(write_still=True)
        shots[name] = scene.render.filepath

    shoot("world_iso", (115, -115, 105), (0, 0, -3), 150)
    shoot("world_iso_back", (-115, 115, 105), (0, 0, -3), 150)
    shoot("world_top", (0, 0, 200), (0, 0, 0), 135)
    shoot("park_iso", (42, -42, 38), (0, 0, 1.5), 62, res=(1600, 1100))
    shoot("park_top", (0, 0, 120), (0, 0, 0), 58, res=(1400, 1400))
    for pid, cname, prefix, center, depth, _b, rad in bi.PLACES:
        dist, side, height, tz, lens = BUILDING_SHOTS[pid]
        c = Vector(center)
        front = bi.front_dir(center)
        right = Vector((front.y, -front.x))
        loc = c + front * dist + right * side
        shoot(f"place_{pid}", (loc.x, loc.y, height), (c.x, c.y, tz), lens=lens, res=(1300, 850))
    cam.data.type, cam.data.ortho_scale = "ORTHO", 150
    cam.location = (115, -115, 105)
    cam.rotation_euler = (Vector((0, 0, -3)) - cam.location).to_track_quat("-Z", "Y").to_euler()
    return shots


# ------------------------------------------------------------------ export
def select_only(objs):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)


def export_organised(path):
    objs = [o for o in bpy.data.objects if o.type == "MESH" and not any(c.name == p2.PROPS_COLLECTION for c in o.users_collection)]
    select_only(objs)
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True, export_apply=False, export_yup=True, export_materials="EXPORT")
    return len(objs)


def export_game(path):
    """Static parts merged per material; objects that share mesh data stay separate so they instance."""
    deps = bpy.context.evaluated_depsgraph_get()
    keep, static = [], {}
    for o in bpy.data.objects:
        if o.type != "MESH" or any(c.name == p2.PROPS_COLLECTION for c in o.users_collection):
            continue
        if o.data.users > 1 or len(o.data.materials) != 1:
            keep.append(o)
        else:
            static.setdefault(o.data.materials[0].name, []).append(o)
    created = []
    for mat, objs in static.items():
        bm = bmesh.new()
        for o in objs:
            tmp = bpy.data.meshes.new_from_object(o.evaluated_get(deps), depsgraph=deps)
            tmp.transform(o.matrix_world)
            bm.from_mesh(tmp)
            bpy.data.meshes.remove(tmp)
        mesh = bpy.data.meshes.new(f"Merged_{mat}")
        bm.to_mesh(mesh)
        bm.free()
        mesh.polygons.foreach_set("use_smooth", [False] * len(mesh.polygons))
        mesh.materials.append(bpy.data.materials[mat])
        out = bpy.data.objects.new(f"Merged_{mat}", mesh)
        bpy.context.scene.collection.objects.link(out)
        created.append(out)
    select_only(created + keep)
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True, export_apply=False, export_yup=True, export_materials="EXPORT")
    for o in created:
        bpy.data.objects.remove(o, do_unlink=True)
    return {"merged_static_meshes": len(created), "kept_separate_objects": len(keep)}


def glb_stats(path):
    raw = open(path, "rb").read()
    clen, _ = struct.unpack("<I4s", raw[12:20])
    j = json.loads(raw[20 : 20 + clen])
    nodes_with_mesh = [n for n in j["nodes"] if "mesh" in n]
    meshes = j["meshes"]
    uses = {}
    for n in nodes_with_mesh:
        uses[n["mesh"]] = uses.get(n["mesh"], 0) + 1
    prims = sum(len(m["primitives"]) for m in meshes)
    tris = 0
    for n in nodes_with_mesh:
        for p in meshes[n["mesh"]]["primitives"]:
            if "indices" in p:
                tris += j["accessors"][p["indices"]]["count"] // 3
    shared = {k: v for k, v in uses.items() if v > 1}
    return {
        "MB": round(len(raw) / 1048576, 2), "nodes_with_mesh": len(nodes_with_mesh), "unique_meshes": len(meshes),
        "primitives_unique": prims, "instanced_meshes": len(shared), "nodes_using_shared_meshes": sum(shared.values()),
        "materials": len(j["materials"]), "triangles_rendered": tris,
        "draw_calls_without_instancing": sum(len(meshes[n["mesh"]]["primitives"]) for n in nodes_with_mesh),
        "draw_calls_with_instancing": prims,
    }



# ------------------------------------------------------------------ data for the web game
NPC_NAMES = {"coffee": "Mia", "restaurant": "Leo", "supermarket": "Hana", "mall": "Zoe", "library": "Eli",
             "school": "Mr. Lee", "hotel": "Tom", "station": "Ken", "airport": "Anna"}
PLACE_TITLES = {"coffee": "Coffee Shop", "restaurant": "Restaurant", "supermarket": "Supermarket", "mall": "Shopping Mall",
                "library": "Library", "school": "School", "hotel": "Hotel", "station": "Train Station", "airport": "Airport"}
MIN_BLOCK_HEIGHT = 0.6  # lower things (rails, floors, kerbs) can be walked over


def min_area_rect(pts):
    """Smallest rectangle around 2D points: (angle, u_min, u_max, v_min, v_max) with u=(cos,sin), v=(-sin,cos)."""
    best = None
    for k in range(180):  # 0..89.5 degrees
        a = math.radians(k * 0.5)
        c, s = math.cos(a), math.sin(a)
        us = [p[0] * c + p[1] * s for p in pts]
        vs = [-p[0] * s + p[1] * c for p in pts]
        area = (max(us) - min(us)) * (max(vs) - min(vs))
        if best is None or area < best[0] * 0.99:  # only leave axis-aligned for a clear gain
            best = (area, a, min(us), max(us), min(vs), max(vs))
    return best[1:]


def add_box(boxes, obbs, pts, top, name):
    """pts are game-space (x, z) points. Axis-aligned objects go to boxes, rotated ones to oriented boxes."""
    angle, u0, u1, v0, v1 = min_area_rect(pts)
    if angle == 0:
        boxes.append([round(u0, 2), round(v0, 2), round(u1, 2), round(v1, 2), round(top, 2), name])
        return
    c, s = math.cos(angle), math.sin(angle)
    mu, mv = (u0 + u1) / 2, (v0 + v1) / 2
    obbs.append([round(c * mu - s * mv, 2), round(s * mu + c * mv, 2), round(c, 4), round(s, 4),
                 round((u1 - u0) / 2, 2), round((v1 - v0) / 2, 2), round(top, 2), name])


def collect_colliders():
    """Axis-aligned boxes, oriented boxes and circles in GAME coordinates (x, z = -y), from every COL_ object."""
    boxes, obbs, circles = [], [], []
    for o in bpy.data.objects:
        if o.type != "MESH" or not o.name.startswith("COL_") or any(c.name == p2.PROPS_COLLECTION for c in o.users_collection):
            continue
        if o.data.users == 1:
            zs = [o.location.z + v.co.z for v in o.data.vertices]
            if max(zs) >= MIN_BLOCK_HEIGHT:
                pts = [(o.location.x + v.co.x, -(o.location.y + v.co.y)) for v in o.data.vertices]
                add_box(boxes, obbs, pts, max(zs), o.name)
            continue
        s = max(o.scale)
        if "Trunk" in o.name:
            circles.append([round(o.location.x, 2), round(-o.location.y, 2), round(0.42 * s, 2)])
        elif "Lamp" in o.name:
            circles.append([round(o.location.x, 2), round(-o.location.y, 2), 0.3])
        elif "Rock" in o.name:
            circles.append([round(o.location.x, 2), round(-o.location.y, 2), round(0.85 * s, 2)])
        else:
            corners = [o.matrix_world @ Vector(c) for c in o.bound_box]
            add_box(boxes, obbs, [(p.x, -p.y) for p in corners], max(p.z for p in corners), o.name)
    return boxes, obbs, circles


def prop_overlap_count(boxes, circles, obbs=()):
    """Trees, lamps and rocks that sit inside a building box (excludes the park interior)."""
    bad = 0
    for x, z, r in circles:
        if math.hypot(x, z) < 33:
            continue
        for x0, z0, x1, z1, top, name in boxes:
            if "Bench" in name or "Fence" in name or "Signboard" in name:
                continue
            if x0 - 0.1 <= x <= x1 + 0.1 and z0 - 0.1 <= z <= z1 + 0.1:
                bad += 1
                break
        else:
            for cx, cz, ux, uz, hu, hv, top, name in obbs:
                if "Bench" in name or "Fence" in name or "Signboard" in name:
                    continue
                du, dv = (x - cx) * ux + (z - cz) * uz, -(x - cx) * uz + (z - cz) * ux
                if abs(du) <= hu + 0.1 and abs(dv) <= hv + 0.1:
                    bad += 1
                    break
    return bad


def export_world_data(out_dir, layout, bridges):
    boxes, obbs, circles = collect_colliders()
    size, half = 121, 60
    heights = [[round(layout.height(gx - half, -(gz - half)), 2) for gx in range(size)] for gz in range(size)]  # heights[gz][gx]
    walkables = []
    for name, pa, pb in bridges:
        axis = bi.unit(pb - pa)
        mid = (pa + pb) / 2
        walkables.append({"x": round(mid.x, 2), "z": round(-mid.y, 2), "hw": 2.7, "hl": round((pb - pa).length / 2 + 1.5, 2),
                          "dx": round(axis.x, 3), "dz": round(-axis.y, 3), "top": 0.52, "name": f"Bridge_{name}"})
    places = []
    for pid, cname, prefix, center, depth, _b, rad in bi.PLACES:
        door = bi.door_point(center, depth)
        front = bi.front_dir(center)
        npc = door + front * 1.6
        places.append({"id": pid, "title": PLACE_TITLES[pid], "collection": cname, "x": center[0], "z": -center[1],
                       "doorX": round(door.x, 2), "doorZ": round(-door.y, 2), "npcName": NPC_NAMES[pid],
                       "npcX": round(npc.x, 2), "npcZ": round(-npc.y, 2), "npcFacingX": round(-front.x, 3), "npcFacingZ": round(front.y, 3)})
    layout_json = {
        "radius": bi.ISLAND_R, "walkRadius": 56.5, "spawn": {"x": 0, "z": -7}, "parkRadius": bi.PARK_R,
        "park": {"id": "park", "title": "Central Park", "npcName": "Sam", "npcX": 0, "npcZ": 15.4, "npcFacingX": 0, "npcFacingZ": -1},
        "places": places, "walkables": walkables,
    }
    with open(os.path.join(out_dir, "island_colliders.json"), "w") as f:
        json.dump({"boxes": boxes, "obbs": obbs, "circles": circles}, f, separators=(",", ":"))
    with open(os.path.join(out_dir, "island_height.json"), "w") as f:
        json.dump({"size": size, "step": 1, "origin": -half, "heights": heights}, f, separators=(",", ":"))
    with open(os.path.join(out_dir, "island_layout.json"), "w") as f:
        json.dump(layout_json, f, indent=1)
    return {"collider_boxes": len(boxes), "collider_obbs": len(obbs), "collider_circles": len(circles), "walkables": len(walkables),
            "props_inside_buildings": prop_overlap_count(boxes, circles, obbs)}


# ------------------------------------------------------------------ report
def report(colls, layout, bridges, masters, counts, names):
    insts = [o for o in bpy.data.objects if o.type == "MESH" and o.data.users > 1 and o not in masters.values()]
    statics = [o for o in bpy.data.objects if o.type == "MESH" and o.data.users == 1]
    bad = [o.name for o in statics if any(abs(s - 1) > 1e-6 for s in o.scale) or any(abs(r) > 1e-6 for r in o.rotation_euler)]
    top = [o for o in bpy.data.objects if o.name == "Island_Top"][0]
    xs, ys = [v.co.x for v in top.data.vertices], [v.co.y for v in top.data.vertices]
    reach = {}
    for pid, cname, prefix, center, depth, _b, rad in bi.PLACES:
        radii = [(o.location.xy + v.co.xy).length for o in colls[cname].objects if o.type == "MESH" and o.data.users == 1 for v in o.data.vertices]
        reach[cname] = (round(min(radii), 1), round(max(radii), 1))
    master_users = {m.name: m.data.users for m in masters.values()}
    return {
        "collections": [c.name for c in bpy.context.scene.collection.children],
        "objects_per_collection": {c.name: len(c.objects) for c in bpy.context.scene.collection.children},
        "mesh_objects": len([o for o in bpy.data.objects if o.type == "MESH"]),
        "unique_meshes": len(bpy.data.meshes),
        "linked_duplicates": len(insts),
        "master_mesh_users": master_users,
        "props_placed": counts,
        "naming": names,
        "materials": len(bpy.data.materials),
        "roughness": sorted({round(m.roughness, 2) for m in bpy.data.materials}),
        "static_objects_with_unapplied_transform": bad[:10],
        "island_diameter_m": round(max(max(xs) - min(xs), max(ys) - min(ys)), 1),
        "hills": len(layout.hills),
        "bridges": [b[0] for b in bridges],
        "reach_min_max_from_centre_m": reach,
    }


def build(out_dir="assets/world", preview=False, export=False, lite=False):
    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    p2.LITE = lite
    colls, layout, bridges, scene, cam, masters = make_scene()
    rng = random.Random(21)
    p3.rebuild_buildings(colls)
    counts = p2.build_park_detail(colls, masters, rng)
    p2.scatter(colls, layout, masters, rng, counts)
    names = p2.apply_collision_names()
    result = report(colls, layout, bridges, masters, counts, names)
    if preview:
        result["previews"] = list(render_all(scene, cam, colls, out_dir))
        result["render_engine"] = scene.render.engine
    if lite:  # mobile variant: only the game glb with low-poly props
        game = os.path.join(out_dir, "island_world_game_lite.glb")
        result["export_game"] = export_game(game)
        result["glb_game"] = glb_stats(game)
        with open(os.path.join(out_dir, "world_report_lite.json"), "w") as f:
            json.dump(result, f, indent=2)
        return result
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out_dir, "island_world.blend"))
    result["world_data"] = export_world_data(out_dir, layout, bridges)
    if export:
        organised = os.path.join(out_dir, "island_world.glb")
        game = os.path.join(out_dir, "island_world_game.glb")
        result["export_organised_objects"] = export_organised(organised)
        result["export_game"] = export_game(game)
        result["glb_organised"] = glb_stats(organised)
        result["glb_game"] = glb_stats(game)
    with open(os.path.join(out_dir, "world_report.json"), "w") as f:
        json.dump(result, f, indent=2)
    return result


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    out = args[0] if args and not args[0].startswith("--") else "assets/world"
    print(json.dumps(build(out, preview="--preview" in args, export="--export" in args, lite="--lite" in args), indent=2))
