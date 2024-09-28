# test_utils.py
from utils import extract_poi_coordinates

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

def test_extract_poi_coordinates():
    # Test per farmacie
    assert extract_poi_coordinates(test_data_farmacia) == [44.50582724111065, 11.302028776971122], "Test farmacia fallito"
    
    # Test per aree verdi, parcheggi, scuole, cinema, ospedali e luoghi di culto (geopoint)
    assert extract_poi_coordinates(test_data_geopoint) == [44.511873, 11.238742], "Test geopoint fallito"
    
    # Test per altri POI con geo_point_2d
    assert extract_poi_coordinates(test_data_geo_point_2d['record']['fields']) == [44.501153, 11.336062], "Test geo_point_2d fallito"
    
    print("Tutti i test extract_poi_coordinates superati con successo!")

# Esegui il test
test_extract_poi_coordinates()
