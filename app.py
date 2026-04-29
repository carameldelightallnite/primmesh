from flask import Flask, request, jsonify, send_from_directory
import os, uuid, math

app = Flask(__name__)
OUT = "output"
os.makedirs(OUT, exist_ok=True)

# ---------- SHAPES ----------
def cube(sx,sy,sz):
    hx,hy,hz = sx/2,sy/2,sz/2
    v=[(-hx,-hy,-hz),(hx,-hy,-hz),(hx,hy,-hz),(-hx,hy,-hz),
       (-hx,-hy,hz),(hx,-hy,hz),(hx,hy,hz),(-hx,hy,hz)]
    f=[(0,1,2),(0,2,3),(4,5,6),(4,6,7),
       (0,1,5),(0,5,4),(2,3,7),(2,7,6),
       (1,2,6),(1,6,5),(3,0,4),(3,4,7)]
    return v,f

def sphere(sx,sy,sz,rings=8,seg=16):
    rx,ry,rz = sx/2,sy/2,sz/2
    v=[];f=[]
    for i in range(rings+1):
        phi=math.pi*i/rings
        for j in range(seg):
            theta=2*math.pi*j/seg
            v.append((rx*math.sin(phi)*math.cos(theta),
                      ry*math.sin(phi)*math.sin(theta),
                      rz*math.cos(phi)))
    for i in range(rings):
        for j in range(seg):
            a=i*seg+j
            b=i*seg+(j+1)%seg
            c=(i+1)*seg+j
            d=(i+1)*seg+(j+1)%seg
            f.append((a,c,b))
            f.append((b,c,d))
    return v,f

def build_shape(t,sx,sy,sz):
    if t==2: return sphere(sx,sy,sz)
    return cube(sx,sy,sz)

# ---------- TRANSFORM ----------
def apply(v,p,r):
    return [(vx+p[0],vy+p[1],vz+p[2]) for (vx,vy,vz) in v]

# ---------- DAE (VALID FOR SL) ----------
def write_dae(path,v,f):
    with open(path,"w") as o:
        o.write('<?xml version="1.0" encoding="utf-8"?>')
        o.write('<COLLADA xmlns="http://www.collada.org/2005/11/COLLADASchema" version="1.4.1">')
        o.write('<library_geometries><geometry id="mesh"><mesh>')

        # positions
        o.write(f'<source id="p"><float_array id="pa" count="{len(v)*3}">')
        for x,y,z in v: o.write(f"{x} {y} {z} ")
        o.write('</float_array>')
        o.write('<technique_common>')
        o.write(f'<accessor source="#pa" count="{len(v)}" stride="3">')
        o.write('<param name="X" type="float"/>')
        o.write('<param name="Y" type="float"/>')
        o.write('<param name="Z" type="float"/>')
        o.write('</accessor></technique_common></source>')

        # normals (required)
        o.write(f'<source id="n"><float_array id="na" count="{len(v)*3}">')
        for x,y,z in v: o.write(f"{x} {y} {z} ")
        o.write('</float_array>')
        o.write('<technique_common>')
        o.write(f'<accessor source="#na" count="{len(v)}" stride="3">')
        o.write('<param name="X" type="float"/>')
        o.write('<param name="Y" type="float"/>')
        o.write('<param name="Z" type="float"/>')
        o.write('</accessor></technique_common></source>')

        o.write('<vertices id="v"><input semantic="POSITION" source="#p"/></vertices>')

        o.write(f'<triangles count="{len(f)}">')
        o.write('<input semantic="VERTEX" source="#v" offset="0"/>')
        o.write('<input semantic="NORMAL" source="#n" offset="0"/>')
        o.write('<p>')
        for a,b,c in f: o.write(f"{a} {b} {c} ")
        o.write('</p></triangles>')

        o.write('</mesh></geometry></library_geometries>')
        o.write('<library_visual_scenes><visual_scene id="s"><node>')
        o.write('<instance_geometry url="#mesh"/>')
        o.write('</node></visual_scene></library_visual_scenes>')
        o.write('<scene><instance_visual_scene url="#s"/></scene>')
        o.write('</COLLADA>')

# ---------- ROUTE ----------
@app.route("/convert",methods=["POST"])
def convert():
    data=request.json.get("prims",[])
    V=[];F=[];off=0

    for p in data:
        t=p.get("type",0)
        sx,sy,sz=p["size"]
        pos=p.get("pos",[0,0,0])
        v,f=build_shape(t,sx,sy,sz)
        v=apply(v,pos,[0,0,0,1])

        V.extend(v)
        for a,b,c in f: F.append((a+off,b+off,c+off))
        off+=len(v)

    if not V: return jsonify({"error":"no geometry"}),400

    name=str(uuid.uuid4())+".dae"
    write_dae(os.path.join(OUT,name),V,F)
    return jsonify({"file":name})

@app.route("/output/<f>")
def out(f): return send_from_directory(OUT,f)

if __name__=="__main__":
    app.run(host="0.0.0.0",port=10000)
