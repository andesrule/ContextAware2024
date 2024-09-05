from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import ARRAY 
from sqlalchemy.dialects.postgresql import JSON

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    content_poi = db.Column(ARRAY(db.String), nullable=False)
    
class Geofence(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    markers = db.Column(JSON)  # Memorizza i marker come JSON
    geofences = db.Column(JSON)  # Memorizza i poligoni come JSON

    def __init__(self, markers=None, geofences=None):
        self.markers = markers or []
        self.geofences = geofences or []