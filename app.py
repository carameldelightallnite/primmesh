from flask import Flask, request, send_from_directory, jsonify
import os, uuid, math

app = Flask(__name__)
OUT = "output"
os.makedirs(OUT, exist_ok=True)

# ---------------------------
# GEOMETRY BUILDERS (REAL)
# ---------------------------

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
    return v,f

def cylinder(sx, sy, sz, seg=16):
    r = max(sx, sy)/2
    h = sz/2
    verts=[]
    faces=[]

    # side verts
    for i in range(seg):
        a = 2*math.pi*i/seg
        x = math.cos(a)*r
        y = math.sin(a)*r
        verts.append((x,y,-h))
        verts.append((x,y,h))

    # side faces
    for i in range(seg):
        a = i*2
        b = ((i+1)%seg)*2
        faces.append((a, b, a+1))
        faces.append((b, b+1, a+1))

    return verts, faces

def sphere(sx, sy, sz, rings=8, seg=16):
    rx, ry, rz = sx/2, sy/2, sz/2
    verts=[]
    faces=[]

    for i in range(rings+1):
        phi = math.pi*i/rings
        for j in range(seg):
            theta = 2*math.pi*j/seg
            x = rx*math.sin(phi)*math.cos(theta)
            y = ry*math.sin(phi)*math.sin(theta)
            z = rz*math.cos(phi)
            verts.append((x,y,z))

    for i in range(rings):
        for j in range(seg):
            a = i*seg + j
            b = i*seg + (j+1)%seg
            c = (i+1)*seg + j
            d = (i+1)*seg + (j+1)%seg
            faces.append((a,c,b))
            faces.append((b,c,d))

    return verts, faces

def torus(sx, sy, sz, ring=16, tube=8):
    R = sx/2
    r = sy/4
    verts=[]
    faces=[]

    for i in range(ring):
        for j in range(tube):
            u = 2*math.pi*i/ring
            v = 2*math.pi*j/tube
            x = (R + r*math.cos(v)) * math.cos(u)
            y = (R + r*math.cos(v)) * math.sin(u)
            z = r*math.sin(v)
            verts.append((x,y,z))

    for i in range(ring):
        for j in range(tube):
            a = i*tube + j
            b = i*tube + (j+1)%tube
            c = ((i+1)%ring)*tube + j
            d = ((i+1)%ring)*tube + (j+1)%tube
            faces.append((a,c,b))
            faces.append((b,c,d))

    return verts, faces

def cone(sx, sy, sz, seg=16):
    r = max(sx,sy)/2
    h = sz/2
    verts=[(0,0,h)]
    for i in range(seg):
        a = 2*math.pi*i/seg
        verts.append((math.cos(a)*r, math.sin(a)*r, -h))

    faces=[]
    for i in range(1,seg):
        faces.append((0,i,i+1))
    faces.append((0,seg,1))
    return verts, faces

# map TYPE → SHAPE
def build_shape(type_id, sx, sy, sz):
    if type_id == 0: return cube(sx,sy,sz)
    if type_id == 1: return cylinder(sx,sy,sz)
    if type_id == 2: return sphere(sx,sy,sz)
    if type_id == 3: return torus(sx,sy,sz)
    if type_id == 4: return cone(sx,sy,sz)
    return cube(sx,sy,sz)

# ---------------------------
# TRANSFORM
# ---------------------------

def quat_rotate(q, v):
    x,y,z,w = q
    vx,vy,vz = v
    ix =  w*vx + y*vz - z*vy
    iy =  w*vy + z*vx - x*vz
    iz =  w*vz + x*vy - y*vx
    iw = -x*vx - y*vy - z*vz
    rx = ix*w + iw*-x + iy*-z - iz*-y
    ry = iy*w + iw*-y + iz*-x - ix*-z
    rz = iz*w + iw*-z + ix*-y - iy*-x
    return (rx,ry,rz)

def apply_transform(verts, pos, rot):
    return [(quat_rotate(rot,v)[0]+pos[0],
             quat_rotate(rot,v)[1]+pos[1],
             quat_rotate(rot,v)[2]+pos[2]) for v in verts]

# ---------------------------
# DAE (SL SAFE)
# ---------------------------

def write_dae(path, verts, faces):
    with open(path,"w") as f:
        f.write('<?xml version="1.0" encoding="utf-8"?>')
        f.write('<COLLADA xmlns="http://www.collada.org/2005/11/COLLADASchema" version="1.4.1">')

        f.write('<library_geometries><geometry id="mesh"><mesh>')

        f.write('<source id="pos">')
        f.write(f'<float_array id="pos-arr" count="{len(verts)*3}">')
        for v in verts:
            f.write(f'{v[0]} {v[1]} {v[2]} ')
        f.write('</float_array>')

        f.write('<technique_common>')
        f.write(f'<accessor source="#pos-arr" count="{len(verts)}" stride="3">')
        f.write('<param name="X" type="float"/>')
        f.write('<param name="Y" type="float"/>')
        f.write('<param name="Z" type="float"/>')
        f.write('</accessor></technique_common></source>')

        f.write('<vertices id="v"><input semantic="POSITION" source="#pos"/></vertices>')

        f.write(f'<triangles count="{len(faces)}">')
        f.write('<input semantic="VERTEX" source="#v" offset="0"/><p>')
        for t in faces:
            f.write(f'{t[0]} {t[1]} {t[2]} ')
        f.write('</p></triangles>')

        f.write('</mesh></geometry></library_geometries>')

        f.write('<library_visual_scenes><visual_scene id="Scene">')
        f.write('<node><instance_geometry url="#mesh"/></node>')
        f.write('</visual_scene></library_visual_scenes>')
        f.write('<scene><instance_visual_scene url="#Scene"/></scene>')

        f.write('</COLLADA>')

# ---------------------------
# ROUTES
# ---------------------------

@app.route("/")
def home():
    return "M3 Mesh Engine Running"

@app.route("/convert", methods=["POST"])
def convert():
    data = request.json or {}
    prims = data.get("prims", [])

    all_v=[]
    all_f=[]
    off=0

    for p in prims:
        try:
            t = p.get("type",0)
            sx,sy,sz = p["size"]
            pos = p.get("pos",[0,0,0])
            rot = p.get("rot",[0,0,0,1])
        except:
            continue

        v,f = build_shape(t, sx,sy,sz)
        v = apply_transform(v,pos,rot)

        all_v.extend(v)
        for tri in f:
            all_f.append((tri[0]+off, tri[1]+off, tri[2]+off))
        off += len(v)

    if not all_v:
        return jsonify({"error":"no geometry"}),400

    name = str(uuid.uuid4())+".dae"
    path = os.path.join(OUT,name)
    write_dae(path, all_v, all_f)

    return jsonify({"file":name})

@app.route("/output/<filename>")
def out(filename):
    return send_from_directory(OUT, filename)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
