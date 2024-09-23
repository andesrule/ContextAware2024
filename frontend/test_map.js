// Inizializza la mappa
var map = L.map('map').setView([44.4936, 11.3430], 13);  // Coordinate per Bologna

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
        marker: true,       // Abilita la creazione di marker
        circlemarker: false
    },
    edit: {
        featureGroup: drawnItems,
        remove: true       // Abilita la rimozione delle geometrie esistenti
    }
});
map.addControl(drawControl);

// Gestisci l'evento di creazione
map.on('draw:created', function (e) {
    var layer = e.layer;

    // Aggiungi il layer creato al gruppo di layer disegnati
    drawnItems.addLayer(layer);

    // Converti in GeoJSON e invia al server
    var geojson = layer.toGeoJSON();
    sendToServer(e.layerType, geojson);
});

// Gestisci l'evento di modifica (per rimuovere)
map.on('draw:deleted', function (e) {
    // Ogni geometria eliminata può essere trattata qui
    e.layers.eachLayer(function (layer) {
        // Esempio di rimozione dal server se necessario
        console.log('Layer removed:', layer.toGeoJSON());
    });
});

// Funzione per inviare i dati al server
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


let poiMarkers = {
    aree_verdi: [],
    parcheggi: [],
    fermate_bus: [],
    luoghi_interesse: [],
    scuole: [],
    cinema: [],
    ospedali: [],
    farmacia: [],
    luogo_culto: [],
    servizi: []
};

// Funzione per mostrare o nascondere i POI sulla mappa
function togglePOI(poiType) {
    if (document.getElementById(poiType).checked) {
        // Se non ci sono marker, carica i dati dal server
        if (poiMarkers[poiType].length === 0) {
            getPOIData(poiType);
        } else {
            // Aggiungi i marker già presenti alla mappa
            poiMarkers[poiType].forEach(marker => marker.addTo(map));
        }
    } else {
        // Rimuovi i marker dalla mappa
        poiMarkers[poiType].forEach(marker => map.removeLayer(marker));
    }
}
// Funzione per recuperare i dati dei POI dal server
function getPOIData(poiType) {
    axios.get(`/api/poi/${poiType}`).then(response => {
        const results = response.data.results;

        if (!results || results.length === 0) {
            console.warn(`Nessun POI trovato per ${poiType}`);
            return;
        }

        results.forEach(record => {
            const poi = record;

            let lat, lon;

            // Gestisci diversi formati di coordinate
            if (poi.geo_point_2d) {
                lat = poi.geo_point_2d.lat;
                lon = poi.geo_point_2d.lon;
            } else if (poi.coordinate) {
                lat = poi.coordinate.lat;
                lon = poi.coordinate.lon;
            } else if (poi.geopoint) {
                lat = poi.geopoint.latitude;  // Assumi 'latitude' e 'longitude'
                lon = poi.geopoint.longitude;
            } else if (poi.point) {
                lat = poi.point.ycoord;  // Assumi 'xcoord' e 'ycoord'
                lon = poi.point.xcoord;
            } else {
                console.warn(`POI senza dati geografici per ${poiType}:`, poi);
                return;  // Salta questo POI se non ha coordinate
            }

            // Controlla se le coordinate sono valide
            if (lat === undefined || lon === undefined) {
                console.warn(`Coordinate mancanti per ${poiType}:`, poi);
                return;
            }

            // Verifica che lat e lon siano numeri validi
            if (isNaN(lat) || isNaN(lon)) {
                console.warn(`Coordinate non valide per ${poiType}:`, poi);
                return;
            }

            const name = poi.name || poi.denominazione || 'POI';

            // Crea e aggiungi il marker alla mappa
            const marker = L.marker([lat, lon]).bindPopup(`<b>${name}</b><br>${poiType}`);
            poiMarkers[poiType].push(marker);  // Salva il marker
        });

        // Aggiungi i marker alla mappa dopo che sono stati caricati
        if (document.getElementById(poiType).checked) {
            poiMarkers[poiType].forEach(marker => marker.addTo(map));
        }
    }).catch(error => {
        console.error(`Errore nel recupero dei POI per ${poiType}:`, error);
    });
}

const poiTypes = ['aree_verdi', 'parcheggi', 'fermate_bus', 'luoghi_interesse', 'scuole', 'cinema', 'ospedali', 'farmacia', 'luogo_culto', 'servizi'];

poiTypes.forEach(poiType => {
    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.id = poiType;
    checkbox.addEventListener('change', () => togglePOI(poiType));

    const label = document.createElement('label');
    label.innerHTML = ` ${poiType.charAt(0).toUpperCase() + poiType.slice(1)}`;
    label.prepend(checkbox);

    document.body.appendChild(label);
    document.body.appendChild(document.createElement('br'));
});