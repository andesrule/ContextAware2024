// Inizializza la mappa centrata su Bologna
let map = L.map('map').setView([44.4949, 11.3426], 13);

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
            circle: false
        }
    });
    map.addControl(drawControl);

    // Gestione degli eventi di disegno
    map.on(L.Draw.Event.CREATED, function (e) {
        let layer = e.layer;

        if (layer instanceof L.Marker) {
            const latlng = layer.getLatLng();
            const userMarker = L.marker([latlng.lat, latlng.lng]).addTo(map);
            userMarker.bindPopup('<b>Marker Utente</b>').openPopup();

            saveGeofenceToDatabase([{ lat: latlng.lat, lng: latlng.lng }], null);
        } else if (layer instanceof L.Polygon) {
            const coordinates = layer.getLatLngs()[0].map(latlng => ({ lat: latlng.lat, lng: latlng.lng }));
            saveGeofenceToDatabase(null, [coordinates]);
        }

        drawnItems.addLayer(layer);
    });

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

    function loadDatabaseMarkers() {
        fetch('/get_markers')
            .then(response => response.json())
            .then(data => {
                databaseMarkers.clearLayers();

                data.forEach(markerData => {
                    const marker = L.marker([markerData.lat, markerData.lng]);
                    marker.bindPopup('<b>Marker dal Database</b>');
                    databaseMarkers.addLayer(marker);
                });

                map.addLayer(databaseMarkers);

                if (databaseMarkers.getLayers().length > 0) {
                    map.fitBounds(databaseMarkers.getBounds());
                }
            })
            .catch(error => console.error('Errore nel caricamento dei marker dal database:', error));
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
                loadDatabaseMarkers();
            }

            L.DomEvent.disableClickPropagation(container);

            return container;
        }
    });

    map.addControl(new customControl());


function saveGeofenceToDatabase(marker, geofence) {
    const data = marker ? { marker } : { geofence };
    
    fetch('/save-geofence', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
    })
    .then(response => response.json())
    .then(data => {
        console.log('Success:', data);
    })
    .catch((error) => {
        console.error('Error:', error);
    });
}