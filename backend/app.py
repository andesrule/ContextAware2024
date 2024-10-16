from flask import Flask
from flask_cors import CORS
from flask_caching import Cache
from config import Config
import os
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from models import *

app = Flask(__name__, template_folder=Config.FRONTEND_PATH, static_folder=Config.FRONTEND_PATH, static_url_path='')
app.config.from_object(Config)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'your-very-secret-key'
app.config['CACHE_TYPE'] = 'simple'  # Aggiungi questa linea per configurare il caching

# Inizializzazione delle estensioni
CORS(app)  # Abilita CORS per tutte le route
db.init_app(app)
cache = Cache(app)

# Importa i blueprint dopo aver creato l'app per evitare importazioni circolari
from utils import utils_bp, update_pois
from routes import views

# Registra i blueprint
app.register_blueprint(utils_bp)
app.register_blueprint(views)

# Inizializza Flask-Admin
admin = Admin(app, name='Admin Panel', template_mode='bootstrap3')

# Personalizza ModelView per mostrare tutte le colonne
class CustomModelView(ModelView):
    column_display_pk = True  # Mostra sempre la chiave primaria (colonna 'id')

# Aggiungi i modelli all'interfaccia di amministrazione
admin.add_view(CustomModelView(User, db.session))

admin.add_view(CustomModelView(QuestionnaireResponse, db.session))
admin.add_view(CustomModelView(POI, db.session))
admin.add_view(CustomModelView(ListaImmobiliCandidati,db.session))
admin.add_view(CustomModelView(ListaAreeCandidate,db.session))

@app.before_request
def initialize_database():
    if not hasattr(app, 'db_initialized'):
        with app.app_context():
            db.create_all()
            if User.query.count() == 0:
                db.session.add(User(content_poi=['First string', 'Another string']))
                db.session.commit()
            update_pois()
        app.db_initialized = True

# Sostituisci @app.before_first_request con questa funzione
@app.before_request
def before_request():
    if not hasattr(app, 'initialized'):
        with app.app_context():
            initialize_database()
         
        app.initialized = True

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)