from flask import Flask, request, send_from_directory, jsonify
import os, uuid

app = Flask(__name__)
OUT = "output"
os.makedirs(OUT, exist_ok=True)

# ---------- GEOMETRY ----------
def cube(sx, sy, sz):
    hx, hy, hz = sx/2, sy/2, sz/2

    verts = [
        (-hx,-hy,-hz),(hx,-hy,-hz),(hx,hy,-hz),(-hx,hy,-hz),
        (-hx,-hy,hz),(hx,-hy,hz),(hx,hy,hz),(-hx,hy,hz)
    ]

    faces = [
        (0,1,2),(0,2,3),
        (4,5,6),(4,6,7),
        (0,1,5),(0,5,4),
        (2,3,7),(2,7,6),
        (1,2,6),(1,6,5),
        (3,0,4),(3,4,7)
    ]

    return verts, faces


# ---------- ROTATION ----------
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
    out = []
    for v in verts:
        rv = quat_rotate(rot, v)
        out.append((rv[0]+pos[0], rv[1]+pos[1], rv[2]+pos[2]))
    return out


# ---------- DAE (FIXED FOR SL) ----------
def write_dae(path, verts, faces):
    with open(path, "w") as f:

        f.write('<?xml version="1.0" encoding="utf-8"?>')
        f.write('<COLLADA xmlns="http://www.collada.org/2005/11/COLLADASchema" version="1.4.1">')

        f.write('<library_geometries>')
        f.write('<geometry id="mesh" name="mesh"><mesh>')

        # POSITIONS
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
        f.write('</accessor>')
        f.write('</technique_common>')
        f.write('</source>')

        # VERTICES
        f.write('<vertices id="mesh-vertices">')
        f.write('<input semantic="POSITION" source="#mesh-positions"/>')
        f.write('</vertices>')

        # TRIANGLES
        f.write(f'<triangles count="{len(faces)}">')
        f.write('<input semantic="VERTEX" source="#mesh-vertices" offset="0"/>')
        f.write('<p>')
        for tri in faces:
            f.write(f'{tri[0]} {tri[1]} {tri[2]} ')
        f.write('</p>')
        f.write('</triangles>')

        f.write('</mesh></geometry>')
        f.write('</library_geometries>')

        # REQUIRED SCENE BLOCK
        f.write('<library_visual_scenes>')
        f.write('<visual_scene id="Scene" name="Scene">')
        f.write('<node id="mesh-node">')
        f.write('<instance_geometry url="#mesh"/>')
        f.write('</node>')
        f.write('</visual_scene>')
        f.write('</library_visual_scenes>')

        f.write('<scene>')
        f.write('<instance_visual_scene url="#Scene"/>')
        f.write('</scene>')

        f.write('</COLLADA>')


# ---------- ROUTES ----------
@app.route("/")
def home():
    return "M3 Mesh Engine Running"


@app.route("/convert", methods=["POST"])
def convert():
    data = request.json or {}
    prims = data.get("prims", [])

    all_v = []
    all_f = []
    offset = 0

    for p in prims:
        try:
            sx, sy, sz = p["size"]
            pos = p.get("pos",[0,0,0])
            rot = p.get("rot",[0,0,0,1])
        except:
            continue

        v, f = cube(sx, sy, sz)
        v = apply_transform(v, pos, rot)

        all_v.extend(v)

        for tri in f:
            all_f.append((tri[0]+offset, tri[1]+offset, tri[2]+offset))

        offset += len(v)

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
