# SIGNAL 첫 화면 파문 루프 렌더 (Blender 5.x).
# 사용: blender --background --factory-startup --python render/ripple.py -- --variant desktop --out render/out/ripple-desktop [--frames 0,40] [--samples 48] [--device GPU|CPU]
# 검은 수면에 빛 방울이 떨어져 파문이 번지는 장면을 끊김 없이 이어지는 루프 프레임(PNG)으로 굽는다.
# 방울 세기는 web/assets/hero/snapshot.json(렌더 시점에 고정)의 뉴스 반응 크기를 따른다. 웹에서는 글자 모양 창 안에 이 영상을 보여 준다.
import bpy, json, math, os, sys, time
import numpy as np

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
def arg(name, default=None):
    return argv[argv.index(name) + 1] if name in argv else default

HERE = os.path.dirname(os.path.abspath(__file__))
VARIANT = arg("--variant", "desktop")
OUT = os.path.abspath(arg("--out", os.path.join(HERE, "out", "ripple-" + VARIANT)))
SAMPLES = int(arg("--samples", "48"))
DEVICE = arg("--device", "GPU")
NFRAMES = int(arg("--nframes", "120"))
SCALE = int(arg("--scale", "100"))
ONLY = [int(x) for x in arg("--frames", "").split(",") if x != ""]
RES = {"desktop": (1600, 1000), "mobile": (720, 1280)}[VARIANT]
os.makedirs(OUT, exist_ok=True)

snap = json.load(open(os.path.join(HERE, "..", "web", "assets", "hero", "snapshot.json"), encoding="utf-8"))
LIME = (0.62, 0.98, 0.10)

# ---------- 파문 ----------
# 루프 길이 T 동안 방울마다 한 번씩 떨어진다. 과거 몇 주기의 파문까지 더해 t=0과 t=T가 같은 모양이 되게 한다.
T = 1.0
MOB = VARIANT == "mobile"
SPOTS = [(0.6, 4.6), (-3.6, 8.2), (4.2, 9.6)] if not MOB else [(0.2, 4.2), (-1.5, 8.0), (1.6, 11.5)]
mag = [min(1.0, abs(p.get("r", 1.0)) / 2.5) for p in snap["pins"]][:3]  # r: 측정된 가격 반응(%)
while len(mag) < 3: mag.append(0.5)
DROPS = [dict(x=SPOTS[i][0], y=SPOTS[i][1], t0=i / 3.0, a=0.03 + 0.06 * mag[i]) for i in range(3)]
C = 3.2     # 파문이 번지는 속도(단위/주기)
WL = 0.62   # 물결 간격

def field(X, Y, t):
    h = np.zeros_like(X)
    for d in DROPS:
        r = np.hypot(X - d["x"], Y - d["y"])
        for k in range(3):
            age = ((t - d["t0"]) % T) + k * T
            R = C * age
            sig = 0.3 + 0.55 * age
            env = np.exp(-((r - R) / sig) ** 2)
            # 바깥쪽 가장자리부터 안쪽으로 몇 겹의 물결. 멀리 갈수록·오래될수록 잦아든다
            amp = d["a"] * math.exp(-age * 1.5) / math.sqrt(1 + 0.6 * R)
            h += amp * env * np.cos(2 * math.pi * (r - R) / WL)
        # 떨어진 직후 가운데가 잠깐 솟았다 가라앉는다
        age = (t - d["t0"]) % T
        h += d["a"] * 1.6 * math.exp(-age * 9.0) * np.exp(-(r / 0.18) ** 2) * math.cos(age * 30)
    # 수면 전체의 아주 느린 일렁임: 주기마다 정수 번 돌아 루프가 이어진다
    tp = 2 * math.pi * t / T
    h += 0.0024 * np.sin(X * 0.9 + Y * 0.35 - tp) + 0.0018 * np.sin(-X * 0.4 + Y * 1.1 - 2 * tp) + 0.0012 * np.sin(X * 1.7 - Y * 0.8 + tp)
    return h

# ---------- 장면 ----------
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "CYCLES"
prefs = bpy.context.preferences.addons["cycles"].preferences
if DEVICE == "GPU":
    for typ in ("METAL", "OPTIX", "CUDA", "HIP", "ONEAPI"):
        try:
            prefs.compute_device_type = typ; prefs.get_devices()
            if any(d.type == typ for d in prefs.devices):
                for d in prefs.devices: d.use = d.type == typ
                sc.cycles.device = "GPU"; break
        except TypeError:
            pass
    else:
        sc.cycles.device = "CPU"
else:
    sc.cycles.device = "CPU"
print("DEVICE", sc.cycles.device, prefs.compute_device_type)
sc.cycles.samples = SAMPLES
sc.cycles.use_adaptive_sampling = True
sc.cycles.adaptive_threshold = 0.015
sc.cycles.use_denoising = True
sc.cycles.denoiser = "OPENIMAGEDENOISE"
sc.cycles.max_bounces = 6
sc.cycles.glossy_bounces = 4
sc.cycles.seed = 11
sc.render.resolution_x, sc.render.resolution_y = RES
sc.render.resolution_percentage = SCALE
sc.view_settings.view_transform = "Standard"
sc.view_settings.look = "None"
sc.render.image_settings.file_format = "PNG"
sc.render.image_settings.color_mode = "RGB"
sc.render.image_settings.compression = 30

world = bpy.data.worlds.new("w"); sc.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.0015, 0.0016, 0.0021, 1)

def mat(name):
    m = bpy.data.materials.new(name); m.use_nodes = True
    n = m.node_tree.nodes; n.clear()
    return m, n, m.node_tree.links
def emit(name, color, strength):
    m, n, l = mat(name)
    o = n.new("ShaderNodeOutputMaterial"); e = n.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = (*color, 1); e.inputs["Strength"].default_value = strength
    l.new(e.outputs[0], o.inputs["Surface"]); return m, e

# 수면: 카메라 가까운 쪽이 촘촘한 격자
NX, NY = (1500, 1600) if not MOB else (1500, 1700)
X0, X1 = (-13.0, 13.0) if not MOB else (-16.0, 16.0)
Y0, Y1 = -2.0, 60.0
u = np.linspace(0, 1, NY) ** 1.6
xs = np.linspace(X0, X1, NX); ys = Y0 + (Y1 - Y0) * u
GX, GY = np.meshgrid(xs, ys)
# 먼 곳은 물결을 줄여 격자보다 잔 물결(계단 무늬)이 생기지 않게 한다
FADE = np.clip(1.0 - (GY - 13) / 9, 0.0, 1.0) ** 2
mesh = bpy.data.meshes.new("water")
base = np.stack([GX.ravel(), GY.ravel(), np.zeros(GX.size)], 1).astype(np.float32)
ii = np.arange(NX * NY).reshape(NY, NX)
faces = np.stack([ii[:-1, :-1].ravel(), ii[:-1, 1:].ravel(), ii[1:, 1:].ravel(), ii[1:, :-1].ravel()], 1)
mesh.vertices.add(len(base)); mesh.vertices.foreach_set("co", base.ravel())
mesh.loops.add(faces.size); mesh.loops.foreach_set("vertex_index", faces.astype(np.int32).ravel())
mesh.polygons.add(len(faces)); mesh.polygons.foreach_set("loop_start", (np.arange(len(faces)) * 4).astype(np.int32)); mesh.polygons.foreach_set("loop_total", np.full(len(faces), 4, np.int32))
mesh.update(); mesh.validate(); mesh.shade_smooth()
water = bpy.data.objects.new("water", mesh); sc.collection.objects.link(water)
wm, n, l = mat("water")
o = n.new("ShaderNodeOutputMaterial"); b = n.new("ShaderNodeBsdfPrincipled")
b.inputs["Base Color"].default_value = (0.0, 0.0, 0.0, 1)
b.inputs["Roughness"].default_value = 0.035
b.inputs["IOR"].default_value = 1.33
b.inputs["Specular IOR Level"].default_value = 0.5
# 멀어질수록 수면이 어둠 속으로 녹는다(수평선이 딱 끊기지 않게)
cd_ = n.new("ShaderNodeCameraData"); fr = n.new("ShaderNodeMapRange")
fr.inputs["From Min"].default_value = 12.0; fr.inputs["From Max"].default_value = 26.0; fr.interpolation_type = "SMOOTHSTEP"
l.new(cd_.outputs["View Distance"], fr.inputs["Value"])
blk = n.new("ShaderNodeEmission"); blk.inputs["Color"].default_value = (0.0015, 0.0016, 0.0021, 1); blk.inputs["Strength"].default_value = 1.0
mx = n.new("ShaderNodeMixShader"); l.new(fr.outputs[0], mx.inputs[0]); l.new(b.outputs[0], mx.inputs[1]); l.new(blk.outputs[0], mx.inputs[2])
l.new(mx.outputs[0], o.inputs["Surface"])
water.data.materials.append(wm)

# 조명: 수면이 비추는 줄무늬 빛판. 파문이 지나가면 반사된 줄이 휘어진다
from mathutils import Vector
CAM = Vector((0, -4.0, 4.2)) if not MOB else Vector((0, -3.6, 4.6))
AIM = Vector((0, 5.2, 0)) if not MOB else Vector((0, 5.0, 0))
def stripes(name, P, dist, size, bands, base_col, strength):
    d = (P - CAM).normalized(); d.z = -d.z  # 수면에서 반사된 방향
    loc = P + d * dist
    bpy.ops.mesh.primitive_plane_add(size=1, location=loc)
    ob = bpy.context.active_object; ob.name = name; ob.scale = (size[0], size[1], 1)
    ob.rotation_euler = (-d).to_track_quat("Z", "Y").to_euler()
    m, n, l = mat(name)
    o = n.new("ShaderNodeOutputMaterial"); e = n.new("ShaderNodeEmission")
    tc = n.new("ShaderNodeTexCoord"); sp = n.new("ShaderNodeSeparateXYZ"); l.new(tc.outputs["Generated"], sp.inputs[0])
    cr = n.new("ShaderNodeValToRGB"); r = cr.color_ramp
    pts = [(0.0, (0, 0, 0)), (0.14, (0, 0, 0)), (0.26, base_col)]
    for (c, w, col) in bands:
        pts += [(c - w * 1.6, base_col), (c - w * 0.5, col), (c + w * 0.5, col), (c + w * 1.6, base_col)]
    # 빛판 양 끝은 검게 사라진다(먼 수면이 줄 하나를 그대로 비추지 않게)
    pts += [(0.72, base_col), (0.88, (0, 0, 0)), (1.0, (0, 0, 0))]
    r.elements[0].position, r.elements[0].color = pts[0][0], (*pts[0][1], 1)
    r.elements[1].position, r.elements[1].color = pts[-1][0], (*pts[-1][1], 1)
    for (pos, col) in pts[1:-1]:
        el = r.elements.new(pos); el.color = (*col, 1)
    l.new(sp.outputs["Y"], cr.inputs[0]); l.new(cr.outputs[0], e.inputs["Color"])
    e.inputs["Strength"].default_value = strength
    l.new(e.outputs[0], o.inputs["Surface"]); ob.data.materials.append(m)
    ob.visible_camera = False
    return ob
DIM = (0.004, 0.0046, 0.0064)
WHITE = (0.85, 0.9, 1.0)
stripes("studio", AIM, 16.0, (80, 46), [
    (0.30, 0.006, WHITE), (0.38, 0.01, (0.4, 0.45, 0.55)), (0.47, 0.012, LIME),
    (0.555, 0.004, WHITE), (0.64, 0.008, (0.4, 0.45, 0.55))], DIM, 7.0)

# 방울: 떨어지는 순간만 빛나는 작은 점광
drop_lights = []
for i, d in enumerate(DROPS):
    li = bpy.data.lights.new(f"d{i}", "POINT"); li.color = LIME; li.shadow_soft_size = 0.05
    lo = bpy.data.objects.new(f"d{i}", li); lo.location = (d["x"], d["y"], 0.25); sc.collection.objects.link(lo)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=0.035, location=(d["x"], d["y"], 0.6))
    bead = bpy.context.active_object; bpy.ops.object.shade_smooth()
    bm_, be = emit(f"bead{i}", LIME, 6.0); bead.data.materials.append(bm_)
    drop_lights.append((li, lo, bead, be))

# 카메라
camd = bpy.data.cameras.new("cam"); camd.lens_unit = "FOV"
camd.sensor_fit = "VERTICAL" if not MOB else "HORIZONTAL"
camd.angle = math.radians(32) if not MOB else math.radians(44)
camo = bpy.data.objects.new("cam", camd); sc.collection.objects.link(camo); sc.camera = camo
camo.location = CAM
tgt = bpy.data.objects.new("tgt", None); tgt.location = AIM; sc.collection.objects.link(tgt)
con = camo.constraints.new("TRACK_TO"); con.target = tgt; con.track_axis = "TRACK_NEGATIVE_Z"; con.up_axis = "UP_Y"
camd.dof.use_dof = True; camd.dof.aperture_fstop = 2.0
camd.dof.focus_object = tgt

# 후처리: 빛 번짐
def setup_bloom():
    ng = bpy.data.node_groups.new("comp", "CompositorNodeTree")
    ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    rl = ng.nodes.new("CompositorNodeRLayers"); gl = ng.nodes.new("CompositorNodeGlare"); go = ng.nodes.new("NodeGroupOutput")
    gl.inputs["Type"].default_value = "Bloom"
    gl.inputs["Quality"].default_value = "High"
    gl.inputs["Threshold"].default_value = 0.7
    gl.inputs["Strength"].default_value = 0.45
    gl.inputs["Size"].default_value = 0.55
    ng.links.new(rl.outputs["Image"], gl.inputs["Image"]); ng.links.new(gl.outputs["Image"], go.inputs[0])
    sc.compositing_node_group = ng
try:
    setup_bloom(); print("COMPOSITOR OK")
except Exception as e:
    sc.compositing_node_group = None; print("COMPOSITOR SKIP", e)

# ---------- 렌더 ----------
frames = ONLY or list(range(NFRAMES))
t_all = time.time()
co = base.copy()
for f in frames:
    t = f / NFRAMES * T
    co[:, 2] = (field(GX, GY, t) * FADE).ravel()
    mesh.vertices.foreach_set("co", co.ravel()); mesh.update()
    for d, (li, lo, bead, be) in zip(DROPS, drop_lights):
        age = (t - d["t0"]) % T
        # 떨어지기 직전 0.08주기 동안 방울이 내려오고, 닿는 순간 번쩍인 뒤 사라진다
        pre = (d["t0"] - t) % T
        if pre < 0.08:
            bead.location.z = 0.04 + 1.6 * (pre / 0.08) ** 1.6; be.inputs["Strength"].default_value = 6.0
        else:
            bead.location.z = -1; be.inputs["Strength"].default_value = 0.0
        li.energy = 14.0 * math.exp(-age * 14.0)
    sc.render.filepath = os.path.join(OUT, "f%03d" % f)
    s = time.time(); bpy.ops.render.render(write_still=True)
    print("FRAME", f, round(time.time() - s, 1), "s", flush=True)
json.dump({"variant": VARIANT, "size": RES, "frames": NFRAMES, "fps": 24}, open(os.path.join(OUT, "meta.json"), "w"))
print("DONE", len(frames), "frames", round(time.time() - t_all, 1), "s")
