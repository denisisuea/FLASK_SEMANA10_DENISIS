from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def index():
    return render_template("index.html", titulo="Megacompu - Inicio")

@app.route('/about')
def about():
    return render_template("about.html", titulo="Acerca de Megacompu")

@app.route('/products')
def products():
    productos = [
        {"nombre": "Laptop Gamer", "precio": 1200},
        {"nombre": "PC de Escritorio", "precio": 850},
        {"nombre": "Monitor 24''", "precio": 180},
        {"nombre": "Teclado Mecánico", "precio": 60}
    ]
    return render_template("products.html", titulo="Productos", productos=productos)

if __name__ == "__main__":
    app.run(debug=True)
