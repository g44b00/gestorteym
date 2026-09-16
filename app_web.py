import streamlit as st
import sqlite3
import pandas as pd
import json
import uuid
from datetime import datetime

# 1. Configuración de la pestaña del navegador
st.set_page_config(page_title="Gestor de Trámites", page_icon="📄", layout="wide")

# 2. SISTEMA DE SEGURIDAD (Login)
def check_password():
    """Verifica si la contraseña ingresada es correcta."""
    def password_entered():
        # CONTRASEÑA DE EJEMPLO: admin123
        if st.session_state["password"] == "admin123": 
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Borra la contraseña de la memoria
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.title("🔒 Acceso Seguro")
        st.text_input("Ingresa tu contraseña para continuar:", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.title("🔒 Acceso Seguro")
        st.text_input("Ingresa tu contraseña para continuar:", type="password", on_change=password_entered, key="password")
        st.error("Contraseña incorrecta. Inténtalo de nuevo.")
        return False
    else:
        return True

# Si la contraseña no es correcta, la página se detiene aquí y no muestra nada más
if not check_password():
    st.stop()


# 3. BASE DE DATOS (Se ejecuta solo si la contraseña es correcta)
def init_db():
    conn = sqlite3.connect("tramites_web.db")
    cursor = conn.cursor()
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS config_tramites (nombre TEXT PRIMARY KEY, campos JSON)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS registros_grupo (id_grupo TEXT PRIMARY KEY, tipo_tramite TEXT, fecha TEXT, monto TEXT, estado_tramite TEXT, estado_pago TEXT, notas TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS registros_personas (id INTEGER PRIMARY KEY AUTOINCREMENT, id_grupo TEXT, es_titular INTEGER, nombre TEXT, datos_dinamicos JSON, documentos TEXT)''')
    
    # Trámites por defecto si está vacío
    cursor.execute("SELECT count(*) FROM config_tramites")
    if cursor.fetchone()[0] == 0:
        defaults = [
            ("Residencia Definitiva", json.dumps(["Celular", "Correo Electrónico", "Clave Única", "Dirección"])),
            ("Residencia Temporaria", json.dumps(["Celular", "Correo Electrónico", "Clave Única", "Dirección"])),
            ("Legalización", json.dumps(["Celular", "Monto a Cobrar"]))
        ]
        cursor.executemany("INSERT INTO config_tramites VALUES (?, ?)", defaults)
        
    conn.commit()
    conn.close()

init_db()


# 4. INTERFAZ VISUAL: MENÚ Y SECCIONES
st.sidebar.title("📄 Gestor Documental")
st.sidebar.write("Bienvenido al sistema.")
st.sidebar.divider()

# Menú de navegación
menu = st.sidebar.radio(
    "Navegación",
    ["📝 Nuevo Registro", "🔍 Buscar / Editar", "📊 Exportar a Excel", "⚙️ Configuración"]
)

# Mostrar contenido según lo que elijas en el menú
if menu == "📝 Nuevo Registro":
    st.title("📝 Nuevo Registro")
    st.info("Aquí construiremos el formulario dinámico para registrar clientes.")

elif menu == "🔍 Buscar / Editar":
    st.title("🔍 Buscador")
    st.info("Aquí construiremos la tabla para buscar personas y trámites.")

elif menu == "📊 Exportar a Excel":
    st.title("📊 Exportar Datos")
    st.info("Aquí colocaremos el botón para descargar toda la base de datos.")

elif menu == "⚙️ Configuración":
    st.title("⚙️ Configuración")
    st.info("Aquí podrás agregar nuevas casillas y tipos de trámites a tu gusto.")
