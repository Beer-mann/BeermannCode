const studioState = {
  currentMode: "analyze",
};

const modes = {
  analyze: {
    title: "Paste source code",
    hint: "Run analysis and reviews against code snippets.",
    inputLabel: "Code Input",
    button: "Analyze",
  },
  review: {
    title: "Paste source code",
    hint: "Inspect maintainability, safety, and review comments.",
    inputLabel: "Code Input",
    button: "Review",
  },
  generate: {
    title: "Describe generated code",
    hint: "Turn a short prompt into implementation scaffolding.",
    inputLabel: "Prompt",
    button: "Generate",
  },
};

function byId(id) {
  return document.getElementById(id);
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
  byId("codeInputWrap").classList.toggle("is-hidden", nextMode === "generate");
  byId("descInputWrap").classList.toggle("is-hidden", nextMode !== "generate");
  clearResults();
}

function clearResults() {
  byId("placeholder").classList.remove("is-hidden");
  document.querySelectorAll(".result-panel").forEach((panel) => panel.classList.remove("is-active"));
  byId("errorAlert").classList.add("is-hidden");
  byId("errorAlert").textContent = "";
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function issueClass(severity) {
  if (severity === "critical") return "item-card item-card--critical";
  if (severity === "warning") return "item-card item-card--warning";
  return "item-card item-card--info";
}

function scoreClass(score) {
  if (score >= 70) return "score-badge score-badge--high";
  if (score >= 40) return "score-badge score-badge--mid";
  return "score-badge score-badge--low";
}

function renderAnalyze(data) {
  byId("analyzeResult").classList.add("is-active");
  byId("qualityCircle").className = scoreClass(data.quality_score || 0);
  byId("qualityCircle").textContent = Math.round(data.quality_score || 0);
  byId("analyzeLanguage").textContent = `Language: ${data.language || "-"}`;
  byId("analyzeLOC").textContent = `Lines of code: ${data.lines_of_code || 0}`;
  byId("analyzeComplexity").textContent = `Complexity: ${data.complexity_score || 0}`;

  const issues = byId("issuesSection");
  if (data.issues && data.issues.length) {
    issues.innerHTML = `<div class="section-label">Issues</div>${data.issues.map((issue) => `
      <article class="${issueClass(issue.severity)}">
        <div class="item-card__meta">
          <span class="issue-tag">${escapeHtml(issue.type || "issue")}</span>
          ${issue.line ? `<span class="badge-mini">L${issue.line}</span>` : ""}
        </div>
        <div class="item-card__body">${escapeHtml(issue.message || "")}</div>
      </article>
    `).join("")}`;
  } else {
    issues.innerHTML = `<div class="summary-box">No issues detected.</div>`;
  }

  const suggestions = byId("suggestionsSection");
  if (data.suggestions && data.suggestions.length) {
    suggestions.innerHTML = `<div class="section-label">Suggestions</div>${data.suggestions.map((item) => `
      <article class="item-card item-card--info">
        <div class="item-card__body">${escapeHtml(item)}</div>
      </article>
    `).join("")}`;
  } else {
    suggestions.innerHTML = "";
  }

  const insights = byId("aiInsightsSection");
  insights.innerHTML = data.ai_insights
    ? `<div class="section-label">AI insights</div><div class="summary-box">${escapeHtml(data.ai_insights)}</div>`
    : `<div class="summary-box">AI insights unavailable.</div>`;
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
  if (data.comments && data.comments.length) {
    commentsNode.innerHTML = `<div class="section-label">Comments</div>${data.comments.slice(0, 20).map((comment) => `
      <article class="${issueClass(comment.severity)}">
        <div class="item-card__meta">
          <span class="issue-tag">${escapeHtml(comment.category || "review")}</span>
          <span class="badge-mini">${escapeHtml(comment.severity || "info")}</span>
          ${comment.line_number ? `<span class="badge-mini">L${comment.line_number}</span>` : ""}
        </div>
        <div class="item-card__body">${escapeHtml(comment.message || "")}</div>
        ${comment.suggestion ? `<div class="meta-line">${escapeHtml(comment.suggestion)}</div>` : ""}
      </article>
    `).join("")}`;
  } else {
    commentsNode.innerHTML = `<div class="summary-box">No review comments returned.</div>`;
  }

  const reviewNode = byId("aiReviewSection");
  reviewNode.innerHTML = data.ai_review
    ? `<div class="section-label">AI review</div><div class="summary-box">${escapeHtml(data.ai_review)}</div>`
    : `<div class="summary-box">AI review unavailable.</div>`;
}

function renderGenerate(data, language) {
  byId("generateResult").classList.add("is-active");
  const codeEl = byId("generatedCode");
  codeEl.className = `language-${language}`;
  codeEl.textContent = data.code || "";
  if (window.hljs) {
    window.hljs.highlightElement(codeEl);
  }
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

document.querySelectorAll("[data-mode]").forEach((button) => {
  button.addEventListener("click", () => setMode(button.dataset.mode));
});

byId("runBtn").addEventListener("click", submitStudio);

byId("copyBtn").addEventListener("click", async () => {
  const code = byId("generatedCode").textContent;
  await navigator.clipboard.writeText(code);
  const button = byId("copyBtn");
  button.textContent = "Copied";
  window.setTimeout(() => {
    button.textContent = "Copy";
  }, 1500);
});

setMode("analyze");
