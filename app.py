import os
import io
import base64
import zipfile
import pandas as pd
import streamlit as st
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas
from pypdf import PdfReader, PdfWriter

st.set_page_config(page_title="Generador de Reconocimientos", layout="centered")

st.title("Sistema de Generación de Reconocimientos")
st.write("Procesamiento volátil en memoria. Cumplimiento de no persistencia.")

def obtener_iniciales(nombre):
    """Extrae las iniciales de un nombre para la nomenclatura de archivos."""
    if pd.isna(nombre):
        return "SIN_NOMBRE"
    palabras = str(nombre).split()
    return "".join([palabra[0].upper() for palabra in palabras if palabra])

def generar_pdf_individual(nombre_str, titulo_str, pdf_base_bytes, config):
    """
    Genera un solo PDF en memoria. Función reutilizable para Preview y Procesamiento Masivo.
    """
    PAGE_WIDTH, PAGE_HEIGHT = landscape(letter)
    temp_pdf_buffer = io.BytesIO()
    c = canvas.Canvas(temp_pdf_buffer, pagesize=landscape(letter))
    
    centro_x_calculado = (PAGE_WIDTH / 2) + config['desfase_x']
    
    # --- DIBUJAR EL NOMBRE ---
    tamanio_fuente_nombre = config['tamanio_fuente_nombre']
    # Reducción dinámica si el nombre es muy largo
    while c.stringWidth(nombre_str, config['fuente_nombre'], tamanio_fuente_nombre) > config['max_ancho'] and tamanio_fuente_nombre > 10:
        tamanio_fuente_nombre -= 1 
    
    c.setFont(config['fuente_nombre'], tamanio_fuente_nombre)
    c.setFillColor(HexColor(config['color_nombre'])) 
    c.drawCentredString(centro_x_calculado, config['pos_y_nombre'], nombre_str)
    
    # --- DIBUJAR EL TÍTULO (Si aplica) ---
    if not config['plantilla_tiene_titulo']:
        tamanio_fuente_titulo = config['tamanio_fuente_titulo']
        while c.stringWidth(titulo_str, config['fuente_titulo'], tamanio_fuente_titulo) > 500 and tamanio_fuente_titulo > 10:
            tamanio_fuente_titulo -= 1

        c.setFont(config['fuente_titulo'], tamanio_fuente_titulo)
        c.setFillColor(HexColor(config['color_titulo'])) 
        c.drawCentredString(centro_x_calculado, config['pos_y_titulo'], titulo_str)
        
    c.save()
    
    # --- FUSIÓN DE CAPAS EN MEMORIA ---
    temp_pdf_buffer.seek(0)
    text_reader = PdfReader(temp_pdf_buffer)
    
    pdf_base_bytes.seek(0)
    template_reader = PdfReader(pdf_base_bytes)
    
    writer = PdfWriter()
    page = template_reader.pages[0]
    page.merge_page(text_reader.pages[0])
    writer.add_page(page)
    
    output_pdf_buffer = io.BytesIO()
    writer.write(output_pdf_buffer)
    output_pdf_buffer.seek(0)
    
    return output_pdf_buffer

def mostrar_pdf_en_navegador(pdf_buffer):
    """Incrusta un visor de PDF directamente en la interfaz de Streamlit usando Base64"""
    base64_pdf = base64.b64encode(pdf_buffer.getvalue()).decode('utf-8')
    
    # CAMBIO 1: Usamos <embed> en lugar de <iframe> para saltar el bloqueo de Edge
    pdf_display = f'<embed src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600" type="application/pdf">'
    st.markdown(pdf_display, unsafe_allow_html=True)
    
    # CAMBIO 2: Plan B infalible. Un botón para descargar la vista previa rápidamente.
    st.download_button(
        label="📥 Descargar PDF de Vista Previa (Si el visor no carga)",
        data=pdf_buffer,
        file_name="Vista_Previa_Test.pdf",
        mime="application/pdf",
        use_container_width=True
    )

uploaded_excel = st.file_uploader("Cargar archivo Excel (.xlsx)", type=["xlsx"])
uploaded_pdf = st.file_uploader("Cargar Plantilla PDF Base (.pdf)", type=["pdf"])

st.markdown("---")
st.subheader("⚙️ Calibración Visual y Vista Previa")

# Formulario para evitar recargas constantes por cada cambio de slider
with st.expander("Ajustar coordenadas y tipografía", expanded=True):
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Ajustes del Nombre**")
        pos_y_nombre = st.slider("Altura del Nombre (Y)", min_value=150, max_value=400, value=305, step=5)
        desfase_x = st.slider("Desfase Horizontal (X)", min_value=-100, max_value=100, value=-25, step=5)
        max_ancho = st.slider("Ancho Máximo (Línea)", min_value=300, max_value=700, value=480, step=10)
        tamanio_nombre = st.slider("Tamaño Fuente Nombre", min_value=12, max_value=40, value=24)
        fuente_nombre = st.selectbox("Tipografía Nombre", ["Helvetica-Bold", "Helvetica", "Times-Bold", "Times-Roman"])

    with col2:
        st.markdown("**Ajustes del Título**")
        plantilla_tiene_titulo = st.checkbox("La plantilla YA trae el título", value=False)
        pos_y_titulo = st.slider("Altura del Título (Y)", min_value=100, max_value=350, value=215, step=5)
        tamanio_titulo = st.slider("Tamaño Fuente Título", min_value=10, max_value=30, value=16)
        fuente_titulo = st.selectbox("Tipografía Título", ["Helvetica-Bold", "Helvetica", "Times-Bold", "Times-Roman"])

    # Diccionario de configuracion consolidado
    config_visual = {
        'pos_y_nombre': pos_y_nombre,
        'desfase_x': desfase_x,
        'max_ancho': max_ancho,
        'tamanio_fuente_nombre': tamanio_nombre,
        'fuente_nombre': fuente_nombre,
        'color_nombre': "#000000",
        'plantilla_tiene_titulo': plantilla_tiene_titulo,
        'pos_y_titulo': pos_y_titulo,
        'tamanio_fuente_titulo': tamanio_titulo,
        'fuente_titulo': fuente_titulo,
        'color_titulo': "#000000"
    }

st.markdown("**Prueba en tiempo real**")
col_prev1, col_prev2, col_prev3 = st.columns([2, 2, 1])
with col_prev1:
    nombre_prueba = st.text_input("Nombre de prueba", value="Juan Pablo Esteban de la Cruz Martínez Fernández")
with col_prev2:
    titulo_prueba = st.text_input("Título de prueba", value='"Webinar Herramientas OSINT"')
with col_prev3:
    st.write("")
    st.write("") # Espaciador para alinear el botón
    btn_preview = st.button("👁️ Vista Previa", use_container_width=True)

if btn_preview:
    if uploaded_pdf:
        with st.spinner("Generando vista previa..."):
            pdf_preview = generar_pdf_individual(
                nombre_str=nombre_prueba,
                titulo_str=titulo_prueba,
                pdf_base_bytes=uploaded_pdf,
                config=config_visual
            )
            mostrar_pdf_en_navegador(pdf_preview)
    else:
        st.warning("⚠️ Sube la Plantilla PDF Base primero para ver la previsualización.")

st.markdown("---")

if uploaded_excel and uploaded_pdf:
    st.subheader("🚀 Procesamiento Masivo")
    if st.button("Procesar Excel Completo", type="primary"):
        try:
            file_name = uploaded_excel.name.replace(".xlsx", "")
            nombre_platica_real = f'"{file_name}"'

            df = pd.read_excel(uploaded_excel, sheet_name="Aprobados", usecols="B")
            zip_buffer = io.BytesIO()
            
            with st.spinner(f"Procesando {len(df)} registros..."):
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                    control_duplicados = {}

                    for index, row in df.iterrows():
                        nombre_participante = row.iloc[0]
                        if pd.isna(nombre_participante):
                            continue

                        nombre_str = str(nombre_participante).strip()
                        iniciales = obtener_iniciales(nombre_str)
                        
                        if iniciales in control_duplicados:
                            control_duplicados[iniciales] += 1
                            nombre_archivo_pdf = f"Reconocimiento_{iniciales}_{control_duplicados[iniciales]}.pdf"
                        else:
                            control_duplicados[iniciales] = 0
                            nombre_archivo_pdf = f"Reconocimiento_{iniciales}.pdf"

                        # Generamos el PDF usando la misma función de la vista previa, 
                        # asegurando que los resultados sean identicos
                        output_pdf_buffer = generar_pdf_individual(
                            nombre_str=nombre_str,
                            titulo_str=nombre_platica_real,
                            pdf_base_bytes=uploaded_pdf,
                            config=config_visual
                        )
                        
                        zip_file.writestr(nombre_archivo_pdf, output_pdf_buffer.getvalue())

            zip_buffer.seek(0)
            
            st.success(f"¡Proceso finalizado con éxito! Registros procesados: {len(control_duplicados)}")
            
            st.download_button(
                label="📥 Descargar paquete de reconocimientos (.ZIP)",
                data=zip_buffer,
                file_name=f"Reconocimientos_{file_name}.zip",
                mime="application/zip",
                type="primary"
            )
            
            print(f"INFO: [AUDIT] Ejecución exitosa. Dataset: {file_name}. Items: {len(control_duplicados)}.")

        except Exception as e:
            st.error("Error en el procesamiento de archivos. Verifique el formato de la hoja 'Aprobados'.")
            print(f"ERROR: [AUDIT] Fallo en ejecución: {str(e)}")
