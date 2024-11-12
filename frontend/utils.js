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

export function showToast(type, message) {
    const toast = document.createElement('div');
    toast.className = `alert ${type === 'success' ? 'alert-success' : 'alert-error'} fixed bottom-4 right-4 z-50`;
    toast.innerHTML = `<span>${message}</span>`;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.remove();
    }, 3000);
}

export function createGeofencePopup(geofenceId, isMarker = true) {
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