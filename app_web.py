import streamlit as st
import sqlite3
import pandas as pd
import json
import uuid
from datetime import datetime

# Configuración visual de la pestaña
st.set_page_config(page_title="Gestor de Trámites", page_icon="📄", layout="wide")
# --- ESTILOS VISUALES Y ANIMACIONES (CSS) ---
estilos_css = """
<style>
    /* 1. Agrandar las opciones del menú lateral y prepararlas para animación */
    [data-testid="stSidebar"] .stRadio label {
        font-size: 18px !important; /* Letra más grande */
        padding: 12px 10px !important; /* Más espacio alrededor de la letra */
        margin-bottom: 5px !important;
        border-radius: 8px !important;
        transition: all 0.3s ease-in-out !important; /* Animación fluida */
        cursor: pointer !important;
    }
    
    /* 2. Efecto HOVER (al pasar el ratón) en el menú lateral */
    [data-testid="stSidebar"] .stRadio label:hover {
        transform: scale(1.05) translateX(15px) !important; /* Crece un 5% y se desliza a la derecha */
        background-color: #f0f8ff !important; /* Fondo azul pastel muy suave */
        color: #2980B9 !important; /* Letra cambia a azul fuerte */
        box-shadow: -2px 2px 10px rgba(0,0,0,0.05) !important; /* Sombra sutil */
    }

    /* 3. Animación para los botones principales (Ej. Guardar Trámite) */
    .stButton > button {
        transition: all 0.3s ease !important;
    }
    .stButton > button:hover {
        transform: translateY(-3px) scale(1.02) !important; /* Botón salta hacia arriba un poquito */
        box-shadow: 0px 5px 15px rgba(0,0,0,0.15) !important; /* Sombra más pronunciada */
    }
    
    /* 4. Animación para las casillas de texto al hacerles clic */
    .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] {
        transition: all 0.3s ease !important;
    }
    .stTextInput input:focus, .stTextArea textarea:focus, .stSelectbox div[data-baseweb="select"]:focus-within {
        transform: scale(1.01) !important; /* Crece microscópicamente */
        border-color: #3498DB !important; /* Borde azul */
        box-shadow: 0px 0px 8px rgba(52, 152, 219, 0.4) !important; /* Resplandor azul */
    }
</style>
"""
st.markdown(estilos_css, unsafe_allow_html=True)

# --- 1. SEGURIDAD ---
def check_password():
    def password_entered():
        if st.session_state["password"] == "programadorgabriel": 
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.title("🔒 Acceso Seguro")
        st.text_input("Contraseña:", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.title("🔒 Acceso Seguro")
        st.text_input("Contraseña:", type="password", on_change=password_entered, key="password")
        st.error("Contraseña incorrecta.")
        return False
    return True

if not check_password():
    st.stop()

# --- 2. BASE DE DATOS ---
def get_db_connection():
    return sqlite3.connect("tramites_web.db", check_same_thread=False)

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS config_tramites (nombre TEXT PRIMARY KEY, campos JSON)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS registros_grupo (id_grupo TEXT PRIMARY KEY, tipo_tramite TEXT, fecha TEXT, monto TEXT, estado_tramite TEXT, estado_pago TEXT, notas TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS registros_personas (id INTEGER PRIMARY KEY AUTOINCREMENT, id_grupo TEXT, es_titular INTEGER, nombre TEXT, datos_dinamicos JSON, documentos TEXT)''')
    
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

# --- 3. MENÚ LATERAL ---
st.sidebar.title("📄 Gestor Documental")
menu = st.sidebar.radio("Navegación", ["📝 Nuevo Registro", "🔍 Buscar / Editar", "📊 Exportar a Excel", "⚙️ Configuración"])

# --- 4. SECCIONES ---
if menu == "⚙️ Configuración":
    st.title("⚙️ Configuración de Trámites")
    conn = get_db_connection()
    df_tramites = pd.read_sql("SELECT * FROM config_tramites", conn)
    
    st.subheader("Añadir casillas a un trámite")
    if not df_tramites.empty:
        tramite_sel = st.selectbox("Selecciona el trámite a modificar:", df_tramites['nombre'].tolist())
        campos_actuales = json.loads(df_tramites[df_tramites['nombre'] == tramite_sel]['campos'].values[0])
        
        st.write(f"Casillas actuales en **{tramite_sel}**:")
        for campo in campos_actuales:
            st.markdown(f"- {campo}")
        
        nuevo_campo = st.text_input("Escribe el nombre de la nueva casilla (ej. Nacionalidad, N° Pasaporte):")
        if st.button("Añadir casilla", type="primary"):
            if nuevo_campo and nuevo_campo not in campos_actuales:
                campos_actuales.append(nuevo_campo)
                cursor = conn.cursor()
                cursor.execute("UPDATE config_tramites SET campos=? WHERE nombre=?", (json.dumps(campos_actuales), tramite_sel))
                conn.commit()
                st.success("¡Casilla añadida! Recarga la página para ver el cambio.")
                st.rerun()
    conn.close()

elif menu == "📝 Nuevo Registro":
    st.title("📝 Nuevo Registro")
    conn = get_db_connection()
    tramites_disp = pd.read_sql("SELECT nombre, campos FROM config_tramites", conn)
    
    if tramites_disp.empty:
        st.warning("No hay trámites configurados.")
    else:
        tipo_tramite = st.selectbox("Selecciona el tipo de trámite:", tramites_disp['nombre'].tolist())
        campos_json = tramites_disp[tramites_disp['nombre'] == tipo_tramite]['campos'].values[0]
        campos_dinamicos = json.loads(campos_json)
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.subheader("Datos Generales (Grupo)")
            monto = st.text_input("Monto Total a cobrar (CLP):", placeholder="$ 50000")
            estado_t = st.selectbox("Estado del Trámite:", ["Recibido", "En proceso", "Finalizado", "Rechazado"])
            estado_p = st.selectbox("Estado de Pago:", ["Pendiente", "Pagado"])
            notas = st.text_area("Notas / Observaciones:", height=150)
            
            # Una barra deslizante para elegir cuántas personas son
            st.subheader("Configuración")
            num_personas = st.slider("¿Cuántas personas incluye este trámite?", min_value=1, max_value=5, value=1)
        
        with col2:
            st.subheader("Datos de las Personas")
            datos_personas = []
            
            with st.form("form_registro"):
                for i in range(num_personas):
                    rol = "Titular" if i == 0 else f"Adicional {i}"
                    st.markdown(f"#### 👤 {rol}")
                    nombre = st.text_input(f"Nombre Completo ({rol}):", key=f"nom_{i}")
                    
                    dinamicos = {}
                    # Crear las casillas personalizadas automáticamente
                    for campo in campos_dinamicos:
                        dinamicos[campo] = st.text_input(f"{campo} ({rol}):", key=f"din_{i}_{campo}")
                        
                    docs = st.text_area(f"Documentos Recibidos ({rol}):", value="Recepción de documentos", key=f"doc_{i}", help="Anota aquí los documentos recibidos, separados por comas.")
                    datos_personas.append({"es_titular": 1 if i==0 else 0, "nombre": nombre, "dinamicos": dinamicos, "documentos": docs})
                    st.divider()
                    
                submit_btn = st.form_submit_button("Guardar Trámite Completo", type="primary")
                
                if submit_btn:
                    if not datos_personas[0]["nombre"].strip():
                        st.error("El nombre del Titular es obligatorio.")
                    else:
                        id_grupo = str(uuid.uuid4())[:8]
                        fecha_actual = datetime.now().strftime("%d/%m/%Y")
                        
                        cursor = conn.cursor()
                        cursor.execute('''INSERT INTO registros_grupo (id_grupo, tipo_tramite, fecha, monto, estado_tramite, estado_pago, notas) 
                                          VALUES (?, ?, ?, ?, ?, ?, ?)''', (id_grupo, tipo_tramite, fecha_actual, monto, estado_t, estado_p, notas))
                        
                        for p in datos_personas:
                            if p["nombre"].strip():
                                cursor.execute('''INSERT INTO registros_personas (id_grupo, es_titular, nombre, datos_dinamicos, documentos)
                                                  VALUES (?, ?, ?, ?, ?)''', 
                                               (id_grupo, p["es_titular"], p["nombre"], json.dumps(p["dinamicos"]), p["documentos"]))
                        
                        conn.commit()
                        st.success("¡Registro guardado correctamente en la nube!")
    conn.close()

elif menu == "🔍 Buscar / Editar":
    st.title("🔍 Buscador de Trámites")
    buscar = st.text_input("Escribe un nombre para buscar:", placeholder="Ej: Juan Pérez")
    if buscar:
        conn = get_db_connection()
        query = f"SELECT p.nombre, p.es_titular, g.tipo_tramite, g.fecha, g.monto, g.estado_tramite FROM registros_personas p JOIN registros_grupo g ON p.id_grupo = g.id_grupo WHERE p.nombre LIKE '%{buscar}%'"
        df_busqueda = pd.read_sql(query, conn)
        df_busqueda['es_titular'] = df_busqueda['es_titular'].apply(lambda x: 'Titular' if x==1 else 'Adicional')
        st.dataframe(df_busqueda, use_container_width=True)
        conn.close()

elif menu == "📊 Exportar a Excel":
    st.title("📊 Exportar Datos a Excel (CSV)")
    st.write("Genera un archivo con todos tus datos en un solo clic.")
    
    conn = get_db_connection()
    query = '''
        SELECT g.id_grupo, g.tipo_tramite, g.fecha, g.monto, g.estado_tramite, g.estado_pago, g.notas,
               p.es_titular, p.nombre, p.datos_dinamicos, p.documentos
        FROM registros_personas p
        JOIN registros_grupo g ON p.id_grupo = g.id_grupo
    '''
    df_export = pd.read_sql(query, conn)
    conn.close()
    
    if not df_export.empty:
        # Acomodar el formato para Excel
        lista_final = []
        for _, row in df_export.iterrows():
            fila = row.to_dict()
            dinamicos = json.loads(fila['datos_dinamicos']) if fila['datos_dinamicos'] else {}
            fila.update(dinamicos)
            del fila['datos_dinamicos']
            fila['es_titular'] = "Titular" if fila['es_titular'] == 1 else "Adicional"
            lista_final.append(fila)
            
        df_limpio = pd.DataFrame(lista_final)
        csv = df_limpio.to_csv(index=False, sep=";").encode('utf-8-sig')
        
        st.download_button(
            label="📥 Descargar Base de Datos Completa",
            data=csv,
            file_name=f"Reporte_Tramites_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            type="primary"
        )
    else:
        st.warning("Todavía no tienes ningún trámite guardado para exportar.")
