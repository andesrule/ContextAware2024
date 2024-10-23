document.addEventListener('DOMContentLoaded', function() {
    // Menu Button
    const menuButton = document.getElementById('menuButton');
    if (menuButton) {
        menuButton.addEventListener('click', function() {
            document.body.classList.toggle('sidebar-open');
        });
    }

    // Close Sidebar Button
    const closeSidebar = document.getElementById('closeSidebar');
    if (closeSidebar) {
        closeSidebar.addEventListener('click', function() {
            document.body.classList.remove('sidebar-open');
        });
    }

    // Open Questionnaire
    const openModalButton = document.getElementById('openModalButton');
    if (openModalButton) {
        openModalButton.addEventListener('click', function() {
            const questionnaire = document.getElementById('questionnaire');
            if (questionnaire) {
                if (questionnaire.classList.contains('hidden')) {
                    questionnaire.classList.remove('hidden');
                } else {
                    questionnaire.classList.add('hidden');
                }
            }
        });
    }

    // Star Rating System
    const stars = document.querySelectorAll('#rating .star');
    const ratingValue = document.getElementById('ratingValue');
    
    if (stars.length > 0 && ratingValue) {
        stars.forEach(star => {
            star.addEventListener('mouseover', function() {
                const value = this.dataset.value;
                updateStars(value);
            });

            star.addEventListener('mouseout', function() {
                const selectedValue = document.querySelector('#rating .star.selected');
                updateStars(selectedValue ? selectedValue.dataset.value : 0);
            });

            star.addEventListener('click', function() {
                const value = this.dataset.value;
                document.querySelector('#rating .star.selected')?.classList.remove('selected');
                this.classList.add('selected');
                ratingValue.textContent = `Rating: ${value}`;
            });
        });
    }

    function updateStars(value) {
        stars.forEach(star => {
            star.classList.toggle('selected', star.dataset.value <= value);
        });
    }
});


window.addEventListener('DOMContentLoaded', function() {

    // Funzione per controllare i questionari nel database
    checkQuestionnaires();
});

const menuCheckbox = document.getElementById('menu_checkbox');
menuCheckbox.addEventListener('change', () => {
    document.body.classList.toggle('panel-open');
    setTimeout(() => {
        window.dispatchEvent(new Event('resize'));
    }, 500);
});

function createAlert(message, type = 'warning', duration = 5000) {
    const alertHTML = `
        <div class="alert bg-yellow-500 border border-yellow-600 rounded-lg p-3 mb-4 flex items-center justify-between space-x-2 text-sm opacity-0 transition-opacity duration-300">
            <div class="flex items-center space-x-2 flex-1">
                <svg class="h-4 w-4 text-yellow-800 flex-shrink-0" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                    <path fill-rule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z" clip-rule="evenodd" />
                </svg>
                <p class="text-yellow-800">${message}</p>
            </div>
            <button class="text-yellow-800 hover:text-yellow-600 font-bold text-xl focus:outline-none" aria-label="Close alert">×</button>
        </div>
    `;

    const alertsContainer = document.getElementById('alertsContainer');
    const alertElement = document.createElement('div');
    alertElement.innerHTML = alertHTML;
    const newAlert = alertElement.firstElementChild;
    
    // Aggiungi l'evento di chiusura al pulsante
    const closeButton = newAlert.querySelector('button');
    closeButton.addEventListener('click', () => {
        newAlert.classList.remove('opacity-100');
        newAlert.classList.add('opacity-0');
        setTimeout(() => {
            newAlert.remove();
            if (alertsContainer.children.length === 0) {
                const alertsSection = document.getElementById('alertsSection');
                if (alertsSection) alertsSection.style.display = 'none';
            }
        }, 300);
    });

    alertsContainer.appendChild(newAlert);

    // Mostra la sezione alerts
    const alertsSection = document.getElementById('alertsSection');
    if (alertsSection) alertsSection.style.display = 'block';

    // Anima l'entrata dell'alert
    setTimeout(() => {
        newAlert.classList.add('opacity-100');
    }, 10);

    // Rimuovi l'alert dopo la durata specificata
    if (duration > 0) {
        setTimeout(() => {
            closeButton.click();
        }, duration);
    }
}

async function checkQuestionnaires() {
    try {
        const response = await fetch('/check-questionnaires');
        const data = await response.json();
        
        const alertsSection = document.querySelector('.collapse');
        const alertsContainer = document.getElementById('alertsContainer');
        
        if (data.count === 0) {
            alertsSection.classList.add('collapse-open');
            createAlert('Non ci sono questionari nel database. Compilare almeno un questionario per visualizzare i dati.');
        } else {
            alertsSection.classList.remove('collapse-open');
            alertsContainer.innerHTML = ''; // Pulisce gli alert esistenti
        }
    } catch (error) {
        console.error('Errore durante il controllo dei questionari:', error);
        createAlert('Errore durante il controllo dei questionari nel database.');
    }
    document.addEventListener('DOMContentLoaded', function() {
        checkQuestionnaires();
    });
}

function createAlert(message, type = 'warning') {
    const alertHTML = `
        <div class="alert bg-yellow-900/50 border border-yellow-700 rounded-lg p-3 mb-4 flex items-start space-x-2 text-sm">
            <svg class="h-4 w-4 text-yellow-400 mt-0.5 flex-shrink-0" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z" clip-rule="evenodd" />
            </svg>
            <div class="flex-1">
                <p class="text-yellow-400">${message}</p>
            </div>
        </div>
    `;

    const alertsContainer = document.getElementById('alertsContainer');
    
    // Aggiungi l'alert
    alertsContainer.insertAdjacentHTML('beforeend', alertHTML);

    // Mostra la sezione alerts
    const alertsSection = document.getElementById('alertsSection');
    alertsSection.style.display = 'block';

    setTimeout(() => {
        const newAlert = alertsContainer.lastElementChild;
        newAlert.classList.add('show');
    }, 100);
}


let currentPage = 1;
const totalPages = 4;

// Funzione per mostrare una pagina specifica
function showPage(pageNumber) {
    // Nascondi tutte le pagine
    document.querySelectorAll('.questionnaire-page').forEach(page => {
        page.classList.add('hidden');
    });
    
    // Mostra la pagina corrente
    const currentPageElement = document.querySelector(`[data-page="${pageNumber}"]`);
    if (currentPageElement) {
        currentPageElement.classList.remove('hidden');
    }

    // Aggiorna il numero di pagina corrente
    document.getElementById('currentPage').textContent = pageNumber;

    // Gestisci lo stato dei pulsanti
    document.getElementById('prevButton').disabled = pageNumber === 1;
    document.getElementById('nextButton').textContent = pageNumber === totalPages ? 'Fine' : 'Successiva';
    
    // Mostra/nascondi il pulsante di invio
    const submitButton = document.getElementById('submitButton');
    submitButton.classList.toggle('hidden', pageNumber !== totalPages);
}

// Funzione per passare alla pagina successiva
function nextPage() {
    if (currentPage < totalPages) {
        currentPage++;
        showPage(currentPage);
    }
}

// Funzione per tornare alla pagina precedente
function previousPage() {
    if (currentPage > 1) {
        currentPage--;
        showPage(currentPage);
    }
}

// Funzione per gestire l'invio del questionario
function submitForm() {
    const form = document.getElementById('poi-form');
    const formData = new FormData(form);
    const answers = {};
    
    formData.forEach((value, key) => {
        answers[key] = parseInt(value);
    });

    // Mostra un loading state sul pulsante
    const submitButton = document.getElementById('submitButton');
    const originalText = submitButton.innerHTML;
    submitButton.innerHTML = '<span class="loading loading-spinner"></span> Invio...';
    submitButton.disabled = true;

    fetch('/submit-questionnaire', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(answers)
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`Errore di rete: ${response.status} - ${response.statusText}`);
        }
        return response.json();
    })
    .then(data => {
        console.log('Risposta del server:', data);
        showToast('success', 'Questionario inviato con successo!');
        // Resetta il questionario alla prima pagina
        currentPage = 1;
        showPage(1);
    })
    .catch(error => {
        console.error('Errore durante l\'invio del questionario:', error);
        showToast('error', `Si è verificato un errore: ${error.message}`);
    })
    .finally(() => {
        submitButton.innerHTML = originalText;
        submitButton.disabled = false;
    });
}

// Funzione per mostrare i toast
function showToast(type, message, duration = 5000) {
    const toast = document.createElement('div');
    toast.className = `alert alert-${type} fixed bottom-4 right-4 z-50`;
    toast.innerHTML = `<span>${message}</span>`;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.remove();
    }, duration);
}


// Inizializza la prima pagina al caricamento
document.addEventListener('DOMContentLoaded', () => {
    showPage(1);
});



const distanceToggle = document.getElementById('distanceToggle');
const distanceMethod = document.getElementById('distanceMethod');
const travelMode = document.getElementById('travelMode');



// Add event listener for the travel mode select
travelMode.addEventListener('change', function() {
    console.log('Travel mode changed to:', this.value);
    // You can add more functionality here in the future
});

// Function to get current distance calculation method
function getDistanceMethod() {
    return distanceToggle.checked ? 'travel-time' : 'straight-line';
}

// Function to get current travel mode
function getTravelMode() {
    return travelMode.value;
}


document.addEventListener('DOMContentLoaded', function() {
    const calculateButton = document.getElementById('calculateOptimalPositions');
    if (calculateButton) {
        calculateButton.addEventListener('click', calculateOptimalPositions);
    }
});

function showLoadingOverlay() {
    document.getElementById('loadingOverlay').classList.add('visible');
}

function hideLoadingOverlay() {
    document.getElementById('loadingOverlay').classList.remove('visible');
}


function calculateOptimalPositions() {
    const loadingOverlay = document.getElementById('loadingOverlay');
    loadingOverlay.classList.add('visible');

    showToast('info', 'Calcolo delle posizioni ottimali in corso. Questo potrebbe richiedere alcuni minuti.');

    fetch('/calculate_optimal_locations')
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            loadingOverlay.classList.remove('visible');
            if (data.error) {
                showToast('error', data.error);
                return;
            }
            showOptimalPositions(data.suggestions);
            showToast('success', 'Posizioni ottimali calcolate e visualizzate sulla mappa');
        })
        .catch(error => {
            loadingOverlay.classList.remove('visible');
            console.error('Errore nel calcolo delle posizioni ottimali:', error);
            showToast('error', `Errore nel calcolo delle posizioni ottimali: ${error.message}`);
        });
}


function showOptimalPositions(positions) {
    // Rimuovi i marker ottimali esistenti, se presenti
    if (window.optimalPositionsLayer) {
        map.removeLayer(window.optimalPositionsLayer);
    }
    
    window.optimalPositionsLayer = L.layerGroup().addTo(map);

    positions.forEach((pos, index) => {
        const marker = L.marker([pos.lat, pos.lng], {
            icon: L.divIcon({
                className: 'custom-div-icon',
                html: `<div style="background-color: #00FF00; color: black; width: 25px; height: 25px; border-radius: 50%; display: flex; justify-content: center; align-items: center; font-weight: bold;">${index + 1}</div>`,
                iconSize: [25, 25],
                iconAnchor: [12, 12]
            })
        });
        
        marker.bindPopup(`Posizione ottimale #${index + 1}<br>Rank: ${pos.rank.toFixed(2)}`);
        window.optimalPositionsLayer.addLayer(marker);
    });

    // Zoom della mappa per mostrare tutti i marker ottimali
    const bounds = L.latLngBounds(positions.map(pos => [pos.lat, pos.lng]));
    map.fitBounds(bounds);
}




// Funzione per aggiornare l'indice di Moran
function updateMoranIndex() {
    fetch('/calculate_morans_i')
        .then(response => {
            if (!response.ok) {
                throw new Error('Servono almeno due immobili con prezzo');
            }
            return response.json();
        })
        .then(data => {
            const moranPrices = document.getElementById('moranPrices');
            const moranPoi = document.getElementById('moranPoi');
            const avgPrice = document.getElementById('avgPrice');
            const numImmobili = document.getElementById('numImmobili');

            if (data.error) {
                showToast('warning', data.error);
                moranPrices.textContent = 'N/A';
                moranPoi.textContent = 'N/A';
                avgPrice.textContent = '-';
                numImmobili.textContent = '-';
                return;
            }

            // Aggiorna valori e applica classi di colore
            moranPrices.textContent = data.morans_i_prices.toFixed(3);
            moranPrices.className = getValueColorClass(data.morans_i_prices);

            moranPoi.textContent = data.morans_i_poi_density.toFixed(3);
            moranPoi.className = getValueColorClass(data.morans_i_poi_density);

            avgPrice.textContent = '€' + data.statistics.prezzo_medio.toLocaleString();
            numImmobili.textContent = data.statistics.num_immobili;
        })
        .catch(error => {
            console.error('Errore nel recupero dell\'indice di Moran:', error);
            showToast('error', 'Errore nel calcolo dell\'indice di Moran');
        });
}

// Funzione per determinare la classe di colore in base al valore
function getValueColorClass(value) {
    if (value === null) return 'text-gray-500';
    if (value > 0.5) return 'text-green-500';  // clustering forte
    if (value > 0) return 'text-blue-500';     // clustering debole
    if (value < -0.5) return 'text-red-500';   // dispersione forte
    return 'text-yellow-500';                  // dispersione debole/random
}

// Modifica le funzioni esistenti per aggiornare l'indice quando necessario
const originalSetPrice = setPrice;
function setPrice(marker, price) {
    originalSetPrice(marker, price);
    updateMoranIndex(); // Aggiorna l'indice dopo aver impostato un prezzo
}

const originalRemoveMarker = removeMarker;
function removeMarker(markerToRemove) {
    originalRemoveMarker(markerToRemove);
    updateMoranIndex(); // Aggiorna l'indice dopo aver rimosso un marker
}

// Aggiungi l'inizializzazione al DOMContentLoaded esistente
document.addEventListener('DOMContentLoaded', function() {
    // Il tuo codice DOMContentLoaded esistente...
    
    // Aggiungi l'inizializzazione dell'indice di Moran
    updateMoranIndex();
    
    // Imposta l'aggiornamento automatico ogni 5 secondi
    setInterval(updateMoranIndex, 5000);
    
    // Il resto del tuo codice DOMContentLoaded...
});

// Modifica la funzione addMarker esistente per includere l'aggiornamento dell'indice
const originalAddMarker = addMarker;
function addMarker(e) {
    originalAddMarker(e);
    updateMoranIndex(); // Aggiorna l'indice dopo aver aggiunto un marker
}