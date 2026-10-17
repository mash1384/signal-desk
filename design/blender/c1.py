# C1 · 개기일식 — 화면을 꽉 채우는 검은 해(원)가 점에서 튀어나오듯 커지고, 보이지 않는 달(배경색 원)이 왼쪽 아래에서 미끄러져 와 해를 갉아먹어 초승달이 된다.
# 초승달은 가는 고리로 졸아들고, 그 안쪽에 검은 원반이 '톡' 튀어나온다. 그동안 전체가 크게 → 작게 물러나며(크기 대비), 심볼이 왼쪽으로 비켜서면 DELFONA 가 아래에서 한 자씩 올라온다.
# 참고: Dribbble Origin(큰 형태 → 작은 점 → 합쳐짐 → 글자), Solaris(점 → 행성 → 고리), 0xchange(크게 → 작게 + 글자 밀려 나옴).
import sys; sys.path.insert(0, '/tmp/bl2')
import importlib, k2; importlib.reload(k2)
from k2 import *
args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
RES = int(args[0]) if args else 1080; ST = [int(x) for x in args[1].split(',')] if len(args) > 1 else None
FR = 270; sc, cam = reset(FR, RES, out='/tmp/bl2/out/c1/')
EM, GAP = 57.7, 34.6; CAP = cap_height(EM)
root = empty('root'); M = empty('M', root); m = mark(M)
L_letters = letters_hdr('DELFONA', mat=[anim_mat(f'l{i}', BLACK)[0] for i in range(7)], parent=root)
LW = WM_END; FW = LW / 0.8; ortho(cam, FW)
X0 = -LW / 2; MX = X0 + 50; TX = X0 + WM_X[0]; TW = WM_END - WM_X[0]; BASE = WM_BASE; CAP = 11.25 * PX; EM = WM_SIZE
for o, x, adv in L_letters: o.location = Vector(((X0 + x) * K, BASE * K, 0.025))
# 글자 가림막: 기준선 아래를 배경색 띠로 가려 글자가 그 밑에서 올라온다
mask = rect('mask', TW + 40, EM * 1.2, BGC, 0.8, root); mask.location = Vector(((TX + TW / 2) * K, (BASE - EM * 0.6) * K, 0.04))  # 글자보다 앞, 심볼보다 뒤
A, D = (53, 47), (46, 54)
def frame(f):
    # 전체 크기: 처음엔 심볼이 화면보다 크다(×5.2) → ×1 (끝은 제자리), 왼쪽으로 비켜서기
    # 물러나기: 크기를 로그 공간에서 보간해야 체감 속도가 고르다(선형 보간은 끝에서 갑자기 쪼그라드는 느낌)
    ZE = bez(0.6, 0, 0.25, 1); z = math.exp(lerp(math.log(5.2), 0.0, seg(f, 70, 188, ZE))); M.scale = (z, z, 1)   # 일식이 끝날 때까지 크게 머물다 물러남
    M.location = Vector((lerp(0, MX, seg(f, 150, 212, bez(0.5, 0, 0.2, 1))) * K, lerp(-12, 0, seg(f, 70, 188, ZE)) * K, 0))
    # 해(고리 바깥 원): 점 → 꽉 찬 원(살짝 지나쳤다 돌아옴)
    r = math.exp(lerp(math.log(3.2), math.log(32.6), seg(f, 1, 50, bez(0.35, 0, 0.2, 1)))); setr(m['ro'], r)   # 점 → 해: 크기를 로그로 키워 처음에 '확' 커지지 않게
    # 달: 왼쪽 아래 멀리서 → D
    t = seg(f, 22, 92, INOUT); place(m['moon'], lerp(D[0] - 80, D[0], t), lerp(D[1] + 80, D[1], t), 3)
    # 해가 고리로: 안쪽 구멍이 0 → 29.4
    setr(m['ri'], max(29.4 * seg(f, 82, 122, INOUT), 1e-3))
    # 원반: 점 → r30 (튀어나옴)
    setr(m['disc'], max(30 * seg(f, 96, 152, bez(0.3, 1.18, 0.6, 1)), 1e-3))   # 살짝만 지나쳤다 돌아옴
    for i, (o, x, adv) in enumerate(L_letters):
        p = seg(f, 180 + i * 3.2, 214 + i * 3.2, EXPO); o.location.y = (BASE - EM * 1.05 * (1 - p)) * K
for f in range(1, FR + 1):
    frame(f); keyall([M] + list(m.values()) + [o for o, _, _ in L_letters], f)
meta('/tmp/bl2/out/c1.json', {'FW': FW, 'box': [(MX - 50 + FW / 2) / FW, (FW / 2 - 50) / FW, 100 / FW], 'frames': FR, 'fps': 60})
bpy.ops.wm.save_as_mainfile(filepath='/tmp/bl2/c1.blend')
render(sc, ST, 'c1')
