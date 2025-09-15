from flask import Flask, render_template, redirect, url_for, flash, request 
from datetime import datetime
from models import db
from forms import ProductoForm
from inventory import Inventario

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
    productos = inventario.buscar_por_nombre(q) if q else inventario.listar_todos()
    return render_template('products/list.html', title='Productos', productos=productos, q=q)

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
