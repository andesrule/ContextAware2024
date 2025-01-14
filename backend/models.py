from flask_sqlalchemy import SQLAlchemy
from geoalchemy2 import Geometry
from sqlalchemy import Index
from sqlalchemy.sql import text
import json
import os
db = SQLAlchemy()


class ListaImmobiliCandidati(db.Model):
    __tablename__ = 'lista_immobili_candidati'
    id = db.Column(db.Integer, primary_key=True)
    marker = db.Column(Geometry(geometry_type='POINT', srid=4326))  
    marker_price = db.Column(db.Float)  

    def __init__(self, marker=None, marker_price=None):
        self.marker = marker
        self.marker_price = marker_price


class ListaAreeCandidate(db.Model):
    __tablename__ = 'lista_aree_candidate'
    id = db.Column(db.Integer, primary_key=True)
    geofence = db.Column(Geometry(geometry_type='POLYGON', srid=4326))  

    def __init__(self, geofence=None):
        self.geofence = geofence

class QuestionnaireResponse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    aree_verdi = db.Column(db.Integer)
    parcheggi = db.Column(db.Integer)
    fermate_bus = db.Column(db.Integer)
    stazioni_ferroviarie = db.Column(db.Integer)
    scuole = db.Column(db.Integer)
    cinema = db.Column(db.Integer)
    ospedali = db.Column(db.Integer)
    farmacia = db.Column(db.Integer)
    colonnina_elettrica = db.Column(db.Integer)
    biblioteca = db.Column(db.Integer)
    densita_aree_verdi = db.Column(db.Integer)
    densita_fermate_bus = db.Column(db.Integer)
    densita_farmacie = db.Column(db.Integer)
    densita_scuole=db.Column(db.Integer)
    densita_parcheggi=db.Column(db.Integer)

class POI(db.Model):
    __tablename__ = 'points_of_interest'

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String)
    location = db.Column(Geometry(geometry_type='POINT', srid=4326))
    additional_data = db.Column(db.String) 
    

    __table_args__ = (

        Index('idx_poi_location', 'location', postgresql_using='gist'),
        Index('idx_poi_type', 'type'),
    )

def reset_db():
    db.drop_all()
    db.create_all()
    db.session.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_poi_location_3857 
        ON points_of_interest 
        USING gist (ST_Transform(location, 3857));
    """))
    
    db.session.commit()

def load_local_pois():

    data_path = os.path.join(os.path.dirname(__file__), 'data', 'db.json')
    try:
        with open(data_path, 'r') as f:
            pois = json.load(f)
            
        for poi in pois:
            new_poi = POI(
                type=poi['type'],
                location=f"POINT({poi['lon']} {poi['lat']})",
                additional_data=json.dumps(poi['additional_data'])
            )
            db.session.add(new_poi)
        
        db.session.commit()
    except Exception as e:
        print(f"Error loading local POIs: {e}")