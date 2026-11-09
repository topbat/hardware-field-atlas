"""Build approximate research models. Run with Blender 5.2 --background --python."""

import math
from pathlib import Path

import bpy

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


def rounded_rectangle(width, depth, radius):
    points = []
    for cx, cy, start in ((width / 2 - radius, depth / 2 - radius, 0),
                          (-width / 2 + radius, depth / 2 - radius, 90),
                          (-width / 2 + radius, -depth / 2 + radius, 180),
                          (width / 2 - radius, -depth / 2 + radius, 270)):
        for i in range(9):
            a = math.radians(start + 90 * i / 8)
            points.append((cx + radius * math.cos(a), cy + radius * math.sin(a)))
    return points


def sleeve(name, width, depth, radius, low, high, wall, mat, group):
    outer = rounded_rectangle(width, depth, radius)
    inner = rounded_rectangle(width - 2 * wall, depth - 2 * wall, radius - wall)
    count = len(outer)
    vertices = [(x, y, z) for loop, z in ((outer, low), (outer, high), (inner, high), (inner, low))
                for x, y in loop]
    faces = [(layer * count + i, layer * count + (i + 1) % count,
              ((layer + 1) % 4) * count + (i + 1) % count, ((layer + 1) % 4) * count + i)
             for layer in range(4) for i in range(count)]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return finish(obj, name, mat, group)


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
    mats = {
        "ink": material("Graphite housing", (0.055, 0.062, 0.058), 0.15, 0.4),
        "charcoal": material("Black polymer", (0.024, 0.031, 0.028)),
        "paper": material("Warm white polymer", (0.81, 0.82, 0.8), 0.0, 0.37),
        "green": material("PCB solder mask", (0.021, 0.19, 0.115), 0.18, 0.4),
        "blue": material("Blue solder mask", (0.014, 0.10, 0.23), 0.15, 0.38),
        "metal": material("Brushed aluminium", (0.62, 0.65, 0.64), 0.78, 0.31),
        "gold": material("Copper foil", (0.63, 0.28, 0.085), 0.62, 0.34),
        "signal": material("Signal orange", (0.9, 0.19, 0.035), 0.1, 0.39),
        "lens": material("Clear lens", (0.72, 0.83, 0.81), 0.0, 0.08),
        "screen": material("Display", (0.025, 0.16, 0.19), 0.38, 0.22),
        "cloth": material("Charcoal woven sleeve", (0.038, 0.042, 0.045), 0.0, 0.87),
    }
    lens = mats["lens"]
    lens.node_tree.nodes.get("Principled BSDF").inputs["Alpha"].default_value = 0.19
    lens.diffuse_color = (0.72, 0.83, 0.81, 0.19)
    return mats


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
        outline = rounded_outline(side * 0.593, 0.16, 0.48, 0.34, 0.0, power=0.83)
        # The lens narrows toward the chin edge, matching the front-view D outline.
        outline = [(side * 0.593 + (x - side * 0.593) * (0.92 if z < 0.16 else 1),
                    y, z) for x, y, z in outline]
        tube("D rim", outline, 0.032, m["ink"], frame)
        pane("Clear lens", [(side * 0.593 + (x - side * 0.593) * 0.97, y + 0.012,
                            0.16 + (z - 0.16) * 0.97) for x, y, z in outline], m["lens"], frame)
        box("Temple corner", (side * 1.05, 0.023, 0.36), (0.20, 0.15, 0.17), m["ink"], frame, 0.033)
    tube("Nose bridge", [(-0.205, 0, 0.373), (-0.104, -0.02, 0.337), (0, -0.022, 0.329),
                         (0.104, -0.02, 0.337), (0.205, 0, 0.373)], 0.043, m["ink"], frame)
    disc("Opposite recording indicator", (-1.06, -0.062, 0.36), 0.033, 0.013, m["metal"], frame, "y")
    # With the front of the frame at negative Y, +X is the wearer's left.
    arms = {}
    for key, side, label in [("left-arm", 1, "左镜腿"), ("right-arm", -1, "右镜腿")]:
        arm = part(key, label, (side * 0.83, 0.46, 0.29))
        arms[key] = arm
        box("Temple housing", (side * 1.10, 0.44, 0.365), (0.105, 0.80, 0.14), m["ink"], arm, 0.038)
        box("Inner cover", (side * 1.047, 0.43, 0.37), (0.024, 0.67, 0.116), m["charcoal"], arm, 0.010)
        tube("Swept ear tip", [(side * 1.10, 0.76, 0.36), (side * 1.09, 0.99, 0.33),
                              (side * 1.046, 1.17, 0.25), (side * 0.989, 1.33, 0.119)],
             0.047, m["ink"], arm)
        if side < 0:
            box("Right USB-C port recess", (side * 0.989, 1.355, 0.118), (0.064, 0.021, 0.029),
                m["charcoal"], arm, 0.008)
        else:
            disc("Left power button", (side * 0.947, 1.30, 0.136), 0.023, 0.014, m["charcoal"], arm, "x")
    camera = part("camera", "左侧摄像头模组", (0.49, -0.43, 0.38))
    box("Camera base", (1.06, -0.021, 0.36), (0.101, 0.075, 0.097), m["charcoal"], camera)
    disc("Camera lens", (1.06, -0.069, 0.36), 0.036, 0.020, m["screen"], camera, "y")
    board = part("board", "左镜腿主板", (0.51, -0.05, -0.34))
    box("Long left PCB", (1.10, 0.335, 0.367), (0.062, 0.46, 0.033), m["charcoal"], board)
    box("RF shield", (1.10, 0.30, 0.393), (0.050, 0.255, 0.017), m["metal"], board)
    chips(board, m["charcoal"], (1.10, 0.505, 0.39), 0.042, 3, "y")
    battery = part("battery", "右镜腿锂电池", (-0.55, 0, -0.34))
    box("Black wrapped pouch", (-1.10, 0.376, 0.367), (0.071, 0.38, 0.075), m["charcoal"], battery)
    box("Battery tab", (-1.10, 0.168, 0.367), (0.055, 0.045, 0.031), m["gold"], battery)
    for y in (0.105, 0.93):
        box("Right end board", (-1.10, y, 0.332), (0.061, 0.10, 0.034), m["charcoal"], arms["right-arm"])
    flex = part("flex", "镜框柔性排线", (0.09, -0.38, 0.53))
    tube("Brow flex routing", [(-1.07, 0.07, 0.36), (-0.72, 0.03, 0.47), (-0.20, 0.02, 0.39),
                               (0, 0.01, 0.335), (0.19, 0.02, 0.39), (0.73, 0.03, 0.47),
                               (1.07, 0.10, 0.36)], 0.014, m["charcoal"], flex)
    speakers = part("speakers", "左右镜腿扬声器", (0.03, 0.68, -0.42))
    for side in (-1, 1):
        box("Speaker capsule", (side * 1.10, 0.655, 0.354), (0.070, 0.177, 0.060), m["metal"], speakers, 0.022)


def toy(m):
    shell = part("shell", "零售开发套件白色卡扣外壳", (0, 0.05, -0.66))
    sleeve("White snap-fit case", 1.69, 1.0, 0.105, 0.01, 0.32, 0.047, m["paper"], shell)
    box("White back panel", (0, 0, 0.028), (1.61, 0.93, 0.075), m["paper"], shell, 0.068)
    box("Left camera and grille fascia", (-0.609, 0.0, 0.313), (0.42, 0.94, 0.054),
        m["paper"], shell, 0.035)
    for y in (-0.275, -0.19, -0.105, -0.02):
        for x in (-0.690, -0.61, -0.53):
            disc("Speaker perforation", (x, y, 0.344), 0.012, 0.009, m["charcoal"], shell, bevel=0.002)
    for x in (-0.30, 0.0):
        box("Visible connector opening", (x, -0.506, 0.158), (0.20, 0.018, 0.047),
            m["charcoal"], shell, 0.009)

    board = part("board", "实战派 S3 电路板", (0, 0.40, 0.28))
    box("Development PCB outline", (0, 0, 0.168), (1.50, 0.83, 0.035), m["green"], board, 0.025)
    box("ESP32-S3 shield block", (0.32, 0.133, 0.205), (0.33, 0.27, 0.061), m["metal"], board, 0.018)
    for x in (-0.30, 0.0):
        box("Board edge connector", (x, -0.377, 0.195), (0.19, 0.108, 0.040), m["paper"], board, 0.007)
    box("USB-C connector housing", (0.70, -0.27, 0.197), (0.11, 0.13, 0.045), m["metal"], board, 0.010)

    camera = part("camera", "GC0308 摄像头", (-0.45, 0.30, 0.52))
    box("GC0308 camera body", (-0.61, 0.245, 0.272), (0.17, 0.17, 0.093), m["charcoal"], camera, 0.013)
    disc("One camera lens", (-0.61, 0.245, 0.334), 0.060, 0.024, m["screen"], camera)
    mic = part("mic", "两个模拟麦克风", (-0.77, -0.31, 0.31))
    for x in (-0.50, 0.43):
        disc("Microphone functional block", (x, -0.35, 0.200), 0.022, 0.026, m["metal"], mic, bevel=0.005)
    speaker = part("speaker", "喇叭", (-0.59, 0, -0.29))
    disc("Speaker functional block", (-0.592, -0.139, 0.237), 0.125, 0.06, m["charcoal"], speaker)
    display = part("display", "2 英寸 IPS 显示组件", (0.25, -0.29, 0.78))
    box("Dark LCD bezel", (0.191, 0.008, 0.326), (1.137, 0.839, 0.061), m["charcoal"], display, 0.052)
    box("Unlit LCD", (0.192, 0.008, 0.357), (0.958, 0.675, 0.018), m["ink"], display, 0.018)
    box("Display flex link", (0.102, -0.24, 0.261), (0.19, 0.12, 0.016), m["gold"], display, 0.007)


def speaker(m):
    shell = part("shell", "编织外壳与底座", (-0.95, -0.20, 0))
    sleeve("Rounded-square fabric sleeve", 1.08, 1.07, 0.175, 0.085, 2.04, 0.048, m["cloth"], shell)
    box("Recessed rubber base", (0, 0, 0.061), (1.03, 1.025, 0.125), m["charcoal"], shell, 0.056)

    chamber = part("chamber", "独立音腔主体")
    box("Acoustic enclosure", (0, 0, 1.04), (0.84, 0.81, 1.78), m["charcoal"], chamber, 0.052)
    for side in (-1, 1):
        box("Chamber front structural rail", (side * 0.397, -0.384, 1.05), (0.040, 0.033, 1.67),
            m["ink"], chamber, 0.01)

    top = part("top", "顶部盖板及麦克风板", (0, -0.025, 0.74))
    box("Rounded-square upper cap", (0, 0, 2.052), (1.058, 1.05, 0.10), m["charcoal"], top, 0.045)
    sleeve("Thin lighting perimeter", 1.056, 1.049, 0.17, 2.023, 2.044, 0.022, m["lens"], top)
    for i in range(4):
        disc("Control key", (-0.255 + i * 0.17, -0.043, 2.108), 0.044, 0.016, m["ink"], top, bevel=0.003)
    box("Blue top secondary PCB", (0, 0, 1.965), (0.89, 0.87, 0.042), m["blue"], top, 0.045)
    for x in (-0.29, 0, 0.29):
        disc("Microphone port", (x, 0.175, 2.107), 0.011, 0.007, m["ink"], top, bevel=0.002)

    board = part("board", "音腔背面主板", (0.57, 0.70, 0.29))
    box("Blue rear main PCB", (0, 0.426, 1.385), (0.61, 0.042, 0.61), m["blue"], board, 0.020)
    box("Main board shield", (0.07, 0.461, 1.40), (0.31, 0.038, 0.29), m["metal"], board, 0.017)
    for x in (-0.23, 0.23):
        box("Rear PCB connector", (x, 0.461, 1.17), (0.083, 0.044, 0.075), m["paper"], board, 0.01)

    driver = part("speaker", "音腔正面上部全频单元", (0.02, -0.83, 0.05))
    box("Driver square frame", (0, -0.416, 1.42), (0.707, 0.065, 0.707), m["ink"], driver, 0.037)
    disc("Single full-range surround", (0, -0.465, 1.42), 0.326, 0.048, m["ink"], driver, "y")
    disc("Single full-range diaphragm", (0, -0.493, 1.42), 0.259, 0.042, m["charcoal"], driver, "y")
    disc("Full-range dust cap", (0, -0.518, 1.42), 0.117, 0.040, m["charcoal"], driver, "y")
    radiators = part("radiators", "左右侧无源辐射器", (0.74, 0.20, -0.32))
    for side in (-1, 1):
        box("Side passive radiator surround", (side * 0.427, 0, 0.979), (0.065, 0.60, 0.92),
            m["ink"], radiators, 0.025)
        box("Side passive radiator membrane", (side * 0.470, 0, 0.979), (0.049, 0.49, 0.76),
            m["charcoal"], radiators, 0.022)

    io = part("io", "底部输入接口", (0, -0.38, -0.58))
    box("Bottom USB audio PCB", (0, 0.02, 0.170), (0.42, 0.32, 0.043), m["blue"], io, 0.018)
    box("USB-C audio port", (-0.115, -0.118, 0.132), (0.109, 0.08, 0.046), m["metal"], io, 0.008)
    disc("Adjacent DC inlet", (0.153, -0.128, 0.13), 0.036, 0.066, m["charcoal"], io, "y", 0.005)


def generate(name, label, builder, source):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.name = label
    scene["asset_status"] = "Approximate visual study. Units are illustrative."
    scene["reference_url"] = source
    scene["cutaway"] = f"/assets/cutaways/{name}.webp"
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
    generate("xiaomi-glasses", "小米 AI 眼镜 M2442G1 / 拆解参考", glasses,
             "https://www.52audio.com/archives/245045.html")
    generate("xiaozhi-esp32", "实战派 ESP32-S3 / 零售套件参考", toy,
             "https://item.szlcsc.com/43285221.html")
    generate("xiaomi-speaker-pro", "Xiaomi 智能音箱 Pro OH2P / 拆解参考", speaker,
             "https://www.52audio.com/archives/234243.html")
