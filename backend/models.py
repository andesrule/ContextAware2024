from flask_sqlalchemy import SQLAlchemy
from geoalchemy2 import Geometry
from sqlalchemy.dialects.postgresql import ARRAY 
from flask_login import UserMixin
from sqlalchemy import Index
from sqlalchemy.sql import text
from geoalchemy2.functions import ST_Transform
db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    content_poi = db.Column(ARRAY(db.String), nullable=False)


class ListaImmobiliCandidati(db.Model):
    __tablename__ = 'lista_immobili_candidati'
    id = db.Column(db.Integer, primary_key=True)
    marker = db.Column(Geometry(geometry_type='POINT', srid=4326))  # Memorizza i marker come POINT
    marker_price = db.Column(db.Float)  # Prezzo del marker

    def __init__(self, marker=None, marker_price=None):
        self.marker = marker
        self.marker_price = marker_price


class ListaAreeCandidate(db.Model):
    __tablename__ = 'lista_aree_candidate'
    id = db.Column(db.Integer, primary_key=True)
    geofence = db.Column(Geometry(geometry_type='POLYGON', srid=4326))  # Memorizza i poligoni come POLYGON

    def __init__(self, geofence=None):
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
    densita_fermate_bus = db.Column(db.Integer)

    user = db.relationship('User', backref=db.backref('questionnaire', uselist=False))

class POI(db.Model):
    __tablename__ = 'points_of_interest'

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String, index=True)  # Indice per ricerche veloci per tipo
    location = db.Column(Geometry(geometry_type='POINT', srid=4326))
    additional_data = db.Column(db.String)  # Per memorizzare dati aggiuntivi in formato JSON

    __table_args__ = (
        # Indice GiST primario per query spaziali
        Index('idx_poi_location', 'location', postgresql_using='gist'),
        # Indice composito per query che filtrano per tipo e posizione
        Index('idx_poi_type_location', 'type', 'location', postgresql_using='gist'),
        # Indice funzionale per ottimizzare le query ST_DWithin in SRID 3857
        Index('idx_poi_location_3857', text('ST_Transform(location, 3857)'), postgresql_using='gist'),
    )

def reset_db():
    """Drop all tables from the database."""
    db.drop_all()
    db.create_all()
        # Aggiungi solo l'indice funzionale per i POI dopo la creazione delle tabelle
    db.session.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_poi_location_3857 
        ON points_of_interest 
        USING gist (ST_Transform(location, 3857));
    """))
    
    db.session.commit()
    print("Database has been reset.")

