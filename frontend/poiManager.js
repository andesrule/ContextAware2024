// poi config
export const poiConfigs = {
    aree_verdi: {
        emoji: '🌳',
        label: 'Aree Verdi',
        icon: {
            html: '🌳',
            className: 'custom-div-icon',
            iconSize: [30, 30],
            iconAnchor: [15, 15],
            popupAnchor: [0, -15]
        }
    },
    parcheggi: {
        emoji: '🅿️',
        label: 'Parcheggi',
        icon: {
            html: '🅿️',
            className: 'custom-div-icon',
            iconSize: [30, 30],
            iconAnchor: [15, 15],
            popupAnchor: [0, -15]
        }
    },
    fermate_bus: {
        emoji: '🚌',
        label: 'Fermate Bus',
        icon: {
            html: '🚌',
            className: 'custom-div-icon',
            iconSize: [30, 30],
            iconAnchor: [15, 15],
            popupAnchor: [0, -15]
        }
    },
    stazioni_ferroviarie: {
        emoji: '🚉',
        label: 'Stazioni',
        icon: {
            html: '🚉',
            className: 'custom-div-icon',
            iconSize: [30, 30],
            iconAnchor: [15, 15],
            popupAnchor: [0, -15]
        }
    },
    scuole: {
        emoji: '🏫',
        label: 'Scuole',
        icon: {
            html: '🏫',
            className: 'custom-div-icon',
            iconSize: [30, 30],
            iconAnchor: [15, 15],
            popupAnchor: [0, -15]
        }
    },
    cinema: {
        emoji: '🎬',
        label: 'Cinema',
        icon: {
            html: '🎬',
            className: 'custom-div-icon',
            iconSize: [30, 30],
            iconAnchor: [15, 15],
            popupAnchor: [0, -15]
        }
    },
    ospedali: {
        emoji: '🏥',
        label: 'Ospedali',
        icon: {
            html: '🏥',
            className: 'custom-div-icon',
            iconSize: [30, 30],
            iconAnchor: [15, 15],
            popupAnchor: [0, -15]
        }
    },
    farmacia: {
        emoji: '💊',
        label: 'Farmacia',
        icon: {
            html: '💊',
            className: 'custom-div-icon',
            iconSize: [30, 30],
            iconAnchor: [15, 15],
            popupAnchor: [0, -15]
        }
    },
    colonnina_elettrica: {
        emoji: '⚡',
        label: 'Colonnina',
        icon: {
            html: '⚡',
            className: 'custom-div-icon',
            iconSize: [30, 30],
            iconAnchor: [15, 15],
            popupAnchor: [0, -15]
        }
    },
    biblioteca: {
        emoji: '🏢',
        label: 'Biblioteca',
        icon: {
            html: '🏢',
            className: 'custom-div-icon',
            iconSize: [30, 30],
            iconAnchor: [15, 15],
            popupAnchor: [0, -15]
        }
    }
};

// crea un gruppo cluster di poi
function createMarkerClusterGroup() {
    return L.markerClusterGroup({
        showCoverageOnHover: false,
        zoomToBoundsOnClick: true,
        spiderfyOnMaxZoom: true,
        removeOutsideVisibleBounds: true,
        iconCreateFunction: createClusterCustomIcon
    });
}
export let poiLayers = Object.fromEntries(
    Object.keys(poiConfigs).map(type => [type, createMarkerClusterGroup()])
);


// Funzione per ottenere un'icona personalizzata per ogni tipo di POI
export function getCustomIcon(poiType) {
    const config = poiConfigs[poiType];
    return L.divIcon(config.icon || {
        html: '📍',
        className: 'custom-div-icon',
        iconSize: [30, 30],
        iconAnchor: [15, 15],
        popupAnchor: [0, -15]
    });
}


//add listener to poi buttons
export function initializePOIControls(map, showToast) {
    const poiGrid = document.querySelector('#poiGrid');  // Aggiungi questa riga
    if (!poiGrid) {
        console.error('Grid container per i POI non trovato');
        return;
    }

    poiGrid.querySelectorAll('button[data-poi-type]').forEach(button => {
        button.addEventListener('click', function() {
            this.classList.toggle('active');
            const poiType = this.getAttribute('data-poi-type');
            togglePOI(poiType, this.classList.contains('active'), map, showToast);
        });
    });
}

export function togglePOI(poiType, show, map, showToast) {
    if (show) {
        if (!poiLayers[poiType] || poiLayers[poiType].getLayers().length === 0) {
            fetch(`/api/pois/${poiType}`)
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success' && data.data.length > 0) {
                        // Usa createMarkerClusterGroup() se il layer non esiste
                        if (!poiLayers[poiType]) {
                            poiLayers[poiType] = createMarkerClusterGroup();
                        }

                        data.data.forEach(poi => {
                            if (poi.lat && poi.lng) {
                                const marker = L.marker([poi.lat, poi.lng], {
                                    icon: getCustomIcon(poiType)
                                });

                                let popupContent = `
                                    <div class="poi-popup">
                                        <h3>${poi.properties?.denominazione_struttura || 
                                             poi.properties?.denominazi || 
                                             poi.properties?.name || 
                                             poiConfigs[poiType].label}</h3>
                                `;

                                if (poi.properties?.esercizio_via_e_civico) {
                                    popupContent += `<p>Indirizzo: ${poi.properties.esercizio_via_e_civico}</p>`;
                                }
                                if (poi.properties?.quartiere) {
                                    popupContent += `<p>Quartiere: ${poi.properties.quartiere}</p>`;
                                }

                                popupContent += '</div>';
                                marker.bindPopup(popupContent);

                                poiLayers[poiType].addLayer(marker);
                            }
                        });

                        map.addLayer(poiLayers[poiType]);
                        
                        if (poiLayers[poiType].getLayers().length > 0) {
                            map.fitBounds(poiLayers[poiType].getBounds());
                        }
                    }
                })
                .catch(error => {
                    console.error(`Errore nel caricamento dei POI ${poiType}:`, error);
                    showToast('error', `Errore nel caricamento dei ${poiConfigs[poiType].label}`);
                });
        } else {
            map.addLayer(poiLayers[poiType]);
        }
    } else {
        if (poiLayers[poiType]) {
            map.removeLayer(poiLayers[poiType]);
        }
    }
}



// custom cluster icon 
function createClusterCustomIcon(cluster) {
    return L.divIcon({
        html: '<div><span>' + cluster.getChildCount() + '</span></div>',
        className: 'marker-cluster marker-cluster-small',
        iconSize: new L.Point(40, 40)
    });
}