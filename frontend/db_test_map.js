    // Funzione per inviare i geofence (marker o poligoni) al backend
    function saveGeofenceToDatabase(markers, geofences) {
        fetch('/save-geofence', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ markers: markers, geofences: geofences }),
        })
        .then(response => response.json())
        .then(data => {
            console.log('Geofence salvato con successo:', data);
        })
        .catch(error => {
            console.error('Errore durante il salvataggio del geofence:', error);
        });
    }

