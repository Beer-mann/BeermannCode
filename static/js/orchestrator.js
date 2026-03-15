const orchestratorApi = "/api/orchestrator";
const cliOrder = ["claude", "copilot", "codex", "aider", "ollama"];

function orchestratorById(id) {
  return document.getElementById(id);
}

function formatStamp(value) {
  if (!value) return "--";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? "--" : parsed.toLocaleString();
}

function setChipState(element, active) {
  element.textContent = active ? "Online" : "Offline";
  element.style.color = active ? "var(--mint-deep)" : "var(--rose)";
}

function renderCliTiles(clis = {}) {
  let activeCount = 0;

  cliOrder.forEach((name) => {
    const active = Boolean(clis[name]);
    if (active) activeCount += 1;
    setChipState(orchestratorById(`cli-${name}`), active);
  });

  orchestratorById("activeCliCount").textContent = `${activeCount} active CLIs`;
}

function renderFallbackChain(clis = {}) {
  const chain = orchestratorById("fallbackChain");
  chain.innerHTML = cliOrder.map((name) => {
    const active = Boolean(clis[name]);
    const label = name.charAt(0).toUpperCase() + name.slice(1);
    return `<span class="fallback-pill ${active ? "fallback-pill--active" : ""}">${label}</span>`;
  }).join("");
}

function renderProjects(projects = {}, priorityProjects = []) {
  const projectEntries = Object.entries(projects).sort((left, right) => {
    const leftPriority = priorityProjects.includes(left[0]);
    const rightPriority = priorityProjects.includes(right[0]);
    if (leftPriority !== rightPriority) return leftPriority ? -1 : 1;
    return (right[1].pending_tasks || 0) - (left[1].pending_tasks || 0);
  });

  orchestratorById("projectCount").textContent = String(projectEntries.length);
  orchestratorById("pendingTaskCount").textContent = String(
    projectEntries.reduce((sum, [, info]) => sum + (info.pending_tasks || 0), 0),
  );

  const list = orchestratorById("projectList");
  if (!projectEntries.length) {
    list.innerHTML = '<div class="empty-message">No project backlog was returned.</div>';
    return;
  }

  list.innerHTML = projectEntries.map(([name, info]) => {
    const taskTypes = Object.entries(info.task_types || {});
    const tags = taskTypes.length
      ? taskTypes.map(([type, count]) => `<span class="badge-mini">${type}: ${count}</span>`).join("")
      : '<span class="badge-mini">No task types</span>';
    const priority = priorityProjects.includes(name) ? '<span class="issue-tag">Priority</span>' : "";

    return `
      <article class="project-item">
        <div class="project-item__meta">
          <h3 class="project-item__title">${name}</h3>
          <div class="tag-rail">
            ${priority}
            <span class="issue-tag">${info.pending_tasks || 0} pending</span>
          </div>
        </div>
        <div class="tag-rail">${tags}</div>
      </article>
    `;
  }).join("");
}

function renderStackList(targetId, entries, emptyLabel, entryRenderer) {
  const target = orchestratorById(targetId);
  if (!entries.length) {
    target.innerHTML = `<div class="empty-message">${emptyLabel}</div>`;
    return;
  }

  target.innerHTML = entries.map(entryRenderer).join("");
}

function renderDone(entries = []) {
  orchestratorById("recentDoneCount").textContent = String(entries.length);
  renderStackList("doneList", entries.slice().reverse().slice(0, 8), "No completed tasks were recorded.", (entry) => `
    <article class="stack-list__row">
      <div>
        <div class="stack-list__title">${entry.project || "Unknown project"}</div>
        <div class="meta-line">${entry.file || "No file"} · ${entry.type || "task"}</div>
      </div>
      <span class="badge-mini">${formatStamp(entry.ts)}</span>
    </article>
  `);
}

function renderSkips(entries = []) {
  renderStackList("skipList", entries.slice().reverse().slice(0, 8), "No recent skips were recorded.", (entry) => `
    <article class="stack-list__row">
      <div>
        <div class="stack-list__title">${entry.project || "Unknown project"}</div>
        <div class="meta-line">${entry.file || "No file"}</div>
        <div class="meta-line">${entry.reason || "No reason provided"}</div>
      </div>
      <span class="badge-mini">${formatStamp(entry.ts)}</span>
    </article>
  `);
}

function renderConfig(status) {
  orchestratorById("maxTasksValue").textContent = String(status.max_tasks_per_run || 5);
  orchestratorById("configMaxTasks").textContent = String(status.max_tasks_per_run || 5);
  orchestratorById("configAutoCommit").textContent = status.auto_commit ? "enabled" : "disabled";
  orchestratorById("configAutoPush").textContent = status.auto_push ? "enabled" : "disabled";
  orchestratorById("priorityProjects").textContent = (status.priority_projects || []).join(", ") || "None";
  orchestratorById("runPolicyChip").textContent = status.auto_commit ? "Auto commit enabled" : "Auto commit disabled";
  orchestratorById("autoPushChip").textContent = status.auto_push ? "Auto push enabled" : "Auto push disabled";
}

function renderLogs(lines = []) {
  const target = orchestratorById("logStream");
  const filtered = lines.filter((line) => line && line.trim());
  if (!filtered.length) {
    target.innerHTML = '<div class="empty-message">No recent log lines were returned.</div>';
    return;
  }

  target.innerHTML = filtered.reverse().map((line) => {
    let className = "log-line";
    if (line.includes("❌") || line.includes("Fatal") || line.includes("ERROR")) className += " log-line--error";
    else if (line.includes("✅")) className += " log-line--success";
    else if (line.includes("🚀") || line.includes("🔧") || line.includes("⏳")) className += " log-line--info";
    return `<div class="${className}">${line.replaceAll("<", "&lt;").replaceAll(">", "&gt;")}</div>`;
  }).join("");
}

async function refreshOrchestrator() {
  try {
    const [statusResponse, logsResponse] = await Promise.all([
      fetch(`${orchestratorApi}/v4/status`),
      fetch(`${orchestratorApi}/logs?limit=40`),
    ]);

    const [status, logs] = await Promise.all([
      statusResponse.json(),
      logsResponse.json(),
    ]);

    if (!statusResponse.ok) {
      throw new Error(status.error || "Unable to load orchestrator status.");
    }

    renderCliTiles(status.clis || {});
    renderFallbackChain(status.clis || {});
    renderProjects(status.projects || {}, status.priority_projects || []);
    renderDone(status.recent_done || []);
    renderSkips(status.recent_skips || []);
    renderConfig(status);
    renderLogs(logs.logs || []);

    orchestratorById("orchestratorTimestamp").textContent = formatStamp(status.timestamp);
  } catch (error) {
    orchestratorById("orchestratorTimestamp").textContent = "Unavailable";
    orchestratorById("projectList").innerHTML = `<div class="alert">${error.message}</div>`;
  }
}

orchestratorById("orchestratorRefreshBtn").addEventListener("click", refreshOrchestrator);

refreshOrchestrator();
window.setInterval(refreshOrchestrator, 15000);
