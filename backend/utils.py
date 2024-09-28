# distance_calculator.py
from shapely.geometry import Point

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

def calculate_poi_distances(geometry, poi_data):
    # Verifica se la risposta contiene 'results' anziché 'records'
    if 'results' not in poi_data:
        print("Errore: 'results' non presente nella risposta API:", poi_data)
        return []

    distances = []
    for result in poi_data['results']:
        # Estrarre le coordinate dai risultati
        poi_coordinates = result['coordinate']

        if poi_coordinates:
            # Latitudine e longitudine in 'lat' e 'lon'
            poi_point = Point(poi_coordinates['lon'], poi_coordinates['lat'])

            # Calcola la distanza usando shapely
            distance = geometry.distance(poi_point)

            # Log per verificare le distanze calcolate
            print(f"Calcolo distanza tra {geometry} e {poi_point}: {distance}")

            distances.append({
                'poi_name': result.get('parcheggio', 'Unnamed POI'),
                'distance': distance
            })
        else:
            print(f"Impossibile estrarre le coordinate per POI: {result}")

    return distances
