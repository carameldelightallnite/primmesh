from flask import Flask, request, send_file
import math

app = Flask(__name__)

OUTPUT = "sphere.dae"
BASE_URL = "https://m3-mesh-engine.onrender.com"

def buildsphere():
    segments = 24
    rings = 16
    radius = 0.1

    verts = []
    faces = []

    verts.append((0.0, 0.0, radius))

    for i in range(1, rings):
        phi = math.pi * i / rings
        for j in range(segments):
            theta = 2 * math.pi * j / segments
            x = radius * math.sin(phi) * math.cos(theta)
            y = radius * math.sin(phi) * math.sin(theta)
            z = radius * math.cos(phi)
            verts.append((x, y, z))

    verts.append((0.0, 0.0, -radius))

    top = 0
    bottom = len(verts) - 1

    for j in range(segments):
        a = 1 + j
        b = 1 + (j + 1) % segments
        faces.append((top, a, b))

    for i in range(1, rings - 1):
        for j in range(segments):
            cur = 1 + (i - 1) * segments + j
            nxt = cur + segments

            right = 1 + (i - 1) * segments + (j + 1) % segments
            nxt_right = right + segments

            faces.append((cur, nxt, right))
            faces.append((right, nxt, nxt_right))

    start = 1 + (rings - 2) * segments
    for j in range(segments):
        a = start + j
        b = start + (j + 1) % segments
        faces.append((a, bottom, b))

    vert_array = " ".join(f"{x} {y} {z}" for (x, y, z) in verts)
    index_array = " ".join(str(i) for f in faces for i in f)

    dae = f"""<?xml version="1.0" encoding="utf-8"?>
<COLLADA xmlns="http://www.collada.org/2005/11/COLLADASchema" version="1.4.1">
  <asset>
    <unit name="meter" meter="1"/>
    <up_axis>Z_UP</up_axis>
  </asset>

  <library_geometries>
    <geometry id="sphere" name="sphere">
      <mesh>

        <source id="sphere-pos">
          <float_array id="sphere-arr" count="{len(verts)*3}">
            {vert_array}
          </float_array>
          <technique_common>
            <accessor source="#sphere-arr" count="{len(verts)}" stride="3">
              <param name="X" type="float"/>
              <param name="Y" type="float"/>
              <param name="Z" type="float"/>
            </accessor>
          </technique_common>
        </source>

        <vertices id="sphere-verts">
          <input semantic="POSITION" source="#sphere-pos"/>
        </vertices>

        <triangles count="{len(faces)}">
          <input semantic="VERTEX" source="#sphere-verts" offset="0"/>
          <p>{index_array}</p>
        </triangles>

      </mesh>
    </geometry>
  </library_geometries>

  <library_visual_scenes>
    <visual_scene id="Scene">
      <node id="sphere-node">
        <instance_geometry url="#sphere"/>
      </node>
    </visual_scene>
  </library_visual_scenes>

  <scene>
    <instance_visual_scene url="#Scene"/>
  </scene>
</COLLADA>
"""

    with open(OUTPUT, "w") as f:
        f.write(dae)


@app.route("/")
def home():
    return "PrimMesh Server Running"


@app.route("/generate", methods=["POST"])
def generate():
    buildsphere()
    return f"{BASE_URL}/download"   # 🔥 ONLY CHANGE


@app.route("/download")
def download():
    return send_file(OUTPUT, as_attachment=True)


if __name__ == "__main__":
    app.run()
