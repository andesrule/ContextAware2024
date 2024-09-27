from flask import Flask, jsonify, render_template, request
from config import Config
from models import db, User, Geofence, QuestionnaireResponse
import os
import json
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView  # Importa ModelView per l'admin
import requests
from flask_cors import CORS  # Aggiunta per gestire le richieste CORS
from ranking import calculate_marker_score
from geoalchemy2.elements import WKTElement

# Usa il percorso assoluto per il frontend
frontend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../frontend'))

app = Flask(__name__, template_folder=frontend_path, static_folder=frontend_path, static_url_path='')
app.config.from_object(Config)

# Inizializza SQLAlchemy
db.init_app(app)

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'your-very-secret-key'


# Inizializza Flask-Admin
admin = Admin(app, name='Admin Panel', template_mode='bootstrap3')


# Personalizza ModelView per mostrare tutte le colonne
class CustomModelView(ModelView):
    column_display_pk = True  # Mostra sempre la chiave primaria (colonna 'id')

# Aggiungi i modelli all'interfaccia di amministrazione
admin.add_view(CustomModelView(User, db.session))
admin.add_view(CustomModelView(Geofence, db.session))
admin.add_view(CustomModelView(QuestionnaireResponse, db.session))

def reset_db():
    """Drop all tables from the database."""
    with app.app_context():
        db.drop_all()
        db.create_all()
        print("Database has been reset.")

@app.before_request
def initialize_database():
    if not hasattr(app, 'db_initialized'):
        with app.app_context():
            db.create_all()
            if User.query.count() == 0:
                db.session.add_all([
                    User(content_poi=['First string', 'Another string'])
                ])
                db.session.commit()
        app.db_initialized = True

@app.route('/')
def index():
    strings = QuestionnaireResponse.query.all()
    return render_template('index.html', strings=strings)

@app.route('/Home')
def get_home():
    return render_template('index.html')

@app.route('/Questionario')
def get_quest():
    return render_template('questionario.html')

@app.route('/get-geofences')
def get_geofences():
    geofences = Geofence.query.all()
    geofences_data = [{'id': gf.id, 'markers': gf.markers, 'geofences': gf.geofences} for gf in geofences]
    return jsonify(geofences_data)

@app.route('/get_database')
def get_database():
    return render_template('database.html')

@app.route('/Test')
def test():
    strings = User.query.all()
    return render_template('test.html', strings=strings)

@app.route('/save-geofence', methods=['POST'])
def save_geofence():
    try:
        data = request.get_json()
        print(f"Received data: {data}")  # Logga i dati ricevuti

        new_entry = None  # Inizializza new_entry

        # Controllo dei dati: se ci sono marker (singolo punto)
        if 'marker' in data:
            marker = data['marker']
            lat = marker['lat']
            lng = marker['lng']
            # Crea un WKTElement per il marker (POINT)
            new_entry = Geofence(marker=WKTElement(f'POINT({lng} {lat})', srid=4326))

        # Controllo dei dati: se ci sono geofence (poligono)
        elif 'geofence' in data:
            geofence = data['geofence']
            print(f"Geofence data received: {geofence}")  # Aggiungi questo log

            # Verifica se geofence è una lista di dizionari con chiavi lat e lng
            if isinstance(geofence, list) and all(isinstance(point, dict) and 'lat' in point and 'lng' in point for point in geofence):
                # Crea il WKTElement per il geofence (POLYGON)
                polygon_points = ', '.join([f'{point["lng"]} {point["lat"]}' for point in geofence])
                new_entry = Geofence(geofence=WKTElement(f'POLYGON(({polygon_points}))', srid=4326))
            else:
                print(f"Geofence format error: {geofence}")  # Aggiungi questo log per errori di formato
                return jsonify({'status': 'error', 'message': 'Invalid geofence data format!'}), 400

        if new_entry:
            # Salva il nuovo marker o geofence nel database
            db.session.add(new_entry)
            db.session.commit()
            return jsonify({'status': 'success', 'message': 'Geofence or marker saved successfully!'}), 200
        else:
            return jsonify({'status': 'error', 'message': 'No valid data provided!'}), 400

    except Exception as e:
        print(f"Error saving geofence: {e}")  # Logga l'errore
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/submit-questionnaire', methods=['POST'])
def submit_questionnaire():
    data = request.get_json()
    response = QuestionnaireResponse(
        aree_verdi=data.get('aree_verdi'),
        parcheggi=data.get('parcheggi'),
        fermate_bus=data.get('fermate_bus'),
        luoghi_interesse=data.get('luoghi_interesse'),
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

    return jsonify({"message": "Questionario inviato con successo!"})

@app.route('/api/poi/<poi_type>', methods=['GET'])
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
        'luoghi_interesse' : 'https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/musei_gallerie_luoghi_e_teatri_storici/records?&refine=macrozona%3A%22Bologna%22 '



        
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




@app.route('/rank-marker/<int:marker_id>', methods=['GET'])
def rank_marker(marker_id):
    marker_entry = Geofence.query.get(marker_id)
    if not marker_entry:
        return jsonify({'error': 'Marker non trovato'}), 404

    questionnaire_responses = QuestionnaireResponse.query.first()  # Modifica per ottenere le risposte giuste
    
    if not questionnaire_responses:
        return jsonify({'error': 'Risposte del questionario non trovate'}), 404

    score = calculate_marker_score(marker_entry.markers[0], questionnaire_responses)

    return jsonify({'marker_id': marker_id, 'score': score})


if __name__ == '__main__':
    reset_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
    reset_db()
