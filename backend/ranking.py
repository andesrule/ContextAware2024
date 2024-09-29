from sqlalchemy import text
from models import db, QuestionnaireResponse
from sqlalchemy.orm.exc import NoResultFound
from models import Geofence
from geoalchemy2 import Geometry
from flask import jsonify

def get_pois_near_marker(marker_id, poi_type, raggio):
    try:
        # Recupera il marker dalla tabella Geofence usando l'ID
        marker = db.session.query(Geofence).filter_by(id=marker_id).one()

        # Verifica se il marker esiste
        if marker.marker is None:
            return jsonify({"error": "Marker non trovato"}), 404

        # Estrai le coordinate dal campo WKB (Well-Known Binary)
        # Usa ST_AsText per convertire WKB in geometria leggibile
        query = text(f"""
            SELECT poi_type, ST_Distance(geofence.marker::geography, poi.geom::geography) AS distance
            FROM poi
            WHERE poi_type = :poi_type
            AND ST_DWithin(geofence.marker::geography, poi.geom::geography, :raggio)
            ORDER BY distance ASC;
        """)
        
        result = db.session.execute(query, {'poi_type': poi_type, 'raggio': raggio})
        pois = result.fetchall()
        print(f'Results: {pois}')
    # Verifica se ci sono risultati
        if not pois:
            return jsonify({'error': 'No POIs found within the specified range'}), 404

    # Restituisce la lista dei POIs
        return pois
        

    except NoResultFound:
        return jsonify({"error": "Marker con l'ID fornito non esiste"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def calcola_rank(marker, user_preferences, nearby_pois):
    """
    Calcola il punteggio del marker tenendo conto dei pesi delle preferenze dell'utente e della presenza di PoI.
    :param marker: Marker dell'immobile
    :param user_preferences: Dizionario con le preferenze dell'utente (da 0 a 5)
    :param nearby_pois: Dizionario con il numero di PoI vicini (reali)
    :return: Punteggio del marker
    """
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
        'aree_verdi_2': 1.3,
        'cinema_2': 0.5,
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
    if nearby_pois.get('aree_verdi_2', 0) >= 2:
        rank += user_preferences['aree_verdi_2'] * pesi['aree_verdi_2']

    #Cinema densitá
    if nearby_pois.get('cinema_2', 0) >= 2:
        rank += user_preferences['cinema_2'] * pesi['cinema_2']
    
    #Fermate bus densitá
    if nearby_pois.get('fermate_bus_2', 0) >= 2:
        rank += user_preferences['fermate_bus_2'] * pesi['fermate_bus_2']

    return rank
