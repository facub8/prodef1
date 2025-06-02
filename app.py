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
from models import db, User, Prediccion, Data
from flask import flash
from apscheduler.schedulers.background import BackgroundScheduler
import pandas as pd
from functools import wraps
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from flask_apscheduler import APScheduler
import os

app = Flask(__name__)
app.config.from_object('config.Config')
app.config['SECRET_KEY'] = 'facub13'
app.config['SESSION_PERMANENT'] = False  # Esto evita que la sesión sea persistente
app.config['SESSION_TYPE'] = 'filesystem'
db.init_app(app)

with app.app_context():
    db.create_all()

puntos_f1 = {
    1: 25,
    2: 18,
    3: 15,
    4: 12,
    5: 10,
    6: 8,
    7: 6,
    8: 4,
    9: 2,
    10: 1
}

puntos_sprint = {
    1: 8,
    2: 7,
    3: 6,
    4: 5,
    5: 4,
    6: 3,
    7: 2,
    8: 1
}

pilotos_actuales = [
    "VER", "TSU", "HAM", "LEC", "RUS", "ANT", "NOR", "PIA", "ALO", "STR",
    "GAS", "COL", "OCO", "BEA", "LAW", "HAD", "SAI", "ALB", "HUL", "BOR"
]



remitente = "f1prode2025@gmail.com"
contraseña = "mmms wqsx tgvz klzs"
asunto = "Prode F1"

cache_path = os.path.join(os.path.dirname(__file__), 'f1cache')

# Crear el directorio si no existe
os.makedirs(cache_path, exist_ok=True)

# Habilitar la caché de FastF1
fastf1.Cache.enable_cache(cache_path)



comparado = False


sheet_id = "1RWVUHx--yBpncxtjvMy_hRmU_clgmnC1YZTxyuqvgTc"
gid = "0"  # Cambiar si es otra pestaña

url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
df = pd.read_csv(url)




with app.app_context():
    if (Data.query.first() is None):
        d = Data(last_obtained="")
        db.session.add(d)
        db.session.commit()

def enviar_correo(nombre, email, cuerpo):

    mensaje = MIMEMultipart()
    mensaje["From"] = remitente
    mensaje["To"] = email
    mensaje["Subject"] = asunto
    mensaje.attach(MIMEText(cuerpo, "plain"))
    try:
        servidor = smtplib.SMTP("smtp.gmail.com", 587)
        servidor.starttls()
        servidor.login(remitente, contraseña)
        servidor.sendmail(remitente, email, mensaje.as_string())
        servidor.quit()
        print("Correo enviado exitosamente.")
    except Exception as e:
        print("Error al enviar el correo:", e)


def obtener_ultimo_gp():
    calendario = fastf1.get_event_schedule(datetime.now().year)
    fecha_actual = datetime.now(pytz.UTC)
    
    ultimo_gp = None

    for evento in calendario.itertuples():
        fecha_evento = evento.EventDate if evento.EventDate.tzinfo else pytz.UTC.localize(evento.EventDate)
        if fecha_evento < fecha_actual:
            ultimo_gp = evento
            _ = Prediccion.query.filter_by(gp=ultimo_gp.EventName).first()
    return ultimo_gp



def obtener_resultados():
    # Obtener el calendario de la temporada actual
    
    d = Data.query.first()
    # Encontrar el último GP completado
    ultimo_gp = obtener_ultimo_gp()
    
    
    if ultimo_gp:

        d.last_obtained = ultimo_gp.EventName
        db.session.commit()

        # Cargar la sesión de carrera
        sessionR = fastf1.get_session(datetime.now().year, ultimo_gp.EventName, 'R')
        sessionR.load()
        
        retired_drivers = sessionR.results[sessionR.results['Status'] == 'Retired']
        retired_abbr = retired_drivers['Abbreviation']
        dnf = retired_abbr.tolist()

        resultsR = sessionR.results
        fastest_lap = sessionR.laps.pick_fastest()

        fastest_pit_stop = ""
        matching_rows = df[df.iloc[:, 1] == ultimo_gp.EventName]
        if not matching_rows.empty:
            # Obtener el valor de la columna 3 (índice 2) de la primera fila que coincide
            value = matching_rows.iloc[0, 2]
            fastest_pit_stop = value



        fastest_lap_driver = fastest_lap['Driver']
        resultados_carrera = []
        for _, driver in resultsR.iterrows():
            resultados_carrera.append({
                'posicion': driver['Position'],
                'abreviacion': driver['Abbreviation']  # o 'Driver' si usas otro campo
            })
        

        sessionQ = fastf1.get_session(datetime.now().year, ultimo_gp.EventName, 'Q')
        sessionQ.load()

        resultsQ = sessionQ.results

        resultados_qualy = []
        for _, driver in resultsQ.iterrows():
            resultados_qualy.append({
                'posicion': driver['Position'],
                'abreviacion': driver['Abbreviation']  # o 'Driver' si usas otro campo
            })
        
        resultados_sprint = []
        resultados_qualyS= []
        es_fin_de_semana_sprint = hasattr(ultimo_gp, 'Sprint') and ultimo_gp.Sprint
        if es_fin_de_semana_sprint:
            sessionS = fastf1.get_session(datetime.now().year, ultimo_gp.EventName, 'S')
            sessionS.load()
            resultsS = sessionS.results

            for _, driver in resultsS.iterrows():
                resultados_sprint.append({
                    'posicion': driver['Position'],
                    'abreviacion': driver['Abbreviation']  # o 'Driver' si usas otro campo
                })

            sessionSS = fastf1.get_session(datetime.now().year, ultimo_gp.EventName, 'SS')
            sessionSS.load()
            resultsSS = sessionSS.results

            for _, driver in resultsSS.iterrows():
                resultados_qualy.append({
                    'posicion': driver['Position'],
                    'abreviacion': driver['Abbreviation']  # o 'Driver' si usas otro campo
                })

        return resultados_carrera, resultados_qualy, resultados_sprint, resultados_qualyS, fastest_lap_driver, fastest_pit_stop, dnf, ultimo_gp.EventName
    else:
        print("No se encontró un último GP completado.")
        return None, None, None, None, None, None, None, None

    return None

@app.route('/comparar_predicciones/312903084756', methods=['POST'])
def comparar_predicciones():
    print("Comprobando Predicciones")
    resultados_carrera, resultados_qualy, resultados_sprint, resultados_qualyS, fastest_lap_driver, fastest_pit_stop, dnf, u_gp = obtener_resultados()
    users = User.query.all()

    if resultados_carrera is None:
        flash("⚠️ No hay resultados disponibles para comparar aún.")
        return redirect(url_for('admin'))

    pilotos_carrera = [p['abreviacion'] for p in resultados_carrera]

    mapa_qualy = {piloto['abreviacion']: piloto['posicion'] for piloto in resultados_qualy}
    mapa_carrera = {piloto['abreviacion']: piloto['posicion'] for piloto in resultados_carrera}
    carrera_por_posicion = {piloto['posicion']: piloto['abreviacion'] for piloto in resultados_carrera}
    print(carrera_por_posicion)

    if resultados_qualyS != []:
        mapa_qualys = {p['abreviacion']: p['posicion'] for p in resultados_qualyS}
        mapa_sprint = {p['abreviacion']: p['posicion'] for p in resultados_sprint}
        es_sprint = True
    else:
        es_sprint = False

    for user in users:
        predicciones = Prediccion.query.filter_by(user_id=user.id).all()

        # Diccionario para acumular puntos por tipo
        puntos_por_tipo = {
            'qualy': 0,
            'carrera': 0,
            'qualys': 0,
            'carreras': 0,
            'fastest-lap': 0,
            'fastest-pit-stop': 0,
            'dnf': 0
        }

        for prediccion in predicciones:
            if prediccion.gp == u_gp:
                if prediccion.tipo == 'qualy':
                    for item in prediccion.tabla:
                        piloto = item['nombre']
                        pos_predicha = item['posicion']

                        if piloto in mapa_qualy:
                            pos_real = mapa_qualy[piloto]
                            diferencia = abs(pos_predicha - pos_real)

                            if diferencia == 0:
                                puntos_por_tipo['qualy'] += 8
                            elif diferencia == 1:
                                puntos_por_tipo['qualy'] += 5
                            elif diferencia == 2:
                                puntos_por_tipo['qualy'] += 4
                            elif diferencia == 3:
                                puntos_por_tipo['qualy'] += 3
                            elif diferencia == 4:
                                puntos_por_tipo['qualy'] += 2
                            elif diferencia == 5:
                                puntos_por_tipo['qualy'] += 1

                elif prediccion.tipo == 'carrera':
                    for item in prediccion.tabla:
                        piloto = item['nombre']
                        pos_predicha = item['posicion']
                        if pos_predicha <= 10:
                            pos_real = mapa_carrera.get(piloto)
                            if pos_real == pos_predicha:
                                puntos_por_tipo['carrera'] += puntos_f1[pos_real]

                if resultados_qualyS != [] and es_sprint:
                    if prediccion.tipo == 'qualys':
                        for item in prediccion.tabla:
                            piloto = item['nombre']
                            pos_predicha = item['posicion']
                            pos_real = mapa_qualys.get(piloto)
                            if pos_real is not None and pos_predicha <= 8 and pos_real <= 8:
                                diferencia = abs(pos_real - pos_predicha)
                                if diferencia == 0:
                                    puntos_por_tipo['qualys'] += 8
                                elif diferencia == 1:
                                    puntos_por_tipo['qualys'] += 5
                                elif diferencia == 2:
                                    puntos_por_tipo['qualys'] += 4
                                elif diferencia == 3:
                                    puntos_por_tipo['qualys'] += 3
                                elif diferencia == 4:
                                    puntos_por_tipo['qualys'] += 2
                                elif diferencia == 5:
                                    puntos_por_tipo['qualys'] += 1

                    if prediccion.tipo == 'carreras':
                        for item in prediccion.tabla:
                            piloto = item['nombre']
                            pos_predicha = item['posicion']
                            pos_real = mapa_sprint.get(piloto)
                            if pos_real == pos_predicha and pos_real in puntos_sprint:
                                puntos_por_tipo['carreras'] += puntos_sprint[pos_real]

                if prediccion.tipo == 'fastest-lap':
                    for item in prediccion.tabla:
                        if item['nombre'] == fastest_lap_driver:
                            puntos_por_tipo['fastest-lap'] += 1
                            break

                if prediccion.tipo == 'fastest-pit-stop':
                    for item in prediccion.tabla:
                        if item['nombre'] == fastest_pit_stop:
                            puntos_por_tipo['fastest-pit-stop'] += 1
                            break

                if prediccion.tipo == 'dnf':
                    
                    for item in prediccion.tabla:
                        if item['nombre'] in dnf or (item['nombre'] not in pilotos_carrera and item['nombre'] in pilotos_actuales):
                            puntos_por_tipo['dnf'] += 1

        # Sumar todos los puntos
        puntos_total = sum(puntos_por_tipo.values())
        user.puntaje += puntos_total
        db.session.commit()

        # Imprimir por tipo y total
        for tipo, pts in puntos_por_tipo.items():
            if pts > 0:
                print(f"Usuario {user.username} sumó {pts} puntos en {tipo}")
        print(f"Total puntos para {user.username}: {puntos_total}")

        cuerpo = (
            f"Hola {user.username},\n"
            f"Has obtenido {str(puntos_total)} puntos en el prode F1:\n\n"
            f"Qualy Sprint: {str(puntos_por_tipo['qualys'])}\n"
            f"Sprint: {str(puntos_por_tipo['carreras'])}\n\n"
            f"Qualy: {str(puntos_por_tipo['qualy'])}\n"
            f"Carrera: {str(puntos_por_tipo['carrera'])}\n\n"
            f"Vuelta Rápida: {str(puntos_por_tipo['fastest-lap'])}\n"
            f"Pit Stop Rápido: {str(puntos_por_tipo['fastest-pit-stop'])}\n"
            f"DNF: {str(puntos_por_tipo['dnf'])}"
        )


        if user.email:
            enviar_correo(user.username, user.email, cuerpo)

    flash("✅ Predicciones comprobadas correctamente.")
    return redirect(url_for('admin'))




    # Configurar el servidor SMTP



def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        
        user = User.query.get(session['user_id'])
        if not user or not user.is_admin:
            
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'user_id' in session:
            return f(*args, **kwargs)
        else:
            return redirect(url_for('login'))
    return wrap

def obtener_proximo_gp():
    # Cargar el calendario de la temporada actual
    calendario = fastf1.get_event_schedule(datetime.now().year)
    
    # Encontrar el próximo evento
    fecha_actual = datetime.now(pytz.UTC)
    proximo_gp = None
    
    for evento in calendario.itertuples():
        # Asegurarnos que la fecha del evento tenga zona horaria
        if not evento.EventDate.tzinfo:
            fecha_evento = pytz.UTC.localize(evento.EventDate)
        else:
            fecha_evento = evento.EventDate
            
        if fecha_evento > fecha_actual:
            proximo_gp = evento
            break
    
    if proximo_gp:
        # Obtener la estructura del fin de semana
        estructura = {
            'GP': proximo_gp.EventName,
            'Fecha': proximo_gp.EventDate.isoformat(),  # Enviamos en formato ISO para mejor manejo en JS
            'Eventos': []
        }
        
        # Verificar el formato del fin de semana (Sprint o Normal)
        es_fin_de_semana_sprint = hasattr(proximo_gp, 'Sprint') and proximo_gp.Sprint
        
        if es_fin_de_semana_sprint:
            # Fin de semana con Sprint
            estructura['Eventos'] = [
                {'Sprint Shootout': proximo_gp.Session3Date.isoformat()}, 
                {'Sprint': proximo_gp.Session4Date.isoformat()},
                {'Qualifying': proximo_gp.Session2Date.isoformat()},  # Clasificación para la carrera principal
                {'Race': proximo_gp.Session5Date.isoformat()}
            ]
            estructura['TipoFinde'] = 'sprint'
        else:
            # Fin de semana normal
            estructura['Eventos'] = [
                {'Qualifying': proximo_gp.Session4Date.isoformat()},
                {'Race': proximo_gp.Session5Date.isoformat()}
            ]
            estructura['TipoFinde'] = 'normal'
        
        return estructura
    return None


@app.route('/register', methods=['POST', 'GET'])
def crear_usuario_ruta():
    if request.method == 'POST':
        access_key = request.form['access_key']
        if access_key != 'facub13':
            flash("Acceso denegado")
            return redirect(url_for('crear_usuario_ruta'))
        username = request.form['username']
        email = request.form.get('email')  # Opcional
        password = request.form['password']
        is_admin = request.form.get('is_admin') == 'on'  # Opcional
        
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        existe_user = User.query.filter_by(username=username).first()
        if existe_user:
            flash("Usuario ya existe")
            return redirect(url_for('crear_usuario_ruta'))
        nuevo_usuario = User(username=username, email=email, password=hashed_password, is_admin=is_admin)
        
        db.session.add(nuevo_usuario)
        db.session.commit()

        flash("Usuario creado exitosamente")

        return redirect(url_for('login'))   
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        user = User.query.filter_by(username=username).first()

        if user and user.password == hashed_password:
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('home'))
        else:
            flash('Usuario o contraseña incorrectos.')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route("/prode")
@login_required
def index():
    proximo_gp = obtener_proximo_gp()
    tipo_finde = proximo_gp['TipoFinde']  # Fixed: use proximo_gp instead of calling the function again
    tiene_sprint = tipo_finde == 'sprint'
    return render_template("prueba.html", gp_info=proximo_gp, tiene_sprint=tiene_sprint, username=session['username'])

@app.route('/guardar_orden', methods=['POST'])
@login_required
def guardar_orden():
    user_id = session.get('user_id')
    if user_id is None:
        return jsonify({'status': 'error', 'message': 'Usuario no autenticado'}), 401
    data = request.get_json()

    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'Usuario no encontrado'}), 404
    
    gp_actual = obtener_proximo_gp()
    if gp_actual:
        nombre_gp = gp_actual['GP']
    else:
        nombre_gp = "Desconocido"
    
    # Crear diccionarios para cada tipo de predicción
    predicciones = {
        'qualy': [],
        'carrera': [],
        'qualys': [],
        'carreras': [],
        'fastest-lap': [],
        'fastest-pit-stop': [],
        'dnf': []  # Agregar esta línea
    }

    # Clasificar las predicciones según su tipo
    for item in data:
        tipo = item['tipo']
        if tipo in predicciones:
            predicciones[tipo].append(item)
        else:
            print(f"Tipo desconocido: {tipo}")

    # Ejemplo de procesamiento: imprimir por tipo
    print("\nPredicciones recibidas:")
    for tipo, items in predicciones.items():
        print(f"\nTipo: {tipo}")
        for item in items:
            print(f"  {item['posicion']}: {item['nombre']}")

    # Aquí podrías guardar cada lista por separado en la base de datos si quieres
    for tipo, items in predicciones.items():
        if items:
            # Limpiar el campo 'tipo' de cada item para no duplicar
            items_limpios = [{k: v for k, v in item.items() if k != 'tipo'} for item in items]

            # Buscar si ya existe una predicción de ese tipo para ese usuario y GP
            pred = Prediccion.query.filter_by(user_id=user_id, tipo=tipo, gp=nombre_gp).first()
            
            # Si existe una predicción para el mismo GP, actualizarla
            if pred and pred.gp == nombre_gp:
                pred.tabla = items_limpios
            # Si no existe o es para un GP diferente, crear una nueva
            else:
                pred = Prediccion(user_id=user_id, tipo=tipo, tabla=items_limpios, gp=nombre_gp)
                db.session.add(pred)



    db.session.commit()


    return jsonify({'status': 'ok'})

@app.route('/tabla')
def tabla():
    users = User.query.order_by(User.puntaje.desc()).all()
    return render_template('tabla.html', users=users)


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    return redirect(url_for('index'))

@app.route('/')
@login_required
def home():
    user = User.query.get_or_404(session['user_id'])
    
    return render_template('home.html', username=session['username'], is_admin=user.is_admin)

@app.route('/actualizar_comparado', methods=['POST'])
def actualizar_comparado():
    global comparado
    comparado = False
    return jsonify({'status': 'ok'})

@app.route('/admin')
@admin_required
@login_required
def admin():
    users = User.query.all()
    return render_template('admin.html', ultimo_gp=obtener_ultimo_gp(), usuarios=users)

@app.route('/establecer_puntos/2189073129873', methods=['POST'])
def establecer_puntos():
    user_id = request.form['username']
    puntaje = request.form['pts']

    user = User.query.get_or_404(user_id)
    user.puntaje = puntaje
    db.session.commit()

    print(f"Puntos establecidos para {user.username} a {puntaje}")
    return redirect(url_for('admin'))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

