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
    const script = document.createElement('script');
    script.src = 'test_map.js';
    document.body.appendChild(script);

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
    alertsContainer.insertAdjacentHTML('beforeend', alertHTML);

    setTimeout(() => {
        const newAlert = alertsContainer.lastElementChild;
        newAlert.classList.add('show');
    }, 100);
}

async function checkQuestionnaires() {
    try {
        const response = await fetch('/check-questionnaires');
        const data = await response.json();
        
        if (data.count === 0) {
            createAlert('Non ci sono questionari nel database. Compilare almeno un questionario per visualizzare i dati.');
        }
    } catch (error) {
        console.error('Errore durante il controllo dei questionari:', error);
        createAlert('Errore durante il controllo dei questionari nel database.');
    }
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
