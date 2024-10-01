from flask import Flask, jsonify, render_template, request
from config import Config
from models import *
import os
import json
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView  # Importa ModelView per l'admin
import requests
from flask_cors import CORS  # Aggiunta per gestire le richieste CORS
from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import mapping, Point, Polygon
from shapely.wkt import loads
from utils import *


app = Flask(__name__, template_folder=Config.FRONTEND_PATH, static_folder=Config.FRONTEND_PATH, static_url_path='')
app.config.from_object(Config)

# Inizializza SQLAlchemy
db.init_app(app)

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'your-very-secret-key'

app.register_blueprint(utils_bp)

# Inizializza Flask-Admin
admin = Admin(app, name='Admin Panel', template_mode='bootstrap3')

# Personalizza ModelView per mostrare tutte le colonne
class CustomModelView(ModelView):
    column_display_pk = True  # Mostra sempre la chiave primaria (colonna 'id')

# Aggiungi i modelli all'interfaccia di amministrazione
admin.add_view(CustomModelView(User, db.session))
admin.add_view(CustomModelView(Geofence, db.session))
admin.add_view(CustomModelView(QuestionnaireResponse, db.session))
admin.add_view(CustomModelView(POI, db.session))



@app.before_request
def initialize_database():
    if not hasattr(app, 'db_initialized'):
        with app.app_context():
            reset_db()
            if User.query.count() == 0:
                db.session.add_all([
                    User(content_poi=['First string', 'Another string'])
                ])
                db.session.commit()
            update_pois()
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


@app.route('/get_database')
def get_database():
    return render_template('database.html')

@app.route('/Test')
def test():
    strings = User.query.all()
    return render_template('test.html', strings=strings)

@app.route('/get_pois')
def get_pois():
    pois = POI.query.all()
    poi_list = []
    for poi in pois:
        # Convert WKBElement to Shapely object
        point = to_shape(poi.location)
        # Convert Shapely object to GeoJSON
        geojson = mapping(point)
        poi_list.append({
            'type': poi.type,
            'lat': geojson['coordinates'][1],
            'lng': geojson['coordinates'][0],
            'additional_data': json.loads(poi.additional_data)
        })
    return jsonify(poi_list)

if __name__ == '__main__':
    #reset_db()
    app.run(host='0.0.0.0', port=5000, debug=True)


