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
