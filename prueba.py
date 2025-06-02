import fastf1
from flask import Flask, jsonify, render_template, request, redirect, url_for, send_file, make_response
from flask_sqlalchemy import SQLAlchemy
from models import db
import datetime
import hashlib
from datetime import datetime, timedelta, timezone
import pytz
from pytz import timezone
from werkzeug.utils import secure_filename
from sqlalchemy import or_
import sqlite3
import smtplib
import schedule
import time
from threading import Thread
from apscheduler.schedulers.background import BackgroundScheduler
import jwt
from io import BytesIO
import hashlib
from flask import session
from models import db, User, Prediccion
from flask import flash
from apscheduler.schedulers.background import BackgroundScheduler
import pandas as pd
from functools import wraps
from matplotlib import pyplot as plt
import numpy as np



session = fastf1.get_session(2025, 'Spanish Grand Prix', 'R')
results = session.load()

print(session.results)