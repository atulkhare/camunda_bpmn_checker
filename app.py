from flask import Flask, jsonify, request
import threading
import webbrowser
import time
from core import run_check, prepare_sync, execute_sync
from config import SOURCE_CAMUNDA_REST_URL, TARGET_CAMUNDA_REST_URL, GIT_REPO_PATH

app = Flask(__name__, static_folder='static', static_url_path='/', template_folder='static')

session_store = {}

@app.route("/")
def index():
    return app.send_static_file("index.html")

@app.route("/api/config")
def get_config():
    return jsonify({
        "SOURCE_CAMUNDA_REST_URL": SOURCE_CAMUNDA_REST_URL,
        "TARGET_CAMUNDA_REST_URL": TARGET_CAMUNDA_REST_URL,
        "GIT_REPO_PATH": GIT_REPO_PATH
    })

@app.route("/api/check")
def api_check():
    result = run_check()
    return jsonify(result)

@app.route("/api/sync/prepare")
def api_prepare_sync():
    result = prepare_sync()
    if not result.get("error"):
        frontend_data = {}
        for dep_name, files in result["deployments_to_sync"].items():
            frontend_data[dep_name] = list(files.keys())
            
        import uuid
        session_id = str(uuid.uuid4())
        session_store[session_id] = result["deployments_to_sync"]
        
        return jsonify({
            "deployments": frontend_data,
            "session_id": session_id
        })
    else:
        return jsonify({"error": result["error"]}), 500

@app.route("/api/sync/execute", methods=["POST"])
def api_execute_sync():
    data = request.json
    session_id = data.get("session_id")
    if not session_id or session_id not in session_store:
        return jsonify({"error": "Invalid or expired session. Please prepare sync again."}), 400
        
    payload = session_store[session_id]
    result = execute_sync(payload)
    
    del session_store[session_id]
    return jsonify(result)

def start_server():
    def open_browser():
        time.sleep(1)
        webbrowser.open("http://127.0.0.1:5000")

    threading.Thread(target=open_browser, daemon=True).start()
    app.run(debug=False, port=5000, host="127.0.0.1")

if __name__ == "__main__":
    start_server()
