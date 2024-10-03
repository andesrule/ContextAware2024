// Inizializza la mappa centrata su Bologna
let map = L.map('map').setView([44.4949, 11.3426], 13);
let neighborhoodRadius = 500; // Raggio iniziale in metri
let circles = {};

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors'
}).addTo(map);

// Oggetto per tenere traccia dei layer group per ciascuna categoria di POI
let poiLayers = {
    aree_verdi: L.markerClusterGroup({ singleMarkerMode: true }),
    parcheggi: L.markerClusterGroup({ singleMarkerMode: true }),
    fermate_bus: L.markerClusterGroup({ singleMarkerMode: true }),
    stazioni_ferroviarie: L.markerClusterGroup({ singleMarkerMode: true }),
    scuole: L.markerClusterGroup({ singleMarkerMode: true }),
    cinema: L.markerClusterGroup({ singleMarkerMode: true }),
    ospedali: L.markerClusterGroup({ singleMarkerMode: true }),
    farmacia: L.markerClusterGroup({ singleMarkerMode: true }),
    luogo_culto: L.markerClusterGroup({ singleMarkerMode: true }),
    servizi: L.markerClusterGroup({ singleMarkerMode: true })
};

// Resto del codice rimane invariato


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

    // Gestione degli eventi di disegno


    function getPOIData(poiType) {
        fetch(`/get_pois?type=${poiType}`)
            .then(response => response.json())
            .then(data => {
                console.log(`Dati ricevuti per ${poiType}:`, data);

                const pois = data.filter(poi => poi.type === poiType);

                if (!pois || pois.length === 0) {
                    console.warn(`Nessun POI trovato per ${poiType}`);
                    return;
                }

                pois.forEach(poi => {
                    const lat = poi.lat;
                    const lon = poi.lng;

                    if (!lat || !lon || isNaN(lat) || isNaN(lon)) {
                        console.warn(`Coordinate non valide per ${poiType}:`, lat, lon);
                        return;
                    }

                    const name = poi.additional_data.denominazione_struttura || poi.additional_data.denominazi || poi.additional_data.name || 'POI';

                    const marker = L.marker([lat, lon]).bindPopup(`<b>${name}</b><br>${poiType}`);
                    poiLayers[poiType].addLayer(marker);
                });

                map.addLayer(poiLayers[poiType]);
            })
            .catch(error => {
                console.error(`Errore nel recupero dei POI per ${poiType}:`, error);
            });
    }

    function togglePOI(poiType) {
        if (document.getElementById(poiType).checked) {
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
            .then(response => response.json())
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
            .catch(error => console.error('Errore nel caricamento dei marker dal database:', error));
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
            .then(response => response.json())
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
            .catch(error => console.error('Errore nel caricamento dei geofences:', error));
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
            container.innerHTML = '🏠';  // Emoji casa per rappresentare geofence
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




// Aggiungi questo codice per creare lo slider
let radiusSlider = L.control({position: 'topright'});

radiusSlider.onAdd = function(map) {
    let div = L.DomUtil.create('div', 'info radius-slider');
    div.innerHTML = '<h4>Raggio del vicinato: <span id="radiusValue">500</span> m</h4>' +
                    '<input type="range" min="50" max="1000" value="500" class="slider" id="radiusSlider">';
    return div;
};

radiusSlider.addTo(map);

// Aggiungi l'evento per lo slider
document.getElementById('radiusSlider').addEventListener('input', function(e) {
    neighborhoodRadius = parseInt(e.target.value);
    document.getElementById('radiusValue').textContent = neighborhoodRadius;
    updateNeighborhoodCircles();
    sendRadiusToBackend(neighborhoodRadius);
});

// Funzione per aggiornare i cerchi del vicinato
function updateNeighborhoodCircles() {
    Object.values(circles).forEach(circle => {
        circle.setRadius(neighborhoodRadius);
    });
}
// Funzione per inviare il raggio al backend
function sendRadiusToBackend(radius) {
    fetch('/get_radius', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ radius: radius })  // Passa il raggio come intero
    })
    .then(response => response.json())
    .then(data => {
        console.log('Success:', data);  // Ricevi la risposta dal backend
    })
    .catch((error) => {
        console.error('Error:', error);
    });
}
// Modifica la gestione degli eventi di disegno per includere i cerchi del vicinato
map.on(L.Draw.Event.CREATED, function (e) {
    let layer = e.layer;

    if (layer instanceof L.Marker) {
        const latlng = layer.getLatLng();
        const userMarker = L.marker([latlng.lat, latlng.lng]).addTo(map);
        userMarker.bindPopup('<b>Marker Utente</b>').openPopup();

        // Crea il cerchio del vicinato
        const circle = L.circle([latlng.lat, latlng.lng], {
            color: 'blue',
            fillColor: '#30f',
            fillOpacity: 0.2,
            radius: neighborhoodRadius
        }).addTo(map);

        // Memorizza il cerchio
        circles[userMarker._leaflet_id] = circle;

        saveGeofenceToDatabase([{ lat: latlng.lat, lng: latlng.lng }], null);
    } else if (layer instanceof L.Polygon) {
        const coordinates = layer.getLatLngs()[0].map(latlng => ({ lat: latlng.lat, lng: latlng.lng }));
        saveGeofenceToDatabase(null, [coordinates]);
    }

    drawnItems.addLayer(layer);
});

// Aggiungi questo stile CSS per lo slider
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