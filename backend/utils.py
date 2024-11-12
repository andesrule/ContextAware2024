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
import numpy as np
import time
from flask_caching import Cache
from functools import lru_cache, partial
from multiprocessing import Pool, cpu_count
from sqlalchemy.exc import SQLAlchemyError
import binascii
from scipy.spatial.distance import cdist


cache = Cache(config={'CACHE_TYPE': 'simple'})

# Definisci una griglia più grande per il pre-calcolo
PRECALC_GRID_SIZE = 20

logging.basicConfig(level=logging.DEBUG)

global_radius = 500
saved_filters = {}

utils_bp = Blueprint('utils', __name__)

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

@utils_bp.route('/api/pois/<poi_type>', methods=['GET'])
def get_pois_by_type(poi_type):
    """
    Restituisce tutti i POI di un determinato tipo dal database.
    Usa direttamente le coordinate geometriche salvate.
    """
    try:
        # Query per ottenere tutti i POI del tipo specificato
        pois = POI.query.filter_by(type=poi_type).all()
        print(f"Trovati {len(pois)} POI di tipo {poi_type}")
        
        poi_list = []
        for poi in pois:
            try:
                # Converti la geometria in coordinate
                point = to_shape(poi.location)
                
                # Crea il dizionario POI
                poi_data = {
                    'id': poi.id,
                    'type': poi_type,
                    'lat': point.y,  # Latitudine
                    'lng': point.x,  # Longitudine
                }

                # Aggiungi i dati addizionali se presenti
                if poi.additional_data:
                    try:
                        additional_data = json.loads(poi.additional_data)
                        poi_data['properties'] = additional_data
                    except json.JSONDecodeError:
                        print(f"Errore nel parsing dei dati addizionali per POI {poi.id}")
                        poi_data['properties'] = {}

                poi_list.append(poi_data)

            except Exception as e:
                print(f"Errore nell'elaborazione del POI {poi.id}: {str(e)}")
                continue
        
        print(f"Restituisco {len(poi_list)} POI formattati")
        return jsonify({
            'status': 'success',
            'count': len(poi_list),
            'data': poi_list
        })
        
    except Exception as e:
        print(f"Errore generale in get_pois_by_type: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
    

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
        # Salvataggio del marker (immobile candidato)
        lat = data['marker']['lat']
        lng = data['marker']['lng']
        point = Point(lng, lat)
        new_immobile = ListaImmobiliCandidati(marker=from_shape(point, srid=4326))
        try:
            db.session.add(new_immobile)
            db.session.commit()
            return jsonify({'status': 'success', 'id': new_immobile.id})
        except Exception as e:
            db.session.rollback()
            return jsonify({'status': 'error', 'message': str(e)}), 500
    elif 'geofence' in data:
        # Salvataggio del geofence (area candidata)
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
            
            new_area = ListaAreeCandidate(geofence=from_shape(polygon, srid=4326))
            db.session.add(new_area)
            db.session.commit()
            return jsonify({'status': 'success', 'id': new_area.id})
        except Exception as e:
            db.session.rollback()
            return jsonify({'status': 'error', 'message': str(e)}), 500
    else:
        return jsonify({'status': 'error', 'message': 'Invalid data'}), 400
    
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
            colonnina_elettrica=data.get('colonnina_elettrica'),
            biblioteca=data.get('biblioteca'),
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
    """
    Conta i POI vicini a un marker utilizzando indici spaziali.
    Utilizza ST_DWithin con proiezione Web Mercator (SRID 3857) per misure di distanza accurate.
    
    Args:
        db: istanza del database
        marker_id: ID del marker di riferimento
        distance_meters: raggio di ricerca in metri
        
    Returns:
        dizionario con il conteggio dei POI per tipo
    """
    # Ottieni il marker specifico dal database
    marker = db.session.query(ListaImmobiliCandidati).get(marker_id)
    if not marker:
        return None

    # Definisci i tipi di POI da contare
    poi_types = [
        'aree_verdi', 'parcheggi', 'fermate_bus', 'stazioni_ferroviarie',
        'scuole', 'cinema', 'ospedali', 'farmacia', 'colonnina_elettrica', 'biblioteca'
    ]
    result = {poi_type: 0 for poi_type in poi_types}

    try:
        # Query ottimizzata che utilizza l'indice spaziale idx_poi_location_3857
        # Usa ST_DWithin con coordinate proiettate per misure di distanza accurate
        poi_counts = db.session.query(
            POI.type,
            func.count(POI.id).label('count')
        ).filter(
            func.ST_DWithin(
                func.ST_Transform(POI.location, 3857),  # Proietta i POI in Web Mercator
                func.ST_Transform(marker.marker, 3857), # Proietta il marker in Web Mercator
                distance_meters  # La distanza in metri è corretta in SRID 3857
            )
        ).group_by(POI.type).all()

        # Popola il dizionario dei risultati
        for poi_type, count in poi_counts:
            if poi_type in result:
                result[poi_type] = count

        return result

    except Exception as e:
        print(f"Errore nel conteggio dei POI vicini: {str(e)}")
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
    limit = 100
    
    # Dizionario per tracciare le fermate uniche per coordinate
    bus_stops = {}
    
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
                    
                    if poi_type == 'fermate_bus':
                        # Crea una chiave unica basata sulle coordinate
                        location_key = f"{lat},{lon}"
                        
                        # Estrai le informazioni sulla linea
                        line_info = {
                            'codice_linea': poi.get('codice_linea'),
                            'denominazione': poi.get('denominazione'),
                            'ubicazione': poi.get('ubicazione')
                        }
                        
                        if location_key in bus_stops:
                            # Aggiorna le informazioni esistenti
                            existing_stop = bus_stops[location_key]
                            if line_info['codice_linea'] not in [l['codice_linea'] for l in existing_stop['lines']]:
                                existing_stop['lines'].append(line_info)
                        else:
                            # Crea una nuova fermata
                            bus_stops[location_key] = {
                                'lat': lat,
                                'lon': lon,
                                'denominazione': poi.get('denominazione'),
                                'ubicazione': poi.get('ubicazione'),
                                'quartiere': poi.get('quartiere'),
                                'comune': poi.get('comune'),
                                'lines': [line_info]
                            }
                    else:
                        # Per altri tipi di POI, procedi come prima
                        new_poi = POI(
                            type=poi_type,
                            location=f'POINT({lon} {lat})',
                            additional_data=json.dumps(poi)
                        )
                        db.session.add(new_poi)
                        total_count += 1
                        
                except ValueError as e:
                    print(f"Errore nell'elaborazione del POI: {e}")
            
            if poi_type != 'fermate_bus':
                db.session.commit()
            
            offset += limit
            print(f"Elaborati {len(results)} risultati per {poi_type}")
        else:
            print(f"Errore nella richiesta API per {poi_type}: {response.status_code}")
            break
    
    # Alla fine, inserisci tutte le fermate bus unificate
    if poi_type == 'fermate_bus':
        for stop_data in bus_stops.values():
            new_poi = POI(
                type=poi_type,
                location=f"POINT({stop_data['lon']} {stop_data['lat']})",
                additional_data=json.dumps({
                    'denominazione': stop_data['denominazione'],
                    'ubicazione': stop_data['ubicazione'],
                    'quartiere': stop_data['quartiere'],
                    'comune': stop_data['comune'],
                    'lines': stop_data['lines']
                })
            )
            db.session.add(new_poi)
            total_count += 1
        db.session.commit()
        print(f"Inserite {total_count} fermate bus uniche")
    
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
        'colonnina_elettrica': 'https://opendata.comune.bologna.it//api/explore/v2.1/catalog/datasets/colonnine-elettriche/records',
        'biblioteca': 'https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/biblioteche-comunali-di-bologna/records',
        'stazioni_ferroviarie': 'https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/stazioniferroviarie_20210401/records'
    }
    results = {}
    for poi_type, api_url in poi_sources.items():
        count = fetch_and_insert_pois(poi_type, api_url)
        results[poi_type] = count
    return results


@utils_bp.route('/get_markers')
def get_markers():
    markers = ListaImmobiliCandidati.query.all()
    marker_list = []
    for marker in markers:
        if marker.marker is not None:
            point = to_shape(marker.marker)
            geojson = mapping(point)
            marker_list.append({
                'lat': geojson['coordinates'][1],
                'lng': geojson['coordinates'][0],
                'price': marker.marker_price
            })
    return jsonify(marker_list)

@utils_bp.route('/get-geofences')
def get_geofences():
    immobili = ListaImmobiliCandidati.query.all()
    aree = ListaAreeCandidate.query.all()
    geofences_data = []

    for immobile in immobili:
        point = to_shape(immobile.marker)
        geofences_data.append({
            'id': immobile.id,
            'type': 'marker',
            'marker': mapping(point),
            'price': immobile.marker_price
        })
    
    for area in aree:
        polygon = to_shape(area.geofence)
        geofences_data.append({
            'id': area.id,
            'type': 'geofence',
            'geofence': mapping(polygon)
        })

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
        'colonnina_elettrica': response.colonnina_elettrica,
        'biblioteca': response.biblioteca,
        'densita_aree_verdi': response.densita_aree_verdi,
        'densita_fermate_bus': response.densita_fermate_bus
    }

def calcola_rank(marker_id, raggio):
    """
    Calcola il punteggio del marker con un sistema più permissivo e meglio allineato
    con le posizioni ottimali.
    """
    nearby_pois = count_nearby_pois(db, marker_id=marker_id, distance_meters=raggio)
    response = QuestionnaireResponse.query.first()
    user_preferences = get_questionnaire_response_dict(response)
    if not user_preferences:
        return 0

    rank = 0
    
    # Pesi base più generosi
    pesi = {
        'aree_verdi': 1.0,
        'parcheggi': 1.0,
        'fermate_bus': 1.0,
        'stazioni_ferroviarie': 1.0,
        'scuole': 1.0,
        'cinema': 0.8,
        'ospedali': 1.0,
        'farmacia': 0.8,
        'colonnina_elettrica': 0.6,
        'biblioteca': 0.8,
    }

    for poi_type in nearby_pois:
        count = nearby_pois.get(poi_type, 0)
        preferenza = user_preferences.get(poi_type, 0)
        peso_base = pesi.get(poi_type, 0.5)

        # Calcolo base del punteggio più generoso
        if count > 0:
            # Bonus crescente ma con diminishing returns per più POI
            poi_score = preferenza * peso_base * (1 + min(count, 5) / 2) * 25

            # Gestione speciale per densità
            if poi_type == 'aree_verdi' and count >= 2:
                density_bonus = user_preferences.get('densita_aree_verdi', 0) * 10
                poi_score += density_bonus

            if poi_type == 'fermate_bus' and count >= 2:
                density_bonus = user_preferences.get('densita_fermate_bus', 0) * 10
                poi_score += density_bonus

            rank += poi_score

        # Bonus per combinazioni strategiche
        if poi_type == 'stazioni_ferroviarie' and count >= 1:
            if nearby_pois.get('fermate_bus', 0) >= 1:
                rank += preferenza * 20

        if poi_type == 'biblioteca' and count >= 1:
            if nearby_pois.get('farmacia', 0) >= 1:
                rank += preferenza * 15

    # Normalizzazione più permissiva
    # Considerando che ogni POI può contribuire fino a circa 125 punti (25 * 5 di preferenza)
    # e ci sono bonus aggiuntivi, scaliamo il punteggio in modo più generoso
    max_theoretical = sum(pesi.values()) * 5 * 25  # Punteggio teorico massimo
    normalized_rank = (rank / max_theoretical) * 200  # Scala fino a 200

    # Aggiustiamo la scala finale per avere più punti verdi/gialli
    if normalized_rank > 70:  # Se il punteggio è decente
        # Boost non lineare per punteggi sopra 70
        normalized_rank = 70 + (normalized_rank - 70) * 1.5

    # Cap finale più alto
    final_rank = min(normalized_rank, 200)
    
    return final_rank

@utils_bp.route('/get_ranked_markers')
def get_ranked_markers():
    try:
        if QuestionnaireResponse.query.count() == 0:
            return jsonify({"error": "No questionnaires found"}), 404

        global global_radius
        
        markers = ListaImmobiliCandidati.query.all()
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
                    'rank': rank,
                    'price': marker.marker_price
                })
            except Exception as e:
                print(f"Errore nell'elaborazione del marker {marker.id}: {str(e)}")
        
        return jsonify(ranked_markers)
    except Exception as e:
        print(f"Errore generale in get_ranked_markers: {str(e)}")
        return jsonify({"error": str(e)}), 500
    
def count_pois_in_geofence(db, geofence_id):
    """
    Conta i POI all'interno di un'area (geofence) utilizzando indici spaziali.
    Utilizza ST_Contains e gli indici spaziali per una ricerca efficiente.
    
    Args:
        db: istanza del database
        geofence_id: ID dell'area di riferimento
        
    Returns:
        dizionario con il conteggio dei POI per tipo
    """
    # Ottieni il geofence specifico dal database
    geofence = db.session.query(ListaAreeCandidate).get(geofence_id)
    if not geofence:
        return None

    # Definisci i tipi di POI da contare
    poi_types = [
        'aree_verdi', 'parcheggi', 'fermate_bus', 'stazioni_ferroviarie',
        'scuole', 'cinema', 'ospedali', 'farmacia', 'colonnina_elettrica', 'biblioteca'
    ]
    result = {poi_type: 0 for poi_type in poi_types}

    try:
        # Query ottimizzata che utilizza l'indice spaziale e ST_Contains
        # ST_Contains verifica se il POI è completamente contenuto nel geofence
        poi_counts = db.session.query(
            POI.type,
            func.count(POI.id).label('count')
        ).filter(
            func.ST_Contains(
                geofence.geofence,  # Il poligono del geofence
                POI.location        # La posizione del POI
            )
        ).group_by(POI.type).all()

        # Popola il dizionario dei risultati
        for poi_type, count in poi_counts:
            if poi_type in result:
                result[poi_type] = count

        return result

    except Exception as e:
        print(f"Errore nel conteggio dei POI nell'area: {str(e)}")
        return result

# Funzione opzionale per contare i POI con buffer intorno al geofence
def count_pois_near_geofence(db, geofence_id, buffer_meters=100):
    """
    Conta i POI all'interno e vicino a un'area con un buffer specificato.
    Utile per considerare anche i POI nelle immediate vicinanze dell'area.
    
    Args:
        db: istanza del database
        geofence_id: ID dell'area di riferimento
        buffer_meters: dimensione del buffer in metri
        
    Returns:
        dizionario con il conteggio dei POI per tipo
    """
    geofence = db.session.query(ListaAreeCandidate).get(geofence_id)
    if not geofence:
        return None

    poi_types = [
        'aree_verdi', 'parcheggi', 'fermate_bus', 'stazioni_ferroviarie',
        'scuole', 'cinema', 'ospedali', 'farmacia', 'colonnina_elettrica', 'biblioteca'
    ]
    result = {poi_type: 0 for poi_type in poi_types}

    try:
        # Query ottimizzata che usa ST_DWithin per considerare anche i POI vicini all'area
        poi_counts = db.session.query(
            POI.type,
            func.count(POI.id).label('count')
        ).filter(
            func.ST_DWithin(
                func.ST_Transform(POI.location, 3857),
                func.ST_Transform(geofence.geofence, 3857),
                buffer_meters
            )
        ).group_by(POI.type).all()

        for poi_type, count in poi_counts:
            if poi_type in result:
                result[poi_type] = count

        return result

    except Exception as e:
        print(f"Errore nel conteggio dei POI nell'area con buffer: {str(e)}")
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
        'colonnina_elettrica': 0.2,
        'biblioteca': 0.4,
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
    rank += nearby_pois.get('colonnina_elettrica', 0) * user_preferences['colonnina_elettrica'] * pesi['colonnina_elettrica']
    
    # Servizi
    if nearby_pois.get('biblioteca', 0) >= 2:
        rank += user_preferences['biblioteca'] * pesi['biblioteca']
    
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

        geofences = ListaAreeCandidate.query.filter(ListaAreeCandidate.geofence.isnot(None)).all()
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


@utils_bp.route('/delete-all-geofences', methods=['POST'])
def delete_all_geofences():
    try:
        ListaImmobiliCandidati.query.delete()
        ListaAreeCandidate.query.delete()
        db.session.commit()
        return jsonify({"message": "Tutti i geofence e i marker sono stati cancellati"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
    
@utils_bp.route('/delete-geofence/<int:geofence_id>', methods=['DELETE'])
def delete_geofence(geofence_id):
    try:
        immobile = ListaImmobiliCandidati.query.get(geofence_id)
        if immobile:
            db.session.delete(immobile)
            db.session.commit()
            return jsonify({"message": f"Immobile con ID {geofence_id} eliminato con successo"}), 200
        
        area = ListaAreeCandidate.query.get(geofence_id)
        if area:
            db.session.delete(area)
            db.session.commit()
            return jsonify({"message": f"Area con ID {geofence_id} eliminata con successo"}), 200
        
        return jsonify({"error": f"Geofence con ID {geofence_id} non trovato"}), 404
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@utils_bp.route('/get_all_geofences')
def get_all_geofences():
    try:
        if QuestionnaireResponse.query.count() == 0:
            return jsonify({"error": "No questionnaires found"}), 404

        immobili = ListaImmobiliCandidati.query.all()
        aree = ListaAreeCandidate.query.all()
        all_geofences = []
        
        for immobile in immobili:
            lat = db.session.scalar(ST_Y(immobile.marker))
            lng = db.session.scalar(ST_X(immobile.marker))
            rank = calcola_rank(immobile.id, raggio=global_radius)
            all_geofences.append({
                'id': immobile.id,
                'type': 'marker',
                'lat': lat,
                'lng': lng,
                'rank': rank,
                'price': immobile.marker_price
            })
        
        for area in aree:
            centroid = db.session.scalar(ST_Centroid(area.geofence))
            centroid_lat = db.session.scalar(func.ST_Y(centroid))
            centroid_lng = db.session.scalar(func.ST_X(centroid))
            rank = calcola_rank_geofence(area.id)
            geofence_geojson = db.session.scalar(ST_AsGeoJSON(area.geofence))
            geofence_dict = json.loads(geofence_geojson)
            coordinates = geofence_dict['coordinates'][0]
            all_geofences.append({
                'id': area.id,
                'type': 'polygon',
                'centroid': {
                    'lat': centroid_lat,
                    'lng': centroid_lng
                },
                'coordinates': coordinates,
                'rank': rank
            })
        
        return jsonify(all_geofences)
    except Exception as e:
        print(f"Errore generale in get_all_geofences: {str(e)}")
        return jsonify({"error": str(e)}), 50

def get_bologna_bounds():
    return {
        'min_lat': 44.4, 'max_lat': 44.6,
        'min_lon': 11.2, 'max_lon': 11.4
    }
def create_grid(bounds, grid_size):
    lats = np.linspace(bounds['min_lat'], bounds['max_lat'], grid_size)
    lons = np.linspace(bounds['min_lon'], bounds['max_lon'], grid_size)
    return [(float(lat), float(lon)) for lat in lats for lon in lons]

def create_centered_grid(center_lat, center_lon, radius, density):
    lat_offset = radius / 111000  # Approssimazione dei gradi di latitudine per metro
    lon_offset = radius / (111000 * np.cos(np.radians(center_lat)))

    lats = np.linspace(center_lat - lat_offset, center_lat + lat_offset, density)
    lons = np.linspace(center_lon - lon_offset, center_lon + lon_offset, density)

    return [(float(lat), float(lon)) for lat in lats for lon in lons]

@lru_cache(maxsize=1000)
def count_pois_near_point(lat, lon, radius):
    """
    Conta i POI vicino a un punto usando la stessa logica di count_nearby_pois.
    """
    query = text("""
    SELECT type, COUNT(*) as count
    FROM points_of_interest
    WHERE ST_DWithin(
        ST_Transform(location, 3857),
        ST_Transform(ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), 3857),
        :radius
    )
    GROUP BY type
    """)
    
    try:
        with db.engine.connect() as connection:
            result = connection.execute(query, {'lat': lat, 'lon': lon, 'radius': radius})
            counts = {row.type: row.count for row in result}
            return counts
    except SQLAlchemyError as e:
        print(f"Errore nell'esecuzione della query: {str(e)}")
        return {}
    

def calculate_rank_for_point(poi_counts, user_preferences):
    """
    Calcola il rank di un punto con una normalizzazione più bilanciata
    """
    if not user_preferences or not poi_counts:
        return 0

    rank = 0
    
    # Pesi base per ciascun tipo di POI
    pesi = {
        'aree_verdi': 1.0,
        'parcheggi': 1.0,
        'fermate_bus': 1.0,
        'stazioni_ferroviarie': 1.2,  # Peso maggiore per servizi importanti
        'scuole': 1.1,
        'cinema': 0.7,
        'ospedali': 1.2,
        'farmacia': 0.9,
        'colonnina_elettrica': 0.6,
        'biblioteca': 0.8,
    }

    # Soglie massime per tipo di POI (oltre queste il bonus diminuisce)
    max_counts = {
        'aree_verdi': 3,
        'parcheggi': 4,
        'fermate_bus': 5,
        'stazioni_ferroviarie': 2,
        'scuole': 3,
        'cinema': 2,
        'ospedali': 2,
        'farmacia': 3,
        'colonnina_elettrica': 2,
        'biblioteca': 4,
    }

    for poi_type, count in poi_counts.items():
        if poi_type not in pesi or poi_type not in max_counts:
            continue

        preferenza = user_preferences.get(poi_type, 0)
        if preferenza == 0:
            continue

        peso_base = pesi[poi_type]
        max_count = max_counts[poi_type]
        
        if count > 0:
            # Calcolo base del punteggio con diminishing returns
            normalized_count = min(count, max_count) / max_count
            base_score = preferenza * peso_base * normalized_count * 20

            # Bonus per ogni POI aggiuntivo oltre il primo, ma con diminishing returns
            if count > 1:
                additional_bonus = min(count - 1, max_count - 1) * 5
                base_score += additional_bonus

            # Gestione bonus densità
            if poi_type == 'aree_verdi' and count >= 2:
                density_bonus = user_preferences.get('densita_aree_verdi', 0) * 8
                base_score += density_bonus

            if poi_type == 'fermate_bus' and count >= 2:
                density_bonus = user_preferences.get('densita_fermate_bus', 0) * 8
                base_score += density_bonus

            rank += base_score

    # Bonus per combinazioni strategiche
    if poi_counts.get('stazioni_ferroviarie', 0) >= 1 and poi_counts.get('fermate_bus', 0) >= 1:
        rank += 15  # Bonus per intermodalità

    if poi_counts.get('biblioteca', 0) >= 1 and poi_counts.get('farmacia', 0) >= 1:
        rank += 10  # Bonus per servizi complementari

    # Normalizzazione più bilanciata
    max_theoretical = sum(pesi.values()) * 5 * 20  # Punteggio teorico massimo base
    max_theoretical += 50  # Aggiungi spazio per i bonus
    normalized_rank = (rank / max_theoretical) * 100  # Scala da 0 a 100

    # Applicazione curve più graduale
    if normalized_rank > 70:
        normalized_rank = 70 + (normalized_rank - 70) * 0.8
    
    return min(round(normalized_rank, 2), 100)  # Arrotonda a 2 decimali e limita a 100


def diverse_locations_selection(locations, num_locations=10, min_distance=0.008):
    """
    Seleziona le locations più diverse tra loro basandosi sia sulla distanza che sul rank
    """
    if not locations:
        return []

    diverse_locations = []
    locations.sort(key=lambda x: x['rank'], reverse=True)

    # Seleziona sempre il punto con il rank più alto
    diverse_locations.append(locations[0])

    for loc in locations[1:]:
        if len(diverse_locations) >= num_locations:
            break

        # Calcola la distanza minima da tutti i punti già selezionati
        distances = []
        for selected in diverse_locations:
            dist = ((loc['lat'] - selected['lat'])**2 + 
                   (loc['lng'] - selected['lng'])**2)**0.5
            distances.append(dist)

        min_dist = min(distances)

        # Se il punto è abbastanza distante e ha un rank sufficientemente diverso
        if min_dist >= min_distance:
            # Verifica che il rank sia sufficientemente diverso dai punti vicini
            ranks_near = [s['rank'] for s in diverse_locations 
                        if ((loc['lat'] - s['lat'])**2 + 
                            (loc['lng'] - s['lng'])**2)**0.5 < min_distance * 2]
            
            if not ranks_near or abs(loc['rank'] - sum(ranks_near)/len(ranks_near)) > 5:
                diverse_locations.append(loc)

    return diverse_locations  
    
def calculate_rank(poi_counts, user_preferences):
    weights = {
        'aree_verdi': 0.8,
        'parcheggi': 1.0,
        'fermate_bus': 1.0,
        'stazioni_ferroviarie': 1.0,
        'scuole': 0.7,
        'cinema': 0.6,
        'ospedali': 1.0,
        'farmacia': 0.5,
        'colonnina_elettrica': 0.2,
        'biblioteca': 0.4,
    }
    return sum(count * user_preferences.get(poi_type, 0) * weights.get(poi_type, 1)
               for poi_type, count in poi_counts.items())


@utils_bp.route('/calculate_optimal_locations', methods=['GET'])
def calculate_optimal_locations():
    """
    Calcola le 10 migliori posizioni per l'acquisto di una casa a Bologna
    basandosi sui POI vicini e le preferenze dell'utente.
    """
    print("Inizio calculate_optimal_locations")
    start_time = time.time()
    
    try:
        # Verifica presenza questionario
        user_prefs = QuestionnaireResponse.query.first()
        if not user_prefs:
            return jsonify({
                "error": "Nessun questionario trovato. Completa il questionario prima.",
                "execution_time_seconds": time.time() - start_time
            }), 400
        
        user_preferences = get_questionnaire_response_dict(user_prefs)
        
        # Definisci i bounds di Bologna con area leggermente più ampia
        bounds = {
            'min_lat': 44.4, 'max_lat': 44.6,
            'min_lon': 11.2, 'max_lon': 11.4
        }
        
        # Query SQL per la griglia e conteggio POI
        sql_query = """
            WITH RECURSIVE grid_points AS (
                SELECT ST_SetSRID(
                    ST_MakePoint(
                        :min_lon + (n % 30) * (:max_lon - :min_lon) / 30,
                        :min_lat + (n / 30) * (:max_lat - :min_lat) / 30
                    ),
                    4326
                ) AS point
                FROM generate_series(0, 899) n
            ),
            poi_counts AS (
                SELECT 
                    ST_X(g.point) as lng,
                    ST_Y(g.point) as lat,
                    p.type,
                    COUNT(*) as count
                FROM grid_points g
                JOIN points_of_interest p ON ST_DWithin(
                    ST_Transform(g.point, 3857),
                    ST_Transform(p.location, 3857),
                    500
                )
                GROUP BY g.point, p.type
            )
            SELECT 
                lng,
                lat,
                type,
                count
            FROM poi_counts;
        """
        
        # Esegui la query
        results = []
        rank_distribution = {
            '0-20': 0, '21-40': 0, '41-60': 0, '61-80': 0, '81-100': 0
        }
        
        with db.engine.connect() as conn:
            grid_results = conn.execute(text(sql_query), bounds)
            
            # Raggruppa i risultati per coordinate
            points_data = {}
            for row in grid_results:
                key = (float(row.lng), float(row.lat))
                if key not in points_data:
                    points_data[key] = {}
                points_data[key][row.type] = row.count

            # Calcola il rank per ogni punto
            for (lng, lat), poi_counts in points_data.items():
                rank = calculate_rank_for_point(poi_counts, user_preferences)
                
                # Aggiorna la distribuzione dei rank
                if rank <= 20: rank_distribution['0-20'] += 1
                elif rank <= 40: rank_distribution['21-40'] += 1
                elif rank <= 60: rank_distribution['41-60'] += 1
                elif rank <= 80: rank_distribution['61-80'] += 1
                else: rank_distribution['81-100'] += 1
                
                if rank > 40:  # Consideriamo punti con rank > 40
                    results.append({
                        'lat': lat,
                        'lng': lng,
                        'rank': rank,
                        'poi_counts': poi_counts
                    })

        # Usa la nuova funzione per selezionare locations diverse
        diverse_locations = diverse_locations_selection(results)
        
        # Aggiungi dettagli POI per le locations selezionate
        for loc in diverse_locations:
            poi_summary = {
                'total_poi': sum(loc['poi_counts'].values()),
                'details': loc['poi_counts']
            }
            loc['poi_details'] = poi_summary
            del loc['poi_counts']

        execution_time = time.time() - start_time
        
        return jsonify({
            "message": "Le 10 migliori posizioni suggerite per acquistare casa a Bologna:",
            "suggestions": diverse_locations,
            "execution_time_seconds": execution_time,
            "total_locations_analyzed": len(results),
            "rank_distribution": rank_distribution,
            "user_preferences": user_preferences,
            "search_parameters": {
                "radius_meters": 500,
                "min_rank_threshold": 40,
                "min_distance_between_points": 0.008 * 111000  # Conversione approssimativa in metri
            }
        })

    except Exception as e:
        print(f"Errore in calculate_optimal_locations: {str(e)}")
        return jsonify({
            "error": str(e),
            "execution_time_seconds": time.time() - start_time
        }), 500


@utils_bp.route('/addMarkerPrice', methods=['POST'])
def add_marker_price():
    data = request.get_json()
    geofence_id = data.get('geofenceId')
    price = data.get('price')

    if price is None or price <= 0:
        return jsonify({'error': 'Prezzo non valido'}), 400

    geofence = ListaImmobiliCandidati.query.get(geofence_id)

    if not geofence:
        return jsonify({'error': 'Geofence non trovato'}), 404

    geofence.marker_price = price
    db.session.commit()

    return jsonify({'success': True, 'message': f'Prezzo di {price} aggiunto per il marker {geofence_id}'})


def process_point(point, user_preferences, radius):
    """
    Processa un punto per il calcolo delle posizioni ottimali usando la stessa funzione di ranking.
    """
    lat, lon = point
    poi_counts = count_pois_near_point(lat, lon, radius)
    
    rank = calculate_rank_for_point(poi_counts, user_preferences)
    if rank > 70:  # Considera solo punti con un punteggio decente
        return {
            'lat': lat,
            'lng': lon,
            'rank': rank
        }
    return None


@utils_bp.route('/calculate_morans_i', methods=['GET'])
def calculate_morans_i():
    try:
        # Recupera immobili con prezzo
        immobili = db.session.query(
            ListaImmobiliCandidati
        ).filter(
            ListaImmobiliCandidati.marker_price.isnot(None)
        ).all()
        
        if len(immobili) < 2:
            return jsonify({
                'error': 'Servono almeno due immobili con prezzo per calcolare l\'indice di Moran'
            }), 400

        # Estrai coordinate e prezzi
        coords = []
        prices = []
        threshold_distance = 500  # metri
        
        for immobile in immobili:
            point = to_shape(immobile.marker)
            coords.append([point.y, point.x])  # [lat, lon]
            prices.append(float(immobile.marker_price))

        coords = np.array(coords)
        prices = np.array(prices)
        
        # Calcola densità POI
        poi_densities = []
        for immobile in immobili:
            poi_count = db.session.query(func.count(POI.id)).filter(
                ST_Distance(
                    ST_Transform(POI.location, 3857),
                    ST_Transform(immobile.marker, 3857)
                ) <= threshold_distance
            ).scalar()
            poi_densities.append(poi_count)
        
        poi_densities = np.array(poi_densities)
        
        # Calcola matrice delle distanze e dei pesi
        dist_matrix = cdist(coords, coords)
        W = np.where(dist_matrix <= threshold_distance, 1, 0)
        np.fill_diagonal(W, 0)
        row_sums = W.sum(axis=1)
        row_sums[row_sums == 0] = 1
        W = W / row_sums[:, np.newaxis]
        
        # Calcola Moran's I per prezzi
        z_prices = prices - np.mean(prices)
        numerator_prices = np.sum(W * np.outer(z_prices, z_prices))
        denominator_prices = np.sum(z_prices**2)
        W_sum = np.sum(W)
        I_prices = (len(prices) / W_sum) * (numerator_prices / denominator_prices)
        
        # Calcola Moran's I per densità POI
        z_poi = poi_densities - np.mean(poi_densities)
        numerator_poi = np.sum(W * np.outer(z_poi, z_poi))
        denominator_poi = np.sum(z_poi**2)
        I_poi = (len(poi_densities) / W_sum) * (numerator_poi / denominator_poi)
        
        return jsonify({
            'morans_i_prices': float(I_prices),
            'morans_i_poi_density': float(I_poi),
            'threshold_distance': threshold_distance,
            'statistics': {
                'num_immobili': len(immobili),
                'prezzo_medio': float(np.mean(prices)),
                'prezzo_std': float(np.std(prices)),
                'poi_density_mean': float(np.mean(poi_densities)),
                'poi_density_std': float(np.std(poi_densities))
            }
        })
    
    except Exception as e:
        print(f"Errore nel calcolo dell'indice di Moran: {str(e)}")
        return jsonify({'error': str(e)}), 500
    

@utils_bp.route('/api/filters', methods=['POST'])
def save_and_return_filters():
    try:
        # Raccoglie i dati JSON dalla richiesta
        data = request.get_json()
        
        # Salva i dati nell'oggetto globale `saved_filters`
        global saved_filters
        saved_filters = {
            "distanceEnabled": data.get("distanceEnabled", False),
            "travelMode": data.get("travelMode", "driving"),
            "travelTime": data.get("travelTime", 5)
        }
        logging.info(f"Valore attuale di saved_filters: {saved_filters}")
        # Restituisce i dati in formato JSON
        return jsonify(saved_filters), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 400  # Errore generico in caso di eccezione
    

def calculate_travel_time_batch(start_coords, destinations, transport_mode, batch_size=10):
    """
    Calcola il tempo di percorrenza per gruppi di destinazioni più piccoli.
    """
    all_travel_times = {}
    
    for i in range(0, len(destinations), batch_size):
        batch = destinations[i:i + batch_size]
        
        try:
            # Costruisci la stringa delle coordinate
            coords = [f"{start_coords[1]:.6f},{start_coords[0]:.6f}"]
            for lat, lon in batch:
                coords.append(f"{lon:.6f},{lat:.6f}")
            
            coordinates_str = ";".join(coords)
            url = f"http://router.project-osrm.org/table/v1/{transport_mode}/{coordinates_str}"
            
            # Costruisci la stringa delle destinazioni
            destinations_str = ",".join(str(j) for j in range(1, len(coords)))
            
            params = {
                "sources": "0",
                "destinations": destinations_str,
                "annotations": "duration"
            }
            
            logging.debug(f"Requesting URL: {url}, params: {params}")
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == "Ok":
                    durations = data["durations"][0]
                    for idx, duration in enumerate(durations):
                        all_travel_times[i + idx] = duration / 60  # Converti in minuti
                else:
                    logging.error(f"OSRM API error for batch {i}: {data}")
                    for idx in range(len(batch)):
                        all_travel_times[i + idx] = float('inf')
            else:
                logging.error(f"HTTP error {response.status_code} for batch {i}")
                for idx in range(len(batch)):
                    all_travel_times[i + idx] = float('inf')
                
        except Exception as e:
            logging.error(f"Error processing batch {i}: {str(e)}")
            for idx in range(len(batch)):
                all_travel_times[i + idx] = float('inf')
            continue
        
        # Aggiungi un piccolo ritardo tra le richieste per non sovraccaricare il server
        time.sleep(0.1)
    
    return all_travel_times

@utils_bp.route('/api/filter_pois/<poi_type>', methods=['GET'])
def get_pois_by_type_and_travel_time(poi_type):
    """
    Restituisce i POI di un determinato tipo filtrati per tempo di viaggio,
    sfruttando gli indici spaziali compositi e funzionali.
    """
    try:
        global saved_filters
        logging.info(f"Filtri correnti: {saved_filters}")
        
        if not saved_filters["distanceEnabled"]:
            return get_pois_by_type(poi_type)
        
        # Centro di Bologna
        start_coords = (44.4949, 11.3426)
        
        # Stima delle velocità medie per modalità di trasporto
        estimated_speed = {
            'walking': 83,     # ~5km/h -> 83m/min
            'cycling': 250,    # ~15km/h -> 250m/min
            'driving': 500     # ~30km/h in città -> 500m/min
        }
        
        # Calcola il raggio del buffer basato sul tempo e modalità
        max_radius = estimated_speed[saved_filters["travelMode"]] * saved_filters["travelTime"]
        
        # Query ottimizzata che sfrutta entrambi gli indici
        query = text("""
            WITH center_point AS (
                SELECT ST_Transform(ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), 3857) as center_3857
            ),
            prefiltered_pois AS (
                SELECT 
                    poi.id,
                    poi.location,
                    poi.additional_data,
                    ST_Distance(
                        ST_Transform(poi.location, 3857),
                        cp.center_3857
                    ) as distance_meters
                FROM points_of_interest poi
                CROSS JOIN center_point cp
                WHERE poi.type = :poi_type  -- Usa l'indice composito idx_poi_type_location
                AND ST_DWithin(
                    ST_Transform(poi.location, 3857),  -- Usa l'indice idx_poi_location_3857
                    cp.center_3857,
                    :max_radius
                )
            )
            SELECT 
                id,
                ST_X(location::geometry) as longitude,
                ST_Y(location::geometry) as latitude,
                additional_data,
                distance_meters
            FROM prefiltered_pois
            ORDER BY distance_meters
        """)
        
        # Esegui la query con i parametri
        result = db.session.execute(query, {
            'lon': start_coords[1],
            'lat': start_coords[0],
            'poi_type': poi_type,
            'max_radius': max_radius
        })
        
        # Prepara i dati pre-filtrati
        pois_data = []
        poi_coords = []
        
        for row in result:
            poi_data = {
                'id': row.id,
                'type': poi_type,
                'lat': float(row.latitude),
                'lng': float(row.longitude),
                'distance': float(row.distance_meters)
            }
            
            if row.additional_data:
                try:
                    additional_data = json.loads(row.additional_data)
                    poi_data['properties'] = additional_data
                except json.JSONDecodeError:
                    logging.error(f"Errore nel parsing dei dati addizionali per POI {row.id}")
                    poi_data['properties'] = {}
            
            pois_data.append(poi_data)
            poi_coords.append((float(row.latitude), float(row.longitude)))
        
        logging.info(f"Pre-filtrati {len(pois_data)} POI usando indici spaziali compositi")
        
        if not pois_data:
            return jsonify({
                'status': 'success',
                'count': 0,
                'data': []
            })
        
        # Calcola i tempi di viaggio effettivi in batch
        travel_times = calculate_travel_time_batch(
            start_coords, 
            poi_coords,
            saved_filters["travelMode"],
            batch_size=10
        )
        
        # Filtra e ordina i POI per tempo di viaggio
        filtered_pois = []
        for i, time in travel_times.items():
            if time <= saved_filters["travelTime"]:
                poi = pois_data[i]
                poi['travel_time'] = time
                filtered_pois.append(poi)
        
        # Ordina per tempo di viaggio
        filtered_pois.sort(key=lambda x: x['travel_time'])
        
        logging.info(f"Restituisco {len(filtered_pois)} POI filtrati per tempo di viaggio effettivo")
        
        return jsonify({
            'status': 'success',
            'count': len(filtered_pois),
            'data': filtered_pois,
            'query_info': {
                'estimated_radius': max_radius,
                'prefiltered_count': len(pois_data),
                'final_count': len(filtered_pois)
            }
        })
        
    except Exception as e:
        logging.error(f"Errore generale in get_pois_by_type_and_travel_time: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500