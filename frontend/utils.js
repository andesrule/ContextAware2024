export function showNoQuestionnaireAlert() {
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

export function getColorFromRank(rank) {
    if (rank < 70) return '#FF0000';      // Rosso
    else if (rank < 90) return '#FFA500'; // Arancione
    else if (rank < 120) return '#FFFF00'; // Giallo
    else if (rank < 150) return '#90EE90'; // Verde chiaro
    else return '#008000';                // Verde scuro
}

export function getCustomIcon(poiType) {
    const iconMap = {
        aree_verdi: '🌳',
        parcheggi: '🅿️',
        fermate_bus: '🚌',
        stazioni_ferroviarie: '🚉',
        scuole: '🏫',
        cinema: '🎬',
        ospedali: '🏥',
        farmacia: '💊',
        colonnina_elettrica: '⚡',
        biblioteca: '🏢'
    };

    return L.divIcon({
        html: iconMap[poiType] || '📍',
        className: 'custom-div-icon',
        iconSize: [30, 30],
        iconAnchor: [15, 15],
        popupAnchor: [0, -15]
    });
}

export function createClusterCustomIcon(cluster) {
    return L.divIcon({
        html: `<div><span>${cluster.getChildCount()}</span></div>`,
        className: 'marker-cluster marker-cluster-small',
        iconSize: new L.Point(40, 40)
    });
}

export const poiConfigs = {
    aree_verdi: { emoji: '🌳', label: 'Aree Verdi' },
    parcheggi: { emoji: '🅿️', label: 'Parcheggi' },
    fermate_bus: { emoji: '🚌', label: 'Fermate Bus' },
    stazioni_ferroviarie: { emoji: '🚉', label: 'Stazioni' },
    scuole: { emoji: '🏫', label: 'Scuole' },
    cinema: { emoji: '🎬', label: 'Cinema' },
    ospedali: { emoji: '🏥', label: 'Ospedali' },
    farmacia: { emoji: '💊', label: 'Farmacia' },
    colonnina_elettrica: { emoji: '⚡', label: 'Colonnina' },
    biblioteca: { emoji: '🏢', label: 'Biblioteca' }
};


export function createMarker(map, drawnItems, circles, data, color, neighborhoodRadius) {
    const marker = L.marker([data.lat, data.lng], {
        icon: L.divIcon({
            className: 'custom-div-icon',
            html: `<div style="background-color: ${color}; width: 20px; height: 20px; border-radius: 50%;"></div>`,
            iconSize: [20, 20],
            iconAnchor: [10, 10]
        })
    }).addTo(map);

    marker.bindPopup(createGeofencePopup(data.id, true));
    marker.geofenceId = data.id;
    drawnItems.addLayer(marker);

    const circle = L.circle([data.lat, data.lng], {
        color: 'blue',
        fillColor: '#30f',
        fillOpacity: 0.2,
        radius: neighborhoodRadius
    }).addTo(map);

    circles[data.id] = circle;
    drawnItems.addLayer(circle);
}

export function createPolygon(map, data, color, geofencesLayer) {
    const polygon = L.polygon(data.coordinates.map(coord => [coord[1], coord[0]]), {
        color: color,
        fillColor: color,
        fillOpacity: 0.5,
        weight: 2
    }).addTo(map);

    polygon.bindPopup(createGeofencePopup(data.id, false));
    polygon.geofenceId = data.id;
    geofencesLayer.addLayer(polygon);
}


export function showToast(type, message) {
    const toast = document.createElement('div');
    toast.className = `alert ${type === 'success' ? 'alert-success' : 'alert-error'} fixed bottom-4 right-4 z-50`;
    toast.innerHTML = `<span>${message}</span>`;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.remove();
    }, 3000);
}


