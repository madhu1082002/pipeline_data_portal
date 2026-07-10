import os

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from config import CORS_ORIGINS, PORT
from services import databricks_service

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
CORS(app, origins=CORS_ORIGINS.split(",") if CORS_ORIGINS != "*" else "*")


def _db_error_response(exc: Exception):
    return jsonify({"error": str(exc)}), 503


@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "service": "Pipeline Data Portal",
        "database": f"{databricks_service.DATABRICKS_CATALOG}.{databricks_service.DATABRICKS_SCHEMA}",
    })


@app.route("/databricks/status")
def databricks_status():
    return jsonify(databricks_service.get_connection_status())


@app.route("/pipelines", methods=["GET"])
def get_pipelines():
    try:
        rows = databricks_service.list_pipelines()
        return jsonify({"pipelines": rows, "count": len(rows)})
    except Exception as e:
        return _db_error_response(e)


@app.route("/pipelines", methods=["POST"])
def create_pipeline():
    body = request.get_json(silent=True) or {}
    if not body.get("pipeline_name") or not body.get("status"):
        return jsonify({"error": "pipeline_name and status are required"}), 400
    try:
        databricks_service.insert_pipeline(body)
        return jsonify({"status": "created", "pipeline_name": body["pipeline_name"]}), 201
    except Exception as e:
        return _db_error_response(e)


@app.route("/pipelines/<path:pipeline_name>", methods=["PUT"])
def update_pipeline(pipeline_name: str):
    body = request.get_json(silent=True) or {}
    if not body.get("pipeline_name") or not body.get("status"):
        return jsonify({"error": "pipeline_name and status are required"}), 400
    try:
        databricks_service.update_pipeline(pipeline_name, body)
        return jsonify({"status": "updated", "pipeline_name": body["pipeline_name"]})
    except Exception as e:
        return _db_error_response(e)


@app.route("/pipelines/<path:pipeline_name>", methods=["DELETE"])
def delete_pipeline(pipeline_name: str):
    try:
        databricks_service.delete_pipeline(pipeline_name)
        return jsonify({"status": "deleted", "pipeline_name": pipeline_name})
    except Exception as e:
        return _db_error_response(e)


@app.route("/failures", methods=["GET"])
def get_failures():
    try:
        rows = databricks_service.list_failures()
        return jsonify({"failures": rows, "count": len(rows)})
    except Exception as e:
        return _db_error_response(e)


@app.route("/failures", methods=["POST"])
def create_failure():
    body = request.get_json(silent=True) or {}
    if not body.get("pipeline_name"):
        return jsonify({"error": "pipeline_name is required"}), 400
    try:
        databricks_service.insert_failure(body)
        return jsonify({"status": "created", "pipeline_name": body["pipeline_name"]}), 201
    except Exception as e:
        return _db_error_response(e)


@app.route("/failures/<path:pipeline_name>", methods=["PUT"])
def update_failure(pipeline_name: str):
    body = request.get_json(silent=True) or {}
    failure_time = request.args.get("failure_time")
    if not failure_time:
        return jsonify({"error": "failure_time query parameter is required"}), 400
    if not body.get("pipeline_name"):
        return jsonify({"error": "pipeline_name is required"}), 400
    try:
        databricks_service.update_failure(pipeline_name, failure_time, body)
        return jsonify({"status": "updated"})
    except Exception as e:
        return _db_error_response(e)


@app.route("/failures/<path:pipeline_name>", methods=["DELETE"])
def delete_failure(pipeline_name: str):
    failure_time = request.args.get("failure_time")
    if not failure_time:
        return jsonify({"error": "failure_time query parameter is required"}), 400
    try:
        databricks_service.delete_failure(pipeline_name, failure_time)
        return jsonify({"status": "deleted"})
    except Exception as e:
        return _db_error_response(e)


@app.route("/clusters", methods=["GET"])
def get_clusters():
    try:
        rows = databricks_service.list_clusters()
        return jsonify({"clusters": rows, "count": len(rows)})
    except Exception as e:
        return _db_error_response(e)


@app.route("/clusters", methods=["POST"])
def create_cluster():
    body = request.get_json(silent=True) or {}
    if not body.get("cluster_id"):
        return jsonify({"error": "cluster_id is required"}), 400
    try:
        databricks_service.insert_cluster(body)
        return jsonify({"status": "created", "cluster_id": body["cluster_id"]}), 201
    except Exception as e:
        return _db_error_response(e)


@app.route("/clusters/<path:cluster_id>", methods=["PUT"])
def update_cluster(cluster_id: str):
    body = request.get_json(silent=True) or {}
    if not body.get("cluster_id"):
        return jsonify({"error": "cluster_id is required"}), 400
    try:
        databricks_service.update_cluster(cluster_id, body)
        return jsonify({"status": "updated", "cluster_id": body["cluster_id"]})
    except Exception as e:
        return _db_error_response(e)


@app.route("/clusters/<path:cluster_id>", methods=["DELETE"])
def delete_cluster(cluster_id: str):
    try:
        databricks_service.delete_cluster(cluster_id)
        return jsonify({"status": "deleted", "cluster_id": cluster_id})
    except Exception as e:
        return _db_error_response(e)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=PORT)
