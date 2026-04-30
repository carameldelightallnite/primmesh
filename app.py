from flask import Flask, request, send_file
import math

app = Flask(__name__)

OUTPUT = "shape.dae"
BASE_URL = "https://m3-mesh-engine.onrender.com"

# ==========================================
# EXACT SHAPE BUILDER (FOR PERFECT CUBES)
# ==========================================
def build_exact_cube():
    # 8 Clean corners - No center vertices to cause "nipples"
    verts = [
        (-0.5,-0.5,-0.5), (0.5,-0.5,-0.5), (0.5,0.5,-0.5), (-0.5,0.5,-0.5), # Bottom
        (-0.5,-0.5, 0.5), (0.5,-0.5, 0.5), (0.5,0.5, 0.5), (-0.5,0.5, 0.5)  # Top
    ]
    # 6 Faces mapped to Mat0 (Outside) for simplicity in SL
    f_out = [
        (0,1,2), (0,2,3), # Bottom
        (4,6,5), (4,7,6), # Top
        (0,4,5), (0,5,1), # Front
        (1,5,6), (1,6,2), # Right
        (2,6,7), (2,7,3), # Back
        (3,7,4), (3,4,0)  # Left
    ]
    write_dae_final(verts, f_out, [], [])

# ==========================================
# PROCEDURAL EXTRUDER (FOR CIRCLES/TORUS)
# ==========================================
def get_profile_point(t, p_type="Square"):
    t %= 1.0
    s = 0.5
    if p_type == "Circle":
        return (s * math.cos(2 * math.pi * t), s * math.sin(2 * math.pi * t))
    elif p_type == "Triangle":
        corners = [(-s, -s), (s, -s), (0, s), (-s, -s)]
        i = int(t * 3); r = (t * 3) - i
        return (corners[i][0] + (corners[i+1][0]-corners[i][0])*r, 
                corners[i][1] + (corners[i+1][1]-corners[i][1])*r)
    return (0,0) # Fallback

def build_extrusion(params):
    p_type = params.get("profile", "Circle")
    path_type = params.get("path", "Linear")
    hollow = float(params.get("hollow", 0.0))
    
    verts, f_out, f_in, f_cap = [], [], [], []
    p_steps = 24 if p_type == "Circle" else 3
    path_steps = 32 if path_type == "Circular" else 1
    major_r, size = 1.0, 1.0
    n = p_steps + 1

    for s_idx in range(path_steps + 1):
        v_c = s_idx / float(path_steps)
        phi = v_c * 2 * math.pi
        cp, sp = math.cos(phi), math.sin(phi)
        for i in range(n):
            px, py = get_profile_point(i/p_steps, p_type)
            if path_type == "Linear":
                z = -size if s_idx == 0 else size
                verts.append((px, py, z))
            else:
                verts.append(((major_r + px) * cp, (major_r + px) * sp, py))

    # Face bridging
    def quad(g, a, b, c, d): g.extend([(a, b, c), (a, c, d)])
    for s in range(path_steps):
        s1, s2 = s * n, (s + 1) * n
        for i in range(p_steps):
            quad(f_out, s1+i, s1+i+1, s2+i+1, s2+i)
            
    write_dae_final(verts, f_out, f_in, f_cap)

# ==========================================
# THE FINAL SL-SAFE DAE WRITER
# ==========================================
def write_dae_final(verts, out_f, in_f, cap_f):
    v_data = " ".join(f"{x} {y} {z}" for x, y, z in verts)
    def pack(f): return " ".join(f"{a} {b} {c}" for (a, b, c) in f)

    dae = f"""<?xml version="1.0" encoding="utf-8"?>
<COLLADA xmlns="http://www.collada.org/2005/11/COLLADASchema" version="1.4.1">
  <asset><unit name="meter" meter="1"/><up_axis>Z_UP</up_axis></asset>
  <library_geometries><geometry id="m"><mesh>
    <source id="p"><float_array id="pa" count="{len(verts)*3}">{v_data}</float_array>
    <technique_common><accessor source="#pa" count="{len(verts)}" stride="3"><param name="X" type="float"/><param name="Y" type="float"/><param name="Z" type="float"/></accessor></technique_common></source>
    <vertices id="v"><input semantic="POSITION" source="#p"/></vertices>
    <triangles material="m0" count="{len(out_f)}"><input semantic="VERTEX" source="#v" offset="0"/><p>{pack(out_f)}</p></triangles>
    <triangles material="m1" count="{len(in_f)}"><input semantic="VERTEX" source="#v" offset="0"/><p>{pack(in_f)}</p></triangles>
    <triangles material="m2" count="{len(cap_f)}"><input semantic="VERTEX" source="#v" offset="0"/><p>{pack(cap_f)}</p></triangles>
  </mesh></geometry></library_geometries>
  <library_visual_scenes><visual_scene id="S"><node><instance_geometry url="#m"/></node></visual_scene></library_visual_scenes>
  <scene><instance_visual_scene url="#S"/></scene>
</COLLADA>"""
    with open(OUTPUT, "w") as f: f.write(dae)

# ==========================================
# ROUTE LOGIC: THE BRAINS
# ==========================================
@app.route("/generate", methods=["POST"])
def generate():
    raw = request.data.decode("utf-8")
    params = dict(p.split("=") for p in raw.split("|") if "=" in p)
    
    p_type = params.get("profile", "Square")
    path_type = params.get("path", "Linear")

    # FORK: Is it a simple cube or a complex extrusion?
    if p_type == "Square" and path_type == "Linear":
        build_exact_cube()
    else:
        build_extrusion(params)
        
    return f"{BASE_URL}/download"

@app.route("/download")
def download(): return send_file(OUTPUT, as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
