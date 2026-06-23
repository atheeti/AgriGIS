/* ============================================================
   TerraGIS Frontend  |  js/map.js
   Leaflet map initialisation  ·  Google Satellite basemap
   Nominatim geocoder (free, no API key)
   ============================================================ */

const MapModule = (() => {

  // ── TILE LAYERS ───────────────────────────────────────────
  const TILES = {

    // Google Satellite — high-resolution, ideal for agriculture
    // Uses Google's public tile CDN (development / demo use)
    satellite: L.tileLayer(
      'https://mt{s}.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
      {
        subdomains: ['0', '1', '2', '3'],
        maxZoom:    21,
        attribution: '© Google Maps',
      }
    ),

    // OpenStreetMap — no-key fallback / street view
    osm: L.tileLayer(
      'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
      {
        maxZoom:    19,
        attribution: '© <a href="https://openstreetmap.org/copyright">OpenStreetMap</a>',
      }
    ),
  };

  let currentTile = 'satellite';

  // ── INIT ──────────────────────────────────────────────────
  function init() {
    AppState.map = L.map('map', {
      center:          [22.5, 78.5],   // Centre of India (good default)
      zoom:            5,
      zoomControl:     false,
      attributionControl: true,
    });

    // Custom zoom control — top-right so it doesn't clash with sidebar
    L.control.zoom({ position: 'topright' }).addTo(AppState.map);

    // Default: Google Satellite
    TILES.satellite.addTo(AppState.map);

    // Live coordinate display
    AppState.map.on('mousemove', (e) => {
      document.getElementById('coord-display').textContent =
        `${e.latlng.lat.toFixed(5)},  ${e.latlng.lng.toFixed(5)}`;
    });

    // Zoom display
    AppState.map.on('zoomend', () => {
      document.getElementById('zoom-display').textContent = AppState.map.getZoom();
      UIModule.updateScaleBar();
    });
    AppState.map.on('moveend', () => UIModule.updateScaleBar());
    setTimeout(() => UIModule.updateScaleBar(), 200);

    // Close search dropdown when clicking on map
    AppState.map.on('click', () => {
      document.getElementById('search-results').classList.remove('open');
    });

    console.log('[MapModule] Leaflet map ready · Google Satellite basemap');
  }

  // ── TILE SWITCHER ─────────────────────────────────────────
  function setTile(type) {
    if (type === currentTile) return;
    AppState.map.removeLayer(TILES[currentTile]);
    TILES[type].addTo(AppState.map);
    TILES[type].bringToBack();
    currentTile = type;
    document.getElementById('btn-satellite').classList.toggle('active', type === 'satellite');
    document.getElementById('btn-osm').classList.toggle('active', type === 'osm');
    UIModule.showToast(
      type === 'satellite' ? 'Google Satellite basemap' : 'OpenStreetMap basemap',
      'info'
    );
  }

  // ── BASEMAP OPACITY ───────────────────────────────────────
  // Dimmed while a Sentinel-2 true/false-colour composite is shown, so the
  // two image sources (different sensor/date) don't visually clash at the
  // AOI boundary — restored to full opacity once both composites are hidden.
  function setBasemapOpacity(value) {
    TILES[currentTile].setOpacity(value);
  }

  return { init, setTile, setBasemapOpacity };
})();


// ── NOMINATIM GEOCODER ────────────────────────────────────────
const SearchModule = (() => {

  let _timer = null;

  function init() {
    const input    = document.getElementById('search-input');
    const clearBtn = document.getElementById('search-clear');

    input.addEventListener('input', (e) => {
      const q = e.target.value.trim();
      clearBtn.classList.toggle('hidden', !q);
      clearTimeout(_timer);
      if (q.length >= 3) _timer = setTimeout(() => _run(q), 420);
      else _close();
    });

    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter')  { clearTimeout(_timer); _run(input.value.trim()); }
      if (e.key === 'Escape') _close();
    });

    clearBtn.addEventListener('click', () => {
      input.value = '';
      clearBtn.classList.add('hidden');
      _close();
      input.focus();
    });

    document.addEventListener('click', (e) => {
      if (!document.getElementById('search-wrap').contains(e.target)) _close();
    });
  }

  async function _run(query) {
    if (!query || query.length < 2) return;
    try {
      const url = `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(query)}&format=json&limit=6&addressdetails=1`;
      const res  = await fetch(url, { headers: { 'Accept-Language': 'en' } });
      const data = await res.json();
      if (!data.length) { UIModule.showToast('Location not found', 'error'); return; }
      _showResults(data);
    } catch {
      UIModule.showToast('Search unavailable — check your connection', 'error');
    }
  }

  function _showResults(results) {
    const box = document.getElementById('search-results');
    box.innerHTML = '';

    results.forEach((r) => {
      const parts = r.display_name.split(',');
      const el    = document.createElement('div');
      el.className = 'search-item';
      el.innerHTML = `
        <div class="search-item-main">${parts[0].trim()}</div>
        <div class="search-item-sub">${parts.slice(1, 3).join(',').trim()}</div>
      `;
      el.addEventListener('click', () => {
        AppState.map.flyTo(
          [parseFloat(r.lat), parseFloat(r.lon)],
          14,
          { duration: 1.4 }
        );
        document.getElementById('search-input').value = parts[0].trim();
        document.getElementById('search-clear').classList.remove('hidden');
        _close();
        UIModule.setMapHint('📍 Location found — select a draw tool and mark your plot');
      });
      box.appendChild(el);
    });

    box.classList.add('open');
  }

  function _close() {
    document.getElementById('search-results').classList.remove('open');
  }

  return { init };
})();


// ── INIT ON DOM READY ─────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  MapModule.init();
  SearchModule.init();
  console.log('[map.js] MapModule + SearchModule initialised.');
});
