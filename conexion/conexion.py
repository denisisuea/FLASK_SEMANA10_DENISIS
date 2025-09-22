# clase de conexion a BD 
import mysql.connector
from mysql.connector import Error

# conexion a la base de datos

def conexion():
    return mysql.connector.connect(
        host='localhost',
        port=3307,
        database='megacompu',
        user='root',  # luego en producción usa variable de entorno
        password='123456' # luego en producción usa variable de entorno
    )

# cerrar conexion a la base de datos

def cerrar_conexion(conn):
    if conn.is_connected():
        conn.close()
        print("Conexion a la base de datos cerrada.")



        

# probar conexion a la base de datos
