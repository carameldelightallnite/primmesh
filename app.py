from flask import Flask, request, send_file
import math
import os

app = Flask(__name__)

OUTPUT = "shape.dae"
BASE_URL = "https://m3-mesh-engine.onrender.com"


# =========================
# VERIFIED PRISM (UNCHANGED)
# =========================
def buildprism():
    verts = [
        (-0.1, -0.1, -0.1),
        ( 0.1, -0.1, -0.1),
        ( 0.1,  0.1, -0.1),
        (-0.1,  0.1, -0.1),
        (-0.1, -0.1,  0.1),
        ( 0.1, -0.1,  0.1),
        ( 0.0,  0.1,  0.1)
    ]

    faces = [
        (0, 1, 2), (0, 2, 3),
        (0, 4, 1), (1, 4, 5),
        (0, 3, 4),
        (1, 5, 2),
        (3, 2, 6),
        (4, 6, 5)
    ]

    write_dae(verts, faces)


# =========================
# REAL TUBE (UNCHANGED)
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
            (outer_r * c, outer_r * s, top_z),
            (outer_r * c, outer_r * s, bot_z),
            (inner_r * c, inner_r * s, top_z),
            (inner_r * c, inner_r * s, bot_z)
        ])

    for i in range(segments):
        curr = i * 4
        nxt = ((i + 1) % segments) * 4

        faces.extend([
            (curr+0, curr+1, nxt+0), (nxt+0, curr+1, nxt+1),
            (curr+2, nxt+2, curr+3), (nxt+2, nxt+3, curr+3),
            (curr+0, nxt+0, curr+2), (nxt+0, nxt+2, curr+2),
            (curr+1, curr+3, nxt+1), (nxt+1, curr+3, nxt+3)
        ])

    write_dae(verts, faces)


# =========================
# REAL CUBE (ADDED)
# =========================
def buildcube():
    verts = [
        (-0.1, -0.1, -0.1),  # 0
        ( 0.1, -0.1, -0.1),  # 1
        ( 0.1,  0.1, -0.1),  # 2
        (-0.1,  0.1, -0.1),  # 3
        (-0.1, -0.1,  0.1),  # 4
        ( 0.1, -0.1,  0.1),  # 5
        ( 0.1,  0.1,  0.1),  # 6
        (-0.1,  0.1,  0.1)   # 7
    ]

    faces = [
        # Bottom
        (0,1,2),(0,2,3),

        # Top
        (4,6,5),(4,7,6),

        # Front
        (0,4,1),(1,4,5),

        # Back
        (3,2,7),(2,6,7),

        # Left
        (0,3,4),(3,7,4),

        # Right
        (1,5,2),(2,5,6)
    ]

    write_dae(verts, faces)


# =========================
# DAE WRITER (UNCHANGED)
# =========================
def write_dae(verts, faces):
    v_str = " ".join(f"{x} {y} {z}" for (x, y, z) in verts)
    i_str = " ".join(f"{a} {b} {c}" for (a, b, c) in faces)

    dae = f"""<?xml version="1.0" encoding="utf-8"?>
<COLLADA xmlns="http://www.collada.org/2005/11/COLLADASchema" version="1.4.1">
  <asset>
    <unit name="meter" meter="1"/>
    <up_axis>Z_UP</up_axis>
  </asset>

  <library_geometries>
    <geometry id="mesh">
      <mesh>
        <source id="pos">
          <float_array id="posArr" count="{len(verts)*3}">{v_str}</float_array>
          <technique_common>
            <accessor source="#posArr" count="{len(verts)}" stride="3">
              <param name="X" type="float"/>
              <param name="Y" type="float"/>
              <param name="Z" type="float"/>
            </accessor>
          </technique_common>
        </source>

        <vertices id="verts">
          <input semantic="POSITION" source="#pos"/>
        </vertices>

        <triangles count="{len(faces)}">
          <input semantic="VERTEX" source="#verts" offset="0"/>
          <p>{i_str}</p>
        </triangles>
      </mesh>
    </geometry>
  </library_geometries>

  <library_visual_scenes>
    <visual_scene id="Scene">
      <node id="node">
        <instance_geometry url="#mesh"/>
      </node>
    </visual_scene>
  </library_visual_scenes>

  <scene>
    <instance_visual_scene url="#Scene"/>
  </scene>
</COLLADA>"""

    with open(OUTPUT, "w") as f:
        f.write(dae)


# =========================
# ROUTES (UPDATED — CUBE ADDED ONLY)
# =========================
@app.route("/generate", methods=["POST"])
def generate():
    data = request.data.decode("utf-8")

    if "Prism" in data:
        buildprism()

    elif "Tube" in data:
        buildtube()

    elif "Cube" in data:
        buildcube()

    else:
        return "ERROR: Unknown shape"

    return f"{BASE_URL}/download"


@app.route("/download")
def download():
    return send_file(OUTPUT, as_attachment=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
