const API = localStorage.getItem("veritas-api-url") || "http://127.0.0.1:8000/api/v1";
let activeCaseId = null;

const $ = (selector) => document.querySelector(selector);
const humanBytes = (bytes) => bytes === undefined || bytes === null ? "—" : bytes < 1024 ** 2 ? `${(bytes / 1024).toFixed(1)} KB` : `${(bytes / 1024 ** 2).toFixed(2)} MB`;
const setFeedback = (message, tone = "") => { const node = $("#upload-feedback"); node.textContent = message; node.style.color = tone || ""; };

function displayCase(caseData) {
  activeCaseId = caseData.case_id;
  const media = caseData.media || {};
  $("#case-label").textContent = `CASE ${activeCaseId.slice(0, 12).toUpperCase()}`;
  $("#case-status").textContent = `${caseData.status} // ${caseData.progress}%`;
  const technical = [media.resolution, media.fps ? `${media.fps} FPS` : null, media.duration_seconds !== null && media.duration_seconds !== undefined ? `${media.duration_seconds}s` : null].filter(Boolean).join(" · ") || "Not available";
  const fields = [["CASE ID", activeCaseId], ["SHA-256", media.original_sha256 || "—"], ["MEDIA", media.filename || "—"], ["SIZE", humanBytes(media.file_size_bytes)], ["TECHNICAL DATA", technical], ["PROCESSING HASH", media.processed_sha256 || "—"]];
  $("#metadata").innerHTML = fields.map(([label, value]) => `<div><dt>${label}</dt><dd>${value}</dd></div>`).join("");
  $("#retrieve-button").disabled = !["image", "video"].includes(media.modality_type);
  $("#retrieval-empty").hidden = false;
  $("#retrieval-results").hidden = true;
}

function displayModels(payload) {
  $("#mode-status").textContent = payload.execution_profile || "—";
  $("#model-device").textContent = `DEVICE: ${(payload.device || "unknown").toUpperCase()}`;
  $("#model-list").innerHTML = Object.entries(payload.models || {}).map(([name, entry]) => `<div class="model"><span class="tag ${entry.weights_available ? "available" : "unavailable"}">${entry.weights_available ? "READY" : "UNAVAILABLE"}</span><strong>${name.toUpperCase()}</strong><small>${entry.weights_available ? "validated weights detected" : "weights not installed"}</small></div>`).join("") || '<p class="muted">No model registry response.</p>';
}

function displayRetrieval(result) {
  const results = $("#retrieval-results");
  $("#retrieval-empty").hidden = true;
  results.hidden = false;
  const candidates = result.candidates || [];
  if (!candidates.length) { results.innerHTML = `<div class="empty-state"><strong>${result.overall_status}</strong><br/>No source candidate was located in the configured local repository. ${result.disclaimer}</div>`; return; }
  results.innerHTML = `<p class="notice">${result.disclaimer}</p>`;
  const template = $("#candidate-template");
  candidates.forEach((candidate, index) => {
    const fragment = template.content.cloneNode(true);
    $(".candidate-class", fragment).textContent = candidate.classification;
    $(".candidate-name", fragment).textContent = candidate.candidate_path || "Unavailable candidate";
    $(".candidate-score", fragment).textContent = candidate.source_confidence !== undefined ? `${(candidate.source_confidence * 100).toFixed(2)}%` : "—";
    if (candidate.provider === "local_repository" && candidate.source_confidence !== undefined) {
      const imageUrl = `${API}/cases/${encodeURIComponent(activeCaseId)}/source-retrieval/candidates/${index}/image`;
      $(".candidate-open", fragment).href = imageUrl;
      $(".candidate-preview", fragment).src = imageUrl;
    } else {
      $(".candidate-open", fragment).hidden = true;
      $(".candidate-preview", fragment).hidden = true;
    }
    const metrics = [["P-HASH DISTANCE", candidate.phash_distance], ["D-HASH DISTANCE", candidate.dhash_distance], ["SSIM", candidate.structural_similarity], ["CROP SIMILARITY", candidate.crop_similarity]];
    $(".metric-grid", fragment).innerHTML = metrics.map(([label, value]) => `<div class="metric"><label>${label}</label><b>${value ?? "—"}</b></div>`).join("");
    $(".candidate-note", fragment).textContent = candidate.verification || candidate.error || "No verification data.";
    results.append(fragment);
  });
}

async function request(path, options) {
  const response = await fetch(`${API}${path}`, options);
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || `Request failed (${response.status})`);
  return body;
}

$("#upload-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const submit = event.currentTarget.querySelector("button[type=submit]");
  submit.disabled = true; setFeedback("Capturing evidence, calculating hash, and recording custody…");
  try {
    const result = await request("/cases", { method: "POST", body: new FormData(event.currentTarget) });
    displayCase(result); setFeedback("Case initialized. Chain-of-custody metadata captured.", "var(--green)");
  } catch (error) { setFeedback(error.message, "var(--danger)"); }
  finally { submit.disabled = false; }
});

$("#media-file").addEventListener("change", (event) => { const file = event.target.files[0]; $("#selected-file").textContent = file ? `${file.name} · ${humanBytes(file.size)}` : "NO FILE SELECTED"; });
$("#focus-intake").addEventListener("click", () => $("#intake").scrollIntoView({ behavior: "smooth" }));
$("#retrieve-button").addEventListener("click", async () => {
  if (!activeCaseId) return;
  const button = $("#retrieve-button"); button.disabled = true; button.textContent = "SEARCHING…";
  try { displayRetrieval(await request(`/cases/${activeCaseId}/source-retrieval`, { method: "POST" })); }
  catch (error) { $("#retrieval-empty").hidden = false; $("#retrieval-empty").textContent = error.message; }
  finally { button.disabled = false; button.textContent = "SEARCH FOR SOURCE IMAGE"; }
});

async function bootstrap() {
  $("#utc-time").textContent = new Date().toISOString().slice(11, 19);
  setInterval(() => { $("#utc-time").textContent = new Date().toISOString().slice(11, 19); }, 1000);
  try { const health = await request("/health"); $("#api-status").textContent = "ONLINE"; $("#engine-status").textContent = "ONLINE"; await request("/models/status").then(displayModels); }
  catch (_) { $("#api-status").textContent = "OFFLINE"; $("#engine-status").textContent = "OFFLINE"; $("#model-list").innerHTML = `<p class="muted">Backend unavailable at ${API}. Start the FastAPI service to enable intake and retrieval.</p>`; }
}
bootstrap();
