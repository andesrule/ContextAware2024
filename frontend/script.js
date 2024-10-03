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
