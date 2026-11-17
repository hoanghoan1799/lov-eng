"""
Re-export only the collider JSON from an already built island_world.blend (no full rebuild).

    /Applications/Blender.app/Contents/MacOS/Blender --background assets/world/island_world.blend \
        --python tools/blender/export_colliders.py -- assets/world
"""

import json
import os
import sys

import bpy  # noqa: F401

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import build_world as bw  # noqa: E402

out_dir = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "assets/world"
boxes, obbs, circles = bw.collect_colliders()
with open(os.path.join(out_dir, "island_colliders.json"), "w") as f:
    json.dump({"boxes": boxes, "obbs": obbs, "circles": circles}, f, separators=(",", ":"))
print("COLLIDERS", len(boxes), "boxes", len(obbs), "obbs", len(circles), "circles", "props inside:", bw.prop_overlap_count(boxes, circles, obbs))
