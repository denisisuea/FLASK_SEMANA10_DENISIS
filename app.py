from flask import Flask, render_template, redirect, url_for, flash, request, session, make_response
from flask_login import (
    LoginManager, login_user, logout_user, login_required,
    current_user, fresh_login_required
)
from conexion.conexion import conexion, cerrar_conexion
from datetime import datetime, timedelta
from decimal import Decimal
from models.model_login import Usuario
from math import ceil

# ---------------- Configuración de la aplicación Flask ----------------
app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key'

# Endurecer cookies/sesión
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",   # usa "Strict" si tu navegación lo permite
    SESSION_COOKIE_SECURE=False,     # pon True en producción con HTTPS
    PERMANENT_SESSION_LIFETIME=timedelta(minutes=30),
    REMEMBER_COOKIE_DURATION=timedelta(0),  # sin "recordarme"
)


# Evitar que el navegador cachee páginas (especialmente tras logout)
@app.after_request
def add_no_cache_headers(resp):
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp

# ---------------- Inicializa Flask-Login ----------------
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # redirige aquí si no está logueado
login_manager.needs_refresh_message = "Por seguridad, vuelve a iniciar sesión."
login_manager.needs_refresh_message_category = "info"

@app.context_processor
def inject_now():
    return {'now': datetime.utcnow()}

@login_manager.user_loader
def load_user(user_id):
    # Busca usuario en la BD por id
    return Usuario.obtener_por_id(user_id)

# ---------------- Rutas de autenticación ----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip()
        password = request.form['password']

        user = Usuario.obtener_por_mail(email)
        if user and user.verificar_password(password):
            login_user(user, remember=False)
            session.permanent = False
            flash('Inicio de sesión exitoso.', 'success')
            next_url = request.args.get('next')
            return redirect(next_url or url_for('index'))
        else:
            flash('Correo o contraseña incorrectos.', 'danger')

    return render_template('login.html', title='Iniciar Sesión')

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form['nombre'].strip()
        email = request.form['email'].strip()
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
            login_user(nuevo_usuario, remember=False)
            session.permanent = False
            return redirect(url_for('dashboard'))
        else:
            flash('Hubo un error al crear la cuenta', 'error')

    return render_template('registro.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    flash('Sesión cerrada.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template("dashboard.html", titulo="Panel de usuario", user=current_user)

# ---------------- Rutas públicas ----------------
@app.route('/')
def index():
    return render_template("index.html", titulo="Megacompu - Inicio")

@app.route('/about')
def about():
    return render_template("about.html", titulo="Acerca de Megacompu")

# ---------------- Rutas protegidas (Productos) ----------------
@app.route('/productos')
@login_required
def listar_productos():
    # Lee parámetros
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 3, type=int)
    q = request.args.get('q', '').strip()

    # Conexión
    conn = conexion()
    cursor = conn.cursor(dictionary=True)

    # 1) TOTAL para calcular páginas
    if q:
        cursor.execute("SELECT COUNT(*) AS c FROM productos WHERE nombre LIKE %s", (f'%{q}%',))
    else:
        cursor.execute("SELECT COUNT(*) AS c FROM productos")
    total = cursor.fetchone()['c']

    # Calcula last_page y corrige page fuera de rango
    last_page = max(1, ceil(total / per_page)) if total else 1
    if page < 1:
        page = 1
    if page > last_page:
        page = last_page

    offset = (page - 1) * per_page

    # 2) Consulta paginada
    if q:
        cursor.execute(
            """
            SELECT id_producto, nombre, cantidad, precio, descripcion
            FROM productos
            WHERE nombre LIKE %s
            ORDER BY nombre
            LIMIT %s OFFSET %s
            """,
            (f'%{q}%', per_page, offset)
        )
    else:
        cursor.execute(
            """
            SELECT id_producto, nombre, cantidad, precio, descripcion
            FROM productos
            ORDER BY nombre
            LIMIT %s OFFSET %s
            """,
            (per_page, offset)
        )

    productos = cursor.fetchall()
    cerrar_conexion(conn)

    # 3) Envía TODO lo que la plantilla usa
    return render_template(
        'products/list.html',
        title='Productos',
        productos=productos,
        q=q,
        page=page,
        per_page=per_page,
        total=total,
        last_page=last_page
    )

@app.route('/productos/nuevo', methods=['GET', 'POST'])
@fresh_login_required
def crear_producto():
    conn = conexion()
    cur = conn.cursor(dictionary=True)
 
    if request.method == 'POST':
        nombre = request.form['nombre'].strip()
        cantidad = int(request.form['cantidad'])
        precio = request.form['precio']                 # DECIMAL como string
        descripcion = request.form.get('descripcion','').strip()
 
        id_categoria = None
 
        # A) Si viene id_categoria, úsalo
        if request.form.get('id_categoria'):
            id_categoria = int(request.form['id_categoria'])
            cur.execute("SELECT 1 FROM categorias WHERE id_categoria=%s", (id_categoria,))
            if cur.fetchone() is None:
                cerrar_conexion(conn)
                flash('La categoría seleccionada no existe.', 'danger')
                return redirect(url_for('crear_producto'))
        else:
            # B) Usar categoria_nombre + marca (crea la categoría si no existe)
            categoria_nombre = (request.form.get('categoria_nombre') or '').strip().lower()
            marca = (request.form.get('marca') or '').strip()
 
            if not categoria_nombre or not marca:
                cerrar_conexion(conn)
                flash('Selecciona una categoría y una marca.', 'warning')
                return redirect(url_for('crear_producto'))
 
            cur.execute(
                "SELECT id_categoria FROM categorias "
                "WHERE LOWER(nombre)=%s AND LOWER(marca)=%s LIMIT 1",
                (categoria_nombre, marca.lower())
            )
            row = cur.fetchone()
            if row:
                id_categoria = row['id_categoria']
            else:
                cur2 = conn.cursor()
                cur2.execute(
                    "INSERT INTO categorias (nombre, marca) VALUES (%s, %s)",
                    (categoria_nombre, marca)
                )
                id_categoria = cur2.lastrowid
 
        # Insertar producto con la FK resuelta
        cur2 = conn.cursor()
        cur2.execute(
            "INSERT INTO productos (nombre, cantidad, precio, descripcion, id_categoria) "
            "VALUES (%s, %s, %s, %s, %s)",
            (nombre, cantidad, precio, descripcion, id_categoria)
        )
        conn.commit()
        cerrar_conexion(conn)
        flash('Producto creado exitosamente.', 'success')
        return redirect(url_for('listar_productos'))
 
    # ---------- GET: opciones para los selects ----------
    # Listas "fijas" que quieres ofrecer siempre:
    CATS_FIJAS = ['escritorio', 'laptop', 'accesorio']
    MARCAS_FIJAS = ['HP', 'Dell', 'Lenovo', 'Acer', 'Asus', 'Apple', 'MSI', 'Genérica']
 
    # Categorías presentes en BD
    cur.execute("SELECT DISTINCT LOWER(nombre) AS nombre FROM categorias")
    db_cats = [r['nombre'] for r in (cur.fetchall() or []) if r['nombre']]
 
    # Marcas presentes en BD
    cur.execute("SELECT DISTINCT marca FROM categorias")
    db_marcas = [r['marca'] for r in (cur.fetchall() or []) if r['marca']]
 
    # Unión (sin duplicados) y ordenadas
    categorias_ui = sorted({*(c.strip().lower() for c in CATS_FIJAS), *db_cats})
    marcas_ui = sorted({*(m.strip() for m in MARCAS_FIJAS), *db_marcas}, key=lambda s: s.lower())
 
    cerrar_conexion(conn)
    return render_template(
        'products/form.html',
        title='Nuevo Producto',
        producto=None,
        categorias_ui=categorias_ui,   # -> ['accesorio','escritorio','laptop', ...]
        marcas_ui=marcas_ui            # -> ['Acer','Apple','Asus','Dell',...,'Genérica',...]
    )

@app.route('/productos/<int:id_producto>/editar', methods=['GET', 'POST'])
@fresh_login_required
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
@fresh_login_required
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

# ---------------- Rutas protegidas (Clientes) ----------------
@app.route('/clientes')
@login_required
def listar_clientes():
    q = request.args.get('q', '').strip()
    conn = conexion()
    cur = conn.cursor(dictionary=True)
    if q:
        cur.execute(
            "SELECT id_cliente, nombre, cedula, telefono, email, direccion "
            "FROM clientes WHERE nombre LIKE %s OR cedula LIKE %s OR email LIKE %s "
            "ORDER BY nombre",
            (f"%{q}%", f"%{q}%", f"%{q}%")
        )
    else:
        cur.execute(
            "SELECT id_cliente, nombre, cedula, telefono, email, direccion "
            "FROM clientes ORDER BY nombre"
        )
    clientes = cur.fetchall()
    cerrar_conexion(conn)
    return render_template('clients/list.html', title='Clientes', clientes=clientes, q=q)

@app.route('/clientes/nuevo', methods=['GET', 'POST'])
@fresh_login_required
def crear_cliente():
    if request.method == 'POST':
        nombre = request.form['nombre'].strip()
        cedula = request.form.get('cedula', '').strip()
        telefono = request.form.get('telefono', '').strip()
        email = request.form.get('email', '').strip()
        direccion = request.form.get('direccion', '').strip()

        if not nombre:
            flash('El nombre es obligatorio', 'warning')
            return render_template('clients/form.html', title='Nuevo Cliente')

        conn = conexion()
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO clientes (nombre, cedula, telefono, email, direccion) "
                "VALUES (%s, %s, %s, %s, %s)",
                (nombre, cedula, telefono, email, direccion)
            )
            conn.commit()
            flash('Cliente creado correctamente', 'success')
            return redirect(url_for('listar_clientes'))
        except Exception:
            conn.rollback()
            flash('No se pudo crear el cliente (¿cedula/email duplicado?)', 'danger')
        finally:
            cerrar_conexion(conn)

    return render_template('clients/form.html', title='Nuevo Cliente')

# ---------------- Rutas protegidas (Ventas) ----------------
@app.route('/ventas')
@login_required
def listar_ventas():
    conn = conexion()
    cur = conn.cursor(dictionary=True)
    cur.execute(
        "SELECT v.id_venta, v.fecha, v.total, v.estado, c.nombre AS cliente "
        "FROM ventas v JOIN clientes c ON c.id_cliente = v.id_cliente "
        "ORDER BY v.id_venta DESC"
    )
    ventas = cur.fetchall()
    cerrar_conexion(conn)
    return render_template('sales/list.html', title='Ventas', ventas=ventas)

@app.route('/ventas/nueva', methods=['GET', 'POST'])
@fresh_login_required
def crear_venta():
    conn = conexion()
    cur = conn.cursor(dictionary=True)

    if request.method == 'GET':
        # Cargar clientes y productos para el formulario
        cur.execute("SELECT id_cliente, nombre FROM clientes ORDER BY nombre")
        clientes = cur.fetchall()
        cur.execute("SELECT id_producto, nombre, precio, cantidad FROM productos ORDER BY nombre")
        productos = cur.fetchall()
        cerrar_conexion(conn)
        return render_template('sales/form.html', title='Nueva Venta',
                               clientes=clientes, productos=productos)

    # POST: procesar venta
    try:
        id_cliente = int(request.form['id_cliente'])
    except Exception:
        cerrar_conexion(conn)
        flash('Cliente inválido', 'danger')
        return redirect(url_for('crear_venta'))

    prod_ids = request.form.getlist('producto_id[]')   # ['1','2',...]
    cantidades = request.form.getlist('cantidad[]')    # ['0','3',...]
    lineas = []
    for pid, qty in zip(prod_ids, cantidades):
        try:
            pid_i = int(pid)
            qty_i = int(qty)
            if qty_i > 0:
                lineas.append((pid_i, qty_i))
        except:
            continue

    if not lineas:
        cerrar_conexion(conn)
        flash('Debes agregar al menos un producto con cantidad > 0', 'warning')
        return redirect(url_for('crear_venta'))

    try:
        conn.start_transaction()

        # 1) Crear cabecera
        cur.execute(
            "INSERT INTO ventas (id_cliente, fecha, total, estado) "
            "VALUES (%s, NOW(), 0, 'PENDIENTE')",
            (id_cliente,)
        )
        id_venta = cur.lastrowid

        total = Decimal('0.00')

        # 2) Recorrer líneas, validar stock, descontar, insertar detalle
        for pid_i, qty_i in lineas:
            cur.execute(
                "SELECT nombre, cantidad, precio FROM productos WHERE id_producto=%s FOR UPDATE",
                (pid_i,)
            )
            row = cur.fetchone()
            if not row:
                raise ValueError(f"Producto {pid_i} no existe")

            nombre_p = row['nombre']
            stock = int(row['cantidad'])
            precio = Decimal(str(row['precio']))

            if qty_i > stock:
                raise ValueError(f"Stock insuficiente para {nombre_p}")

            # Descontar stock
            cur.execute(
                "UPDATE productos SET cantidad = cantidad - %s WHERE id_producto=%s",
                (qty_i, pid_i)
            )

            # Insertar detalle
            subtotal = (precio * Decimal(qty_i)).quantize(Decimal('0.01'))
            cur.execute(
                "INSERT INTO detalle_venta (id_venta, id_producto, cantidad, precio_unit, subtotal) "
                "VALUES (%s, %s, %s, %s, %s)",
                (id_venta, pid_i, qty_i, str(precio), str(subtotal))
            )
            total += subtotal

        # 3) Cerrar cabecera COMPLETADA con total
        total = total.quantize(Decimal('0.01'))
        cur.execute(
            "UPDATE ventas SET total=%s, estado='COMPLETADA' WHERE id_venta=%s",
            (str(total), id_venta)
        )

        conn.commit()
        flash(f'Venta #{id_venta} creada (total ${total})', 'success')
        return redirect(url_for('listar_ventas'))

    except Exception as e:
        conn.rollback()
        flash(f'No se pudo crear la venta: {e}', 'danger')
        return redirect(url_for('crear_venta'))
    finally:
        cerrar_conexion(conn)

if __name__ == '__main__':
    app.run(debug=True)