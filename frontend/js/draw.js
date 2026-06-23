/* ============================================================
   TerraGIS Frontend  |  js/draw.js
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
  // Edit state
  let _editHandler = null;
  let _editing      = false;
  // Cross-section line state
  let _xsHandler   = null;
  let _xsLineLayer = null;
  let _xsActive    = false;
  let _xsMarker    = null;

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
    _xsHandler = new L.Draw.Polyline(AppState.map, { shapeOptions: { color: '#FF3B30', weight: 3 } });

    AppState.map.on(L.Draw.Event.CREATED, (e) => {
      if (_xsActive) {
        _xsActive = false;
        if (_xsLineLayer) AppState.map.removeLayer(_xsLineLayer);
        _xsLineLayer = e.layer;
        _xsLineLayer.addTo(AppState.map);
        if (typeof UIModule !== 'undefined') UIModule.onCrossSectionLineDrawn();
        return;
      }
      _drawnItems.addLayer(e.layer);
      _onComplete(e.layer);
    });

    AppState.map.on(L.Draw.Event.EDITED, () => _refreshPlotStats());

    console.log('[DrawModule] Drawing tools ready.');
  }

  // ── EDIT VERTICES (toggle reshape mode) ───────────────────
  // Uses Leaflet.draw's edit toolbar to make every shape in
  // _drawnItems draggable at the vertex level (works for
  // polygon/rectangle node handles and the circle's edge handle).
  function toggleEdit() {
    if (!_drawnItems || _drawnItems.getLayers().length === 0) return;

    if (_editing) {
      _editHandler?.disable();
      _editHandler = null;
      _editing = false;
      _refreshPlotStats();
    } else {
      _deactivateAll();
      _editHandler = new L.EditToolbar.Edit(AppState.map, { featureGroup: _drawnItems });
      _editHandler.enable();
      _editing = true;
    }
    return _editing;
  }

  // ── AREA UNIT CONVERSION ──────────────────────────────────
  const AREA_UNITS = {
    ha:    { label: 'ha',     toUnit: m2 => m2 / 10000 },
    sqkm:  { label: 'km²',    toUnit: m2 => m2 / 1e6 },
    acre:  { label: 'acres',  toUnit: m2 => m2 / 4046.8564224 },
    sqyd:  { label: 'yd²',    toUnit: m2 => m2 * 1.19599005 },
  };

  function _formatArea(areaM) {
    AppState.lastAreaM2 = areaM;
    const sel  = document.getElementById('area-unit-select');
    const unit = AREA_UNITS[sel?.value] || AREA_UNITS.ha;
    return unit.toUnit(areaM).toFixed(2) + ' ' + unit.label;
  }

  // Re-renders the area text using the currently stored raw area
  // (called when the unit dropdown selection changes).
  function refreshAreaDisplay() {
    if (AppState.lastAreaM2 == null) return;
    document.getElementById('val-area').textContent = _formatArea(AppState.lastAreaM2);
  }

  function _refreshPlotStats() {
    const layer = AppState.drawnLayer;
    if (!layer) return;
    let areaM = 0, areaText = '—', perimText = '—', vertCount = '—';
    if (layer instanceof L.Circle) {
      const r  = layer.getRadius();
      areaM     = Math.PI * r * r;
      areaText  = _formatArea(areaM);
      perimText = (2 * Math.PI * r / 1000).toFixed(3) + ' km';
      vertCount = 'circle';
    } else {
      try {
        const gj  = layer.toGeoJSON();
        areaM     = turf.area(gj);
        areaText  = _formatArea(areaM);
        perimText = turf.length(turf.polygonToLine(gj), { units: 'kilometers' }).toFixed(3) + ' km';
        vertCount = layer.getLatLngs()[0]?.length ?? '—';
      } catch (e) { console.warn('[DrawModule] Turf error:', e.message); }
    }
    document.getElementById('val-area').textContent  = areaText;
    document.getElementById('val-perim').textContent = perimText;
    document.getElementById('val-verts').textContent = vertCount;
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
    let areaM = 0, areaText = '—', perimText = '—', vertCount = '—';
    if (layer instanceof L.Circle) {
      const r  = layer.getRadius();
      areaM     = Math.PI * r * r;
      areaText  = _formatArea(areaM);
      perimText = (2 * Math.PI * r / 1000).toFixed(3) + ' km';
      vertCount = 'circle';
    } else {
      try {
        const gj  = layer.toGeoJSON();
        areaM     = turf.area(gj);
        areaText  = _formatArea(areaM);
        perimText = turf.length(turf.polygonToLine(gj), { units: 'kilometers' }).toFixed(3) + ' km';
        vertCount = layer.getLatLngs()[0]?.length ?? '—';
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
    if (_editing) { _editHandler?.disable(); _editHandler = null; _editing = false; }
    stopCrossSectionDraw();
    clearCrossSectionLine();
    _drawnItems?.clearLayers();
    if (AppState.overlayLayer)    { AppState.map.removeLayer(AppState.overlayLayer);    AppState.overlayLayer    = null; }
    if (AppState.trueColorLayer)  { AppState.map.removeLayer(AppState.trueColorLayer);  AppState.trueColorLayer  = null; }
    if (AppState.falseColorLayer) { AppState.map.removeLayer(AppState.falseColorLayer); AppState.falseColorLayer = null; }
    AppState.drawnLayer = AppState.selectedIndex = AppState.lastResult = null;
    AppState.lastAreaM2 = null;

    document.getElementById('val-area').textContent  = '—';
    document.getElementById('val-perim').textContent = '—';
    document.getElementById('val-verts').textContent = '—';
    document.getElementById('plot-info-box').classList.add('hidden');
    document.getElementById('draw-hint').style.display = '';

    UIModule.hideSection('sec-indices');
    UIModule.hideSection('sec-results');
    UIModule.hideSection('sec-legend');
    UIModule.hideSection('sec-xsection');
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
      opacity:     AppState.overlayOpacity ?? 0.82,
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

  // ── OVERLAY OPACITY ───────────────────────────────────────
  // Called live from the Legend opacity slider (0–1).
  function setOverlayOpacity(value) {
    AppState.overlayOpacity = value;
    AppState.overlayLayer?.setOpacity(value);
  }

  // ── OVERLAY VISIBILITY ────────────────────────────────────
  // Show/hide the classification layer without losing it —
  // toggled from the Legend's "Show Classification Layer" checkbox.
  function setOverlayVisible(visible) {
    if (!AppState.overlayLayer) return;
    if (visible) {
      if (!AppState.map.hasLayer(AppState.overlayLayer)) AppState.overlayLayer.addTo(AppState.map);
    } else {
      AppState.map.removeLayer(AppState.overlayLayer);
    }
  }

  // ── TRUE / FALSE COLOUR GROUND-TRUTH LAYERS ───────────────
  // Stored on AppState so other modules (api.js) can clear/inspect them.
  // Both start hidden (off) — user opts in via the legend toggles.
  function renderGroundTruthLayers(trueColorUrl, falseColorUrl) {
    if (AppState.trueColorLayer)  { AppState.map.removeLayer(AppState.trueColorLayer);  AppState.trueColorLayer  = null; }
    if (AppState.falseColorLayer) { AppState.map.removeLayer(AppState.falseColorLayer); AppState.falseColorLayer = null; }
    MapModule.setBasemapOpacity(1); // reset dimming from any previous AOI's composite toggle

    if (trueColorUrl) {
      AppState.trueColorLayer = L.tileLayer(trueColorUrl, {
        maxZoom: 21,
        attribution: 'Google Earth Engine / Sentinel-2 (True Colour)',
      });
    }
    if (falseColorUrl) {
      AppState.falseColorLayer = L.tileLayer(falseColorUrl, {
        maxZoom: 21,
        attribution: 'Google Earth Engine / Sentinel-2 (False Colour)',
      });
    }
    // Both layers stay off the map until explicitly toggled on.
  }

  // NOTE: composite layers must NOT use bringToBack() — that sends them
  // below the basemap's own tile layer (which is opaque), making them
  // invisible no matter how "on" the toggle is. Instead we add them on
  // top, then re-assert the classification overlay's z-order above them
  // so it still wins if a user enables both at once.
  function setTrueColorVisible(visible) {
    if (!AppState.trueColorLayer) return;
    if (visible) {
      // Mutually exclusive with false colour — only one composite at a time.
      if (AppState.falseColorLayer && AppState.map.hasLayer(AppState.falseColorLayer)) {
        AppState.map.removeLayer(AppState.falseColorLayer);
      }
      if (!AppState.map.hasLayer(AppState.trueColorLayer)) AppState.trueColorLayer.addTo(AppState.map);
      AppState.trueColorLayer.bringToFront();
      AppState.overlayLayer?.bringToFront();
      if (AppState.drawnLayer?.bringToFront) AppState.drawnLayer.bringToFront();
      MapModule.setBasemapOpacity(0.15);
    } else {
      AppState.map.removeLayer(AppState.trueColorLayer);
      _restoreBasemapIfNoComposite();
    }
  }

  function setFalseColorVisible(visible) {
    if (!AppState.falseColorLayer) return;
    if (visible) {
      if (AppState.trueColorLayer && AppState.map.hasLayer(AppState.trueColorLayer)) {
        AppState.map.removeLayer(AppState.trueColorLayer);
      }
      if (!AppState.map.hasLayer(AppState.falseColorLayer)) AppState.falseColorLayer.addTo(AppState.map);
      AppState.falseColorLayer.bringToFront();
      AppState.overlayLayer?.bringToFront();
      if (AppState.drawnLayer?.bringToFront) AppState.drawnLayer.bringToFront();
      MapModule.setBasemapOpacity(0.15);
    } else {
      AppState.map.removeLayer(AppState.falseColorLayer);
      _restoreBasemapIfNoComposite();
    }
  }

  // Only restore full basemap opacity once neither composite is showing —
  // toggling true→false colour (or vice versa) should keep it dimmed.
  function _restoreBasemapIfNoComposite() {
    const trueShown  = AppState.trueColorLayer  && AppState.map.hasLayer(AppState.trueColorLayer);
    const falseShown = AppState.falseColorLayer && AppState.map.hasLayer(AppState.falseColorLayer);
    if (!trueShown && !falseShown) MapModule.setBasemapOpacity(1);
  }

  // ── CROSS-SECTION LINE TOOL ────────────────────────────────
  function startCrossSectionDraw() {
    _deactivateAll();
    if (_editing) { _editHandler?.disable(); _editHandler = null; _editing = false; }
    _xsActive = true;
    _xsHandler.enable();
  }
  function stopCrossSectionDraw() {
    _xsActive = false;
    _xsHandler.disable();
  }
  function clearCrossSectionLine() {
    if (_xsLineLayer) { AppState.map.removeLayer(_xsLineLayer); _xsLineLayer = null; }
    hideXsectionMarker();
  }
  // Returns [[lon, lat], ...] for the drawn cross-section line, or null.
  function getLineCoords() {
    if (!_xsLineLayer) return null;
    return _xsLineLayer.toGeoJSON().geometry.coordinates;
  }

  // ── CROSS-SECTION SCRUB MARKER ────────────────────────────
  // Moves a marker along the drawn red line to mirror whichever
  // sample point the user is hovering/scrolling over in the chart.
  function showXsectionMarker(lat, lng) {
    if (lat == null || lng == null) { hideXsectionMarker(); return; }
    if (!_xsMarker) {
      _xsMarker = L.circleMarker([lat, lng], {
        radius: 7,
        color: '#FFFFFF',
        weight: 2,
        fillColor: '#FF3B30',
        fillOpacity: 1,
      }).addTo(AppState.map);
    } else {
      _xsMarker.setLatLng([lat, lng]);
    }
  }
  function hideXsectionMarker() {
    if (_xsMarker) { AppState.map.removeLayer(_xsMarker); _xsMarker = null; }
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

  return {
    init, activate, clearAll, renderGEETileOverlay, getGeoJSONGeometry,
    toggleEdit, setOverlayOpacity, setOverlayVisible,
    renderGroundTruthLayers, setTrueColorVisible, setFalseColorVisible,
    startCrossSectionDraw, stopCrossSectionDraw, clearCrossSectionLine, getLineCoords,
    showXsectionMarker, hideXsectionMarker, refreshAreaDisplay,
  };
})();

document.addEventListener('DOMContentLoaded', () => {
  setTimeout(() => { DrawModule.init(); console.log('[draw.js] DrawModule ready.'); }, 60);
});


