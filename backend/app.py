from flask import Flask, jsonify, render_template, send_from_directory, request
from config import Config
from models import db, User, Geofence
import os

# Usa il percorso assoluto per il frontend
frontend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../frontend'))


app = Flask(__name__, template_folder=frontend_path, static_folder=frontend_path, static_url_path='')
app.config.from_object(Config)

# Inizializza SQLAlchemy
db.init_app(app)

@app.before_request
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
    strings = User.query.all()
    return render_template('index.html', strings=strings)

@app.route('/Home')
def get_home():
    return render_template('index.html')

@app.route('/get-geofences')
def get_geofences():
    geofences = Geofence.query.all()
    # Converti i dati in un formato JSON serializzabile
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
    print(f"Received data: {data}")
    markers = data.get('markers')
    geofences = data.get('geofences')

    if markers is not None or geofences is not None:
        # Creare un nuovo oggetto Geofence
        new_entry = Geofence(markers=markers, geofences=geofences)
        db.session.add(new_entry)
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Geofence saved successfully!'}), 200
    else:
        return jsonify({'status': 'error', 'message': 'Invalid data!'}), 400
    


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
