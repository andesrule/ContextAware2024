document.addEventListener('DOMContentLoaded', function () {
    // Fetch dati Geofence
    fetch('/get-geofences')
        .then(response => response.json())
        .then(data => {
            const tableBody = document.querySelector('#geofencesTable tbody');
            tableBody.innerHTML = ''; // Pulisci la tabella esistente

            data.forEach(item => {
                const row = document.createElement('tr');

                const idCell = document.createElement('td');
                idCell.textContent = item.id;
                row.appendChild(idCell);

                const markersCell = document.createElement('td');
                markersCell.textContent = JSON.stringify(item.markers);
                row.appendChild(markersCell);

                const geofencesCell = document.createElement('td');
                geofencesCell.textContent = JSON.stringify(item.geofences);
                row.appendChild(geofencesCell);

                tableBody.appendChild(row);
            });
        })
        .catch(error => {
            console.error('Error fetching geofences:', error);
        });


// Fetch dati User
    fetch('/get-users')
        .then(response => response.json())
        .then(data => {
            const tableBody = document.querySelector('#usersTable tbody');
            tableBody.innerHTML = ''; // Pulisci la tabella esistente

            data.forEach(item => {
                const row = document.createElement('tr');

                const idCell = document.createElement('td');
                idCell.textContent = item.id;
                row.appendChild(idCell);

                const contentCell = document.createElement('td');
                contentCell.textContent = JSON.stringify(item.content_poi);
                row.appendChild(contentCell);

                tableBody.appendChild(row);
            });
        })
        .catch(error => {
            console.error('Error fetching users:', error);
        });

    // Fetch dati Questionario
    fetch('/get-questionnaire-responses')
        .then(response => response.json())
        .then(data => {
            const tableBody = document.querySelector('#questionnaireTable tbody');
            tableBody.innerHTML = ''; // Pulisci la tabella esistente

            data.forEach(item => {
                const row = document.createElement('tr');

                const idCell = document.createElement('td');
                idCell.textContent = item.id;
                row.appendChild(idCell);

                const areeVerdiCell = document.createElement('td');
                areeVerdiCell.textContent = item.aree_verdi;
                row.appendChild(areeVerdiCell);

                const parcheggiCell = document.createElement('td');
                parcheggiCell.textContent = item.parcheggi;
                row.appendChild(parcheggiCell);

                const fermateBusCell = document.createElement('td');
                fermateBusCell.textContent = item.fermate_bus;
                row.appendChild(fermateBusCell);

                const supermercatiCell = document.createElement('td');
                supermercatiCell.textContent = item.supermercati;
                row.appendChild(supermercatiCell);

                const scuoleCell = document.createElement('td');
                scuoleCell.textContent = item.scuole;
                row.appendChild(scuoleCell);

                const ristorantiCell = document.createElement('td');
                ristorantiCell.textContent = item.ristoranti;
                row.appendChild(ristorantiCell);

                const ospedaliCell = document.createElement('td');
                ospedaliCell.textContent = item.ospedali;
                row.appendChild(ospedaliCell);

                const cinemaCell = document.createElement('td');
                cinemaCell.textContent = item.cinema;
                row.appendChild(cinemaCell);

                const parchiGiochiCell = document.createElement('td');
                parchiGiochiCell.textContent = item.parchi_giochi;
                row.appendChild(parchiGiochiCell);
                
                const palestreCell = document.createElement('td');
                palestreCell.textContent = item.palestre;
                row.appendChild(palestreCell);

                tableBody.appendChild(row);
            });
        })
        .catch(error => {
            console.error('Error fetching questionnaire responses:', error);
        });
});
