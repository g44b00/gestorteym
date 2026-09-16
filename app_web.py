import streamlit as st
import sqlite3
import pandas as pd
import json
import uuid
from datetime import datetime
import io 

# --- CONFIGURACIÓN VISUAL ---
st.set_page_config(page_title="Gestor de Trámites", page_icon="📄", layout="wide")

estilos_css = """
<style>
    /* Menú Lateral */
    [data-testid="stSidebar"] .stRadio label { font-size: 24px !important; padding: 18px 16px !important; margin-bottom: 12px !important; border-radius: 12px !important; transition: all 0.3s ease-in-out !important; cursor: pointer !important; }
    [data-testid="stSidebar"] .stRadio label p { font-size: 24px !important; }
    [data-testid="stSidebar"] .stRadio label:hover { transform: scale(1.06) translateX(15px) !important; background-color: rgba(52, 152, 219, 0.15) !important; color: #3498DB !important; box-shadow: -2px 4px 15px rgba(0,0,0,0.1) !important; }
    
    /* Textos Generales y Controles */
    label, .stSelectbox label, .stTextInput label, .stTextArea label, p { font-size: 20px !important; font-weight: 600 !important; }
    .stTextInput, .stSelectbox, .stTextArea { max-width: 650px !important; }
    .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] { font-size: 18px !important; padding: 10px 14px !important; border-radius: 8px !important; }
    
    /* Botones */
    .stButton > button { font-size: 20px !important; font-weight: 600 !important; padding: 12px 28px !important; border-radius: 8px !important; transition: all 0.3s ease !important; }
    .stButton > button:hover { transform: translateY(-3px) scale(1.02) !important; box-shadow: 0px 5px 15px rgba(0,0,0,0.15) !important; }
    
    /* Tarjetas del Dashboard */
    .metric-card {
        background-color: #f8f9fa;
        border-left: 6px solid #3498DB;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0px 4px 6px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }
    .metric-card h3 { margin: 0; color: #7f8c8d; font-size: 18px; }
    .metric-card h2 { margin: 5px 0 0 0; color: #2c3e50; font-size: 36px; }
</style>
"""
st.markdown(estilos_css, unsafe_allow_html=True)

# --- 1. SEGURIDAD ---
def check_password():
    def password_entered():
        if st.session_state["password"] == "MisTramites2026": 
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
    cursor.execute('''CREATE TABLE IF NOT EXISTS archivos_subidos (id INTEGER PRIMARY KEY AUTOINCREMENT, id_persona INTEGER, nombre_archivo TEXT, tipo_archivo TEXT, datos BLOB)''')
    
    cursor.execute("SELECT count(*) FROM config_tramites")
    if cursor.fetchone()[0] == 0:
        defaults = [("Residencia Definitiva", json.dumps(["Celular", "Correo Electrónico"])),
                    ("Residencia Temporaria", json.dumps(["Celular", "Correo Electrónico"])),
                    ("Legalización", json.dumps(["Celular"]))]
        cursor.executemany("INSERT INTO config_tramites VALUES (?, ?)", defaults)
    conn.commit()
    conn.close()

init_db()

# --- 3. MENÚ LATERAL ---
st.sidebar.title("📄 Gestor Documental")
menu = st.sidebar.radio("Navegación", ["🏠 Dashboard Inicial", "📝 Nuevo Registro", "🔍 Buscar / Editar", "📊 Exportar a Excel", "⚙️ Configuración"])

# --- 4. SECCIONES ---

if menu == "🏠 Dashboard Inicial":
    st.title("🏠 Panel de Control")
    conn = get_db_connection()
    
    # Cálculos para el Dashboard
    df_dashboard = pd.read_sql("SELECT monto, estado_pago, tipo_tramite, fecha FROM registros_grupo", conn)
    
    # Limpiar montos (quitar el signo $ y puntos para poder sumar matemáticamente)
    def limpiar_monto(valor):
        try:
            return int(str(valor).replace('$', '').replace('.', '').replace(' ', '').strip())
        except:
            return 0
            
    if not df_dashboard.empty:
        df_dashboard['monto_num'] = df_dashboard['monto'].apply(limpiar_monto)
        
        ingresos_totales = df_dashboard[df_dashboard['estado_pago'] == 'Pagado']['monto_num'].sum()
        dinero_pendiente = df_dashboard[df_dashboard['estado_pago'] == 'Pendiente']['monto_num'].sum()
        total_tramites = len(df_dashboard)
        
        # Formatear números como CLP
        formato_ingreso = f"${ingresos_totales:,.0f}".replace(",", ".")
        formato_pendiente = f"${dinero_pendiente:,.0f}".replace(",", ".")
        
        # Mostrar Tarjetas (Cards)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"<div class='metric-card'><h3>💰 Ingresos Pagados</h3><h2>{formato_ingreso}</h2></div>", unsafe_allow_html=True)
        with col2:
            st.markdown(f"<div class='metric-card' style='border-left-color: #E74C3C;'><h3>⏳ Dinero Pendiente</h3><h2>{formato_pendiente}</h2></div>", unsafe_allow_html=True)
        with col3:
            st.markdown(f"<div class='metric-card' style='border-left-color: #2ECC71;'><h3>📄 Total Trámites</h3><h2>{total_tramites}</h2></div>", unsafe_allow_html=True)
        
        st.divider()
        
        # Gráfico simple de Trámites
        st.subheader("Distribución de Trámites")
        conteo_tramites = df_dashboard['tipo_tramite'].value_counts()
        st.bar_chart(conteo_tramites, use_container_width=True)
        
    else:
        st.info("Aún no hay trámites registrados. El panel de control se poblará cuando agregues datos.")
    conn.close()

elif menu == "⚙️ Configuración":
    st.title("⚙️ Configuración del Sistema")
    conn = get_db_connection()
    
    st.subheader("1. Crear Nuevo Tipo de Trámite")
    nuevo_tramite_nombre = st.text_input("Nombre del nuevo trámite:")
    if st.button("Crear Trámite", type="primary"):
        if nuevo_tramite_nombre:
            try:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO config_tramites VALUES (?, ?)", (nuevo_tramite_nombre, "[]"))
                conn.commit()
                st.success(f"Trámite '{nuevo_tramite_nombre}' creado con éxito.")
                st.rerun()
            except sqlite3.IntegrityError:
                st.error("Ese trámite ya existe.")
    
    st.divider()
    
    st.subheader("2. Modificar Casillas de un Trámite")
    df_tramites = pd.read_sql("SELECT * FROM config_tramites", conn)
    if not df_tramites.empty:
        tramite_sel = st.selectbox("Selecciona el trámite a modificar:", df_tramites['nombre'].tolist())
        campos_actuales = json.loads(df_tramites[df_tramites['nombre'] == tramite_sel]['campos'].values[0])
        
        st.write("Casillas actuales (Haz clic en 🗑️ para eliminar):")
        for campo in campos_actuales:
            col1, col2 = st.columns([4, 1])
            col1.markdown(f"- {campo}")
            if col2.button("🗑️ Eliminar", key=f"del_{tramite_sel}_{campo}"):
                campos_actuales.remove(campo)
                cursor = conn.cursor()
                cursor.execute("UPDATE config_tramites SET campos=? WHERE nombre=?", (json.dumps(campos_actuales), tramite_sel))
                conn.commit()
                st.rerun()
        
        nuevo_campo = st.text_input("Agregar nueva casilla:")
        if st.button("Añadir casilla"):
            if nuevo_campo and nuevo_campo not in campos_actuales:
                campos_actuales.append(nuevo_campo)
                cursor = conn.cursor()
                cursor.execute("UPDATE config_tramites SET campos=? WHERE nombre=?", (json.dumps(campos_actuales), tramite_sel))
                conn.commit()
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
            st.subheader("Datos del Grupo")
            monto = st.text_input("Monto Total (CLP):", placeholder="Ej: 50000")
            estado_t = st.selectbox("Estado del Trámite:", ["Recibido", "En proceso", "Finalizado", "Rechazado"])
            estado_p = st.selectbox("Estado de Pago:", ["Pendiente", "Pagado"])
            notas = st.text_area("Notas / Observaciones:", height=150)
            st.divider()
            num_personas = st.slider("¿Cuántas personas incluye?", 1, 5, 1)
        
        with col2:
            st.subheader("Personas y Archivos")
            datos_personas = []
            
            with st.form("form_registro", clear_on_submit=True):
                for i in range(num_personas):
                    es_titular = (i == 0)
                    rol = "Titular" if es_titular else f"Adicional {i}"
                    st.markdown(f"#### 👤 {rol}")
                    
                    nombre = st.text_input(f"Nombre Completo:", key=f"nom_{i}")
                    dinamicos = {}
                    
                    if tipo_tramite == "Legalización" and es_titular:
                        dinamicos["Tipo de certificado"] = st.selectbox("Tipo de certificado:", ["Antecedentes", "Nacimiento"], key=f"cert_{i}")
                    
                    for campo in campos_dinamicos:
                        dinamicos[campo] = st.text_input(f"{campo}:", key=f"din_{i}_{campo}")
                    
                    docs = ""
                    if tipo_tramite != "Legalización":
                        docs = st.text_area(f"Documentos Físicos Recibidos:", value="Ninguno", key=f"doc_{i}")
                    
                    archivos = st.file_uploader(f"Subir archivos (PDF, JPG, PNG)", type=["pdf", "png", "jpg"], accept_multiple_files=True, key=f"file_{i}")
                    datos_personas.append({"es_titular": 1 if es_titular else 0, "nombre": nombre, "dinamicos": dinamicos, "documentos": docs, "archivos": archivos})
                    st.divider()
                    
                submit_btn = st.form_submit_button("Guardar Trámite Completo", type="primary")
                
                if submit_btn:
                    if not datos_personas[0]["nombre"].strip():
                        st.error("El nombre del Titular es obligatorio.")
                    else:
                        id_grupo = str(uuid.uuid4())[:8]
                        fecha_actual = datetime.now().strftime("%d/%m/%Y")
                        cursor = conn.cursor()
                        cursor.execute('''INSERT INTO registros_grupo (id_grupo, tipo_tramite, fecha, monto, estado_tramite, estado_pago, notas) VALUES (?, ?, ?, ?, ?, ?, ?)''', (id_grupo, tipo_tramite, fecha_actual, monto, estado_t, estado_p, notas))
                        
                        for p in datos_personas:
                            if p["nombre"].strip():
                                cursor.execute('''INSERT INTO registros_personas (id_grupo, es_titular, nombre, datos_dinamicos, documentos) VALUES (?, ?, ?, ?, ?)''', (id_grupo, p["es_titular"], p["nombre"], json.dumps(p["dinamicos"]), p["documentos"]))
                                person_id = cursor.lastrowid
                                if p["archivos"]:
                                    for arch in p["archivos"]:
                                        cursor.execute("INSERT INTO archivos_subidos (id_persona, nombre_archivo, tipo_archivo, datos) VALUES (?, ?, ?, ?)", (person_id, arch.name, arch.type, arch.read()))
                        conn.commit()
                        st.success("¡Registro guardado con archivos en la nube!")
    conn.close()

elif menu == "🔍 Buscar / Editar":
    st.title("🔍 Buscador de Trámites")
    st.write("Selecciona una o varias filas usando las casillas de la izquierda.")
    conn = get_db_connection()
    
    query = '''SELECT p.id, p.nombre as Nombre, g.tipo_tramite as Trámite, g.fecha as Fecha, g.monto as Monto, g.estado_pago as Pago, p.datos_dinamicos FROM registros_personas p JOIN registros_grupo g ON p.id_grupo = g.id_grupo'''
    df_busqueda = pd.read_sql(query, conn)
    
    if not df_busqueda.empty:
        df_busqueda['Tipo de Certificado'] = df_busqueda['datos_dinamicos'].apply(lambda x: json.loads(x).get('Tipo de certificado', '-') if pd.notnull(x) else '-')
        
        # APLICAR INSIGNIAS (EMOJIS/COLORES) A LA COLUMNA PAGO
        def formato_pago(val):
            if val == "Pagado":
                return "✅ Pagado"
            return "🔴 Pendiente"
            
        df_busqueda['Pago'] = df_busqueda['Pago'].apply(formato_pago)
        
        buscar = st.text_input("🔎 Buscar por nombre:")
        if buscar:
            df_busqueda = df_busqueda[df_busqueda['Nombre'].str.contains(buscar, case=False, na=False)]
        
        columnas_mostrar = ['Nombre', 'Tipo de Certificado', 'Trámite', 'Fecha', 'Monto', 'Pago']
        df_mostrar = df_busqueda[['id'] + columnas_mostrar]
        
        event = st.dataframe(df_mostrar, column_config={"id": None}, on_select="rerun", selection_mode="multi-row", use_container_width=True, hide_index=True)
        
        if event.selection.rows:
            filas_seleccionadas = event.selection.rows
            ids_seleccionados = [int(df_mostrar.iloc[i]['id']) for i in filas_seleccionadas]
            
            st.divider()
            
            st.error(f"⚠️ Has seleccionado {len(ids_seleccionados)} persona(s).")
            if st.button("🗑️ Eliminar Seleccionados", type="primary"):
                cursor = conn.cursor()
                placeholders = ','.join('?' for _ in ids_seleccionados)
                cursor.execute(f"DELETE FROM archivos_subidos WHERE id_persona IN ({placeholders})", ids_seleccionados)
                cursor.execute(f"DELETE FROM registros_personas WHERE id IN ({placeholders})", ids_seleccionados)
                conn.commit()
                st.success("¡Registros eliminados correctamente!")
                st.rerun()

            if len(ids_seleccionados) == 1:
                id_persona = ids_seleccionados[0]
                p_data = pd.read_sql(f"SELECT p.*, g.* FROM registros_personas p JOIN registros_grupo g ON p.id_grupo = g.id_grupo WHERE p.id = {id_persona}", conn).iloc[0]
                dinamicos_json = json.loads(p_data['datos_dinamicos'])
                
                st.divider()
                colA, colB = st.columns([9, 1])
                colA.subheader(f"📋 Detalles de: {p_data['nombre']}")
                
                if colB.button("✏️ Editar", type="secondary"):
                    st.session_state[f"editando_{id_persona}"] = not st.session_state.get(f"editando_{id_persona}", False)
                
                edit_mode = st.session_state.get(f"editando_{id_persona}", False)
                
                if not edit_mode:
                    col1, col2 = st.columns(2)
                    col1.markdown(f"**Trámite:** {p_data['tipo_tramite']} - {p_data['estado_tramite']}")
                    col1.markdown(f"**Monto:** {p_data['monto']} ({p_data['estado_pago']})")
                    col2.markdown(f"**Rol:** {'Titular' if p_data['es_titular']==1 else 'Adicional'}")
                    if p_data['documentos']: col2.markdown(f"**Docs Físicos:** {p_data['documentos']}")
                    
                    st.markdown("#### Datos de la Casilla")
                    for key, val in dinamicos_json.items():
                        st.markdown(f"**{key}:** {val}")
                    st.markdown(f"**Notas del Grupo:** {p_data['notas']}")
                    
                 # --- FASE 2: VISOR INTELIGENTE (TAMAÑO COMPACTO) ---
                    archivos = pd.read_sql(f"SELECT nombre_archivo, tipo_archivo, datos FROM archivos_subidos WHERE id_persona = {id_persona}", conn)
                    if not archivos.empty:
                        st.markdown("#### 📁 Archivos Adjuntos")
                        
                        imagenes = []
                        otros_archivos = []
                        
                        for _, archivo in archivos.iterrows():
                            if "image" in archivo['tipo_archivo']:
                                imagenes.append(archivo)
                            else:
                                otros_archivos.append(archivo)
                        
                        # 1. Documentos y PDFs (Solo botones de descarga)
                        if otros_archivos:
                            st.write("📄 Documentos:")
                            for idx, archivo in enumerate(otros_archivos):
                                st.download_button(label=f"Descargar {archivo['nombre_archivo']}", data=archivo['datos'], file_name=archivo['nombre_archivo'], mime=archivo['tipo_archivo'], key=f"dl_pdf_{id_persona}_{idx}")
                        
                        # 2. Galería de Imágenes (Tamaño pequeño)
                        if imagenes:
                            st.write("🖼️ Galería Visual:")
                            cols = st.columns(min(len(imagenes), 4)) # Ahora caben 4 fotos pequeñas por fila
                            for idx, img in enumerate(imagenes):
                                with cols[idx % 4]:
                                    try:
                                        foto_virtual = io.BytesIO(img['datos'])
                                        # Aquí limitamos el ancho de la imagen a 200 píxeles para que no sea gigante
                                        st.image(foto_virtual, caption=img['nombre_archivo'], width=200)
                                    except Exception:
                                        st.error("Error al mostrar la imagen.")
                                        
                                    st.download_button(label="📥 Descargar Foto", data=img['datos'], file_name=img['nombre_archivo'], mime=img['tipo_archivo'], key=f"dl_img_{id_persona}_{idx}")

elif menu == "📊 Exportar a Excel":
    st.title("📊 Exportar Datos a Excel (CSV)")
    conn = get_db_connection()
    df_export = pd.read_sql("SELECT g.id_grupo, g.tipo_tramite, g.fecha, g.monto, g.estado_tramite, g.estado_pago, g.notas, p.es_titular, p.nombre, p.datos_dinamicos, p.documentos FROM registros_personas p JOIN registros_grupo g ON p.id_grupo = g.id_grupo", conn)
    conn.close()
    
    if not df_export.empty:
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
        st.download_button(label="📥 Descargar Base de Datos Completa", data=csv, file_name=f"Reporte_Tramites_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv", type="primary")
