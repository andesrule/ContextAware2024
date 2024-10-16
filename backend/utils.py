from flask import jsonify, request, Blueprint
from geoalchemy2.shape import from_shape, to_shape
from models import *
import json, logging 
import requests
from shapely.geometry import mapping, Point, Polygon
from shapely.wkt import loads
from sqlalchemy import func, text
from geoalchemy2.functions import *
from shapely import wkb
import binascii
from flask_login import current_user
import numpy as np



global_radius = 500
utils_bp = Blueprint('utils', __name__)

@utils_bp.route('/debug_poi_count')
def debug_poi_count():
    total_count = POI.query.count()
    parking_count = POI.query.filter_by(type='fermate_bus').count()
    return jsonify({
        'total_poi_count': total_count,
        'parking_poi_count': parking_count
    })

@utils_bp.route('/get_pois')
def get_pois():
    pois = POI.query.all()
    print(f"Numero totale di POI nel database: {len(pois)}")
    
    poi_list = []
    for index, poi in enumerate(pois):
        print(f"Elaborazione POI {index + 1}: Tipo = {poi.type}")
        # Convert WKBElement to Shapely object
        point = to_shape(poi.location)
        # Convert Shapely object to GeoJSON
        geojson = mapping(point)
        poi_data = {
            'type': poi.type,
            'lat': geojson['coordinates'][1],
            'lng': geojson['coordinates'][0],
            'additional_data': json.loads(poi.additional_data)
        }
        print(f"Dati POI {index + 1}: {poi_data}")
        poi_list.append(poi_data)
    
    print(f"Numero di POI restituiti: {len(poi_list)}")
    return jsonify(poi_list)

@utils_bp.route('/get_radius', methods=['POST'])
def get_radius():
    global global_radius
    try:
        data = request.get_json(force=True)
        if 'radius' not in data:
            return jsonify({"error": "Il parametro 'radius' è mancante"}), 400
        
        radius = int(data['radius'])
        global_radius = radius  # Salva il raggio nella variabile globale
        return jsonify({"message": f"Raggio aggiornato a {radius} metri", "radius": radius}), 200
    
    except ValueError:
        return jsonify({"error": "Il raggio deve essere un numero intero"}), 400
    except Exception as e:
        return jsonify({"error": f"Errore imprevisto: {str(e)}"}), 500
    
@utils_bp.route('/save-geofence', methods=['POST'])
def save_geofence():
    data = request.json
    
    if 'marker' in data:
        # Salvataggio del marker
        lat = data['marker']['lat']
        lng = data['marker']['lng']
        point = Point(lng, lat)
        new_geofence = Geofence(marker=from_shape(point, srid=4326))
    elif 'geofence' in data:
        # Salvataggio del geofence
        try:
            # Se il geofence è già una stringa WKT
            if isinstance(data['geofence'], str):
                polygon = loads(data['geofence'])
            else:
                # Se il geofence è una lista di coordinate
                coords = [(p['lng'], p['lat']) for p in data['geofence']]
                # Assicuriamoci che il poligono sia chiuso
                if coords[0] != coords[-1]:
                    coords.append(coords[0])
                polygon = Polygon(coords)
            
            new_geofence = Geofence(geofence=from_shape(polygon, srid=4326))
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 400
    else:
        return jsonify({'status': 'error', 'message': 'Invalid data'}), 400

    try:
        db.session.add(new_geofence)
        db.session.commit()
        return jsonify({'status': 'success', 'id': new_geofence.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
    
@utils_bp.route('/submit-questionnaire', methods=['POST'])
def submit_questionnaire():
    data = request.get_json()
    
    # Cerca se esiste già un questionario nel database
    existing_questionnaire = QuestionnaireResponse.query.first()

    if existing_questionnaire:
        # Se esiste, aggiorna i valori
        for key, value in data.items():
            setattr(existing_questionnaire, key, value)
    else:
        # Se non esiste, crea un nuovo questionario
        new_questionnaire = QuestionnaireResponse(
            aree_verdi=data.get('aree_verdi'),
            parcheggi=data.get('parcheggi'),
            fermate_bus=data.get('fermate_bus'),
            stazioni_ferroviarie=data.get('stazioni_ferroviarie'),
            scuole=data.get('scuole'),
            cinema=data.get('cinema'),
            ospedali=data.get('ospedali'),
            farmacia=data.get('farmacia'),
            luogo_culto=data.get('luogo_culto'),
            servizi=data.get('servizi'),
            densita_aree_verdi=data.get('densita_aree_verdi'),

            densita_fermate_bus=data.get('densita_fermate_bus')
        )
        db.session.add(new_questionnaire)

    try:
        db.session.commit()
        return jsonify({"message": "Questionario inviato con successo!"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

def get_poi_coordinates(poi):
    """Estrae le coordinate dal PoI, gestendo diversi formati."""
    if 'geo_point_2d' in poi and 'lat' in poi['geo_point_2d'] and 'lon' in poi['geo_point_2d']:
        # Handle geo_point_2d format
        return float(poi['geo_point_2d']['lat']), float(poi['geo_point_2d']['lon'])
    elif 'geopoint' in poi and poi['geopoint'] is not None and 'lat' in poi['geopoint'] and 'lon' in poi['geopoint']:
        # Handle geopoint format, ensuring geopoint is not None
        return float(poi['geopoint']['lat']), float(poi['geopoint']['lon'])
    elif 'coordinate' in poi and 'lat' in poi['coordinate'] and 'lon' in poi['coordinate']:
        # Handle coordinate format for parking data
        return float(poi['coordinate']['lat']), float(poi['coordinate']['lon'])
    elif 'ycoord' in poi and 'xcoord' in poi:
        # Handle ycoord/xcoord format
        return float(poi['ycoord']), float(poi['xcoord'])
    elif 'geo_shape' in poi and 'geometry' in poi['geo_shape'] and 'coordinates' in poi['geo_shape']['geometry']:
        # Handle geo_shape (GeoJSON) format
        coordinates = poi['geo_shape']['geometry']['coordinates']
        return float(coordinates[1]), float(coordinates[0])  # Nota: l'ordine è [lon, lat] in GeoJSON
    elif 'geo_point' in poi and 'lat' in poi['geo_point'] and 'lon' in poi['geo_point']:
        # Handle geo_point format
        return float(poi['geo_point']['lat']), float(poi['geo_point']['lon'])
    else:
        raise ValueError("Formato coordinate non riconosciuto")

def count_nearby_pois(db, marker_id, distance_meters):
    # Ottieni il marker specifico dal database
    marker = db.session.query(Geofence).get(marker_id)
    if not marker:
        return None

    # Definisci i tipi di POI che vogliamo contare
    poi_types = [
        'aree_verdi', 'parcheggi', 'fermate_bus', 'stazioni_ferroviarie',
        'scuole', 'cinema', 'ospedali', 'farmacia', 'luogo_culto', 'servizi'
    ]

    # Inizializza il dizionario dei risultati
    result = {poi_type: 0 for poi_type in poi_types}

    # Esegui la query per contare i POI vicini
    poi_counts = db.session.query(
        POI.type,
        func.count(POI.id).label('count')
    ).filter(
        ST_DWithin(
            ST_Transform(POI.location, 3857),
            ST_Transform(marker.marker, 3857),
            distance_meters
        )
    ).group_by(POI.type).all()

    # Popola il dizionario dei risultati
    for poi_type, count in poi_counts:
        if poi_type in result:
            result[poi_type] = count


    return result

@utils_bp.route('/api/count_nearby_pois', methods=['GET'])
def api_count_nearby_pois():
    marker_id = request.args.get('marker_id', type=int)
    distance_meters = request.args.get('distance', type=float)

    if not marker_id or not distance_meters:
        return jsonify({"error": "Missing marker_id or distance parameter"}), 400

    logging.debug(f"Received request with marker_id: {marker_id}, distance: {distance_meters}")

    result = count_nearby_pois(db, marker_id, distance_meters)
    if result is None:
        return jsonify({"error": "Marker not found or no POIs in database"}), 404

    logging.debug(f"Result: {result}")
    return jsonify(result)

def fetch_and_insert_pois(poi_type, api_url):
    total_count = 0
    offset = 0
    limit = 100  # Mantenuto a 100 per efficienza
    
    while True:
        if "tper-fermate-autobus" in api_url:
            paginated_url = f"{api_url}?limit={limit}&offset={offset}&refine=comune%3A%22BOLOGNA%22"
        else:
            paginated_url = f"{api_url}?limit={limit}&offset={offset}"
        response = requests.get(paginated_url)
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            
            if not results:
                break  # Nessun altro risultato, usciamo dal loop
            
            for poi in results:
                try:
                    lat, lon = get_poi_coordinates(poi)
                    new_poi = POI(
                        type=poi_type,
                        location=f'POINT({lon} {lat})',
                        additional_data=json.dumps(poi)
                    )
                    db.session.add(new_poi)
                except ValueError as e:
                    print(f"Errore nell'elaborazione del POI: {e}")
            
            db.session.commit()
            total_count += len(results)
            offset += limit
            
            print(f"Elaborati {total_count} POI di tipo {poi_type}")
        else:
            print(f"Errore nella richiesta API per {poi_type}: {response.status_code}")
            break

    return total_count

def update_pois():
    poi_sources = {
        'parcheggi': 'https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/parcheggi/records',
        'cinema': 'https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/teatri-cinema-teatri/records',
        'farmacia': 'https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/farmacie/records',
        'ospedali': 'https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/strutture-sanitarie/records',
        'fermate_bus': 'https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/tper-fermate-autobus/records',
        'scuole': 'https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/elenco-delle-scuole/records',
        'aree_verdi': 'https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/carta-tecnica-comunale-toponimi-parchi-e-giardini/records',
        'luogo_culto': 'https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/origini-di-bologna-chiese-e-conventi/records',
        'servizi': 'https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/istanze-servizi-alla-persona/records',
        'stazioni_ferroviarie': 'https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/stazioniferroviarie_20210401/records'
    }
    results = {}
    for poi_type, api_url in poi_sources.items():
        count = fetch_and_insert_pois(poi_type, api_url)
        results[poi_type] = count
    return results

@utils_bp.route('/api/poi/<poi_type>', methods=['GET'])
def get_poi(poi_type):
    base_urls = {
        'parcheggi': 'https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/disponibilita-parcheggi-storico/records',
        'cinema': 'https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/teatri-cinema-teatri/records',
        'farmacia': 'https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/farmacie/records',
        'ospedali': 'https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/strutture-sanitarie/records',
        'fermate_bus' : 'https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/tper-fermate-autobus/records?select=*&limit=100&refine=comune%3A%22BOLOGNA%22',
        'scuole' : 'https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/elenco-delle-scuole/records',
        'aree_verdi' : 'https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/carta-tecnica-comunale-toponimi-parchi-e-giardini/records',
        'luogo_culto' : 'https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/origini-di-bologna-chiese-e-conventi/records',
        'servizi' : 'https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/istanze-servizi-alla-persona/records',
        'stazioni_ferroviarie': 'https://opendata.comune.bologna.it/api/api/explore/v2.1/catalog/datasets/stazioniferroviarie_20210401/records'
        
        # Aggiungi altre categorie qui
    }

    if poi_type not in base_urls:
        return jsonify({'error': f'POI type {poi_type} not recognized'}), 400

    url = base_urls[poi_type]
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        return jsonify(data)
    else:
        return jsonify({'error': f'Errore API: {response.status_code}'}), 500

@utils_bp.route('/get_markers')
def get_markers():
    markers = Geofence.query.all()
    marker_list = []
    for marker in markers:
        if marker.marker is not None:
            # Converti WKBElement in un oggetto Shapely
            point = to_shape(marker.marker)
            # Converti l'oggetto Shapely in un dizionario GeoJSON
            geojson = mapping(point)
            marker_list.append({
                'lat': geojson['coordinates'][1],
                'lng': geojson['coordinates'][0]
            })
    return jsonify(marker_list) 
    
@utils_bp.route('/get-geofences')
def get_geofences():
    geofences = Geofence.query.all()
    geofences_data = []

    for gf in geofences:
        geofence_data = {'id': gf.id}

        if gf.marker is not None:
            point = to_shape(gf.marker)
            geofence_data['marker'] = mapping(point)
        
        if gf.geofence is not None:
            polygon = to_shape(gf.geofence)
            geofence_data['geofence'] = mapping(polygon)
        
        geofences_data.append(geofence_data)

    return jsonify(geofences_data)    

def get_questionnaire_response_dict(response):
    return {
        'aree_verdi': response.aree_verdi,
        'parcheggi': response.parcheggi,
        'fermate_bus': response.fermate_bus,
        'stazioni_ferroviarie': response.stazioni_ferroviarie,
        'scuole': response.scuole,
        'cinema': response.cinema,
        'ospedali': response.ospedali,
        'farmacia': response.farmacia,
        'luogo_culto': response.luogo_culto,
        'servizi': response.servizi,
        'densita_aree_verdi': response.densita_aree_verdi,
        'densita_fermate_bus': response.densita_fermate_bus
    }

def calcola_rank(marker_id, raggio):
    """
    Calcola il punteggio del marker tenendo conto dei pesi delle preferenze dell'utente e della presenza di PoI.
    :param marker: Marker dell'immobile
    :param user_preferences: Dizionario con le preferenze dell'utente (da 0 a 5)
    :param nearby_pois: Dizionario con il numero di PoI vicini (reali)
    :return: Punteggio del marker
    """
    nearby_pois = count_nearby_pois(db, marker_id=marker_id, distance_meters=raggio)
    response = QuestionnaireResponse.query.first()
    user_preferences = get_questionnaire_response_dict(response = QuestionnaireResponse.query.get(1))
    if not user_preferences:
        # Se non ci sono preferenze dell'utente, restituisci un rank di default
        return 0

    rank = 0
    
    # Definisci pesi per ciascun tipo di PoI (questi valori sono un esempio)
    pesi = {
        'aree_verdi': 0.8,
        'parcheggi': 1.0,
        'fermate_bus': 1.0,
        'stazioni_ferroviarie': 1.0,
        'scuole': 0.7,
        'cinema': 0.6,
        'ospedali': 1.0,
        'farmacia': 0.5,
        'luogo_culto': 0.2,
        'servizi': 0.4,
    }
    
    # Aree Verdi
    rank += nearby_pois.get('aree_verdi', 0) * user_preferences['aree_verdi'] * pesi['aree_verdi']
    
    # Parcheggi
    if nearby_pois.get('parcheggi', 0) >= 2:
        rank += user_preferences['parcheggi'] * pesi['parcheggi']
    
    # Fermate Bus
    rank += nearby_pois.get('fermate_bus', 0) * user_preferences['fermate_bus'] * pesi['fermate_bus']
    
    # Luoghi di interesse
    if nearby_pois.get('stazioni_ferroviarie', 0) >= 2:
        rank += user_preferences['stazioni_ferroviarie'] * pesi['stazioni_ferroviarie']
    
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
        rank += user_preferences['densita_aree_verdi'] * pesi['aree_verdi']

    #Fermate bus densitá
    if nearby_pois.get('fermate_bus', 0) >= 2:
        rank += user_preferences['densita_fermate_bus'] * pesi['fermate_bus']

    return rank

@utils_bp.route('/get_ranked_markers')
def get_ranked_markers():
    try:
        # Controlla se ci sono questionari nel database
        if QuestionnaireResponse.query.count() == 0:
            return jsonify({"error": "No questionnaires found"}), 404

        global global_radius
        
        markers = Geofence.query.filter(Geofence.marker.isnot(None)).all()
        ranked_markers = []
        
        for marker in markers:
            try:
                lat = db.session.scalar(ST_Y(marker.marker))
                lng = db.session.scalar(ST_X(marker.marker))
                rank = calcola_rank(marker.id, raggio=global_radius)
                ranked_markers.append({
                    'id': marker.id,
                    'lat': lat,
                    'lng': lng,
                    'rank': rank
                })
            except Exception as e:
                print(f"Errore nell'elaborazione del marker {marker.id}: {str(e)}")
        
        return jsonify(ranked_markers)
    except Exception as e:
        print(f"Errore generale in get_ranked_markers: {str(e)}")
        return jsonify({"error": str(e)}), 500

def count_pois_in_geofence(db, geofence_id):
    # Ottieni il geofence specifico dal database
    geofence = db.session.query(Geofence).get(geofence_id)
    if not geofence:
        return None

    # Definisci i tipi di POI che vogliamo contare
    poi_types = [
        'aree_verdi', 'parcheggi', 'fermate_bus', 'stazioni_ferroviarie',
        'scuole', 'cinema', 'ospedali', 'farmacia', 'luogo_culto', 'servizi'
    ]

    # Inizializza il dizionario dei risultati
    result = {poi_type: 0 for poi_type in poi_types}

    # Esegui la query per contare i POI all'interno del geofence
    poi_counts = db.session.query(
        POI.type,
        func.count(POI.id).label('count')
    ).filter(
        ST_Contains(geofence.geofence, POI.location)
    ).group_by(POI.type).all()

    # Popola il dizionario dei risultati
    for poi_type, count in poi_counts:
        if poi_type in result:
            result[poi_type] = count

    return result

def calcola_rank_geofence(geofence_id):
    """
    Calcola il punteggio del marker tenendo conto dei pesi delle preferenze dell'utente e della presenza di PoI.
    :param marker: Marker dell'immobile
    :param user_preferences: Dizionario con le preferenze dell'utente (da 0 a 5)
    :param nearby_pois: Dizionario con il numero di PoI vicini (reali)
    :return: Punteggio del marker
    """
    nearby_pois= count_pois_in_geofence(db, geofence_id=geofence_id)
    user_preferences = get_questionnaire_response_dict(response = QuestionnaireResponse.query.get(1))
    rank = 0
    
    # Definisci pesi per ciascun tipo di PoI (questi valori sono un esempio)
    pesi = {
        'aree_verdi': 0.8,
        'parcheggi': 1.0,
        'fermate_bus': 1.0,
        'stazioni_ferroviarie': 1.0,
        'scuole': 0.7,
        'cinema': 0.6,
        'ospedali': 1.0,
        'farmacia': 0.5,
        'luogo_culto': 0.2,
        'servizi': 0.4,
    }
    
    # Aree Verdi
    rank += nearby_pois.get('aree_verdi', 0) * user_preferences['aree_verdi'] * pesi['aree_verdi']
    
    # Parcheggi
    if nearby_pois.get('parcheggi', 0) >= 2:
        rank += user_preferences['parcheggi'] * pesi['parcheggi']
    
    # Fermate Bus
    rank += nearby_pois.get('fermate_bus', 0) * user_preferences['fermate_bus'] * pesi['fermate_bus']
    
    # Luoghi di interesse
    if nearby_pois.get('stazioni_ferroviarie', 0) >= 2:
        rank += user_preferences['stazioni_ferroviarie'] * pesi['stazioni_ferroviarie']
    
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
        rank += user_preferences['densita_aree_verdi'] * pesi['aree_verdi']


    #Fermate bus densitá
    if nearby_pois.get('fermate_bus', 0) >= 2:
        rank += user_preferences['densita_fermate_bus'] * pesi['fermate_bus']

    return rank

@utils_bp.route('/get_ranked_geofences')
def get_ranked_geofences():
    try:
        # Controlla se ci sono questionari nel database
        if QuestionnaireResponse.query.count() == 0:
            return jsonify({"error": "No questionnaires found"}), 404

        geofences = Geofence.query.filter(Geofence.geofence.isnot(None)).all()
        ranked_geofences = []
        
        for geofence in geofences:
            try:
                # Ottieni il centroide del geofence
                centroid = db.session.scalar(ST_Centroid(geofence.geofence))
                centroid_lat = db.session.scalar(func.ST_Y(centroid))
                centroid_lng = db.session.scalar(func.ST_X(centroid))
                
                # Calcola il rank
                rank = calcola_rank_geofence(geofence.id)
                
                # Ottieni il geofence come GeoJSON
                geofence_geojson = db.session.scalar(ST_AsGeoJSON(geofence.geofence))
                geofence_dict = json.loads(geofence_geojson)
                
                # Estrai le coordinate dal GeoJSON
                coordinates = geofence_dict['coordinates'][0]  # Prendi il primo (e unico) anello di coordinate
                
                ranked_geofences.append({
                    'id': geofence.id,
                    'centroid': {
                        'lat': centroid_lat,
                        'lng': centroid_lng
                    },
                    'coordinates': coordinates,
                    'rank': rank
                })
            except Exception as e:
                print(f"Errore nell'elaborazione del geofence {geofence.id}: {str(e)}")
        
        return jsonify(ranked_geofences)
    except Exception as e:
        print(f"Errore generale in get_ranked_geofences: {str(e)}")
        return jsonify({"error": str(e)}), 500

@utils_bp.route('/check-questionnaires')
def check_questionnaires():
    count = QuestionnaireResponse.query.count()
    return jsonify({'count': count})

def wkb_to_coordinates(wkb_input):
    """Converte WKB in coordinate (lon, lat)"""
    logging.debug(f"Received WKB input: {wkb_input}")
    try:
        if isinstance(wkb_input, float):
            # Se riceviamo un float, lo trattiamo come una singola coordinata
            return (wkb_input, wkb_input)
        elif isinstance(wkb_input, (list, tuple)) and len(wkb_input) == 2:
            # Se riceviamo una lista o tupla di due elementi, le trattiamo come lon, lat
            return tuple(wkb_input)
        elif isinstance(wkb_input, str):
            # Rimuovi eventuali spazi bianchi e converti in minuscolo
            wkb_hex = wkb_input.strip().lower()
            # Rimuovi il prefisso '0x' se presente
            if wkb_hex.startswith('0x'):
                wkb_hex = wkb_hex[2:]
            wkb_binary = binascii.unhexlify(wkb_hex)
            point = wkb.loads(wkb_binary)
            return (point.x, point.y)
        else:
            raise ValueError(f"Formato WKB non supportato: {type(wkb_input)}")
    except Exception as e:
        logging.error(f"Error in wkb_to_coordinates: {str(e)}")
        raise ValueError(f"WKB non valido: {str(e)}")

def calculate_travel_time(start_coords, end_coords, transport_mode='driving'):
    """Calcola il tempo di percorrenza tra due punti usando OSRM."""
    logging.debug(f"Calculating travel time from {start_coords} to {end_coords}")
    base_url = "http://router.project-osrm.org/route/v1"
    url = f"{base_url}/{transport_mode}/{start_coords[0]},{start_coords[1]};{end_coords[0]},{end_coords[1]}"
    
    params = {
        "overview": "false",
        "alternatives": "false",
    }
    
    response = requests.get(url, params=params)
    data = response.json()
    
    if response.status_code == 200 and data["code"] == "Ok":
        duration_seconds = data["routes"][0]["duration"]
        return duration_seconds / 60  # Converti in minuti
    else:
        logging.error(f"OSRM API error: {data}")
        raise Exception("Errore nel calcolo del percorso")

@utils_bp.route('/calculate_travel_time', methods=['POST'])
def api_calculate_travel_time():
    data = request.json
    logging.debug(f"Received request data: {data}")
    
    start_wkb = data.get('start_wkb')
    end_wkb = data.get('end_wkb')
    transport_mode = data.get('transport_mode', 'driving')

    if start_wkb is None or end_wkb is None:
        return jsonify({"error": "Mancano le coordinate di partenza o arrivo"}), 400

    try:
        start_coords = wkb_to_coordinates(start_wkb)
        end_coords = wkb_to_coordinates(end_wkb)
        travel_time = calculate_travel_time(start_coords, end_coords, transport_mode)
        return jsonify({"travel_time_minutes": travel_time})
    except ValueError as e:
        logging.error(f"ValueError in api_calculate_travel_time: {str(e)}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logging.error(f"Unexpected error in api_calculate_travel_time: {str(e)}")
        return jsonify({"error": str(e)}), 500
    
@utils_bp.route('/delete-all-geofences', methods=['POST'])
def delete_all_geofences():
    try:
        Geofence.query.delete()
        db.session.commit()
        return jsonify({"message": "Tutti i geofence sono stati cancellati"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
    

@utils_bp.route('/delete-geofence/<int:geofence_id>', methods=['DELETE'])
def delete_geofence(geofence_id):
    try:
        geofence = Geofence.query.get(geofence_id)
        if geofence:
            db.session.delete(geofence)
            db.session.commit()
            return jsonify({"message": f"Geofence con ID {geofence_id} eliminato con successo"}), 200
        else:
            return jsonify({"error": f"Geofence con ID {geofence_id} non trovato"}), 404
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
    



 # ... [Importazioni e altro codice rimangono invariati]

@utils_bp.route('/get_all_geofences')
def get_all_geofences():
    try:
        # Controlla se ci sono questionari nel database
        if QuestionnaireResponse.query.count() == 0:
            return jsonify({"error": "No questionnaires found"}), 404

        geofences = Geofence.query.all()
        all_geofences = []
        
        for geofence in geofences:
            try:
                if geofence.marker is not None:
                    # È un marker
                    lat = db.session.scalar(ST_Y(geofence.marker))
                    lng = db.session.scalar(ST_X(geofence.marker))
                    rank = calcola_rank(geofence.id, raggio=global_radius)
                    all_geofences.append({
                        'id': geofence.id,
                        'type': 'marker',
                        'lat': lat,
                        'lng': lng,
                        'rank': rank
                    })
                elif geofence.geofence is not None:
                    # È un poligono
                    centroid = db.session.scalar(ST_Centroid(geofence.geofence))
                    centroid_lat = db.session.scalar(func.ST_Y(centroid))
                    centroid_lng = db.session.scalar(func.ST_X(centroid))
                    rank = calcola_rank_geofence(geofence.id)
                    geofence_geojson = db.session.scalar(ST_AsGeoJSON(geofence.geofence))
                    geofence_dict = json.loads(geofence_geojson)
                    coordinates = geofence_dict['coordinates'][0]
                    all_geofences.append({
                        'id': geofence.id,
                        'type': 'polygon',
                        'centroid': {
                            'lat': centroid_lat,
                            'lng': centroid_lng
                        },
                        'coordinates': coordinates,
                        'rank': rank
                    })
            except Exception as e:
                print(f"Errore nell'elaborazione del geofence {geofence.id}: {str(e)}")
        
        return jsonify(all_geofences)
    except Exception as e:
        print(f"Errore generale in get_all_geofences: {str(e)}")
        return jsonify({"error": str(e)}), 500

def get_bologna_bounds():
    # Coordinate approssimative di Bologna (in lat, lon)
    return (44.4949, 11.3426, 44.4949, 11.3426)  # nord, est, sud, ovest

def create_grid(bounds, grid_size):
    north, east, south, west = bounds
    lat_points = np.linspace(south, north, grid_size)
    lon_points = np.linspace(west, east, grid_size)
    return [(lat, lon) for lat in lat_points for lon in lon_points]

def count_pois_near_point(db, lat, lon, radius):
    point = f'POINT({lon} {lat})'
    poi_counts = db.session.query(
        POI.type,
        func.count(POI.id).label('count')
    ).filter(
        ST_DWithin(
            ST_Transform(POI.location, 3857),
            ST_Transform(func.ST_GeomFromText(point, 4326), 3857),
            radius
        )
    ).group_by(POI.type).all()
    
    return dict(poi_counts)

def calculate_rank(poi_counts, user_preferences):
    rank = 0
    weights = {
        'aree_verdi': 0.8, 'parcheggi': 1.0, 'fermate_bus': 1.0,
        'stazioni_ferroviarie': 1.0, 'scuole': 0.7, 'cinema': 0.6,
        'ospedali': 1.0, 'farmacia': 0.5, 'luogo_culto': 0.2, 'servizi': 0.4,
    }
    
    for poi_type, count in poi_counts.items():
        if poi_type in user_preferences and poi_type in weights:
            rank += count * user_preferences[poi_type] * weights[poi_type]
    
    # Aggiungi bonus per densità se applicabile
    if poi_counts.get('aree_verdi', 0) >= 2:
        rank += user_preferences.get('densita_aree_verdi', 0) * weights['aree_verdi']
    if poi_counts.get('fermate_bus', 0) >= 2:
        rank += user_preferences.get('densita_fermate_bus', 0) * weights['fermate_bus']
    
    return rank

@utils_bp.route('/calculate_optimal_locations', methods=['GET'])
def calculate_optimal_locations():
    try:
        grid_size = 100
        radius = 500  # metri

        user_prefs = QuestionnaireResponse.query.first()
        if not user_prefs:
            return jsonify({"error": "Nessun questionario trovato. Completa il questionario prima."}), 400
        
        user_preferences = get_questionnaire_response_dict(user_prefs)

        bounds = get_bologna_bounds()
        grid_points = create_grid(bounds, grid_size)

        # Creiamo una tabella temporanea con i punti della griglia
        create_temp_table_query = text("""
        CREATE TEMPORARY TABLE grid_points (
            id SERIAL PRIMARY KEY,
            geom GEOMETRY(POINT, 4326)
        )
        """)
        db.session.execute(create_temp_table_query)

        # Inseriamo i punti della griglia nella tabella temporanea
        insert_points_query = text("""
        INSERT INTO grid_points (geom)
        VALUES (:point)
        """)
        for lat, lon in grid_points:
            db.session.execute(insert_points_query, {"point": f"SRID=4326;POINT({lon} {lat})"})

        # Eseguiamo la query spaziale
        query = text("""
        SELECT g.id, ST_X(g.geom) as lon, ST_Y(g.geom) as lat, 
               poi.type, COUNT(poi.id) as count
        FROM grid_points g
        LEFT JOIN points_of_interest poi ON ST_DWithin(
            ST_Transform(g.geom, 3857),
            ST_Transform(poi.location, 3857),
            :radius
        )
        GROUP BY g.id, g.geom, poi.type
        """)

        result = db.session.execute(query, {"radius": radius})

        # Organizziamo i risultati
        poi_counts = {}
        for row in result:
            point = (row.lat, row.lon)
            if point not in poi_counts:
                poi_counts[point] = {}
            if row.type:
                poi_counts[point][row.type] = row.count

        # Calcola il rank per ogni punto
        ranked_locations = []
        for point, counts in poi_counts.items():
            lat, lon = point
            rank = calculate_rank(counts, user_preferences)
            ranked_locations.append({"lat": lat, "lon": lon, "rank": rank})

        # Ordina e prendi i top 5
        top_locations = sorted(ranked_locations, key=lambda x: x['rank'], reverse=True)[:5]

        # Pulizia: eliminiamo la tabella temporanea
        db.session.execute(text("DROP TABLE IF EXISTS grid_points"))
        db.session.commit()

        return jsonify({
            "message": "Ecco le 5 migliori posizioni suggerite per acquistare casa a Bologna:",
            "suggestions": top_locations,
            "user_preferences": user_preferences,
            "total_locations_analyzed": len(ranked_locations)
        })

    except Exception as e:
        db.session.rollback()
        print(f"Errore in calculate_optimal_locations: {str(e)}")
        return jsonify({"error": str(e)}), 500
    

@utils_bp.route('/addMarkerPrice', methods=['POST'])
def add_marker_price():
    data = request.get_json()  # Ricevi i dati JSON dalla richiesta
    geofence_id = data.get('geofenceId')
    price = data.get('price')

    # Controllo di validità del prezzo
    if price is None or price <= 0:
        return jsonify({'error': 'Prezzo non valido'}), 400

    # Cerca il Geofence nel database tramite l'id
    geofence = Geofence.query.get(geofence_id)

    if not geofence:
        return jsonify({'error': 'Geofence non trovato'}), 404

    # Aggiorna il prezzo del marker
    geofence.marker_price = price
    db.session.commit()  # Salva i cambiamenti nel database

    return jsonify({'success': True, 'message': f'Prezzo di {price} aggiunto per il marker {geofence_id}'})