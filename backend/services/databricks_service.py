import json
import logging
import time

import requests

from config import (
    DATABRICKS_CATALOG,
    DATABRICKS_HOST,
    DATABRICKS_SCHEMA,
    DATABRICKS_TOKEN,
    DATABRICKS_WAREHOUSE_ID,
    USE_DATABRICKS,
)

logger = logging.getLogger(__name__)


def is_configured() -> bool:
    return USE_DATABRICKS and bool(DATABRICKS_HOST and DATABRICKS_TOKEN and DATABRICKS_WAREHOUSE_ID)


def _table(name: str) -> str:
    return f"{DATABRICKS_CATALOG}.{DATABRICKS_SCHEMA}.{name}"


def _headers() -> dict:
    return {"Authorization": f"Bearer {DATABRICKS_TOKEN}"}


def _rows_to_dicts(result: dict) -> list[dict]:
    columns = [c["name"] for c in result.get("manifest", {}).get("schema", {}).get("columns", [])]
    rows = result.get("result", {}).get("data_array", [])
    return [dict(zip(columns, row)) for row in rows]


def sql_escape(value) -> str:
    if value is None or value == "":
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def execute_sql(statement: str) -> list[dict]:
    if not is_configured():
        raise RuntimeError("Databricks is not configured. Set credentials in .env or dataops-copilot/.env")

    url = f"{DATABRICKS_HOST.rstrip('/')}/api/2.0/sql/statements"
    payload = {
        "warehouse_id": DATABRICKS_WAREHOUSE_ID,
        "statement": statement,
        "wait_timeout": "50s",
    }
    response = requests.post(url, headers=_headers(), json=payload, timeout=60)
    response.raise_for_status()
    statement_id = response.json().get("statement_id")

    for _ in range(30):
        status_resp = requests.get(f"{url}/{statement_id}", headers=_headers(), timeout=30)
        status_resp.raise_for_status()
        status_data = status_resp.json()
        state = status_data.get("status", {}).get("state")
        if state == "SUCCEEDED":
            return _rows_to_dicts(status_data)
        if state in {"FAILED", "CANCELED", "CLOSED"}:
            error = status_data.get("status", {}).get("error", {})
            raise RuntimeError(error.get("message", status_data))
        time.sleep(2)

    raise TimeoutError("Databricks SQL statement timed out")


def get_connection_status() -> dict:
    if not is_configured():
        return {
            "configured": False,
            "connected": False,
            "message": "Set DATABRICKS_HOST, DATABRICKS_TOKEN, DATABRICKS_WAREHOUSE_ID",
        }

    try:
        rows = execute_sql(f"SHOW TABLES IN {DATABRICKS_CATALOG}.{DATABRICKS_SCHEMA}")
        return {
            "configured": True,
            "connected": True,
            "host": DATABRICKS_HOST,
            "catalog": DATABRICKS_CATALOG,
            "schema": DATABRICKS_SCHEMA,
            "tables": len(rows),
            "message": f"Connected to {DATABRICKS_CATALOG}.{DATABRICKS_SCHEMA}",
        }
    except Exception as e:
        logger.exception("Databricks connection failed")
        return {"configured": True, "connected": False, "message": str(e)}


def list_pipelines() -> list[dict]:
    return execute_sql(f"SELECT * FROM {_table('pipeline_runs')} ORDER BY run_time DESC")


def list_failures() -> list[dict]:
    return execute_sql(f"SELECT * FROM {_table('failure_logs')} ORDER BY failure_time DESC")


def list_clusters() -> list[dict]:
    return execute_sql(f"SELECT * FROM {_table('cluster_metrics')} ORDER BY cluster_name")


def insert_pipeline(data: dict) -> None:
    deps = json.dumps(data.get("dependencies") or [])
    sql = f"""
    INSERT INTO {_table('pipeline_runs')} VALUES (
        {sql_escape(data['pipeline_name'])},
        {sql_escape(data['status'])},
        {sql_escape(data.get('run_time'))},
        {sql_escape(data.get('duration_minutes'))},
        {sql_escape(data.get('error_message'))},
        {sql_escape(data.get('cluster_id'))},
        {sql_escape(data.get('cpu_usage'))},
        {sql_escape(data.get('memory_usage'))},
        {sql_escape(deps)},
        {sql_escape(data.get('last_success'))}
    )
    """
    execute_sql(sql)


def update_pipeline(pipeline_name: str, data: dict) -> None:
    safe_name = pipeline_name.replace("'", "''")
    deps = json.dumps(data.get("dependencies") or [])
    sql = f"""
    UPDATE {_table('pipeline_runs')} SET
        pipeline_name = {sql_escape(data['pipeline_name'])},
        status = {sql_escape(data['status'])},
        run_time = {sql_escape(data.get('run_time'))},
        duration_minutes = {sql_escape(data.get('duration_minutes'))},
        error_message = {sql_escape(data.get('error_message'))},
        cluster_id = {sql_escape(data.get('cluster_id'))},
        cpu_usage = {sql_escape(data.get('cpu_usage'))},
        memory_usage = {sql_escape(data.get('memory_usage'))},
        dependencies = {sql_escape(deps)},
        last_success = {sql_escape(data.get('last_success'))}
    WHERE pipeline_name = '{safe_name}'
    """
    execute_sql(sql)


def delete_pipeline(pipeline_name: str) -> None:
    safe_name = pipeline_name.replace("'", "''")
    execute_sql(f"DELETE FROM {_table('pipeline_runs')} WHERE pipeline_name = '{safe_name}'")


def insert_failure(data: dict) -> None:
    dep_status = json.dumps(data.get("dependency_status") or {})
    actions = json.dumps(data.get("suggested_actions") or [])
    sql = f"""
    INSERT INTO {_table('failure_logs')} VALUES (
        {sql_escape(data['pipeline_name'])},
        {sql_escape(data.get('failure_time'))},
        {sql_escape(data.get('root_cause'))},
        {sql_escape(data.get('error_details'))},
        {sql_escape(data.get('cluster_logs'))},
        {sql_escape(dep_status)},
        {sql_escape(actions)}
    )
    """
    execute_sql(sql)


def update_failure(pipeline_name: str, failure_time: str, data: dict) -> None:
    safe_name = pipeline_name.replace("'", "''")
    safe_time = failure_time.replace("'", "''")
    dep_status = json.dumps(data.get("dependency_status") or {})
    actions = json.dumps(data.get("suggested_actions") or [])
    sql = f"""
    UPDATE {_table('failure_logs')} SET
        pipeline_name = {sql_escape(data['pipeline_name'])},
        failure_time = {sql_escape(data.get('failure_time'))},
        root_cause = {sql_escape(data.get('root_cause'))},
        error_details = {sql_escape(data.get('error_details'))},
        cluster_logs = {sql_escape(data.get('cluster_logs'))},
        dependency_status = {sql_escape(dep_status)},
        suggested_actions = {sql_escape(actions)}
    WHERE pipeline_name = '{safe_name}' AND failure_time = '{safe_time}'
    """
    execute_sql(sql)


def delete_failure(pipeline_name: str, failure_time: str) -> None:
    safe_name = pipeline_name.replace("'", "''")
    safe_time = failure_time.replace("'", "''")
    execute_sql(
        f"DELETE FROM {_table('failure_logs')} "
        f"WHERE pipeline_name = '{safe_name}' AND failure_time = '{safe_time}'"
    )


def insert_cluster(data: dict) -> None:
    jobs = json.dumps(data.get("jobs_running") or [])
    sql = f"""
    INSERT INTO {_table('cluster_metrics')} VALUES (
        {sql_escape(data['cluster_id'])},
        {sql_escape(data.get('cluster_name'))},
        {sql_escape(data.get('instance_type'))},
        {sql_escape(data.get('recommended_type'))},
        {sql_escape(data.get('avg_cpu_usage'))},
        {sql_escape(data.get('avg_memory_usage'))},
        {sql_escape(data.get('peak_cpu_usage'))},
        {sql_escape(data.get('peak_memory_usage'))},
        {sql_escape(data.get('monthly_cost_inr'))},
        {sql_escape(data.get('estimated_savings_inr'))},
        {sql_escape(jobs)},
        {sql_escape(data.get('recommendation'))}
    )
    """
    execute_sql(sql)


def update_cluster(cluster_id: str, data: dict) -> None:
    safe_id = cluster_id.replace("'", "''")
    jobs = json.dumps(data.get("jobs_running") or [])
    sql = f"""
    UPDATE {_table('cluster_metrics')} SET
        cluster_id = {sql_escape(data['cluster_id'])},
        cluster_name = {sql_escape(data.get('cluster_name'))},
        instance_type = {sql_escape(data.get('instance_type'))},
        recommended_type = {sql_escape(data.get('recommended_type'))},
        avg_cpu_usage = {sql_escape(data.get('avg_cpu_usage'))},
        avg_memory_usage = {sql_escape(data.get('avg_memory_usage'))},
        peak_cpu_usage = {sql_escape(data.get('peak_cpu_usage'))},
        peak_memory_usage = {sql_escape(data.get('peak_memory_usage'))},
        monthly_cost_inr = {sql_escape(data.get('monthly_cost_inr'))},
        estimated_savings_inr = {sql_escape(data.get('estimated_savings_inr'))},
        jobs_running = {sql_escape(jobs)},
        recommendation = {sql_escape(data.get('recommendation'))}
    WHERE cluster_id = '{safe_id}'
    """
    execute_sql(sql)


def delete_cluster(cluster_id: str) -> None:
    safe_id = cluster_id.replace("'", "''")
    execute_sql(f"DELETE FROM {_table('cluster_metrics')} WHERE cluster_id = '{safe_id}'")
