from flask import Flask, request, send_file
import math
import os

app = Flask(__name__)

OUTPUT = "shape.dae"
BASE_URL = "https://m3-mesh-engine.onrender.com"

# =========================
# VERIFIED PRISM
# =========================
def buildprism():
    # 7 Vertices: 4 for the base, 3 for the top ridge
    verts = [
        (-0.1, -0.1, -0.1), # 0
        ( 0.1, -0.1, -0.1), # 1
        ( 0.1,  0.1, -0.1), # 2
        (-0.1,  0.1, -0.1), # 3
        (-0.1, -0.1,  0.1), # 4
        ( 0.1, -0.1,  0.1), # 5
        ( 0.0,  0.1,  0.1)  # 6
    ]
    
    # 8 Triangles
    faces = [
        (0, 1, 2), (0, 2, 3), # Bottom
        (0, 4, 1), (1, 4, 5), # Front Wall
        (0, 3, 4),            # Left Side
        (1, 5, 2),            # Right Side
        (3, 2, 6),            # Back Slope
        (4, 6, 5)             # Front Slope
    ]
    write_dae(verts, faces)

# =========================
# REAL TUBE
# =========================
def buildtube():
    segments = 24
    outer_r, inner_r, h = 0.12, 0.07, 0.2
    top_z, bot_z = h/2, -h/2
    verts, faces = [], []

    for i in range(segments):
        theta = 2 * math.pi * i / segments
        c, s = math.cos(theta), math.sin(theta)
        verts.extend([
            (outer_r * c, outer_r * s, top_z), # OT
            (outer_r * c, outer_r * s, bot_z), # OB
            (inner_r * c, inner_r * s, top_z), # IT
            (inner_r * c, inner_r * s, bot_z)  # IB
        ])

    for i in range(segments):
        curr, nxt = i * 4, ((i + 1) % segments) * 4
        faces.extend([
            (curr+0, curr+1, nxt+0), (nxt+0, curr+1, nxt+1), # Outer
            (curr+2, nxt+2, curr+3), (nxt+2, nxt+3, curr+3), # Inner
            (curr+0, nxt+0, curr+2), (nxt+0, nxt+2, curr+2), # Top Rim
            (curr+1, curr+3, nxt+1), (nxt+1, curr+3, nxt+3)  # Bot Rim
        ])
    write_dae(verts, faces)

# =========================
# DAE WRITER UTILITY
# =========================
def write_dae(verts, faces):
    v_str = " ".join(f"{v[0]} {v[1]} {v[2]}" for v in verts)
    i_str = " ".join(f"{f[0]} {f[1]} {f[2]}" for f in faces)
    dae = f"""<?xml version="1.0" encoding="utf-8"?>
<COLLADA xmlns="http://www.collada.org/2005/11/COLLADASchema" version="1.4.1">
  <asset><unit name="meter" meter="1"/><up_axis>Z_UP</up_axis></asset>
  <library_geometries>
    <geometry id="mesh">
      <mesh>
        <source id="pos">
          <float_array id="posArr" count="{len(verts)*3}">{v_str}</float_array>
          <technique_common>
            <accessor source="#posArr" count="{len(verts)}" stride="3">
              <param name="X" type="float"/><param name="Y" type="float"/><param name="Z" type="float"/>
            </accessor>
          </technique_common>
        </source>
        <vertices id="verts"><input semantic="POSITION" source="#pos"/></vertices>
        <triangles count="{len(faces)}">
          <input semantic="VERTEX" source="#verts" offset="0"/>
          <p>{i_str}</p>
        </triangles>
      </mesh>
    </geometry>
  </library_geometries>
  <library_visual_scenes>
    <visual_scene id="Scene"><node id="node"><instance_geometry url="#mesh"/></node></visual_scene>
  </library_visual_scenes>
  <scene><instance_visual_scene url="#Scene"/></scene>
</COLLADA>"""
    with open(OUTPUT, "w") as f: f.write(dae)

# =========================
# API ROUTES
# =========================
@app.route("/generate", methods=["POST"])
def generate():
    data = request.data.decode("utf-8")
    if "Prism" in data: buildprism()
    elif "Tube" in data: buildtube()
    else: buildprism() # Default
    return f"{BASE_URL}/download"

@app.route("/download")
def download():
    return send_file(OUTPUT, as_attachment=True)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
