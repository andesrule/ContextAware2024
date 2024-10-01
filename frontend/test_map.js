// Aggiungi un listener per 'DOMContentLoaded' per assicurarti che il DOM sia completamente caricato prima di eseguire il codice

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
        // Usa l'icona rossa per i marker dell'utente
        const latlng = layer.getLatLng();
        const userMarker = L.marker([latlng.lat, latlng.lng], { icon: userMarkerIcon }).addTo(map);
        userMarker.bindPopup('<b>Marker Utente</b>').openPopup();

        // Salva il marker nel database
        saveGeofenceToDatabase([{ lat: latlng.lat, lng: latlng.lng }], null);  // Salva il marker come punto singolo
    } else if (layer instanceof L.Polygon) {
        // Salva il poligono nel database
        const coordinates = layer.getLatLngs()[0].map(latlng => ({ lat: latlng.lat, lng: latlng.lng }));
        saveGeofenceToDatabase(null, [coordinates]);  // Salva il poligono
    }

    // Aggiungi il layer alla mappa (usato per visualizzare sia marker che poligoni)
    drawnItems.addLayer(layer);
});

// Marker per i POI con colore blu (default)
const poiMarkerIcon = L.divIcon({
    className: 'poi-marker', // Classe per il marker
    html: '<div style="background-color: blue; width: 25px; height: 25px; border-radius: 50%;"></div>', // Stile del marker
    iconSize: [25, 25],
    iconAnchor: [12, 12]
});

const userMarkerIcon = L.divIcon({
    className: 'user-marker',
    html: `
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="25" height="25">
            <path fill="red" d="M12 0C7.58 0 4 3.58 4 8c0 5.5 8 16 8 16s8-10.5 8-16c0-4.42-3.58-8-8-8zm0 12c-2.21 0-4-1.79-4-4s1.79-4 4-4 4 1.79 4 4-1.79 4-4 4z"/>
        </svg>
    `,
    iconSize: [25, 25],
    iconAnchor: [12, 25],
    popupAnchor: [0, -25]
});

// Funzione per aggiungere un marker inserito dall'utente
function addUserMarker(lat, lon) {
    const marker = L.marker([lat, lon], { icon: userMarkerIcon }).addTo(map);
    marker.bindPopup('<b>Marker Utente</b>').openPopup();
    userMarkers.push(marker); // Salva i marker inseriti dall'utente
}

// Funzione per aggiungere un marker per i POI
function addPOIMarker(lat, lon, poiType, name) {
    const marker = L.marker([lat, lon], { icon: poiMarkerIcon }).bindPopup(`<b>${name}</b><br>${poiType}`);
    marker.addTo(map);
    poiMarkers[poiType].push(marker);
}


// Funzione per recuperare i dati dei POI dal server
// Funzione generica per recuperare i dati dei POI dal server
// Funzione generica per recuperare i dati dei POI dal server// Funzione generica per recuperare i dati dei POI dal server
function getPOIData(poiType) {
    axios.get(`/get_pois`).then(response => {
        console.log(`Dati ricevuti per ${poiType}:`, response.data);

        const pois = response.data.filter(poi => poi.type === poiType);

        if (!pois || pois.length === 0) {
            console.warn(`Nessun POI trovato per ${poiType}`);
            return;
        }

        pois.forEach(poi => {
            let lat, lon;

            // Handle different coordinate formats
            if (poi.additional_data.geo_point_2d) {
                lat = poi.additional_data.geo_point_2d.lat;
                lon = poi.additional_data.geo_point_2d.lon;
            } else if (poi.additional_data.geopoint) {
                lat = poi.additional_data.geopoint.lat;
                lon = poi.additional_data.geopoint.lon;
            } else if (poi.additional_data.point) {
                lat = poi.additional_data.point.lat;
                lon = poi.additional_data.point.lon;
            } else if (poi.additional_data.coordinate) {
                // Handle 'coordinate' for parking POIs
                lat = poi.additional_data.coordinate.lat;
                lon = poi.additional_data.coordinate.lon;
            } else {
                console.warn(`POI senza dati geografici per ${poiType}:`, poi);
                return;  // Skip this POI if no valid coordinates are found
            }

            // Ensure that lat and lon are valid numbers
            if (!lat || !lon || isNaN(lat) || isNaN(lon)) {
                console.warn(`Coordinate non valide per ${poiType}:`, lat, lon);
                return;
            }

            const name = poi.additional_data.denominazione_struttura || poi.additional_data.denominazi || poi.additional_data.name || 'POI';

            // Create and add the marker to the map
            addPOIMarker(lat, lon, poiType, name);
        });
    }).catch(error => {
        console.error(`Errore nel recupero dei POI per ${poiType}:`, error);
    });
}


function togglePOI(poiType) {
    if (document.getElementById(poiType).checked) {
        // Se non ci sono marker, carica i dati dal server
        if (poiMarkers[poiType].length === 0) {
            getPOIData(poiType);  // Usa la funzione generica per tutti i tipi di POI
        } else {
            // Aggiungi i marker già presenti alla mappa
            poiMarkers[poiType].forEach(marker => marker.addTo(map));
        }
    } else {
        // Rimuovi i marker dalla mappa
        poiMarkers[poiType].forEach(marker => map.removeLayer(marker));
    }
}
let databaseMarkers = [];
function loadDatabaseMarkers() {
    fetch('/get_markers')
        .then(response => response.json())
        .then(data => {
            // Rimuovi i marker esistenti
            databaseMarkers.forEach(marker => map.removeLayer(marker));
            databaseMarkers = [];

            // Aggiungi i nuovi marker
            data.forEach(markerData => {
                const marker = L.marker([markerData.lat, markerData.lng], { icon: userMarkerIcon }).addTo(map);
                marker.bindPopup('<b>Marker dal Database</b>');
                databaseMarkers.push(marker);
            });

            // Centra la mappa sui marker se ce ne sono
            if (databaseMarkers.length > 0) {
                let group = new L.featureGroup(databaseMarkers);
                map.fitBounds(group.getBounds());
            }
        })
        .catch(error => console.error('Errore nel caricamento dei marker dal database:', error));
}

// Definizione del controllo personalizzato
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

// Aggiungi il controllo personalizzato alla mappa
map.addControl(new customControl());

