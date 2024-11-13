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