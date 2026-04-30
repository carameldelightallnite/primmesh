from flask import Flask, request

app = Flask(__name__)

@app.route("/")
def home():
    return "PrimMesh Server Running"

@app.route("/generate", methods=["POST"])
def generate():
    try:
        data = request.data.decode("utf-8")
        print("Received:", data)

        return "OK"

    except Exception as e:
        return str(e)

if __name__ == "__main__":
    app.run()
