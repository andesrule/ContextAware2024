from flask import Flask, jsonify, render_template, send_from_directory
from config import Config
from models import db, User
import os

# Usa il percorso assoluto per il frontend
frontend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../frontend'))

app = Flask(__name__, template_folder=frontend_path, static_folder=frontend_path, static_url_path='')
app.config.from_object(Config)

# Inizializza SQLAlchemy
db.init_app(app)

@app.before_request
def initialize_database():
    if not hasattr(app, 'db_initialized'):
        with app.app_context():
            db.create_all()
            if User.query.count() == 0:
                db.session.add_all([
                    User(content_poi=['First string', 'Another string']),
                    User(content_poi=['First string', 'Another string'])
                ])
                db.session.commit()
        app.db_initialized = True

@app.route('/')
def index():
    strings = User.query.all()
    return render_template('index.html', strings=strings)

@app.route('/api/test')
def api_test():
    return jsonify({"message": "API is working!"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
