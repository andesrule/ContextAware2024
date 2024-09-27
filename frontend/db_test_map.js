// Funzione per inviare i geofence (marker o poligoni) al backend
// Funzione per inviare i geofence (marker o poligoni) al backend
function saveGeofenceToDatabase(markers, geofences) {
    // Verifica se i marker sono validi e non null
    if (markers && markers.length === 1) {
        // Invia il singolo marker
        fetch('/save-geofence', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ marker: markers[0] }),  // Invia il singolo marker
        })
        .then(response => response.json())
        .then(data => {
            console.log('Marker salvato con successo:', data);
        })
        .catch(error => {
            console.error('Errore durante il salvataggio del marker:', error);
        });
    }
    // Verifica se esistono i geofence
    else if (geofences && geofences.length > 0) {
        // Invia un geofence
        fetch('/save-geofence', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ geofence: geofences }),  // Invia il geofence
        })
        .then(response => response.json())
        .then(data => {
            console.log('Geofence salvato con successo:', data);
        })
        .catch(error => {
            console.error('Errore durante il salvataggio del geofence:', error);
        });
    } else {
        console.error('Nessun marker o geofence valido da salvare.');
    }
}
