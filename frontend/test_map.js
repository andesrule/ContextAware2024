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
    edit: false,  // Questo rimuove i pulsanti di modifica ed eliminazione
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


function loadAllGeofences() {
    fetch('/get_all_geofences')
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
            // Pulisci i layer esistenti
            drawnItems.clearLayers();
            Object.values(circles).forEach(circle => map.removeLayer(circle));
            circles = {};
            if (window.geofencesLayer) {
                window.geofencesLayer.clearLayers();
            } else {
                window.geofencesLayer = L.layerGroup().addTo(map);
            }

            data.forEach(geofenceData => {
                const color = getColorFromRank(geofenceData.rank);
                
                if (geofenceData.type === 'marker') {
                    // Crea un marker
                    const marker = L.marker([geofenceData.lat, geofenceData.lng], {
                        icon: L.divIcon({
                            className: 'custom-div-icon',
                            html: `<div style="background-color: ${color}; width: 20px; height: 20px; border-radius: 50%;"></div>`,
                            iconSize: [20, 20],
                            iconAnchor: [10, 10]
                        })
                    }).addTo(map);
                    
                    marker.bindPopup(createGeofencePopup(geofenceData.id, true));
                    marker.geofenceId = geofenceData.id;
                    drawnItems.addLayer(marker);

                    const circle = L.circle([geofenceData.lat, geofenceData.lng], {
                        color: 'blue',
                        fillColor: '#30f',
                        fillOpacity: 0.2,
                        radius: neighborhoodRadius
                    }).addTo(map);

                    circles[geofenceData.id] = circle;
                    drawnItems.addLayer(circle);
                } else if (geofenceData.type === 'polygon') {
                    // Crea un poligono
                    const polygon = L.polygon(geofenceData.coordinates.map(coord => [coord[1], coord[0]]), {
                        color: color,
                        fillColor: color,
                        fillOpacity: 0.5,
                        weight: 2
                    }).addTo(map);

                    polygon.bindPopup(createGeofencePopup(geofenceData.id, false));
                    polygon.geofenceId = geofenceData.id;
                    window.geofencesLayer.addLayer(polygon);
                }
            });

            // Adatta la vista della mappa per includere tutti i geofence
            if (drawnItems.getLayers().length > 0 || window.geofencesLayer.getLayers().length > 0) {
                let bounds = L.latLngBounds();
                drawnItems.eachLayer(layer => bounds.extend(layer.getBounds ? layer.getBounds() : layer.getLatLng()));
                window.geofencesLayer.eachLayer(layer => bounds.extend(layer.getBounds()));
                map.fitBounds(bounds);
            }
        })
        .catch(error => {
            console.error('Errore nel caricamento dei geofence:', error);
            if (error.message === 'No questionnaires found') {
                showNoQuestionnaireAlert();
            } else {
                showToast('error', `Errore nel caricamento dei geofence: ${error.message}`);
            }
        });
}

// Carica tutti i geofence quando la pagina è completamente caricata
document.addEventListener('DOMContentLoaded', function() {
    loadAllGeofences();
});



    
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

// ... [Codice precedente rimane invariato]

map.on(L.Draw.Event.CREATED, function (e) {
    let layer = e.layer;

    if (layer instanceof L.Marker) {
        const latlng = layer.getLatLng();
        saveGeofenceToDatabase([{ lat: latlng.lat, lng: latlng.lng }], null)
            .then(response => response.json())
            .then(data => {
                loadAllGeofences(); // Ricarica tutti i geofence dopo l'aggiunta
            })
            .catch(error => console.error('Errore nel salvare il marker:', error));
    } else if (layer instanceof L.Polygon) {
        const coordinates = layer.getLatLngs()[0].map(latlng => ({ lat: latlng.lat, lng: latlng.lng }));
        saveGeofenceToDatabase(null, [coordinates])
            .then(response => response.json())
            .then(data => {
                loadAllGeofences(); // Ricarica tutti i geofence dopo l'aggiunta
            })
            .catch(error => console.error('Errore nel salvare il geofence:', error));
    }
});

// ... [Resto del codice rimane invariato]
function saveGeofenceToDatabase(markers, geofences) {
    let data;
    if (markers && markers.length === 1) {
        data = { marker: markers[0] };
    } else if (geofences && geofences.length > 0) {
        data = { geofence: geofences[0] };
    } else {
        console.error('Nessun marker o geofence valido da salvare.');
        return Promise.reject('Dati non validi');
    }

    return fetch('/save-geofence', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
    });
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


function loadMarkersFromDatabase() {
    fetch('/get_ranked_markers')
        .then(response => response.json())
        .then(data => {
            data.forEach(markerData => {
                const color = getColorFromRank(markerData.rank);
                const marker = L.marker([markerData.lat, markerData.lng], {
                    icon: L.divIcon({
                        className: 'custom-div-icon',
                        html: `<div style="background-color: ${color}; width: 20px; height: 20px; border-radius: 50%;"></div>`,
                        iconSize: [20, 20],
                        iconAnchor: [10, 10]
                    })
                }).addTo(map);
                
                marker.bindPopup(createGeofencePopup(markerData.id, true));
                marker.geofenceId = markerData.id;
                drawnItems.addLayer(marker);

                const circle = L.circle([markerData.lat, markerData.lng], {
                    color: 'blue',
                    fillColor: '#30f',
                    fillOpacity: 0.2,
                    radius: neighborhoodRadius
                }).addTo(map);

                circles[markerData.id] = circle;
                drawnItems.addLayer(circle);
            });
        })
        .catch(error => console.error('Errore nel caricamento dei marker:', error));
}

function loadGeofencesFromDatabase() {
    fetch('/get_ranked_geofences')
        .then(response => response.json())
        .then(data => {
            data.forEach(geofenceData => {
                if (geofenceData.coordinates) {
                    const color = getColorFromRank(geofenceData.rank);
                    const polygon = L.polygon(geofenceData.coordinates.map(coord => [coord[1], coord[0]]), {
                        color: color,
                        fillColor: color,
                        fillOpacity: 0.5
                    }).addTo(map);
                    polygon.bindPopup(createGeofencePopup(geofenceData.id, false));
                    polygon.geofenceId = geofenceData.id;
                    drawnItems.addLayer(polygon);
                }
            });
        })
        .catch(error => console.error('Errore nel caricamento dei geofence:', error));
}


// Carica i marker e i geofence quando la pagina è completamente caricata
document.addEventListener('DOMContentLoaded', function() {
    loadMarkersFromDatabase();
    loadGeofencesFromDatabase();
});


var deleteAllControl = L.Control.extend({
    options: {
        position: 'topleft'
    },
    onAdd: function(map) {
        var container = L.DomUtil.create('div', 'leaflet-control-custom');
        container.innerHTML = '🗑️';
        container.style.backgroundColor = 'white';
        container.style.width = '30px';
        container.style.height = '30px';
        container.style.lineHeight = '30px';
        container.style.textAlign = 'center';
        container.style.cursor = 'pointer';
        container.title = 'Cancella tutti i geofence';

        container.onclick = function(){
            if (confirm('Sei sicuro di voler cancellare tutti i geofence (marker e poligoni)?')) {
                deleteAllGeofences();
            }
        }

        L.DomEvent.disableClickPropagation(container);

        return container;
    }
});

map.addControl(new deleteAllControl());


function deleteAllGeofences() {
    fetch('/delete-all-geofences', {
        method: 'POST',
    })
    .then(response => response.json())
    .then(data => {
        console.log('Tutti i geofence cancellati:', data);
        // Rimuovi tutti i geofence dalla mappa
        drawnItems.clearLayers();
        // Rimuovi tutti i cerchi
        Object.values(circles).forEach(circle => map.removeLayer(circle));
        circles = {};
        // Rimuovi i marker clusterizzati
        databaseMarkers.clearLayers();
        // Rimuovi il layer dei geofence se esiste
        if (window.geofencesLayer) {
            window.geofencesLayer.clearLayers();
        }
        showToast('success', 'Tutti i geofence sono stati cancellati');
    })
    .catch(error => {
        console.error('Errore nella cancellazione dei geofence:', error);
        showToast('error', 'Errore nella cancellazione dei geofence');
    });
}


function removeGeofenceFromMap(geofenceId) {
    console.log('Removing geofence from map:', geofenceId);
    // Rimuovi il marker o il poligono dalla mappa
    drawnItems.eachLayer(function (layer) {
        if (layer.geofenceId === geofenceId) {
            drawnItems.removeLayer(layer);
            map.removeLayer(layer);
        }
    });

    // Se è un marker, rimuovi anche il cerchio associato
    if (circles[geofenceId]) {
        map.removeLayer(circles[geofenceId]);
        delete circles[geofenceId];
    }

    // Se stai usando un layer separato per i geofence, aggiorna anche quello
    if (window.geofencesLayer) {
        window.geofencesLayer.eachLayer(function (layer) {
            if (layer.geofenceId === geofenceId) {
                window.geofencesLayer.removeLayer(layer);
            }
        });
    }

    // Rimuovi anche dal layer dei marker del database, se presente
    databaseMarkers.eachLayer(function (layer) {
        if (layer.geofenceId === geofenceId) {
            databaseMarkers.removeLayer(layer);
        }
    });
}

function createGeofencePopup(geofenceId, isMarker = true) {
    let content = `
        <b>${isMarker ? 'Marker' : 'Geofence'} ID: ${geofenceId}</b><br>
        <button onclick="deleteGeofence(${geofenceId})">
            🗑️ Elimina ${isMarker ? 'Marker' : 'Geofence'}
        </button><br><br>
        
        <!-- Aggiungi il campo input per il prezzo -->
        <label for="priceInput">Prezzo:</label>
        <input type="number" id="priceInput-${geofenceId}" placeholder="Inserisci il prezzo"><br>
        
        <!-- Aggiungi il bottone per salvare il prezzo -->
        <button onclick="addMarkerPrice(${geofenceId})">
            💰 Aggiungi Prezzo
        </button>
    `;
    return content;
}

function deleteGeofence(geofenceId) {
    console.log('Deleting geofence with ID:', geofenceId);
    fetch(`/delete-geofence/${geofenceId}`, {
        method: 'DELETE',
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        console.log('Geofence eliminato:', data);
        removeGeofenceFromMap(geofenceId);
        showToast('success', `Geofence ${geofenceId} eliminato con successo`);
    })
    .catch(error => {
        console.error('Errore nell\'eliminazione del geofence:', error);
        showToast('error', `Errore nell'eliminazione del geofence ${geofenceId}`);
    });
}

function addMarkerPrice(geofenceId) {
    // Ottieni il valore del prezzo inserito dall'input
    let priceInput = document.getElementById(`priceInput-${geofenceId}`).value;
    
    // Verifica che il prezzo sia valido (opzionale)
    if (!priceInput || priceInput <= 0) {
        alert('Per favore, inserisci un prezzo valido.');
        return;
    }

    // Esegui qui la logica per salvare il prezzo, ad esempio con una chiamata API
    // Puoi usare fetch per inviare il prezzo al server
    fetch(`/addMarkerPrice`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            geofenceId: geofenceId,
            price: parseFloat(priceInput)
        })
    })
    .then(response => response.json())
    .then(data => {
        alert(`Prezzo di ${priceInput} aggiunto con successo per il marker ${geofenceId}`);
        // Eventuali altre azioni come aggiornare l'interfaccia
    })
    .catch((error) => {
        console.error('Errore durante l\'aggiunta del prezzo:', error);
    });
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




