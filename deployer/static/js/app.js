// BuildSmart 360 - Standalone Render Deployment Application Frontend Controller

let currentStep = 1;
let appConfig = null;
let activeDeployInterval = null;
let latestCommitData = null;
let approvalState = null;

document.addEventListener("DOMContentLoaded", () => {
  loadInitialConfig();
});

function showToast(message, type = "success") {
  const container = document.getElementById("toastContainer");
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.innerText = message;
  container.appendChild(toast);
  setTimeout(() => {
    toast.remove();
  }, 4000);
}

function restoreRenderCredentials() {
  const savedKey = localStorage.getItem("bs_render_api_key");
  const savedOwner = localStorage.getItem("bs_render_owner_id");
  const savedService = localStorage.getItem("bs_render_service_name");

  if (savedKey) {
    const keyInput = document.getElementById("renderApiKeyInput");
    if (keyInput) keyInput.value = savedKey;
    fetchRenderOwners(savedOwner);
  }
  if (savedService) {
    const sInput = document.getElementById("renderServiceNameInput");
    if (sInput) sInput.value = savedService;
    updateRedirectUriDisplay(savedService);
  }

  const ownerSelect = document.getElementById("renderOwnerSelect");
  if (ownerSelect) {
    ownerSelect.addEventListener("change", (e) => {
      localStorage.setItem("bs_render_owner_id", e.target.value);
    });
  }
}

async function refreshLatestCommit(fetchRemote = false) {
  const btn = document.getElementById("btnRefreshCommits");
  if (btn) {
    btn.disabled = true;
    btn.innerText = "Checking...";
  }

  try {
    const res = await fetch(`/api/git/commits?fetch=${fetchRemote ? "true" : "false"}`);
    const data = await res.json();
    if (res.ok && data.success && data.latest) {
      latestCommitData = data.latest;
      approvalState = data.approval || {};
      updateCommitUI(latestCommitData, approvalState);
      if (fetchRemote) {
        showToast("Fetched latest commits from GitHub!");
      }
    }
  } catch (err) {
    console.warn("Could not fetch commits:", err);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerText = "🔄 Check for New Commits";
    }
  }
}

function updateCommitUI(commit, approval) {
  if (!commit) return;

  // Step 3 Commit Details
  const hashEl = document.getElementById("commitHashBadge");
  const subjectEl = document.getElementById("commitSubject");
  const authorEl = document.getElementById("commitAuthor");
  const timeEl = document.getElementById("commitTimestamp");
  const syncBadge = document.getElementById("commitSyncBadge");
  const approvalBadge = document.getElementById("commitApprovalBadge");
  const actionsBox = document.getElementById("approvalActionsBox");
  const promptTitle = document.getElementById("approvalPromptTitle");
  const promptDesc = document.getElementById("approvalPromptDesc");
  const btnApprove = document.getElementById("btnApproveCommit");
  const btnQuickDeploy = document.getElementById("btnQuickDeploy");

  if (hashEl) hashEl.innerText = commit.short_hash || commit.hash.substring(0, 7);
  if (subjectEl) subjectEl.innerText = commit.subject || "No message";
  if (authorEl) authorEl.innerText = `Committed by ${commit.author_name} (${commit.author_email || "GitHub"})`;
  if (timeEl) timeEl.innerText = commit.date || "";

  if (syncBadge) {
    syncBadge.className = commit.is_on_origin ? "badge badge-success font-mono" : "badge badge-warning font-mono";
    syncBadge.innerText = commit.is_on_origin ? "origin/main (Pushed)" : "Local (Push to GitHub)";
  }

  // Check approval
  const isApproved = (
    commit.approved ||
    (approval && (approval.approved_commit === commit.hash || approval.short_hash === commit.short_hash))
  );

  if (isApproved) {
    if (approvalBadge) {
      approvalBadge.className = "badge badge-success";
      approvalBadge.innerText = "✅ Approved for Deployment";
    }
    if (actionsBox) actionsBox.className = "approval-actions-box approved mt-3";
    if (promptTitle) promptTitle.innerHTML = `✅ Commit Approved for Deployment`;
    if (promptDesc) promptDesc.innerHTML = `Authorized by <strong>${(approval && approval.approver) || "Administrator"}</strong> for Render production.`;
    if (btnApprove) btnApprove.classList.add("hidden");
    if (btnQuickDeploy) {
      btnQuickDeploy.classList.remove("hidden");
      btnQuickDeploy.innerText = `🚀 Deploy Approved Commit (${commit.short_hash}) to Render &rarr;`;
    }

    // Step 4 updates
    const s4Banner = document.getElementById("step4CommitBanner");
    const s4Badge = document.getElementById("step4ApprovalBadge");
    const s4ApproveBtn = document.getElementById("step4ApproveBtn");
    const btnDeploy = document.getElementById("btnRenderDeploy");

    if (s4Banner) s4Banner.className = "commit-target-banner approved mt-3";
    if (s4Badge) {
      s4Badge.className = "badge badge-success";
      s4Badge.innerText = "✅ Approved";
    }
    if (s4ApproveBtn) s4ApproveBtn.classList.add("hidden");
    if (btnDeploy && !btnDeploy.innerText.includes("Deploying")) {
      btnDeploy.innerText = `Deploy Approved Commit (${commit.short_hash}) to Render Now`;
    }
  } else {
    if (approvalBadge) {
      approvalBadge.className = "badge badge-warning";
      approvalBadge.innerText = "⏳ Pending Approval";
    }
    if (actionsBox) actionsBox.className = "approval-actions-box mt-3";
    if (promptTitle) promptTitle.innerText = "Deployment Authorization Required:";
    if (promptDesc) promptDesc.innerText = "Review the commit above. Click 'Approve Commit' to verify this release and authorize deployment.";
    if (btnApprove) {
      btnApprove.classList.remove("hidden");
      btnApprove.innerText = `✅ Approve Commit (${commit.short_hash}) for Deployment`;
    }
    if (btnQuickDeploy) btnQuickDeploy.classList.add("hidden");

    // Step 4 updates
    const s4Banner = document.getElementById("step4CommitBanner");
    const s4Badge = document.getElementById("step4ApprovalBadge");
    const s4ApproveBtn = document.getElementById("step4ApproveBtn");
    const btnDeploy = document.getElementById("btnRenderDeploy");

    if (s4Banner) s4Banner.className = "commit-target-banner mt-3";
    if (s4Badge) {
      s4Badge.className = "badge badge-warning";
      s4Badge.innerText = "⚠️ Pending Approval";
    }
    if (s4ApproveBtn) s4ApproveBtn.classList.remove("hidden");
    if (btnDeploy && !btnDeploy.innerText.includes("Deploying")) {
      btnDeploy.innerText = `Deploy BuildSmart 360 to Render Now`;
    }
  }

  // Step 4 Banner Details
  const s4Hash = document.getElementById("step4CommitHash");
  const s4Sub = document.getElementById("step4CommitSubject");
  const s4Meta = document.getElementById("step4CommitMeta");

  if (s4Hash) s4Hash.innerText = commit.short_hash || commit.hash.substring(0, 7);
  if (s4Sub) s4Sub.innerText = commit.subject || "Latest commit";
  if (s4Meta) s4Meta.innerText = `${commit.author_name} • ${commit.date}`;
}

async function approveCurrentCommit() {
  if (!latestCommitData) {
    await refreshLatestCommit(false);
  }
  if (!latestCommitData) {
    showToast("No commit found to approve", "error");
    return;
  }

  const btnApprove = document.getElementById("btnApproveCommit");
  const s4ApproveBtn = document.getElementById("step4ApproveBtn");
  if (btnApprove) btnApprove.disabled = true;
  if (s4ApproveBtn) s4ApproveBtn.disabled = true;

  try {
    const res = await fetch("/api/git/approve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        commit_hash: latestCommitData.hash,
        approver: "Workspace Owner",
        notes: "Approved via BuildSmart Deployer"
      })
    });
    const data = await res.json();
    if (res.ok && data.success) {
      approvalState = data.approval;
      latestCommitData.approved = true;
      updateCommitUI(latestCommitData, approvalState);
      showToast(`Commit ${latestCommitData.short_hash} approved for Render deployment!`);
    } else {
      throw new Error(data.error || "Failed to approve commit");
    }
  } catch (err) {
    showToast(err.message, "error");
  } finally {
    if (btnApprove) btnApprove.disabled = false;
    if (s4ApproveBtn) s4ApproveBtn.disabled = false;
  }
}

async function quickDeployApprovedCommit() {
  jumpToStep(4);
  const apiKey = document.getElementById("renderApiKeyInput").value.trim();
  const ownerId = document.getElementById("renderOwnerSelect").value;

  if (!apiKey) {
    showToast("Please enter your Render API Key to proceed with deployment", "error");
    document.getElementById("renderApiKeyInput").focus();
    return;
  }
  if (!ownerId) {
    await fetchRenderOwners();
  }
  triggerRenderDeploy();
}

async function loadInitialConfig() {
  try {
    const res = await fetch("/api/config");
    appConfig = await res.json();
    
    // Header & Workspace
    const wsName = appConfig.buildsmart_path.split("\\").pop();
    document.getElementById("workspaceBadge").innerText = `Workspace: ${wsName}`;
    
    // Step 1 Previews
    document.getElementById("sheetIdPreview").innerText = `Sheet: ${appConfig.config_summary.sheet_id}`;
    document.getElementById("brevoSenderPreview").innerText = `Sender: ${appConfig.config_summary.brevo_sender}`;

    // Step 2 Previews
    updateGitUI(appConfig.git);

    // Step 3 Previews
    document.getElementById("githubRepoUrlInput").value = appConfig.git.remote_origin || appConfig.default_repo_url || "https://github.com/vtabsquare/Build-smart-application.git";

    // Load Commit & Approval State
    if (appConfig.git && appConfig.git.latest_commit_details) {
      latestCommitData = appConfig.git.latest_commit_details;
      approvalState = appConfig.git.approval || {};
      updateCommitUI(latestCommitData, approvalState);
    } else {
      refreshLatestCommit(false);
    }

    // Step 4 Environment Variables
    renderEnvVarsCopy(appConfig.render_vars);

    // Step 5 Defaults
    updateRedirectUriDisplay("buildsmart-360");

    // Restore saved Render credentials
    restoreRenderCredentials();

  } catch (err) {
    showToast("Failed to load local configuration: " + err.message, "error");
  }
}

// Navigation
function jumpToStep(step) {
  currentStep = step;
  for (let i = 1; i <= 5; i++) {
    const section = document.getElementById(`stepSection${i}`);
    const node = document.getElementById(`stepNode${i}`);
    if (i === step) {
      section.classList.remove("hidden");
      node.classList.add("active");
    } else {
      section.classList.add("hidden");
      node.classList.remove("active");
      if (i < step) {
        node.classList.add("completed");
      }
    }
  }
}

function nextStep(step) {
  jumpToStep(step);
}

function prevStep(step) {
  jumpToStep(step);
}

// ==========================================
// STEP 1: Pre-Flight Verification & Credentials
// ==========================================

async function saveIntegrationKeys() {
  const refreshToken = document.getElementById("inputGoogleRefreshToken")?.value?.trim();
  const brevoKey = document.getElementById("inputBrevoApiKey")?.value?.trim();
  const statusEl = document.getElementById("keysSaveStatus");

  if (!refreshToken && !brevoKey) {
    if (statusEl) statusEl.innerText = "Please enter at least one key.";
    return;
  }
  if (statusEl) statusEl.innerText = "Applying credentials...";
  try {
    const res = await fetch("/api/config/update-keys", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        GOOGLE_REFRESH_TOKEN: refreshToken,
        BREVO_API_KEY: brevoKey,
      }),
    });
    const data = await res.json();
    if (data.success) {
      if (statusEl) statusEl.innerText = "Applied successfully! Retesting...";
      showToast("Credentials saved to session!");
      if (refreshToken) verifyGoogleSheets();
      if (brevoKey) verifyEmailDelivery();
    } else {
      if (statusEl) statusEl.innerText = "Failed: " + (data.error || "Unknown error");
    }
  } catch (err) {
    if (statusEl) statusEl.innerText = "Error: " + err.message;
  }
}

async function verifyGoogleSheets() {
  const btn = document.getElementById("btnVerifyGoogle");
  const badge = document.getElementById("googleStatusBadge");
  const resultBox = document.getElementById("googleResultBox");

  btn.disabled = true;
  badge.className = "status-indicator running";
  badge.innerText = "Checking...";
  resultBox.classList.add("hidden");

  try {
    const res = await fetch("/api/verify/google", { method: "POST" });
    const data = await res.json();
    if (res.ok && data.success) {
      badge.className = "status-indicator success";
      badge.innerText = "Connected";
      resultBox.className = "result-box success";
      resultBox.innerHTML = `<strong>Connected:</strong> ${data.message}<br><small>Matched Tabs: ${data.expected_tabs_matched.join(", ")}</small>`;
      resultBox.classList.remove("hidden");
      showToast("Google Sheets connection verified!");
    } else {
      throw new Error(data.error || "Failed to connect to Google Sheets");
    }
  } catch (err) {
    badge.className = "status-indicator error";
    badge.innerText = "Failed";
    resultBox.className = "result-box error";
    resultBox.innerHTML = `<strong>Error:</strong> ${err.message}`;
    resultBox.classList.remove("hidden");
    showToast(err.message, "error");
  } finally {
    btn.disabled = false;
  }
}

async function verifyEmailDelivery() {
  const btn = document.getElementById("btnVerifyEmail");
  const badge = document.getElementById("emailStatusBadge");
  const resultBox = document.getElementById("emailResultBox");

  btn.disabled = true;
  badge.className = "status-indicator running";
  badge.innerText = "Sending...";
  resultBox.classList.add("hidden");

  try {
    const res = await fetch("/api/verify/email", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    const data = await res.json();
    if (res.ok && data.success) {
      badge.className = "status-indicator success";
      badge.innerText = "Verified";
      resultBox.className = "result-box success";
      resultBox.innerHTML = `<strong>Delivered:</strong> ${data.message}`;
      resultBox.classList.remove("hidden");
      showToast("Test email sent to verified address!");
    } else {
      throw new Error(data.error || "Failed to send email");
    }
  } catch (err) {
    badge.className = "status-indicator error";
    badge.innerText = "Failed";
    resultBox.className = "result-box error";
    resultBox.innerHTML = `<strong>Error:</strong> ${err.message}`;
    resultBox.classList.remove("hidden");
    showToast(err.message, "error");
  } finally {
    btn.disabled = false;
  }
}

async function runTestSuite() {
  const btn = document.getElementById("btnRunTests");
  const badge = document.getElementById("testsStatusBadge");
  const termBox = document.getElementById("testOutputBox");

  btn.disabled = true;
  badge.className = "status-indicator running";
  badge.innerText = "Running Tests...";
  termBox.classList.remove("hidden");
  termBox.innerText = "Running 20 automated tests...\n";

  try {
    const res = await fetch("/api/verify/tests", { method: "POST" });
    const data = await res.json();
    termBox.innerText = data.output || "No output";
    if (res.ok && data.success) {
      badge.className = "status-indicator success";
      badge.innerText = "All Tests Passed";
      showToast("All 20 application tests passed cleanly!");
    } else {
      badge.className = "status-indicator error";
      badge.innerText = "Tests Failed";
      showToast("Some tests failed. Inspect the terminal log.", "error");
    }
  } catch (err) {
    badge.className = "status-indicator error";
    badge.innerText = "Error";
    termBox.innerText = "Execution failed: " + err.message;
    showToast(err.message, "error");
  } finally {
    btn.disabled = false;
  }
}

// ==========================================
// STEP 2: Git Verification & Commit
// ==========================================

function updateGitUI(git) {
  document.getElementById("gitBranchDisplay").innerText = `Branch: ${git.branch}`;
  document.getElementById("gitLastCommit").innerText = git.last_commit || "None";
  document.getElementById("gitRemoteDisplay").innerText = git.remote_origin || "None";

  const badge = document.getElementById("gitCleanBadge");
  const list = document.getElementById("uncommittedFilesList");
  const wrap = document.getElementById("uncommittedFilesWrap");

  list.innerHTML = "";
  if (git.clean) {
    badge.className = "status-indicator success";
    badge.innerText = "Clean Working Tree";
    wrap.classList.add("hidden");
  } else {
    badge.className = "status-indicator error";
    badge.innerText = `${git.modified_files.length} Uncommitted Files`;
    wrap.classList.remove("hidden");
    git.modified_files.forEach((file) => {
      const li = document.createElement("li");
      li.className = "text-mono text-muted";
      li.innerText = file;
      list.appendChild(li);
    });
  }
}

async function commitChanges() {
  const msgInput = document.getElementById("commitMessageInput");
  const msg = msgInput.value.trim() || "deploy: prepare release for Render";
  const btn = document.getElementById("btnCommit");

  btn.disabled = true;
  try {
    const res = await fetch("/api/git/commit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: msg }),
    });
    const data = await res.json();
    if (res.ok && data.success) {
      showToast("Changes committed successfully!");
      const stRes = await fetch("/api/git/status");
      updateGitUI(await stRes.json());
      msgInput.value = "";
      await refreshLatestCommit(false);
    } else {
      throw new Error(data.error || "Failed to commit");
    }
  } catch (err) {
    showToast(err.message, "error");
  } finally {
    btn.disabled = false;
  }
}

// ==========================================
// STEP 3: GitHub Remote & Push
// ==========================================

async function saveRemoteUrl() {
  const url = document.getElementById("githubRepoUrlInput").value.trim();
  if (!url) {
    showToast("Please enter a GitHub repository URL", "error");
    return;
  }
  try {
    const res = await fetch("/api/git/set-remote", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ remote_url: url }),
    });
    const data = await res.json();
    if (res.ok && data.success) {
      showToast("Remote origin configured!");
      document.getElementById("gitRemoteDisplay").innerText = url;
    } else {
      throw new Error(data.error || "Failed to set remote");
    }
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function pushToGitHub() {
  const btn = document.getElementById("btnPushGitHub");
  const outputBox = document.getElementById("gitPushOutput");

  btn.disabled = true;
  btn.innerText = "Pushing to GitHub...";
  outputBox.classList.remove("hidden");
  outputBox.innerText = "Running: git push -u origin main...\n";

  try {
    const res = await fetch("/api/git/push", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ branch: "main" }),
    });
    const data = await res.json();
    outputBox.innerText = data.output || data.error || "Pushed.";
    if (res.ok && data.success) {
      showToast("Pushed to GitHub successfully!");
      btn.innerText = "Pushed to GitHub!";
      await refreshLatestCommit(true);
    } else {
      throw new Error(data.error || "Push failed");
    }
  } catch (err) {
    showToast(err.message, "error");
    btn.innerText = "Push to GitHub (Retry)";
  } finally {
    btn.disabled = false;
  }
}

// ==========================================
// STEP 4: Render Deployment
// ==========================================

function switchDeployTab(tab) {
  const autoBtn = document.getElementById("tabAutoBtn");
  const manualBtn = document.getElementById("tabManualBtn");
  const autoContent = document.getElementById("tabContentAuto");
  const manualContent = document.getElementById("tabContentManual");

  if (tab === "auto") {
    autoBtn.classList.add("active");
    manualBtn.classList.remove("active");
    autoContent.classList.remove("hidden");
    manualContent.classList.add("hidden");
  } else {
    manualBtn.classList.add("active");
    autoBtn.classList.remove("active");
    manualContent.classList.remove("hidden");
    autoContent.classList.add("hidden");
  }
}

async function fetchRenderOwners(selectedOwnerId = null) {
  const key = document.getElementById("renderApiKeyInput").value.trim();
  if (!key) {
    showToast("Please enter your Render API Key", "error");
    return;
  }
  localStorage.setItem("bs_render_api_key", key);
  try {
    const res = await fetch("/api/render/owners", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ api_key: key }),
    });
    const data = await res.json();
    if (res.ok && data.success) {
      const select = document.getElementById("renderOwnerSelect");
      select.innerHTML = "";
      data.owners.forEach((item) => {
        const owner = item.owner || item;
        const opt = document.createElement("option");
        opt.value = owner.id;
        opt.innerText = `${owner.name || owner.email} (${owner.type})`;
        if (selectedOwnerId && owner.id === selectedOwnerId) {
          opt.selected = true;
        }
        select.appendChild(opt);
      });
      if (selectedOwnerId) {
        select.value = selectedOwnerId;
      } else if (select.options.length > 0) {
        localStorage.setItem("bs_render_owner_id", select.value);
      }
      showToast(`Connected! Loaded ${data.owners.length} Render workspace(s).`);
    } else {
      throw new Error(data.error || "Invalid API key");
    }
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function triggerRenderDeploy() {
  const apiKey = document.getElementById("renderApiKeyInput").value.trim();
  const ownerId = document.getElementById("renderOwnerSelect").value;
  const serviceName = document.getElementById("renderServiceNameInput").value.trim();
  const repoUrl = document.getElementById("githubRepoUrlInput").value.trim();
  const region = document.getElementById("renderRegionSelect").value;
  const plan = document.getElementById("renderPlanSelect").value;

  if (!apiKey) {
    showToast("Please enter your Render API Key", "error");
    return;
  }
  if (!ownerId) {
    showToast("Please connect your API Key and select an owner/workspace", "error");
    return;
  }
  if (!repoUrl) {
    showToast("GitHub repository URL is missing. Set it in Step 3.", "error");
    return;
  }

  if (apiKey) localStorage.setItem("bs_render_api_key", apiKey);
  if (ownerId) localStorage.setItem("bs_render_owner_id", ownerId);
  if (serviceName) localStorage.setItem("bs_render_service_name", serviceName);

  const btn = document.getElementById("btnRenderDeploy");
  const progressWrap = document.getElementById("deployProgressWrap");
  const statusBadge = document.getElementById("deployStatusBadge");
  const statusText = document.getElementById("deployStatusText");
  const progressBar = document.getElementById("deployProgressBar");

  btn.disabled = true;
  progressWrap.classList.remove("hidden");
  statusBadge.className = "badge badge-accent";
  statusBadge.innerText = "Deploying";
  const commitTag = (latestCommitData && latestCommitData.short_hash) ? ` (Commit ${latestCommitData.short_hash})` : "";
  statusText.innerText = `Deploying latest approved commit${commitTag} to Render...`;
  progressBar.style.width = "30%";
  progressBar.style.background = "";

  try {
    const commitId = (latestCommitData && latestCommitData.hash) ? latestCommitData.hash : "";
    const res = await fetch("/api/render/deploy", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        api_key: apiKey,
        owner_id: ownerId,
        service_name: serviceName,
        repo_url: repoUrl,
        branch: "main",
        region: region,
        plan: plan,
        commit_id: commitId,
      }),
    });
    const data = await res.json();
    if (res.ok && data.success) {
      showToast(`Render service ${data.action} successfully!`);
      progressBar.style.width = "55%";
      statusText.innerText = `Service ID: ${data.service_id}. Building application...`;

      // Update Live URL
      const liveUrl = data.url || `https://${serviceName}.onrender.com`;
      document.getElementById("liveServiceLink").href = liveUrl;
      document.getElementById("liveServiceLink").innerText = liveUrl;
      document.getElementById("liveUrlBox").classList.remove("hidden");
      document.getElementById("liveHealthUrlInput").value = liveUrl;
      updateRedirectUriDisplay(serviceName);

      // Start status polling
      startStatusPolling(apiKey, data.service_id || "", data.deploy_id || "", serviceName);
    } else {
      throw new Error(data.error || "Deployment initiation failed");
    }
  } catch (err) {
    showToast(err.message, "error");
    statusBadge.className = "badge badge-error";
    statusBadge.innerText = "Error";
    statusText.innerText = err.message;
    progressBar.style.width = "10%";
    btn.disabled = false;
  }
}

function startStatusPolling(apiKey, serviceId, deployId, targetServiceName) {
  if (activeDeployInterval) clearInterval(activeDeployInterval);

  const statusBadge = document.getElementById("deployStatusBadge");
  const statusText = document.getElementById("deployStatusText");
  const progressBar = document.getElementById("deployProgressBar");
  const btn = document.getElementById("btnRenderDeploy");
  const sInput = document.getElementById("renderServiceNameInput") || document.getElementById("renderServiceName");
  const serviceName = (targetServiceName || (sInput ? sInput.value : "") || "buildsmart-360").trim();

  let pollCount = 0;
  activeDeployInterval = setInterval(async () => {
    pollCount++;
    try {
      const res = await fetch("/api/render/deploy-status", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          api_key: apiKey, 
          service_id: serviceId, 
          deploy_id: deployId,
          service_name: serviceName
        }),
      });
      const data = await res.json();
      if (res.ok && data.success) {
        if (data.service_id && !serviceId) {
          serviceId = data.service_id;
        }
        const st = data.status;
        statusBadge.innerText = st.toUpperCase();
        if (st === "live") {
          clearInterval(activeDeployInterval);
          statusBadge.className = "badge badge-success";
          statusText.innerText = `Your BuildSmart 360 service (ID: ${serviceId || serviceName}) is LIVE on Render!`;
          progressBar.style.width = "100%";
          progressBar.style.background = "linear-gradient(90deg, #0ea5e9, #10b981)";
          showToast("Deployment Complete! Service is Live.");
          btn.disabled = false;
          btn.innerText = "Deploy BuildSmart 360 to Render Now";
          nextStep(5);
        } else if (st === "build_failed" || st === "update_failed" || st === "canceled" || st === "deactivated") {
          clearInterval(activeDeployInterval);
          statusBadge.className = "badge badge-error";
          statusText.innerText = `Deployment ended with status: ${st}. Check logs and click Redeploy.`;
          progressBar.style.width = "100%";
          progressBar.style.background = "#ef4444";
          btn.disabled = false;
          btn.innerText = "Redeploy BuildSmart 360 to Render";
          showToast(`Deployment ${st}. Click Redeploy to retry.`, "error");
        } else {
          statusText.innerText = `Service ID: ${serviceId || serviceName}. Status: ${st}... (Elapsed: ${pollCount * 3}s)`;
          progressBar.style.width = `${Math.min(55 + pollCount * 2, 90)}%`;
        }
      } else {
        if (pollCount > 2 && (res.status === 400 || res.status === 404)) {
          clearInterval(activeDeployInterval);
          statusBadge.className = "badge badge-error";
          statusBadge.innerText = "Error";
          statusText.innerText = data.error || "Failed to fetch deployment status";
          btn.disabled = false;
        }
      }
    } catch (e) {
      // Ignore polling blips
    }
  }, 3500);
}

function renderEnvVarsCopy(vars) {
  const lines = vars.map((v) => `${v.key}=${v.value}`).join("\n");
  document.getElementById("envVarsText").innerText = lines;
}

function copyEnvVars() {
  const text = document.getElementById("envVarsText").innerText;
  navigator.clipboard.writeText(text);
  showToast("All 15 environment variables copied to clipboard!");
}

// ==========================================
// STEP 5: Verification & Google OAuth
// ==========================================

function updateRedirectUriDisplay(serviceName) {
  const uri = `https://${serviceName}.onrender.com/setup/google/callback`;
  document.getElementById("googleRedirectUriDisplay").innerText = uri;
}

function copyRedirectUri() {
  const uri = document.getElementById("googleRedirectUriDisplay").innerText;
  navigator.clipboard.writeText(uri);
  showToast("Redirect URI copied to clipboard!");
}

async function verifyLiveService() {
  const input = document.getElementById("liveHealthUrlInput");
  const url = input.value.trim();
  if (!url) {
    showToast("Please enter the live URL to verify", "error");
    return;
  }

  const btn = document.getElementById("btnVerifyLive");
  const badge = document.getElementById("liveHealthBadge");
  const resultBox = document.getElementById("liveHealthResultBox");
  const openWrap = document.getElementById("openLiveAppWrap");
  const openBtn = document.getElementById("btnOpenLiveApp");

  btn.disabled = true;
  badge.className = "status-indicator running";
  badge.innerText = "Checking...";
  resultBox.classList.add("hidden");

  try {
    const res = await fetch("/api/verify/live", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: url }),
    });
    const data = await res.json();
    if (res.ok && data.success) {
      badge.className = "status-indicator success";
      badge.innerText = "Live & Healthy";
      resultBox.className = "result-box success";
      resultBox.innerHTML = `
        <strong>Health Check Passed!</strong><br>
        Version: <code>${data.data.version}</code> | Storage: <code>${data.data.storage}</code><br>
        Google Sheets Source: <code>${data.data.source ? data.data.source.mode : "Ready"}</code> | Email: <code>${data.data.email_configured ? "Configured" : "Unset"}</code>
      `;
      resultBox.classList.remove("hidden");
      openWrap.classList.remove("hidden");
      openBtn.href = url.startsWith("http") ? url : `https://${url}`;
      showToast("Live deployment verified healthy!");
    } else {
      throw new Error(data.error || "Service did not respond with 200 OK");
    }
  } catch (err) {
    badge.className = "status-indicator error";
    badge.innerText = "Unhealthy";
    resultBox.className = "result-box error";
    resultBox.innerHTML = `<strong>Verification Failed:</strong> ${err.message}`;
    resultBox.classList.remove("hidden");
    showToast(err.message, "error");
  } finally {
    btn.disabled = false;
  }
}
