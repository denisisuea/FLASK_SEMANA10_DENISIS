from flask import Flask, render_template, redirect, url_for, flash, request 
from datetime import datetime
from models import db
from forms import ProductoForm
from inventory import Inventario
from conexion.conexion import conexion, cerrar_conexion
from flask import render_template, request, url_for, redirect, make_response
app = Flask(__name__)

# Configuración
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inventario.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'dev-secret-key'
db.init_app(app)

@app.context_processor
def inject_now():
    return {'now': datetime.utcnow}

with app.app_context():
    db.create_all()
    inventario = Inventario.cargar_desde_bd()

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
 
    # página actual (>=1)
    try:
        page = int(request.args.get('page', 1))
    except (TypeError, ValueError):
        page = 1
    if page < 1:
        page = 1
 
    PER_PAGE = 3
 
    conn = None
    total = 0
    productos = []
 
    try:
        conn = conexion()
        cursor = conn.cursor(dictionary=True)
 
        # 1) total con mismo filtro de búsqueda
        if q:
            cursor.execute("SELECT COUNT(*) AS total FROM productos WHERE nombre LIKE %s", (f"%{q}%",))
        else:
            cursor.execute("SELECT COUNT(*) AS total FROM productos")
        row = cursor.fetchone() or {}
        total = int(row.get("total", 0))
 
        # 2) páginas y corrección si se pasa
        last_page = max(1, (total + PER_PAGE - 1) // PER_PAGE)
        if page > last_page:
            return redirect(url_for('listar_productos', page=last_page, q=q))
 
        offset = (page - 1) * PER_PAGE
 
        # 3) lista paginada (orden estable)
        base_sql = (
            "SELECT id_producto, nombre, cantidad, precio, descripcion "
            "FROM productos "
        )
        where = "WHERE nombre LIKE %s " if q else ""
        order = "ORDER BY id_producto ASC "
        limit = f"LIMIT {int(PER_PAGE)} OFFSET {int(offset)}"
        sql = base_sql + where + order + limit
 
        if q:
            cursor.execute(sql, (f"%{q}%",))
        else:
            cursor.execute(sql)
 
        productos = cursor.fetchall() or []
 
    finally:
        try:
            cerrar_conexion(conn)
        except Exception:
            pass
 
    # LOG de depuración: verifica en consola que "enviados" sea 3
    print(f"[/productos] q='{q}' page={page}/{last_page} total={total} enviados={len(productos)}")
 
    # Desactivar caché del navegador para esta página
    resp = make_response(render_template(
        "products/list.html",
        title="Productos",
        productos=productos,
        q=q,
        page=page,
        last_page=last_page,
        per_page=PER_PAGE,
        total=total,
    ))
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    resp.headers['Pragma'] = 'no-cache'
    return resp
@app.route('/productos/nuevo', methods=['GET', 'POST'])
def crear_producto():
    form = ProductoForm()
    if form.validate_on_submit():
        try:
            inventario.agregar(form.nombre.data, form.cantidad.data, form.precio.data)
            flash('Producto agregado correctamente.', 'success')
            return redirect(url_for('listar_productos'))
        except ValueError as e:
            form.nombre.errors.append(str(e))
    return render_template('products/form.html', title='Nuevo producto', form=form, modo='crear')

@app.route('/productos/<int:pid>/editar', methods=['GET', 'POST'])
def editar_producto(pid):
    prod = inventario.productos.get(pid)  # usamos cache de inventario
    if not prod:
        flash("Producto no encontrado", "warning")
        return redirect(url_for("listar_productos"))

    form = ProductoForm(obj=prod)
    if form.validate_on_submit():
        try:
            inventario.actualizar(pid, form.nombre.data, form.cantidad.data, form.precio.data)
            flash('Producto actualizado.', 'success')
            return redirect(url_for('listar_productos'))
        except ValueError as e:
            form.nombre.errors.append(str(e))
    return render_template('products/form.html', title='Editar producto', form=form, modo='editar')

@app.route('/productos/<int:pid>/eliminar', methods=['POST'])
def eliminar_producto(pid):
    ok = inventario.eliminar(pid)
    flash('Producto eliminado.' if ok else 'Producto no encontrado.', 'info' if ok else 'warning')
    return redirect(url_for('listar_productos'))

if __name__ == "__main__":
    app.run(debug=True)