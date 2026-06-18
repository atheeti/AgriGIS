/* ============================================================
   AgriGIS Frontend  |  js/ui.js
   All UI state management: buttons, results, legend,
   histogram, loading overlay, toasts, PDF report, GeoJSON export.
   ============================================================ */

const UIModule = (() => {

  // Badge colour map: classification label → [bg, text]
  const STATUS_COLORS = {
    'Dense Vegetation':['#1a9850','#d9ef8b'], 'Healthy Crop':['#52B788','#d9f0a3'],
    'Very Dense':['#1a9850','#d9ef8b'],        'High Chlorophyll':['#238443','#d9f0a3'],
    'High Biomass':['#52B788','#d9ef8b'],      'Very Moist':['#01665e','#c7eae5'],
    'Moist':['#35978f','#c7eae5'],             'Healthy':['#52B788','#d9f0a3'],
    'Healthy/Dense':['#52B788','#d9f0a3'],     'Good':['#52B788','#d9f0a3'],
    'Very High':['#238443','#d9f0a3'],         'Moderate Growth':['#C9A84C','#ffe4a0'],
    'Moderate':['#C9A84C','#ffe4a0'],          'Normal':['#C9A84C','#ffe4a0'],
    'Normal Moisture':['#C9A84C','#ffe4a0'],   'Unburned':['#C9A84C','#ffe4a0'],
    'Low':['#d4a017','#fff3cd'],               'Sparse Vegetation':['#d4a017','#fff3cd'],
    'Sparse–Moderate':['#d4a017','#fff3cd'],   'Low Biomass':['#d4a017','#fff3cd'],
    'Low Chlorophyll':['#d4a017','#fff3cd'],   'Low Severity':['#d4a017','#fff3cd'],
    'Dry':['#bf812d','#f6e8c3'],               'Mild Stress':['#e67e22','#fdebd0'],
    'Bare Soil':['#a0522d','#f5deb3'],         'Very Dry':['#c0392b','#ffd0cc'],
    'Very Dry Land':['#c0392b','#ffd0cc'],     'Stressed':['#c0392b','#ffd0cc'],
    'High Burn Severity':['#7b0000','#ffd0cc'],'Moderate Burn':['#c0392b','#ffd0cc'],
    'Water / Non-Veg':['#2980b9','#aed6f1'],   'Water Body':['#2980b9','#aed6f1'],
    'Open Water':['#1a5276','#aed6f1'],        'Wet Soil':['#35978f','#c7eae5'],
    'Moist Soil':['#35978f','#c7eae5'],        'Soil':['#bf812d','#f6e8c3'],
    'Dry Land':['#c0392b','#ffd0cc'],          'No Vegetation':['#888','#eee'],
  };

  // ── BUILD INDEX BUTTONS ───────────────────────────────────
  function buildIndexButtons() {
    const grid = document.getElementById('index-grid');
    if (!grid) return;
    grid.innerHTML = '';
    Object.entries(INDICES).forEach(([key, cfg]) => {
      const btn = document.createElement('button');
      btn.className = 'index-btn'; btn.id = `ibtn-${key}`; btn.title = cfg.full;
      btn.innerHTML = `
        <div class="index-dot" style="background:${cfg.color}"></div>
        <div class="index-btn-name">${key}</div>
        <div class="index-btn-abbr">${cfg.full.split(' ').slice(0,2).join(' ')}</div>
      `;
      btn.addEventListener('mouseenter', () => { if (!btn.classList.contains('selected')) btn.style.borderColor = cfg.color + 'AA'; });
      btn.addEventListener('mouseleave', () => { if (!btn.classList.contains('selected')) btn.style.borderColor = ''; });
      btn.addEventListener('click', () => _selectIndex(key));
      grid.appendChild(btn);
    });
  }

  function _selectIndex(key) {
    document.querySelectorAll('.index-btn').forEach(b => { b.classList.remove('selected'); b.style.borderColor = ''; });
    const btn = document.getElementById(`ibtn-${key}`);
    if (btn) { btn.classList.add('selected'); btn.style.borderColor = INDICES[key].color; }
    AppState.selectedIndex = key;
    showToast(`${key} selected — click Run on Earth Engine`, 'info');
  }

  // ── SHOW RESULT ───────────────────────────────────────────
  function showResult(key, cfg, result) {
    const classification = cfg.classify(result.mean);
    const [dmin, dmax]   = cfg.disp;

    document.getElementById('res-name').textContent     = key;
    document.getElementById('res-fullname').textContent = cfg.full;
    document.getElementById('res-formula').textContent  = cfg.formula;
    document.getElementById('res-mean').textContent     = result.mean.toFixed(4);
    document.getElementById('res-min').textContent      = result.min.toFixed(4);
    document.getElementById('res-max').textContent      = result.max.toFixed(4);
    document.getElementById('res-std').textContent      = result.std.toFixed(4);
    document.getElementById('res-sentinel-date').textContent = result.sentinelDate;

    // Soil-strip glow (signature element)
    const [r, g, b] = valueToRGB(result.mean, cfg.stops, dmin, dmax);
    const hex = `rgb(${r},${g},${b})`;
    document.getElementById('soil-strip').style.cssText =
      `background:${hex};box-shadow:0 0 16px ${hex}`;
    document.getElementById('res-mean').style.color = hex;

    // Status badge
    const badge  = document.getElementById('res-status');
    const colors = STATUS_COLORS[classification] || ['#7FA98B', '#2D6A4F'];
    badge.textContent = classification;
    badge.style.background   = colors[0] + '28';
    badge.style.color        = colors[0];
    badge.style.border       = `1px solid ${colors[0]}66`;

    showSection('sec-results');
    showSection('sec-legend');
    showSection('sec-download');
    setStepChip('chip-2', 'done');
    setStepChip('chip-3', 'active');

    _buildLegend(cfg, result.mean);
    _buildHistogram(cfg, result.histogram);
    document.getElementById('sec-results').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  // ── LEGEND ────────────────────────────────────────────────
  function _buildLegend(cfg, meanValue) {
    const [dmin, dmax] = cfg.disp;
    document.getElementById('legend-gradient-bar').style.background =
      `linear-gradient(to right,${cfg.stops.join(',')})`;
    document.getElementById('legend-bar-labels').innerHTML =
      `<span>${dmin.toFixed(2)}</span><span>${((dmin+dmax)/2).toFixed(2)}</span><span>${dmax.toFixed(2)}</span>`;

    const list = document.getElementById('legend-class-list');
    list.innerHTML = '';
    cfg.classes.forEach(cls => {
      const active = meanValue >= cls.range[0] && meanValue < cls.range[1];
      const row    = document.createElement('div');
      row.className = `legend-class-row${active ? ' active-class' : ''}`;
      row.innerHTML = `
        <div class="legend-swatch" style="background:${cls.color}"></div>
        <div class="legend-class-label">${cls.label}</div>
        <div class="legend-class-range">${cls.range[0]} – ${cls.range[1]}</div>
      `;
      list.appendChild(row);
    });
  }

  // ── HISTOGRAM ─────────────────────────────────────────────
  function _buildHistogram(cfg, bins) {
    const canvas = document.getElementById('histogram-chart');
    if (!canvas || !bins?.length) return;
    if (AppState.histChart) { AppState.histChart.destroy(); AppState.histChart = null; }

    const [dmin, dmax] = cfg.disp;
    const colors = bins.map(b => {
      const [r, g, bv] = valueToRGB(b.center, cfg.stops, dmin, dmax);
      return `rgba(${r},${g},${bv},0.82)`;
    });

    AppState.histChart = new Chart(canvas, {
      type: 'bar',
      data: {
        labels:   bins.map(b => b.center.toFixed(2)),
        datasets: [{
          data:              bins.map(b => b.count),
          backgroundColor:   colors,
          borderColor:       colors.map(c => c.replace('0.82', '1')),
          borderWidth:       0.5,
          borderRadius:      2,
          categoryPercentage:0.92,
          barPercentage:     0.95,
        }],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: '#1B4332', titleColor: '#B7E4C7', bodyColor: '#B7E4C7',
            borderColor: 'rgba(82,183,136,0.3)', borderWidth: 1,
            callbacks: { title: i => `Value: ${i[0].label}`, label: i => `Pixels: ${Math.round(i.raw)}` },
          },
        },
        scales: {
          x: { ticks: { color: '#7FA98B', font: { family: "'JetBrains Mono',monospace", size: 8 }, maxRotation: 0, maxTicksLimit: 6 }, grid: { color: 'rgba(82,183,136,0.05)' } },
          y: { ticks: { color: '#7FA98B', font: { family: "'JetBrains Mono',monospace", size: 8 }, maxTicksLimit: 4 }, grid: { color: 'rgba(82,183,136,0.07)' } },
        },
      },
    });
  }

  // ── RESET ─────────────────────────────────────────────────
  function resetAnalysis() {
    if (AppState.overlayLayer) { AppState.map.removeLayer(AppState.overlayLayer); AppState.overlayLayer = null; }
    if (AppState.drawnLayer?.setStyle) {
      AppState.drawnLayer.setStyle({ color:'#52B788', weight:2.5, fillColor:'#52B788', fillOpacity:0.12, dashArray:'7 4' });
    }
    hideSection('sec-results'); hideSection('sec-legend'); hideSection('sec-download');
    setStepChip('chip-3', ''); setStepChip('chip-2', 'active');
    document.querySelectorAll('.index-btn').forEach(b => { b.classList.remove('selected'); b.style.borderColor = ''; });
    AppState.selectedIndex = null;
    document.getElementById('sentinel-date-display').textContent = 'No scene loaded';
    showToast('Ready for new analysis', 'info');
  }

  // ── API STATUS PILL ────────────────────────────────────────
  function setAPIStatus(state, text) {
    const pill = document.getElementById('api-status-pill');
    const span = document.getElementById('api-status-text');
    pill.className = `api-status-pill${state ? ' ' + state : ''}`;
    span.textContent = text;
  }

  // ── LOADING ───────────────────────────────────────────────
  const _STAGES = [
    { title: 'Sending polygon to Earth Engine…',  sub: 'POST /api/calculate' },
    { title: 'Filtering Sentinel-2 scenes…',      sub: 'Date range + cloud cover filter' },
    { title: 'Masking cloudy pixels (QA60)…',     sub: 'Bits 10 & 11 bitmask' },
    { title: 'Computing spectral index…',         sub: 'Running formula on GEE servers' },
    { title: 'Reducing region statistics…',       sub: 'mean · min · max · stdDev' },
    { title: 'Building histogram (20 bins)…',     sub: 'fixedHistogram reducer' },
    { title: 'Generating tile URL…',              sub: 'getMapId → Leaflet overlay' },
  ];
  let _stTimer = null, _stIdx = 0;

  function showLoading(title, sub) {
    AppState.isLoading = true;
    document.getElementById('loading-overlay').classList.add('show');
    _stIdx = 0;
    updateLoadingText(title || _STAGES[0].title, sub || _STAGES[0].sub);
    _stTimer = setInterval(() => {
      _stIdx = (_stIdx + 1) % _STAGES.length;
      updateLoadingText(_STAGES[_stIdx].title, _STAGES[_stIdx].sub);
    }, 900);
  }
  function hideLoading() {
    AppState.isLoading = false;
    document.getElementById('loading-overlay').classList.remove('show');
    clearInterval(_stTimer); _stTimer = null;
  }
  function updateLoadingText(title, sub) {
    document.getElementById('loading-title').textContent = title;
    document.getElementById('loading-sub').textContent   = sub;
  }

  // ── TOASTS ────────────────────────────────────────────────
  const _ICONS = { success: 'fa-check-circle', error: 'fa-exclamation-circle', info: 'fa-info-circle' };
  function showToast(msg, type = 'info') {
    const el = document.createElement('div');
    el.className = `toast-msg ${type}`;
    el.innerHTML = `<i class="fas ${_ICONS[type] || _ICONS.info}"></i> ${msg}`;
    document.getElementById('toast-container').appendChild(el);
    setTimeout(() => {
      el.classList.add('fade-out');
      setTimeout(() => el.parentNode?.removeChild(el), 350);
    }, 3800);
  }

  // ── MAP HINT ──────────────────────────────────────────────
  let _hTimer = null;
  function setMapHint(text, autoFade = true) {
    document.getElementById('map-hint-text').textContent = text;
    document.getElementById('map-hint').classList.remove('fade-out');
    clearTimeout(_hTimer);
    if (autoFade) _hTimer = setTimeout(() => document.getElementById('map-hint').classList.add('fade-out'), 4500);
  }

  // ── SECTION HELPERS ───────────────────────────────────────
  function showSection(id) { const el = document.getElementById(id); if (!el) return; el.classList.remove('hidden'); el.classList.add('slide-in'); }
  function hideSection(id) { const el = document.getElementById(id); if (!el) return; el.classList.add('hidden'); el.classList.remove('slide-in'); }
  function setStepChip(id, state) { const el = document.getElementById(id); if (!el) return; el.classList.remove('active', 'done'); if (state) el.classList.add(state); }

  // ── PDF REPORT ────────────────────────────────────────────
  function downloadReport() {
    const r = AppState.lastResult;
    if (!r) { showToast('No results to export', 'error'); return; }
    const today  = new Date().toLocaleDateString('en-IN', { year:'numeric', month:'long', day:'numeric' });
    const sc     = (STATUS_COLORS[r.cfg.classify(r.mean)] || ['#52B788'])[0];
    const html = `<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><title>AgriGIS Report — ${r.key}</title>
<style>@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&family=Inter:wght@400;500&family=JetBrains+Mono:wght@400;600&display=swap');
*{box-sizing:border-box;margin:0;padding:0}body{font-family:'Inter',sans-serif;background:#fff;color:#1a1a1a;padding:40px;max-width:760px;margin:auto}
.hdr{background:#0B1F12;padding:18px 22px;border-radius:10px;margin-bottom:22px}.hdr h1{font-family:'Space Grotesk',sans-serif;font-size:22px;color:#fff;margin-bottom:3px}.hdr p{font-size:11.5px;color:#7FA98B}
.gee{display:inline-flex;align-items:center;gap:5px;margin-top:5px;font-size:10px;color:#4285F4;border:1px solid rgba(66,133,244,.3);padding:2px 8px;border-radius:20px}
.sec{font-family:'Space Grotesk',sans-serif;font-size:10px;font-weight:700;letter-spacing:1.2px;text-transform:uppercase;color:#52B788;border-bottom:1.5px solid #e8f5ee;padding-bottom:5px;margin:18px 0 10px}
.idx{font-family:'Space Grotesk',sans-serif;font-size:30px;font-weight:700;color:#0B1F12}.idxf{font-size:13px;color:#666;margin:3px 0 5px}.fml{font-family:'JetBrains Mono',monospace;font-size:10.5px;color:#888;background:#f5f5f5;padding:4px 9px;border-radius:5px;display:inline-block;margin-bottom:12px}
.badge{display:inline-block;padding:4px 12px;border-radius:20px;font-size:11px;font-weight:700;color:#fff;background:${sc};margin-bottom:14px}
.g4{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:14px}.box{border:1.5px solid #e8f5ee;border-radius:7px;padding:8px;text-align:center}.bl{font-size:9px;text-transform:uppercase;color:#999;margin-bottom:2px}.bv{font-family:'JetBrains Mono',monospace;font-size:16px;font-weight:600;color:#1B4332}
.grad{height:13px;border-radius:6px;background:linear-gradient(to right,${r.cfg.stops.join(',')});margin-bottom:4px}.gl{display:flex;justify-content:space-between;font-family:'JetBrains Mono',monospace;font-size:9px;color:#888;margin-bottom:12px}
.cr{display:flex;align-items:center;gap:7px;padding:4px 7px;border-radius:5px;margin-bottom:3px}.cr.a{background:#f0f9f4;border:1px solid #c3e6d3}.sw{width:10px;height:10px;border-radius:3px;flex-shrink:0}.cl{font-size:11px;flex:1}.cv{font-family:'JetBrains Mono',monospace;font-size:9.5px;color:#888}
.ft{margin-top:24px;padding-top:12px;border-top:1px solid #eee;font-size:10px;color:#aaa;display:flex;justify-content:space-between}
@media print{body{padding:20px}}</style></head><body>
<div class="hdr"><h1>🌿 AgriGIS — Crop Health Report</h1><p>Generated: ${today} · Sentinel-2: ${r.scene_date||r.sentinelDate||'—'}</p><div class="gee">⬤ Google Earth Engine · COPERNICUS/S2_SR_HARMONIZED · 10 m</div></div>
<div class="sec">Index</div>
<div class="idx">${r.key}</div><div class="idxf">${r.cfg.full}</div><div class="fml">${r.cfg.formula}</div><br><span class="badge">${r.cfg.classify(r.mean)}</span>
<div class="g4"><div class="box"><div class="bl">Mean</div><div class="bv">${r.mean.toFixed(4)}</div></div><div class="box"><div class="bl">Min</div><div class="bv">${r.min.toFixed(4)}</div></div><div class="box"><div class="bl">Max</div><div class="bv">${r.max.toFixed(4)}</div></div><div class="box"><div class="bl">Std Dev</div><div class="bv">${r.std.toFixed(4)}</div></div></div>
<div class="sec">Scale</div><div class="grad"></div><div class="gl"><span>${r.cfg.disp[0]}</span><span>${((r.cfg.disp[0]+r.cfg.disp[1])/2).toFixed(2)}</span><span>${r.cfg.disp[1]}</span></div>
<div class="sec">Classification</div>
${r.cfg.classes.map(c=>{const a=r.mean>=c.range[0]&&r.mean<c.range[1];return`<div class="cr${a?' a':''}"><div class="sw" style="background:${c.color}"></div><div class="cl">${c.label}${a?' ← Current':''}</div><div class="cv">${c.range[0]}–${c.range[1]}</div></div>`;}).join('')}
<div class="ft"><span>AgriGIS — Crop Health Intelligence</span><span>Google Earth Engine · Sentinel-2</span></div>
<script>window.onload=()=>window.print()<\/script></body></html>`;
    window.open(URL.createObjectURL(new Blob([html], { type: 'text/html' })), '_blank');
    showToast('PDF report opened — press Ctrl+P to print', 'success');
  }

  // ── GEOJSON EXPORT ────────────────────────────────────────
  function downloadGeoJSON() {
    if (!AppState.drawnLayer) { showToast('Draw a plot first', 'error'); return; }
    let gj; try { gj = AppState.drawnLayer.toGeoJSON?.(); } catch { showToast('Cannot export this shape', 'error'); return; }
    if (!gj) { showToast('Circles cannot be exported as GeoJSON', 'error'); return; }
    const r = AppState.lastResult;
    if (r) gj.properties = { index: r.key, mean: r.mean, min: r.min, max: r.max, std: r.std, classification: r.cfg.classify(r.mean), scene_date: r.scene_date || r.sentinelDate, source: 'GEE COPERNICUS/S2_SR_HARMONIZED', exported: new Date().toISOString() };
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([JSON.stringify(gj, null, 2)], { type: 'application/json' }));
    a.download = `agrigis_${r?.key || 'plot'}_${Date.now()}.geojson`;
    a.click();
    showToast('GeoJSON exported', 'success');
  }

  // ── INIT ──────────────────────────────────────────────────
  function init() {
    buildIndexButtons();
    setTimeout(() => setMapHint('Search a location and draw your plot to begin', true), 300);
    console.log('[UIModule] Initialised.');
  }

  return {
    init, buildIndexButtons, showResult, resetAnalysis,
    showLoading, hideLoading, updateLoadingText,
    setAPIStatus, showToast, setMapHint,
    showSection, hideSection, setStepChip,
    downloadReport, downloadGeoJSON,
  };
})();

document.addEventListener('DOMContentLoaded', () => {
  UIModule.init();
  console.log('[ui.js] UIModule initialised.');
});
