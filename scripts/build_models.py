"""Build approximate research models. Run with Blender 5.2 --background --python."""

import math
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "web/public/assets/models"
SOURCES = ROOT / "assets/blender"


def material(name, color, metal=0, roughness=0.5):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*color, 1)
    shader.inputs["Metallic"].default_value = metal
    shader.inputs["Roughness"].default_value = roughness
    return mat


def finish(obj, name, mat, group):
    obj.name = name
    obj.data.materials.append(mat)
    obj.parent = group
    return obj


def part(identifier, label, direction=(0, 0, 0)):
    obj = bpy.data.objects.new(identifier, None)
    bpy.context.collection.objects.link(obj)
    obj.empty_display_size = 0.08
    obj["part_id"] = identifier
    obj["label"] = label
    # Y-up axis used by glTF clients.
    obj["explode"] = [direction[0], direction[2], -direction[1]]
    return obj


def box(name, at, dimensions, mat, group, bevel=0.025, rotation=0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=at)
    obj = bpy.context.object
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.rotation_euler.z = rotation
    if bevel:
        modifier = obj.modifiers.new("Rounded edges", "BEVEL")
        modifier.width = bevel
        modifier.segments = 3
        modifier = obj.modifiers.new("Corner normals", "WEIGHTED_NORMAL")
        modifier.keep_sharp = True
    return finish(obj, name, mat, group)


def disc(name, at, radius, depth, mat, group, axis="z", bevel=0.018):
    angle = math.pi / 2
    rotations = {"z": (0, 0, 0), "y": (angle, 0, 0), "x": (0, angle, 0)}
    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=radius, depth=depth,
                                       location=at, rotation=rotations[axis])
    obj = bpy.context.object
    modifier = obj.modifiers.new("Edge radius", "BEVEL")
    modifier.width = bevel
    modifier.segments = 3
    for face in obj.data.polygons:
        face.use_smooth = len(face.vertices) == 4
    return finish(obj, name, mat, group)


def tube(name, points, radius, mat, group):
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = radius
    curve.bevel_resolution = 3
    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for node, point in zip(spline.points, points):
        node.co = (*point, 1)
    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    curve.materials.append(mat)
    obj.parent = group
    return obj


def rounded_outline(cx, cz, rx, rz, y, power=0.65):
    coordinates = []
    for i in range(65):
        angle = i * 2 * math.pi / 64
        x, z = math.cos(angle), math.sin(angle)
        coordinates.append((cx + rx * math.copysign(abs(x) ** power, x),
                            y, cz + rz * math.copysign(abs(z) ** power, z)))
    return coordinates


def pane(name, loop, mat, group):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(loop[:-1], [], [list(range(len(loop) - 1))])
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    mod = obj.modifiers.new("Lens thickness", "SOLIDIFY")
    mod.thickness = 0.016
    return finish(obj, name, mat, group)


def palette():
    return {
        "ink": material("Graphite housing", (0.055, 0.062, 0.058), 0.15, 0.4),
        "charcoal": material("Black polymer", (0.024, 0.031, 0.028)),
        "paper": material("Warm polymer", (0.66, 0.63, 0.51), 0.08, 0.35),
        "green": material("PCB solder mask", (0.021, 0.19, 0.115), 0.18, 0.4),
        "metal": material("Brushed aluminium", (0.62, 0.65, 0.64), 0.78, 0.31),
        "gold": material("Copper foil", (0.63, 0.28, 0.085), 0.62, 0.34),
        "signal": material("Signal orange", (0.9, 0.19, 0.035), 0.1, 0.39),
        "lens": material("Tinted lens", (0.35, 0.49, 0.47), 0.25, 0.12),
        "screen": material("Display", (0.025, 0.16, 0.19), 0.38, 0.22),
    }


def chips(group, mat, at, size, count=6, axis="x"):
    for i in range(count):
        step = size * (i - (count - 1) / 2) * 1.35
        x, y, z = at
        if axis == "y":
            y += step
        else:
            x += step
        box(f"Chip {i + 1}", (x, y, z), (size, size, size * 0.33),
            mat, group, size * 0.08)


def glasses(m):
    frame = part("frame", "镜框与镜片")
    for side in (-1, 1):
        outline = rounded_outline(side * 0.60, 0.13, 0.50, 0.34, 0)
        tube("Molded rim", outline, 0.055, m["ink"], frame)
        pane("Tinted lens", rounded_outline(side * 0.60, 0.13, 0.48, 0.32, 0.012),
             m["lens"], frame)
        box("Hinge block", (side * 1.10, 0.035, 0.31), (0.19, 0.24, 0.19), m["ink"], frame)
    tube("Nose bridge", [(-0.14, 0, 0.25), (0, -0.02, 0.29), (0.14, 0, 0.25)], 0.052, m["ink"], frame)
    for key, side, label in [("left-arm", -1, "左镜腿"), ("right-arm", 1, "右镜腿")]:
        arm = part(key, label, (side * 0.72, 0.43, 0.35))
        box("Temple cover", (side * 1.17, 0.43, 0.33), (0.16, 0.77, 0.20), m["ink"], arm)
        tube("Temple tip", [(side * 1.17, 0.72, 0.31), (side * 1.12, 1.02, 0.28),
                            (side * 1.07, 1.22, 0.16), (side * 1.03, 1.30, 0.03)], 0.062, m["ink"], arm)
        box("Hinge", (side * 1.14, 0.12, 0.33), (0.12, 0.12, 0.12), m["metal"], arm)
    camera = part("camera", "摄像头模组", (-0.63, -0.45, 0.46))
    box("Camera base", (-1.094, -0.04, 0.33), (0.14, 0.08, 0.14), m["charcoal"], camera)
    disc("Camera lens", (-1.094, -0.096, 0.33), 0.049, 0.04, m["screen"], camera, "y")
    board = part("board", "主板", (-0.59, 0, -0.31))
    box("Main PCB", (-1.15, 0.41, 0.33), (0.077, 0.52, 0.061), m["green"], board)
    chips(board, m["charcoal"], (-1.15, 0.42, 0.375), 0.054, 6, "y")
    battery = part("battery", "锂电池", (0.67, 0, -0.34))
    box("Battery pouch", (1.16, 0.44, 0.34), (0.093, 0.47, 0.10), m["metal"], battery)
    box("Battery tab", (1.16, 0.19, 0.34), (0.086, 0.052, 0.09), m["gold"], battery)
    flex = part("flex", "柔性排线", (0.09, -0.38, 0.57))
    tube("Flex routing", [(-1.10, 0.07, 0.36), (-0.72, 0.03, 0.46),
                          (0, 0.01, 0.30), (0.73, 0.03, 0.46), (1.10, 0.10, 0.34)], 0.022, m["gold"], flex)
    speakers = part("speakers", "开放式扬声器", (0.03, 0.62, -0.46))
    for side in (-1, 1):
        box("Speaker capsule", (side * 1.14, 0.66, 0.28), (0.087, 0.21, 0.075), m["metal"], speakers)


def toy(m):
    shell = part("shell", "外壳", (0, 0.36, -0.62))
    box("Desk shell", (0, 0, 0.58), (1.52, 1.04, 1.28), m["paper"], shell, 0.22)
    box("Foot", (0, 0.015, 0.005), (1.20, 0.76, 0.14), m["ink"], shell, 0.06)
    box("Top switch", (0.4, 0, 1.244), (0.24, 0.22, 0.11), m["signal"], shell, 0.038)
    board = part("board", "ESP32-S3 主板", (0, 0.65, 0.60))
    box("Development PCB", (0, 0.04, 0.48), (1.01, 0.59, 0.05), m["green"], board)
    box("ESP32 module", (-0.16, 0.04, 0.54), (0.39, 0.33, 0.08), m["metal"], board)
    chips(board, m["ink"], (0.24, 0.06, 0.53), 0.07, 4)
    for side in (-1, 1):
        for j in range(9):
            disc("Pin", (-0.40 + j * 0.10, side * 0.24, 0.532), 0.017, 0.028, m["gold"], board)
    mic = part("mic", "数字麦克风", (-0.68, -0.18, 0.56))
    box("Microphone board", (-0.45, -0.29, 0.95), (0.24, 0.17, 0.06), m["green"], mic)
    disc("MEMS port", (-0.45, -0.29, 0.987), 0.056, 0.039, m["metal"], mic)
    speaker = part("speaker", "扬声器", (0.79, -0.12, 0.05))
    disc("Speaker body", (0.56, -0.16, 0.50), 0.23, 0.13, m["metal"], speaker, "x")
    disc("Speaker diaphragm", (0.64, -0.16, 0.50), 0.18, 0.033, m["charcoal"], speaker, "x")
    display = part("display", "显示屏", (0, -0.82, 0.19))
    box("LCD frame", (0, -0.51, 0.80), (1.13, 0.084, 0.60), m["ink"], display, 0.038)
    box("LCD pane", (0, -0.561, 0.80), (0.99, 0.021, 0.47), m["screen"], display, 0.009)
    for side in (-1, 1):
        box("Status eye", (side * 0.19, -0.576, 0.82), (0.095, 0.013, 0.14), m["paper"], display, 0.006)


def speaker(m):
    shell = part("shell", "外壳与网罩", (-0.77, -0.24, 0))
    box("Speaker enclosure", (0, 0, 0.94), (1.22, 1.13, 1.83), m["ink"], shell, 0.19)
    for j in range(20):
        z = 0.25 + j * 0.07
        box("Grille slot", (0, -0.559, z), (0.87, 0.024, 0.023), m["charcoal"], shell, 0.008)
    top = part("top", "顶部控制与麦克风组件", (0, -0.02, 0.76))
    box("Upper control cap", (0, 0, 1.87), (1.16, 1.08, 0.13), m["charcoal"], top, 0.058)
    for i in range(4):
        disc("Control key", (-0.30 + i * 0.20, -0.08, 1.945), 0.053, 0.021, m["ink"], top)
    box("Status bar", (0, -0.37, 1.941), (0.31, 0.03, 0.02), m["signal"], top, 0.009)
    board = part("board", "内部主板", (0.65, 0.49, 0.42))
    box("Main PCB", (0, 0.32, 1.57), (0.77, 0.46, 0.07), m["green"], board)
    box("Shield", (0.02, 0.31, 1.634), (0.36, 0.29, 0.065), m["metal"], board)
    chips(board, m["ink"], (0, 0.15, 1.624), 0.06, 6)
    driver = part("speaker", "主动扬声器", (0.02, -0.84, 0.01))
    disc("Driver mounting", (0, -0.30, 0.92), 0.45, 0.20, m["metal"], driver, "y")
    disc("Surround", (0, -0.424, 0.92), 0.39, 0.08, m["charcoal"], driver, "y")
    disc("Diaphragm", (0, -0.474, 0.92), 0.30, 0.042, m["ink"], driver, "y")
    disc("Dust cap", (0, -0.51, 0.92), 0.125, 0.049, m["charcoal"], driver, "y")
    radiators = part("radiators", "被动辐射器", (0.75, 0.20, -0.39))
    for side in (-1, 1):
        box("Passive radiator", (side * 0.46, 0.04, 0.72), (0.12, 0.56, 0.71), m["metal"], radiators, 0.056)
        box("Radiator surround", (side * 0.525, 0.04, 0.72), (0.042, 0.48, 0.63), m["charcoal"], radiators, 0.02)


def generate(name, label, builder):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.name = label
    scene["asset_status"] = "Approximate visual study. Units are illustrative."
    builder(palette())
    for obj in scene.objects:
        obj.select_set(False)
    bpy.ops.wm.save_as_mainfile(filepath=str(SOURCES / f"{name}.blend"))
    bpy.ops.export_scene.gltf(filepath=str(OUTPUT / f"{name}.glb"), export_format="GLB",
                              export_apply=True, export_extras=True, export_yup=True,
                              export_cameras=False, export_lights=False)


if __name__ == "__main__":
    for folder in (OUTPUT, SOURCES):
        folder.mkdir(parents=True, exist_ok=True)
    generate("xiaomi-glasses", "AI 眼镜 / 拆解参考", glasses)
    generate("xiaozhi-esp32", "小智桌面样机 / 原创外壳概念", toy)
    generate("xiaomi-speaker-pro", "AI 音箱 / 拆解参考", speaker)
