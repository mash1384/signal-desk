import math
ax,ay=53,47; bx,by,rb=46,54,34; ro,ri=31+1.6,31-1.6
def inter(r):
    # circle A radius r with circle B rb; returns two points (p_left/top, p_right)
    d=math.hypot(bx-ax,by-ay); a=(r*r-rb*rb+d*d)/(2*d); h=math.sqrt(r*r-a*a)
    mx,my=ax+a*(bx-ax)/d, ay+a*(by-ay)/d; ux,uy=(bx-ax)/d,(by-ay)/d
    return (mx+h*uy, my-h*ux), (mx-h*uy, my+h*ux)
P1,P2=inter(ro); Q1,Q2=inter(ri)
f=lambda p:f"{p[0]:.2f} {p[1]:.2f}"
# region outside B: A-arc far from B. For outer: from P1 to P2 going around far side. Large-arc decided by whether chord center side
def la(r):
    d=math.hypot(bx-ax,by-ay); a=(r*r-rb*rb+d*d)/(2*d); return 1 if a>0 else 0
# Order: P1 -> (outer A arc, far side) -> P2 -> (B arc) -> Q2 -> (inner A arc back, far side) -> Q1 -> (B arc) -> P1
print("P1",P1,"P2",P2,"Q1",Q1,"Q2",Q2, "la", la(ro), la(ri))
for s1 in (0,1):
  d=f"M{f(P1)} A{ro} {ro} 0 {la(ro)} {s1} {f(P2)} A{rb} {rb} 0 0 {1-s1} {f(Q2)} A{ri} {ri} 0 {la(ri)} {1-s1} {f(Q1)} A{rb} {rb} 0 0 {1-s1} {f(P1)} Z"
  print(s1, d)
