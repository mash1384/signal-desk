# Delfona 2D 브랜드 모션 공통(Blender 5.2, 정사영 카메라 + 평면 단색 + 진짜 모션 블러).
# 심볼은 N3 그대로를 '겹'으로 만든다: [뒤] 고리 바깥 원(검정) → 고리 안쪽 원(배경색) → 달 r34(배경색) → [앞] 원반 r30(검정). 겹친 결과가 정확히 marks2 N3.
# 글자: Michroma 대문자 DELFONA, 헤더 비율(심볼 상자 26px : 글자 15px : 간격 9px : 자간 .24em)을 그대로.
import bpy, math, json
from mathutils import Vector
K = 0.01                                          # 심볼 1 단위 = 0.01 m (상자 100 = 1 m)
BG = (247, 249, 252)
def lin(c): return tuple(((v / 255) / 12.92) if v / 255 <= 0.04045 else (((v / 255) + 0.055) / 1.055) ** 2.4 for v in c)
def bez(x1, y1, x2, y2):
    cx = 3 * x1; bx = 3 * (x2 - x1) - cx; ax = 1 - cx - bx; cy = 3 * y1; by = 3 * (y2 - y1) - cy; ay = 1 - cy - by
    def f(x):
        if x <= 0: return 0.0
        if x >= 1: return 1.0
        lo, hi, t = 0.0, 1.0, x
        for _ in range(48):
            if ((ax * t + bx) * t + cx) * t < x: lo = t
            else: hi = t
            t = (lo + hi) / 2
        return ((ay * t + by) * t + cy) * t
    return f
OUT, INOUT, BACK, IN = bez(0.23, 1, 0.32, 1), bez(0.77, 0, 0.175, 1), bez(0.34, 1.56, 0.64, 1), bez(0.55, 0, 1, 0.45)
EXPO = bez(0.16, 1, 0.3, 1)
def spring(bounce=0.2):
    z = 1 - bounce; w = 2 * math.pi * 1.6; wd = w * math.sqrt(max(1e-4, 1 - z * z))
    return lambda p: 1.0 if p >= 1 else (0.0 if p <= 0 else 1 - math.exp(-z * w * p) * (math.cos(wd * p) + (z * w / wd) * math.sin(wd * p)))
def seg(f, a, b, e=INOUT): return e(min(1, max(0, (f - a) / (b - a))))
def lerp(a, b, t): return a + (b - a) * t
def U(x, y): return Vector(((x - 50) * K, (50 - y) * K, 0))     # 심볼 좌표 → 평면(X, Y)

def reset(frames, res=1080, fps=60, out='/tmp/bl2/out/x/'):
    bpy.ops.wm.read_factory_settings(use_empty=True); sc = bpy.context.scene
    sc.frame_start, sc.frame_end, sc.render.fps = 1, frames, fps
    sc.render.resolution_x = sc.render.resolution_y = res; sc.render.engine = 'BLENDER_EEVEE'; sc.eevee.taa_render_samples = 32
    sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.5; sc.eevee.motion_blur_steps = 8 if hasattr(sc.eevee, 'motion_blur_steps') else None
    sc.render.filter_size = 1.2
    sc.view_settings.view_transform = 'Standard'; sc.view_settings.look = 'None'
    sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGB'; sc.render.filepath = out
    w = bpy.data.worlds.new('W'); sc.world = w; w.use_nodes = True; w.node_tree.nodes['Background'].inputs[0].default_value = (*lin(BG), 1)
    cd = bpy.data.cameras.new('cam'); cd.type = 'ORTHO'; cam = bpy.data.objects.new('cam', cd); sc.collection.objects.link(cam); sc.camera = cam
    cam.location = (0, 0, 10); cd.clip_end = 100
    return sc, cam
_mats = {}
def flat(rgb):
    if rgb in _mats: return _mats[rgb]
    m = bpy.data.materials.new(str(rgb)); m.use_nodes = True; nt = m.node_tree; nt.nodes.remove(nt.nodes['Principled BSDF'])
    e = nt.nodes.new('ShaderNodeEmission'); e.inputs[0].default_value = (*lin(rgb), 1); e.inputs[1].default_value = 1
    nt.links.new(e.outputs[0], nt.nodes['Material Output'].inputs[0]); _mats[rgb] = m; return m
def anim_mat(name, rgb):
    """색을 애니메이션할 수 있는 단색(글자 페이드 = 배경색 → 검정)."""
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; nt.nodes.remove(nt.nodes['Principled BSDF'])
    e = nt.nodes.new('ShaderNodeEmission'); e.inputs[0].default_value = (*lin(rgb), 1); nt.links.new(e.outputs[0], nt.nodes['Material Output'].inputs[0]); return m, e
BLACK, BGC = (0, 0, 0), BG
def disc(name, r, rgb, z, parent=None, n=256):
    bpy.ops.mesh.primitive_circle_add(vertices=n, radius=1, fill_type='NGON', location=(0, 0, 0)); o = bpy.context.object; o.name = name
    o.data.materials.append(flat(rgb) if isinstance(rgb, tuple) else rgb); o.scale = (r * K, r * K, 1); o.location.z = z * 0.05
    if parent: o.parent = parent
    return o
def empty(name, parent=None):
    e = bpy.data.objects.new(name, None); bpy.context.scene.collection.objects.link(e)
    if parent: e.parent = parent
    return e
def place(o, x, y, z=None):
    v = U(x, y); o.location.x, o.location.y = v.x, v.y
    if z is not None: o.location.z = z * 0.05
def rect(name, w, h, rgb, z, parent=None):
    bpy.ops.mesh.primitive_plane_add(size=1); o = bpy.context.object; o.name = name; o.scale = (w * K, h * K, 1); o.location.z = z * 0.05
    o.data.materials.append(flat(rgb) if isinstance(rgb, tuple) else rgb)
    if parent: o.parent = parent
    return o
FONT = None
def letters(word='DELFONA', em=57.7, track=0.24, mat=None, parent=None, z=1):
    """글자를 한 자씩 따로(따로 움직이게). 반환: [(obj, x0)] — x0 는 글자 왼쪽(심볼 단위), 높이는 대문자 기준선 0."""
    global FONT
    FONT = FONT or bpy.data.fonts.load('/tmp/bl2/Michroma.ttf')
    out, x = [], 0.0
    for i, ch in enumerate(word):
        cu = bpy.data.curves.new(f'ch{i}', 'FONT'); cu.body = ch; cu.font = FONT; cu.size = em * K; cu.align_x = 'LEFT'; cu.align_y = 'BOTTOM_BASELINE'
        o = bpy.data.objects.new(f'ch{i}', cu); bpy.context.scene.collection.objects.link(o)
        if mat: o.data.materials.append(mat[i] if isinstance(mat, list) else mat)
        if parent: o.parent = parent
        bpy.context.view_layer.update(); adv = o.dimensions.x / K
        out.append([o, x, adv]); x += adv + track * em + (0.0 if ch != ' ' else em * 0.3)
    return out, x - track * em
def cap_height(em=57.7):
    global FONT
    FONT = FONT or bpy.data.fonts.load('/tmp/bl2/Michroma.ttf')
    cu = bpy.data.curves.new('tmpH', 'FONT'); cu.body = 'H'; cu.font = FONT; cu.size = em * K; o = bpy.data.objects.new('tmpH', cu); bpy.context.scene.collection.objects.link(o)
    bpy.context.view_layer.update(); h = o.dimensions.y / K; bpy.data.objects.remove(o); return h
# 마크(N3) 겹: 부모 empty 'M' 아래(원점 = 심볼 상자 중심 50,50)
def mark(parent):
    o = {}
    o['ro'] = disc('ringOuter', 32.6, BLACK, 1, parent); place(o['ro'], 53, 47, 1)
    o['ri'] = disc('ringInner', 29.4, BGC, 2, parent); place(o['ri'], 53, 47, 2)
    o['moon'] = disc('moon', 34, BGC, 3, parent); place(o['moon'], 46, 54, 3)
    o['disc'] = disc('disc', 30, BLACK, 4, parent); place(o['disc'], 46, 54, 4)
    return o
def setr(o, r): o.scale = (r * K, r * K, 1)
def keyall(objs, f):
    for o in objs:
        o.keyframe_insert('location', frame=f); o.keyframe_insert('scale', frame=f); o.keyframe_insert('rotation_euler', frame=f)
def ortho(cam, frame_units): cam.data.ortho_scale = frame_units * K   # 화면 가로 = frame_units 심볼 단위
def meta(path, d): json.dump(d, open(path, 'w'))
def render(sc, stills=None, tag='x'):
    if stills:
        for f in stills: sc.frame_set(f); sc.render.filepath = f'/tmp/bl2/out/{tag}_s{f:04d}.png'; bpy.ops.render.render(write_still=True)
    else: bpy.ops.render.render(animation=True)

def stroke(name, pts, width, rgb, z, parent=None):
    """심볼 좌표 점들 → 굵기 width 인 선(관 단면, 위에서 보면 평면 선). 반환: (obj, 누적길이 비율 목록)."""
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = width / 2 * K; cu.bevel_resolution = 4; cu.use_fill_caps = True
    cu.bevel_factor_mapping_start = 'SPLINE'; cu.bevel_factor_mapping_end = 'SPLINE'  # 실제 길이 기준
    sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
    for i, (x, y) in enumerate(pts): v = U(x, y); sp.points[i].co = (v.x, v.y, 0, 1)
    o = bpy.data.objects.new(name, cu); bpy.context.scene.collection.objects.link(o); o.location.z = z * 0.05
    o.data.materials.append(flat(rgb)); 
    if parent: o.parent = parent
    L = [0.0]
    for i in range(1, len(pts)): L.append(L[-1] + math.dist(pts[i], pts[i - 1]))
    return o, [l / L[-1] for l in L], L[-1]
def at(pts, cum, s):
    """경로 비율 s 지점의 심볼 좌표."""
    s = min(1, max(0, s))
    for i in range(1, len(cum)):
        if cum[i] >= s:
            t = (s - cum[i - 1]) / max(cum[i] - cum[i - 1], 1e-9); return (lerp(pts[i - 1][0], pts[i][0], t), lerp(pts[i - 1][1], pts[i][1], t))
    return pts[-1]
def keystroke(o, f):
    o.data.keyframe_insert('bevel_factor_start', frame=f); o.data.keyframe_insert('bevel_factor_end', frame=f)
def show(o, f, vis):
    o.hide_render = not vis; o.keyframe_insert('hide_render', frame=f)

# 헤더에서 잰 실제 글자 자리(px, 심볼 상자 왼쪽 기준)와 기준선 — 영상 마지막 장면이 헤더 로고와 화소 단위로 겹치게
HM = json.load(open('/tmp/bl2/header_metrics.json')); PX = 100 / HM['box'][2]          # 1px = 3.846 단위
WM_SIZE = 57.7 * (11.25 * PX) / 24.5097354054451                                       # 대문자 높이(CSS 11.25px)에 맞춘 Blender 글자 크기
WM_BASE = -HM['baseline'] * PX                                                           # 심볼 가운데 기준 기준선(위 = +)
WM_X = [x * PX for x, w in HM['xs']]                                                    # 상자 왼쪽 기준 글자 왼쪽
WM_END = (HM['xs'][-1][0] + HM['xs'][-1][1] - 3.6) * PX                                 # 마지막 글자 끝(뒤 자간 제외)
def letters_hdr(word='DELFONA', mat=None, parent=None):
    global FONT
    FONT = FONT or bpy.data.fonts.load('/tmp/bl2/Michroma.ttf')
    out = []
    for i, ch in enumerate(word):
        cu = bpy.data.curves.new(f'ch{i}', 'FONT'); cu.body = ch; cu.font = FONT; cu.size = WM_SIZE * K; cu.align_x = 'LEFT'; cu.align_y = 'BOTTOM_BASELINE'
        o = bpy.data.objects.new(f'ch{i}', cu); bpy.context.scene.collection.objects.link(o)
        if mat: o.data.materials.append(mat[i] if isinstance(mat, list) else mat)
        if parent: o.parent = parent
        out.append([o, WM_X[i], 0])
    return out
