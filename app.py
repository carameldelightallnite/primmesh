from flask import Flask, request, jsonify, send_from_directory
import os, uuid, math

app = Flask(__name__)
OUT = "output"
os.makedirs(OUT, exist_ok=True)

# ---------------- ROTATION ----------------
def apply_rotation(v, q):
    x, y, z, w = q
    vx, vy, vz = v
    tx = 2 * (y * vz - z * vy)
    ty = 2 * (z * vx - x * vz)
    tz = 2 * (x * vy - y * vx)
    rx = vx + w * tx + (y * tz - z * ty)
    ry = vy + w * ty + (z * tx - x * tz)
    rz = vz + w * tz + (x * ty - y * tx)
    return (rx, ry, rz)

# ---------------- SHAPES ----------------
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
    return v, f

def cylinder(sx, sy, sz, seg=16):
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

def sphere(sx, sy, sz, rings=8, seg=16):
    rx, ry, rz = sx/2, sy/2, sz/2
    v=[]; f=[]
    for i in range(rings+1):
        phi = math.pi*i/rings
        for j in range(seg):
            theta = 2*math.pi*j/seg
            v.append((
                rx*math.sin(phi)*math.cos(theta),
                ry*math.sin(phi)*math.sin(theta),
                rz*math.cos(phi)
            ))
    for i in range(rings):
        for j in range(seg):
            a=i*seg+j
            b=i*seg+(j+1)%seg
            c=(i+1)*seg+j
            d=(i+1)*seg+(j+1)%seg
            f.append((a,c,b))
            f.append((b,c,d))
    return v,f

def torus(sx, sy, sz, ring=16, tube=8):
    R = sx/2
    r = sy/4
    v=[]; f=[]
    for i in range(ring):
        for j in range(tube):
            u=2*math.pi*i/ring
            v_ang=2*math.pi*j/tube
            x=(R+r*math.cos(v_ang))*math.cos(u)
            y=(R+r*math.cos(v_ang))*math.sin(u)
            z=r*math.sin(v_ang)
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

def build_shape(t, sx, sy, sz):
    if t == 1: return cylinder(sx,sy,sz)
    if t == 2: return sphere(sx,sy,sz)
    if t == 3: return torus(sx,sy,sz)
    return cube(sx,sy,sz)

# ---------------- DAE ----------------
def write_dae(path, verts, faces):
    with open(path, "w") as f:

        f.write('<?xml version="1.0" encoding="utf-8"?>')
        f.write('<COLLADA xmlns="http://www.collada.org/2005/11/COLLADASchema" version="1.4.1">')

        f.write('<library_geometries><geometry id="mesh" name="mesh"><mesh>')

        # positions
        f.write('<source id="mesh-positions">')
        f.write(f'<float_array id="mesh-positions-array" count="{len(verts)*3}">')
        for v in verts:
            f.write(f'{v[0]} {v[1]} {v[2]} ')
        f.write('</float_array>')
        f.write('<technique_common>')
        f.write(f'<accessor source="#mesh-positions-array" count="{len(verts)}" stride="3">')
        f.write('<param name="X" type="float"/>')
        f.write('<param name="Y" type="float"/>')
        f.write('<param name="Z" type="float"/>')
        f.write('</accessor></technique_common></source>')

        # normals
        f.write('<source id="mesh-normals">')
        f.write(f'<float_array id="mesh-normals-array" count="{len(verts)*3}">')
        for v in verts:
            l = max((v[0]**2+v[1]**2+v[2]**2)**0.5, 0.0001)
            f.write(f'{v[0]/l} {v[1]/l} {v[2]/l} ')
        f.write('</float_array>')
        f.write('<technique_common>')
        f.write(f'<accessor source="#mesh-normals-array" count="{len(verts)}" stride="3">')
        f.write('<param name="X" type="float"/>')
        f.write('<param name="Y" type="float"/>')
        f.write('<param name="Z" type="float"/>')
        f.write('</accessor></technique_common></source>')

        f.write('<vertices id="mesh-vertices">')
        f.write('<input semantic="POSITION" source="#mesh-positions"/>')
        f.write('</vertices>')

        f.write(f'<triangles count="{len(faces)}">')
        f.write('<input semantic="VERTEX" source="#mesh-vertices" offset="0"/>')
        f.write('<input semantic="NORMAL" source="#mesh-normals" offset="1"/>')
        f.write('<p>')
        for tri in faces:
            for idx in tri:
                f.write(f'{idx} {idx} ')
        f.write('</p></triangles>')

        f.write('</mesh></geometry></library_geometries>')

        f.write('<library_visual_scenes><visual_scene id="Scene">')
        f.write('<node><instance_geometry url="#mesh"/></node>')
        f.write('</visual_scene></library_visual_scenes>')

        f.write('<scene><instance_visual_scene url="#Scene"/></scene>')
        f.write('</COLLADA>')

# ---------------- ROUTE ----------------
@app.route("/convert", methods=["POST"])
def convert():
    prims = request.json.get("prims", [])
    V=[]; F=[]; off=0

    for p in prims:
        t=p.get("type",0)
        sx,sy,sz=p["size"]
        pos=p.get("pos",[0,0,0])
        rot=p.get("rot",[0,0,0,1])

        v,f=build_shape(t,sx,sy,sz)
        v=[apply_rotation(vx,rot) for vx in v]
        v=[(vx+pos[0],vy+pos[1],vz+pos[2]) for vx,vy,vz in v]

        V.extend(v)
        for a,b,c in f:
            F.append((a+off,b+off,c+off))
        off+=len(v)

    if not V:
        return jsonify({"error":"no geometry"}),400

    name=str(uuid.uuid4())+".dae"
    write_dae(os.path.join(OUT,name),V,F)

    return jsonify({"file":name})

@app.route("/output/<f>")
def out(f):
    return send_from_directory(OUT,f)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
