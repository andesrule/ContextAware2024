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

      if (data.count === 0) {
          alert("Non ci sono questionari nel database. Compilare almeno un questionario per visualizzare i dati.");
      }
  } catch (error) {
      console.error("Errore durante il controllo dei questionari:", error);
      alert("Errore durante il controllo dei questionari nel database.");
  }
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
              if (response.status === 400) {
                  throw new Error("Devi prima compilare il questionario per calcolare le posizioni ottimali");
              }
              throw new Error(`HTTP error! status: ${response.status}`);
          }
          return response.json();
      })
      .then((data) => {
          console.log("Data received:", data);
          if (data.error) {
              alert(data.error);
              return;
          }

          // Usa la funzione globale da map.js
          window.showOptimalPositions(data.suggestions);
      })
      .catch((error) => {
          console.error("Error:", error);
          alert(error.message);
      })
      .finally(() => {
          if (loadingOverlay) {
              loadingOverlay.classList.add("hidden");
          }
      });
}

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

});

// Modifica la funzione addMarker esistente per includere l'aggiornamento dell'indice
const originalAddMarker = addMarker;
function addMarker(e) {
  originalAddMarker(e);
  updateMoranIndex(); // Aggiorna l'indice dopo aver aggiunto un marker
}
