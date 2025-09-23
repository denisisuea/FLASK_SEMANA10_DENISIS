# reset_password.py
from conexion.conexion import conexion, cerrar_conexion
from werkzeug.security import generate_password_hash

UID = 8
NUEVA_CLAVE = "12345"  # <-- cámbiala a la que quieras

def main():
    nuevo_hash = generate_password_hash(
        NUEVA_CLAVE,
        method='pbkdf2:sha256:600000',
        salt_length=16
    )
    print("Nuevo hash:", nuevo_hash)

    conn = conexion()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE usuarios SET password=%s WHERE id_usuario=%s", (nuevo_hash, UID))
        conn.commit()
        print(f"Contraseña actualizada para id_usuario={UID}")
    finally:
        cur.close()
        cerrar_conexion(conn)

if __name__ == "__main__":
    main()