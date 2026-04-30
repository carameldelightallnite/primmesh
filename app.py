from flask import Flask, request

app = Flask(__name__)

OUTPUT = "sphere.dae"

def buildsphere():
    content = """<?xml version="1.0" encoding="utf-8"?>
<COLLADA xmlns="http://www.collada.org/2005/11/COLLADASchema" version="1.4.1">
  <asset>
    <unit name="meter" meter="1"/>
    <up_axis>Z_UP</up_axis>
  </asset>

  <library_geometries>
    <geometry id="sphere" name="sphere">
      <mesh>

        <source id="spherePos">
          <float_array id="sphereArr" count="72">
          0 0 0.1   0.1 0 0   0 0.1 0
          -0.1 0 0  0 -0.1 0  0 0 -0.1
          0.07 0.07 0  -0.07 0.07 0
          -0.07 -0.07 0  0.07 -0.07 0
          0 0.07 0.07  0 -0.07 0.07
          0 0.07 -0.07 0 -0.07 -0.07
          </float_array>

          <technique_common>
            <accessor source="#sphereArr" count="24" stride="3">
              <param name="X" type="float"/>
              <param name="Y" type="float"/>
              <param name="Z" type="float"/>
            </accessor>
          </technique_common>
        </source>

        <vertices id="sphereVerts">
          <input semantic="POSITION" source="#spherePos"/>
        </vertices>

        <triangles count="8">
          <input semantic="VERTEX" source="#sphereVerts" offset="0"/>
          <p>
          0 1 2
          0 2 3
          0 3 4
          0 4 1
          5 1 2
          5 2 3
          5 3 4
          5 4 1
          </p>
        </triangles>

      </mesh>
    </geometry>
  </library_geometries>

  <library_visual_scenes>
    <visual_scene id="Scene">
      <node id="sphereNode">
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
        f.write(content)

@app.route("/")
def home():
    return "PrimMesh Server Running"

@app.route("/generate", methods=["POST"])
def generate():
    try:
        data = request.data.decode("utf-8")
        print("Received:", data)

        buildsphere()

        return "Download ready: https://m3-mesh-engine.onrender.com/download"

    except Exception as e:
        return str(e)

@app.route("/download")
def download():
    from flask import send_file
    return send_file(OUTPUT, as_attachment=True)

if __name__ == "__main__":
    app.run()
