
//restituisci colore in base al rank 
export function getColorFromRank(rank) {
  if (rank < 20) return "#FF0000"; // Rosso (0-19)
  else if (rank < 40) return "#FFA500"; // Arancione (20-39)
  else if (rank < 60) return "#FFFF00"; // Giallo (40-59)
  else if (rank < 80) return "#05C953"; // Verde chiaro (60-79)
  else return "#2038AF"; // Blu (80-100)
}

//icon per quicksettings
export function getCustomIcon(poiType) {
  const iconMap = {
    aree_verdi: "🌳",
    parcheggi: "🅿️",
    fermate_bus: "🚌",
    stazioni_ferroviarie: "🚉",
    scuole: "🏫",
    cinema: "🎬",
    ospedali: "🏥",
    farmacia: "💊",
    colonnina_elettrica: "⚡",
    biblioteca: "🏢",
  };

  return L.divIcon({
    html: iconMap[poiType] || "📍",
    className: "custom-div-icon",
    iconSize: [30, 30],
    iconAnchor: [15, 15],
    popupAnchor: [0, -15],
  });
}

//icona per cluster di marker
export function createClusterCustomIcon(cluster) {
  return L.divIcon({
    html: `<div><span>${cluster.getChildCount()}</span></div>`,
    className: "marker-cluster marker-cluster-small",
    iconSize: new L.Point(40, 40),
  });
}

//config per quicksettings poi
export const poiConfigs = {
  aree_verdi: { emoji: "🌳", label: "Aree Verdi" },
  parcheggi: { emoji: "🅿️", label: "Parcheggi" },
  fermate_bus: { emoji: "🚌", label: "Fermate Bus" },
  stazioni_ferroviarie: { emoji: "🚉", label: "Stazioni" },
  scuole: { emoji: "🏫", label: "Scuole" },
  cinema: { emoji: "🎬", label: "Cinema" },
  ospedali: { emoji: "🏥", label: "Ospedali" },
  farmacia: { emoji: "💊", label: "Farmacia" },
  colonnina_elettrica: { emoji: "⚡", label: "Colonnina" },
  biblioteca: { emoji: "🏢", label: "Biblioteca" },
};

//marker
export function createMarker(
  map,
  drawnItems,
  circles,
  data,
  color,
  neighborhoodRadius
) {
  const marker = L.marker([data.lat, data.lng], {
    icon: L.divIcon({
      className: "custom-div-icon",
      html: `<div style="background-color: ${color}; width: 20px; height: 20px; border-radius: 50%;"></div>`,
      iconSize: [20, 20],
      iconAnchor: [10, 10],
    }),
  }).addTo(map);

  marker.bindPopup(createGeofencePopup(data.id, true));
  marker.geofenceId = data.id;
  drawnItems.addLayer(marker);

  const circle = L.circle([data.lat, data.lng], {
    color: "blue",
    fillColor: "#30f",
    fillOpacity: 0.2,
    radius: neighborhoodRadius,
  }).addTo(map);

  circles[data.id] = circle;
  drawnItems.addLayer(circle);
}

//poligono
export function createPolygon(map, data, color, geofencesLayer) {
  const polygon = L.polygon(
    data.coordinates.map((coord) => [coord[1], coord[0]]),
    {
      color: color,
      fillColor: color,
      fillOpacity: 0.5,
      weight: 2,
    }
  ).addTo(map);

  polygon.bindPopup(createGeofencePopup(data.id, false));
  polygon.geofenceId = data.id;
  geofencesLayer.addLayer(polygon);
}



//popup posizione ottimale
export function createOptimalPopup(pos, index) {
  const popupContent = document.createElement("div");
  popupContent.className = "p-2";

  const title = document.createElement("div");
  title.className = "font-bold mb-2";
  title.textContent = `Posizione ottimale #${index + 1}`;
  popupContent.appendChild(title);

  const rankInfo = document.createElement("div");
  rankInfo.className = "mb-2";
  rankInfo.textContent = `Rank: ${pos.rank.toFixed(2)}`;
  popupContent.appendChild(rankInfo);

  if (pos.poi_details) {
    const poiSection = document.createElement("div");
    poiSection.className = "mt-2";

    const poiTitle = document.createElement("div");
    poiTitle.className = "font-bold mb-1";
    poiTitle.textContent = "POI nelle vicinanze:";
    poiSection.appendChild(poiTitle);

    const poiList = document.createElement("ul");
    poiList.className = "list-disc pl-4";

    Object.entries(pos.poi_details.details).forEach(([type, count]) => {
      if (count > 0) {
        const li = document.createElement("li");
        li.textContent = `${poiConfigs[type]?.label || type}: ${count}`;
        poiList.appendChild(li);
      }
    });

    poiSection.appendChild(poiList);

    const totalPoi = document.createElement("div");
    totalPoi.className = "mt-2";
    totalPoi.textContent = `Totale POI: ${pos.poi_details.total_poi}`;
    poiSection.appendChild(totalPoi);

    popupContent.appendChild(poiSection);
  }

  return popupContent;
}
