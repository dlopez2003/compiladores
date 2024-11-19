from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_socketio import SocketIO, emit
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
import re
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'mi_clave_secreta'

# Configuración de Socket.IO
socketio = SocketIO(app)

# Conexión a la base de datos
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="chat_universidad"
    )

# Ruta para la página de inicio
@app.route('/')
def index():
    if 'usuario' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

# Ruta para el login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        correo = request.form['correo']
        contrasena = request.form['contrasena']

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM usuarios WHERE correo = %s", (correo,))
        user = cursor.fetchone()
        cursor.close()
        connection.close()

        if user and check_password_hash(user['contrasena'], contrasena):
            session['usuario'] = user
            session['usuario_id'] = user['id']
            flash("Inicio de sesión exitoso.", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Credenciales incorrectas", "error")

    return render_template('login.html')

# Ruta para el registro de nuevos usuarios
@app.route('/registro', methods=['GET', 'POST'])
def registro(): 
    if request.method == 'POST':
        correo = request.form['correo']
        nombre = request.form['nombre']
        contrasena = request.form['contrasena']
        contrasena_confirmada = request.form.get('contrasena_confirmada')

        if not contrasena_confirmada or contrasena != contrasena_confirmada:
            flash("Las contraseñas no coinciden.", "error")
            return render_template('registro.html')

        if not re.match(r"[^@]+@[^@]+\.[^@]+", correo):
            flash("Correo electrónico no válido.", "error")
            return render_template('registro.html')

        if not correo.endswith('@uab.edu.bo'):
            flash("El correo debe pertenecer al dominio @uab.edu.bo.", "error")
            return render_template('registro.html')

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM usuarios WHERE correo = %s", (correo,))
        user = cursor.fetchone()

        if user:
            flash("El correo ya está registrado.", "error")
            return render_template('registro.html')

        contrasena_hash = generate_password_hash(contrasena)
        rol = request.form['rol']

        cursor.execute(
            "INSERT INTO usuarios (nombre, correo, contrasena, rol) VALUES (%s, %s, %s, %s)",
            (nombre, correo, contrasena_hash, rol)
        )
        connection.commit()
        cursor.close()
        connection.close()

        flash("Registro exitoso. Puedes iniciar sesión ahora.", "success")
        return redirect(url_for('login'))

    return render_template('registro.html')

# Ruta para el dashboard
@app.route('/dashboard')
def dashboard():
    if 'usuario' not in session:
        flash("Por favor, inicia sesión primero.", "warning")
        return redirect(url_for('login'))

    usuario = session['usuario']
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM areas")
    areas = cursor.fetchall()
    cursor.close()
    connection.close()

    if usuario['rol'] == 'estudiante':
        return render_template('dashboard_estudiante.html', usuario=usuario, areas=areas)
    elif usuario['rol'] == 'administrador':
        return render_template('dashboard_admin.html', usuario=usuario, areas=areas)

# Ruta para los mensajes de un chat específico
@app.route('/mensajes/<int:area_id>', methods=['GET', 'POST'])
def mensajes(area_id):
    if 'usuario' not in session:
        flash("Por favor, inicia sesión primero.", "warning")
        return redirect(url_for('login'))

    usuario = session['usuario']
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    chat_id = None
    chat = None

    if usuario['rol'] == 'estudiante':
        cursor.execute("""
            SELECT c.id, a.nombre as area_nombre
            FROM chats c
            INNER JOIN areas a ON c.area_id = a.id
            WHERE c.estudiante_id = %s AND c.area_id = %s
        """, (usuario['id'], area_id))
        chat = cursor.fetchone()

        if not chat:
            cursor.execute("""
                INSERT INTO chats (estudiante_id, area_id) 
                VALUES (%s, %s)
            """, (usuario['id'], area_id))
            connection.commit()

            cursor.execute("""
                SELECT c.id, a.nombre as area_nombre 
                FROM chats c
                INNER JOIN areas a ON c.area_id = a.id
                WHERE c.estudiante_id = %s AND c.area_id = %s
            """, (usuario['id'], area_id))
            chat = cursor.fetchone()

        chat_id = chat['id']

    elif usuario['rol'] == 'administrador':
        estudiante_id = request.args.get('estudiante_id')
        if not estudiante_id:
            cursor.execute("""
                SELECT DISTINCT u.id as estudiante_id, u.nombre as estudiante_nombre,
                       COALESCE(c.mensajes_no_leidos, 0) as mensajes_no_leidos
                FROM chats c
                INNER JOIN usuarios u ON c.estudiante_id = u.id
                WHERE c.area_id = %s
            """, (area_id,))
            estudiantes = cursor.fetchall()
            cursor.close()
            connection.close()
            return render_template('mensajes.html', estudiantes=estudiantes, area_id=area_id, usuario=usuario)

        cursor.execute("""
            SELECT c.id, u.nombre as estudiante_nombre 
            FROM chats c
            INNER JOIN usuarios u ON c.estudiante_id = u.id
            WHERE c.estudiante_id = %s AND c.area_id = %s
        """, (estudiante_id, area_id))
        chat = cursor.fetchone()

        if not chat:
            cursor.execute("""
                INSERT INTO chats (estudiante_id, area_id, administrador_id) 
                VALUES (%s, %s, %s)
            """, (estudiante_id, area_id, usuario['id']))
            connection.commit()

            cursor.execute("""
                SELECT c.id, u.nombre as estudiante_nombre 
                FROM chats c
                INNER JOIN usuarios u ON c.estudiante_id = u.id
                WHERE c.estudiante_id = %s AND c.area_id = %s
            """, (estudiante_id, area_id))
            chat = cursor.fetchone()

        chat_id = chat['id']

    if chat_id:
        cursor.execute("""
            SELECT m.*, u.nombre 
            FROM mensajes m
            INNER JOIN usuarios u ON m.usuario_id = u.id
            WHERE m.chat_id = %s
            ORDER BY m.fecha_hora ASC
        """, (chat_id,))
        mensajes = cursor.fetchall()
    else:
        mensajes = []

    cursor.close()
    connection.close()

    return render_template('mensajes.html', mensajes=mensajes, chat=chat, area_id=area_id, usuario=usuario)

# Ruta para cerrar sesión
@app.route('/logout')
def logout():
    session.pop('usuario', None)
    flash("Has cerrado sesión exitosamente.", "success")
    return redirect(url_for('index'))

# Evento de Socket.IO para manejar mensajes
@socketio.on('send_message')
def handle_send_message(data):
    # Validar que los datos requeridos están presentes
    if 'usuario_id' not in data or 'mensaje' not in data or 'chat_id' not in data:
        print("Error: Datos incompletos al enviar el mensaje.")
        return

    usuario_id = data['usuario_id']
    mensaje = data['mensaje']
    chat_id = data['chat_id']
    fecha_hora = datetime.now()

    # Obtener el usuario y área asociados al mensaje
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        # Guardar el mensaje en la base de datos
        cursor.execute("""
            INSERT INTO mensajes (usuario_id, chat_id, mensaje, fecha_hora) 
            VALUES (%s, %s, %s, %s)
        """, (usuario_id, chat_id, mensaje, fecha_hora))
        connection.commit()

        # Actualizar el contador de mensajes no leídos para el estudiante
        if usuario_id != data['usuario_id']:  # No aumentar para el administrador que envió el mensaje
            cursor.execute("""
                UPDATE chats 
                SET mensajes_no_leidos = mensajes_no_leidos + 1 
                WHERE id = %s
            """, (chat_id,))
            connection.commit()

        # Obtener el nombre del usuario y el área
        cursor.execute("""
            SELECT u.nombre, c.area_id 
            FROM usuarios u 
            INNER JOIN chats c ON c.id = %s 
            WHERE u.id = %s
        """, (chat_id, usuario_id))
        user_data = cursor.fetchone()

        if not user_data:
            print("Error: No se encontró el usuario o chat asociado.")
            return
    except Exception as e:
        print("Error al guardar el mensaje:", e)
        return
    finally:
        cursor.close()
        connection.close()

    # Emitir el mensaje a todos los clientes conectados
    emit('new_message', {
        'usuario_id': usuario_id,
        'mensaje': mensaje,
        'chat_id': chat_id,
        'area_id': user_data['area_id'],
        'usuario_nombre': user_data['nombre'],
        'fecha_hora': fecha_hora.strftime('%Y-%m-%d %H:%M:%S')
    }, broadcast=True)

# Arrancar el servidor
if __name__ == "__main__":
    socketio.run(app, debug=True)
