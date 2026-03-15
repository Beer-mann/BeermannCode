const studioState = {
  currentMode: "analyze",
  workflows: [],
  languages: [],
  lastOutput: "",
};

const modes = {
  analyze: {
    title: "Paste source code",
    hint: "Run analysis and reviews against code snippets.",
    inputLabel: "Code Input",
    button: "Analyze",
    endpoint: "POST /analyze",
    requestHint: "Inspect complexity, quality score, and issue hotspots.",
  },
  review: {
    title: "Paste source code",
    hint: "Inspect maintainability, safety, and review comments.",
    inputLabel: "Code Input",
    button: "Review",
    endpoint: "POST /review",
    requestHint: "Generate maintainability, safety, and style feedback.",
  },
  generate: {
    title: "Describe generated code",
    hint: "Turn a short prompt into implementation scaffolding.",
    inputLabel: "Prompt",
    button: "Generate",
    endpoint: "POST /generate",
    requestHint: "Produce starter code from a concrete engineering prompt.",
  },
};

const presets = {
  analyze: {
    python: `def sync_users(users, db, logger):\n    results = []\n    for user in users:\n        if user.get("email"):\n            try:\n                db.save(user)\n                logger.info("saved %s", user["email"])\n                results.append(user["email"])\n            except Exception:\n                pass\n    return results\n`,
    javascript: `async function syncUsers(users, api) {\n  const saved = [];\n  for (const user of users) {\n    if (!user.email) continue;\n    try {\n      await api.save(user);\n      saved.push(user.email);\n    } catch (error) {\n      console.log(error);\n    }\n  }\n  return saved;\n}\n`,
  },
  review: {
    python: `password = "secret123"\n\n\ndef run(query, payload):\n    print("Running query", query)\n    return eval(query)\n`,
    javascript: `const adminPassword = "super-secret";\n\nfunction execute(userInput) {\n  console.log("input", userInput);\n  return eval(userInput);\n}\n`,
  },
  generate: {
    default: "Create a Python function that parses a webhook payload, validates required fields, and returns a structured result with clear error handling.",
  },
};

function byId(id) {
  return document.getElementById(id);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function scoreClass(score) {
  if (score >= 70) return "score-badge score-badge--high";
  if (score >= 40) return "score-badge score-badge--mid";
  return "score-badge score-badge--low";
}

function issueClass(severity) {
  if (severity === "critical") return "item-card item-card--critical";
  if (severity === "warning") return "item-card item-card--warning";
  return "item-card item-card--info";
}

function resetOutputCopyLabel() {
  byId("copyResultBtn").textContent = "Copy output";
}

function setLastOutput(value) {
  studioState.lastOutput = value || "";
  resetOutputCopyLabel();
}

function clearResults() {
  byId("placeholder").classList.remove("is-hidden");
  document.querySelectorAll(".result-panel").forEach((panel) => panel.classList.remove("is-active"));
  byId("errorAlert").classList.add("is-hidden");
  byId("errorAlert").textContent = "";
  setLastOutput("");
}

function populateLanguageSelect(languages) {
  const select = byId("languageSelect");
  const previous = select.value;
  select.innerHTML = languages.map((language) => (
    `<option value="${language}">${language.charAt(0).toUpperCase()}${language.slice(1)}</option>`
  )).join("");
  if (languages.includes(previous)) {
    select.value = previous;
  }
}

function renderWorkflowCards(workflows) {
  byId("workflowCards").innerHTML = workflows.map((workflow) => `
    <article class="workflow-item">
      <div class="workflow-item__meta">
        <strong>${escapeHtml(workflow.label)}</strong>
        <span class="workflow-item__endpoint">${escapeHtml(workflow.endpoint)}</span>
      </div>
      <small>${escapeHtml(workflow.description)}</small>
    </article>
  `).join("");
}

function renderPresetRail() {
  const language = byId("languageSelect").value || studioState.languages[0] || "python";
  const entries = [
    {
      title: "Analysis sample",
      description: "Loads a snippet with control-flow and exception handling for static analysis.",
      action: "Load analyze preset",
      mode: "analyze",
      value: presets.analyze[language] || presets.analyze.python,
    },
    {
      title: "Review sample",
      description: "Loads a deliberately risky snippet to exercise the reviewer.",
      action: "Load review preset",
      mode: "review",
      value: presets.review[language] || presets.review.python,
    },
    {
      title: "Generation sample",
      description: "Loads a concrete generation prompt instead of a vague free-form request.",
      action: "Load generate preset",
      mode: "generate",
      value: presets.generate.default,
    },
    {
      title: "Dashboard view",
      description: "Open the orchestration dashboard to inspect runtime activity separately.",
      action: "Open dashboard",
      href: "/dashboard",
    },
  ];

  byId("presetRail").innerHTML = entries.map((entry) => `
    <article class="preset-card">
      <strong>${escapeHtml(entry.title)}</strong>
      <small>${escapeHtml(entry.description)}</small>
      ${entry.href
        ? `<a class="button button--ghost button--small" href="${entry.href}">${escapeHtml(entry.action)}</a>`
        : `<button class="button button--ghost button--small" type="button" data-preset-mode="${entry.mode}">${escapeHtml(entry.action)}</button>`}
    </article>
  `).join("");

  document.querySelectorAll("[data-preset-mode]").forEach((button) => {
    button.addEventListener("click", () => {
      applyPreset(button.dataset.presetMode);
    });
  });
}

function setMode(nextMode) {
  studioState.currentMode = nextMode;
  document.querySelectorAll("[data-mode]").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.mode === nextMode);
  });

  const config = modes[nextMode];
  byId("inputTitle").textContent = config.title;
  byId("inputHint").textContent = config.hint;
  byId("inputModeLabel").textContent = config.inputLabel;
  byId("btnText").textContent = config.button;
  byId("endpointLabel").textContent = config.endpoint;
  byId("requestHint").textContent = config.requestHint;
  byId("codeInputWrap").classList.toggle("is-hidden", nextMode === "generate");
  byId("descInputWrap").classList.toggle("is-hidden", nextMode !== "generate");
  clearResults();
}

function applyPreset(mode = studioState.currentMode) {
  const language = byId("languageSelect").value || "python";
  if (mode === "generate") {
    setMode("generate");
    byId("descInput").value = presets.generate.default;
    return;
  }

  setMode(mode);
  const source = presets[mode][language] || presets[mode].python;
  byId("codeInput").value = source;
}

function formatJson(value) {
  return JSON.stringify(value, null, 2);
}

function renderAnalyze(data) {
  byId("analyzeResult").classList.add("is-active");
  byId("qualityCircle").className = scoreClass(data.quality_score || 0);
  byId("qualityCircle").textContent = Math.round(data.quality_score || 0);
  byId("analyzeLanguage").textContent = `Language: ${data.language || "-"}`;
  byId("analyzeLOC").textContent = `Lines of code: ${data.lines_of_code || 0}`;
  byId("analyzeComplexity").textContent = `Complexity: ${data.complexity_score || 0}`;

  const issues = byId("issuesSection");
  issues.innerHTML = data.issues && data.issues.length
    ? `<div class="section-label">Issues</div>${data.issues.map((issue) => `
        <article class="${issueClass(issue.severity)}">
          <div class="item-card__meta">
            <span class="issue-tag">${escapeHtml(issue.type || "issue")}</span>
            ${issue.line ? `<span class="badge-mini">L${issue.line}</span>` : ""}
          </div>
          <div>${escapeHtml(issue.message || "")}</div>
        </article>
      `).join("")}`
    : `<div class="summary-box">No issues detected.</div>`;

  const suggestions = byId("suggestionsSection");
  suggestions.innerHTML = data.suggestions && data.suggestions.length
    ? `<div class="section-label">Suggestions</div>${data.suggestions.map((item) => `
        <article class="item-card item-card--info">
          <div>${escapeHtml(item)}</div>
        </article>
      `).join("")}`
    : "";

  const insights = byId("aiInsightsSection");
  insights.innerHTML = data.ai_insights
    ? `<div class="section-label">AI Insights</div><div class="summary-box">${escapeHtml(data.ai_insights)}</div>`
    : `<div class="summary-box">AI insights unavailable.</div>`;

  setLastOutput(formatJson(data));
}

function renderReview(data) {
  byId("reviewResult").classList.add("is-active");
  const rating = data.overall_rating || "good";
  const badge = byId("ratingBadge");
  badge.className = `pill pill--${rating}`;
  badge.textContent = rating.toUpperCase();

  const metrics = data.metrics || {};
  byId("reviewMetrics").textContent = `${metrics.total_lines || 0} lines, ${metrics.critical_issues || 0} critical, ${metrics.warnings || 0} warnings, ${metrics.info_issues || 0} info`;
  byId("reviewSummary").textContent = data.summary || "No summary returned.";

  const commentsNode = byId("reviewComments");
  commentsNode.innerHTML = data.comments && data.comments.length
    ? `<div class="section-label">Comments</div>${data.comments.slice(0, 20).map((comment) => `
        <article class="${issueClass(comment.severity)}">
          <div class="item-card__meta">
            <span class="issue-tag">${escapeHtml(comment.category || "review")}</span>
            <span class="badge-mini">${escapeHtml(comment.severity || "info")}</span>
            ${comment.line_number ? `<span class="badge-mini">L${comment.line_number}</span>` : ""}
          </div>
          <div>${escapeHtml(comment.message || "")}</div>
          ${comment.suggestion ? `<div class="meta-line">${escapeHtml(comment.suggestion)}</div>` : ""}
        </article>
      `).join("")}`
    : `<div class="summary-box">No review comments returned.</div>`;

  const reviewNode = byId("aiReviewSection");
  reviewNode.innerHTML = data.ai_review
    ? `<div class="section-label">AI Review</div><div class="summary-box">${escapeHtml(data.ai_review)}</div>`
    : `<div class="summary-box">AI review unavailable.</div>`;

  setLastOutput(formatJson(data));
}

function renderGenerate(data, language) {
  byId("generateResult").classList.add("is-active");
  const codeEl = byId("generatedCode");
  codeEl.className = `language-${language}`;
  codeEl.textContent = data.code || "";
  if (window.hljs) {
    window.hljs.highlightElement(codeEl);
  }
  setLastOutput(data.code || "");
}

async function copyText(value, button, idleLabel, doneLabel) {
  if (!value) return;
  await navigator.clipboard.writeText(value);
  button.textContent = doneLabel;
  window.setTimeout(() => {
    button.textContent = idleLabel;
  }, 1500);
}

async function submitStudio() {
  const language = byId("languageSelect").value;
  const spinner = byId("btnSpinner");
  const button = byId("runBtn");
  const errorNode = byId("errorAlert");

  button.disabled = true;
  spinner.classList.remove("is-hidden");
  errorNode.classList.add("is-hidden");

  try {
    let endpoint = "";
    let payload = {};

    if (studioState.currentMode === "analyze" || studioState.currentMode === "review") {
      const code = byId("codeInput").value.trim();
      if (!code) throw new Error(`Please enter code to ${studioState.currentMode}.`);
      endpoint = `/${studioState.currentMode}`;
      payload = { code, language };
    } else {
      const description = byId("descInput").value.trim();
      if (!description) throw new Error("Please enter a description.");
      endpoint = "/generate";
      payload = {
        description,
        language,
        include_comments: byId("includeComments").checked,
        include_tests: byId("includeTests").checked,
      };
    }

    const response = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || `Request failed (${response.status})`);
    }

    clearResults();
    byId("placeholder").classList.add("is-hidden");

    if (studioState.currentMode === "analyze") renderAnalyze(data);
    else if (studioState.currentMode === "review") renderReview(data);
    else renderGenerate(data, language);
  } catch (error) {
    errorNode.textContent = error.message;
    errorNode.classList.remove("is-hidden");
  } finally {
    spinner.classList.add("is-hidden");
    button.disabled = false;
  }
}

async function loadOverview() {
  try {
    const response = await fetch("/api/studio/overview");
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Unable to load studio overview.");

    studioState.workflows = data.workflows || [];
    studioState.languages = data.languages || [];

    byId("serviceName").textContent = data.service || "BeermannCode";
    byId("serviceStatus").textContent = data.status === "ok" ? "Operational" : "Unavailable";
    byId("languageCount").textContent = String(studioState.languages.length);
    byId("workflowCount").textContent = String(studioState.workflows.length);
    byId("runtimeHealth").textContent = data.status || "unknown";
    byId("runtimePort").textContent = String(data.port || 5004);
    byId("runtimeLanguages").textContent = studioState.languages.join(", ");
    byId("healthChip").textContent = data.status === "ok" ? "Healthy" : "Unavailable";
    byId("healthChip").classList.toggle("status-chip--offline", data.status !== "ok");

    populateLanguageSelect(studioState.languages);
    renderWorkflowCards(studioState.workflows);
    renderPresetRail();
  } catch (error) {
    byId("serviceStatus").textContent = "Overview unavailable";
    byId("runtimeHealth").textContent = "Unavailable";
    byId("healthChip").textContent = "Offline";
    byId("healthChip").classList.add("status-chip--offline");
  }
}

function clearWorkspace() {
  byId("codeInput").value = "";
  byId("descInput").value = "";
  clearResults();
}

document.querySelectorAll("[data-mode]").forEach((button) => {
  button.addEventListener("click", () => setMode(button.dataset.mode));
});

byId("languageSelect").addEventListener("change", renderPresetRail);
byId("runBtn").addEventListener("click", submitStudio);
byId("clearBtn").addEventListener("click", clearWorkspace);
byId("loadPresetBtn").addEventListener("click", () => applyPreset(studioState.currentMode === "review" ? "review" : "analyze"));
byId("loadPromptPresetBtn").addEventListener("click", () => applyPreset("generate"));
byId("copyBtn").addEventListener("click", async () => {
  await copyText(byId("generatedCode").textContent, byId("copyBtn"), "Copy code", "Copied");
});
byId("copyResultBtn").addEventListener("click", async () => {
  await copyText(studioState.lastOutput, byId("copyResultBtn"), "Copy output", "Copied");
});

setMode("analyze");
loadOverview();
