from flask import Flask, jsonify, send_from_directory, render_template
from flask_sqlalchemy import SQLAlchemy
import os

# Usa il percorso assoluto per il frontend
frontend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../frontend'))

app = Flask(__name__, template_folder=frontend_path, static_folder=frontend_path, static_url_path='')
app.config.from_object('config.Config')

# Inizializza SQLAlchemy
db = SQLAlchemy(app)

# Definisci un modello per le stringhe
class MyString(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(255), nullable=False)

@app.before_request
def initialize_database():
    if not hasattr(app, 'db_initialized'):
        db.create_all()
        if MyString.query.count() == 0:
            db.session.add_all([
                MyString(content='First string'),
                MyString(content='Second string'),
                MyString(content='Third string')
            ])
            db.session.commit()
        app.db_initialized = True

@app.route('/')
def index():
    strings = MyString.query.all()
    return render_template('index.html', strings=strings)

@app.route('/api/test')
def api_test():
    return jsonify({"message": "API is working!"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
