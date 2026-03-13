const dashboardApi = "/api/orchestrator";

function dashboardById(id) {
  return document.getElementById(id);
}

function formatTime(value) {
  if (!value) return "--";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? "--" : parsed.toLocaleString();
}

function applyStatusText(element, text, tone) {
  element.textContent = text;
  element.style.color = tone === "ok" ? "var(--accent)" : tone === "warn" ? "var(--warm)" : tone === "error" ? "var(--danger)" : "var(--text)";
}

function updateClock() {
  dashboardById("current-time").textContent = new Date().toLocaleTimeString();
}

function updateStatusCard(status) {
  const cycle = status.last_cycle || {};
  const tasks = status.tasks || {};
  const agentsRun = cycle.agents_run || {};
  const agentCount = Object.keys(agentsRun).length;
  const successCount = Object.values(agentsRun).filter((agent) => agent && agent.success).length;
  const successRate = agentCount ? Math.round((successCount / agentCount) * 100) : 0;
  const totalTasks = (tasks.pending || 0) + (tasks.completed || 0) + (tasks.failed || 0) + (tasks.in_progress || 0);
  const pendingWidth = totalTasks ? Math.round(((tasks.pending || 0) / totalTasks) * 100) : 0;
  const agentWidth = agentCount ? Math.round((successCount / agentCount) * 100) : 0;

  dashboardById("last-cycle-time").textContent = formatTime(status.last_run);
  dashboardById("cycle-duration").textContent = cycle.cycle_duration ? `${cycle.cycle_duration.toFixed(2)}s` : "--";
  dashboardById("agents-count").textContent = String(agentCount);
  dashboardById("agents-progress").style.width = `${agentWidth}%`;
  dashboardById("success-rate").textContent = `${successRate}%`;
  dashboardById("total-runs").textContent = String(agentCount);
  dashboardById("pending-tasks").textContent = String(tasks.pending || 0);
  dashboardById("completed-tasks").textContent = String(tasks.completed || 0);
  dashboardById("failed-tasks").textContent = String(tasks.failed || 0);
  dashboardById("tasks-progress").style.width = `${pendingWidth}%`;
  dashboardById("today-completed").textContent = String(tasks.completed || 0);
  dashboardById("error-status").textContent = (tasks.failed || 0) > 0 ? `${tasks.failed} failed` : "None";
}

function updateLogs(logs) {
  const container = dashboardById("logs-container");
  const lines = (logs.logs || []).filter((line) => line.trim());

  if (!lines.length) {
    container.innerHTML = '<div class="empty-message">No recent logs.</div>';
    return;
  }

  container.innerHTML = lines.reverse().map((line) => {
    let className = "log-line";
    if (line.includes("ERROR") || line.includes("FAILED")) className += " log-line--error";
    else if (line.includes("WARN") || line.includes("⚠")) className += " log-line--warning";
    else if (line.includes("SUCCESS") || line.includes("✅")) className += " log-line--success";
    return `<div class="${className}">${line.replaceAll("<", "&lt;").replaceAll(">", "&gt;")}</div>`;
  }).join("");
}

function updateTasks(data) {
  const container = dashboardById("tasks-container");
  const tasks = data.tasks || [];

  if (!tasks.length) {
    container.innerHTML = '<div class="empty-message">No recent tasks.</div>';
    return;
  }

  container.innerHTML = tasks.slice(-10).reverse().map((task) => {
    const status = task.status || "pending";
    const toneClass = status === "failed" ? "item-card--critical" : status === "pending" ? "item-card--warning" : "item-card--info";
    const stamp = formatTime(task.timestamp || task.ts);
    return `
      <article class="item-card ${toneClass}">
        <div class="item-card__meta">
          <span class="issue-tag">${status}</span>
          <span class="badge-mini">${stamp}</span>
        </div>
        <div class="item-card__body">${task.project || "Unknown project"}</div>
        <div class="meta-line">${task.type || "task"} -> ${task.file || task.detail || "no details"}</div>
      </article>
    `;
  }).join("");
}

function updateOllama(data) {
  const target = dashboardById("ollama-status");
  if (data.status === "online") {
    applyStatusText(target, `Online (${data.models_count || 0} models)`, "ok");
  } else {
    applyStatusText(target, "Offline", "error");
  }
}

function updateAgents(data) {
  const agents = data.agents || {};
  const container = dashboardById("agents-container");
  const entries = Object.entries(agents);

  container.innerHTML = entries.length ? entries.map(([name, agent]) => {
    const tone = agent.status === "installed" ? "ok" : agent.status === "extension_missing" ? "warn" : "error";
    const statusText = agent.status === "installed" ? "Installed" : agent.status === "extension_missing" ? "Extension missing" : "Unavailable";
    return `
      <article class="item-card item-card--info">
        <div class="item-card__meta">
          <span class="issue-tag">${name.replaceAll("_", " ")}</span>
          <span class="badge-mini">${statusText}</span>
        </div>
        <div class="meta-line">${agent.version || "Version unknown"}</div>
        <div class="meta-line">${agent.path || ""}</div>
      </article>
    `;
  }).join("") : '<div class="empty-message">No agent data available.</div>';

  const serviceMap = [
    ["aider", "aider-status", "aider-version"],
    ["codex", "codex-status", "codex-version"],
    ["claude", "claude-status", "claude-version"],
    ["github_copilot", "gh-status", "gh-version"],
  ];

  serviceMap.forEach(([key, statusId, versionId]) => {
    const agent = agents[key] || {};
    const tone = agent.status === "installed" ? "ok" : agent.status === "extension_missing" ? "warn" : "error";
    const statusText = agent.status === "installed" ? "Installed" : agent.status === "extension_missing" ? "Extension missing" : "Unavailable";
    applyStatusText(dashboardById(statusId), statusText, tone);
    dashboardById(versionId).textContent = agent.version || "--";
  });
}

async function refreshDashboard() {
  try {
    const [statusRes, logsRes, tasksRes, ollamaRes, agentsRes] = await Promise.all([
      fetch(`${dashboardApi}/status`),
      fetch(`${dashboardApi}/logs?limit=20`),
      fetch(`${dashboardApi}/tasks`),
      fetch(`${dashboardApi}/ollama`),
      fetch(`${dashboardApi}/agents`),
    ]);

    const [status, logs, tasks, ollama, agents] = await Promise.all([
      statusRes.json(),
      logsRes.json(),
      tasksRes.json(),
      ollamaRes.json(),
      agentsRes.json(),
    ]);

    updateStatusCard(status);
    updateLogs(logs);
    updateTasks(tasks);
    updateOllama(ollama);
    updateAgents(agents);
  } catch (error) {
    console.error("Dashboard refresh failed", error);
  }
}

dashboardById("refreshBtn").addEventListener("click", refreshDashboard);

updateClock();
refreshDashboard();
window.setInterval(updateClock, 1000);
window.setInterval(refreshDashboard, 5000);
