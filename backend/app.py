from flask import Flask
from flask_cors import CORS
from flask_caching import Cache
from config import Config
import os
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from models import *
from flask import render_template

app = Flask(__name__, template_folder=Config.FRONTEND_PATH, static_folder=Config.FRONTEND_PATH, static_url_path='')
app.config.from_object(Config)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'your-very-secret-key'
app.config['CACHE_TYPE'] = 'simple'

CORS(app) 
db.init_app(app)
cache = Cache(app)


from utils import utils_bp, update_pois
app.register_blueprint(utils_bp)

# FLASK ADMIN
admin = Admin(app, name='Admin Panel', template_mode='bootstrap3')

class CustomModelView(ModelView):
    column_display_pk = True  
admin.add_view(CustomModelView(QuestionnaireResponse, db.session))
admin.add_view(CustomModelView(POI, db.session))
admin.add_view(CustomModelView(ListaImmobiliCandidati,db.session))
admin.add_view(CustomModelView(ListaAreeCandidate,db.session))

@app.route('/')
def index():
    strings = QuestionnaireResponse.query.all()
    return render_template('index.html', strings=strings)


if __name__ == '__main__':  
    with app.app_context():
            reset_db()
            update_pois()

    
    app.run(host='0.0.0.0', port=5000, debug=True)