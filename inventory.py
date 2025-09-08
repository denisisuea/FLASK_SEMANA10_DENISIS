# inventory.py
from models import db, Producto
from utils import guardar_productos_multi
 
class Inventario:
    """
    Inventario híbrido:
    - Se guarda siempre en BD.
    - Se sincroniza en JSON, CSV y TXT.
    """
 
    def __init__(self, productos_dict=None):
        self.productos = productos_dict or {}
        self.nombres = set(p.nombre.lower() for p in self.productos.values())
        self._guardar_archivos()
 
    @classmethod
    def cargar_desde_bd(cls):
        productos = Producto.query.all()
        productos_dict = {p.id: p for p in productos}
        return cls(productos_dict)
 
    def _guardar_archivos(self):
        productos_lista = [
            {"id": p.id, "nombre": p.nombre, "cantidad": p.cantidad, "precio": p.precio}
            for p in self.productos.values()
        ]
        guardar_productos_multi(productos_lista)
 
    # --- CRUD ---
    def agregar(self, nombre: str, cantidad: int, precio: float) -> Producto:
        if nombre.lower() in self.nombres:
            raise ValueError('Ya existe un producto con ese nombre.')
 
        p = Producto(nombre=nombre.strip(), cantidad=int(cantidad), precio=float(precio))
        db.session.add(p)
        db.session.commit()
 
        self.productos[p.id] = p
        self.nombres.add(p.nombre.lower())
 
        self._guardar_archivos()
        return p
 
    def eliminar(self, id: int) -> bool:
        p = self.productos.get(id) or Producto.query.get(id)
        if not p:
            return False
 
        db.session.delete(p)
        db.session.commit()
 
        self.productos.pop(id, None)
        self.nombres.discard(p.nombre.lower())
 
        self._guardar_archivos()
        return True
 
    def actualizar(self, id: int, nombre=None, cantidad=None, precio=None) -> Producto | None:
        p = self.productos.get(id) or Producto.query.get(id)
        if not p:
            return None
 
        if nombre is not None:
            nuevo = nombre.strip()
            if nuevo.lower() != p.nombre.lower() and nuevo.lower() in self.nombres:
                raise ValueError('Ya existe otro producto con ese nombre.')
            self.nombres.discard(p.nombre.lower())
            p.nombre = nuevo
            self.nombres.add(p.nombre.lower())
 
        if cantidad is not None:
            p.cantidad = int(cantidad)
        if precio is not None:
            p.precio = float(precio)
 
        db.session.commit()
        self.productos[p.id] = p
 
        self._guardar_archivos()
        return p
 
    # --- Consultas ---
    def buscar_por_nombre(self, q: str):
        q = q.lower()
        return sorted([p for p in self.productos.values() if q in p.nombre.lower()],
                      key=lambda x: x.nombre)
 
    def listar_todos(self):
        return sorted(self.productos.values(), key=lambda x: x.nombre)