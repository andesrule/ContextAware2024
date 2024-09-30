from sqlalchemy import text
from models import db, QuestionnaireResponse
from sqlalchemy.orm.exc import NoResultFound
from models import Geofence
from geoalchemy2 import Geometry
from flask import jsonify
import json
from flask import jsonify
from sqlalchemy.orm.exc import NoResultFound
from geoalchemy2.shape import to_shape
import requests
from math import radians, sin, cos, sqrt, atan2

def get_questionnaire_by_id(response_id):
    try:
        # Esegui la query per recuperare la risposta al questionario con l'ID specificato
        response = QuestionnaireResponse.query.filter_by(id=response_id).first()

        # Verifica se la risposta esiste
        if response is None:
            return {"error": "Questionnaire response not found"}

        # Converte l'oggetto in un dizionario
        response_data = {
            'id': response.id,
            'aree_verdi': response.aree_verdi,
            'parcheggi': response.parcheggi,
            'fermate_bus': response.fermate_bus,
            'luoghi_interesse': response.luoghi_interesse,
            'scuole': response.scuole,
            'cinema': response.cinema,
            'ospedali': response.ospedali,
            'farmacia': response.farmacia,
            'luogo_culto': response.luogo_culto,
            'servizi': response.servizi,
            'densita_aree_verdi': response.densita_aree_verdi,
            'densita_cinema': response.densita_cinema,
            'densita_fermate_bus': response.densita_fermate_bus
        }

        return response_data

    except Exception as e:
        return {"error": str(e)}

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371  # Raggio della Terra in km
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    distance = R * c
    return distance

def count_pois_near_marker(marker_id, raggio):
    poi_types = [
        'aree_verdi', 'parcheggi', 'fermate_bus', 'luoghi_interesse',
        'scuole', 'cinema', 'ospedali', 'farmacia', 'luogo_culto', 'servizi'
    ]

    # Dizionario per tenere traccia del numero di POI per ogni tipo
    poi_counts = {
        'aree_verdi': 0,
        'parcheggi': 0,
        'fermate_bus': 0,
        'luoghi_interesse': 0,
        'scuole': 0,
        'cinema': 0,
        'ospedali': 0,
        'farmacia': 0,
        'luogo_culto': 0,
        'servizi': 0
    }

    # Itera su ciascun tipo di POI e chiama get_pois_near_marker
    for poi_type in poi_types:
        # Chiama get_pois_near_marker per ogni tipo di POI
        response = get_pois_near_marker(marker_id, poi_type, raggio)

        # Verifica se la risposta è valida
        if response.status_code == 200:
            poi_data = response.json()  # Estrai i dati JSON dalla risposta
            
            # Conta i POI vicini per quel tipo di POI
            poi_counts[poi_type] = len(poi_data.get('nearby_pois', []))
        else:
            print(f"Errore nell'ottenere i dati per {poi_type}: {response.status_code}")

    return poi_counts

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

def get_pois_near_marker(marker_id, poi_type, raggio):
    try:
        # Recupera il marker dalla tabella Geofence usando l'ID
        marker = db.session.query(Geofence).filter_by(id=marker_id).first()
        
        # Verifica se il marker esiste
        if marker is None or marker.marker is None:
            return jsonify({"error": "Marker non trovato"}), 404
        
        # Estrai le coordinate dal campo marker
        marker_point = to_shape(marker.marker)
        marker_lat, marker_lon = marker_point.y, marker_point.x

        # Recupera i dati dei PoI dall'API esterna
        poi_response = requests.get(f'http://localhost:5000/api/poi/{poi_type}')
        
        if poi_response.status_code != 200:
            return jsonify({'error': f'Errore API: {poi_response.status_code}'}), 500
        
        poi_data = poi_response.json()
        
        nearby_pois = []

        for poi in poi_data['results']:
            try:
                poi_lat, poi_lon = get_poi_coordinates(poi)
                
                distance = haversine_distance(marker_lat, marker_lon, poi_lat, poi_lon)
                
                if distance <= raggio:
                    nearby_pois.append({
                        'poi': poi,
                        'distance': distance
                    })
            except ValueError as e:
                print(f"Errore nel processare le coordinate del POI: {str(e)}")
                continue

        # Ordina i PoI per distanza
        nearby_pois.sort(key=lambda x: x['distance'])

        # Verifica se ci sono risultati
        if not nearby_pois:
            return jsonify({'error': 'Nessun POI trovato entro il raggio specificato'}), 404

        return jsonify({
            'marker_id': marker_id,
            'marker_location': {'lat': marker_lat, 'lon': marker_lon},
            'nearby_pois': nearby_pois
        })

    except NoResultFound:
        return jsonify({"error": "Marker con l'ID fornito non esiste"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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

