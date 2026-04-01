from flask import Flask, jsonify, request
import threading
import webbrowser
import time
from core import run_check, prepare_sync, execute_sync, compare_servers, run_local_check, get_mappings, save_mappings, prepare_local_sync, execute_local_sync
from config import SOURCE_CAMUNDA_REST_URL, TARGET_CAMUNDA_REST_URL, GIT_REPO_PATH, CAMUNDA_BASE_URL, TECHNICAL_FOLDER_PATH

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
        "GIT_REPO_PATH": GIT_REPO_PATH,
        "CAMUNDA_BASE_URL": CAMUNDA_BASE_URL,
        "TECHNICAL_FOLDER_PATH": TECHNICAL_FOLDER_PATH
    })

@app.route("/api/check")
def api_check():
    result = run_check()
    return jsonify(result)

@app.route("/api/local-check")
def api_local_check():
    base_url = request.args.get("baseUrl")
    result = run_local_check(base_url)
    return jsonify(result)

@app.route("/api/mapping", methods=["GET"])
def api_get_mapping():
    return jsonify(get_mappings())

@app.route("/api/mapping", methods=["POST"])
def api_post_mapping():
    data = request.json
    save_mappings(data)
    return jsonify({"status": "success"})

@app.route("/api/compare")
def api_compare():
    source_url = request.args.get('sourceUrl')
    target_url = request.args.get('targetUrl')
    result = compare_servers(source_url, target_url)
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

@app.route("/api/local-sync/prepare", methods=["POST"])
def api_prepare_local_sync():
    data = request.json
    selected_items = data.get("selected_items", [])
    result = prepare_local_sync(selected_items)
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

@app.route("/api/local-sync/execute", methods=["POST"])
def api_execute_local_sync():
    data = request.json
    session_id = data.get("session_id")
    base_url = data.get("baseUrl")
    if not session_id or session_id not in session_store:
        return jsonify({"error": "Invalid or expired session. Please prepare local sync again."}), 400
        
    payload = session_store[session_id]
    result = execute_local_sync(payload, base_url)
    
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
