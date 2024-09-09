function submitForm() {
    // Ottieni le risposte dal questionario
    const form = document.getElementById('poi-form');
    const formData = new FormData(form);
    const answers = {};

    formData.forEach((value, key) => {
        answers[key] = value;
    });

    // Invia i dati al server Flask
    fetch('/submit-questionnaire', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(answers)
    })
    .then(response => response.json())
    .then(data => {
        alert('Questionario inviato con successo!');
    })
    .catch(error => {
        console.error('Errore:', error);
    });
}