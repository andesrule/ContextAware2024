// JavaScript to handle sidebar toggle
document.getElementById('menuButton').addEventListener('click', function() {
    document.body.classList.toggle('sidebar-open');
});

document.getElementById('closeSidebar').addEventListener('click', function() {
    document.body.classList.remove('sidebar-open');
});

// JavaScript to handle star rating
const stars = document.querySelectorAll('#rating .star');
const ratingValue = document.getElementById('ratingValue');

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

function updateStars(value) {
    stars.forEach(star => {
        star.classList.toggle('selected', star.dataset.value <= value);
    });
}

// Initialize Leaflet map
document.addEventListener('DOMContentLoaded', function() {
    var map = L.map('map').setView([44.4936, 11.3430], 13); // Coordinates for Bologna

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);

    L.marker([44.4936, 11.3430]).addTo(map)
        .bindPopup('Bologna')
        .openPopup();
});
