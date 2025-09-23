# models/model_login.py
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from conexion.conexion import conexion, cerrar_conexion
from mysql.connector import Error

class Usuario(UserMixin):
    def __init__(self, id_usuario, nombre, email, password):
        # Flask-Login usa .id (string)
        self.id = str(id_usuario)  # id_usuario en la tabla
        self.user_id = id_usuario    # opcional, si quieres el int
        self.nombre = nombre
        self.email = email
        self.password_hash = password  # columna 'password' de la tabla

    def verificar_password(self, password_plano: str) -> bool:
        return check_password_hash(self.password_hash, password_plano)

    @staticmethod
    def obtener_por_id(user_id: int):
        conn = conexion()
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute("SELECT id_usuario, nombre, email, password FROM usuarios WHERE id_usuario = %s", (user_id,))
            row = cur.fetchone()
            if row:
                return Usuario(row['id_usuario'], row['nombre'], row['email'], row['password'])
            return None
        except Error as e:
            print(f"Error al obtener usuario por ID: {e}")
            return None
        finally:
            try: cur.close()
            finally: cerrar_conexion(conn)

    @staticmethod
    def obtener_por_mail(email: str):
        conn = conexion()
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute("SELECT id_usuario, nombre, email, password FROM usuarios WHERE email = %s", (email,))
            row = cur.fetchone()
            if row:
                return Usuario(row['id_usuario'], row['nombre'], row['email'], row['password'])
            return None
        except Error as e:
            print(f"Error al obtener usuario por email: {e}")
            return None
        finally:
            try: cur.close()
            finally: cerrar_conexion(conn)

    @staticmethod
    def crear_usuario(email: str, password_plano: str, nombre: str):
        """Crea usuario usando PBKDF2-SHA256 (600k)."""
        conn = conexion()
        cur = conn.cursor()
        try:
            password_hash = generate_password_hash(
                password_plano,
                method='pbkdf2:sha256:600000',
                salt_length=16
            )
            cur.execute(
                "INSERT INTO usuarios (nombre, email, password) VALUES (%s, %s, %s)",
                (nombre, email, password_hash)
            )
            conn.commit()
            cur.close()
            # Nuevo cursor para obtener el usuario recién creado
            cur2 = conn.cursor(dictionary=True)
            cur2.execute("SELECT id_usuario, nombre, email, password FROM usuarios WHERE email=%s", (email,))
            row = cur2.fetchone()
            cur2.close()
            return Usuario(row['id_usuario'], row['nombre'], row['email'], row['password']) if row else None
        except Error as e:
            print(f"Error al crear usuario: {e}")
            return None
        finally:
            cerrar_conexion(conn)