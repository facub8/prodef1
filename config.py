import os

class Config:
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.urandom(24)
    SQLALCHEMY_DATABASE_URI = 'sqlite:///data.db'
    CLAVE_SEGURIDAD = "cefb685afd1217e6ac855ba8fa9a7f454b1a16b2c060dcf1b8f13e9a1e80cd29" #3937303345

    SCHEDULER_TIMEZONE = "America/Argentina/Buenos_Aires"
