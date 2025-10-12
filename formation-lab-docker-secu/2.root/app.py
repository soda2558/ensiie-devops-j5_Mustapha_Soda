from flask import Flask, request, jsonify
import pickle

app = Flask(__name__)

@app.route("/")
def home():
    return """
    <h1>Pickle File Upload Service</h1>
    <p>Welcome! This server provides an endpoint to upload and deserialize pickled data.</p>
    <h2>Usage:</h2>
    <p><strong>POST /upload</strong></p>
    <p>Send a raw binary payload containing a pickled Python object.</p>
    <pre>
    curl -X POST http://localhost:8080/upload --data-binary content
    </pre>
    """

@app.route("/upload", methods=["POST"])
def upload():
    data = request.data

    try:
        obj = pickle.loads(data)
        return jsonify({"message": "Data processed successfully!", "data": str(obj)})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)
