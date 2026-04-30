from flask import Flask, request, send_file
import math

app = Flask(__name__)

OUTPUT = "shape.dae"
BASE_URL = "https://m3-mesh-engine.onrender.com"

# ==========================================
# 1. AAA NORMAL ENGINE (FIXED)
# ==========================================
def compute_normals(verts, faces):
    """Calculates vertex normals. Essential for smooth shading in SL."""
    normals = [[0.0, 0.0, 0.0] for _ in range(len(verts))]
    for a, b, c in faces:
        v1, v2, v3 = verts[a], verts[b], verts[c]
        # Cross product
        ux, uy, uz = v2[0]-v1[0], v2[1]-v1[1], v2[2]-v1[2]
        vx, vy, vz = v3[0]-v1[0], v3[1]-v1[1], v3[2]-v1[2]
        nx, ny, nz = uy*vz - uz*vy, uz*vx - ux*vz, ux*vy - uy*vx
        for i in (a, b, c):
            normals[i][0] += nx
            normals[i][1] += ny
            normals[i][2] += nz
    
    result = []
    for n in normals:
        mag = math.sqrt(n[0]**2 + n[1]**2 + n[2]**2) or 1.0
        result.append((n[0]/mag, n[1]/mag, n[2]/mag))
    return result

# ==========================================
# 2. UPDATED PROFILES (SQUARE, TRIANGLE, CIRCLE, STAR)
# ==========================================
def get_profile_point(t, p_type="Square"):
    t %= 1.0
    s = 0.5
    if p_type == "Circle":
        return (s * math.cos(2 * math.pi * t), s * math.sin(2 * math.pi * t))
    elif p_type == "Star":
        # 5-pointed star: 10 points (outer/inner)
        outer_r, inner_r = s, s * 0.4
        points = 10
        angle = 2 * math.pi * t
        r = outer_r if int(t * points + 0.5) % 2 == 0 else inner_r
        return (r * math.cos(angle), r * math.sin(angle))
    elif p_type == "Triangle":
        corners = [(-s,-s),(s,-s),(0,s),(-s,-s)]
        i = int(t*3); r = (t*3)-i
        return (corners[i][0] + (corners[i+1][0]-corners[i][0])*r,
                corners[i][1] + (corners[i+1][1]-corners[i][1])*r)
    else: # Square
        corners = [(-s,-s),(s,-s),(s,s),(-s,s),(-s,-s)]
        i = int(t*4); r = (t*4)-i
        return (corners[i][0] + (corners[i+1][0]-corners[i][0])*r,
                corners[i][1] + (corners[i+1][1]-corners[i][1])*r)

# ==========================================
# 3. CORE EXTRUSION ENGINE (HOLLOW + CUTS)
# ==========================================
def build_extrusion(params):
    p_type = params.get("profile", "Square")
    path_type = params.get("path", "Linear")
    hollow = float(params.get("hollow", 0.0))
    cut_s, cut_e = float(params.get("cut_s", 0.0)), float(params.get("cut_e", 1.0))

    verts, f_out, f_in, f_cap = [], [], [], []
    
    # Smoothness steps
    p_steps = 40 if p_type in ["Circle", "Star"] else (3 if p_type == "Triangle" else 4)
    path_steps = 32 if path_type == "Circular" else 1
    major_r, size = 1.0, 1.0

    path_t = sorted(set(round(t,6) for t in 
        [cut_s] + [i/p_steps for i in range(1,p_steps)] + [cut_e] 
        if cut_s <= round(t,6) <= cut_e))
    n = len(path_t)

    for s_idx in range(path_steps + 1):
        v_c = s_idx / float(path_steps)
        phi = v_c * 2 * math.pi
        cp, sp = math.cos(phi), math.sin(phi)

        # Outer loop
        for t in path_t:
            px, py = get_profile_point(t, p_type)
            if path_type == "Linear":
                verts.append((px, py, -size if s_idx == 0 else size))
            else:
                verts.append(((major_r + px) * cp, (major_r + px) * sp, py))
        
        # Inner loop (Hollow)
        if hollow > 0:
            for t in path_t:
                px, py = get_profile_point(t, p_type)
                if path_type == "Linear":
                    verts.append((px*hollow, py*hollow, -size if s_idx == 0 else size))
                else:
                    verts.append(((major_r + px*hollow)*cp, (major_r + px*hollow)*sp, py*hollow))

    vps = n * (2 if hollow > 0 else 1)
    def quad(g, a, b, c, d): g.extend([(a,b,c),(a,c,d)])

    for s in range(path_steps):
        s1, s2 = s * vps, (s+1) * vps
        for i in range(n-1):
            quad(f_out, s1+i, s1+i+1, s2+i+1, s2+i)
            if hollow > 0:
                quad(f_in, s1+i+n+1, s1+i+n, s2+i+n, s2+i+n+1)

    # Caps & Cuts
    if path_type == "Linear":
        base, top = 0, path_steps * vps
        for i in range(1, n-1):
            f_cap.append((base, base+i, base+i+1))
            f_cap.append((top, top+i+1, top+i))
        if hollow > 0:
            for i in range(n-1):
                quad(f_cap, base+i, base+i+1, base+i+n+1, base+i+n)
                quad(f_cap, top+i+n, top+i+n+1, top+i+1, top+i)

    if (cut_e - cut_s) < 1.0:
        for s in range(path_steps):
            a, b = s*vps, (s+1)*vps
            ae, be = a+n-1, b+n-1
            if hollow > 0:
                quad(f_cap, a, b, b+n, a+n)
                quad(f_cap, ae+n, be+n, be, ae)
            else:
                for i in range(1, n-1):
                    f_cap.append((a, a+i, a+i+1))
                    f_cap.append((ae, ae-i, ae-i-1))

    write_dae_final(verts, f_out, f_in, f_cap)

# ==========================================
# 4. EXACT CUBE (FALLBACK)
# ==========================================
def build_exact_cube():
    verts = [(-0.5,-0.5,-1.0),(0.5,-0.5,-1.0),(0.5,0.5,-1.0),(-0.5,0.5,-1.0),
             (-0.5,-0.5, 1.0),(0.5,-0.5, 1.0),(0.5,0.5, 1.0),(-0.5,0.5, 1.0)]
    f_out = [(0,1,2),(0,2,3),(4,6,5),(4,7,6),(0,4,5),(0,5,1),
             (1,5,6),(1,6,2),(2,6,7),(2,7,3),(3,7,4),(3,4,0)]
    write_dae_final(verts, f_out, [], [])

# ==========================================
# 5. DAE WRITER (LOCKED OFFSETS + MATERIALS)
# ==========================================
def write_dae_final(verts, out_f, in_f, cap_f):
    v_data = " ".join(f"{x} {y} {z}" for x,y,z in verts)
    all_faces = out_f + in_f + cap_f
    normals = compute_normals(verts, all_faces)
    n_data = " ".join(f"{x} {y} {z}" for x,y,z in normals)
    
    def pack_vn(f):
        return " ".join(f"{i} {i}" for tri in f for i in tri)

    tri_blocks, effects, materials, binds = "", "", "", ""
    for m_id, faces in [("mat0", out_f), ("mat1", in_f), ("mat2", cap_f)]:
        if faces:
            # FIX: Interleaved offsets (0 for Vertex, 1 for Normal)
            tri_blocks += f"""
        <triangles material="{m_id}" count="{len(faces)}">
          <input semantic="VERTEX" source="#v" offset="0"/>
          <input semantic="NORMAL" source="#n" offset="1"/>
          <p>{pack_vn(faces)}</p>
        </triangles>"""
            effects += f'<effect id="{m_id}-fx"><profile_COMMON><technique sid="common"><lambert><diffuse><color>0.8 0.8 0.8 1</color></diffuse></lambert></technique></profile_COMMON></effect>'
            materials += f'<material id="{m_id}" name="{m_id}"><instance_effect url="#{m_id}-fx"/></material>'
            binds += f'<instance_material symbol="{m_id}" target="#{m_id}"/>'

    dae = f"""<?xml version="1.0" encoding="utf-8"?>
<COLLADA xmlns="http://www.collada.org/2005/11/COLLADASchema" version="1.4.1">
  <asset><unit name="meter" meter="1"/><up_axis>Z_UP</up_axis></asset>
  <library_effects>{effects}</library_effects>
  <library_materials>{materials}</library_materials>
  <library_geometries><geometry id="m"><mesh>
    <source id="p">
      <float_array id="pa" count="{len(verts)*3}">{v_data}</float_array>
      <technique_common><accessor source="#pa" count="{len(verts)}" stride="3"><param name="X" type="float"/><param name="Y" type="float"/><param name="Z" type="float"/></accessor></technique_common>
    </source>
    <source id="n">
      <float_array id="na" count="{len(normals)*3}">{n_data}</float_array>
      <technique_common><accessor source="#na" count="{len(normals)}" stride="3"><param name="X" type="float"/><param name="Y" type="float"/><param name="Z" type="float"/></accessor></technique_common>
    </source>
    <vertices id="v"><input semantic="POSITION" source="#p"/></vertices>
    {tri_blocks}
  </mesh></geometry></library_geometries>
  <library_visual_scenes><visual_scene id="S"><node><instance_geometry url="#m">
    <bind_material><technique_common>{binds}</technique_common></bind_material>
  </instance_geometry></node></visual_scene></library_visual_scenes>
  <scene><instance_visual_scene url="#S"/></scene>
</COLLADA>"""
    with open(OUTPUT, "w") as f: f.write(dae)

# ==========================================
# ROUTES
# ==========================================
@app.route("/generate", methods=["POST"])
def generate():
    raw = request.data.decode("utf-8")
    params = dict(p.split("=") for p in raw.split("|") if "=" in p)
    if params.get("profile") == "Square" and params.get("path") == "Linear" and float(params.get("hollow", 0)) == 0:
        build_exact_cube()
    else:
        build_extrusion(params)
    return f"{BASE_URL}/download"

@app.route("/download")
def download(): return send_file(OUTPUT, as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
