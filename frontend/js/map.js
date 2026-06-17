/* =============================================
   AgriGIS – Leaflet Map Manager
   ============================================= */

const MapManager = (() => {
  let map = null;
  let drawnItems = null;
  let currentOverlay = null;
  let currentGeometry = null;
  let currentBounds = null;
  let searchMarker = null;

  const BASE_LAYERS = {
    "OpenStreetMap": L.tileLayer(
      "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
      { attribution: "© OpenStreetMap contributors", maxZoom: 19 }
    ),
    "Satellite (ESRI)": L.tileLayer(
      "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
      { attribution: "© Esri, USDA, USGS", maxZoom: 19 }
    ),
    "Terrain": L.tileLayer(
      "https://stamen-tiles-{s}.a.ssl.fastly.net/terrain/{z}/{x}/{y}.jpg",
      { attribution: "Map tiles by Stamen Design", maxZoom: 18 }
    ),
  };

  function init(onPlotDrawn) {
    map = L.map("map", {
      center: [20.5937, 78.9629],
      zoom: 5,
      zoomControl: true,
    });

    BASE_LAYERS["Satellite (ESRI)"].addTo(map);

    drawnItems = new L.FeatureGroup().addTo(map);

    const drawControl = new L.Control.Draw({
      position: "topright",
      draw: {
        polygon: {
          allowIntersection: false,
          showArea: true,
          shapeOptions: {
            color: "#52b788",
            weight: 2,
            fillOpacity: 0.15,
          },
          tooltip: { start: "Click to start drawing your plot", cont: "Click to continue — Double-click to finish", end: "Click first point to close" },
        },
        rectangle: {
          shapeOptions: {
            color: "#52b788",
            weight: 2,
            fillOpacity: 0.15,
          },
        },
        circle: {
          shapeOptions: { color: "#52b788", weight: 2, fillOpacity: 0.15 },
        },
        circlemarker: false,
        polyline: false,
        marker: false,
      },
      edit: {
        featureGroup: drawnItems,
        remove: true,
      },
    });

    map.addControl(drawControl);
    L.control.layers(BASE_LAYERS, {}, { position: "topright" }).addTo(map);

    map.on(L.Draw.Event.CREATED, function (e) {
      drawnItems.clearLayers();
      drawnItems.addLayer(e.layer);
      currentGeometry = e.layer.toGeoJSON().geometry;

      if (e.layerType === "circle") {
        const center = e.layer.getLatLng();
        const radius = e.layer.getRadius();
        currentGeometry = circleToPolygon(center, radius);
      }

      currentBounds = e.layer.getBounds();

      const area = calculateArea(currentBounds);
      updatePlotStatus(`Plot drawn — ~${area}`);

      if (typeof onPlotDrawn === "function") {
        onPlotDrawn(currentGeometry, currentBounds);
      }

      setMapInfo("Plot drawn! Complete registration in the sidebar.");
    });

    map.on(L.Draw.Event.DELETED, function () {
      currentGeometry = null;
      currentBounds = null;
      currentOverlay && map.removeLayer(currentOverlay);
      currentOverlay = null;
      updatePlotStatus("No plot drawn yet");
      setMapInfo("Plot removed. Draw a new plot using the toolbar.");
    });

    map.on(L.Draw.Event.EDITED, function (e) {
      e.layers.eachLayer(function (layer) {
        currentGeometry = layer.toGeoJSON().geometry;
        currentBounds = layer.getBounds();
      });
    });
  }

  function circleToPolygon(center, radius, points = 64) {
    const coords = [];
    for (let i = 0; i < points; i++) {
      const angle = (i * 360) / points;
      const rad = (angle * Math.PI) / 180;
      const lat = center.lat + (radius / 111320) * Math.cos(rad);
      const lng = center.lng + (radius / (111320 * Math.cos((center.lat * Math.PI) / 180))) * Math.sin(rad);
      coords.push([lng, lat]);
    }
    coords.push(coords[0]);
    return { type: "Polygon", coordinates: [coords] };
  }

  function calculateArea(bounds) {
    if (!bounds) return "unknown";
    const sw = bounds.getSouthWest();
    const ne = bounds.getNorthEast();
    const widthKm = ((ne.lng - sw.lng) * Math.PI * 6371 * Math.cos((sw.lat * Math.PI) / 180)) / 180;
    const heightKm = ((ne.lat - sw.lat) * Math.PI * 6371) / 180;
    const area = Math.abs(widthKm * heightKm);
    if (area < 0.01) return `${(area * 10000).toFixed(0)} m²`;
    if (area < 1) return `${(area * 100).toFixed(1)} ha`;
    return `${area.toFixed(2)} km²`;
  }

  function flyTo(lat, lng, zoom = 14) {
    if (searchMarker) map.removeLayer(searchMarker);
    searchMarker = L.marker([lat, lng], {
      icon: L.divIcon({
        className: "",
        html: `<div style="background:#52b788;border-radius:50%;width:14px;height:14px;border:2px solid white;box-shadow:0 0 8px rgba(82,183,136,0.8)"></div>`,
        iconSize: [14, 14],
        iconAnchor: [7, 7],
      }),
    }).addTo(map);
    map.flyTo([lat, lng], zoom, { duration: 1.2 });
  }

  function setIndexOverlay(imageData, bounds) {
    if (currentOverlay) map.removeLayer(currentOverlay);
    const leafletBounds = L.latLngBounds(
      [bounds.south, bounds.west],
      [bounds.north, bounds.east]
    );
    currentOverlay = L.imageOverlay(imageData, leafletBounds, {
      opacity: 0.85,
      interactive: false,
    }).addTo(map);
    map.fitBounds(leafletBounds, { padding: [40, 40] });
  }

  function clearOverlay() {
    if (currentOverlay) {
      map.removeLayer(currentOverlay);
      currentOverlay = null;
    }
  }

  function fitToPlot() {
    if (currentBounds) map.fitBounds(currentBounds, { padding: [60, 60] });
  }

  function getGeometry() { return currentGeometry; }
  function getBounds() { return currentBounds; }

  function updatePlotStatus(text) {
    const el = document.getElementById("plotStatus");
    const preview = document.getElementById("plotPreview");
    if (el) el.textContent = text;
    if (preview) {
      if (currentGeometry) preview.classList.add("ready");
      else preview.classList.remove("ready");
    }
  }

  function setMapInfo(text) {
    const el = document.getElementById("mapInfoText");
    if (el) el.textContent = text;
  }

  return {
    init,
    flyTo,
    setIndexOverlay,
    clearOverlay,
    fitToPlot,
    getGeometry,
    getBounds,
    setMapInfo,
  };
})();
