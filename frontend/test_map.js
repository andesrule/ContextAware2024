// Inizializza la mappa centrata su Bologna
let map = L.map('map').setView([44.4949, 11.3426], 13);
let neighborhoodRadius = 500; // Raggio iniziale in metri
let circles = {};

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors'
}).addTo(map);

// Funzione per creare un'icona cluster personalizzata
function createClusterCustomIcon(cluster) {
    return L.divIcon({
        html: '<div><span>' + cluster.getChildCount() + '</span></div>',
        className: 'marker-cluster marker-cluster-small',
        iconSize: new L.Point(40, 40)
    });
}

// Oggetto per tenere traccia dei layer group per ciascuna categoria di POI
let poiLayers = {
    aree_verdi: L.markerClusterGroup({
        showCoverageOnHover: false,
        zoomToBoundsOnClick: true,
        spiderfyOnMaxZoom: true,
        removeOutsideVisibleBounds: true,
        iconCreateFunction: createClusterCustomIcon
    }),
    parcheggi: L.markerClusterGroup({
        showCoverageOnHover: false,
        zoomToBoundsOnClick: true,
        spiderfyOnMaxZoom: true,
        removeOutsideVisibleBounds: true,
        iconCreateFunction: createClusterCustomIcon
    }),
    fermate_bus: L.markerClusterGroup({
        showCoverageOnHover: false,
        zoomToBoundsOnClick: true,
        spiderfyOnMaxZoom: true,
        removeOutsideVisibleBounds: true,
        iconCreateFunction: createClusterCustomIcon
    }),
    stazioni_ferroviarie: L.markerClusterGroup({
        showCoverageOnHover: false,
        zoomToBoundsOnClick: true,
        spiderfyOnMaxZoom: true,
        removeOutsideVisibleBounds: true,
        iconCreateFunction: createClusterCustomIcon
    }),
    scuole: L.markerClusterGroup({
        showCoverageOnHover: false,
        zoomToBoundsOnClick: true,
        spiderfyOnMaxZoom: true,
        removeOutsideVisibleBounds: true,
        iconCreateFunction: createClusterCustomIcon
    }),
    cinema: L.markerClusterGroup({
        showCoverageOnHover: false,
        zoomToBoundsOnClick: true,
        spiderfyOnMaxZoom: true,
        removeOutsideVisibleBounds: true,
        iconCreateFunction: createClusterCustomIcon
    }),
    ospedali: L.markerClusterGroup({
        showCoverageOnHover: false,
        zoomToBoundsOnClick: true,
        spiderfyOnMaxZoom: true,
        removeOutsideVisibleBounds: true,
        iconCreateFunction: createClusterCustomIcon
    }),
    farmacia: L.markerClusterGroup({
        showCoverageOnHover: false,
        zoomToBoundsOnClick: true,
        spiderfyOnMaxZoom: true,
        removeOutsideVisibleBounds: true,
        iconCreateFunction: createClusterCustomIcon
    }),
    luogo_culto: L.markerClusterGroup({
        showCoverageOnHover: false,
        zoomToBoundsOnClick: true,
        spiderfyOnMaxZoom: true,
        removeOutsideVisibleBounds: true,
        iconCreateFunction: createClusterCustomIcon
    }),
    servizi: L.markerClusterGroup({
        showCoverageOnHover: false,
        zoomToBoundsOnClick: true,
        spiderfyOnMaxZoom: true,
        removeOutsideVisibleBounds: true,
        iconCreateFunction: createClusterCustomIcon
    })
};

// Funzione per centrare la mappa su Bologna
function recenterMap() {
    map.setView([44.4949, 11.3426], 13);
}

var recenterControl = L.Control.extend({
    options: {
        position: 'topright'
    },
    onAdd: function(map) {
        var container = L.DomUtil.create('div', 'leaflet-control-custom');
        container.innerHTML = '📍';
        container.style.backgroundColor = 'white';
        container.style.width = '30px';
        container.style.height = '30px';
        container.style.lineHeight = '30px';
        container.style.textAlign = 'center';
        container.style.cursor = 'pointer';
        container.title = 'Ricentra su Bologna';

        container.onclick = function(){
            recenterMap();
        }

        L.DomEvent.disableClickPropagation(container);

        return container;
    }
});

// Aggiungiamo il nuovo controllo alla mappa
map.addControl(new recenterControl());

// Variabili per la gestione dei poligoni
let drawnItems = new L.FeatureGroup();
map.addLayer(drawnItems);

let drawControl = new L.Control.Draw({
    edit: {
        featureGroup: drawnItems
    },
    draw: {
        polygon: true,
        marker: true,
        polyline: false,
        rectangle: false,
        circle: false,
        circlemarker: false
    }
});
map.addControl(drawControl);

function getPOIData(poiType) {
    // Pulisci il layer cluster esistente
    poiLayers[poiType].clearLayers();
    
    fetch(`/get_pois?type=${poiType}`)
        .then(response => response.json())
        .then(data => {
            console.log(`Dati ricevuti per ${poiType}:`, data);

            if (!Array.isArray(data) || data.length === 0) {
                console.warn(`Nessun POI trovato per ${poiType}`);
                return;
            }

            data.forEach(poi => {
                if (!poi.lat || !poi.lng || isNaN(poi.lat) || isNaN(poi.lng)) {
                    console.warn(`Coordinate non valide per POI:`, poi);
                    return;
                }

                try {
                    const name = poi.additional_data?.denominazione_struttura || 
                               poi.additional_data?.denominazi || 
                               poi.additional_data?.name || 
                               `${poiType.charAt(0).toUpperCase() + poiType.slice(1)}`;

                    const icon = getCustomIcon(poiType);
                    const marker = L.marker([poi.lat, poi.lng], { icon: icon });
                    
                    let popupContent = `<div class="poi-popup">
                        <h3>${name}</h3>
                        <p>Tipo: ${poiType}</p>`;
                    
                    if (poi.additional_data) {
                        if (poi.additional_data.esercizio_via_e_civico) {
                            popupContent += `<p>Indirizzo: ${poi.additional_data.esercizio_via_e_civico}</p>`;
                        }
                        if (poi.additional_data.quartiere) {
                            popupContent += `<p>Quartiere: ${poi.additional_data.quartiere}</p>`;
                        }
                    }
                    
                    popupContent += '</div>';
                    
                    marker.bindPopup(popupContent);
                    
                    poiLayers[poiType].addLayer(marker);
                } catch (error) {
                    console.error(`Errore nella creazione del marker per:`, poi, error);
                }
            });

            map.addLayer(poiLayers[poiType]);
            
            if (poiLayers[poiType].getLayers().length > 0) {
                map.fitBounds(poiLayers[poiType].getBounds());
            }
        })
        .catch(error => {
            console.error(`Errore nel recupero dei POI per ${poiType}:`, error);
        });
}

function getCustomIcon(poiType) {
    // Definisci le icone per ogni tipo di POI
    const iconMap = {
        aree_verdi: '🌳',
        parcheggi: '🅿️',
        fermate_bus: '🚌',
        stazioni_ferroviarie: '🚉',
        scuole: '🏫',
        cinema: '🎬',
        ospedali: '🏥',
        farmacia: '💊',
        luogo_culto: '⛪',
        servizi: '🏢'
    };

    return L.divIcon({
        html: iconMap[poiType] || '📍',
        className: 'custom-div-icon',
        iconSize: [30, 30],
        iconAnchor: [15, 15],
        popupAnchor: [0, -15]
    });
}

function togglePOI(button, poiType) {
    button.classList.toggle('btn-active');
    const isActive = button.classList.contains('btn-active');
    
    if (isActive) {
        if (poiLayers[poiType].getLayers().length === 0) {
            getPOIData(poiType);
        } else {
            map.addLayer(poiLayers[poiType]);
        }
    } else {
        map.removeLayer(poiLayers[poiType]);
    }
}

// Esponi la funzione togglePOI globalmente
window.togglePOI = togglePOI;

let databaseMarkers = L.markerClusterGroup();

function loadRankedMarkers() {
    fetch('/get_ranked_markers')
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => {
                    throw new Error(err.error || `HTTP error! status: ${response.status}`);
                });
            }
            return response.json();
        })
        .then(data => {
            databaseMarkers.clearLayers();

            data.forEach(markerData => {
                const color = getColorFromRank(markerData.rank);
                const marker = L.circleMarker([markerData.lat, markerData.lng], {
                    radius: 10,
                    fillColor: color,
                    color: '#000',
                    weight: 1,
                    opacity: 1,
                    fillOpacity: 0.8
                });
                marker.bindPopup(`<b>Rank: ${markerData.rank.toFixed(2)}</b><br>Marker dal Database`);
                databaseMarkers.addLayer(marker);
            });

            map.addLayer(databaseMarkers);

            if (databaseMarkers.getLayers().length > 0) {
                map.fitBounds(databaseMarkers.getBounds());
            }
        })
        .catch(error => {
            console.error('Errore nel caricamento dei marker dal database:', error);
            showToast('error', `Errore nel caricamento dei marker: ${error.message}`);
            if (error.message === 'No questionnaires found') {
                showNoQuestionnaireAlert();
            }
        });

    }        
function showNoQuestionnaireAlert() {
    // Espandi la sezione degli alert
    const alertsSection = document.getElementById('alertsSection');
    if (alertsSection) {
        alertsSection.style.display = 'block';
    }

    // Crea e mostra l'alert
    createAlert('Non ci sono questionari nel database. Compilare almeno un questionario per visualizzare i dati.');

    // Mostra una notifica pop-up
    showToast('warning', 'Compila il questionario prima di visualizzare i marker.');
}
function getColorFromRank(rank) {
    if (rank < 70) return '#FF0000';      // Rosso
    else if (rank < 90) return '#FFA500'; // Arancione
    else if (rank < 120) return '#FFFF00'; // Giallo
    else if (rank < 150) return '#90EE90'; // Verde chiaro
    else return '#008000';                // Verde scuro
}

function loadRankedGeofences() {
    fetch('/get_ranked_geofences')
        .then(response => {
            if (!response.ok) {
                if (response.status === 404) {
                    throw new Error('No questionnaires found');
                }
                return response.text().then(text => {
                    throw new Error(`HTTP error! status: ${response.status}, body: ${text}`);
                });
            }
            return response.json();
        })
        .then(data => {
            // Assicuriamoci che il layer dei geofences esista
            if (!window.geofencesLayer) {
                window.geofencesLayer = L.layerGroup().addTo(map);
            } else {
                window.geofencesLayer.clearLayers();
            }

            data.forEach(geofenceData => {
                const color = getColorFromRank(geofenceData.rank);
                
                // Creiamo un poligono per ogni geofence
                const polygon = L.polygon(geofenceData.coordinates.map(coord => [coord[1], coord[0]]), {
                    color: color,
                    fillColor: color,
                    fillOpacity: 0.5,
                    weight: 2
                });

                // Aggiungiamo un popup al poligono
                polygon.bindPopup(`
                    <b>Geofence ID: ${geofenceData.id}</b><br>
                    Rank: ${geofenceData.rank.toFixed(2)}<br>
                    Centroid: ${geofenceData.centroid.lat.toFixed(6)}, ${geofenceData.centroid.lng.toFixed(6)}
                `);

                // Aggiungiamo il poligono al layer dei geofences
                window.geofencesLayer.addLayer(polygon);
            });

            // Adattiamo la vista della mappa per includere tutti i geofences
            if (window.geofencesLayer.getLayers().length > 0) {
                map.fitBounds(window.geofencesLayer.getBounds());
            }
        })
        .catch(error => {
            console.error('Errore nel caricamento dei geofences:', error);
            if (error.message === 'No questionnaires found') {
                showNoQuestionnaireAlert();
            } else {
                showToast('error', `Errore nel caricamento dei geofences: ${error.message}`);
            }
        });
}


var customControl = L.Control.extend({
    options: {
        position: 'topleft'
    },
    onAdd: function(map) {
        var container = L.DomUtil.create('div', 'leaflet-control-custom');
        container.innerHTML = '📍';
        container.style.backgroundColor = 'white';
        container.style.width = '30px';
        container.style.height = '30px';
        container.style.lineHeight = '30px';
        container.style.textAlign = 'center';
        container.style.cursor = 'pointer';
        container.title = 'Mostra marker dal database';

        container.onclick = function(){
            loadRankedMarkers();
        }

        L.DomEvent.disableClickPropagation(container);

        return container;
    }
});

map.addControl(new customControl());

var geofenceControl = L.Control.extend({
    options: {
        position: 'topleft'
    },
    onAdd: function(map) {
        var container = L.DomUtil.create('div', 'leaflet-control-custom');
        container.innerHTML = '🏠';
        container.style.backgroundColor = 'white';
        container.style.width = '30px';
        container.style.height = '30px';
        container.style.lineHeight = '30px';
        container.style.textAlign = 'center';
        container.style.cursor = 'pointer';
        container.title = 'Mostra Geofence';
        container.onclick = function(){
            loadRankedGeofences();
        }
        L.DomEvent.disableClickPropagation(container);
        return container;
    }
});

map.addControl(new geofenceControl());

// Aggiungi l'evento per lo slider
document.getElementById('radiusSlider').addEventListener('input', function(e) {
    neighborhoodRadius = parseInt(e.target.value);
    document.getElementById('radiusValue').textContent = neighborhoodRadius;
    updateNeighborhoodCircles();
    sendRadiusToBackend(neighborhoodRadius);
});

function updateNeighborhoodCircles() {
    Object.values(circles).forEach(circle => {
        circle.setRadius(neighborhoodRadius);
    });
}

function sendRadiusToBackend(radius) {
    fetch('/get_radius', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ radius: radius })
    })
    .then(response => response.json())
    .then(data => {
        console.log('Success:', data);
    })
    .catch((error) => {
        console.error('Error:', error);
    });
}

map.on(L.Draw.Event.CREATED, function (e) {
    let layer = e.layer;

    if (layer instanceof L.Marker) {
        const latlng = layer.getLatLng();
        const userMarker = L.marker([latlng.lat, latlng.lng]).addTo(map);

        const circle = L.circle([latlng.lat, latlng.lng], {
            color: 'blue',
            fillColor: '#30f',
            fillOpacity: 0.2,
            radius: neighborhoodRadius
        }).addTo(map);

        circles[userMarker._leaflet_id] = circle;

        userMarker.bindPopup(`
            <b>Marker Utente</b><br>
            <button class="delete-marker-btn" onclick="deleteMarker(${userMarker._leaflet_id})">
                🗑 Elimina Marker
            </button>
        `).openPopup();

        drawnItems.addLayer(userMarker);
        drawnItems.addLayer(circle);

        saveGeofenceToDatabase([{ lat: latlng.lat, lng: latlng.lng }], null);
    } else if (layer instanceof L.Polygon) {
        const coordinates = layer.getLatLngs()[0].map(latlng => ({ lat: latlng.lat, lng: latlng.lng }));
        saveGeofenceToDatabase(null, [coordinates]);
        drawnItems.addLayer(layer);
    }
});

function deleteMarker(markerId) {
    const marker = drawnItems.getLayer(markerId);
    if (marker) {
        map.removeLayer(marker);
        if (circles[markerId]) {
            map.removeLayer(circles[markerId]);
            delete circles[markerId];
        }
    }
}


function showToast(type, message) {
    const toast = document.createElement('div');
    toast.className = `alert ${type === 'success' ? 'alert-success' : 'alert-error'} fixed bottom-4 right-4 z-50`;
    toast.innerHTML = `<span>${message}</span>`;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.remove();
    }, 3000);
}

// Stile CSS per lo slider
const style = document.createElement('style');
style.textContent = `
    .radius-slider {
        background: white;
        padding: 10px;
        border-radius: 5px;
    }
    .radius-slider h4 {
        margin: 0 0 10px 0;
    }
    .slider {
        width: 100%;
    }
`;
document.head.appendChild(style);

const clusterStyle = document.createElement('style');
clusterStyle.textContent = `
    .marker-cluster-small {
        background-color: rgba(181, 226, 140, 0.6);
    }
    .marker-cluster-small div {
        background-color: rgba(110, 204, 57, 0.6);
    }
    .marker-cluster-medium {
        background-color: rgba(241, 211, 87, 0.6);
    }
    .marker-cluster-medium div {
        background-color: rgba(240, 194, 12, 0.6);
    }
    .marker-cluster-large {
        background-color: rgba(253, 156, 115, 0.6);
    }
    .marker-cluster-large div {
        background-color: rgba(241, 128, 23, 0.6);
    }
    .marker-cluster {
        background-clip: padding-box;
        border-radius: 20px;
    }
    .marker-cluster div {
        width: 30px;
        height: 30px;
        margin-left: 5px;
        margin-top: 5px;
        text-align: center;
        border-radius: 15px;
        font: 12px "Helvetica Neue", Arial, Helvetica, sans-serif;
        color: #ffffff;
        font-weight: bold;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .marker-cluster span {
        line-height: 30px;
    }
`;
document.head.appendChild(clusterStyle);