from flask import jsonify, request, Blueprint
from geoalchemy2.shape import from_shape, to_shape
from models import *
import json, logging
import requests
from shapely.geometry import mapping, Point, Polygon
from shapely.wkt import loads
from sqlalchemy import func, text, case
from geoalchemy2.functions import *
import numpy as np
import time
from flask_caching import Cache
from functools import lru_cache
from sqlalchemy.exc import SQLAlchemyError
from scipy.spatial.distance import cdist
import math


logging.basicConfig(level=logging.DEBUG)

global_radius = 500
saved_filters = {}

utils_bp = Blueprint("utils", __name__)


def update_pois():
    poi_sources = {
        "parcheggi": "https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/parcheggi/records",
        "cinema": "https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/teatri-cinema-teatri/records",
        "farmacia": "https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/farmacie/records",
        "ospedali": "https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/strutture-sanitarie/records",
        "fermate_bus": "https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/tper-fermate-autobus/records",
        "scuole": "https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/elenco-delle-scuole/records",
        "aree_verdi": "https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/carta-tecnica-comunale-toponimi-parchi-e-giardini/records",
        "colonnina_elettrica": "https://opendata.comune.bologna.it//api/explore/v2.1/catalog/datasets/colonnine-elettriche/records",
        "biblioteca": "https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/biblioteche-comunali-di-bologna/records",
        "stazioni_ferroviarie": "https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/stazioniferroviarie_20210401/records",
    }
    results = {}
    for poi_type, api_url in poi_sources.items():
        count = fetch_and_insert_pois(poi_type, api_url)
        results[poi_type] = count
    return results



# estrae le coordinate dei POI presei dall'api
def get_poi_coordinates(poi):
    if (
        "geo_point_2d" in poi
        and "lat" in poi["geo_point_2d"]
        and "lon" in poi["geo_point_2d"]
    ):
        # Handle geo_point_2d format
        return float(poi["geo_point_2d"]["lat"]), float(poi["geo_point_2d"]["lon"])
    elif (
        "geopoint" in poi
        and poi["geopoint"] is not None
        and "lat" in poi["geopoint"]
        and "lon" in poi["geopoint"]
    ):
        # Handle geopoint format, ensuring geopoint is not None
        return float(poi["geopoint"]["lat"]), float(poi["geopoint"]["lon"])
    elif (
        "coordinate" in poi
        and "lat" in poi["coordinate"]
        and "lon" in poi["coordinate"]
    ):
        # Handle coordinate format for parking data
        return float(poi["coordinate"]["lat"]), float(poi["coordinate"]["lon"])
    elif "ycoord" in poi and "xcoord" in poi:
        # Handle ycoord/xcoord format
        return float(poi["ycoord"]), float(poi["xcoord"])
    elif (
        "geo_shape" in poi
        and "geometry" in poi["geo_shape"]
        and "coordinates" in poi["geo_shape"]["geometry"]
    ):
        # Handle geo_shape (GeoJSON) format
        coordinates = poi["geo_shape"]["geometry"]["coordinates"]
        return float(coordinates[1]), float(
            coordinates[0]
        )  #  l'ordine è [lon, lat] in GeoJSON
    elif "geo_point" in poi and "lat" in poi["geo_point"] and "lon" in poi["geo_point"]:
        # Handle geo_point format
        return float(poi["geo_point"]["lat"]), float(poi["geo_point"]["lon"])
    else:
        raise ValueError("Formato coordinate non riconosciuto")


# inserisce i poi nel db, viene usata una logica speciale per gestire le fermate del bus,
# raggruppando i punti vicini
def fetch_and_insert_pois(poi_type, api_url):
    total_count = 0
    offset = 0
    limit = 100

    bus_stops = {}

    while True:
        if "tper-fermate-autobus" in api_url:
            paginated_url = (
                f"{api_url}?limit={limit}&offset={offset}&refine=comune%3A%22BOLOGNA%22"
            )
        else:
            paginated_url = f"{api_url}?limit={limit}&offset={offset}"

        response = requests.get(paginated_url)

        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])

            if not results:
                break
            for poi in results:
                
                    lat, lon = get_poi_coordinates(poi)

                    if poi_type == "fermate_bus":
                        # unique key
                        location_key = f"{lat},{lon}"

                        # estrai le informazioni sulla linea
                        line_info = {
                            "codice_linea": poi.get("codice_linea"),
                            "denominazione": poi.get("denominazione"),
                            "ubicazione": poi.get("ubicazione"),
                        }

                        if location_key in bus_stops:
                        
                            existing_stop = bus_stops[location_key]
                            if line_info["codice_linea"] not in [
                                l["codice_linea"] for l in existing_stop["lines"]
                            ]:
                                existing_stop["lines"].append(line_info)
                        else:
                            # Crea una nuova fermata
                            bus_stops[location_key] = {
                                "lat": lat,
                                "lon": lon,
                                "denominazione": poi.get("denominazione"),
                                "ubicazione": poi.get("ubicazione"),
                                "quartiere": poi.get("quartiere"),
                                "comune": poi.get("comune"),
                                "lines": [line_info],
                            }
                    else:
                        # per altri tipi di POI, procedi come prima
                        new_poi = POI(
                            type=poi_type,
                            location=f"POINT({lon} {lat})",
                            additional_data=json.dumps(poi),
                        )
                        db.session.add(new_poi)
                        total_count += 1


            if poi_type != "fermate_bus":
                db.session.commit()

            offset += limit

        else:
            print(f"Errore nella richiesta API {poi_type}: {response.status_code}")
            break

    # inserisci tutte le fermate bus unificate
    if poi_type == "fermate_bus":
        for stop_data in bus_stops.values():
            new_poi = POI(
                type=poi_type,
                location=f"POINT({stop_data['lon']} {stop_data['lat']})",
                additional_data=json.dumps(
                    {
                        "denominazione": stop_data["denominazione"],
                        "ubicazione": stop_data["ubicazione"],
                        "quartiere": stop_data["quartiere"],
                        "comune": stop_data["comune"],
                        "lines": stop_data["lines"],
                    }
                ),
            )
            db.session.add(new_poi)
            total_count += 1
        db.session.commit()

    return total_count


# ritorna i POI di un certo tipo
@utils_bp.route("/api/pois/<poi_type>", methods=["GET"])
def get_pois_by_type(poi_type):

        # prendi tutti i poi dal db
        pois = POI.query.filter_by(type=poi_type).all()

        poi_list = []
        for poi in pois:
            try:
                point = to_shape(poi.location)

                poi_data = {
                    "id": poi.id,
                    "type": poi_type,
                    "lat": point.y,  # Latitudine
                    "lng": point.x,  # Longitudine
                }

               
                if poi.additional_data:
                    
                        additional_data = json.loads(poi.additional_data)
                        poi_data["properties"] = additional_data
                        poi_data["properties"] = {}

                poi_list.append(poi_data)

            except Exception as e:
                return jsonify({"error": str(e)}), 500  
                continue
        return jsonify({"status": "success", "count": len(poi_list), "data": poi_list})


@utils_bp.route("/set_radius", methods=["POST"])
def set_radius():
    global global_radius
    global_radius = request.json.get("radius")
    return jsonify({"radius": global_radius}), 200

# salva un marker o un geofence nel database
@utils_bp.route("/save-geofence", methods=["POST"])
def save_geofence():
    data = request.json

    if "marker" in data:
        lat = data["marker"]["lat"]
        lng = data["marker"]["lng"]
        point = Point(lng, lat)
        new_immobile = ListaImmobiliCandidati(marker=from_shape(point, srid=4326))
        try:
            db.session.add(new_immobile)
            db.session.commit()
            return jsonify({"status": "success", "id": new_immobile.id})
        except Exception as e:
            db.session.rollback()
            return jsonify({"status": "error", "message": str(e)}), 500
    elif "geofence" in data:
        try:
            if isinstance(data["geofence"], str):
                polygon = loads(data["geofence"])
            else:
                coords = [(p["lng"], p["lat"]) for p in data["geofence"]]
                polygon = Polygon(coords)

            new_area = ListaAreeCandidate(geofence=from_shape(polygon, srid=4326))
            db.session.add(new_area)
            db.session.commit()
            return jsonify({"status": "success", "id": new_area.id})
        except Exception as e:
            db.session.rollback()
            return jsonify({"status": "error", "message": str(e)}), 500


# aggiunge le user preference nel db una volta configurato il questionario
@utils_bp.route("/submit-questionnaire", methods=["POST"])
def submit_questionnaire():
    try:
        data = request.get_json()
        existing_questionnaire = QuestionnaireResponse.query.first()
        if existing_questionnaire:
            for key, value in data.items():
                setattr(existing_questionnaire, key, value)
        else:
            new_questionnaire = QuestionnaireResponse(**data)
            db.session.add(new_questionnaire)

        db.session.commit()
        return jsonify({"status": "success"}), 200

    except Exception:
        db.session.rollback()
        return jsonify({"status": "error"}), 500


# calcila i poi vicini ad un marker, o all'interno di un poligono
def count_nearby_pois(location_id, distance_meters=None):
    unique_types = db.session.query(POI.type).distinct().all()
    poi_types = [type_[0] for type_ in unique_types]
    result = {poi_type: 0 for poi_type in poi_types}

    marker = ListaImmobiliCandidati.query.get(location_id)
    geofence = None if marker else ListaAreeCandidate.query.get(location_id)

    if marker:
        poi_counts = (
            db.session.query(POI.type, func.count(POI.id).label("count"))
            .filter(
                # ST_Transform da gradi a metri
                # ST_D tutti i poi intorno al marker nel raggio
                func.ST_DWithin(
                    func.ST_Transform(POI.location, 3857),
                    func.ST_Transform(marker.marker, 3857),
                    distance_meters,
                )
            )
            .group_by(POI.type)
            .all()
        )


    else:

        poi_counts = (
            db.session.query(POI.type, func.count(POI.id).label("count"))
            .filter(
                # se il poligono contiene poi
                func.ST_Contains(geofence.geofence, POI.location)
            )
            .group_by(POI.type)
            .all()
        )


    for poi_type, count in poi_counts:
        if poi_type in result:
            result[poi_type] = count
        else:
            return result


def calculate_rank(poi_counts, user_preferences, radius_meters=500):
    # area di Bologna in km² 
    BOLOGNA_AREA = 140.86
    
    # area del buffer in km² (vicinato)
    buffer_area = math.pi * (radius_meters/1000)**2
    
    if not poi_counts or not user_preferences:
        return 0
        
    
    # numero poi totali
    total_counts_query = """
    SELECT type, COUNT(*) as total 
    FROM points_of_interest 
    GROUP BY type;
    """
       
    with db.engine.connect() as conn:
        result = conn.execute(text(total_counts_query))
        # densita
        city_poi_density = {row.type: row.total / BOLOGNA_AREA for row in result}
        
        total_score = 0
        counted_types = 0
        
        for poi_type, count in poi_counts.items():
            preference = user_preferences.get(poi_type, 0)
            city_density = city_poi_density.get(poi_type, 0)
            
            if preference > 0 and city_density > 0:
        
                local_density = count / buffer_area
                
                # normalize
                density_score = min((local_density / city_density) * 100, 100)
                preference_percentage = (preference / 5) * 100
                type_score = (density_score * 0.7) + (preference_percentage * 0.3)
                
                total_score += type_score
                counted_types += 1
        
        if counted_types > 0:
            final_rank = total_score / counted_types
            final_rank = round(min(final_rank, 100), 2)
            return final_rank
        
        return 0
            
    


@utils_bp.route("/count_nearby_pois", methods=["POST"])
def count_nearby_pois_endpoint():
    data = request.get_json()
    location_id = data.get("location_id")
    distance_meters = data.get("distance_meters")

    poi_counts = count_nearby_pois(location_id, distance_meters)

    return jsonify(poi_counts)


@utils_bp.route("/calculate_rank", methods=["POST"])
def calculate_rank_endpoint():
    data = request.get_json()
    poi_counts = data.get("poi_counts", {})
    user_preferences = data.get("user_preferences", {})

    rank = calculate_rank(poi_counts, user_preferences)

    return jsonify({"rank": rank})


def get_questionnaire():
    
        questionnaire = QuestionnaireResponse.query.first()

        if not questionnaire:
            return None

        return {
            "aree_verdi": questionnaire.aree_verdi,
            "parcheggi": questionnaire.parcheggi,
            "fermate_bus": questionnaire.fermate_bus,
            "stazioni_ferroviarie": questionnaire.stazioni_ferroviarie,
            "scuole": questionnaire.scuole,
            "cinema": questionnaire.cinema,
            "ospedali": questionnaire.ospedali,
            "farmacia": questionnaire.farmacia,
            "colonnina_elettrica": questionnaire.colonnina_elettrica,
            "biblioteca": questionnaire.biblioteca,
            "densita_aree_verdi": questionnaire.densita_aree_verdi,
            "densita_fermate_bus": questionnaire.densita_fermate_bus,
            "densita_farmacie": questionnaire.densita_farmacie,
            "densita_scuole": questionnaire.densita_scuole,
            "densita_parcheggi": questionnaire.densita_parcheggi,
        }






@utils_bp.route("/delete-all-geofences", methods=["POST"])
def delete_all_geofences():
    try:
        ListaImmobiliCandidati.query.delete()
        ListaAreeCandidate.query.delete()
        db.session.commit()
        return (
            jsonify({"message": "Tutti i geofence e i marker sono stati cancellati"}),
            200,
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@utils_bp.route("/delete-geofence/<int:geofence_id>", methods=["DELETE"])
def delete_geofence(geofence_id):
    try:
        immobile = ListaImmobiliCandidati.query.get(geofence_id)
        if immobile:
            db.session.delete(immobile)
            db.session.commit()
            return (
                jsonify(
                    {"message": f"Immobile con ID {geofence_id} eliminato con successo"}
                ),
                200,
            )

        area = ListaAreeCandidate.query.get(geofence_id)
        if area:
            db.session.delete(area)
            db.session.commit()
            return (
                jsonify(
                    {"message": f"Area con ID {geofence_id} eliminata con successo"}
                ),
                200,
            )

        return jsonify({"error": f"Geofence con ID {geofence_id} non trovato"}), 404
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

#calcola il rank per una location
def calculate_location_rank(lat, lng, radius=None):
    if radius is None:
        radius = global_radius



    
    #crea prima un punto geometrico, poi calcola la distanza, infine aggiunge il rank degradando in base alla distanza
    sql_query = """
    
    WITH location AS (
        SELECT ST_SetSRID(ST_MakePoint(:lng, :lat), 4326) as point
    ),
    poi_distances AS (
        SELECT 
            p.type,
            ST_Distance(
                ST_Transform(location.point, 3857),
                ST_Transform(p.location, 3857)
            ) as distance
        FROM points_of_interest p, location
        WHERE ST_DWithin(
            ST_Transform(location.point, 3857),
            ST_Transform(p.location, 3857),
            :extended_radius
        )
    ),
    weighted_counts AS (
        SELECT 
            type,
            SUM(
                CASE 
                    WHEN distance <= :radius THEN 1.0
                    ELSE 1.0 - ((distance - :radius) / :radius)
                END
            ) as weighted_count
        FROM poi_distances
        GROUP BY type
    )
    SELECT type, ROUND(weighted_count::numeric, 2) as count
    FROM weighted_counts;
    """

    try:
        extended_radius = radius * 1.5

        with db.engine.connect() as conn:
            result = conn.execute(
                text(sql_query),
                {
                    "lat": lat,
                    "lng": lng,
                    "radius": radius,
                    "extended_radius": extended_radius,
                },
            )

            poi_counts = {row.type: float(row.count) for row in result}
            user_preferences = get_questionnaire()

            if not user_preferences:
                return 0

            rank = calculate_rank(poi_counts, user_preferences)
            return rank

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    
#get di tutti i geofence
@utils_bp.route('/get_all_geofences')
def get_all_geofences():
        if QuestionnaireResponse.query.count() == 0:
            return jsonify({"error": "No questionnaires found"}), 404

        all_geofences = []
        
        markers = ListaImmobiliCandidati.query.all()
        for marker in markers:
            lat = db.session.scalar(ST_Y(marker.marker))
            lng = db.session.scalar(ST_X(marker.marker))
            all_geofences.append({
                'id': marker.id,
                'type': 'marker',
                'lat': lat,
                'lng': lng,
                'rank': calculate_location_rank(lat, lng),
                'price': marker.marker_price
            })

        areas = ListaAreeCandidate.query.all()
        for area in areas:
            #  centroide per il rank
            centroid = db.session.scalar(ST_Centroid(area.geofence))
            lat = db.session.scalar(ST_Y(centroid))
            lng = db.session.scalar(ST_X(centroid))
        
            geofence_json = db.session.scalar(ST_AsGeoJSON(area.geofence))
            geofence = json.loads(geofence_json)
            
            all_geofences.append({
                'id': area.id,
                'type': 'polygon',
                'rank': calculate_location_rank(lat, lng),
                'coordinates': geofence['coordinates'][0]
            })

        return jsonify(all_geofences)



#conta i poi vicini ad un punto a partire dal raggio
@lru_cache(maxsize=1000)
def count_pois_near_point(lat, lon, radius):

        point = ST_SetSRID(ST_MakePoint(lon, lat), 4326)
        
   
        counts = (db.session.query(
                    POI.type,
                    func.count(POI.id).label('count')
                )
                .filter(
                    ST_DWithin(
                        ST_Transform(POI.location, 3857),
                        ST_Transform(point, 3857),
                        radius
                    )
                )
                .group_by(POI.type)
                .all())
        
   
        return {poi_type: count for poi_type, count in counts}
        


#seleziona delle location diverse, altrimenti le zone consigliate sono tutte nello stesso punto 
def diverse_locations_selection(locations, num_locations=10, min_distance=0.008):

    if not locations:
        return []

    diverse_locations = []
    locations.sort(key=lambda x: x["rank"], reverse=True)

    # rank piu alto
    diverse_locations.append(locations[0])

    for loc in locations[1:]:
        if len(diverse_locations) >= num_locations:
            break

        
        distances = []
        for selected in diverse_locations:
            dist = (
                (loc["lat"] - selected["lat"]) ** 2
                + (loc["lng"] - selected["lng"]) ** 2
            ) ** 0.5
            distances.append(dist)

        min_dist = min(distances)

        # se il punto è abbastanza distante e ha un rank sufficientemente diverso
        if min_dist >= min_distance:
            ranks_near = [
                s["rank"]
                for s in diverse_locations
                if ((loc["lat"] - s["lat"]) ** 2 + (loc["lng"] - s["lng"]) ** 2) ** 0.5
                < min_distance * 2
            ]

            if (
                not ranks_near
                or abs(loc["rank"] - sum(ranks_near) / len(ranks_near)) > 5
            ):
                diverse_locations.append(loc)

    return diverse_locations

#calcola posizione ottimale con una griglia di punti che ricopre l'area di bologna
@utils_bp.route("/calculate_optimal_locations")
def calculate_optimal_locations():

    start_time = time.time()

    
    user_preferences = get_questionnaire()


    if user_preferences is None:
        return (
            jsonify(
                {
                    "error": "Nessun questionario trovato. Completa il questionario prima.",
                    "execution_time_seconds": time.time() - start_time,
                }
            ),
            400,
        )

    bounds = {"min_lat": 44.4, "max_lat": 44.6, "min_lon": 11.2, "max_lon": 11.4}

    grid_points = []
    grid_size = 50
    lat_step = (bounds["max_lat"] - bounds["min_lat"]) / grid_size
    lon_step = (bounds["max_lon"] - bounds["min_lon"]) / grid_size

    for i in range(grid_size):
        for j in range(grid_size):
            lat = bounds["min_lat"] + i * lat_step
            lon = bounds["min_lon"] + j * lon_step
            grid_points.append((lat, lon))

    results = []
    #distribuzione per classificare i risultati
    rank_distribution = {"0-20": 0, "21-40": 0, "41-60": 0, "61-80": 0, "81-100": 0}

    for point in grid_points:
        lat, lon = point
        rank = calculate_location_rank(lat, lon)


        #aggiungi il rank alla distribuzione
        if rank <= 20:
            rank_distribution["0-20"] += 1
        elif rank <= 40:
            rank_distribution["21-40"] += 1
        elif rank <= 60:
            rank_distribution["41-60"] += 1
        elif rank <= 80:
            rank_distribution["61-80"] += 1
        else:
            rank_distribution["81-100"] += 1

        if rank > 30:
            results.append({"lat": lat, "lng": lon, "rank": rank})

    diverse_locations = diverse_locations_selection(results)

    execution_time = time.time() - start_time

    return jsonify(
        {
            "message": "Le 10 migliori posizioni suggerite per acquistare casa a Bologna:",
            "suggestions": diverse_locations,
            "execution_time_seconds": execution_time,
            "total_locations_analyzed": len(results),
            "rank_distribution": rank_distribution,
            "user_preferences": user_preferences,
            "search_parameters": {
                "radius_meters": global_radius,
                "min_rank_threshold": 30,
            },
        }
    )

    
#aggiunge il prezzo ad un marker
@utils_bp.route("/addMarkerPrice", methods=["POST"])
def add_marker_price():
    data = request.get_json()
    geofence_id = data.get("geofenceId")
    price = data.get("price")

    if price is None or price <= 0:
        return jsonify({"error": "Prezzo non valido"}), 400

    geofence = ListaImmobiliCandidati.query.get(geofence_id)

    if not geofence:
        return jsonify({"error": "Geofence non trovato"}), 404

    geofence.marker_price = price
    db.session.commit()

    return jsonify(
        {
            "success": True,
            "message": f"Prezzo di {price} aggiunto per il marker {geofence_id}",
        }
    )


#calcola l'indice di Moran rispetto ai prezzi e rispetto alla densità dei poi
@utils_bp.route("/calculate_morans_i", methods=["GET"])
def calculate_morans_i():
    try:
        #  immobili con prezzo
        immobili = (
            db.session.query(ListaImmobiliCandidati)
            .filter(ListaImmobiliCandidati.marker_price.isnot(None))
            .all()
        )

        if len(immobili) < 2:
            return jsonify({
                "error": "Servono almeno due immobili con prezzo per calcolare l'indice di Moran"
            }), 400

  
        coords = []
        prices = []
        threshold_distance = 1000 

        for immobile in immobili:
            point = to_shape(immobile.marker)
            coords.append([point.y, point.x]) 
            prices.append(float(immobile.marker_price))

        coords = np.array(coords)
        prices = np.array(prices)

        # densità POI
        poi_densities = []
        for immobile in immobili:
            poi_count = (
                db.session.query(func.count(POI.id))
                .filter(
                    ST_Distance(
                        ST_Transform(POI.location, 3857),
                        ST_Transform(immobile.marker, 3857)
                    ) <= threshold_distance
                )
                .scalar()
            )
            poi_densities.append(poi_count)

        poi_densities = np.array(poi_densities)

        #  matrice delle distanze usando PostGIS
        n = len(immobili)
        dist_matrix = np.zeros((n, n))
        
        for i in range(n):
            for j in range(n):
                if i != j:
                    distance = db.session.scalar(
                        func.ST_Distance(
                            func.ST_Transform(immobili[i].marker, 3857),
                            func.ST_Transform(immobili[j].marker, 3857)
                        )
                    )
                    dist_matrix[i,j] = distance

        # matrice dei pesi con decadimento esponenziale
        W = np.exp(-2 * dist_matrix / threshold_distance)
        np.fill_diagonal(W, 0)  # rimuovi self-connections
        
        # Normalizza
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
            "morans_i_prices": float(I_prices),
            "morans_i_poi_density": float(I_poi),
            "threshold_distance": threshold_distance,
            "statistics": {
                "num_immobili": len(immobili),
                "prezzo_medio": float(np.mean(prices)),
                "prezzo_std": float(np.std(prices)),
                "poi_density_mean": float(np.mean(poi_densities)),
                "poi_density_std": float(np.std(poi_densities)),
            },
            "debug_info": {
                "max_distance": float(dist_matrix.max()),
                "min_distance": float(dist_matrix[dist_matrix > 0].min()),
                "mean_distance": float(dist_matrix.mean()),
                "weight_matrix_stats": {
                    "max_weight": float(W.max()),
                    "min_weight": float(W[W > 0].min()),
                    "mean_weight": float(W.mean())
                }
            }
        })

    except Exception as e:

        return jsonify({"error": str(e)}), 500
    

@utils_bp.route("/api/filters", methods=["POST"])
def save_and_return_filters():
    try:
       
        data = request.get_json()

        
        global saved_filters
        saved_filters = {
            "distanceEnabled": data.get("distanceEnabled", False),
            "travelMode": data.get("travelMode", "driving"),
            "travelTime": data.get("travelTime", 5),
        }
        logging.info(f"Valore attuale di saved_filters: {saved_filters}")
       
        return jsonify(saved_filters), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 400  # Errore generico in caso di eccezione

#calcola i tempi di percorrenza per un batch di destinazioni
def calculate_travel_time(start_coords, destinations, transport_mode):
    base_url = "https://api.openrouteservice.org/v2/matrix/{transport_mode}"
    
    ors_modes = {
        "driving": "driving-car",
        "walking": "foot-walking",
        "cycling": "cycling-regular",
    }
    
    mode = ors_modes.get(transport_mode, "driving-car")
    headers = {
        "Authorization": "5b3ce3597851110001cf62480413fa5f131b477d986b9d8b3eb992eb",
        "Content-Type": "application/json",
    }
    
    try:
        data = {
            "locations": [[start_coords[1], start_coords[0]]] + 
                       [[lon, lat] for lat, lon in destinations],
            "sources": [0],
            "destinations": list(range(1, len(destinations) + 1))
        }
        
        response = requests.post(
            base_url.format(transport_mode=mode),
            json=data,
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            durations = result.get("durations", [[]])[0]
            
            return {
                idx: duration / 60 if duration is not None else None 
                for idx, duration in enumerate(durations)
            }
        else:
            logging.error(f"API error: {response.text}")
            return {}
            
    except Exception as e:
        return {}

#restituisce poi in base al tipo e tempo di percorso 
@utils_bp.route("/api/filter_pois/<poi_type>", methods=["GET"])
def get_pois_by_type_and_travel_time(poi_type):
    try:
        pois = (
            db.session.query(
                POI.id,
                POI.type,
                POI.additional_data,
                func.ST_Y(POI.location).label('latitude'),
                func.ST_X(POI.location).label('longitude')
            )
            .filter(POI.type == poi_type)
            .all()
        )

        results = []
        for poi in pois:
            try:
                poi_data = {
                    'id': poi.id,
                    'type': poi_type,
                    'lat': float(poi.latitude),
                    'lng': float(poi.longitude)
                }

                if poi.additional_data:
                    try:
                        poi_data['properties'] = json.loads(poi.additional_data)
                    except json.JSONDecodeError:
                        poi_data['properties'] = {}

                results.append(poi_data)

            except Exception as e:
                continue

        if saved_filters["distanceEnabled"] and results:
            coords = [(p['lat'], p['lng']) for p in results]
            center_lat, center_lon = 44.4949, 11.3426  
            
            travel_times = calculate_travel_time(
                (center_lat, center_lon),
                coords,
                saved_filters["travelMode"]
            )
            
            filtered_results = []
            for idx, result in enumerate(results):
                if idx in travel_times and travel_times[idx] is not None:
                    result['travel_time'] = travel_times[idx]
                    if travel_times[idx] <= saved_filters["travelTime"]:
                        filtered_results.append(result)
            
            results = filtered_results

        return jsonify({
            "status": "success",
            "count": len(results),
            "data": results
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500