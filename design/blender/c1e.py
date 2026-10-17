# C1E · 마무리(랜딩 맨 끝) — 지구 입자가 모여 만든 일식 심볼을 그대로 이어받아 '로고만 크게' 보여 준다(브랜드 이름 없음).
# 움직임은 오프닝 원반이 튀어나올 때와 같은 결: 원반이 숨 쉬듯 살짝 작아졌다가 살짝 지나쳐 커지며 제자리, 전체는 1.06 → 1 로 가라앉는다. 이후 정지.
# 첫 프레임 = 심볼(영상 가로의 60%, 가운데) — 웹에서 입자 심볼과 같은 자리·크기로 맞춘다.
import sys; sys.path.insert(0, '/tmp/bl2')
import importlib, k2; importlib.reload(k2)
k2.BG = k2.BGC = (255, 255, 255)   # 흰 바탕: 웹에서 곱하기 합성하면 바탕이 완전히 투명해진다
from k2 import *
args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
RES = int(args[0]) if args else 1080; ST = [int(x) for x in args[1].split(',')] if len(args) > 1 else None
FR = 120; MKF = 0.6; sc, cam = reset(FR, RES, out='/tmp/bl2/out/c1e/')
root = empty('root'); M = empty('M', root); m = mark(M)
ortho(cam, 100 / MKF)
POP = bez(0.3, 1.25, 0.6, 1)
def frame(f):
    dip = math.sin(math.pi * seg(f, 2, 26, bez(0.45, 0, 0.55, 1)))                 # 숨 들이쉬기(작아짐)
    pop = seg(f, 22, 70, POP)                                                      # 살짝 지나쳐 커졌다 제자리
    r = 30 * (1 - 0.08 * dip) if f < 22 else 30 * lerp(1 - 0.08 * math.sin(math.pi * seg(22, 2, 26, bez(0.45, 0, 0.55, 1))), 1, pop)
    setr(m['disc'], r); setr(m['moon'], 34 * (r / 30) ** 0.5)
    z = lerp(1.0, 1.0, 0) * (1 + 0.06 * math.sin(math.pi * seg(f, 18, 84, bez(0.4, 0, 0.3, 1))))   # 전체가 한 번 부풀었다 가라앉음
    M.scale = (z, z, 1)
for f in range(1, FR + 1):
    frame(f); keyall([M] + list(m.values()), f)
meta('/tmp/bl2/out/c1e.json', {'mark': MKF, 'frames': FR, 'fps': 60})
bpy.ops.wm.save_as_mainfile(filepath='/tmp/bl2/c1e.blend')
render(sc, ST, 'c1e')
