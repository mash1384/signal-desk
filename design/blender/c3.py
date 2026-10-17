# C3 · 궤도 착지 — 화면 가운데 점이 '톡' 원반으로 튀어나오고(눌렸다 펴짐), 짧은 고리 조각이 원반 둘레를 빠르게 한 바퀴 반 돌며 점점 길어져
# 오른쪽 위에 스프링으로 착지한다. 착지 순간 심볼 전체가 한 번 '쿵' 하고(살짝 커졌다 돌아옴), 물러나며 왼쪽으로 비켜서면
# 검은 막대가 오른쪽으로 쭉 뻗었다가 왼쪽부터 걷히며 DELFONA 를 남긴다.
# 참고: Dribbble Solaris(점 → 행성 → 궤도 고리), KANTIV(조각이 돌며 맞물림 + 모션 블러), selected.design(검은 상자가 글자를 쓸고 지나감), 0xchange(착지 펄스).
import sys; sys.path.insert(0, '/tmp/bl2')
import importlib, k2; importlib.reload(k2)
from k2 import *
args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
RES = int(args[0]) if args else 1080; ST = [int(x) for x in args[1].split(',')] if len(args) > 1 else None
FR = 270; sc, cam = reset(FR, RES, out='/tmp/bl2/out/c3/')
EM, GAP = 57.7, 34.6; CAP = cap_height(EM)
root = empty('root'); M = empty('M', root); m = mark(M)
for k in ('ro', 'ri'): show(m[k], 1, False)
A, D = (53, 47), (46, 54)
# 고리: 원 A(r31) 위의 굵기 3.2 선(달 r34 가 안쪽을 가려 끝이 정확히 잘린다). 원반 중심 D 를 축으로 도는 부모에 단다.
orb = empty('orb', M); place(orb, *D, 0)
circ = [(A[0] - D[0] + 50 + 31 * math.cos(2 * math.pi * i / 360), A[1] - D[1] + 50 + 31 * math.sin(2 * math.pi * i / 360)) for i in range(361)]
st, cum, LEN = stroke('ring', circ, 3.2, BLACK, 1, orb)
L_letters = letters_hdr('DELFONA', mat=flat(BLACK), parent=root)
LW = WM_END; FW = LW / 0.8; ortho(cam, FW)
X0 = -LW / 2; MX = X0 + 50; TX = X0 + WM_X[0]; TW = WM_END - WM_X[0]; BASE = WM_BASE; CAP = 11.25 * PX; EM = WM_SIZE
for o, x, adv in L_letters: o.location = Vector(((X0 + x) * K, BASE * K, 0.025)); show(o, 1, False); show(o, 196, True)
bar = rect('bar', 1, CAP * 1.5, BLACK, 0.9, root)
SP = spring(0.16)
# 고리 위 '보이는 쪽' 가운데 각(원 A 기준, 오른쪽 위) — 조각은 여기를 중심으로 자란다
AM = math.atan2(-1, 1)
def frame(f):
    z = lerp(3.4, 1.0, seg(f, 96, 176, INOUT)); pulse = 1 + 0.07 * math.sin(math.pi * seg(f, 84, 104, OUT))
    M.scale = (z * pulse, z * pulse, 1); M.location = Vector((lerp(0, MX, seg(f, 150, 190, INOUT)) * K, 0, 0))
    # 원반: 점 → 눌렸다 펴지며 r30 (가로·세로 따로)
    p = seg(f, 4, 36, BACK); sq = 1 + 0.12 * math.sin(math.pi * seg(f, 18, 44, OUT))
    m['disc'].scale = (max(30 * p * sq, 1e-3) * K, max(30 * p / sq, 1e-3) * K, 1); setr(m['moon'], max(34 * seg(f, 4, 36, OUT), 1e-3))
    # 고리 조각: 한 바퀴 반(-540°) 돌다 스프링 착지, 길이는 짧은 조각 → 원 전체
    q = SP(min(1, max(0, (f - 26) / 70))); orb.rotation_euler.z = math.radians(lerp(540, 0, q))
    half = lerp(0.04, 0.5, seg(f, 26, 92, bez(0.5, 0, 0.3, 1)))
    c = (AM % (2 * math.pi)) / (2 * math.pi)
    st.data.bevel_factor_start = max(0.0, c - half) if half < 0.5 else 0.0; st.data.bevel_factor_end = min(1.0, c + half) if half < 0.5 else 1.0
    st.hide_render = f < 26
    # 글자 막대: 왼쪽 끝 고정으로 뻗었다가(EXPO) 왼쪽부터 걷힘
    g = seg(f, 172, 196, EXPO); r_ = seg(f, 198, 228, EXPO)
    left, right = TX - 6 + (TW + 12) * r_, TX - 6 + (TW + 12) * g
    w = max(right - left, 1e-3); bar.scale = (w * K, CAP * 1.5 * K, 1); bar.location = Vector(((left + w / 2) * K, (BASE + CAP / 2) * K, 0.045))
    bar.hide_render = not (172 < f < 229)
for f in range(1, FR + 1):
    frame(f); keyall([M, orb, m['disc'], m['moon'], bar], f); keystroke(st, f); st.keyframe_insert('hide_render', frame=f); bar.keyframe_insert('hide_render', frame=f)
meta('/tmp/bl2/out/c3.json', {'FW': FW, 'box': [(MX - 50 + FW / 2) / FW, (FW / 2 - 50) / FW, 100 / FW], 'frames': FR, 'fps': 60})
bpy.ops.wm.save_as_mainfile(filepath='/tmp/bl2/c3.blend')
render(sc, ST, 'c3')
