# SIGNAL 첫 화면 지형 렌더 (Blender 5.x).
# 사용: blender --background --factory-startup --python render/terrain.py -- --variant desktop --out web/assets/hero/desktop [--frames 0,40,80] [--samples 48] [--device GPU|CPU]
# 데이터는 web/assets/hero/snapshot.json(렌더 시점에 고정).
# snapshot.json(렌더 시점의 7일 BTC 1시간봉·뉴스 핀)으로 지형을 만들고, 카메라가 핀마다 멈췄다 전체를 내려다보는 장면을 프레임으로 굽는다.
# 프레임마다 핀의 화면 좌표를 anchors.json으로 함께 저장해 웹에서 기사 카드를 그 자리에 붙인다.
import bpy, bmesh, json, math, os, sys, time
import numpy as np
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
def arg(name, default=None):
    return argv[argv.index(name) + 1] if name in argv else default

HERE = os.path.dirname(os.path.abspath(__file__))
VARIANT = arg("--variant", "desktop")
OUT = os.path.abspath(arg("--out", os.path.join(HERE, "out", VARIANT)))
SAMPLES = int(arg("--samples", "48"))
DEVICE = arg("--device", "GPU")
NFRAMES = int(arg("--nframes", "96"))
ONLY = [int(x) for x in arg("--frames", "").split(",") if x != ""]
RES = {"desktop": (1600, 1000), "mobile": (780, 1300)}[VARIANT]
os.makedirs(OUT, exist_ok=True)

snap = json.load(open(os.path.join(HERE, "..", "web", "assets", "hero", "snapshot.json"), encoding="utf-8"))
L, D = 26.0, 24.0
SPAN = snap["end"] - snap["start"]
bars = np.array(snap["bars"], dtype=float)

# ---------- 데이터 → 높이 ----------
t_bars, p_bars = bars[:, 0], bars[:, 1]
pn = (p_bars - p_bars.min()) / max(p_bars.max() - p_bars.min(), 1e-9)
ret = np.concatenate([[0], np.abs(np.diff(np.log(p_bars)))])
k = np.exp(-(np.arange(-9, 10) ** 2) / 18.0)
sm = np.convolve(ret, k / k.sum(), mode="same")
vn = np.minimum(1.35, sm / max(np.quantile(sm, 0.95), 1e-9))
def price_at(t): return np.interp(t, t_bars, pn)
def vol_at(t): return np.interp(t, t_bars, vn)
def x_of(t): return ((t - snap["start"]) / SPAN - 0.5) * L
def t_of(x): return snap["start"] + (x / L + 0.5) * SPAN

def hash2(x, y):
    s = np.sin(x * 127.1 + y * 311.7) * 43758.5453
    return s - np.floor(s)
def vnoise(x, y):
    xi, yi = np.floor(x), np.floor(y)
    xf, yf = x - xi, y - yi
    u, v = xf * xf * (3 - 2 * xf), yf * yf * (3 - 2 * yf)
    a, b, c, d = hash2(xi, yi), hash2(xi + 1, yi), hash2(xi, yi + 1), hash2(xi + 1, yi + 1)
    return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v
def fbm(x, y, o=6):
    s, a, f = 0, 0.5, 1
    for _ in range(o):
        s = s + a * vnoise(x * f, y * f); f *= 2.03; a *= 0.5
    return s
def ridged(x, y, o=6):
    s, a, f = 0, 0.55, 1
    for _ in range(o):
        n = 1 - np.abs(vnoise(x * f, y * f) * 2 - 1); s = s + a * n * n; f *= 2.07; a *= 0.48
    return s
def sstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)

stop_x = np.array([x_of(p["t0"]) for p in snap["pins"]])
def height(x, z):
    t = t_of(x)
    v = np.clip(vol_at(t), 0, 1.35)
    env = np.exp(-((z / 4.2) ** 2))
    h = 0.1 + 0.6 * price_at(t) * np.exp(-((z / 3.5) ** 2))
    h = h + (0.7 + 2.6 * v ** 1.2) * ridged(x * 0.3 + 5.3, z * 0.38 + 1.7) * env
    h = h + (fbm(x * 0.2 + 7, z * 0.26) - 0.4) * 1.5 * (0.45 + 0.55 * np.exp(-((z / 6) ** 2)))
    h = h + (fbm(x * 1.6, z * 1.6 + 3, 5) - 0.5) * 0.12 + (fbm(x * 5.0, z * 5.0 + 9, 3) - 0.5) * 0.03
    for sx in stop_x:
        h = h + 0.35 * np.exp(-((x - sx) ** 2) / 0.25 - (z * z) / 0.8)
    h = h - 0.9 * sstep(4.5, 7, np.abs(z))
    h = h - 3.5 * sstep(5.5, 10.5, -z)  # 산맥 뒤쪽은 어둠 속으로 떨어진다
    return h
PZ = -5.2
def price_y(x): return 2.4 + 1.7 * price_at(t_of(x))

# ---------- 장면 초기화 ----------
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
sc.cycles.adaptive_threshold = 0.02
sc.cycles.use_denoising = True
sc.cycles.denoiser = "OPENIMAGEDENOISE"
sc.cycles.max_bounces = 4
sc.cycles.seed = 7
sc.render.resolution_x, sc.render.resolution_y = RES
sc.render.resolution_percentage = 100
sc.render.film_transparent = False
sc.view_settings.view_transform = "Standard"
sc.view_settings.look = "None"
sc.render.image_settings.file_format = "WEBP"
sc.render.image_settings.quality = 82
sc.render.image_settings.color_mode = "RGB"

BG = (0.0032, 0.0034, 0.0044)
HAZE = (0.010, 0.012, 0.016)
LIME = (0.62, 0.98, 0.10)
world = bpy.data.worlds.new("w"); sc.world = world
world.use_nodes = True
wn = world.node_tree.nodes; wl = world.node_tree.links
wbg = wn["Background"]; wbg.inputs[1].default_value = 1.0
wtc = wn.new("ShaderNodeTexCoord"); wsep = wn.new("ShaderNodeSeparateXYZ"); wl.new(wtc.outputs["Window"], wsep.inputs[0])
wcr = wn.new("ShaderNodeValToRGB"); wcr.color_ramp.elements[0].position = 0.35; wcr.color_ramp.elements[0].color = (*BG, 1)
wcr.color_ramp.elements[1].position = 0.75; wcr.color_ramp.elements[1].color = (0.0062, 0.0068, 0.0092, 1)
wl.new(wsep.outputs["Y"], wcr.inputs[0]); wl.new(wcr.outputs[0], wbg.inputs[0])

def mat(name):
    m = bpy.data.materials.new(name); m.use_nodes = True
    return m, m.node_tree.nodes, m.node_tree.links

# ---------- 지형 ----------
NX, NZ = (900, 760)
xs = np.linspace(-L / 2, L / 2, NX); zs = np.linspace(-D / 2, D / 2, NZ)
X, Z = np.meshgrid(xs, zs)
Hh = height(X, Z)
VOL = np.clip(vol_at(t_of(X)), 0, 1.35) * np.exp(-((Z / 2.6) ** 2)) * np.clip(Hh / 1.6, 0, 1.2)
mesh = bpy.data.meshes.new("terrain")
verts = np.stack([X.ravel(), -Z.ravel(), Hh.ravel()], 1)  # 블렌더: X 시간, Y 깊이(앞이 -), Z 위
ii = np.arange(NX * NZ).reshape(NZ, NX)
faces = np.stack([ii[:-1, :-1].ravel(), ii[:-1, 1:].ravel(), ii[1:, 1:].ravel(), ii[1:, :-1].ravel()], 1)
mesh.vertices.add(len(verts)); mesh.vertices.foreach_set("co", verts.astype(np.float32).ravel())
mesh.loops.add(faces.size); mesh.loops.foreach_set("vertex_index", faces.astype(np.int32).ravel())
mesh.polygons.add(len(faces)); mesh.polygons.foreach_set("loop_start", (np.arange(len(faces)) * 4).astype(np.int32)); mesh.polygons.foreach_set("loop_total", np.full(len(faces), 4, np.int32))
mesh.update(); mesh.validate()
mesh.shade_smooth()
attr = mesh.attributes.new("vol", "FLOAT", "POINT"); attr.data.foreach_set("value", VOL.ravel().astype(np.float32))
terrain = bpy.data.objects.new("terrain", mesh); sc.collection.objects.link(terrain)

m, n, l = mat("rock")
n.clear()
out = n.new("ShaderNodeOutputMaterial")
bsdf = n.new("ShaderNodeBsdfPrincipled")
bsdf.inputs["Base Color"].default_value = (0.04, 0.042, 0.05, 1)
bsdf.inputs["Roughness"].default_value = 0.55
bsdf.inputs["Specular IOR Level"].default_value = 0.35
# 바위 결: 노이즈로 거칠기·색을 살짝 흔든다
tex = n.new("ShaderNodeTexNoise"); tex.inputs["Scale"].default_value = 9.0; tex.inputs["Detail"].default_value = 12.0
ramp = n.new("ShaderNodeValToRGB"); ramp.color_ramp.elements[0].color = (0.010, 0.011, 0.014, 1); ramp.color_ramp.elements[1].color = (0.034, 0.036, 0.044, 1)
l.new(tex.outputs["Fac"], ramp.inputs["Fac"]); l.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
bump = n.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.45; bump.inputs["Distance"].default_value = 0.02
tex2 = n.new("ShaderNodeTexNoise"); tex2.inputs["Scale"].default_value = 40.0; tex2.inputs["Detail"].default_value = 8.0
l.new(tex2.outputs["Fac"], bump.inputs["Height"]); l.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
# 등고선: 높이 z를 일정 간격으로 끊어 가는 빛 선. 굵은 선은 5칸마다
geo = n.new("ShaderNodeNewGeometry")
sep = n.new("ShaderNodeSeparateXYZ"); l.new(geo.outputs["Position"], sep.inputs[0])
def contour(step, width):
    a = n.new("ShaderNodeMath"); a.operation = "MULTIPLY"; a.inputs[1].default_value = 1.0 / step
    l.new(sep.outputs["Z"], a.inputs[0])
    f = n.new("ShaderNodeMath"); f.operation = "FRACT"; l.new(a.outputs[0], f.inputs[0])
    s = n.new("ShaderNodeMath"); s.operation = "SUBTRACT"; s.inputs[1].default_value = 0.5; l.new(f.outputs[0], s.inputs[0])
    ab = n.new("ShaderNodeMath"); ab.operation = "ABSOLUTE"; l.new(s.outputs[0], ab.inputs[0])
    # 0.5 근처(=정수 높이)에서 1
    mr = n.new("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = 0.5 - width / step; mr.inputs["From Max"].default_value = 0.5
    mr.inputs["To Min"].default_value = 0.0; mr.inputs["To Max"].default_value = 1.0; mr.interpolation_type = "SMOOTHSTEP"
    l.new(ab.outputs[0], mr.inputs["Value"])
    return mr.outputs[0]
minor = contour(0.16, 0.0035)
major = contour(0.8, 0.007)
va = n.new("ShaderNodeAttribute"); va.attribute_name = "vol"
hot = n.new("ShaderNodeMapRange"); hot.inputs["From Min"].default_value = 0.2; hot.inputs["From Max"].default_value = 0.85; hot.interpolation_type = "SMOOTHSTEP"
l.new(va.outputs["Fac"], hot.inputs["Value"])
cmix = n.new("ShaderNodeMix"); cmix.data_type = "RGBA"
cmix.inputs["A"].default_value = (0.30, 0.33, 0.40, 1); cmix.inputs["B"].default_value = (*LIME, 1)
l.new(hot.outputs[0], cmix.inputs["Factor"])
mm = n.new("ShaderNodeMath"); mm.operation = "MULTIPLY_ADD"; mm.inputs[1].default_value = 1.8  # minor*0.45 + major*1.8 비슷하게
w1 = n.new("ShaderNodeMath"); w1.operation = "MULTIPLY"; w1.inputs[1].default_value = 0.35; l.new(minor, w1.inputs[0])
l.new(major, mm.inputs[0]); l.new(w1.outputs[0], mm.inputs[2])
lowmask = n.new("ShaderNodeMapRange"); lowmask.inputs["From Min"].default_value = 0.15; lowmask.inputs["From Max"].default_value = 0.5; lowmask.interpolation_type = "SMOOTHSTEP"
l.new(sep.outputs["Z"], lowmask.inputs["Value"])
ya = n.new("ShaderNodeMath"); ya.operation = "ABSOLUTE"; l.new(sep.outputs["Y"], ya.inputs[0])
edge = n.new("ShaderNodeMapRange"); edge.inputs["From Min"].default_value = 3.0; edge.inputs["From Max"].default_value = 4.4; edge.inputs["To Min"].default_value = 1.0; edge.inputs["To Max"].default_value = 0.0
l.new(ya.outputs[0], edge.inputs["Value"])
lm2 = n.new("ShaderNodeMath"); lm2.operation = "MULTIPLY"; l.new(lowmask.outputs[0], lm2.inputs[0]); l.new(edge.outputs[0], lm2.inputs[1])
mm2 = n.new("ShaderNodeMath"); mm2.operation = "MULTIPLY"; l.new(mm.outputs[0], mm2.inputs[0]); l.new(lm2.outputs[0], mm2.inputs[1])
# 뜨거운 곳일수록 선이 밝다
gain = n.new("ShaderNodeMapRange"); gain.inputs["To Min"].default_value = 0.22; gain.inputs["To Max"].default_value = 3.0
l.new(hot.outputs[0], gain.inputs["Value"])
strength = n.new("ShaderNodeMath"); strength.operation = "MULTIPLY"; l.new(mm2.outputs[0], strength.inputs[0]); l.new(gain.outputs[0], strength.inputs[1])
# 거리 안개: 멀어질수록 선과 표면이 배경으로 녹는다
cam = n.new("ShaderNodeCameraData")
fog = n.new("ShaderNodeMapRange"); fog.inputs["From Min"].default_value = 7.0; fog.inputs["From Max"].default_value = 34.0; fog.inputs["To Min"].default_value = 1.0; fog.inputs["To Max"].default_value = 0.0
fog.interpolation_type = "SMOOTHSTEP"; l.new(cam.outputs["View Distance"], fog.inputs["Value"])
s2 = n.new("ShaderNodeMath"); s2.operation = "MULTIPLY"; l.new(strength.outputs[0], s2.inputs[0]); l.new(fog.outputs[0], s2.inputs[1])
l.new(cmix.outputs["Result"], bsdf.inputs["Emission Color"]); l.new(s2.outputs[0], bsdf.inputs["Emission Strength"])
mixfog = n.new("ShaderNodeMixShader"); bgem = n.new("ShaderNodeEmission"); bgem.inputs["Color"].default_value = (*HAZE, 1)
inv = n.new("ShaderNodeMath"); inv.operation = "SUBTRACT"; inv.inputs[0].default_value = 1.0; l.new(fog.outputs[0], inv.inputs[1])
vm_ = n.new("ShaderNodeMapRange"); vm_.inputs["From Min"].default_value = -0.4; vm_.inputs["From Max"].default_value = 0.9; vm_.inputs["To Min"].default_value = 0.55; vm_.inputs["To Max"].default_value = 0.0
vm_.interpolation_type = "SMOOTHSTEP"; l.new(sep.outputs["Z"], vm_.inputs["Value"])
fogsum = n.new("ShaderNodeMath"); fogsum.operation = "ADD"; fogsum.use_clamp = True; l.new(inv.outputs[0], fogsum.inputs[0]); l.new(vm_.outputs[0], fogsum.inputs[1])
inv = fogsum
l.new(inv.outputs[0], mixfog.inputs[0]); l.new(bsdf.outputs[0], mixfog.inputs[1]); l.new(bgem.outputs[0], mixfog.inputs[2])
l.new(mixfog.outputs[0], out.inputs["Surface"])
terrain.data.materials.append(m)

# ---------- 가격 빛줄기 (산맥 뒤 하늘선) ----------
def emit_mat(name, color, strength):
    m, n, l = mat(name); n.clear()
    o = n.new("ShaderNodeOutputMaterial"); e = n.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = (*color, 1); e.inputs["Strength"].default_value = strength
    l.new(e.outputs[0], o.inputs["Surface"]); return m
def poly_curve(name, pts, bevel, material):
    cu = bpy.data.curves.new(name, "CURVE"); cu.dimensions = "3D"; cu.bevel_depth = bevel; cu.bevel_resolution = 3
    sp = cu.splines.new("POLY"); sp.points.add(len(pts) - 1)
    for i, p in enumerate(pts): sp.points[i].co = (*p, 1)
    ob = bpy.data.objects.new(name, cu); sc.collection.objects.link(ob); cu.materials.append(material); return ob
px = np.linspace(-L / 2, L / 2, 520)
poly_curve("price", [(x, -PZ, price_y(x)) for x in px], 0.016, emit_mat("price", LIME, 2.6))
# 가격선 아래 옅은 빛 막
glow_m, n, l = mat("veil"); n.clear()
o = n.new("ShaderNodeOutputMaterial"); e = n.new("ShaderNodeEmission"); tr = n.new("ShaderNodeBsdfTransparent"); mx = n.new("ShaderNodeMixShader")
e.inputs["Color"].default_value = (*LIME, 1); e.inputs["Strength"].default_value = 0.12
tc = n.new("ShaderNodeTexCoord"); sp = n.new("ShaderNodeSeparateXYZ"); l.new(tc.outputs["Generated"], sp.inputs[0])
pw = n.new("ShaderNodeMath"); pw.operation = "POWER"; pw.inputs[1].default_value = 5.0; l.new(sp.outputs["Z"], pw.inputs[0])
# 위(가격선 쪽)가 진하고 아래로 사라지게: 높이 비율의 세제곱만큼 발광
l.new(pw.outputs[0], mx.inputs[0]); l.new(tr.outputs[0], mx.inputs[1]); l.new(e.outputs[0], mx.inputs[2])
l.new(mx.outputs[0], o.inputs["Surface"])
bm = bmesh.new()
prev = None
for x in px[::2]:
    y = price_y(x)
    a = bm.verts.new((x, -PZ, y)); b = bm.verts.new((x, -PZ, y - 1.2))
    if prev: bm.faces.new((prev[0], prev[1], b, a))
    prev = (a, b)
vm = bpy.data.meshes.new("veil"); bm.to_mesh(vm); bm.free()
veil = bpy.data.objects.new("veil", vm); sc.collection.objects.link(veil); vm.materials.append(glow_m)
veil.visible_shadow = False

# ---------- 뉴스 핀 ----------
white_m = emit_mat("pinwhite", (0.85, 0.88, 0.95), 1.1)
lime_m = emit_mat("pinlime", LIME, 2.2)
ring_m = emit_mat("ring", LIME, 1.4)
pins = []
for i, sx in enumerate(stop_x):
    y0 = float(height(np.array([sx]), np.array([0.0]))[0])
    y1 = y0 + 1.5
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.008, depth=y1 - y0, location=(sx, 0, (y0 + y1) / 2))
    st = bpy.context.active_object; st.data.materials.append(white_m); st.name = f"stem{i}"
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=0.05, location=(sx, 0, y1))
    hd = bpy.context.active_object; hd.data.materials.append(lime_m); bpy.ops.object.shade_smooth(); hd.name = f"head{i}"
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=0.035, location=(sx, 0, y0))
    ft = bpy.context.active_object; ft.data.materials.append(white_m); bpy.ops.object.shade_smooth()
    for rr in (0.22, 0.42):
        bpy.ops.mesh.primitive_torus_add(major_radius=rr, minor_radius=0.006, major_segments=96, minor_segments=8, location=(sx, 0, y0 + 0.03))
        bpy.context.active_object.data.materials.append(ring_m)
    # 핀 머리 아래 작은 조명: 봉우리 바위를 연두빛으로 비춘다
    li = bpy.data.lights.new(f"pl{i}", "POINT"); li.energy = 25; li.color = LIME; li.shadow_soft_size = 0.2
    lo = bpy.data.objects.new(f"pl{i}", li); lo.location = (sx, -0.3, y0 + 0.5); sc.collection.objects.link(lo)
    pins.append((sx, y0, y1))
# 지금 표시: 가격선 오른쪽 끝
bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=0.09, location=(L / 2, -PZ, price_y(L / 2 - 1e-3)))
bpy.context.active_object.data.materials.append(lime_m)

# ---------- 조명 ----------
sun = bpy.data.lights.new("moon", "SUN"); sun.energy = 2.4; sun.color = (0.70, 0.78, 1.0); sun.angle = math.radians(4)
so = bpy.data.objects.new("moon", sun); so.rotation_euler = (math.radians(74), 0, math.radians(170)); sc.collection.objects.link(so)
rim = bpy.data.lights.new("rim", "SUN"); rim.energy = 0.35; rim.color = (0.85, 0.9, 1.0); rim.angle = math.radians(3)
ro = bpy.data.objects.new("rim", rim); ro.rotation_euler = (math.radians(45), 0, math.radians(-35)); sc.collection.objects.link(ro)

# ---------- 카메라 동선 (웹 시안과 같은 흐름) ----------
camd = bpy.data.cameras.new("cam"); camd.lens_unit = "FOV"
camd.sensor_fit = "VERTICAL" if VARIANT == "desktop" else "HORIZONTAL"
camd.angle = math.radians(36) if VARIANT == "desktop" else math.radians(62)
camd.dof.use_dof = True; camd.dof.aperture_fstop = 0.9
camo = bpy.data.objects.new("cam", camd); sc.collection.objects.link(camo); sc.camera = camo
tgt = bpy.data.objects.new("tgt", None); sc.collection.objects.link(tgt)
con = camo.constraints.new("TRACK_TO"); con.target = tgt; con.track_axis = "TRACK_NEGATIVE_Z"; con.up_axis = "UP_Y"
camd.dof.focus_object = tgt

SLOTS = [(0.22, 0.34), (0.44, 0.56), (0.66, 0.78)]
def plan():
    mob = VARIANT == "mobile"
    k = []
    # (진행도, 카메라 x, 높이, 앞쪽 거리), (바라보는 x, 높이, 깊이)  — 웹 좌표(z 앞이 +)를 블렌더(y 앞이 -)로 바꿔 쓴다
    intro = ((-L / 2 + 0.2, 4.4, 7.2), (-L / 2 + 5.5, -0.6, -1.5)) if mob else ((-L / 2 + 0.8, 1.72, 6.6), (-L / 2 + 9.5, 1.7, -1))
    k.append((0.0,) + intro)
    k.append((0.12, (intro[0][0] + 1.4, intro[0][1] - 0.2, intro[0][2] - 0.6), intro[1]))
    for i, (sx, y0, y1) in enumerate(pins):
        a, b = SLOTS[i]
        mid = y0 + 0.6
        dz, dx, dy, ay = (5.6, -0.8, 1.4, -1.3) if mob else (5.4, -3.4, 0.35, 0.0)
        k.append((a, (sx + dx, mid + dy, dz), (sx + 0.4, mid + ay, -1)))
        k.append((b, (sx + dx + 0.6, mid + dy + 0.15, dz - 0.4), (sx + 0.6, mid + ay, -1)))
    over = ((2.0, 8.5, 10.5), (2.0, -0.4, -2.0)) if mob else ((0.5, 8, 17), (0.5, 1.8, 0))
    k.append((0.9,) + over)
    k.append((1.0, (over[0][0], over[0][1] + 0.4, over[0][2] + 0.4), over[1]))
    return k
def smooth(t): return t * t * (3 - 2 * t)
def pose(p):
    k = plan(); i = 0
    while i < len(k) - 2 and p > k[i + 1][0]: i += 1
    t = smooth(min(1, max(0, (p - k[i][0]) / (k[i + 1][0] - k[i][0]))))
    lerp = lambda a, b: tuple(a[j] + (b[j] - a[j]) * t for j in range(3))
    pos, at = lerp(k[i][1], k[i + 1][1]), lerp(k[i][2], k[i + 1][2])
    to_b = lambda v: (v[0], -v[2], v[1])
    return to_b(pos), to_b(at)

# ---------- 후처리: 빛 번짐 ----------
def setup_bloom():
    ng = bpy.data.node_groups.new("comp", "CompositorNodeTree")
    ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    rl = ng.nodes.new("CompositorNodeRLayers"); gl = ng.nodes.new("CompositorNodeGlare"); go = ng.nodes.new("NodeGroupOutput")
    gl.inputs["Type"].default_value = "Bloom"
    gl.inputs["Quality"].default_value = "High"
    gl.inputs["Threshold"].default_value = 0.85
    gl.inputs["Strength"].default_value = 0.5
    gl.inputs["Size"].default_value = 0.5
    ng.links.new(rl.outputs["Image"], gl.inputs["Image"]); ng.links.new(gl.outputs["Image"], go.inputs[0])
    sc.compositing_node_group = ng
try:
    setup_bloom(); print("COMPOSITOR OK")
except Exception as e:
    sc.compositing_node_group = None; print("COMPOSITOR SKIP", e)

# ---------- 렌더 ----------
anchors = {"variant": VARIANT, "size": RES, "frames": NFRAMES, "slots": SLOTS, "pins": [p["id"] for p in snap["pins"]], "xy": []}
from bpy_extras.object_utils import world_to_camera_view
frames = ONLY or list(range(NFRAMES))
t_all = time.time()
for f in range(NFRAMES):
    p = f / (NFRAMES - 1)
    pos, at = pose(p)
    camo.location = pos; tgt.location = at
    bpy.context.view_layer.update()
    xy = []
    for (sx, y0, y1) in pins:
        v = world_to_camera_view(sc, camo, Vector((sx, 0, y1)))
        xy.append([round(v.x, 4), round(1 - v.y, 4), round(v.z, 3)])
    anchors["xy"].append(xy)
    if f in frames:
        sc.render.filepath = os.path.join(OUT, "f%03d" % f)
        t = time.time(); bpy.ops.render.render(write_still=True)
        print("FRAME", f, round(time.time() - t, 1), "s", flush=True)
json.dump(anchors, open(os.path.join(OUT, "anchors.json"), "w"))
print("DONE", len(frames), "frames", round(time.time() - t_all, 1), "s")
