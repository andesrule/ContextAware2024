function submitForm() {
  // Ottieni le risposte dal questionario
  const form = document.getElementById("poi-form");
  const formData = new FormData(form);
  const answers = {};

  formData.forEach((value, key) => {
    answers[key] = value;
  });

  // Invia i dati al server Flask
  fetch("/submit-questionnaire", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(answers),
  })
    .then((response) => {
      // Controlla se la risposta è OK (codice HTTP 2xx)
      if (!response.ok) {
        throw new Error(
          `Errore di rete: ${response.status} - ${response.statusText}`
        );
      }
      // Prova a fare il parsing JSON
      return response.json();
    })
    .then((data) => {
      // Se il parsing ha successo, esegui il codice desiderato
      console.log("Risposta del server:", data);
      alert("Questionario inviato con successo!");
    })
    .catch((error) => {
      // Gestisci e logga tutti gli errori di rete o di parsing
      console.error("Errore durante l'invio del questionario:", error);

      // Aggiungi ulteriori dettagli per facilitare il debug
      alert(`Si è verificato un errore: ${error.message}`);
    });
}
