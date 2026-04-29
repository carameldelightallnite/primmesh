from flask import Flask, request, jsonify, send_from_directory
import os, uuid, math

app = Flask(__name__)
OUT = "output"
os.makedirs(OUT, exist_ok=True)

# ---------- SHAPES ----------

def cube(sx, sy, sz):
    hx, hy, hz = sx/2, sy/2, sz/2
    v = [
        (-hx,-hy,-hz),(hx,-hy,-hz),(hx,hy,-hz),(-hx,hy,-hz),
        (-hx,-hy,hz),(hx,-hy,hz),(hx,hy,hz),(-hx,hy,hz)
    ]
    f = [
        (0,1,2),(0,2,3),(4,5,6),(4,6,7),
        (0,1,5),(0,5,4),(2,3,7),(2,7,6),
        (1,2,6),(1,6,5),(3,0,4),(3,4,7)
    ]
    return v,f


def cylinder(sx, sy, sz):
    seg = 20
    r = max(sx, sy)/2
    h = sz/2
    v=[]; f=[]
    for i in range(seg):
        a = 2*math.pi*i/seg
        x = math.cos(a)*r
        y = math.sin(a)*r
        v.append((x,y,-h))
        v.append((x,y,h))
    for i in range(seg):
        a=i*2
        b=((i+1)%seg)*2
        f.append((a,b,a+1))
        f.append((b,b+1,a+1))
    return v,f


def sphere(sx, sy, sz):
    seg=16; rings=10
    rx,ry,rz = sx/2, sy/2, sz/2
    v=[]; f=[]
    for i in range(rings+1):
        phi=math.pi*i/rings
        for j in range(seg):
            theta=2*math.pi*j/seg
            x=rx*math.sin(phi)*math.cos(theta)
            y=ry*math.sin(phi)*math.sin(theta)
            z=rz*math.cos(phi)
            v.append((x,y,z))
    for i in range(rings):
        for j in range(seg):
            a=i*seg+j
            b=i*seg+(j+1)%seg
            c=(i+1)*seg+j
            d=(i+1)*seg+(j+1)%seg
            f.append((a,c,b))
            f.append((b,c,d))
    return v,f


def cone(sx, sy, sz):
    seg=20
    r=max(sx,sy)/2
    h=sz
    v=[(0,0,h/2)]
    for i in range(seg):
        a=2*math.pi*i/seg
        v.append((math.cos(a)*r, math.sin(a)*r, -h/2))
    f=[]
    for i in range(1,seg):
        f.append((0,i,i+1))
    f.append((0,seg,1))
    return v,f


def torus(sx, sy, sz):
    ring=16; tube=10
    R=sx/2
    r=sy/4
    v=[]; f=[]
    for i in range(ring):
        for j in range(tube):
            u=2*math.pi*i/ring
            t=2*math.pi*j/tube
            x=(R+r*math.cos(t))*math.cos(u)
            y=(R+r*math.cos(t))*math.sin(u)
            z=r*math.sin(t)
            v.append((x,y,z))
    for i in range(ring):
        for j in range(tube):
            a=i*tube+j
            b=i*tube+(j+1)%tube
            c=((i+1)%ring)*tube+j
            d=((i+1)%ring)*tube+(j+1)%tube
            f.append((a,c,b))
            f.append((b,c,d))
    return v,f


def prism(sx, sy, sz):
    # tapered box → prism
    top_scale = 0.2
    hx,hy,hz = sx/2, sy/2, sz/2

    v = [
        (-hx,-hy,-hz),(hx,-hy,-hz),(hx,hy,-hz),(-hx,hy,-hz),
        (-hx*top_scale,-hy*top_scale,hz),
        (hx*top_scale,-hy*top_scale,hz),
        (hx*top_scale,hy*top_scale,hz),
        (-hx*top_scale,hy*top_scale,hz)
    ]

    f = [
        (0,1,2),(0,2,3),
        (4,5,6),(4,6,7),
        (0,1,5),(0,5,4),
        (1,2,6),(1,6,5),
        (2,3,7),(2,7,6),
        (3,0,4),(3,4,7)
    ]
    return v,f


# ---------- SHAPE ROUTER ----------

def build_shape(t, sx, sy, sz):
    if t == 0: return cube(sx,sy,sz)
    if t == 1: return cylinder(sx,sy,sz)
    if t == 2: return sphere(sx,sy,sz)
    if t == 3: return torus(sx,sy,sz)
    if t == 4: return cone(sx,sy,sz)
    if t == 5: return prism(sx,sy,sz)
    return cube(sx,sy,sz)


# ---------- EXPORT ----------

def write_dae(path, V, F):
    with open(path,"w") as f:
        f.write('<?xml version="1.0" encoding="utf-8"?>')
        f.write('<COLLADA version="1.4.1">')
        f.write('<library_geometries><geometry id="m"><mesh>')

        f.write(f'<source id="p"><float_array count="{len(V)*3}">')
        for v in V:
            f.write(f'{v[0]} {v[1]} {v[2]} ')
        f.write('</float_array></source>')

        f.write('<vertices id="v"><input semantic="POSITION" source="#p"/></vertices>')

        f.write(f'<triangles count="{len(F)}">')
        f.write('<input semantic="VERTEX" source="#v" offset="0"/><p>')
        for a,b,c in F:
            f.write(f'{a} {b} {c} ')
        f.write('</p></triangles>')

        f.write('</mesh></geometry></library_geometries>')
        f.write('<scene><instance_visual_scene url="#s"/></scene>')
        f.write('</COLLADA>')


# ---------- ROUTE ----------

@app.route("/convert",methods=["POST"])
def convert():
    prims=request.json.get("prims",[])
    V=[]; F=[]; off=0

    for p in prims:
        t=p["type"]
        sx,sy,sz=p["size"]
        pos=p["pos"]

        v,f=build_shape(t,sx,sy,sz)
        v=[(x+pos[0],y+pos[1],z+pos[2]) for x,y,z in v]

        V.extend(v)
        for a,b,c in f:
            F.append((a+off,b+off,c+off))
        off+=len(v)

    name=str(uuid.uuid4())+".dae"
    write_dae(os.path.join(OUT,name),V,F)

    return jsonify({"file":name})


@app.route("/output/<f>")
def out(f):
    return send_from_directory(OUT,f)


app.run(host="0.0.0.0",port=10000)
