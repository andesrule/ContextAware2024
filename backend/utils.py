from flask import jsonify, request, Blueprint
from geoalchemy2.shape import from_shape, to_shape
from models import *
import json, logging
import requests
from shapely.geometry import mapping, Point, Polygon
from shapely.wkt import loads
from sqlalchemy import func, text
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
        )  # Nota: l'ordine è [lon, lat] in GeoJSON
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
                try:
                    lat, lon = get_poi_coordinates(poi)

                    if poi_type == "fermate_bus":
                        # crea una chiave unica basata sulle coordinate
                        location_key = f"{lat},{lon}"

                        # estrai le informazioni sulla linea
                        line_info = {
                            "codice_linea": poi.get("codice_linea"),
                            "denominazione": poi.get("denominazione"),
                            "ubicazione": poi.get("ubicazione"),
                        }

                        if location_key in bus_stops:
                            # Aggiorna le informazioni esistenti
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
                        # Per altri tipi di POI, procedi come prima
                        new_poi = POI(
                            type=poi_type,
                            location=f"POINT({lon} {lat})",
                            additional_data=json.dumps(poi),
                        )
                        db.session.add(new_poi)
                        total_count += 1

                except ValueError as e:
                    print(f"Errore nell'elaborazione del POI: {e}")

            if poi_type != "fermate_bus":
                db.session.commit()

            offset += limit
            print(f"Elaborati {len(results)} risultati per {poi_type}")
        else:
            print(f"Errore nella richiesta API per {poi_type}: {response.status_code}")
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
        print(f"Inserite {total_count} fermate bus uniche")

    return total_count


# ritorna i POI di un certo tipo
@utils_bp.route("/api/pois/<poi_type>", methods=["GET"])
def get_pois_by_type(poi_type):
    try:
        # prendi tutti i poi dal db
        pois = POI.query.filter_by(type=poi_type).all()
        print(f"Trovati {len(pois)} POI di tipo {poi_type}")

        poi_list = []
        for poi in pois:
            try:
                # converti la geometria in coordinate
                point = to_shape(poi.location)

                poi_data = {
                    "id": poi.id,
                    "type": poi_type,
                    "lat": point.y,  # Latitudine
                    "lng": point.x,  # Longitudine
                }

                # Aggiungi i dati addizionali se presenti
                if poi.additional_data:
                    try:
                        additional_data = json.loads(poi.additional_data)
                        poi_data["properties"] = additional_data
                    except json.JSONDecodeError:
                        print(
                            f"Errore nel parsing dei dati addizionali per POI {poi.id}"
                        )
                        poi_data["properties"] = {}

                poi_list.append(poi_data)

            except Exception as e:
                print(f"Errore nell'elaborazione del POI {poi.id}: {str(e)}")
                continue

        print(f"Restituisco {len(poi_list)} POI formattati")
        return jsonify({"status": "success", "count": len(poi_list), "data": poi_list})

    except Exception as e:
        print(f"Errore generale in get_pois_by_type: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


@utils_bp.route("/set_radius", methods=["POST"])
def set_radius():
    global global_radius
    try:
        data = request.get_json(force=True)

        radius = int(data["radius"])
        global_radius = radius  # Aggiorna il raggio globale
        return jsonify({"radius": radius}), 200

    except ValueError:
        return jsonify({"error": "Il raggio deve essere un numero intero"}), 400


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
    data = request.get_json()

    # se esite gia aggiorniamo i valori
    existing_questionnaire = QuestionnaireResponse.query.first()
    if existing_questionnaire:
        for key, value in data.items():
            setattr(existing_questionnaire, key, value)
    else:
        new_questionnaire = QuestionnaireResponse(
            aree_verdi=data.get("aree_verdi"),
            parcheggi=data.get("parcheggi"),
            fermate_bus=data.get("fermate_bus"),
            stazioni_ferroviarie=data.get("stazioni_ferroviarie"),
            scuole=data.get("scuole"),
            cinema=data.get("cinema"),
            ospedali=data.get("ospedali"),
            farmacia=data.get("farmacia"),
            colonnina_elettrica=data.get("colonnina_elettrica"),
            biblioteca=data.get("biblioteca"),
            densita_aree_verdi=data.get("densita_aree_verdi"),
            densita_fermate_bus=data.get("densita_fermate_bus"),
            densita_farmacie=data.get("densita_farmacie"),
            densita_scuole=data.get("densita_scuole"),
            densita_parcheggi=data.get("densita_parcheggi"),
        )
        db.session.add(new_questionnaire)

    try:
        db.session.commit()
        return jsonify({"message": "Questionario inviato con successo!"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


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

        print(f"Counted POIs within {distance_meters}m of marker {location_id}")

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

        print(f"Counted POIs within geofence {location_id}")

    for poi_type, count in poi_counts:
        if poi_type in result:
            result[poi_type] = count
        else:
            print(f"Warning: Unexpected POI type found: {poi_type}")

    return result


def calculate_rank(poi_counts, user_preferences, radius_meters=500):
    # area di Bologna in km² 
    BOLOGNA_AREA = 140.86
    
    # area del buffer in km² (vicinato)
    buffer_area = math.pi * (radius_meters/1000)**2
    
    if not poi_counts or not user_preferences:
        return 0
        
    try:
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
            
            print(f"Densità POI città: {city_poi_density}")
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
                print(f"Final rank: {final_rank}")
                return final_rank
            
            return 0
            
    except Exception as e:
        print(f"Error in calculate_rank: {str(e)}")
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
    try:
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
    except Exception as e:
        print(f"Errore nel recupero del questionario: {str(e)}")
        return None




@utils_bp.route("/check-questionnaires")
def check_questionnaires():
    count = QuestionnaireResponse.query.count()
    return jsonify({"count": count})


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

    print(f"Calculating rank using radius: {radius}m")

    
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
                print("Warning: No questionnaire found")
                return 0

            rank = calculate_rank(poi_counts, user_preferences)
            print(f"Calculated rank for location ({lat}, {lng}): {rank}")
            print(f"Using radius: {radius}m (extended: {extended_radius}m)")
            print(f"Weighted POI counts: {poi_counts}")
            return rank

    except Exception as e:
        print(f"Error calculating location rank: {str(e)}")
        return 0

#get di tutti i geofence
@utils_bp.route("/get_all_geofences")
def get_all_geofences():
    try:
        if QuestionnaireResponse.query.count() == 0:
            return jsonify({"error": "No questionnaires found"}), 404

        immobili = ListaImmobiliCandidati.query.all()
        aree = ListaAreeCandidate.query.all()
        all_geofences = []

        # Processa i marker
        for immobile in immobili:
            try:
                lat = db.session.scalar(ST_Y(immobile.marker))
                lng = db.session.scalar(ST_X(immobile.marker))

                rank = calculate_location_rank(lat, lng)

                all_geofences.append(
                    {
                        "id": immobile.id,
                        "type": "marker",
                        "lat": lat,
                        "lng": lng,
                        "rank": rank,
                        "price": immobile.marker_price,
                    }
                )
                print(f"Processed marker {immobile.id} with rank {rank}")

            except Exception as e:
                print(f"Error processing marker {immobile.id}: {str(e)}")
                continue

        # Processa le aree
        for area in aree:
            try:
                centroid = db.session.scalar(ST_Centroid(area.geofence))
                lat = db.session.scalar(func.ST_Y(centroid))
                lng = db.session.scalar(func.ST_X(centroid))

                rank = calculate_location_rank(lat, lng)

                geofence_geojson = db.session.scalar(ST_AsGeoJSON(area.geofence))
                geofence_dict = json.loads(geofence_geojson)

                all_geofences.append(
                    {
                        "id": area.id,
                        "type": "polygon",
                        "rank": rank,
                        "coordinates": geofence_dict["coordinates"][0],
                    }
                )

            except Exception as e:
                print(f"Error processing area {area.id}: {str(e)}")
                continue

        return jsonify(all_geofences)

    except Exception as e:
        print(f"Error in get_all_geofences: {str(e)}")
        return jsonify({"error": str(e)}), 500


def get_bologna_bounds():
    return {"min_lat": 44.4, "max_lat": 44.6, "min_lon": 11.2, "max_lon": 11.4}



@lru_cache(maxsize=1000)
def count_pois_near_point(lat, lon, radius):
    """
    Conta i POI vicino a un punto usando la stessa logica di count_nearby_pois.
    """
    query = text(
        """
    SELECT type, COUNT(*) as count
    FROM points_of_interest
    WHERE ST_DWithin(
        ST_Transform(location, 3857),
        ST_Transform(ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), 3857),
        :radius
    )
    GROUP BY type
    """
    )

    try:
        with db.engine.connect() as connection:
            result = connection.execute(
                query, {"lat": lat, "lon": lon, "radius": radius}
            )
            counts = {row.type: row.count for row in result}
            return counts
    except SQLAlchemyError as e:
        print(f"Errore nell'esecuzione della query: {str(e)}")
        return {}


def diverse_locations_selection(locations, num_locations=10, min_distance=0.008):
    """
    Seleziona le locations più diverse tra loro basandosi sia sulla distanza che sul rank
    """
    if not locations:
        return []

    diverse_locations = []
    locations.sort(key=lambda x: x["rank"], reverse=True)

    # Seleziona sempre il punto con il rank più alto
    diverse_locations.append(locations[0])

    for loc in locations[1:]:
        if len(diverse_locations) >= num_locations:
            break

        # Calcola la distanza minima da tutti i punti già selezionati
        distances = []
        for selected in diverse_locations:
            dist = (
                (loc["lat"] - selected["lat"]) ** 2
                + (loc["lng"] - selected["lng"]) ** 2
            ) ** 0.5
            distances.append(dist)

        min_dist = min(distances)

        # Se il punto è abbastanza distante e ha un rank sufficientemente diverso
        if min_dist >= min_distance:
            # Verifica che il rank sia sufficientemente diverso dai punti vicini
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


@utils_bp.route("/calculate_optimal_locations")
def calculate_optimal_locations():
    print("Inizio calculate_optimal_locations")
    start_time = time.time()

    try:
        user_preferences = get_questionnaire()
        print("User preferences trovate:", user_preferences)

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
        lat_step = (bounds["max_lat"] - bounds["min_lat"]) / 30
        lon_step = (bounds["max_lon"] - bounds["min_lon"]) / 30

        for i in range(30):
            for j in range(30):
                lat = bounds["min_lat"] + i * lat_step
                lon = bounds["min_lon"] + j * lon_step
                grid_points.append((lat, lon))

        results = []
        rank_distribution = {"0-20": 0, "21-40": 0, "41-60": 0, "61-80": 0, "81-100": 0}

        for point in grid_points:
            lat, lon = point
            rank = calculate_location_rank(lat, lon)

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

    except Exception as e:
        print(f"Errore in calculate_optimal_locations: {str(e)}")
        return (
            jsonify(
                {"error": str(e), "execution_time_seconds": time.time() - start_time}
            ),
            500,
        )


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



@utils_bp.route("/calculate_morans_i", methods=["GET"])
def calculate_morans_i():
    try:
        # Recupera immobili con prezzo
        immobili = (
            db.session.query(ListaImmobiliCandidati)
            .filter(ListaImmobiliCandidati.marker_price.isnot(None))
            .all()
        )

        if len(immobili) < 2:
            return (
                jsonify(
                    {
                        "error": "Servono almeno due immobili con prezzo per calcolare l'indice di Moran"
                    }
                ),
                400,
            )

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
            poi_count = (
                db.session.query(func.count(POI.id))
                .filter(
                    ST_Distance(
                        ST_Transform(POI.location, 3857),
                        ST_Transform(immobile.marker, 3857),
                    )
                    <= threshold_distance
                )
                .scalar()
            )
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

        return jsonify(
            {
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
            }
        )

    except Exception as e:
        print(f"Errore nel calcolo dell'indice di Moran: {str(e)}")
        return jsonify({"error": str(e)}), 500


@utils_bp.route("/api/filters", methods=["POST"])
def save_and_return_filters():
    try:
        # Raccoglie i dati JSON dalla richiesta
        data = request.get_json()

        # Salva i dati nell'oggetto globale `saved_filters`
        global saved_filters
        saved_filters = {
            "distanceEnabled": data.get("distanceEnabled", False),
            "travelMode": data.get("travelMode", "driving"),
            "travelTime": data.get("travelTime", 5),
        }
        logging.info(f"Valore attuale di saved_filters: {saved_filters}")
        # Restituisce i dati in formato JSON
        return jsonify(saved_filters), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 400  # Errore generico in caso di eccezione


def calculate_travel_time_batch(
    start_coords, destinations, transport_mode, batch_size=10
):
    """
    Calcola tempi di percorrenza usando OpenRouteService
    """
    # API endpoint
    base_url = "https://api.openrouteservice.org/v2/matrix/{transport_mode}"

    # Converti modalità di trasporto
    ors_modes = {
        "driving": "driving-car",
        "walking": "foot-walking",
        "cycling": "cycling-regular",
    }

    mode = ors_modes.get(transport_mode, "driving-car")

    # Chiave API gratuita (richiede registrazione su openrouteservice.org)
    headers = {
        "Authorization": "5b3ce3597851110001cf62480413fa5f131b477d986b9d8b3eb992eb",
        "Content-Type": "application/json",
    }

    all_travel_times = {}

    for i in range(0, len(destinations), batch_size):
        batch = destinations[i : i + batch_size]

        try:
            # Prepara i dati per la richiesta
            data = {
                "locations": [[start_coords[1], start_coords[0]]]
                + [[lon, lat] for lat, lon in batch],
                "sources": [0],
                "destinations": list(range(1, len(batch) + 1)),
            }

            response = requests.post(
                base_url.format(transport_mode=mode),
                json=data,
                headers=headers,
                timeout=30,
            )

            if response.status_code == 200:
                matrix = response.json()
                durations = matrix.get("durations", [[]])[0]

                for idx, duration in enumerate(durations):
                    all_travel_times[i + idx] = (
                        duration / 60 if duration else float("inf")
                    )
            else:
                logging.error(f"API error: {response.text}")
                for idx in range(len(batch)):
                    all_travel_times[i + idx] = float("inf")

        except Exception as e:
            logging.error(f"Batch {i} error: {str(e)}")
            for idx in range(len(batch)):
                all_travel_times[i + idx] = float("inf")
            time.sleep(1)

        time.sleep(0.1)  # Rate limiting

    return all_travel_times


@utils_bp.route("/api/filter_pois/<poi_type>", methods=["GET"])
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
            "walking": 83,  # ~5km/h -> 83m/min
            "cycling": 250,  # ~15km/h -> 250m/min
            "driving": 500,  # ~30km/h in città -> 500m/min
        }

        # Calcola il raggio del buffer basato sul tempo e modalità
        max_radius = (
            estimated_speed[saved_filters["travelMode"]] * saved_filters["travelTime"]
        )

        # Query ottimizzata che sfrutta entrambi gli indici
        query = text(
            """
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
        """
        )

        # Esegui la query con i parametri
        result = db.session.execute(
            query,
            {
                "lon": start_coords[1],
                "lat": start_coords[0],
                "poi_type": poi_type,
                "max_radius": max_radius,
            },
        )

        # Prepara i dati pre-filtrati
        pois_data = []
        poi_coords = []

        for row in result:
            poi_data = {
                "id": row.id,
                "type": poi_type,
                "lat": float(row.latitude),
                "lng": float(row.longitude),
                "distance": float(row.distance_meters),
            }

            if row.additional_data:
                try:
                    additional_data = json.loads(row.additional_data)
                    poi_data["properties"] = additional_data
                except json.JSONDecodeError:
                    logging.error(
                        f"Errore nel parsing dei dati addizionali per POI {row.id}"
                    )
                    poi_data["properties"] = {}

            pois_data.append(poi_data)
            poi_coords.append((float(row.latitude), float(row.longitude)))

        logging.info(
            f"Pre-filtrati {len(pois_data)} POI usando indici spaziali compositi"
        )

        if not pois_data:
            return jsonify({"status": "success", "count": 0, "data": []})

        # Calcola i tempi di viaggio effettivi in batch
        travel_times = calculate_travel_time_batch(
            start_coords, poi_coords, saved_filters["travelMode"], batch_size=10
        )

        # Filtra e ordina i POI per tempo di viaggio
        filtered_pois = []
        for i, time in travel_times.items():
            if time <= saved_filters["travelTime"]:
                poi = pois_data[i]
                poi["travel_time"] = time
                filtered_pois.append(poi)

        # Ordina per tempo di viaggio
        filtered_pois.sort(key=lambda x: x["travel_time"])

        logging.info(
            f"Restituisco {len(filtered_pois)} POI filtrati per tempo di viaggio effettivo"
        )

        return jsonify(
            {
                "status": "success",
                "count": len(filtered_pois),
                "data": filtered_pois,
                "query_info": {
                    "estimated_radius": max_radius,
                    "prefiltered_count": len(pois_data),
                    "final_count": len(filtered_pois),
                },
            }
        )

    except Exception as e:
        logging.error(f"Errore generale in get_pois_by_type_and_travel_time: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500
