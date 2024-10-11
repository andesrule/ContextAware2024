from flask_sqlalchemy import SQLAlchemy
from geoalchemy2 import Geometry
from sqlalchemy.dialects.postgresql import ARRAY 
from flask_login import UserMixin


db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    content_poi = db.Column(ARRAY(db.String), nullable=False)
    
class Geofence(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    marker = db.Column(Geometry(geometry_type='POINT', srid=4326))  # Memorizza i marker come POINT
    geofence = db.Column(Geometry(geometry_type='POLYGON', srid=4326))  # Memorizza i poligoni come POLYGON

    def __init__(self, marker=None, geofence=None):
/*************  ✨ Codeium Command ⭐  *************/
        """
        Inizializza un nuovo oggetto Geofence con i parametri marker e geofence.

        :param marker: Coordinate del marker come oggetto Geometry(Point)
        :param geofence: Coordinate del poligono come oggetto Geometry(Polygon)
        """
/******  ae1eaf1b-e8dd-4770-9224-731528060578  *******/
        self.marker = marker
        self.geofence = geofence

class QuestionnaireResponse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True)
    aree_verdi = db.Column(db.Integer)
    parcheggi = db.Column(db.Integer)
    fermate_bus = db.Column(db.Integer)
    stazioni_ferroviarie = db.Column(db.Integer)
    scuole = db.Column(db.Integer)
    cinema = db.Column(db.Integer)
    ospedali = db.Column(db.Integer)
    farmacia = db.Column(db.Integer)
    luogo_culto = db.Column(db.Integer)
    servizi = db.Column(db.Integer)
    densita_aree_verdi = db.Column(db.Integer)
    densita_cinema = db.Column(db.Integer)
    densita_fermate_bus = db.Column(db.Integer)

    user = db.relationship('User', backref=db.backref('questionnaire', uselist=False))


class POI(db.Model):
    __tablename__ = 'points_of_interest'

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String)
    location = db.Column(Geometry(geometry_type='POINT', srid=4326))
    additional_data = db.Column(db.String)  # Per memorizzare dati aggiuntivi in formato JSON


def reset_db():
    """Drop all tables from the database."""
    db.drop_all()
    db.create_all()
    print("Database has been reset.")

