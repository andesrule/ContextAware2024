import { 
    poiConfigs,
    initializePOIControls,
    togglePOI,
    getCustomIcon,
    poiLayers
    
} from './poiManager.js';  

// Inizializza la mappa centrata su Bologna
let map = L.map('map').setView([44.4949, 11.3426], 13);
let neighborhoodRadius = 500; // Raggio iniziale in metri
let circles = {};

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors'
}).addTo(map);






//centra la mappa su Bologna
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


document.addEventListener('DOMContentLoaded', function() {
    initializePOIControls(map, showToast);
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
        <div class="p-2">
            <b class="text-dark-200 mb-2 block">${isMarker ? 'Marker' : 'Geofence'} ID: ${geofenceId}</b>
            
            <button onclick="deleteGeofence(${geofenceId})" 
                    class="bg-red-500 hover:bg-red-600 text-white px-3 py-1 rounded flex items-center gap-2 mb-3 w-full">
                <span>🗑️</span> Elimina ${isMarker ? 'Marker' : 'Geofence'}
            </button>
    `;

    if (isMarker) {
        content += `
            <div class="space-y-2">
                <label for="priceInput-${geofenceId}" class="text-dark-200 block">Prezzo:</label>
                <input type="number" 
                       id="priceInput-${geofenceId}" 
                       placeholder="Inserisci il prezzo"
                       class="bg-gray-700 text-gray-200 rounded px-2 py-1 w-full border border-gray-600 focus:border-blue-500 focus:outline-none">
                
                <button onclick="addMarkerPrice(${geofenceId})"
                        class="bg-green-600 hover:bg-green-700 text-white px-3 py-1 rounded flex items-center gap-2 w-full">
                    <span>💰</span> Aggiungi Prezzo
                </button>
            </div>
        `;
    }

    content += '</div>';
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





function handleFilters() {

    // Raccoglie i valori dai controlli

    const distanceFilter = document.getElementById('distanceToggle').checked;

    const travelMode = document.getElementById('travelMode').value;

    const filterTime = document.getElementById('filterTime').value;



    // Prepara i dati per l'invio

    const filterData = {

        distanceEnabled: distanceFilter,

        travelMode: travelMode,

        travelTime: parseInt(filterTime)

    };

    console.log("Dati inviati al backend:", filterData);

    // Invia la richiesta all'endpoint

    fetch('/api/filters', {

        method: 'POST',

        headers: {

            'Content-Type': 'application/json',

        },

        body: JSON.stringify(filterData)

    })

    .then(response => response.json())

    .then(data => {

        console.log('Success:', data);

        // Qui puoi gestire la risposta dal server

    })

    .catch((error) => {

        console.error('Error:', error);

    });

}


// Aggiungi event listeners per reagire ai cambiamenti

document.getElementById('distanceToggle').addEventListener('change', handleFilters);

document.getElementById('travelMode').addEventListener('change', handleFilters);

document.getElementById('filterTime').addEventListener('change', handleFilters);



