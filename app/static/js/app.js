// BugFlow Single-Page Application Client Logic

let authToken = "";
let currentUser = null;
let currentProjectId = null;
let categoriesList = [];
let developersList = [];
let currentIssueInModal = null;
let duplicateTimeout = null;
let filterTimeout = null;

// --- INITIALIZATION ---
document.addEventListener("DOMContentLoaded", () => {
  // Keep login screen visible and dashboard hidden initially until authentication
  const loginScreen = document.getElementById("login-screen");
  const appDashboard = document.getElementById("app-dashboard");
  if (loginScreen) loginScreen.classList.remove("hidden");
  if (appDashboard) appDashboard.classList.add("hidden");
});

// --- AUTHENTICATION & LOGIN FLOW ---
async function handleLogin(event) {
  if (event) event.preventDefault();

  const errorEl = document.getElementById("login-error");
  const errorTextEl = document.getElementById("login-error-text");
  const submitBtn = document.getElementById("login-submit-btn");
  const spinnerEl = document.getElementById("login-spinner");
  const btnTextEl = document.getElementById("login-btn-text");
  const usernameInput = document.getElementById("login-username");
  const passwordInput = document.getElementById("login-password");

  if (errorEl) errorEl.classList.add("hidden");

  const username = usernameInput ? usernameInput.value.trim() : "";
  const password = passwordInput ? passwordInput.value : "";

  if (!username || !password) {
    if (errorTextEl) errorTextEl.textContent = "Please enter both username/email and password.";
    if (errorEl) errorEl.classList.remove("hidden");
    return;
  }

  // Set loading state
  if (submitBtn) submitBtn.disabled = true;
  if (spinnerEl) spinnerEl.classList.remove("hidden");
  if (btnTextEl) btnTextEl.textContent = "Signing In...";

  try {
    const res = await fetch("/api/v1/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });

    const data = await res.json().catch(() => ({}));

    if (!res.ok) {
      const errorMsg = data.detail || "Authentication failed. Please verify your credentials.";
      if (errorTextEl) errorTextEl.textContent = errorMsg;
      if (errorEl) errorEl.classList.remove("hidden");
      return;
    }

    // Auth succeeded: store state
    authToken = data.access_token;
    currentUser = data.user;

    // Update user display in top header
    updateUserHeaderDisplay();

    // Clear password input for security
    if (passwordInput) passwordInput.value = "";

    // Switch view to dashboard
    const loginScreen = document.getElementById("login-screen");
    const appDashboard = document.getElementById("app-dashboard");
    if (loginScreen) loginScreen.classList.add("hidden");
    if (appDashboard) appDashboard.classList.remove("hidden");

    showAlert(
      `Welcome back, <strong>${currentUser.full_name || currentUser.username}</strong>! (${currentUser.role})`,
      "success"
    );

    // Initialize & refresh dashboard data
    await loadInitialDropdowns();
    await fetchIssues();

    // Refresh active tab views if already selected
    const activeTab = document.querySelector(".tab-content:not(.hidden)");
    if (activeTab) {
      const activeTabId = activeTab.id;
      if (activeTabId === "tab-m2") {
        fetchSprints();
        fetchBacklog();
        fetchActivityStream();
        fetchReleases();
      } else if (activeTabId === "tab-m3") {
        fetchQualityMetrics();
        renderPlotlyCharts();
      } else if (activeTabId === "tab-m4") {
        fetchQualityMetrics();
        fetchWorkloadMatrix();
      }
    }
  } catch (err) {
    console.error("Login error:", err);
    if (errorTextEl) errorTextEl.textContent = "Unable to connect to the authentication server. Please try again.";
    if (errorEl) errorEl.classList.remove("hidden");
  } finally {
    if (submitBtn) submitBtn.disabled = false;
    if (spinnerEl) spinnerEl.classList.add("hidden");
    if (btnTextEl) btnTextEl.textContent = "Sign In";
  }
}

function togglePasswordVisibility() {
  const passwordInput = document.getElementById("login-password");
  const icon = document.getElementById("toggle-password-icon");
  if (!passwordInput || !icon) return;

  if (passwordInput.type === "password") {
    passwordInput.type = "text";
    icon.classList.remove("fa-eye");
    icon.classList.add("fa-eye-slash");
  } else {
    passwordInput.type = "password";
    icon.classList.remove("fa-eye-slash");
    icon.classList.add("fa-eye");
  }
}

function fillCredentials(username, password) {
  const usernameInput = document.getElementById("login-username");
  const passwordInput = document.getElementById("login-password");
  if (usernameInput) usernameInput.value = username;
  if (passwordInput) passwordInput.value = password;
  const errorEl = document.getElementById("login-error");
  if (errorEl) errorEl.classList.add("hidden");
}

function updateUserHeaderDisplay() {
  if (!currentUser) return;
  const nameEl = document.getElementById("user-display-name");
  const roleEl = document.getElementById("user-display-role");
  const initialsEl = document.getElementById("user-avatar-initials");

  const displayName = currentUser.full_name || currentUser.username || "User";
  if (nameEl) nameEl.textContent = displayName;
  if (roleEl) roleEl.textContent = currentUser.role || "User";

  if (initialsEl) {
    const parts = displayName.trim().split(" ");
    let initials = "";
    if (parts.length >= 2 && parts[0] && parts[1]) {
      initials = (parts[0][0] + parts[1][0]).toUpperCase();
    } else if (parts[0] && parts[0].length >= 1) {
      initials = parts[0].substring(0, 2).toUpperCase();
    }
    initialsEl.textContent = initials || "U";
  }
}

function handleLogout() {
  // Clear in-memory auth state
  authToken = "";
  currentUser = null;

  // Reset login form and inputs
  const loginForm = document.getElementById("login-form");
  if (loginForm) loginForm.reset();

  const passwordInput = document.getElementById("login-password");
  const icon = document.getElementById("toggle-password-icon");
  if (passwordInput) passwordInput.type = "password";
  if (icon) {
    icon.classList.remove("fa-eye-slash");
    icon.classList.add("fa-eye");
  }

  const errorEl = document.getElementById("login-error");
  if (errorEl) errorEl.classList.add("hidden");

  // Close any open modals
  const modalIds = [
    "issue-detail-modal",
    "ai-core-modal",
    "sprint-modal",
    "release-modal",
    "merge-issues-modal",
    "escalate-issue-modal",
    "approve-issue-modal",
    "portals-modal",
  ];
  modalIds.forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.classList.add("hidden");
  });

  // Switch view back to login screen
  const appDashboard = document.getElementById("app-dashboard");
  const loginScreen = document.getElementById("login-screen");
  if (appDashboard) appDashboard.classList.add("hidden");
  if (loginScreen) loginScreen.classList.remove("hidden");

  const usernameInput = document.getElementById("login-username");
  if (usernameInput) usernameInput.focus();
}

function getAuthHeaders() {
  return {
    "Content-Type": "application/json",
    Authorization: `Bearer ${authToken}`,
  };
}

// --- TAB SWITCHING ---
function switchTab(tabId) {
  document.querySelectorAll(".tab-content").forEach((el) => el.classList.add("hidden"));
  document.getElementById(tabId).classList.remove("hidden");

  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.className =
      "tab-btn px-3.5 py-1.5 rounded-lg flex items-center space-x-2 text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 whitespace-nowrap transition";
  });

  const activeBtn = document.getElementById("nav-" + tabId);
  if (activeBtn) {
    activeBtn.className =
      "tab-btn active-tab px-3.5 py-1.5 rounded-lg flex items-center space-x-2 text-indigo-400 bg-indigo-500/10 border border-indigo-500/30 whitespace-nowrap";
  }

  // Load relevant data on tab activate
  if (tabId === "tab-m1") {
    fetchIssues();
  } else if (tabId === "tab-m2") {
    fetchSprints();
    fetchBacklog();
    fetchActivityStream();
    fetchReleases();
  } else if (tabId === "tab-m3") {
    fetchQualityMetrics();
    renderPlotlyCharts();
  } else if (tabId === "tab-m4") {
    fetchQualityMetrics();
    fetchWorkloadMatrix();
  }
}

// --- ALERT NOTIFICATIONS ---
function showAlert(message, type = "info") {
  const alertEl = document.getElementById("global-alert");
  const inner = document.getElementById("global-alert-inner");

  const colors = {
    success: "bg-emerald-950/80 border-emerald-500/30 text-emerald-300",
    error: "bg-rose-950/80 border-rose-500/30 text-rose-300",
    info: "bg-indigo-950/80 border-indigo-500/30 text-indigo-300",
    warning: "bg-amber-950/80 border-amber-500/30 text-amber-300",
  };

  inner.className = `p-3 rounded-xl border flex items-center justify-between text-xs shadow-lg ${colors[type] || colors.info}`;
  inner.innerHTML = `
    <div class="flex items-center space-x-2">
      <i class="fa-solid fa-circle-info text-sm"></i>
      <span>${message}</span>
    </div>
    <button onclick="document.getElementById('global-alert').classList.add('hidden')" class="text-slate-400 hover:text-white ml-4">
      <i class="fa-solid fa-xmark"></i>
    </button>
  `;
  alertEl.classList.remove("hidden");
  setTimeout(() => alertEl.classList.add("hidden"), 6000);
}

// --- INITIAL DROPDOWNS ---
async function loadInitialDropdowns() {
  try {
    // 1. Projects
    const projRes = await fetch("/api/v1/projects/", { headers: getAuthHeaders() });
    if (projRes.ok) {
      const projects = await projRes.json();
      const projSelect = document.getElementById("form-project");
      projSelect.innerHTML = "";
      projects.forEach((p) => {
        projSelect.innerHTML += `<option value="${p.project_id}">${p.project_name}</option>`;
      });
      if (projects.length > 0) currentProjectId = projects[0].project_id;
    }

    // 2. Bug Categories
    const catRes = await fetch("/api/v1/projects/categories", { headers: getAuthHeaders() });
    if (catRes.ok) {
      categoriesList = await catRes.json();
      const catSelect = document.getElementById("form-category");
      catSelect.innerHTML = "";
      categoriesList.forEach((c) => {
        catSelect.innerHTML += `<option value="${c.category_id}" data-urgency="${c.urgency}">${c.category_name} (${c.urgency})</option>`;
      });
    }

    // 3. Developers
    const devRes = await fetch("/api/v1/analytics/developer-workload", { headers: getAuthHeaders() });
    if (devRes.ok) {
      developersList = await devRes.json();
      const assignSelect = document.getElementById("form-assignee");
      assignSelect.innerHTML = `<option value="">-- Leave Unassigned --</option>`;
      developersList.forEach((d) => {
        assignSelect.innerHTML += `<option value="${d.user_id}">${d.full_name} (${d.team})</option>`;
      });
    }

    // 4. Releases (Module 4)
    const relRes = await fetch("/api/v1/releases/", { headers: getAuthHeaders() });
    if (relRes.ok) {
      const releases = await relRes.json();
      const relSelect = document.getElementById("form-release");
      if (relSelect) {
        relSelect.innerHTML = `<option value="">-- No Release --</option>`;
        releases.forEach((r) => {
          relSelect.innerHTML += `<option value="${r.release_id}">${r.version_name} (${r.status})</option>`;
        });
      }
    }

    updatePriorityScorePreview();
  } catch (e) {
    console.error("Failed to load initial dropdowns:", e);
  }
}

// --- MILESTONE 1: SMART PRIORITY PREVIEW ---
function updatePriorityScorePreview() {
  const sev = document.getElementById("form-severity").value;
  const catSelect = document.getElementById("form-category");
  const selectedOpt = catSelect.options[catSelect.selectedIndex];
  const urg = selectedOpt ? selectedOpt.getAttribute("data-urgency") : "Medium Urgency";

  const sevWeights = { CRITICAL: 4, MAJOR: 3, MINOR: 2, TRIVIAL: 1 };
  const urgWeights = { "High Urgency": 3, "Medium Urgency": 2, "Low Urgency": 1 };

  const sWeight = sevWeights[sev] || 2;
  const uWeight = urgWeights[urg] || 2;
  const score = sWeight * uWeight;

  let priority = "LOW";
  let badgeClass = "bg-blue-500/20 text-blue-300 border-blue-500/30";

  if (score >= 10) {
    priority = "URGENT";
    badgeClass = "bg-red-500/20 text-red-300 border-red-500/30 animate-pulse";
  } else if (score >= 7) {
    priority = "HIGH";
    badgeClass = "bg-orange-500/20 text-orange-300 border-orange-500/30";
  } else if (score >= 4) {
    priority = "MEDIUM";
    badgeClass = "bg-yellow-500/20 text-yellow-300 border-yellow-500/30";
  }

  document.getElementById("preview-priority-formula").textContent = `Severity (${sWeight}) \u00d7 Urgency (${uWeight})`;
  document.getElementById("preview-priority-score").textContent = score.toFixed(1);

  const badge = document.getElementById("preview-priority-badge");
  badge.className = `ml-2 px-2 py-0.5 text-[10px] font-bold rounded border ${badgeClass}`;
  badge.textContent = priority;
}

// --- MILESTONE 1: DUPLICATE DETECTION ---
function debounceDuplicateCheck() {
  clearTimeout(duplicateTimeout);
  const title = document.getElementById("form-title").value.trim();
  const badge = document.getElementById("dup-status-badge");
  const box = document.getElementById("duplicate-warning-box");

  if (title.length < 5) {
    badge.textContent = "";
    box.classList.add("hidden");
    return;
  }

  badge.textContent = "Scanning for duplicates...";
  duplicateTimeout = setTimeout(async () => {
    try {
      const projId = document.getElementById("form-project").value || 1;
      const res = await fetch("/api/v1/issues/check-duplicates", {
        method: "POST",
        headers: getAuthHeaders(),
        body: JSON.stringify({ project_id: parseInt(projId), title }),
      });

      if (!res.ok) return;
      const data = await res.json();

      if (data.is_duplicate && data.matches.length > 0) {
        badge.textContent = `\u26a0 ${data.matches.length} potential duplicate(s) found!`;
        badge.className = "text-[10px] text-amber-400 font-bold";
        box.classList.remove("hidden");

        const list = document.getElementById("duplicate-matches-list");
        list.innerHTML = data.matches
          .map(
            (m) => `
          <div class="flex items-center justify-between py-1 border-b border-amber-500/20 last:border-0">
            <span class="truncate pr-2">B-${m.id.toString().padStart(3, "0")}: ${m.title}</span>
            <span class="font-bold text-amber-300 whitespace-nowrap">${m.similarity_score}% match</span>
          </div>
        `
          )
          .join("");
      } else {
        badge.textContent = "\u2714 Title is unique";
        badge.className = "text-[10px] text-emerald-400";
        box.classList.add("hidden");
      }
    } catch (e) {
      console.error("Duplicate check error:", e);
    }
  }, 400);
}

// --- MILESTONE 1 & 2: SMART DEVELOPER MATCHER ---
async function triggerSmartDeveloperMatch() {
  const title = document.getElementById("form-title").value.trim();
  const description = document.getElementById("form-description").value.trim();
  const severity = document.getElementById("form-severity").value;
  const category_id = parseInt(document.getElementById("form-category").value);
  const affected_modules = document.getElementById("form-modules").value.trim();

  if (!title) {
    showAlert("Please enter an issue title first", "warning");
    return;
  }

  const previewBox = document.getElementById("smart-match-preview");
  previewBox.classList.remove("hidden");
  previewBox.innerHTML = `<span class="text-indigo-300"><i class="fa-solid fa-spinner fa-spin mr-1"></i> Analyzing text skills & developer workloads...</span>`;

  try {
    const res = await fetch("/api/v1/issues/triage-recommendation", {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({
        title,
        description,
        severity,
        category_id,
        affected_modules,
      }),
    });

    if (!res.ok) {
      previewBox.innerHTML = `<span class="text-red-400">Failed to calculate recommendation</span>`;
      return;
    }

    const data = await res.json();
    let devsHtml = data.recommended_developers
      .map(
        (dev, idx) => `
      <div class="flex items-center justify-between p-2 rounded bg-slate-900 border border-slate-800">
        <div>
          <span class="font-bold text-slate-200">#${idx + 1} ${dev.full_name}</span>
          <span class="text-[10px] text-indigo-400 block">${dev.rationale}</span>
        </div>
        <div class="flex items-center space-x-2">
          <span class="px-2 py-0.5 rounded font-bold text-xs bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">${dev.match_percentage}% Match</span>
          <button type="button" onclick="selectRecommendedDev(${dev.user_id})" class="px-2 py-1 bg-indigo-600 hover:bg-indigo-500 text-white rounded text-[10px]">Select</button>
        </div>
      </div>
    `
      )
      .join("");

    previewBox.innerHTML = `
      <div class="font-bold text-indigo-300 mb-1.5 flex items-center justify-between">
        <span><i class="fa-solid fa-brain mr-1"></i> Recommended Assignees:</span>
        <span>Priority: ${data.priority} (${data.priority_score})</span>
      </div>
      <div class="space-y-1.5">${devsHtml}</div>
    `;
  } catch (err) {
    previewBox.innerHTML = `<span class="text-red-400">Error: ${err.message}</span>`;
  }
}

function selectRecommendedDev(devId) {
  document.getElementById("form-assignee").value = devId;
  showAlert("Developer assigned from Smart Match!", "success");
}

// --- MILESTONE 1: CREATE ISSUE ---
async function handleCreateIssue(e) {
  e.preventDefault();

  const payload = {
    project_id: parseInt(document.getElementById("form-project").value),
    category_id: parseInt(document.getElementById("form-category").value),
    title: document.getElementById("form-title").value.trim(),
    description: document.getElementById("form-description").value.trim(),
    reproduction_steps: document.getElementById("form-steps").value.trim(),
    severity: document.getElementById("form-severity").value,
    affected_modules: document.getElementById("form-modules").value.trim(),
    environment_details: document.getElementById("form-environment").value.trim(),
    dev_stage: document.getElementById("form-stage").value,
    issue_type: document.getElementById("form-type") ? document.getElementById("form-type").value : "BUG",
    tags: document.getElementById("form-tags") ? document.getElementById("form-tags").value.trim() : "",
    code_references: document.getElementById("form-code-ref") ? document.getElementById("form-code-ref").value.trim() : "",
    release_id: document.getElementById("form-release") && document.getElementById("form-release").value
      ? parseInt(document.getElementById("form-release").value)
      : null,
    assignee_id: document.getElementById("form-assignee").value
      ? parseInt(document.getElementById("form-assignee").value)
      : null,
    estimated_effort: 2.0,
  };

  try {
    const res = await fetch("/api/v1/issues/", {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const err = await res.json();
      showAlert(err.detail || "Failed to create issue", "error");
      return;
    }

    const created = await res.json();
    showAlert(`Issue <strong>B-${created.id.toString().padStart(3, "0")}</strong> created successfully!`, "success");

    // Reset Form
    document.getElementById("form-title").value = "";
    document.getElementById("form-description").value = "";
    document.getElementById("form-steps").value = "";
    document.getElementById("form-modules").value = "";
    document.getElementById("form-environment").value = "";
    document.getElementById("duplicate-warning-box").classList.add("hidden");
    document.getElementById("smart-match-preview").classList.add("hidden");

    fetchIssues();
  } catch (err) {
    showAlert("Error submitting issue: " + err.message, "error");
  }
}

// --- ISSUE LIST & FILTERING ---
function debounceFilterIssues() {
  clearTimeout(filterTimeout);
  filterTimeout = setTimeout(fetchIssues, 300);
}

async function fetchIssues() {
  try {
    const search = document.getElementById("filter-search").value.trim();
    const status = document.getElementById("filter-status").value;
    const severity = document.getElementById("filter-severity").value;

    let url = `/api/v1/issues/?`;
    if (search) url += `search=${encodeURIComponent(search)}&`;
    if (status) url += `status=${encodeURIComponent(status)}&`;
    if (severity) url += `severity=${encodeURIComponent(severity)}&`;

    const res = await fetch(url, { headers: getAuthHeaders() });
    if (!res.ok) return;

    const issues = await res.json();
    renderIssuesList(issues);
  } catch (err) {
    console.error("Fetch issues error:", err);
  }
}

function renderIssuesList(issues) {
  const container = document.getElementById("issues-list-container");
  const countBadge = document.getElementById("issue-count-badge");
  countBadge.textContent = `${issues.length} bugs`;

  if (issues.length === 0) {
    container.innerHTML = `
      <div class="text-center py-12 text-slate-500 text-xs">
        <i class="fa-solid fa-inbox text-3xl mb-2 block"></i>
        No matching defects found. Try clearing filters or submit a new bug ticket.
      </div>
    `;
    return;
  }

  const sevColors = {
    CRITICAL: "bg-red-500/20 text-red-300 border-red-500/30",
    MAJOR: "bg-orange-500/20 text-orange-300 border-orange-500/30",
    MINOR: "bg-yellow-500/20 text-yellow-300 border-yellow-500/30",
    TRIVIAL: "bg-blue-500/20 text-blue-300 border-blue-500/30",
  };

  const statusColors = {
    REPORTED: "bg-slate-800 text-slate-300 border-slate-700",
    TRIAGED: "bg-purple-900/30 text-purple-300 border-purple-800/40",
    IN_PROGRESS: "bg-blue-900/30 text-blue-300 border-blue-800/40",
    CODE_REVIEW: "bg-pink-900/30 text-pink-300 border-pink-800/40",
    QA_VERIFICATION: "bg-amber-900/30 text-amber-300 border-amber-800/40",
    RESOLVED: "bg-emerald-900/30 text-emerald-300 border-emerald-800/40",
    CLOSED: "bg-slate-800 text-slate-400 border-slate-700",
  };

  container.innerHTML = issues
    .map(
      (i) => `
    <div class="p-3 bg-slate-950/60 hover:bg-slate-800/50 border border-slate-800/80 rounded-xl transition cursor-pointer flex flex-wrap sm:flex-nowrap items-center justify-between gap-3" onclick="openIssueModal(${i.id})">
      <div class="flex items-start space-x-3 min-w-0 flex-1">
        <span class="font-mono font-bold text-xs px-2 py-0.5 rounded bg-indigo-600/20 text-indigo-400 border border-indigo-500/30 whitespace-nowrap">
          B-${i.id.toString().padStart(3, "0")}
        </span>
        <div class="min-w-0">
          <h4 class="font-bold text-slate-200 text-xs truncate hover:text-indigo-400 transition">${i.title}</h4>
          <div class="flex flex-wrap items-center gap-2 mt-1 text-[11px] text-slate-400">
            <span><i class="fa-solid fa-layer-group text-slate-500 mr-1"></i>${i.category ? i.category.category_name : "General"}</span>
            <span>&bull;</span>
            <span><i class="fa-solid fa-user text-slate-500 mr-1"></i>${i.assignee ? i.assignee.full_name : "Unassigned"}</span>
            ${i.dev_stage ? `<span>&bull;</span><span>${i.dev_stage}</span>` : ""}
          </div>
        </div>
      </div>

      <div class="flex items-center space-x-2 text-[11px] font-semibold">
        <span class="px-2 py-0.5 rounded border ${sevColors[i.severity] || sevColors.MINOR}">${i.severity}</span>
        <span class="px-2 py-0.5 rounded border ${statusColors[i.status] || statusColors.REPORTED}">${i.status}</span>
        <i class="fa-solid fa-chevron-right text-slate-600 text-xs"></i>
      </div>
    </div>
  `
    )
    .join("");
}

// --- ISSUE DETAIL & LIFECYCLE MODAL ---
async function openIssueModal(id) {
  try {
    const res = await fetch(`/api/v1/issues/${id}`, { headers: getAuthHeaders() });
    if (!res.ok) return;

    const issue = await res.json();
    currentIssueInModal = issue;

    document.getElementById("modal-issue-id").textContent = `B-${issue.id.toString().padStart(3, "0")}`;
    document.getElementById("modal-issue-title").textContent = issue.title;
    document.getElementById("modal-status-badge").textContent = issue.status;
    document.getElementById("modal-severity-badge").textContent = issue.severity;
    document.getElementById("modal-priority-badge").textContent = `${issue.priority} (${issue.priority_score})`;
    document.getElementById("modal-assignee-text").textContent = `Assignee: ${issue.assignee ? issue.assignee.full_name : "Unassigned"}`;
    document.getElementById("modal-issue-desc").textContent = issue.description;
    document.getElementById("modal-issue-steps").textContent = issue.reproduction_steps || "No reproduction steps provided.";

    const typeEl = document.getElementById("modal-type-badge");
    if (typeEl) typeEl.textContent = issue.issue_type || "BUG";

    const tagsEl = document.getElementById("modal-tags-badge");
    if (tagsEl) tagsEl.innerHTML = `<i class="fa-solid fa-tags mr-1"></i>Tags: ${issue.tags || "None"}`;

    const coderefEl = document.getElementById("modal-coderef-badge");
    if (coderefEl) coderefEl.innerHTML = `<i class="fa-solid fa-code mr-1"></i>Ref: ${issue.code_references || "None"}`;

    const relEl = document.getElementById("modal-release-badge");
    if (relEl) relEl.innerHTML = `<i class="fa-solid fa-flag-checkered mr-1"></i>Release: ${issue.release ? issue.release.version_name : "Unscheduled"}`;

    const approveBtn = document.getElementById("modal-approve-btn");
    if (approveBtn) {
      if (["CODE_REVIEW", "QA_VERIFICATION"].includes(issue.status)) {
        approveBtn.classList.remove("hidden");
      } else {
        approveBtn.classList.add("hidden");
      }
    }

    // Render Valid Next Transitions Buttons
    renderStateTransitions(issue);

    // Render Comments
    renderComments(issue.comments || []);

    // Render Attachments
    renderAttachments(issue.attachments || []);

    // Render Audit Trail
    renderAuditLogs(issue.audit_logs || []);

    document.getElementById("issue-detail-modal").classList.remove("hidden");
  } catch (err) {
    showAlert("Failed to load issue details", "error");
  }
}

function closeIssueModal() {
  document.getElementById("issue-detail-modal").classList.add("hidden");
  currentIssueInModal = null;
}

const VALID_TRANSITIONS = {
  REPORTED: ["TRIAGED"],
  TRIAGED: ["IN_PROGRESS"],
  IN_PROGRESS: ["CODE_REVIEW"],
  CODE_REVIEW: ["QA_VERIFICATION", "IN_PROGRESS"],
  QA_VERIFICATION: ["RESOLVED", "IN_PROGRESS"],
  RESOLVED: ["CLOSED", "IN_PROGRESS"],
  CLOSED: ["IN_PROGRESS"],
};

function renderStateTransitions(issue) {
  const container = document.getElementById("modal-transitions-container");
  const nextStates = VALID_TRANSITIONS[issue.status.toUpperCase()] || [];

  if (nextStates.length === 0) {
    container.innerHTML = `<span class="text-[11px] text-slate-500">Terminal State</span>`;
    return;
  }

  container.innerHTML = nextStates
    .map(
      (st) => `
    <button onclick="handleTransitionStatus('${st}')" class="px-2.5 py-1 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded text-xs transition flex items-center space-x-1">
      <span>Advance to ${st}</span>
      <i class="fa-solid fa-arrow-right text-[10px]"></i>
    </button>
  `
    )
    .join("");
}

async function handleTransitionStatus(newStatus) {
  if (!currentIssueInModal) return;

  try {
    const res = await fetch(`/api/v1/issues/${currentIssueInModal.id}/status`, {
      method: "PATCH",
      headers: getAuthHeaders(),
      body: JSON.stringify({ status: newStatus }),
    });

    if (!res.ok) {
      const err = await res.json();
      showAlert(err.detail || "Transition failed", "error");
      return;
    }

    showAlert(`Issue status successfully moved to <strong>${newStatus}</strong>!`, "success");
    await openIssueModal(currentIssueInModal.id);
    fetchIssues();
    if (!document.getElementById("tab-m2").classList.contains("hidden")) {
      fetchSprints();
      fetchActivityStream();
    }
  } catch (err) {
    showAlert("Transition error: " + err.message, "error");
  }
}

// --- COMMENTS & COLLABORATION ---
function renderComments(comments) {
  const container = document.getElementById("modal-comments-list");
  if (comments.length === 0) {
    container.innerHTML = `<span class="text-slate-500 text-[11px]">No comments posted yet. Start the discussion below.</span>`;
    return;
  }

  container.innerHTML = comments
    .map(
      (c) => `
    <div class="p-2.5 bg-slate-950 rounded-lg border border-slate-800 text-xs">
      <div class="flex items-center justify-between text-[10px] text-slate-400 mb-1">
        <span class="font-bold text-indigo-300">${c.user ? c.user.full_name : "User"}</span>
        <span>${new Date(c.created_at).toLocaleString()}</span>
      </div>
      <p class="text-slate-200">${c.content}</p>
    </div>
  `
    )
    .join("");
}

async function handlePostComment(e) {
  e.preventDefault();
  if (!currentIssueInModal) return;

  const input = document.getElementById("modal-comment-input");
  const content = input.value.trim();
  if (!content) return;

  try {
    const res = await fetch(`/api/v1/collaboration/issues/${currentIssueInModal.id}/comments`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({ content }),
    });

    if (!res.ok) {
      showAlert("Failed to post comment", "error");
      return;
    }

    input.value = "";
    const commRes = await fetch(`/api/v1/collaboration/issues/${currentIssueInModal.id}/comments`, {
      headers: getAuthHeaders(),
    });
    const updated = await commRes.json();
    renderComments(updated);
    showAlert("Comment posted", "success");
  } catch (err) {
    showAlert("Comment error: " + err.message, "error");
  }
}

// --- ATTACHMENTS ---
function renderAttachments(attachments) {
  const container = document.getElementById("modal-attachments-list");
  if (attachments.length === 0) {
    container.innerHTML = `<span class="text-slate-500 text-[11px]">No attachments uploaded.</span>`;
    return;
  }

  container.innerHTML = attachments
    .map(
      (a) => `
    <div class="flex items-center justify-between p-2 bg-slate-950 rounded border border-slate-800 text-[11px]">
      <div class="flex items-center space-x-2 truncate">
        <i class="fa-solid fa-file-code text-indigo-400"></i>
        <span class="text-slate-200 truncate">${a.filename}</span>
        <span class="text-slate-500">(${Math.round(a.file_size / 1024)} KB)</span>
      </div>
      <a href="/api/v1/collaboration/attachments/${a.id}/download" target="_blank" class="text-indigo-400 hover:text-indigo-300 font-semibold px-2 py-0.5 rounded bg-slate-800">
        <i class="fa-solid fa-download mr-1"></i> Download
      </a>
    </div>
  `
    )
    .join("");
}

async function handleUploadAttachment(e) {
  e.preventDefault();
  if (!currentIssueInModal) return;

  const fileInput = document.getElementById("modal-file-input");
  if (!fileInput.files || fileInput.files.length === 0) return;

  const formData = new FormData();
  formData.append("file", fileInput.files[0]);

  try {
    const res = await fetch(`/api/v1/collaboration/issues/${currentIssueInModal.id}/attachments`, {
      method: "POST",
      headers: { Authorization: `Bearer ${authToken}` },
      body: formData,
    });

    if (!res.ok) {
      const err = await res.json();
      showAlert(err.detail || "Upload failed", "error");
      return;
    }

    fileInput.value = "";
    showAlert("Attachment uploaded successfully!", "success");
    await openIssueModal(currentIssueInModal.id);
  } catch (err) {
    showAlert("Upload error: " + err.message, "error");
  }
}

// --- AUDIT TRAIL ---
function renderAuditLogs(logs) {
  const tbody = document.getElementById("modal-audit-tbody");
  if (logs.length === 0) {
    tbody.innerHTML = `<tr><td colspan="5" class="text-center py-2 text-slate-500">No audit records found</td></tr>`;
    return;
  }

  tbody.innerHTML = logs
    .map(
      (l) => `
    <tr class="hover:bg-slate-800/40">
      <td class="px-2 py-1.5 text-slate-500">${new Date(l.timestamp).toLocaleTimeString()}</td>
      <td class="px-2 py-1.5 font-bold text-indigo-400">${l.action}</td>
      <td class="px-2 py-1.5 text-slate-300">${l.field_name}</td>
      <td class="px-2 py-1.5 text-slate-400 font-mono">${l.old_value || "\u2014"}</td>
      <td class="px-2 py-1.5 text-emerald-400 font-mono font-bold">${l.new_value || "\u2014"}</td>
    </tr>
  `
    )
    .join("");
}

// --- MILESTONE 2: SPRINTS & BACKLOG ---
async function fetchSprints() {
  try {
    const res = await fetch("/api/v1/sprints/", { headers: getAuthHeaders() });
    if (!res.ok) return;

    const sprints = await res.json();
    const container = document.getElementById("sprints-container");
    document.getElementById("active-sprint-badge").textContent = `${sprints.length} sprints`;

    if (sprints.length === 0) {
      container.innerHTML = `<span class="text-slate-500 text-xs">No active sprints. Click "Create New Sprint" above.</span>`;
      return;
    }

    container.innerHTML = sprints
      .map((s) => {
        const total = s.issue_count || 0;
        const resolved = s.resolved_count || 0;
        const progress = total > 0 ? Math.round((resolved / total) * 100) : 0;

        return `
        <div class="p-3 bg-slate-900 rounded-xl border border-slate-800 space-y-2.5">
          <div class="flex items-center justify-between">
            <div>
              <h4 class="font-bold text-slate-200 text-xs">${s.sprint_name}</h4>
              <span class="text-[10px] text-slate-400">${s.goal || "Agile cycle"}</span>
            </div>
            <span class="px-2 py-0.5 rounded text-[10px] font-bold ${
              s.status === "ACTIVE"
                ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                : s.status === "COMPLETED"
                ? "bg-blue-500/20 text-blue-300 border border-blue-500/30"
                : "bg-slate-800 text-slate-400"
            }">${s.status}</span>
          </div>

          <!-- Progress Bar -->
          <div>
            <div class="flex items-center justify-between text-[10px] text-slate-400 mb-1">
              <span>Progress: ${resolved} / ${total} resolved</span>
              <span class="font-bold text-indigo-400">${progress}%</span>
            </div>
            <div class="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
              <div class="bg-indigo-500 h-full transition-all duration-500" style="width: ${progress}%"></div>
            </div>
          </div>

          ${
            s.status === "ACTIVE"
              ? `
            <div class="pt-1 flex justify-end">
              <button onclick="completeSprint(${s.sprint_id})" class="text-[10px] bg-slate-800 hover:bg-slate-700 text-slate-300 px-2 py-1 rounded border border-slate-700">
                Mark Completed (Track Velocity)
              </button>
            </div>
          `
              : ""
          }
        </div>
      `;
      })
      .join("");
  } catch (err) {
    console.error("Fetch sprints error:", err);
  }
}

async function fetchBacklog() {
  try {
    const res = await fetch("/api/v1/sprints/backlog", { headers: getAuthHeaders() });
    if (!res.ok) return;

    const backlog = await res.json();
    const container = document.getElementById("backlog-container");
    document.getElementById("backlog-count-badge").textContent = `${backlog.length} bugs waiting`;

    if (backlog.length === 0) {
      container.innerHTML = `<div class="text-center py-8 text-slate-500 text-xs">Backlog is empty! All bugs assigned to sprints.</div>`;
      return;
    }

    // Fetch active sprints for the "+ Add to Sprint" dropdown
    const spRes = await fetch("/api/v1/sprints/", { headers: getAuthHeaders() });
    const sprints = spRes.ok ? await spRes.json() : [];
    const activeSprints = sprints.filter((s) => s.status !== "COMPLETED");

    container.innerHTML = backlog
      .map(
        (b) => `
      <div class="p-2.5 bg-slate-900 rounded-xl border border-slate-800 flex items-center justify-between gap-2">
        <div class="min-w-0 flex-1">
          <div class="flex items-center space-x-1.5">
            <span class="font-mono text-[10px] text-indigo-400">B-${b.id.toString().padStart(3, "0")}</span>
            <span class="text-xs font-bold text-slate-200 truncate block">${b.title}</span>
          </div>
          <span class="text-[10px] text-slate-400">${b.severity} &bull; ${b.category ? b.category.category_name : "Bug"}</span>
        </div>

        <div>
          ${
            activeSprints.length > 0
              ? `
            <select onchange="addBugToSprint(${b.id}, this.value)" class="bg-slate-800 text-[10px] text-indigo-300 font-semibold rounded px-2 py-1 border border-slate-700 focus:outline-none">
              <option value="">+ Add to Sprint</option>
              ${activeSprints.map((s) => `<option value="${s.sprint_id}">${s.sprint_name}</option>`).join("")}
            </select>
          `
              : `<span class="text-[10px] text-slate-500">No Active Sprint</span>`
          }
        </div>
      </div>
    `
      )
      .join("");
  } catch (err) {
    console.error("Fetch backlog error:", err);
  }
}

async function addBugToSprint(issueId, sprintId) {
  if (!sprintId) return;
  try {
    const res = await fetch(`/api/v1/sprints/${sprintId}/add-issue/${issueId}`, {
      method: "POST",
      headers: getAuthHeaders(),
    });

    if (!res.ok) {
      showAlert("Failed to assign bug to sprint", "error");
      return;
    }

    showAlert(`Moved Bug B-${issueId.toString().padStart(3, "0")} into Sprint!`, "success");
    fetchSprints();
    fetchBacklog();
    fetchActivityStream();
  } catch (err) {
    showAlert("Error: " + err.message, "error");
  }
}

async function completeSprint(sprintId) {
  try {
    const res = await fetch(`/api/v1/sprints/${sprintId}/status?new_status=COMPLETED`, {
      method: "PATCH",
      headers: getAuthHeaders(),
    });

    if (!res.ok) {
      showAlert("Failed to complete sprint", "error");
      return;
    }

    const s = await res.json();
    showAlert(`Sprint Completed! Calculated Velocity: <strong>${s.velocity}</strong> fixes.`, "success");
    fetchSprints();
  } catch (err) {
    showAlert("Error: " + err.message, "error");
  }
}

function openCreateSprintModal() {
  document.getElementById("create-sprint-modal").classList.remove("hidden");
}

function closeCreateSprintModal() {
  document.getElementById("create-sprint-modal").classList.add("hidden");
}

async function handleCreateSprint(e) {
  e.preventDefault();
  const name = document.getElementById("sprint-name-input").value.trim();
  const goal = document.getElementById("sprint-goal-input").value.trim();
  const projId = currentProjectId || 1;

  try {
    const res = await fetch("/api/v1/sprints/", {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({
        project_id: projId,
        sprint_name: name,
        goal: goal,
        status: "ACTIVE",
      }),
    });

    if (!res.ok) {
      showAlert("Failed to create sprint", "error");
      return;
    }

    showAlert("New Agile Sprint created!", "success");
    closeCreateSprintModal();
    fetchSprints();
  } catch (err) {
    showAlert("Error: " + err.message, "error");
  }
}

async function fetchActivityStream() {
  try {
    const res = await fetch("/api/v1/collaboration/activity-stream?limit=25", {
      headers: getAuthHeaders(),
    });
    if (!res.ok) return;

    const stream = await res.json();
    const container = document.getElementById("activity-stream-list");
    if (!container) return;

    if (stream.length === 0) {
      container.innerHTML = `<span class="text-slate-500 text-xs">No activity yet.</span>`;
      return;
    }

    container.innerHTML = stream
      .map(
        (a) => `
      <div class="p-2.5 bg-slate-950 rounded-lg border border-slate-800 text-xs space-y-1">
        <div class="flex items-center justify-between text-[10px] text-slate-500">
          <span class="font-bold text-indigo-400">B-${a.issue_id.toString().padStart(3, "0")}</span>
          <span>${new Date(a.timestamp).toLocaleTimeString()}</span>
        </div>
        <p class="text-slate-300 font-medium">
          <span class="text-indigo-300">${a.user ? a.user.full_name : "CI/CD System"}</span>: 
          ${a.action} (${a.field_name} \u2192 <span class="text-emerald-400 font-bold">${a.new_value}</span>)
        </p>
      </div>
    `
      )
      .join("");
  } catch (err) {
    console.error("Activity stream error:", err);
  }
}

// --- MILESTONE 3: CI/CD GIT WEBHOOK SIMULATOR ---
async function simulateGitWebhook() {
  const commit_message = document.getElementById("webhook-commit-msg").value.trim();
  const commit_sha = document.getElementById("webhook-commit-sha").value.trim();
  const branch = document.getElementById("webhook-commit-branch").value.trim();

  const outBox = document.getElementById("webhook-output-box");
  outBox.classList.remove("hidden");
  outBox.innerHTML = `Running Git webhook ingestion for ${commit_sha}...`;

  try {
    const res = await fetch("/api/v1/webhooks/git", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ commit_message, commit_sha, branch }),
    });

    const data = await res.json();
    outBox.innerHTML = `
      <div class="text-emerald-400 font-bold">\u2714 Webhook 200 OK</div>
      <div>Matched Issues: [${data.matched_issues.join(", ")}]</div>
      <div>Result: ${data.message}</div>
      <div class="text-slate-400 text-[10px] mt-1">Status changed automatically to QA_VERIFICATION!</div>
    `;

    showAlert(`CI/CD Webhook processed: ${data.message}`, "success");
    fetchIssues();
    renderPlotlyCharts();
  } catch (err) {
    outBox.innerHTML = `<div class="text-red-400">Webhook error: ${err.message}</div>`;
  }
}

function setSampleWebhookCommit(text) {
  document.getElementById("webhook-commit-msg").value = text;
  simulateGitWebhook();
}

// --- MILESTONE 3: REST API EXPLORER ---
async function executeApiExplorerRequest() {
  const endpoint = document.getElementById("api-explorer-endpoint").value;
  const statusEl = document.getElementById("api-explorer-status");
  const outputEl = document.getElementById("api-explorer-output");

  statusEl.textContent = "Sending...";
  statusEl.className = "font-bold text-amber-400";
  outputEl.textContent = "Waiting for response...";

  try {
    const res = await fetch(endpoint, { headers: getAuthHeaders() });
    const json = await res.json();

    statusEl.textContent = `HTTP ${res.status} ${res.statusText || "OK"}`;
    statusEl.className = res.ok ? "font-bold text-emerald-400" : "font-bold text-rose-400";

    outputEl.textContent = JSON.stringify(json, null, 2);
  } catch (err) {
    statusEl.textContent = "Network Error";
    statusEl.className = "font-bold text-rose-400";
    outputEl.textContent = err.message;
  }
}

// --- MILESTONE 3: PLOTLY CHARTS ---
async function renderPlotlyCharts() {
  try {
    const res = await fetch("/api/v1/analytics/plotly-charts", { headers: getAuthHeaders() });
    if (!res.ok) return;

    const charts = await res.json();

    // 1. Defect Trend
    if (document.getElementById("chart-defect-trends") && charts.defect_trend) {
      Plotly.newPlot("chart-defect-trends", charts.defect_trend.data, charts.defect_trend.layout, {
        responsive: true,
        displayModeBar: false,
      });
    }

    // 2. Severity Donut
    if (document.getElementById("chart-severity-donut") && charts.severity_donut) {
      Plotly.newPlot("chart-severity-donut", charts.severity_donut.data, charts.severity_donut.layout, {
        responsive: true,
        displayModeBar: false,
      });
    }

    // 3. Workflow Pipeline Bar
    if (document.getElementById("chart-workflow-bar") && charts.workflow_pipeline) {
      Plotly.newPlot("chart-workflow-bar", charts.workflow_pipeline.data, charts.workflow_pipeline.layout, {
        responsive: true,
        displayModeBar: false,
      });
    }
  } catch (err) {
    console.error("Plotly render error:", err);
  }
}

// --- MILESTONE 4: QUALITY SCORECARD & WORKLOAD MATRIX ---
async function fetchQualityMetrics() {
  try {
    const res = await fetch("/api/v1/analytics/quality-metrics", { headers: getAuthHeaders() });
    if (!res.ok) return;

    const m = await res.json();
    document.getElementById("kpi-fix-rate").textContent = `${m.fix_rate_percentage}%`;
    document.getElementById("kpi-mttr").textContent = `${m.mean_time_to_resolution_hours} hrs`;
    document.getElementById("kpi-health-score").textContent = `${m.backlog_health_score} / 100`;
    document.getElementById("kpi-leakage-rate").textContent = `${m.defect_leakage_rate_percentage}%`;
  } catch (err) {
    console.error("Metrics fetch error:", err);
  }
}

async function fetchWorkloadMatrix() {
  try {
    const res = await fetch("/api/v1/analytics/developer-workload", { headers: getAuthHeaders() });
    if (!res.ok) return;

    const devs = await res.json();
    const tbody = document.getElementById("developer-workload-tbody");

    tbody.innerHTML = devs
      .map((d) => {
        let balanceBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">Balanced</span>`;
        if (d.active_tasks >= 4) {
          balanceBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-red-500/20 text-red-300 border border-red-500/30">Overloaded</span>`;
        } else if (d.active_tasks === 0) {
          balanceBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-500/20 text-blue-300 border border-blue-500/30">Available</span>`;
        }

        return `
        <tr class="hover:bg-slate-800/40">
          <td class="px-4 py-3 flex items-center space-x-2">
            <div class="w-7 h-7 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center font-bold text-indigo-400 text-xs">
              ${d.full_name.charAt(0)}
            </div>
            <div>
              <span class="font-bold text-slate-200 block">${d.full_name}</span>
              <span class="text-[10px] text-slate-500">@${d.username}</span>
            </div>
          </td>
          <td class="px-4 py-3 text-slate-300">${d.team}</td>
          <td class="px-4 py-3">
            <span class="font-bold font-mono ${d.active_tasks > 3 ? "text-amber-400" : "text-slate-200"}">${d.active_tasks}</span> active
          </td>
          <td class="px-4 py-3">
            <span class="font-bold font-mono text-emerald-400">${d.completed_fixes}</span> fixes
          </td>
          <td class="px-4 py-3 text-slate-400">
            ${d.average_mttr_hours > 0 ? `${d.average_mttr_hours} hrs` : "\u2014"}
          </td>
          <td class="px-4 py-3">${balanceBadge}</td>
        </tr>
      `;
      })
      .join("");
  } catch (err) {
    console.error("Workload matrix error:", err);
  }
}

// --- EXPORTS & DOCUMENTATION ---
function exportCSV() {
  window.open("/api/v1/export/csv", "_blank");
}

function exportPDF() {
  window.open("/api/v1/export/pdf", "_blank");
}

function publishAllDocumentation() {
  showAlert(
    "All documentation published! Accessible at <a href='/docs' target='_blank' class='underline font-bold text-white'>/docs (Swagger)</a>, <a href='/redoc' target='_blank' class='underline font-bold text-white'>/redoc</a>, and project README.md.",
    "info"
  );
}

// =========================================================================
// MODULE 4: RELEASES & READINESS DASHBOARD
// =========================================================================
async function fetchReleases() {
  const container = document.getElementById("releases-container");
  if (!container) return;

  try {
    const res = await fetch("/api/v1/releases/", { headers: getAuthHeaders() });
    if (!res.ok) return;

    const releases = await res.json();
    if (releases.length === 0) {
      container.innerHTML = `<div class="col-span-2 text-center py-6 text-slate-500 text-xs">No active releases scheduled.</div>`;
      return;
    }

    const cards = await Promise.all(
      releases.map(async (r) => {
        let readiness = { readiness_status: "RELEASE_READY", readiness_percentage: 100, open_blockers_count: 0 };
        try {
          const readRes = await fetch(`/api/v1/releases/${r.release_id}/readiness`, { headers: getAuthHeaders() });
          if (readRes.ok) readiness = await readRes.json();
        } catch (_) {}

        const statusBadges = {
          RELEASE_READY: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30",
          AT_RISK: "bg-amber-500/20 text-amber-300 border-amber-500/30",
          BLOCKED: "bg-rose-500/20 text-rose-300 border-rose-500/30",
        };

        const targetDate = r.release_date ? new Date(r.release_date).toLocaleDateString() : "TBD";

        return `
          <div class="p-4 bg-slate-950 rounded-xl border border-slate-800 space-y-3">
            <div class="flex items-center justify-between">
              <div>
                <h3 class="font-bold text-slate-200 text-sm flex items-center space-x-2">
                  <i class="fa-solid fa-box text-indigo-400"></i>
                  <span>${r.version_name}</span>
                </h3>
                <span class="text-[10px] text-slate-500">${r.release_notes || "Scheduled milestone"}</span>
              </div>
              <span class="px-2 py-0.5 rounded font-bold text-[10px] border ${statusBadges[readiness.readiness_status] || statusBadges.RELEASE_READY}">
                ${readiness.readiness_status.replace("_", " ")}
              </span>
            </div>

            <!-- Progress Bar -->
            <div class="space-y-1">
              <div class="flex items-center justify-between text-[11px] text-slate-400">
                <span>Completion: ${r.resolved_issues || 0} / ${r.total_issues || 0} bugs resolved</span>
                <span class="font-bold text-slate-200">${readiness.readiness_percentage}%</span>
              </div>
              <div class="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                <div class="bg-gradient-to-r from-indigo-500 to-emerald-400 h-2 rounded-full transition-all duration-500" style="width: ${readiness.readiness_percentage}%"></div>
              </div>
            </div>

            <div class="flex items-center justify-between pt-1 border-t border-slate-800/80 text-[11px] text-slate-400">
              <span><i class="fa-regular fa-calendar mr-1"></i> Target: ${targetDate}</span>
              <span class="font-semibold ${readiness.open_blockers_count > 0 ? "text-rose-400" : "text-emerald-400"}">
                <i class="fa-solid fa-triangle-exclamation mr-1"></i> ${readiness.open_blockers_count} open blockers
              </span>
            </div>
          </div>
        `;
      })
    );

    container.innerHTML = cards.join("");
  } catch (err) {
    console.error("Fetch releases error:", err);
  }
}

// =========================================================================
// BUGFLOW AI CORE ENGINE DIALOG (Page 10 Architecture & Pipeline)
// =========================================================================
async function triggerModalAICore() {
  if (!currentIssueInModal) return;

  const issue = currentIssueInModal;
  const payload = {
    title: issue.title,
    description: issue.description,
    category_id: issue.category_id,
    severity: issue.severity,
    code_diff: issue.code_references ? `Reference: ${issue.code_references}` : "",
    affected_modules: issue.affected_modules || "",
  };

  try {
    showAlert("BugFlow AI Core analyzing defect report, past fix patterns & capacity...", "info");
    const res = await fetch("/api/v1/issues/ai-core-analysis", {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      showAlert("AI Core analysis failed", "error");
      return;
    }

    const data = await res.json();

    document.getElementById("ai-ethics-report").textContent = data.ethical_bias_report;
    document.getElementById("ai-categorization").textContent = data.categorization;
    document.getElementById("ai-suggested-sev").textContent = `${data.suggested_severity} (${data.priority})`;
    document.getElementById("ai-priority-score").textContent = `Priority Score: ${data.priority_score}`;
    document.getElementById("ai-rollback-path").textContent = data.automated_cicd_rollback_path;

    // 4-Step Resolution Path
    const stepsContainer = document.getElementById("ai-resolution-path-steps");
    stepsContainer.innerHTML = data.personalized_resolution_path
      .map(
        (s) => `
        <div class="p-2.5 bg-slate-900 border border-slate-800 rounded-lg flex items-start space-x-3">
          <span class="w-5 h-5 rounded-full bg-indigo-600/30 text-indigo-400 font-bold flex items-center justify-center text-[10px] shrink-0 mt-0.5">${s.step}</span>
          <div class="flex-1 space-y-1">
            <div class="font-bold text-slate-200 text-xs">${s.phase}</div>
            <p class="text-[11px] text-slate-400">${s.action}</p>
            <div class="text-[10px] text-emerald-400 font-mono"><i class="fa-solid fa-vial mr-1"></i> Tests: ${s.suggested_tests.join(", ")}</div>
          </div>
        </div>
      `
      )
      .join("");

    // Historical Patterns
    const patternsContainer = document.getElementById("ai-historical-patterns");
    patternsContainer.innerHTML = data.matched_historical_patterns
      .map(
        (p) => `
        <div class="p-2 bg-slate-900 border border-slate-800/80 rounded">
          <span class="text-indigo-400 font-bold">&bull; ${p.past_fixes}</span>
          <span class="text-slate-400 block text-[10px] mt-0.5">Approach: ${p.suggested_approach} (Turnaround: ${p.resolution_time})</span>
        </div>
      `
      )
      .join("");

    // Recommended Devs
    const devsContainer = document.getElementById("ai-developer-assignments");
    devsContainer.innerHTML = data.developer_assignments
      .slice(0, 2)
      .map(
        (d) => `
        <div class="p-2 bg-slate-900 border border-slate-800 rounded flex items-center justify-between">
          <div>
            <span class="font-bold text-slate-200">${d.full_name} (@${d.username})</span>
            <span class="text-[10px] text-indigo-400 block">${d.rationale}</span>
          </div>
          <span class="px-2 py-0.5 rounded font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 text-xs">${d.match_percentage}% Match</span>
        </div>
      `
      )
      .join("");

    document.getElementById("ai-core-modal").classList.remove("hidden");
  } catch (err) {
    showAlert("AI Core Analysis error: " + err.message, "error");
  }
}

function closeAICoreModal() {
  document.getElementById("ai-core-modal").classList.add("hidden");
}

// =========================================================================
// MODULE 1: ISSUE MERGE WORKFLOW
// =========================================================================
async function openMergeModal() {
  if (!currentIssueInModal) return;
  const select = document.getElementById("merge-duplicate-select");
  select.innerHTML = `<option value="">Loading candidate issues...</option>`;

  try {
    const res = await fetch(`/api/v1/issues/?project_id=${currentIssueInModal.project_id}`, {
      headers: getAuthHeaders(),
    });
    if (res.ok) {
      const issues = await res.json();
      const candidates = issues.filter((i) => i.id !== currentIssueInModal.id && i.status !== "CLOSED");
      select.innerHTML = candidates
        .map((i) => `<option value="${i.id}">#${i.id} - ${i.title} (${i.status})</option>`)
        .join("");
    }
  } catch (_) {}

  document.getElementById("merge-issue-modal").classList.remove("hidden");
}

function closeMergeModal() {
  document.getElementById("merge-issue-modal").classList.add("hidden");
}

async function handleMergeIssue(e) {
  e.preventDefault();
  if (!currentIssueInModal) return;

  const dupId = parseInt(document.getElementById("merge-duplicate-select").value);
  const reason = document.getElementById("merge-reason-input").value.trim();

  try {
    const res = await fetch(`/api/v1/issues/${currentIssueInModal.id}/merge`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({ duplicate_issue_id: dupId, merge_reason: reason }),
    });

    if (!res.ok) {
      const err = await res.json();
      showAlert(err.detail || "Merge failed", "error");
      return;
    }

    showAlert(`Successfully merged duplicate issue #${dupId} into #${currentIssueInModal.id}!`, "success");
    closeMergeModal();
    openIssueModal(currentIssueInModal.id);
    fetchIssues();
  } catch (err) {
    showAlert("Merge error: " + err.message, "error");
  }
}

// =========================================================================
// MODULE 3: ESCALATION WORKFLOW
// =========================================================================
function openEscalateModal() {
  document.getElementById("escalate-issue-modal").classList.remove("hidden");
}

function closeEscalateModal() {
  document.getElementById("escalate-issue-modal").classList.add("hidden");
}

async function handleEscalateIssue(e) {
  e.preventDefault();
  if (!currentIssueInModal) return;

  const reason = document.getElementById("escalate-reason-input").value.trim();
  const targetPriority = document.getElementById("escalate-priority-select").value;

  try {
    const res = await fetch(`/api/v1/issues/${currentIssueInModal.id}/escalate`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({ reason: reason, target_priority: targetPriority }),
    });

    if (!res.ok) {
      const err = await res.json();
      showAlert(err.detail || "Escalation failed", "error");
      return;
    }

    showAlert(`Issue escalated to ${targetPriority}!`, "success");
    closeEscalateModal();
    openIssueModal(currentIssueInModal.id);
    fetchIssues();
  } catch (err) {
    showAlert("Escalation error: " + err.message, "error");
  }
}

// =========================================================================
// MODULE 3: APPROVAL WORKFLOW
// =========================================================================
function openApproveModal() {
  document.getElementById("approve-issue-modal").classList.remove("hidden");
}

function closeApproveModal() {
  document.getElementById("approve-issue-modal").classList.add("hidden");
}

async function handleApproveIssue(e) {
  e.preventDefault();
  if (!currentIssueInModal) return;

  const notes = document.getElementById("approve-notes-input").value.trim();

  try {
    const res = await fetch(`/api/v1/issues/${currentIssueInModal.id}/approve`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({ approval_notes: notes }),
    });

    if (!res.ok) {
      const err = await res.json();
      showAlert(err.detail || "Approval failed", "error");
      return;
    }

    showAlert(`Stage approved and workflow advanced!`, "success");
    closeApproveModal();
    openIssueModal(currentIssueInModal.id);
    fetchIssues();
  } catch (err) {
    showAlert("Approval error: " + err.message, "error");
  }
}

// =========================================================================
// MODULE 5: SYSTEM MAINTENANCE & ADMINISTRATION
// =========================================================================
async function triggerDatabaseBackup() {
  const box = document.getElementById("system-admin-output");
  box.classList.remove("hidden");
  box.innerHTML = `<i class="fa-solid fa-spinner fa-spin mr-1"></i> Creating JSON snapshot backup...`;

  try {
    const res = await fetch("/api/v1/system/backup", {
      method: "POST",
      headers: getAuthHeaders(),
    });
    const data = await res.json();
    if (res.ok) {
      box.innerHTML = `
        <span class="text-emerald-400 font-bold"><i class="fa-solid fa-check mr-1"></i> ${data.message}</span>
        <div class="mt-1 text-slate-400 text-[10px]">Records: ${JSON.stringify(data.records_count)}</div>
        <div class="text-indigo-400 text-[10px]">File: ${data.backup_file}</div>
      `;
      showAlert("Database backup successfully created!", "success");
    } else {
      box.innerHTML = `<span class="text-rose-400">${data.detail || "Backup failed"}</span>`;
    }
  } catch (err) {
    box.innerHTML = `<span class="text-rose-400">Error: ${err.message}</span>`;
  }
}

async function triggerDatabaseRestore() {
  const box = document.getElementById("system-admin-output");
  box.classList.remove("hidden");
  box.innerHTML = `<i class="fa-solid fa-spinner fa-spin mr-1"></i> Validating restore against latest snapshot...`;

  try {
    const res = await fetch("/api/v1/system/restore", {
      method: "POST",
      headers: getAuthHeaders(),
    });
    const data = await res.json();
    if (res.ok) {
      box.innerHTML = `
        <span class="text-emerald-400 font-bold"><i class="fa-solid fa-check mr-1"></i> ${data.message}</span>
        <div class="mt-1 text-slate-400 text-[10px]">Verified counts: ${JSON.stringify(data.records_count)}</div>
      `;
      showAlert("Database recovery verified successfully!", "success");
    } else {
      box.innerHTML = `<span class="text-rose-400">${data.detail || "Restore check failed"}</span>`;
    }
  } catch (err) {
    box.innerHTML = `<span class="text-rose-400">Error: ${err.message}</span>`;
  }
}

async function triggerRetentionPolicyCheck() {
  const box = document.getElementById("system-admin-output");
  box.classList.remove("hidden");
  box.innerHTML = `<i class="fa-solid fa-spinner fa-spin mr-1"></i> Evaluating 90-day retention threshold...`;

  try {
    const res = await fetch("/api/v1/system/retention-policy?retention_days=90", {
      headers: getAuthHeaders(),
    });
    const data = await res.json();
    if (res.ok) {
      box.innerHTML = `
        <span class="text-sky-400 font-bold"><i class="fa-solid fa-circle-info mr-1"></i> ${data.policy_name}</span>
        <div class="mt-1 text-slate-300">Archived / Evaluated Records: <strong>${data.archived_or_evaluated_records}</strong> closed issues</div>
        <div class="text-emerald-400 text-[10px]">Policy Status: ${data.status}</div>
      `;
      showAlert("Retention policy evaluation complete!", "info");
    }
  } catch (err) {
    box.innerHTML = `<span class="text-rose-400">Error: ${err.message}</span>`;
  }
}

async function showUserPortals() {
  const modal = document.getElementById("portals-modal");
  const container = document.getElementById("portals-list-container");
  modal.classList.remove("hidden");
  container.innerHTML = `<div class="text-slate-400">Loading user portals...</div>`;

  try {
    const res = await fetch("/api/v1/system/portals", { headers: getAuthHeaders() });
    if (res.ok) {
      const portals = await res.json();
      container.innerHTML = portals
        .map(
          (p) => `
        <div class="p-3 bg-slate-950 rounded-xl border border-slate-800 flex items-center justify-between">
          <div class="flex items-center space-x-2.5">
            <div class="w-7 h-7 rounded-lg bg-indigo-600/20 text-indigo-400 border border-indigo-500/30 flex items-center justify-center font-bold">
              <i class="fa-solid fa-layer-group text-xs"></i>
            </div>
            <div>
              <span class="font-bold text-slate-200 block">${p.portal_name}</span>
              <span class="text-[10px] text-slate-500">Type: ${p.portal_type}</span>
            </div>
          </div>
          <span class="px-2 py-0.5 rounded bg-slate-800 text-indigo-300 font-mono text-[10px]">v${p.version}</span>
        </div>
      `
        )
        .join("");
    }
  } catch (err) {
    container.innerHTML = `<span class="text-rose-400">Failed to load portals: ${err.message}</span>`;
  }
}
