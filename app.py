from flask import Flask, request, send_file
import math
import os

app = Flask(__name__)

OUTPUT = "shape.dae"
BASE_URL = "https://m3-mesh-engine.onrender.com"

# ==========================================
# ADVANCED GEOMETRY ENGINE
# ==========================================

def buildcube(hollow=0.0, path_cut=1.0, taper=(1.0, 1.0), shear=(0.0, 0.0)):
    """
    hollow: 0.0 (solid) to 0.95 (thin walls)
    path_cut: 1.0 (full) to 0.1 (sliver)
    taper: (x_scale, y_scale) for the top face
    shear: (x_offset, y_offset) for the top face
    """
    verts = []
    faces = []
    
    size = 0.1
    z_levels = [-size, size]
    
    # Generate 4 points for a square (counter-clockwise)
    base_coords = [(-size, -size), (size, -size), (size, size), (-size, size)]
    
    # We build two rings per Z level if hollow > 0
    # Ring 0: Bottom Outer, Ring 1: Bottom Inner
    # Ring 2: Top Outer,    Ring 3: Top Inner
    
    for i, z in enumerate(z_levels):
        # Apply Taper and Shear only to the top level (index 1)
        tx, ty = (taper[0], taper[1]) if z > 0 else (1.0, 1.0)
        sx, sy = (shear[0], shear[1]) if z > 0 else (0.0, 0.0)
        
        # Outer Ring
        for px, py in base_coords:
            verts.append((px * tx + sx, py * ty + sy, z))
            
        # Inner Ring (Hollow)
        if hollow > 0:
            for px, py in base_coords:
                verts.append((px * tx * hollow + sx, py * ty * hollow + sy, z))

    # Helper to add quads
    def add_quad(a, b, c, d):
        faces.extend([(a, b, c), (a, c, d)])

    # Logic for faces
    if hollow <= 0:
        # SOLID CUBE logic
        # Side walls
        for i in range(4):
            nxt = (i + 1) % 4
            add_quad(i, nxt, nxt + 4, i + 4)
        # Caps
        add_quad(3, 2, 1, 0) # Bottom
        add_quad(4, 5, 6, 7) # Top
    else:
        # HOLLOW PIPE logic
        # Outer Walls
        for i in range(4):
            nxt = (i + 1) % 4
            add_quad(i, nxt, nxt + 8, i + 8)
        # Inner Walls
        for i in range(4):
            nxt = (i + 1) % 4
            add_quad(i + 4, i + 12, nxt + 12, nxt + 4)
        # Top Rim
        for i in range(4):
            nxt = (i + 1) % 4
            add_quad(i + 8, nxt + 8, nxt + 12, i + 12)
        # Bottom Rim
        for i in range(4):
            nxt = (i + 1) % 4
            add_quad(i, i + 4, nxt + 4, nxt)

    write_dae(verts, faces)

def buildprism():
    # Keep your verified prism
    verts = [(-0.1,-0.1,-0.1),(0.1,-0.1,-0.1),(0.1,0.1,-0.1),(-0.1,0.1,-0.1),
             (-0.1,-0.1,0.1),(0.1,-0.1,0.1),(0.0,0.1,0.1)]
    faces = [(0,1,2),(0,2,3),(0,4,1),(1,4,5),(0,3,4),(1,5,2),(3,2,6),(4,6,5)]
    write_dae(verts, faces)

def buildtube():
    # Keep your verified tube
    segments = 24
    outer_r, inner_r, h = 0.12, 0.07, 0.2
    top_z, bot_z = h/2, -h/2
    verts, faces = [], []
    for i in range(segments):
        theta = 2 * math.pi * i / segments
        c, s = math.cos(theta), math.sin(theta)
        verts.extend([(outer_r*c, outer_r*s, top_z), (outer_r*c, outer_r*s, bot_z),
                      (inner_r*c, inner_r*s, top_z), (inner_r*c, inner_r*s, bot_z)])
    for i in range(segments):
        curr, nxt = i*4, ((i+1)%segments)*4
        faces.extend([(curr+0,curr+1,nxt+0),(nxt+0,curr+1,nxt+1),
                      (curr+2,nxt+2,curr+3),(nxt+2,nxt+3,curr+3),
                      (curr+0,nxt+0,curr+2),(nxt+0,nxt+2,curr+2),
                      (curr+1,curr+3,nxt+1),(nxt+1,curr+3,nxt+3)])
    write_dae(verts, faces)

# =========================
# DAE WRITER (UNCHANGED)
# =========================
def write_dae(verts, faces):
    v_str = " ".join(f"{x} {y} {z}" for (x, y, z) in verts)
    i_str = " ".join(f"{a} {b} {c}" for (a, b, c) in faces)
    dae = f"""<?xml version="1.0" encoding="utf-8"?>
<COLLADA xmlns="http://www.collada.org/2005/11/COLLADASchema" version="1.4.1">
  <asset><unit name="meter" meter="1"/><up_axis>Z_UP</up_axis></asset>
  <library_geometries>
    <geometry id="mesh"><mesh>
        <source id="pos">
          <float_array id="posArr" count="{len(verts)*3}">{v_str}</float_array>
          <technique_common><accessor source="#posArr" count="{len(verts)}" stride="3">
              <param name="X" type="float"/><param name="Y" type="float"/><param name="Z" type="float"/>
          </accessor></technique_common>
        </source>
        <vertices id="verts"><input semantic="POSITION" source="#pos"/></vertices>
        <triangles count="{len(faces)}"><input semantic="VERTEX" source="#verts" offset="0"/><p>{i_str}</p></triangles>
    </mesh></geometry>
  </library_geometries>
  <library_visual_scenes><visual_scene id="Scene"><node id="node"><instance_geometry url="#mesh"/></node></visual_scene></library_visual_scenes>
  <scene><instance_visual_scene url="#Scene"/></scene>
</COLLADA>"""
    with open(OUTPUT, "w") as f: f.write(dae)

# =========================
# ROUTES
# =========================
@app.route("/generate", methods=["POST"])
def generate():
    data = request.data.decode("utf-8")

    if "Prism" in data:
        buildprism()
    elif "Tube" in data:
        buildtube()
    elif "Cube" in data:
        # Example: Building a Sheared, Tapered, Hollow Cube
        # In a real scenario, you'd parse these from 'data'
        buildcube(hollow=0.7, taper=(0.5, 0.5), shear=(0.05, 0.0))
    else:
        return "ERROR: Unknown shape"

    return f"{BASE_URL}/download"

@app.route("/download")
def download():
    return send_file(OUTPUT, as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
