import {
  getColorFromRank,
  getCustomIcon,
  createClusterCustomIcon,
  poiConfigs,
  createMarker,
  createPolygon,
  createOptimalPopup,
} from "./utils.js";


let map = L.map("map").setView([44.4949, 11.3426], 13);
//raggio
let neighborhoodRadius = 500;
//cerchi per mostrare il radius per i marker
let circles = {};
window.optimalPositionsLayer = L.layerGroup().addTo(map);

L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  attribution: "© OpenStreetMap contributors",
}).addTo(map);

// centra
function recenterMap() {
  map.setView([44.4949, 11.3426], 13);
}

/////////////// GESTIONE POI ///////////

//cluster
function createMarkerClusterGroup() {
  return L.markerClusterGroup({
    showCoverageOnHover: false,
    zoomToBoundsOnClick: true,
    spiderfyOnMaxZoom: true,
    removeOutsideVisibleBounds: true,
    iconCreateFunction: createClusterCustomIcon,
  });
}

const poiTypes = [
  "aree_verdi",
  "parcheggi",
  "fermate_bus",
  "stazioni_ferroviarie",
  "scuole",
  "cinema",
  "ospedali",
  "farmacia",
  "colonnina_elettrica",
  "biblioteca",
];

const poiLayers = poiTypes.reduce((layers, type) => {
  layers[type] = createMarkerClusterGroup();
  return layers;
}, {});


// filtri salvati
let savedFilters = {
  distanceEnabled: false,
  travelMode: 'driving',
  travelTime: 10
};

//da richiamare nell'html per gestire i toggle
let popupContent = `
    <div class="poi-popup">
        <h3>${name}</h3>
        ${savedFilters.distanceEnabled && poi.travel_time ? 
            `<p class="text-sm mt-2">⏱️ ${Math.round(poi.travel_time)} minuti</p>` 
            : ''}
    </div>
`;

//slider geofence
document.getElementById("radiusSlider").addEventListener("input", function (e) {
  neighborhoodRadius = parseInt(e.target.value);
  document.getElementById("radiusValue").textContent = neighborhoodRadius;
  updateNeighborhoodCircles();
  sendRadiusToBackend(neighborhoodRadius);
});

function updateNeighborhoodCircles() {
  Object.values(circles).forEach((circle) => {
    circle.setRadius(neighborhoodRadius);
  });
}

function sendRadiusToBackend(radius) {
  fetch("/set_radius", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ radius: radius }),
  })
    .then((response) => response.json())
    .then((data) => {
      console.log("Success:", data);
    })
    .catch((error) => {
      console.error("Error:", error);
    });
}

//carica marker e poligoni
function loadAllGeofences() {
  fetch("/get_all_geofences")
      .then((response) => {
          if (response.status === 404) {
              throw new Error("No questionnaires found");
          }
          if (!response.ok) {
              throw new Error(`HTTP error! status: ${response.status}`);
          }
          return response.json();
      })
      .then((data) => {
          console.log("Received geofences data:", data);
          
          // elimina layer esistenti
          drawnItems.clearLayers();
          Object.values(circles).forEach((circle) => map.removeLayer(circle));
          circles = {};

          // r
          window.geofencesLayer = window.geofencesLayer || L.layerGroup().addTo(map);
          window.geofencesLayer.clearLayers();

          data.forEach((geofenceData) => {
              console.log("Processing geofence:", geofenceData);
              
              if (geofenceData.type === "marker") {
                  const color = getColorFromRank(geofenceData.rank);
                  console.log(`Creating marker with rank ${geofenceData.rank}, color: ${color}`);
                  
                  createMarker(
                      map,
                      drawnItems,
                      circles,
                      geofenceData,
                      color,
                      neighborhoodRadius
                  );
              } 
              else if (geofenceData.type === "polygon") {
                  const color = getColorFromRank(geofenceData.rank);
                  console.log(`Creating polygon with rank ${geofenceData.rank}, color: ${color}`);
                  
                  createPolygon(
                      map,
                      geofenceData,
                      color,
                      window.geofencesLayer
                  );
              }
          });

        
          if (data.length > 0) {
              const bounds = L.featureGroup([drawnItems, window.geofencesLayer])
                  .getBounds();
              map.fitBounds(bounds);
          }
      })
      .catch((error) => {
          console.error("Error loading geofences:", error);
          if (error.message === "No questionnaires found") {
              alert("Completa prima il questionario per visualizzare i dati.");
          }
      });
}

document.addEventListener("DOMContentLoaded", loadAllGeofences);

//crea popup per marker/poligono
function createGeofencePopup(geofenceId, isMarker = true) {
  const popupContent = document.createElement("div");
  popupContent.className = "p-2";

  const idText = document.createElement("b");
  idText.className = "text-dark-200 mb-2 block";
  idText.textContent = `${isMarker ? "Marker" : "Geofence"} ID: ${geofenceId}`;
  popupContent.appendChild(idText);

  const deleteButton = document.createElement("button");
  deleteButton.className =
    "bg-red-500 hover:bg-red-600 text-white px-3 py-1 rounded flex items-center gap-2 mb-3 w-full";
  deleteButton.innerHTML = `<span>🗑️</span> Elimina ${
    isMarker ? "Marker" : "Geofence"
  }`;
  deleteButton.addEventListener("click", () =>
    window.deleteGeofence(geofenceId)
  );
  popupContent.appendChild(deleteButton);

  if (isMarker) {
    const priceContainer = document.createElement("div");
    priceContainer.className = "space-y-2";

    const priceLabel = document.createElement("label");
    priceLabel.className = "text-dark-200 block";
    priceLabel.textContent = "Prezzo:";
    priceContainer.appendChild(priceLabel);

    const priceInput = document.createElement("input");
    priceInput.type = "number";
    priceInput.id = `priceInput-${geofenceId}`;
    priceInput.placeholder = "Inserisci il prezzo";
    priceInput.className =
      "bg-gray-700 text-gray-200 rounded px-2 py-1 w-full border border-gray-600 focus:border-blue-500 focus:outline-none";
    priceContainer.appendChild(priceInput);

    const addPriceButton = document.createElement("button");
    addPriceButton.className =
      "bg-green-600 hover:bg-green-700 text-white px-3 py-1 rounded flex items-center gap-2 w-full";
    addPriceButton.innerHTML = "<span>💰</span> Aggiungi Prezzo";
    addPriceButton.addEventListener("click", () =>
      window.addMarkerPrice(geofenceId)
    );
    priceContainer.appendChild(addPriceButton);

    popupContent.appendChild(priceContainer);
  }

  return popupContent;
}

window.createGeofencePopup = createGeofencePopup;

//rimuove un singolo geofence dalla mappa e dal db
window.deleteGeofence = function (geofenceId) {
  console.log("Delete geofence with ID:", geofenceId);
  fetch(`/delete-geofence/${geofenceId}`, {
    method: "DELETE",
  })
    .then((data) => {
      console.log("Geofence eliminato:", data);
      removeGeofenceFromMap(geofenceId);
      updateMoranIndex();
    })
};

//aggiunge il prezzo ad un marker/poligono
window.addMarkerPrice = function (geofenceId) {
  const priceInput = document.getElementById(`priceInput-${geofenceId}`);

  const price = parseFloat(priceInput.value);

  if (!price || price <= 0) {
    alert("Inserisci un prezzo valido.");
    return;
  }

  fetch("/addMarkerPrice", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      geofenceId: geofenceId,
      price: price,
    }),
  })
    .then((response) => response.json())
    .then((data) => {
      updateMoranIndex();
    })
    .catch((error) => {
      console.error("Errore durante l'aggiunta del prezzo:", error);
      alert("Errore durante l'aggiunta del prezzo");
    });
};

map.on(L.Draw.Event.CREATED, function (e) {
  let layer = e.layer;

  if (layer instanceof L.Marker) {
    const latlng = layer.getLatLng();
    saveGeofenceToDatabase([{ lat: latlng.lat, lng: latlng.lng }], null)
      .then((response) => response.json())
      .then((data) => {
        loadAllGeofences();
      })
      .catch((error) => console.error("Errore nel salvare il marker:", error));
  } else if (layer instanceof L.Polygon) {
    const coordinates = layer
      .getLatLngs()[0]
      .map((latlng) => ({ lat: latlng.lat, lng: latlng.lng }));
    saveGeofenceToDatabase(null, [coordinates])
      .then((response) => response.json())
      .then((data) => {
        loadAllGeofences();
      })
      .catch((error) =>
        console.error("Errore nel salvare il geofence:", error)
      );
  }
});

//aggiungi un geofence al db, gestisce sia una lista che un singolo marker/poligono
function saveGeofenceToDatabase(markers, geofences) {
  let data;
  if (markers && markers.length === 1) {
    data = { marker: markers[0] };
  } else if (geofences && geofences.length > 0) {
    data = { geofence: geofences[0] };
  } else {
    console.error("Nessun marker o geofence valido da salvare.");
    return Promise.reject("Dati non validi");
  }

  return fetch("/save-geofence", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });
}

//rimuovi tutti i geofence dalla mappa e dal db
function deleteAllGeofences() {
  fetch("/delete-all-geofences", {
      method: "POST",
  })
  .then((response) => {
      if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
      }
      return response.json();
  })
  .then((data) => {
      console.log("Cancellazione geofence completata:", data);
      
      //pulisci tutti i layer
      drawnItems.clearLayers();
      
      // rimuovi i cerchi
      Object.values(circles).forEach((circle) => map.removeLayer(circle));
      circles = {};
      
      //  rimuove dal db
      if (typeof databaseMarkers !== 'undefined' && databaseMarkers) {
          databaseMarkers.clearLayers();
      }
      
      // pulisci geofence
      if (window.geofencesLayer) {
          window.geofencesLayer.clearLayers();
      }
      
      //aggiorna indice moran
      if (typeof updateMoranIndex === 'function') {
          updateMoranIndex();
      }
      
      alert("Tutti i geofence sono stati cancellati con successo");
  })
  .catch((error) => {
      console.error("Errore nella cancellazione dei geofence:", error);
      alert("Si è verificato un errore durante la cancellazione dei geofence");
  });
}

function removeGeofenceFromMap(geofenceId) {
  console.log("Removing geofence from map:", geofenceId);
  // Rimuovi il marker 
  drawnItems.eachLayer(function (layer) {
    if (layer.geofenceId === geofenceId) {
      drawnItems.removeLayer(layer);
      map.removeLayer(layer);
    }
  });

  // rimuovi il cerchio associato
  if (circles[geofenceId]) {
    map.removeLayer(circles[geofenceId]);
    delete circles[geofenceId];
  }

  //rimuovi il poligono
  if (window.geofencesLayer) {
    window.geofencesLayer.eachLayer(function (layer) {
      if (layer.geofenceId === geofenceId) {
        window.geofencesLayer.removeLayer(layer);
      }
    });
  }

  databaseMarkers.eachLayer(function (layer) {
    if (layer.geofenceId === geofenceId) {
      databaseMarkers.removeLayer(layer);
    }
  });
}

////controls

var recenterControl = L.Control.extend({
  options: {
    position: "topright",
  },
  onAdd: function (map) {
    var container = L.DomUtil.create("div", "leaflet-control-custom");
    container.innerHTML = "📍";
    container.style.backgroundColor = "white";
    container.style.width = "30px";
    container.style.height = "30px";
    container.style.lineHeight = "30px";
    container.style.textAlign = "center";
    container.style.cursor = "pointer";
    container.title = "Ricentra su Bologna";

    container.onclick = function () {
      recenterMap();
    };

    L.DomEvent.disableClickPropagation(container);

    return container;
  },
});

map.addControl(new recenterControl());


let drawnItems = new L.FeatureGroup();
map.addLayer(drawnItems);
let optimalPositionsLayer = L.layerGroup();
map.addLayer(optimalPositionsLayer);

let drawControl = new L.Control.Draw({
  edit: false, //rimuove i pulsanti di modifica ed eliminazione
  draw: {
    polygon: true,
    marker: true,
    polyline: false,
    rectangle: false,
    circle: false,
    circlemarker: false,
  },
});
map.addControl(drawControl);

var deleteAllControl = L.Control.extend({
  options: {
    position: "topleft",
  },
  onAdd: function (map) {
    var container = L.DomUtil.create("div", "leaflet-control-custom");
    container.innerHTML = "🗑️";
    container.style.backgroundColor = "white";
    container.style.width = "30px";
    container.style.height = "30px";
    container.style.lineHeight = "30px";
    container.style.textAlign = "center";
    container.style.cursor = "pointer";
    container.title = "Cancella tutti i geofence";

    container.onclick = function () {
      if (
        confirm(
          "Sei sicuro di voler cancellare tutti i geofence (marker e poligoni)?"
        )
      ) {
        deleteAllGeofences();
      }
    };

    L.DomEvent.disableClickPropagation(container);

    return container;
  },
});

map.addControl(new deleteAllControl());

function handleFilters() {
  const filterData = {
      distanceEnabled: document.getElementById("distanceToggle").checked,
      travelMode: document.getElementById("travelMode").value,
      travelTime: parseInt(document.getElementById("filterTime").value)
  };

  // Aggiorna savedFilters
  savedFilters = filterData;

  fetch("/api/filters", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(filterData)
  })
  .then(response => response.json())
  .then(() => {
      // Ricarica i POI visibili
      Object.entries(poiLayers).forEach(([poiType, layer]) => {
          if (map.hasLayer(layer)) {
              poiLayers[poiType].clearLayers();  // Pulisce i layer esistenti
              togglePOI(poiType, true);          // Ricarica con i nuovi filtri
          }
      });
  })
}

function togglePOI(poiType, show) {
  if (!show) {
      map.removeLayer(poiLayers[poiType]);
      return;
  }

  if (poiLayers[poiType].getLayers().length > 0) {
      map.addLayer(poiLayers[poiType]);
      return;
  }

  const endpoint = savedFilters.distanceEnabled ? 
      `/api/filter_pois/${poiType}` : 
      `/api/pois/${poiType}`;

  fetch(endpoint)
      .then((response) => response.json())
      .then((data) => {
          poiLayers[poiType].clearLayers();

          if (!data.data || data.data.length === 0) {
              alert(`Nessun ${poiConfigs[poiType].label} raggiungibile in ${savedFilters.travelTime} minuti ${
                  savedFilters.travelMode === 'driving' ? 'in auto' : 
                  savedFilters.travelMode === 'walking' ? 'a piedi' : 'in bici'
              }`);
              return;
          }

          let addedMarkers = 0;
          data.data.forEach((poi) => {
              if (!poi.lat || !poi.lng) return;

              const marker = L.marker([poi.lat, poi.lng], {
                  icon: getCustomIcon(poiType),
              });

              const name = poi.properties?.denominazione_struttura ||
                          poi.properties?.denominazi ||
                          poi.properties?.name ||
                          poiConfigs[poiType].label;

              let popupContent = `
                  <div class="poi-popup">
                      <h3>${name}</h3>
                      ${savedFilters.distanceEnabled && poi.travel_time ? 
                          `<p class="text-sm mt-2">⏱️ ${Math.round(poi.travel_time)} minuti</p>` 
                          : ''}
                  </div>
              `;

              marker.bindPopup(popupContent);
              poiLayers[poiType].addLayer(marker);
              addedMarkers++;
          });

          if (addedMarkers === 0) {
              alert(`Nessun ${poiConfigs[poiType].label} raggiungibile in ${savedFilters.travelTime} minuti ${
                  savedFilters.travelMode === 'driving' ? 'in auto' : 
                  savedFilters.travelMode === 'walking' ? 'a piedi' : 'in bici'
              }`);
          } else {
              map.addLayer(poiLayers[poiType]);
              map.fitBounds(poiLayers[poiType].getBounds());
          }
      })
      .catch((error) => {
          console.error(`Errore nel caricamento dei POI ${poiType}:`, error);
          alert(`Errore nel caricamento dei ${poiConfigs[poiType].label}`);
      });
}
//listeners
document.getElementById("distanceToggle").addEventListener("change", handleFilters);
document.getElementById("travelMode").addEventListener("change", handleFilters);
document.getElementById("filterTime").addEventListener("change", handleFilters);


function initializePOIControls() {
  const poiGrid = document.querySelector(".grid.grid-cols-2.gap-2");
  if (!poiGrid) {
    console.error("Grid container per i POI non trovato");
    return;
  }

  poiGrid.innerHTML = "";

  //pulsanti per poi
  Object.entries(poiConfigs).forEach(([poiType, config]) => {
    const button = document.createElement("button");
    button.className =
      "poi-button btn btn-sm w-full flex items-center justify-start gap-2 text-white";
    button.innerHTML = `
            <span class="poi-emoji">${config.emoji}</span>
            <span class="poi-label">${config.label}</span>
        `;

    button.addEventListener("click", function () {
      this.classList.toggle("active");
      togglePOI(poiType, this.classList.contains("active"));
    });

    poiGrid.appendChild(button);
  });
}

document.addEventListener("DOMContentLoaded", initializePOIControls);


window.showOptimalPositions = function(positions) {
  window.optimalPositionsLayer.clearLayers();

  positions.forEach((pos, index) => {
      const color = getColorFromRank(pos.rank);
      
      const markerDiv = document.createElement('div');
      markerDiv.style.backgroundColor = color;
      markerDiv.style.width = '25px';
      markerDiv.style.height = '25px';
      markerDiv.style.borderRadius = '50%';
      markerDiv.style.border = '2px solid white';
      markerDiv.style.boxShadow = '0 0 4px rgba(0,0,0,0.5)';
      markerDiv.style.display = 'flex';
      markerDiv.style.justifyContent = 'center';
      markerDiv.style.alignItems = 'center';
      markerDiv.style.color = 'white';
      markerDiv.style.fontWeight = 'bold';
      markerDiv.textContent = (index + 1).toString();

      const marker = L.marker([pos.lat, pos.lng], {
          icon: L.divIcon({
              html: markerDiv,
              className: '',
              iconSize: [25, 25],
              iconAnchor: [12, 12]
          }),
          zIndexOffset: 1000
      });

      const circle = L.circle([pos.lat, pos.lng], {
          color: color,
          fillColor: color,
          fillOpacity: 0.1,
          weight: 2,
          radius: neighborhoodRadius
      });

      marker.bindPopup(createOptimalPopup(pos, index));
      window.optimalPositionsLayer.addLayer(marker);
      window.optimalPositionsLayer.addLayer(circle);
  });

  if (positions.length > 0) {
      const bounds = L.latLngBounds(positions.map((pos) => [pos.lat, pos.lng]));
      map.fitBounds(bounds);
  }
};