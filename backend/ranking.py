from sqlalchemy import text
from models import db, QuestionnaireResponse

def get_pois_near_marker(marker_geom, poi_type, raggio):
    query = text(f"""
        SELECT poi_type, ST_Distance(ST_SetSRID(ST_MakePoint(:lng, :lat), 4326), poi.geom) AS distance
        FROM poi
        WHERE poi_type = :poi_type AND ST_DWithin(ST_SetSRID(ST_MakePoint(:lng, :lat), 4326), poi.geom, :raggio)
        ORDER BY distance ASC;
    """)
    result = db.session.execute(query, {'lng': marker_geom['lng'], 'lat': marker_geom['lat'], 'poi_type': poi_type, 'raggio': raggio})
    return result.fetchall()

def calculate_marker_score(marker, questionnaire_responses, raggio=1000):
    score = 0
    poi_types = [
        ('aree_verdi', 'densita_aree_verdi'),
        ('parcheggi', 'parcheggi'),
        # Altri tipi di POI
    ]
    
    for poi_type, response_field in poi_types:
        pois = get_pois_near_marker(marker['location'], poi_type, raggio)
        user_preference = getattr(questionnaire_responses, response_field, 0)
        
        for poi in pois:
            distance = poi['distance']
            poi_score = max(0, 10 - distance / 100)
            score += poi_score * user_preference
    
    return score

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
