import datetime
from flask_sqlalchemy import SQLAlchemy
from datetime import date
from sqlalchemy.dialects.sqlite import JSON

import pytz
from pytz import timezone

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), nullable=True)
    password = db.Column(db.String(120), nullable=False)
    puntaje = db.Column(db.Integer, nullable=False, default=0)
    prediccion = db.relationship('Prediccion', back_populates='user')
    is_admin = db.Column(db.Boolean, nullable=False, default=False)
    
class Prediccion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(80), nullable=False)
    tabla = db.Column(JSON)
    gp = db.Column(db.String(80), nullable=False)
    user = db.relationship('User', back_populates='prediccion')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Data(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    last_obtained = db.Column(db.String(80))


