
from models import db, QuestionnaireResponse
from sqlalchemy.orm.exc import NoResultFound
from models import Geofence
from flask import jsonify
from flask import jsonify
from sqlalchemy.orm.exc import NoResultFound
from geoalchemy2.shape import to_shape
import requests


def get_poi_coordinates(poi):
    """Estrae le coordinate dal PoI, gestendo diversi formati."""
    if 'geo_point_2d' in poi and 'lat' in poi['geo_point_2d'] and 'lon' in poi['geo_point_2d']:
        return float(poi['geo_point_2d']['lat']), float(poi['geo_point_2d']['lon'])
    elif 'ycoord' in poi and 'xcoord' in poi:
        return float(poi['ycoord']), float(poi['xcoord'])
    elif 'geo_shape' in poi and 'geometry' in poi['geo_shape'] and 'coordinates' in poi['geo_shape']['geometry']:
        coordinates = poi['geo_shape']['geometry']['coordinates']
        return float(coordinates[1]), float(coordinates[0])  # Nota: l'ordine è [lon, lat] in GeoJSON
    else:
        raise ValueError("Formato coordinate non riconosciuto")


def calcola_rank(marker_id, user_preferences, raggio):
    """
    Calcola il punteggio del marker tenendo conto dei pesi delle preferenze dell'utente e della presenza di PoI.
    :param marker: Marker dell'immobile
    :param user_preferences: Dizionario con le preferenze dell'utente (da 0 a 5)
    :param nearby_pois: Dizionario con il numero di PoI vicini (reali)
    :return: Punteggio del marker
    """

    nearby_pois= count_pois_near_marker(marker_id, raggio)
    user_preferences= get_questionnaire_by_id(1)
    rank = 0
    
    # Definisci pesi per ciascun tipo di PoI (questi valori sono un esempio)
    pesi = {
        'aree_verdi': 0.8,
        'parcheggi': 1.2,
        'fermate_bus': 1.0,
        'luoghi_interesse': 1.1,
        'scuole': 0.9,
        'cinema': 0.6,
        'ospedali': 1.5,
        'farmacia': 1.3,
        'luogo_culto': 0.5,
        'servizi': 1.0,
        'densita_aree_verdi': 1.3,
        'densita_cinema': 0.5,
        'fermate_bus2': 1.0
    }
    
    # Aree Verdi
    rank += nearby_pois.get('aree_verdi', 0) * user_preferences['aree_verdi'] * pesi['aree_verdi']
    
    # Parcheggi
    if nearby_pois.get('parcheggi', 0) >= 2:
        rank += user_preferences['parcheggi'] * pesi['parcheggi']
    
    # Fermate Bus
    rank += nearby_pois.get('fermate_bus', 0) * user_preferences['fermate_bus'] * pesi['fermate_bus']
    
    # Luoghi di interesse
    if nearby_pois.get('luoghi_interesse', 0) >= 2:
        rank += user_preferences['luoghi_interesse'] * pesi['luoghi_interesse']
    
    # Scuole
    rank += nearby_pois.get('scuole', 0) * user_preferences['scuole'] * pesi['scuole']
    
    # Cinema
    rank += nearby_pois.get('cinema', 0) * user_preferences['cinema'] * pesi['cinema']
    
    # Ospedali
    rank += nearby_pois.get('ospedali', 0) * user_preferences['ospedali'] * pesi['ospedali']
    
    # Farmacia
    rank += nearby_pois.get('farmacia', 0) * user_preferences['farmacia'] * pesi['farmacia']
    
    # Luogo di Culto
    rank += nearby_pois.get('luogo_culto', 0) * user_preferences['luogo_culto'] * pesi['luogo_culto']
    
    # Servizi
    if nearby_pois.get('servizi', 0) >= 2:
        rank += user_preferences['servizi'] * pesi['servizi']
    
    #Aree verdi densitá
    if nearby_pois.get('aree_verdi', 0) >= 2:
        rank += user_preferences['densita_aree_verdi'] * pesi['densita_aree_verdi']

    #Cinema densitá
    if nearby_pois.get('cinema', 0) >= 2:
        rank += user_preferences['densita_cinema'] * pesi['densita_cinema']
    
    #Fermate bus densitá
    if nearby_pois.get('fermate_bus', 0) >= 2:
        rank += user_preferences['densita_fermate_bus'] * pesi['densita_fermate_bus']

    return rank

