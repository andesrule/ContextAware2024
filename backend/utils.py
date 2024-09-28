# distance_calculator.py
from shapely.geometry import Point
from pyproj import Proj, Transformer

# utils.py
# utils.py
# utils.py
# utils.py
def extract_poi_coordinates(record):
    """
    Funzione per estrarre le coordinate dai diversi formati delle API.
    """
    # Caso 1: formato per le farmacie (coordinate in 'point')
    if 'point' in record:
        return [record['point']['lat'], record['point']['lon']]
    
    # Caso 2: formato per le aree verdi, parcheggi, scuole, cinema, ospedali e luoghi di culto (coordinate in 'geopoint')
    if 'geopoint' in record:
        return [record['geopoint']['lat'], record['geopoint']['lon']]
    
    # Caso 3: altri POI con coordinate in 'geo_point_2d'
    if 'geo_point_2d' in record:
        return [record['geo_point_2d'][0], record['geo_point_2d'][1]]
    
    # Se nessun formato è trovato
    return None

# utils.py
from shapely.geometry import Point

# utils.py
def extract_poi_coordinates(record):
    """
    Funzione per estrarre le coordinate dai diversi formati delle API.
    """
    # Caso 1: formato per le farmacie (coordinate in 'point')
    if 'point' in record:
        return [record['point']['lat'], record['point']['lon']]
    
    # Caso 2: formato per le aree verdi, parcheggi, scuole, cinema, ospedali e luoghi di culto (coordinate in 'geopoint')
    if 'geopoint' in record:
        return [record['geopoint']['lat'], record['geopoint']['lon']]
    
    # Caso 3: formato per altri POI con 'geo_point_2d'
    if 'geo_point_2d' in record:
        # Gestisci sia il caso in cui geo_point_2d sia una lista che un oggetto
        if isinstance(record['geo_point_2d'], list):
            return [record['geo_point_2d'][0], record['geo_point_2d'][1]]
        else:
            return [record['geo_point_2d']['lat'], record['geo_point_2d']['lon']]
    
    # Caso 4: altri formati
    if 'coordinate' in record:
        return [record['coordinate']['lat'], record['coordinate']['lon']]
    
    return None

from shapely.ops import transform
from pyproj import Proj, Transformer

# Funzione aggiornata per calcolare la distanza in metri
def calculate_poi_distances(geometry, poi_data):
    distances = []

    # Converti il punto di riferimento (marker) in una proiezione in metri (come UTM)
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)  # Da WGS84 a Mercatore
    projected_marker = transform(transformer.transform, geometry)

    for record in poi_data['results']:
        poi_coordinates = extract_poi_coordinates(record)

        if poi_coordinates:
            # Converti il POI in una proiezione in metri
            poi_point = Point(poi_coordinates[1], poi_coordinates[0])
            projected_poi = transform(transformer.transform, poi_point)
            
            # Calcola la distanza in metri
            distance = projected_marker.distance(projected_poi)
            distances.append({
                'poi_name': record.get('denominazi') or record.get('denominazione_struttura') or record.get('farmacia', 'Unnamed POI'),
                'distance': distance
            })
        else:
            print(f"Impossibile estrarre le coordinate per POI: {record}")
    
    return distances


