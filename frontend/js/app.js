/* =============================================
   AgriGIS – Main Application Logic
   ============================================= */

const API_BASE = "http://localhost:8000";

let currentFarmerId = null;
let searchDebounceTimer = null;

// ── Init ──────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  MapManager.init(onPlotDrawn);
  initDateDefaults();
  bindEvents();
  setStep(1);
});

// ── Step Management ───────────────────────────
function setStep(step) {
  const panels = [
    { id: "panelSearch", step: 1 },
    { id: "panelRegister", step: 2 },
    { id: "panelIndex", step: 3 },
  ];
  panels.forEach(({ id, step: s }) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.classList.remove("locked", "active");
    if (s < step) {
      // completed — keep unlocked but not active
    } else if (s === step) {
      el.classList.add("active");
    } else {
      el.classList.add("locked");
    }
  });
}

// ── Date Defaults ─────────────────────────────
function initDateDefaults() {
  const today = new Date();
  const from = new Date(today);
  from.setDate(today.getDate() - 30);
  document.getElementById("dateTo").value = formatDate(today);
  document.getElementById("dateFrom").value = formatDate(from);
}

function formatDate(d) {
  return d.toISOString().split("T")[0];
}

// ── Plot Drawn Callback ───────────────────────
function onPlotDrawn(geometry, bounds) {
  setStep(2);
  const regPanel = document.getElementById("panelRegister");
  regPanel.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

// ── Event Bindings ────────────────────────────
function bindEvents() {
  // Location search
  document.getElementById("searchInput").addEventListener("keydown", (e) => {
    if (e.key === "Enter") doSearch();
  });
  document.getElementById("searchInput").addEventListener("input", (e) => {
    clearTimeout(searchDebounceTimer);
    const q = e.target.value.trim();
    if (q.length < 3) {
      document.getElementById("searchSuggestions").innerHTML = "";
      return;
    }
    searchDebounceTimer = setTimeout(() => fetchSuggestions(q), 400);
  });
  document.getElementById("btnSearch").addEventListener("click", doSearch);

  // Farmer form
  document.getElementById("farmerForm").addEventListener("submit", handleRegister);

  // Phone: digits only
  document.getElementById("farmerPhone").addEventListener("input", (e) => {
    e.target.value = e.target.value.replace(/\D/g, "").slice(0, 10);
  });

  // Index selection
  document.getElementById("indexSelect").addEventListener("change", (e) => {
    const key = e.target.value;
    if (key) {
      const cfg = getIndexConfig(key);
      document.getElementById("indexDescription").innerHTML =
        cfg ? `<strong>${cfg.formula}</strong><br>${cfg.description}` : "";
      renderLegend(key);
      document.getElementById("panelLegend").classList.remove("hidden");
    } else {
      document.getElementById("indexDescription").innerHTML = "";
    }
  });

  // Generate map
  document.getElementById("btnGenerateMap").addEventListener("click", handleGenerateMap);

  // Get statistics
  document.getElementById("btnGetStats").addEventListener("click", handleGetStats);
}

// ── Location Search ───────────────────────────
async function fetchSuggestions(query) {
  try {
    const url = `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(query)}&format=json&limit=5&countrycodes=in`;
    const res = await fetch(url, { headers: { "Accept-Language": "en" } });
    const data = await res.json();
    renderSuggestions(data);
  } catch {
    // network error — silent
  }
}

function renderSuggestions(results) {
  const el = document.getElementById("searchSuggestions");
  if (!results.length) { el.innerHTML = ""; return; }
  el.innerHTML = results.map((r, i) =>
    `<div class="suggestion-item" data-idx="${i}" data-lat="${r.lat}" data-lng="${r.lon}">
       <i class="fa-solid fa-location-dot"></i>
       <span>${r.display_name}</span>
     </div>`
  ).join("");
  el.querySelectorAll(".suggestion-item").forEach(item => {
    item.addEventListener("click", () => {
      const lat = parseFloat(item.dataset.lat);
      const lng = parseFloat(item.dataset.lng);
      MapManager.flyTo(lat, lng, 15);
      document.getElementById("searchInput").value = item.querySelector("span").textContent;
      el.innerHTML = "";
      MapManager.setMapInfo("Location found. Now draw your farm plot using the toolbar →");
    });
  });
}

async function doSearch() {
  const q = document.getElementById("searchInput").value.trim();
  if (!q) return;
  document.getElementById("searchSuggestions").innerHTML = "";
  try {
    const url = `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(q)}&format=json&limit=1`;
    const res = await fetch(url, { headers: { "Accept-Language": "en" } });
    const data = await res.json();
    if (data.length) {
      MapManager.flyTo(parseFloat(data[0].lat), parseFloat(data[0].lon), 14);
      MapManager.setMapInfo("Location found. Draw your farm plot using the toolbar on the right →");
    } else {
      showToast("Location not found. Try a different search.", "error");
    }
  } catch {
    showToast("Search failed. Check your connection.", "error");
  }
}

// ── Farmer Registration ───────────────────────
async function handleRegister(e) {
  e.preventDefault();
  clearErrors();

  const name = document.getElementById("farmerName").value.trim();
  const phone = document.getElementById("farmerPhone").value.trim();
  const plot = document.getElementById("plotNumber").value.trim();
  const crop = document.getElementById("cropType").value;
  const geometry = MapManager.getGeometry();

  let valid = true;
  if (!name || name.length < 2) { showError("errName", "Name must be at least 2 characters"); valid = false; }
  if (!/^\d{10}$/.test(phone)) { showError("errPhone", "Must be exactly 10 digits"); valid = false; }
  if (!plot) { showError("errPlot", "Plot number is required"); valid = false; }
  if (!crop) { showError("errCrop", "Please select a crop type"); valid = false; }
  if (!geometry) {
    showToast("Please draw your farm plot on the map first.", "error");
    valid = false;
  }
  if (!valid) return;

  const btn = document.getElementById("btnRegister");
  btn.disabled = true;
  btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Registering…';

  try {
    const res = await fetch(`${API_BASE}/api/farmers/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, phone, plot_number: plot, crop_type: crop, geometry }),
    });

    const data = await res.json();

    if (res.status === 409) {
      const msg = data.detail || "Plot number already exists";
      showError("errPlot", msg);
      showToast(msg, "error");
      document.getElementById("plotNumber").focus();
      return;
    }
    if (!res.ok) {
      const msg = data.detail?.[0]?.msg || data.detail || "Registration failed";
      showToast(msg, "error");
      return;
    }

    currentFarmerId = data.id;

    // Show success state
    document.getElementById("farmerForm").classList.add("hidden");
    const successCard = document.getElementById("registrationSuccess");
    successCard.classList.remove("hidden");
    document.getElementById("successName").textContent = `${name} · ${crop}`;

    showToast(`Welcome, ${name}! Registration successful.`, "success");
    setStep(3);

    const indexPanel = document.getElementById("panelIndex");
    setTimeout(() => indexPanel.scrollIntoView({ behavior: "smooth", block: "start" }), 400);

  } catch (err) {
    showToast("Connection error. Make sure the backend is running.", "error");
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<i class="fa-solid fa-check-circle"></i> Register & Continue';
  }
}

// ── Generate Index Map ────────────────────────
async function handleGenerateMap() {
  const indexKey = document.getElementById("indexSelect").value;
  const dateFrom = document.getElementById("dateFrom").value;
  const dateTo = document.getElementById("dateTo").value;
  const geometry = MapManager.getGeometry();

  if (!indexKey) { showToast("Please select an index.", "error"); return; }
  if (!geometry) { showToast("Please draw your farm plot first.", "error"); return; }
  if (!dateFrom || !dateTo) { showToast("Please select date range.", "error"); return; }
  if (new Date(dateTo) < new Date(dateFrom)) { showToast("End date must be after start date.", "error"); return; }

  showLoader("Generating " + indexKey + " map from Sentinel-2…");

  try {
    const res = await fetch(`${API_BASE}/api/indices/map`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        index: indexKey,
        geometry,
        date_from: dateFrom,
        date_to: dateTo,
        farmer_id: currentFarmerId,
      }),
    });

    const data = await res.json();

    if (!res.ok) {
      showToast(data.detail || "Map generation failed.", "error");
      return;
    }

    MapManager.setIndexOverlay(data.image_data, data.bounds);
    renderLegend(indexKey);

    document.getElementById("panelLegend").classList.remove("hidden");
    MapManager.setMapInfo(`${data.full_name} map — ${dateFrom} to ${dateTo}`);
    showToast(`${indexKey} map generated successfully!`, "success");

  } catch (err) {
    showToast("Failed to generate map. Check backend connection.", "error");
    console.error(err);
  } finally {
    hideLoader();
  }
}

// ── Get Statistics ────────────────────────────
async function handleGetStats() {
  const indexKey = document.getElementById("indexSelect").value;
  const dateFrom = document.getElementById("dateFrom").value;
  const dateTo = document.getElementById("dateTo").value;
  const geometry = MapManager.getGeometry();

  if (!indexKey) { showToast("Please select an index.", "error"); return; }
  if (!geometry) { showToast("Please draw your farm plot first.", "error"); return; }

  const statsPanel = document.getElementById("panelStats");
  statsPanel.classList.remove("hidden");
  document.getElementById("statsIndexTitle").textContent = `${indexKey} Statistics`;
  document.getElementById("valueMean").textContent = "…";

  showLoader("Calculating " + indexKey + " statistics…");

  try {
    const res = await fetch(`${API_BASE}/api/indices/stats`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        index: indexKey,
        geometry,
        date_from: dateFrom,
        date_to: dateTo,
        farmer_id: currentFarmerId,
      }),
    });

    const data = await res.json();

    if (!res.ok) {
      showToast(data.detail || "Statistics calculation failed.", "error");
      return;
    }

    renderStats(data, indexKey);
    statsPanel.scrollIntoView({ behavior: "smooth", block: "nearest" });

  } catch (err) {
    showToast("Failed to get statistics. Check backend connection.", "error");
    console.error(err);
  } finally {
    hideLoader();
  }
}

function renderStats(data, indexKey) {
  const s = data.statistics;
  const color = getHealthColor(s.mean, indexKey);

  document.getElementById("valueMean").textContent = s.mean.toFixed(4);
  document.getElementById("valueMean").style.color = color;
  document.getElementById("valueLabel").textContent = `Mean ${indexKey}`;

  const interpEl = document.getElementById("valueInterpretation");
  interpEl.textContent = data.interpretation || "";
  interpEl.style.display = data.interpretation ? "inline-block" : "none";

  document.getElementById("statMin").textContent = s.min.toFixed(4);
  document.getElementById("statMax").textContent = s.max.toFixed(4);
  document.getElementById("statStd").textContent = s.stDev.toFixed(4);
  document.getElementById("statP25").textContent = s.percentiles?.p25?.toFixed(4) ?? "—";
  document.getElementById("statP50").textContent = s.percentiles?.p50?.toFixed(4) ?? "—";
  document.getElementById("statP75").textContent = s.percentiles?.p75?.toFixed(4) ?? "—";

  const pixelEl = document.getElementById("pixelInfo");
  if (s.totalPixels) {
    const pct = (((s.totalPixels - s.noDataPixels) / s.totalPixels) * 100).toFixed(1);
    pixelEl.textContent = `${s.totalPixels.toLocaleString()} pixels · ${pct}% valid`;
  } else {
    pixelEl.textContent = "";
  }
}

// ── UI Helpers ────────────────────────────────
function showLoader(text = "Processing…") {
  document.getElementById("loaderText").textContent = text;
  document.getElementById("mapLoader").classList.remove("hidden");
}
function hideLoader() {
  document.getElementById("mapLoader").classList.add("hidden");
}

function showError(id, msg) {
  const el = document.getElementById(id);
  if (el) el.textContent = msg;
}
function clearErrors() {
  ["errName", "errPhone", "errPlot", "errCrop"].forEach(id => showError(id, ""));
}

function showToast(message, type = "info") {
  const icons = { success: "circle-check", error: "circle-xmark", info: "circle-info" };
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.innerHTML = `<i class="fa-solid fa-${icons[type] || "circle-info"}"></i><span>${message}</span>`;
  const container = document.getElementById("toastContainer");
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.animation = "slideOut 0.3s ease forwards";
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}
