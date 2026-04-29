from flask import Flask, request, jsonify, send_from_directory
import os, uuid, math

app = Flask(__name__)
OUT = "output"
os.makedirs(OUT, exist_ok=True)

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

def build_shape(t, sx, sy, sz):
    return cube(sx, sy, sz)

# ---------------- ROTATION ----------------
def apply_rotation(v, q):
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

# ---------------- FINAL DAE ----------------
def write_dae(path, verts, faces):
    normals = []
    normal_indices = []

    for tri in faces:
        a,b,c = tri
        v1,v2,v3 = verts[a],verts[b],verts[c]

        ux,uy,uz = v2[0]-v1[0],v2[1]-v1[1],v2[2]-v1[2]
        vx,vy,vz = v3[0]-v1[0],v3[1]-v1[1],v3[2]-v1[2]

        nx = uy*vz - uz*vy
        ny = uz*vx - ux*vz
        nz = ux*vy - uy*vx

        l = max((nx*nx+ny*ny+nz*nz)**0.5,0.0001)
        nx,ny,nz = nx/l,ny/l,nz/l

        idx = len(normals)
        normals.append((nx,ny,nz))
        normal_indices.append((idx,idx,idx))

    with open(path,"w") as f:

        f.write('<?xml version="1.0" encoding="utf-8"?>')
        f.write('<COLLADA xmlns="http://www.collada.org/2005/11/COLLADASchema" version="1.4.1">')

        f.write('<library_geometries><geometry id="mesh"><mesh>')

        # positions
        f.write(f'<source id="pos"><float_array id="posa" count="{len(verts)*3}">')
        for v in verts: f.write(f'{v[0]} {v[1]} {v[2]} ')
        f.write('</float_array>')
        f.write('<technique_common>')
        f.write(f'<accessor source="#posa" count="{len(verts)}" stride="3">')
        f.write('<param name="X" type="float"/><param name="Y" type="float"/><param name="Z" type="float"/>')
        f.write('</accessor></technique_common></source>')

        # normals
        f.write(f'<source id="norm"><float_array id="norma" count="{len(normals)*3}">')
        for n in normals: f.write(f'{n[0]} {n[1]} {n[2]} ')
        f.write('</float_array>')
        f.write('<technique_common>')
        f.write(f'<accessor source="#norma" count="{len(normals)}" stride="3">')
        f.write('<param name="X" type="float"/><param name="Y" type="float"/><param name="Z" type="float"/>')
        f.write('</accessor></technique_common></source>')

        f.write('<vertices id="v"><input semantic="POSITION" source="#pos"/></vertices>')

        f.write(f'<triangles material="Material" count="{len(faces)}">')
        f.write('<input semantic="VERTEX" source="#v" offset="0"/>')
        f.write('<input semantic="NORMAL" source="#norm" offset="1"/>')
        f.write('<p>')
        for i,tri in enumerate(faces):
            a,b,c = tri
            na,nb,nc = normal_indices[i]
            f.write(f'{a} {na} {b} {nb} {c} {nc} ')
        f.write('</p></triangles>')

        f.write('</mesh></geometry></library_geometries>')

        f.write('<library_materials><material id="Material"><instance_effect url="#Material-effect"/></material></library_materials>')
        f.write('<library_effects><effect id="Material-effect"><profile_COMMON><technique sid="common"><lambert><diffuse><color>0.8 0.8 0.8 1</color></diffuse></lambert></technique></profile_COMMON></effect></library_effects>')

        f.write('<library_visual_scenes><visual_scene id="Scene"><node>')
        f.write('<instance_geometry url="#mesh"><bind_material><technique_common>')
        f.write('<instance_material symbol="Material" target="#Material"/>')
        f.write('</technique_common></bind_material></instance_geometry>')
        f.write('</node></visual_scene></library_visual_scenes>')

        f.write('<scene><instance_visual_scene url="#Scene"/></scene>')
        f.write('</COLLADA>')

# ---------------- ROUTE ----------------
@app.route("/convert", methods=["POST"])
def convert():
    prims = request.json.get("prims", [])
    V,F,off=[],[],0

    for p in prims:
        sx,sy,sz=p["size"]
        pos=p["pos"]
        rot=p["rot"]

        v,f=build_shape(0,sx,sy,sz)
        v=[apply_rotation(vx,rot) for vx in v]
        v=[(vx+pos[0],vy+pos[1],vz+pos[2]) for vx,vy,vz in v]

        V.extend(v)
        for a,b,c in f: F.append((a+off,b+off,c+off))
        off+=len(v)

    name=str(uuid.uuid4())+".dae"
    write_dae(os.path.join(OUT,name),V,F)
    return jsonify({"file":name})

@app.route("/output/<f>")
def out(f): return send_from_directory(OUT,f)

app.run(host="0.0.0.0",port=10000)
