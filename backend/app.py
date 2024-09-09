from flask import Flask, jsonify, render_template, request
from config import Config
from models import db, User, Geofence, QuestionnaireResponse
import os
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView  # Importa ModelView per l'admin

# Usa il percorso assoluto per il frontend
frontend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../frontend'))

app = Flask(__name__, template_folder=frontend_path, static_folder=frontend_path, static_url_path='')
app.config.from_object(Config)

# Inizializza SQLAlchemy
db.init_app(app)

# Inizializza Flask-Admin
admin = Admin(app, name='Admin Panel', template_mode='bootstrap3')

# Aggiungi i modelli all'interfaccia di amministrazione
admin.add_view(ModelView(User, db.session))
admin.add_view(ModelView(Geofence, db.session))
admin.add_view(ModelView(QuestionnaireResponse, db.session))

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
    data = request.get_json()
    markers = data.get('markers')
    geofences = data.get('geofences')

    if markers is not None or geofences is not None:
        new_entry = Geofence(markers=markers, geofences=geofences)
        db.session.add(new_entry)
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Geofence saved successfully!'}), 200
    else:
        return jsonify({'status': 'error', 'message': 'Invalid data!'}), 400

@app.route('/submit-questionnaire', methods=['POST'])
def submit_questionnaire():
    data = request.get_json()
    response = QuestionnaireResponse(
        aree_verdi=data.get('aree_verdi'),
        parcheggi=data.get('parcheggi'),
        fermate_bus=data.get('fermate_bus'),
        supermercati=data.get('supermercati'),
        scuole=data.get('scuole'),
        ristoranti=data.get('ristoranti'),
        ospedali=data.get('ospedali'),
        cinema=data.get('cinema'),
        parchi_giochi=data.get('parchi_giochi'),
        palestre=data.get('palestre')
    )
    
    db.session.add(response)
    db.session.commit()

    return jsonify({"message": "Questionario inviato con successo!"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
