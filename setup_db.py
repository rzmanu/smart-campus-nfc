import pymysql

# Datos de conexión de tu servidor Aiven
DB_HOST = "mysql-nfc-zacatenco-jprza19-892f.a.aivencloud.com"
DB_PORT = 11799
DB_USER = "avnadmin"
DB_PASSWORD = "AVNS_0SRER5qnfA6_166jQLQ"  # <--- Reemplaza esto con tu contraseña de Aiven
DB_NAME = "defaultdb"

def init_db():
    print("Conectando a la base de datos MySQL en Aiven...")
    try:
        connection = pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            ssl={'ssl': {}}  # Requerido obligatoriamente por Aiven
        )
        print("¡Conexión establecida con éxito!")

        with connection.cursor() as cursor:
            # 1. Tabla de Usuarios
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS usuarios (
                    id_usuario INT AUTO_INCREMENT PRIMARY KEY,
                    boleta_empleado VARCHAR(20) NOT NULL UNIQUE,
                    nombre_completo VARCHAR(150) NOT NULL,
                    rol ENUM('Alumno', 'Docente', 'PAAE', 'Investigador') NOT NULL DEFAULT 'Alumno',
                    unidad_academica VARCHAR(100) DEFAULT 'ESIME Zacatenco',
                    fotografia_url VARCHAR(255) DEFAULT NULL,
                    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB;
            """)

            # 2. Tabla de Vehículos
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vehiculos (
                    id_vehiculo INT AUTO_INCREMENT PRIMARY KEY,
                    usuario_id INT NOT NULL,
                    tag_nfc_uid VARCHAR(50) NOT NULL UNIQUE,
                    tipo ENUM('Bicicleta', 'Bicicleta Eléctrica', 'Monopatín Eléctrico', 'Motocicleta') NOT NULL,
                    marca VARCHAR(50) NOT NULL,
                    modelo VARCHAR(50) NOT NULL,
                    color VARCHAR(30) NOT NULL,
                    numero_serie VARCHAR(100) DEFAULT NULL,
                    estatus ENUM('DENTRO', 'FUERA') NOT NULL DEFAULT 'FUERA',
                    reportado_robo BOOLEAN NOT NULL DEFAULT FALSE,
                    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (usuario_id) REFERENCES usuarios(id_usuario) ON DELETE CASCADE
                ) ENGINE=InnoDB;
            """)

            # Crear índice para búsquedas optimizadas en < 100 ms
            try:
                cursor.execute("CREATE INDEX idx_tag_uid ON vehiculos(tag_nfc_uid);")
            except Exception:
                pass

            # 3. Tabla de Registros de Acceso
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS registros_acceso (
                    id_registro INT AUTO_INCREMENT PRIMARY KEY,
                    vehiculo_id INT NOT NULL,
                    tipo_evento ENUM('ENTRADA', 'SALIDA') NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    id_guardia VARCHAR(50) DEFAULT 'GUARDIA_CASETA_1',
                    FOREIGN KEY (vehiculo_id) REFERENCES vehiculos(id_vehiculo) ON DELETE CASCADE
                ) ENGINE=InnoDB;
            """)

            # 4. Insertar datos de prueba
            print("Insertando registro inicial de prueba...")
            cursor.execute("""
                INSERT IGNORE INTO usuarios (id_usuario, boleta_empleado, nombre_completo, rol, unidad_academica)
                VALUES (1, '2022630000', 'Pérez Arenas José Manuel', 'Alumno', 'ESIME Zacatenco');
            """)

            cursor.execute("""
                INSERT IGNORE INTO vehiculos (usuario_id, tag_nfc_uid, tipo, marca, modelo, color, numero_serie)
                VALUES (1, '04A28B91', 'Bicicleta', 'Trek', 'Marlin 5', 'Negro/Verde', 'SN12345678');
            """)

        connection.commit()
        connection.close()
        print("--------------------------------------------------")
        print("¡ÉXITO! Tablas creadas y datos de prueba guardados en Aiven.")
        print("--------------------------------------------------")

    except Exception as e:
        print(f"Error durante la inicialización: {e}")

if __name__ == '__main__':
    init_db()