from flask import Flask, request, send_from_directory, jsonify
import os, uuid, math

app = Flask(__name__)
OUT = "output"
os.makedirs(OUT, exist_ok=True)

# -------------------------------
# GEOMETRY
# -------------------------------

def cube(sx, sy, sz):
    hx, hy, hz = sx/2, sy/2, sz/2
    v = [
        (-hx,-hy,-hz),(hx,-hy,-hz),(hx,hy,-hz),(-hx,hy,-hz),
        (-hx,-hy,hz),(hx,-hy,hz),(hx,hy,hz),(-hx,hy,hz)
    ]
    f = [
        (0,1,2),(0,2,3),
        (4,5,6),(4,6,7),
        (0,1,5),(0,5,4),
        (2,3,7),(2,7,6),
        (1,2,6),(1,6,5),
        (3,0,4),(3,4,7)
    ]
    return v, f

def cylinder(sx, sy, sz, seg=10):
    r = sx/2
    h = sz/2
    v=[]; f=[]
    for i in range(seg):
        a=2*math.pi*i/seg
        x=math.cos(a)*r
        y=math.sin(a)*r
        v.append((x,y,-h))
        v.append((x,y,h))
    for i in range(0,seg*2,2):
        n=(i+2)%(seg*2)
        f.append((i,n,n+1))
        f.append((i,n+1,i+1))
    return v,f

def sphere(sx, sy, sz, rings=5, seg=10):
    r=sx/2
    v=[]; f=[]
    for i in range(rings+1):
        phi=math.pi*i/rings
        for j in range(seg):
            theta=2*math.pi*j/seg
            x=r*math.sin(phi)*math.cos(theta)
            y=r*math.sin(phi)*math.sin(theta)
            z=r*math.cos(phi)
            v.append((x,y,z))
    for i in range(rings):
        for j in range(seg):
            nj=(j+1)%seg
            a=i*seg+j
            b=i*seg+nj
            c=(i+1)*seg+j
            d=(i+1)*seg+nj
            f.append((a,b,d))
            f.append((a,d,c))
    return v,f

def torus(sx, sy, sz, seg_major=12, seg_minor=6):
    R = sx / 2.0
    r = sz / 4.0
    verts = []
    faces = []

    for i in range(seg_major):
        theta = 2 * math.pi * i / seg_major
        for j in range(seg_minor):
            phi = 2 * math.pi * j / seg_minor

            x = (R + r * math.cos(phi)) * math.cos(theta)
            y = (R + r * math.cos(phi)) * math.sin(theta)
            z = r * math.sin(phi)

            verts.append((x,y,z))

    for i in range(seg_major):
        for j in range(seg_minor):
            a = i * seg_minor + j
            b = ((i+1)%seg_major)*seg_minor + j
            c = ((i+1)%seg_major)*seg_minor + (j+1)%seg_minor
            d = i*seg_minor + (j+1)%seg_minor

            faces.append((a,b,d))
            faces.append((b,c,d))

    return verts, faces

# -------------------------------
# TRANSFORM
# -------------------------------

def quat_rotate(q, v):
    x, y, z, w = q
    vx, vy, vz = v

    ix =  w * vx + y * vz - z * vy
    iy =  w * vy + z * vx - x * vz
    iz =  w * vz + x * vy - y * vx
    iw = -x * vx - y * vy - z * vz

    rx = ix * w + iw * -x + iy * -z - iz * -y
    ry = iy * w + iw * -y + iz * -x - ix * -z
    rz = iz * w + iw * -z + ix * -y - iy * -x

    return (rx, ry, rz)

def apply_transform(verts, pos, rot):
    out = []
    for v in verts:
        rv = quat_rotate(rot, v)
        out.append((rv[0]+pos[0], rv[1]+pos[1], rv[2]+pos[2]))
    return out

# -------------------------------
# SHAPE BUILDER
# -------------------------------

def build_shape(type_id, sx, sy, sz):
    if type_id == 0:
        return cube(sx, sy, sz)
    elif type_id == 1:
        return cylinder(sx, sy, sz)
    elif type_id == 3:
        return sphere(sx, sy, sz)
    elif type_id == 4:
        return torus(sx, sy, sz)
    else:
        return cube(sx, sy, sz)

# -------------------------------
# DAE WRITER
# -------------------------------

def write_dae(path, verts, faces):
    with open(path, "w") as f:
        f.write('<?xml version="1.0" encoding="utf-8"?>')
        f.write('<COLLADA xmlns="http://www.collada.org/2005/11/COLLADASchema" version="1.4.1">')

        f.write('<library_geometries><geometry id="mesh"><mesh>')

        f.write(f'<source id="pos"><float_array count="{len(verts)*3}">')
        for v in verts:
            f.write(f'{v[0]} {v[1]} {v[2]} ')
        f.write('</float_array></source>')

        f.write('<vertices id="verts"><input semantic="POSITION" source="#pos"/></vertices>')

        f.write(f'<triangles count="{len(faces)}">')
        f.write('<input semantic="VERTEX" source="#verts" offset="0"/><p>')
        for tri in faces:
            f.write(f'{tri[0]} {tri[1]} {tri[2]} ')
        f.write('</p></triangles>')

        f.write('</mesh></geometry></library_geometries>')

        f.write('<library_visual_scenes><visual_scene id="Scene"><node>')
        f.write('<instance_geometry url="#mesh"/>')
        f.write('</node></visual_scene></library_visual_scenes>')

        f.write('<scene><instance_visual_scene url="#Scene"/></scene>')
        f.write('</COLLADA>')

# -------------------------------
# API
# -------------------------------

@app.route("/")
def home():
    return "M3 Mesh Engine Running"

@app.route("/convert", methods=["POST"])
def convert():
    data = request.json or {}
    prims = data.get("prims", [])

    all_verts = []
    all_faces = []
    offset = 0

    for prim in prims:
        try:
            type_id = prim["type"]
            sx, sy, sz = prim["size"]
            pos = prim.get("pos",[0,0,0])
            rot = prim.get("rot",[0,0,0,1])
        except:
            continue

        v,f = build_shape(type_id, sx, sy, sz)
        v = apply_transform(v, pos, rot)

        all_verts.extend(v)

        for face in f:
            all_faces.append((
                face[0]+offset,
                face[1]+offset,
                face[2]+offset
            ))

        offset += len(v)

    name = str(uuid.uuid4()) + ".dae"
    path = os.path.join(OUT, name)

    write_dae(path, all_verts, all_faces)

    return jsonify({"file": name})

@app.route("/output/<filename>")
def output_file(filename):
    return send_from_directory(OUT, filename)
