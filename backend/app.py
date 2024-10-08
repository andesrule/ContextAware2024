from config import Config
from models import *
import os
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView  # Importa ModelView per l'admin
from utils import *
from routes import *
from flask import Flask 

app = Flask(__name__, template_folder=Config.FRONTEND_PATH, static_folder=Config.FRONTEND_PATH, static_url_path='')
app.config.from_object(Config)

# Inizializza SQLAlchemy
db.init_app(app)

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'your-very-secret-key'

app.register_blueprint(utils_bp)
app.register_blueprint(views)

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


#@app.before_request
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



if __name__ == '__main__':
    #reset_db()
    
    app.run(host='0.0.0.0', port=5000, debug=True)


