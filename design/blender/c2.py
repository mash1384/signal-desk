# C2 · 한 획 — 굵은 검은 선 하나가 왼쪽 아래 화면 밖에서 들어와 고리를 따라 돌고, 끝이 안쪽으로 말려 들어가 중심에서 멈춘다.
# 그 자리에서 원반이 부풀며(배경색 틈과 함께) 선의 안쪽 부분을 지워 정확히 고리만 남긴다. 한 획이 고리와 원반이 되는 이야기.
# 이어 심볼이 왼쪽으로 비켜서고, DELFONA 가 넓은 자간에서 제 자간으로 모이며(트래킹 인) 배경색에서 검정으로 짙어진다.
# 참고: Dribbble nomics(한 획이 글자가 됨), yuno(선 → 점 → 글자), OpenAI(넓게 → 모여 로고).
import sys; sys.path.insert(0, '/tmp/bl2')
import importlib, k2; importlib.reload(k2)
from k2 import *
args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
RES = int(args[0]) if args else 1080; ST = [int(x) for x in args[1].split(',')] if len(args) > 1 else None
FR = 270; sc, cam = reset(FR, RES, out='/tmp/bl2/out/c2/')
EM, GAP = 57.7, 34.6; CAP = cap_height(EM)
root = empty('root'); M = empty('M', root); m = mark(M)
for k in ('ro', 'ri'): show(m[k], 1, False)                 # 고리는 선으로 그린다(겹 고리는 쓰지 않음)
LM = [anim_mat(f'l{i}', BGC) for i in range(7)]
L_letters = letters_hdr('DELFONA', mat=[x[0] for x in LM], parent=root)
LW = WM_END; FW = LW / 0.8; ortho(cam, FW)
X0 = -LW / 2; MX = X0 + 50; TX = X0 + WM_X[0]; TW = WM_END - WM_X[0]; BASE = WM_BASE; CAP = 11.25 * PX; EM = WM_SIZE
A, D = (53, 47), (46, 54)
# 경로: 들어오는 곡선(2차 베지어) → 원 A 를 따라 시계 방향 → 오른쪽 아래 끝을 지나 중심 D 로 말려 들어감
# 고리 중심선(r31)이 달 경계(r34)와 만나는 각 = 왼쪽 위 끝
def rb(a): return math.dist((A[0] + 31 * math.cos(a), A[1] + 31 * math.sin(a)), D) - 34
lo_, hi_ = -2.8, -1.8
for _ in range(60):
    mid = (lo_ + hi_) / 2
    if rb(lo_) * rb(mid) <= 0: hi_ = mid
    else: lo_ = mid
a0 = (lo_ + hi_) / 2; T = (A[0] + 31 * math.cos(a0), A[1] + 31 * math.sin(a0))
tg = (-math.sin(a0), math.cos(a0)); E0 = (-70, 125); C = (T[0] - 45 * tg[0], T[1] - 45 * tg[1])
pts = []
for i in range(80):
    u = i / 80
    pts.append(((1 - u) ** 2 * E0[0] + 2 * (1 - u) * u * C[0] + u * u * T[0], (1 - u) ** 2 * E0[1] + 2 * (1 - u) * u * C[1] + u * u * T[1]))
pts += [(A[0] + 31 * math.cos(a0 + (0.79 - a0) * i / 160), A[1] + 31 * math.sin(a0 + (0.79 - a0) * i / 160)) for i in range(160)]
for i in range(1, 121):
    s = i / 120; a = 0.79 + 2.2 * s; c = (lerp(A[0], D[0], s), lerp(A[1], D[1], s)); r = 31 * (1 - s) ** 1.4
    pts.append((c[0] + r * math.cos(a), c[1] + r * math.sin(a)))
st, cum, LEN = stroke('stroke', pts, 3.2, BLACK, 1, M)
s_tail_final = cum[72]                                          # 들어오는 곡선 안쪽(달 r34 안)에서 꼬리가 멈춘다 → 가려짐
head = disc('head', 1.6, BLACK, 1, M); tail = disc('tail', 1.6, BLACK, 1, M)
def frame(f):
    z = lerp(4.6, 1.0, seg(f, 70, 168, INOUT)); M.scale = (z, z, 1)
    M.location = Vector((lerp(0, MX, seg(f, 152, 198, INOUT)) * K, 0, 0))
    h = lerp(cum[30], 1, seg(f, 2, 116, bez(0.45, 0, 0.2, 1)))  # 화면 가장자리 근처에서 시작
    t = lerp(cum[22], s_tail_final, seg(f, 22, 124, INOUT)); t = min(t, max(h - 0.02, 0))
    st.data.bevel_factor_end = h; st.data.bevel_factor_start = t
    hx, hy = at(pts, cum, h); place(head, hx, hy, 1); tx, ty = at(pts, cum, t); place(tail, tx, ty, 1)
    # 원반 + 틈(달): 중심에서 부풀어 선의 안쪽을 지운다
    p = seg(f, 112, 146, BACK); setr(m['disc'], max(30 * p, 1e-3)); setr(m['moon'], max(34 * min(1, seg(f, 108, 140, OUT)), 1e-3))
    for i, (o, x, adv) in enumerate(L_letters):
        q = seg(f, 168 + i * 2.5, 214 + i * 2.5, EXPO)
        wide = x + 0.62 * EM * i                       # 넓은 자간에서 출발
        o.location = Vector(((X0 + lerp(wide, x, q)) * K, BASE * K, 0.025))
        c = [lerp(a, 0, q) for a in lin(BGC)]; LM[i][1].inputs[0].default_value = (*c, 1); LM[i][1].inputs[0].keyframe_insert('default_value', frame=f)
for f in range(1, FR + 1):
    frame(f); keyall([M, head, tail, m['disc'], m['moon']] + [o for o, _, _ in L_letters], f); keystroke(st, f)
meta('/tmp/bl2/out/c2.json', {'FW': FW, 'box': [(MX - 50 + FW / 2) / FW, (FW / 2 - 50) / FW, 100 / FW], 'frames': FR, 'fps': 60})
bpy.ops.wm.save_as_mainfile(filepath='/tmp/bl2/c2.blend')
render(sc, ST, 'c2')
