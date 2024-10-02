from flask import jsonify, request, Blueprint
from geoalchemy2.shape import from_shape, to_shape
from models import *
import json, logging 
import requests
from geoalchemy2.functions import ST_DWithin
from shapely.geometry import mapping, Point, Polygon
from shapely.wkt import loads
from sqlalchemy import func

from flask import request, jsonify

from geoalchemy2 import  WKBElement
from geoalchemy2.functions import ST_DWithin, ST_Transform, ST_GeomFromWKB


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
    response = QuestionnaireResponse(
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
        densita_cinema=data.get('densita_cinema'),
        densita_fermate_bus=data.get('densita_fermate_bus')

    )
    
    db.session.add(response)
    db.session.commit()

    return jsonify({"message": "questionario inviato con successo!"})

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
'''
def calcola_rank(marker_id, user_preferences, raggio):
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

'''