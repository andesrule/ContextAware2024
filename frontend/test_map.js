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

// Marker per i marker dell'utente con colore rosso
const userMarkerIcon = L.divIcon({
    className: 'user-marker', // Classe per il marker
    html: '<div style="background-color: red; width: 25px; height: 25px; border-radius: 50%;"></div>', // Stile del marker
    iconSize: [25, 25],
    iconAnchor: [12, 12]
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
function getPOIDataGeopoint(poiType) {
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


function getPOIDataGeoPoint2D(poiType) {
    axios.get(`/api/poi/${poiType}`).then(response => {
        console.log(`Dati ricevuti per ${poiType}:`, response.data);

        // Accedi al campo 'results' invece di 'records'
        const results = response.data.results;

        if (!results || results.length === 0) {
            console.warn(`Nessun POI trovato per ${poiType}`);
            return;
        }

        results.forEach(record => {
            const poi = record;  // I dati del POI si trovano direttamente in 'record'

            let lat, lon;

            // Supponiamo che le coordinate siano in 'geo_point_2d' o 'geopoint'
            if (poi.geo_point_2d) {
                lat = poi.geo_point_2d[0];
                lon = poi.geo_point_2d[1];
            } else if (poi.geopoint && poi.geopoint.lat && poi.geopoint.lon) {
                lat = poi.geopoint.lat;
                lon = poi.geopoint.lon;
            } else {
                console.warn(`POI senza dati geografici per ${poiType}:`, poi);
                return;  // Salta questo POI se non ha coordinate
            }

            if (!lat || !lon || isNaN(lat) || isNaN(lon)) {
                console.warn(`Coordinate non valide per ${poiType}:`, lat, lon);
                return;
            }

            console.log(`Aggiungo POI: ${poiType}, lat: ${lat}, lon: ${lon}`);

            const name = poi.nomevia || poi.denominazione || 'POI';  // Usa 'nomevia' o 'denominazione'

            // Crea e aggiungi il marker alla mappa
            const marker = L.marker([lat, lon]).bindPopup(`<b>${name}</b><br>${poiType}`);
            marker.addTo(map);  // Aggiunge il marker alla mappa
            poiMarkers[poiType].push(marker);  // Salva il marker per rimuoverlo successivamente se necessario
        });

    }).catch(error => {
        console.error(`Errore nel recupero dei POI per ${poiType}:`, error);
    });
}

function getFarmaciaData() {
    axios.get(`/api/poi/farmacia`).then(response => {
        console.log(`Dati ricevuti per farmacia:`, response.data);

        const results = response.data.results;

        if (!results || results.length === 0) {
            console.warn(`Nessun POI trovato per farmacia`);
            return;
        }

        results.forEach(record => {
            const poi = record;

            let lat, lon;

            // Verifica se le coordinate sono nel campo 'point'
            if (poi.point && poi.point.lat && poi.point.lon) {
                lat = poi.point.lat;
                lon = poi.point.lon;
            } 
            // In alternativa, usa 'xcoord' e 'ycoord' se presenti
            else if (poi.xcoord && poi.ycoord) {
                lat = parseFloat(poi.ycoord);
                lon = parseFloat(poi.xcoord);
            } else {
                console.warn(`POI senza dati geografici per farmacia:`, poi);
                return;  // Salta questo POI se non ha coordinate
            }

            if (!lat || !lon || isNaN(lat) || isNaN(lon)) {
                console.warn(`Coordinate non valide per farmacia:`, lat, lon);
                return;
            }

            const name = poi.farmacia || 'Farmacia';

            // Crea e aggiungi il marker alla mappa
            const marker = L.marker([lat, lon]).bindPopup(`<b>${name}</b><br>Farmacia`);
            marker.addTo(map);
            poiMarkers['farmacia'].push(marker);
        });

    }).catch(error => {
        console.error(`Errore nel recupero dei POI per farmacia:`, error);
    });
}

function togglePOI(poiType) {
    if (document.getElementById(poiType).checked) {
        // Se non ci sono marker, carica i dati dal server
        if (poiMarkers[poiType].length === 0) {
            // Seleziona la funzione corretta per il caricamento dei POI
            if (poiType === 'farmacia') {
                getFarmaciaData(poiType);  // Chiamata per le farmacie
            } else if (poiType === 'aree_verdi' || poiType === 'parcheggi' ||  poiType === 'scuole' || poiType === 'cinema' || poiType === 'ospedali' || poiType === 'luogo_culto') {
                getPOIDataGeopoint(poiType);  
            } else {
                getPOIDataGeoPoint2D(poiType);  // Chiamata per 'geopoint'
            }
        } else {
            // Aggiungi i marker già presenti alla mappa
            poiMarkers[poiType].forEach(marker => marker.addTo(map));
        }
    } else {
        // Rimuovi i marker dalla mappa
        poiMarkers[poiType].forEach(marker => map.removeLayer(marker));
    }
}




