from flask import Flask, request, jsonify
from flask_cors import CORS
import pymysql

app = Flask(__name__)
CORS(app)  # Permite que la Web App móvil haga peticiones al servidor

# Configuración de conexión a Aiven
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

# Ruta raíz para verificar que el servidor está vivo
@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "estado": "Servidor Activo",
        "proyecto": "Smart Campus NFC - ESIME Zacatenco"
    }), 200

# 1. Endpoint: Consultar datos al escanear la etiqueta NFC
@app.route('/api/consulta/<uid>', methods=['GET'])
def consultar_tag(uid):
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            sql = """
                SELECT 
                    u.id_usuario, u.boleta_empleado, u.nombre_completo, u.rol, u.unidad_academica, u.fotografia_url,
                    v.id_vehiculo, v.tag_nfc_uid, v.tipo, v.marca, v.modelo, v.color, 
                    v.numero_serie, v.estatus, v.reportado_robo
                FROM vehiculos v
                JOIN usuarios u ON v.usuario_id = u.id_usuario
                WHERE v.tag_nfc_uid = %s
            """
            cursor.execute(sql, (uid,))
            resultado = cursor.fetchone()
            
        connection.close()

        if resultado:
            return jsonify({
                "exito": True,
                "datos": resultado
            }), 200
        else:
            return jsonify({
                "exito": False,
                "mensaje": "Vehículo no registrado o etiqueta NFC no vinculada."
            }), 404

    except Exception as e:
        return jsonify({"exito": False, "error": str(e)}), 500

# 2. Endpoint: Registrar evento de ENTRADA o SALIDA
@app.route('/api/registro', methods=['POST'])
def registrar_evento():
    data = request.get_json()
    id_vehiculo = data.get('id_vehiculo')
    tipo_evento = data.get('tipo_evento')  # 'ENTRADA' o 'SALIDA'
    id_guardia = data.get('id_guardia', 'GUARDIA_CASETA_1')

    if not id_vehiculo or tipo_evento not in ['ENTRADA', 'SALIDA']:
        return jsonify({"exito": False, "mensaje": "Datos incompletos o tipo de evento inválido."}), 400

    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # Registrar en bitácora de accesos
            sql_log = """
                INSERT INTO registros_acceso (vehiculo_id, tipo_evento, id_guardia)
                VALUES (%s, %s, %s)
            """
            cursor.execute(sql_log, (id_vehiculo, tipo_evento, id_guardia))

            # Actualizar estatus del vehículo
            nuevo_estatus = 'DENTRO' if tipo_evento == 'ENTRADA' else 'FUERA'
            sql_update = "UPDATE vehiculos SET estatus = %s WHERE id_vehiculo = %s"
            cursor.execute(sql_update, (nuevo_estatus, id_vehiculo))

        connection.commit()
        connection.close()

        return jsonify({
            "exito": True,
            "mensaje": f"Evento de {tipo_evento} registrado correctamente.",
            "nuevo_estatus": nuevo_estatus
        }), 200

    except Exception as e:
        return jsonify({"exito": False, "error": str(e)}), 500

 # 3. Endpoint: Enrolamiento / Registro de nuevo Usuario y Vehículo
@app.route('/api/enroled', methods=['POST'])
def enrolar_usuario_vehiculo():
    data = request.get_json()
    
    # Extraer campos requeridos
    boleta = data.get('boleta_empleado')
    nombre = data.get('nombre_completo')
    rol = data.get('rol', 'Alumno')
    unidad = data.get('unidad_academica', 'ESIME Zacatenco')
    
    tag_uid = data.get('tag_nfc_uid')
    tipo_vehiculo = data.get('tipo')
    marca = data.get('marca')
    modelo = data.get('modelo')
    color = data.get('color')
    numero_serie = data.get('numero_serie', '')

    if not boleta or not nombre or not tag_uid or not tipo_vehiculo:
        return jsonify({"exito": False, "mensaje": "Faltan datos obligatorios (Boleta, Nombre, UID o Tipo de Vehículo)."}), 400

    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # A) Verificar si el usuario ya existe o crearlo
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

            # B) Verificar que el Tag NFC no esté registrado previo
            sql_check_tag = "SELECT id_vehiculo FROM vehiculos WHERE tag_nfc_uid = %s"
            cursor.execute(sql_check_tag, (tag_uid,))
            if cursor.fetchone():
                connection.close()
                return jsonify({"exito": False, "mensaje": "Este Tag NFC ya está vinculado a otro vehículo."}), 400

            # C) Registrar el nuevo vehículo vinculado al usuario
            sql_insert_vehiculo = """
                INSERT INTO vehiculos (usuario_id, tag_nfc_uid, tipo, marca, modelo, color, numero_serie)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql_insert_vehiculo, (id_usuario, tag_uid, tipo_vehiculo, marca, modelo, color, numero_serie))

        connection.commit()
        connection.close()

        return jsonify({
            "exito": True,
            "mensaje": f"Vehículo ({marca} {modelo}) registrado correctamente para {nombre}."
        }), 201

    except Exception as e:
        return jsonify({"exito": False, "error": str(e)}), 500  

if __name__ == '__main__':
    # Se ejecuta localmente en el puerto 5000
    app.run(host='0.0.0.0', port=5000, debug=True)