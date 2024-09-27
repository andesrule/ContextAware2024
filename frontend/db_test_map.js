// Funzione per inviare i geofence (marker o poligoni) al backend
// Funzione per inviare i geofence (marker o poligoni) al backend
function saveGeofenceToDatabase(markers, geofences) {
    let data;
    if (markers && markers.length === 1) {
        data = { marker: markers[0] };
    } else if (geofences && geofences.length > 0) {
        data = { geofence: geofences[0] };
    } else {
        console.error('Nessun marker o geofence valido da salvare.');
        return;
    }

    fetch('/save-geofence', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            console.log('Geofence salvato con successo:', data);
        } else {
            console.error('Errore durante il salvataggio:', data.message);
        }
    })
    .catch(error => {
        console.error('Errore durante la richiesta:', error);
    });
}