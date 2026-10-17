import math,sys
def cres(ax,ay,ra,bx,by,rb):
    d=math.hypot(bx-ax,by-ay); a=(ra*ra-rb*rb+d*d)/(2*d); h=math.sqrt(ra*ra-a*a)
    mx,my=ax+a*(bx-ax)/d, ay+a*(by-ay)/d
    p1=(mx+h*(by-ay)/d, my-h*(bx-ax)/d); p2=(mx-h*(by-ay)/d, my+h*(bx-ax)/d)
    f=lambda p:f"{p[0]:.2f} {p[1]:.2f}"
    # outer arc of A from p1 to p2 going away from B, inner arc of B back
    la=1 if a>0 else 0
    return f"M{f(p1)} A{ra} {ra} 0 {la} 0 {f(p2)} A{rb} {rb} 0 0 1 {f(p1)} Z"
# variants
for name,(dx,dy,dr,ax,ay,ra,rb) in {"fav":(43,57,27,54,46,33,33.5)}.items():
    print(name, f'<circle cx="{dx}" cy="{dy}" r="{dr}"/>', cres(ax,ay,ra,dx,dy,rb))
