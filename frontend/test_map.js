// Definisco le variabili buildingLayerGroup e poiLayerGroup globalmente
var map;
var buildingLayerGroup;
var poiLayerGroup;

// Funzione per inviare i dati al server
function sendToServer(type, geojson) {
    let markers = [];
    let geofences = [];

    if (type === 'marker') {
        markers.push(geojson);
    } else if (type === 'polygon') {
        geofences.push(geojson);
    }

    fetch('/save-geofence', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            markers: markers,
            geofences: geofences
        })
    })
    .then(response => response.json())
    .then(data => {
        console.log('Geofence saved:', data);
    })
    .catch(error => {
        console.error('Error saving geofence:', error);
    });
}

// Funzione per caricare gli edifici (immobili)
function fetchBuildings() {
    var overpassUrl = 'https://overpass-api.de/api/interpreter';
    var query = `
        [out:json];
        (
          way["building"](44.485,11.30,44.505,11.36);
        );
        (._;>;);
        out body;
    `;
    
    fetch(overpassUrl, {
        method: 'POST',
        body: query,
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
    })
    .then(response => response.json())
    .then(data => {
        buildingLayerGroup.clearLayers(); // Pulisci il layerGroup prima di aggiungere nuovi edifici
        var nodes = {};
        data.elements.forEach(element => {
            if (element.type === 'node') {
                nodes[element.id] = [element.lat, element.lon];
            }
        });

        data.elements.forEach(element => {
            if (element.type === 'way' && element.nodes) {
                var latlngs = [];
                element.nodes.forEach(nodeId => {
                    if (nodes[nodeId]) {
                        latlngs.push(nodes[nodeId]);
                    }
                });
                if (latlngs.length > 0) {
                    var polygon = L.polygon(latlngs, {color: 'blue'}).addTo(buildingLayerGroup);
                    polygon.bindPopup('Edificio');
                }
            }
        });
    })
    .catch(error => console.error('Errore nel recupero dei dati degli edifici:', error));
}

// Funzione per caricare i POI
function fetchAndDisplayPOI(poiType) {
    fetch('/api/poi/' + poiType)
        .then(response => response.json())
        .then(data => {
            poiLayerGroup.clearLayers();
            if (data.records) {
                data.records.forEach(record => {
                    var coords = record.geometry.coordinates;
                    var lat = coords[1];
                    var lng = coords[0];
                    L.marker([lat, lng]).addTo(poiLayerGroup).bindPopup(record.record.fields.denominazione);
                });
            }
        })
        .catch(error => console.error('Errore nel recupero dei dati dei POI:', error));
}

// Inizializza la mappa all'interno dell'evento DOMContentLoaded
document.addEventListener('DOMContentLoaded', function() {
    if (map) {
        console.log("Mappa già inizializzata.");
        return; // Evita di inizializzare la mappa se è già stata inizializzata
    }

    map = L.map('map').setView([44.4936, 11.3430], 13);
    buildingLayerGroup = L.layerGroup().addTo(map); // LayerGroup per gli edifici
    poiLayerGroup = L.layerGroup().addTo(map); // LayerGroup per i POI

    // Aggiungi il tile layer di OpenStreetMap
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);

    // Inizializza il controllo di disegno
    var drawnItems = L.featureGroup().addTo(map);
    var drawControl = new L.Control.Draw({
        draw: {
            polyline: false,   // Disabilita la creazione di linee
            polygon: true,     // Abilita la creazione di poligoni
            rectangle: false,  // Disabilita la creazione di rettangoli
            circle: false,     // Disabilita la creazione di cerchi
            marker: true,      // Abilita la creazione di marker
            circlemarker: false
        },
        edit: {
            featureGroup: drawnItems,
            remove: true       // Abilita la rimozione delle geometrie esistenti
        }
    });
    map.addControl(drawControl);

    // Gestione del checkbox per mostrare/nascondere gli edifici
    document.getElementById('showBuildings').addEventListener('change', function(e) {
        if (this.checked) {
            fetchBuildings();
        } else {
            buildingLayerGroup.clearLayers();
        }
    });

    // Carica gli edifici inizialmente se il checkbox è selezionato
    if (document.getElementById('showBuildings').checked) {
        fetchBuildings();
    }

    // Esegui il fetch degli edifici al caricamento della mappa
    map.on('moveend', function() {
        if (document.getElementById('showBuildings').checked) {
            fetchBuildings();
        }
    });
});
