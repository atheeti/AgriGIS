/* ============================================================
   AgriGIS Frontend  |  js/api.js
   All communication with the FastAPI backend.
   No GEE code here — backend handles all Earth Engine logic.
   ============================================================ */

const ApiModule = (() => {

  // Auto-detect backend URL:
  //   • If the page is served by FastAPI (port 8000) → same origin
  //   • If opened via VS Code Live Server (port 5500) → localhost:8000
  const BASE_URL =
    window.location.port === '8000'
      ? ''
      : 'http://localhost:8000';

  // ── HEALTH CHECK ─────────────────────────────────────────
  // Called on page load.  Updates the status pill in the header.
  async function checkHealth() {
    UIModule.setAPIStatus('checking', 'Connecting…');
    try {
      const res  = await fetch(`${BASE_URL}/api/health`);
      const data = await res.json();

      if (data.gee_ready) {
        UIModule.setAPIStatus('ready', 'GEE Ready');
        AppState.apiReady = true;
        UIModule.setMapHint('✓ GEE connected — search a location and draw your plot');
      } else {
        UIModule.setAPIStatus('error', 'GEE not ready');
        UIModule.showToast('Backend started but GEE is not initialised. Check backend logs.', 'error');
      }
    } catch {
      UIModule.setAPIStatus('error', 'Backend Offline');
      UIModule.showToast(
        'Cannot reach backend. Run:  cd backend  &&  uvicorn main:app --reload',
        'error'
      );
    }
  }

  // ── CALCULATE INDEX ───────────────────────────────────────
  // Sends the drawn polygon + selected index to /api/calculate.
  // The backend does all GEE work and returns stats + tile URL.
  async function calculate() {
    if (!AppState.drawnLayer)    { UIModule.showToast('Draw a plot first', 'error'); return; }
    if (!AppState.selectedIndex) { UIModule.showToast('Select an index first', 'error'); return; }

    const key      = AppState.selectedIndex;
    const cfg      = INDICES[key];
    const geometry = DrawModule.getGeoJSONGeometry();
    const daysBack = parseInt(document.getElementById('date-range').value);
    const maxCloud = parseInt(document.getElementById('cloud-cover').value);

    UIModule.showLoading();

    try {
      const res = await fetch(`${BASE_URL}/api/calculate`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({
          index:     key,
          geometry:  geometry,
          days_back: daysBack,
          max_cloud: maxCloud,
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || `Server error ${res.status}`);
      }

      const data = await res.json();
      // data = { mean, min, max, std, scene_date, tile_url, histogram, image_count }

      // Save result to shared state
      AppState.lastResult = { key, cfg, ...data };

      // Render the GEE classification tile overlay on the map
      DrawModule.renderGEETileOverlay(data.tile_url);

      // Update header scene date
      document.getElementById('sentinel-date-display').textContent = `S-2: ${data.scene_date}`;

      // Show results in sidebar
      UIModule.showResult(key, cfg, {
        mean:         data.mean,
        min:          data.min,
        max:          data.max,
        std:          data.std,
        sentinelDate: data.scene_date,
        histogram:    data.histogram,
      });

      UIModule.showToast(
        `${key}: ${data.mean.toFixed(3)} — ${cfg.classify(data.mean)}`,
        'success'
      );

    } catch (err) {
      console.error('[ApiModule]', err.message);
      UIModule.showToast(err.message, 'error');
    } finally {
      UIModule.hideLoading();
    }
  }

  // ── INIT: check health on page load ──────────────────────
  document.addEventListener('DOMContentLoaded', () => {
    setTimeout(checkHealth, 800);   // slight delay for page to render first
    console.log('[api.js] ApiModule ready. Backend:', BASE_URL || '(same origin)');
  });

  return { checkHealth, calculate };
})();


