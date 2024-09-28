# test_utils.py
from utils import extract_poi_coordinates, calculate_poi_distances
from shapely.geometry import Point

# Dati di test basati sulla risposta dell'API delle farmacie
test_data_farmacia = {
    "area_stati": "EMILIA PONENTE",
    "civkey": "058000028000",
    "farmacia": "COMUNALE BATTINDARNO",
    "indirizzo": "VIA BATTINDARNO, 28",
    "point": {
        "lat": 44.50582724111065,
        "lon": 11.302028776971122
    }
}

# Dati di test basati sulla risposta per parcheggi, scuole, cinema, ecc. con 'geopoint'
test_data_geopoint = {
    "area_statistica": "RIGOSA",
    "geopoint": {
        "lat": 44.511873,
        "lon": 11.238742
    },
    "denominazione": "RIGOSA CHIESA"
}

# Dati di test basati su altri POI con 'geo_point_2d'
test_data_geo_point_2d = {
    "record": {
        "fields": {
            "geo_point_2d": [44.501153, 11.336062]
        }
    }
}

# Marker simulato (un punto con latitudine e longitudine)
test_marker = Point(11.336062, 44.501153)

# Dati simulati dall'API dei POI per parcheggi, scuole, ecc.
# Dati simulati dall'API dei POI per parcheggi, scuole, ecc.
test_poi_data = {
    'results': [
        {
            'geo_point_2d': [44.501153, 11.336062],  # Usare una lista per lat/lon
            'denominazi': 'Scuola A'
        },
        {
            'geopoint': {'lat': 44.505827, 'lon': 11.302028},
            'denominazione_struttura': 'Ospedale B'
        },
        {
            # Modifica le coordinate della Farmacia C
            'point': {'lat': 44.510000, 'lon': 11.290000},
            'farmacia': 'Farmacia C'
        }
    ]
}

# Test per extract_poi_coordinates
def test_extract_poi_coordinates():
    # Test per farmacie
    assert extract_poi_coordinates(test_data_farmacia) == [44.50582724111065, 11.302028776971122], "Test farmacia fallito"
    
    # Test per aree verdi, parcheggi, scuole, cinema, ospedali e luoghi di culto (geopoint)
    assert extract_poi_coordinates(test_data_geopoint) == [44.511873, 11.238742], "Test geopoint fallito"
    
    # Test per altri POI con geo_point_2d
    assert extract_poi_coordinates(test_data_geo_point_2d['record']['fields']) == [44.501153, 11.336062], "Test geo_point_2d fallito"
    
    print("Tutti i test extract_poi_coordinates superati con successo!")

# Test per calculate_poi_distances con visualizzazione delle distanze
def test_calculate_poi_distances():
    # Esegui il calcolo delle distanze con il marker e i dati POI simulati
    distances = calculate_poi_distances(test_marker, test_poi_data)
    
    # Controlla se il numero di POI è corretto
    assert len(distances) == 3, "Errore: numero di POI non corretto"
    
    # Mostra le distanze calcolate
    for idx, distance_info in enumerate(distances):
        poi_name = distance_info['poi_name']
        distance = distance_info['distance']
        print(f"POI {idx + 1}: {poi_name}, Distanza: {distance:.2f} metri")

    print("Test calculate_poi_distances superato con successo!")

# Esegui tutti i test
test_extract_poi_coordinates()
test_calculate_poi_distances()
