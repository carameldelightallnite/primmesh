# FINAL app.py (UPLOAD SAFE)

from flask import Flask, request, jsonify, send_from_directory
import os, uuid

app = Flask(__name__)
OUT = "output"
os.makedirs(OUT, exist_ok=True)

def cube():
    v = [
        (-0.5,-0.5,-0.5),(0.5,-0.5,-0.5),(0.5,0.5,-0.5),(-0.5,0.5,-0.5),
        (-0.5,-0.5,0.5),(0.5,-0.5,0.5),(0.5,0.5,0.5),(-0.5,0.5,0.5)
    ]
    f = [
        (0,1,2),(0,2,3),(4,5,6),(4,6,7),
        (0,1,5),(0,5,4),(2,3,7),(2,7,6),
        (1,2,6),(1,6,5),(3,0,4),(3,4,7)
    ]
    return v,f

def write_dae(path):
    v,f = cube()

    with open(path,"w") as o:
        o.write('<?xml version="1.0" encoding="utf-8"?>')
        o.write('<COLLADA version="1.4.1">')
        o.write('<library_geometries><geometry id="m"><mesh>')
        o.write('<source id="p"><float_array count="24">')
        for x,y,z in v: o.write(f"{x} {y} {z} ")
        o.write('</float_array></source>')
        o.write('<vertices id="v"><input semantic="POSITION" source="#p"/></vertices>')
        o.write('<triangles count="12"><input semantic="VERTEX" source="#v" offset="0"/><p>')
        for a,b,c in f: o.write(f"{a} {b} {c} ")
        o.write('</p></triangles>')
        o.write('</mesh></geometry></library_geometries>')
        o.write('<scene><instance_visual_scene url="#s"/></scene>')
        o.write('</COLLADA>')

@app.route("/convert",methods=["POST"])
def convert():
    name=str(uuid.uuid4())+".dae"
    write_dae(os.path.join(OUT,name))
    return jsonify({"file":name})

@app.route("/output/<f>")
def out(f): return send_from_directory(OUT,f)

app.run(host="0.0.0.0",port=10000)
