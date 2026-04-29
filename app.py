from flask import Flask, request, send_from_directory, jsonify
import os, uuid, math

app = Flask(__name__)
OUT = "output"
os.makedirs(OUT, exist_ok=True)

# ---------- SIMPLE GEOMETRY ----------
def cube(sx, sy, sz):
    hx, hy, hz = sx/2, sy/2, sz/2
    v = [(-hx,-hy,-hz),(hx,-hy,-hz),(hx,hy,-hz),(-hx,hy,-hz),
         (-hx,-hy,hz),(hx,-hy,hz),(hx,hy,hz),(-hx,hy,hz)]
    f = [(0,1,2),(0,2,3),(4,5,6),(4,6,7),
         (0,1,5),(0,5,4),(2,3,7),(2,7,6),
         (1,2,6),(1,6,5),(3,0,4),(3,4,7)]
    return v, f

def build_shape(type_id, sx, sy, sz):
    return cube(sx, sy, sz)  # keep stable

# ---------- TRANSFORM ----------
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
    out=[]
    for v in verts:
        rv = quat_rotate(rot, v)
        out.append((rv[0]+pos[0], rv[1]+pos[1], rv[2]+pos[2]))
    return out

# ---------- DAE ----------
def write_dae(path, verts, faces):
    with open(path, "w") as f:
        f.write('<?xml version="1.0" encoding="utf-8"?>')
        f.write('<COLLADA version="1.4.1">')
        f.write('<library_geometries><geometry id="m"><mesh>')
        f.write(f'<source id="p"><float_array count="{len(verts)*3}">')
        for v in verts:
            f.write(f'{v[0]} {v[1]} {v[2]} ')
        f.write('</float_array></source>')
        f.write('<vertices id="v"><input semantic="POSITION" source="#p"/></vertices>')
        f.write(f'<triangles count="{len(faces)}">')
        f.write('<input semantic="VERTEX" source="#v" offset="0"/><p>')
        for t in faces:
            f.write(f'{t[0]} {t[1]} {t[2]} ')
        f.write('</p></triangles>')
        f.write('</mesh></geometry></library_geometries>')
        f.write('<library_visual_scenes><visual_scene id="s"><node>')
        f.write('<instance_geometry url="#m"/>')
        f.write('</node></visual_scene></library_visual_scenes>')
        f.write('<scene><instance_visual_scene url="#s"/></scene>')
        f.write('</COLLADA>')

# ---------- ROUTES ----------
@app.route("/")
def home():
    return "M3 Mesh Engine Running"

@app.route("/convert", methods=["POST"])
def convert():
    data = request.json or {}
    prims = data.get("prims", [])

    all_v=[]; all_f=[]; off=0

    for p in prims:
        try:
            sx,sy,sz = p["size"]
            pos = p.get("pos",[0,0,0])
            rot = p.get("rot",[0,0,0,1])
        except:
            continue

        v,f = build_shape(0, sx,sy,sz)
        v = apply_transform(v, pos, rot)

        all_v.extend(v)
        for face in f:
            all_f.append((face[0]+off, face[1]+off, face[2]+off))
        off += len(v)

    if not all_v:
        return jsonify({"error":"no geometry"}), 400

    name = str(uuid.uuid4()) + ".dae"
    path = os.path.join(OUT, name)

    write_dae(path, all_v, all_f)

    return jsonify({"file": name})

@app.route("/output/<filename>")
def out(filename):
    return send_from_directory(OUT, filename)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
