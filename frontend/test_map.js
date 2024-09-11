// Inizializza la mappa centrata su Bologna
let map = L.map('map').setView([44.4949, 11.3426], 13);

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors'
}).addTo(map);

// Oggetto per tenere traccia dei marker per ciascuna categoria di POI
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

// Variabili per la gestione dei poligoni
let drawnItems = new L.FeatureGroup();
map.addLayer(drawnItems);

let drawControl = new L.Control.Draw({
    edit: {
        featureGroup: drawnItems
    }
});
map.addControl(drawControl);

// Gestione degli eventi di disegno
map.on(L.Draw.Event.CREATED, function (e) {
    let layer = e.layer;
    drawnItems.addLayer(layer);
});

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

// Crea una funzione per ogni tipo di POI e associa a un checkbox
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

// Pulsanti per la gestione dei poligoni
const savePolygonButton = document.createElement('button');
savePolygonButton.innerText = 'Salva Poligono';
savePolygonButton.addEventListener('click', () => {
    const layers = drawnItems.getLayers();
    if (layers.length === 0) {
        alert('Nessun poligono disegnato!');
        return;
    }
    const polygons = layers.map(layer => {
        return {
            type: 'Polygon',
            coordinates: layer.getLatLngs()[0].map(latlng => [latlng.lng, latlng.lat])
        };
    });
    axios.post('/api/save_polygons', { polygons })
        .then(response => alert('Poligoni salvati con successo!'))
        .catch(error => console.error('Errore nel salvataggio dei poligoni:', error));
});
document.body.appendChild(savePolygonButton);

// Pulsante per aggiungere marker ai poligoni
const addMarkersButton = document.createElement('button');
addMarkersButton.innerText = 'Aggiungi Marker ai Poligoni';
addMarkersButton.addEventListener('click', () => {
    const layers = drawnItems.getLayers();
    if (layers.length === 0) {
        alert('Nessun poligono disegnato!');
        return;
    }
    layers.forEach(polygonLayer => {
        const polygon = polygonLayer.getLatLngs()[0];
        poiTypes.forEach(poiType => {
            poiMarkers[poiType].forEach(marker => {
                const markerLatLng = marker.getLatLng();
                if (L.Polygon.prototype.isPointInPolygon.call(polygonLayer, markerLatLng)) {
                    marker.addTo(polygonLayer); // Aggiungi marker al poligono
                }
            });
        });
    });
});
document.body.appendChild(addMarkersButton);
