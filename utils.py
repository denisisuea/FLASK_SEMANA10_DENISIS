# utils.py
import json
import os
import csv
 
# Rutas a los archivos
BASE_DIR = os.path.dirname(__file__)
JSON_PATH = os.path.join(BASE_DIR, 'datos', 'datos.json')
CSV_PATH = os.path.join(BASE_DIR, 'datos', 'datos.csv')
TXT_PATH = os.path.join(BASE_DIR, 'datos', 'datos.txt')
 
# --- JSON ---
def guardar_productos_json(productos, filename=JSON_PATH):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(productos, f, ensure_ascii=False, indent=4)
 
def cargar_productos_json(filename=JSON_PATH):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []
 
# --- CSV ---
def guardar_productos_csv(productos, filename=CSV_PATH):
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["id", "nombre", "cantidad", "precio"])
        writer.writeheader()
        writer.writerows(productos)
 
# --- TXT ---
def guardar_productos_txt(productos, filename=TXT_PATH):
    with open(filename, 'w', encoding='utf-8') as f:
        for p in productos:
            f.write(f"ID: {p['id']} | Nombre: {p['nombre']} | Cantidad: {p['cantidad']} | Precio: {p['precio']}\n")
 
# --- Función central para sincronizar todos los formatos ---
def guardar_productos_multi(productos):
    """Guarda los productos en JSON, CSV y TXT."""
    guardar_productos_json(productos)
    guardar_productos_csv(productos)
    guardar_productos_txt(productos)