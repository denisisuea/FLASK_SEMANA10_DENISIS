from flask import Flask, render_template, redirect, url_for, flash, request
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from conexion.conexion import conexion, cerrar_conexion
from datetime import datetime
from models.model_login import Usuario

# Configuración de la aplicación Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key'

# Inicializa Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # redirige aquí si no está logueado

@app.context_processor
def inject_now():
    return {'now': datetime.utcnow()}

@login_manager.user_loader
def load_user(user_id):
    # Busca usuario en la BD por id
    return Usuario.obtener_por_id(user_id)

# --- Rutas de autenticación ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']       # cambiamos a email
        password = request.form['password']

        user = Usuario.obtener_por_mail(email)
        if user and user.verificar_password(password):
            login_user(user)
            flash('Inicio de sesión exitoso.', 'success')
            return redirect(url_for('index'))
        else:
            flash('Correo o contraseña incorrectos.', 'danger')

    return render_template('login.html', title='Iniciar Sesión')

#  ---> Aquí va la nueva ruta de registro

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form['nombre']
        email = request.form['email']
        password = request.form['password']
        password2 = request.form['password2']

        if password != password2:
            flash('Las contraseñas no coinciden', 'error')
            return render_template('registro.html', nombre=nombre, email=email)

        existente = Usuario.obtener_por_mail(email)
        if existente:
            flash('Este correo ya está registrado', 'error')
            return render_template('registro.html', nombre=nombre)

        nuevo_usuario = Usuario.crear_usuario(email, password, nombre)
        if nuevo_usuario:
            flash('Cuenta creada con éxito, ahora estás logueado', 'success')
            login_user(nuevo_usuario)
            return redirect(url_for('dashboard'))
        else:
            flash('Hubo un error al crear la cuenta', 'error')

    return render_template('registro.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sesión cerrada.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template("dashboard.html", titulo="Panel de usuario", user=current_user)

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
    cursor = conn.cursor(dictionary=True)
    if q:
        cursor.execute(
            "SELECT id_producto, nombre, cantidad, precio, descripcion FROM productos "
            "WHERE nombre LIKE %s ORDER BY nombre",
            (f'%{q}%',)
        )
    else:
        cursor.execute(
            "SELECT id_producto, nombre, cantidad, precio, descripcion FROM productos ORDER BY nombre"
        )
    productos = cursor.fetchall()
    cerrar_conexion(conn)
    return render_template('products/list.html', title='Productos', productos=productos, q=q)

@app.route('/productos/nuevo', methods=['GET', 'POST'])
def crear_producto():
    if request.method == 'POST':
        nombre = request.form['nombre']
        cantidad = request.form['cantidad']
        precio = request.form['precio']
        descripcion = request.form['descripcion']
        conn = conexion()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO productos (nombre, cantidad, precio, descripcion) VALUES (%s, %s, %s, %s)",
            (nombre, cantidad, precio, descripcion)
        )
        conn.commit()
        cerrar_conexion(conn)
        flash('Producto creado exitosamente.')
        return redirect(url_for('listar_productos'))
    return render_template('products/form.html', title='Nuevo Producto', producto=None)

@app.route('/productos/<int:id_producto>/editar', methods=['GET', 'POST'])
def editar_producto(id_producto):
    conn = conexion()
    cursor = conn.cursor(dictionary=True)
    if request.method == 'POST':
        nombre = request.form['nombre']
        cantidad = request.form['cantidad']
        precio = request.form['precio']
        descripcion = request.form['descripcion']
        cursor.execute(
            "UPDATE productos SET nombre=%s, cantidad=%s, precio=%s, descripcion=%s WHERE id_producto=%s",
            (nombre, cantidad, precio, descripcion, id_producto)
        )
        conn.commit()
        cerrar_conexion(conn)
        flash('Producto actualizado exitosamente.')
        return redirect(url_for('listar_productos'))
    else:
        cursor.execute(
            "SELECT id_producto, nombre, cantidad, precio, descripcion FROM productos WHERE id_producto=%s",
            (id_producto,)
        )
        producto = cursor.fetchone()
        cerrar_conexion(conn)
        if producto is None:
            flash('Producto no encontrado.')
            return redirect(url_for('listar_productos'))
    return render_template('products/form.html', title='Editar Producto', producto=producto)

@app.route('/productos/<int:id_producto>/eliminar', methods=['POST'])
def eliminar_producto(id_producto):
    conn = conexion()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM productos WHERE id_producto=%s",
        (id_producto,)
    )
    conn.commit()
    cerrar_conexion(conn)
    flash('Producto eliminado exitosamente.')
    return redirect(url_for('listar_productos'))

if __name__ == '__main__':
    app.run(debug=True)
