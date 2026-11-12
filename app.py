from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import pymysql

app = Flask(__name__, template_folder='.')
CORS(app)  # Permite peticiones desde la Web App HTML/JS

# Configuración de conexión a Aiven MySQL
DB_HOST = "mysql-nfc-zacatenco-jprza19-892f.a.aivencloud.com"
DB_PORT = 11799
DB_USER = "avnadmin"
DB_PASSWORD = r"AVNS_0SRER5qnfA6_166jQLQ"
DB_NAME = "defaultdb"

def get_db_connection():
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        ssl={'ssl': {}},
        cursorclass=pymysql.cursors.DictCursor
    )

# Rutas para servir las vistas web desde cualquier dispositivo
@app.route('/')
@app.route('/index.html')
def home():
    return render_template('index.html')

@app.route('/enrolamiento.html')
def enrolamiento_page():
    return render_template('enrolamiento.html')

@app.route('/bitacora.html')
def bitacora_page():
    return render_template('bitacora.html')

@app.route('/login.html')
def login_page():
    return render_template('login.html')

# Ruta directa para el escaneo de la URL en el Tag NFC
@app.route('/ver')
def ver_tag():
    return render_template('index.html')

# 1. Endpoint: Consultar datos de usuario y vehículo por Tag NFC UID
@app.route('/api/consulta/<uid>', methods=['GET'])
def consultar_tag(uid):
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            sql = """
                SELECT u.id_usuario, u.boleta_empleado, u.nombre_completo, u.rol, u.unidad_academica,
                       u.fotografia_url, v.id_vehiculo, v.tag_nfc_uid, v.tipo, v.marca, v.modelo,
                       v.color, v.numero_serie, v.reportado_robo, v.estatus
                FROM vehiculos v
                JOIN usuarios u ON v.usuario_id = u.id_usuario
                WHERE v.tag_nfc_uid = %s
            """
            cursor.execute(sql, (uid,))
            resultado = cursor.fetchone()

        if resultado:
            return jsonify({"exito": True, "datos": resultado}), 200
        else:
            return jsonify({"exito": False, "mensaje": "Vehículo no registrado o etiqueta NFC no vinculada."}), 404

    except Exception as e:
        return jsonify({"exito": False, "error": str(e)}), 500
    finally:
        if connection:
            connection.close()

# 2. Endpoint: Registrar Entrada o Salida
@app.route('/api/registro', methods=['POST'])
def registrar_evento():
    data = request.get_json() or {}
    id_vehiculo = data.get('id_vehiculo')
    tipo_evento = data.get('tipo_evento')
    id_guardia = data.get('id_guardia', 'CASETA_EDIFICIO_1')

    if not id_vehiculo or tipo_evento not in ['ENTRADA', 'SALIDA']:
        return jsonify({"exito": False, "mensaje": "Faltan datos obligatorios o tipo de evento inválido."}), 400

    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            sql_insert = """
                INSERT INTO registros_acceso (vehiculo_id, tipo_evento, id_guardia)
                VALUES (%s, %s, %s)
            """
            cursor.execute(sql_insert, (id_vehiculo, tipo_evento, id_guardia))

            nuevo_estatus = 'DENTRO' if tipo_evento == 'ENTRADA' else 'FUERA'
            sql_update = "UPDATE vehiculos SET estatus = %s WHERE id_vehiculo = %s"
            cursor.execute(sql_update, (nuevo_estatus, id_vehiculo))

        connection.commit()

        return jsonify({
            "exito": True,
            "mensaje": f"Acceso registrado: {tipo_evento}",
            "nuevo_estatus": nuevo_estatus
        }), 200

    except Exception as e:
        if connection:
            connection.rollback()
        return jsonify({"exito": False, "error": str(e)}), 500
    finally:
        if connection:
            connection.close()

# 3. Endpoint: Enrolamiento / Registro de nuevo Usuario y Vehículo
@app.route('/api/enroled', methods=['POST'])
def enrolar_usuario_vehiculo():
    data = request.get_json() or {}
    boleta = data.get('boleta_empleado')
    nombre = data.get('nombre_completo')
    rol = data.get('rol', 'Alumno')
    unidad = data.get('unidad_academica', 'ESIME Zacatenco')
    
    tag_uid = data.get('tag_nfc_uid')
    marca = data.get('marca')
    modelo = data.get('modelo')
    color = data.get('color')
    numero_serie = data.get('numero_serie', '')

    raw_tipo = str(data.get('tipo', 'Bicicleta'))
    if 'Moto' in raw_tipo:
        tipo_vehiculo = 'Motocicleta'
    elif 'Mono' in raw_tipo or 'Scooter' in raw_tipo:
        tipo_vehiculo = 'Monopatín Eléctrico'
    elif 'Eléctrica' in raw_tipo or 'Electrica' in raw_tipo:
        tipo_vehiculo = 'Bicicleta Eléctrica'
    else:
        tipo_vehiculo = 'Bicicleta'

    if not boleta or not nombre or not tag_uid:
        return jsonify({"exito": False, "mensaje": "Faltan datos obligatorios."}), 400

    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            sql_check_tag = "SELECT id_vehiculo FROM vehiculos WHERE tag_nfc_uid = %s"
            cursor.execute(sql_check_tag, (tag_uid,))
            if cursor.fetchone():
                return jsonify({"exito": False, "mensaje": "Este Tag NFC ya está vinculado a otro vehículo."}), 400

            sql_buscar_usuario = "SELECT id_usuario FROM usuarios WHERE boleta_empleado = %s"
            cursor.execute(sql_buscar_usuario, (boleta,))
            usuario = cursor.fetchone()

            if usuario:
                id_usuario = usuario['id_usuario']
            else:
                sql_insert_usuario = """
                    INSERT INTO usuarios (boleta_empleado, nombre_completo, rol, unidad_academica)
                    VALUES (%s, %s, %s, %s)
                """
                cursor.execute(sql_insert_usuario, (boleta, nombre, rol, unidad))
                id_usuario = cursor.lastrowid

            sql_insert_vehiculo = """
                INSERT INTO vehiculos (usuario_id, tag_nfc_uid, tipo, marca, modelo, color, numero_serie)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql_insert_vehiculo, (id_usuario, tag_uid, tipo_vehiculo, marca, modelo, color, numero_serie))

        connection.commit()

        return jsonify({
            "exito": True,
            "mensaje": f"Vehículo ({marca} {modelo}) registrado correctamente para {nombre}."
        }), 201

    except Exception as e:
        if connection:
            connection.rollback()
        return jsonify({"exito": False, "error": str(e)}), 500
    finally:
        if connection:
            connection.close()

# 4. Endpoint: Obtener el padrón completo de vehículos
@app.route('/api/vehiculos', methods=['GET'])
def obtener_todos_los_vehiculos():
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            sql = """
                SELECT u.boleta_empleado, u.nombre_completo, u.rol, u.unidad_academica,
                       v.tag_nfc_uid, v.tipo, v.marca, v.modelo, v.color, v.estatus
                FROM vehiculos v
                JOIN usuarios u ON v.usuario_id = u.id_usuario
                ORDER BY v.id_vehiculo DESC
            """
            cursor.execute(sql)
            resultados = cursor.fetchall()
        return jsonify({"exito": True, "total": len(resultados), "datos": resultados}), 200
    except Exception as e:
        return jsonify({"exito": False, "error": str(e)}), 500
    finally:
        if connection:
            connection.close()

# 5. Endpoint: Obtener la bitácora de accesos
@app.route('/api/bitacora', methods=['GET'])
def obtener_bitacora():
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            sql = """
                SELECT r.id_registro, r.tipo_evento, r.timestamp, r.id_guardia,
                       u.boleta_empleado, u.nombre_completo,
                       v.tag_nfc_uid, v.tipo, v.marca, v.modelo
                FROM registros_acceso r
                JOIN vehiculos v ON r.vehiculo_id = v.id_vehiculo
                JOIN usuarios u ON v.usuario_id = u.id_usuario
                ORDER BY r.timestamp DESC
                LIMIT 100
            """
            cursor.execute(sql)
            resultados = cursor.fetchall()
        return jsonify({"exito": True, "total": len(resultados), "datos": resultados}), 200
    except Exception as e:
        return jsonify({"exito": False, "error": str(e)}), 500
    finally:
        if connection:
            connection.close()

# 6. Endpoint: Inicio de Sesión (Login - pendiente de integrar sesiones)
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    usuario = data.get('usuario')
    password = data.get('password')

    if not usuario or not password:
        return jsonify({"exito": False, "mensaje": "Ingresa usuario y contraseña."}), 400

    CREDENCIALES = {
        "guardia": {"password": "123", "rol": "Guardia", "nombre": "Guardia Caseta"},
        "admin": {"password": "admin", "rol": "Administrador", "nombre": "Jefe de Seguridad"}
    }

    if usuario in CREDENCIALES and CREDENCIALES[usuario]["password"] == password:
        user_info = CREDENCIALES[usuario]
        return jsonify({
            "exito": True,
            "mensaje": f"Bienvenido, {user_info['nombre']}",
            "rol": user_info['rol'],
            "usuario": usuario
        }), 200
    else:
        return jsonify({"exito": False, "mensaje": "Usuario o contraseña incorrectos."}), 401

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
