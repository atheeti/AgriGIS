/* ============================================================
   AgriGIS Frontend  |  js/draw.js
   All drawing tools: Rectangle · Polygon · Circle · Freehand
   Uses Turf.js for accurate area / perimeter.
   ============================================================ */

const DrawModule = (() => {

  const DRAW_STYLE = {
    color:       '#52B788',
    weight:      2.5,
    fillColor:   '#52B788',
    fillOpacity: 0.12,
    dashArray:   '7 4',
  };

  let _drawnItems  = null;
  let _activeId    = null;
  let _drawHandlers = {};
  // Freehand state
  let _fhActive = false, _fhPts = [], _fhLine = null;

  // ── INIT ─────────────────────────────────────────────────
  function init() {
    if (!AppState.map) { console.error('[DrawModule] Map not ready'); return; }

    _drawnItems = new L.FeatureGroup();
    AppState.map.addLayer(_drawnItems);

    _drawHandlers = {
      rect:   new L.Draw.Rectangle(AppState.map, { shapeOptions: DRAW_STYLE }),
      poly:   new L.Draw.Polygon  (AppState.map, { shapeOptions: DRAW_STYLE, showArea: true }),
      circle: new L.Draw.Circle   (AppState.map, { shapeOptions: DRAW_STYLE }),
    };

    AppState.map.on(L.Draw.Event.CREATED, (e) => {
      _drawnItems.addLayer(e.layer);
      _onComplete(e.layer);
    });

    console.log('[DrawModule] Drawing tools ready.');
  }

  // ── ACTIVATE TOOL ─────────────────────────────────────────
  function activate(toolId) {
    if (_activeId === toolId) { _deactivateAll(); return; }
    _deactivateAll();
    _activeId = toolId;
    document.querySelectorAll('.draw-btn').forEach(b => b.classList.remove('active'));
    document.getElementById('btn-' + toolId)?.classList.add('active');

    const hints = {
      rect:     'Click and drag to draw a rectangle',
      poly:     'Click to add points · Double-click to finish',
      circle:   'Click centre, then drag to set the radius',
      freehand: 'Hold mouse and drag to draw any shape',
    };
    // Enable draw handler FIRST — so drawing works even if UIModule hasn't loaded yet
    if (toolId === 'freehand') _startFH();
    else _drawHandlers[toolId]?.enable();

    // Show hint safely — optional chaining guards against UIModule load failures
    try { if (typeof UIModule !== 'undefined') UIModule.setMapHint(hints[toolId] || ''); } catch(_) {}
  }

  function _deactivateAll() {
    Object.values(_drawHandlers).forEach(h => h.disable());
    _stopFH();
    document.querySelectorAll('.draw-btn').forEach(b => b.classList.remove('active'));
    _activeId = null;
  }

  // ── FREEHAND ──────────────────────────────────────────────
  function _startFH() {
    _fhActive = true;
    AppState.map.dragging.disable();
    AppState.map.on('mousedown', _fhDown);
  }
  function _stopFH() {
    _fhActive = false;
    AppState.map.dragging.enable();
    AppState.map.off('mousedown', _fhDown);
    AppState.map.off('mousemove', _fhMove);
    AppState.map.off('mouseup',   _fhUp);
    if (_fhLine) { AppState.map.removeLayer(_fhLine); _fhLine = null; }
    _fhPts = [];
  }
  function _fhDown(e) {
    if (!_fhActive) return;
    _fhPts  = [e.latlng];
    _fhLine = L.polyline([e.latlng], { color:'#52B788', weight:2.5, dashArray:'5 3' }).addTo(AppState.map);
    AppState.map.on('mousemove', _fhMove);
    AppState.map.on('mouseup',   _fhUp);
  }
  function _fhMove(e) { if (_fhLine) { _fhPts.push(e.latlng); _fhLine.addLatLng(e.latlng); } }
  function _fhUp() {
    AppState.map.off('mousemove', _fhMove);
    AppState.map.off('mouseup',   _fhUp);
    if (_fhPts.length > 5) {
      if (_fhLine) { AppState.map.removeLayer(_fhLine); _fhLine = null; }
      _fhPts.push(_fhPts[0]);
      const poly = L.polygon(_fhPts, DRAW_STYLE);
      _drawnItems.addLayer(poly);
      _onComplete(poly);
    }
    _fhActive = false; _fhPts = [];
    AppState.map.dragging.enable();
    document.querySelectorAll('.draw-btn').forEach(b => b.classList.remove('active'));
    _activeId = null;
  }

  // ── ON COMPLETE ───────────────────────────────────────────
  function _onComplete(layer) {
    _deactivateAll();
    AppState.drawnLayer = layer;

    // ── Area & Perimeter via Turf.js ──────────────────────
    let areaText = '—', perimText = '—', vertCount = '—';
    if (layer instanceof L.Circle) {
      const r  = layer.getRadius();
      areaText  = (Math.PI * r * r / 10000).toFixed(2) + ' ha';
      perimText = (2 * Math.PI * r / 1000).toFixed(3) + ' km';
      vertCount = 'circle';
    } else {
      try {
        const gj    = layer.toGeoJSON();
        const areaM = turf.area(gj);
        areaText    = areaM >= 10000 ? (areaM / 10000).toFixed(2) + ' ha' : areaM.toFixed(0) + ' m²';
        perimText   = turf.length(turf.polygonToLine(gj), { units: 'kilometers' }).toFixed(3) + ' km';
        vertCount   = layer.getLatLngs()[0]?.length ?? '—';
      } catch (e) { console.warn('[DrawModule] Turf error:', e.message); }
    }

    document.getElementById('val-area').textContent  = areaText;
    document.getElementById('val-perim').textContent = perimText;
    document.getElementById('val-verts').textContent = vertCount;
    document.getElementById('plot-info-box').classList.remove('hidden');
    document.getElementById('draw-hint').style.display = 'none';

    if (typeof UIModule !== 'undefined') {
      UIModule.showSection('sec-indices');
      UIModule.setStepChip('chip-1', 'done');
      UIModule.setStepChip('chip-2', 'active');
    }

    const bounds = layer.getBounds?.();
    if (bounds?.isValid()) AppState.map.flyToBounds(bounds, { padding: [40, 40], maxZoom: 16, duration: 1.2 });
    UIModule.setMapHint('✓ Plot drawn — select an index and click Run on Earth Engine');
    UIModule.showToast(`Plot captured: ${areaText}`, 'success');
  }

  // ── CLEAR ALL ────────────────────────────────────────────
  function clearAll() {
    _drawnItems?.clearLayers();
    if (AppState.overlayLayer) { AppState.map.removeLayer(AppState.overlayLayer); AppState.overlayLayer = null; }
    AppState.drawnLayer = AppState.selectedIndex = AppState.lastResult = null;

    document.getElementById('val-area').textContent  = '—';
    document.getElementById('val-perim').textContent = '—';
    document.getElementById('val-verts').textContent = '—';
    document.getElementById('plot-info-box').classList.add('hidden');
    document.getElementById('draw-hint').style.display = '';

    UIModule.hideSection('sec-indices');
    UIModule.hideSection('sec-results');
    UIModule.hideSection('sec-legend');
    UIModule.hideSection('sec-download');
    UIModule.setStepChip('chip-1', '');
    UIModule.setStepChip('chip-2', '');
    UIModule.setStepChip('chip-3', '');
    document.querySelectorAll('.index-btn').forEach(b => { b.classList.remove('selected'); b.style.borderColor = ''; });

    UIModule.showToast('Plot cleared', 'info');
    UIModule.setMapHint('🌿 Search a location or draw a new plot');
  }

  // ── RENDER GEE TILE OVERLAY ──────────────────────────────
  // The tile URL comes directly from the backend (GEE getMapId).
  // Leaflet fetches tiles straight from Google Earth Engine servers.
  function renderGEETileOverlay(tileUrl) {
    if (AppState.overlayLayer) { AppState.map.removeLayer(AppState.overlayLayer); AppState.overlayLayer = null; }
    if (!tileUrl) return;

    AppState.overlayLayer = L.tileLayer(tileUrl, {
      opacity:     0.82,
      maxZoom:     21,
      attribution: 'Google Earth Engine / Sentinel-2',
    });
    AppState.overlayLayer.addTo(AppState.map);

    // Keep the polygon border visible on top of the overlay
    if (AppState.drawnLayer?.setStyle) {
      AppState.drawnLayer.setStyle({ color: '#FFFFFF', weight: 2.5, dashArray: null, fillOpacity: 0 });
      AppState.drawnLayer.bringToFront();
    }
  }

  // ── GEOMETRY EXPORT ──────────────────────────────────────
  // Returns a GeoJSON geometry object for the current drawn layer.
  // Circles are approximated to 64-point polygons via Turf.js.
  function getGeoJSONGeometry() {
    const layer = AppState.drawnLayer;
    if (!layer) return null;
    if (layer instanceof L.Circle) {
      const center   = [layer.getLatLng().lng, layer.getLatLng().lat];
      const radiusKm = layer.getRadius() / 1000;
      return turf.circle(center, radiusKm, { steps: 64 }).geometry;
    }
    return layer.toGeoJSON().geometry;
  }

  return { init, activate, clearAll, renderGEETileOverlay, getGeoJSONGeometry };
})();

document.addEventListener('DOMContentLoaded', () => {
  setTimeout(() => { DrawModule.init(); console.log('[draw.js] DrawModule ready.'); }, 60);
});


