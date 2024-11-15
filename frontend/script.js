let currentPage = 1;
const totalPages = 5;

window.addEventListener("DOMContentLoaded", function () {
  checkQuestionnaires();
});

const menuCheckbox = document.getElementById("menu_checkbox");
menuCheckbox.addEventListener("change", () => {
  document.body.classList.toggle("panel-open");
  setTimeout(() => {
    window.dispatchEvent(new Event("resize"));
  }, 500);
});

async function checkQuestionnaires() {
  try {
    const response = await fetch("/check-questionnaires");
    const data = await response.json();

    const alertsSection = document.querySelector(".collapse");
    const alertsContainer = document.getElementById("alertsContainer");

    if (data.count === 0) {
      alertsSection.classList.add("collapse-open");
      createAlert(
        "Non ci sono questionari nel database. Compilare almeno un questionario per visualizzare i dati."
      );
    } else {
      alertsSection.classList.remove("collapse-open");
      alertsContainer.innerHTML = ""; // Pulisce gli alert esistenti
    }
  } catch (error) {
    console.error("Errore durante il controllo dei questionari:", error);
    createAlert("Errore durante il controllo dei questionari nel database.");
  }
  document.addEventListener("DOMContentLoaded", function () {
    checkQuestionnaires();
  });
}

function createAlert(message, type = "warning") {
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

  const alertsContainer = document.getElementById("alertsContainer");

  // Aggiungi l'alert
  alertsContainer.insertAdjacentHTML("beforeend", alertHTML);

  // Mostra la sezione alerts
  const alertsSection = document.getElementById("alertsSection");
  alertsSection.style.display = "block";

  setTimeout(() => {
    const newAlert = alertsContainer.lastElementChild;
    newAlert.classList.add("show");
  }, 100);
}

//naviga nelle pagine del questionario
function showPage(pageNumber) {
  //nascondi tutte le pagine
  document.querySelectorAll(".questionnaire-page").forEach((page) => {
    page.classList.add("hidden");
  });

  //mostra la pagina corrente
  const currentPageElement = document.querySelector(
    `[data-page="${pageNumber}"]`
  );
  if (currentPageElement) {
    currentPageElement.classList.remove("hidden");
  }

  document.getElementById("currentPage").textContent = pageNumber;

  document.getElementById("prevButton").disabled = pageNumber === 1;
  document.getElementById("nextButton").textContent ="Successiva";
  document.getElementById("nextButton").disabled = pageNumber === totalPages;



}

//pagina successiva
function nextPage() {
  if (currentPage < totalPages) {
    currentPage++;
    showPage(currentPage);
  }
}

//pagina precedente
function previousPage() {
  if (currentPage > 1) {
    currentPage--;
    showPage(currentPage);
  }
}

//invio questionario al backend
function submitForm() {
  const form = document.getElementById("poi-form");
  const formData = new FormData(form);
  const answers = {};

  formData.forEach((value, key) => {
    answers[key] = parseInt(value);
  });


  fetch("/submit-questionnaire", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(answers),
  })
    .then((response) => {
      if (!response.ok) {
        throw new Error(
          `Errore di rete: ${response.status} - ${response.statusText}`
        );
      }
      return response.json();
    })
    .then((data) => {
      console.log("Risposta del server:", data);
      showToast("success", "Questionario inviato con successo!");
      currentPage = 1;
      showPage(1);
    })
    .catch((error) => {
      console.error("Errore durante l'invio del questionario:", error);
      showToast("error", `Si è verificato un errore: ${error.message}`);
    })
    .finally(() => {
      submitButton.innerHTML = originalText;
      submitButton.disabled = false;
    });

    alert("Questionario Inviato")
}

// Funzione per mostrare i toast
function showToast(type, message, duration = 5000) {
  const toast = document.createElement("div");
  toast.className = `alert alert-${type} fixed bottom-4 right-4 z-50`;
  toast.innerHTML = `<span>${message}</span>`;

  document.body.appendChild(toast);

  setTimeout(() => {
    toast.remove();
  }, duration);
}

// Inizializza la prima pagina al caricamento
document.addEventListener("DOMContentLoaded", () => {
  showPage(1);
});

document.addEventListener("DOMContentLoaded", function () {
  const calculateButton = document.getElementById("calculateOptimalPositions");
  if (calculateButton) {
    calculateButton.addEventListener("click", calculateOptimalPositions);
  }
});

function showLoadingOverlay() {
  document.getElementById("loadingOverlay").classList.add("visible");
}

function hideLoadingOverlay() {
  document.getElementById("loadingOverlay").classList.remove("visible");
}

function calculateOptimalPositions(e) {
  e.preventDefault();
  console.log("Calculating optimal positions...");

  const loadingOverlay = document.getElementById("loadingOverlay");
  if (loadingOverlay) {
    loadingOverlay.classList.remove("hidden");
  }

  fetch("/calculate_optimal_locations")
    .then((response) => {
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return response.json();
    })
    .then((data) => {
      console.log("Data received:", data);
      if (data.error) {
        showToast("error", data.error);
        return;
      }

      // Usa la funzione globale da map.js
      window.showOptimalPositions(data.suggestions);
      showToast(
        "success",
        `Trovate ${data.suggestions.length} posizioni ottimali`
      );
    })
    .catch((error) => {
      console.error("Error:", error);
      showToast("error", error.message);
    })
    .finally(() => {
      if (loadingOverlay) {
        loadingOverlay.classList.add("hidden");
      }
    });
}

// Modifica l'event listener in script.js
document.addEventListener("DOMContentLoaded", function () {
  const calculateButton = document.querySelector(
    'button[id="calculateOptimalPositions"]'
  );
  if (calculateButton) {
    calculateButton.addEventListener("click", calculateOptimalPositions);
  }
});

// Funzione per aggiornare l'indice di Moran
function updateMoranIndex() {
  fetch("/calculate_morans_i")
    .then((response) => {
      if (!response.ok) {
        throw new Error("Servono almeno due immobili con prezzo");
      }
      return response.json();
    })
    .then((data) => {
      const moranPrices = document.getElementById("moranPrices");
      const moranPoi = document.getElementById("moranPoi");
      const avgPrice = document.getElementById("avgPrice");
      const numImmobili = document.getElementById("numImmobili");

      if (data.error) {
        showToast("warning", data.error);
        moranPrices.textContent = "N/A";
        moranPoi.textContent = "N/A";
        avgPrice.textContent = "-";
        numImmobili.textContent = "-";
        return;
      }

      // Aggiorna valori e applica classi di colore
      moranPrices.textContent = data.morans_i_prices.toFixed(3);
      moranPrices.className = getValueColorClass(data.morans_i_prices);

      moranPoi.textContent = data.morans_i_poi_density.toFixed(3);
      moranPoi.className = getValueColorClass(data.morans_i_poi_density);

      avgPrice.textContent =
        "€" + data.statistics.prezzo_medio.toLocaleString();
      numImmobili.textContent = data.statistics.num_immobili;
    })
    .catch((error) => {
      console.error("Errore nel recupero dell'indice di Moran:", error);
      showToast("error", "Errore nel calcolo dell'indice di Moran");
    });
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
document.addEventListener("DOMContentLoaded", function () {
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
