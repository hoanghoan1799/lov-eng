"""
Rigs the blockout characters (boy / girl) and exports a game-ready GLB with animations.

Run headless:
    /Applications/Blender.app/Contents/MacOS/Blender --background \
        --python tools/blender/build_rigged.py -- boy assets/characters --preview
    ... -- girl assets/characters --preview

Or paste into Blender and call build("boy") / build("girl"). When pasting, set RIG_DIR
to the folder that holds build_blockout.py first.

Rig
- 15 bones: Root, Hips, Spine, Head, UpperArm/LowerArm/Hand and UpperLeg/LowerLeg/Foot, both sides.
- Every bone's Z axis points to the character's front (-Y), so on every limb:
    +X rotation = swing forward; on the legs a knee bend is a negative X rotation.
    +Z rotation on a .L arm lifts it outwards, on a .R arm it lifts it inwards (mirrored).
- Rigid skinning: each part follows exactly one bone (weight 1.0), which keeps the cartoon shapes intact.
- Rest pose is the A-pose from the blockout.

Animations (glTF names): Idle, Walk, Run, Wave, Clap, Laugh, Think, Dance, Heart.
"""

import json
import math
import os
import sys

import bpy
from mathutils import Vector

try:
    RIG_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:  # pasted into Blender: set this to the folder with build_blockout.py
    RIG_DIR = os.path.abspath("tools/blender")
if RIG_DIR not in sys.path:
    sys.path.insert(0, RIG_DIR)

import build_blockout as bo  # noqa: E402

FPS = 24
A_POSE = bo.A_POSE

# ------------------------------------------------------------------ skeleton
JOINTS = {
    # hip height, leg x, knee z, ankle z
    "boy": {"hip": 0.62, "leg_x": 0.115, "knee": 0.36, "ankle": 0.095},
    "girl": {"hip": 0.55, "leg_x": 0.075, "knee": 0.32, "ankle": 0.09},
}


def bone_table(variant):
    j = JOINTS[variant]
    hip, lx, knee, ankle = j["hip"], j["leg_x"], j["knee"], j["ankle"]
    bones = [
        # name, head, tail, parent, roll_axis (the bone's Z axis points here)
        ("Root", (0, 0, 0), (0, 0, 0.15), None, (0, -1, 0)),
        ("Hips", (0, 0, hip), (0, 0, hip + 0.08), "Root", (0, -1, 0)),
        ("Spine", (0, 0, hip + 0.08), (0, 0, 0.95), "Hips", (0, -1, 0)),
        ("Head", (0, 0, 0.95), (0, 0, 1.5), "Spine", (0, -1, 0)),
    ]
    for side, sx in (("L", 1), ("R", -1)):
        shoulder, elbow, wrist, hand, d = bo.arm_points(sx)
        bones += [
            (f"UpperArm.{side}", tuple(shoulder), tuple(elbow), "Spine", (0, -1, 0)),
            (f"LowerArm.{side}", tuple(elbow), tuple(wrist), f"UpperArm.{side}", (0, -1, 0)),
            (f"Hand.{side}", tuple(wrist), tuple(hand + d * 0.04), f"LowerArm.{side}", (0, -1, 0)),
            (f"UpperLeg.{side}", (lx * sx, 0, hip), (lx * sx, 0, knee), "Hips", (0, -1, 0)),
            (f"LowerLeg.{side}", (lx * sx, 0, knee), (lx * sx, 0, ankle), f"UpperLeg.{side}", (0, -1, 0)),
            (f"Foot.{side}", (lx * sx, 0, ankle), (lx * sx, -0.2, 0.04), f"LowerLeg.{side}", (0, 0, 1)),
        ]
    return bones


def build_armature(collection, root, variant):
    data = bpy.data.armatures.new("CharacterRig")
    rig = bpy.data.objects.new("CharacterRig", data)
    collection.objects.link(rig)
    rig.parent = root
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    for name, head, tail, parent, roll_axis in bone_table(variant):
        bone = data.edit_bones.new(name)
        bone.head, bone.tail = head, tail
        bone.align_roll(Vector(roll_axis))
        if parent:
            bone.parent = data.edit_bones[parent]
    bpy.ops.object.mode_set(mode="OBJECT")
    return rig


# ------------------------------------------------------------------ skinning
HEAD_PARTS = {"Head", "Ear", "Eye", "EyeShine", "EyeShine2", "Brow", "Blush", "Nose", "Mouth"}
SPINE_PARTS = {"Neck", "Torso", "ShoulderYoke", "HoodiePocket", "HoodieHem", "StarFront", "HoodCollar", "HoodBack",
               "HoodDroop", "Cord", "CordTip", "ShirtTorso", "ShirtPanel", "JacketBack", "JacketFlap", "JacketTrim",
               "JacketHem", "JacketCollar", "Backpack", "BackpackPocket", "BackpackStrap"}
HIPS_PARTS = {"PantsHip", "Skirt", "SkirtBelt"}
ARM_PARTS = {"SleeveUpper": "UpperArm", "SleeveBulge": "UpperArm", "SleeveLower": "LowerArm", "SleeveRing": "LowerArm",
             "Cuff": "LowerArm", "WristCuff": "LowerArm", "Hand": "Hand", "Thumb": "Hand"}
LEG_PARTS = {"PantsThigh": "UpperLeg", "PantsPocket": "UpperLeg", "LegThigh": "UpperLeg", "PantsShin": "LowerLeg",
             "PantsHem": "LowerLeg", "LegShin": "LowerLeg", "Sock": "LowerLeg", "SockRing": "LowerLeg"}


def bone_for(name):
    """Which bone drives a part, by name. Every part follows exactly one bone (rigid skinning)."""
    base, _, side = name.partition(".")
    if base in HEAD_PARTS or base.startswith("Hair"):
        return "Head"
    if base in HIPS_PARTS:
        return "Hips"
    if base in SPINE_PARTS:
        return "Spine"
    if base.startswith("Shoe") and side in ("L", "R"):
        return f"Foot.{side}"
    for table in (ARM_PARTS, LEG_PARTS):
        if base in table and side in ("L", "R"):
            return f"{table[base]}.{side}"
    return None


def skin_to_rig(collection, rig):
    unmapped = []
    for obj in list(collection.objects):
        if obj.type != "MESH":
            continue
        bone = bone_for(obj.name)
        if bone is None:
            unmapped.append(obj.name)
            continue
        group = obj.vertex_groups.new(name=bone)
        group.add(list(range(len(obj.data.vertices))), 1.0, "REPLACE")
        modifier = obj.modifiers.new("Armature", "ARMATURE")  # last in the stack: deforms the rounded mesh
        modifier.object = rig
        obj.parent = rig
    return unmapped


# ------------------------------------------------------------------ animation
def key(rig, bone, frame, rot=None, loc=None):
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


def build_animations(rig):
    tau = math.tau
    s = lambda t, k=1, phase=0: math.sin(tau * (t * k + phase))
    c = lambda t, k=1, phase=0: math.cos(tau * (t * k + phase))
    Z3 = (0, 0, 0)
    BONES = [b.name for b in rig.pose.bones]

    def arm_z(side, hang):
        """Z rotation that puts the arm `hang` radians from straight down (rest is the A-pose)."""
        v = hang - A_POSE
        return v if side == "L" else -v

    def bend_in(side, amount):
        """Z rotation that bends a forearm towards the body."""
        return amount if side == "L" else -amount

    def reset(f, skip=()):
        for name in BONES:
            if name == "Root" or name in skip:
                continue
            key(rig, name, f, rot=Z3, loc=Z3 if name == "Hips" else None)

    def cycle(name, length, fn):
        action = new_action(rig, name)
        for frame in range(length + 1):
            f, t = frame + 1, (frame % length) / length
            reset(f)
            fn(f, t)
        finish_action(rig, action, name)

    def idle(f, t):
        key(rig, "Hips", f, loc=(0, 0, 0.008 * s(t)))
        key(rig, "Spine", f, rot=(0.02 * s(t), 0, 0))
        key(rig, "Head", f, rot=(0.03 * s(t, 1, 0.15), 0.04 * s(t, 1, 0.5), 0))
        for side in ("L", "R"):
            key(rig, f"UpperArm.{side}", f, rot=(0.05 * s(t, 1, 0.2), 0, arm_z(side, 0.3 + 0.02 * s(t, 1, 0.2))))
            key(rig, f"LowerArm.{side}", f, rot=(0.15, 0, 0))

    def locomotion(swing, bob, lean, knee):
        def fn(f, t):
            key(rig, "Hips", f, rot=(0, 0.06 * s(t), 0), loc=(0, 0, bob * abs(c(t))))
            key(rig, "Spine", f, rot=(lean, -0.07 * s(t), 0))
            key(rig, "Head", f, rot=(-lean * 0.6, 0.04 * s(t), 0))
            for side, ph in (("L", 0.0), ("R", 0.5)):
                leg = swing * s(t, 1, ph)
                lower = -knee * (0.55 + 0.45 * c(t, 1, ph))
                key(rig, f"UpperLeg.{side}", f, rot=(leg, 0, 0))
                key(rig, f"LowerLeg.{side}", f, rot=(lower, 0, 0))
                key(rig, f"Foot.{side}", f, rot=(-(leg + lower) * 0.6, 0, 0))
                key(rig, f"UpperArm.{side}", f, rot=(-leg * 0.9, 0, arm_z(side, 0.22)))
                key(rig, f"LowerArm.{side}", f, rot=(0.3 + 0.35 * max(0.0, -s(t, 1, ph)) + lean, 0, 0))
        return fn

    def wave(f, t):
        key(rig, "UpperArm.R", f, rot=(0, 0, arm_z("R", 2.3)))
        key(rig, "LowerArm.R", f, rot=(0, 0, 0.55 * s(t, 3)))
        key(rig, "UpperArm.L", f, rot=(0, 0, arm_z("L", 0.3)))
        key(rig, "LowerArm.L", f, rot=(0.15, 0, 0))
        key(rig, "Head", f, rot=(0, 0, 0.1))
        key(rig, "Hips", f, loc=(0, 0, 0.01 * s(t, 2)))

    def clap(f, t):
        k = 0.5 + 0.5 * s(t, 4)
        for side in ("L", "R"):
            key(rig, f"UpperArm.{side}", f, rot=(0.95, 0, arm_z(side, 0.45 - 0.2 * k)))
            key(rig, f"LowerArm.{side}", f, rot=(0.85, 0, bend_in(side, 0.4 - 0.2 * k)))
        key(rig, "Head", f, rot=(0.05 * s(t, 4), 0, 0))
        key(rig, "Hips", f, loc=(0, 0, 0.015 * abs(s(t, 4))))

    def laugh(f, t):
        key(rig, "Spine", f, rot=(-0.14 + 0.05 * s(t, 4), 0, 0))
        key(rig, "Head", f, rot=(-0.3 + 0.08 * s(t, 4), 0, 0))
        key(rig, "Hips", f, loc=(0, 0, 0.03 * abs(s(t, 4))))
        for side in ("L", "R"):
            key(rig, f"UpperArm.{side}", f, rot=(0.3, 0, arm_z(side, 0.35 + 0.1 * s(t, 4))))
            key(rig, f"LowerArm.{side}", f, rot=(1.0, 0, 0))

    def think(f, t):
        key(rig, "UpperArm.R", f, rot=(0.6, 0, arm_z("R", 0.5)))
        key(rig, "LowerArm.R", f, rot=(2.25, 0, 0))
        key(rig, "UpperArm.L", f, rot=(0.2, 0, arm_z("L", 0.35)))
        key(rig, "LowerArm.L", f, rot=(1.1, 0, 0))
        key(rig, "Head", f, rot=(0.1, 0, -0.2 + 0.03 * s(t)))
        key(rig, "Hips", f, loc=(0, 0, 0.006 * s(t)))

    def dance(f, t):
        key(rig, "Hips", f, rot=(0, 0.12 * s(t), 0), loc=(0.05 * s(t), 0, 0.04 * abs(s(t, 2))))
        key(rig, "Spine", f, rot=(0, 0.1 * s(t), 0))
        key(rig, "Head", f, rot=(0, 0, 0.15 * s(t)))
        key(rig, "UpperArm.L", f, rot=(0.1, 0, arm_z("L", 1.55 + 0.55 * s(t, 2))))
        key(rig, "UpperArm.R", f, rot=(0.1, 0, arm_z("R", 1.55 + 0.55 * s(t, 2, 0.5))))
        for side in ("L", "R"):
            key(rig, f"LowerArm.{side}", f, rot=(0.4, 0, 0))
        key(rig, "UpperLeg.L", f, rot=(0.3 * s(t, 2), 0, 0))
        key(rig, "UpperLeg.R", f, rot=(-0.3 * s(t, 2), 0, 0))
        key(rig, "LowerLeg.L", f, rot=(-0.35 * max(0.0, s(t, 2)), 0, 0))
        key(rig, "LowerLeg.R", f, rot=(-0.35 * max(0.0, -s(t, 2)), 0, 0))

    def heart(f, t):
        pulse = 0.08 * s(t, 2)
        for side in ("L", "R"):
            key(rig, f"UpperArm.{side}", f, rot=(0, 0, arm_z(side, 2.75 + pulse)))
            key(rig, f"LowerArm.{side}", f, rot=(0, 0, bend_in(side, 1.35)))
        key(rig, "Head", f, rot=(0, 0, 0.08 * s(t)))
        key(rig, "Hips", f, loc=(0, 0, 0.012 * s(t, 2)))

    cycle("Idle", 48, idle)
    cycle("Walk", 24, locomotion(0.6, 0.025, 0.04, 0.95))
    cycle("Run", 16, locomotion(0.95, 0.055, 0.2, 1.5))
    cycle("Wave", 48, wave)
    cycle("Clap", 24, clap)
    cycle("Laugh", 24, laugh)
    cycle("Think", 48, think)
    cycle("Dance", 48, dance)
    cycle("Heart", 48, heart)


# ------------------------------------------------------------------ preview / export
def reset_pose(rig):
    for pb in rig.pose.bones:
        pb.rotation_mode = "XYZ"
        pb.rotation_euler = (0, 0, 0)
        pb.location = (0, 0, 0)
    bpy.context.view_layer.update()


def render_poses(rig, out_dir, variant):
    scene = bpy.context.scene
    cam = bo.setup_preview(scene)  # EEVEE + 3-point studio lights
    cam.data.lens = 70

    def shot(name, loc):
        cam.location = loc
        cam.rotation_euler = (Vector((0, 0, 0.78)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = os.path.join(out_dir, f"rigged_{variant}_{name}.png")
        bpy.ops.render.render(write_still=True)

    for track in rig.animation_data.nla_tracks:  # tracks start together and would blend
        track.mute = True
    reset_pose(rig)
    shot("rest", (0, -5.2, 0.85))
    for action, frame, where in (
        ("Idle", 12, (0, -5.2, 0.85)), ("Walk", 7, (4.6, -3.2, 1.0)), ("Run", 5, (4.6, -3.2, 1.0)),
        ("Wave", 8, (0, -5.2, 0.85)), ("Clap", 5, (0, -5.2, 0.85)), ("Laugh", 3, (0, -5.2, 0.85)),
        ("Think", 10, (0, -5.2, 0.85)), ("Dance", 12, (0, -5.2, 0.85)), ("Heart", 6, (0, -5.2, 0.85)),
    ):
        reset_pose(rig)
        rig.animation_data.action = bpy.data.actions[action]
        bpy.context.scene.frame_set(frame)
        shot(action.lower(), where)
    rig.animation_data.action = None
    for track in rig.animation_data.nla_tracks:
        track.mute = False


def build(variant="boy", preview_dir=None, export_path=None):
    collection, root = bo.create_character(variant)
    rig = build_armature(collection, root, variant)
    unmapped = skin_to_rig(collection, rig)
    assert not unmapped, f"parts without a bone: {unmapped}"
    build_animations(rig)
    bpy.context.scene.render.fps = FPS
    report = {
        "variant": variant,
        "bones": len(rig.pose.bones),
        "meshes": len([o for o in collection.objects if o.type == "MESH"]),
        "actions": [a.name for a in bpy.data.actions],
    }
    if export_path:
        os.makedirs(os.path.dirname(os.path.abspath(export_path)), exist_ok=True)
        bpy.ops.object.select_all(action="DESELECT")
        bpy.ops.export_scene.gltf(
            filepath=export_path, export_format="GLB", export_apply=True, export_yup=True,
            export_animations=True, export_animation_mode="NLA_TRACKS", export_materials="EXPORT",
        )
        report["exported"] = export_path
    if preview_dir:
        os.makedirs(preview_dir, exist_ok=True)
        render_poses(rig, preview_dir, variant)
    return report


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    variant = args[0] if args else "boy"
    out_dir = os.path.abspath(args[1]) if len(args) > 1 and not args[1].startswith("--") else os.path.abspath("assets/characters")
    print(json.dumps(build(
        variant,
        preview_dir=out_dir if "--preview" in args else None,
        export_path=os.path.join(out_dir, f"{variant}_rigged.glb"),
    ), indent=2))
