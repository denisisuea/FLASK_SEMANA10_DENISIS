# hacer con mysql-connector-python
from flask import Flask, render_template, redirect, url_for, flash, request 
from conexion.conexion import conexion, cerrar_conexion
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key'   # en producción usa variable de entorno
 
@app.context_processor
def inject_now():
    return {'now': datetime.utcnow()}

# --- Rutas ---
@app.route('/')
def index():
    return render_template("index.html", titulo="Megacompu - Inicio")       

@app.route('/about')
def about():
    return render_template("about.html", titulo="Acerca de Megacompu")

@app.route('/productos')
def listar_productos():
    q = request.args.get('q', '').strip()
    conn = conexion()
    cursor = conn.cursor()
    if q:
        cursor.execute("SELECT id, nombre, cantidad, precio FROM productos WHERE nombre LIKE %s ORDER BY nombre", (f'%{q}%',))
    else:
        cursor.execute("SELECT id, nombre, cantidad, precio FROM productos ORDER BY nombre")
    productos = cursor.fetchall()
    cerrar_conexion(conn)
    return render_template('products/list.html', title='Productos', productos=productos, q=q)

# crear producto
@app.route('/productos/nuevo', methods=['GET', 'POST'])
def crear_producto():
    if request.method == 'POST':
        nombre = request.form['nombre']
        cantidad = request.form['cantidad']
        precio = request.form['precio']
        conn = conexion()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO productos (nombre, cantidad, precio) VALUES (%s, %s, %s)", (nombre, cantidad, precio))
        conn.commit()
        cerrar_conexion(conn)
        flash('Producto creado exitosamente.')
        return redirect(url_for('listar_productos'))
    return render_template('products/new.html', title='Nuevo Producto')

# editar producto
@app.route('/productos/<int:pid>/editar', methods=['GET', 'POST'])
def editar_producto(pid):
    conn = conexion()
    cursor = conn.cursor()
    if request.method == 'POST':
        nombre = request.form['nombre']
        cantidad = request.form['cantidad']
        precio = request.form['precio']
        cursor.execute("UPDATE productos SET nombre=%s, cantidad=%s, precio=%s WHERE id=%s", (nombre, cantidad, precio, pid))
        conn.commit()
        cerrar_conexion(conn)
        flash('Producto actualizado exitosamente.')
        return redirect(url_for('listar_productos'))
    else:
        cursor.execute("SELECT id, nombre, cantidad, precio FROM productos WHERE id=%s", (pid,))
        producto = cursor.fetchone()
        cerrar_conexion(conn)
        if producto is None:
            flash('Producto no encontrado.')
            return redirect(url_for('listar_productos'))
        return render_template('products/edit.html', title='Editar Producto', producto=producto)
# eliminar producto
@app.route('/productos/<int:pid>/eliminar', methods=['POST'])
def eliminar_producto(pid):
    conn = conexion()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM productos WHERE id=%s", (pid,))
    conn.commit()
    cerrar_conexion(conn)
    flash('Producto eliminado exitosamente.')
    return redirect(url_for('listar_productos'))

if __name__ == '__main__':
    app.run(debug=True)
