const API = "";

let currentTab = "pipelines";
let editContext = null;

const PIPELINE_FIELDS = [
  { name: "pipeline_name", label: "Pipeline Name", required: true },
  { name: "status", label: "Status", type: "select", options: ["success", "failed", "running", "partial_failure", "unknown"], required: true },
  { name: "run_time", label: "Run Time", placeholder: "2026-07-08T03:00:00Z" },
  { name: "duration_minutes", label: "Duration (minutes)", type: "number" },
  { name: "error_message", label: "Error Message", type: "textarea" },
  { name: "cluster_id", label: "Cluster ID" },
  { name: "cpu_usage", label: "CPU Usage (%)", type: "number" },
  { name: "memory_usage", label: "Memory Usage (%)", type: "number" },
  { name: "dependencies", label: "Dependencies (comma-separated)", placeholder: "api_gateway, raw_storage" },
  { name: "last_success", label: "Last Success", placeholder: "2026-07-07T02:10:00Z" },
];

const FAILURE_FIELDS = [
  { name: "pipeline_name", label: "Pipeline Name", required: true },
  { name: "failure_time", label: "Failure Time", placeholder: "2026-07-08T01:30:00Z" },
  { name: "root_cause", label: "Root Cause" },
  { name: "error_details", label: "Error Details", type: "textarea" },
  { name: "cluster_logs", label: "Cluster Logs", type: "textarea" },
  { name: "dependency_status", label: "Dependency Status (JSON)", placeholder: '{"api_gateway": "down"}' },
  { name: "suggested_actions", label: "Suggested Actions (one per line)" },
];

const CLUSTER_FIELDS = [
  { name: "cluster_id", label: "Cluster ID", required: true },
  { name: "cluster_name", label: "Cluster Name" },
  { name: "instance_type", label: "Instance Type" },
  { name: "recommended_type", label: "Recommended Type" },
  { name: "avg_cpu_usage", label: "Avg CPU (%)", type: "number" },
  { name: "avg_memory_usage", label: "Avg Memory (%)", type: "number" },
  { name: "peak_cpu_usage", label: "Peak CPU (%)", type: "number" },
  { name: "peak_memory_usage", label: "Peak Memory (%)", type: "number" },
  { name: "monthly_cost_inr", label: "Monthly Cost (₹)", type: "number" },
  { name: "estimated_savings_inr", label: "Est. Savings (₹)", type: "number" },
  { name: "jobs_running", label: "Jobs Running (comma-separated)" },
  { name: "recommendation", label: "Recommendation", type: "textarea" },
];

function showToast(message, type = "success") {
  const el = document.getElementById("toast");
  el.textContent = message;
  el.className = `toast ${type}`;
  setTimeout(() => el.classList.add("hidden"), 3000);
}

async function api(path, options = {}) {
  const res = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
  return data;
}

function statusClass(status) {
  if (!status) return "unknown";
  const s = status.toLowerCase();
  if (s === "success") return "success";
  if (s === "failed" || s === "partial_failure") return "failed";
  if (s === "running") return "running";
  return "unknown";
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}

function parseListField(value) {
  if (!value || !value.trim()) return [];
  return value.split(",").map((s) => s.trim()).filter(Boolean);
}

function parseJsonField(value, fallback) {
  if (!value || !value.trim()) return fallback;
  try { return JSON.parse(value); } catch { return fallback; }
}

function serializeRow(fields, row) {
  const out = {};
  for (const f of fields) {
    let val = row[f.name];
    if (f.name === "dependencies" || f.name === "jobs_running") {
      out[f.name] = Array.isArray(val) ? val : parseListField(val);
    } else if (f.name === "dependency_status") {
      out[f.name] = typeof val === "object" ? val : parseJsonField(val, {});
    } else if (f.name === "suggested_actions") {
      if (Array.isArray(val)) out[f.name] = val;
      else if (typeof val === "string" && val.includes("\n")) out[f.name] = val.split("\n").map((s) => s.trim()).filter(Boolean);
      else out[f.name] = parseListField(val);
    } else if (f.type === "number" && val !== "" && val != null) {
      out[f.name] = Number(val);
    } else {
      out[f.name] = val || null;
    }
  }
  return out;
}

function displayValue(val) {
  if (val == null || val === "") return "—";
  if (Array.isArray(val)) return val.join(", ");
  if (typeof val === "object") return JSON.stringify(val);
  return String(val);
}

async function checkDbStatus() {
  const badge = document.getElementById("db-status");
  try {
    const status = await api("/databricks/status");
    if (status.connected) {
      badge.textContent = `✓ ${status.catalog}.${status.schema}`;
      badge.className = "status-badge connected";
    } else {
      badge.textContent = `✗ ${status.message}`;
      badge.className = "status-badge error";
    }
  } catch {
    badge.textContent = "✗ Cannot reach API";
    badge.className = "status-badge error";
  }
}

function renderPipelinesTable(pipelines) {
  const wrap = document.getElementById("pipelines-table");
  if (!pipelines.length) {
    wrap.innerHTML = '<div class="empty-state">No pipeline runs yet. Click "+ Add Pipeline" to create one.</div>';
    return;
  }
  wrap.innerHTML = `
    <table>
      <thead>
        <tr>
          <th>Pipeline</th><th>Status</th><th>Run Time</th><th>Duration</th><th>Cluster</th><th>Actions</th>
        </tr>
      </thead>
      <tbody>
        ${pipelines.map((p) => `
          <tr>
            <td><strong>${escapeHtml(p.pipeline_name)}</strong></td>
            <td><span class="status-pill ${statusClass(p.status)}">${escapeHtml(p.status)}</span></td>
            <td>${escapeHtml(displayValue(p.run_time))}</td>
            <td>${p.duration_minutes != null ? p.duration_minutes + " min" : "—"}</td>
            <td>${escapeHtml(displayValue(p.cluster_id))}</td>
            <td class="actions">
              <button class="btn sm" data-edit-pipeline="${escapeHtml(p.pipeline_name)}">Edit</button>
              <button class="btn sm danger" data-delete-pipeline="${escapeHtml(p.pipeline_name)}">Delete</button>
            </td>
          </tr>
        `).join("")}
      </tbody>
    </table>`;
}

function renderFailuresTable(failures) {
  const wrap = document.getElementById("failures-table");
  if (!failures.length) {
    wrap.innerHTML = '<div class="empty-state">No failure logs yet.</div>';
    return;
  }
  wrap.innerHTML = `
    <table>
      <thead>
        <tr>
          <th>Pipeline</th><th>Failure Time</th><th>Root Cause</th><th>Actions</th>
        </tr>
      </thead>
      <tbody>
        ${failures.map((f) => `
          <tr>
            <td><strong>${escapeHtml(f.pipeline_name)}</strong></td>
            <td>${escapeHtml(displayValue(f.failure_time))}</td>
            <td>${escapeHtml(displayValue(f.root_cause))}</td>
            <td class="actions">
              <button class="btn sm" data-edit-failure='${JSON.stringify({ name: f.pipeline_name, time: f.failure_time })}'>Edit</button>
              <button class="btn sm danger" data-delete-failure='${JSON.stringify({ name: f.pipeline_name, time: f.failure_time })}'>Delete</button>
            </td>
          </tr>
        `).join("")}
      </tbody>
    </table>`;
}

function renderClustersTable(clusters) {
  const wrap = document.getElementById("clusters-table");
  if (!clusters.length) {
    wrap.innerHTML = '<div class="empty-state">No cluster metrics yet.</div>';
    return;
  }
  wrap.innerHTML = `
    <table>
      <thead>
        <tr>
          <th>Cluster</th><th>Instance</th><th>Avg CPU</th><th>Cost (₹)</th><th>Savings (₹)</th><th>Actions</th>
        </tr>
      </thead>
      <tbody>
        ${clusters.map((c) => `
          <tr>
            <td><strong>${escapeHtml(c.cluster_name || c.cluster_id)}</strong></td>
            <td>${escapeHtml(displayValue(c.instance_type))}</td>
            <td>${c.avg_cpu_usage != null ? c.avg_cpu_usage + "%" : "—"}</td>
            <td>${c.monthly_cost_inr != null ? "₹" + c.monthly_cost_inr : "—"}</td>
            <td>${c.estimated_savings_inr != null ? "₹" + c.estimated_savings_inr : "—"}</td>
            <td class="actions">
              <button class="btn sm" data-edit-cluster="${escapeHtml(c.cluster_id)}">Edit</button>
              <button class="btn sm danger" data-delete-cluster="${escapeHtml(c.cluster_id)}">Delete</button>
            </td>
          </tr>
        `).join("")}
      </tbody>
    </table>`;
}

async function loadData() {
  try {
    const [pipelines, failures, clusters] = await Promise.all([
      api("/pipelines"),
      api("/failures"),
      api("/clusters"),
    ]);
    renderPipelinesTable(pipelines.pipelines);
    renderFailuresTable(failures.failures);
    renderClustersTable(clusters.clusters);
  } catch (err) {
    showToast(err.message, "error");
  }
}

function buildForm(fields, data = {}) {
  const form = document.getElementById("modal-form");
  form.innerHTML = fields.map((f) => {
    let value = data[f.name];
    if (f.name === "dependencies" || f.name === "jobs_running") {
      value = Array.isArray(value) ? value.join(", ") : (value || "");
    } else if (f.name === "dependency_status") {
      value = typeof value === "object" && value ? JSON.stringify(value) : (value || "");
    } else if (f.name === "suggested_actions") {
      value = Array.isArray(value) ? value.join("\n") : (value || "");
    } else {
      value = value ?? "";
    }

    if (f.type === "select") {
      return `<div class="form-group">
        <label>${f.label}${f.required ? " *" : ""}</label>
        <select name="${f.name}" ${f.required ? "required" : ""}>
          ${f.options.map((o) => `<option value="${o}" ${value === o ? "selected" : ""}>${o}</option>`).join("")}
        </select>
      </div>`;
    }
    if (f.type === "textarea") {
      return `<div class="form-group">
        <label>${f.label}${f.required ? " *" : ""}</label>
        <textarea name="${f.name}" ${f.required ? "required" : ""} placeholder="${f.placeholder || ""}">${escapeHtml(String(value))}</textarea>
      </div>`;
    }
    return `<div class="form-group">
      <label>${f.label}${f.required ? " *" : ""}</label>
      <input name="${f.name}" type="${f.type || "text"}" value="${escapeHtml(String(value))}"
        ${f.required ? "required" : ""} placeholder="${f.placeholder || ""}" />
    </div>`;
  }).join("");
}

function openModal(title, fields, data, context) {
  editContext = context;
  document.getElementById("modal-title").textContent = title;
  buildForm(fields, data);
  document.getElementById("modal").classList.remove("hidden");
}

function closeModal() {
  document.getElementById("modal").classList.add("hidden");
  editContext = null;
}

function getFormData(fields) {
  const form = document.getElementById("modal-form");
  const raw = {};
  for (const f of fields) {
    const el = form.elements[f.name];
    raw[f.name] = el ? el.value : "";
  }
  return serializeRow(fields, raw);
}

async function handleFormSubmit(e) {
  e.preventDefault();
  if (!editContext) return;

  const { type, mode, key } = editContext;
  const fieldMap = { pipelines: PIPELINE_FIELDS, failures: FAILURE_FIELDS, clusters: CLUSTER_FIELDS };
  const fields = fieldMap[type];
  const body = getFormData(fields);

  try {
    if (type === "pipelines") {
      if (mode === "create") await api("/pipelines", { method: "POST", body: JSON.stringify(body) });
      else await api(`/pipelines/${encodeURIComponent(key)}`, { method: "PUT", body: JSON.stringify(body) });
    } else if (type === "failures") {
      if (mode === "create") await api("/failures", { method: "POST", body: JSON.stringify(body) });
      else await api(`/failures/${encodeURIComponent(key.name)}?failure_time=${encodeURIComponent(key.time)}`, { method: "PUT", body: JSON.stringify(body) });
    } else if (type === "clusters") {
      if (mode === "create") await api("/clusters", { method: "POST", body: JSON.stringify(body) });
      else await api(`/clusters/${encodeURIComponent(key)}`, { method: "PUT", body: JSON.stringify(body) });
    }
    closeModal();
    showToast(mode === "create" ? "Record created — refresh DataOps Copilot to see changes" : "Record updated");
    await loadData();
  } catch (err) {
    showToast(err.message, "error");
  }
}

function setupTabs() {
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      currentTab = tab.dataset.tab;
      document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t === tab));
      document.querySelectorAll(".panel").forEach((p) => p.classList.toggle("active", p.id === `panel-${currentTab}`));
    });
  });
}

function setupButtons() {
  document.getElementById("btn-add-pipeline").addEventListener("click", () => {
    openModal("Add Pipeline Run", PIPELINE_FIELDS, {}, { type: "pipelines", mode: "create" });
  });
  document.getElementById("btn-add-failure").addEventListener("click", () => {
    openModal("Add Failure Log", FAILURE_FIELDS, {}, { type: "failures", mode: "create" });
  });
  document.getElementById("btn-add-cluster").addEventListener("click", () => {
    openModal("Add Cluster Metrics", CLUSTER_FIELDS, {}, { type: "clusters", mode: "create" });
  });

  document.getElementById("modal-close").addEventListener("click", closeModal);
  document.getElementById("modal-cancel").addEventListener("click", closeModal);
  document.getElementById("modal-form").addEventListener("submit", handleFormSubmit);

  document.body.addEventListener("click", async (e) => {
    const editPipeline = e.target.dataset.editPipeline;
    const deletePipeline = e.target.dataset.deletePipeline;
    const editFailure = e.target.dataset.editFailure;
    const deleteFailure = e.target.dataset.deleteFailure;
    const editCluster = e.target.dataset.editCluster;
    const deleteCluster = e.target.dataset.deleteCluster;

    if (editPipeline) {
      const data = (await api("/pipelines")).pipelines.find((p) => p.pipeline_name === editPipeline);
      openModal("Edit Pipeline Run", PIPELINE_FIELDS, data, { type: "pipelines", mode: "edit", key: editPipeline });
    }
    if (deletePipeline && confirm(`Delete pipeline "${deletePipeline}"?`)) {
      try {
        await api(`/pipelines/${encodeURIComponent(deletePipeline)}`, { method: "DELETE" });
        showToast("Pipeline deleted");
        await loadData();
      } catch (err) { showToast(err.message, "error"); }
    }
    if (editFailure) {
      const key = JSON.parse(editFailure);
      const data = (await api("/failures")).failures.find((f) => f.pipeline_name === key.name && f.failure_time === key.time);
      openModal("Edit Failure Log", FAILURE_FIELDS, data, { type: "failures", mode: "edit", key });
    }
    if (deleteFailure) {
      const key = JSON.parse(deleteFailure);
      if (confirm(`Delete failure log for "${key.name}"?`)) {
        try {
          await api(`/failures/${encodeURIComponent(key.name)}?failure_time=${encodeURIComponent(key.time)}`, { method: "DELETE" });
          showToast("Failure log deleted");
          await loadData();
        } catch (err) { showToast(err.message, "error"); }
      }
    }
    if (editCluster) {
      const data = (await api("/clusters")).clusters.find((c) => c.cluster_id === editCluster);
      openModal("Edit Cluster Metrics", CLUSTER_FIELDS, data, { type: "clusters", mode: "edit", key: editCluster });
    }
    if (deleteCluster && confirm(`Delete cluster "${deleteCluster}"?`)) {
      try {
        await api(`/clusters/${encodeURIComponent(deleteCluster)}`, { method: "DELETE" });
        showToast("Cluster deleted");
        await loadData();
      } catch (err) { showToast(err.message, "error"); }
    }
  });
}

document.addEventListener("DOMContentLoaded", async () => {
  setupTabs();
  setupButtons();
  await checkDbStatus();
  await loadData();
});
